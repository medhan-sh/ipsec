import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "@/context/store";
import { SampleDataChip } from "@/components/app/SampleDataChip";
import { SystemCheck } from "./components/SystemCheck";
import { CaptureDropzone } from "./components/CaptureDropzone";
import { TiersReference } from "./components/TiersReference";

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { state } = useAppStore();
  const [serverError, setServerError] = useState(false);

  // If statusPayload failed to fetch and isn't mock mode
  useEffect(() => {
    if (!state.statusPayload && state.dataSource === "real") {
      // Small timeout to allow initial fetch before flagging unreachable
      const timer = setTimeout(() => {
        if (!state.statusPayload) {
          setServerError(true);
        }
      }, 800);
      return () => clearTimeout(timer);
    } else {
      setServerError(false);
    }
  }, [state.statusPayload, state.dataSource]);

  // Global key navigation for shortcuts (1-5 pages, / filter, : palette, ? help)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || "").toLowerCase();
      if (activeTag === "input" || activeTag === "textarea") return;

      if (e.key === "1") {
        e.preventDefault();
        navigate("/app/overview");
      } else if (e.key === "2") {
        e.preventDefault();
        navigate("/app/findings");
      } else if (e.key === "3") {
        e.preventDefault();
        navigate("/app/tunnels");
      } else if (e.key === "4") {
        e.preventDefault();
        navigate("/app/claims");
      } else if (e.key === "5") {
        e.preventDefault();
        navigate("/app/coverage");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate]);

  return (
    <main className="min-h-screen w-full bg-surface-base text-text-primary font-mono flex flex-col items-center justify-start pt-16 md:pt-20 px-6 select-none">
      <div className="w-full max-w-[880px] flex flex-col gap-8 pb-16">
        {/* Section 1: Wordmark */}
        <section className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <h1 className="text-[28px] font-bold tracking-tight text-signal font-mono leading-none">
              UMBRA
            </h1>
            {state.dataSource === "mock" && <SampleDataChip />}
          </div>
          <p className="text-xs text-text-secondary font-mono">
            Passive IPsec analysis. Reads captures, decrypts nothing, touches no network.
          </p>
        </section>

        {/* Section 2: System Check */}
        <SystemCheck
          status={state.statusPayload}
          capturesCount={state.captures.length}
          serverError={serverError}
        />

        {/* Section 3: Open a Capture */}
        <CaptureDropzone />

        {/* Section 4: How to Read the Results */}
        <TiersReference />

        {/* Section 5: Footer shortcuts */}
        <footer className="text-[11px] text-text-tertiary pt-4 border-t border-border-hairline flex flex-wrap items-center justify-between gap-2">
          <span>1-5 pages · a analyze · r refresh · / filter · : palette · ? help</span>
          <span className="text-text-tertiary/70">local offline forensic console</span>
        </footer>
      </div>
    </main>
  );
};
