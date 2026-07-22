/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ivory: "#FBF7EF",
        cream: "#F4ECD9",
        sand: "#EFE6D2",
        ink: "#211F1A",
        char: "#232320",
        gold: "#F5D45F",
        goldDeep: "#DDB43A",
        risk: {
          low: "#22A06B",
          moderate: "#E0A92E",
          high: "#E8730C",
          severe: "#DC3545",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Poppins", "Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 2px 20px rgba(90, 74, 40, 0.06)",
        soft: "0 1px 3px rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
};
