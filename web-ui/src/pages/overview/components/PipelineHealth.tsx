import React from "react";
import { CoverageMeta } from "@/api/types";
import { SectionHeader } from "@/components/app/SectionHeader";
import { cn } from "@/lib/utils";

interface PipelineHealthProps {
  coverage: CoverageMeta;
}

export const PipelineHealth: React.FC<PipelineHealthProps> = ({ coverage }) => {
  const tsharkClean = Boolean(coverage.tshark_exit_clean);
  const skippedOk = coverage.packets_skipped === 0;

  const reqObserved = Boolean(coverage.ike_sa_init_request_observed);
  const respObserved = Boolean(coverage.ike_sa_init_response_observed);
  const handshakeOk = reqObserved && respObserved;

  const tunnelsMissing = coverage.esp_tunnels_missing_a_direction || 0;
  const tunnelsOk = tunnelsMissing === 0;

  return (
    <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-col gap-3 font-mono text-xs select-none">
      <SectionHeader title="pipeline health" className="my-0 mb-1" />

      <div className="space-y-2">
        {/* Row 1: Dissector / TShark */}
        <div className="flex items-baseline justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full shrink-0",
                tsharkClean ? "bg-signal" : "bg-amber-sample"
              )}
            />
            <span className="text-text-secondary">tshark engine</span>
          </div>
          <span className="text-text-primary text-[11px] text-right truncate">
            {coverage.tshark_version || "4.4.18"} ({tsharkClean ? "clean exit" : "non-zero exit"})
          </span>
        </div>

        {/* Row 2: Packets skipped */}
        <div className="flex items-baseline justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full shrink-0",
                skippedOk ? "bg-signal" : "bg-amber-sample"
              )}
            />
            <span className="text-text-secondary">packets skipped</span>
          </div>
          <span
            className={cn(
              "text-[11px] tabular-nums",
              skippedOk ? "text-text-primary" : "text-amber-sample font-medium"
            )}
          >
            {coverage.packets_skipped.toLocaleString()}
          </span>
        </div>

        {/* Row 3: IKE SA_INIT Handshake */}
        <div className="flex items-baseline justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full shrink-0",
                handshakeOk ? "bg-signal" : "bg-amber-sample"
              )}
            />
            <span className="text-text-secondary">IKE SA_INIT handshake</span>
          </div>
          <span className="text-text-primary text-[11px] text-right">
            {reqObserved && respObserved
              ? "request & response observed"
              : reqObserved
              ? "request only (half handshake)"
              : respObserved
              ? "response only"
              : "not observed (mid-session)"}
          </span>
        </div>

        {/* Row 4: ESP Tunnels */}
        <div className="flex items-baseline justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full shrink-0",
                tunnelsOk ? "bg-signal" : "bg-amber-sample"
              )}
            />
            <span className="text-text-secondary">ESP tunnels</span>
          </div>
          <span className="text-text-primary text-[11px] text-right">
            <span className="tabular-nums font-medium">{coverage.esp_tunnels_total}</span> total
            {tunnelsMissing > 0 ? (
              <span className="text-amber-sample ml-1">
                ({tunnelsMissing} missing a direction)
              </span>
            ) : (
              <span className="text-text-tertiary ml-1">(all bidirectional)</span>
            )}
          </span>
        </div>
      </div>
    </div>
  );
};
