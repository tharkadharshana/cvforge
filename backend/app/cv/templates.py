"""CV template catalog — the single source of truth for the render library.

A template never changes the CV *data* (schemas.CVData); it only changes how that
data is presented. Each entry is a set of style tokens the renderers read.

Two kinds of template:

* ``ats_safe=True``  — rendered by the pure-Python backend renderers (cv/render.py)
  into single-column, parseable PDF/DOCX. These feed the ATS critic and the file the
  user uploads to job sites. They only vary fonts/colours/spacing, so they stay safe.
* ``ats_safe=False`` — "designer" templates (sidebars, colour blocks, photo). These are
  rendered on the client (React + print-to-PDF) for humans to look at; they are NOT used
  for scoring, and the backend falls back to the ATS-safe style for the scored/download file.

The frontend template registry (frontend/src/templates/registry.js) mirrors these ids so
the picker, preview and print view all agree on what "aurora" or "ats_modern" means.
"""
from __future__ import annotations

# Style tokens consumed by cv/render.py for ats_safe templates:
#   font        - base font family name (must be a core PDF font for fpdf: Helvetica/Times/Courier)
#   accent      - hex colour for headings/name (kept dark enough to print/scan cleanly)
#   heading     - "rule" (underline rule under heading) | "plain" | "caps"
#   name_size   - point size of the candidate name
#   body_size   - point size of body text
#   columns     - 1 (always 1 for ats_safe; designer templates may use 2 on the client)
TEMPLATES: dict[str, dict] = {
    "ats_classic": {
        "name": "ATS Classic",
        "ats_safe": True,
        "description": "Clean single-column layout. The safest choice for applicant tracking systems.",
        "style": {"font": "Helvetica", "accent": "#1A1A1A", "heading": "rule",
                  "name_size": 18, "body_size": 10.5, "columns": 1},
    },
    "ats_modern": {
        "name": "ATS Modern",
        "ats_safe": True,
        "description": "Same ATS-safe structure with a subtle accent colour and lighter headings.",
        "style": {"font": "Helvetica", "accent": "#0B6E4F", "heading": "caps",
                  "name_size": 20, "body_size": 10.5, "columns": 1},
    },
    "ats_serif": {
        "name": "ATS Serif",
        "ats_safe": True,
        "description": "Traditional serif type, ATS-safe. Good for academic and formal roles.",
        "style": {"font": "Times", "accent": "#1A1A1A", "heading": "rule",
                  "name_size": 19, "body_size": 11, "columns": 1},
    },
    "aurora": {
        "name": "Aurora (Designer)",
        "ats_safe": False,
        "description": "Two-column layout with a coloured sidebar. Great for humans, may parse poorly in some ATS.",
        "style": {"font": "Inter", "accent": "#4F46E5", "heading": "sidebar",
                  "name_size": 26, "body_size": 11, "columns": 2, "sidebar": "left"},
    },
    "sidebar_pro": {
        "name": "Sidebar Pro (Designer)",
        "ats_safe": False,
        "description": "Dark sidebar with contact + skills, roomy main column. Designer look for sharing/printing.",
        "style": {"font": "Inter", "accent": "#0F172A", "heading": "sidebar",
                  "name_size": 28, "body_size": 11, "columns": 2, "sidebar": "left"},
    },
}

DEFAULT_TEMPLATE_ID = "ats_classic"


def get_template(template_id: str | None) -> dict:
    """Return a template definition, falling back to the default for unknown ids."""
    return TEMPLATES.get(template_id or "", TEMPLATES[DEFAULT_TEMPLATE_ID])


def resolve_style(template_id: str | None, overrides: dict | None = None) -> dict:
    """Style tokens for the *ATS-safe* render of a given template.

    Designer (non-ats_safe) templates are never rendered by the backend, so for the
    scored/downloaded file we fall back to the default ATS-safe style. User overrides
    (e.g. a custom accent colour) are layered on top.
    """
    tpl = get_template(template_id)
    base = TEMPLATES[DEFAULT_TEMPLATE_ID]["style"]
    style = dict(base)
    if tpl.get("ats_safe"):
        style.update(tpl["style"])
    # keep ATS-safe files single-column regardless of the template's columns hint
    style["columns"] = 1
    if overrides:
        # only allow known style keys through
        for k in ("font", "accent", "heading", "name_size", "body_size"):
            if k in overrides:
                style[k] = overrides[k]
    return style


def catalog() -> list[dict]:
    """Public, ordered catalog for the /templates endpoint and the frontend picker."""
    return [
        {"id": tid, "name": t["name"], "ats_safe": t["ats_safe"],
         "description": t["description"], "style": t["style"]}
        for tid, t in TEMPLATES.items()
    ]
