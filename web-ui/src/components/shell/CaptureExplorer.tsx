import React, { useState, useRef } from "react";
import { Folder, RefreshCw, Upload, CheckCircle2, AlertCircle } from "lucide-react";
import { useAppStore } from "@/context/store";
import { uploadCapture } from "@/api/client";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface CaptureExplorerProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
}

export const CaptureExplorer: React.FC<CaptureExplorerProps> = ({
  collapsed = false,
  className,
}) => {
  const { state, selectCapture, refreshCaptures } = useAppStore();
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    await processUpload(files[0]);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    await processUpload(files[0]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const processUpload = async (file: File) => {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (ext !== ".pcap" && ext !== ".pcapng") {
      toast.error("Invalid file: only .pcap and .pcapng are accepted.");
      return;
    }

    setIsUploading(true);
    try {
      await uploadCapture(file, false);
      toast.success(`Uploaded ${file.name}`);
      await refreshCaptures();
      await selectCapture(file.name);
    } catch (err: any) {
      if (err.message?.includes("already exists")) {
        if (confirm(`Capture '${file.name}' already exists. Overwrite?`)) {
          try {
            await uploadCapture(file, true);
            toast.success(`Overwritten ${file.name}`);
            await refreshCaptures();
            await selectCapture(file.name);
          } catch (e: any) {
            toast.error(`Upload error: ${e.message}`);
          }
        }
      } else {
        toast.error(`Upload error: ${err.message}`);
      }
    } finally {
      setIsUploading(false);
    }
  };

  if (collapsed) {
    return (
      <div className={cn("w-12 bg-surface-panel border-r border-border-hairline p-2 flex flex-col items-center select-none font-mono", className)}>
        <Folder className="h-5 w-5 text-text-tertiary mb-4" />
      </div>
    );
  }

  return (
    <aside
      className={cn(
        "w-64 shrink-0 bg-surface-panel border-r border-border-hairline flex flex-col font-mono select-none text-xs h-full",
        className
      )}
    >
      <div className="h-10 px-3 border-b border-border-hairline flex items-center justify-between">
        <span className="text-text-tertiary uppercase tracking-wider text-[10px] font-semibold flex items-center gap-1.5">
          <Folder className="h-3.5 w-3.5 text-text-secondary" />
          captures ({state.captures.length})
        </span>
        <button
          onClick={refreshCaptures}
          disabled={state.isLoadingCaptures}
          className="text-text-tertiary hover:text-signal transition-colors p-1 disabled:opacity-40"
          title="Refresh captures (r)"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", state.isLoadingCaptures && "animate-spin")} />
        </button>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleFileDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "m-2 p-3 rounded-data border border-dashed text-center cursor-pointer transition-colors duration-150",
          isDragOver
            ? "border-signal bg-signal-faint text-signal"
            : "border-border-hairline hover:border-border-strong text-text-tertiary hover:text-text-secondary",
          isUploading && "opacity-50 pointer-events-none"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pcap,.pcapng"
          onChange={handleFileSelect}
          className="hidden"
        />
        <Upload className="h-4 w-4 mx-auto mb-1 opacity-70" />
        <span className="text-[10px] block">
          {isUploading ? "uploading..." : "drop .pcap / click to upload"}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-1 space-y-0.5">
        {state.captures.length === 0 ? (
          <div className="p-4 text-center text-text-tertiary text-[11px] font-sans">
            No captures found in captures/. Drop a .pcap above.
          </div>
        ) : (
          state.captures.map((capture) => {
            const isSelected = state.selectedCapture === capture.name;
            const criticalCount = capture.severity_counts?.critical || 0;
            const highCount = capture.severity_counts?.high || 0;

            return (
              <div
                key={capture.name}
                onClick={() => selectCapture(capture.name)}
                className={cn(
                  "px-2.5 py-2 rounded-data cursor-pointer transition-colors border",
                  isSelected
                    ? "bg-signal-faint border-signal/50 text-text-primary border-l-2 border-l-signal"
                    : "border-transparent text-text-secondary hover:bg-surface-raised hover:text-text-primary"
                )}
              >
                <div className="flex items-center justify-between text-[11px] font-medium truncate">
                  <span className="truncate">{capture.name}</span>
                  {capture.has_findings && (
                    <CheckCircle2 className="h-3 w-3 text-signal shrink-0 ml-1" />
                  )}
                </div>

                <div className="flex items-center justify-between text-[10px] text-text-tertiary mt-1">
                  <span>{(capture.size / 1024).toFixed(0)} KB</span>
                  {(criticalCount > 0 || highCount > 0) && (
                    <span className="flex items-center gap-1 text-severity-critical">
                      <AlertCircle className="h-2.5 w-2.5" />
                      {criticalCount + highCount} alerts
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
