import React, { useState, useEffect } from "react";
import { SystemStatus } from "@/api/types";
import { cn } from "@/lib/utils";

interface SystemCheckProps {
  status: SystemStatus | null;
  capturesCount: number;
  serverError: boolean;
  onSkipped?: () => void;
}

interface StatusItem {
  label: string;
  value: string;
  ok: boolean;
  fix?: string;
}

const STORAGE_KEY = "umbra_system_check_shown";

export const SystemCheck: React.FC<SystemCheckProps> = ({
  status,
  capturesCount,
  serverError,
  onSkipped,
}) => {
  const isReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const alreadyShown =
    typeof window !== "undefined" &&
    window.sessionStorage.getItem(STORAGE_KEY) === "true";

  const [revealedCount, setRevealedCount] = useState<number>(() => {
    if (isReducedMotion || alreadyShown) return 10;
    return 1;
  });

  const tsharkOk = Boolean(status?.tshark?.available);
  const tsharkValue = tsharkOk
    ? status?.tshark?.version || "available"
    : `not detected — ${status?.tshark?.error || "install Wireshark / tshark or run in Docker"}`;

  const items: StatusItem[] = [
    {
      label: "analyzer",
      value: status?.analyzer || status?.analyzer_version || "0.1.0",
      ok: true,
    },
    {
      label: "tshark",
      value: tsharkValue,
      ok: tsharkOk,
    },
    {
      label: "rules",
      value: `${status?.rules ?? status?.rules_count ?? 15} loaded`,
      ok: true,
    },
    {
      label: "captures",
      value: `${status?.captures ?? status?.captures_count ?? capturesCount} in captures/`,
      ok: true,
    },
    {
      label: "network",
      value: "none (offline local)",
      ok: true,
    },
  ];

  useEffect(() => {
    if (isReducedMotion || alreadyShown) {
      setRevealedCount(items.length);
      return;
    }

    const timer = setInterval(() => {
      setRevealedCount((prev) => {
        if (prev >= items.length) {
          clearInterval(timer);
          window.sessionStorage.setItem(STORAGE_KEY, "true");
          return items.length;
        }
        return prev + 1;
      });
    }, 120);

    return () => clearInterval(timer);
  }, [isReducedMotion, alreadyShown, items.length]);

  const handleSkip = () => {
    setRevealedCount(items.length);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(STORAGE_KEY, "true");
    }
    onSkipped?.();
  };

  return (
    <div
      onClick={handleSkip}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " " || e.key === "Escape") {
          handleSkip();
        }
      }}
      role="region"
      aria-label="System status checks"
      tabIndex={0}
      className="p-4 rounded-data border border-border-hairline bg-surface-panel/60 font-mono text-xs flex flex-col gap-2 select-none focus:outline-none focus:border-border-strong cursor-default"
    >
      <div className="flex items-center justify-between text-[10px] text-text-tertiary uppercase tracking-wider font-semibold">
        <span>system status</span>
        {revealedCount < items.length && (
          <span className="text-[10px] text-text-tertiary lowercase font-normal">
            click or press any key to skip
          </span>
        )}
      </div>

      {serverError ? (
        <div className="flex items-center gap-2 text-amber-sample mt-1">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-sample shrink-0" />
          <span>Server not reachable. Start it with ./umbra web.</span>
        </div>
      ) : (
        <div className="space-y-1.5 mt-1">
          {items.map((item, idx) => {
            const isVisible = idx < revealedCount;
            return (
              <div
                key={item.label}
                className={cn(
                  "flex items-baseline gap-2 transition-opacity duration-150 motion-reduce:!opacity-100",
                  isVisible ? "opacity-100" : "opacity-0 pointer-events-none"
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full shrink-0 translate-y-[-1px]",
                    item.ok ? "bg-signal" : "bg-amber-sample"
                  )}
                />
                <span className="text-text-secondary shrink-0">{item.label}</span>
                <span
                  className={cn(
                    "truncate",
                    item.ok ? "text-text-primary" : "text-amber-sample"
                  )}
                >
                  {item.value}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
