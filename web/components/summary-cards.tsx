"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { RunSummary } from "@/lib/types";

type Props = {
  summary: RunSummary | null | undefined;
  /** 「高符合度，需人工搜索」条数，来自前端对 leads 的统计 */
  manualSearchHintCount?: number;
};

export function SummaryCards({
  summary,
  manualSearchHintCount = 0,
}: Props) {
  const total = summary?.total ?? 0;
  const a = summary?.a_count ?? summary?.grade_counts?.A ?? 0;
  const b = summary?.b_count ?? summary?.grade_counts?.B ?? 0;
  const c = summary?.c_count ?? summary?.grade_counts?.C ?? 0;
  const d = summary?.d_count ?? summary?.grade_counts?.D ?? 0;

  const items = [
    { label: "总客户", value: total, className: "" },
    { label: "A", value: a, className: "text-emerald-700 dark:text-emerald-300" },
    { label: "B", value: b, className: "text-sky-700 dark:text-sky-300" },
    { label: "C", value: c, className: "text-amber-700 dark:text-amber-200" },
    { label: "D", value: d, className: "text-muted-foreground" },
    {
      label: "高符合度 · 待人工搜索",
      value: manualSearchHintCount,
      className: "text-red-700 dark:text-red-300",
    },
  ];

  return (
    <section className="rounded-2xl border border-border/60 bg-muted/20 p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">结果摘要</h3>
        <span className="text-xs text-muted-foreground">精简视图</span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {items.map((it) => (
          <Card
            key={it.label}
            className="border-border/70 bg-background/80 shadow-none"
          >
            <CardContent className="p-4">
              <p className="text-[11px] font-medium text-muted-foreground leading-tight">
                {it.label}
              </p>
              <p
                className={`mt-2 text-2xl font-semibold tabular-nums ${it.className}`}
              >
                {it.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
