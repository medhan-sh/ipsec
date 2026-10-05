import React from "react";
import { Tier } from "@/api/types";
import { cn } from "@/lib/utils";

interface ConfidenceMeterProps {
  tier: Tier | string;
  confidence: number | null;
  className?: string;
}

export const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({
  tier,
  confidence,
  className,
}) => {
  if (tier === "OBSERVED") {
    return (
      <span className={cn("font-mono text-xs text-signal font-medium select-none", className)}>
        certain
      </span>
    );
  }

  if (tier === "NOT_OBSERVABLE" || confidence === null) {
    return (
      <span className={cn("font-mono text-xs text-text-tertiary select-none", className)}>
        — not observable
      </span>
    );
  }

  const pct = Math.round(confidence * 100);

  return (
    <div className={cn("inline-flex items-center gap-2 font-mono text-xs text-text-secondary", className)}>
      <div className="h-1.5 w-12 rounded-data bg-surface-panel overflow-hidden border border-border-hairline">
        <div
          className="h-full bg-signal-dim transition-all duration-150"
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>
      <span className="text-[11px] tabular-nums">{pct}%</span>
    </div>
  );
};
