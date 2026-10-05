# Umbra Motion & Interaction Manifest

**Document:** `web-ui/MOTION.md`  
**Compliance Authority:** `UMBRA_MOTION_ADDENDUM.md`, `AGENTS.md`, and Phase 0 Foundation rules.  
**Philosophy:** Minimalist Maximalism — "Quiet until it moves, then unforgettable." Evidence becomes illuminated as it becomes observable.

---

## 1. Implemented Motion Choreography & Visual Moments

| Surface | Interaction / Effect | Implementation | Trigger & Frequency | Reduced Motion (`prefers-reduced-motion: reduce`) |
|---|---|---|---|---|
| **Landing Hero** | Architectural Evidence Topology Vector Animation | CSS keyframe transitions on SVG paths (`pulse`, `spin`) and glow filters | Continuous but restrained; terminal discipline | Statically rendered vector geometry without animation |
| **Landing System Check** | Truthful Diagnostic Probe Reveal | `setInterval` at 120ms stepping through real `/api/status` fields | Runs once on first session load | All probe lines rendered immediately (`sessionStorage` persistence) |
| **Landing Capture Inlet** | Diagnostic Dropzone Feedback | Border color & background tint transition (150ms ease-out) | On dragover, file drop, upload, or selection | Instant border change |
| **Analysis Lifecycle** | Active Convergence Scanning Beam | TopBar status badge + `<main>` sticky emerald scanning beam (`animate-pulse`) | Active strictly while `runStatus === "running"` | Static indicator text, no pulsing |
| **Overview Provenance** | Provenance Distribution Illumination | Dynamic CSS width & opacity transitions on tier bars | Plays strictly once per newly analyzed capture | Instant final bar widths rendered directly |
| **Findings Ledger** | Selected Row Indication | 2px spring-green border (`border-l-signal`) + `bg-signal-faint` | Instant on row selection / keyboard navigation | Instant highlight without color transitions |
| **Findings Detail Drawer** | Forensic Investigation Slide-in | Radix Sheet GPU-accelerated translate-x | On selecting finding or pressing Enter | Instant drawer display |
| **Tunnels Elimination** | Candidate Staged Funnel Segment Selection | Data-bound proportional segment highlight | On clicking elimination step or hover | Instant segment highlight |
| **Command Palette** | Modal Scale & Opacity | Radix Dialog transition (150ms ease-out) | On `:` or `Ctrl+K` | Instant display |

---

## 2. Prohibited Behaviors Strictly Omitted
- **Zero fake progress:** No simulated upload percentages, fake packet counters, or artificial delays.
- **Zero matrix rain / CRT scanlines:** No retro-hacker cliches or decorative noise overlays.
- **Zero remote assets:** Zero CDN scripts, remote fonts, or network animation libraries.
- **Zero tier distortion:** Never use brightness or motion to imply a stronger evidence tier than the underlying data provides.

---

## 3. Global Reduced-Motion Verification
Enforced globally via `tokens.css`:
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
All components check `window.matchMedia("(prefers-reduced-motion: reduce)").matches` to initialize immediately into their completed state.
