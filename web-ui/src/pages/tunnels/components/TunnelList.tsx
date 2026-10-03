import React from "react";
import { NormalizedCandidateSet } from "../types";
import { Mono } from "@/components/app/Mono";
import { Badge } from "@/components/vendor/badge";
import { Button } from "@/components/vendor/button";
import { Input } from "@/components/vendor/input";
import { cn } from "@/lib/utils";
import { AlertCircle, ChevronLeft, ChevronRight, Search } from "lucide-react";

interface TunnelListProps {
  tunnels: NormalizedCandidateSet[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  filterText: string;
  onFilterChange: (val: string) => void;
}

export const TunnelList: React.FC<TunnelListProps> = ({
  tunnels,
  selectedIndex,
  onSelectIndex,
  filterText,
  onFilterChange,
}) => {
  const filteredTunnels = tunnels
    .map((tunnel, originalIndex) => ({ tunnel, originalIndex }))
    .filter(({ tunnel }) => {
      if (!filterText.trim()) return true;
      const q = filterText.toLowerCase();
      return (
        tunnel.sa_id.toLowerCase().includes(q) ||
        tunnel.survivors.some((s) => s.toLowerCase().includes(q))
      );
    });

  const handlePrev = () => {
    if (tunnels.length <= 1) return;
    const nextIdx = (selectedIndex - 1 + tunnels.length) % tunnels.length;
    onSelectIndex(nextIdx);
  };

  const handleNext = () => {
    if (tunnels.length <= 1) return;
    const nextIdx = (selectedIndex + 1) % tunnels.length;
    onSelectIndex(nextIdx);
  };

  return (
    <div className="flex flex-col h-full rounded-data border border-border-hairline bg-surface-panel overflow-hidden">
      {/* Header with tunnel count and navigation buttons */}
      <div className="p-3 border-b border-border-hairline flex items-center justify-between gap-2 bg-surface-base">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary font-mono">
            tunnels
          </span>
          <span className="ml-1.5 text-xs text-text-tertiary tabular-nums font-mono">
            ({tunnels.length})
          </span>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrev}
            disabled={tunnels.length <= 1}
            title="Previous tunnel ([)"
            className="h-6 px-1.5 text-[11px] font-mono text-text-secondary hover:text-text-primary"
          >
            <ChevronLeft className="h-3 w-3 mr-0.5" />
            <span>[</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNext}
            disabled={tunnels.length <= 1}
            title="Next tunnel (])"
            className="h-6 px-1.5 text-[11px] font-mono text-text-secondary hover:text-text-primary"
          >
            <span>]</span>
            <ChevronRight className="h-3 w-3 ml-0.5" />
          </Button>
        </div>
      </div>

      {/* Filter Bar if > 1 tunnel */}
      {tunnels.length > 2 && (
        <div className="p-2 border-b border-border-hairline bg-surface-base/50">
          <div className="relative">
            <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-text-tertiary pointer-events-none" />
            <Input
              value={filterText}
              onChange={(e) => onFilterChange(e.target.value)}
              placeholder="filter spi..."
              className="h-7 pl-7 pr-2 text-xs font-mono bg-surface-panel"
            />
          </div>
        </div>
      )}

      {/* Tunnel Items List */}
      <div className="flex-1 overflow-y-auto divide-y divide-border-hairline p-1">
        {filteredTunnels.length === 0 ? (
          <div className="p-4 text-center text-xs text-text-tertiary font-mono">
            No matching tunnels
          </div>
        ) : (
          filteredTunnels.map(({ tunnel, originalIndex }) => {
            const isSelected = originalIndex === selectedIndex;
            const pct =
              tunnel.universeSize > 0
                ? Math.round((tunnel.survivors.length / tunnel.universeSize) * 100)
                : 0;

            return (
              <div
                key={tunnel.sa_id}
                onClick={() => onSelectIndex(originalIndex)}
                className={cn(
                  "group relative flex flex-col gap-1.5 p-3 cursor-pointer rounded-data transition-colors font-mono select-none border-l-2",
                  isSelected
                    ? "bg-signal-faint border-l-signal border-t border-b border-r border-border-strong text-text-primary"
                    : "border-l-transparent hover:bg-surface-raised hover:border-l-border-strong text-text-secondary"
                )}
              >
                {/* Top Row: Index + SA ID */}
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[11px] text-text-tertiary tabular-nums shrink-0">
                      {String(originalIndex + 1).padStart(2, "0")}
                    </span>
                    <Mono
                      value={tunnel.sa_id}
                      copyable={false}
                      className={cn(
                        "text-xs truncate max-w-[200px] border-none px-0 py-0 bg-transparent",
                        isSelected ? "text-text-primary font-medium" : "text-text-secondary group-hover:text-text-primary"
                      )}
                    />
                  </div>

                  {/* Active Indicator Pin */}
                  {isSelected && (
                    <span className="h-1.5 w-1.5 rounded-full bg-signal shadow-[0_0_6px_#00ff7f] shrink-0" />
                  )}
                </div>

                {/* Second Row: Direction Note + Survivor Metrics */}
                <div className="flex items-center justify-between gap-2 mt-0.5 text-xs">
                  {tunnel.missingDirection ? (
                    <Badge
                      variant="warning"
                      className="text-[10px] px-1 py-0 h-4 shrink-0 flex items-center gap-1 font-mono"
                    >
                      <AlertCircle className="h-2.5 w-2.5" />
                      <span>missing direction</span>
                    </Badge>
                  ) : (
                    <span className="text-[11px] text-text-tertiary">
                      bidirectional
                    </span>
                  )}

                  <div className="text-right tabular-nums">
                    <span
                      className={cn(
                        "font-medium",
                        tunnel.survivors.length > 0 ? "text-signal" : "text-text-tertiary"
                      )}
                    >
                      {tunnel.survivors.length}
                    </span>
                    <span className="text-text-tertiary text-[11px]">
                      {" "}/ {tunnel.universeSize}
                    </span>
                  </div>
                </div>

                {/* Mini Ratio Track */}
                <div className="w-full h-1 bg-surface-base rounded-data overflow-hidden mt-1 border border-border-hairline/60">
                  <div
                    className={cn(
                      "h-full transition-all duration-150",
                      isSelected ? "bg-signal" : "bg-signal-dim/70"
                    )}
                    style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                  />
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Keyboard Shortcut Hint Footer */}
      <div className="p-2 border-t border-border-hairline bg-surface-base text-[11px] text-text-tertiary flex items-center justify-between font-mono">
        <span>navigate:</span>
        <div className="flex items-center gap-1">
          <kbd className="px-1 py-0.5 rounded-data bg-surface-raised border border-border-hairline text-[10px] text-text-secondary">
            [
          </kbd>
          <kbd className="px-1 py-0.5 rounded-data bg-surface-raised border border-border-hairline text-[10px] text-text-secondary">
            ]
          </kbd>
        </div>
      </div>
    </div>
  );
};
