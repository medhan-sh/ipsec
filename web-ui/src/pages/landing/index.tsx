import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAppStore } from "@/context/store";
import { SampleDataChip } from "@/components/app/SampleDataChip";
import { SystemCheck } from "./components/SystemCheck";
import { CaptureDropzone } from "./components/CaptureDropzone";
import { TiersReference } from "./components/TiersReference";
import { HeroVisual } from "./components/HeroVisual";
import { Button } from "@/components/vendor/button";
import { ArrowRight, Terminal, HelpCircle } from "lucide-react";
import { ShortcutDialog } from "@/components/shell/ShortcutDialog";

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { state } = useAppStore();
  const [serverError, setServerError] = useState(false);
  const [shortcutOpen, setShortcutOpen] = useState(false);

  // If statusPayload failed to fetch and isn't mock mode
  useEffect(() => {
    if (!state.statusPayload && state.dataSource === "real") {
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
      } else if (e.key === "?") {
        e.preventDefault();
        setShortcutOpen(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate]);

  return (
    <div className="min-h-screen w-full bg-[#000000] text-text-primary font-mono flex flex-col items-center justify-between select-none relative">
      {/* Precision Floating Navbar */}
      <header className="sticky top-0 z-30 w-full border-b border-border-hairline bg-[#000000]/90 backdrop-blur-sm px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <Link
            to="/"
            className="flex items-center gap-2 text-sm font-bold tracking-widest text-signal hover:text-signal/90 transition-colors"
          >
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-signal shadow-glow animate-pulse" />
            UMBRA
          </Link>
          <span className="hidden sm:inline-block text-border-hairline">/</span>
          <span className="hidden sm:inline-block text-[11px] text-text-tertiary tracking-wider uppercase">
            Passive IPsec Forensics
          </span>
          {state.dataSource === "mock" && <SampleDataChip />}
        </div>

        {/* Quick Nav & Launch */}
        <div className="flex items-center gap-3 sm:gap-4">
          <nav className="hidden md:flex items-center gap-4 text-xs text-text-secondary">
            <Link
              to="/app/overview"
              className="hover:text-signal transition-colors flex items-center gap-1.5"
            >
              <span>overview</span>
              <kbd className="text-[10px] px-1 py-0.2 bg-surface-raised rounded-data border border-border-hairline text-text-tertiary">
                1
              </kbd>
            </Link>
            <Link
              to="/app/findings"
              className="hover:text-signal transition-colors flex items-center gap-1.5"
            >
              <span>findings</span>
              <kbd className="text-[10px] px-1 py-0.2 bg-surface-raised rounded-data border border-border-hairline text-text-tertiary">
                2
              </kbd>
            </Link>
            <Link
              to="/app/tunnels"
              className="hover:text-signal transition-colors flex items-center gap-1.5"
            >
              <span>tunnels</span>
              <kbd className="text-[10px] px-1 py-0.2 bg-surface-raised rounded-data border border-border-hairline text-text-tertiary">
                3
              </kbd>
            </Link>
            <Link
              to="/app/claims"
              className="hover:text-signal transition-colors flex items-center gap-1.5"
            >
              <span>claims</span>
              <kbd className="text-[10px] px-1 py-0.2 bg-surface-raised rounded-data border border-border-hairline text-text-tertiary">
                4
              </kbd>
            </Link>
            <Link
              to="/app/coverage"
              className="hover:text-signal transition-colors flex items-center gap-1.5"
            >
              <span>coverage</span>
              <kbd className="text-[10px] px-1 py-0.2 bg-surface-raised rounded-data border border-border-hairline text-text-tertiary">
                5
              </kbd>
            </Link>
          </nav>

          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-text-tertiary hover:text-text-primary"
            onClick={() => setShortcutOpen(true)}
            title="Keyboard shortcuts (?)"
          >
            <HelpCircle className="h-3.5 w-3.5" />
          </Button>

          <Button
            variant="signal"
            size="sm"
            className="h-7 text-xs font-mono tracking-wider font-semibold"
            onClick={() => navigate("/app/overview")}
          >
            ENTER WORKSPACE
            <ArrowRight className="h-3 w-3 ml-1.5" />
          </Button>
        </div>
      </header>

      {/* Main Forensic Viewport */}
      <main className="w-full max-w-5xl px-6 py-8 sm:py-12 flex flex-col gap-10">
        {/* Hero Section: Minimalist Maximalism */}
        <section className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-[10px] tracking-widest uppercase text-signal-dim">
              <Terminal className="h-3 w-3" />
              <span>Offline Cryptographic Evidence Instrument</span>
              <span className="text-border-hairline">|</span>
              <span className="text-text-tertiary">Schema 1.0</span>
            </div>

            <h1 className="text-3xl sm:text-5xl md:text-6xl font-bold tracking-tight text-text-primary leading-[1.05]">
              EVIDENCE EMERGING <br />
              <span className="text-signal">FROM DARKNESS.</span>
            </h1>

            <p className="max-w-2xl text-xs sm:text-sm text-text-secondary font-sans leading-relaxed pt-1">
              Passive IPsec observation console. Derives cryptographic posture,
              DH group invariants, and ESP parameters from wire evidence without
              decrypting traffic or making external calls.
            </p>
          </div>

          {/* Central Architectural Topology Visual */}
          <HeroVisual />
        </section>

        {/* Capture Inlet Section */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 flex flex-col gap-4">
            <CaptureDropzone />
          </div>

          <div className="lg:col-span-5 flex flex-col gap-6">
            {/* Real System Check Probes */}
            <SystemCheck
              status={state.statusPayload}
              capturesCount={state.captures.length}
              serverError={serverError}
            />

            {/* Provenance Tier Lattice Reference */}
            <TiersReference />
          </div>
        </section>
      </main>

      {/* Terminal Discipline Status Bar Footer */}
      <footer className="w-full border-t border-border-hairline bg-[#000000] px-6 py-2.5 text-[11px] text-text-tertiary flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-signal" />
            <span>LOCAL FORENSIC CONSOLE</span>
          </span>
          <span className="hidden sm:inline text-border-hairline">|</span>
          <span className="hidden sm:inline">ZERO RUNTIME NETWORK CALLS</span>
        </div>
        <div className="flex items-center gap-3">
          <span>SHORTCUTS: 1-5 pages · a analyze · r refresh · ? help</span>
        </div>
      </footer>

      {/* Keyboard Shortcut Modal */}
      <ShortcutDialog open={shortcutOpen} onOpenChange={setShortcutOpen} />
    </div>
  );
};
