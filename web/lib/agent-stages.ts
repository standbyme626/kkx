import type { RunDetailResponse } from "@/lib/types";
import type { InferredRunUi } from "@/lib/run-status";

export type AgentUiStatus = "等待中" | "进行中" | "已完成" | "失败" | "未启用";

export type AgentStageModel = {
  id: string;
  name: string;
  blurb: string;
  status: AgentUiStatus;
  progress: number;
};

const AGENTS: Omit<AgentStageModel, "status" | "progress">[] = [
  {
    id: "profile",
    name: "公司画像识别 Agent",
    blurb: "读取画像与规则，锁定目标市场与产品语境。",
  },
  {
    id: "search",
    name: "候选客户搜索 Agent",
    blurb: "生成检索词并抓取候选客户，完成归一化。",
  },
  {
    id: "grade",
    name: "客户分级 Agent",
    blurb: "按规则计算符合度与 A/B/C/D 等级。",
  },
  {
    id: "enrich",
    name: "联系人补全 Agent",
    blurb: "对高价值客户二次搜索，补全决策人与线索。",
  },
  {
    id: "action",
    name: "动作建议 Agent",
    blurb: "生成下一步动作与邮件草稿（可关 LLM）。",
  },
  {
    id: "feishu",
    name: "飞书同步 Agent",
    blurb: "将完整 15 字段写入多维表（按需启用）。",
  },
];

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n));
}

/** 用后端 feishu_sync_status 校准「飞书同步 Agent」卡片 */
function applyFeishuFromServer(
  stages: AgentStageModel[],
  run: RunDetailResponse | null
): AgentStageModel[] {
  if (!run) return stages;
  const idx = stages.findIndex((s) => s.id === "feishu");
  if (idx < 0) return stages;
  const st = run.feishu_sync_status || "未创建";
  const pipelineOn = run.params?.output_feishu === true;

  if (!pipelineOn && st === "未创建") {
    stages[idx] = { ...stages[idx], status: "未启用", progress: 0 };
    return stages;
  }

  switch (st) {
    case "已创建":
      stages[idx] = { ...stages[idx], status: "进行中", progress: 45 };
      break;
    case "写入中":
      stages[idx] = { ...stages[idx], status: "进行中", progress: 72 };
      break;
    case "已完成":
      stages[idx] = { ...stages[idx], status: "已完成", progress: 100 };
      break;
    case "失败":
      stages[idx] = { ...stages[idx], status: "失败", progress: 40 };
      break;
    default:
      break;
  }
  return stages;
}

/**
 * 根据 run 状态与前端推断进度，生成 6 个 Agent 卡片的展示状态（纯前端推断）。
 */
export function buildAgentStages(
  run: RunDetailResponse | null,
  ui: InferredRunUi
): AgentStageModel[] {
  const status = run?.status ?? "";
  const leadCount = run?.lead_count ?? run?.leads?.length ?? 0;
  const maxLeads = run?.params?.max_leads ?? 10;
  const useLlmActions = run?.params?.use_llm_actions !== false;
  const outputFeishu = Boolean(run?.params?.output_feishu);
  const p = ui.progressPercent;

  const base = (): AgentStageModel[] =>
    AGENTS.map((a) => ({
      ...a,
      status: "等待中" as AgentUiStatus,
      progress: 0,
    }));

  if (!run) {
    return AGENTS.map((a) => ({
      ...a,
      status: a.id === "feishu" ? "未启用" : ("等待中" as AgentUiStatus),
      progress: 0,
    }));
  }

  if (status === "failed") {
    const arr: AgentStageModel[] = AGENTS.map((a, i) => {
      if (a.id === "feishu") {
        return { ...a, status: "未启用" as AgentUiStatus, progress: 0 };
      }
      if (i <= 1) return { ...a, status: "已完成" as AgentUiStatus, progress: 100 };
      if (i === 2)
        return { ...a, status: "失败" as AgentUiStatus, progress: 35 };
      return { ...a, status: "等待中" as AgentUiStatus, progress: 0 };
    });
    return applyFeishuFromServer(arr, run);
  }

  if (status === "completed") {
    const arr: AgentStageModel[] = AGENTS.map((a) => {
      if (a.id === "feishu") {
        if (!outputFeishu)
          return { ...a, status: "未启用" as AgentUiStatus, progress: 0 };
        return { ...a, status: "已完成" as AgentUiStatus, progress: 100 };
      }
      return { ...a, status: "已完成" as AgentUiStatus, progress: 100 };
    });
    return applyFeishuFromServer(arr, run);
  }

  if (status === "running") {
    const stages = base();

    const setProg = (idx: number, st: AgentUiStatus, pg: number) => {
      stages[idx] = { ...stages[idx], status: st, progress: clamp(pg, 0, 100) };
    };

    // 画像：起步即推进
    if (p <= 5) {
      setProg(0, "进行中", 55);
    } else {
      setProg(0, "已完成", 100);
    }

    // 搜索
    if (p <= 5) {
      setProg(1, "等待中", 0);
    } else if (p <= 25) {
      setProg(1, "进行中", 40 + p);
    } else {
      setProg(1, "已完成", 100);
    }

    // 分级
    if (p < 25) {
      setProg(2, "等待中", 0);
    } else if (p < 60) {
      setProg(2, "进行中", 35 + Math.round((p - 25) * 1.2));
    } else {
      setProg(2, "已完成", 100);
    }

    // 联系人补全（与高阶流水线并行感）
    if (p < 35) {
      setProg(3, "等待中", 0);
    } else if (p < 60) {
      setProg(3, "进行中", 30 + Math.round((p - 35) * 1.4));
    } else {
      setProg(3, "已完成", 100);
    }

    // 动作建议
    if (!useLlmActions) {
      setProg(4, "已完成", 100);
    } else if (p < 50) {
      setProg(4, "等待中", 0);
    } else if (p < 85) {
      setProg(4, "进行中", 25 + Math.round((p - 50) * 2));
    } else {
      setProg(4, "已完成", 100);
    }

    // 飞书
    if (!outputFeishu) {
      stages[5] = { ...stages[5], status: "未启用", progress: 0 };
    } else if (p < 90) {
      setProg(5, "等待中", 0);
    } else {
      setProg(5, "进行中", 80);
    }

    // 有中间结果时，稍微拉高「动作」进度观感
    if (leadCount > 0 && p >= 25 && p < 60) {
      setProg(4, "进行中", Math.max(stages[4].progress, 45));
    }

    return applyFeishuFromServer(stages, run);
  }

  // pending / 其它
  const pend: AgentStageModel[] = AGENTS.map((a, i) => ({
    ...a,
    status: (i === 0
      ? "进行中"
      : a.id === "feishu" && !outputFeishu
        ? "未启用"
        : "等待中") as AgentUiStatus,
    progress: i === 0 ? 20 : 0,
  }));
  return applyFeishuFromServer(pend, run);
}

export function formatProcessedPair(
  run: RunDetailResponse | null,
  summaryTotal: number
): { x: number; y: number } {
  if (!run) return { x: 0, y: 0 };
  const y = run.params?.max_leads ?? 10;
  const x = summaryTotal > 0 ? summaryTotal : run.lead_count ?? run.leads?.length ?? 0;
  return { x, y };
}
