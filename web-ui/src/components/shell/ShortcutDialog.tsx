import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/vendor/dialog";

interface ShortcutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const SHORTCUTS = [
  { key: "1 – 5", desc: "Jump to page (1 Overview, 2 Findings, 3 Tunnels, 4 Claims, 5 Coverage)" },
  { key: "a", desc: "Analyze selected capture" },
  { key: "r", desc: "Refresh captures list" },
  { key: "/", desc: "Focus filter bar" },
  { key: "Esc", desc: "Clear filter or close overlay/drawer" },
  { key: "j", desc: "View raw findings JSON document" },
  { key: ": / Ctrl+K", desc: "Open command palette" },
  { key: "?", desc: "Open this keyboard shortcut reference" },
  { key: "↑ / ↓", desc: "Navigate table selection" },
  { key: "Enter", desc: "Open selected finding or tunnel details" },
];

export const ShortcutDialog: React.FC<ShortcutDialogProps> = ({
  open,
  onOpenChange,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md font-mono">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold lowercase">
            keyboard shortcuts
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-2 mt-2">
          {SHORTCUTS.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between text-xs py-1 border-b border-border-hairline last:border-b-0"
            >
              <span className="text-text-secondary font-sans">{item.desc}</span>
              <kbd className="rounded-data bg-surface-raised px-1.5 py-0.5 border border-border-hairline text-signal font-mono text-[11px] shrink-0 ml-3">
                {item.key}
              </kbd>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
};
