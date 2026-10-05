import React, { useState } from "react";
import { ClaimItem, Tier } from "@/api/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/vendor/table";
import { TierBadge } from "@/components/app/TierBadge";
import { ConfidenceMeter } from "@/components/app/ConfidenceMeter";
import { Mono } from "@/components/app/Mono";
import { AlertTriangle, ChevronDown, ChevronRight, Layers } from "lucide-react";
import { formatClaimValue, GroupedClaim } from "./claims-utils";
import { cn } from "@/lib/utils";

interface ClaimsTableProps {
  claims: ClaimItem[];
  groupedClaims: GroupedClaim[];
  groupByField: boolean;
  selectedIndex: number;
  onSelectIndex: (idx: number) => void;
  onOpenClaimDrawer: (claim: ClaimItem, group?: ClaimItem[]) => void;
  className?: string;
}

export const ClaimsTable: React.FC<ClaimsTableProps> = ({
  claims,
  groupedClaims,
  groupByField,
  selectedIndex,
  onSelectIndex,
  onOpenClaimDrawer,
  className,
}) => {
  // Track expanded evidence frames per row index
  const [expandedEvidence, setExpandedEvidence] = useState<Record<number, boolean>>({});

  const toggleEvidence = (e: React.MouseEvent, idx: number) => {
    e.stopPropagation();
    setExpandedEvidence((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const renderConfidence = (tier: Tier | string, confidence: number | null) => {
    if (tier === "OBSERVED") {
      return <span className="font-mono text-xs text-signal font-medium">certain</span>;
    }
    if (tier === "NOT_OBSERVABLE") {
      return <span className="font-mono text-xs text-text-tertiary">— not observable</span>;
    }
    if (confidence === null) {
      return <span className="font-mono text-xs text-text-tertiary">n/a</span>;
    }
    return <ConfidenceMeter tier={tier} confidence={confidence} />;
  };

  const rowCount = groupByField ? groupedClaims.length : claims.length;

  if (rowCount === 0) {
    return (
      <div className="p-8 text-center border border-border-hairline rounded-data bg-surface-panel font-mono text-xs text-text-tertiary">
        No claims match the active filter criteria.
      </div>
    );
  }

  return (
    <div className={cn("rounded-data border border-border-hairline bg-surface-panel overflow-hidden", className)}>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-10 text-center text-text-tertiary font-mono text-[11px]">
              #
            </TableHead>
            <TableHead className="w-44 font-mono text-xs">field</TableHead>
            <TableHead className="w-36 font-mono text-xs">value</TableHead>
            <TableHead className="w-32 font-mono text-xs">tier</TableHead>
            <TableHead className="w-28 font-mono text-xs">confidence</TableHead>
            <TableHead className="font-mono text-xs min-w-[180px]">method</TableHead>
            <TableHead className="w-28 font-mono text-xs">evidence</TableHead>
            <TableHead className="w-20 font-mono text-xs text-right">caveats</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {groupByField
            ? groupedClaims.map((group, idx) => {
                const isSelected = selectedIndex === idx;
                const isEvidenceExpanded = Boolean(expandedEvidence[idx]);

                return (
                  <TableRow
                    key={group.field}
                    selected={isSelected}
                    onClick={() => {
                      onSelectIndex(idx);
                      onOpenClaimDrawer(group.claims[0], group.claims);
                    }}
                    className="cursor-pointer group select-none"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        onOpenClaimDrawer(group.claims[0], group.claims);
                      }
                    }}
                  >
                    {/* Gutter */}
                    <TableCell className="text-center font-mono text-[11px] text-text-tertiary tabular-nums py-2.5">
                      {String(idx + 1).padStart(2, "0")}
                    </TableCell>

                    {/* Field & Occurrences Badge */}
                    <TableCell className="py-2.5 font-mono text-xs font-medium text-text-primary">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate" title={group.field}>
                          {group.field}
                        </span>
                        {group.occurrences > 1 && (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-data bg-surface-raised border border-border-hairline text-[10px] text-signal font-mono font-normal">
                            <Layers className="h-2.5 w-2.5" />
                            <span>×{group.occurrences}</span>
                          </span>
                        )}
                      </div>
                    </TableCell>

                    {/* Value Summary */}
                    <TableCell className="py-2.5 font-mono text-xs text-text-secondary">
                      {group.distinctValues.length === 1 ? (
                        <span className="truncate block" title={group.distinctValues[0]}>
                          {group.distinctValues[0]}
                        </span>
                      ) : (
                        <span className="text-text-primary text-[11px] font-mono">
                          {group.distinctValues.length} distinct values
                        </span>
                      )}
                    </TableCell>

                    {/* Tier */}
                    <TableCell className="py-2.5">
                      <div className="flex items-center gap-1 flex-wrap">
                        {group.tiers.map((t) => (
                          <TierBadge key={t} tier={t} showLabel={group.tiers.length === 1} />
                        ))}
                      </div>
                    </TableCell>

                    {/* Confidence */}
                    <TableCell className="py-2.5">
                      {group.tiers.length === 1 ? (
                        renderConfidence(group.tiers[0], group.claims[0].confidence)
                      ) : (
                        <span className="text-text-tertiary font-mono text-xs">mixed</span>
                      )}
                    </TableCell>

                    {/* Method */}
                    <TableCell className="py-2.5 font-sans text-xs text-text-secondary">
                      <div className="truncate max-w-sm" title={group.claims[0].method}>
                        {group.claims.length === 1
                          ? group.claims[0].method
                          : `${group.claims[0].method} (+${group.claims.length - 1} more)`}
                      </div>
                    </TableCell>

                    {/* Evidence (Expandable) */}
                    <TableCell className="py-2.5 font-mono text-xs">
                      {group.uniqueEvidence.length > 0 ? (
                        <div className="space-y-1">
                          <button
                            type="button"
                            onClick={(e) => toggleEvidence(e, idx)}
                            className="inline-flex items-center gap-1 text-[11px] text-text-secondary hover:text-signal transition-colors rounded-data px-1.5 py-0.5 bg-surface-base border border-border-hairline"
                          >
                            {isEvidenceExpanded ? (
                              <ChevronDown className="h-3 w-3 text-signal" />
                            ) : (
                              <ChevronRight className="h-3 w-3 text-text-tertiary" />
                            )}
                            <span className="tabular-nums">{group.uniqueEvidence.length}</span>
                            <span>{group.uniqueEvidence.length === 1 ? "frame" : "frames"}</span>
                          </button>

                          {isEvidenceExpanded && (
                            <div className="flex flex-wrap gap-1 pt-1 max-w-[220px]">
                              {group.uniqueEvidence.map((f) => (
                                <Mono key={f} label="frame" value={f} />
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-text-tertiary text-xs">—</span>
                      )}
                    </TableCell>

                    {/* Caveats */}
                    <TableCell className="py-2.5 text-right font-mono text-xs">
                      {group.totalCaveatsCount > 0 ? (
                        <span className="inline-flex items-center gap-1 font-mono text-xs text-amber-sample font-medium bg-amber-sample/10 border border-amber-sample/40 px-1.5 py-0.5 rounded-data">
                          <AlertTriangle className="h-3 w-3" />
                          <span>{group.totalCaveatsCount}</span>
                        </span>
                      ) : (
                        <span className="text-text-tertiary">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            : claims.map((claim, idx) => {
                const isSelected = selectedIndex === idx;
                const isEvidenceExpanded = Boolean(expandedEvidence[idx]);
                const displayVal = formatClaimValue(claim.value, claim.tier);
                const caveatsCount = claim.caveats?.length || 0;

                return (
                  <TableRow
                    key={`${claim.field}-${idx}`}
                    selected={isSelected}
                    onClick={() => {
                      onSelectIndex(idx);
                      onOpenClaimDrawer(claim);
                    }}
                    className="cursor-pointer group select-none"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        onOpenClaimDrawer(claim);
                      }
                    }}
                  >
                    {/* Gutter */}
                    <TableCell className="text-center font-mono text-[11px] text-text-tertiary tabular-nums py-2.5">
                      {String(idx + 1).padStart(2, "0")}
                    </TableCell>

                    {/* Field */}
                    <TableCell className="py-2.5 font-mono text-xs font-medium text-text-primary">
                      <span className="truncate block" title={claim.field}>
                        {claim.field}
                      </span>
                    </TableCell>

                    {/* Value */}
                    <TableCell className="py-2.5 font-mono text-xs text-text-secondary">
                      <span className="truncate block max-w-[180px]" title={displayVal}>
                        {displayVal}
                      </span>
                    </TableCell>

                    {/* Tier */}
                    <TableCell className="py-2.5">
                      <TierBadge tier={claim.tier} />
                    </TableCell>

                    {/* Confidence */}
                    <TableCell className="py-2.5">
                      {renderConfidence(claim.tier, claim.confidence)}
                    </TableCell>

                    {/* Method */}
                    <TableCell className="py-2.5 font-sans text-xs text-text-secondary">
                      <div className="truncate max-w-sm" title={claim.method}>
                        {claim.method}
                      </div>
                    </TableCell>

                    {/* Evidence (Expandable) */}
                    <TableCell className="py-2.5 font-mono text-xs">
                      {claim.evidence && claim.evidence.length > 0 ? (
                        <div className="space-y-1">
                          <button
                            type="button"
                            onClick={(e) => toggleEvidence(e, idx)}
                            className="inline-flex items-center gap-1 text-[11px] text-text-secondary hover:text-signal transition-colors rounded-data px-1.5 py-0.5 bg-surface-base border border-border-hairline"
                          >
                            {isEvidenceExpanded ? (
                              <ChevronDown className="h-3 w-3 text-signal" />
                            ) : (
                              <ChevronRight className="h-3 w-3 text-text-tertiary" />
                            )}
                            <span className="tabular-nums">{claim.evidence.length}</span>
                            <span>{claim.evidence.length === 1 ? "frame" : "frames"}</span>
                          </button>

                          {isEvidenceExpanded && (
                            <div className="flex flex-wrap gap-1 pt-1 max-w-[220px]">
                              {claim.evidence.map((f) => (
                                <Mono key={f} label="frame" value={f} />
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-text-tertiary text-xs">—</span>
                      )}
                    </TableCell>

                    {/* Caveats */}
                    <TableCell className="py-2.5 text-right font-mono text-xs">
                      {caveatsCount > 0 ? (
                        <span
                          className="inline-flex items-center gap-1 font-mono text-xs text-amber-sample font-medium bg-amber-sample/10 border border-amber-sample/40 px-1.5 py-0.5 rounded-data"
                          title={claim.caveats.join(" | ")}
                        >
                          <AlertTriangle className="h-3 w-3" />
                          <span>{caveatsCount}</span>
                        </span>
                      ) : (
                        <span className="text-text-tertiary">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
        </TableBody>
      </Table>
    </div>
  );
};
