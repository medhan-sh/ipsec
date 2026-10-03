import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { CoverageMeta } from "@/api/types";
import { SectionHeader } from "@/components/app/SectionHeader";
import { Button } from "@/components/vendor/button";

interface CoverageGlanceProps {
  coverage: CoverageMeta;
}

export const CoverageGlance: React.FC<CoverageGlanceProps> = ({ coverage }) => {
  const navigate = useNavigate();

  const total = coverage.checks_total || 15;
  const foundPct = total > 0 ? (coverage.checks_found / total) * 100 : 0;
  const passedPct = total > 0 ? (coverage.checks_passed / total) * 100 : 0;
  const gapPct = total > 0 ? (coverage.checks_gap / total) * 100 : 0;

  return (
    <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col gap-3 font-mono text-xs select-none">
      <SectionHeader
        title="coverage at a glance"
        className="my-0 mb-1"
        action={
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/app/coverage")}
            className="h-6 px-2 text-[11px] text-text-secondary hover:text-signal"
          >
            view coverage
            <ArrowUpRight className="h-3 w-3 ml-1" />
          </Button>
        }
      />

      {/* Readable summary line */}
      <div className="text-text-secondary text-xs">
        <span className="text-text-primary font-medium tabular-nums">{total}</span> checks total —{" "}
        <span className="text-severity-high font-medium tabular-nums">{coverage.checks_found}</span> found,{" "}
        <span className="text-signal font-medium tabular-nums">{coverage.checks_passed}</span> passed,{" "}
        <span className="text-text-tertiary font-medium tabular-nums">{coverage.checks_gap}</span> gaps{" "}
        <span className="text-text-tertiary">
          ({coverage.checks_assessable} assessable)
        </span>
      </div>

      {/* Thin Segmented Bar */}
      <div
        onClick={() => navigate("/app/coverage")}
        className="h-2 w-full rounded-data overflow-hidden flex bg-surface-base border border-border-hairline cursor-pointer"
        title="Click to view full coverage report"
      >
        {foundPct > 0 && (
          <div
            style={{ width: `${foundPct}%` }}
            className="bg-severity-high transition-all duration-300"
            title={`${coverage.checks_found} found (${foundPct.toFixed(0)}%)`}
          />
        )}
        {passedPct > 0 && (
          <div
            style={{ width: `${passedPct}%` }}
            className="bg-signal transition-all duration-300"
            title={`${coverage.checks_passed} passed (${passedPct.toFixed(0)}%)`}
          />
        )}
        {gapPct > 0 && (
          <div
            style={{ width: `${gapPct}%` }}
            className="bg-surface-raised border-l border-border-hairline transition-all duration-300"
            title={`${coverage.checks_gap} gaps (${gapPct.toFixed(0)}%)`}
          />
        )}
      </div>

      {/* Metric Breakdown */}
      <div className="grid grid-cols-3 gap-2 pt-1 text-[11px]">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-severity-high shrink-0" />
          <span className="text-text-secondary">found:</span>
          <span className="text-text-primary tabular-nums font-medium">
            {coverage.checks_found}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-signal shrink-0" />
          <span className="text-text-secondary">passed:</span>
          <span className="text-text-primary tabular-nums font-medium">
            {coverage.checks_passed}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-text-tertiary shrink-0" />
          <span className="text-text-secondary">gaps:</span>
          <span className="text-text-primary tabular-nums font-medium">
            {coverage.checks_gap}
          </span>
        </div>
      </div>
    </div>
  );
};
