"use client";

import type { UILeadRecord } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Props = {
  lead: UILeadRecord | null;
};

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="whitespace-pre-wrap text-sm leading-relaxed">{value || "—"}</p>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4 rounded-2xl border border-border/60 bg-muted/15 p-4">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h4>
      <div className="grid gap-4 md:grid-cols-2">{children}</div>
    </div>
  );
}

/** 完整 15 字段，按模块分组展示 */
export function LeadDetailPanel({ lead }: Props) {
  return (
    <Card className="border-border/70">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">客户详情</CardTitle>
        <p className="text-xs text-muted-foreground">
          与飞书 / 本地 JSON 对齐的 15 个业务字段。
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {!lead ? (
          <p className="text-sm text-muted-foreground">
            展开结果表并点击一行以查看详情。
          </p>
        ) : (
          <>
            <Section title="基础信息">
              <Field label="公司名称" value={lead.公司名称} />
              <Field label="官网" value={lead.官网} />
              <Field label="国家" value={lead.国家} />
              <Field label="客户类型" value={lead.客户类型} />
              <Field label="创建时间" value={lead.创建时间} />
            </Section>
            <Section title="判断结果">
              <Field label="客户等级" value={String(lead.客户等级)} />
              <Field label="客户符合度分" value={String(lead.客户符合度分)} />
              <Field label="分级原因" value={lead.分级原因} />
              <Field label="关键判断信号" value={lead.关键判断信号} />
              <Field label="搜索处理状态" value={lead.搜索处理状态} />
            </Section>
            <Section title="联系与动作">
              <Field label="推荐联系人" value={lead.推荐联系人} />
              <Field label="联系方式线索" value={lead.联系方式线索} />
              <Field label="下一步动作" value={lead.下一步动作} />
              <Field label="邮件草稿" value={lead.邮件草稿} />
            </Section>
            <Section title="补充内容">
              <Field label="备注" value={lead.备注} />
            </Section>
          </>
        )}
      </CardContent>
    </Card>
  );
}
