import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";
import { Mono } from "@/components/app/Mono";
import { Badge } from "@/components/vendor/badge";
import { Button } from "@/components/vendor/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/vendor/tabs";
import { SectionHeader } from "@/components/app/SectionHeader";
import {
  normalizeCandidateSet,
  groupEliminatedByReason,
  getTunnelVerdicts,
  getIkeClaims,
} from "./types";
import { TunnelList } from "./components/TunnelList";
import { EliminationStagedBar } from "./components/EliminationStagedBar";
import { EliminatedCandidates } from "./components/EliminatedCandidates";
import { SurvivorsList } from "./components/SurvivorsList";
import { TunnelVerdicts } from "./components/TunnelVerdicts";
import { IkeClaimsCard } from "./components/IkeClaimsCard";
import { AlertCircle, ChevronLeft, ChevronRight } from "lucide-react";

export const TunnelsPage: React.FC = () => {
  const { state, analyzeSelected } = useAppStore();
  const [selectedTunnelIndex, setSelectedTunnelIndex] = useState(0);
  const [tunnelFilter, setTunnelFilter] = useState("");
  const [selectedReasonGroupId, setSelectedReasonGroupId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"all" | "elimination" | "verdicts" | "ike">("all");

  const doc = state.loadedDocument;

  // Normalized candidate sets
  const candidateSets = useMemo(() => {
    if (!doc || !doc.candidate_sets) return [];
    return doc.candidate_sets.map((cs) => normalizeCandidateSet(cs, doc));
  }, [doc]);

  // Keep selectedTunnelIndex within bounds
  useEffect(() => {
    if (selectedTunnelIndex >= candidateSets.length && candidateSets.length > 0) {
      setSelectedTunnelIndex(0);
    }
  }, [candidateSets.length, selectedTunnelIndex]);

  // Current tunnel
  const currentTunnel = candidateSets[selectedTunnelIndex] || null;

  // Grouped elimination reasons for current tunnel
  const eliminationGroups = useMemo(() => {
    if (!currentTunnel) return [];
    return groupEliminatedByReason(currentTunnel.eliminated);
  }, [currentTunnel]);

  // Verdicts for current tunnel
  const currentVerdicts = useMemo(() => {
    if (!doc || !currentTunnel) return [];
    const direct = getTunnelVerdicts(currentTunnel.sa_id, doc.verdicts || []);
    if (direct.length > 0) return direct;
    // Fallback if sa_id formatting differs slightly or if only 1 tunnel exists
    if (candidateSets.length === 1 && (doc.verdicts?.length ?? 0) > 0) {
      return doc.verdicts || [];
    }
    return [];
  }, [doc, currentTunnel, candidateSets.length]);

  // IKE claims
  const ikeClaims = useMemo(() => {
    if (!doc || !doc.claims) return [];
    return getIkeClaims(doc.claims);
  }, [doc]);

  // Keyboard navigation: '[' and ']' step between tunnels
  const stepTunnel = useCallback(
    (delta: number) => {
      if (candidateSets.length <= 1) return;
      setSelectedTunnelIndex((prev) => {
        const next = (prev + delta + candidateSets.length) % candidateSets.length;
        return next;
      });
      setSelectedReasonGroupId(null);
    },
    [candidateSets.length]
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || "").toLowerCase();
      const isInput =
        activeTag === "input" ||
        activeTag === "textarea" ||
        (document.activeElement as HTMLElement)?.isContentEditable;

      if (isInput) return;

      if (e.key === "[") {
        e.preventDefault();
        stepTunnel(-1);
      } else if (e.key === "]") {
        e.preventDefault();
        stepTunnel(1);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [stepTunnel]);

  // State 1: Running / Loading
  if (state.runStatus === "running") {
    return (
      <div className="space-y-4">
        <PageHeader
          title="tunnels"
          description="Candidate elimination before ranking and tunnel verdict lifting."
        />
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1 space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
          <div className="lg:col-span-3 space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    );
  }

  // State 2: Error
  if (state.runStatus === "error") {
    return (
      <div>
        <PageHeader
          title="tunnels"
          description="Candidate elimination before ranking and tunnel verdict lifting."
        />
        <ErrorState
          error={state.runError || undefined}
          onAction={analyzeSelected}
          actionLabel="Retry analysis"
        />
      </div>
    );
  }

  // State 3: Empty - No Document Loaded
  if (!doc) {
    return (
      <div>
        <PageHeader
          title="tunnels"
          description="Candidate elimination before ranking and tunnel verdict lifting."
        />
        <EmptyState
          title="No capture analyzed yet"
          message="Pick a capture from the left explorer, then choose Analyze capture."
        />
      </div>
    );
  }

  // State 3b: Empty - Document loaded but 0 candidate sets
  if (candidateSets.length === 0) {
    return (
      <div>
        <PageHeader
          title="tunnels"
          description="Candidate elimination before ranking and tunnel verdict lifting."
        />
        <EmptyState
          title="No ESP tunnels observed"
          message="No ESP data-plane traffic was observed in this capture — nothing to narrow. (This capture may be an IKE-handshake-only vector; see the coverage section.)"
        />
      </div>
    );
  }

  // State 4: Populated
  return (
    <div className="space-y-6">
      {/* Page Title & Global Actions */}
      <PageHeader
        title="tunnels"
        description="Candidate elimination before ranking and tunnel verdict lifting."
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-tertiary font-mono hidden sm:inline">
              tunnel {selectedTunnelIndex + 1} of {candidateSets.length}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => stepTunnel(-1)}
              disabled={candidateSets.length <= 1}
              className="h-8 text-xs font-mono"
              title="Previous tunnel ([)"
            >
              <ChevronLeft className="h-3.5 w-3.5 mr-1" />
              <span>[ prev</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => stepTunnel(1)}
              disabled={candidateSets.length <= 1}
              className="h-8 text-xs font-mono"
              title="Next tunnel (])"
            >
              <span>next ]</span>
              <ChevronRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          </div>
        }
      />

      {/* Two Column Layout: Left master list, Right detail inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Tunnel Selector List */}
        <div className="lg:col-span-4 xl:col-span-3 lg:sticky lg:top-0">
          <TunnelList
            tunnels={candidateSets}
            selectedIndex={selectedTunnelIndex}
            onSelectIndex={(idx) => {
              setSelectedTunnelIndex(idx);
              setSelectedReasonGroupId(null);
            }}
            filterText={tunnelFilter}
            onFilterChange={setTunnelFilter}
          />
        </div>

        {/* Right Column: Selected Tunnel Forensics */}
        {currentTunnel && (
          <div className="lg:col-span-8 xl:col-span-9 space-y-6 min-w-0">
            {/* Tunnel Identity & Direction Banner */}
            <div className="rounded-data border border-border-hairline bg-surface-panel p-4 flex flex-wrap items-center justify-between gap-4 font-mono">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-text-tertiary uppercase">tunnel SA ID:</span>
                  <Mono value={currentTunnel.sa_id} copyable className="text-xs font-semibold text-text-primary" />
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-text-tertiary">field:</span>
                  <span className="text-text-secondary">{currentTunnel.field}</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {currentTunnel.missingDirection ? (
                  <Badge variant="warning" className="text-xs px-2 py-0.5 flex items-center gap-1.5 font-mono">
                    <AlertCircle className="h-3.5 w-3.5" />
                    <span>missing return direction (unidirectional)</span>
                  </Badge>
                ) : (
                  <Badge variant="signal" className="text-xs px-2 py-0.5 font-mono">
                    bidirectional (reciprocal traffic observed)
                  </Badge>
                )}

                <div className="text-right text-xs tabular-nums border-l border-border-hairline pl-3">
                  <div className="text-signal font-semibold">
                    {currentTunnel.survivors.length} surviving
                  </div>
                  <div className="text-text-tertiary text-[11px]">
                    of {currentTunnel.universeSize} RFC suites
                  </div>
                </div>
              </div>
            </div>

            {/* View Filter Tabs */}
            <div className="flex items-center justify-between border-b border-border-hairline pb-2">
              <Tabs
                value={activeTab}
                onValueChange={(v) => setActiveTab(v as any)}
                className="w-full"
              >
                <TabsList className="bg-surface-panel border border-border-hairline h-8 p-0.5">
                  <TabsTrigger value="all" className="text-xs px-3 font-mono">
                    all forensics
                  </TabsTrigger>
                  <TabsTrigger value="elimination" className="text-xs px-3 font-mono">
                    elimination & survivors
                  </TabsTrigger>
                  <TabsTrigger value="verdicts" className="text-xs px-3 font-mono">
                    lifted verdicts ({currentVerdicts.length})
                  </TabsTrigger>
                  <TabsTrigger value="ike" className="text-xs px-3 font-mono">
                    IKE claims ({ikeClaims.length})
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            {/* Content Sections */}
            {(activeTab === "all" || activeTab === "elimination") && (
              <div className="space-y-6">
                {/* 1. Elimination Staged Bar */}
                <section>
                  <SectionHeader title="elimination pipeline" count={currentTunnel.universeSize} />
                  <EliminationStagedBar
                    universeSize={currentTunnel.universeSize}
                    survivorsCount={currentTunnel.survivors.length}
                    groups={eliminationGroups}
                    selectedGroupId={selectedReasonGroupId}
                    onSelectGroup={setSelectedReasonGroupId}
                  />
                </section>

                {/* 2. Surviving Candidates & Indistinguishable Groups */}
                <section>
                  <SectionHeader title="survivors & indistinguishable groups" count={currentTunnel.survivors.length} />
                  <SurvivorsList
                    survivors={currentTunnel.survivors}
                    indistinguishable={currentTunnel.indistinguishable}
                  />
                </section>

                {/* 3. Eliminated Candidates Grouped by Reason */}
                <section>
                  <SectionHeader title="eliminated candidate suites" count={currentTunnel.eliminated.length} />
                  <EliminatedCandidates
                    groups={eliminationGroups}
                    selectedGroupId={selectedReasonGroupId}
                    onSelectGroup={setSelectedReasonGroupId}
                  />
                </section>
              </div>
            )}

            {(activeTab === "all" || activeTab === "verdicts") && (
              <section className="space-y-4">
                <SectionHeader title="lifted risk verdicts" count={currentVerdicts.length} />
                <TunnelVerdicts
                  verdicts={currentVerdicts}
                  sa_id={currentTunnel.sa_id}
                />
              </section>
            )}

            {(activeTab === "all" || activeTab === "ike") && (
              <section className="space-y-4">
                <SectionHeader title="IKE handshake suite claims" count={ikeClaims.length} />
                <IkeClaimsCard claims={ikeClaims} />
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
