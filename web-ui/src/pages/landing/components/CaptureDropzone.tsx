import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FolderOpen, Play, CheckCircle2 } from "lucide-react";
import { useAppStore } from "@/context/store";
import { uploadCapture } from "@/api/client";
import { CaptureItem } from "@/api/types";
import { Button } from "@/components/vendor/button";
import { SeverityChip } from "@/components/app/SeverityChip";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface CaptureDropzoneProps {
  onCaptureSelected?: (captureName: string) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatFindingsSummary(cap: CaptureItem): React.ReactNode {
  if (!cap.has_findings) {
    return <span className="text-text-tertiary">not analyzed</span>;
  }

  const { critical, high, medium, low, info } = cap.severity_counts || {};
  const total =
    (critical || 0) +
    (high || 0) +
    (medium || 0) +
    (low || 0) +
    (info || 0);

  if (total === 0) {
    return (
      <span className="text-signal-dim flex items-center gap-1">
        <CheckCircle2 className="h-3 w-3" />
        clean (0 findings)
      </span>
    );
  }

  const highestSeverity =
    critical > 0
      ? "CRITICAL"
      : high > 0
      ? "HIGH"
      : medium > 0
      ? "MEDIUM"
      : low > 0
      ? "LOW"
      : "INFO";

  const parts: string[] = [];
  if (critical > 0) parts.push(`${critical} crit`);
  if (high > 0) parts.push(`${high} high`);
  if (medium > 0) parts.push(`${medium} med`);
  if (low > 0) parts.push(`${low} low`);
  if (info > 0) parts.push(`${info} info`);

  return (
    <span className="flex items-center gap-1.5">
      <SeverityChip severity={highestSeverity} />
      <span className="text-text-secondary">{parts.join(" · ")}</span>
    </span>
  );
}

export const CaptureDropzone: React.FC<CaptureDropzoneProps> = ({
  onCaptureSelected,
}) => {
  const navigate = useNavigate();
  const { state, selectCapture, analyzeSelected, refreshCaptures, loadSampleData } =
    useAppStore();

  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadFileName, setUploadFileName] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const recentCaptures = state.captures.slice(0, 5);

  const handleOpenCapture = async (name: string) => {
    await selectCapture(name);
    if (onCaptureSelected) {
      onCaptureSelected(name);
    } else {
      navigate("/app/overview");
    }
  };

  const handleAnalyzeCapture = async (name: string) => {
    await selectCapture(name);
    await analyzeSelected();
    navigate("/app/overview");
  };

  const processUpload = async (file: File) => {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (ext !== ".pcap" && ext !== ".pcapng") {
      toast.error("Invalid file format. Only .pcap and .pcapng files are supported.");
      return;
    }

    setIsUploading(true);
    setUploadFileName(file.name);
    try {
      await uploadCapture(file, false);
      toast.success(`Uploaded ${file.name}`);
      await refreshCaptures();
      await selectCapture(file.name);
      navigate("/app/overview");
    } catch (err: any) {
      if (err.message?.includes("already exists")) {
        const shouldOverwrite = window.confirm(
          `Capture '${file.name}' already exists. Overwrite?`
        );
        if (shouldOverwrite) {
          try {
            await uploadCapture(file, true);
            toast.success(`Overwritten ${file.name}`);
            await refreshCaptures();
            await selectCapture(file.name);
            navigate("/app/overview");
          } catch (e: any) {
            toast.error(`Upload error: ${e.message}`);
          }
        }
      } else {
        toast.error(`Upload error: ${err.message}`);
      }
    } finally {
      setIsUploading(false);
      setUploadFileName(null);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    await processUpload(files[0]);
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    await processUpload(files[0]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Keyboard navigation for recent captures list: Enter / a / Up / Down
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || "").toLowerCase();
      if (activeTag === "input" || activeTag === "textarea") return;

      if (recentCaptures.length === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % recentCaptures.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev === 0 ? recentCaptures.length - 1 : prev - 1
        );
      } else if (e.key === "Enter") {
        const target = recentCaptures[selectedIndex] || recentCaptures[0];
        if (target) {
          e.preventDefault();
          handleOpenCapture(target.name);
        }
      } else if (e.key === "a") {
        const target = recentCaptures[selectedIndex] || recentCaptures[0];
        if (target) {
          e.preventDefault();
          handleAnalyzeCapture(target.name);
        }
      } else if (e.key === "r") {
        e.preventDefault();
        refreshCaptures();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [recentCaptures, selectedIndex]);

  return (
    <div className="flex flex-col gap-3 font-mono text-xs">
      <div className="flex items-center justify-between text-xs text-text-secondary font-semibold">
        <span>open a capture</span>
        {recentCaptures.length > 0 && (
          <span className="text-[11px] text-text-tertiary font-normal">
            Enter to open · a to analyze · ↑/↓ navigate
          </span>
        )}
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".pcap,.pcapng"
        className="hidden"
        onChange={handleFileInputChange}
      />

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "p-6 rounded-data border border-dashed transition-all duration-150 flex flex-col items-center justify-center gap-2.5 text-center cursor-pointer select-none",
          isDragOver
            ? "border-signal bg-signal-faint text-signal"
            : "border-border-hairline bg-surface-panel/40 hover:border-border-strong hover:bg-surface-panel text-text-secondary"
        )}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload
          className={cn(
            "h-6 w-6 transition-colors",
            isDragOver ? "text-signal" : "text-text-tertiary"
          )}
        />
        {isUploading ? (
          <div className="space-y-1">
            <p className="text-text-primary font-medium">
              Uploading {uploadFileName}...
            </p>
            <p className="text-[11px] text-text-tertiary">
              Writing file to captures/ directory
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="text-text-primary font-medium">
              Drop <span className="text-signal">.pcap</span> or{" "}
              <span className="text-signal">.pcapng</span> here
            </p>
            <p className="text-[11px] text-text-tertiary">
              or click to browse local filesystem
            </p>
          </div>
        )}
      </div>

      {/* Captures List or Empty State */}
      {recentCaptures.length > 0 ? (
        <div className="space-y-1.5 mt-1" role="listbox" aria-label="Recent captures">
          {recentCaptures.map((cap, idx) => {
            const isSelected = idx === selectedIndex;
            return (
              <div
                key={cap.name}
                role="option"
                aria-selected={isSelected}
                onClick={() => handleOpenCapture(cap.name)}
                className={cn(
                  "p-3 rounded-data border transition-all duration-150 flex items-center justify-between cursor-pointer group",
                  isSelected
                    ? "border-signal/60 bg-surface-raised relative before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[2px] before:bg-signal"
                    : "border-border-hairline bg-surface-panel hover:bg-surface-raised hover:border-border-strong"
                )}
              >
                <div className="flex items-center gap-3 truncate">
                  <span className="text-text-tertiary text-[11px] tabular-nums shrink-0 w-3">
                    {idx + 1}
                  </span>
                  <div className="flex flex-col gap-0.5 truncate">
                    <span className="font-medium text-text-primary truncate">
                      {cap.name}
                    </span>
                    <div className="text-[11px]">{formatFindingsSummary(cap)}</div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0 ml-4">
                  <span className="text-text-tertiary text-[11px] tabular-nums">
                    {formatFileSize(cap.size)}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-[11px] text-text-secondary hover:text-signal opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAnalyzeCapture(cap.name);
                    }}
                    title="Analyze capture"
                  >
                    <Play className="h-3 w-3 mr-1" />
                    analyze
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel/30 text-center text-text-tertiary">
          No captures yet. Drop a .pcap here, or put files in captures/ and press r.
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-3 mt-2">
        <Button
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
        >
          <FolderOpen className="h-4 w-4 mr-2" />
          Choose capture
        </Button>

        <Button
          variant="signal"
          onClick={() => {
            if (recentCaptures.length > 0) {
              const target = recentCaptures[selectedIndex] || recentCaptures[0];
              handleOpenCapture(target.name);
            } else {
              navigate("/app/overview");
            }
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
  );
};
