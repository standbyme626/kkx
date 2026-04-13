"use client";

import type { RunListItem } from "@/lib/types";
import { Label } from "@/components/ui/label";

type Props = {
  runs: RunListItem[];
  currentRunId: string | null;
  onChange: (runId: string) => void;
};

function displayRunName(r: RunListItem): string {
  // 优先 run_name（业务名），fallback 到 run_id
  return r.run_name || r.feishu_table_name || r.run_id;
}

export function CurrentRunSelector({ runs, currentRunId, onChange }: Props) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <Label htmlFor="run-select" className="text-muted-foreground">
        当前运行
      </Label>
      <select
        id="run-select"
        className="h-9 w-full max-w-md rounded-lg border border-border/80 bg-background/80 px-3 text-sm shadow-sm backdrop-blur-sm sm:w-auto"
        value={currentRunId ?? ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">— 选择一次运行 —</option>
        {runs.map((r) => {
          const name = displayRunName(r);
          const isBusinessName = !!(r.run_name || r.feishu_table_name);
          return (
            <option key={r.run_id} value={r.run_id}>
              {name + " · " + r.status + (isBusinessName ? "" : ` (技术名)`)}
            </option>
          );
        })}
      </select>
    </div>
  );
}
