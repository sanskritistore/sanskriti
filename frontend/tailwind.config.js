/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Sanskriti brand palette - warm, Indian-market friendly
        brand: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
        },
        hindi: {
          // Colors used in Hindi UI metaphors
          success: "#16a34a",
          warning: "#f59e0b",
          danger: "#dc2626",
        },
      },
      fontFamily: {
        // Hindi-first font stack (Noto Sans Devanagari for Hindi, system fallback)
        sans: [
          "Noto Sans Devanagari",
          "Noto Sans",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      fontSize: {
        // Larger base sizes for readability by non-technical users
        base: ["1.05rem", "1.65rem"],
        lg: ["1.15rem", "1.75rem"],
      },
    },
  },
  plugins: [],
};
