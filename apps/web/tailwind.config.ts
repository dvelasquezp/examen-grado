/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#1e3a5f",
          light: "#2d5a8e",
        },
        accent: "#c8922a",
        doctrine: "#2563eb",
        ai: "#d97706",
        exam: "#ea580c",
      },
    },
  },
  plugins: [],
};
