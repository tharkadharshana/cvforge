import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, downloadFile } from "../lib/api";
import { useCredits } from "../lib/credits";
import { Banner, Spinner, ScoreGauge } from "../components/ui";
import CVView from "../components/CVView";

export function DownloadBar({ id }) {
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const grab = async (doc, fmt) => {
    setErr(""); setBusy(`${doc}-${fmt}`);
    try { await downloadFile(id, doc, fmt); }
    catch (e) { setErr(e.message); }
    finally { setBusy(""); }
  };
  const items = [
    ["cv", "pdf", "CV · PDF"], ["cv", "docx", "CV · DOCX"],
    ["cover", "pdf", "Letter · PDF"], ["cover", "docx", "Letter · DOCX"],
  ];
  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap gap-2 justify-end">
        {items.map(([doc, fmt, label]) => (
          <button key={label} className="btn-ghost text-[11px] px-3 py-2" disabled={busy === `${doc}-${fmt}`} onClick={() => grab(doc, fmt)}>
            {busy === `${doc}-${fmt}` ? "…" : `↓ ${label}`}
          </button>
        ))}
      </div>
      {err && <Banner>{err}</Banner>}
    </div>
  );
}

export function ImproveButton({ applicationId, onImproved }) {
  const { refresh: refreshCredits } = useCredits();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [paywall, setPaywall] = useState(false);

  const run = async () => {
    setErr(""); setPaywall(false); setBusy(true);
    try {
      const r = await api.improveApplication(applicationId);
      onImproved(r);
      refreshCredits();
    } catch (e) {
      if (e.status === 402) setPaywall(true);
      else setErr(e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <button className="btn-ghost text-[11px] px-3 py-2" disabled={busy} onClick={run}>
        {busy ? "Improving…" : "↑ Improve score (1 credit)"}
      </button>
      {paywall && <div className="text-[12px]"><Link to="/billing" className="text-accent">Out of credits — top up →</Link></div>}
      {err && <Banner>{err}</Banner>}
    </div>
  );
}

function Chips({ items, tone }) {
  if (!items?.length) return <span className="font-mono text-[12px] text-muted">none</span>;
  const cls = tone === "good" ? "border-good/40 text-good" : tone === "bad" ? "border-bad/40 text-bad" : "border-line2 text-muted";
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((x, i) => <span key={i} className={`tag ${cls}`}>{x}</span>)}
    </div>
  );
}

export function CritiquePanel({ critique }) {
  if (!critique) return null;
  const target = critique.target_ats_score || 0;
  return (
    <div className="panel p-5 space-y-4">
      <h2 className="label">ATS critique (cross-model)</h2>
      {target > 0 && (
        critique.meets_ats_guarantee ? (
          <Banner kind="ok">Meets your plan's {target}% ATS guarantee (score {critique.ats_score}%).</Banner>
        ) : (
          <Banner kind="error">
            Couldn't reach your plan's {target}% ATS guarantee after {critique.ats_iterations || 1} attempt(s)
            (score {critique.ats_score}%). Add the missing keywords below, then hit "Improve" to try again.
          </Banner>
        )
      )}
      <div>
        <div className="label mb-1.5 text-good">Matched keywords</div>
        <Chips items={critique.keyword_matches} tone="good" />
      </div>
      <div>
        <div className="label mb-1.5 text-bad">Missing keywords</div>
        <Chips items={critique.missing_keywords} tone="bad" />
      </div>
      {critique.human_tone_notes?.length > 0 && (
        <div>
          <div className="label mb-1.5">Tone notes</div>
          <ul className="list-disc ml-5 font-mono text-[12px] text-muted space-y-1">{critique.human_tone_notes.map((x, i) => <li key={i}>{x}</li>)}</ul>
        </div>
      )}
      {critique.suggestions?.length > 0 && (
        <div>
          <div className="label mb-1.5">Suggestions</div>
          <ul className="list-disc ml-5 font-mono text-[12px] text-muted space-y-1">{critique.suggestions.map((x, i) => <li key={i}>{x}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

export default function ApplicationDetail() {
  const { id } = useParams();
  const [app, setApp] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setApp(await api.getApplication(id)); }
      catch (e) { setErr(e.message); }
      finally { setLoading(false); }
    })();
  }, [id]);

  if (loading) return <Spinner label="Loading application" />;
  if (err) return <Banner>{err}</Banner>;
  if (!app) return null;

  const onImproved = (r) => {
    setApp({ ...app, tailored_cv: r.tailored_cv, cover_letter: r.cover_letter,
      ats_score: r.critique?.ats_score || 0, critique: r.critique });
  };

  return (
    <div className="rise space-y-6">
      <Link to="/applications" className="label text-accent">← History</Link>
      <div className="flex items-center justify-between gap-4 panel p-5 flex-wrap">
        <div className="flex items-center gap-5">
          <ScoreGauge score={app.ats_score || 0} />
          <div>
            <div className="font-display font-bold text-xl">{app.job_title || "Untitled role"}</div>
            <div className="font-mono text-[12px] text-muted">{app.company || "—"}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <ImproveButton applicationId={app.id} onImproved={onImproved} />
          <DownloadBar id={app.id} />
        </div>
      </div>

      <CritiquePanel critique={app.critique} />

      <div>
        <h2 className="label mb-2">Tailored CV</h2>
        <div className="panel p-7"><CVView cv={app.tailored_cv} /></div>
      </div>

      <div>
        <h2 className="label mb-2">Cover letter</h2>
        <div className="panel p-7 font-read text-[15px] leading-relaxed whitespace-pre-wrap">{app.cover_letter}</div>
      </div>
    </div>
  );
}
