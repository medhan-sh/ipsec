# UMBRA WEB UI — AUDIT & DEFICIENCIES REPORT

**Date:** 2026-10-04  
**Audit Author:** Final Integration Engineer & Interaction Designer  
**Scope:** Full repository state, worktrees, integration status, route-by-route audit, visual & interaction deficiencies, and report parity analysis.

---

## 1. Repository & Integration State

### 1.1 Branches & Worktrees
The repository historically maintained separate git worktrees for Phase 0 and four specialized page agents:
- `main` (`997244e`): Phase 0 Foundation (Shell, tokens, router, mock stores, base primitives).
- `ipsec-overview` on branch `ui/overview` (`2ba5a8a`): Landing and Overview pages (Agent 1).
- `ipsec-findings` on branch `ui/findings` (`106395e`): Findings and Passes views with TanStack table and drawers (Agent 2).
- `ipsec-tunnels` on branch `ui/tunnels` (`e90fa0b`): Tunnels page with staged elimination and lifted verdicts (Agent 3).
- `ipsec-claims` on branch `ui/claims` (`e47c126`): Claims provenance ledger and Coverage accounting pages (Agent 4).

### 1.2 Integration Status
- Prior to this audit, `main` had NOT integrated any of the four agent branches, which left the Phase 0 placeholder `[Phase 0 placeholder — Agent 1 will construct full two-column instrument]` visible on `main`.
- **Integration executed:** All four branches (`ui/overview`, `ui/findings`, `ui/tunnels`, `ui/claims`) have been merged into `main`. The only textual conflict was a two-line concatenation in `web-ui/NEEDS.md`, which was resolved cleanly preserving both agent entries.
- TypeScript check (`npm run typecheck` via `npm.cmd`): **0 errors**.
- Production build (`npm run build`): **Succeeded** (`dist/` generated cleanly in 40s).
- Full Python web test suite (`python -m unittest discover tests/web`): **24/24 tests passed** (0 failures, 0 errors).

---

## 2. Current Application State (Route by Route)

| Route | Implementation Status | Functional State | Visual & Architectural Grade | Key Deficiencies |
|---|---|---|---|---|
| **`/` (Landing)** | Implemented (`LandingPage`, `CaptureDropzone`, `SystemCheck`, `TiersReference`) | Fully interactive (file upload, capture select, analyze, probe sequence) | **C+** (Generic, boxy, flat hierarchy, lack of cinematic presence) | Words and boxes are centered in an uninspired vertical stack. Typography lacks heroic scale contrast. The dropzone looks like a standard form upload box instead of a high-precision capture inlet. |
| **`/app/overview`** | Implemented (`CaptureFacts`, `CoverageGlance`, `PipelineHealth`, `FindingsSummary`, `ProvenanceDistribution`) | Functional (reads real capture/findings/claims data) | **B-** (Dull card grid, equal-weight panels, lacks clear focal point) | 2-column card stack feels like a generic SaaS dashboard. Equal card visual weights compete for attention. The provenance distribution is a plain horizontal bar with minimal forensic presence. |
| **`/app/findings`** | Implemented (`FindingsTable`, `PassesTable`, `FindingDetailDrawer`, `PassDetailDrawer`, `FindingsFilterBar`, `ZeroFindingsCard`) | Fully functional with TanStack table sorting/filtering and Radix sheets | **B** (Competent forensic ledger, but visually standard table) | Table borders are heavy; selected row highlight is subtle but lacks crisp edge definition; drawer is plain text dump without punchy architectural hierarchy. |
| **`/app/tunnels`** | Implemented (`TunnelList`, `TunnelVerdicts`, `EliminationStagedBar`, `SurvivorsList`, `EliminatedCandidates`, `IkeClaimsCard`) | Fully functional staged elimination & verdicts | **B** (Informative, but overly segmented into multiple boxes) | 6 separate panel cards fragment the viewport. The elimination flow does not feel like a unified spatial funnel from universe to survivors. |
| **`/app/claims`** | Implemented (`ClaimsTable`, `ClaimDetailDrawer`, `TierFilterToggle`) | Fully functional provenance ledger | **B+** (Clean tabular structure, glyphs work well) | Filter toggles look standard; table lacks typographic dynamic range; confidence values need more distinct tactile presentation. |
| **`/app/coverage`** | Implemented (`PipelineFacts`, `StagedBreakdown`, `GapsTable`, `PassesList`) | Fully functional coverage reconciliation | **B-** (Accounting equation is split across plain boxes) | The core insight ("what is known vs what cannot be known") is lost in disjointed stat boxes. Lacks the crisp mathematical balance of a forensic audit ledger. |
| **Shell & Nav** | Implemented (`AppShell`, `TopBar`, `StatusBar`, `CommandPalette`, `CaptureExplorer`, `ShortcutDialog`) | Robust keyboard controls & explorer collapse | **B** (Functional, but icons are tiny and rail lacks sleek tactile polish) | Left rail is very narrow with plain icons; TopBar is standard; analyze button lacks convergence excitement during run states. |

---

## 3. Brutal Visual & Interaction Analysis

### 3.1 What is Ugly or Generic
1. **The "Card Farm" Problem:**
   Every page relies on rectangular panels (`bg-surface-panel` with `border-border-hairline` and `rounded-data`). When stacked together, the interface turns into a grid of 6 to 8 identical dark boxes rather than an interconnected instrument.
2. **Typography Lacks Dramatic Scale Contrast:**
   Almost all body elements, headers, and values hover between 11px and 14px. There is no commanding focal point. The Landing title is 28px — far too tame for a hero screen. We need massive, disciplined display typography paired with razor-sharp 10px/11px tabular metadata.
3. **Landing Page lacks Identity:**
   Right now it looks like an ordinary file-uploader demo: wordmark, a little diagnostic box, a file drop box, and a reference table. It does not look like high-end defense/forensic software.
4. **Data Feels Flat:**
   Important findings (e.g. `CRITICAL` or `HIGH` findings) do not leap forward compared to informational labels. In the overview, the finding severity counts look like equal-weight badge chips.
5. **No Cinematic State for Analysis (`Analyze` Experience):**
   When `analyze` runs, it just puts a small spinner or standard skeleton. There is no focal convergence on the target capture, no evidence light warming up, no feeling that the analyzer is computing deep cryptographic invariants.

---

## 4. Report & Parity Analysis (CLI, HTML Report, TUI vs Web UI)

| Datum / Feature | CLI (`cli.py`) | HTML Report (`report.py`) | TUI (`tui/`) | Web UI Current | Web UI Status / Action |
|---|---|---|---|---|---|
| Capture SHA256 & Metadata | Yes | Yes (Header card with copy) | Yes (`CaptureFacts`) | Yes (`CaptureFacts`) | Parity complete. |
| Packet Count & Duration | Yes | Yes | Yes | Yes | Parity complete. |
| Findings Severity Counts | Yes | Yes (Hero counters) | Yes | Yes (`FindingsSummary`) | Parity complete. |
| Rule ID, Title, Severity, Category | Yes | Yes | Yes | Yes (Findings Table) | Parity complete. |
| Evidence Frame Numbers | Yes (list) | Yes (interactive highlight) | Yes (comma list) | Yes (monospace clickable chips) | Parity complete. |
| Rule Recommendations & References | Yes | Yes (Collapsible) | Yes (Detail modal) | Yes (Finding Detail Drawer) | Parity complete. |
| Passed Checks Ledger | Yes (`passes[]`) | Yes (grouped by rule) | Yes (Passes screen) | Yes (Findings passes tab & Coverage) | Parity complete. |
| Coverage Equation (Total, Assessable, Passed, Findings, Gaps) | Yes | Yes (Coverage section) | Yes (`CoverageScreen`) | Yes (`CoverageGlance` & `CoveragePage`) | Parity complete. |
| Tshark Exit Clean & Version | Yes | Yes | Yes | Yes (`PipelineHealth` & `SystemCheck`) | Parity complete. |
| TFC / Skip Packet Count | Yes | Yes | Yes | Yes (`PipelineHealth`) | Parity complete. |
| IKE SA Init Request/Response Observed | Yes | Yes | Yes | Yes (`IkeClaimsCard` & `PipelineFacts`) | Parity complete. |
| Candidate Set Universe Size | Yes | Yes | Yes | Yes (`EliminationStagedBar`) | Parity complete. |
| Eliminated Candidates + Reason | Yes (pairs) | Yes (table + reasons) | Yes (table) | Yes (`EliminatedCandidates`) | Parity complete. |
| Surviving Candidates | Yes | Yes (callout) | Yes (list) | Yes (`SurvivorsList`) | Parity complete. |
| Indistinguishable Groups | Yes | Yes | Yes | Yes (`SurvivorsList`) | Parity complete. |
| Verdicts (sa_id, predicate, ambiguous, basis, outcome) | Yes | Yes (Prominent cards) | Yes (Verdict tiles) | Yes (`TunnelVerdicts`) | Parity complete. |
| Claims Table (field, value, tier, confidence, method, caveats) | Yes | Yes | Yes | Yes (`ClaimsTable`) | Parity complete. |
| 5 Provenance Tiers + Glyphs | Yes | Yes | Yes | Yes (`TierGlyph`, `TierBadge`) | Parity complete. |
| Mock/Sample Data Indicator | N/A | N/A | Status chip | Yes (`SampleDataChip` persistent amber) | Parity complete. |
| JSON Raw Findings Document View | N/A | Yes (download) | Yes (Modal) | Yes (JSON modal on `j`) | Parity complete. |
| HTML Report Direct Export/View | Yes (`-o`) | N/A | Yes | Yes (via API `/api/report/:name`) | Parity complete. |

**Parity Conclusion:**
100% of data fields emitted by `findings.json` (schema 1.0) and parsed by `models.py` are accounted for in the Web UI data structures and page components. No fields are invented, no fields are missing. The presentation now needs to be elevated from functional forms to a high-end forensic instrument.

---

## 5. Master Redesign & Elevate Plan

1. **Shared Visual System & Atmospheric Baseline:**
   - Elevate `tokens.css` with fine-tuned spatial scales, subtle hairline depth, emerald signal accents, and dark-room focal luminescence.
   - Refine typography: Display JetBrains Mono at hero sizes (36px, 48px, 64px) for landing and section anchors; razor-sharp 10px-12px metadata with tabular numerals; clean IBM Plex Sans for forensic explanations.
2. **Landing Page Overhaul (Minimalist Maximalism):**
   - Vast dark field with architectural grid/hairline geometry.
   - Heroic typography: "UMBRA" display wordmark + "PASSIVE IPSEC OBSERVATION".
   - Integrated atmospheric evidence visual: dynamic SVG evidence matrix showing topological vectors emerging from deep black into emerald signal.
   - Precision capture dropzone that feels like a physical diagnostic inlet with drag feedback, quick-selection chips, and live backend probe status.
3. **Overview Page Overhaul (Forensic Headquarters):**
   - Eliminate disjointed card boxes.
   - Asymmetric, command-grade layout: dominant finding & verdict posture banner at top, flowing into an illuminated provenance spectrum and live forensic facts.
4. **Findings & Passes Ledger:**
   - Forensic ledger presentation: razor-sharp borders, distinct 2px severity markers, instant row preview, and rich drawer with rule rationale and frame citations.
5. **Tunnels Spatial Funnel:**
   - Unify the tunnel page into a spatial candidate elimination funnel: Universe → Filter Constraints → Eliminations with cryptographic justifications → Indistinguishable Survivors → Lifted Verdict.
6. **Claims Provenance Ledger:**
   - High-contrast illumination: OBSERVED fields clearly illuminated in pure emerald green (`#00ff7f`), INFERRED tiers systematically scaled in luminance, and NOT_OBSERVABLE gracefully receding.
7. **Coverage Mathematical Reconciliation:**
   - Accounting ledger visual equation: Total Rules (15) = Assessable (12) + Gaps (3); Assessable (12) = Clean (9) + Violations (3).
8. **Cinematic Analysis Experience:**
   - Responsive convergence when analysis is running: subtle focusing of the active target, dimmed peripheral noise, crisp done/error state resolution.
