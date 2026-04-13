"use client";

import type { AgentStageModel } from "@/lib/agent-stages";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusStyles: Record<string, string> = {
  等待中: "border-border bg-muted/50 text-muted-foreground",
  进行中: "border-sky-500/40 bg-sky-500/10 text-sky-800 dark:text-sky-100",
  已完成: "border-emerald-500/40 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100",
  失败: "border-red-500/45 bg-red-500/10 text-red-900 dark:text-red-100",
  未启用: "border-dashed border-muted-foreground/40 bg-background text-muted-foreground",
};

export function AgentStageCard({ agent }: { agent: AgentStageModel }) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl border border-border/60 bg-card/60 p-4 shadow-sm backdrop-blur-sm",
        agent.status === "进行中" && "ring-1 ring-sky-500/25"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold leading-snug">{agent.name}</p>
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
            {agent.blurb}
          </p>
        </div>
        <Badge
          variant="outline"
          className={cn(
            "shrink-0 text-[10px] font-medium uppercase tracking-wide",
            statusStyles[agent.status] ?? statusStyles["等待中"]
          )}
        >
          {agent.status}
        </Badge>
      </div>
      <div className="mt-auto space-y-1">
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>进度</span>
          <span className="tabular-nums">{agent.progress}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn(
              "h-full rounded-full transition-[width] duration-500",
              agent.status === "失败" && "bg-red-500",
              agent.status === "已完成" && "bg-emerald-500",
              agent.status === "进行中" && "bg-sky-500",
              agent.status === "等待中" && "bg-muted-foreground/30",
              agent.status === "未启用" && "bg-transparent"
            )}
            style={{
              width:
                agent.status === "未启用" ? "0%" : `${Math.max(4, agent.progress)}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
