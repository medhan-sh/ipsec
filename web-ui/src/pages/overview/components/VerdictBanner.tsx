import React from "react";
import { useNavigate } from "react-router-dom";
import { ShieldAlert, CheckCircle2, AlertTriangle, ArrowRight } from "lucide-react";
import { FindingItem, VerdictItem } from "@/api/types";
import { TierGlyph } from "@/components/app/TierGlyph";
import { SeverityChip } from "@/components/app/SeverityChip";
import { Button } from "@/components/vendor/button";

interface VerdictBannerProps {
  verdicts: VerdictItem[];
  findings: FindingItem[];
}

export const VerdictBanner: React.FC<VerdictBannerProps> = ({
  verdicts = [],
  findings = [],
}) => {
  const navigate = useNavigate();

  const hasCritical = findings.some(
    (f) => f.severity?.toUpperCase() === "CRITICAL"
  );
  const hasHigh = findings.some((f) => f.severity?.toUpperCase() === "HIGH");
  const hasFailedVerdict = verdicts.some((v) => v.outcome === false);

  const isAlarm = hasCritical || hasHigh || hasFailedVerdict;
  const isClean = findings.length === 0 && !hasFailedVerdict;

  // Dominant finding
  const dominantFinding = findings[0];

  return (
    <div
      className={`p-4 sm:p-5 rounded-data border transition-all duration-200 select-none font-mono ${
        isAlarm
          ? "border-severity-critical/50 bg-[#0f0406]/90 relative before:absolute before:left-0 before:top-0 before:bottom-0 before:w-1 before:bg-severity-critical"
          : isClean
          ? "border-signal/40 bg-[#030d07]/90 relative before:absolute before:left-0 before:top-0 before:bottom-0 before:w-1 before:bg-signal"
          : "border-border-hairline bg-surface-panel"
      }`}
    >
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Overall Assessment Posture */}
        <div className="flex items-start gap-3.5">
          <div className="mt-0.5 shrink-0">
            {isAlarm ? (
              <ShieldAlert className="h-5 w-5 text-severity-critical animate-pulse" />
            ) : isClean ? (
              <CheckCircle2 className="h-5 w-5 text-signal" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-amber-sample" />
            )}
          </div>

          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-bold tracking-wider uppercase ${
                  isAlarm
                    ? "text-severity-critical"
                    : isClean
                    ? "text-signal"
                    : "text-amber-sample"
                }`}
              >
                {isAlarm
                  ? "FORENSIC FINDINGS REQUIRE REMEDIATION"
                  : isClean
                  ? "CAPTURE ASSESSMENT: ALL CHECKS CONFORMANT"
                  : "ASSESSMENT: POLICY FINDINGS OBSERVED"}
              </span>
              <span className="text-[10px] text-text-tertiary">
                // SCHEMA 1.0 AUDIT
              </span>
            </div>

            {dominantFinding ? (
              <div className="flex flex-wrap items-center gap-2 pt-0.5">
                <span className="text-xs text-text-secondary">
                  Primary exposure:
                </span>
                <SeverityChip severity={dominantFinding.severity} />
                <span className="text-xs text-text-primary font-semibold">
                  {dominantFinding.title}
                </span>
                <span className="text-[11px] text-text-tertiary">
                  ({dominantFinding.rule_id})
                </span>
              </div>
            ) : (
              <p className="text-xs text-text-secondary font-sans">
                Zero policy violations detected across evaluated frames. All tunnel
                constraints satisfied without tier degradation.
              </p>
            )}
          </div>
        </div>

        {/* Right: Quick Action to Findings / Tunnels */}
        <div className="flex items-center gap-2 shrink-0">
          {findings.length > 0 ? (
            <Button
              variant="signal"
              size="sm"
              onClick={() => navigate("/app/findings")}
              className="text-xs font-mono"
            >
              INVESTIGATE {findings.length} FINDINGS
              <ArrowRight className="h-3 w-3 ml-1.5" />
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/app/tunnels")}
              className="text-xs font-mono"
            >
              INSPECT TUNNELS
              <ArrowRight className="h-3 w-3 ml-1.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Sub-strip: Cryptographic Verdicts by SA */}
      {verdicts.length > 0 && (
        <div className="mt-4 pt-3 border-t border-border-hairline/80 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {verdicts.map((v, i) => {
            const predName = v.predicate.replace("_acceptable", "");
            const isOk = v.outcome === true;
            const isAmbiguous = v.ambiguous;

            return (
              <div
                key={`${v.sa_id}-${v.predicate}-${i}`}
                className="px-2.5 py-1.5 rounded-data bg-surface-base/80 border border-border-hairline flex items-center justify-between gap-2 text-[11px]"
              >
                <div className="flex items-center gap-1.5 truncate">
                  <TierGlyph tier={v.basis_tier} size={12} />
                  <span className="text-text-secondary capitalize">
                    {predName}:
                  </span>
                  <span
                    className={`font-semibold ${
                      isAmbiguous
                        ? "text-amber-sample"
                        : isOk
                        ? "text-signal"
                        : "text-severity-critical"
                    }`}
                  >
                    {isAmbiguous ? "ambiguous" : isOk ? "acceptable" : "violation"}
                  </span>
                </div>

                <span className="text-text-tertiary text-[10px] shrink-0 font-sans">
                  {v.basis_tier === "OBSERVED" ? "certain" : v.basis_tier.toLowerCase()}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
