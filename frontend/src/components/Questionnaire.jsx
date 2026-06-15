import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../lib/api";
import { useCVStatus } from "../lib/cvstatus";
import { useCredits } from "../lib/credits";
import { Banner, Spinner } from "./ui";

const blankExp = { title: "", company: "", dates: "", did: "" };
const blankEdu = { degree: "", institution: "", dates: "" };
const blankProj = { name: "", tech: "", did: "" };

export default function Questionnaire({ onBack }) {
  const nav = useNavigate();
  const { refresh } = useCVStatus();
  const { refresh: refreshCredits } = useCredits();
  const [c, setC] = useState({ full_name: "", email: "", phone: "", location: "", linkedin: "", github: "", website: "" });
  const [about, setAbout] = useState("");
  const [target, setTarget] = useState("");
  const [exp, setExp] = useState([{ ...blankExp }]);
  const [edu, setEdu] = useState([{ ...blankEdu }]);
  const [proj, setProj] = useState([]);
  const [skills, setSkills] = useState("");
  const [certs, setCerts] = useState("");
  const [langs, setLangs] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [paywall, setPaywall] = useState(false);

  const submit = async () => {
    setErr(""); setPaywall(false);
    if (!c.full_name.trim()) { setErr("Your name is required."); return; }
    setBusy(true);
    const answers = {
      contact: c,
      target_role: target,
      about,
      experience: exp.filter((e) => e.title || e.company || e.did),
      education: edu.filter((e) => e.degree || e.institution),
      projects: proj.filter((p) => p.name || p.did),
      skills,
      certifications: certs,
      languages: langs,
    };
    try { await api.buildCV(answers); await refresh(); refreshCredits(); nav("/cv"); }
    catch (e) {
      if (e.status === 402) setPaywall(true);
      else setErr(e.message);
    }
    finally { setBusy(false); }
  };

  return (
    <div className="panel p-6 space-y-7">
      <button onClick={onBack} className="label text-accent">← back</button>

      <Q n="1" q="Who are you? (contact details)">
        <div className="grid sm:grid-cols-2 gap-2">
          <I v={c.full_name} set={(v) => setC({ ...c, full_name: v })} ph="Full name *" />
          <I v={c.email} set={(v) => setC({ ...c, email: v })} ph="Email" />
          <I v={c.phone} set={(v) => setC({ ...c, phone: v })} ph="Phone" />
          <I v={c.location} set={(v) => setC({ ...c, location: v })} ph="Location" />
          <I v={c.linkedin} set={(v) => setC({ ...c, linkedin: v })} ph="LinkedIn" />
          <I v={c.github} set={(v) => setC({ ...c, github: v })} ph="GitHub" />
          <I v={c.website} set={(v) => setC({ ...c, website: v })} ph="Website" />
        </div>
      </Q>

      <Q n="2" q="What role are you targeting?">
        <I v={target} set={setTarget} ph="e.g. Senior Backend Engineer" />
      </Q>

      <Q n="3" q="Tell us about yourself — years of experience, strengths, what you do best.">
        <textarea className="field min-h-[90px]" value={about} onChange={(e) => setAbout(e.target.value)}
          placeholder="Plain words are fine — we'll polish into a professional summary." />
      </Q>

      <Q n="4" q="Work experience">
        {exp.map((e, i) => (
          <Row key={i} onRemove={exp.length > 1 ? () => setExp(exp.filter((_, j) => j !== i)) : null}>
            <div className="grid sm:grid-cols-3 gap-2">
              <I v={e.title} set={(v) => up(setExp, exp, i, "title", v)} ph="Job title" />
              <I v={e.company} set={(v) => up(setExp, exp, i, "company", v)} ph="Company" />
              <I v={e.dates} set={(v) => up(setExp, exp, i, "dates", v)} ph="2021 – Present" />
            </div>
            <textarea className="field mt-2 min-h-[70px]" value={e.did}
              onChange={(ev) => up(setExp, exp, i, "did", ev.target.value)}
              placeholder="What did you do / achieve? Bullet points or sentences — we'll sharpen them." />
          </Row>
        ))}
        <Add onClick={() => setExp([...exp, { ...blankExp }])} label="Add another role" />
      </Q>

      <Q n="5" q="Education">
        {edu.map((e, i) => (
          <Row key={i} onRemove={edu.length > 1 ? () => setEdu(edu.filter((_, j) => j !== i)) : null}>
            <div className="grid sm:grid-cols-3 gap-2">
              <I v={e.degree} set={(v) => up(setEdu, edu, i, "degree", v)} ph="Degree" />
              <I v={e.institution} set={(v) => up(setEdu, edu, i, "institution", v)} ph="Institution" />
              <I v={e.dates} set={(v) => up(setEdu, edu, i, "dates", v)} ph="2018 – 2022" />
            </div>
          </Row>
        ))}
        <Add onClick={() => setEdu([...edu, { ...blankEdu }])} label="Add education" />
      </Q>

      <Q n="6" q="Skills (comma separated)">
        <textarea className="field min-h-[60px]" value={skills} onChange={(e) => setSkills(e.target.value)}
          placeholder="Python, FastAPI, React, MySQL, Docker, AWS…" />
      </Q>

      <Q n="7" q="Projects (optional)">
        {proj.map((p, i) => (
          <Row key={i} onRemove={() => setProj(proj.filter((_, j) => j !== i))}>
            <div className="grid sm:grid-cols-2 gap-2">
              <I v={p.name} set={(v) => up(setProj, proj, i, "name", v)} ph="Project name" />
              <I v={p.tech} set={(v) => up(setProj, proj, i, "tech", v)} ph="Tech used" />
            </div>
            <textarea className="field mt-2 min-h-[60px]" value={p.did}
              onChange={(ev) => up(setProj, proj, i, "did", ev.target.value)} placeholder="What it does / your role." />
          </Row>
        ))}
        <Add onClick={() => setProj([...proj, { ...blankProj }])} label="Add project" />
      </Q>

      <Q n="8" q="Certifications & languages (optional)">
        <I v={certs} set={setCerts} ph="Certifications (comma separated)" />
        <div className="mt-2"><I v={langs} set={setLangs} ph="Languages (comma separated)" /></div>
      </Q>

      {paywall && <div className="text-[12px]"><Link to="/billing" className="text-accent">Out of credits — top up →</Link></div>}
      {err && <Banner>{err}</Banner>}
      <div className="flex justify-end">
        <button className="btn-primary" disabled={busy} onClick={submit}>
          {busy ? "Building your CV…" : "Build my CV (1 credit)"}
        </button>
      </div>
      {busy && <Spinner label="LLM polishing your answers into a CV" />}
    </div>
  );
}

function up(setter, arr, i, key, val) {
  setter(arr.map((x, j) => (j === i ? { ...x, [key]: val } : x)));
}
function I({ v, set, ph }) {
  return <input className="field" value={v} onChange={(e) => set(e.target.value)} placeholder={ph} />;
}
function Q({ n, q, children }) {
  return (
    <div>
      <div className="flex items-baseline gap-2 mb-2">
        <span className="font-mono text-accent text-[12px]">{n}.</span>
        <span className="font-display font-semibold text-[15px]">{q}</span>
      </div>
      {children}
    </div>
  );
}
function Row({ children, onRemove }) {
  return (
    <div className="border border-line p-3 mb-2 relative">
      {onRemove && <button onClick={onRemove} className="absolute top-2 right-2 label text-bad hover:text-bad">remove</button>}
      {children}
    </div>
  );
}
function Add({ onClick, label }) {
  return <button onClick={onClick} className="btn-ghost text-[11px] px-3 py-2">+ {label}</button>;
}
