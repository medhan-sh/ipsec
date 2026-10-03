# web-ui/DEPS.md — NPM Dependencies Manifest

All dependencies installed in `web-ui/` must be recorded here with their exact pinned version, purpose, and component consumer.
**Rules:** Only Phase 0 may add dependencies. Page agents must never run `npm install` or introduce new dependencies.

## Production Dependencies

| Package | Version | Purpose / Consumer | License |
|---|---|---|---|
| `react` | `^18.3.1` | Core UI library | MIT |
| `react-dom` | `^18.3.1` | React DOM renderer | MIT |
| `react-router-dom` | `^6.26.2` | Routing & URL state | MIT |
| `@radix-ui/react-dialog` | `^1.1.1` | Modal & Dialog primitives (Shortcut help, Command palette) | MIT |
| `@radix-ui/react-tabs` | `^1.1.0` | Accessible tab primitives (Findings passes/failures) | MIT |
| `@radix-ui/react-tooltip` | `^1.1.2` | Monospace chip SHA-256 tooltips | MIT |
| `@radix-ui/react-separator` | `^1.1.0` | Hairline dividers | MIT |
| `@radix-ui/react-slot` | `^1.1.0` | Radix polymorphic asChild slot component | MIT |
| `@radix-ui/react-scroll-area` | `^1.1.0` | Accessible custom scroll areas | MIT |
| `@radix-ui/react-select` | `^2.1.1` | Accessible filter dropdowns | MIT |
| `@radix-ui/react-toggle-group` | `^1.1.0` | Tier & severity toggle filters | MIT |
| `@radix-ui/react-collapsible` | `^1.1.0` | Capture explorer & candidate elimination trees | MIT |
| `cmdk` | `^1.0.0` | Command palette on `:` and `Ctrl+K` | MIT |
| `sonner` | `^1.5.0` | Toast notifications | MIT |
| `lucide-react` | `^0.441.0` | Iconography (lucide only per stack) | MIT |
| `clsx` | `^2.1.1` | Classname concatenation utility | MIT |
| `tailwind-merge` | `^2.5.2` | Tailwind class merging | MIT |
| `@tanstack/react-table` | `^8.20.5` | Headless table logic (Findings table) | MIT |
| `@tanstack/react-virtual` | `^3.10.7` | Large dataset virtualization | MIT |
| `react-resizable-panels` | `^2.1.3` | Resizable shell explorer & detail drawer | MIT |
| `@fontsource/jetbrains-mono` | `^5.0.21` | Bundled monospace font (UI chrome, tables, data) | OFL-1.1 |
| `@fontsource/ibm-plex-sans` | `^5.0.19` | Bundled sans-serif font (long-form prose only) | OFL-1.1 |

## Development Dependencies

| Package | Version | Purpose | License |
|---|---|---|---|
| `typescript` | `^5.5.4` | Strict TypeScript compiler | Apache-2.0 |
| `vite` | `^5.4.6` | Development server & production bundler | MIT |
| `@vitejs/plugin-react` | `^4.3.1` | React Fast Refresh for Vite | MIT |
| `tailwindcss` | `^3.4.11` | Utility-first CSS engine | MIT |
| `autoprefixer` | `^10.4.20` | CSS vendor prefixing | MIT |
| `postcss` | `^8.4.47` | PostCSS processing | MIT |
| `@types/react` | `^18.3.5` | TypeScript types for React | MIT |
| `@types/react-dom` | `^18.3.0` | TypeScript types for React DOM | MIT |
| `@types/node` | `^20.16.5` | TypeScript types for Node (path resolution) | MIT |
