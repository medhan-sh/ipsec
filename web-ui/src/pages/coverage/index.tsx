import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAppStore } from "@/context/store";
import { PageHeader } from "@/components/app/PageHeader";
import { SectionHeader } from "@/components/app/SectionHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { Skeleton } from "@/components/vendor/skeleton";
import { StagedBreakdown } from "./components/StagedBreakdown";
import { GapsTable } from "./components/GapsTable";
import { PassesList } from "./components/PassesList";
import { PipelineFacts } from "./components/PipelineFacts";

export const CoveragePage: React.FC = () => {
  const { state, analyzeSelected, selectCapture, loadSampleData } = useAppStore();
  const [searchParams] = useSearchParams();
  const captureParam = searchParams.get("capture");

  useEffect(() => {
    if (captureParam && captureParam !== state.selectedCapture) {
      selectCapture(captureParam);
    }
  }, [captureParam, state.selectedCapture, selectCapture]);

  // State 1: Running
  if (state.runStatus === "running") {
    return (
      <div className="space-y-4">
        <PageHeader
          title="coverage"
          description="Policy rule coverage, passes, and gaps accounting."
        />
        <div className="space-y-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    );
  }

  // State 2: Error
  if (state.runStatus === "error") {
    return (
      <div>
        <PageHeader
          title="coverage"
          description="Policy rule coverage, passes, and gaps accounting."
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
          title="coverage"
          description="Policy rule coverage, passes, and gaps accounting."
        />
        <EmptyState
          title="No coverage data"
          message="Pick a capture from the left explorer, then choose Analyze capture."
          actionLabel="Load sample data"
          onAction={loadSampleData}
        />
      </div>
    );
  }

  const { coverage, gaps = [], passes = [], capture } = state.loadedDocument;

  return (
    <div className="space-y-6 pb-16 font-mono">
      <PageHeader
        title="coverage"
        description="Accounting of evaluated rules, passes, and coverage gaps. What we know, what we could not know, and why."
      />

      {/* 1. Staged Breakdown: total -> found -> assessable -> passed, accounting for gaps */}
      <section>
        <SectionHeader title="checks breakdown" />
        <StagedBreakdown coverage={coverage} />
      </section>

      {/* 2. Coverage Gaps Table */}
      <section>
        <SectionHeader title="coverage gaps" count={gaps.length} />
        <GapsTable gaps={gaps} />
      </section>

      {/* 3. Passed Checks List (Compact) */}
      <section>
        <SectionHeader title="passed checks" count={passes.length} />
        <PassesList passes={passes} />
      </section>

      {/* 4. Pipeline Facts Block */}
      <section>
        <SectionHeader title="pipeline facts" />
        <PipelineFacts coverage={coverage} capture={capture} />
      </section>
    </div>
  );
};
