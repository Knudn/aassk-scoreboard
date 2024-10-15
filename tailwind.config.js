/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
    "./node_modules/flowbite/**/*.js"  // Add this line
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('flowbite/plugin')  // Add this line
  ],
}