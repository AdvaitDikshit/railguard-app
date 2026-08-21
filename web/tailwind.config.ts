import type { Config } from "tailwindcss";

// Design tokens for the A+C direction: machine-vision inspection tool
// (dark image canvas, thin precise overlays, monospace data) disciplined
// with Swiss railway-signage restraint (calm off-white chrome, one
// functional accent, strong type hierarchy). See project design brief.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "#f7f5f1", // warm off-white chrome (not pure grey/white)
        panel: "#ffffff",
        ink: "#1c2024",
        "ink-soft": "#5b6470",
        rule: "#dcd7cd",
        canvas: "#15171b", // dark inspection viewport — the one deliberate dark surface
        "canvas-border": "#2c2f35",
        accent: "#a3182a", // single functional accent (muted railway red) — primary actions only
        "accent-soft": "#f3e3e3",
        sev: {
          critical: "#b3261e",
          high: "#c1701f",
          moderate: "#a68a1f",
          low: "#2f7a4f",
          ok: "#2f7a4f",
        },
      },
      fontFamily: {
        sans: ["var(--font-public-sans)", "Arial", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "3px",
        DEFAULT: "4px",
      },
    },
  },
  plugins: [],
};

export default config;
