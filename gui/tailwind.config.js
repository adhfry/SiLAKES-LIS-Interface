/** @type {import('tailwindcss').Config} */
// Palet & token diambil verbatim dari produli.labkesdasumenep.id
// (/var/www/produli.labkesdasumenep.id/app/assets/css/main.css @theme block)
// supaya SiLAKES LIS Interface konsisten dgn identitas visual ekosistem Labkesda.
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0fcfb', 100: '#ccf7f3', 200: '#99efe9', 300: '#5ce3da', 400: '#2bd3c8',
          500: '#00a59a', 600: '#00857d', 700: '#006b65', 800: '#00544f', 900: '#004541', 950: '#002927',
          DEFAULT: '#00a59a',
        },
        secondary: {
          50: '#f6fcf1', 100: '#eaf8df', 200: '#d0f0ba', 300: '#aee48d', 400: '#8cd35f',
          500: '#65b32e', 600: '#4f8f23', 700: '#3b6d19', 800: '#2a4f12', 900: '#234211', 950: '#112306',
          DEFAULT: '#65b32e',
        },
        accent: {
          50: '#f0f6fa', 100: '#daeaf3', 200: '#badae8', 300: '#8bc3da', 400: '#57a4c6',
          500: '#3385aa', 600: '#23698b', 700: '#1d5471', 800: '#19465e', 900: '#003b5c', 950: '#051d2e',
          DEFAULT: '#003b5c',
        },
        surface: {
          50: '#f4fbf9', 100: '#e1f5f0', 200: '#c2ebe0', 300: '#9ddbcb', 400: '#73c4b2',
          500: '#4ea693', 600: '#388574', 700: '#2e6b5e', 800: '#26554b', 900: '#21473f', 950: '#102722',
          DEFAULT: '#f4fbf9',
        },
        danger: {
          50: '#fef2f2', 100: '#fee2e2', 200: '#fecaca', 300: '#fca5a5', 400: '#f87171',
          500: '#ef4444', 600: '#dc2626', 700: '#b91c1c', 800: '#991b1b', 900: '#7f1d1d', 950: '#450a0a',
          DEFAULT: '#ef4444',
        },
        warning: {
          50: '#fffbeb', 100: '#fef3c7', 200: '#fde68a', 300: '#fcd34d', 400: '#fbbf24',
          500: '#f59e0b', 600: '#d97706', 700: '#b45309', 800: '#92400e', 900: '#78350f', 950: '#451a03',
          DEFAULT: '#f59e0b',
        },
        info: {
          50: '#f0f9ff', 100: '#e0f2fe', 200: '#bae6fd', 300: '#7dd3fc', 400: '#38bdf8',
          500: '#0284c7', 600: '#0369a1', 700: '#075985', 800: '#0c4a6e', 900: '#082f49', 950: '#041f33',
          DEFAULT: '#0284c7',
        },
        success: {
          50: '#ecfdf5', 100: '#d1fae5', 200: '#a7f3d0', 300: '#6ee7b7', 400: '#34d399',
          500: '#10b981', 600: '#059669', 700: '#047857', 800: '#065f46', 900: '#064e3b', 950: '#022c22',
          DEFAULT: '#10b981',
        },
        neutral: {
          50: '#f8fafc', 100: '#f1f5f9', 200: '#e2e8f0', 300: '#cbd5e1', 400: '#94a3b8',
          500: '#64748b', 600: '#475569', 700: '#334155', 800: '#1e293b', 900: '#0f172a', 950: '#020617',
          DEFAULT: '#64748b',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Segoe UI', 'system-ui', 'sans-serif'],
        heading: ['Outfit', '"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Cascadia Code"', 'Consolas', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px rgb(0 165 154 / 0.5)',
        card: '0 4px 24px -4px rgb(0 59 92 / 0.1)',
        glass: '0 8px 32px 0 rgb(0 59 92 / 0.07)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #2bd3c8 0%, #00857d 100%)',
        'radial-fade-light': 'radial-gradient(circle at 50% -10%, #e1f5f0 0%, #f4fbf9 45%, #f8fafc 100%)',
        'radial-fade-dark': 'radial-gradient(circle at 50% -10%, #16465e 0%, #0f172a 45%, #020617 100%)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2.2s linear infinite',
      },
    },
  },
  plugins: [],
}
