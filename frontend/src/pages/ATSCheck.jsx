import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { ThemeToggle } from "../lib/theme";

const CATEGORY_LABELS = {
  sections: "Sections",
  ats_essentials: "ATS essentials",
  hr_red_flags: "HR red flags",
  discrimination: "Discrimination",
  seniority: "Seniority",
  tailoring: "Tailoring",
};
const SEVERITY_COLOR = { high: "#f85149", medium: "#d29922", low: "#7ee787" };

const scoreColor = (n) => (n >= 80 ? "#7ee787" : n >= 60 ? "#d29922" : "#f85149");

export default function ATSCheck() {
  const { authed } = useAuth();
  const [file, setFile] = useState(null);
  const [rawText, setRawText] = useState("");
  const [jd, setJd] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const fileRef = useRef();

  const canSubmit = !busy && (file || rawText.trim().length >= 50);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await api.atsCheck({ file, rawText: file ? "" : rawText, jobDescription: jd }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-ink/70 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-5 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-baseline gap-2">
            <span className="font-display font-extrabold text-xl tracking-tight">CVForge</span>
            <span className="label text-accent hidden sm:inline">/ ATS checker</span>
          </Link>
          <nav className="flex items-center gap-4">
            {!authed && <Link to="/login" className="label hover:text-fg transition-colors">Sign in</Link>}
            <ThemeToggle />
            <Link to={authed ? "/cv" : "/register"} className="btn-primary text-[11px] px-4 py-2">
              {authed ? "Open app" : "Start free"}
            </Link>
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-5 py-12">
        <div className="label text-accent mb-3">Free ATS resume checker</div>
        <h1 className="font-display font-extrabold text-[clamp(1.8rem,4vw,2.6rem)] leading-tight">
          Is your CV getting past the robots?
        </h1>
        <p className="mt-3 text-muted text-[15px] max-w-xl leading-relaxed">
          Upload your CV (PDF, Word, or text) and get an instant ATS score with a category
          breakdown — no account needed. 2 free checks per day.
        </p>

        <form onSubmit={submit} className="panel p-6 mt-8 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <div className="label mb-2">Upload CV</div>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(e) => setFile(e.target.files[0] || null)}
                className="block w-full text-[13px] text-muted file:btn-ghost file:mr-3 file:px-4 file:py-2 file:text-[11px] file:border-line"
              />
              {file && (
                <button type="button" className="label text-accent mt-2"
                  onClick={() => { setFile(null); fileRef.current.value = ""; }}>
                  ✕ remove file, paste text instead
                </button>
              )}
            </div>
            <div>
              <div className="label mb-2">…or paste your CV text</div>
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                disabled={!!file}
                rows={4}
                placeholder="Paste the full text of your CV"
                className="w-full bg-ink border border-line p-3 text-[13px] disabled:opacity-40"
              />
            </div>
          </div>
          <div>
            <div className="label mb-2">Job description <span className="text-muted">(optional — unlocks the tailoring score)</span></div>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              rows={3}
              placeholder="Paste the job posting to score keyword match against it"
              className="w-full bg-ink border border-line p-3 text-[13px]"
            />
          </div>
          {error && <div className="text-[13px]" style={{ color: "#f85149" }}>{error}</div>}
          <div className="flex items-center gap-4">
            <button type="submit" disabled={!canSubmit} className="btn-primary px-6 py-3 text-[13px] disabled:opacity-50">
              {busy ? "Analysing…" : "Check my CV →"}
            </button>
            {result && result.checks_left !== null && (
              <span className="label">{result.checks_left} free check{result.checks_left === 1 ? "" : "s"} left today</span>
            )}
          </div>
        </form>

        {result && <Report result={result} authed={authed} />}
      </main>
    </div>
  );
}

function Report({ result, authed }) {
  const { ats_score, parse_rate, categories, issues, detailed } = result;
  const dash = 264;
  return (
    <div className="mt-8 space-y-4">
      {/* score + parse rate */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="panel p-6 flex items-center gap-5">
          <div className="relative w-24 h-24 shrink-0">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="42" fill="none" stroke="#2a2a2e" strokeWidth="8" />
              <circle cx="50" cy="50" r="42" fill="none" stroke={scoreColor(ats_score)} strokeWidth="8"
                strokeDasharray={dash} strokeDashoffset={dash * (1 - ats_score / 100)} />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center font-display font-extrabold text-2xl"
              style={{ color: scoreColor(ats_score) }}>{ats_score}</div>
          </div>
          <div>
            <div className="label">Your ATS score</div>
            <div className="font-mono text-sm text-fg mt-1">
              {ats_score >= 80 ? "Strong — ready to send" : ats_score >= 60 ? "Decent — fixable issues" : "At risk of being filtered"}
            </div>
            <div className="label mt-2">{issues.length} issue{issues.length === 1 ? "" : "s"} found</div>
          </div>
        </div>
        <div className="panel p-6">
          <div className="label mb-2">ATS parse rate</div>
          <div className="h-2 bg-line2 mb-3">
            <div className="h-2" style={{ width: `${parse_rate}%`, background: scoreColor(parse_rate) }} />
          </div>
          <p className="text-[13px] text-muted leading-relaxed">
            We estimate an ATS reads <span className="text-fg font-mono">{parse_rate}%</span> of your
            resume's structure correctly — contact info, section headers, dates, and bullets.
          </p>
        </div>
      </div>

      {/* category breakdown */}
      <div className="panel p-6">
        <div className="label mb-4">Category breakdown</div>
        <div className="grid sm:grid-cols-2 gap-x-8 gap-y-3">
          {Object.entries(CATEGORY_LABELS).map(([key, label]) => {
            const v = categories[key];
            return (
              <div key={key} className="flex items-center gap-3">
                <span className="label w-32 shrink-0">{label}</span>
                <div className="h-1.5 bg-line2 flex-1">
                  {v != null && <div className="h-1.5" style={{ width: `${v}%`, background: scoreColor(v) }} />}
                </div>
                <span className="font-mono text-[12px] w-9 text-right">{v != null ? `${v}%` : "—"}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* issues */}
      <div className="panel p-6">
        <div className="label mb-4">Issues found</div>
        <div className="space-y-4">
          {issues.map((it, i) => (
            <div key={i} className="border-b border-line pb-4 last:border-0 last:pb-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono text-[10px] px-1.5 py-0.5 border"
                  style={{ color: SEVERITY_COLOR[it.severity] || "#d29922", borderColor: SEVERITY_COLOR[it.severity] || "#d29922" }}>
                  {(it.severity || "medium").toUpperCase()}
                </span>
                <span className="label">{CATEGORY_LABELS[it.category] || it.category}</span>
                <span className="text-[14px] font-semibold">{it.title}</span>
              </div>
              {detailed ? (
                <p className="text-[13.5px] text-muted leading-relaxed mt-2">{it.fix}</p>
              ) : (
                <p className="text-[13px] text-muted mt-2 select-none blur-[3px]" aria-hidden="true">
                  Upgrade to see exactly how to fix this issue, with concrete wording suggestions.
                </p>
              )}
            </div>
          ))}
          {issues.length === 0 && <p className="text-[13.5px] text-muted">No issues found — your CV looks solid.</p>}
        </div>

        {!detailed && issues.length > 0 && (
          <div className="mt-6 border border-accent/40 p-5 text-center" style={{ boxShadow: "0 0 40px rgba(255,92,53,0.08)" }}>
            <div className="font-display font-bold text-[16px]">Unlock the full report</div>
            <p className="text-[13px] text-muted mt-1 max-w-md mx-auto">
              Paid plans get step-by-step fixes for every issue, unlimited checks, and AI-tailored
              CVs that fix these problems for you.
            </p>
            <Link to={authed ? "/billing" : "/register"} className="btn-primary inline-block mt-4 px-6 py-2.5 text-[12px]">
              {authed ? "Upgrade →" : "Start free →"}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
