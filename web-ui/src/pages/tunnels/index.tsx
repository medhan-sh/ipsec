import React from "react";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";

export const TunnelsPage: React.FC = () => {
  const { state, analyzeSelected } = useAppStore();

  if (state.runStatus === "running") {
    return (
      <div className="space-y-4">
        <PageHeader title="tunnels" description="ESP data plane tunnels and candidate elimination." />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (state.runStatus === "error") {
    return (
      <div>
        <PageHeader title="tunnels" description="ESP data plane tunnels and candidate elimination." />
        <ErrorState error={state.runError || undefined} onAction={analyzeSelected} />
      </div>
    );
  }

  if (!state.loadedDocument) {
    return (
      <div>
        <PageHeader title="tunnels" description="ESP data plane tunnels and candidate elimination." />
        <EmptyState
          title="No tunnels observed"
          message="Pick a capture from the left explorer, then choose Analyze capture."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="tunnels"
        description="Candidate elimination before ranking and tunnel verdict lifting."
      />
      <div className="p-4 rounded-data border border-border-hairline bg-surface-panel text-xs font-mono">
        <div className="text-text-secondary text-[11px] mb-2">
          [Phase 0 placeholder — Agent 3 will construct candidate elimination stages and verdict inspector]
        </div>
        <p className="text-text-primary">
          Loaded document contains <strong>{state.loadedDocument.candidate_sets.length}</strong> candidate sets and <strong>{state.loadedDocument.verdicts.length}</strong> verdicts.
        </p>
      </div>
    </div>
  );
};
