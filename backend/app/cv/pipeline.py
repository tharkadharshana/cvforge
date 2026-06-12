from __future__ import annotations
import time
from ..schemas import CVData
from ..llm.orchestrator import drafter, critic
from ..logging_config import get_logger
from . import prompts

log = get_logger("pipeline")


def _stage(name: str, fn):
    t0 = time.perf_counter()
    log.info("stage '%s' start", name)
    try:
        out = fn()
    except Exception as e:
        log.error("stage '%s' FAILED after %.0fms: %s", name, (time.perf_counter() - t0) * 1000, e)
        raise
    log.info("stage '%s' done %.0fms", name, (time.perf_counter() - t0) * 1000)
    return out


def parse_raw_cv(raw_text: str) -> CVData:
    log.info("parse_raw_cv: %d chars in", len(raw_text))
    sys, usr = prompts.parse_base_cv(raw_text)
    data = _stage("parse_cv", lambda: drafter().complete_json(sys, usr))
    cv = CVData.model_validate(data)
    log.info("parse_raw_cv: parsed exp=%d edu=%d proj=%d skills=%d",
             len(cv.experience), len(cv.education), len(cv.projects), len(cv.skills))
    return cv


def build_from_answers(answers: dict) -> CVData:
    log.info("build_from_answers: %d fields", len(answers))
    sys, usr = prompts.build_from_answers(answers)
    data = _stage("build_cv", lambda: drafter().complete_json(sys, usr, pro=True))
    return CVData.model_validate(data)


def merge_qualification(current: CVData, new_text: str) -> CVData:
    log.info("merge_qualification: %d chars", len(new_text))
    sys, usr = prompts.add_qualification(current.model_dump(), new_text)
    data = _stage("merge_qual", lambda: drafter().complete_json(sys, usr))
    return CVData.model_validate(data)


def generate_application(base_cv: CVData, job_description: str, company: str, job_title: str):
    log.info("generate_application: company=%r title=%r jd_chars=%d",
             company, job_title, len(job_description))
    base = base_cv.model_dump()

    def _tailor():
        sys, usr = prompts.tailor_cv(base, job_description)
        return CVData.model_validate(drafter().complete_json(sys, usr, pro=True))
    tailored = _stage("tailor_cv", _tailor)

    def _cover():
        sys, usr = prompts.cover_letter(tailored.model_dump(), job_description, company, job_title)
        return drafter().complete(sys, usr).strip()
    cover = _stage("cover_letter", _cover)

    def _crit():
        sys, usr = prompts.critique(tailored.model_dump(), cover, job_description)
        return critic().complete_json(sys, usr)
    crit = _stage("critique", _crit)

    for k, d in (("ats_score", 0), ("keyword_matches", []), ("missing_keywords", []),
                 ("human_tone_notes", []), ("suggestions", [])):
        crit.setdefault(k, d)
    log.info("generate_application: done ats_score=%s", crit.get("ats_score"))
    return tailored, cover, crit


def annotate_ats_guarantee(crit: dict, min_ats_score: int, iterations: int = 1) -> dict:
    crit["target_ats_score"] = min_ats_score
    crit["meets_ats_guarantee"] = crit.get("ats_score", 0) >= min_ats_score
    crit["ats_iterations"] = iterations
    return crit


def generate_application_guaranteed(base_cv: CVData, job_description: str, company: str, job_title: str,
                                      min_ats_score: int = 0, max_iterations: int = 3):
    """Like generate_application, but if the critique score is below
    min_ats_score, re-runs the improve pass (re-tailor + re-critique) until
    it meets the target or max_iterations is reached."""
    tailored, cover, crit = generate_application(base_cv, job_description, company, job_title)
    iterations = 1
    while crit.get("ats_score", 0) < min_ats_score and iterations < max_iterations:
        log.info("ats guarantee: score=%s below target=%s, retrying (%d/%d)",
                 crit.get("ats_score"), min_ats_score, iterations + 1, max_iterations)
        tailored, cover, crit = improve_application(
            base_cv, tailored, cover, crit, job_description, company, job_title
        )
        iterations += 1
    annotate_ats_guarantee(crit, min_ats_score, iterations)
    return tailored, cover, crit


def improve_application(base_cv: CVData, tailored_cv: CVData, cover_letter_text: str, critique: dict,
                         job_description: str, company: str, job_title: str):
    log.info("improve_application: company=%r title=%r prev_score=%s",
             company, job_title, critique.get("ats_score"))
    base = base_cv.model_dump()
    prev_cv = tailored_cv.model_dump()

    def _tailor():
        sys, usr = prompts.improve_cv(base, job_description, prev_cv, critique)
        return CVData.model_validate(drafter().complete_json(sys, usr, pro=True))
    tailored = _stage("improve_tailor_cv", _tailor)

    def _cover():
        sys, usr = prompts.improve_cover_letter(tailored.model_dump(), cover_letter_text, job_description, company, job_title, critique)
        return drafter().complete(sys, usr).strip()
    cover = _stage("improve_cover_letter", _cover)

    def _crit():
        sys, usr = prompts.critique(tailored.model_dump(), cover, job_description)
        return critic().complete_json(sys, usr)
    crit = _stage("critique", _crit)

    for k, d in (("ats_score", 0), ("keyword_matches", []), ("missing_keywords", []),
                 ("human_tone_notes", []), ("suggestions", [])):
        crit.setdefault(k, d)
    log.info("improve_application: done ats_score=%s", crit.get("ats_score"))
    return tailored, cover, crit
