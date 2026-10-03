# Page agent briefs (run only after Phase 0 is merged to main and you have reviewed `/__gallery`)

Setup once per agent, from the main repo folder:

```
git worktree add ../umbra-overview -b ui/overview main
git worktree add ../umbra-findings -b ui/findings main
git worktree add ../umbra-tunnels  -b ui/tunnels  main
git worktree add ../umbra-claims   -b ui/claims   main
```

Open each folder as its own Antigravity workspace. In each: `cd web-ui && npm ci`.
Dev ports: 5173 overview, 5174 findings, 5175 tunnels, 5176 claims.
Run: `VITE_USE_MOCKS=1 npm run dev -- --port <port>`.

---

## Preamble (paste at the top of EVERY agent)

Read `AGENTS.md` (especially `## Motion and animation`), `UMBRA_MOTION_ADDENDUM.md`,
`CLAUDE.md`, `context.md`, `web-ui/COMPONENTS.md` and `web-ui/src/api/types.ts`.
Open `/__gallery` with the browser tool to see the shared components and the
visual language. You own ONLY `web-ui/src/pages/<your page>/`. Build it to the
Definition of Done in `AGENTS.md`. Page agents may use only the approved motion
patterns and existing animation primitives already established by Phase 0. They
must not add a new animation library or invent new motion patterns. If a shared
primitive or dependency is missing, record it in `NEEDS.md`. Develop against
`rich.mock.json`, then check `golden.mock.json` and `empty.mock.json` still render.
Take data from the shared store; do not fetch on your own. Never run `npm install <anything>`.
Do not invent data fields: if you need one that is not in `types.ts`, write it in
`NEEDS.md` and move on. Run the terminal in ask mode.

---

## Agent 1 — Landing + Overview (`src/pages/landing/`, `src/pages/overview/`)

*Ownership note:* Landing/overview agent owns the landing signature animation and the one-shot post-analysis provenance reveal.

### Landing (`/`, outside the shell)

First screen of the app. A calm, dark, terminal-flavoured start page that tells
the truth about the system state and gets the person to a capture fast. It is
not a marketing page. Add a restrained cinematic touch: choose **one** primary
signature, either a brief wordmark reveal or a minimal evidence-line/motif
resolving into place. Do not combine multiple hero effects. The signature must
not block the dropzone or system status, must not imitate a fake terminal/scan,
and must disappear immediately under reduced motion (`prefers-reduced-motion: reduce`).

Layout: a single left-aligned column, max 880px, starting around the top third
of the viewport. Black field, no sidebar. Sections, in order:

1. Wordmark `umbra` in JetBrains Mono, signal green, 28px. Under it one plain
   line: "Passive IPsec analysis. Reads captures, decrypts nothing, touches no network."
2. **System check** from `GET /api/status`, real values only, one line each:
   `analyzer 0.1.0`, `tshark 4.4.18` (or amber with the reason and the fix),
   `rules 15 loaded`, `captures 0 in captures/`, `network none`.
   Lines print in sequence once per browser session (about 600ms total), any key
   or click skips it, reduced motion shows them instantly. Healthy = signal
   green dot, problem = amber dot plus what to do. No fake lines, no fake progress.
3. **Open a capture**: a drop zone for `.pcap` / `.pcapng` and a "Choose capture"
   button. If captures exist, list the most recent five (name, size, findings
   summary if analyzed) with Enter to open the first and `a` to analyze it.
   Selecting one goes to `/app/overview`. Empty: "No captures yet. Drop a .pcap
   here, or put files in captures/ and press r."
4. **How to read the results**: the five tiers as five rows, glyph + name + one
   plain sentence. Take exact tier order and meaning from `core/claims.py`
   docstrings; indicative copy: OBSERVED "Read directly from the handshake.
   Certain." / INFERRED_SIDE_CHANNEL "Deduced from sizes and timing of what is
   visible." / INFERRED_IMPLEMENTATION_DEFAULT "Assumed from how this
   implementation usually behaves." / ML_PREDICTION "A statistical prediction."
   / NOT_OBSERVABLE "The capture cannot tell us. We say so rather than guess."
5. Footer line of shortcuts: `1-5 pages · a analyze · / filter · : palette · ? help`.

States: status request fails → "Server not reachable. Start it with ./umbra web."
In mock mode only, show "Load sample data" (clearly labeled) and the persistent
sample-data chip. In real mode that button does not exist.

### Overview (`/app/overview`)

Answers: what is this capture, how much can we say, what is the worst thing found.

- Capture facts: filename, packets, duration, SHA-256 (short, full on hover, copy). If `truncated`, a clear warning row saying what truncation means for the results.
- Findings summary: counts by severity as one compact bar, then the top five findings (severity, title, one-line recommendation). Select → Findings with that finding open.
- Provenance distribution: claims per tier with `TierGlyph` and a proportional bar. This is where the one-shot compact provenance distribution reveal ("illumination") plays once after a successful analysis result is loaded (not continuously on rerender; shows immediately under reduced motion).
- Coverage and severity summaries: severity summaries and coverage bars may transition from their prior value to the actual returned value (do not animate from invented values). Coverage at a glance: found / assessable / passed / gaps out of total, one readable line plus a thin segmented bar, linking to Coverage.
- Pipeline health in plain words: tshark version, clean exit, packets skipped, IKE SA_INIT request and response observed, ESP tunnels total and how many miss a direction.
- Empty (no capture analyzed): tell the person what to do.
- Dense two-column grid. No big-number hero, no row of stat tiles.

## Agent 2 — Findings (`src/pages/findings/`)

*Motion note:* May use approved patterns only (subtle selected-row indication, filter updates, and detail-drawer transitions). Do not animate each table row on initial render or make sorting/filtering feel slow. Large lists must remain responsive. Do not install packages or create new shared animation primitives.

- TanStack table: severity, title, category, tier, scope. Default sort severity then title. `SeverityChip` plus 2px left edge. Row-number gutter, sticky header, signal-green bar on the selected row.
- Filters: severity toggle group, category select, `/` text filter, `Esc` clears. State in the URL.
- Detail drawer (`Enter` or click): explanation (from `rules[rule_id]`), recommendation, references as plain text with copy, evidence frames as `Mono` chips, scope, rule id, tier.
- Second tab for passes: what was checked and passed, at which tier. Quiet and compact.
- A failing rule is not a gap. If a related gap exists, link to Coverage; never merge them.
- Zero findings: "This capture produced no findings. N checks passed." Show how many gaps remain, because zero findings with many gaps is not good news. Do not celebrate.
- Verify with `rich.mock.json` (many) and `golden.mock.json` (none).

## Agent 3 — Tunnels (`src/pages/tunnels/`)

*Motion note:* May use approved patterns only. Candidate elimination stages may reveal in sequence only when each stage corresponds to real `candidate_sets` data; the sequence must be skippable and must not imply extra analysis. Eliminated candidates and reasons must remain readable without waiting for the animation. Do not install packages or create new shared animation primitives.

The core idea of the product shows here: elimination before ranking, then verdict lifting.

- Left list of tunnels keyed by `sa_id` (`spi:0x…+0x…` as `Mono`), surviving-candidate count, and a note when the tunnel is missing a direction. `[` and `]` step between tunnels.
- Elimination view from `candidate_sets`: universe size → survivors as a staged bar with labeled steps (not decoration).
- Eliminated candidates, from the `[candidate, reason]` pairs, grouped by reason, collapsed by default.
- Survivors, with `indistinguishable` groups bracketed together so it is obvious which cannot be told apart on the wire.
- **Verdicts** from `verdicts[]` for this `sa_id`: per predicate show `basis` text, `basis_tier` glyph, and the survivors split into `surviving_true` / `surviving_false` with counts. If `ambiguous` is true, say so plainly and name both sides; if false, show `outcome`. Use the data's words. Do not write your own security conclusions and do not turn counts into a score.
- IKE-side suite claims for the tunnel with tiers via the shared glyphs. Ranking is never shown as certainty.
- Handle: zero tunnels, one tunnel, a candidate set with thousands of eliminated entries (virtualize or paginate), `confidence: null`.

## Agent 4 — Claims + Coverage (`src/pages/claims/`, `src/pages/coverage/`)

*Motion note:* May use approved patterns only. Tier glyphs, provenance summaries, coverage segments, and detail drawers may use restrained state transitions. Never use motion, color, or animation intensity to imply a tier stronger than the source data. Do not install packages or create new shared animation primitives.

Claims is the provenance ledger, the strongest differentiator. Coverage is honest accounting of what the tool could not say.

Claims:
- Ledger: field, value, tier (`TierBadge`), confidence, method, evidence (count, expandable), caveats (count with a warning mark).
- OBSERVED → "certain". NOT_OBSERVABLE → em dash and "not observable", nothing else. Others → `ConfidenceMeter`; `null` → "n/a".
- Five-way tier toggle group, each option showing glyph and count. `/` filters field and method. State in the URL.
- Drawer: full value (pretty JSON in `Mono`), method in plain words, every caveat, evidence frame list, one-sentence tier explanation matching `core/claims.py`.
- Group-by-field toggle so repeated fields collapse into one row with a count.

Coverage:
- Staged breakdown of checks: total → found → assessable → passed, with gaps accounted so the numbers visibly add up.
- Gaps table: rule id, title, gap kind, required tier vs actual tier (two glyphs side by side so the shortfall is visible), full reason. This is the "what we cannot know" page; make the reasons easy to read.
- Passes list, compact. Pipeline facts block (tshark version, clean exit, packets skipped, SA_INIT flags, tunnels missing a direction).

---

## Scope check before every merge (you run this, not the agents)

Save as `scripts/check-branch-scope.sh` on main and run `./scripts/check-branch-scope.sh ui/findings src/pages/findings`:

```bash
#!/usr/bin/env bash
# usage: check-branch-scope.sh <branch> <allowed web-ui subfolder(s)...>
set -e
BR="$1"; shift
BAD=0
for f in $(git diff --name-only main..."$BR"); do
  ok=0
  for allowed in "$@"; do
    case "$f" in web-ui/$allowed/*|tests/web/*) ok=1 ;; esac
  done
  if [ $ok -eq 0 ]; then echo "OUT OF SCOPE: $f"; BAD=1; fi
done
# the invariants: nothing here may ever change on a UI branch
if git diff --name-only main..."$BR" | grep -E '^(src/ipsec_analyzer/(core|protocol|inference|assessment|output|synth|tui)/|tests/(core|protocol|inference|assessment|output|synth|tui|integration)/|CLAUDE.md|ARCHITECTURE.md|web-ui/package(-lock)?.json)'; then
  echo "FROZEN FILE TOUCHED"; BAD=1
fi
[ $BAD -eq 0 ] && echo "scope ok: $BR"
exit $BAD
```

(For Agent 4 pass both folders: `src/pages/claims src/pages/coverage`. For Agent 1: `src/pages/landing src/pages/overview`.)

## Merge order and finish

1. Run the scope check, then merge `ui/overview`, then `ui/findings`, `ui/tunnels`, `ui/claims`, rebuilding and clicking through after each.
2. Read `NEEDS.md`. Promote anything two pages needed into `src/components/app/` yourself.
3. One polish agent: spacing, focus states, 1024-wide layout, test both normal motion and `prefers-reduced-motion: reduce`, "Do NOT" list from `AGENTS.md`.
4. `make test`, `make web`, click every page with sample data and (when you have them) real captures.
5. Decide whether to commit `web-ui/dist` so a teammate can run `./umbra web` without Node. It is static and small. Remove it from `.gitignore` in the last commit only.
