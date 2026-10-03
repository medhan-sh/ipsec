import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "@/context/store";
import { TierGlyph } from "@/components/app/TierGlyph";
import { Button } from "@/components/vendor/button";
import { SampleDataChip } from "@/components/app/SampleDataChip";
import { cn } from "@/lib/utils";

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { state, selectCapture, loadSampleData } = useAppStore();
  const [skipped, setSkipped] = useState(false);
  const [revealedCount, setRevealedCount] = useState(1);

  const status = state.statusPayload;

  const items = [
    { label: "analyzer", value: status?.analyzer || "0.1.0", ok: true },
    {
      label: "tshark",
      value: status?.tshark?.available
        ? status.tshark.version
        : status?.tshark?.error || "not detected",
      ok: !!status?.tshark?.available,
    },
    { label: "rules", value: `${status?.rules || 15} loaded`, ok: true },
    { label: "captures", value: `${state.captures.length} in captures/`, ok: true },
    { label: "network", value: "none (offline local)", ok: true },
  ];

  useEffect(() => {
    if (skipped) {
      setRevealedCount(items.length);
      return;
    }
    const timer = setInterval(() => {
      setRevealedCount((prev) => {
        if (prev >= items.length) {
          clearInterval(timer);
          return items.length;
        }
        return prev + 1;
      });
    }, 120);
    return () => clearInterval(timer);
  }, [skipped, items.length]);

  const handleOpenCapture = async (name: string) => {
    await selectCapture(name);
    navigate("/app/overview");
  };

  return (
    <div
      onClick={() => setSkipped(true)}
      onKeyDown={() => setSkipped(true)}
      tabIndex={0}
      className="min-h-screen w-screen bg-surface-base text-text-primary font-mono flex flex-col items-center justify-start pt-20 px-6 select-none focus:outline-none"
    >
      <div className="w-full max-w-2xl flex flex-col gap-8">
        {/* Section 1: Wordmark */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight text-signal font-mono">
              UMBRA
            </h1>
            {state.dataSource === "mock" && <SampleDataChip />}
          </div>
          <p className="text-xs text-text-secondary font-mono">
            Passive IPsec analysis. Reads captures, decrypts nothing, touches no network.
          </p>
        </div>

        {/* Section 2: System Check */}
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel/60 font-mono text-xs flex flex-col gap-2">
          <span className="text-[10px] text-text-tertiary uppercase tracking-wider font-semibold">
            system status
          </span>

          <div className="space-y-1.5 mt-1">
            {items.map((item, idx) => {
              const isVisible = skipped || idx < revealedCount;
              return (
                <div
                  key={item.label}
                  className={cn(
                    "flex items-center gap-2 transition-opacity duration-150 motion-reduce:!opacity-100",
                    isVisible ? "opacity-100" : "opacity-0 pointer-events-none"
                  )}
                >
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      item.ok ? "bg-signal" : "bg-amber-sample"
                    )}
                  />
                  <span className="text-text-secondary">{item.label}</span>
                  <span className="text-text-primary">{item.value}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 3: Open Capture */}
        <div className="flex flex-col gap-3">
          <span className="text-xs text-text-secondary font-semibold">
            open a capture
          </span>

          {state.captures.length > 0 ? (
            <div className="space-y-1.5">
              {state.captures.slice(0, 5).map((cap) => (
                <div
                  key={cap.name}
                  onClick={() => handleOpenCapture(cap.name)}
                  className="p-3 rounded-data border border-border-hairline bg-surface-panel hover:bg-surface-raised hover:border-border-strong cursor-pointer transition-colors flex items-center justify-between text-xs"
                >
                  <span className="font-medium text-text-primary">{cap.name}</span>
                  <span className="text-text-tertiary">{(cap.size / 1024).toFixed(0)} KB</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 rounded-data border border-dashed border-border-hairline text-center text-xs text-text-tertiary">
              No captures yet. Drop a .pcap file here, or put files in captures/ and press r.
            </div>
          )}

          <div className="flex items-center gap-3 mt-2">
            <Button
              variant="signal"
              onClick={() => {
                if (state.captures[0]) handleOpenCapture(state.captures[0].name);
                else navigate("/app/overview");
              }}
            >
              Enter console
            </Button>

            {state.dataSource === "mock" && (
              <Button
                variant="outline"
                onClick={async () => {
                  await loadSampleData();
                  navigate("/app/overview");
                }}
              >
                Load sample data
              </Button>
            )}
          </div>
        </div>

        {/* Section 4: Tiers Explanation */}
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel/40 flex flex-col gap-2.5 text-xs">
          <span className="text-[10px] text-text-tertiary uppercase tracking-wider font-semibold">
            how to read the results
          </span>

          <div className="space-y-2 mt-1">
            <div className="flex items-start gap-2.5">
              <TierGlyph tier="OBSERVED" size={14} className="mt-0.5" />
              <div>
                <span className="text-text-primary font-medium">OBSERVED: </span>
                <span className="text-text-secondary font-sans text-xs">
                  Read directly from the handshake. Certain.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <TierGlyph tier="INFERRED_SIDE_CHANNEL" size={14} className="mt-0.5" />
              <div>
                <span className="text-text-primary font-medium">INFERRED_SIDE_CHANNEL: </span>
                <span className="text-text-secondary font-sans text-xs">
                  Deduced from sizes and timing of what is visible.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <TierGlyph tier="INFERRED_IMPLEMENTATION_DEFAULT" size={14} className="mt-0.5" />
              <div>
                <span className="text-text-primary font-medium">INFERRED_IMPLEMENTATION_DEFAULT: </span>
                <span className="text-text-secondary font-sans text-xs">
                  Assumed from how this implementation usually behaves.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <TierGlyph tier="ML_PREDICTION" size={14} className="mt-0.5" />
              <div>
                <span className="text-text-primary font-medium">ML_PREDICTION: </span>
                <span className="text-text-secondary font-sans text-xs">
                  A statistical prediction.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <TierGlyph tier="NOT_OBSERVABLE" size={14} className="mt-0.5" />
              <div>
                <span className="text-text-tertiary font-medium">NOT_OBSERVABLE: </span>
                <span className="text-text-tertiary font-sans text-xs">
                  The capture cannot tell us. We say so rather than guess.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Section 5: Footer shortcuts */}
        <div className="text-[11px] text-text-tertiary pb-12 pt-2 border-t border-border-hairline">
          1-5 pages · a analyze · r refresh · / filter · : palette · ? help
        </div>
      </div>
    </div>
  );
};
