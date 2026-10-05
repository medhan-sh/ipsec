import React from "react";
import { Mono } from "@/components/app/Mono";
import { Badge } from "@/components/vendor/badge";
import { Button } from "@/components/vendor/button";
import { Copy, HelpCircle, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

interface SurvivorsListProps {
  survivors: string[];
  indistinguishable: string[][];
}

export const SurvivorsList: React.FC<SurvivorsListProps> = ({
  survivors,
  indistinguishable,
}) => {
  // Map each suite to its indistinguishable group index if it belongs to one
  const suiteGroupMap = new Map<string, number>();
  indistinguishable.forEach((group, groupIdx) => {
    group.forEach((suite) => {
      suiteGroupMap.set(suite, groupIdx);
    });
  });

  // Filter indistinguishable groups to only include surviving suites
  const survivingIndistGroups: { groupIndex: number; suites: string[] }[] = [];
  indistinguishable.forEach((group, idx) => {
    const present = group.filter((s) => survivors.includes(s));
    if (present.length > 0) {
      survivingIndistGroups.push({ groupIndex: idx + 1, suites: present });
    }
  });

  // Ungrouped survivors that are uniquely distinguishable
  const ungrouped = survivors.filter((s) => !suiteGroupMap.has(s));

  const handleCopyAll = () => {
    navigator.clipboard.writeText(survivors.join("\n"));
    toast.success(`Copied ${survivors.length} surviving suites to clipboard`);
  };

  return (
    <div className="rounded-data border border-border-hairline bg-surface-panel p-4 space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-hairline">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-signal" />
          <span className="text-xs uppercase tracking-wider text-text-secondary font-semibold">
            surviving cipher suites
          </span>
          <span className="text-xs text-signal tabular-nums font-semibold">
            ({survivors.length} suites)
          </span>
        </div>

        {survivors.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyAll}
            className="h-7 text-[11px] text-text-secondary hover:text-text-primary"
            title="Copy all surviving candidate names"
          >
            <Copy className="h-3 w-3 mr-1" />
            copy survivors
          </Button>
        )}
      </div>

      {survivors.length === 0 ? (
        <div className="p-4 rounded-data border border-border-hairline bg-surface-base text-xs text-[#ff4d5e] flex items-center gap-2">
          <span>(none survive — all candidate suites eliminated by wire framing)</span>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Note explaining indistinguishable groups */}
          <div className="flex items-start gap-2 p-2.5 rounded-data bg-surface-base border border-border-hairline text-xs text-text-secondary">
            <HelpCircle className="h-3.5 w-3.5 text-text-tertiary shrink-0 mt-0.5" />
            <p className="font-sans leading-relaxed text-[11px]">
              Suites bracketed into <strong>indistinguishable groups</strong> share identical wire geometry (block alignment and ICV length). Passive observation cannot tell them apart on the wire without decrypting.
            </p>
          </div>

          {/* Indistinguishable Groups (Bracketed together) */}
          {survivingIndistGroups.map(({ groupIndex, suites }) => (
            <div
              key={`group-${groupIndex}`}
              className="relative pl-4 border-l-2 border-signal/70 py-2.5 pr-3 rounded-r-data bg-surface-base/80 border-t border-b border-r border-border-hairline space-y-2.5"
            >
              {/* Bracket Header */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-signal text-xs font-semibold">
                    [ Indistinguishable Group {groupIndex} ]
                  </span>
                  <span className="text-[11px] text-text-tertiary tabular-nums">
                    ({suites.length} suites)
                  </span>
                </div>

                <Badge
                  variant="signal"
                  className="text-[10px] uppercase font-mono px-1.5 py-0 h-4"
                >
                  identical wire geometry
                </Badge>
              </div>

              {/* Suites in group */}
              <div className="flex flex-wrap gap-2">
                {suites.map((suite) => (
                  <Mono
                    key={suite}
                    value={suite}
                    copyable
                    className="text-xs bg-surface-panel border-border-strong text-text-primary hover:border-signal"
                  />
                ))}
              </div>
            </div>
          ))}

          {/* Ungrouped / Distinctly Distinguishable Survivors */}
          {ungrouped.length > 0 && (
            <div className="pl-4 border-l-2 border-border-strong py-2.5 pr-3 rounded-r-data bg-surface-base/50 border-t border-b border-r border-border-hairline space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-text-secondary">
                  [ Unique Wire Framing ({ungrouped.length} suites) ]
                </span>
                <span className="text-[10px] text-text-tertiary">
                  distinguishable from all other candidate suites
                </span>
              </div>

              <div className="flex flex-wrap gap-2">
                {ungrouped.map((suite) => (
                  <Mono
                    key={suite}
                    value={suite}
                    copyable
                    className="text-xs bg-surface-panel border-border-hairline text-text-primary"
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
