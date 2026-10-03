import React from "react";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";

export const CoveragePage: React.FC = () => {
  const { state, analyzeSelected } = useAppStore();

  if (state.runStatus === "running") {
    return (
      <div className="space-y-4">
        <PageHeader title="coverage" description="Policy rule coverage, passes, and gaps accounting." />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (state.runStatus === "error") {
    return (
      <div>
        <PageHeader title="coverage" description="Policy rule coverage, passes, and gaps accounting." />
        <ErrorState error={state.runError || undefined} onAction={analyzeSelected} />
      </div>
    );
  }

  if (!state.loadedDocument) {
    return (
      <div>
        <PageHeader title="coverage" description="Policy rule coverage, passes, and gaps accounting." />
        <EmptyState
          title="No coverage data"
          message="Pick a capture from the left explorer, then choose Analyze capture."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="coverage"
        description="Accounting of evaluated rules, passes, and coverage gaps."
      />
      <div className="p-4 rounded-data border border-border-hairline bg-surface-panel text-xs font-mono">
        <div className="text-text-secondary text-[11px] mb-2">
          [Phase 0 placeholder — Agent 4 will construct coverage waterfall and gaps ledger]
        </div>
        <p className="text-text-primary">
          Checks Total: <strong>{state.loadedDocument.coverage.checks_total}</strong> |
          Passed: <strong>{state.loadedDocument.coverage.checks_passed}</strong> |
          Gaps: <strong>{state.loadedDocument.coverage.checks_gap}</strong>
        </p>
      </div>
    </div>
  );
};
