/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B1220",
        mist: "#E8EEF7",
        accent: "#1FA97A",
        accent2: "#0E7C66",
        copper: "#C4A35A",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        soft: "0 20px 60px rgba(11,18,32,0.18)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        drift: {
          "0%,100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        glow: {
          "0%,100%": { opacity: "0.45" },
          "50%": { opacity: "0.85" },
        },
      },
      animation: {
        rise: "rise 0.8s ease-out both",
        drift: "drift 7s ease-in-out infinite",
        glow: "glow 4.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
