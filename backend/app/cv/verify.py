from __future__ import annotations
import re
from .extract import _from_pdf
from ..schemas import CVData

# Fixed heading order emitted by render.render_pdf — a regression here means the
# rendered PDF's text layer is scrambling reading order (e.g. a broken column flow).
_SECTION_ORDER = ["SUMMARY", "SKILLS", "EXPERIENCE", "PROJECTS", "EDUCATION",
                   "CERTIFICATIONS", "AWARDS", "LANGUAGES"]

_GARBLED_RE = re.compile(r"[�]")


def verify_text_layer(pdf_bytes: bytes, cv: CVData) -> dict:
    """Deterministic check that CVForge's own rendered PDF has a clean, machine-readable
    text layer: no pdfplumber-visible replacement chars, contact details present as
    literal text, and section headings still appear in the order render_pdf emits them.

    Pure stdlib + pdfplumber (already a dependency) — no LLM call, no poppler/pdftotext.
    """
    text = _from_pdf(pdf_bytes)
    issues = []

    c = cv.contact
    if c.email and c.email not in text:
        issues.append("Email not found as literal text in the rendered PDF")
    if c.phone and c.phone not in text:
        issues.append("Phone number not found as literal text in the rendered PDF")
    if c.full_name and c.full_name not in text:
        issues.append("Full name not found as literal text in the rendered PDF")

    if _GARBLED_RE.search(text):
        issues.append("Garbled/unrenderable characters found in the extracted text")

    present = [h for h in _SECTION_ORDER if h in text]
    positions = [text.index(h) for h in present]
    if positions != sorted(positions):
        issues.append("Section reading order is out of sequence in the extracted text")

    return {"machine_readable": len(issues) == 0, "issues": issues}
