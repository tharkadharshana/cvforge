import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useCVStatus } from "../lib/cvstatus";
import { Banner, Spinner } from "../components/ui";
import Questionnaire from "../components/Questionnaire";

export default function Onboarding() {
  const [mode, setMode] = useState(null); // null | "import" | "build"
  return (
    <div className="rise max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="font-display font-extrabold text-3xl">Set up your base CV</h1>
        <p className="label mt-2">One master CV. Every tailored CV is forged from it. Start one way:</p>
      </div>

      {!mode && (
        <div className="grid md:grid-cols-2 gap-4">
          <Choice title="Import existing CV" desc="Upload a PDF / Word file, or paste text. We parse it into a structured CV."
            onClick={() => setMode("import")} tag="Fastest" />
          <Choice title="Build from questions" desc="Answer a guided set of questions. We turn your answers into a polished, ATS-ready CV."
            onClick={() => setMode("build")} tag="No CV yet?" />
        </div>
      )}

      {mode === "import" && <ImportPanel onBack={() => setMode(null)} />}
      {mode === "build" && <Questionnaire onBack={() => setMode(null)} />}
    </div>
  );
}

function Choice({ title, desc, tag, onClick }) {
  return (
    <button onClick={onClick}
      className="panel p-6 text-left hover:border-accent transition-colors group">
      <div className="label text-accent mb-3">{tag}</div>
      <div className="font-display font-bold text-xl mb-2 group-hover:text-accent transition-colors">{title}</div>
      <p className="font-mono text-[12px] text-muted leading-relaxed">{desc}</p>
    </button>
  );
}

function ImportPanel({ onBack }) {
  const nav = useNavigate();
  const { refresh } = useCVStatus();
  const fileRef = useRef();
  const [raw, setRaw] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [fileName, setFileName] = useState("");

  const done = async (fn, label) => {
    setErr(""); setBusy(label);
    try { await fn(); await refresh(); nav("/cv"); }
    catch (e) { setErr(e.message); }
    finally { setBusy(""); }
  };

  const onFile = (f) => {
    if (!f) return;
    setFileName(f.name);
    done(() => api.importFile(f), "file");
  };

  return (
    <div className="panel p-6">
      <button onClick={onBack} className="label text-accent mb-4">← back</button>

      <div className="label mb-2">Upload PDF / Word / TXT</div>
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); onFile(e.dataTransfer.files?.[0]); }}
        className="border border-dashed border-line2 hover:border-accent cursor-pointer p-8 text-center transition-colors"
      >
        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="hidden"
          onChange={(e) => onFile(e.target.files?.[0])} />
        <div className="font-mono text-sm text-muted">
          {fileName ? `Selected: ${fileName}` : "Click or drop a .pdf / .docx / .txt file"}
        </div>
        <div className="font-mono text-[11px] text-muted/60 mt-1">Legacy .doc not supported — save as .docx</div>
      </div>

      <div className="label my-4 text-center">— or paste text —</div>
      <textarea className="field min-h-[200px] resize-y leading-relaxed" value={raw}
        onChange={(e) => setRaw(e.target.value)} placeholder="Paste your full CV text here…" />
      <div className="flex justify-end mt-3">
        <button className="btn-primary" disabled={!!busy || raw.trim().length < 20}
          onClick={() => done(() => api.importCV(raw), "paste")}>
          {busy === "paste" ? "Parsing…" : "Parse pasted text"}
        </button>
      </div>

      {busy && <div className="mt-4"><Spinner label={busy === "file" ? "Extracting + parsing file" : "Parsing CV"} /></div>}
      {err && <div className="mt-4"><Banner>{err}</Banner></div>}
    </div>
  );
}
