import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Banner, Spinner } from "../components/ui";

// In-app job feed. Search a legal aggregator (Adzuna) and, for any listing, jump
// straight into Generate with the description prefilled — no manual copy-paste.
// Users still apply on the original posting (the "Apply ↗" link).
export default function Jobs() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [loc, setLoc] = useState("");
  const [page, setPage] = useState(1);
  const [results, setResults] = useState(null);
  const [enabled, setEnabled] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const run = async (p = 1) => {
    if (q.trim().length < 2) return;
    setErr(""); setBusy(true);
    try {
      const r = await api.searchJobs(q.trim(), loc.trim(), p);
      setResults(r.results); setEnabled(r.enabled); setPage(p);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const generateFor = (job) => {
    // hand the listing to Generate via router state; Generate prefills the form
    nav("/generate", { state: {
      job_description: job.description,
      company: job.company,
      job_title: job.title,
    }});
  };

  return (
    <div className="rise">
      <h1 className="font-display font-extrabold text-3xl mb-1">Find jobs</h1>
      <p className="label mb-5">Search live listings, then forge a tailored CV against one in a click.</p>

      <div className="flex flex-col sm:flex-row gap-2">
        <input className="field flex-1" value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(1)} placeholder="Role or keywords, e.g. backend engineer" />
        <input className="field sm:w-56" value={loc} onChange={(e) => setLoc(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(1)} placeholder="Location (optional)" />
        <button className="btn-primary px-6" disabled={busy || q.trim().length < 2} onClick={() => run(1)}>
          {busy ? "Searching…" : "Search"}
        </button>
      </div>

      {!enabled && (
        <div className="mt-4"><Banner kind="info">
          Job search isn't configured on this server yet (needs Adzuna API keys). You can still
          paste a job description on the Generate page.
        </Banner></div>
      )}
      {err && <div className="mt-4"><Banner>{err}</Banner></div>}
      {busy && <div className="mt-4"><Spinner label="Searching listings" /></div>}

      {results && results.length === 0 && !busy && enabled && (
        <div className="mt-6 label text-muted">No listings matched. Try broader keywords.</div>
      )}

      <div className="mt-5 space-y-3">
        {(results || []).map((job) => (
          <div key={job.id} className="panel p-4">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="font-display font-semibold text-[15px]">{job.title}</div>
                <div className="font-mono text-[12px] text-muted">
                  {[job.company, job.location].filter(Boolean).join(" · ") || "—"}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                {job.url && (
                  <a href={job.url} target="_blank" rel="noreferrer" className="btn-ghost text-[11px] px-3 py-2">Apply ↗</a>
                )}
                <button className="btn-primary text-[11px] px-3 py-2" onClick={() => generateFor(job)}>Forge CV →</button>
              </div>
            </div>
            {job.description && (
              <p className="mt-2 text-[13px] text-muted line-clamp-3">{job.description}</p>
            )}
          </div>
        ))}
      </div>

      {results && results.length > 0 && (
        <div className="mt-5 flex items-center justify-between">
          <button className="btn-ghost text-[11px] px-3 py-2" disabled={busy || page <= 1} onClick={() => run(page - 1)}>← Prev</button>
          <span className="label">Page {page}</span>
          <button className="btn-ghost text-[11px] px-3 py-2" disabled={busy || results.length === 0} onClick={() => run(page + 1)}>Next →</button>
        </div>
      )}
    </div>
  );
}
