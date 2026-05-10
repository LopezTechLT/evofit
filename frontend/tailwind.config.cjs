/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ember: {
          500: '#f97316',
          600: '#ea580c'
        },
        rouge: {
          500: '#ef4444',
          600: '#dc2626'
        }
      },
      borderRadius: {
        '2xl': '1.25rem'
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        elevated: '0 10px 40px rgba(0,0,0,0.08)'
      }
    }
  },
  plugins: []
}
