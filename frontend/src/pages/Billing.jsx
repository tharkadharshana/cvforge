import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { useCredits } from "../lib/credits";
import { Banner, Spinner } from "../components/ui";

export default function Billing() {
  const [sum, setSum] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");
  const [params, setParams] = useSearchParams();
  const { refresh: refreshNav } = useCredits();
  const justPaid = params.get("status") === "success";

  const load = async () => {
    try {
      const { summary, ledger } = await api.billingOverview();
      setSum(summary); setLedger(ledger); refreshNav();
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  // after returning from Polar, the webhook may take a moment — poll a few times
  useEffect(() => {
    if (!justPaid) return;
    let n = 0;
    const t = setInterval(async () => {
      n += 1;
      await load();
      if (n >= 5) clearInterval(t);
    }, 2500);
    return () => clearInterval(t);
  }, [justPaid]);

  if (loading) return <Spinner label="Loading billing" />;
  if (!sum) return <Banner>{err || "Could not load billing."}</Banner>;

  const go = async (fn, key) => {
    setErr(""); setBusy(key);
    try { const { checkout_url } = await fn(); window.location.href = checkout_url; }
    catch (e) { setErr(e.message); setBusy(""); }
  };

  const low = sum.credits <= sum.credits_per_generation;

  return (
    <div className="rise space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="font-display font-extrabold text-3xl">Billing</h1>
          <p className="label mt-1">Credits power CV generation · {sum.credits_per_generation} credit per CV.</p>
        </div>
        {sum.has_customer && (
          <button className="btn-ghost text-[11px] px-4 py-2.5" disabled={busy === "portal"}
            onClick={() => go(api.billingPortal, "portal")}>
            {busy === "portal" ? "Opening…" : "Manage billing & cards"}
          </button>
        )}
      </div>

      {justPaid && <Banner kind="ok">Payment received. Your credits will appear here within a few seconds.</Banner>}
      {err && <Banner>{err}</Banner>}

      <div className="panel p-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="label">Current balance</div>
          <div className="flex items-baseline gap-2">
            <span className={`font-display font-extrabold text-5xl ${low ? "text-bad" : "text-accent"}`}>{sum.credits}</span>
            <span className="label">credits</span>
          </div>
        </div>
        <div className="text-right">
          <div className="label">Plan</div>
          <div className="font-display font-bold text-xl capitalize">{sum.plan}</div>
          <div className="label mt-1">{sum.free_tier_mode === "forever_free" ? "Free tier refills monthly" : "Free trial credits"}</div>
        </div>
      </div>

      {low && <Banner kind="info">You're low on credits. Top up below to keep generating tailored CVs.</Banner>}

      <div>
        <h2 className="label mb-3">Plans</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          {sum.plans.map((p) => (
            <div key={p.id} className="panel p-6 flex flex-col">
              <div className="flex items-center justify-between">
                <div className="font-display font-bold text-xl">{p.name}</div>
                {p.recurring && <span className="tag border-accent/40 text-accent">monthly</span>}
              </div>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="font-display font-extrabold text-4xl">${p.price_usd}</span>
                {p.recurring && <span className="label">/mo</span>}
              </div>
              <div className="label mt-1">{p.credits} credits · {p.credits} tailored CVs</div>
              <div className="font-mono text-[11px] text-muted mt-1">${p.price_per_credit.toFixed(2)} per CV</div>
              <button className="btn-primary mt-5" disabled={busy === p.id || !p.available}
                onClick={() => go(() => api.checkout(p.id), p.id)}>
                {busy === p.id ? "Redirecting…" : !p.available ? "Coming soon" : p.recurring ? "Subscribe" : `Buy ${p.credits} credits`}
              </button>
              {!p.available && <p className="label mt-2 text-center">Not configured yet</p>}
            </div>
          ))}
        </div>
        <p className="label mt-3">Secure checkout by Polar. Cards are handled by Polar — never stored on our servers.</p>
      </div>

      <div>
        <h2 className="label mb-3">Recent activity</h2>
        {ledger.length === 0 ? (
          <p className="font-mono text-[12px] text-muted">No transactions yet.</p>
        ) : (
          <div className="border border-line divide-y divide-line">
            {ledger.map((r, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-2.5 bg-panel/50">
                <div>
                  <div className="font-mono text-[12px]">{label(r.reason)}</div>
                  <div className="label">{new Date(r.created_at).toLocaleString()}</div>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`font-mono text-sm ${r.delta >= 0 ? "text-good" : "text-muted"}`}>
                    {r.delta >= 0 ? "+" : ""}{r.delta}
                  </span>
                  <span className="font-mono text-[12px] text-muted w-10 text-right">{r.balance_after}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function label(reason) {
  const map = {
    signup_trial: "Free trial credits",
    signup_free_monthly: "Free monthly credits",
    monthly_refill: "Monthly refill",
    generation: "CV generated",
  };
  if (reason.startsWith("purchase:")) return "Credits purchased";
  return map[reason] || reason;
}
