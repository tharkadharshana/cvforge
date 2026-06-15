import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../lib/api";
import { useCVStatus } from "../lib/cvstatus";
import { useCredits } from "../lib/credits";
import { Banner, Spinner } from "../components/ui";

const splitComma = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
const splitLines = (s) => s.split("\n").map((x) => x.replace(/^[-•]\s*/, "").trim()).filter(Boolean);

const empty = {
  contact: { full_name: "", email: "", phone: "", location: "", linkedin: "", github: "", website: "" },
  summary: "", skills: {}, experience: [], projects: [], education: [],
  certifications: [], awards: [], languages: [],
};

export default function BaseCV() {
  const { status, loading: stLoading, refresh } = useCVStatus();
  const { refresh: refreshCredits } = useCredits();
  const [cv, setCv] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [qual, setQual] = useState("");
  const [qbusy, setQbusy] = useState(false);
  const [paywall, setPaywall] = useState(false);
  const [rev, setRev] = useState(0);

  useEffect(() => {
    (async () => {
      try { setCv({ ...empty, ...(await api.getCV()) }); }
      catch (e) { setErr(e.message); }
      finally { setLoading(false); }
    })();
  }, []);

  if (!stLoading && status && !status.has_base_cv) return <Navigate to="/onboarding" replace />;
  if (loading || !cv) return <Spinner label="Loading CV" />;

  const set = (patch) => setCv({ ...cv, ...patch });
  const setC = (k, v) => setCv({ ...cv, contact: { ...cv.contact, [k]: v } });

  const save = async () => {
    setErr(""); setMsg(""); setBusy(true);
    try { await api.replaceCV(cv); await refresh(); setMsg("Saved."); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const addQual = async () => {
    setErr(""); setMsg(""); setPaywall(false); setQbusy(true);
    try {
      const u = await api.addQualification(qual);
      setCv({ ...empty, ...u }); setRev((r) => r + 1); setQual(""); setMsg("Merged into CV.");
      refreshCredits();
    } catch (e) {
      if (e.status === 402) setPaywall(true);
      else setErr(e.message);
    } finally { setQbusy(false); }
  };

  return (
    <div className="rise space-y-6">
      <div className="flex items-end justify-between gap-3 flex-wrap">
        <div>
          <h1 className="font-display font-extrabold text-3xl">Your base CV</h1>
          <p className="label mt-1">Edit freely. This is the source for every tailored CV.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/onboarding" className="btn-ghost text-[11px] px-3 py-2">Re-import / rebuild</Link>
          <button className="btn-primary" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save CV"}</button>
        </div>
      </div>

      {msg && <Banner kind="ok">{msg}</Banner>}
      {err && <Banner>{err}</Banner>}

      <Card title="Contact">
        <div className="grid sm:grid-cols-2 gap-2">
          {["full_name", "email", "phone", "location", "linkedin", "github", "website"].map((k) => (
            <input key={k} className="field" value={cv.contact[k] || ""} onChange={(e) => setC(k, e.target.value)} placeholder={k.replace("_", " ")} />
          ))}
        </div>
      </Card>

      <Card title="Summary">
        <textarea className="field min-h-[90px]" value={cv.summary} onChange={(e) => set({ summary: e.target.value })} placeholder="Professional summary" />
      </Card>

      <Card title="Skills" action={<AddBtn onClick={() => set({ skills: { ...cv.skills, "New category": [] } })} label="category" />}>
        {Object.keys(cv.skills).length === 0 && <Empty />}
        {Object.entries(cv.skills).map(([cat, items], i) => (
          <div key={`${rev}-${i}`} className="flex flex-col sm:flex-row gap-2 mb-2 items-start">
            <input className="field sm:w-48" value={cat}
              onChange={(e) => { const s = {}; Object.entries(cv.skills).forEach(([k, v]) => { s[k === cat ? e.target.value : k] = v; }); set({ skills: s }); }} placeholder="Category" />
            <CommaInput className="field flex-1" value={items}
              onChange={(arr) => set({ skills: { ...cv.skills, [cat]: arr } })} placeholder="comma, separated, skills" />
            <button onClick={() => { const s = { ...cv.skills }; delete s[cat]; set({ skills: s }); }} className="label text-bad shrink-0 py-2">remove</button>
          </div>
        ))}
      </Card>

      <ListEditor title="Experience" items={cv.experience} onChange={(v) => set({ experience: v })}
        template={{ title: "", company: "", location: "", start: "", end: "", bullets: [] }}
        render={(e, upd) => (
          <>
            <div className="grid sm:grid-cols-2 gap-2">
              <input className="field" value={e.title} onChange={(ev) => upd({ title: ev.target.value })} placeholder="Title" />
              <input className="field" value={e.company} onChange={(ev) => upd({ company: ev.target.value })} placeholder="Company" />
              <input className="field" value={e.location} onChange={(ev) => upd({ location: ev.target.value })} placeholder="Location" />
              <div className="flex gap-2">
                <input className="field" value={e.start} onChange={(ev) => upd({ start: ev.target.value })} placeholder="Start" />
                <input className="field" value={e.end} onChange={(ev) => upd({ end: ev.target.value })} placeholder="End" />
              </div>
            </div>
            <Bullets value={e.bullets} onChange={(b) => upd({ bullets: b })} split={splitLines} />
          </>
        )} />

      <ListEditor title="Projects" items={cv.projects} onChange={(v) => set({ projects: v })}
        template={{ name: "", description: "", tech: [], bullets: [], link: "" }}
        render={(p, upd) => (
          <>
            <div className="grid sm:grid-cols-2 gap-2">
              <input className="field" value={p.name} onChange={(ev) => upd({ name: ev.target.value })} placeholder="Name" />
              <input className="field" value={p.link} onChange={(ev) => upd({ link: ev.target.value })} placeholder="Link" />
            </div>
            <CommaInput key={`tech-${rev}`} className="field mt-2" value={p.tech} onChange={(arr) => upd({ tech: arr })} placeholder="Tech (comma separated)" />
            <input className="field mt-2" value={p.description} onChange={(ev) => upd({ description: ev.target.value })} placeholder="Description" />
            <Bullets value={p.bullets} onChange={(b) => upd({ bullets: b })} split={splitLines} />
          </>
        )} />

      <ListEditor title="Education" items={cv.education} onChange={(v) => set({ education: v })}
        template={{ degree: "", institution: "", location: "", start: "", end: "", details: [] }}
        render={(e, upd) => (
          <div className="grid sm:grid-cols-2 gap-2">
            <input className="field" value={e.degree} onChange={(ev) => upd({ degree: ev.target.value })} placeholder="Degree" />
            <input className="field" value={e.institution} onChange={(ev) => upd({ institution: ev.target.value })} placeholder="Institution" />
            <input className="field" value={e.start} onChange={(ev) => upd({ start: ev.target.value })} placeholder="Start" />
            <input className="field" value={e.end} onChange={(ev) => upd({ end: ev.target.value })} placeholder="End" />
          </div>
        )} />

      <Card title="Certifications">
        <textarea className="field min-h-[70px]" value={(cv.certifications || []).join("\n")}
          onChange={(e) => set({ certifications: splitLines(e.target.value) })} placeholder="One per line" />
      </Card>
      <Card title="Awards">
        <textarea className="field min-h-[60px]" value={(cv.awards || []).join("\n")}
          onChange={(e) => set({ awards: splitLines(e.target.value) })} placeholder="One per line" />
      </Card>
      <Card title="Languages">
        <CommaInput key={`languages-${rev}`} className="field" value={cv.languages}
          onChange={(arr) => set({ languages: arr })} placeholder="comma separated" />
      </Card>

      <Card title="Quick add — dump a new qualification">
        <p className="font-mono text-[11px] text-muted mb-2">Free text. LLM slots it into the right section, then re-save.</p>
        <textarea className="field min-h-[80px]" value={qual} onChange={(e) => setQual(e.target.value)}
          placeholder="e.g. Earned AWS SAA cert March 2026; led migration to Kubernetes." />
        <div className="flex justify-end mt-2">
          <button className="btn-ghost" disabled={qbusy || qual.trim().length < 3} onClick={addQual}>{qbusy ? "Merging…" : "Merge into CV (1 credit)"}</button>
        </div>
        {qbusy && <Spinner label="Merging" />}
        {paywall && <div className="mt-2 text-[12px]"><Link to="/billing" className="text-accent">Out of credits — top up →</Link></div>}
      </Card>

      <div className="flex justify-end pb-6">
        <button className="btn-primary" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save CV"}</button>
      </div>
    </div>
  );
}

function Card({ title, action, children }) {
  return (
    <section className="panel p-5">
      <div className="flex items-center justify-between mb-3"><h2 className="label">{title}</h2>{action}</div>
      {children}
    </section>
  );
}
function ListEditor({ title, items, onChange, template, render }) {
  const add = () => onChange([...items, JSON.parse(JSON.stringify(template))]);
  const remove = (i) => onChange(items.filter((_, j) => j !== i));
  const updAt = (i, patch) => onChange(items.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  return (
    <Card title={title} action={<AddBtn onClick={add} label="entry" />}>
      {items.length === 0 && <Empty />}
      {items.map((it, i) => (
        <div key={i} className="border border-line p-3 mb-2 relative">
          <button onClick={() => remove(i)} className="absolute top-2 right-2 label text-bad">remove</button>
          {render(it, (patch) => updAt(i, patch))}
        </div>
      ))}
    </Card>
  );
}
function CommaInput({ className, value, onChange, placeholder }) {
  const [text, setText] = useState((value || []).join(", "));
  return (
    <input className={className} value={text}
      onChange={(e) => { setText(e.target.value); onChange(splitComma(e.target.value)); }}
      placeholder={placeholder} />
  );
}
function Bullets({ value, onChange, split }) {
  return (
    <textarea className="field mt-2 min-h-[70px]" value={(value || []).join("\n")}
      onChange={(e) => onChange(split(e.target.value))} placeholder="Achievements — one bullet per line" />
  );
}
function AddBtn({ onClick, label }) {
  return <button onClick={onClick} className="btn-ghost text-[11px] px-3 py-1.5">+ {label}</button>;
}
function Empty() { return <p className="font-mono text-[12px] text-muted">none yet</p>; }
