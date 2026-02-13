import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f172a",
        surface: "#1e293b",
        border: "#334155",
        "text-primary": "#f8fafc",
        "text-secondary": "#94a3b8",
        accent: "#3b82f6",
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
      },
    },
  },
  plugins: [],
};

export default config;
