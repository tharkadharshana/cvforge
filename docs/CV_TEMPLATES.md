# CV Templates

Two files, both required, ids must match between them. Source of truth:
`app/cv/templates.py` (backend) and `frontend/src/templates/registry.jsx` (frontend).

## Two kinds of template

- **ATS-safe** (`ats_safe: True`): single-column, rendered by the pure-Python
  backend (`cv/render.py`) into the actual downloadable PDF/DOCX. This is what
  the ATS critic scores and what gets uploaded to job sites. Only fonts/colors/
  spacing vary — structure never changes, so it stays parseable.
- **Designer** (`ats_safe: False`): sidebars, color blocks, 2-column layouts —
  rendered client-side only (React + print-to-PDF), for a human to look at.
  Never scored, never downloaded as the "ATS" file — the backend silently
  falls back to the default ATS-safe style for the scored/download copy
  regardless of which designer template is selected on screen.

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

Style keys the renderer reads:

| key | values | notes |
|---|---|---|
| `font` | `Helvetica` / `Times` / `Courier` | must be a core PDF font — `fpdf2` can't embed arbitrary fonts |
| `accent` | hex color | headings/name color; keep dark enough to scan/print cleanly |
| `heading` | `rule` / `plain` / `caps` | section heading style |
| `name_size` / `body_size` | point size | |
| `columns` | `1` for `ats_safe` (always), designer templates may use `2` client-side |

This entry alone drives the `/generate/templates` catalog and the backend PDF/DOCX
renderer — but only takes effect for the scored/downloaded file if `ats_safe: True`.

### 2. `frontend/src/templates/registry.jsx` — mirror the same id

```jsx
my_template: {
  name: "My Template", ats_safe: true,
  render: (cv) => <SingleColumn cv={cv} accent="#1A1A1A" font="Helvetica, Arial, sans-serif"
                                heading="rule" nameSize={26} />,
},
```

Reuse `SingleColumn` (1-column, mirrors the ATS-safe backend render) or `Sidebar`
(2-column, designer) — both live in `frontend/src/templates/`. If neither layout
fits, add a new component there following the same `(cv, accent, font, ...)` prop
pattern as the existing two.

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

1. Add both entries above.
2. Run the frontend (`npm run dev`) and open `/templates` — confirms the render
   works against sample data, free, no credits.
3. Generate a real CV once with the new `template_id` and download both PDF and
   DOCX (`cv/render.py`'s two renderers are separate code paths — check both if
   `ats_safe: True`).
