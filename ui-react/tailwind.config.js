/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark mode palette (default / dark:)
        bg: {
          primary: '#0B0F19',
          card: '#161B22',
          code: '#0D1117',
          input: '#0D1117',
          border: '#30363D',
          tab: '#21262D',
        },
        accent: {
          blue: '#3B82F6',
          green: '#238636',
          red: '#DA3633',
          purple: '#7C3AED',
          orange: '#F97316',
          blueDark: '#1F2937',
        },
        text: {
          primary: '#E6EDF3',
          secondary: '#8B949E',
          muted: '#484F58',
        },
        // Light mode palette (prefixed "lt-" to avoid conflict with Tailwind defaults)
        lt: {
          bg: {
            primary: '#FFFFFF',
            card: '#F6F8FA',
            code: '#F6F8FA',
            input: '#FFFFFF',
            border: '#D0D7DE',
            tab: '#EBEEF2',
          },
          text: {
            primary: '#1F2328',
            secondary: '#656D76',
            muted: '#8C959F',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
