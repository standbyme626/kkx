"use client";

import type { RunDetailResponse } from "@/lib/types";
import { inferRunUiState, formatProcessedLine } from "@/lib/run-status";
import {
  buildAgentStages,
  formatProcessedPair,
} from "@/lib/agent-stages";
import { AgentStageGrid } from "@/components/agent-stage-grid";
import { FeishuSyncStrip } from "@/components/feishu-sync-strip";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Props = {
  run: RunDetailResponse | null;
};

function heroTitle(run: RunDetailResponse | null): string {
  if (!run) return "等待启动智能体流水线";
  switch (run.status) {
    case "running":
      return "系统正在处理本次客户筛选任务";
    case "completed":
      return "本次客户筛选任务已完成";
    case "failed":
      return "本次任务未成功完成";
    default:
      return "已提交客户筛选任务";
  }
}

function statusPill(status: string | undefined) {
  const s = status ?? "—";
  const map: Record<string, string> = {
    running: "border-sky-500/40 bg-sky-500/10 text-sky-900 dark:text-sky-100",
    completed: "border-emerald-500/40 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100",
    failed: "border-red-500/45 bg-red-500/10 text-red-900 dark:text-red-100",
  };
  return (
    <Badge
      variant="outline"
      className={cn(
        "rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide",
        map[s] ?? "border-border bg-muted text-muted-foreground"
      )}
    >
      {s}
    </Badge>
  );
}

export function RunStatusPanel({ run }: Props) {
  const ui = inferRunUiState(run);
  const summary = run?.summary;
  const processedLine = formatProcessedLine(run, summary);
  const { x, y } = formatProcessedPair(run, summary?.total ?? 0);
  const agents = buildAgentStages(run, ui);

  return (
    <section className="space-y-6 rounded-3xl border border-sky-500/15 bg-gradient-to-b from-sky-500/5 via-background to-background p-5 shadow-lg shadow-sky-500/5 sm:p-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3 lg:max-w-[70%]">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-sky-600/90 dark:text-sky-300/90">
            系统工作主舞台
          </p>
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            {heroTitle(run)}
          </h2>
          <p className="text-sm text-muted-foreground">{ui.stageDescription}</p>
          {run?.run_name ? (
            <p className="text-xs text-muted-foreground">
              业务运行名：<span className="font-medium text-foreground">{run.run_name}</span>
            </p>
          ) : null}
        </div>
        <div className="flex flex-col items-start gap-2 lg:items-end">
          <span className="text-xs text-muted-foreground">当前状态</span>
          {statusPill(run?.status)}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className="text-sm font-medium">{ui.stageName}</p>
            <p className="text-xs text-muted-foreground">总进度 · {ui.progressPercent}%</p>
          </div>
        </div>
        <div className="h-4 w-full overflow-hidden rounded-full bg-muted shadow-inner">
          <div
            className="h-full rounded-full bg-gradient-to-r from-sky-500 via-indigo-500 to-violet-500 transition-[width] duration-700"
            style={{ width: `${ui.progressPercent}%` }}
          />
        </div>
      </div>

      <FeishuSyncStrip run={run} />

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-border/60 bg-card/60 px-4 py-3">
          <p className="text-xs text-muted-foreground">已处理 / 目标规模</p>
          <p className="mt-1 text-lg font-semibold tabular-nums">
            {y > 0 ? `${x} / ${y}` : "—"}
          </p>
        </div>
        <div className="rounded-2xl border border-border/60 bg-card/60 px-4 py-3 sm:col-span-2">
          <p className="text-xs text-muted-foreground">已生成客户</p>
          <p className="mt-1 text-lg font-semibold tabular-nums">{processedLine}</p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">多 Agent 协同</h3>
          <span className="text-xs text-muted-foreground">推断展示 · 非独立后端事件流</span>
        </div>
        <AgentStageGrid agents={agents} />
      </div>

      {run?.status === "failed" ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/10 px-4 py-3 space-y-2">
          <p className="text-sm font-medium text-destructive">
            任务未成功完成
          </p>
          {run.failed_stage ? (
            <p className="text-xs text-destructive/90">
              失败阶段：<span className="font-medium">{run.failed_stage}</span>
              {run.failed_agent ? ` (${run.failed_agent})` : ""}
            </p>
          ) : null}
          {run.error ? (
            <p className="text-xs text-destructive/80">
              错误信息：{run.error}
            </p>
          ) : null}
          {run.feishu_sync_error && run.failed_stage === "飞书建表" ? (
            <p className="text-xs text-destructive/80">
              飞书错误：{run.feishu_sync_error}
            </p>
          ) : null}
        </div>
      ) : null}

      <p className="rounded-2xl border border-dashed border-border/80 bg-muted/30 px-4 py-3 text-xs text-muted-foreground">
        {ui.footerMessage}
      </p>
    </section>
  );
}
