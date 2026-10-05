import React from "react";
import { tierLabel } from "@/api/types";
import { TierGlyph } from "@/components/app/TierGlyph";
import { ToggleGroup, ToggleGroupItem } from "@/components/vendor/toggle-group";
import { ALL_TIERS } from "./claims-utils";
import { cn } from "@/lib/utils";

interface TierFilterToggleProps {
  counts: Record<string, number>;
  totalCount: number;
  selectedTier: string; // "ALL" or a specific Tier
  onSelectTier: (tier: string) => void;
  className?: string;
}

export const TierFilterToggle: React.FC<TierFilterToggleProps> = ({
  counts,
  totalCount,
  selectedTier,
  onSelectTier,
  className,
}) => {
  const handleValueChange = (val: string) => {
    // If user clicks currently active or empty, reset to ALL
    if (!val || val === selectedTier) {
      onSelectTier("ALL");
    } else {
      onSelectTier(val);
    }
  };

  return (
    <div className={cn("flex items-center gap-1.5 font-mono text-xs select-none", className)}>
      <ToggleGroup
        type="single"
        value={selectedTier}
        onValueChange={handleValueChange}
        className="bg-surface-panel p-0.5 border border-border-hairline rounded-data flex-wrap"
      >
        <ToggleGroupItem
          value="ALL"
          className={cn(
            "px-2 py-1 text-xs transition-colors",
            selectedTier === "ALL" && "bg-surface-raised text-signal font-medium border border-signal/40"
          )}
          title="Show claims across all tiers"
        >
          <span>all</span>
          <span className="ml-1 text-[11px] text-text-tertiary tabular-nums">
            ({totalCount})
          </span>
        </ToggleGroupItem>

        {ALL_TIERS.map((tier) => {
          const count = counts[tier] ?? 0;
          const isSelected = selectedTier === tier;
          const isObserved = tier === "OBSERVED";
          const isNotObservable = tier === "NOT_OBSERVABLE";

          return (
            <ToggleGroupItem
              key={tier}
              value={tier}
              className={cn(
                "px-2 py-1 text-xs flex items-center gap-1.5 transition-colors",
                isSelected &&
                  (isObserved
                    ? "bg-surface-raised text-signal font-medium border border-signal/50"
                    : isNotObservable
                    ? "bg-surface-raised text-text-primary border border-border-strong"
                    : "bg-surface-raised text-text-primary border border-border-strong")
              )}
              title={`Filter by ${tierLabel(tier)} tier (${count} claims)`}
            >
              <TierGlyph tier={tier} size={11} />
              <span className={cn(isSelected ? "text-text-primary" : "text-text-secondary")}>
                {tierLabel(tier)}
              </span>
              <span className="text-[11px] text-text-tertiary tabular-nums font-normal">
                ({count})
              </span>
            </ToggleGroupItem>
          );
        })}
      </ToggleGroup>
    </div>
  );
};
