import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Banner, Spinner } from "../components/ui";

const TIME_FILTERS = [
  ["any", "Any time"], ["day", "Past 24h"], ["week", "Past week"], ["month", "Past month"],
];
const EXPERIENCE_LEVELS = [
  ["", "Any level"], ["entry", "Entry"], ["mid_senior", "Mid-Senior"], ["senior", "Senior"], ["director", "Director"],
];

// Job discovery via LinkedIn's public listing pages. Off by default server-side
// (see docs/LEGAL_NOTES.md) — this page shows a plain banner if disabled.
export default function JobSearch() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [loc, setLoc] = useState("");
  const [timeFilter, setTimeFilter] = useState("week");
  const [experience, setExperience] = useState("");
  const [jobs, setJobs] = useState(null);
  const [remaining, setRemaining] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [disabled, setDisabled] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailBusy, setDetailBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const p = await api.linkedinGetPreferences();
        if (p.keywords?.length) setQ(p.keywords[0]);
        if (p.location) setLoc(p.location);
        if (p.time_filter) setTimeFilter(p.time_filter);
        if (p.experience_level) setExperience(p.experience_level);
      } catch (e) {
        if (e.status === 404) setDisabled(true);
      }
    })();
  }, []);

  const run = async () => {
    if (q.trim().length < 2) return;
    setErr(""); setBusy(true); setExpandedId(null); setDetail(null);
    try {
      const r = await api.linkedinSearch({ q: q.trim(), location: loc.trim(), timeFilter, experience });
      setJobs(r.jobs);
      setRemaining(r.searches_remaining_today);
    } catch (e) {
      if (e.status === 404) setDisabled(true);
      else setErr(e.message);
    } finally { setBusy(false); }
  };

  const toggleExpand = async (job) => {
    if (expandedId === job.job_id) { setExpandedId(null); setDetail(null); return; }
    setExpandedId(job.job_id); setDetail(null); setDetailBusy(true);
    try { setDetail(await api.linkedinJobDetail(job.job_id)); }
    catch (e) { setErr(e.message); }
    finally { setDetailBusy(false); }
  };

  const toggleSave = async (job) => {
    const next = job.saved ? "unsave" : "save";
    setJobs((cur) => cur.map((j) => (j.job_id === job.job_id ? { ...j, saved: !j.saved } : j)));  // optimistic
    try { await api.linkedinJobAction(job.job_id, next); }
    catch (e) { setErr(e.message); }
  };

  const dismiss = async (job) => {
    setJobs((cur) => cur.filter((j) => j.job_id !== job.job_id));  // optimistic
    try { await api.linkedinJobAction(job.job_id, "dismiss"); }
    catch (e) { setErr(e.message); }
  };

  const generateFor = async (job) => {
    let d = detail?.job_id === job.job_id ? detail : null;
    if (!d) {
      try { d = await api.linkedinJobDetail(job.job_id); }
      catch (e) { setErr(e.message); return; }
    }
    nav("/generate", { state: { job_description: d.description, company: job.company, job_title: job.title } });
  };

  if (disabled) {
    return (
      <div className="rise">
        <h1 className="font-display font-extrabold text-3xl mb-1">LinkedIn job discovery</h1>
        <Banner kind="info">
          This feature isn't enabled on this server. Use "Find Jobs" for Adzuna listings, or paste a
          job description directly on the Generate page.
        </Banner>
      </div>
    );
  }

  return (
    <div className="rise">
      <h1 className="font-display font-extrabold text-3xl mb-1">LinkedIn job discovery</h1>
      <p className="label mb-3">Search live listings from LinkedIn's public job pages.</p>
      <Banner kind="info">
        Listings are sourced from a third-party public web source and provided as-is. CVForge is not
        affiliated with LinkedIn. Verify details on the original posting before applying.
      </Banner>

      <div className="grid md:grid-cols-2 gap-2 mt-4">
        <input className="field" value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} placeholder="Role or keywords, e.g. backend engineer" />
        <input className="field" value={loc} onChange={(e) => setLoc(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} placeholder="Location (optional)" />
      </div>
      <div className="flex flex-wrap gap-2 mt-2 items-center">
        <select className="field text-[12px] py-1.5 w-auto" value={timeFilter} onChange={(e) => setTimeFilter(e.target.value)}>
          {TIME_FILTERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select className="field text-[12px] py-1.5 w-auto" value={experience} onChange={(e) => setExperience(e.target.value)}>
          {EXPERIENCE_LEVELS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <button className="btn-primary px-6" disabled={busy || q.trim().length < 2} onClick={run}>
          {busy ? "Searching…" : "Search"}
        </button>
      </div>

      {err && <div className="mt-4"><Banner>{err}</Banner></div>}
      {busy && <div className="mt-4"><Spinner label="Searching LinkedIn" /></div>}

      {jobs && (
        <div className="mt-3 label">
          {jobs.length} jobs found
          {remaining !== null && <> · {remaining} searches left today (free plan)</>}
        </div>
      )}

      {jobs && jobs.length === 0 && !busy && (
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
                  <>
                    <p className="text-[13px] text-muted whitespace-pre-wrap">{detail.description}</p>
                    {Object.keys(detail.criteria || {}).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {Object.entries(detail.criteria).map(([k, v]) => (
                          <span key={k} className="tag border-line2 text-muted">{k}: {v}</span>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
