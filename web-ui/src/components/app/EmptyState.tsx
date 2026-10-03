import React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/vendor/button";

interface EmptyStateProps {
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No data available",
  message = "No capture analyzed yet. Pick one on the left, then choose Analyze capture.",
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-start justify-center p-8 rounded-data border border-border-hairline bg-surface-panel/50 font-mono text-left max-w-xl",
        className
      )}
    >
      <span className="text-text-tertiary text-xs mb-1">[empty]</span>
      <h3 className="text-sm font-semibold text-text-primary mb-2">{title}</h3>
      <p className="text-xs text-text-secondary mb-4 font-sans leading-relaxed">{message}</p>
      {actionLabel && onAction && (
        <Button variant="outline" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
