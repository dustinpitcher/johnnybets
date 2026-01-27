import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Terminal-inspired color scheme
        terminal: {
          bg: "#0a0a0a",
          surface: "#141414",
          border: "#262626",
          text: "#e5e5e5",
          muted: "#737373",
          accent: "#22c55e",
          "accent-dim": "#166534",
          warning: "#f59e0b",
          error: "#ef4444",
          info: "#3b82f6",
        },
        // Sport-specific colors
        nfl: {
          primary: "#013369",
          secondary: "#d50a0a",
        },
        nhl: {
          primary: "#000000",
          secondary: "#c8102e",
        },
        mlb: {
          primary: "#002d72",
          secondary: "#d50032",
        },
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "Fira Code",
          "SF Mono",
          "Consolas",
          "monospace",
        ],
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      animation: {
        "cursor-blink": "blink 1s step-end infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;

