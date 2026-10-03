import React from "react";
import { Play, FileText, Code2 } from "lucide-react";
import { useAppStore } from "@/context/store";
import { Button } from "@/components/vendor/button";
import { SampleDataChip } from "@/components/app/SampleDataChip";
import { cn } from "@/lib/utils";

interface TopBarProps {
  onOpenJson?: () => void;
  className?: string;
}

export const TopBar: React.FC<TopBarProps> = ({ onOpenJson, className }) => {
  const { state, analyzeSelected } = useAppStore();

  const handleOpenReport = () => {
    if (!state.selectedCapture) return;
    window.open(`/api/report/${encodeURIComponent(state.selectedCapture)}`, "_blank");
  };

  const isAnalyzing = state.runStatus === "running";

  return (
    <header
      className={cn(
        "h-12 w-full border-b border-border-hairline bg-surface-chrome px-4 flex items-center justify-between font-mono select-none z-10",
        className
      )}
    >
      <div className="flex items-center gap-3 overflow-hidden text-xs">
        <span className="text-text-tertiary">capture:</span>
        <span className="text-text-primary font-medium truncate max-w-xs">
          {state.selectedCapture || "none selected"}
        </span>

        {state.dataSource === "mock" && <SampleDataChip />}
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="signal"
          size="sm"
          onClick={analyzeSelected}
          disabled={!state.selectedCapture || isAnalyzing}
          className="gap-1.5"
        >
          <Play className={cn("h-3 w-3", isAnalyzing && "animate-spin")} />
          <span>{isAnalyzing ? "Analyzing..." : "Analyze capture"}</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={handleOpenReport}
          disabled={!state.selectedCapture}
          className="gap-1.5"
        >
          <FileText className="h-3 w-3 text-text-secondary" />
          <span>Open report</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={onOpenJson}
          disabled={!state.loadedDocument}
          className="gap-1.5"
        >
          <Code2 className="h-3 w-3 text-text-secondary" />
          <span>View JSON</span>
        </Button>
      </div>
    </header>
  );
};
