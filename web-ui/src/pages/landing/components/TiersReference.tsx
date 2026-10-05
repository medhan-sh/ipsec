import React from "react";
import { TierGlyph } from "@/components/app/TierGlyph";
import { Tier } from "@/api/types";

interface TierRow {
  tier: Tier;
  name: string;
  description: string;
}

const TIERS_DATA: TierRow[] = [
  {
    tier: "OBSERVED",
    name: "OBSERVED",
    description: "Read directly from the handshake. Certain.",
  },
  {
    tier: "INFERRED_SIDE_CHANNEL",
    name: "INFERRED_SIDE_CHANNEL",
    description: "Deduced from sizes and timing of what is visible.",
  },
  {
    tier: "INFERRED_IMPLEMENTATION_DEFAULT",
    name: "INFERRED_IMPLEMENTATION_DEFAULT",
    description: "Assumed from how this implementation usually behaves.",
  },
  {
    tier: "ML_PREDICTION",
    name: "ML_PREDICTION",
    description: "A statistical prediction.",
  },
  {
    tier: "NOT_OBSERVABLE",
    name: "NOT_OBSERVABLE",
    description: "The capture cannot tell us. We say so rather than guess.",
  },
];

export const TiersReference: React.FC = () => {
  return (
    <div
      role="region"
      aria-label="Provenance tiers reference"
      className="p-4 rounded-data border border-border-hairline bg-surface-panel/40 flex flex-col gap-2.5 text-xs font-mono select-none"
    >
      <span className="text-[10px] text-text-tertiary uppercase tracking-wider font-semibold">
        how to read the results
      </span>

      <div className="space-y-2 mt-1">
        {TIERS_DATA.map((row) => {
          const isNotObservable = row.tier === "NOT_OBSERVABLE";
          return (
            <div key={row.tier} className="flex items-start gap-2.5">
              <TierGlyph tier={row.tier} size={14} className="mt-0.5 shrink-0" />
              <div>
                <span
                  className={
                    isNotObservable
                      ? "text-text-tertiary font-medium"
                      : "text-text-primary font-medium"
                  }
                >
                  {row.name}:{" "}
                </span>
                <span
                  className={
                    isNotObservable
                      ? "text-text-tertiary font-sans text-xs"
                      : "text-text-secondary font-sans text-xs"
                  }
                >
                  {row.description}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
