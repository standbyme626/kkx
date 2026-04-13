"use client";

import type { AgentStageModel } from "@/lib/agent-stages";
import { AgentStageCard } from "@/components/agent-stage-card";

export function AgentStageGrid({ agents }: { agents: AgentStageModel[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {agents.map((a) => (
        <AgentStageCard key={a.id} agent={a} />
      ))}
    </div>
  );
}
