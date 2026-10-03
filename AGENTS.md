# AGENTS.md — rules for the Umbra web UI work

Read first, in this order: `CLAUDE.md`, `context.md`, `ARCHITECTURE.md`,
`MVP_BUILD_PROMPT.md` §7, then `web-ui/COMPONENTS.md` and this file.
Every invariant in `CLAUDE.md` still applies. If anything here conflicts with
`CLAUDE.md`, `CLAUDE.md` wins.

## Scope (explicitly requested by the repo owner)

Build a **local, dark-mode-only web UI** for the existing analyzer. The
backend, analysis pipeline, rules, tests and the TUI are DONE. Do not modify:

- `src/ipsec_analyzer/{core,protocol,inference,assessment,output,synth}/`
- `src/ipsec_analyzer/tui/`
- any existing file under `tests/` (new tests go only under `tests/web/`)

The UI is a second presentation layer. Its only contract with the analyzer is
`findings.json` (schema 1.0). It never re-derives, re-scores or re-ranks
anything. It renders what the file says.

## Data contract (read `src/ipsec_analyzer/tui/models.py` — it is the reference parser)

Top-level keys: `schema_version, capture, coverage, claims, candidate_sets,
findings, passes, gaps, verdicts, rules`.

- Tier values in the data are UPPERCASE enum names, e.g. `OBSERVED`,
  `INFERRED_SIDE_CHANNEL`, `INFERRED_IMPLEMENTATION_DEFAULT`,
  `ML_PREDICTION`, `NOT_OBSERVABLE`. Types use these exact strings. One
  function `tierLabel()` turns them into display text. Read `core/claims.py` for
  the exact set and order; if the data contains a tier not in the union, show it
  as-is and log a console warning, never crash.
- `claim.confidence` can be `null`. `claim.value` can be any JSON.
- `candidate_sets[].eliminated` is a list of `[candidate, reason]` pairs.
  `indistinguishable` is a list of groups of candidate names.
- `sa_id` looks like `spi:0x3d713155+0xf918698d`.
- `verdicts[]` is where tunnel conclusions live: `sa_id, predicate, ambiguous,
  confidence, basis_tier, basis, outcome, surviving_true, surviving_false`.
- `findings[]`: `rule_id, severity, category, title, tier, evidence (frame
  numbers), scope, references, recommendation`. Static text per rule also lives
  in `rules[rule_id]` (`explanation`, `recommendation`, `passed_title`, ...).
- The golden fixture has `findings: []` but a non-empty `verdicts`. Any page
  must handle every list being empty, one item, and several hundred.
- Never invent a field. Unknown field needed → write it in `NEEDS.md`.

## Hard rules (repo-level)

- No tier promotion in the UI. Never show a tier stronger than the data says.
  Never merge tiers into one "score".
- `OBSERVED` means confidence exactly 1.0. Show "certain", never a percentage bar.
- `NOT_OBSERVABLE` carries no value. Render an em dash and "not observable".
  Never a value, never a bar, never a guess.
- **Sample data is never allowed to pass as real.** Any data from `src/mocks/`
  makes a persistent amber chip "sample data" appear in the top bar of every
  page, and it cannot be dismissed.
- No network at runtime, ever. No CDN scripts, Google Fonts, remote images,
  analytics. Fonts bundled via `@fontsource`. No external links: references
  (RFC numbers etc.) are plain text with a copy button.
- Python side: **no new runtime dependencies**. Standard library only. Node
  dependencies live in `web-ui/` only and only the ones under Stack. Ask before
  adding any other.
- Never weaken or delete a test to make it pass.
- Do only your assigned task. Do not prepare for or stub other tasks.

## Stack (fixed)

Vite, React, TypeScript (strict), Tailwind CSS, React Router, shadcn/ui
primitives (Radix), lucide-react (icons: lucide only), TanStack Table,
react-resizable-panels, @tanstack/react-virtual (long lists), cmdk (command palette), Recharts (only where a chart is
truly the clearest form), Sonner (toasts). Fonts: JetBrains Mono (UI chrome,
data, headings) and IBM Plex Sans (long prose only), via `@fontsource`.

Exception: Phase 0 may add npm dependencies that components in `design/components/`
need, and must record each one (name, version, which component needs it) in
`web-ui/DEPS.md`. Nobody else adds dependencies.

## Design system — "illuminated evidence" security console

Subject: a passive IPsec forensics console. The analyst's one question is
"how do we know this?" The product's idea: **the more directly something was
observed, the more light it gets.** Umbra means shadow: not observable is dark.

Look: black field, spring-green signal, terminal discipline. It should feel like
a well-made instrument, not a hacker movie. Green is a *signal*, not a theme:
body text is a soft green-white, and green appears only where something is
alive, selected, observed or actionable.

Dark only. No theme toggle. All values from `web-ui/src/styles/tokens.css`;
no hardcoded hex elsewhere.

Starting tokens (Phase 0 tunes after looking at screenshots):

- Surfaces: chrome `#000000` (nav, status bar), base `#040806`, panel `#08100c`, raised `#0d1812`
- Borders: hairline `#17261d`, strong `#24402f`. 1px only.
- Text: primary `#d3ecdd`, secondary `#82a592`, tertiary `#5f8270` (gutters and hints only, never essential info)
- Signal (spring green): `#00ff7f`; dim `#00b35a`; faint `rgba(0,255,127,0.12)` for selected-row fill
- Severity (severity chips and a 2px left edge of finding rows only):
  critical `#ff4d5e`, high `#ff8a3d`, medium `#ffd23f`, low `#3fb8ff`, info `#82a592`
- Warning/sample-data amber: `#ffd23f`
- Radii: 2px on data surfaces, 4px on overlays. Nothing else.
- Type: JetBrains Mono for nav, labels, tables, hashes, hex, SPIs, frames, headings.
  IBM Plex Sans only for paragraphs longer than one line (explanations,
  recommendations). Scale 12 / 13 / 14 / 16 / 20 / 28.
  Tabular numerals everywhere. Prose line length under 80ch.
- Contrast: all text meets WCAG AA on its surface. Color is never the only
  carrier: tiers use shape, severity uses text label plus color.

### Terminal discipline — the things that make it a security console

- **Status bar** pinned at the bottom: selected capture, short sha, run state,
  current page, `? help`. Real values only.
- **Command palette** on `:` and `Ctrl+K` (cmdk): jump to a page, analyze, open
  report, view JSON, switch capture.
- Tables have a dim row-number gutter and a 2px signal-green bar on the selected row.
- Section headers are lowercase mono with a hairline that runs to the edge:
  `findings (7) ────────`. Built with flex + border, not characters.
- Filter input is prefixed with `/` and shows a block caret when focused.
  The caret blink is the only idle animation in the app and obeys reduced motion.
- Keyboard first (see Keyboard). Every action reachable without a mouse.
- Raw values (hashes, SPIs, frame numbers) are monospace chips with copy on click.

### Tier language (the one bold element — build once, reuse everywhere)

`TierGlyph` + `TierBadge` in `src/components/app/`. Five tiers, distinct by
shape AND luminance:

| tier | glyph | light |
|---|---|---|
| OBSERVED | solid disc | full signal green, faint glow |
| INFERRED_SIDE_CHANNEL | three-quarter disc | 75% |
| INFERRED_IMPLEMENTATION_DEFAULT | half disc | 55% |
| ML_PREDICTION | dashed ring | 35%, dashed outline |
| NOT_OBSERVABLE | empty hatched ring | none, label in tertiary |

The only glow in the whole UI: the OBSERVED glyph and the focus ring
(`0 0 8px rgba(0,255,127,.35)`). Nothing else glows.

### Layout

```
┌─────┬──────────────────┬───────────────────────────────┐
│ nav │ capture explorer │ top bar: capture · status · run│
│ 5   │ (collapsible)    ├───────────────────────────────┤
│     │                  │ page content           [drawer]│
├─────┴──────────────────┴───────────────────────────────┤
│ status bar                                              │
└─────────────────────────────────────────────────────────┘
```

Dense, left-aligned, tables over cards. Panels are hairline regions, not
floating cards. The landing page (`/`) is outside this shell.

### Do NOT (these make a security UI corny or generated)

- Matrix rain, scanlines, CRT curvature, noise overlays, glitch or scramble text
- Fake hacking logs, fake progress, fake typing. Every line shown is real data.
- Skulls, hooded figures, padlock hero art, ASCII-art banners, `>_` as decoration
- Green body paragraphs or green everything. Signal only.
- Gradients, blur, drop shadows (except on overlays), hover-lift cards
- Identical rounded cards chopped out of every section; big-number stat tiles as a default overview
- ALL-CAPS eyebrow labels, "WORD — fragment" labels, arrows on buttons, emoji
- Entrance fade/slide animations on sections
- Marketing copy, lorem ipsum, filler

### Motion

Avoid gratuitous motion, but the repo owner explicitly approves the bounded motion behaviors in `Motion Design Addendum` (see ## Motion and animation below). Those behaviors are permitted when they follow the addendum. All other existing visual, security, offline, data-truth, and ownership constraints remain in force. Reduced motion is mandatory.

### Copy

Sentence case. Plain verbs. Say what happened and what to do next.
Buttons: "Analyze capture", "Open report", "View JSON".
Empty: "No capture analyzed yet. Pick one on the left, then choose Analyze capture."
Error: "Analysis failed: tshark exited with code 2. Check that Docker is running, then try again."

### Keyboard (match the TUI)

`1`–`5` pages, `a` analyze, `r` refresh captures, `/` focus filter, `Esc` clears
filter or closes drawer/palette, `j` view JSON, `?` shortcut help, `:` or
`Ctrl+K` palette, arrows move table selection, `Enter` opens the drawer.
Shortcuts are ignored while typing in an input.

### Every screen has four states

loading (skeleton, not spinner), empty, error, populated. Build all four.

## Motion and animation

### 1. Motion direction

Umbra should feel like a precise, cinematic instrument: quiet by default, responsive to interaction, and occasionally expressive when real analysis results arrive. Minimal and clean does not mean static. Motion must communicate hierarchy, state, cause-and-effect, or focus.

#### Approved motion
- **Micro-interactions:** subtle hover, pressed, focus, selected, toggle, and tab-indicator transitions.
- **Upload lifecycle:** drag-over, validation, uploading, success, duplicate/overwrite confirmation, rejection, and failure states. Show real progress only if the backend/API exposes real progress. Never simulate progress.
- **Analysis lifecycle:** idle, running, success, and failure transitions tied to actual request state. Do not imply the analyzer is working before it has started or finished.
- **Layout:** restrained drawer/sheet opening, panel resizing, expanding details, and selected-row transitions.
- **Evidence and charts:** animate a chart or evidence diagram when it first becomes meaningful or when its real data changes. Preserve exact values and ordering. The overview's provenance “illumination” may play once after a successful analysis result is loaded.
- **Typography:** one restrained landing-page wordmark or evidence motif may reveal/resolve on initial load. It must be brief, readable, skippable where appropriate, and must not imitate a fake terminal, fake scan, or fake analysis.
- **System check:** preserve the existing sequential reveal behavior if implemented, but use real `/api/status` data only. Any key or click skips it; reduced-motion preferences show all lines immediately.

#### Avoid
- Infinite decorative loops, particles, cursor trails, parallax, animated noise, fake telemetry, fake logs, fake progress bars, or fake analysis steps.
- Glows, blurred glass, gradients, neon bloom, or moving backgrounds.
- Text scrambling or typewriter effects on important instructions, findings, evidence, errors, or data values.
- Animating every row, every number, or every route transition.
- Motion that delays access to a capture, hides a result, changes a security conclusion's perceived certainty, or suggests a stronger evidence tier.
- Adding a new animation library solely for one tiny effect.

### 2. Motion implementation rules

- Use CSS transitions for simple color, opacity, border, and transform changes. Use the existing stack where possible.
- Motion for React may be added by the Phase 0 foundation agent only if it materially supports the approved interactions. Pin the version and document it in `web-ui/DEPS.md`. Page agents must not install dependencies.
- Respect `prefers-reduced-motion: reduce` globally. Remove or substantially shorten nonessential movement, disable reveal/typewriter sequences, and show content immediately. Never make content available only after an animation.
- Keep transitions short and purposeful. Suggested starting ranges: 100–180 ms for micro-interactions; 160–240 ms for drawers and small layout changes; up to 500–700 ms only for the landing system-check sequence or a single post-analysis evidence reveal. These are guidelines, not a reason to animate everything.
- Prefer opacity and small positional changes. Avoid large travel distances, springy overshoot, scale-popping, and dramatic camera-like moves.
- Keyboard focus, screen-reader semantics, keyboard shortcuts, and direct interaction must work regardless of animation state.
- Animation must never change, infer, rank, score, conceal, or fabricate analyzer data. Never animate a confidence value as if it were a measured progress value.
- Keep the UI local-only: no remote animation assets, CDN scripts, remote fonts, or runtime network requests.
- If a component's original effect conflicts with these rules, simplify it or reject it. Existing licensing requirements still apply.

### 3. Required behavior by surface

- **Landing:** Keep existing non-marketing, left-aligned capture-first layout. Choose one primary signature, either a brief wordmark reveal or a minimal evidence-line/motif resolving into place. Do not combine multiple hero effects. The signature must not block the dropzone or system status, and must disappear immediately under reduced motion. Preserve truthful system checks and the real drag-and-drop upload flow.
- **Overview:** On successful analysis, one compact provenance distribution reveal is allowed. Play once for that result, not continuously on rerender. Severity summaries and coverage bars may transition from their prior value to the actual returned value. Do not animate from invented values. Keep the existing dense two-column layout; do not introduce a large hero or stat-tile row.
- **Findings:** Selected-row indication, filter updates, and detail-drawer transitions may animate subtly. Do not animate each table row on initial render or make sorting/filtering feel slow. Large lists must remain responsive.
- **Tunnels:** Candidate elimination stages may reveal in sequence only when each stage corresponds to real `candidate_sets` data. The sequence must be skippable and must not imply extra analysis. Keep eliminated candidates and reasons readable without waiting for the animation.
- **Claims and coverage:** Tier glyphs, provenance summaries, coverage segments, and detail drawers may use restrained state transitions. Never use motion, color, or animation intensity to imply a tier stronger than the source data.
- **Upload and analysis states:** Every state remains understandable with motion disabled. Validation errors and completion messages appear immediately when known. Do not fabricate upload percentages, analysis stages, ETA, or packet counts.

## Components policy

1. Prefer primitives in `src/components/vendor/` (see `COMPONENTS.md`).
   Components the repo owner collected are in `vendor/` too, each flagged in
   `COMPONENTS.md` with an intended page. Use the ones flagged for your page
   unless they genuinely do not fit, and in your final message list which you
   skipped and why.
2. If something is missing you MAY build a small composite, but only: from
   vendor primitives + tokens; inside your own page folder
   (`src/pages/<yours>/components/`); without adding custom icons or gradients.
   Page agents may use only the approved motion patterns and existing animation
   primitives already established by Phase 0. They must not add a new animation
   library or invent new motion patterns. If a shared primitive or dependency is
   missing, record it in `NEEDS.md`.
   Append one line to `NEEDS.md`: `<page> | <component> | why it was needed`.
3. Never edit `src/components/vendor/` or `src/components/app/`. Ask via `NEEDS.md`.

## File ownership (parallel agents)

You edit ONLY `web-ui/src/pages/<your-page>/` plus your own tests. Shared files
belong to Phase 0 and the repo owner: router, shell, `package.json` and the
lockfile, `tokens.css`, `src/api/*`, `src/mocks/*`, `src/components/*`.
Need a change there? Write it in `NEEDS.md`, use a placeholder, keep going.
Never run `npm install <anything>`.

## Git

One branch and one worktree per agent. Small commits. Never rebase or merge
other branches. Never force-push. Never touch files outside your ownership.

## Agent safety (this is a security project)

Run the terminal in review/ask mode, not auto-approve. Do not let an agent run
`rm -rf`, `git clean`, `docker system prune`, `curl | sh`, or anything outside
the repo folder. Do not paste real captures or secrets into any agent prompt.

## Definition of done (every task)

1. Runs in mock mode (`VITE_USE_MOCKS=1`) with no backend; all four states work.
2. `npm run typecheck` and `npm run build` pass. Zero console errors or warnings.
3. DevTools network tab shows zero requests to any non-local host.
4. You drove the app with the browser tool, took screenshots at 1440×900 and
   1024×768, and fixed the layout bugs you saw.
5. Final message lists: files changed, components built (and why), what is in `NEEDS.md`.
