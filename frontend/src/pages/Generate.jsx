import { useState } from "react";
import { useNavigate, Navigate, Link } from "react-router-dom";
import { api } from "../lib/api";
import { useCVStatus } from "../lib/cvstatus";
import { useCredits } from "../lib/credits";
import { Banner, Spinner, ScoreGauge } from "../components/ui";
import TemplatePicker from "../components/TemplatePicker";
import { renderTemplate, TEMPLATES } from "../templates/registry";
import { DownloadBar, CritiquePanel, ImproveButton } from "./ApplicationDetail";

const STEPS = [
  { key: "tailor", label: "Tailoring CV", call: (id) => api.tailor(id) },
  { key: "cover", label: "Writing cover letter", call: (id) => api.cover(id) },
  { key: "critique", label: "Scoring ATS", call: (id) => api.critique(id) },
];

function Stepper({ jobStatus, steps, onRetry, busy }) {
  return (
    <div className="flex flex-col gap-2">
      {steps.map((s) => {
        const st = jobStatus[s.key] || "idle";
        const icon = st === "done" ? "✓" : st === "running" ? "⟳" : st === "error" ? "✗" : "▢";
        const tone = st === "done" ? "text-good" : st === "error" ? "text-bad" : st === "running" ? "text-accent" : "text-muted";
        return (
          <div key={s.key} className="flex items-center gap-2 font-mono text-[13px]">
            <span className={tone}>{icon}</span>
            <span className={tone}>{s.label}</span>
            {st === "error" && (
              <button className="btn-ghost text-[11px] px-2 py-1" disabled={busy} onClick={() => onRetry(s.key)}>
                Retry this step
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

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

  const [jobId, setJobId] = useState(null);
  const [stepStatus, setStepStatus] = useState({});
  const [stepError, setStepError] = useState({});
  const [tailoredCv, setTailoredCv] = useState(null);
  const [coverLetter, setCoverLetter] = useState(null);
  const [critique, setCritique] = useState(null);
  const [autoTuning, setAutoTuning] = useState(false);
  const [templateId, setTemplateId] = useState("ats_classic");

  const MAX_AUTO_RETRIES = 2; // free retries to honor the plan's ATS guarantee

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

  // Free, bounded auto-retries: if the score is below the plan's guarantee,
  // re-run the improve pass (no credit charged for these) keeping the best result.
  const autoTune = async (id, crit) => {
    let best = crit;
    if (!best || best.meets_ats_guarantee !== false) return best;
    setAutoTuning(true);
    try {
      for (let i = 0; i < MAX_AUTO_RETRIES; i++) {
        const r = await api.improveApplication(id, true);
        setTailoredCv(r.tailored_cv);
        setCoverLetter(r.cover_letter);
        setCritique(r.critique);
        best = r.critique;
        if (best?.meets_ats_guarantee) break;
      }
    } catch {
      // auto-tune is best-effort; keep whatever score we already have
    } finally {
      setAutoTuning(false);
    }
    return best;
  };

  const runFrom = async (id, fromIndex) => {
    let lastCrit = critique;
    for (let i = fromIndex; i < STEPS.length; i++) {
      const step = STEPS[i];
      setStepStatus((s) => ({ ...s, [step.key]: "running" }));
      setStepError((e) => ({ ...e, [step.key]: "" }));
      try {
        const r = await step.call(id);
        if (step.key === "tailor") setTailoredCv(r.tailored_cv);
        if (step.key === "cover") setCoverLetter(r.cover_letter);
        if (step.key === "critique") { setCritique(r.critique); lastCrit = r.critique; }
        setStepStatus((s) => ({ ...s, [step.key]: "done" }));
      } catch (e) {
        setStepStatus((s) => ({ ...s, [step.key]: "error" }));
        setStepError((er) => ({ ...er, [step.key]: e.message }));
        setBusy(false);
        return;
      }
    }
    await autoTune(id, lastCrit);
    setBusy(false);
    refreshCredits();
  };

  const run = async () => {
    setErr(""); setPaywall(false); setBusy(true);
    setJobId(null); setTailoredCv(null); setCoverLetter(null); setCritique(null);
    setStepStatus({}); setStepError({});
    let id;
    try {
      const r = await api.startGeneration({ job_description: jd, company, job_title: title, template_id: templateId });
      id = r.job_id;
      setJobId(id);
    } catch (e) {
      setBusy(false);
      if (e.status === 402) setPaywall(true);
      else setErr(e.message);
      return;
    }
    await runFrom(id, 0);
  };

  const retryStep = async (key) => {
    if (!jobId) return;
    setBusy(true);
    const idx = STEPS.findIndex((s) => s.key === key);
    await runFrom(jobId, idx);
  };

  const result = critique && jobId
    ? { application_id: jobId, tailored_cv: tailoredCv, cover_letter: coverLetter, critique }
    : null;

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

      <div className="label mt-4 mb-2">Template (you can change this any time later)</div>
      <TemplatePicker value={templateId} onSelect={setTemplateId} busy={busy} />

      <div className="flex items-center justify-between mt-4 gap-3 flex-wrap">
        <div>{busy && !jobId && <Spinner label="Starting" />}</div>
        <button className="btn-primary" disabled={busy || jd.trim().length < 20} onClick={run}>
          {busy ? "Forging…" : "Forge CV + cover letter (1 credit)"}
        </button>
      </div>

      {jobId && (
        <div className="mt-5 panel p-5">
          <Stepper jobStatus={stepStatus} steps={STEPS} onRetry={retryStep} busy={busy} />
          {autoTuning && (
            <div className="mt-2"><Spinner label="Boosting ATS score to meet your plan guarantee (free)" /></div>
          )}
          {Object.values(stepError).some(Boolean) && (
            <div className="mt-3"><Banner>{Object.values(stepError).find(Boolean)}</Banner></div>
          )}
        </div>
      )}

      {paywall && (
        <div className="mt-5 panel p-6 text-center border-accent/40">
          <h3 className="font-display font-bold text-xl">You're out of credits</h3>
          <p className="text-muted text-[14px] mt-1 mb-4">Top up to keep forging tailored CVs.</p>
          <Link to="/billing" className="btn-primary px-6 py-2.5 inline-block">View plans →</Link>
        </div>
      )}
      {err && <div className="mt-4"><Banner>{err}</Banner></div>}

      {tailoredCv && (
        <div className="mt-8 space-y-6 rise">
          {critique && (
            <div className="flex items-center justify-between gap-4 panel p-5 flex-wrap">
              <ScoreGauge score={critique?.ats_score || 0} />
              <div className="flex items-center gap-2 flex-wrap justify-end">
                <ImproveButton applicationId={jobId} onImproved={(r) => {
                  setTailoredCv(r.tailored_cv); setCoverLetter(r.cover_letter); setCritique(r.critique);
                }} />
                <DownloadBar id={jobId} onPrint={() => window.print()} designer={!(TEMPLATES[templateId] || TEMPLATES.ats_classic).ats_safe} />
              </div>
            </div>
          )}
          {critique && <CritiquePanel critique={critique} />}
          <div>
            <h2 className="label mb-2">Tailored CV</h2>
            <div className="panel p-4 overflow-x-auto">
              <div style={{ transform: "scale(0.62)", transformOrigin: "top left", width: "210mm" }}>
                {renderTemplate(templateId, tailoredCv)}
              </div>
            </div>
          </div>
          {coverLetter && (
            <div>
              <h2 className="label mb-2">Cover letter</h2>
              <div className="panel p-7 font-read text-[15px] leading-relaxed whitespace-pre-wrap">{coverLetter}</div>
            </div>
          )}
          {result && (
            <button className="btn-ghost" onClick={() => nav(`/applications/${jobId}`)}>
              Open in history →
            </button>
          )}
          <div className="cv-print-root">{renderTemplate(templateId, tailoredCv)}</div>
        </div>
      )}
    </div>
  );
}
