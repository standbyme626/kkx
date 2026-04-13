"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  disabled?: boolean;
  children: React.ReactNode;
  className?: string;
};

export function ResultToggle({
  open,
  onOpen,
  onClose,
  disabled,
  children,
  className,
}: Props) {
  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant={open ? "secondary" : "default"}
          size="sm"
          disabled={disabled}
          onClick={onOpen}
        >
          查看结果表
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!open}
          onClick={onClose}
        >
          隐藏结果表
        </Button>
      </div>
      {open ? <div>{children}</div> : null}
    </div>
  );
}
