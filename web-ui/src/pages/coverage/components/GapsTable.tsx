import React, { useState, useMemo } from "react";
import { CoverageGapItem, tierLabel } from "@/api/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/vendor/table";
import { TierGlyph } from "@/components/app/TierGlyph";
import { Mono } from "@/components/app/Mono";
import { FilterBar } from "@/components/app/FilterBar";
import { getGapKindLabel, getGapKindDescription } from "./coverage-utils";
import { cn } from "@/lib/utils";

interface GapsTableProps {
  gaps: CoverageGapItem[];
  className?: string;
}

export const GapsTable: React.FC<GapsTableProps> = ({ gaps, className }) => {
  const [filterText, setFilterText] = useState("");

  const filteredGaps = useMemo(() => {
    if (!filterText.trim()) return gaps;
    const q = filterText.toLowerCase().trim();
    return gaps.filter((g) => {
      const idMatch = g.rule_id.toLowerCase().includes(q);
      const titleMatch = (g.title || "").toLowerCase().includes(q);
      const reasonMatch = (g.reason || "").toLowerCase().includes(q);
      const kindMatch = (g.gap_kind || "").toLowerCase().includes(q);
      return idMatch || titleMatch || reasonMatch || kindMatch;
    });
  }, [gaps, filterText]);

  if (gaps.length === 0) {
    return (
      <div className="p-8 text-center border border-border-hairline rounded-data bg-surface-panel font-mono text-xs text-text-tertiary">
        No individual coverage gap records listed in findings document.
      </div>
    );
  }

  return (
    <div className={cn("space-y-3 font-mono", className)}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <span className="text-xs text-text-tertiary">
          accounting for what the analyzer could not determine
        </span>
        <div className="w-full sm:w-64">
          <FilterBar
            value={filterText}
            onChange={setFilterText}
            placeholder="filter gaps..."
          />
        </div>
      </div>

      <div className="rounded-data border border-border-hairline bg-surface-panel overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-12 text-center text-text-tertiary text-[11px]">
                #
              </TableHead>
              <TableHead className="w-48 text-xs font-mono">rule id</TableHead>
              <TableHead className="w-56 text-xs font-mono">check title</TableHead>
              <TableHead className="w-48 text-xs font-mono">gap classification</TableHead>
              <TableHead className="w-44 text-xs font-mono">tier shortfall</TableHead>
              <TableHead className="text-xs font-mono min-w-[280px]">full reason</TableHead>
              <TableHead className="w-36 text-xs font-mono text-right">scope</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {filteredGaps.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-6 text-text-tertiary text-xs">
                  No gaps match "{filterText}".
                </TableCell>
              </TableRow>
            ) : (
              filteredGaps.map((gap, idx) => {
                const reqTier = gap.required_tier || "OBSERVED";
                const actTier = gap.actual_tier || "NOT_OBSERVABLE";
                const kindDesc = getGapKindDescription(gap.gap_kind);

                return (
                  <TableRow
                    key={`${gap.rule_id}-${idx}`}
                    className="hover:bg-surface-raised/40 transition-colors"
                  >
                    {/* Gutter */}
                    <TableCell className="text-center font-mono text-[11px] text-text-tertiary tabular-nums align-top py-3">
                      {String(idx + 1).padStart(2, "0")}
                    </TableCell>

                    {/* Rule ID */}
                    <TableCell className="font-mono text-xs align-top py-3">
                      <Mono value={gap.rule_id} copyable />
                    </TableCell>

                    {/* Check Title */}
                    <TableCell className="font-mono text-xs font-medium text-text-primary align-top py-3">
                      <span className="block leading-snug">
                        {gap.title || gap.rule_id}
                      </span>
                    </TableCell>

                    {/* Gap Classification */}
                    <TableCell className="align-top py-3">
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded-data text-[11px] font-mono bg-surface-base border border-border-hairline text-text-secondary"
                        title={kindDesc}
                      >
                        {getGapKindLabel(gap.gap_kind)}
                      </span>
                    </TableCell>

                    {/* Tier Shortfall (Two glyphs side-by-side) */}
                    <TableCell className="align-top py-3 font-mono">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <span
                            className="inline-flex items-center gap-1 text-signal text-xs"
                            title={`Required: ${reqTier}`}
                          >
                            <TierGlyph tier={reqTier} size={12} />
                            <span className="text-[11px] font-mono">{tierLabel(reqTier)}</span>
                          </span>
                          <span className="text-text-tertiary text-[11px]">→</span>
                          <span
                            className="inline-flex items-center gap-1 text-text-tertiary text-xs"
                            title={`Actual: ${actTier}`}
                          >
                            <TierGlyph tier={actTier} size={12} />
                            <span className="text-[11px] font-mono">{tierLabel(actTier)}</span>
                          </span>
                        </div>
                        <span className="text-[10px] text-text-tertiary">
                          light deficit
                        </span>
                      </div>
                    </TableCell>

                    {/* Full Reason (Easy to read prose) */}
                    <TableCell className="align-top py-3">
                      <div className="font-sans text-xs text-text-primary leading-relaxed max-w-xl select-text">
                        {gap.reason || "No explicit reason specified in gap document."}
                      </div>
                    </TableCell>

                    {/* Scope */}
                    <TableCell className="align-top py-3 text-right">
                      {gap.scope ? (
                        <Mono value={gap.scope} copyable className="text-[11px]" />
                      ) : (
                        <span className="text-text-tertiary text-xs">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};
