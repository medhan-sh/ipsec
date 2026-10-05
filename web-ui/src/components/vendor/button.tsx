import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: "default" | "outline" | "ghost" | "link" | "signal";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    const variantStyles = {
      default:
        "bg-surface-raised text-text-primary border border-border-hairline hover:border-border-strong hover:bg-surface-panel active:bg-surface-base",
      signal:
        "bg-signal text-black font-semibold border border-signal hover:bg-[#00e673] active:bg-[#00cc66]",
      outline:
        "bg-transparent text-text-primary border border-border-hairline hover:border-border-strong hover:bg-surface-raised",
      ghost:
        "bg-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised",
      link:
        "text-signal underline-offset-4 hover:underline p-0 h-auto font-normal",
    }[variant];

    const sizeStyles = {
      default: "h-8 px-3 py-1.5 text-xs",
      sm: "h-7 px-2.5 text-xs",
      lg: "h-9 px-4 text-sm",
      icon: "h-8 w-8",
    }[size];

    return (
      <Comp
        className={cn(
          "inline-flex items-center justify-center font-mono rounded-data transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal focus-visible:shadow-focus disabled:pointer-events-none disabled:opacity-40 select-none",
          variantStyles,
          sizeStyles,
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
