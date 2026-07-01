import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, downloadFile } from "../lib/api";
import { useCredits } from "../lib/credits";
import { Banner, Spinner, ScoreGauge } from "../components/ui";
import CVEditor from "../components/CVEditor";
import TemplatePicker from "../components/TemplatePicker";
import { renderTemplate, TEMPLATES } from "../templates/registry";

export function DownloadBar({ id, onPrint, designer }) {
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const grab = async (doc, fmt) => {
    setErr(""); setBusy(`${doc}-${fmt}`);
    try { await downloadFile(id, doc, fmt); }
    catch (e) { setErr(e.message); }
    finally { setBusy(""); }
  };
  const items = [
    ["cv", "pdf", "ATS CV · PDF"], ["cv", "docx", "ATS CV · DOCX"],
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
        {onPrint && (
          <button className="btn-ghost text-[11px] px-3 py-2" onClick={onPrint}>
            🖨 {designer ? "Print designer PDF" : "Print PDF"}
          </button>
        )}
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

export function ReevaluateButton({ applicationId, free, onDone }) {
  const { refresh: refreshCredits } = useCredits();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [paywall, setPaywall] = useState(false);

  const run = async () => {
    setErr(""); setPaywall(false); setBusy(true);
    try {
      const app = await api.reevaluateApplication(applicationId);
      onDone(app);
      refreshCredits();
    } catch (e) {
      if (e.status === 402) setPaywall(true);
      else setErr(e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <button className="btn-primary text-[12px] px-3 py-2" disabled={busy} onClick={run}>
        {busy ? "Scoring…" : free ? "Re-evaluate ATS (free)" : "Re-evaluate ATS (1 credit)"}
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

  // manual-edit state
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(null);        // working copy of tailored_cv while editing
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState("");

  // template state (mirrors app.template_id; changes persist via PATCH, no credit)
  const [templateId, setTemplateId] = useState("ats_classic");
  const [showPicker, setShowPicker] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const a = await api.getApplication(id);
        setApp(a);
        setTemplateId(a.template_id || "ats_classic");
      }
      catch (e) { setErr(e.message); }
      finally { setLoading(false); }
    })();
  }, [id]);

  if (loading) return <Spinner label="Loading application" />;
  if (err) return <Banner>{err}</Banner>;
  if (!app) return null;

  const stale = !!app.ats_stale;
  const tpl = TEMPLATES[templateId] || TEMPLATES.ats_classic;

  const selectTemplate = async (tid) => {
    setTemplateId(tid);                    // optimistic — pure re-render, free
    try { await api.patchApplication(app.id, { template_id: tid }); }
    catch { /* keep the local selection; persistence can retry on next change */ }
  };

  const printCV = () => window.print();

  const onImproved = (r) => {
    setApp({ ...app, tailored_cv: r.tailored_cv, cover_letter: r.cover_letter,
      ats_score: r.critique?.ats_score || 0, critique: r.critique, ats_stale: false });
  };

  const startEdit = () => { setDraft(JSON.parse(JSON.stringify(app.tailored_cv))); setEditing(true); setSaveErr(""); };
  const cancelEdit = () => { setEditing(false); setDraft(null); };
  const saveEdit = async () => {
    setSaveErr(""); setSaving(true);
    try {
      const updated = await api.patchApplication(app.id, { tailored_cv: draft });
      setApp(updated);            // server echoes ats_stale: true
      setEditing(false); setDraft(null);
    } catch (e) { setSaveErr(e.message); }
    finally { setSaving(false); }
  };

  return (
    <div className="rise space-y-6">
      <Link to="/applications" className="label text-accent">← History</Link>
      <div className="flex items-center justify-between gap-4 panel p-5 flex-wrap">
        <div className="flex items-center gap-5">
          {stale ? (
            <div className="w-[64px] h-[64px] rounded-full border border-line2 flex items-center justify-center text-muted font-mono text-[10px] text-center leading-tight">ATS<br/>stale</div>
          ) : (
            <ScoreGauge score={app.ats_score || 0} />
          )}
          <div>
            <div className="font-display font-bold text-xl">{app.job_title || "Untitled role"}</div>
            <div className="font-mono text-[12px] text-muted">{app.company || "—"}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {!editing && (
            stale
              ? <ReevaluateButton applicationId={app.id} free={true} onDone={setApp} />
              : <ImproveButton applicationId={app.id} onImproved={onImproved} />
          )}
          {!editing && <button className="btn-ghost text-[11px] px-3 py-2" onClick={() => setShowPicker((v) => !v)}>🎨 Template</button>}
          {!editing && <button className="btn-ghost text-[11px] px-3 py-2" onClick={startEdit}>✎ Edit CV</button>}
          <DownloadBar id={app.id} onPrint={printCV} designer={!tpl.ats_safe} />
        </div>
      </div>

      {!editing && showPicker && (
        <div className="panel p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="label">Template</h2>
            <span className="font-mono text-[11px] text-muted">Switching is free — the ATS score always reflects the ATS-safe file.</span>
          </div>
          <TemplatePicker value={templateId} onSelect={selectTemplate} />
          {!tpl.ats_safe && (
            <Banner kind="warn">
              Designer templates look great for humans but may parse poorly in some ATS.
              Your ATS score and the "Download ATS" files always use the safe layout.
            </Banner>
          )}
        </div>
      )}

      {stale && !editing && (
        <Banner kind="error">
          Since you edited this CV manually, the ATS score isn't available.
          Re-evaluate to score the current version.
        </Banner>
      )}

      {!editing && !stale && <CritiquePanel critique={app.critique} />}

      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="label">Tailored CV</h2>
          {editing && (
            <div className="flex gap-2">
              <button className="btn-ghost text-[11px] px-3 py-1.5" disabled={saving} onClick={cancelEdit}>Cancel</button>
              <button className="btn-primary text-[11px] px-3 py-1.5" disabled={saving} onClick={saveEdit}>{saving ? "Saving…" : "Save edits"}</button>
            </div>
          )}
        </div>
        {editing && (
          <Banner>Editing manually disables the ATS score. After saving, re-evaluate to score the new version.</Banner>
        )}
        {saveErr && <Banner>{saveErr}</Banner>}
        {editing
          ? <div className="mt-3"><CVEditor cv={draft} onChange={setDraft} /></div>
          : (
            <div className="panel p-4 overflow-x-auto">
              {/* live preview of the selected template, scaled down to fit */}
              <div style={{ transform: "scale(0.62)", transformOrigin: "top left", width: "210mm" }}>
                {renderTemplate(templateId, app.tailored_cv)}
              </div>
            </div>
          )}
      </div>

      {!editing && (
        <div>
          <h2 className="label mb-2">Cover letter</h2>
          <div className="panel p-7 font-read text-[15px] leading-relaxed whitespace-pre-wrap">{app.cover_letter}</div>
        </div>
      )}

      {/* Off-screen full-size render used only by print-to-PDF (see .cv-print-root in index.css) */}
      <div className="cv-print-root">{renderTemplate(templateId, app.tailored_cv)}</div>
    </div>
  );
}
