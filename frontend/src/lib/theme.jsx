import { createContext, useContext, useState, useEffect, useCallback } from "react";

const KEY = "cvforge_theme";
const ThemeCtx = createContext(null);

function apply(theme) {
  const el = document.documentElement;
  if (theme === "light") el.classList.add("light");
  else el.classList.remove("light");
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const saved = typeof localStorage !== "undefined" && localStorage.getItem(KEY);
    if (saved) return saved;
    return "dark";
  });

  useEffect(() => { apply(theme); localStorage.setItem(KEY, theme); }, [theme]);

  const toggle = useCallback(() => setTheme((t) => (t === "light" ? "dark" : "light")), []);

  return <ThemeCtx.Provider value={{ theme, toggle }}>{children}</ThemeCtx.Provider>;
}

export const useTheme = () => useContext(ThemeCtx);

export function ThemeToggle({ className = "" }) {
  const { theme, toggle } = useTheme();
  const dark = theme !== "light";
  return (
    <button onClick={toggle} aria-label="Toggle theme"
      className={`p-2 border border-line text-muted hover:text-accent hover:border-accent transition-colors ${className}`}>
      {dark ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      )}
    </button>
  );
}
