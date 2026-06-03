import type { Config } from "tailwindcss";

// Tremor v3 requires Tailwind. The content paths must include the
// Tremor package so its classes are kept by the JIT.
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "./node_modules/@tremor/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Match the design-mockup palette — see frontend/_design/.
        viberoi: {
          bg: "#080808",
          card: "#101010",
          surface: "#181818",
          accent: "#00D4FF",
          text: "#F0F0F0",
          sub: "#5A5A5A",
        },
      },
      fontFamily: {
        ui: ["Outfit", "sans-serif"],
        body: ["DM Sans", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
} satisfies Config;
