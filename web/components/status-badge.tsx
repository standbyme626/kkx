import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusClass: Record<string, string> = {
  已补全可跟进:
    "border-emerald-600/40 bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100",
  "高符合度，需第三次搜索":
    "border-orange-600/40 bg-orange-50 text-orange-900 dark:bg-orange-950/40 dark:text-orange-100",
  "高符合度，需人工搜索":
    "border-red-600/40 bg-red-50 text-red-900 dark:bg-red-950/40 dark:text-red-100",
  "信息不足，继续背调":
    "border-yellow-600/40 bg-yellow-50 text-yellow-950 dark:bg-yellow-950/30 dark:text-yellow-100",
  暂不优先: "border-muted-foreground/30 bg-muted text-muted-foreground",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = statusClass[status] ?? "border-border bg-secondary text-secondary-foreground";
  return (
    <Badge variant="outline" className={cn("max-w-[220px] truncate font-normal", cls)}>
      {status || "—"}
    </Badge>
  );
}
