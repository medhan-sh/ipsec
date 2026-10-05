/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          chrome: "var(--surface-chrome)",
          base: "var(--surface-base)",
          panel: "var(--surface-panel)",
          raised: "var(--surface-raised)",
        },
        border: {
          hairline: "var(--border-hairline)",
          strong: "var(--border-strong)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          tertiary: "var(--text-tertiary)",
        },
        signal: {
          DEFAULT: "var(--signal-green)",
          dim: "var(--signal-dim)",
          faint: "var(--signal-faint)",
        },
        severity: {
          critical: "var(--severity-critical)",
          high: "var(--severity-high)",
          medium: "var(--severity-medium)",
          low: "var(--severity-low)",
          info: "var(--severity-info)",
        },
        amber: {
          sample: "var(--color-amber-sample)",
        },
      },
      borderRadius: {
        data: "2px",
        overlay: "4px",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "monospace"],
        sans: ["'IBM Plex Sans'", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 8px rgba(0, 255, 127, 0.35)",
        focus: "0 0 0 1px #00ff7f, 0 0 8px rgba(0, 255, 127, 0.35)",
      },
    },
  },
  plugins: [],
};
