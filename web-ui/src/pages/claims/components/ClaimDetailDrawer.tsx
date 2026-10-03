import React, { useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/vendor/sheet";
import { ClaimItem } from "@/api/types";
import { TierBadge } from "@/components/app/TierBadge";
import { TierGlyph } from "@/components/app/TierGlyph";
import { ConfidenceMeter } from "@/components/app/ConfidenceMeter";
import { Mono } from "@/components/app/Mono";
import { Separator } from "@/components/vendor/separator";
import { AlertTriangle, Layers } from "lucide-react";
import { TIER_EXPLANATIONS, getFormattedClaimJson } from "./claims-utils";
import { cn } from "@/lib/utils";

interface ClaimDetailDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  claim: ClaimItem | null;
  groupedClaims?: ClaimItem[] | null;
}

export const ClaimDetailDrawer: React.FC<ClaimDetailDrawerProps> = ({
  open,
  onOpenChange,
  claim: initialClaim,
  groupedClaims,
}) => {
  const isGrouped = Boolean(groupedClaims && groupedClaims.length > 1);
  const [activeGroupIndex, setActiveGroupIndex] = useState(0);

  // If grouped, show the selected claim from the group; otherwise show initialClaim
  const currentClaim = isGrouped && groupedClaims ? groupedClaims[activeGroupIndex] : initialClaim;

  if (!currentClaim) return null;

  const tier = currentClaim.tier;
  const isObserved = tier === "OBSERVED";
  const isNotObservable = tier === "NOT_OBSERVABLE";
  const jsonString = getFormattedClaimJson(currentClaim.value, tier);
  const explanation =
    TIER_EXPLANATIONS[tier] ||
    "Provenance tier from the analyzer classification lattice.";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto bg-surface-panel border-l border-border-hairline text-text-primary p-6">
        <SheetHeader className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <TierBadge tier={tier} />
              <Separator orientation="vertical" className="h-3" />
              {isObserved ? (
                <span className="font-mono text-xs text-signal font-medium">certain</span>
              ) : isNotObservable ? (
                <span className="font-mono text-xs text-text-tertiary">— not observable</span>
              ) : currentClaim.confidence === null ? (
                <span className="font-mono text-xs text-text-tertiary">n/a</span>
              ) : (
                <ConfidenceMeter tier={tier} confidence={currentClaim.confidence} />
              )}
            </div>
            {isGrouped && groupedClaims && (
              <span className="flex items-center gap-1 font-mono text-[11px] text-text-secondary bg-surface-raised px-2 py-0.5 rounded-data border border-border-hairline">
                <Layers className="h-3 w-3 text-signal" />
                <span>occurrence {activeGroupIndex + 1} of {groupedClaims.length}</span>
              </span>
            )}
          </div>

          <SheetTitle className="text-base font-mono font-semibold tracking-tight text-text-primary break-all">
            {currentClaim.field}
          </SheetTitle>
        </SheetHeader>

        {/* Group occurrence tabs if multiple claims under this field */}
        {isGrouped && groupedClaims && (
          <div className="mb-4">
            <span className="text-text-tertiary text-[11px] font-mono block mb-1.5">
              collapsed occurrences ({groupedClaims.length}):
            </span>
            <div className="flex flex-wrap gap-1.5">
              {groupedClaims.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveGroupIndex(idx)}
                  className={cn(
                    "px-2.5 py-1 text-xs font-mono rounded-data border transition-colors flex items-center gap-1.5",
                    activeGroupIndex === idx
                      ? "border-signal bg-surface-raised text-signal font-medium shadow-focus"
                      : "border-border-hairline bg-surface-base text-text-secondary hover:border-border-strong"
                  )}
                >
                  <TierGlyph tier={item.tier} size={10} />
                  <span>#{idx + 1}</span>
                  <span className="text-text-tertiary text-[11px]">
                    ({item.evidence.length}f)
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-5 font-mono text-xs">
          {/* 1. One-sentence tier explanation */}
          <div className="rounded-data border border-border-hairline bg-surface-base p-3">
            <div className="flex items-center gap-2 mb-1.5">
              <TierGlyph tier={tier} size={13} />
              <span className="text-text-secondary font-semibold text-xs lowercase">
                provenance: {tier.toLowerCase().replace(/_/g, " ")}
              </span>
            </div>
            <p className="font-sans text-xs text-text-secondary leading-relaxed">
              {explanation}
            </p>
          </div>

          {/* 2. Method in plain words */}
          <div>
            <span className="text-text-tertiary block mb-1.5 font-semibold lowercase">
              method:
            </span>
            <div className="p-3 rounded-data bg-surface-base border border-border-hairline">
              <p className="font-sans text-xs text-text-primary leading-relaxed">
                {currentClaim.method || "No specific extraction method recorded."}
              </p>
            </div>
          </div>

          {/* 3. Full Value (Pretty JSON in Mono) */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-text-tertiary font-semibold lowercase">
                full value (json):
              </span>
              <Mono value={jsonString} label="copy json" copyable />
            </div>
            <pre className="p-3 rounded-data bg-surface-base border border-border-hairline text-text-primary font-mono text-xs overflow-x-auto whitespace-pre leading-relaxed select-text">
              <code>{jsonString}</code>
            </pre>
          </div>

          <Separator className="my-2" />

          {/* 4. Caveats */}
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-text-tertiary font-semibold lowercase">
                caveats ({currentClaim.caveats?.length || 0}):
              </span>
              {currentClaim.caveats && currentClaim.caveats.length > 0 && (
                <span className="inline-flex items-center gap-1 text-[11px] text-amber-sample font-mono font-medium">
                  <AlertTriangle className="h-3 w-3" />
                  <span>conditional</span>
                </span>
              )}
            </div>

            {currentClaim.caveats && currentClaim.caveats.length > 0 ? (
              <div className="space-y-2">
                {currentClaim.caveats.map((cav, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2.5 p-2.5 rounded-data bg-amber-sample/5 border border-amber-sample/30 text-text-primary"
                  >
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-sample shrink-0 mt-0.5" />
                    <p className="font-sans text-xs text-text-primary leading-relaxed">
                      {cav}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-tertiary font-mono italic">
                No caveats recorded. Observation is unconditional.
              </p>
            )}
          </div>

          <Separator className="my-2" />

          {/* 5. Evidence frame list */}
          <div>
            <span className="text-text-tertiary block mb-2 font-semibold lowercase">
              evidence frames ({currentClaim.evidence?.length || 0}):
            </span>
            {currentClaim.evidence && currentClaim.evidence.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 p-3 rounded-data bg-surface-base border border-border-hairline">
                {currentClaim.evidence.map((frameNum) => (
                  <Mono key={frameNum} label="frame" value={frameNum} copyable />
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-tertiary font-mono italic">
                No packet frames cited (unobservable or global property).
              </p>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};
