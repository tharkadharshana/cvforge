import { useState } from "react";
import { useNavigate, Navigate, Link } from "react-router-dom";
import { api } from "../lib/api";
import { useCVStatus } from "../lib/cvstatus";
import { useCredits } from "../lib/credits";
import { Banner, Spinner, ScoreGauge } from "../components/ui";
import CVView from "../components/CVView";
import { DownloadBar, CritiquePanel } from "./ApplicationDetail";

export default function Generate() {
  const nav = useNavigate();
  const { status, loading: stLoading } = useCVStatus();
  const { refresh: refreshCredits } = useCredits();
  const [url, setUrl] = useState("");
  const [jd, setJd] = useState("");
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [fetching, setFetching] = useState(false);
  const [fetchErr, setFetchErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [paywall, setPaywall] = useState(false);
  const [result, setResult] = useState(null);

  if (!stLoading && status && !status.has_base_cv) return <Navigate to="/onboarding" replace />;

  const fetchUrl = async () => {
    setFetchErr(""); setFetching(true);
    try {
      const { title: t, text } = await api.fetchJobUrl(url);
      setJd(text);
      if (t && !title) setTitle(t);
    } catch (e) { setFetchErr(e.message); }
    finally { setFetching(false); }
  };

  const run = async () => {
    setErr(""); setPaywall(false); setResult(null); setBusy(true);
    try {
      const r = await api.generate({ job_description: jd, company, job_title: title });
      setResult(r);
      refreshCredits();
    } catch (e) {
      if (e.status === 402) setPaywall(true);
      else setErr(e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="rise">
      <h1 className="font-display font-extrabold text-3xl mb-1">Generate</h1>
      <p className="label mb-5">Paste a job link or the description. Get a tailored CV + cover letter + ATS score.</p>

      {/* URL paste */}
      <div className="label mb-1">Job posting URL</div>
      <div className="flex gap-2">
        <input className="field flex-1" value={url} onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && url && fetchUrl()}
          placeholder="https://… (LinkedIn, job board, company careers page)" />
        <button className="btn-ghost px-4" disabled={fetching || !url} onClick={fetchUrl}>
          {fetching ? "Fetching…" : "Fetch"}
        </button>
      </div>
      {fetchErr && <div className="mt-2"><Banner kind="info">{fetchErr}</Banner></div>}
      <div className="label my-3 text-center text-muted">— or paste the text below —</div>

      <div className="grid md:grid-cols-2 gap-3 mb-3">
        <div><div className="label mb-1">Company (optional)</div>
          <input className="field" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Acme Inc." /></div>
        <div><div className="label mb-1">Role title (optional)</div>
          <input className="field" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Backend Engineer" /></div>
      </div>

      <div className="label mb-1">Job description</div>
      <textarea className="field min-h-[220px] resize-y leading-relaxed" value={jd} onChange={(e) => setJd(e.target.value)}
        placeholder="Paste the full job description here…" />

      <div className="flex items-center justify-between mt-4 gap-3 flex-wrap">
        <div>{busy && <Spinner label="Tailoring CV · writing letter · scoring ATS" />}</div>
        <button className="btn-primary" disabled={busy || jd.trim().length < 20} onClick={run}>
          {busy ? "Forging…" : "Forge CV + cover letter (1 credit)"}
        </button>
      </div>

      {paywall && (
        <div className="mt-5 panel p-6 text-center border-accent/40">
          <h3 className="font-display font-bold text-xl">You're out of credits</h3>
          <p className="text-muted text-[14px] mt-1 mb-4">Top up to keep forging tailored CVs.</p>
          <Link to="/billing" className="btn-primary px-6 py-2.5 inline-block">View plans →</Link>
        </div>
      )}
      {err && <div className="mt-4"><Banner>{err}</Banner></div>}

      {result && (
        <div className="mt-8 space-y-6 rise">
          <div className="flex items-center justify-between gap-4 panel p-5 flex-wrap">
            <ScoreGauge score={result.critique?.ats_score || 0} />
            <DownloadBar id={result.application_id} />
          </div>
          <CritiquePanel critique={result.critique} />
          <div>
            <h2 className="label mb-2">Tailored CV</h2>
            <div className="panel p-7"><CVView cv={result.tailored_cv} /></div>
          </div>
          <div>
            <h2 className="label mb-2">Cover letter</h2>
            <div className="panel p-7 font-read text-[15px] leading-relaxed whitespace-pre-wrap">{result.cover_letter}</div>
          </div>
          <button className="btn-ghost" onClick={() => nav(`/applications/${result.application_id}`)}>
            Open in history →
          </button>
        </div>
      )}
    </div>
  );
}
