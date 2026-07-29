import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Banner, Spinner } from "../components/ui";

// Combined job discovery: LinkedIn's public listing pages + Gemini's live web
// search, merged into one result list ordered by most-recently-posted. Each
// source is independently optional (LinkedIn off by default server-side, see
// docs/LEGAL_NOTES.md; Gemini auto-enabled when a key is configured) -- if one
// is unavailable the other's results still show.

function postedAtMs(job) {
  const t = job.posted_at ? Date.parse(job.posted_at) : NaN;
  return Number.isNaN(t) ? -Infinity : t;  // undated listings sort last
}

export default function JobSearch() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [loc, setLoc] = useState("");
  const [jobs, setJobs] = useState(null);
  const [linkedinRemaining, setLinkedinRemaining] = useState(null);
  const [geminiRemaining, setGeminiRemaining] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [expandedKey, setExpandedKey] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const key = (job) => `${job.source}:${job.job_id}`;

  const run = async () => {
    if (q.trim().length < 2) return;
    setErr(""); setBusy(true); setExpandedKey(null); setDetail(null);

    const [li, gm] = await Promise.allSettled([
      api.linkedinSearch({ q: q.trim(), location: loc.trim() }),
      api.geminiSearch({ q: q.trim(), location: loc.trim() }),
    ]);

    const merged = [];
    if (li.status === "fulfilled") {
      merged.push(...li.value.jobs.map((j) => ({ ...j, source: "linkedin" })));
      setLinkedinRemaining(li.value.searches_remaining_today);
    } else {
      setLinkedinRemaining(null);
    }
    if (gm.status === "fulfilled") {
      merged.push(...gm.value.jobs.map((j) => ({ ...j, source: "gemini" })));
      setGeminiRemaining(gm.value.enabled ? gm.value.searches_remaining_today : null);
    } else {
      setGeminiRemaining(null);
    }

    merged.sort((a, b) => postedAtMs(b) - postedAtMs(a));
    setJobs(merged);

    // both sources failed outright (not just disabled/empty) -- surface the error
    if (li.status === "rejected" && gm.status === "rejected") {
      setErr(li.reason?.message || gm.reason?.message || "Job search failed.");
    }
    setBusy(false);
  };

  const detailApi = (source) => (source === "linkedin" ? api.linkedinJobDetail : api.geminiJobDetail);
  const actionApi = (source) => (source === "linkedin" ? api.linkedinJobAction : api.geminiJobAction);

  const toggleExpand = async (job) => {
    const k = key(job);
    if (expandedKey === k) { setExpandedKey(null); setDetail(null); return; }
    setExpandedKey(k); setDetail(null); setDetailBusy(true);
    try { setDetail({ ...(await detailApi(job.source)(job.job_id)), source: job.source }); }
    catch (e) { setErr(e.message); }
    finally { setDetailBusy(false); }
  };

  const toggleSave = async (job) => {
    const next = job.saved ? "unsave" : "save";
    setJobs((cur) => cur.map((j) => (key(j) === key(job) ? { ...j, saved: !j.saved } : j)));  // optimistic
    try { await actionApi(job.source)(job.job_id, next); }
    catch (e) { setErr(e.message); }
  };

  const dismiss = async (job) => {
    setJobs((cur) => cur.filter((j) => key(j) !== key(job)));  // optimistic
    try { await actionApi(job.source)(job.job_id, "dismiss"); }
    catch (e) { setErr(e.message); }
  };

  const generateFor = async (job) => {
    let d = detail && detail.job_id === job.job_id && detail.source === job.source ? detail : null;
    if (!d) {
      try { d = await detailApi(job.source)(job.job_id); }
      catch (e) { setErr(e.message); return; }
    }
    nav("/generate", { state: { job_description: d.description, company: job.company, job_title: job.title } });
  };

  return (
    <div className="rise">
      <h1 className="font-display font-extrabold text-3xl mb-1">Job search</h1>
      <p className="label mb-3">
        Search LinkedIn's public listings and live web results together, then forge a tailored CV in a click.
      </p>
      <Banner kind="info">
        Listings are sourced from third-party sites and provided as-is. CVForge is not affiliated with
        LinkedIn or any listed employer. Verify details on the original posting before applying.
      </Banner>

      <div className="flex flex-col sm:flex-row gap-2 mt-4">
        <input className="field flex-1" value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} placeholder="Role or keywords, e.g. backend engineer" />
        <input className="field sm:w-56" value={loc} onChange={(e) => setLoc(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} placeholder="Location (optional)" />
        <button className="btn-primary px-6" disabled={busy || q.trim().length < 2} onClick={run}>
          {busy ? "Searching…" : "Search"}
        </button>
      </div>

      {err && <div className="mt-4"><Banner>{err}</Banner></div>}
      {busy && <div className="mt-4"><Spinner label="Searching listings" /></div>}

      {jobs && (
        <div className="mt-3 label">
          {jobs.length} jobs found
          {linkedinRemaining !== null && <> · LinkedIn: {linkedinRemaining} left today</>}
          {geminiRemaining !== null && <> · AI search: {geminiRemaining} left today</>}
        </div>
      )}

      {jobs && jobs.length === 0 && !busy && (
        <div className="mt-6 label text-muted">No listings matched. Try broader keywords.</div>
      )}

      <div className="mt-3 space-y-3">
        {(jobs || []).map((job) => (
          <div key={key(job)} className="panel p-4">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="font-display font-semibold text-[15px]">{job.title}</div>
                <div className="font-mono text-[12px] text-muted">
                  {[job.company, job.location].filter(Boolean).join(" · ") || "—"}
                  {" · "}<span className="tag border-line2">{job.source === "linkedin" ? "LinkedIn" : "AI search"}</span>
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button className="btn-ghost text-[11px] px-3 py-2" onClick={() => toggleExpand(job)}>
                  {expandedKey === key(job) ? "Hide" : "View"}
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
            {expandedKey === key(job) && (
              <div className="mt-3 pt-3 border-t border-line">
                {detailBusy && <Spinner label="Loading description" />}
                {detail && detail.job_id === job.job_id && detail.source === job.source && (
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
