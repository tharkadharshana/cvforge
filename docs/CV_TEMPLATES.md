# CV Templates

Spec for creating a new CV template — the exact data contract, the render
contract, and the hard rules a template must follow. Written so a template
can be produced (by a person or an AI) from this document alone, without
needing to read the rest of the codebase.

A template is registered in two places, and both must use the same id:

1. A **catalog entry** — name, whether it's ATS-safe, and style tokens (or,
   for a designer template, nothing beyond identity — see below).
2. A **renderer** — a function that takes CV data and produces the visual layout.

## The data contract: `CVData`

Every template renders the same shape, always. All fields have defaults
(empty string / empty list / `{}`), so a template must handle any field being
empty — never assume it's populated.

```jsonc
{
  "contact": {
    "full_name": "", "email": "", "phone": "", "location": "",
    "linkedin": "", "github": "", "website": ""
  },
  "summary": "",                          // plain string, may be empty
  "skills": { "Category name": ["skill", "..."] },   // dict of category -> list, may be {}
  "experience": [
    { "title": "", "company": "", "location": "", "start": "", "end": "", "bullets": ["..."] }
  ],
  "projects": [
    { "name": "", "description": "", "tech": ["..."], "bullets": ["..."], "link": "" }
  ],
  "education": [
    { "degree": "", "institution": "", "location": "", "start": "", "end": "", "details": ["..."] }
  ],
  "certifications": ["..."],
  "awards": ["..."],
  "languages": ["..."]
}
```

Notes:

- `start`/`end` are free-text strings (e.g. `"Jan 2023"`, `"Present"`), not dates — join with `" – "`, don't parse them.
- Every list field can be empty — guard every section with `.length > 0` (see the reference implementations below).
- This is the exact object both the PDF/DOCX renderer and every on-screen template receive — no separate "preview data" format.

## Two kinds of template

- **ATS-safe**: single-column, rendered into the actual downloadable PDF/DOCX
  that gets scored and uploaded to job sites. **No custom rendering code is
  needed for these** — one shared PDF renderer and one shared DOCX renderer
  handle *every* ATS-safe template; a new one only ever contributes a `style`
  dict (see below), never new render logic.
- **Designer**: sidebars, color blocks, 2-column layouts — rendered on-screen
  only, for a human to look at. Never scored, never downloaded as the "ATS"
  file — the system silently falls back to the default ATS-safe style for the
  scored/download copy regardless of which designer template is selected on
  screen. **These do require a custom render function** since there's no
  shared renderer to fall back on visually.

## Existing ids — don't collide

`ats_classic`, `ats_modern`, `ats_serif`, `aurora`, `sidebar_pro`. A new
template needs a new, unique id used identically in both the catalog entry
and the renderer. Nothing validates this automatically — see the gotcha below.

## Adding one

### 1. Catalog entry (style tokens)

```python
"my_template": {
    "name": "My Template",
    "ats_safe": True,   # False = designer, see above
    "description": "One line shown in the picker.",
    "style": {"font": "Helvetica", "accent": "#1A1A1A", "heading": "rule",
              "name_size": 18, "body_size": 10.5, "columns": 1},
},
```

Style keys the shared ATS-safe renderer reads:

| key | values | notes |
|---|---|---|
| `font` | `Helvetica` / `Times` / `Courier` | must be a core PDF font. Anything else silently maps to a fallback (e.g. `Helvetica`→Calibri for the DOCX output) — using a non-core name doesn't error, it just quietly renders as the fallback, so stick to the three above |
| `accent` | hex color, e.g. `"#1A1A1A"` | headings/name color; keep dark enough to scan/print cleanly |
| `heading` | `rule` / `plain` / `caps` | section heading style |
| `name_size` / `body_size` | point size (float) | |
| `columns` | `1` for ATS-safe (always forced to 1 regardless of what you put here — designer templates ignore this key entirely, column layout is hardcoded in the renderer) | |

This entry alone drives the template catalog and the shared PDF/DOCX
renderer for ATS-safe templates — no rendering code, just data.

### 2. Renderer

For an ATS-safe template, reuse the single-column reference renderer (matches what gets downloaded):

```jsx
my_template: {
  name: "My Template", ats_safe: true,
  render: (cv) => <SingleColumn cv={cv} accent="#1A1A1A" font="Helvetica, Arial, sans-serif"
                                heading="rule" nameSize={26} />,
},
```

For a designer template, reuse the sidebar reference renderer (2-column, colored sidebar):

```jsx
my_designer: {
  name: "My Designer (Designer)", ats_safe: false,
  render: (cv) => <Sidebar cv={cv} accent="#0EA5E9" sidebarBg="#0EA5E9" sidebarFg="#fff"
                           font="Inter, system-ui, sans-serif" />,
},
```

`render` is the whole contract: a function `(cv: CVData) => JSX.Element`,
given the exact object shape documented above.

### 3. Building a brand-new layout (not just new colors/fonts)

If neither reference renderer's structure fits, write a new render function
following the same shape as those two:

```jsx
import { Page, contactBits, hasSkills } from "./common";

export default function MyLayout({ cv, accent = "#1a1a1a", font = "Helvetica, Arial, sans-serif" }) {
  if (!cv) return null;               // guard: may be called before data loads
  const c = cv.contact || {};

  return (
    <Page style={{ fontFamily: font, padding: "18mm", fontSize: 11, lineHeight: 1.45 }}>
      <div style={{ fontSize: 26, fontWeight: 800, color: accent }}>{c.full_name || "—"}</div>
      <div style={{ fontSize: 10, color: "#555" }}>{contactBits(c).join("   |   ")}</div>

      {cv.summary && <p>{cv.summary}</p>}

      {hasSkills(cv) && Object.entries(cv.skills).map(([cat, items]) => (
        <div key={cat}><strong>{cat}:</strong> {(items || []).join(", ")}</div>
      ))}

      {cv.experience?.length > 0 && cv.experience.map((e, i) => (
        <div key={i}>
          <strong>{e.title}{e.company ? `, ${e.company}` : ""}</strong>
          <span>{[e.start, e.end].filter(Boolean).join(" – ")}</span>
          <ul>{(e.bullets || []).map((b, j) => <li key={j}>{b}</li>)}</ul>
        </div>
      ))}
      {/* ...projects / education / certifications / awards / languages, same pattern */}
    </Page>
  );
}
```

Hard rules for any new renderer (all come from how print/preview actually works — breaking them breaks the download or the preview, not just looks):

- **Inline styles only, no utility CSS classes, no dark-theme awareness.** Templates render on a white page for print-to-PDF and the live preview — they must look identical regardless of the app's own theme. Every reference renderer does 100% inline `style={{...}}`.
- **Wrap the whole thing in `Page`** — it sets the `210mm` A4 width/height every renderer and the print stylesheet assumes.
- **Guard every optional field.** `cv.experience?.length > 0`, `hasSkills(cv)`, etc. — an empty CV must render without crashing (this is exactly what the free sample-data preview exercises, but real user CVs will have gaps too).
- **`contactBits(c)`** returns the non-empty contact fields already filtered and ready to join — use it instead of hand-rolling the same filter.
- If ATS-safe, keep the layout single-column and close to the single-column reference structure — the point of ATS-safe is that it matches what actually gets downloaded; a wildly different on-screen layout for an ATS-safe id would mislead the user about what they're going to download.

### That's it

No other part of the system needs to know about the new id. The catalog and
renderer feed everything that shows templates: the template picker (shown
before and after generating a CV), the free preview gallery, and the template
catalog endpoint.

## Testing a new template

1. Add both entries above (three if you wrote a new renderer).
2. Open the free preview gallery — confirms the render works against sample
   data, free, no credits, and catches any crash on missing/empty fields immediately.
3. Generate a real CV once with the new template id and download both PDF and
   DOCX — the two output formats are separate render paths, check both if ATS-safe.

## Gotcha: the catalog and renderer are not validated against each other

Nothing enforces that a catalog id has a matching renderer entry, or vice
versa — no test, no build check, no runtime error. A mismatch (typo, or added
one side and forgot the other) fails **silently**: both sides independently
fall back to the default template for any unknown id.

So a broken new template doesn't error — it just quietly renders as the
default everywhere, which is easy to mistake for "it worked." After adding a
template, explicitly confirm the *new* id shows up distinctly in the preview
gallery and in the template catalog response — don't just confirm nothing crashed.

## Appendix: reference implementations

Paste these into context (or point an AI at them) if generating templates —
the prose contract above is a summary, this is ground truth.

Shared helpers used by every renderer:

```jsx
// Shared helpers for print/preview CV templates. Templates use inline styles so
// they render identically on a white page regardless of the app's (dark) theme,
// which is what we want for print-to-PDF and for the small live preview.

export const contactBits = (c = {}) =>
  [c.email, c.phone, c.location, c.linkedin, c.github, c.website].filter(Boolean);

// section presence helpers keep templates tidy
export const hasSkills = (cv) => cv?.skills && Object.keys(cv.skills).length > 0;

// A4-ish page frame used by every template's print view.
export function Page({ children, style }) {
  return (
    <div
      style={{
        width: "210mm",
        minHeight: "297mm",
        margin: "0 auto",
        background: "#fff",
        color: "#1a1a1a",
        boxSizing: "border-box",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
```

Reference renderer — single-column, ATS-safe (the actual full one with every section; `MyLayout` above is trimmed for readability):

```jsx
import { Page, contactBits, hasSkills } from "./common";

// ATS-safe single-column template, parameterized by accent colour, font family and
// heading style. Mirrors the pure backend PDF/DOCX render so the on-screen
// preview matches the downloaded file.
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
```

Reference renderer — sidebar, designer (2-column):

```jsx
import { Page, contactBits, hasSkills } from "./common";

// Designer two-column template with a coloured sidebar (contact + skills + education)
// and a roomy main column. NOT ATS-safe — used only for the on-screen designer preview
// and print-to-PDF.
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
```
