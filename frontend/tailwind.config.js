/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        noto: ['"Noto Sans KR"', "sans-serif"],
        gowun: ['"Gowun Dodum"', "sans-serif"],
      },
    },
  },
  plugins: [],
};
