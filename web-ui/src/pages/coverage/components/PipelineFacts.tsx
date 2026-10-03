import React from "react";
import { CoverageMeta, CaptureMeta } from "@/api/types";
import { Mono } from "@/components/app/Mono";
import { Terminal, ShieldCheck, Activity, Network, FileCode } from "lucide-react";
import { cn } from "@/lib/utils";

interface PipelineFactsProps {
  coverage: CoverageMeta;
  capture?: CaptureMeta;
  className?: string;
}

export const PipelineFacts: React.FC<PipelineFactsProps> = ({
  coverage,
  capture,
  className,
}) => {
  const isTsharkClean = coverage.tshark_exit_clean;
  const isSkippedClean = (coverage.packets_skipped || 0) === 0;
  const isHandshakeComplete =
    coverage.ike_sa_init_request_observed && coverage.ike_sa_init_response_observed;
  const isDirectionalityClean = (coverage.esp_tunnels_missing_a_direction || 0) === 0;
  const isTruncated = capture?.truncated ?? false;

  return (
    <div className={cn("space-y-3 font-mono", className)}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Fact 1: TShark dissector */}
        <div className="p-3.5 rounded-data border border-border-hairline bg-surface-panel flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="text-text-tertiary lowercase flex items-center gap-1.5">
              <Terminal className="h-3.5 w-3.5" />
              <span>tshark engine</span>
            </span>
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isTsharkClean ? "bg-signal shadow-[0_0_4px_rgba(0,255,127,0.5)]" : "bg-severity-critical"
              )}
            />
          </div>
          <div>
            <div className="text-sm font-semibold text-text-primary">
              v{coverage.tshark_version || "unknown"}
            </div>
            <div className="text-xs text-text-secondary mt-0.5">
              {isTsharkClean ? "exited cleanly (status 0)" : "non-zero exit status"}
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-border-hairline text-[11px] font-sans text-text-tertiary">
            Zero protocol dissectors hand-rolled.
          </div>
        </div>

        {/* Fact 2: Packet Ingest Integrity */}
        <div className="p-3.5 rounded-data border border-border-hairline bg-surface-panel flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="text-text-tertiary lowercase flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5" />
              <span>ingest integrity</span>
            </span>
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isSkippedClean && !isTruncated
                  ? "bg-signal shadow-[0_0_4px_rgba(0,255,127,0.5)]"
                  : "bg-amber-sample"
              )}
            />
          </div>
          <div>
            <div className="text-sm font-semibold text-text-primary tabular-nums">
              {coverage.packets_skipped || 0} packets skipped
            </div>
            <div className="text-xs text-text-secondary mt-0.5">
              {isTruncated ? "capture truncated by snaplen" : "untruncated stream"}
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-border-hairline text-[11px] font-sans text-text-tertiary">
            Strict packet framing validation.
          </div>
        </div>

        {/* Fact 3: SA_INIT Flags */}
        <div className="p-3.5 rounded-data border border-border-hairline bg-surface-panel flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="text-text-tertiary lowercase flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>sa_init flags</span>
            </span>
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isHandshakeComplete
                  ? "bg-signal shadow-[0_0_4px_rgba(0,255,127,0.5)]"
                  : "bg-amber-sample"
              )}
            />
          </div>
          <div>
            <div className="text-sm font-semibold text-text-primary">
              {isHandshakeComplete ? "bidirectional" : "unidirectional"}
            </div>
            <div className="text-xs text-text-secondary mt-0.5 space-x-1.5">
              <span className={coverage.ike_sa_init_request_observed ? "text-signal" : "text-text-tertiary"}>
                req: {coverage.ike_sa_init_request_observed ? "yes" : "no"}
              </span>
              <span>·</span>
              <span className={coverage.ike_sa_init_response_observed ? "text-signal" : "text-text-tertiary"}>
                resp: {coverage.ike_sa_init_response_observed ? "yes" : "no"}
              </span>
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-border-hairline text-[11px] font-sans text-text-tertiary">
            Negative conclusions require both halves.
          </div>
        </div>

        {/* Fact 4: ESP Tunnels & Directionality */}
        <div className="p-3.5 rounded-data border border-border-hairline bg-surface-panel flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="text-text-tertiary lowercase flex items-center gap-1.5">
              <Network className="h-3.5 w-3.5" />
              <span>esp tunnels</span>
            </span>
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isDirectionalityClean && (coverage.esp_tunnels_total || 0) > 0
                  ? "bg-signal shadow-[0_0_4px_rgba(0,255,127,0.5)]"
                  : (coverage.esp_tunnels_total || 0) === 0
                  ? "bg-text-tertiary"
                  : "bg-amber-sample"
              )}
            />
          </div>
          <div>
            <div className="text-sm font-semibold text-text-primary tabular-nums">
              {coverage.esp_tunnels_total || 0} tunnels tracked
            </div>
            <div className="text-xs text-text-secondary mt-0.5">
              {isDirectionalityClean
                ? "all directions paired"
                : `${coverage.esp_tunnels_missing_a_direction} missing return direction`}
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-border-hairline text-[11px] font-sans text-text-tertiary">
            Reciprocal SPI pairing analysis.
          </div>
        </div>
      </div>

      {/* Capture Telemetry Bar */}
      {capture && (
        <div className="p-3 rounded-data border border-border-hairline bg-surface-base flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-text-secondary">
          <div className="flex items-center gap-2 flex-wrap">
            <FileCode className="h-3.5 w-3.5 text-text-tertiary" />
            <span className="text-text-primary font-medium">{capture.filename}</span>
            <span className="text-text-tertiary">·</span>
            <span className="tabular-nums">{capture.packet_count.toLocaleString()} packets</span>
            <span className="text-text-tertiary">·</span>
            <span className="tabular-nums">{capture.duration_s.toFixed(2)}s duration</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-text-tertiary text-[11px]">sha256:</span>
            <Mono value={capture.sha256} copyable className="text-[11px]" />
          </div>
        </div>
      )}
    </div>
  );
};
