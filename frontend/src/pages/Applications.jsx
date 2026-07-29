import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Banner, Spinner } from "../components/ui";

const TRACKER_STATUSES = [
  "not_applied", "applied", "screening", "interview_1", "interview_2",
  "offer", "hired", "rejected", "withdrawn", "ghosted",
];

const STATUS_LABEL = {
  not_applied: "Not applied", applied: "Applied", screening: "Screening",
  interview_1: "Interview 1", interview_2: "Interview 2", offer: "Offer",
  hired: "Hired", rejected: "Rejected", withdrawn: "Withdrawn", ghosted: "Ghosted",
};

const STATUS_COLOR = {
  not_applied: "#8b8b90", applied: "#5b9dd9", screening: "#f0c674",
  interview_1: "#b48ead", interview_2: "#b48ead", offer: "#7ee787",
  hired: "#34d399", rejected: "#ff6b6b", withdrawn: "#8b8b90", ghosted: "#8b8b90",
};

export default function Applications() {
  const [apps, setApps] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = async () => {
    try {
      const [list, s] = await Promise.all([api.listApplications(), api.applicationStats()]);
      setApps(list);
      setStats(s);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const setStatus = async (id, tracker_status) => {
    setApps((cur) => cur.map((a) => (a.id === id ? { ...a, tracker_status } : a)));  // optimistic
    try {
      await api.updateTrackerStatus(id, tracker_status);
      const s = await api.applicationStats();
      setStats(s);
    } catch (e) { setErr(e.message); }
  };

  if (loading) return <Spinner label="Loading history" />;

  return (
    <div className="rise">
      <h1 className="font-display font-extrabold text-3xl mb-1">History</h1>
      <p className="label mb-5">Every generated application.</p>
      {err && <Banner>{err}</Banner>}

      {Object.keys(stats).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-5">
          {Object.entries(stats).map(([status, count]) => (
            <span key={status} className="border border-line2 px-2.5 py-1 font-mono text-[11px]"
              style={{ color: STATUS_COLOR[status] || "#8b8b90" }}>
              {STATUS_LABEL[status] || status}: {count}
            </span>
          ))}
        </div>
      )}

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
              <div key={a.id} className="flex items-center justify-between gap-4 px-4 py-3 bg-panel/50 hover:bg-panel2 transition-colors group">
                <Link to={`/applications/${a.id}`} className="min-w-0 flex-1">
                  <div className="font-display font-semibold truncate group-hover:text-accent transition-colors">{a.job_title || "Untitled role"}</div>
                  <div className="font-mono text-[11px] text-muted truncate">{a.company || "—"} · {new Date(a.created_at).toLocaleDateString()}</div>
                </Link>
                <div className="flex items-center gap-3 shrink-0">
                  <select className="field text-[11px] py-1.5" value={a.tracker_status || "not_applied"}
                    onChange={(e) => setStatus(a.id, e.target.value)} onClick={(e) => e.stopPropagation()}>
                    {TRACKER_STATUSES.map((st) => <option key={st} value={st}>{STATUS_LABEL[st]}</option>)}
                  </select>
                  <span className="font-mono text-[11px] text-muted">ATS</span>
                  <span className="font-display font-extrabold text-lg" style={{ color }}>{s}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
