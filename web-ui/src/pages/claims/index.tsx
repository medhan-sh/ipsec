import React from "react";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";

export const ClaimsPage: React.FC = () => {
  const { state, analyzeSelected } = useAppStore();

  if (state.runStatus === "running") {
    return (
      <div className="space-y-4">
        <PageHeader title="claims" description="Provenance ledger of atomic security claims." />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (state.runStatus === "error") {
    return (
      <div>
        <PageHeader title="claims" description="Provenance ledger of atomic security claims." />
        <ErrorState error={state.runError || undefined} onAction={analyzeSelected} />
      </div>
    );
  }

  if (!state.loadedDocument) {
    return (
      <div>
        <PageHeader title="claims" description="Provenance ledger of atomic security claims." />
        <EmptyState
          title="No claims recorded"
          message="Pick a capture from the left explorer, then choose Analyze capture."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="claims"
        description="Forensic provenance ledger tracking every fact and inference tier."
      />
      <div className="p-4 rounded-data border border-border-hairline bg-surface-panel text-xs font-mono">
        <div className="text-text-secondary text-[11px] mb-2">
          [Phase 0 placeholder — Agent 4 will construct provenance ledger and tier filter]
        </div>
        <p className="text-text-primary">
          Loaded document contains <strong>{state.loadedDocument.claims.length}</strong> claims.
        </p>
      </div>
    </div>
  );
};
