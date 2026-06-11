/** @type {import('tailwindcss').Config} */
const tok = (v) => `rgb(var(${v}) / <alpha-value>)`;
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: tok('--ink'),
        panel: tok('--panel'),
        panel2: tok('--panel2'),
        line: tok('--line'),
        line2: tok('--line2'),
        fg: tok('--fg'),
        muted: tok('--muted'),
        accent: tok('--accent'),
        accentdim: tok('--accentdim'),
        good: tok('--good'),
        warn: tok('--warn'),
        bad: tok('--bad'),
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        read: ['Newsreader', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
