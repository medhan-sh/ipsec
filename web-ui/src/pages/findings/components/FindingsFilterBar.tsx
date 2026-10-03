import React, { useRef, useImperativeHandle, forwardRef } from "react";
import { ToggleGroup, ToggleGroupItem } from "@/components/vendor/toggle-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/vendor/select";
import { Button } from "@/components/vendor/button";
import { Severity } from "@/api/types";
import { cn } from "@/lib/utils";

export interface FindingsFilterBarRef {
  focusInput: () => void;
  clearInput: () => void;
}

interface FindingsFilterBarProps {
  filterText: string;
  onFilterTextChange: (value: string) => void;
  selectedSeverities: string[];
  onSeveritiesChange: (severities: string[]) => void;
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
  availableCategories: string[];
  severityCounts: Record<string, number>;
  categoryCounts: Record<string, number>;
  totalCount: number;
  filteredCount: number;
  onClearAll: () => void;
}

const SEVERITY_LEVELS: { key: Severity; label: string; short: string; color: string }[] = [
  { key: "CRITICAL", label: "Critical", short: "crit", color: "text-severity-critical" },
  { key: "HIGH", label: "High", short: "high", color: "text-severity-high" },
  { key: "MEDIUM", label: "Medium", short: "med", color: "text-severity-medium" },
  { key: "LOW", label: "Low", short: "low", color: "text-severity-low" },
  { key: "INFO", label: "Info", short: "info", color: "text-severity-info" },
];

export const FindingsFilterBar = forwardRef<FindingsFilterBarRef, FindingsFilterBarProps>(
  (
    {
      filterText,
      onFilterTextChange,
      selectedSeverities,
      onSeveritiesChange,
      selectedCategory,
      onCategoryChange,
      availableCategories,
      severityCounts,
      categoryCounts,
      totalCount,
      filteredCount,
      onClearAll,
    },
    ref
  ) => {
    const inputRef = useRef<HTMLInputElement>(null);
    const [isFocused, setIsFocused] = React.useState(false);

    useImperativeHandle(ref, () => ({
      focusInput: () => {
        inputRef.current?.focus();
        inputRef.current?.select();
      },
      clearInput: () => {
        onFilterTextChange("");
        inputRef.current?.blur();
      },
    }));

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Escape") {
        onFilterTextChange("");
        inputRef.current?.blur();
      }
    };

    const hasActiveFilters =
      filterText.trim().length > 0 ||
      selectedSeverities.length > 0 ||
      selectedCategory !== "all";

    return (
      <div className="space-y-2.5 font-mono text-xs">
        <div className="flex flex-col md:flex-row gap-2.5 items-stretch md:items-center justify-between">
          {/* Text filter with terminal discipline */}
          <div
            onClick={() => inputRef.current?.focus()}
            className={cn(
              "relative flex flex-1 h-8 items-center rounded-data border bg-surface-panel px-2.5 font-mono text-xs transition-colors",
              isFocused
                ? "border-signal ring-1 ring-signal shadow-focus"
                : "border-border-hairline hover:border-border-strong"
            )}
          >
            <span className="text-signal font-semibold mr-1.5 select-none">/</span>
            <input
              ref={inputRef}
              type="text"
              value={filterText}
              onChange={(e) => onFilterTextChange(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="filter findings (/ to focus, esc to clear)..."
              className="w-full bg-transparent text-text-primary placeholder:text-text-tertiary focus:outline-none"
            />
            {isFocused && (
              <span className="inline-block w-1.5 h-3.5 bg-signal terminal-caret ml-0.5 select-none" />
            )}
            {filterText && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onFilterTextChange("");
                }}
                className="text-text-tertiary hover:text-text-primary ml-1 text-[10px] select-none"
                title="Clear filter text (Esc)"
              >
                [esc]
              </button>
            )}
          </div>

          {/* Category Dropdown Filter */}
          {availableCategories.length > 0 && (
            <div className="w-full md:w-52 shrink-0">
              <Select value={selectedCategory} onValueChange={onCategoryChange}>
                <SelectTrigger className="h-8 text-xs">
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="text-text-tertiary">cat:</span>
                    <SelectValue placeholder="All categories" />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    <span>all categories ({totalCount})</span>
                  </SelectItem>
                  {availableCategories.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      <span>
                        {cat} ({categoryCounts[cat] ?? 0})
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        {/* Second Row: Severity Toggle Group & Filter State Status */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-text-tertiary select-none">severity:</span>
            <ToggleGroup
              type="multiple"
              value={selectedSeverities}
              onValueChange={onSeveritiesChange}
              className="bg-surface-panel"
            >
              {SEVERITY_LEVELS.map(({ key, short, color }) => {
                const count = severityCounts[key] ?? 0;
                const isSelected = selectedSeverities.includes(key);
                return (
                  <ToggleGroupItem
                    key={key}
                    value={key}
                    className={cn(
                      "px-2 py-0.5 text-[11px] gap-1.5 transition-colors",
                      isSelected && "bg-surface-raised border border-border-strong text-text-primary"
                    )}
                    title={`Filter by ${key} severity (${count} finding${count === 1 ? "" : "s"})`}
                  >
                    <span className={cn("font-semibold uppercase tracking-wider", color)}>
                      {short}
                    </span>
                    <span className="text-text-tertiary tabular-nums text-[10px]">
                      {count}
                    </span>
                  </ToggleGroupItem>
                );
              })}
            </ToggleGroup>
          </div>

          {/* Filter Status Summary & Reset */}
          <div className="flex items-center gap-2 ml-auto text-[11px] text-text-secondary select-none">
            <span>
              showing <strong className="text-text-primary tabular-nums">{filteredCount}</strong> of{" "}
              <span className="tabular-nums">{totalCount}</span>
            </span>

            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClearAll}
                className="h-6 px-1.5 text-[11px] text-signal hover:text-signal hover:bg-surface-raised"
              >
                reset filters
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }
);

FindingsFilterBar.displayName = "FindingsFilterBar";
