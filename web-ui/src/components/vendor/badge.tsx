import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "signal" | "warning";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantStyles = {
    default: "bg-surface-raised text-text-primary border-border-hairline",
    secondary: "bg-surface-panel text-text-secondary border-border-hairline",
    outline: "text-text-primary border-border-hairline bg-transparent",
    signal: "bg-signal-faint text-signal border-signal/40",
    warning: "bg-amber-sample/10 text-amber-sample border-amber-sample/40",
  }[variant];

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-data border px-2 py-0.5 text-xs font-mono font-medium transition-colors",
        variantStyles,
        className
      )}
      {...props}
    />
  );
}

export { Badge };
