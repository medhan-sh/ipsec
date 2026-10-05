import React from "react";
import { useNavigate } from "react-router-dom";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from "@/components/vendor/command";
import { useAppStore } from "@/context/store";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenJsonModal?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  open,
  onOpenChange,
  onOpenJsonModal,
}) => {
  const navigate = useNavigate();
  const { state, selectCapture, analyzeSelected, refreshCaptures } = useAppStore();

  const handleSelectPage = (path: string) => {
    navigate(path);
    onOpenChange(false);
  };

  const handleAnalyze = () => {
    onOpenChange(false);
    analyzeSelected();
  };

  const handleSwitchCapture = (name: string) => {
    selectCapture(name);
    onOpenChange(false);
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Type a command or jump to page..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Navigation">
          <CommandItem onSelect={() => handleSelectPage("/app/overview")}>
            <span>1 Overview</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelectPage("/app/findings")}>
            <span>2 Findings</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelectPage("/app/tunnels")}>
            <span>3 Tunnels</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelectPage("/app/claims")}>
            <span>4 Claims</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelectPage("/app/coverage")}>
            <span>5 Coverage</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelectPage("/__gallery")}>
            <span>Component Gallery</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Actions">
          <CommandItem onSelect={handleAnalyze} disabled={!state.selectedCapture}>
            <span>Analyze current capture</span>
          </CommandItem>
          <CommandItem
            onSelect={() => {
              onOpenChange(false);
              if (state.selectedCapture) {
                window.open(`/api/report/${encodeURIComponent(state.selectedCapture)}`, "_blank");
              }
            }}
            disabled={!state.selectedCapture}
          >
            <span>Open HTML report in new tab</span>
          </CommandItem>
          <CommandItem
            onSelect={() => {
              onOpenChange(false);
              onOpenJsonModal?.();
            }}
            disabled={!state.loadedDocument}
          >
            <span>View findings.json document</span>
          </CommandItem>
          <CommandItem
            onSelect={() => {
              onOpenChange(false);
              refreshCaptures();
            }}
          >
            <span>Refresh captures list</span>
          </CommandItem>
        </CommandGroup>

        {state.captures.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Switch Capture">
              {state.captures.map((c) => (
                <CommandItem key={c.name} onSelect={() => handleSwitchCapture(c.name)}>
                  <span>{c.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
};
