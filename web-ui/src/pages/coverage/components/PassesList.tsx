import React from "react";
import { PassedCheckItem } from "@/api/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/vendor/table";
import { TierBadge } from "@/components/app/TierBadge";
import { Mono } from "@/components/app/Mono";
import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface PassesListProps {
  passes: PassedCheckItem[];
  className?: string;
}

export const PassesList: React.FC<PassesListProps> = ({ passes, className }) => {
  if (passes.length === 0) {
    return (
      <div className="p-6 text-center border border-border-hairline rounded-data bg-surface-panel font-mono text-xs text-text-tertiary">
        Zero rules evaluated clean as passed checks in this capture.
      </div>
    );
  }

  return (
    <div className={cn("rounded-data border border-border-hairline bg-surface-panel overflow-hidden font-mono", className)}>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-12 text-center text-text-tertiary text-[11px]">
              #
            </TableHead>
            <TableHead className="w-48 text-xs font-mono">rule id</TableHead>
            <TableHead className="text-xs font-mono min-w-[240px]">check passed</TableHead>
            <TableHead className="w-40 text-xs font-mono">basis tier</TableHead>
            <TableHead className="w-44 text-xs font-mono">evidence</TableHead>
            <TableHead className="w-36 text-xs font-mono text-right">scope</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {passes.map((passItem, idx) => {
            return (
              <TableRow
                key={`${passItem.rule_id}-${idx}`}
                className="hover:bg-surface-raised/40 transition-colors"
              >
                {/* Gutter */}
                <TableCell className="text-center font-mono text-[11px] text-text-tertiary tabular-nums py-2">
                  {String(idx + 1).padStart(2, "0")}
                </TableCell>

                {/* Rule ID */}
                <TableCell className="py-2">
                  <Mono value={passItem.rule_id} copyable />
                </TableCell>

                {/* Title */}
                <TableCell className="py-2 font-mono text-xs text-text-primary">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-signal shrink-0" />
                    <span>{passItem.title || passItem.rule_id}</span>
                  </div>
                </TableCell>

                {/* Tier */}
                <TableCell className="py-2">
                  <TierBadge tier={passItem.tier} />
                </TableCell>

                {/* Evidence */}
                <TableCell className="py-2 font-mono text-xs">
                  {passItem.evidence && passItem.evidence.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {passItem.evidence.map((f) => (
                        <Mono key={f} label="frame" value={f} />
                      ))}
                    </div>
                  ) : (
                    <span className="text-text-tertiary">—</span>
                  )}
                </TableCell>

                {/* Scope */}
                <TableCell className="py-2 text-right">
                  {passItem.scope ? (
                    <Mono value={passItem.scope} copyable className="text-[11px]" />
                  ) : (
                    <span className="text-text-tertiary text-xs">—</span>
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
