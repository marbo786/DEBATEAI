/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Syne", "system-ui", "sans-serif"],
        body: ["DM Sans", "system-ui", "sans-serif"],
      },
      animation: {
        "belief-bar": "beliefBar 0.8s ease-out forwards",
      },
      keyframes: {
        beliefBar: {
          "0%": { width: "var(--prev-width, 50%)" },
          "100%": { width: "var(--curr-width, 50%)" },
        },
      },
    },
  },
  plugins: [],
};
