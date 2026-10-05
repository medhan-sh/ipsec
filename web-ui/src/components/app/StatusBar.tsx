import React from "react";
import { useLocation } from "react-router-dom";
import { useAppStore } from "@/context/store";
import { cn } from "@/lib/utils";

interface StatusBarProps {
  onOpenHelp?: () => void;
  className?: string;
}

export const StatusBar: React.FC<StatusBarProps> = ({ onOpenHelp, className }) => {
  const { state } = useAppStore();
  const location = useLocation();

  const shortSha = state.loadedDocument?.capture?.sha256
    ? state.loadedDocument.capture.sha256.slice(0, 8)
    : "—";

  const captureName = state.selectedCapture || "none selected";

  const path = location.pathname.replace(/^\/app\/?/, "") || "root";

  return (
    <footer
      className={cn(
        "h-6 w-full shrink-0 border-t border-border-hairline bg-surface-chrome px-3 flex items-center justify-between font-mono text-[11px] text-text-secondary select-none z-20",
        className
      )}
    >
      <div className="flex items-center gap-4 overflow-hidden text-ellipsis whitespace-nowrap">
        <span className="flex items-center gap-1.5">
          <span className="text-text-tertiary">capture:</span>
          <span className="text-text-primary font-medium">{captureName}</span>
        </span>

        <span className="flex items-center gap-1.5">
          <span className="text-text-tertiary">sha:</span>
          <span className="text-text-primary font-mono">{shortSha}</span>
        </span>

        <span className="flex items-center gap-1.5">
          <span className="text-text-tertiary">state:</span>
          <span
            className={cn(
              "font-medium",
              state.runStatus === "running" && "text-amber-sample",
              state.runStatus === "success" && "text-signal",
              state.runStatus === "error" && "text-severity-critical",
              state.runStatus === "idle" && "text-text-secondary"
            )}
          >
            {state.runStatus}
          </span>
        </span>

        <span className="flex items-center gap-1.5">
          <span className="text-text-tertiary">page:</span>
          <span className="text-text-primary">{path}</span>
        </span>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={onOpenHelp}
          className="text-text-tertiary hover:text-signal transition-colors focus:outline-none"
          title="Press ? for shortcut help"
        >
          ? help
        </button>
      </div>
    </footer>
  );
};
