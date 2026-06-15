import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ThemeToggle } from "../lib/theme";

/* ---------- inline icons (stroke = currentColor) ---------- */
const Icon = ({ d, size = 22 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {d}
  </svg>
);
const icons = {
  target: <Icon d={<><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.4" /></>} />,
  gauge: <Icon d={<><path d="M12 13l4-4" /><path d="M4 18a8 8 0 1 1 16 0" /></>} />,
  pen: <Icon d={<><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></>} />,
  file: <Icon d={<><path d="M14 3v5h5" /><path d="M14 3H6v18h12V8Z" /><path d="M9 13h6M9 17h4" /></>} />,
  layers: <Icon d={<><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></>} />,
  history: <Icon d={<><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4" /><path d="M12 8v4l3 2" /></>} />,
  bolt: <Icon d={<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />} />,
  shield: <Icon d={<><path d="M12 3 5 6v5c0 4 3 7 7 9 4-2 7-5 7-9V6l-7-3Z" /><path d="m9 12 2 2 4-4" /></>} />,
};

export default function Landing() {
  const { authed } = useAuth();
  const primaryTo = authed ? "/cv" : "/register";
  const primaryLabel = authed ? "Open app" : "Start free";

  return (
    <div className="min-h-screen">
      {/* nav */}
      <header className="sticky top-0 z-30 border-b border-line bg-ink/70 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="font-display font-extrabold text-xl tracking-tight">CVForge</span>
            <span className="label text-accent hidden sm:inline">/ forge per job</span>
          </div>
          <nav className="flex items-center gap-4">
            <a href="#how" className="label hover:text-fg transition-colors hidden sm:inline">How it works</a>
            <a href="#features" className="label hover:text-fg transition-colors hidden sm:inline">Features</a>
            <Link to="/login" className="label hover:text-fg transition-colors">Sign in</Link>
            <ThemeToggle />
            <Link to={primaryTo} className="btn-primary text-[11px] px-4 py-2">{primaryLabel}</Link>
          </nav>
        </div>
      </header>

      {/* hero */}
      <section className="max-w-6xl mx-auto px-5 pt-16 pb-20 grid lg:grid-cols-[1.05fr_0.95fr] gap-12 items-center">
        <div>
          <div className="label text-accent mb-5 rise">ATS-tuned · AI-powered</div>
          <h1 className="font-display font-extrabold leading-[1.02] text-[clamp(2.4rem,6vw,4.2rem)] rise" style={{ animationDelay: ".05s" }}>
            A tailored CV for<br />every job — forged<br />from <span className="text-accent">one</span> master profile.
          </h1>
          <p className="mt-6 text-[17px] text-muted max-w-md leading-relaxed rise" style={{ animationDelay: ".12s" }}>
            Keep one CV with everything you've ever done. Paste a job description and CVForge writes a sharp,
            ATS-ready CV and a human-sounding cover letter built for that exact role.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3 rise" style={{ animationDelay: ".18s" }}>
            <Link to={primaryTo} className="btn-primary px-6 py-3 text-[13px]">{primaryLabel} →</Link>
            <a href="#how" className="btn-ghost px-6 py-3 text-[13px]">See how it works</a>
          </div>
          <p className="mt-4 label rise" style={{ animationDelay: ".22s" }}>No credit card · free to start</p>
        </div>

        <ForgeVisual />
      </section>

      {/* how it works */}
      <section id="how" className="border-t border-line bg-panel/30">
        <div className="max-w-6xl mx-auto px-5 py-16">
          <SectionHead eyebrow="How it works" title="Three steps. Every time." />
          <div className="grid md:grid-cols-3 gap-px bg-line border border-line mt-8">
            {[
              ["01", "Build your base CV", "Import a PDF, Word doc, or paste text — or answer a few guided questions. This master CV holds everything you've done."],
              ["02", "Paste a job description", "Drop in the role you want. CVForge reads it, then selects and rewrites the parts of your CV that matter most."],
              ["03", "Download and apply", "Get a tailored CV, a matching cover letter, and an ATS score — as PDF or Word, ready to send."],
            ].map(([n, t, d]) => (
              <div key={n} className="bg-ink p-7">
                <div className="font-mono text-accent text-sm mb-3">{n}</div>
                <h3 className="font-display font-bold text-lg mb-2">{t}</h3>
                <p className="text-[14px] text-muted leading-relaxed">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* features */}
      <section id="features" className="max-w-6xl mx-auto px-5 py-16">
        <SectionHead eyebrow="What's inside" title="Built to get past the filter — and the recruiter." />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
          {[
            [icons.target, "Job-matched tailoring", "Mirrors the job's language and surfaces your most relevant work — without inventing anything you didn't do."],
            [icons.gauge, "Live ATS score", "Every CV is scored and audited by a second AI model for keyword coverage and parse-ability."],
            [icons.pen, "Human cover letters", "Specific, natural letters tied to your real achievements. No clichés, no robotic filler."],
            [icons.file, "PDF + Word export", "Clean single-column output that ATS software reads correctly. Download in either format."],
            [icons.layers, "One master, many CVs", "Edit your base CV once. Add new wins anytime in plain words and they slot into the right place."],
            [icons.history, "Application history", "Every CV you generate is saved with its score, ready to revisit, tweak, or download again."],
          ].map(([ic, t, d], i) => (
            <div key={i} className="panel p-6 hover:border-line2 transition-colors">
              <div className="text-accent mb-4">{ic}</div>
              <h3 className="font-display font-semibold text-[16px] mb-2">{t}</h3>
              <p className="text-[13.5px] text-muted leading-relaxed">{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* why band */}
      <section className="border-y border-line bg-panel/30">
        <div className="max-w-6xl mx-auto px-5 py-16 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <div className="text-accent mb-3">{icons.shield}</div>
            <h2 className="font-display font-extrabold text-3xl leading-tight">
              Most applications are filtered by software before a human ever reads them.
            </h2>
          </div>
          <div className="space-y-4 text-muted text-[15px] leading-relaxed">
            <p>
              Applicant tracking systems rank resumes on how well they match the posting. A strong, generic CV
              still loses to a focused one that speaks the role's language.
            </p>
            <p>
              CVForge does that focusing for you — pulling the right experience forward, matching keywords honestly,
              and formatting so the parser reads every line. You stay truthful; you just stop getting filtered out.
            </p>
          </div>
        </div>
      </section>

      {/* final cta */}
      <section className="max-w-6xl mx-auto px-5 py-20 text-center">
        <div className="text-accent flex justify-center mb-4">{icons.bolt}</div>
        <h2 className="font-display font-extrabold text-[clamp(1.8rem,4vw,2.8rem)] leading-tight">
          Stop rewriting your CV for every job.
        </h2>
        <p className="mt-4 text-muted text-[16px] max-w-lg mx-auto">
          Set up your master CV once. Forge a perfect one for each role in seconds.
        </p>
        <div className="mt-8 flex justify-center">
          <Link to={primaryTo} className="btn-primary px-8 py-3.5 text-[13px]">{primaryLabel} →</Link>
        </div>
      </section>

      {/* footer */}
      <footer className="border-t border-line">
        <div className="max-w-6xl mx-auto px-5 py-6 flex flex-col sm:flex-row justify-between gap-3 label">
          <span>CVForge — tailored CVs, forged per job.</span>
          <span className="text-line2">Built with FastAPI · React · AI-powered</span>
        </div>
      </footer>
    </div>
  );
}

function SectionHead({ eyebrow, title }) {
  return (
    <div className="max-w-2xl">
      <div className="label text-accent mb-2">{eyebrow}</div>
      <h2 className="font-display font-extrabold text-[clamp(1.6rem,3.5vw,2.4rem)] leading-tight">{title}</h2>
    </div>
  );
}

/* the signature: base CV -> tailored CV, with ATS score climbing */
function ForgeVisual() {
  const score = 94;
  const dash = 264;
  const offset = dash * (1 - score / 100);
  return (
    <div className="relative rise floaty" style={{ animationDelay: ".1s" }} aria-hidden="true">
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        {/* base */}
        <div className="panel p-4 opacity-80">
          <div className="label mb-3">Base CV</div>
          {[80, 95, 70, 88, 60, 75].map((w, i) => (
            <div key={i} className="h-1.5 bg-line2 mb-2" style={{ width: `${w}%` }} />
          ))}
        </div>

        {/* arrow */}
        <div className="flex flex-col items-center gap-1 text-accent">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />
          </svg>
          <span className="label text-accent">forge</span>
        </div>

        {/* tailored */}
        <div className="panel p-4 border-accent/40" style={{ boxShadow: "0 0 40px rgba(255,92,53,0.12)" }}>
          <div className="label text-accent mb-3">Tailored · Backend Eng</div>
          {[
            [90, true], [70, false], [95, true], [80, true], [65, false],
          ].map(([w, hot], i) => (
            <div key={i} className={`h-1.5 mb-2 ${hot ? "bg-accent" : "bg-line2"}`} style={{ width: `${w}%` }} />
          ))}
          <div className="flex flex-wrap gap-1 mt-3">
            {["FastAPI", "Python", "AWS"].map((k) => (
              <span key={k} className="font-mono text-[9px] px-1.5 py-0.5 border border-accent/40 text-accent">{k}</span>
            ))}
          </div>
        </div>
      </div>

      {/* ATS gauge */}
      <div className="panel mt-3 p-4 flex items-center gap-4">
        <div className="relative w-16 h-16 shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            <circle cx="50" cy="50" r="42" fill="none" stroke="#2a2a2e" strokeWidth="8" />
            <circle cx="50" cy="50" r="42" fill="none" stroke="#7ee787" strokeWidth="8" strokeLinecap="butt"
              strokeDasharray={dash} strokeDashoffset={offset} className="ringfill" />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center font-display font-extrabold text-lg" style={{ color: "#7ee787" }}>{score}</div>
        </div>
        <div>
          <div className="label">ATS score</div>
          <div className="font-mono text-sm text-fg">Strong match · ready to send</div>
        </div>
      </div>
    </div>
  );
}
