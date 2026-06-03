/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'background': '#f0fdfa', // Soft teal background
        'surface': '#ffffff',    // White for cards/containers
        'primary': '#c084fc',     // Soft purple-400
        'secondary': '#2dd4bf',   // Teal-400
        'foreground': '#4a4e69', // Soft purple-gray for text
        'muted': '#f0fdfa',       // Soft teal-50 for inputs/subtle backgrounds
        'border-color': '#99f6e4', // Soft teal-200 for borders
        'brand-safe': '#86efac', // Soft green-300
        'brand-caution': '#2dd4bf', // Teal-400
        'brand-unsafe': '#fca5a5', // Soft red-300
        'accent-purple': '#d8b4fe', // Soft purple-300
        'accent-yellow': '#5eead4', // Teal-300
      }
    },
  },
  plugins: [],
}