# Phase 0 — web UI foundation (one agent, alone, before the four page agents)

Paste everything below into ONE Antigravity agent on branch `ui/foundation`.

---

Read `AGENTS.md`, `UMBRA_MOTION_ADDENDUM.md`, `CLAUDE.md`, `context.md`, `ARCHITECTURE.md` and
`MVP_BUILD_PROMPT.md` §7 first. Then read `src/ipsec_analyzer/tui/models.py`
(the reference parser for findings.json), `tui/runner.py`, `tui/app.py`,
`output/findings.py`, `core/claims.py` (tier names and order),
`tests/fixtures/golden_findings.json` and `docker-compose.yml`.

I (the repo owner) explicitly request this as a new phase: "Web UI foundation".
It overrides the "no later-phase work" rule for this phase only. You own every
shared file. The four page agents start after you, so everything they depend on
must exist and be stable when you finish.

`captures/` is empty and there is no network at runtime, so DO NOT download
captures. Build against the golden fixture plus a hand-built rich mock.

## Part A — local server (Python, standard library only)

Create `src/ipsec_analyzer/web/` with `__init__.py`, `__main__.py`, `server.py`.

- `ThreadingHTTPServer`. Flags: `--host` (default `127.0.0.1`), `--port` (default 8765).
  No async, no streaming, no new dependencies.
- **Docker gotcha:** inside a container the server must listen on `0.0.0.0` or the
  published port is unreachable. So the compose service passes `--host 0.0.0.0`
  but publishes the port as `127.0.0.1:8765:8765`, so it is still host-only.
  Verify this works from the host browser.
- Endpoints (JSON unless stated):
  - `GET  /api/status` → analyzer version, tshark found + version (or a clear reason it is missing), rule count (from the loaded rules), captures count, `network: "none"`. Never fails the whole call because one probe failed: report each probe separately.
  - `GET  /api/captures` → `.pcap` / `.pcapng` in `captures/`: name, size, modified, `has_findings`, `has_report`, and when findings exist a tiny summary (counts by severity)
  - `POST /api/analyze` `{"capture": "<name>"}` → run the analyzer the same way `tui/runner.py` does (same command resolution, same timeout). Return status, duration, parsed findings. **One analysis per capture at a time** (lock per capture; a second request gets 409 with a clear message). Write findings atomically (temp file then rename) so a reader never sees half a file.
  - `GET  /api/findings/<capture>` → sibling `.findings.json` or 404 with a clear message
  - `GET  /api/report/<capture>` → sibling `.report.html` (`text/html`)
  - `PUT  /api/upload?name=<file>` → raw body into `captures/`; only `.pcap`/`.pcapng`; 200 MB cap; refuse to overwrite an existing file unless `&overwrite=1`
  - everything else → static files from `web-ui/dist` with SPA fallback to `index.html`; if `dist` is missing return a plain page saying "UI not built. Run `make web-build`."
- Security: resolve every path and confirm it stays inside `captures/`; reject separators and `..`; allowlist extensions; JSON errors with a human `message`; never echo stack traces; send `X-Content-Type-Options: nosniff` and a CSP that allows only `'self'`. The report HTML is served from the same origin, so serve it with `Content-Security-Policy: sandbox` and open it in a new tab or iframe sandbox only.
- Reuse parsing from `tui/` only if it does not break the layering in `ARCHITECTURE.md`. Do not import from `core/`, `inference/`, or any analysis layer. Mirror instead of importing if in doubt.
- Entry points: `python -m ipsec_analyzer.web`, `./umbra web` in the launcher, `[project.scripts] umbra-web`, and a `web` service in `docker-compose.yml` styled like `umbra-tui`.
- `Makefile`: add `web-build` (runs `npm ci && npm run build` in `web-ui/`) and `web` (build, then start the server).
- Tests in `tests/web/` (stdlib `unittest.mock`/`http.client`, no new deps): path traversal rejected, bad extension rejected, missing findings → 404, captures list shape, double-analyze → 409, status survives a missing tshark. Run `make test`. The whole existing suite must pass with no existing test touched.
### Animation research and design ownership

Before implementing the frontend, research the official Motion for React documentation and React Bits library for components or techniques that could support the approved cinematic-but-minimal Umbra motion direction.

Do not assume that every effect needs a downloaded component. Prefer native CSS transitions for simple interactions and consider Motion for React only when it provides meaningful value.

Create `design/ANIMATION_RESEARCH.md` containing:
- A shortlist of no more than five relevant animation ideas.
- A source URL and license information for any source code proposed for reuse.
- The intended page or interaction and why it fits Umbra.
- Required npm dependencies and whether the effect can be implemented with existing tools.
- Any accessibility, reduced-motion, performance, or security concerns.
- A clear recommendation for which effects to implement and which to skip.

Use screenshots or official demos as visual references where possible. Do not copy code without checking its license. Do not add dependencies merely to demonstrate an effect.

You own the component naming conventions, folder structure, dependency documentation, and integration. Follow the conventions already defined in `AGENTS.md` and this prompt. Maintain `design/components/INDEX.md`, `web-ui/DEPS.md`, and `web-ui/COMPONENTS.md` as specified. Do not ask the repository owner to organize or rename component files manually.

Implement only the selected, approved motion patterns. Keep the landing page's signature effect restrained, make state transitions reflect real application states, and honor `prefers-reduced-motion`.

Before finishing Phase 0, show the owner the animation research shortlist and the `/__gallery` implementation so the visual direction can be reviewed before the page agents begin.
## Part B — frontend scaffold (`web-ui/`)

- Vite + React + TypeScript strict + Tailwind + React Router. Pin versions. Scripts: `dev`, `build`, `typecheck`, `preview`. Commit the lockfile.
- `vite.config.ts`: dev server proxies `/api` to `http://127.0.0.1:8765`.
- `src/styles/tokens.css`: every token in `AGENTS.md`, wired into Tailwind. Dark only. Screenshot it and tune values until surfaces separate cleanly without glare and green stays a signal.
- **Motion and animation foundation (per `UMBRA_MOTION_ADDENDUM.md`):**
  1. Read this addendum (`UMBRA_MOTION_ADDENDUM.md` and `AGENTS.md` § Motion and animation).
  2. Establish shared motion tokens/utilities and a global reduced-motion policy (`prefers-reduced-motion: reduce`).
  3. Decide whether CSS alone is sufficient; add Motion for React only if justified (pin version and document in `web-ui/DEPS.md`).
  4. Implement only shared primitives and states that Phase 0 owns. Do not build page-specific signature animations beyond the landing placeholder/system-check behavior.
  5. Add an animation/reduced-motion section to `web-ui/COMPONENTS.md` or the appropriate shared design documentation, including examples and the list of allowed motion patterns.
  6. Ensure `/__gallery` shows interaction states without autoplaying distracting loops.
  7. Verify reduced motion, keyboard interaction, and no fake progress.
- Fonts: `@fontsource/jetbrains-mono` and `@fontsource/ibm-plex-sans`, weights 400/500/600. Confirm no font request leaves localhost.
- `src/api/types.ts`: types for findings.json schema 1.0 mirroring `tui/models.py`, with UPPERCASE tier strings exactly as in the data, `verdicts` included, `confidence: number | null`. `tierLabel()` and `tierOrder()` helpers.
- `src/api/client.ts`: typed function per endpoint. With `VITE_USE_MOCKS=1` it serves from `src/mocks/` and reports `source: "mock"`.
- `src/mocks/`:
  - `golden.mock.json`: copy of `tests/fixtures/golden_findings.json`.
  - `rich.mock.json`: hand-built, obeying every `CLAUDE.md` invariant: OBSERVED confidence exactly 1.0, NOT_OBSERVABLE has no value, no tier above its inputs. Findings across all five severities (about 12), claims across all five tiers (about 25, some with caveats, one with `confidence: null`), 3 `candidate_sets` of different sizes with `[candidate, reason]` eliminations and indistinguishable groups, matching `verdicts` (one ambiguous, one unanimous), gaps, passes.
  - `empty.mock.json`: valid document with every list empty.
  - Use the real rule ids and titles from `assessment/rules/rules.yaml` for findings, gaps and passes so the mock looks like real output.
  - Mock mode must show the amber "sample data" chip (see AGENTS.md).
- Router and shell:
  - `/` landing page (outside the shell). Phase 0 builds only a placeholder; Agent 1 builds the real one.
  - `/app/overview`, `/app/findings`, `/app/tunnels`, `/app/claims`, `/app/coverage` inside the shell.
  - Shell: left nav with the five pages and keyboard shortcuts; collapsible capture explorer (list from `/api/captures`, selection in URL + store, analyze, refresh, drag-and-drop upload); top bar with capture name, run status, sample-data chip when applicable, "Analyze capture", "Open report", "View JSON"; **status bar** at the bottom; **command palette** (cmdk) on `:` and `Ctrl+K`; shortcut help dialog on `?`; global toast host.
- Shared store (context + reducer): selected capture, run status, loaded document, data source (`real` | `mock`), status payload. Pages only read from it.
- Five page stubs under `src/pages/{overview,findings,tunnels,claims,coverage}/index.tsx`, each a placeholder inside the real shell. Do not build page content. Create `src/pages/landing/index.tsx` as a placeholder too.
- shadcn primitives into `src/components/vendor/`: button, badge, tabs, table, sheet, dialog, input, select, tooltip, scroll-area, separator, resizable, command, skeleton, sonner, toggle-group, collapsible. Restyle only through tokens.
- `src/components/app/`: `TierGlyph` (exactly per the table in AGENTS.md), `TierBadge`, `SeverityChip`, `ConfidenceMeter` ("certain" for OBSERVED; never a bar for NOT_OBSERVABLE; handles null), `Mono` (monospace chip with copy), `SectionHeader` (lowercase label + hairline), `EmptyState`, `ErrorState`, `PageHeader`, `FilterBar` (prefixed with `/`), `DetailDrawer`, `SampleDataChip`, `StatusBar`. Every one with all states.
- **Owner's component inbox (no index file exists, you create it):** the owner drops free/open component source files into `design/components/`. Optional naming hint: a filename prefix says the intended page (`findings--data-table.tsx`, `tunnels--stepper.tsx`, `overview--stat-row.tsx`; `all--` or no prefix = shared). Read every file there, then generate `design/components/INDEX.md` yourself: name, file, npm deps (from its imports), intended page (from the prefix, otherwise your best guess marked "guessed"), and source URL if the file has one in a header comment. Then for each component: adapt it into `src/components/vendor/` so it uses tokens only (no hardcoded colors), install the deps it needs (record in `web-ui/DEPS.md`), and flag it in `COMPONENTS.md` with its intended page. If a license is stated in the file and it is not MIT/Apache/BSD/ISC-style open, skip it and say so. SKIP and explain in your final message any component that needs a network call or remote asset, adds gradients/glows/blur beyond AGENTS.md, plays entrance animations, or cannot be restyled to the dark green system. Show every adopted component in `/__gallery`.
- `web-ui/COMPONENTS.md`: every vendor and app component with import path, props and one example. Create an empty `web-ui/NEEDS.md`.
- `src/pages/_gallery/` on a hidden route `/__gallery`: every shared component in every state, on the real dark surfaces, so I can review the look before the page agents start.
- Add `web-ui/node_modules` to `.gitignore`. Keep `web-ui/dist` ignored for now (I will decide about committing it at the end).

## Acceptance

1. `make test` passes with no existing test changed.
2. `cd web-ui && npm run typecheck && npm run build` passes.
3. `make web` serves the app at `http://127.0.0.1:8765` from the host browser, including when launched through the compose service. Status endpoint works with and without tshark.
4. `VITE_USE_MOCKS=1 npm run dev` works with no backend and shows the sample-data chip.
5. Selecting a capture and pressing Analyze loads real data into the store (log it for now) when a capture exists. With zero captures the explorer shows a useful empty state.
6. `/__gallery` looks deliberate at 1440×900 and 1024×768 and passes the "Do NOT" list in AGENTS.md.
7. Zero requests to non-local hosts. Zero console errors.
8. Add a short "Web UI" section to `README.md` (build and run). Touch no other doc.
9. Commit on `ui/foundation`, then stop. Do not start any page. Final message: what you built, decisions you made, what I should review first.
