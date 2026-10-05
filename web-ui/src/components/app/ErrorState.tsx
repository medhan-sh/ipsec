import React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/vendor/button";

interface ErrorStateProps {
  title?: string;
  error?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Analysis failed",
  error = "Analysis failed: check that Docker or python analyzer is configured properly, then try again.",
  actionLabel = "Try again",
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-start justify-center p-6 rounded-data border border-severity-critical/30 bg-severity-critical/5 font-mono text-left max-w-xl",
        className
      )}
    >
      <span className="text-severity-critical text-xs font-semibold uppercase mb-1">
        [error]
      </span>
      <h3 className="text-sm font-semibold text-text-primary mb-2">{title}</h3>
      <p className="text-xs text-text-secondary mb-4 font-sans leading-relaxed">{error}</p>
      {actionLabel && onAction && (
        <Button variant="outline" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
