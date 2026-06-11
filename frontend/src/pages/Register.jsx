import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Banner } from "../components/ui";
import { AuthShell } from "./Login";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setErr("");
    if (password.length < 8) { setErr("Password must be at least 8 characters."); return; }
    setBusy(true);
    try { await register(email, password, name); nav("/cv"); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <AuthShell heading="Create your account" sub="Free to start. No credit card.">
      <div className="space-y-3">
        <div><div className="label mb-1">Full name</div>
          <input className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" autoFocus /></div>
        <div><div className="label mb-1">Email</div>
          <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@domain.com" /></div>
        <div><div className="label mb-1">Password</div>
          <input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()} placeholder="At least 8 characters" /></div>
        <Banner>{err}</Banner>
        <button className="btn-primary w-full" disabled={busy} onClick={submit}>{busy ? "Creating…" : "Create account"}</button>
        <p className="label text-center pt-1">Already have an account? <Link to="/login" className="text-accent">Sign in</Link></p>
      </div>
    </AuthShell>
  );
}
