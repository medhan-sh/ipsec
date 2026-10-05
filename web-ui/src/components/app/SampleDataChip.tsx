import React from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface SampleDataChipProps {
  className?: string;
}

export const SampleDataChip: React.FC<SampleDataChipProps> = ({ className }) => {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-data border border-amber-sample/50 bg-amber-sample/10 px-2 py-0.5 font-mono text-[11px] font-semibold text-amber-sample select-none",
        className
      )}
      title="Sample/mock data is active. Not real analysis from captures/."
    >
      <AlertTriangle className="h-3 w-3 shrink-0" />
      <span>sample data</span>
    </span>
  );
};
