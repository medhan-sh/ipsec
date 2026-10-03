import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";
import { CaptureFacts } from "./components/CaptureFacts";
import { CoverageGlance } from "./components/CoverageGlance";
import { PipelineHealth } from "./components/PipelineHealth";
import { FindingsSummary } from "./components/FindingsSummary";
import { ProvenanceDistribution } from "./components/ProvenanceDistribution";

export const OverviewPage: React.FC = () => {
  const { state, analyzeSelected, selectCapture } = useAppStore();
  const [searchParams] = useSearchParams();
  const captureParam = searchParams.get("capture");

  useEffect(() => {
    if (captureParam && state.selectedCapture !== captureParam) {
      selectCapture(captureParam);
    }
  }, [captureParam, state.selectedCapture, selectCapture]);

  // State 1: Running / Loading
  if (state.runStatus === "running") {
    return (
      <div className="space-y-6">
        <PageHeader
          title="overview"
          description="Forensic posture, evidence provenance, and policy assessment summary."
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <Skeleton className="h-44 w-full rounded-data" />
            <Skeleton className="h-36 w-full rounded-data" />
            <Skeleton className="h-36 w-full rounded-data" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-64 w-full rounded-data" />
            <Skeleton className="h-56 w-full rounded-data" />
          </div>
        </div>
      </div>
    );
  }

  // State 2: Error
  if (state.runStatus === "error") {
    return (
      <div className="space-y-6">
        <PageHeader
          title="overview"
          description="Forensic posture, evidence provenance, and policy assessment summary."
        />
        <ErrorState
          error={state.runError || "Analysis failed unexpectedly."}
          actionLabel="Retry analysis"
          onAction={analyzeSelected}
        />
      </div>
    );
  }

  // State 3: Empty (no capture analyzed yet)
  if (!state.loadedDocument) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="overview"
          description="Forensic posture, evidence provenance, and policy assessment summary."
        />
        <EmptyState
          title="No capture analyzed yet"
          message="Pick a capture from the left explorer, then choose Analyze capture."
          actionLabel={state.selectedCapture ? "Analyze capture" : undefined}
          onAction={state.selectedCapture ? analyzeSelected : undefined}
        />
      </div>
    );
  }

  // State 4: Populated (Forensic Instrument)
  const { capture, coverage, findings, claims, rules } = state.loadedDocument;

  return (
    <div className="space-y-6 select-none font-mono">
      <PageHeader
        title="overview"
        description="Forensic posture, evidence provenance, and policy assessment summary."
      />

      {/* Dense Two-Column Grid: Forensic Instrument */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Facts, Coverage, Pipeline */}
        <div className="flex flex-col gap-6">
          <CaptureFacts capture={capture} />
          <CoverageGlance coverage={coverage} />
          <PipelineHealth coverage={coverage} />
        </div>

        {/* Right Column: Findings Summary, Provenance Distribution */}
        <div className="flex flex-col gap-6">
          <FindingsSummary findings={findings} rules={rules} />
          <ProvenanceDistribution
            claims={claims}
            runStatus={state.runStatus}
            captureName={capture.filename}
          />
        </div>
      </div>
    </div>
  );
};
