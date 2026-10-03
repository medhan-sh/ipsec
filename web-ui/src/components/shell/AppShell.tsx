import React, { useState, useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ShieldAlert,
  GitCommit,
  FileCheck2,
  PieChart,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useAppStore } from "@/context/store";
import { TopBar } from "./TopBar";
import { CaptureExplorer } from "./CaptureExplorer";
import { StatusBar } from "@/components/app/StatusBar";
import { ShortcutDialog } from "./ShortcutDialog";
import { CommandPalette } from "./CommandPalette";
import { Toaster } from "@/components/vendor/sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/vendor/dialog";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { path: "/app/overview", label: "overview", icon: LayoutDashboard, shortcut: "1" },
  { path: "/app/findings", label: "findings", icon: ShieldAlert, shortcut: "2" },
  { path: "/app/tunnels", label: "tunnels", icon: GitCommit, shortcut: "3" },
  { path: "/app/claims", label: "claims", icon: FileCheck2, shortcut: "4" },
  { path: "/app/coverage", label: "coverage", icon: PieChart, shortcut: "5" },
];

export const AppShell: React.FC = () => {
  const navigate = useNavigate();
  const { state, analyzeSelected, refreshCaptures } = useAppStore();

  const [explorerCollapsed, setExplorerCollapsed] = useState(() => {
    if (typeof window !== "undefined" && window.innerWidth < 768) {
      return true;
    }
    return false;
  });
  const [shortcutOpen, setShortcutOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [jsonModalOpen, setJsonModalOpen] = useState(false);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || "").toLowerCase();
      const isInput = activeTag === "input" || activeTag === "textarea";

      // Palette toggle on Ctrl+K
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
        return;
      }

      if (isInput) return;

      if (e.key >= "1" && e.key <= "5") {
        const idx = parseInt(e.key, 10) - 1;
        if (NAV_ITEMS[idx]) {
          e.preventDefault();
          navigate(NAV_ITEMS[idx].path);
        }
      } else if (e.key === "a") {
        e.preventDefault();
        analyzeSelected();
      } else if (e.key === "r") {
        e.preventDefault();
        refreshCaptures();
      } else if (e.key === "j") {
        e.preventDefault();
        if (state.loadedDocument) setJsonModalOpen(true);
      } else if (e.key === "?") {
        e.preventDefault();
        setShortcutOpen(true);
      } else if (e.key === ":") {
        e.preventDefault();
        setPaletteOpen(true);
      } else if (e.key === "Escape") {
        setShortcutOpen(false);
        setPaletteOpen(false);
        setJsonModalOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate, state.loadedDocument, analyzeSelected, refreshCaptures]);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-surface-base text-text-primary font-mono select-none">
      <div className="flex flex-1 overflow-hidden">
        {/* Left Nav */}
        <nav className="w-14 shrink-0 bg-surface-chrome border-r border-border-hairline flex flex-col items-center py-3 z-20">
          <div className="text-signal font-bold text-sm tracking-widest mb-6">
            U
          </div>

          <div className="flex flex-col gap-2 w-full px-2">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    cn(
                      "flex flex-col items-center justify-center p-2 rounded-data text-text-secondary hover:text-text-primary hover:bg-surface-panel transition-colors relative group",
                      isActive && "text-signal bg-surface-raised border-l-2 border-l-signal"
                    )
                  }
                  title={`${item.label} (${item.shortcut})`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-[9px] mt-1 text-text-tertiary font-mono">
                    {item.shortcut}
                  </span>
                </NavLink>
              );
            })}
          </div>

          <div className="mt-auto flex flex-col items-center gap-2">
            <button
              onClick={() => setExplorerCollapsed((prev) => !prev)}
              className="text-text-tertiary hover:text-text-primary p-2 transition-colors"
              title={explorerCollapsed ? "Expand explorer" : "Collapse explorer"}
            >
              {explorerCollapsed ? (
                <PanelLeftOpen className="h-4 w-4" />
              ) : (
                <PanelLeftClose className="h-4 w-4" />
              )}
            </button>
          </div>
        </nav>

        {/* Capture Explorer Panel */}
        <CaptureExplorer collapsed={explorerCollapsed} />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <TopBar onOpenJson={() => setJsonModalOpen(true)} />

          <main className="flex-1 overflow-y-auto p-4 sm:p-6 bg-surface-base relative">
            {state.runStatus === "running" && (
              <div className="sticky top-0 left-0 right-0 z-20 h-[2px] bg-gradient-to-r from-transparent via-signal to-transparent animate-pulse -mt-4 sm:-mt-6 mb-4 sm:mb-6" />
            )}
            <Outlet />
          </main>
        </div>
      </div>

      {/* Pinned Bottom Status Bar */}
      <StatusBar onOpenHelp={() => setShortcutOpen(true)} />

      {/* Overlays */}
      <ShortcutDialog open={shortcutOpen} onOpenChange={setShortcutOpen} />
      <CommandPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        onOpenJsonModal={() => setJsonModalOpen(true)}
      />

      {/* JSON Viewer Modal */}
      <Dialog open={jsonModalOpen} onOpenChange={setJsonModalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col font-mono">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold lowercase">
              findings.json (schema {state.loadedDocument?.schema_version || "1.0"})
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-auto bg-surface-base p-4 rounded-data border border-border-hairline text-xs font-mono select-text text-text-secondary">
            <pre>{JSON.stringify(state.loadedDocument, null, 2)}</pre>
          </div>
        </DialogContent>
      </Dialog>

      <Toaster />
    </div>
  );
};
