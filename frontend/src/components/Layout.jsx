import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useCredits } from "../lib/credits";
import { ThemeToggle } from "../lib/theme";

const links = [
  { to: "/cv", label: "Base CV" },
  { to: "/generate", label: "Generate" },
  { to: "/applications", label: "History" },
  { to: "/billing", label: "Billing" },
];

export default function Layout() {
  const { logout } = useAuth();
  const { summary } = useCredits();
  const nav = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-line bg-ink/70 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-5 h-16 flex items-center justify-between gap-3">
          <NavLink to="/cv" className="flex items-baseline gap-2 shrink-0">
            <span className="font-display font-extrabold text-xl tracking-tight">CVForge</span>
            <span className="label text-accent hidden md:inline">/ forge per job</span>
          </NavLink>

          <nav className="flex items-center gap-1">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to}
                className={({ isActive }) =>
                  `font-mono text-[12px] uppercase tracking-[0.12em] px-2.5 py-2 border transition-colors ${
                    isActive ? "border-accent text-accent" : "border-transparent text-muted hover:text-fg"}`
                }>
                {l.label}
              </NavLink>
            ))}

            {summary && (
              <NavLink to="/billing" title="Credit balance"
                className="ml-1 font-mono text-[12px] px-2.5 py-1.5 border border-line text-fg hover:border-accent transition-colors">
                <span className={summary.credits <= summary.credits_per_generation ? "text-bad" : "text-accent"}>
                  {summary.credits}
                </span>
                <span className="text-muted"> cr</span>
              </NavLink>
            )}

            <ThemeToggle className="ml-1" />

            <button onClick={() => { logout(); nav("/"); }}
              className="font-mono text-[12px] uppercase tracking-[0.12em] px-2.5 py-2 text-muted hover:text-bad transition-colors">
              Exit
            </button>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto px-5 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="max-w-5xl mx-auto px-5 py-4 label flex justify-between">
          <span>CVForge — ATS-tuned · AI-powered</span>
          <span className="text-line2">v0.3</span>
        </div>
      </footer>
    </div>
  );
}
