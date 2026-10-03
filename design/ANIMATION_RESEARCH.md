# Umbra Animation & Motion Research

**Author:** Phase 0 Foundation Agent
**Context:** Motion Design Addendum (`UMBRA_MOTION_ADDENDUM.md`, `AGENTS.md`)
**Design Philosophy:** Illuminated Evidence. Umbra is a passive IPsec forensics console: quiet by default, terminal discipline, responsive to interaction, and expressive only when real analysis results arrive. All motion must respect `prefers-reduced-motion: reduce`, introduce zero remote/CDN dependencies, and never simulate progress or distort data certainty.

---

## 1. Candidate Animation Shortlist

### Candidate 1: Forensic Wordmark / Evidence Line Resolve (Landing Page)
- **Source / Reference:** React Bits (Decrypted / Text Pressure motifs adapted to subtle hairline SVG line-draw or opacity-stagger resolve) / Motion for React text reveal.
- **License:** MIT
- **Intended Surface:** Landing Page (`/`, outside shell).
- **Rationale for Fit:** Landing needs a single, calm signature touch to establish the forensic console feel without feeling like a marketing site or a fake Hollywood hacker terminal. A brief (400–600ms) one-shot resolve of the `umbra` wordmark or hairline evidence motif on initial session load fits the "illuminated evidence" motif.
- **Dependencies vs Native CSS:** Can be achieved with standard CSS keyframe transitions (`stroke-dasharray` / `opacity` + subtle transform) or lightweight `motion/react` `initial`/`animate`.
- **Accessibility & Reduced Motion:** Under `prefers-reduced-motion: reduce`, the signature displays immediately with zero delay and opacity 1. Skippable on any keypress or click.
- **Recommendation:** **Adopt (Native CSS).** Implement via a CSS utility class (`.animate-signature-resolve`) with immediate fallback for reduced motion. No dedicated library needed.

---

### Candidate 2: Provenance Distribution Illumination (Overview Page)
- **Source / Reference:** Custom "Illuminated Evidence" staged luminance reveal inspired by physical instrument readouts / Motion for React layout stagger.
- **License:** MIT (concept derived from project PRD)
- **Intended Surface:** Overview (`/app/overview`).
- **Rationale for Fit:** When an analysis finishes, the claims breakdown transitions from dark to illuminated based on evidence tier (OBSERVED glows spring green, INFERRED tiers receive fractional luminance, NOT_OBSERVABLE remains dark). This is the thematic centerpiece of Umbra.
- **Dependencies vs Native CSS:** Can be implemented with pure CSS transitions on CSS custom properties (`--tier-lum`, `transition: width 350ms cubic-bezier(0.16, 1, 0.3, 1), opacity 350ms`).
- **Accessibility & Reduced Motion:** Plays exactly once per new analysis result; never loops on rerender. Under reduced motion, bar widths and opacities render immediately at their final values.
- **Recommendation:** **Adopt (Native CSS transitions + Tailwind tokens).** Completely achievable using Tailwind transition utilities and token classes.

---

### Candidate 3: Micro-Interactions (Selected-Row Signal Bar, Gutter Highlight, Tab Pills)
- **Source / Reference:** shadcn/ui + Radix UI interactive primitives.
- **License:** MIT
- **Intended Surface:** Tables (Findings, Gaps), Collapsible Drawers, Capture Explorer.
- **Rationale for Fit:** Terminal discipline requires fast, crisp feedback. A 2px spring-green border on the selected row and smooth 100–160ms background tint (`rgba(0, 255, 127, 0.08)`) gives instant feedback without layout shifts.
- **Dependencies vs Native CSS:** Pure CSS (`transition: background-color 120ms ease-out, border-color 120ms ease-out`).
- **Accessibility & Reduced Motion:** Does not rely on motion to convey state: selection also changes aria-selected, border indicator, and drawer opening. Instant when reduced motion is requested.
- **Recommendation:** **Adopt (Native CSS).** Use standard Tailwind `transition-colors duration-150`.

---

### Candidate 4: Staged Candidate Elimination Steps (Tunnels Page)
- **Source / Reference:** Staged stepper / bar visualization (React Bits Stepper / Step Progress).
- **License:** MIT
- **Intended Surface:** Tunnels (`/app/tunnels`).
- **Rationale for Fit:** Tunnels demonstrate the elimination-before-ranking pipeline. Showing the progression (universe size → filtered by SPI → filtered by DH group → survivors) helps analysts understand how candidates were eliminated.
- **Dependencies vs Native CSS:** Can be achieved with CSS transitions linked to real `candidate_sets` data.
- **Caution:** Must never simulate steps or delay display of eliminated candidates. The full list and reasons must be readable immediately.
- **Recommendation:** **Adopt (Native CSS, data-bound).** Render stages statically by default; animate width/opacity only if the user triggers a re-run or step change (160ms ease-out). No extra packages required.

---

### Candidate 5: Motion for React (`motion`) Framework Evaluation
- **Source / Reference:** [Motion for React](https://motion.dev/) (formerly Framer Motion)
- **License:** MIT
- **Intended Surface:** Shared drawer / sheet entrance, resizable panels, command palette modals.
- **Rationale for Fit:** Evaluated whether an external library is required for Umbra's bounded animations.
- **Evaluation:**
  - Radix UI (`@radix-ui/react-dialog`, `@radix-ui/react-tabs`, etc.) and Tailwind CSS already provide `data-[state=open]:animate-in` utilities with GPU-accelerated CSS transitions that cleanly handle drawers, dialogs, and tooltips.
  - Adding `motion` (approx. 30–45kB minified + gzipped) solely for simple opacity and slide transitions violates the rule: *"Do not add a new animation library solely for one tiny effect."*
- **Recommendation:** **Skip as an npm dependency for Phase 0.** Native CSS transitions, Tailwind animation classes, and Radix state attributes fully satisfy all Approved Motion criteria in `UMBRA_MOTION_ADDENDUM.md` with zero runtime dependency overhead and 100% offline stability. If later pages prove an absolute mathematical necessity for layout springs, it can be proposed via `NEEDS.md`, but native CSS is superior here.

---

## 2. Animation & Reduced Motion Matrix

| Surface / Component | Interaction | Implementation | Duration | Reduced Motion (`prefers-reduced-motion: reduce`) |
|---|---|---|---|---|
| **Landing** Wordmark | Initial session resolve | CSS keyframes (`opacity`, `transform: translateY(2px) -> 0`) | 400ms ease-out | `animation: none; opacity: 1;` (Instant) |
| **Landing** System Check | Truthful probe reveal | Sequential display of real `/api/status` probes | ~120ms per line | All lines rendered instantly |
| **Overview** Provenance | One-shot illumination | CSS width + opacity transition on result load | 300–400ms cubic-bezier | Render static final bar width instantly |
| **Overview / Claims** Coverage | Segment transition | CSS width transition from prior to current value | 200ms ease-out | Instant layout update |
| **Findings / Tables** | Selected row signal | CSS 2px spring-green border + faint tint | 120ms ease-out | Instant color switch |
| **Shell** Detail Drawer | Slide-in drawer | CSS translate / opacity via Radix sheet | 180ms cubic-bezier(0.16, 1, 0.3, 1) | Instant display (`transition: none`) |
| **Shell** Command Palette | Dialog open / close | CSS scale + opacity via Radix dialog | 150ms ease-out | Instant display |
| **Explorer** Drag-and-Drop | Dropzone hover / active | Border highlight + background tint | 120ms ease-out | Instant border switch |

---

## 3. Global Reduced-Motion Policy

All motion tokens and animation utilities in `tokens.css` and `globals.css` must adhere to:

```css
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

This guarantees:
1. Keyboard accessibility, focus rings, and direct manipulation never wait on animations.
2. Content is immediately readable by screen readers and users who prefer reduced motion.
3. No fake analysis progress, loops, or text scrambling can ever run.
