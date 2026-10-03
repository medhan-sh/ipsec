import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, CheckCircle2 } from "lucide-react";
import { FindingItem, RuleMeta, Severity } from "@/api/types";
import { SectionHeader } from "@/components/app/SectionHeader";
import { SeverityChip } from "@/components/app/SeverityChip";
import { Mono } from "@/components/app/Mono";
import { Button } from "@/components/vendor/button";
import { cn } from "@/lib/utils";

interface FindingsSummaryProps {
  findings: FindingItem[];
  rules?: Record<string, RuleMeta>;
}

const SEVERITY_WEIGHT: Record<string, number> = {
  CRITICAL: 5,
  HIGH: 4,
  MEDIUM: 3,
  LOW: 2,
  INFO: 1,
};

export const FindingsSummary: React.FC<FindingsSummaryProps> = ({
  findings,
  rules = {},
}) => {
  const navigate = useNavigate();

  const counts: Record<Severity, number> = {
    CRITICAL: 0,
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0,
    INFO: 0,
  };

  findings.forEach((f) => {
    const sev = f.severity?.toUpperCase() as Severity;
    if (counts[sev] !== undefined) {
      counts[sev]++;
    }
  });

  const total = findings.length;

  const sortedFindings = [...findings].sort((a, b) => {
    const wA = SEVERITY_WEIGHT[a.severity?.toUpperCase()] || 0;
    const wB = SEVERITY_WEIGHT[b.severity?.toUpperCase()] || 0;
    return wB - wA;
  });

  const topFive = sortedFindings.slice(0, 5);

  const handleSelectFinding = (finding: FindingItem) => {
    navigate(`/app/findings?rule=${encodeURIComponent(finding.rule_id)}`);
  };

  return (
    <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col gap-3 font-mono text-xs select-none">
      <SectionHeader
        title="findings summary"
        count={total}
        className="my-0 mb-1"
        action={
          total > 5 ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/app/findings")}
              className="h-6 px-2 text-[11px] text-text-secondary hover:text-signal"
            >
              view all {total}
              <ArrowUpRight className="h-3 w-3 ml-1" />
            </Button>
          ) : undefined
        }
      />

      {total === 0 ? (
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel/40 flex items-center gap-2.5 text-signal-dim">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-signal" />
          <span className="text-text-secondary font-sans text-xs">
            0 findings — capture is clean against all assessable policy rules.
          </span>
        </div>
      ) : (
        <>
          {/* Compact Severity Bar */}
          <div className="space-y-1.5">
            <div className="h-2 w-full rounded-data overflow-hidden flex bg-surface-base border border-border-hairline">
              {(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] as const).map(
                (sev) => {
                  const count = counts[sev];
                  if (count === 0) return null;
                  const pct = (count / total) * 100;
                  const colorClass =
                    sev === "CRITICAL"
                      ? "bg-severity-critical"
                      : sev === "HIGH"
                      ? "bg-severity-high"
                      : sev === "MEDIUM"
                      ? "bg-severity-medium"
                      : sev === "LOW"
                      ? "bg-severity-low"
                      : "bg-severity-info";

                  return (
                    <div
                      key={sev}
                      style={{ width: `${pct}%` }}
                      className={cn(colorClass, "h-full transition-all duration-200")}
                      title={`${sev}: ${count} (${pct.toFixed(0)}%)`}
                    />
                  );
                }
              )}
            </div>

            {/* Counts breakdown row */}
            <div className="flex flex-wrap gap-2 text-[11px] pt-0.5">
              {(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] as const).map(
                (sev) => {
                  const count = counts[sev];
                  return (
                    <div
                      key={sev}
                      className={cn(
                        "flex items-center gap-1.5 px-1.5 py-0.5 rounded-data border",
                        count > 0
                          ? "border-border-hairline bg-surface-base"
                          : "border-border-hairline/40 bg-surface-base/30 opacity-40"
                      )}
                    >
                      <SeverityChip severity={sev} />
                      <span className="text-text-primary tabular-nums font-medium">
                        {count}
                      </span>
                    </div>
                  );
                }
              )}
            </div>
          </div>

          {/* Top Five Findings List */}
          <div className="space-y-1.5 mt-1" role="list" aria-label="Top findings">
            {topFive.map((f, idx) => {
              const ruleMeta = rules[f.rule_id];
              const recommendation =
                f.recommendation || ruleMeta?.recommendation || "Investigate cipher suite posture.";

              const borderSevColor =
                f.severity === "CRITICAL"
                  ? "before:bg-severity-critical"
                  : f.severity === "HIGH"
                  ? "before:bg-severity-high"
                  : f.severity === "MEDIUM"
                  ? "before:bg-severity-medium"
                  : f.severity === "LOW"
                  ? "before:bg-severity-low"
                  : "before:bg-severity-info";

              return (
                <div
                  key={`${f.rule_id}-${idx}`}
                  role="listitem"
                  onClick={() => handleSelectFinding(f)}
                  className={cn(
                    "p-2.5 rounded-data border border-border-hairline bg-surface-panel hover:bg-surface-raised hover:border-border-strong cursor-pointer transition-colors duration-150 flex flex-col gap-1 relative overflow-hidden pl-3",
                    `before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[2px] ${borderSevColor}`
                  )}
                >
                  <div className="flex items-center gap-2">
                    <SeverityChip severity={f.severity} />
                    <span className="font-medium text-text-primary text-xs truncate">
                      {f.title}
                    </span>
                  </div>

                  <div className="flex items-center justify-between gap-2 mt-0.5 text-[11px]">
                    <p className="text-text-secondary font-sans line-clamp-1 flex-1">
                      {recommendation}
                    </p>
                    {f.scope && (
                      <Mono
                        value={f.scope}
                        copyable={false}
                        className="text-[10px] shrink-0"
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
