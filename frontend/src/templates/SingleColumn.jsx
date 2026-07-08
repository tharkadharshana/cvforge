import { Page, contactBits, hasSkills } from "./common";

// ATS-safe single-column template, parameterized by accent colour, font family and
// heading style. Mirrors the backend pure-Python PDF/DOCX render so the on-screen
// preview matches the "Download ATS" file. Used for ats_classic / ats_modern / ats_serif.
export default function SingleColumn({ cv, accent = "#1a1a1a", font = "Helvetica, Arial, sans-serif", heading = "rule", nameSize = 26 }) {
  if (!cv) return null;
  const c = cv.contact || {};
  const caps = heading === "caps";
  const H = ({ children }) => (
    <h2 style={{
      fontSize: 13, fontWeight: 700, color: accent, margin: "16px 0 6px",
      textTransform: caps ? "uppercase" : "none", letterSpacing: caps ? 1 : 0,
      borderBottom: heading === "plain" ? "none" : `1px solid ${accent}`,
      paddingBottom: 3,
    }}>{children}</h2>
  );
  return (
    <Page style={{ fontFamily: font, padding: "18mm 18mm", fontSize: 11, lineHeight: 1.45 }}>
      <div style={{ textAlign: "center", marginBottom: 10 }}>
        <div style={{ fontSize: nameSize, fontWeight: 800, color: accent }}>{c.full_name || "—"}</div>
        <div style={{ fontSize: 10, color: "#555", marginTop: 3 }}>{contactBits(c).join("   |   ")}</div>
      </div>

      {cv.summary && (<><H>Professional Summary</H><p>{cv.summary}</p></>)}

      {hasSkills(cv) && (
        <><H>Skills</H>
          {Object.entries(cv.skills).map(([cat, items]) => (
            <div key={cat}><strong>{cat}:</strong> {(items || []).join(", ")}</div>
          ))}
        </>
      )}

      {cv.experience?.length > 0 && (
        <><H>Experience</H>
          {cv.experience.map((e, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{e.title}{e.company ? `, ${e.company}` : ""}</strong>
                <span style={{ color: "#555", fontSize: 10 }}>{[e.start, e.end].filter(Boolean).join(" – ")}</span>
              </div>
              <ul style={{ margin: "3px 0 0 18px" }}>{(e.bullets || []).map((b, j) => <li key={j}>{b}</li>)}</ul>
            </div>
          ))}
        </>
      )}

      {cv.projects?.length > 0 && (
        <><H>Projects</H>
          {cv.projects.map((p, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <strong>{p.name}</strong>{p.tech?.length ? ` (${p.tech.join(", ")})` : ""}
              {p.description && <div>{p.description}</div>}
              <ul style={{ margin: "3px 0 0 18px" }}>{(p.bullets || []).map((b, j) => <li key={j}>{b}</li>)}</ul>
            </div>
          ))}
        </>
      )}

      {cv.education?.length > 0 && (
        <><H>Education</H>
          {cv.education.map((e, i) => (
            <div key={i} style={{ marginBottom: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{e.degree}{e.institution ? `, ${e.institution}` : ""}</strong>
                <span style={{ color: "#555", fontSize: 10 }}>{[e.start, e.end].filter(Boolean).join(" – ")}</span>
              </div>
              {e.details?.length > 0 && <ul style={{ margin: "3px 0 0 18px" }}>{e.details.map((d, j) => <li key={j}>{d}</li>)}</ul>}
            </div>
          ))}
        </>
      )}

      {cv.certifications?.length > 0 && (<><H>Certifications</H><ul style={{ margin: "0 0 0 18px" }}>{cv.certifications.map((x, i) => <li key={i}>{x}</li>)}</ul></>)}
      {cv.awards?.length > 0 && (<><H>Awards</H><ul style={{ margin: "0 0 0 18px" }}>{cv.awards.map((x, i) => <li key={i}>{x}</li>)}</ul></>)}
      {cv.languages?.length > 0 && (<><H>Languages</H><p>{cv.languages.join(", ")}</p></>)}
    </Page>
  );
}
