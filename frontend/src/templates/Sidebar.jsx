import { Page, contactBits, hasSkills } from "./common";

// Designer two-column template with a coloured sidebar (contact + skills + education)
// and a roomy main column. NOT ATS-safe — used only for the on-screen designer preview
// and print-to-PDF. Used for aurora / sidebar_pro (they differ only by colours).
export default function Sidebar({ cv, accent = "#4F46E5", sidebarBg = "#4F46E5", sidebarFg = "#fff", font = "Inter, system-ui, sans-serif" }) {
  if (!cv) return null;
  const c = cv.contact || {};
  const SideH = ({ children }) => (
    <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, opacity: 0.85, margin: "16px 0 6px" }}>{children}</div>
  );
  const MainH = ({ children }) => (
    <h2 style={{ fontSize: 14, fontWeight: 700, color: accent, margin: "14px 0 6px", borderBottom: `2px solid ${accent}22`, paddingBottom: 3 }}>{children}</h2>
  );
  return (
    <Page style={{ fontFamily: font, display: "flex", fontSize: 11, lineHeight: 1.45 }}>
      {/* sidebar */}
      <div style={{ width: "34%", background: sidebarBg, color: sidebarFg, padding: "18mm 10mm", boxSizing: "border-box" }}>
        <div style={{ fontSize: 22, fontWeight: 800, lineHeight: 1.1 }}>{c.full_name || "—"}</div>
        <SideH>Contact</SideH>
        <div style={{ fontSize: 10, wordBreak: "break-word" }}>
          {contactBits(c).map((x, i) => <div key={i} style={{ marginBottom: 3 }}>{x}</div>)}
        </div>
        {hasSkills(cv) && (
          <><SideH>Skills</SideH>
            {Object.entries(cv.skills).map(([cat, items]) => (
              <div key={cat} style={{ marginBottom: 6, fontSize: 10 }}>
                <div style={{ fontWeight: 700 }}>{cat}</div>
                <div>{(items || []).join(", ")}</div>
              </div>
            ))}
          </>
        )}
        {cv.education?.length > 0 && (
          <><SideH>Education</SideH>
            {cv.education.map((e, i) => (
              <div key={i} style={{ marginBottom: 6, fontSize: 10 }}>
                <div style={{ fontWeight: 700 }}>{e.degree}</div>
                <div>{e.institution}</div>
                <div style={{ opacity: 0.8 }}>{[e.start, e.end].filter(Boolean).join(" – ")}</div>
              </div>
            ))}
          </>
        )}
        {cv.languages?.length > 0 && (<><SideH>Languages</SideH><div style={{ fontSize: 10 }}>{cv.languages.join(", ")}</div></>)}
      </div>

      {/* main */}
      <div style={{ flex: 1, padding: "18mm 12mm", boxSizing: "border-box" }}>
        {cv.summary && (<><MainH>Profile</MainH><p>{cv.summary}</p></>)}

        {cv.experience?.length > 0 && (
          <><MainH>Experience</MainH>
            {cv.experience.map((e, i) => (
              <div key={i} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{e.title}{e.company ? `, ${e.company}` : ""}</strong>
                  <span style={{ color: "#666", fontSize: 10 }}>{[e.start, e.end].filter(Boolean).join(" – ")}</span>
                </div>
                <ul style={{ margin: "3px 0 0 18px" }}>{(e.bullets || []).map((b, j) => <li key={j}>{b}</li>)}</ul>
              </div>
            ))}
          </>
        )}

        {cv.projects?.length > 0 && (
          <><MainH>Projects</MainH>
            {cv.projects.map((p, i) => (
              <div key={i} style={{ marginBottom: 8 }}>
                <strong>{p.name}</strong>{p.tech?.length ? ` (${p.tech.join(", ")})` : ""}
                {p.description && <div>{p.description}</div>}
                <ul style={{ margin: "3px 0 0 18px" }}>{(p.bullets || []).map((b, j) => <li key={j}>{b}</li>)}</ul>
              </div>
            ))}
          </>
        )}

        {cv.certifications?.length > 0 && (<><MainH>Certifications</MainH><ul style={{ margin: "0 0 0 18px" }}>{cv.certifications.map((x, i) => <li key={i}>{x}</li>)}</ul></>)}
        {cv.awards?.length > 0 && (<><MainH>Awards</MainH><ul style={{ margin: "0 0 0 18px" }}>{cv.awards.map((x, i) => <li key={i}>{x}</li>)}</ul></>)}
      </div>
    </Page>
  );
}
