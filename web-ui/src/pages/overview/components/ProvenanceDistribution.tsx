import React, { useState, useEffect } from "react";
import { ClaimItem, Tier, tierLabel } from "@/api/types";
import { SectionHeader } from "@/components/app/SectionHeader";
import { TierGlyph } from "@/components/app/TierGlyph";
import { cn } from "@/lib/utils";

interface ProvenanceDistributionProps {
  claims: ClaimItem[];
  runStatus?: string;
  captureName?: string;
}

interface TierRowData {
  tier: Tier;
  label: string;
  count: number;
  pct: number;
  barColor: string;
}

const ORDERED_TIERS: Tier[] = [
  "OBSERVED",
  "INFERRED_SIDE_CHANNEL",
  "INFERRED_IMPLEMENTATION_DEFAULT",
  "ML_PREDICTION",
  "NOT_OBSERVABLE",
];

const TIER_COLORS: Record<Tier, string> = {
  OBSERVED: "bg-signal shadow-[0_0_8px_rgba(0,255,127,0.4)]",
  INFERRED_SIDE_CHANNEL: "bg-signal-dim",
  INFERRED_IMPLEMENTATION_DEFAULT: "bg-[#00994d]",
  ML_PREDICTION: "bg-signal/35",
  NOT_OBSERVABLE: "bg-text-tertiary",
};

export const ProvenanceDistribution: React.FC<ProvenanceDistributionProps> = ({
  claims,
  captureName,
}) => {
  const isReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const storageKey = captureName ? `umbra_illuminated_${captureName}` : null;
  const alreadyIlluminated =
    typeof window !== "undefined" && storageKey
      ? window.sessionStorage.getItem(storageKey) === "true"
      : false;

  const [illuminated, setIlluminated] = useState<boolean>(() => {
    if (isReducedMotion || alreadyIlluminated) return true;
    return false;
  });

  useEffect(() => {
    if (isReducedMotion || alreadyIlluminated) {
      setIlluminated(true);
      return;
    }

    // Play illumination once on run/load
    const timer = setTimeout(() => {
      setIlluminated(true);
      if (storageKey && typeof window !== "undefined") {
        window.sessionStorage.setItem(storageKey, "true");
      }
    }, 50);

    return () => clearTimeout(timer);
  }, [isReducedMotion, alreadyIlluminated, storageKey]);

  const total = claims.length;

  const tierRows: TierRowData[] = ORDERED_TIERS.map((tier) => {
    const count = claims.filter((c) => c.tier === tier).length;
    const pct = total > 0 ? (count / total) * 100 : 0;
    return {
      tier,
      label: tierLabel(tier),
      count,
      pct,
      barColor: TIER_COLORS[tier],
    };
  });

  return (
    <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col gap-3 font-mono text-xs select-none">
      <div className="flex items-center justify-between">
        <SectionHeader
          title="provenance distribution"
          count={total}
          className="my-0 mb-1"
        />
      </div>

      <p className="text-[11px] text-text-tertiary font-sans -mt-1 mb-1">
        Evidence certainty hierarchy: directly observed facts emit the highest luminance.
      </p>

      <div className="space-y-3">
        {tierRows.map((row) => {
          const isObserved = row.tier === "OBSERVED";
          const isNotObservable = row.tier === "NOT_OBSERVABLE";

          return (
            <div key={row.tier} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <TierGlyph tier={row.tier} size={13} />
                  <span
                    className={cn(
                      "font-medium",
                      isNotObservable
                        ? "text-text-tertiary"
                        : isObserved
                        ? "text-signal"
                        : "text-text-primary"
                    )}
                  >
                    {row.label}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "tabular-nums font-medium",
                      isNotObservable
                        ? "text-text-tertiary"
                        : isObserved
                        ? "text-signal"
                        : "text-text-primary"
                    )}
                  >
                    {row.count}
                  </span>
                  <span className="text-text-tertiary text-[11px] tabular-nums w-10 text-right">
                    {row.pct.toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Proportional Bar Track */}
              <div className="h-1.5 w-full rounded-data bg-surface-base border border-border-hairline overflow-hidden">
                <div
                  style={{
                    width: illuminated ? `${row.pct}%` : "0%",
                  }}
                  className={cn(
                    "h-full transition-all duration-500 ease-out motion-reduce:!transition-none",
                    row.barColor
                  )}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
