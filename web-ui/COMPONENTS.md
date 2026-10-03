# Umbra Web UI — Component Catalog & Design System Reference

This document catalogs all available UI components, design tokens, primitives, and interaction patterns for the Umbra Web UI.

All page agents must follow these guidelines:
1. **Prefer existing primitives** in `src/components/vendor/` and `src/components/app/`.
2. **Never edit** `src/components/vendor/` or `src/components/app/`. If an extension or fix is required, record it in `web-ui/NEEDS.md`.
3. If building a page-specific composite, create it inside your page directory: `src/pages/<page>/components/`.
4. Adhere strictly to the "Illuminated Evidence" design tokens and terminal discipline.

---

## 1. Design System & Tokens

Umbra is an offline, dark-mode-only passive IPsec forensics console.
All styling is driven by CSS variables in `src/styles/tokens.css` mapped through Tailwind:

### Surfaces
- `bg-surface-chrome` (`#000000`): Pinned chrome, status bar, app frame edges.
- `bg-surface-base` (`#040806`): Workspace canvas background.
- `bg-surface-panel` (`#08100c`): Hairline panels, table backgrounds, inspection containers.
- `bg-surface-raised` (`#0d1812`): Hovered rows, floating command dialogs, interactive card surfaces.

### Borders
- `border-border-hairline` (`#17261d`): Standard structural divider (1px solid).
- `border-border-strong` (`#24402f`): Focused element border, active selection outline (1px solid).

### Text Colors
- `text-text-primary` (`#d3ecdd`): Primary values, hashes, active labels, mono readings.
- `text-text-secondary` (`#82a592`): Field names, table headers, supporting metadata.
- `text-text-tertiary` (`#5f8270`): Gutters, row counts, hints, inactive indicators (never essential data).

### Signal & Accents
- `text-signal`, `bg-signal` (`#00ff7f`): Spring-green evidence signal (OBSERVED tier, selection markers, active status).
- `text-signal-dim`, `bg-signal-dim` (`#00b35a`): Secondary signal markers.
- `bg-signal-faint` (`rgba(0, 255, 127, 0.12)`): Selected table row background tint.
- `text-amber-sample`, `bg-amber-sample` (`#ffd23f`): Warning state, mock sample data indicator.

### Severity Accents
- `critical` (`#ff4d5e`): Finding indicator and 2px row edge marker.
- `high` (`#ff8a3d`): High severity finding indicator.
- `medium` (`#ffd23f`): Medium severity finding indicator.
- `low` (`#3fb8ff`): Low severity finding indicator.
- `info` (`#82a592`): Informational finding indicator.

### Typography
- **JetBrains Mono**: Nav items, tables, hex, SPIs, frame numbers, headings, status indicators, code.
- **IBM Plex Sans**: Multi-line prose explanations and remediation recommendations.
- **Tabular numerals**: `font-mono tabular-nums` for all numeric metrics and time offsets.

---

## 2. Tier Language & Evidence System

The central tenet of Umbra is that **the more directly evidence was observed, the more light it receives**.
Tier names are strictly uppercase strings from the analyzer contract:

| Tier String | Display Glyph | Luminance | Semantics |
|---|---|---|---|
| `OBSERVED` | Solid disc (●) | 100% Signal Green (`#00ff7f`) + faint glow | Certain (confidence = 1.0). Never show a percentage bar. |
| `INFERRED_SIDE_CHANNEL` | 3/4 disc (◕) | 75% Luminance | Inferred from packet timing, sizes, sequences. |
| `INFERRED_IMPLEMENTATION_DEFAULT` | 1/2 disc (◐) | 55% Luminance | Inferred from RFC/vendor default behaviors. |
| `ML_PREDICTION` | Dashed ring (◌) | 35% Luminance | Statistical / heuristic model output. |
| `NOT_OBSERVABLE` | Hatched empty ring (○) | 0% Luminance (tertiary grey `#5f8270`) | Value is an em dash ("—"). Never guess or show a bar. |

---

## 3. Vendor Primitives (`src/components/vendor/`)

These accessible primitives are built on Radix UI and Tailwind CSS:

| Component | Export Path | Usage & Intended Page |
|---|---|---|
| `Button` | `@/components/vendor/button` | Standard button (`variant="default" \| "signal" \| "outline" \| "ghost"`). Used across all pages. |
| `Badge` | `@/components/vendor/badge` | Small tag/badge (`variant="default" \| "signal" \| "outline" \| "secondary"`). |
| `Table` | `@/components/vendor/table` | Dense data tables (`Table, TableHeader, TableBody, TableRow, TableHead, TableCell`). Findings, Tunnels, Claims. |
| `Tabs` | `@/components/vendor/tabs` | Tabbed navigation views (`Tabs, TabsList, TabsTrigger, TabsContent`). Page sub-views, drawers. |
| `Sheet` | `@/components/vendor/sheet` | Slide-in drawer container (`Sheet, SheetContent, SheetHeader, SheetTitle`). Detail views. |
| `Dialog` | `@/components/vendor/dialog` | Modal dialogs (`Dialog, DialogContent, DialogHeader, DialogTitle`). Palette, shortcut help. |
| `Input` | `@/components/vendor/input` | Monospace text inputs with terminal focus ring. |
| `Select` | `@/components/vendor/select` | Styled dropdown select primitives. Filter bars and options. |
| `Tooltip` | `@/components/vendor/tooltip` | Micro-tooltips for glyphs, abbreviations, and truncate hints. |
| `ScrollArea` | `@/components/vendor/scroll-area` | Custom styled thin scrollbars for long tables and panels. |
| `Separator` | `@/components/vendor/separator` | 1px hairline horizontal/vertical rules. |
| `ResizablePanelGroup` | `@/components/vendor/resizable` | Split view layouts (`react-resizable-panels`). Detail drawers and split panes. |
| `Command` | `@/components/vendor/command` | Command palette primitives (`cmdk`). Global search and navigation. |
| `Skeleton` | `@/components/vendor/skeleton` | Pulse loading placeholder for table rows and metrics. |
| `Toaster` | `@/components/vendor/sonner` | Toast notification dispatcher (`toast.error()`, `toast.success()`). |
| `ToggleGroup` | `@/components/vendor/toggle-group` | Multi-select and single-select toggle buttons. Tier and severity filters. |
| `Collapsible` | `@/components/vendor/collapsible` | Expandable disclosure sections. Tunnel details, evidence traces. |

---

## 4. App Primitives (`src/components/app/`)

Purpose-built domain components implementing the Umbra data contract:

### `TierGlyph`
- **Path**: `@/components/app/TierGlyph`
- **Props**: `{ tier: string; className?: string }`
- **Usage**: Renders the canonical SVG glyph with corresponding luminance and shape.
- **Example**: `<TierGlyph tier="OBSERVED" />`

### `TierBadge`
- **Path**: `@/components/app/TierBadge`
- **Props**: `{ tier: string; showLabel?: boolean; className?: string }`
- **Usage**: Combines `TierGlyph` with the human-readable tier label (`Certain (Observed)`, `Side channel`, etc.).
- **Example**: `<TierBadge tier={claim.tier} />`

### `SeverityChip`
- **Path**: `@/components/app/SeverityChip`
- **Props**: `{ severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | string; className?: string }`
- **Usage**: Displays severity indicator with color-matched border and text. Never relies on color alone.
- **Example**: `<SeverityChip severity={finding.severity} />`

### `ConfidenceMeter`
- **Path**: `@/components/app/ConfidenceMeter`
- **Props**: `{ tier: string; confidence?: number | null; className?: string }`
- **Usage**: Displays confidence metric adhering to tier rules:
  - `OBSERVED`: Renders "certain" (never a bar or percentage).
  - `NOT_OBSERVABLE`: Renders "—".
  - Other tiers: Renders formatted percentage (e.g. `85%`) with a subtle confidence track.
- **Example**: `<ConfidenceMeter tier={verdict.basis_tier} confidence={verdict.confidence} />`

### `Mono`
- **Path**: `@/components/app/Mono`
- **Props**: `{ children: React.ReactNode; copyable?: boolean; copyValue?: string; className?: string }`
- **Usage**: Renders monospace chips for hex values, SPIs, frame numbers, and packet IDs with click-to-copy interaction.
- **Example**: `<Mono copyable>{finding.scope.spi}</Mono>`

### `SectionHeader`
- **Path**: `@/components/app/SectionHeader`
- **Props**: `{ title: string; count?: number; rightAction?: React.ReactNode; className?: string }`
- **Usage**: Renders terminal-disciplined section headers: lowercase title followed by an extending 1px hairline rule to the edge.
- **Example**: `<SectionHeader title="findings" count={findings.length} />`

### `PageHeader`
- **Path**: `@/components/app/PageHeader`
- **Props**: `{ title: string; subtitle?: string; actions?: React.ReactNode }`
- **Usage**: Page-level header with page title, capture indicator, and primary action buttons.

### `FilterBar`
- **Path**: `@/components/app/FilterBar`
- **Props**: `{ value: string; onChange: (v: string) => void; placeholder?: string; count?: number }`
- **Usage**: Pinned search bar with leading `/` prompt glyph and block cursor. Registers `/` keyboard focus shortcut.

### `DetailDrawer`
- **Path**: `@/components/app/DetailDrawer`
- **Props**: `{ open: boolean; onOpenChange: (open: boolean) => void; title: string; subtitle?: string; children: React.ReactNode }`
- **Usage**: Right-side drawer for deep inspection of findings, claims, or tunnel records.

### `SampleDataChip`
- **Path**: `@/components/app/SampleDataChip`
- **Props**: `{ className?: string }`
- **Usage**: Persistent amber badge rendered when mocks or sample captures are loaded. Cannot be dismissed.

### `StatusBar`
- **Path**: `@/components/app/StatusBar`
- **Props**: None (reads directly from `useAppStore`)
- **Usage**: Pinned bottom bar displaying selected capture, git commit SHA, runner status, active page, and `? help` trigger.

### `EmptyState` & `ErrorState`
- **Path**: `@/components/app/EmptyState`, `@/components/app/ErrorState`
- **Props**: `{ title: string; description?: string; actionLabel?: string; onAction?: () => void }`
- **Usage**: Standard empty and error surfaces with terminal aesthetic and actionable buttons.

---

## 5. Animation & Reduced-Motion Specification

Following the Umbra Motion Design Addendum, motion is strictly bounded, purposeful, and quiet by default.

### Approved Motion Patterns
1. **Micro-interactions** (100–180ms):
   - Hover and active states on table rows (`transition-colors duration-150`).
   - Focus rings on interactive inputs (`focus:ring-1 focus:ring-signal`).
   - Button press state transitions.
2. **Layout & Panels** (160–240ms):
   - Detail drawer slide-in / slide-out (`transition-transform ease-out duration-200`).
   - Collapsible panel expansions (`transition-[height] duration-200`).
3. **Evidence Lifecycle** (Max 500ms):
   - One-shot landing status sequential reveal on load (skippable via click/keypress).
   - One-shot post-analysis evidence illumination reveal on the overview page.

### Forbidden Motion Patterns
- **No decorative loops**: No infinite pulsing, floating elements, matrix rain, or scanlines.
- **No fake progress or scanning**: Never simulate analyzer progress with timers. Progress indicators must reflect true backend state.
- **No text scrambles**: Findings titles, recommendations, hex, and evidence must render directly.
- **No animated per-row entrances**: Do not animate table rows entering the DOM one-by-one during filtering or scrolling.
- **No tier promotion**: Never use motion or luminance to imply higher confidence than the data specifies.

### Accessibility: `prefers-reduced-motion: reduce`
All animations and transitions must immediately honor user preferences. This is implemented at three levels:

1. **Global CSS Rule** in `src/styles/tokens.css`:
   ```css
   @media (prefers-reduced-motion: reduce) {
     *,
     *::before,
     *::after {
       animation-duration: 0.01ms !important;
       animation-iteration-count: 1 !important;
       transition-duration: 0.01ms !important;
       scroll-behavior: auto !important;
     }
   }
   ```
2. **Tailwind Motion Utility Overrides**:
   Components that conditionally show or transition elements must use Tailwind's `motion-reduce:` variant to provide instant visibility:
   ```tsx
   <div className="transition-opacity duration-150 motion-reduce:!opacity-100 motion-reduce:!transition-none">
     {/* Content rendered immediately under reduced motion */}
   </div>
   ```
3. **Skippable Reveal Logic**:
   Sequences (e.g. system check) must listen for user interaction (`onClick`, `onKeyDown`) to immediately set completion state, bypassing delay.

---

## 6. Design Components Inbox Policy

Components provided by external contributors or designers are staged in `design/components/`.
- The index is tracked in `design/components/INDEX.md`.
- No page agent may import directly from `design/components/`.
- Phase 0 evaluates, ports, and adopts inbox components into `src/components/vendor/` or `src/components/app/`, records any needed dependencies in `web-ui/DEPS.md`, and documents them here.
