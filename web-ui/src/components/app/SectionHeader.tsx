import React from "react";
import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  title: string;
  count?: number;
  action?: React.ReactNode;
  className?: string;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  count,
  action,
  className,
}) => {
  return (
    <div className={cn("flex items-center gap-3 my-4 w-full select-none", className)}>
      <span className="font-mono text-xs font-semibold lowercase text-text-secondary whitespace-nowrap">
        {title}
        {count !== undefined && (
          <span className="text-text-tertiary ml-1.5 font-normal tabular-nums">
            ({count})
          </span>
        )}
      </span>
      <div className="flex-1 h-[1px] bg-border-hairline" />
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
};
