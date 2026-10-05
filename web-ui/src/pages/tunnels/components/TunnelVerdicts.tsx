import React from "react";
import { VerdictItem } from "@/api/types";
import { TierBadge } from "@/components/app/TierBadge";
import { ConfidenceMeter } from "@/components/app/ConfidenceMeter";
import { Mono } from "@/components/app/Mono";
import { Badge } from "@/components/vendor/badge";
import { AlertTriangle, CheckCircle2, Scale, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface TunnelVerdictsProps {
  verdicts: VerdictItem[];
  sa_id: string;
}

export const TunnelVerdicts: React.FC<TunnelVerdictsProps> = ({
  verdicts,
  sa_id,
}) => {
  return (
    <div className="rounded-data border border-border-hairline bg-surface-panel p-4 space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-hairline">
        <div className="flex items-center gap-2">
          <Scale className="h-4 w-4 text-signal" />
          <span className="text-xs uppercase tracking-wider text-text-secondary font-semibold">
            lifted risk verdicts
          </span>
          <span className="text-xs text-text-tertiary tabular-nums">
            ({verdicts.length} evaluated predicates)
          </span>
        </div>

        <span className="text-[11px] text-text-tertiary">
          evaluated across surviving candidate sets
        </span>
      </div>

      {verdicts.length === 0 ? (
        <div className="p-4 rounded-data border border-border-hairline bg-surface-base text-xs text-text-tertiary">
          No lifted risk verdicts recorded for tunnel <Mono value={sa_id} copyable={false} />.
        </div>
      ) : (
        <div className="space-y-4">
          {verdicts.map((verdict, idx) => {
            const isAmbiguous = Boolean(verdict.ambiguous);
            const trueCount = verdict.surviving_true?.length ?? 0;
            const falseCount = verdict.surviving_false?.length ?? 0;

            return (
              <div
                key={`${verdict.predicate}-${idx}`}
                className={cn(
                  "p-4 rounded-data border bg-surface-base space-y-3 transition-colors",
                  isAmbiguous
                    ? "border-amber-sample/50 shadow-[0_0_8px_rgba(255,210,63,0.1)]"
                    : "border-border-hairline"
                )}
              >
                {/* Predicate title & badges */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-text-primary">
                      {verdict.predicate}
                    </span>
                    {isAmbiguous ? (
                      <Badge
                        variant="warning"
                        className="text-[11px] flex items-center gap-1 font-mono uppercase"
                      >
                        <AlertTriangle className="h-3 w-3" />
                        ambiguous
                      </Badge>
                    ) : (
                      <Badge
                        variant={verdict.outcome ? "signal" : "secondary"}
                        className="text-[11px] font-mono"
                      >
                        outcome: {String(verdict.outcome)}
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    <TierBadge tier={verdict.basis_tier} />
                    <ConfidenceMeter
                      tier={verdict.basis_tier}
                      confidence={verdict.confidence}
                    />
                  </div>
                </div>

                {/* Basis from data */}
                <div className="p-2.5 rounded-data bg-surface-panel border border-border-hairline text-xs">
                  <span className="text-text-tertiary block text-[10px] uppercase tracking-wider mb-1">
                    basis:
                  </span>
                  <p className="text-text-secondary font-sans leading-relaxed text-xs">
                    {verdict.basis || "No basis explanation recorded in findings data."}
                  </p>
                </div>

                {/* Survivors split into surviving_true / surviving_false */}
                <div className="pt-1 space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-text-tertiary">
                    <span>
                      {isAmbiguous
                        ? "Ambiguous: candidate set divides across this risk question"
                        : "Surviving candidate split:"}
                    </span>
                    <span className="tabular-nums">
                      {trueCount} true / {falseCount} false
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Surviving True */}
                    <div className="p-3 rounded-data border border-border-hairline bg-surface-panel space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-text-secondary font-semibold flex items-center gap-1.5">
                          <CheckCircle2 className="h-3.5 w-3.5 text-signal" />
                          <span>Satisfies predicate (true)</span>
                        </span>
                        <span className="text-signal tabular-nums font-semibold">
                          {trueCount}
                        </span>
                      </div>

                      {trueCount === 0 ? (
                        <span className="text-[11px] text-text-tertiary block italic">
                          (none)
                        </span>
                      ) : (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {verdict.surviving_true.map((suite) => (
                            <Mono
                              key={suite}
                              value={suite}
                              copyable
                              className="text-xs bg-surface-raised border-border-hairline text-text-primary"
                            />
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Surviving False */}
                    <div className="p-3 rounded-data border border-border-hairline bg-surface-panel space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-text-secondary font-semibold flex items-center gap-1.5">
                          <XCircle className="h-3.5 w-3.5 text-text-tertiary" />
                          <span>Does not satisfy (false)</span>
                        </span>
                        <span className="text-text-secondary tabular-nums font-semibold">
                          {falseCount}
                        </span>
                      </div>

                      {falseCount === 0 ? (
                        <span className="text-[11px] text-text-tertiary block italic">
                          (none)
                        </span>
                      ) : (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {verdict.surviving_false.map((suite) => (
                            <Mono
                              key={suite}
                              value={suite}
                              copyable
                              className="text-xs bg-surface-raised border-border-hairline text-text-primary"
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
