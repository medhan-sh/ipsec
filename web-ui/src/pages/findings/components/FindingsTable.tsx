import React, { useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  ColumnDef,
  flexRender,
} from "@tanstack/react-table";
import { FindingItem, tierOrder } from "@/api/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/vendor/table";
import { SeverityChip } from "@/components/app/SeverityChip";
import { TierBadge } from "@/components/app/TierBadge";
import { Mono } from "@/components/app/Mono";
import { Button } from "@/components/vendor/button";
import { cn } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

interface FindingsTableProps {
  findings: FindingItem[];
  selectedFindingIndex: number | null;
  onSelectRow: (index: number, finding: FindingItem) => void;
  onOpenDrawer: (finding: FindingItem) => void;
  sorting: SortingState;
  onSortingChange: React.Dispatch<React.SetStateAction<SortingState>>;
  onClearFilters?: () => void;
}

const SEVERITY_RANKS: Record<string, number> = {
  CRITICAL: 5,
  HIGH: 4,
  MEDIUM: 3,
  LOW: 2,
  INFO: 1,
};

function getSeverityBorderClass(sev: string): string {
  switch (sev.toUpperCase()) {
    case "CRITICAL":
      return "border-l-2 border-l-severity-critical";
    case "HIGH":
      return "border-l-2 border-l-severity-high";
    case "MEDIUM":
      return "border-l-2 border-l-severity-medium";
    case "LOW":
      return "border-l-2 border-l-severity-low";
    case "INFO":
      return "border-l-2 border-l-severity-info";
    default:
      return "border-l-2 border-l-border-hairline";
  }
}

export const FindingsTable: React.FC<FindingsTableProps> = ({
  findings,
  selectedFindingIndex,
  onSelectRow,
  onOpenDrawer,
  sorting,
  onSortingChange,
  onClearFilters,
}) => {
  const columns = useMemo<ColumnDef<FindingItem>[]>(
    () => [
      {
        id: "gutter",
        header: () => <span className="w-12 block text-center text-text-tertiary select-none">#</span>,
        cell: (info) => (
          <span className="w-12 block text-center text-text-tertiary font-mono select-none">
            {info.row.index + 1}
          </span>
        ),
        enableSorting: false,
        size: 48,
      },
      {
        accessorKey: "severity",
        header: ({ column }) => {
          const isSorted = column.getIsSorted();
          return (
            <button
              type="button"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="flex items-center gap-1.5 hover:text-text-primary transition-colors text-left font-mono"
            >
              <span>Severity</span>
              {isSorted === "asc" ? (
                <ArrowUp className="h-3 w-3 text-signal" />
              ) : isSorted === "desc" ? (
                <ArrowDown className="h-3 w-3 text-signal" />
              ) : (
                <ArrowUpDown className="h-3 w-3 text-text-tertiary opacity-40 hover:opacity-100" />
              )}
            </button>
          );
        },
        cell: (info) => (
          <div className="flex items-center">
            <SeverityChip severity={info.getValue() as string} />
          </div>
        ),
        sortingFn: (rowA, rowB) => {
          const rankA = SEVERITY_RANKS[String(rowA.original.severity).toUpperCase()] ?? 0;
          const rankB = SEVERITY_RANKS[String(rowB.original.severity).toUpperCase()] ?? 0;
          return rankA - rankB;
        },
      },
      {
        accessorKey: "title",
        header: ({ column }) => {
          const isSorted = column.getIsSorted();
          return (
            <button
              type="button"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="flex items-center gap-1.5 hover:text-text-primary transition-colors text-left font-mono"
            >
              <span>Finding / Rule</span>
              {isSorted === "asc" ? (
                <ArrowUp className="h-3 w-3 text-signal" />
              ) : isSorted === "desc" ? (
                <ArrowDown className="h-3 w-3 text-signal" />
              ) : (
                <ArrowUpDown className="h-3 w-3 text-text-tertiary opacity-40 hover:opacity-100" />
              )}
            </button>
          );
        },
        cell: (info) => {
          const finding = info.row.original;
          return (
            <div className="space-y-0.5 max-w-xl py-0.5">
              <div className="text-text-primary font-medium hover:text-signal transition-colors">
                {finding.title}
              </div>
              <div className="text-[10px] text-text-tertiary font-mono">
                {finding.rule_id}
              </div>
            </div>
          );
        },
      },
      {
        accessorKey: "category",
        header: ({ column }) => {
          const isSorted = column.getIsSorted();
          return (
            <button
              type="button"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="flex items-center gap-1.5 hover:text-text-primary transition-colors text-left font-mono"
            >
              <span>Category</span>
              {isSorted === "asc" ? (
                <ArrowUp className="h-3 w-3 text-signal" />
              ) : isSorted === "desc" ? (
                <ArrowDown className="h-3 w-3 text-signal" />
              ) : (
                <ArrowUpDown className="h-3 w-3 text-text-tertiary opacity-40 hover:opacity-100" />
              )}
            </button>
          );
        },
        cell: (info) => {
          const cat = info.getValue() as string | undefined;
          if (!cat) return <span className="text-text-tertiary">—</span>;
          return (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded-data text-[10px] font-mono border border-border-hairline bg-surface-raised text-text-secondary uppercase tracking-wider">
              {cat}
            </span>
          );
        },
      },
      {
        accessorKey: "tier",
        header: ({ column }) => {
          const isSorted = column.getIsSorted();
          return (
            <button
              type="button"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="flex items-center gap-1.5 hover:text-text-primary transition-colors text-left font-mono"
            >
              <span>Evidence Tier</span>
              {isSorted === "asc" ? (
                <ArrowUp className="h-3 w-3 text-signal" />
              ) : isSorted === "desc" ? (
                <ArrowDown className="h-3 w-3 text-signal" />
              ) : (
                <ArrowUpDown className="h-3 w-3 text-text-tertiary opacity-40 hover:opacity-100" />
              )}
            </button>
          );
        },
        cell: (info) => <TierBadge tier={info.getValue() as string} />,
        sortingFn: (rowA, rowB) => {
          return tierOrder(rowA.original.tier) - tierOrder(rowB.original.tier);
        },
      },
      {
        accessorKey: "scope",
        header: ({ column }) => {
          const isSorted = column.getIsSorted();
          return (
            <button
              type="button"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="flex items-center gap-1.5 hover:text-text-primary transition-colors text-left font-mono"
            >
              <span>Scope</span>
              {isSorted === "asc" ? (
                <ArrowUp className="h-3 w-3 text-signal" />
              ) : isSorted === "desc" ? (
                <ArrowDown className="h-3 w-3 text-signal" />
              ) : (
                <ArrowUpDown className="h-3 w-3 text-text-tertiary opacity-40 hover:opacity-100" />
              )}
            </button>
          );
        },
        cell: (info) => {
          const scope = info.getValue() as string;
          return <Mono value={scope} copyable className="text-[11px]" />;
        },
      },
    ],
    []
  );

  const table = useReactTable({
    data: findings,
    columns,
    state: { sorting },
    onSortingChange,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const rows = table.getRowModel().rows;

  return (
    <div className="border border-border-hairline rounded-data overflow-hidden bg-surface-panel shadow-sm">
      <div className="max-h-[calc(100vh-270px)] overflow-auto">
        <Table className="min-w-[720px] w-full">
          <TableHeader className="bg-surface-panel sticky top-0 z-10 border-b border-border-hairline">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="border-b border-border-hairline hover:bg-surface-panel">
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className="h-9 px-3 text-text-secondary font-mono text-xs uppercase tracking-wider select-none bg-surface-panel"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {rows.length > 0 ? (
              rows.map((row, index) => {
                const isSelected = selectedFindingIndex === index;
                const finding = row.original;
                const severityBorder = getSeverityBorderClass(finding.severity);

                return (
                  <TableRow
                    key={row.id}
                    selected={isSelected}
                    onClick={() => {
                      onSelectRow(index, finding);
                      onOpenDrawer(finding);
                    }}
                    className={cn(
                      "cursor-pointer transition-colors text-xs",
                      !isSelected && severityBorder
                    )}
                    title="Click or press Enter to inspect finding details"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="p-2.5 px-3">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-32 text-center text-text-tertiary font-mono"
                >
                  <div className="space-y-2">
                    <p>No findings match the current filter criteria.</p>
                    {onClearFilters && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={onClearFilters}
                        className="text-xs"
                      >
                        Reset filters
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};
