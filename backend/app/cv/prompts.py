from __future__ import annotations
import json

CV_SCHEMA_HINT = """Return JSON matching exactly this shape (omit empty fields is OK, never invent facts):
{
  "contact": {"full_name","email","phone","location","linkedin","github","website"},
  "summary": "string",
  "skills": {"Category": ["skill", ...]},
  "experience": [{"title","company","location","start","end","bullets":["..."]}],
  "projects": [{"name","description","tech":["..."],"bullets":["..."],"link"}],
  "education": [{"degree","institution","location","start","end","details":["..."]}],
  "certifications": ["..."],
  "awards": ["..."],
  "languages": ["..."]
}"""

NO_FABRICATION = (
    "CRITICAL: never invent employers, dates, degrees, metrics, or skills not present in the source. "
    "You may rephrase, reorder, emphasise, and quantify ONLY what is supported. Fabrication disqualifies the candidate."
)


def parse_base_cv(raw_cv_text: str) -> tuple[str, str]:
    system = (
        "You convert a raw CV/resume into clean structured JSON. " + NO_FABRICATION + " Output JSON only."
    )
    user = f"{CV_SCHEMA_HINT}\n\nRaw CV text:\n\"\"\"\n{raw_cv_text}\n\"\"\""
    return system, user


def add_qualification(current_cv: dict, new_text: str) -> tuple[str, str]:
    system = (
        "You merge a new qualification/experience/skill into an existing structured CV JSON. "
        "Place it in the correct section. Keep all existing content. Deduplicate. " + NO_FABRICATION + " Output the FULL updated JSON only."
    )
    user = (
        f"{CV_SCHEMA_HINT}\n\nExisting CV JSON:\n{json.dumps(current_cv, ensure_ascii=False)}\n\n"
        f"New information to incorporate:\n\"\"\"\n{new_text}\n\"\"\""
    )
    return system, user


def build_from_answers(answers: dict) -> tuple[str, str]:
    system = (
        "You build a polished, professional, ATS-friendly CV from a candidate's questionnaire answers. "
        "Turn plain answers into strong action-verb achievement bullets. Write a crisp professional summary. "
        "Organise skills into sensible categories. " + NO_FABRICATION + " Output JSON only."
    )
    user = (
        f"{CV_SCHEMA_HINT}\n\nQuestionnaire answers (field -> answer):\n"
        f"{json.dumps(answers, ensure_ascii=False, indent=2)}\n\nProduce the CV JSON."
    )
    return system, user


def _style_block(style: dict | None) -> str:
    """Format a user's declared writing-style preferences for splicing into a system prompt.

    Returns "" when the profile is empty so callers can unconditionally append it.
    """
    if not style:
        return ""
    tone = style.get("tone") or ""
    dos = style.get("dos") or []
    donts = style.get("donts") or []
    avoid = style.get("avoid_phrases") or []
    if not (tone or dos or donts or avoid):
        return ""
    parts = []
    if tone:
        parts.append(f"tone={tone}")
    if dos:
        parts.append("always: " + "; ".join(dos))
    if donts:
        parts.append("never: " + "; ".join(donts))
    if avoid:
        parts.append("avoid these phrases entirely: " + ", ".join(avoid))
    return " Writing style rules (follow strictly): " + "; ".join(parts) + "."


def _fit_block(fit: dict | None) -> str:
    """Format a job-fit evaluation's strengths/gaps for splicing into a system prompt."""
    if not fit:
        return ""
    strengths = fit.get("strengths") or []
    gaps = fit.get("gaps") or []
    if not (strengths or gaps):
        return ""
    parts = []
    if strengths:
        parts.append("lean into: " + "; ".join(strengths))
    if gaps:
        parts.append("the role also needs (address only where genuinely supported by the source, never fabricate): " + "; ".join(gaps))
    return " Fit analysis: " + "; ".join(parts) + "."


def tailor_cv(base_cv: dict, job_description: str, style: dict | None = None, fit: dict | None = None) -> tuple[str, str]:
    system = (
        "You are an expert resume writer producing an ATS-optimised, single-column CV tailored to a specific job. "
        "Select and prioritise the most relevant experience, projects and skills from the candidate's master CV. "
        "Mirror the job description's keywords and terminology where the candidate genuinely has the skill. "
        "Rewrite bullets in strong action-verb + impact form, quantified where the source supports it. "
        "Keep it concise (most relevant experience first, trim irrelevant items). " + NO_FABRICATION + " Output JSON only."
        + _style_block(style) + _fit_block(fit)
    )
    user = (
        f"{CV_SCHEMA_HINT}\n\nCandidate master CV JSON:\n{json.dumps(base_cv, ensure_ascii=False)}\n\n"
        f"Target job description:\n\"\"\"\n{job_description}\n\"\"\"\n\n"
        "Produce the tailored CV JSON."
    )
    return system, user


def cover_letter(tailored_cv: dict, job_description: str, company: str, job_title: str,
                  style: dict | None = None, fit: dict | None = None) -> tuple[str, str]:
    system = (
        "You write cover letters that read as genuinely human-written: natural, specific, confident but not "
        "boastful, no clichés ('I am writing to express my interest', 'team player', 'fast-paced environment'), "
        "no em-dash overuse, varied sentence length. 3-4 short paragraphs. Tie concrete achievements to the role. "
        + NO_FABRICATION + " Output plain text only, no markdown."
        + _style_block(style) + _fit_block(fit)
    )
    user = (
        f"Candidate (tailored) CV JSON:\n{json.dumps(tailored_cv, ensure_ascii=False)}\n\n"
        f"Company: {company or 'the company'}\nRole: {job_title or 'the role'}\n\n"
        f"Job description:\n\"\"\"\n{job_description}\n\"\"\"\n\nWrite the cover letter."
    )
    return system, user


def improve_cv(base_cv: dict, job_description: str, previous_cv: dict, critique: dict) -> tuple[str, str]:
    system = (
        "You are an expert resume writer revising an ATS-tailored CV based on a critic's feedback. "
        "Address the missing keywords and suggestions where the candidate genuinely has the underlying "
        "skill or experience in their master CV — work it into relevant bullets/skills naturally. "
        "Keep everything that already works. " + NO_FABRICATION + " Output JSON only."
    )
    user = (
        f"{CV_SCHEMA_HINT}\n\nCandidate master CV JSON (source of truth, never go beyond this):\n"
        f"{json.dumps(base_cv, ensure_ascii=False)}\n\n"
        f"Previous tailored CV JSON:\n{json.dumps(previous_cv, ensure_ascii=False)}\n\n"
        f"Target job description:\n\"\"\"\n{job_description}\"\"\"\n\n"
        "Critic feedback to address:\n"
        f"Missing keywords: {json.dumps(critique.get('missing_keywords', []), ensure_ascii=False)}\n"
        f"Suggestions: {json.dumps(critique.get('suggestions', []), ensure_ascii=False)}\n\n"
        "Produce an improved tailored CV JSON."
    )
    return system, user


def improve_cover_letter(tailored_cv: dict, previous_letter: str, job_description: str,
                          company: str, job_title: str, critique: dict) -> tuple[str, str]:
    system = (
        "You revise a cover letter based on critic feedback, keeping it genuinely human-written: natural, "
        "specific, confident but not boastful, no clichés ('I am writing to express my interest', "
        "'team player', 'fast-paced environment'), no em-dash overuse, varied sentence length. "
        "3-4 short paragraphs. " + NO_FABRICATION + " Output plain text only, no markdown."
    )
    user = (
        f"Candidate (tailored) CV JSON:\n{json.dumps(tailored_cv, ensure_ascii=False)}\n\n"
        f"Company: {company or 'the company'}\nRole: {job_title or 'the role'}\n\n"
        f"Job description:\n\"\"\"\n{job_description}\"\"\"\n\n"
        f"Previous cover letter:\n\"\"\"\n{previous_letter}\"\"\"\n\n"
        "Tone notes to address: " + json.dumps(critique.get("human_tone_notes", []), ensure_ascii=False) + "\n"
        "Suggestions to address: " + json.dumps(critique.get("suggestions", []), ensure_ascii=False) + "\n\n"
        "Write the improved cover letter."
    )
    return system, user


def ats_check(cv_text: str, job_description: str = "") -> tuple[str, str]:
    """Standalone ATS audit of raw resume text (public checker, no account needed)."""
    system = (
        "You are a strict ATS auditor and senior recruiter. Audit the resume text the way an "
        "applicant tracking system plus a critical human screener would. Score each category "
        "0-100 (100 = perfect). Report concrete issues found. Be specific and critical, "
        "never generic. Output JSON only."
    )
    jd_part = (
        f"\n\nTarget job description (score 'tailoring' against it):\n\"\"\"\n{job_description}\n\"\"\""
        if job_description.strip() else
        "\n\nNo job description provided: set \"tailoring\" to null and do not report tailoring issues."
    )
    user = (
        "Return JSON exactly:\n"
        "{\"ats_score\": int 0-100 overall,\n"
        " \"parse_rate\": int 0-100 (how cleanly an ATS parses this text: structure, ordering, contact info, section headers),\n"
        " \"categories\": {\"sections\": int, \"ats_essentials\": int, \"hr_red_flags\": int, "
        "\"discrimination\": int, \"seniority\": int, \"tailoring\": int|null},\n"
        " \"issues\": [{\"category\": one of the category keys, \"severity\": \"high\"|\"medium\"|\"low\", "
        "\"title\": short issue name, \"fix\": 2-4 sentences of concrete, actionable instructions to fix it}]}\n\n"
        "Category meanings: sections = presence/quality of expected resume sections; "
        "ats_essentials = contact info, standard headers, parseable dates, keyword-friendly wording; "
        "hr_red_flags = gaps, job hopping, vague bullets, missing metrics; "
        "discrimination = info that invites bias (age, photo, marital status, etc.); "
        "seniority = whether content signals a clear seniority level; "
        "tailoring = keyword match against the job description."
        f"{jd_part}\n\nResume text:\n\"\"\"\n{cv_text}\n\"\"\""
    )
    return system, user


def fit_score(base_cv: dict, job_description: str) -> tuple[str, str]:
    """Score a job description against the candidate's master CV, pre-generation.

    Rubric adapted from github.com/MadsLorentzen/ai-job-search's job-evaluation skill:
    5 weighted dimensions, deal-breakers cap the score, always surface gaps honestly.
    """
    system = (
        "You are a strict, honest career advisor evaluating whether a candidate should apply to a job. "
        "Score across 5 weighted dimensions and never hide genuine gaps to make a job look better. "
        "Output JSON only."
    )
    user = (
        "Return JSON exactly:\n"
        "{\"score\": int 0-100 overall weighted score,\n"
        " \"dimensions\": {\"skills_match\": int, \"experience_level\": int, \"culture_fit\": int, "
        "\"location\": int, \"career_alignment\": int},\n"
        " \"deal_breakers\": [\"hard requirements the candidate cannot meet\"],\n"
        " \"strengths\": [\"top reasons this is a good fit\"],\n"
        " \"gaps\": [\"honest gaps — never hide these\"],\n"
        " \"recommendation\": one of \"STRONG_MATCH\"|\"GOOD_MATCH\"|\"WEAK_MATCH\"|\"SKIP\"}\n\n"
        "Weights: skills_match 0.35, experience_level 0.25, culture_fit 0.15, location 0.15, "
        "career_alignment 0.10 — weigh them holistically into the overall score. "
        "If deal_breakers is non-empty, cap the overall score at 30 and set recommendation to SKIP.\n\n"
        f"Candidate master CV JSON:\n{json.dumps(base_cv, ensure_ascii=False)}\n\n"
        f"Job description:\n\"\"\"\n{job_description}\n\"\"\""
    )
    return system, user


def critique(tailored_cv: dict, cover_letter_text: str, job_description: str) -> tuple[str, str]:
    system = (
        "You are a strict ATS auditor and hiring reviewer. Score the tailored CV against the job description. "
        "Check keyword coverage, formatting parse-ability, relevance, and whether the cover letter reads as "
        "AI-generated vs human. Be specific and critical. Output JSON only."
    )
    user = (
        "Return JSON: {\"ats_score\": int 0-100, \"keyword_matches\": [..], \"missing_keywords\": [..], "
        "\"human_tone_notes\": [..], \"suggestions\": [..]}\n\n"
        f"Tailored CV JSON:\n{json.dumps(tailored_cv, ensure_ascii=False)}\n\n"
        f"Cover letter:\n\"\"\"\n{cover_letter_text}\n\"\"\"\n\n"
        f"Job description:\n\"\"\"\n{job_description}\n\"\"\""
    )
    return system, user
