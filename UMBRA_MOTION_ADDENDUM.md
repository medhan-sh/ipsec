# Umbra Motion Design Addendum
## For Gemini / Antigravity implementation

**Purpose:** Add restrained cinematic motion to Umbra without weakening the existing product, security, data-truth, offline-runtime, or branch-ownership constraints. This addendum updates the motion-related rules in `AGENTS.md`, `PHASE0_PROMPT.md`, and `AGENT_BRIEFS.md`. It does not authorize changes to the analyzer, findings schema, security behavior, or unrelated project rules.

## 1. Motion direction

Umbra should feel like a precise, cinematic instrument: quiet by default, responsive to interaction, and occasionally expressive when real analysis results arrive. Minimal and clean does not mean static. Motion must communicate hierarchy, state, cause-and-effect, or focus.

### Approved motion
- **Micro-interactions:** subtle hover, pressed, focus, selected, toggle, and tab-indicator transitions.
- **Upload lifecycle:** drag-over, validation, uploading, success, duplicate/overwrite confirmation, rejection, and failure states. Show real progress only if the backend/API exposes real progress. Never simulate progress.
- **Analysis lifecycle:** idle, running, success, and failure transitions tied to actual request state. Do not imply the analyzer is working before it has started or finished.
- **Layout:** restrained drawer/sheet opening, panel resizing, expanding details, and selected-row transitions.
- **Evidence and charts:** animate a chart or evidence diagram when it first becomes meaningful or when its real data changes. Preserve exact values and ordering. The overview's provenance “illumination” may play once after a successful analysis result is loaded.
- **Typography:** one restrained landing-page wordmark or evidence motif may reveal/resolve on initial load. It must be brief, readable, skippable where appropriate, and must not imitate a fake terminal, fake scan, or fake analysis.
- **System check:** preserve the existing sequential reveal behavior if implemented, but use real `/api/status` data only. Any key or click skips it; reduced-motion preferences show all lines immediately.

### Avoid
- Infinite decorative loops, particles, cursor trails, parallax, animated noise, fake telemetry, fake logs, fake progress bars, or fake analysis steps.
- Glows, blurred glass, gradients, neon bloom, or moving backgrounds.
- Text scrambling or typewriter effects on important instructions, findings, evidence, errors, or data values.
- Animating every row, every number, or every route transition.
- Motion that delays access to a capture, hides a result, changes a security conclusion's perceived certainty, or suggests a stronger evidence tier.
- Adding a new animation library solely for one tiny effect.

## 2. Motion implementation rules

- Use CSS transitions for simple color, opacity, border, and transform changes. Use the existing stack where possible.
- Motion for React may be added by the Phase 0 foundation agent only if it materially supports the approved interactions. Pin the version and document it in `web-ui/DEPS.md`. Page agents must not install dependencies.
- Respect `prefers-reduced-motion: reduce` globally. Remove or substantially shorten nonessential movement, disable reveal/typewriter sequences, and show content immediately. Never make content available only after an animation.
- Keep transitions short and purposeful. Suggested starting ranges: 100–180 ms for micro-interactions; 160–240 ms for drawers and small layout changes; up to 500–700 ms only for the landing system-check sequence or a single post-analysis evidence reveal. These are guidelines, not a reason to animate everything.
- Prefer opacity and small positional changes. Avoid large travel distances, springy overshoot, scale-popping, and dramatic camera-like moves.
- Keyboard focus, screen-reader semantics, keyboard shortcuts, and direct interaction must work regardless of animation state.
- Animation must never change, infer, rank, score, conceal, or fabricate analyzer data. Never animate a confidence value as if it were a measured progress value.
- Keep the UI local-only: no remote animation assets, CDN scripts, remote fonts, or runtime network requests.
- If a component's original effect conflicts with these rules, simplify it or reject it. Existing licensing requirements still apply.

## 3. Required behavior by surface

### Landing
- Keep the existing non-marketing, left-aligned capture-first layout.
- Add a restrained cinematic touch: choose **one** primary signature, either a brief wordmark reveal or a minimal evidence-line/motif resolving into place. Do not combine multiple hero effects.
- The signature must not block the dropzone or system status, and must disappear immediately under reduced motion.
- Preserve truthful system checks and the real drag-and-drop upload flow.

### Overview
- On successful analysis, one compact provenance distribution reveal is allowed. Play once for that result, not continuously on rerender.
- Severity summaries and coverage bars may transition from their prior value to the actual returned value. Do not animate from invented values.
- Keep the existing dense two-column layout; do not introduce a large hero or stat-tile row.

### Findings
- Selected-row indication, filter updates, and detail-drawer transitions may animate subtly.
- Do not animate each table row on initial render or make sorting/filtering feel slow.
- Large lists must remain responsive.

### Tunnels
- Candidate elimination stages may reveal in sequence only when each stage corresponds to real `candidate_sets` data. The sequence must be skippable and must not imply extra analysis.
- Keep eliminated candidates and reasons readable without waiting for the animation.

### Claims and coverage
- Tier glyphs, provenance summaries, coverage segments, and detail drawers may use restrained state transitions.
- Never use motion, color, or animation intensity to imply a tier stronger than the source data.

### Upload and analysis states
- Every state remains understandable with motion disabled.
- Validation errors and completion messages appear immediately when known.
- Do not fabricate upload percentages, analysis stages, ETA, or packet counts.

## 4. Update instructions for the project docs

### Add to `AGENTS.md`
Add a `## Motion and animation` section using sections 1 and 2 above. Then update any older blanket prohibition on animations as follows:

> Avoid gratuitous motion, but the repo owner explicitly approves the bounded motion behaviors in `Motion Design Addendum`. Those behaviors are permitted when they follow the addendum. All other existing visual, security, offline, data-truth, and ownership constraints remain in force. Reduced motion is mandatory.

Where the file says page agents may build composites “with no new animations,” clarify:

> Page agents may use only the approved motion patterns and existing animation primitives already established by Phase 0. They must not add a new animation library or invent new motion patterns. If a shared primitive or dependency is missing, record it in `NEEDS.md`.

### Add to `PHASE0_PROMPT.md`
In the frontend scaffold/design-system work, instruct the foundation agent to:
1. Read this addendum.
2. Establish shared motion tokens/utilities and a global reduced-motion policy.
3. Decide whether CSS alone is sufficient; add Motion for React only if justified.
4. Implement only shared primitives and states that Phase 0 owns. Do not build page-specific signature animations beyond the landing placeholder/system-check behavior.
5. Add an animation/reduced-motion section to `web-ui/COMPONENTS.md` or the appropriate shared design documentation, including examples and the list of allowed motion patterns.
6. Ensure `/__gallery` shows interaction states without autoplaying distracting loops.
7. Verify reduced motion, keyboard interaction, and no fake progress.

### Add to `AGENT_BRIEFS.md`
- Include the motion addendum in every page-agent preamble.
- Remove the old broad ban on all new animations only to the extent specified in the `AGENTS.md` clarification above.
- Landing/overview agent owns the landing signature animation and one-shot post-analysis provenance reveal.
- Findings, tunnels, claims, and coverage agents may use the approved patterns only; do not install packages or create new shared animation primitives.
- The final polish pass must test both normal motion and `prefers-reduced-motion: reduce`.

## 5. Acceptance checklist

- [ ] Landing has at most one restrained signature reveal.
- [ ] System check uses real status data; no fake logs or fake progress; skip works.
- [ ] Upload and analysis transitions are tied to real states.
- [ ] Overview provenance reveal runs once after successful results load, not on every render.
- [ ] Tables and large lists do not animate row-by-row.
- [ ] No continuous decorative animation.
- [ ] Reduced-motion mode removes reveals and makes content immediately available.
- [ ] Keyboard and focus behavior work with motion on and off.
- [ ] No non-local requests, remote assets, or new runtime network dependencies.
- [ ] Existing tests, typecheck, and build pass.
- [ ] No changes to analyzer logic, schema, rules, findings, or existing TUI behavior.

**Agent instruction:** Treat this as an explicit, narrow update to the project's motion rules, not permission to reinterpret or relax any other constraint.
