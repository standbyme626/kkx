"use client";

import type { UILeadRecord } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GradeBadge } from "@/components/grade-badge";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";

type Props = {
  rows: UILeadRecord[];
  selected: UILeadRecord | null;
  onSelect: (row: UILeadRecord) => void;
};

export function LeadsTable({ rows, selected, onSelect }: Props) {
  return (
    <Card className="border-border/70 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">结果清单</CardTitle>
        <p className="text-xs text-muted-foreground">
          主表仅 6 列；完整 15 字段请在展开后点击行查看详情。
        </p>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0 sm:p-6 sm:pt-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>公司名称</TableHead>
              <TableHead>国家</TableHead>
              <TableHead>客户等级</TableHead>
              <TableHead className="text-right">符合度分</TableHead>
              <TableHead>下一步动作</TableHead>
              <TableHead className="min-w-[140px]">搜索处理状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  暂无数据。任务完成后可在此查看客户清单。
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r, i) => {
                const key = `${r.公司名称}-${r.创建时间}-${i}`;
                const isSel =
                  selected &&
                  selected.公司名称 === r.公司名称 &&
                  selected.创建时间 === r.创建时间;
                return (
                  <TableRow
                    key={key}
                    className={cn(
                      "cursor-pointer",
                      isSel && "bg-muted/70 hover:bg-muted/70"
                    )}
                    onClick={() => onSelect(r)}
                  >
                    <TableCell className="max-w-[200px] truncate font-medium">
                      {r.公司名称 || "—"}
                    </TableCell>
                    <TableCell>{r.国家 || "—"}</TableCell>
                    <TableCell>
                      <GradeBadge grade={r.客户等级} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {r.客户符合度分}
                    </TableCell>
                    <TableCell className="max-w-[140px] whitespace-normal text-sm">
                      {r.下一步动作 || "—"}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={r.搜索处理状态} />
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
