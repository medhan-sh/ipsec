import React, { useState, useMemo } from "react";
import { EliminationReasonGroup } from "../types";
import { Mono } from "@/components/app/Mono";
import { Badge } from "@/components/vendor/badge";
import { Button } from "@/components/vendor/button";
import { Input } from "@/components/vendor/input";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/vendor/collapsible";
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Layers,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface EliminatedCandidatesProps {
  groups: EliminationReasonGroup[];
  selectedGroupId?: string | null;
  onSelectGroup?: (groupId: string | null) => void;
}

const PAGE_SIZE = 25;

export const EliminatedCandidates: React.FC<EliminatedCandidatesProps> = ({
  groups,
  selectedGroupId,
  onSelectGroup,
}) => {
  const [openGroupIds, setOpenGroupIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [pageByGroup, setPageByGroup] = useState<Record<string, number>>({});

  // When a group is selected externally (e.g. from the staged bar), expand it
  React.useEffect(() => {
    if (selectedGroupId) {
      setOpenGroupIds((prev) => new Set([...prev, selectedGroupId]));
      // Scroll into view
      const elem = document.getElementById(selectedGroupId);
      if (elem) {
        elem.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [selectedGroupId]);

  const toggleGroup = (id: string) => {
    setOpenGroupIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleExpandAll = () => {
    setOpenGroupIds(new Set(groups.map((g) => g.id)));
  };

  const handleCollapseAll = () => {
    setOpenGroupIds(new Set());
    onSelectGroup?.(null);
  };

  const handleCopyAll = () => {
    const all = groups.flatMap((g) => g.candidates);
    navigator.clipboard.writeText(all.join("\n"));
    toast.success(`Copied ${all.length} eliminated candidates to clipboard`);
  };

  // Filter groups and candidates by search query
  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) return groups;
    const q = searchQuery.toLowerCase();
    return groups
      .map((g) => {
        const matchesReason = g.reason.toLowerCase().includes(q);
        const matchedCandidates = g.candidates.filter((c) =>
          c.toLowerCase().includes(q)
        );
        if (matchesReason) return g;
        return {
          ...g,
          candidates: matchedCandidates,
          count: matchedCandidates.length,
        };
      })
      .filter((g) => g.candidates.length > 0);
  }, [groups, searchQuery]);

  const totalEliminated = groups.reduce((acc, g) => acc + g.count, 0);

  return (
    <div className="rounded-data border border-border-hairline bg-surface-panel p-4 space-y-4 font-mono">
      {/* Header and Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-hairline">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-[#ff4d5e]" />
          <span className="text-xs uppercase tracking-wider text-text-secondary font-semibold">
            eliminated candidate suites
          </span>
          <span className="text-xs text-text-tertiary tabular-nums">
            ({totalEliminated} eliminated across {groups.length} criteria)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExpandAll}
            className="h-7 text-[11px] text-text-secondary hover:text-text-primary"
          >
            expand all
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCollapseAll}
            className="h-7 text-[11px] text-text-secondary hover:text-text-primary"
          >
            collapse all
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyAll}
            className="h-7 text-[11px] text-text-secondary hover:text-text-primary"
            title="Copy all eliminated candidate names"
          >
            <Copy className="h-3 w-3 mr-1" />
            copy all
          </Button>
        </div>
      </div>

      {/* Search Filter for eliminated candidates */}
      {totalEliminated > 10 && (
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-text-tertiary pointer-events-none" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="filter eliminated suites by name or elimination reason..."
            className="h-8 pl-8 pr-3 text-xs font-mono bg-surface-base border-border-hairline"
          />
        </div>
      )}

      {/* Reason Groups (Collapsed by default) */}
      <div className="space-y-3">
        {filteredGroups.length === 0 ? (
          <div className="p-4 text-center text-xs text-text-tertiary">
            {totalEliminated === 0
              ? "No candidate suites were eliminated for this tunnel."
              : "No eliminated suites match filter criteria."}
          </div>
        ) : (
          filteredGroups.map((group) => {
            const isOpen = openGroupIds.has(group.id);
            const isHighlighted = selectedGroupId === group.id;
            const currentPage = pageByGroup[group.id] || 1;
            const totalPages = Math.ceil(group.candidates.length / PAGE_SIZE);
            const startIndex = (currentPage - 1) * PAGE_SIZE;
            const paginatedCandidates = group.candidates.slice(
              startIndex,
              startIndex + PAGE_SIZE
            );

            return (
              <Collapsible
                key={group.id}
                open={isOpen}
                onOpenChange={() => toggleGroup(group.id)}
                id={group.id}
                className={cn(
                  "rounded-data border transition-colors bg-surface-base overflow-hidden",
                  isHighlighted
                    ? "border-[#ff4d5e] shadow-[0_0_8px_rgba(255,77,94,0.15)]"
                    : "border-border-hairline hover:border-border-strong"
                )}
              >
                <CollapsibleTrigger asChild>
                  <button
                    type="button"
                    className="w-full flex items-start justify-between gap-3 p-3 text-left hover:bg-surface-raised transition-colors group select-none"
                  >
                    <div className="flex items-start gap-2.5 min-w-0">
                      <span className="mt-0.5 text-text-tertiary group-hover:text-text-primary transition-colors">
                        {isOpen ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </span>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-text-primary">
                            {group.shortLabel}
                          </span>
                          <span className="text-[10px] text-text-tertiary">
                            (click to {isOpen ? "collapse" : "expand"})
                          </span>
                        </div>
                        <p className="text-xs text-text-secondary font-sans leading-relaxed">
                          {group.reason}
                        </p>
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className="text-[11px] tabular-nums font-mono border-[#ff4d5e]/40 text-[#ff8a3d]"
                      >
                        -{group.count} suites
                      </Badge>
                    </div>
                  </button>
                </CollapsibleTrigger>

                <CollapsibleContent className="border-t border-border-hairline p-3 bg-surface-panel space-y-3">
                  {/* Candidates Monospace Grid */}
                  <div className="flex flex-wrap gap-1.5">
                    {paginatedCandidates.map((suite) => (
                      <Mono
                        key={suite}
                        value={suite}
                        copyable
                        className="text-xs border-border-hairline text-text-primary bg-surface-raised"
                      />
                    ))}
                  </div>

                  {/* Pagination Controls for large candidate sets */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between pt-2 border-t border-border-hairline text-xs text-text-secondary">
                      <span className="tabular-nums">
                        Showing {startIndex + 1}–
                        {Math.min(startIndex + PAGE_SIZE, group.candidates.length)} of{" "}
                        {group.candidates.length} suites
                      </span>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={currentPage <= 1}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPageByGroup((prev) => ({
                              ...prev,
                              [group.id]: currentPage - 1,
                            }));
                          }}
                          className="h-6 px-2 text-[11px]"
                        >
                          prev
                        </Button>
                        <span className="tabular-nums">
                          {currentPage} / {totalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={currentPage >= totalPages}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPageByGroup((prev) => ({
                              ...prev,
                              [group.id]: currentPage + 1,
                            }));
                          }}
                          className="h-6 px-2 text-[11px]"
                        >
                          next
                        </Button>
                      </div>
                    </div>
                  )}
                </CollapsibleContent>
              </Collapsible>
            );
          })
        )}
      </div>
    </div>
  );
};
