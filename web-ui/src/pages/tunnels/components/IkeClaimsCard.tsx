import React from "react";
import { ClaimItem } from "@/api/types";
import { formatClaimDisplayValue } from "../types";
import { TierBadge } from "@/components/app/TierBadge";
import { ConfidenceMeter } from "@/components/app/ConfidenceMeter";
import { Mono } from "@/components/app/Mono";
import { AlertTriangle, KeyRound } from "lucide-react";

interface IkeClaimsCardProps {
  claims: ClaimItem[];
}

export const IkeClaimsCard: React.FC<IkeClaimsCardProps> = ({ claims }) => {
  return (
    <div className="rounded-data border border-border-hairline bg-surface-panel p-4 space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border-hairline">
        <div className="flex items-center gap-2">
          <KeyRound className="h-4 w-4 text-signal" />
          <span className="text-xs uppercase tracking-wider text-text-secondary font-semibold">
            IKE handshake & suite claims
          </span>
          <span className="text-xs text-text-tertiary tabular-nums">
            ({claims.length} claims observed)
          </span>
        </div>

        <span className="text-[11px] text-text-tertiary">
          control plane parameters (dissected via tshark)
        </span>
      </div>

      {claims.length === 0 ? (
        <div className="p-4 rounded-data border border-border-hairline bg-surface-base text-xs text-text-tertiary">
          No IKE handshake claims observed in this capture. (Handshake may not have been present in the pcap window).
        </div>
      ) : (
        <div className="divide-y divide-border-hairline rounded-data border border-border-hairline bg-surface-base overflow-hidden">
          {claims.map((claim, idx) => {
            const displayVal = formatClaimDisplayValue(claim.value);

            return (
              <div
                key={`${claim.field}-${idx}`}
                className="p-3.5 space-y-2 hover:bg-surface-raised/40 transition-colors"
              >
                {/* Field name + Tier & Confidence */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-text-primary">
                      {claim.field}
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <TierBadge tier={claim.tier} />
                    <ConfidenceMeter
                      tier={claim.tier}
                      confidence={claim.confidence}
                    />
                  </div>
                </div>

                {/* Value row */}
                <div className="flex items-baseline gap-2 text-xs">
                  <span className="text-text-tertiary text-[11px]">value:</span>
                  <span className="text-text-primary font-medium">
                    {displayVal}
                  </span>
                </div>

                {/* Method */}
                {claim.method && (
                  <div className="text-[11px] text-text-secondary font-sans leading-relaxed">
                    <span className="text-text-tertiary font-mono text-[10px] uppercase mr-1.5">
                      method:
                    </span>
                    {claim.method}
                  </div>
                )}

                {/* Evidence Frames & Caveats */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                  {claim.evidence && claim.evidence.length > 0 ? (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-text-tertiary text-[10px] uppercase">
                        evidence frames:
                      </span>
                      {claim.evidence.map((f) => (
                        <Mono key={f} label="frame" value={f} />
                      ))}
                    </div>
                  ) : (
                    <span className="text-[10px] text-text-tertiary">
                      no frame evidence
                    </span>
                  )}

                  {claim.caveats && claim.caveats.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[11px] text-amber-sample">
                      <AlertTriangle className="h-3 w-3 shrink-0" />
                      <span>{claim.caveats.join("; ")}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
