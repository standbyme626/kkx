"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

type Props = {
  maxLeads: number;
  onMaxLeadsChange: (n: number) => void;
  useLlmQueries: boolean;
  onUseLlmQueries: (v: boolean) => void;
  useLlmActions: boolean;
  onUseLlmActions: (v: boolean) => void;
  outputFeishu: boolean;
  onOutputFeishu: (v: boolean) => void;
  onStart: () => void;
  onRefreshRuns: () => void;
  starting: boolean;
};

export function RunControls({
  maxLeads,
  onMaxLeadsChange,
  useLlmQueries,
  onUseLlmQueries,
  useLlmActions,
  onUseLlmActions,
  outputFeishu,
  onOutputFeishu,
  onStart,
  onRefreshRuns,
  starting,
}: Props) {
  return (
    <section className="rounded-2xl border border-border/70 bg-card/70 p-4 shadow-sm backdrop-blur-sm sm:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-tight">操作条</h2>
        <p className="text-xs text-muted-foreground">启动任务、切换运行与 LLM 选项</p>
      </div>
      <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end">
        <div className="grid gap-2">
          <Label htmlFor="max-leads" className="text-xs">
            max_leads
          </Label>
          <Input
            id="max-leads"
            type="number"
            min={1}
            max={500}
            className="h-9 w-32 rounded-lg"
            value={maxLeads}
            onChange={(e) => onMaxLeadsChange(Number(e.target.value) || 1)}
          />
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-background/50 px-3 py-2">
          <Switch
            id="use-llm-q"
            checked={useLlmQueries}
            onCheckedChange={onUseLlmQueries}
          />
          <Label htmlFor="use-llm-q" className="cursor-pointer text-sm">
            use_llm_queries
          </Label>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-background/50 px-3 py-2">
          <Switch
            id="use-llm-a"
            checked={useLlmActions}
            onCheckedChange={onUseLlmActions}
          />
          <Label htmlFor="use-llm-a" className="cursor-pointer text-sm">
            use_llm_actions
          </Label>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-emerald-600/25 bg-emerald-500/5 px-3 py-2">
          <Switch
            id="output-feishu"
            checked={outputFeishu}
            onCheckedChange={onOutputFeishu}
          />
          <Label htmlFor="output-feishu" className="cursor-pointer text-sm">
            同步飞书（每次新建客户表）
          </Label>
        </div>
        <div className="flex flex-wrap gap-2 lg:ml-auto">
          <Button onClick={onStart} disabled={starting} className="rounded-lg">
            {starting ? "启动中…" : "开始运行 Demo"}
          </Button>
          <Button variant="outline" onClick={onRefreshRuns} type="button" className="rounded-lg">
            刷新运行列表
          </Button>
        </div>
      </div>
    </section>
  );
}
