import React from "react";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";

export const FindingsPage: React.FC = () => {
  const { state, analyzeSelected } = useAppStore();

  if (state.runStatus === "running") {
    return (
      <div className="space-y-4">
        <PageHeader title="findings" description="Security findings and evaluated rules." />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (state.runStatus === "error") {
    return (
      <div>
        <PageHeader title="findings" description="Security findings and evaluated rules." />
        <ErrorState error={state.runError || undefined} onAction={analyzeSelected} />
      </div>
    );
  }

  if (!state.loadedDocument) {
    return (
      <div>
        <PageHeader title="findings" description="Security findings and evaluated rules." />
        <EmptyState
          title="No findings available"
          message="Pick a capture from the left explorer, then choose Analyze capture."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="findings"
        description="Evaluated findings with severity classification and evidence provenance."
      />
      <div className="p-4 rounded-data border border-border-hairline bg-surface-panel text-xs font-mono">
        <div className="text-text-secondary text-[11px] mb-2">
          [Phase 0 placeholder — Agent 2 will construct TanStack findings table with filters and drawer]
        </div>
        <p className="text-text-primary">
          Loaded document contains <strong>{state.loadedDocument.findings.length}</strong> findings and <strong>{state.loadedDocument.passes.length}</strong> passes.
        </p>
      </div>
    </div>
  );
};
