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


def tailor_cv(base_cv: dict, job_description: str) -> tuple[str, str]:
    system = (
        "You are an expert resume writer producing an ATS-optimised, single-column CV tailored to a specific job. "
        "Select and prioritise the most relevant experience, projects and skills from the candidate's master CV. "
        "Mirror the job description's keywords and terminology where the candidate genuinely has the skill. "
        "Rewrite bullets in strong action-verb + impact form, quantified where the source supports it. "
        "Keep it concise (most relevant experience first, trim irrelevant items). " + NO_FABRICATION + " Output JSON only."
    )
    user = (
        f"{CV_SCHEMA_HINT}\n\nCandidate master CV JSON:\n{json.dumps(base_cv, ensure_ascii=False)}\n\n"
        f"Target job description:\n\"\"\"\n{job_description}\n\"\"\"\n\n"
        "Produce the tailored CV JSON."
    )
    return system, user


def cover_letter(tailored_cv: dict, job_description: str, company: str, job_title: str) -> tuple[str, str]:
    system = (
        "You write cover letters that read as genuinely human-written: natural, specific, confident but not "
        "boastful, no clichés ('I am writing to express my interest', 'team player', 'fast-paced environment'), "
        "no em-dash overuse, varied sentence length. 3-4 short paragraphs. Tie concrete achievements to the role. "
        + NO_FABRICATION + " Output plain text only, no markdown."
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
