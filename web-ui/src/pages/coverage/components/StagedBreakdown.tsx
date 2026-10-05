import React from "react";
import { CoverageMeta } from "@/api/types";
import { ArrowRight, CheckCircle2, AlertOctagon, HelpCircle, Shield } from "lucide-react";
import { cn } from "@/lib/utils";

interface StagedBreakdownProps {
  coverage: CoverageMeta;
  className?: string;
}

export const StagedBreakdown: React.FC<StagedBreakdownProps> = ({
  coverage,
  className,
}) => {
  const total = coverage.checks_total || 0;
  const gaps = coverage.checks_gap || 0;
  const assessable = coverage.checks_assessable || 0;
  const found = coverage.checks_found || 0;
  const passed = coverage.checks_passed || 0;

  const assessablePct = total > 0 ? Math.round((assessable / total) * 100) : 0;
  const gapsPct = total > 0 ? Math.round((gaps / total) * 100) : 0;
  const passedPct = total > 0 ? Math.round((passed / total) * 100) : 0;
  const foundPct = total > 0 ? Math.round((found / total) * 100) : 0;

  return (
    <div className={cn("space-y-4 font-mono", className)}>
      {/* 4-Stage Waterfall Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {/* Stage 1: Total Rules */}
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-text-tertiary lowercase">
              stage 1 · total
            </span>
            <Shield className="h-4 w-4 text-text-secondary" />
          </div>
          <div className="my-2">
            <div className="text-2xl font-bold tracking-tight text-text-primary tabular-nums">
              {total}
            </div>
            <div className="text-xs text-text-secondary lowercase">
              catalogue rules
            </div>
          </div>
          <p className="text-[11px] font-sans text-text-tertiary leading-relaxed mt-2 pt-2 border-t border-border-hairline">
            All policy rules defined in analyzer schema.
          </p>
        </div>

        {/* Stage 2: Coverage Gaps */}
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-text-tertiary lowercase">
              stage 2 · gaps
            </span>
            <HelpCircle className="h-4 w-4 text-text-tertiary" />
          </div>
          <div className="my-2">
            <div className="text-2xl font-bold tracking-tight text-text-tertiary tabular-nums flex items-baseline gap-1">
              <span>{gaps}</span>
              <span className="text-xs font-normal text-text-tertiary">
                ({gapsPct}%)
              </span>
            </div>
            <div className="text-xs text-text-tertiary lowercase">
              unobservable / omitted
            </div>
          </div>
          <p className="text-[11px] font-sans text-text-tertiary leading-relaxed mt-2 pt-2 border-t border-border-hairline">
            Signal unobservable or missing in capture.
          </p>
        </div>

        {/* Stage 3: Assessable Checks */}
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-text-tertiary lowercase">
              stage 3 · assessable
            </span>
            <ArrowRight className="h-4 w-4 text-signal" />
          </div>
          <div className="my-2">
            <div className="text-2xl font-bold tracking-tight text-text-primary tabular-nums flex items-baseline gap-1">
              <span>{assessable}</span>
              <span className="text-xs font-normal text-text-secondary">
                ({assessablePct}%)
              </span>
            </div>
            <div className="text-xs text-text-secondary lowercase">
              sufficient evidence
            </div>
          </div>
          <p className="text-[11px] font-sans text-text-tertiary leading-relaxed mt-2 pt-2 border-t border-border-hairline">
            Minimum required tier satisfied.
          </p>
        </div>

        {/* Stage 4: Evaluated Outcomes */}
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-text-tertiary lowercase">
              stage 4 · outcomes
            </span>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-signal" />
              <AlertOctagon className="h-3.5 w-3.5 text-severity-high" />
            </div>
          </div>
          <div className="my-2 space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-signal flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> passed:
              </span>
              <strong className="text-signal tabular-nums font-bold text-sm">
                {passed}
              </strong>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-severity-high flex items-center gap-1">
                <AlertOctagon className="h-3 w-3" /> violations:
              </span>
              <strong className="text-severity-high tabular-nums font-bold text-sm">
                {found}
              </strong>
            </div>
          </div>
          <p className="text-[11px] font-sans text-text-tertiary leading-relaxed mt-2 pt-2 border-t border-border-hairline">
            Final declarative policy verdicts.
          </p>
        </div>
      </div>

      {/* Accounting Reconciliation Strip */}
      <div className="p-3.5 rounded-data border border-border-hairline bg-surface-base flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-text-tertiary font-semibold uppercase text-[10px] tracking-wider">
            accounting:
          </span>
          <span className="text-text-primary font-medium">
            {total} total
          </span>
          <span className="text-text-tertiary">=</span>
          <span className="text-text-tertiary">
            {gaps} gaps
          </span>
          <span className="text-text-tertiary">+</span>
          <span className="text-text-primary">
            {assessable} assessable
          </span>
          <span className="text-text-tertiary">
            ({passed} passed · {found} found)
          </span>
        </div>

        {/* Proportional distribution bar */}
        <div className="w-full sm:w-64 space-y-1">
          <div className="h-2 w-full bg-surface-panel rounded-data overflow-hidden flex border border-border-hairline">
            {passedPct > 0 && (
              <div
                style={{ width: `${passedPct}%` }}
                className="bg-signal transition-all duration-200"
                title={`Passed: ${passed} (${passedPct}%)`}
              />
            )}
            {foundPct > 0 && (
              <div
                style={{ width: `${foundPct}%` }}
                className="bg-severity-high transition-all duration-200"
                title={`Violations: ${found} (${foundPct}%)`}
              />
            )}
            {gapsPct > 0 && (
              <div
                style={{ width: `${gapsPct}%` }}
                className="bg-text-tertiary/40 transition-all duration-200"
                title={`Gaps: ${gaps} (${gapsPct}%)`}
              />
            )}
          </div>
          <div className="flex justify-between text-[10px] text-text-tertiary font-mono">
            <span className="text-signal">{passed} passed</span>
            {found > 0 && <span className="text-severity-high">{found} found</span>}
            <span className="text-text-tertiary">{gaps} gaps</span>
          </div>
        </div>
      </div>
    </div>
  );
};
