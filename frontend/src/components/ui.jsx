import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export function Protected({ children }) {
  const { authed } = useAuth();
  return authed ? children : <Navigate to="/login" replace />;
}

export function Spinner({ label = "Working" }) {
  return (
    <div className="flex items-center gap-3 font-mono text-sm text-muted">
      <span className="relative inline-block w-24 h-1 bg-line overflow-hidden scan" />
      {label}…
    </div>
  );
}

export function Banner({ kind = "error", children }) {
  const map = {
    error: "border-bad text-bad",
    ok: "border-good text-good",
    info: "border-line2 text-muted",
  };
  if (!children) return null;
  return (
    <div className={`border ${map[kind]} bg-ink/60 px-3 py-2 font-mono text-[12px]`}>
      {children}
    </div>
  );
}

export function ScoreGauge({ score = 0 }) {
  const s = Math.max(0, Math.min(100, score));
  const color = s >= 80 ? "#7ee787" : s >= 60 ? "#f0c674" : "#ff6b6b";
  return (
    <div className="flex items-center gap-4">
      <div className="relative w-20 h-20">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" stroke="#2a2a2e" strokeWidth="8" />
          <circle
            cx="50" cy="50" r="42" fill="none" stroke={color} strokeWidth="8"
            strokeDasharray={`${(s / 100) * 264} 264`} strokeLinecap="butt"
            style={{ transition: "stroke-dasharray 0.8s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display font-extrabold text-2xl" style={{ color }}>{s}</span>
        </div>
      </div>
      <div>
        <div className="label">ATS score</div>
        <div className="font-mono text-sm text-fg">{s >= 80 ? "Strong match" : s >= 60 ? "Decent — tighten keywords" : "Weak — revise"}</div>
      </div>
    </div>
  );
}
