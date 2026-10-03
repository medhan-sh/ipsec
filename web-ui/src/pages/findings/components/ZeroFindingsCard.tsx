import React from "react";
import { Link } from "react-router-dom";
import { CoverageGapItem } from "@/api/types";
import { Button } from "@/components/vendor/button";
import { Mono } from "@/components/app/Mono";
import { ShieldCheck, AlertCircle, ArrowUpRight } from "lucide-react";

interface ZeroFindingsCardProps {
  passedCount: number;
  gaps: CoverageGapItem[];
  coverageGapCount?: number;
  onViewPasses: () => void;
}

export const ZeroFindingsCard: React.FC<ZeroFindingsCardProps> = ({
  passedCount,
  gaps,
  coverageGapCount = 0,
  onViewPasses,
}) => {
  const gapsCount = Math.max(gaps.length, coverageGapCount);

  return (
    <div className="space-y-4 font-mono text-xs">
      <div className="p-5 rounded-data border border-border-hairline bg-surface-panel space-y-4">
        {/* Primary Statement */}
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-data bg-surface-raised border border-border-hairline shrink-0 text-signal">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-text-primary">
              This capture produced no findings. {passedCount} checks passed.
            </h3>
            <p className="text-xs text-text-secondary font-sans leading-relaxed max-w-[80ch]">
              None of the 15 security evaluation rules detected violations or policy breaches in the observed packets.
            </p>
          </div>
        </div>

        {/* Gap Accounting & Forensics Context */}
        {gapsCount > 0 ? (
          <div className="p-4 rounded-data border border-border-strong bg-surface-base space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-severity-medium shrink-0" />
                <span className="font-semibold text-text-primary text-xs">
                  {gapsCount} coverage gap{gapsCount === 1 ? "" : "s"} remain
                </span>
              </div>
              <Link
                to="/app/coverage"
                className="text-signal hover:underline inline-flex items-center gap-1 text-[11px]"
              >
                Inspect in Coverage
                <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>

            <p className="text-xs text-text-secondary font-sans leading-relaxed max-w-[80ch]">
              Absence of findings is not evidence of security when unobservable parameters exist. The analyzer abstained from evaluating certain assertions because the requisite exchanges or metadata were missing from the trace:
            </p>

            {/* List of remaining gaps */}
            <div className="space-y-2 pt-1">
              {gaps.length > 0 ? (
                gaps.slice(0, 5).map((gap, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-data bg-surface-panel border border-border-hairline flex flex-col md:flex-row md:items-center justify-between gap-2"
                  >
                    <div className="space-y-0.5">
                      <div className="text-text-primary font-medium text-xs">
                        {gap.title || gap.rule_id}
                      </div>
                      {gap.reason && (
                        <div className="text-[11px] text-text-secondary font-sans max-w-[70ch]">
                          {gap.reason}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {gap.gap_kind && (
                        <span className="text-[10px] text-text-tertiary px-1.5 py-0.5 bg-surface-raised border border-border-hairline rounded-data">
                          kind: {gap.gap_kind}
                        </span>
                      )}
                      {gap.scope && (
                        <Mono value={gap.scope} copyable className="text-[10px]" />
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-2.5 rounded-data bg-surface-panel border border-border-hairline text-text-secondary text-[11px] font-sans">
                  {gapsCount} checks could not be evaluated due to missing traffic or unobserved exchanges in this capture.
                </div>
              )}
              {gaps.length > 5 && (
                <div className="text-[11px] text-text-tertiary pl-1">
                  + {gaps.length - 5} more coverage gaps in Coverage tab
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-3 rounded-data border border-border-hairline bg-surface-base text-xs text-text-secondary font-sans">
            Full coverage achieved: 0 gaps remaining across evaluated policy checks.
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center gap-3 pt-2">
          <Button variant="outline" size="sm" onClick={onViewPasses} className="text-xs font-mono">
            View {passedCount} passed check{passedCount === 1 ? "" : "s"}
          </Button>
          {gapsCount > 0 && (
            <Link to="/app/coverage">
              <Button variant="ghost" size="sm" className="text-xs font-mono text-signal hover:text-signal">
                Open coverage report
              </Button>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
};
