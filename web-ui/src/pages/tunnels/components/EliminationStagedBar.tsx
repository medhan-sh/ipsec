import React from "react";
import { EliminationReasonGroup, computeEliminationSteps } from "../types";
import { cn } from "@/lib/utils";
import { ArrowRight, CheckCircle2 } from "lucide-react";

interface EliminationStagedBarProps {
  universeSize: number;
  survivorsCount: number;
  groups: EliminationReasonGroup[];
  onSelectGroup?: (groupId: string) => void;
  selectedGroupId?: string | null;
}

export const EliminationStagedBar: React.FC<EliminationStagedBarProps> = ({
  universeSize,
  survivorsCount,
  groups,
  onSelectGroup,
  selectedGroupId,
}) => {
  const steps = computeEliminationSteps(universeSize, groups);
  const totalEliminated = universeSize - survivorsCount;
  const survivingPct =
    universeSize > 0 ? ((survivorsCount / universeSize) * 100).toFixed(1) : "0.0";

  return (
    <div className="rounded-data border border-border-hairline bg-surface-panel p-4 space-y-4 font-mono">
      {/* Top Headline Metrics */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-hairline">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-wider text-text-secondary font-semibold">
            elimination pipeline
          </span>
          <span className="text-[11px] text-text-tertiary">
            (wire-geometry constraint narrowing)
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs tabular-nums">
          <div>
            <span className="text-text-tertiary mr-1">universe:</span>
            <span className="text-text-primary font-medium">{universeSize}</span>
          </div>
          <div>
            <span className="text-text-tertiary mr-1">eliminated:</span>
            <span className="text-[#ff4d5e] font-medium">{totalEliminated}</span>
          </div>
          <div>
            <span className="text-text-tertiary mr-1">survivors:</span>
            <span className="text-signal font-semibold">{survivorsCount}</span>
            <span className="text-text-tertiary text-[11px] ml-1">({survivingPct}%)</span>
          </div>
        </div>
      </div>

      {/* Proportional Segmented Staged Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px] text-text-tertiary">
          <span>proportional wire representation</span>
          <span>{survivorsCount} of {universeSize} survive</span>
        </div>

        <div className="h-6 w-full rounded-data bg-surface-base border border-border-hairline flex overflow-hidden p-0.5 gap-0.5">
          {/* Surviving Segment */}
          {survivorsCount > 0 && (
            <div
              style={{
                width: `${Math.max(6, (survivorsCount / universeSize) * 100)}%`,
              }}
              className="h-full bg-signal/20 border border-signal text-signal flex items-center justify-center px-1.5 transition-all text-[11px] font-semibold truncate cursor-default"
              title={`Surviving candidates: ${survivorsCount} suites (${survivingPct}%)`}
            >
              <CheckCircle2 className="h-3 w-3 mr-1 shrink-0" />
              <span className="truncate">{survivorsCount} surviving</span>
            </div>
          )}

          {/* Eliminated Segments per Group */}
          {groups.map((group, idx) => {
            const widthPct = (group.count / universeSize) * 100;
            const isSelected = selectedGroupId === group.id;

            return (
              <button
                key={group.id}
                type="button"
                onClick={() => onSelectGroup?.(group.id)}
                style={{ width: `${Math.max(4, widthPct)}%` }}
                className={cn(
                  "h-full flex items-center justify-center px-1 transition-colors text-[10px] truncate border",
                  isSelected
                    ? "bg-[#ff4d5e]/30 border-[#ff4d5e] text-[#ff8a3d]"
                    : "bg-surface-raised border-border-hairline text-text-tertiary hover:bg-surface-panel hover:text-text-secondary"
                )}
                title={`Step ${idx + 1}: ${group.shortLabel} eliminated ${group.count} suites. Click to inspect.`}
              >
                <span className="truncate">
                  -{group.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Sequential Labeled Steps Pipeline */}
      <div className="pt-2">
        <div className="text-[11px] text-text-tertiary mb-2 uppercase tracking-wide">
          staged elimination steps:
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Step 0: Initial Universe */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-data bg-surface-base border border-border-hairline">
            <span className="text-text-tertiary text-[10px]">initial</span>
            <span className="text-text-primary font-medium">
              {universeSize} universe
            </span>
          </div>

          {/* Elimination Steps */}
          {steps.map((step) => {
            const isSelected = selectedGroupId === step.groupId;
            return (
              <React.Fragment key={step.groupId}>
                <ArrowRight className="h-3 w-3 text-border-strong shrink-0" />

                <button
                  type="button"
                  onClick={() => onSelectGroup?.(step.groupId)}
                  className={cn(
                    "flex flex-col items-start px-2.5 py-1.5 rounded-data border transition-colors text-left group",
                    isSelected
                      ? "bg-surface-raised border-[#ff4d5e] text-text-primary"
                      : "bg-surface-base border-border-hairline hover:border-border-strong hover:bg-surface-raised"
                  )}
                  title={`Eliminated: ${step.reasonText}`}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#ff4d5e] font-semibold tabular-nums">
                      -{step.countEliminated}
                    </span>
                    <span className="text-text-secondary group-hover:text-text-primary font-mono text-[11px]">
                      {step.label}
                    </span>
                  </div>
                  <span className="text-[10px] text-text-tertiary tabular-nums">
                    → {step.remainingCount} remaining
                  </span>
                </button>
              </React.Fragment>
            );
          })}

          {/* Final Step: Survivors */}
          <ArrowRight className="h-3 w-3 text-border-strong shrink-0" />

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-data bg-signal-faint border border-signal text-signal">
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
            <div className="flex flex-col">
              <span className="font-semibold text-xs tabular-nums">
                {survivorsCount} survivors
              </span>
              <span className="text-[10px] text-signal-dim font-normal">
                surviving candidates
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
