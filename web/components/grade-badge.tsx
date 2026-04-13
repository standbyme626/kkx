import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const gradeClass: Record<string, string> = {
  A: "border-emerald-600/40 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200",
  B: "border-blue-600/40 bg-blue-50 text-blue-800 dark:bg-blue-950/40 dark:text-blue-200",
  C: "border-amber-600/40 bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-100",
  D: "border-muted-foreground/30 bg-muted text-muted-foreground",
};

export function GradeBadge({ grade }: { grade: string }) {
  const g = String(grade || "D").toUpperCase().slice(0, 1);
  return (
    <Badge
      variant="outline"
      className={cn("font-semibold", gradeClass[g] ?? gradeClass.D)}
    >
      {g}
    </Badge>
  );
}
