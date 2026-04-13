"use client";

import type { RunDetailResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const statusStyle: Record<string, string> = {
  未创建: "border-muted-foreground/40 bg-muted text-muted-foreground",
  未启用: "border-muted-foreground/40 bg-muted text-muted-foreground",
  已创建: "border-sky-500/40 bg-sky-500/10 text-sky-900 dark:text-sky-100",
  写入中: "border-amber-500/40 bg-amber-500/10 text-amber-950 dark:text-amber-100",
  已完成: "border-emerald-500/40 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100",
  失败: "border-red-500/45 bg-red-500/10 text-red-900 dark:text-red-100",
};

type Props = {
  run: RunDetailResponse | null;
};

export function FeishuSyncStrip({ run }: Props) {
  if (!run) {
    return (
      <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
        选择或启动一次运行后，将显示对应的飞书客户表与同步状态。
      </div>
    );
  }

  const name = run.feishu_table_name || run.run_name || "—";
  const st = run.feishu_sync_status || "未创建";
  const url = run.feishu_table_url?.trim();
  const err = run.feishu_sync_error?.trim();
  const tableId = run.feishu_table_id || "";
  const tableIdDisplay = tableId
    ? tableId.slice(0, 6) + "..." + tableId.slice(-4)
    : "—";

  return (
    <div className="rounded-2xl border border-border/70 bg-card/80 px-4 py-3 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            飞书客户表（本次运行）
          </p>
          <p className="text-sm font-semibold">{name}</p>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium",
                statusStyle[st] ?? "border-border bg-muted text-muted-foreground"
              )}
            >
              {st}
            </Badge>
            <span className="text-[11px] text-muted-foreground">
              table_id: {tableIdDisplay}
            </span>
          </div>
          {err ? (
            <p className="text-xs text-destructive mt-1">{err}</p>
          ) : null}
        </div>
        <div className="shrink-0">
          {url ? (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(buttonVariants({ variant: "outline", size: "sm" }), "rounded-lg")}
            >
              打开飞书表
            </a>
          ) : (
            <span
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "rounded-lg pointer-events-none opacity-50"
              )}
            >
              暂无链接
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
