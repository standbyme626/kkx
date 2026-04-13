"""
输出模块 - JSON + 飞书
15 个业务字段（含邮件草稿、创建时间）
业务词库生成关键判断信号和分级原因
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime


# ========== 业务词库 ==========

# 市场词库
MARKET_WORDS = {
    "UK": "英国首选市场",
    "AU": "澳洲重点市场",
    "US": "美国培育市场",
    "DE": "德国需认证",
    "OTHER": "非目标市场",
}

# 客户类型词库
TYPE_WORDS = {
    "retail": "英澳礼品买手",
    "chain": "英澳零售商",
    "pet": "美国宠物电商",
    "kids": "儿童礼品专营店",
    "wholesale": "大宗批发商",
    "blank": "空白素坯采购商",
    "supermarket": "超市直采",
}

# 需求词库
NEED_WORDS = {
    "multi": "多材质主题配套",
    "dtf": "DTF快样",
    "sample": "小批量测款",
    "oem": "OEM定制",
    "seasonal": "节日主题快速响应",
}

# 信号词库
SIGNAL_WORDS = {
    "hiring": "招聘品类经理",
    "fair": "参加Reed Gift Fairs",
    "new": "新品上架",
    "funding": "融资",
    "inquiry": "平台询盘",
}

# 风险词库
RISK_WORDS = {
    "en71": "缺EN71认证",
    "lfgb": "缺LFGB认证",
    "price": "只比价",
    "small": "小单散客",
    "cost": "服务成本过高",
}


def _generate_key_signals_business(
    lead: Dict[str, Any], grade: str, country: str, industry: str
) -> str:
    """用业务词库生成关键判断信号"""
    parts = []

    # 市场
    market_word = MARKET_WORDS.get(
        country.upper()[:2] if country else "OTHER", "非目标市场"
    )
    parts.append(f"市场：{market_word}")

    # 类型
    ind = (industry or "").lower()
    if "retail" in ind or "gift" in ind:
        parts.append("类型：英澳礼品买手")
    elif "chain" in ind or "department" in ind:
        parts.append("类型：英澳零售商")
    elif "pet" in ind:
        parts.append("类型：美国宠物电商")
    elif "kids" in ind or "child" in ind:
        parts.append("类型：儿童礼品专营店")
    elif "wholesale" in ind or "distributor" in ind:
        parts.append("类型：大宗批发商")

    # 需求 - 从 business_scope 推断
    scope = (lead.get("business_scope") or "").lower()
    if "oem" in scope or "custom" in scope:
        parts.append("需求：OEM定制")
    elif "dtf" in scope:
        parts.append("需求：DTF快样")
    elif "seasonal" in scope or "christmas" in scope:
        parts.append("需求：节日主题快速响应")

    # 风险 - D级专用
    if grade == "D":
        if "wholesale" in ind or "distributor" in ind:
            parts.append("风险：只比价")
        elif "blank" in ind:
            parts.append("风险：小单散客")
        elif "germany" in country.lower() or "german" in scope:
            parts.append("风险：缺LFGB认证")

    return " / ".join(parts) if parts else "市场：非目标市场"


def _generate_grade_reason_business(
    lead: Dict[str, Any], grade: str, country: str, industry: str
) -> str:
    """用业务话术生成分级原因"""
    ind = (industry or "").lower()
    scope = (lead.get("business_scope") or "").lower()

    if grade == "A":
        if country.upper() in ["UK", "AU"]:
            if "retail" in ind or "gift" in ind:
                return "英国礼品买手，主营家居/礼品，匹配我司首选市场"
            return "英澳零售商家，匹配重点市场"
        return "礼品零售买手，匹配目标市场"

    elif grade == "B":
        if "pet" in ind:
            return "美国宠物电商卖家，主营相关品类，匹配DTF快样优势"
        if "kids" in ind or "child" in ind:
            return "英国儿童礼品专营店，有套装需求，需先确认EN71认证"
        return "市场对/类型对，有合作潜力"

    elif grade == "C":
        if "germany" in country.lower():
            return "德国零售商，但缺少LFGB认证，需先核实"
        if "wholesale" in ind:
            return "大宗批发商，价格敏感，匹配度低"
        return "边缘匹配，信息待完善"

    elif grade == "D":
        if "wholesale" in ind:
            return "小单散客，服务成本过高，暂不优先"
        if "blank" in ind:
            return "只买空白素坯，绕过我司最强印花能力"
        return "非目标客户，暂不优先"

    return ""


def write_json(leads: List[Dict[str, Any]], output_path: str = None) -> str:
    """生成本地 JSON"""
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/output/leads_{timestamp}.json"
        if not os.path.isabs(output_path):
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), output_path
            )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stamped: List[Dict[str, Any]] = []
    for lead in leads:
        row = dict(lead)
        if not row.get("record_created_at"):
            row["record_created_at"] = now
        stamped.append(row)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stamped, f, ensure_ascii=False, indent=2)

    return output_path


def _join_list(values: Any) -> str:
    """列表转字符串"""
    if isinstance(values, list):
        return ", ".join([str(v).strip() for v in values if str(v).strip()])
    return ""


def _normalize_grade(value: str) -> str:
    """标准化等级"""
    raw = str(value or "").upper()
    return raw if raw in ["A", "B", "C", "D"] else "C"


def _derive_search_status(lead: Dict[str, Any]) -> tuple[str, str]:
    """推导搜索处理状态和备注

    使用新的两层评分结构：
    - 客户匹配分决定 A/B/C/D
    - 推进就绪分决定下一步动作
    """
    grade = _normalize_grade(
        lead.get("final_grade")
        or lead.get("customer_grade")
        or lead.get("grade")
        or "D"
    )
    match_score = lead.get("customer_value_score") or lead.get("customer_match_score") or 0
    readiness_score = lead.get("readiness_score") or lead.get("data_completeness_score") or 0
    has_name = bool(lead.get("decision_makers") or lead.get("decision_maker"))
    has_email = bool(lead.get("emails"))
    has_phone = bool(lead.get("contacts"))
    has_linkedin = bool(lead.get("linkedin_urls"))
    has_linkedin_personal = any(
        "/in/" in str(li) for li in (lead.get("linkedin_urls") or [])
    )

    # 优先使用已计算好的推进状态
    pre_computed = lead.get("second_search_status", "")
    if pre_computed:
        status_to_action = {
            "已补全可跟进": ("已补全可跟进", ""),
            "部分补全": ("部分补全", "联系方式不完整"),
            "信息不足，继续背调": ("信息不足，继续背调", "需补充联系方式"),
            "信息严重不足": ("信息严重不足", "需第三次搜索或人工搜索"),
        }
        if pre_computed in status_to_action:
            return status_to_action[pre_computed]

    # 降级推导
    # A. 已补全可跟进
    if has_name and (has_email or has_phone or has_linkedin_personal):
        return "已补全可跟进", ""

    # B. 高匹配度，需第三次搜索（高等级但无联系方式）
    if (grade in ("A", "B") or match_score >= 55) and not (
        has_email or has_phone or has_linkedin_personal
    ):
        return "高匹配度，需第三次搜索", "缺联系方式"

    # C. 高匹配度，需人工搜索
    if grade in ("A", "B") or match_score >= 55:
        clues = []
        if has_linkedin and not has_linkedin_personal:
            clues.append("仅LinkedIn公司页")
        if has_name and not (has_email or has_phone):
            clues.append("有人名无联系方式")
        if clues:
            return "高匹配度，需人工搜索", "，".join(clues)

    # D. 信息不足，继续背调
    if grade == "C":
        return "信息不足，继续背调", "需进一步背调"

    # E. 暂不优先（D级或默认）
    return "暂不优先", "低匹配"


def _format_contact_clues(lead: Dict[str, Any]) -> str:
    """合并联系方式线索

    注意：只在有真实联系方式时才展示，不再凭空拼 /contact 链接
    """
    parts = []

    # 1. 真实邮箱
    emails = lead.get("emails", [])
    if emails:
        parts.extend([str(e) for e in emails[:2]])

    # 2. 电话 - contacts 可能是 dict 列表（来自 enrich.py）或 str 列表
    phones = lead.get("contacts", [])
    if phones:
        for p in phones[:2]:
            if isinstance(p, dict):
                name = p.get("name", "")
                title = p.get("title", "")
                if name:
                    parts.append(f"{name}" + (f" ({title})" if title else ""))
            else:
                parts.append(str(p))

    # 3. LinkedIn 个人页
    linkedins = lead.get("linkedin_urls", [])
    for li in linkedins[:2]:
        if "/in/" in li:
            parts.append(li)

    # 4. 如果有官网但没有其他联系方式，只显示"官网"
    if not parts and lead.get("website"):
        website = lead.get("website", "")
        if website:
            parts.append(website)

    return " | ".join(parts)


def _format_recommended_contact(lead: Dict[str, Any]) -> str:
    """格式化推荐联系人"""
    names = lead.get("decision_makers", [])
    titles = lead.get("decision_maker_titles", [])
    if not names:
        return ""

    # 合并 name + title
    contacts = []
    for i, name in enumerate(names[:3]):
        title = titles[i] if i < len(titles) else ""
        if title:
            contacts.append(f"{name} ({title})")
        else:
            contacts.append(name)

    return " / ".join(contacts)


def _format_for_feishu(lead: Dict[str, Any]) -> Dict[str, Any]:
    """格式化飞书数据 - 15 个字段（含创建时间）"""

    # 获取基础字段
    company_name = lead.get("company_name", "")
    website = lead.get("website", "")
    country = lead.get("country", "")
    industry = lead.get("industry", "")

    # 客户等级
    grade = _normalize_grade(
        lead.get("final_grade")
        or lead.get("customer_grade")
        or lead.get("grade")
        or "D"
    )

    # 客户符合度分
    score = int(lead.get("customer_value_score") or lead.get("total_score") or 0)

    # 分级原因 - 业务词库生成
    reason = _generate_grade_reason_business(lead, grade, country, industry)

    # 关键判断信号 - 业务词库生成
    key_signals = _generate_key_signals_business(lead, grade, country, industry)

    # 推荐联系人
    recommended_contact = _format_recommended_contact(lead)

    # 联系方式线索
    contact_clues = _format_contact_clues(lead)

    # 搜索处理状态 + 备注
    search_status, remark = _derive_search_status(lead)

    # 下一步动作（基于状态）— 覆盖新评分系统的所有可能值
    status_to_action = {
        "已补全可跟进": "立即跟进",
        "高匹配度，需第三次搜索": "第三次搜索",
        "高匹配度，需人工搜索": "人工搜索",
        "高符合度，需第三次搜索": "第三次搜索",
        "高符合度，需人工搜索": "人工搜索",
        "信息不足，继续背调": "继续背调",
        "部分补全": "发送开发信",
        "信息严重不足": "第三次搜索或人工搜索",
        "暂不优先": "暂不优先",
    }
    next_action = status_to_action.get(search_status, "待处理")

    created_at = str(
        lead.get("record_created_at")
        or lead.get("created_at")
        or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    return {
        "公司名称": company_name,
        "官网": website,
        "国家": country,
        "客户类型": industry,
        "客户等级": grade,
        "客户符合度分": float(score),
        "分级原因": reason,
        "关键判断信号": key_signals,
        "推荐联系人": recommended_contact,
        "联系方式线索": contact_clues,
        "邮件草稿": lead.get("email_draft", ""),
        "搜索处理状态": search_status,
        "下一步动作": next_action,
        "备注": remark,
        "创建时间": created_at,
    }


# 飞书字段定义 - 15 个（含邮件草稿、创建时间）
# 可被独立测试接口导入
FEISHU_FIELDS = [
    {"field_name": "公司名称", "type": "text", "field_type": "text"},
    {"field_name": "官网", "type": "text", "field_type": "text"},
    {"field_name": "国家", "type": "text", "field_type": "text"},
    {"field_name": "客户类型", "type": "text", "field_type": "text"},
    {"field_name": "客户等级", "type": "text", "field_type": "text"},
    {"field_name": "客户符合度分", "type": "number", "field_type": "number"},
    {"field_name": "分级原因", "type": "text", "field_type": "text"},
    {"field_name": "关键判断信号", "type": "text", "field_type": "text"},
    {"field_name": "推荐联系人", "type": "text", "field_type": "text"},
    {"field_name": "联系方式线索", "type": "text", "field_type": "text"},
    {"field_name": "邮件草稿", "type": "text", "field_type": "text"},
    {"field_name": "搜索处理状态", "type": "text", "field_type": "text"},
    {"field_name": "下一步动作", "type": "text", "field_type": "text"},
    {"field_name": "备注", "type": "text", "field_type": "text"},
    {"field_name": "创建时间", "type": "text", "field_type": "text"},
]


def build_feishu_table_open_url(app_token: str, table_id: str) -> str:
    """生成在浏览器中打开指定数据表的链接（同一 Base App）。"""
    import config as cfg

    token = (app_token or cfg.FEISHU_APP_TOKEN or "").strip()
    tid = (table_id or "").strip()
    if not token or not tid:
        return ""
    base = str(cfg.FEISHU_BITABLE_WEB_BASE).rstrip("/")
    return f"{base}/{token}?table={tid}"


async def _get_tenant_access_token(
    app_id: str, app_secret: str
) -> dict:
    """
    通过 app_id + app_secret 获取 tenant_access_token。
    返回 {"tenant_token": "...", "error": None} 或 {"tenant_token": None, "error": "..."}
    """
    import requests

    print(f"🔵 [飞书Token] 开始获取 tenant_access_token")
    print(f"   app_id: {app_id[:12]}... (脱敏)")

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": app_id, "app_secret": app_secret}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        data = resp.json()

        print(f"   响应状态: {resp.status_code}")
        print(f"   响应内容: {json.dumps(data, ensure_ascii=False)[:300]}")

        if resp.status_code == 200 and data.get("code") == 0:
            token = data.get("tenant_access_token")
            if token:
                print(f"   ✅ 获取 tenant_access_token 成功")
                return {"tenant_token": token, "error": None}
            else:
                err = "响应中无 tenant_access_token 字段"
                print(f"   ❌ {err}")
                return {"tenant_token": None, "error": err}
        else:
            msg = data.get("msg", "未知错误")
            code = data.get("code", "unknown")
            err = f"获取 token 失败: {msg}, code: {code}"
            print(f"   ❌ {err}")
            return {"tenant_token": None, "error": err}

    except requests.exceptions.Timeout:
        err = "获取 tenant_access_token 超时"
        print(f"   ❌ {err}")
        return {"tenant_token": None, "error": err}
    except Exception as e:
        err = f"获取 token 异常: {str(e)}"
        print(f"   ❌ {err}")
        return {"tenant_token": None, "error": err}


async def create_feishu_table(
    app_token: str = None,
    table_name: str = "外贸获客结果v17",
    app_id: str = None,
    app_secret: str = None,
) -> dict:
    """
    创建飞书多维表 - 直接调用飞书 Open API
    流程: 1. 用 app_id+app_secret 获取 tenant_access_token
         2. 用 tenant_access_token 调用创建表 API
    """
    import requests

    import config as cfg

    # 1. 获取凭证
    if not app_id:
        app_id = os.getenv("FEISHU_APP_ID", "") or cfg.FEISHU_APP_ID
    if not app_secret:
        app_secret = os.getenv("FEISHU_APP_SECRET", "") or cfg.FEISHU_APP_SECRET
    if not app_token:
        app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN", "") or cfg.FEISHU_APP_TOKEN

    if not app_id or not app_secret:
        print("❌ [飞书建表] 未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        return {"error": "未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET"}

    if not app_token:
        print("❌ [飞书建表] 未配置 FEISHU_BITABLE_APP_TOKEN")
        return {"error": "未配置 FEISHU_BITABLE_APP_TOKEN"}

    print(f"🔵 [飞书建表] 开始建表，表名={table_name}")
    print(f"   app_token 末尾: {app_token[-8:] if app_token else 'None'}")
    print(f"   app_id: {app_id[:12]}... (脱敏)")

    # Step 1: 获取 tenant_access_token
    token_result = await _get_tenant_access_token(app_id, app_secret)
    if token_result["error"]:
        return {
            "error": f"获取 tenant_access_token 失败: {token_result['error']}",
            "tenant_token_obtained": False,
            "auth_mode": "app_id+app_secret",
            "app_token_tail": app_token[-8:] if app_token else None,
        }

    tenant_token = token_result["tenant_token"]

    # Step 2: 创建表 (在已有的 Base App 下新建一张数据表)
    # 正确 URL: POST /bitable/v1/apps/{app_token}/tables
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    print(f"   请求 URL: {url}")
    print(f"   Auth 模式: Bearer (tenant_access_token)")

    # 构建字段定义 - 飞书使用整数 type
    # 1=文本, 2=数字, 5=日期, 11=超链接
    fields = []
    for f in FEISHU_FIELDS:
        field_type = f.get("field_type", f.get("type", "text"))
        if field_type == "number":
            api_type = 2  # 数字
        else:
            api_type = 1  # 文本

        fields.append({"field_name": f["field_name"], "type": api_type})

    payload = {"table": {"name": table_name, "fields": fields}}

    print(f"   发送创建请求...")
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)

        # 先打印原始响应，再尝试解析
        print(f"   响应状态: {resp.status_code}")
        print(f"   响应头 Content-Type: {resp.headers.get('Content-Type', 'unknown')}")
        print(f"   响应原始文本 (前500字符): {resp.text[:500]}")

        try:
            data = resp.json()
        except Exception as json_err:
            print(f"   ❌ JSON 解析失败: {str(json_err)}")
            return {
                "error": f"飞书 API 响应解析失败: {str(json_err)}, 响应内容: {resp.text[:300]}",
                "tenant_token_obtained": True,
                "auth_mode": "app_id+app_secret",
                "app_token_tail": app_token[-8:] if app_token else None,
            }

        print(f"   响应内容: {json.dumps(data, ensure_ascii=False)[:500]}")

        if resp.status_code == 200 and data.get("code") == 0:
            # 飞书返回: data.table_id (直接在 data 下，不在 data.table 下)
            table_id = data.get("data", {}).get("table_id")
            if not table_id:
                # 兼容可能的嵌套格式
                table_id = data.get("data", {}).get("table", {}).get("table_id")
            print(f"   ✅ 建表成功! table_id={table_id}")
            return {
                "table_id": table_id,
                "data": data,
                "tenant_token_obtained": True,
                "auth_mode": "app_id+app_secret",
                "app_token_tail": app_token[-8:] if app_token else None,
            }
        else:
            msg = data.get("msg", "未知错误")
            code = data.get("code", "unknown")
            err = f"飞书 API 错误: {msg}, code: {code}"
            print(f"   ❌ 建表失败! {err}")
            return {
                "error": err,
                "tenant_token_obtained": True,
                "auth_mode": "app_id+app_secret",
                "app_token_tail": app_token[-8:] if app_token else None,
            }

    except requests.exceptions.Timeout:
        err = "飞书 API 请求超时"
        print(f"   ❌ {err}")
        return {"error": err}
    except Exception as e:
        err = f"建表异常: {str(e)}"
        print(f"   ❌ {err}")
        return {"error": err}


async def write_feishu(leads: List[Dict[str, Any]], table_id: str = None) -> dict:
    """写入飞书多维表"""
    import sys
    from pathlib import Path

    import config as cfg

    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

    from app.providers.feishu import create_feishu_provider

    if not table_id:
        table_id = os.getenv("FEISHU_BITABLE_TABLE_ID", "") or cfg.FEISHU_TABLE_ID

    if not table_id:
        print("❌ [飞书写入] 未配置 FEISHU_BITABLE_TABLE_ID")
        return {"error": "未配置 FEISHU_BITABLE_TABLE_ID"}

    print(f"🔵 [飞书写入] 开始写入，table_id={table_id}, 记录数={len(leads)}")

    feishu = create_feishu_provider(table_id_override=table_id)
    records = [_format_for_feishu(lead) for lead in leads]

    try:
        # 打印第一条记录的所有字段类型，排查类型问题
        if records:
            first = records[0]
            for k, v in first.items():
                t = type(v).__name__
                print(f"   字段检查: {k} -> {t} = {str(v)[:60]}")

        print(f"   调用 feishu.write_records()...")
        result = await feishu.write_records(records)
        print(f"   写入响应: {json.dumps(result, ensure_ascii=False)[:500]}")
        if isinstance(result, dict) and result.get("error"):
            print(f"   ❌ 飞书写入失败: {result['error']}")
        else:
            print(f"   ✅ 飞书写入成功")
        return result
    except Exception as e:
        err = f"飞书写入异常: {str(e)}"
        print(f"   ❌ {err}")
        import traceback
        traceback.print_exc()
        return {"error": err}


# ========== 演示 ==========
if __name__ == "__main__":
    # 演示数据
    demo_records = [
        {
            "company_name": "The Range",
            "website": "https://www.therange.co.uk/",
            "country": "UK",
            "industry": "Retail",
            "final_grade": "A",
            "customer_value_score": 85,
            "grading_reason": "目标种子客户，英国市场",
            "key_signals": ["目标市场匹配", "种子客户"],
            "decision_makers": ["John Smith"],
            "decision_maker_titles": ["Category Buyer"],
            "emails": ["buyer@therange.co.uk"],
            "contacts": [],
            "linkedin_urls": [],
        },
        {
            "company_name": "Dunelm",
            "website": "https://www.dunelm.com/",
            "country": "UK",
            "industry": "Retail",
            "final_grade": "B",
            "customer_value_score": 75,
            "grading_reason": "英国零售",
            "key_signals": ["目标市场"],
            "decision_makers": [],
            "emails": [],
            "contacts": [],
            "linkedin_urls": ["https://linkedin.com/company/dunelm"],
        },
        {
            "company_name": "Small Shop",
            "website": "https://smallshop.co.uk/",
            "country": "UK",
            "industry": "Retail",
            "final_grade": "D",
            "customer_value_score": 30,
            "grading_reason": "低匹配",
            "key_signals": [],
            "decision_makers": [],
            "emails": [],
            "contacts": [],
            "linkedin_urls": [],
        },
    ]

    print("=== 演示新飞书格式 ===")
    for rec in demo_records:
        result = _format_for_feishu(rec)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("---")
