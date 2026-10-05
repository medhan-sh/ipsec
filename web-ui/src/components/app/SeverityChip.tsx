import React from "react";
import { Severity } from "@/api/types";
import { cn } from "@/lib/utils";

interface SeverityChipProps {
  severity: Severity | string;
  className?: string;
}

export const SeverityChip: React.FC<SeverityChipProps> = ({
  severity,
  className,
}) => {
  const sev = severity.toUpperCase();

  const styles: Record<string, string> = {
    CRITICAL: "border-severity-critical/40 text-severity-critical bg-severity-critical/10",
    HIGH: "border-severity-high/40 text-severity-high bg-severity-high/10",
    MEDIUM: "border-severity-medium/40 text-severity-medium bg-severity-medium/10",
    LOW: "border-severity-low/40 text-severity-low bg-severity-low/10",
    INFO: "border-severity-info/40 text-severity-info bg-severity-info/10",
  };

  const style = styles[sev] ?? "border-border-hairline text-text-secondary bg-surface-raised";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-data border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider select-none",
        style,
        className
      )}
    >
      {sev}
    </span>
  );
};
