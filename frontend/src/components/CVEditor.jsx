import { useState } from "react";

// Shared inline editor for the CVData structure. Used by both the base-CV page
// and the per-application manual editor so there is exactly one place that knows
// how to edit a CV. It is a controlled component: the parent owns the `cv` state.

export const splitComma = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
export const splitLines = (s) => s.split("\n").map((x) => x.replace(/^[-•]\s*/, "").trim()).filter(Boolean);

export const emptyCV = {
  contact: { full_name: "", email: "", phone: "", location: "", linkedin: "", github: "", website: "" },
  summary: "", skills: {}, experience: [], projects: [], education: [],
  certifications: [], awards: [], languages: [],
};

/**
 * @param cv       current CVData object
 * @param onChange (nextCv) => void — called with the full updated CV
 * @param rev      optional key bump to reset uncontrolled comma inputs after external replaces
 */
export default function CVEditor({ cv, onChange, rev = 0 }) {
  const set = (patch) => onChange({ ...cv, ...patch });
  const setC = (k, v) => onChange({ ...cv, contact: { ...cv.contact, [k]: v } });

  return (
    <div className="space-y-6">
      <Card title="Contact">
        <div className="grid sm:grid-cols-2 gap-2">
          {["full_name", "email", "phone", "location", "linkedin", "github", "website"].map((k) => (
            <input key={k} className="field" value={cv.contact?.[k] || ""} onChange={(e) => setC(k, e.target.value)} placeholder={k.replace("_", " ")} />
          ))}
        </div>
      </Card>

      <Card title="Summary">
        <textarea className="field min-h-[90px]" value={cv.summary} onChange={(e) => set({ summary: e.target.value })} placeholder="Professional summary" />
      </Card>

      <Card title="Skills" action={<AddBtn onClick={() => set({ skills: { ...cv.skills, "New category": [] } })} label="category" />}>
        {Object.keys(cv.skills || {}).length === 0 && <Empty />}
        {Object.entries(cv.skills || {}).map(([cat, items], i) => (
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
    </div>
  );
}

export function Card({ title, action, children }) {
  return (
    <section className="panel p-5">
      <div className="flex items-center justify-between mb-3"><h2 className="label">{title}</h2>{action}</div>
      {children}
    </section>
  );
}
function ListEditor({ title, items, onChange, template, render }) {
  const add = () => onChange([...(items || []), JSON.parse(JSON.stringify(template))]);
  const remove = (i) => onChange(items.filter((_, j) => j !== i));
  const updAt = (i, patch) => onChange(items.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  return (
    <Card title={title} action={<AddBtn onClick={add} label="entry" />}>
      {(!items || items.length === 0) && <Empty />}
      {(items || []).map((it, i) => (
        <div key={i} className="border border-line p-3 mb-2 relative">
          <button onClick={() => remove(i)} className="absolute top-2 right-2 label text-bad">remove</button>
          {render(it, (patch) => updAt(i, patch))}
        </div>
      ))}
    </Card>
  );
}
export function CommaInput({ className, value, onChange, placeholder }) {
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
export function AddBtn({ onClick, label }) {
  return <button onClick={onClick} className="btn-ghost text-[11px] px-3 py-1.5">+ {label}</button>;
}
function Empty() { return <p className="font-mono text-[12px] text-muted">none yet</p>; }
