import React, { useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  ColumnDef,
  flexRender,
} from "@tanstack/react-table";
import { PassedCheckItem, RuleMeta, tierOrder } from "@/api/types";
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
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

interface PassesTableProps {
  passes: PassedCheckItem[];
  rules: Record<string, RuleMeta>;
  selectedPassIndex: number | null;
  onSelectRow: (index: number, pass: PassedCheckItem) => void;
  onOpenDrawer: (pass: PassedCheckItem) => void;
  sorting: SortingState;
  onSortingChange: React.Dispatch<React.SetStateAction<SortingState>>;
}

export const PassesTable: React.FC<PassesTableProps> = ({
  passes,
  rules,
  selectedPassIndex,
  onSelectRow,
  onOpenDrawer,
  sorting,
  onSortingChange,
}) => {
  const columns = useMemo<ColumnDef<PassedCheckItem>[]>(
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
        accessorKey: "title",
        header: ({ column }) => {
          const isSorted = column.getIsSorted();
          return (
            <button
              type="button"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              className="flex items-center gap-1.5 hover:text-text-primary transition-colors text-left font-mono"
            >
              <span>Evaluated Check</span>
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
          const pass = info.row.original;
          const ruleMeta = rules[pass.rule_id];
          const displayTitle =
            pass.title || ruleMeta?.passed_title || ruleMeta?.title || pass.rule_id;

          return (
            <div className="space-y-0.5 py-0.5 max-w-xl">
              <div className="text-text-primary font-medium hover:text-signal transition-colors">
                {displayTitle}
              </div>
              <div className="text-[10px] text-text-tertiary font-mono">
                {pass.rule_id}
              </div>
            </div>
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
              <span>Passed Tier</span>
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
          const scope = info.getValue() as string | undefined;
          if (!scope) return <span className="text-text-tertiary">—</span>;
          return <Mono value={scope} copyable className="text-[11px]" />;
        },
      },
      {
        id: "evidence",
        header: () => <span>Evidence Frames</span>,
        enableSorting: false,
        cell: (info) => {
          const evidence = info.row.original.evidence;
          if (!evidence || evidence.length === 0) {
            return <span className="text-text-tertiary">—</span>;
          }
          return (
            <div className="flex flex-wrap gap-1">
              {evidence.map((f) => (
                <Mono key={f} label="frame" value={f} copyable className="text-[10px]" />
              ))}
            </div>
          );
        },
      },
    ],
    [rules]
  );

  const table = useReactTable({
    data: passes,
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
        <Table className="min-w-[650px] w-full">
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
                const isSelected = selectedPassIndex === index;
                const pass = row.original;

                return (
                  <TableRow
                    key={row.id}
                    selected={isSelected}
                    onClick={() => {
                      onSelectRow(index, pass);
                      onOpenDrawer(pass);
                    }}
                    className="cursor-pointer transition-colors text-xs hover:bg-surface-raised/50"
                    title="Click or press Enter to inspect pass details"
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
                  No passed checks recorded for this capture.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};
