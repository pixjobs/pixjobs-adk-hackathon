import plugin from 'tailwindcss/plugin';
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class', // dark mode enabled via 'dark' class
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './app/**/*.{js,ts,jsx,tsx}',
    './layouts/**/*.{js,ts,jsx,tsx}',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: 'var(--accent-color)',
        background: 'var(--bg-primary)',
        text: 'var(--text-primary)',
        border: 'var(--border-color)',
        bubbleUser: 'var(--bubble-user)',
        bubbleAssistant: 'var(--bubble-assistant)',
      },
      fontFamily: {
        sans: ['Noto Sans', 'sans-serif'],
      },
      boxShadow: {
        chat: '0 2px 6px rgba(0, 0, 0, 0.1)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
    require('daisyui'),
    plugin(function ({ addUtilities }) {
      const heightUtilities = {
        '.h-dvh': { height: '100dvh' },
        '.min-h-dvh': { 'min-height': '100dvh' },
        '.max-h-dvh': { 'max-height': '100dvh' },
      };

      const fallbackHeightUtilities = {
        '@supports not (height: 100dvh)': {
          '.h-dvh': { height: '100vh' },
          '.min-h-dvh': { 'min-height': '100vh' },
          '.max-h-dvh': { 'max-height': '100vh' },
        },
      };

      addUtilities(heightUtilities);
      addUtilities(fallbackHeightUtilities);
    }),
  ],
};

export default config;
