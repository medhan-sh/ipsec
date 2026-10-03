import React from "react";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";

export const OverviewPage: React.FC = () => {
  const { state, analyzeSelected } = useAppStore();

  if (state.runStatus === "running") {
    return (
      <div className="space-y-4">
        <PageHeader title="overview" description="System posture and evidence provenance ledger." />
        <Skeleton className="h-28 w-full" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (state.runStatus === "error") {
    return (
      <div>
        <PageHeader title="overview" description="System posture and evidence provenance ledger." />
        <ErrorState error={state.runError || undefined} onAction={analyzeSelected} />
      </div>
    );
  }

  if (!state.loadedDocument) {
    return (
      <div>
        <PageHeader title="overview" description="System posture and evidence provenance ledger." />
        <EmptyState
          title="No capture analyzed yet"
          message="Pick a capture from the left explorer, then choose Analyze capture."
          actionLabel={state.selectedCapture ? "Analyze capture" : undefined}
          onAction={state.selectedCapture ? analyzeSelected : undefined}
        />
      </div>
    );
  }

  const { capture, findings, claims } = state.loadedDocument;

  return (
    <div className="space-y-6">
      <PageHeader
        title="overview"
        description="Forensic overview of handshake facts, severity breakdown, and tier distribution."
      />

      <div className="p-4 rounded-data border border-border-hairline bg-surface-panel text-xs font-mono space-y-2">
        <div className="text-text-secondary text-[11px]">
          [Phase 0 placeholder — Agent 1 will construct full two-column instrument]
        </div>
        <div className="flex gap-4">
          <span>File: <strong className="text-text-primary">{capture.filename}</strong></span>
          <span>Packets: <strong className="text-text-primary">{capture.packet_count}</strong></span>
          <span>Duration: <strong className="text-text-primary">{capture.duration_s}s</strong></span>
          <span>Findings: <strong className="text-text-primary">{findings.length}</strong></span>
          <span>Claims: <strong className="text-text-primary">{claims.length}</strong></span>
        </div>
      </div>
    </div>
  );
};
