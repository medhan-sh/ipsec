import React from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/vendor/sheet";
import { FindingItem, RuleMeta } from "@/api/types";
import { TierBadge } from "./TierBadge";
import { SeverityChip } from "./SeverityChip";
import { Mono } from "./Mono";
import { Separator } from "@/components/vendor/separator";

interface DetailDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  finding: FindingItem | null;
  ruleMeta?: RuleMeta;
}

export const DetailDrawer: React.FC<DetailDrawerProps> = ({
  open,
  onOpenChange,
  finding,
  ruleMeta,
}) => {
  if (!finding) return null;

  const explanation = ruleMeta?.explanation || "No explanation catalogue entry available.";
  const recommendation = finding.recommendation || ruleMeta?.recommendation;
  const references = finding.references || ruleMeta?.references || [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <SeverityChip severity={finding.severity} />
            <TierBadge tier={finding.tier} />
          </div>
          <SheetTitle className="text-base font-semibold leading-snug">
            {finding.title}
          </SheetTitle>
        </SheetHeader>

        <div className="space-y-4 font-mono text-xs text-text-primary">
          <div>
            <span className="text-text-tertiary block mb-1">rule id:</span>
            <Mono value={finding.rule_id} copyable />
          </div>

          <div>
            <span className="text-text-tertiary block mb-1">scope:</span>
            <Mono value={finding.scope} copyable />
          </div>

          {finding.evidence && finding.evidence.length > 0 && (
            <div>
              <span className="text-text-tertiary block mb-1">evidence frames:</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {finding.evidence.map((f) => (
                  <Mono key={f} label="frame" value={f} />
                ))}
              </div>
            </div>
          )}

          <Separator className="my-3" />

          <div>
            <span className="text-text-tertiary block mb-1.5 font-semibold">explanation:</span>
            <p className="text-xs text-text-secondary font-sans leading-relaxed">
              {explanation}
            </p>
          </div>

          {recommendation && (
            <div>
              <span className="text-text-tertiary block mb-1.5 font-semibold">recommendation:</span>
              <p className="text-xs text-text-secondary font-sans leading-relaxed">
                {recommendation}
              </p>
            </div>
          )}

          {references.length > 0 && (
            <div>
              <span className="text-text-tertiary block mb-1.5 font-semibold">references:</span>
              <div className="flex flex-col gap-1.5">
                {references.map((ref, idx) => (
                  <div key={idx} className="flex items-center">
                    <Mono value={ref} copyable />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};
