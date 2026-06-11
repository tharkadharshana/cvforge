import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Banner, Spinner } from "../components/ui";

export default function Applications() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try { setApps(await api.listApplications()); }
      catch (e) { setErr(e.message); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) return <Spinner label="Loading history" />;

  return (
    <div className="rise">
      <h1 className="font-display font-extrabold text-3xl mb-1">History</h1>
      <p className="label mb-5">Every generated application.</p>
      {err && <Banner>{err}</Banner>}

      {apps.length === 0 ? (
        <div className="panel p-8 text-center font-mono text-sm text-muted">
          Nothing yet. <Link to="/generate" className="text-accent">Generate your first →</Link>
        </div>
      ) : (
        <div className="border border-line divide-y divide-line">
          {apps.map((a) => {
            const s = a.ats_score || 0;
            const color = s >= 80 ? "#7ee787" : s >= 60 ? "#f0c674" : "#ff6b6b";
            return (
              <Link key={a.id} to={`/applications/${a.id}`}
                className="flex items-center justify-between gap-4 px-4 py-3 bg-panel/50 hover:bg-panel2 transition-colors group">
                <div className="min-w-0">
                  <div className="font-display font-semibold truncate group-hover:text-accent transition-colors">{a.job_title || "Untitled role"}</div>
                  <div className="font-mono text-[11px] text-muted truncate">{a.company || "—"} · {new Date(a.created_at).toLocaleDateString()}</div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="font-mono text-[11px] text-muted">ATS</span>
                  <span className="font-display font-extrabold text-lg" style={{ color }}>{s}</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
