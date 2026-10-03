import React from "react";
import { Link } from "react-router-dom";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/vendor/sheet";
import { FindingItem, RuleMeta, CoverageGapItem } from "@/api/types";
import { TierBadge } from "@/components/app/TierBadge";
import { SeverityChip } from "@/components/app/SeverityChip";
import { Mono } from "@/components/app/Mono";
import { Separator } from "@/components/vendor/separator";
import { ArrowUpRight } from "lucide-react";

interface FindingDetailDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  finding: FindingItem | null;
  ruleMeta?: RuleMeta;
  allGaps?: CoverageGapItem[];
}

export const FindingDetailDrawer: React.FC<FindingDetailDrawerProps> = ({
  open,
  onOpenChange,
  finding,
  ruleMeta,
  allGaps = [],
}) => {
  if (!finding) return null;

  const explanation =
    ruleMeta?.explanation || "No explanation catalogue entry recorded for this rule.";
  const recommendation = finding.recommendation || ruleMeta?.recommendation;
  const references = finding.references || ruleMeta?.references || [];

  // Check for related coverage gap (matching rule_id or matching scope)
  const relatedGaps = allGaps.filter(
    (gap) => gap.rule_id === finding.rule_id || (gap.scope && finding.scope && gap.scope === finding.scope)
  );

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl bg-surface-panel border-l border-border-hairline overflow-y-auto p-6 space-y-6 text-xs font-mono"
      >
        {/* Drawer Header */}
        <SheetHeader className="space-y-3 pb-3 border-b border-border-hairline">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityChip severity={finding.severity} />
            <TierBadge tier={finding.tier} />
            {finding.category && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-data text-[10px] font-mono border border-border-hairline bg-surface-raised text-text-secondary uppercase tracking-wider">
                {finding.category}
              </span>
            )}
          </div>
          <SheetTitle className="text-base font-semibold leading-snug text-text-primary font-mono text-left">
            {finding.title}
          </SheetTitle>
        </SheetHeader>

        {/* Structured Metadata Grid */}
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-data bg-surface-base border border-border-hairline">
            <div>
              <span className="text-[10px] text-text-tertiary uppercase tracking-wider block mb-1">
                rule id:
              </span>
              <Mono value={finding.rule_id} copyable className="text-xs" />
            </div>

            <div>
              <span className="text-[10px] text-text-tertiary uppercase tracking-wider block mb-1">
                scope:
              </span>
              <Mono value={finding.scope} copyable className="text-xs" />
            </div>

            {finding.category && (
              <div>
                <span className="text-[10px] text-text-tertiary uppercase tracking-wider block mb-1">
                  category:
                </span>
                <span className="text-text-primary text-xs">{finding.category}</span>
              </div>
            )}

            <div>
              <span className="text-[10px] text-text-tertiary uppercase tracking-wider block mb-1">
                evidence tier:
              </span>
              <TierBadge tier={finding.tier} />
            </div>
          </div>

          {/* Evidence Frames */}
          {finding.evidence && finding.evidence.length > 0 && (
            <div>
              <span className="text-[11px] text-text-secondary uppercase tracking-wider block mb-1.5">
                evidence frames ({finding.evidence.length}):
              </span>
              <div className="flex flex-wrap gap-1.5 p-2 rounded-data bg-surface-base border border-border-hairline">
                {finding.evidence.map((frameNum) => (
                  <Mono
                    key={frameNum}
                    label="frame"
                    value={frameNum}
                    copyable
                    className="text-xs hover:border-signal/50"
                  />
                ))}
              </div>
            </div>
          )}

          <Separator className="bg-border-hairline" />

          {/* Detailed Prose Explanation */}
          <div>
            <span className="text-[11px] text-text-primary font-semibold uppercase tracking-wider block mb-1.5">
              explanation:
            </span>
            <div className="p-3 rounded-data bg-surface-base border border-border-hairline">
              <p className="text-xs text-text-secondary font-sans leading-relaxed max-w-[80ch]">
                {explanation}
              </p>
            </div>
          </div>

          {/* Recommendation */}
          {recommendation && (
            <div>
              <span className="text-[11px] text-text-primary font-semibold uppercase tracking-wider block mb-1.5">
                recommendation:
              </span>
              <div className="p-3 rounded-data bg-surface-base border border-border-hairline">
                <p className="text-xs text-text-secondary font-sans leading-relaxed max-w-[80ch]">
                  {recommendation}
                </p>
              </div>
            </div>
          )}

          {/* Plain Text References with Copy Button */}
          {references.length > 0 && (
            <div>
              <span className="text-[11px] text-text-primary font-semibold uppercase tracking-wider block mb-1.5">
                references:
              </span>
              <div className="space-y-1.5">
                {references.map((ref, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-data bg-surface-base border border-border-hairline"
                  >
                    <span className="text-xs text-text-primary font-mono select-all">
                      {ref}
                    </span>
                    <Mono value={ref} copyable className="ml-2 shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Related Coverage Gaps (Distinct, Never Merged) */}
          {relatedGaps.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border-hairline">
              <div className="rounded-data border border-border-strong bg-surface-base p-3.5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-severity-medium" />
                    Related Coverage Gap ({relatedGaps.length})
                  </span>
                  <Link
                    to="/app/coverage"
                    className="text-[11px] text-signal hover:underline inline-flex items-center gap-1"
                  >
                    View in Coverage
                    <ArrowUpRight className="h-3 w-3" />
                  </Link>
                </div>

                <div className="space-y-2">
                  {relatedGaps.map((gap, gIdx) => (
                    <div
                      key={gIdx}
                      className="p-2.5 rounded-data bg-surface-panel border border-border-hairline space-y-1.5"
                    >
                      <div className="text-xs font-medium text-text-primary">
                        {gap.title || gap.rule_id}
                      </div>
                      {gap.reason && (
                        <p className="text-[11px] text-text-secondary font-sans leading-relaxed max-w-[80ch]">
                          {gap.reason}
                        </p>
                      )}
                      <div className="flex flex-wrap items-center gap-2 text-[10px] text-text-tertiary pt-1">
                        {gap.gap_kind && <span>kind: <strong className="text-text-secondary">{gap.gap_kind}</strong></span>}
                        {gap.actual_tier && <span>tier: <strong className="text-text-secondary">{gap.actual_tier}</strong></span>}
                        {gap.scope && <span>scope: <strong className="text-text-secondary">{gap.scope}</strong></span>}
                      </div>
                    </div>
                  ))}
                </div>

                <p className="text-[10px] text-text-tertiary font-sans italic border-t border-border-hairline pt-2">
                  A failing rule evaluates negative policy assertions on observed frames. A coverage gap tracks unobservable or unassessed properties. They are independent analytical items and never merged into a single score.
                </p>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};
