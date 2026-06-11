function Section({ title, children }) {
  return (
    <section className="mb-5">
      <h3 className="label border-b border-line pb-1 mb-2">{title}</h3>
      {children}
    </section>
  );
}

export default function CVView({ cv }) {
  if (!cv) return null;
  const c = cv.contact || {};
  const contactBits = [c.email, c.phone, c.location, c.linkedin, c.github, c.website].filter(Boolean);

  return (
    <div className="font-read text-fg leading-relaxed">
      <div className="text-center mb-5">
        <div className="font-display font-extrabold text-2xl">{c.full_name || "—"}</div>
        <div className="font-mono text-[11px] text-muted mt-1">{contactBits.join("  ·  ")}</div>
      </div>

      {cv.summary && <Section title="Summary"><p className="text-[15px]">{cv.summary}</p></Section>}

      {cv.skills && Object.keys(cv.skills).length > 0 && (
        <Section title="Skills">
          <div className="space-y-1">
            {Object.entries(cv.skills).map(([cat, items]) => (
              <div key={cat} className="text-[14px]">
                <span className="font-mono text-accent text-[12px]">{cat}: </span>
                {(items || []).join(", ")}
              </div>
            ))}
          </div>
        </Section>
      )}

      {cv.experience?.length > 0 && (
        <Section title="Experience">
          {cv.experience.map((e, i) => (
            <div key={i} className="mb-3">
              <div className="flex justify-between items-baseline gap-3">
                <span className="font-display font-semibold text-[15px]">{e.title}{e.company ? `, ${e.company}` : ""}</span>
                <span className="font-mono text-[11px] text-muted whitespace-nowrap">{[e.start, e.end].filter(Boolean).join(" – ")}</span>
              </div>
              <ul className="list-disc ml-5 mt-1 text-[14px] space-y-0.5">
                {(e.bullets || []).map((b, j) => <li key={j}>{b}</li>)}
              </ul>
            </div>
          ))}
        </Section>
      )}

      {cv.projects?.length > 0 && (
        <Section title="Projects">
          {cv.projects.map((p, i) => (
            <div key={i} className="mb-3">
              <div className="font-display font-semibold text-[15px]">
                {p.name} {p.tech?.length ? <span className="font-mono text-[11px] text-muted">({p.tech.join(", ")})</span> : null}
              </div>
              {p.description && <p className="text-[14px]">{p.description}</p>}
              <ul className="list-disc ml-5 mt-1 text-[14px] space-y-0.5">
                {(p.bullets || []).map((b, j) => <li key={j}>{b}</li>)}
              </ul>
            </div>
          ))}
        </Section>
      )}

      {cv.education?.length > 0 && (
        <Section title="Education">
          {cv.education.map((e, i) => (
            <div key={i} className="mb-2">
              <div className="flex justify-between items-baseline gap-3">
                <span className="font-display font-semibold text-[15px]">{e.degree}{e.institution ? `, ${e.institution}` : ""}</span>
                <span className="font-mono text-[11px] text-muted whitespace-nowrap">{[e.start, e.end].filter(Boolean).join(" – ")}</span>
              </div>
              {e.details?.length > 0 && (
                <ul className="list-disc ml-5 mt-1 text-[14px]">{e.details.map((d, j) => <li key={j}>{d}</li>)}</ul>
              )}
            </div>
          ))}
        </Section>
      )}

      {cv.certifications?.length > 0 && (
        <Section title="Certifications"><ul className="list-disc ml-5 text-[14px]">{cv.certifications.map((x, i) => <li key={i}>{x}</li>)}</ul></Section>
      )}
      {cv.awards?.length > 0 && (
        <Section title="Awards"><ul className="list-disc ml-5 text-[14px]">{cv.awards.map((x, i) => <li key={i}>{x}</li>)}</ul></Section>
      )}
      {cv.languages?.length > 0 && (
        <Section title="Languages"><p className="text-[14px]">{cv.languages.join(", ")}</p></Section>
      )}
    </div>
  );
}
