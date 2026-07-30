# CV Templates

Two files, both required, ids must match between them. Source of truth:
`app/cv/templates.py` (backend) and `frontend/src/templates/registry.jsx` (frontend).

## The data contract: `CVData`

Every template renders the same shape, always — this is the one structure you
need to know, defined in `backend/app/schemas.py`. All fields have defaults
(empty string / empty list / `{}`), so a template must handle any field being
empty, never assume it's populated.

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
- Every list field can be empty — guard every section with `.length > 0` (see any existing template).
- This is the exact object both the backend PDF/DOCX renderer and every frontend template receive. There is no separate "preview data" format — `frontend/src/templates/sampleCv.js` is just a hand-written example of this same shape, used by `/templates` for the zero-cost gallery.

## Two kinds of template

- **ATS-safe** (`ats_safe: True`): single-column, rendered by the pure-Python
  backend (`cv/render.py`) into the actual downloadable PDF/DOCX. This is what
  the ATS critic scores and what gets uploaded to job sites. **You do not write
  any backend rendering code for these** — `cv/render.py` has one shared
  PDF renderer and one shared DOCX renderer for *all* ats_safe templates; a new
  template only ever contributes a `style` dict (see below), never new render logic.
- **Designer** (`ats_safe: False`): sidebars, color blocks, 2-column layouts —
  rendered client-side only (React + print-to-PDF), for a human to look at.
  Never scored, never downloaded as the "ATS" file — the backend silently
  falls back to the default ATS-safe style for the scored/download copy
  regardless of which designer template is selected on screen. **These do
  require a frontend React component** since there's no backend equivalent to fall back on visually.

## Adding one

### 1. `backend/app/cv/templates.py` — add to the `TEMPLATES` dict

```python
"my_template": {
    "name": "My Template",
    "ats_safe": True,   # False = designer, see above
    "description": "One line shown in the picker.",
    "style": {"font": "Helvetica", "accent": "#1A1A1A", "heading": "rule",
              "name_size": 18, "body_size": 10.5, "columns": 1},
},
```

Style keys the shared backend renderer reads:

| key | values | notes |
|---|---|---|
| `font` | `Helvetica` / `Times` / `Courier` | must be a core PDF font. Anything else silently maps to a fallback in `render.py`'s `_PDF_FONT`/`_DOCX_FONT` dicts (`Helvetica`→Calibri in docx, etc) — using a non-core name doesn't error, it just quietly renders as the fallback, so stick to the three above |
| `accent` | hex color, e.g. `"#1A1A1A"` | headings/name color; keep dark enough to scan/print cleanly |
| `heading` | `rule` / `plain` / `caps` | section heading style |
| `name_size` / `body_size` | point size (float) | |
| `columns` | `1` for `ats_safe` (always forced to 1 regardless of what you put here — designer templates ignore this key entirely, column layout is hardcoded in the React component) | |

This entry alone drives the `/generate/templates` catalog and the backend PDF/DOCX
renderer for `ats_safe: True` templates — no code, just data.

### 2. `frontend/src/templates/registry.jsx` — mirror the same id

For an ATS-safe template, reuse `SingleColumn` (matches what the backend renders):

```jsx
my_template: {
  name: "My Template", ats_safe: true,
  render: (cv) => <SingleColumn cv={cv} accent="#1A1A1A" font="Helvetica, Arial, sans-serif"
                                heading="rule" nameSize={26} />,
},
```

For a designer template, reuse `Sidebar` (2-column, colored sidebar):

```jsx
my_designer: {
  name: "My Designer (Designer)", ats_safe: false,
  render: (cv) => <Sidebar cv={cv} accent="#0EA5E9" sidebarBg="#0EA5E9" sidebarFg="#fff"
                           font="Inter, system-ui, sans-serif" />,
},
```

`render` is the whole contract: a function `(cv: CVData) => JSX.Element`, given
the exact object shape documented above. Both `SingleColumn` and `Sidebar` live
in `frontend/src/templates/`.

### 3. Building a brand-new layout (not just new colors/fonts)

If neither `SingleColumn` nor `Sidebar`'s structure fits, write a new component
in `frontend/src/templates/`, following the same shape as those two:

```jsx
import { Page, contactBits, hasSkills } from "./common";

export default function MyLayout({ cv, accent = "#1a1a1a", font = "Helvetica, Arial, sans-serif" }) {
  if (!cv) return null;               // guard: registry may call this before data loads
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

Hard rules for any new component (all come from how print/preview actually works — breaking them breaks the download or the preview, not just looks):

- **Inline styles only, no Tailwind classes, no dark-theme awareness.** Templates render on a white page for print-to-PDF (`window.print()`) and the live preview — they must look identical regardless of the app's own theme. Every existing template does 100% inline `style={{...}}`.
- **Wrap the whole thing in `<Page>`** (from `./common`) — it sets the `210mm` A4 width/height every renderer and the print CSS (`.cv-print-root` in `index.css`) assumes.
- **Guard every optional field.** `cv.experience?.length > 0`, `hasSkills(cv)`, etc. — an empty base CV must render without crashing (this is exactly what `/templates`'s sample-data gallery exercises, but real user CVs will have gaps too).
- **`contactBits(c)`** (from `./common`) returns the non-empty contact fields already filtered and ready to join — use it instead of hand-rolling the same filter.
- If `ats_safe: True`, keep the layout single-column and close to `SingleColumn`'s structure — the point of ATS-safe is that it matches what the backend actually renders into the downloaded file; a wildly different frontend layout for an `ats_safe` id would mislead the user about what they're going to download.

### That's it

No other file needs to know about the new id. These two registries feed
everything that shows templates:

- `TemplatePicker` (`frontend/src/components/TemplatePicker.jsx`) — the picker
  shown on Generate (pre-generation) and ApplicationDetail (post-generation)
- `/templates` — the free preview gallery (`frontend/src/pages/TemplateGallery.jsx`),
  renders every registry entry against a hardcoded sample CV
  (`frontend/src/templates/sampleCv.js`), no backend/LLM call
- `GET /generate/templates` — the backend catalog endpoint, built from
  `cv/templates.py::catalog()`

## Testing a new template

1. Add both entries above (three if you wrote a new component).
2. Run the frontend (`npm run dev`) and open `/templates` — confirms the render
   works against sample data, free, no credits, and catches any crash on
   missing/empty fields immediately.
3. Generate a real CV once with the new `template_id` and download both PDF and
   DOCX (`cv/render.py`'s two renderers are separate code paths — check both if
   `ats_safe: True`).
