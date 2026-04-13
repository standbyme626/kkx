/** 与飞书 / 本地 JSON 对齐的 15 个业务字段（UI 层统一使用中文键） */
export type UILeadRecord = {
  公司名称: string;
  官网: string;
  国家: string;
  客户类型: string;
  客户等级: "A" | "B" | "C" | "D" | string;
  客户符合度分: number;
  分级原因: string;
  关键判断信号: string;
  推荐联系人: string;
  联系方式线索: string;
  邮件草稿: string;
  搜索处理状态: SearchProcessStatus;
  下一步动作: string;
  备注: string;
  创建时间: string;
};

export type SearchProcessStatus =
  | "已补全可跟进"
  | "高符合度，需第三次搜索"
  | "高符合度，需人工搜索"
  | "信息不足，继续背调"
  | "暂不优先"
  | string;

export type RunStatus = "pending" | "running" | "completed" | "failed" | string;

export type FeishuSyncStatus =
  | "未创建"
  | "已创建"
  | "写入中"
  | "已完成"
  | "失败"
  | string;

export type RunSummary = {
  total: number;
  grade_counts: Record<string, number>;
  a_count?: number;
  b_count?: number;
  c_count?: number;
  d_count?: number;
};

/** 后端 GET /api/runs/{id} 响应（leads 为原始 pipeline 对象） */
export type RunDetailResponse = {
  run_id: string;
  run_name?: string;
  status: RunStatus;
  created_at: string;
  params?: {
    max_leads?: number;
    use_llm_queries?: boolean;
    use_llm_actions?: boolean;
    output_feishu?: boolean;
    profile?: string;
    rules?: string;
  };
  output_file?: string | null;
  summary?: RunSummary | null;
  lead_count?: number;
  error?: string | null;
  stdout?: string | null;
  stderr?: string | null;
  leads: unknown[];
  feishu_table_name?: string | null;
  feishu_table_id?: string | null;
  feishu_table_url?: string | null;
  feishu_sync_status?: FeishuSyncStatus | null;
  feishu_sync_error?: string | null;
  failed_stage?: string | null;
  failed_agent?: string | null;
};

export type RunListItem = {
  run_id: string;
  run_name?: string;
  status: RunStatus;
  created_at: string;
  output_file?: string | null;
  summary?: RunSummary | null;
  feishu_table_name?: string | null;
  feishu_sync_status?: FeishuSyncStatus | null;
  feishu_table_url?: string | null;
  error?: string | null;
  failed_stage?: string | null;
};

export type StartRunResponse = {
  run_id: string;
  run_name: string;
  feishu_table_name: string;
  feishu_sync_status: string;
  status: string;
  feishu_table_id?: string | null;
  feishu_table_url?: string | null;
  feishu_sync_error?: string | null;
};

export type HealthResponse = {
  ok?: boolean;
};

export type TestCreateTableResponse = {
  ok: boolean;
  table_name: string;
  table_id: string | null;
  table_url: string | null;
  raw_error: string | null;
  auth_mode: string;
  app_token_tail: string | null;
  tenant_token_obtained: boolean;
  steps: {
    token_ready: boolean;
    create_request_sent: boolean;
    create_response_received: boolean;
  };
};
