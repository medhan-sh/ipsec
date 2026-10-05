import React, { useState } from "react";
import { TierGlyph } from "@/components/app/TierGlyph";
import { TierBadge } from "@/components/app/TierBadge";
import { SeverityChip } from "@/components/app/SeverityChip";
import { ConfidenceMeter } from "@/components/app/ConfidenceMeter";
import { Mono } from "@/components/app/Mono";
import { SectionHeader } from "@/components/app/SectionHeader";
import { EmptyState } from "@/components/app/EmptyState";
import { ErrorState } from "@/components/app/ErrorState";
import { FilterBar } from "@/components/app/FilterBar";
import { SampleDataChip } from "@/components/app/SampleDataChip";
import { DetailDrawer } from "@/components/app/DetailDrawer";
import { Button } from "@/components/vendor/button";
import { Badge } from "@/components/vendor/badge";
import { Input } from "@/components/vendor/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/vendor/tabs";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/vendor/table";
import { Skeleton } from "@/components/vendor/skeleton";
import { FindingItem } from "@/api/types";
import { toast } from "sonner";

export const ComponentGallery: React.FC = () => {
  const [filterText, setFilterText] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedFinding, setSelectedFinding] = useState<FindingItem | null>(null);
  const [selectedTableRow, setSelectedTableRow] = useState<number>(0);
  const [simulateReducedMotion, setSimulateReducedMotion] = useState(false);

  const sampleFinding: FindingItem = {
    rule_id: "sixty_four_bit_block_cipher_in_esp",
    severity: "CRITICAL",
    category: "cryptography",
    title: "64-bit block cipher in use for ESP tunnel",
    tier: "INFERRED_SIDE_CHANNEL",
    evidence: [31, 35, 42],
    scope: "spi:0x3d713155+0xf918698d",
    references: ["RFC 8429 §3.1", "Sweet32 Vulnerability CVE-2016-2183"],
    recommendation: "Migrate the ESP tunnel to AES-GCM (128 or 256-bit).",
  };

  const handleOpenDrawer = (finding: FindingItem) => {
    setSelectedFinding(finding);
    setDrawerOpen(true);
  };

  return (
    <div className={`p-8 max-w-6xl mx-auto space-y-10 font-mono text-text-primary ${simulateReducedMotion ? "[&_*]:!transition-none [&_*]:!animation-none" : ""}`}>
      <div className="flex items-center justify-between pb-4 border-b border-border-hairline">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-signal lowercase">
            umbra component gallery
          </h1>
          <p className="text-xs text-text-secondary mt-1 font-sans">
            Visual verification suite for Phase 0 shared primitives, states, and tokens.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant={simulateReducedMotion ? "signal" : "outline"}
            size="sm"
            onClick={() => setSimulateReducedMotion((prev) => !prev)}
          >
            {simulateReducedMotion ? "Reduced Motion: ACTIVE" : "Simulate Reduced Motion"}
          </Button>
          <SampleDataChip />
        </div>
      </div>

      {/* 1. TIER GLYPHS & BADGES */}
      <section className="space-y-4">
        <SectionHeader title="1. tier language & glyphs" count={5} />
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 p-4 rounded-data border border-border-hairline bg-surface-panel">
          {(["OBSERVED", "INFERRED_SIDE_CHANNEL", "INFERRED_IMPLEMENTATION_DEFAULT", "ML_PREDICTION", "NOT_OBSERVABLE"] as const).map((tier) => (
            <div key={tier} className="flex flex-col gap-2 p-2 rounded-data bg-surface-base border border-border-hairline">
              <span className="text-[10px] text-text-tertiary">{tier}</span>
              <TierBadge tier={tier} />
              <div className="flex items-center gap-2 mt-1">
                <TierGlyph tier={tier} size={18} />
                <span className="text-[11px] text-text-secondary">Glyph 18px</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 2. SEVERITY & CONFIDENCE METERS */}
      <section className="space-y-4">
        <SectionHeader title="2. severity chips & confidence meters" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-data border border-border-hairline bg-surface-panel space-y-3">
            <span className="text-xs text-text-tertiary block font-semibold">Severity Classification (2px edges)</span>
            <div className="flex flex-wrap gap-2">
              <SeverityChip severity="CRITICAL" />
              <SeverityChip severity="HIGH" />
              <SeverityChip severity="MEDIUM" />
              <SeverityChip severity="LOW" />
              <SeverityChip severity="INFO" />
            </div>
          </div>

          <div className="p-4 rounded-data border border-border-hairline bg-surface-panel space-y-3">
            <span className="text-xs text-text-tertiary block font-semibold">Confidence Meters (No bar for OBSERVED / NOT_OBSERVABLE)</span>
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-text-secondary">OBSERVED:</span>
                <ConfidenceMeter tier="OBSERVED" confidence={1.0} />
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-text-secondary">INFERRED (88%):</span>
                <ConfidenceMeter tier="INFERRED_SIDE_CHANNEL" confidence={0.88} />
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-text-secondary">ML PREDICTION (42%):</span>
                <ConfidenceMeter tier="ML_PREDICTION" confidence={0.42} />
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-text-secondary">NOT_OBSERVABLE:</span>
                <ConfidenceMeter tier="NOT_OBSERVABLE" confidence={null} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. MONOSPACE CHIPS & COPY ON CLICK */}
      <section className="space-y-4">
        <SectionHeader title="3. monospace chips (copy on click)" />
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel space-y-3">
          <span className="text-xs text-text-tertiary block">Raw hashes, SPIs, and evidence frames with click-to-copy:</span>
          <div className="flex flex-wrap gap-3">
            <Mono label="spi" value="0x3d713155" />
            <Mono label="outbound" value="0xf918698d" />
            <Mono label="sha256" value="4a7d1ed414474e4033ac29ccb8653d9b13904996" />
            <Mono label="frame" value={42} />
            <Mono value="RFC 8429 §3.1" />
          </div>
        </div>
      </section>

      {/* 4. FILTER BAR WITH BLOCK CARET */}
      <section className="space-y-4">
        <SectionHeader title="4. filter input (terminal discipline)" />
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel space-y-2">
          <span className="text-xs text-text-tertiary block">Prefix '/' with blinking block caret on focus:</span>
          <FilterBar
            value={filterText}
            onChange={setFilterText}
            placeholder="search by title, rule id, or scope..."
          />
        </div>
      </section>

      {/* 5. BUTTONS, BADGES & INTERACTION STATES */}
      <section className="space-y-4">
        <SectionHeader title="5. buttons & micro-interactions" />
        <div className="p-4 rounded-data border border-border-hairline bg-surface-panel flex flex-wrap gap-3 items-center">
          <Button variant="signal" onClick={() => toast.success("Signal action triggered")}>
            Signal Primary
          </Button>
          <Button variant="default">Default Raised</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
          <Button disabled variant="signal">Disabled</Button>
          <Badge variant="signal">Signal Badge</Badge>
          <Badge variant="warning">Amber Badge</Badge>
          <div className="w-full mt-2 flex items-center gap-2">
            <span className="text-xs text-text-tertiary">Input:</span>
            <Input placeholder="Standalone monospace input..." className="max-w-xs" />
          </div>
        </div>
      </section>

      {/* 6. TABLE WITH SELECTION INDICATOR */}
      <section className="space-y-4">
        <SectionHeader title="6. table (signal-green selected row bar)" />
        <div className="border border-border-hairline rounded-data overflow-hidden bg-surface-panel">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12 text-center text-text-tertiary">#</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Rule / Finding</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Scope</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[
                { id: 1, sev: "CRITICAL", title: "64-bit block cipher in use for ESP tunnel", tier: "INFERRED_SIDE_CHANNEL", scope: "spi:0x3d713155+0xf918698d" },
                { id: 2, sev: "HIGH", title: "Weak Diffie-Hellman group negotiated (MODP-1024)", tier: "OBSERVED", scope: "ike_sa:0x7a892b1c" },
                { id: 3, sev: "HIGH", title: "Legacy IKEv1 protocol in use", tier: "OBSERVED", scope: "ike_sa:0x7a892b1c" },
                { id: 4, sev: "MEDIUM", title: "Truncated 96-bit ICV used in ESP data plane", tier: "INFERRED_SIDE_CHANNEL", scope: "spi:0x3d713155+0xf918698d" },
              ].map((row, idx) => (
                <TableRow
                  key={row.id}
                  selected={selectedTableRow === idx}
                  onClick={() => setSelectedTableRow(idx)}
                  className="cursor-pointer"
                >
                  <TableCell className="text-center text-text-tertiary">{row.id}</TableCell>
                  <TableCell><SeverityChip severity={row.sev} /></TableCell>
                  <TableCell className="font-medium text-text-primary">{row.title}</TableCell>
                  <TableCell><TierBadge tier={row.tier} /></TableCell>
                  <TableCell><Mono value={row.scope} copyable /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      {/* 7. ALL FOUR STATES: LOADING, EMPTY, ERROR, POPULATED */}
      <section className="space-y-4">
        <SectionHeader title="7. all four screen states" count={4} />
        <Tabs defaultValue="populated" className="w-full">
          <TabsList>
            <TabsTrigger value="populated">Populated</TabsTrigger>
            <TabsTrigger value="loading">Loading Skeleton</TabsTrigger>
            <TabsTrigger value="empty">Empty State</TabsTrigger>
            <TabsTrigger value="error">Error State</TabsTrigger>
          </TabsList>

          <TabsContent value="populated" className="p-4 border border-border-hairline rounded-data bg-surface-panel mt-3">
            <p className="text-xs text-text-primary mb-3 font-sans">
              Populated findings card with detail drawer trigger:
            </p>
            <div className="flex items-center justify-between p-3 rounded-data bg-surface-raised border border-border-hairline">
              <div className="flex items-center gap-3">
                <SeverityChip severity={sampleFinding.severity} />
                <span className="text-xs font-medium text-text-primary">{sampleFinding.title}</span>
              </div>
              <Button size="sm" variant="outline" onClick={() => handleOpenDrawer(sampleFinding)}>
                Inspect details
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="loading" className="p-4 border border-border-hairline rounded-data bg-surface-panel mt-3 space-y-2">
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </TabsContent>

          <TabsContent value="empty" className="p-4 border border-border-hairline rounded-data bg-surface-panel mt-3">
            <EmptyState
              title="No capture analyzed yet"
              message="Pick a capture from the left explorer, then choose Analyze capture."
              actionLabel="Analyze capture"
              onAction={() => toast.info("Analyze clicked from empty state")}
            />
          </TabsContent>

          <TabsContent value="error" className="p-4 border border-border-hairline rounded-data bg-surface-panel mt-3">
            <ErrorState
              title="Analysis failed"
              error="Analysis failed: tshark exited with code 2. Check that Docker is running, then try again."
              actionLabel="Retry analysis"
              onAction={() => toast.info("Retrying analysis...")}
            />
          </TabsContent>
        </Tabs>
      </section>

      {/* DETAIL DRAWER PREVIEW */}
      <DetailDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        finding={selectedFinding}
        ruleMeta={{
          explanation: "64-bit block ciphers are vulnerable to Sweet32 collision attacks on high-bandwidth tunnels.",
          recommendation: "Migrate to AES-GCM.",
          references: ["RFC 8429", "Sweet32 (CVE-2016-2183)"],
        }}
      />
    </div>
  );
};
