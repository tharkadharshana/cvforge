import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../lib/api";
import { useCVStatus } from "../lib/cvstatus";
import { useCredits } from "../lib/credits";
import { Banner, Spinner } from "../components/ui";
import CVEditor, { Card, emptyCV } from "../components/CVEditor";

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
      try { setCv({ ...emptyCV, ...(await api.getCV()) }); }
      catch (e) { setErr(e.message); }
      finally { setLoading(false); }
    })();
  }, []);

  if (!stLoading && status && !status.has_base_cv) return <Navigate to="/onboarding" replace />;
  if (loading || !cv) return <Spinner label="Loading CV" />;

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
      setCv({ ...emptyCV, ...u }); setRev((r) => r + 1); setQual(""); setMsg("Merged into CV.");
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

      <CVEditor cv={cv} onChange={setCv} rev={rev} />

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
