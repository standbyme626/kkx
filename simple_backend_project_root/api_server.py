"""
Simple Backend API Server - FastAPI 包装层
每次 Demo：同一 Base App 下新建一张表，表名 = run_name，流水线结束后写入该表。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------- 路径：优先注入 backend（飞书 / LLM provider）----------
_ROOT = Path(__file__).resolve().parent
_BACKEND = Path(os.getenv("SWSAGE_BACKEND_ROOT", str(_ROOT.parent / "backend")))
if _BACKEND.is_dir():
    sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_ROOT))

import config  # noqa: E402
from output import build_feishu_table_open_url, create_feishu_table  # noqa: E402
from run_naming import (  # noqa: E402
    make_demo_run_table_name,
    make_demo_run_table_name_with_retry,
)


# ==================== 数据模型 ====================


class RunRequest(BaseModel):
    profile: Optional[str] = None
    rules: Optional[str] = None
    max_leads: int = 10
    use_llm_queries: bool = True
    use_llm_actions: bool = True
    output_feishu: bool = True


class RunResponse(BaseModel):
    run_id: str
    run_name: str
    feishu_table_name: str
    feishu_sync_status: str
    status: str
    feishu_table_id: Optional[str] = None
    feishu_table_url: Optional[str] = None
    feishu_sync_error: Optional[str] = None


# ==================== 运行注册表 ====================


def _normalize_run_record(raw: dict) -> dict:
    """兼容旧 runs_index 缺字段。"""
    defaults = {
        "run_name": raw.get("run_name") or raw.get("run_id", ""),
        "feishu_table_name": raw.get("feishu_table_name"),
        "feishu_table_id": raw.get("feishu_table_id"),
        "feishu_table_url": raw.get("feishu_table_url"),
        "feishu_sync_status": raw.get("feishu_sync_status") or "未创建",
        "feishu_sync_error": raw.get("feishu_sync_error"),
    }
    merged = {
        **raw,
        **{k: v for k, v in defaults.items() if k not in raw or raw.get(k) is None},
    }
    if not merged.get("run_name"):
        merged["run_name"] = merged.get("run_id", "")
    if not merged.get("feishu_table_name"):
        merged["feishu_table_name"] = merged.get("run_name")
    return merged


class RunRegistry:
    def __init__(self):
        self.runs: dict[str, dict] = {}
        self._load_from_file()

    def _get_index_path(self) -> Path:
        return config.RUNS_INDEX_FILE

    def _load_from_file(self):
        idx_path = self._get_index_path()
        if idx_path.exists():
            try:
                with open(idx_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    raw_runs = data.get("runs", {})
                    self.runs = {
                        k: _normalize_run_record(v) for k, v in raw_runs.items()
                    }
            except Exception as e:
                print(f"加载运行记录失败: {e}")
                self.runs = {}

    def _save_to_file(self):
        idx_path = self._get_index_path()
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(idx_path, "w", encoding="utf-8") as f:
                json.dump({"runs": self.runs}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存运行记录失败: {e}")

    def create(self, run_id: str, record: dict) -> dict:
        self.runs[run_id] = _normalize_run_record(record)
        self._save_to_file()
        return self.runs[run_id]

    def update(self, run_id: str, **kwargs):
        if run_id in self.runs:
            self.runs[run_id].update(kwargs)
            self._save_to_file()

    def get(self, run_id: str) -> Optional[dict]:
        return self.runs.get(run_id)

    def list_all(self) -> list[dict]:
        runs = list(self.runs.values())
        runs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return runs

    def get_summary_from_output(self, output_file: str) -> Optional[dict]:
        if not output_file or not Path(output_file).exists():
            return None
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                leads = json.load(f)
            return self.summary_from_leads(leads)
        except Exception as e:
            print(f"解析输出文件失败: {e}")
            return None

    @staticmethod
    def summary_from_leads(leads: list) -> Optional[dict]:
        if not leads:
            return None
        grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for lead in leads:
            g = str(
                lead.get("final_grade")
                or lead.get("customer_grade")
                or lead.get("grade")
                or "D"
            ).upper()
            if g not in grade_counts:
                g = "D"
            grade_counts[g] += 1
        return {
            "total": len(leads),
            "grade_counts": grade_counts,
            "a_count": grade_counts["A"],
            "b_count": grade_counts["B"],
            "c_count": grade_counts["C"],
            "d_count": grade_counts["D"],
        }


registry = RunRegistry()


def _parse_table_id_from_create_result(cre: dict) -> Optional[str]:
    if not isinstance(cre, dict):
        return None
    if cre.get("error"):
        return None
    tid = cre.get("table_id")
    if tid:
        return str(tid)
    # 飞书返回格式: data.table_id
    nested = cre.get("data")
    if isinstance(nested, dict):
        tid = nested.get("table_id")
        if tid:
            return str(tid)
        # 兼容旧格式: data.table.table_id
        nested2 = nested.get("table")
        if isinstance(nested2, dict):
            tid = nested2.get("table_id")
            if tid:
                return str(tid)
    return None


# ==================== FastAPI ====================


app = FastAPI(title="Simple Backend API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"ok": True}


# ==================== 独立飞书建表测试接口 ====================

import config


@app.get("/api/feishu/test-create-table")
async def test_create_table():
    """独立飞书建表测试 - 不走主流程，先验证建表本身是否成功"""
    # 生成业务名
    table_name = make_demo_run_table_name()
    app_token = config.FEISHU_APP_TOKEN

    result = {
        "ok": False,
        "table_name": table_name,
        "table_id": None,
        "table_url": None,
        "raw_error": None,
        "auth_mode": "app_token",
        "app_token_tail": app_token[-8:] if app_token else None,
        "tenant_token_obtained": False,
        "steps": {
            "token_ready": bool(app_token),
            "create_request_sent": False,
            "create_response_received": False,
        },
    }

    print(f"\n{'=' * 50}")
    print(f"🧪 [飞书建表测试] 开始测试")
    print(f"   表名: {table_name}")
    print(f"   app_token 末尾: {app_token[-8:] if app_token else 'None'}")
    print(f"{'=' * 50}\n")

    # Step 1: 检查 token
    if not app_token:
        result["raw_error"] = "FEISHU_APP_TOKEN 未配置"
        print(f"❌ [飞书建表测试] Token 未配置\n")
        return result

    # Step 2: 直接调用 create_feishu_table
    try:
        result["steps"]["create_request_sent"] = True
        print(f"🔵 [飞书建表测试] 调用 create_feishu_table()...")
        create_result = await create_feishu_table(
            app_token=app_token, table_name=table_name
        )
        result["steps"]["create_response_received"] = True
        print(f"🔵 [飞书建表测试] 收到响应\n")

        # 解析响应
        if isinstance(create_result, dict):
            if create_result.get("error"):
                result["raw_error"] = str(create_result.get("error"))
                print(f"❌ [飞书建表测试] 建表失败: {result['raw_error']}\n")
            else:
                # 成功
                result["ok"] = True
                result["tenant_token_obtained"] = True
                result["table_id"] = _parse_table_id_from_create_result(create_result)
                print(f"✅ [飞书建表测试] 建表成功! table_id={result['table_id']}\n")
                # 生成 URL
                if result["table_id"]:
                    result["table_url"] = build_feishu_table_open_url(
                        app_token, result["table_id"]
                    )
                    print(f"   表链接: {result['table_url']}\n")
        else:
            result["raw_error"] = f"返回值不是 dict: {type(create_result)}"
            print(f"❌ [飞书建表测试] 返回值类型错误: {result['raw_error']}\n")

    except Exception as e:
        result["raw_error"] = f"建表异常: {str(e)}"
        import traceback

        result["raw_error"] += f"\n{traceback.format_exc()}"
        print(f"❌ [飞书建表测试] 异常: {result['raw_error']}\n")

    return result


@app.post("/api/run", response_model=RunResponse)
async def start_run(req: RunRequest, background_tasks: BackgroundTasks):
    run_name = make_demo_run_table_name()
    run_id = uuid.uuid4().hex[:12]

    profile_path = req.profile or str(config.PROFILE_PATH)
    rules_path = req.rules or str(config.RULES_PATH)

    feishu_table_id: Optional[str] = None
    feishu_table_url: Optional[str] = None
    feishu_sync_status = "未创建"
    feishu_sync_error: Optional[str] = None

    # ---- Step 1: 先尝试飞书建表（如果启用） ----
    if req.output_feishu:
        max_retries = 5
        for attempt in range(max_retries):
            table_name = make_demo_run_table_name_with_retry(attempt=attempt)
            print(f"\n{'=' * 50}")
            print(f"🔵 [{run_id}] 步骤 1: 尝试飞书建表 (attempt {attempt + 1}/{max_retries})")
            print(f"   表名: {table_name}")
            print(f"{'=' * 50}")
            try:
                cre = await create_feishu_table(
                    table_name=table_name,
                    app_id=config.FEISHU_APP_ID,
                    app_secret=config.FEISHU_APP_SECRET,
                    app_token=config.FEISHU_APP_TOKEN,
                )
                if isinstance(cre, dict) and cre.get("error"):
                    err_str = str(cre.get("error", ""))
                    # 表名重复 → 重试
                    if "TableNameDuplicated" in err_str or "1254013" in err_str:
                        print(f"⚠️ [{run_id}] 表名重复，尝试新名字...")
                        continue
                    feishu_sync_status = "失败"
                    feishu_sync_error = err_str
                    print(f"❌ [{run_id}] 飞书建表失败: {feishu_sync_error}")
                    break
                else:
                    feishu_table_id = _parse_table_id_from_create_result(cre or {})
                    if not feishu_table_id:
                        feishu_sync_status = "失败"
                        feishu_sync_error = "创建表成功但未解析到 table_id"
                        print(f"❌ [{run_id}] 建表成功但无 table_id")
                        break
                    feishu_sync_status = "已创建"
                    feishu_table_url = build_feishu_table_open_url(
                        config.FEISHU_APP_TOKEN, feishu_table_id
                    )
                    run_name = table_name  # 更新 run_name 为实际使用的表名
                    print(f"✅ [{run_id}] 飞书建表成功: table_id={feishu_table_id}")
                    print(f"   链接: {feishu_table_url}")
                    break  # 成功，退出重试循环
            except Exception as e:
                err_str = str(e)
                # 表名重复 → 重试
                if "TableNameDuplicated" in err_str or "1254013" in err_str:
                    print(f"⚠️ [{run_id}] 建表异常(表名重复)，尝试新名字...")
                    continue
                feishu_sync_status = "失败"
                feishu_sync_error = f"飞书建表异常: {err_str}"
                print(f"❌ [{run_id}] 飞书建表异常: {feishu_sync_error}")
                break
        else:
            # 重试耗尽
            if feishu_sync_status != "失败":
                feishu_sync_status = "失败"
                feishu_sync_error = f"表名重试 {max_retries} 次仍重复"
                print(f"❌ [{run_id}] 重试耗尽: {feishu_sync_error}")

    # ---- Step 2: 建表失败 → 直接标为 failed，不跑主流程 ----
    if req.output_feishu and feishu_sync_status == "失败":
        record = {
            "run_id": run_id,
            "run_name": run_name,
            "status": "failed",
            "created_at": datetime.now().isoformat(),
            "params": {
                "profile": profile_path,
                "rules": rules_path,
                "max_leads": req.max_leads,
                "use_llm_queries": req.use_llm_queries,
                "use_llm_actions": req.use_llm_actions,
                "output_feishu": req.output_feishu,
            },
            "output_file": None,
            "summary": None,
            "error": f"飞书建表失败，未启动主流程",
            "stdout": "",
            "stderr": feishu_sync_error or "",
            "feishu_table_name": run_name,
            "feishu_table_id": None,
            "feishu_table_url": None,
            "feishu_sync_status": feishu_sync_status,
            "feishu_sync_error": feishu_sync_error,
            "failed_stage": "飞书建表",
        }
        registry.create(run_id, record)
        return RunResponse(
            run_id=run_id,
            run_name=run_name,
            feishu_table_name=run_name,
            feishu_sync_status=feishu_sync_status,
            status="failed",
            feishu_table_id=None,
            feishu_table_url=None,
            feishu_sync_error=feishu_sync_error,
        )

    # ---- Step 3: 建表成功（或未启用飞书）→ 启动主流程 ----
    do_write_feishu = bool(req.output_feishu and feishu_table_id)

    params: dict[str, Any] = {
        "profile": profile_path,
        "rules": rules_path,
        "max_leads": req.max_leads,
        "use_llm_queries": req.use_llm_queries,
        "use_llm_actions": req.use_llm_actions,
        "output_feishu": do_write_feishu,
    }

    record = {
        "run_id": run_id,
        "run_name": run_name,
        "status": "running",
        "created_at": datetime.now().isoformat(),
        "params": params,
        "output_file": None,
        "summary": None,
        "error": None,
        "stdout": "",
        "stderr": "",
        "feishu_table_name": run_name,
        "feishu_table_id": feishu_table_id,
        "feishu_table_url": feishu_table_url or None,
        "feishu_sync_status": feishu_sync_status,
        "feishu_sync_error": feishu_sync_error,
        "failed_stage": None,
        "failed_agent": None,
    }
    registry.create(run_id, record)

    background_tasks.add_task(
        run_pipeline_task,
        run_id,
        profile_path,
        rules_path,
        req.max_leads,
        req.use_llm_queries,
        req.use_llm_actions,
        do_write_feishu,
        feishu_table_id,
    )

    return RunResponse(
        run_id=run_id,
        run_name=run_name,
        feishu_table_name=run_name,
        feishu_sync_status=feishu_sync_status if feishu_sync_status != "未创建" else ("已创建" if do_write_feishu else "未启用"),
        status="running",
        feishu_table_id=feishu_table_id,
        feishu_table_url=feishu_table_url or None,
        feishu_sync_error=feishu_sync_error,
    )


async def run_pipeline_task(
    run_id: str,
    profile_path: str,
    rules_path: str,
    max_leads: int,
    use_llm_queries: bool,
    use_llm_actions: bool,
    output_feishu: bool,
    feishu_table_id: Optional[str],
):
    """异步执行主流程（与 CLI 同源 run_workflow）。"""
    from main import run_workflow

    if output_feishu and feishu_table_id:
        registry.update(run_id, feishu_sync_status="写入中", feishu_sync_error=None)

    try:
        _scored, output_path = await run_workflow(
            profile_path=profile_path,
            rules_path=rules_path,
            use_llm_for_queries=use_llm_queries,
            use_llm_for_actions=use_llm_actions,
            max_leads=max_leads,
            output_json=True,
            output_feishu=output_feishu,
            feishu_table_id=feishu_table_id,
        )

        summary = None
        if output_path and Path(output_path).exists():
            summary = registry.get_summary_from_output(output_path)

        extra: dict[str, Any] = {
            "status": "completed",
            "output_file": output_path,
            "summary": summary,
            "failed_stage": None,
            "failed_agent": None,
        }
        if output_feishu and feishu_table_id:
            extra["feishu_sync_status"] = "已完成"
            extra["feishu_sync_error"] = None

        registry.update(run_id, **extra)
        print(f"[{run_id}] 完成，输出: {output_path}")

    except Exception as e:
        err = str(e)
        import traceback
        tb = traceback.format_exc()
        print(f"[{run_id}] Full traceback:\n{tb}")
        # 尝试判断失败阶段
        failed_stage = "主流程执行"
        failed_agent = None
        err_lower = err.lower()
        if "profile" in err_lower or "画像" in err_lower:
            failed_stage = "加载数据"
            failed_agent = "loader"
        elif "rule" in err_lower or "规则" in err_lower:
            failed_stage = "加载规则"
            failed_agent = "loader"
        elif "search" in err_lower or "搜索" in err_lower:
            failed_stage = "搜索客户"
            failed_agent = "searcher"
        elif "score" in err_lower or "评分" in err_lower or "grade" in err_lower:
            failed_stage = "客户分级"
            failed_agent = "scorer"
        elif "enrich" in err_lower or "联系人" in err_lower:
            failed_stage = "联系人补全"
            failed_agent = "enrich"
        elif "email" in err_lower or "邮件" in err_lower:
            failed_stage = "邮件草稿"
            failed_agent = "actions"
        elif "feishu" in err_lower or "飞书" in err_lower or "写入" in err_lower:
            failed_stage = "飞书写入"
            failed_agent = "output"

        stderr_text = (registry.get(run_id) or {}).get("stderr", "") or ""
        stderr_text = (stderr_text + f"\n{err}").strip()

        update_data: dict[str, Any] = {
            "status": "failed",
            "error": err,
            "stderr": stderr_text,
            "failed_stage": failed_stage,
            "failed_agent": failed_agent,
        }

        if output_feishu and feishu_table_id:
            update_data["feishu_sync_status"] = "失败"
            update_data["feishu_sync_error"] = err

        registry.update(run_id, **update_data)
        print(f"[{run_id}] 失败: {e}")


@app.get("/api/runs")
async def list_runs():
    runs = registry.list_all()
    result = []
    for r in runs:
        result.append(
            {
                "run_id": r["run_id"],
                "run_name": r.get("run_name") or r["run_id"],
                "status": r["status"],
                "created_at": r["created_at"],
                "output_file": r.get("output_file"),
                "summary": r.get("summary"),
                "feishu_table_name": r.get("feishu_table_name"),
                "feishu_sync_status": r.get("feishu_sync_status") or "未创建",
                "feishu_table_url": r.get("feishu_table_url"),
                "error": r.get("error"),
                "failed_stage": r.get("failed_stage"),
            }
        )
    return result


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    run = registry.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    leads = []
    output_file = run.get("output_file")
    if output_file and Path(output_file).exists():
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                leads = json.load(f)
        except Exception as e:
            print(f"读取输出文件失败: {e}")

    summary = RunRegistry.summary_from_leads(leads) or run.get("summary")

    return {
        "run_id": run["run_id"],
        "run_name": run.get("run_name") or run["run_id"],
        "status": run["status"],
        "created_at": run["created_at"],
        "params": run.get("params"),
        "output_file": run.get("output_file"),
        "summary": summary,
        "lead_count": len(leads),
        "error": run.get("error"),
        "stdout": run.get("stdout"),
        "stderr": run.get("stderr"),
        "leads": leads,
        "feishu_table_name": run.get("feishu_table_name"),
        "feishu_table_id": run.get("feishu_table_id"),
        "feishu_table_url": run.get("feishu_table_url"),
        "feishu_sync_status": run.get("feishu_sync_status") or "未创建",
        "feishu_sync_error": run.get("feishu_sync_error"),
        "failed_stage": run.get("failed_stage"),
        "failed_agent": run.get("failed_agent"),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
