import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Banner, Spinner } from "../components/ui";

// Job discovery via Gemini's Google Search grounding tool — a live web search,
// not a fixed job board. Auto-enabled server-side when GEMINI_API_KEY is set.
export default function JobSearchAI() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [loc, setLoc] = useState("");
  const [jobs, setJobs] = useState(null);
  const [remaining, setRemaining] = useState(null);
  const [enabled, setEnabled] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const run = async () => {
    if (q.trim().length < 2) return;
    setErr(""); setBusy(true); setExpandedId(null); setDetail(null);
    try {
      const r = await api.geminiSearch({ q: q.trim(), location: loc.trim() });
      setJobs(r.jobs);
      setRemaining(r.searches_remaining_today);
      setEnabled(r.enabled);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const toggleExpand = async (job) => {
    if (expandedId === job.job_id) { setExpandedId(null); setDetail(null); return; }
    setExpandedId(job.job_id); setDetail(null); setDetailBusy(true);
    try { setDetail(await api.geminiJobDetail(job.job_id)); }
    catch (e) { setErr(e.message); }
    finally { setDetailBusy(false); }
  };

  const toggleSave = async (job) => {
    const next = job.saved ? "unsave" : "save";
    setJobs((cur) => cur.map((j) => (j.job_id === job.job_id ? { ...j, saved: !j.saved } : j)));  // optimistic
    try { await api.geminiJobAction(job.job_id, next); }
    catch (e) { setErr(e.message); }
  };

  const dismiss = async (job) => {
    setJobs((cur) => cur.filter((j) => j.job_id !== job.job_id));  // optimistic
    try { await api.geminiJobAction(job.job_id, "dismiss"); }
    catch (e) { setErr(e.message); }
  };

  const generateFor = async (job) => {
    let d = detail?.job_id === job.job_id ? detail : null;
    if (!d) {
      try { d = await api.geminiJobDetail(job.job_id); }
      catch (e) { setErr(e.message); return; }
    }
    nav("/generate", { state: { job_description: d.description, company: job.company, job_title: job.title } });
  };

  return (
    <div className="rise">
      <h1 className="font-display font-extrabold text-3xl mb-1">AI job search</h1>
      <p className="label mb-5">Search the live web for current job postings, then forge a tailored CV in a click.</p>

      <div className="flex flex-col sm:flex-row gap-2">
        <input className="field flex-1" value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} placeholder="Role or keywords, e.g. backend engineer" />
        <input className="field sm:w-56" value={loc} onChange={(e) => setLoc(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} placeholder="Location (optional)" />
        <button className="btn-primary px-6" disabled={busy || q.trim().length < 2} onClick={run}>
          {busy ? "Searching…" : "Search"}
        </button>
      </div>

      {!enabled && (
        <div className="mt-4"><Banner kind="info">
          AI job search isn't configured on this server yet (needs a Gemini API key). You can still
          use "Find Jobs" or paste a job description on the Generate page.
        </Banner></div>
      )}
      {err && <div className="mt-4"><Banner>{err}</Banner></div>}
      {busy && <div className="mt-4"><Spinner label="Searching the web" /></div>}

      {jobs && enabled && (
        <div className="mt-3 label">
          {jobs.length} jobs found
          {remaining !== null && <> · {remaining} searches left today (free plan)</>}
        </div>
      )}

      {jobs && jobs.length === 0 && !busy && enabled && (
        <div className="mt-6 label text-muted">No listings matched. Try broader keywords.</div>
      )}

      <div className="mt-3 space-y-3">
        {(jobs || []).map((job) => (
          <div key={job.job_id} className="panel p-4">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="font-display font-semibold text-[15px]">{job.title}</div>
                <div className="font-mono text-[12px] text-muted">
                  {[job.company, job.location].filter(Boolean).join(" · ") || "—"}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button className="btn-ghost text-[11px] px-3 py-2" onClick={() => toggleExpand(job)}>
                  {expandedId === job.job_id ? "Hide" : "View"}
                </button>
                <button className="btn-ghost text-[11px] px-3 py-2" onClick={() => toggleSave(job)}>
                  {job.saved ? "★ Saved" : "☆ Save"}
                </button>
                <button className="btn-ghost text-[11px] px-3 py-2" onClick={() => dismiss(job)}>Dismiss</button>
                {job.url && (
                  <a href={job.url} target="_blank" rel="noreferrer" className="btn-ghost text-[11px] px-3 py-2">Apply ↗</a>
                )}
                <button className="btn-primary text-[11px] px-3 py-2" onClick={() => generateFor(job)}>Forge CV →</button>
              </div>
            </div>
            {expandedId === job.job_id && (
              <div className="mt-3 pt-3 border-t border-line">
                {detailBusy && <Spinner label="Loading description" />}
                {detail && detail.job_id === job.job_id && (
                  <p className="text-[13px] text-muted whitespace-pre-wrap">{detail.description}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
