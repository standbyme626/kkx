import type { RunDetailResponse, RunStatus } from "@/lib/types";

export type InferredRunUi = {
  taskLabel: string;
  stageName: string;
  stageDescription: string;
  progressPercent: number;
  footerMessage: string;
};

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n));
}

/**
 * 后端若无细粒度阶段事件，前端轻量推断展示文案与进度条。
 */
export function inferRunUiState(run: RunDetailResponse | null): InferredRunUi {
  if (!run) {
    return {
      taskLabel: "等待任务",
      stageName: "未选择运行",
      stageDescription: "请从上方下拉框选择一次历史运行，或点击「开始运行 Demo」启动新任务。",
      progressPercent: 0,
      footerMessage: "尚无当前运行上下文。",
    };
  }

  const status = (run?.status ?? "pending") as RunStatus;
  const leadCount = run?.lead_count ?? run?.leads?.length ?? 0;
  const maxLeads = run?.params?.max_leads ?? 10;

  if (status === "failed") {
    const stageHint = run?.failed_stage ? `失败阶段：${run.failed_stage}` : "";
    const agentHint = run?.failed_agent ? ` (模块：${run.failed_agent})` : "";
    return {
      taskLabel: "处理失败",
      stageName: "任务结束",
      stageDescription:
        run?.error ||
        "本次任务执行失败，请检查后端服务、依赖配置或查看 stderr 日志。",
      progressPercent: 100,
      footerMessage: `failed：本次任务执行失败。${stageHint}${agentHint} 请检查相关配置或日志。`,
    };
  }

  if (status === "completed") {
    return {
      taskLabel: "处理完成",
      stageName: "结果已生成",
      stageDescription: "客户分级、联系人补全与输出已完成，可在下方结果表中查看。",
      progressPercent: 100,
      footerMessage:
        "completed：本次任务处理完成，已生成客户结果清单（含本地 JSON / 可选飞书）。",
    };
  }

  if (status === "running") {
    if (leadCount === 0) {
      return {
        taskLabel: "系统正在运行",
        stageName: "第一次搜索与归一化",
        stageDescription:
          "正在构建搜索词、抓取候选客户并完成归一化；完成后进入分级与联系人补全。",
        progressPercent: 25,
        footerMessage: "running：流水线执行中，请稍候…",
      };
    }
    return {
      taskLabel: "系统正在运行",
      stageName: "分级与联系人补全",
      stageDescription:
        "正在对客户进行价值分级、二次搜索补全决策人与联系方式，并生成动作建议。",
      progressPercent: 60,
      footerMessage: "running：已产生中间结果，仍在补全与收尾…",
    };
  }

  // pending / 刚启动
  return {
    taskLabel: "已启动任务",
    stageName: "任务排队 / 启动中",
    stageDescription: `目标处理规模约 ${maxLeads} 条线索，任务已提交后台执行。`,
    progressPercent: 5,
    footerMessage: "任务已创建，等待后端开始执行…",
  };
}

export function formatProcessedLine(
  run: RunDetailResponse | null,
  summary: { total: number } | null | undefined
): string {
  if (!run) return "—";
  const total = summary?.total ?? run?.lead_count ?? run?.leads?.length ?? 0;
  const maxLeads = run?.params?.max_leads;
  if (run?.status === "running" && maxLeads) {
    return `已生成客户（当前可见） ${total} 条 · 目标上限约 ${maxLeads} 条`;
  }
  return `已生成客户 ${total} 条`;
}
