"use client";

import type { TestCreateTableResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  result: TestCreateTableResponse | null;
  loading: boolean;
  onTest: () => void;
};

const statusStyle: Record<string, string> = {
  true: "border-emerald-500/40 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100",
  false: "border-red-500/45 bg-red-500/10 text-red-900 dark:text-red-100",
};

export function FeishuTestPanel({ result, loading, onTest }: Props) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card/80 px-4 py-3 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          飞书建表独立测试
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={onTest}
          disabled={loading}
        >
          {loading ? "测试中..." : "测试飞书建表"}
        </Button>
      </div>

      {result ? (
        <div className="space-y-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium",
                statusStyle[String(result.ok)]
              )}
            >
              {result.ok ? "建表成功" : "建表失败"}
            </Badge>
            <span className="text-muted-foreground">
              表名: {result.table_name}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div>
              <span className="text-muted-foreground">Auth 模式:</span>
              <p className="font-medium">{result.auth_mode}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Token 获取:</span>
              <p className="font-medium">
                {result.tenant_token_obtained ? "✅" : "❌"}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">app_token 末尾:</span>
              <p className="font-medium">{result.app_token_tail || "—"}</p>
            </div>
            <div>
              <span className="text-muted-foreground">table_id:</span>
              <p className="font-medium">{result.table_id || "—"}</p>
            </div>
          </div>

          {result.table_url ? (
            <div>
              <span className="text-muted-foreground">表链接:</span>
              <p className="font-mono text-[11px] break-all text-sky-600">
                {result.table_url}
              </p>
            </div>
          ) : null}

          {result.raw_error ? (
            <div>
              <span className="text-muted-foreground">错误:</span>
              <pre className="mt-1 whitespace-pre-wrap text-[11px] text-destructive font-mono">
                {result.raw_error}
              </pre>
            </div>
          ) : null}

          <details className="text-muted-foreground">
            <summary className="cursor-pointer text-[11px]">查看步骤详情</summary>
            <div className="mt-1 space-y-1 pl-2">
              <p>Token 就绪: {result.steps.token_ready ? "✅" : "❌"}</p>
              <p>创建请求已发: {result.steps.create_request_sent ? "✅" : "❌"}</p>
              <p>收到创建响应: {result.steps.create_response_received ? "✅" : "❌"}</p>
            </div>
          </details>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          点击按钮测试飞书建表链路，不跑主流程。
        </p>
      )}
    </div>
  );
}
