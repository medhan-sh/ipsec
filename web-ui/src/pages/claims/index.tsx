import React, { useState, useMemo, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAppStore } from "@/context/store";
import { ClaimItem } from "@/api/types";
import { PageHeader } from "@/components/app/PageHeader";
import { FilterBar } from "@/components/app/FilterBar";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";
import { Button } from "@/components/vendor/button";
import { Layers } from "lucide-react";
import { TierFilterToggle } from "./components/TierFilterToggle";
import { ClaimsTable } from "./components/ClaimsTable";
import { ClaimDetailDrawer } from "./components/ClaimDetailDrawer";
import { groupClaimsByField } from "./components/claims-utils";

export const ClaimsPage: React.FC = () => {
  const { state, analyzeSelected, selectCapture, loadSampleData } = useAppStore();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL State parameters
  const captureParam = searchParams.get("capture");
  const claimParam = searchParams.get("claim");
  const drawerParam = searchParams.get("drawer");
  const currentTierParam = (searchParams.get("tier") || "ALL").toUpperCase();
  const currentQueryParam = searchParams.get("q") || "";
  const currentGroupParam = searchParams.get("group") === "field";

  // Selected row state for keyboard navigation
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [activeClaim, setActiveClaim] = useState<ClaimItem | null>(null);
  const [activeGroupedClaims, setActiveGroupedClaims] = useState<ClaimItem[] | null>(null);

  // Synchronize capture from URL if provided
  useEffect(() => {
    if (captureParam && captureParam !== state.selectedCapture) {
      selectCapture(captureParam);
    }
  }, [captureParam, state.selectedCapture, selectCapture]);

  // Helper to update search params
  const updateUrlParams = (updates: {
    tier?: string;
    q?: string;
    group?: boolean;
  }) => {
    const next = new URLSearchParams(searchParams);

    if (updates.tier !== undefined) {
      if (updates.tier === "ALL" || !updates.tier) {
        next.delete("tier");
      } else {
        next.set("tier", updates.tier);
      }
    }

    if (updates.q !== undefined) {
      if (!updates.q) {
        next.delete("q");
      } else {
        next.set("q", updates.q);
      }
    }

    if (updates.group !== undefined) {
      if (updates.group) {
        next.set("group", "field");
      } else {
        next.delete("group");
      }
    }

    setSearchParams(next, { replace: true });
    setSelectedIndex(0);
  };

  const claims = state.loadedDocument?.claims || [];

  // Compute tier counts across all claims in the document
  const tierCounts = useMemo(() => {
    const counts: Record<string, number> = {
      OBSERVED: 0,
      INFERRED_SIDE_CHANNEL: 0,
      INFERRED_IMPLEMENTATION_DEFAULT: 0,
      ML_PREDICTION: 0,
      NOT_OBSERVABLE: 0,
    };
    for (const c of claims) {
      if (counts[c.tier] !== undefined) {
        counts[c.tier]++;
      } else {
        counts[c.tier] = 1;
      }
    }
    return counts;
  }, [claims]);

  // Filter claims by tier and search query (field + method)
  const filteredClaims = useMemo(() => {
    return claims.filter((claim) => {
      // Tier filter
      if (currentTierParam !== "ALL" && claim.tier !== currentTierParam) {
        return false;
      }
      // Query filter on field and method
      if (currentQueryParam.trim()) {
        const query = currentQueryParam.toLowerCase().trim();
        const matchesField = claim.field.toLowerCase().includes(query);
        const matchesMethod = (claim.method || "").toLowerCase().includes(query);
        if (!matchesField && !matchesMethod) {
          return false;
        }
      }
      return true;
    });
  }, [claims, currentTierParam, currentQueryParam]);

  // Grouped claims by field
  const groupedClaims = useMemo(() => {
    return groupClaimsByField(filteredClaims);
  }, [filteredClaims]);

  const maxIndex = currentGroupParam ? groupedClaims.length - 1 : filteredClaims.length - 1;

  // Keyboard navigation for table selection and drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || "").toLowerCase();
      const isInput = activeTag === "input" || activeTag === "textarea";

      // If user presses '/' outside an input, focus filter
      if (e.key === "/" && !isInput) {
        e.preventDefault();
        const filterInput = document.querySelector<HTMLInputElement>(
          'input[placeholder="filter field or method..."]'
        );
        filterInput?.focus();
        return;
      }

      if (isInput) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, Math.max(0, maxIndex)));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter") {
        if (maxIndex >= 0) {
          e.preventDefault();
          if (currentGroupParam) {
            const group = groupedClaims[selectedIndex];
            if (group && group.claims.length > 0) {
              setActiveClaim(group.claims[0]);
              setActiveGroupedClaims(group.claims);
              setDrawerOpen(true);
            }
          } else {
            const item = filteredClaims[selectedIndex];
            if (item) {
              setActiveClaim(item);
              setActiveGroupedClaims(null);
              setDrawerOpen(true);
            }
          }
        }
      } else if (e.key === "Escape") {
        if (drawerOpen) {
          e.preventDefault();
          setDrawerOpen(false);
        } else if (currentQueryParam) {
          e.preventDefault();
          updateUrlParams({ q: "" });
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [maxIndex, currentGroupParam, groupedClaims, filteredClaims, selectedIndex, drawerOpen, currentQueryParam]);

  // Auto-open drawer when URL specifies claim or drawer
  useEffect(() => {
    if ((drawerParam || claimParam) && claims.length > 0 && !drawerOpen) {
      const target = claimParam
        ? claims.find((c) => c.field === claimParam) || claims[0]
        : claims[0];
      if (target) {
        setActiveClaim(target);
        setDrawerOpen(true);
      }
    }
  }, [drawerParam, claimParam, claims, drawerOpen]);

  // Handle drawer open trigger
  const handleOpenClaimDrawer = (claim: ClaimItem, group?: ClaimItem[]) => {
    setActiveClaim(claim);
    setActiveGroupedClaims(group || null);
    setDrawerOpen(true);
  };

  // State 1: Running
  if (state.runStatus === "running") {
    return (
      <div className="space-y-4">
        <PageHeader
          title="claims"
          description="Provenance ledger tracking every atomic fact and inference tier."
        />
        <div className="space-y-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  // State 2: Error
  if (state.runStatus === "error") {
    return (
      <div>
        <PageHeader
          title="claims"
          description="Provenance ledger tracking every atomic fact and inference tier."
        />
        <ErrorState error={state.runError || undefined} onAction={analyzeSelected} />
      </div>
    );
  }

  // State 3: Empty (no loaded capture document)
  if (!state.loadedDocument) {
    return (
      <div>
        <PageHeader
          title="claims"
          description="Provenance ledger tracking every atomic fact and inference tier."
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

  // State 3b: Empty claims list in loaded document
  if (claims.length === 0) {
    return (
      <div>
        <PageHeader
          title="claims"
          description="Provenance ledger tracking every atomic fact and inference tier."
        />
        <EmptyState
          title="No claims recorded"
          message="The analyzed capture contained zero security or protocol claims."
        />
      </div>
    );
  }

  // State 4: Populated
  return (
    <div className="space-y-4 pb-12 font-mono">
      <PageHeader
        title="claims"
        description="Forensic provenance ledger tracking every fact and inference tier. What we know, how we know it, and how certain we are."
        actions={
          <Button
            variant={currentGroupParam ? "signal" : "outline"}
            size="sm"
            onClick={() => updateUrlParams({ group: !currentGroupParam })}
            className="flex items-center gap-1.5 font-mono text-xs"
            title="Collapse repeated fields into single rows"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>group by field</span>
            {currentGroupParam && (
              <span className="ml-1 text-[11px] text-text-primary bg-surface-chrome px-1 rounded-data">
                on
              </span>
            )}
          </Button>
        }
      />

      {/* Control bar: 5-way tier toggle group & search filter */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <TierFilterToggle
          counts={tierCounts}
          totalCount={claims.length}
          selectedTier={currentTierParam}
          onSelectTier={(tier) => updateUrlParams({ tier })}
        />

        <div className="w-full md:w-72 shrink-0">
          <FilterBar
            value={currentQueryParam}
            onChange={(q) => updateUrlParams({ q })}
            placeholder="filter field or method..."
          />
        </div>
      </div>

      {/* Filter status & counter */}
      <div className="flex items-center justify-between text-xs text-text-tertiary px-1">
        <span>
          showing{" "}
          <strong className="text-text-primary tabular-nums">
            {currentGroupParam ? groupedClaims.length : filteredClaims.length}
          </strong>{" "}
          {currentGroupParam ? "fields" : "claims"} of{" "}
          <strong className="text-text-secondary tabular-nums">{claims.length}</strong> total
          {currentTierParam !== "ALL" && (
            <span>
              {" "}· tier: <span className="text-signal lowercase">{currentTierParam.replace(/_/g, " ")}</span>
            </span>
          )}
          {currentQueryParam && (
            <span>
              {" "}· query: <span className="text-text-primary font-mono">"{currentQueryParam}"</span>
            </span>
          )}
        </span>

        <span className="text-[11px] hidden sm:inline">
          [↑ / ↓ navigate · Enter open · / search · Esc clear]
        </span>
      </div>

      {/* Ledger Table */}
      <ClaimsTable
        claims={filteredClaims}
        groupedClaims={groupedClaims}
        groupByField={currentGroupParam}
        selectedIndex={selectedIndex}
        onSelectIndex={setSelectedIndex}
        onOpenClaimDrawer={handleOpenClaimDrawer}
      />

      {/* Detail Drawer */}
      <ClaimDetailDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        claim={activeClaim}
        groupedClaims={activeGroupedClaims}
      />
    </div>
  );
};
