import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Banner } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setErr(""); setBusy(true);
    try { await login(email, password); nav("/cv"); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <AuthShell heading="Welcome back" sub="Sign in to forge your next CV.">
      <div className="space-y-3">
        <div><div className="label mb-1">Email</div>
          <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@domain.com" autoFocus /></div>
        <div><div className="label mb-1">Password</div>
          <input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()} placeholder="••••••••" /></div>
        <Banner>{err}</Banner>
        <button className="btn-primary w-full" disabled={busy} onClick={submit}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="label text-center pt-1">New here? <Link to="/register" className="text-accent">Create an account</Link></p>
      </div>
    </AuthShell>
  );
}

/* shared split-screen auth layout: brand panel + form */
export function AuthShell({ heading, sub, children }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* brand panel */}
      <div className="relative hidden lg:flex flex-col justify-between p-10 border-r border-line overflow-hidden">
        <div
          className="absolute inset-0 -z-10"
          style={{
            backgroundImage:
              "radial-gradient(800px 400px at 20% 0%, rgba(255,92,53,0.12), transparent 60%)," +
              "linear-gradient(to right, rgba(255,255,255,0.025) 1px, transparent 1px)," +
              "linear-gradient(to bottom, rgba(255,255,255,0.025) 1px, transparent 1px)",
            backgroundSize: "auto, 38px 38px, 38px 38px",
          }}
        />
        <Link to="/" className="flex items-baseline gap-2">
          <span className="font-display font-extrabold text-2xl tracking-tight">CVForge</span>
          <span className="label text-accent">/ forge per job</span>
        </Link>

        <div className="max-w-sm">
          <h2 className="font-display font-extrabold text-3xl leading-tight">
            One master CV.<br />A perfect one for<br /><span className="text-accent">every</span> job.
          </h2>
          <p className="mt-4 text-muted text-[15px] leading-relaxed">
            Import once, then generate ATS-ready CVs and cover letters tailored to each role you apply for.
          </p>
        </div>

        <div className="label">ATS-tuned · DeepSeek + Gemini</div>
      </div>

      {/* form */}
      <div className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-sm rise">
          <Link to="/" className="lg:hidden flex items-baseline gap-2 mb-8">
            <span className="font-display font-extrabold text-2xl">CVForge</span>
          </Link>
          <h1 className="font-display font-extrabold text-2xl">{heading}</h1>
          <p className="label mt-1 mb-6">{sub}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
