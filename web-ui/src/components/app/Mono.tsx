import React, { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface MonoProps {
  value: string | number;
  label?: string;
  copyable?: boolean;
  className?: string;
}

export const Mono: React.FC<MonoProps> = ({
  value,
  label,
  copyable = true,
  className,
}) => {
  const [copied, setCopied] = useState(false);
  const textVal = String(value);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!copyable) return;
    navigator.clipboard.writeText(textVal);
    setCopied(true);
    toast.success(`Copied: ${textVal}`);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <span
      onClick={copyable ? handleCopy : undefined}
      className={cn(
        "inline-flex items-center gap-1 rounded-data bg-surface-raised px-1.5 py-0.5 font-mono text-xs border border-border-hairline text-text-primary transition-colors",
        copyable && "cursor-pointer hover:border-border-strong hover:bg-surface-panel group select-none",
        className
      )}
      title={copyable ? "Click to copy" : undefined}
    >
      {label && <span className="text-text-tertiary mr-0.5">{label}:</span>}
      <span className="tabular-nums font-mono">{textVal}</span>
      {copyable && (
        <span className="opacity-0 group-hover:opacity-100 transition-opacity ml-0.5">
          {copied ? (
            <Check className="h-3 w-3 text-signal" />
          ) : (
            <Copy className="h-3 w-3 text-text-tertiary" />
          )}
        </span>
      )}
    </span>
  );
};
