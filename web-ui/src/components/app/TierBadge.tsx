import React from "react";
import { Tier, tierLabel } from "@/api/types";
import { TierGlyph } from "./TierGlyph";
import { cn } from "@/lib/utils";

interface TierBadgeProps {
  tier: Tier | string;
  showLabel?: boolean;
  className?: string;
}

export const TierBadge: React.FC<TierBadgeProps> = ({
  tier,
  showLabel = true,
  className,
}) => {
  const isNotObservable = tier === "NOT_OBSERVABLE";
  const isObserved = tier === "OBSERVED";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-mono text-xs select-none",
        isObserved && "text-signal font-medium",
        isNotObservable && "text-text-tertiary",
        !isObserved && !isNotObservable && "text-text-secondary",
        className
      )}
    >
      <TierGlyph tier={tier} size={12} />
      {showLabel && <span>{tierLabel(tier)}</span>}
    </span>
  );
};
