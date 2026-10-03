import React from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { CaptureMeta } from "@/api/types";
import { SectionHeader } from "@/components/app/SectionHeader";
import { Mono } from "@/components/app/Mono";
import { toast } from "sonner";

interface CaptureFactsProps {
  capture: CaptureMeta;
}

export const CaptureFacts: React.FC<CaptureFactsProps> = ({ capture }) => {
  const shortSha =
    capture.sha256 && capture.sha256.length >= 18
      ? `${capture.sha256.slice(0, 10)}...${capture.sha256.slice(-8)}`
      : capture.sha256 || "unknown";

  return (
    <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col gap-3 font-mono text-xs select-none">
      <SectionHeader title="capture facts" className="my-0 mb-1" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2.5">
        <div className="flex flex-col gap-0.5">
          <span className="text-text-tertiary text-[11px]">filename</span>
          <span className="text-text-primary font-medium truncate" title={capture.filename}>
            {capture.filename}
          </span>
        </div>

        <div className="flex flex-col gap-0.5">
          <span className="text-text-tertiary text-[11px]">sha256 digest</span>
          <div
            title={`Full SHA-256: ${capture.sha256} (click to copy)`}
            onClick={() => {
              navigator.clipboard.writeText(capture.sha256);
              toast.success(`Copied SHA-256: ${capture.sha256.slice(0, 16)}...`);
            }}
            className="cursor-pointer group flex items-center gap-1 w-fit"
          >
            <Mono
              value={shortSha}
              copyable={false}
              className="text-[11px] group-hover:border-border-strong group-hover:bg-surface-raised"
            />
          </div>
        </div>

        <div className="flex flex-col gap-0.5">
          <span className="text-text-tertiary text-[11px]">packets</span>
          <span className="text-text-primary tabular-nums font-medium">
            {capture.packet_count.toLocaleString()}
          </span>
        </div>

        <div className="flex flex-col gap-0.5">
          <span className="text-text-tertiary text-[11px]">duration</span>
          <span className="text-text-primary tabular-nums font-medium">
            {capture.duration_s.toFixed(2)}s
          </span>
        </div>
      </div>

      {/* Truncation Integrity State */}
      <div className="pt-2 border-t border-border-hairline">
        {capture.truncated ? (
          <div className="p-2.5 rounded-data border border-amber-sample/40 bg-amber-sample/10 text-amber-sample text-xs flex items-start gap-2.5">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-sample" />
            <div className="space-y-0.5">
              <span className="font-semibold block text-amber-sample">
                Capture truncated
              </span>
              <p className="text-text-secondary font-sans text-xs leading-relaxed">
                Packets were cut short at capture time (snaplen or premature capture halt).
                Framing arithmetic, cipher candidate set elimination, and policy verdicts
                may be incomplete or forced to abstain.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-text-secondary text-[11px]">
            <CheckCircle2 className="h-3.5 w-3.5 text-signal shrink-0" />
            <span className="text-text-primary">complete</span>
            <span className="text-text-tertiary">— no packet truncation detected</span>
          </div>
        )}
      </div>
    </div>
  );
};
