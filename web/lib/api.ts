import type {
  HealthResponse,
  RunDetailResponse,
  RunListItem,
  StartRunResponse,
  TestCreateTableResponse,
} from "@/lib/types";

export function getApiBase(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000"
  );
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Invalid JSON (${res.status}): ${text.slice(0, 200)}`);
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${getApiBase()}/api/health`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`health ${res.status}`);
  return parseJson<HealthResponse>(res);
}

export type StartRunBody = {
  max_leads: number;
  use_llm_queries: boolean;
  use_llm_actions: boolean;
  output_feishu?: boolean;
};

export async function startRun(body: StartRunBody): Promise<StartRunResponse> {
  const res = await fetch(`${getApiBase()}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      max_leads: body.max_leads,
      use_llm_queries: body.use_llm_queries,
      use_llm_actions: body.use_llm_actions,
      output_feishu: body.output_feishu ?? true,
    }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`start run ${res.status}: ${t}`);
  }
  return parseJson<StartRunResponse>(res);
}

export async function fetchRunsList(): Promise<RunListItem[]> {
  const res = await fetch(`${getApiBase()}/api/runs`, { cache: "no-store" });
  if (!res.ok) throw new Error(`runs ${res.status}`);
  return parseJson<RunListItem[]>(res);
}

export async function fetchRunDetail(runId: string): Promise<RunDetailResponse> {
  const res = await fetch(`${getApiBase()}/api/runs/${runId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`run ${runId} ${res.status}: ${t}`);
  }
  return parseJson<RunDetailResponse>(res);
}

// ==================== 飞书建表独立测试 ====================

export async function testFeishuCreateTable(): Promise<TestCreateTableResponse> {
  const res = await fetch(`${getApiBase()}/api/feishu/test-create-table`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`test create table ${res.status}: ${t}`);
  }
  return parseJson<TestCreateTableResponse>(res);
}
