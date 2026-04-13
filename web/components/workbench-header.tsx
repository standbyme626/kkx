"use client";

import { cn } from "@/lib/utils";

type Props = {
  backendOnline: boolean | null;
};

export function WorkbenchHeader({ backendOnline }: Props) {
  return (
    <header className="relative overflow-hidden border-b border-white/10 bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-white">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, rgba(56,189,248,0.25), transparent 45%), radial-gradient(circle at 80% 0%, rgba(129,140,248,0.35), transparent 40%)",
        }}
      />
      <div className="relative mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 sm:flex-row sm:items-end sm:justify-between sm:px-6">
        <div className="space-y-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-sky-200/80">
            SWSAGE · Agentic Workbench
          </p>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            SWSAGE 外贸获客智能体 Demo
          </h1>
          <p className="max-w-xl text-sm text-slate-200/85">
            客户分级、分级原因、动作建议、飞书同步工作台
          </p>
        </div>
        <div
          className={cn(
            "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm backdrop-blur-md",
            backendOnline === true &&
              "border-emerald-400/40 bg-emerald-500/15 text-emerald-50",
            backendOnline === false &&
              "border-red-400/45 bg-red-500/15 text-red-50",
            backendOnline === null && "border-white/20 bg-white/10 text-slate-100"
          )}
        >
          <span
            className={cn(
              "size-2 rounded-full",
              backendOnline === true && "bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.9)]",
              backendOnline === false && "bg-red-400",
              backendOnline === null && "bg-slate-300"
            )}
          />
          Backend {backendOnline === true ? "在线" : backendOnline === false ? "不可用" : "检测中…"}
        </div>
      </div>
    </header>
  );
}
