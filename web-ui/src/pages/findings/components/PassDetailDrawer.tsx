import React from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/vendor/sheet";
import { PassedCheckItem, RuleMeta } from "@/api/types";
import { TierBadge } from "@/components/app/TierBadge";
import { Mono } from "@/components/app/Mono";
import { Separator } from "@/components/vendor/separator";
import { CheckCircle2 } from "lucide-react";

interface PassDetailDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pass: PassedCheckItem | null;
  ruleMeta?: RuleMeta;
}

export const PassDetailDrawer: React.FC<PassDetailDrawerProps> = ({
  open,
  onOpenChange,
  pass,
  ruleMeta,
}) => {
  if (!pass) return null;

  const displayTitle =
    pass.title ||
    ruleMeta?.passed_title ||
    ruleMeta?.title ||
    pass.rule_id;

  const explanation =
    ruleMeta?.explanation || "This rule check evaluated successfully with zero violations.";
  const references = ruleMeta?.references || [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl bg-surface-panel border-l border-border-hairline overflow-y-auto p-6 space-y-6 text-xs font-mono"
      >
        <SheetHeader className="space-y-3 pb-3 border-b border-border-hairline">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-data text-[10px] font-mono border border-signal/40 bg-signal-faint text-signal uppercase tracking-wider font-semibold">
              <CheckCircle2 className="h-3 w-3" />
              Passed Check
            </span>
            <TierBadge tier={pass.tier} />
          </div>
          <SheetTitle className="text-base font-semibold leading-snug text-text-primary font-mono text-left">
            {displayTitle}
          </SheetTitle>
        </SheetHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-data bg-surface-base border border-border-hairline">
            <div>
              <span className="text-[10px] text-text-tertiary uppercase tracking-wider block mb-1">
                rule id:
              </span>
              <Mono value={pass.rule_id} copyable className="text-xs" />
            </div>

            <div>
              <span className="text-[10px] text-text-tertiary uppercase tracking-wider block mb-1">
                evaluated tier:
              </span>
              <TierBadge tier={pass.tier} />
            </div>

            {pass.scope && (
              <div className="col-span-full">
                <span className="text-[10px] text-text-tertiary uppercase tracking-wider block mb-1">
                  scope:
                </span>
                <Mono value={pass.scope} copyable className="text-xs" />
              </div>
            )}
          </div>

          {pass.evidence && pass.evidence.length > 0 && (
            <div>
              <span className="text-[11px] text-text-secondary uppercase tracking-wider block mb-1.5">
                evidence frames ({pass.evidence.length}):
              </span>
              <div className="flex flex-wrap gap-1.5 p-2 rounded-data bg-surface-base border border-border-hairline">
                {pass.evidence.map((f) => (
                  <Mono key={f} label="frame" value={f} copyable className="text-xs" />
                ))}
              </div>
            </div>
          )}

          <Separator className="bg-border-hairline" />

          <div>
            <span className="text-[11px] text-text-primary font-semibold uppercase tracking-wider block mb-1.5">
              rule context & explanation:
            </span>
            <div className="p-3 rounded-data bg-surface-base border border-border-hairline">
              <p className="text-xs text-text-secondary font-sans leading-relaxed max-w-[80ch]">
                {explanation}
              </p>
            </div>
          </div>

          {references.length > 0 && (
            <div>
              <span className="text-[11px] text-text-primary font-semibold uppercase tracking-wider block mb-1.5">
                references:
              </span>
              <div className="space-y-1.5">
                {references.map((ref, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-data bg-surface-base border border-border-hairline"
                  >
                    <span className="text-xs text-text-primary font-mono select-all">
                      {ref}
                    </span>
                    <Mono value={ref} copyable className="ml-2 shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};
