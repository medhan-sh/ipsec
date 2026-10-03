import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/vendor/tabs";
import { SortingState } from "@tanstack/react-table";
import { FindingItem, PassedCheckItem } from "@/api/types";
import { FindingsFilterBar, FindingsFilterBarRef } from "./components/FindingsFilterBar";
import { FindingsTable } from "./components/FindingsTable";
import { PassesTable } from "./components/PassesTable";
import { FindingDetailDrawer } from "./components/FindingDetailDrawer";
import { PassDetailDrawer } from "./components/PassDetailDrawer";
import { ZeroFindingsCard } from "./components/ZeroFindingsCard";

export const FindingsPage: React.FC = () => {
  const { state, analyzeSelected, loadSampleData } = useAppStore();
  const [searchParams, setSearchParams] = useSearchParams();

  // Filter Bar ref for '/' key shortcut focus
  const filterBarRef = useRef<FindingsFilterBarRef>(null);

  // Local and URL state synchronization
  const [activeTab, setActiveTab] = useState<string>(() => {
    return searchParams.get("tab") === "passes" ? "passes" : "findings";
  });
  const [filterText, setFilterText] = useState<string>(() => {
    return searchParams.get("q") || "";
  });
  const [selectedCategory, setSelectedCategory] = useState<string>(() => {
    return searchParams.get("category") || "all";
  });
  const [selectedSeverities, setSelectedSeverities] = useState<string[]>(() => {
    const raw = searchParams.get("severity");
    return raw ? raw.split(",").filter(Boolean) : [];
  });
  const deepSelectedRuleId = searchParams.get("selected");

  // Keep local state in sync if URL search params change externally
  useEffect(() => {
    const paramTab = searchParams.get("tab") === "passes" ? "passes" : "findings";
    setActiveTab(paramTab);

    const paramQ = searchParams.get("q") || "";
    setFilterText(paramQ);

    const paramCat = searchParams.get("category") || "all";
    setSelectedCategory(paramCat);

    const rawSev = searchParams.get("severity");
    setSelectedSeverities(rawSev ? rawSev.split(",").filter(Boolean) : []);
  }, [searchParams]);

  // Local Selection and Drawer State
  const [selectedFindingIndex, setSelectedFindingIndex] = useState<number | null>(null);
  const [selectedPassIndex, setSelectedPassIndex] = useState<number | null>(null);
  const [activeFinding, setActiveFinding] = useState<FindingItem | null>(null);
  const [activePass, setActivePass] = useState<PassedCheckItem | null>(null);
  const [findingDrawerOpen, setFindingDrawerOpen] = useState(false);
  const [passDrawerOpen, setPassDrawerOpen] = useState(false);

  // Sorting state (default: severity desc, title asc)
  const [findingsSorting, setFindingsSorting] = useState<SortingState>([
    { id: "severity", desc: true },
    { id: "title", desc: false },
  ]);
  const [passesSorting, setPassesSorting] = useState<SortingState>([
    { id: "title", desc: false },
  ]);

  const doc = state.loadedDocument;
  const allFindings = useMemo(() => doc?.findings || [], [doc?.findings]);
  const allPasses = useMemo(() => doc?.passes || [], [doc?.passes]);
  const rules = useMemo(() => doc?.rules || {}, [doc?.rules]);
  const gaps = useMemo(() => doc?.gaps || [], [doc?.gaps]);

  // Derived filter options & counts
  const { availableCategories, severityCounts, categoryCounts } = useMemo(() => {
    const cats = new Set<string>();
    const sevMap: Record<string, number> = {
      CRITICAL: 0,
      HIGH: 0,
      MEDIUM: 0,
      LOW: 0,
      INFO: 0,
    };
    const catMap: Record<string, number> = {};

    for (const f of allFindings) {
      const sev = f.severity?.toUpperCase();
      if (sevMap[sev] !== undefined) sevMap[sev]++;
      if (f.category) {
        cats.add(f.category);
        catMap[f.category] = (catMap[f.category] || 0) + 1;
      }
    }

    return {
      availableCategories: Array.from(cats).sort(),
      severityCounts: sevMap,
      categoryCounts: catMap,
    };
  }, [allFindings]);

  // Filtered Findings
  const filteredFindings = useMemo(() => {
    return allFindings.filter((finding) => {
      // 1. Severity filter
      if (
        selectedSeverities.length > 0 &&
        !selectedSeverities.includes(finding.severity?.toUpperCase())
      ) {
        return false;
      }

      // 2. Category filter
      if (selectedCategory !== "all" && finding.category !== selectedCategory) {
        return false;
      }

      // 3. Search query filter
      if (filterText.trim()) {
        const query = filterText.toLowerCase();
        const titleMatch = finding.title.toLowerCase().includes(query);
        const ruleIdMatch = finding.rule_id.toLowerCase().includes(query);
        const scopeMatch = finding.scope.toLowerCase().includes(query);
        const catMatch = finding.category?.toLowerCase().includes(query) ?? false;
        const refMatch =
          finding.references?.some((r) => r.toLowerCase().includes(query)) ?? false;

        if (!titleMatch && !ruleIdMatch && !scopeMatch && !catMatch && !refMatch) {
          return false;
        }
      }

      return true;
    });
  }, [allFindings, selectedSeverities, selectedCategory, filterText]);

  // Filtered Passes
  const filteredPasses = useMemo(() => {
    if (!filterText.trim()) return allPasses;
    const query = filterText.toLowerCase();
    return allPasses.filter((pass) => {
      const ruleMeta = rules[pass.rule_id];
      const title =
        pass.title || ruleMeta?.passed_title || ruleMeta?.title || pass.rule_id;
      const titleMatch = title.toLowerCase().includes(query);
      const ruleIdMatch = pass.rule_id.toLowerCase().includes(query);
      const scopeMatch = pass.scope?.toLowerCase().includes(query) ?? false;
      return titleMatch || ruleIdMatch || scopeMatch;
    });
  }, [allPasses, rules, filterText]);

  // Deep-linking effect for ?selected=rule_id
  useEffect(() => {
    if (!deepSelectedRuleId || !doc) return;
    const found = allFindings.find((f) => f.rule_id === deepSelectedRuleId);
    if (found) {
      setActiveFinding(found);
      setFindingDrawerOpen(true);
      const idx = filteredFindings.indexOf(found);
      if (idx !== -1) setSelectedFindingIndex(idx);
    } else {
      const passFound = allPasses.find((p) => p.rule_id === deepSelectedRuleId);
      if (passFound) {
        setActivePass(passFound);
        setPassDrawerOpen(true);
        const pIdx = filteredPasses.indexOf(passFound);
        if (pIdx !== -1) setSelectedPassIndex(pIdx);
      }
    }
  }, [deepSelectedRuleId, doc, allFindings, allPasses, filteredFindings, filteredPasses]);

  // Update URL helper
  const updateUrlParams = useCallback(
    (updates: Record<string, string | null>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [key, val] of Object.entries(updates)) {
            if (val === null || val === "" || val === "all") {
              next.delete(key);
            } else {
              next.set(key, val);
            }
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  // Filter Handlers
  const handleFilterTextChange = (text: string) => {
    setFilterText(text);
    updateUrlParams({ q: text || null });
    setSelectedFindingIndex(null);
    setSelectedPassIndex(null);
  };

  const handleSeveritiesChange = (severities: string[]) => {
    setSelectedSeverities(severities);
    updateUrlParams({ severity: severities.length ? severities.join(",") : null });
    setSelectedFindingIndex(null);
  };

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    updateUrlParams({ category: category === "all" ? null : category });
    setSelectedFindingIndex(null);
  };

  const handleClearAllFilters = () => {
    setFilterText("");
    setSelectedSeverities([]);
    setSelectedCategory("all");
    updateUrlParams({ q: null, severity: null, category: null });
    setSelectedFindingIndex(null);
    setSelectedPassIndex(null);
  };

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    updateUrlParams({ tab: tab === "findings" ? null : tab });
    setSelectedFindingIndex(null);
    setSelectedPassIndex(null);
  };

  const handleOpenFindingDrawer = (finding: FindingItem) => {
    setActiveFinding(finding);
    setFindingDrawerOpen(true);
    updateUrlParams({ selected: finding.rule_id });
  };

  const handleCloseFindingDrawer = (open: boolean) => {
    setFindingDrawerOpen(open);
    if (!open) {
      updateUrlParams({ selected: null });
    }
  };

  const handleOpenPassDrawer = (pass: PassedCheckItem) => {
    setActivePass(pass);
    setPassDrawerOpen(true);
    updateUrlParams({ selected: pass.rule_id });
  };

  const handleClosePassDrawer = (open: boolean) => {
    setPassDrawerOpen(open);
    if (!open) {
      updateUrlParams({ selected: null });
    }
  };

  // Keyboard navigation for Findings & Passes tables
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || "").toLowerCase();
      const isInput = activeTag === "input" || activeTag === "textarea";

      // '/' focuses the filter bar
      if (e.key === "/" && !isInput) {
        e.preventDefault();
        filterBarRef.current?.focusInput();
        return;
      }

      // 'Escape' clears filter or closes drawer
      if (e.key === "Escape") {
        if (findingDrawerOpen) {
          handleCloseFindingDrawer(false);
          return;
        }
        if (passDrawerOpen) {
          handleClosePassDrawer(false);
          return;
        }
        if (filterText) {
          handleFilterTextChange("");
          return;
        }
      }

      if (isInput) return;

      // Arrow navigation
      if (activeTab === "findings" && filteredFindings.length > 0) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setSelectedFindingIndex((prev) => {
            const nextIdx = prev === null ? 0 : Math.min(prev + 1, filteredFindings.length - 1);
            return nextIdx;
          });
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setSelectedFindingIndex((prev) => {
            const nextIdx = prev === null ? filteredFindings.length - 1 : Math.max(prev - 1, 0);
            return nextIdx;
          });
        } else if (e.key === "Enter" && selectedFindingIndex !== null) {
          e.preventDefault();
          const target = filteredFindings[selectedFindingIndex];
          if (target) handleOpenFindingDrawer(target);
        }
      } else if (activeTab === "passes" && filteredPasses.length > 0) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setSelectedPassIndex((prev) => {
            const nextIdx = prev === null ? 0 : Math.min(prev + 1, filteredPasses.length - 1);
            return nextIdx;
          });
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setSelectedPassIndex((prev) => {
            const nextIdx = prev === null ? filteredPasses.length - 1 : Math.max(prev - 1, 0);
            return nextIdx;
          });
        } else if (e.key === "Enter" && selectedPassIndex !== null) {
          e.preventDefault();
          const target = filteredPasses[selectedPassIndex];
          if (target) handleOpenPassDrawer(target);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    activeTab,
    filteredFindings,
    filteredPasses,
    selectedFindingIndex,
    selectedPassIndex,
    findingDrawerOpen,
    passDrawerOpen,
    filterText,
  ]);

  // 1. Loading State
  if (state.runStatus === "running") {
    return (
      <div className="space-y-4 font-mono">
        <PageHeader
          title="findings"
          description="Security findings and evaluated policy rules."
        />
        <div className="space-y-3 p-4 rounded-data border border-border-hairline bg-surface-panel">
          <Skeleton className="h-8 w-full max-w-md bg-surface-raised" />
          <div className="flex gap-2">
            <Skeleton className="h-6 w-20 bg-surface-raised" />
            <Skeleton className="h-6 w-20 bg-surface-raised" />
            <Skeleton className="h-6 w-20 bg-surface-raised" />
          </div>
        </div>
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full bg-surface-panel" />
          ))}
        </div>
      </div>
    );
  }

  // 2. Error State
  if (state.runStatus === "error") {
    return (
      <div className="space-y-4 font-mono">
        <PageHeader
          title="findings"
          description="Security findings and evaluated policy rules."
        />
        <ErrorState
          error={state.runError || "An unexpected error occurred while analyzing the capture."}
          onAction={analyzeSelected}
          actionLabel="Retry analysis"
        />
      </div>
    );
  }

  // 3. Empty State (No capture loaded)
  if (!doc) {
    return (
      <div className="space-y-4 font-mono">
        <PageHeader
          title="findings"
          description="Security findings and evaluated policy rules."
        />
        <EmptyState
          title="No capture analyzed yet"
          message="Pick a capture from the left explorer, then choose Analyze capture."
          actionLabel="Load sample data"
          onAction={loadSampleData}
        />
      </div>
    );
  }

  // 4. Populated State
  const hasZeroFindings = allFindings.length === 0;

  return (
    <div className="space-y-4 font-mono">
      <PageHeader
        title="findings"
        description="Evaluated findings with severity classification and evidence provenance."
      />

      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1 border-b border-border-hairline">
          <TabsList>
            <TabsTrigger value="findings" className="gap-2">
              <span>findings</span>
              <span className="px-1.5 py-0.2 rounded-data text-[10px] bg-surface-raised text-text-secondary tabular-nums">
                {allFindings.length}
              </span>
            </TabsTrigger>
            <TabsTrigger value="passes" className="gap-2">
              <span>passes</span>
              <span className="px-1.5 py-0.2 rounded-data text-[10px] bg-surface-raised text-text-secondary tabular-nums">
                {allPasses.length}
              </span>
            </TabsTrigger>
          </TabsList>

          <div className="text-[11px] text-text-tertiary select-none">
            {allFindings.length > 0
              ? `${allFindings.length} policy violations found`
              : "0 policy violations found"}
            {" · "}
            {allPasses.length} checks passed
            {gaps.length > 0 && ` · ${gaps.length} coverage gaps remain`}
          </div>
        </div>

        {/* Tab 1: Findings */}
        <TabsContent value="findings" className="space-y-4 mt-0">
          {hasZeroFindings ? (
            <ZeroFindingsCard
              passedCount={allPasses.length}
              gaps={gaps}
              coverageGapCount={doc?.coverage?.checks_gap}
              onViewPasses={() => handleTabChange("passes")}
            />
          ) : (
            <>
              {/* Filter Bar */}
              <FindingsFilterBar
                ref={filterBarRef}
                filterText={filterText}
                onFilterTextChange={handleFilterTextChange}
                selectedSeverities={selectedSeverities}
                onSeveritiesChange={handleSeveritiesChange}
                selectedCategory={selectedCategory}
                onCategoryChange={handleCategoryChange}
                availableCategories={availableCategories}
                severityCounts={severityCounts}
                categoryCounts={categoryCounts}
                totalCount={allFindings.length}
                filteredCount={filteredFindings.length}
                onClearAll={handleClearAllFilters}
              />

              {/* Table */}
              <FindingsTable
                findings={filteredFindings}
                selectedFindingIndex={selectedFindingIndex}
                onSelectRow={(idx, finding) => {
                  setSelectedFindingIndex(idx);
                  handleOpenFindingDrawer(finding);
                }}
                onOpenDrawer={handleOpenFindingDrawer}
                sorting={findingsSorting}
                onSortingChange={setFindingsSorting}
                onClearFilters={handleClearAllFilters}
              />
            </>
          )}
        </TabsContent>

        {/* Tab 2: Passes (Quiet and Compact) */}
        <TabsContent value="passes" className="space-y-3 mt-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="text-text-secondary font-sans">
              Checks evaluated against observed capture frames that yielded zero policy violations:
            </div>
            {allPasses.length > 0 && (
              <div className="w-full sm:w-72">
                <input
                  type="text"
                  value={filterText}
                  onChange={(e) => handleFilterTextChange(e.target.value)}
                  placeholder="filter passes by title or rule id..."
                  className="w-full h-8 px-2.5 rounded-data border border-border-hairline bg-surface-panel text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-signal"
                />
              </div>
            )}
          </div>

          <PassesTable
            passes={filteredPasses}
            rules={rules}
            selectedPassIndex={selectedPassIndex}
            onSelectRow={(idx, pass) => {
              setSelectedPassIndex(idx);
              handleOpenPassDrawer(pass);
            }}
            onOpenDrawer={handleOpenPassDrawer}
            sorting={passesSorting}
            onSortingChange={setPassesSorting}
          />
        </TabsContent>
      </Tabs>

      {/* Detail Drawers */}
      <FindingDetailDrawer
        open={findingDrawerOpen}
        onOpenChange={handleCloseFindingDrawer}
        finding={activeFinding}
        ruleMeta={activeFinding ? rules[activeFinding.rule_id] : undefined}
        allGaps={gaps}
      />

      <PassDetailDrawer
        open={passDrawerOpen}
        onOpenChange={handleClosePassDrawer}
        pass={activePass}
        ruleMeta={activePass ? rules[activePass.rule_id] : undefined}
      />
    </div>
  );
};
