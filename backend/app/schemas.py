from __future__ import annotations
import typing
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, model_validator


class CoerceModel(BaseModel):
    """Tolerate LLM output that sends null for fields we expect as str/list/dict."""

    @model_validator(mode="before")
    @classmethod
    def _coerce_none(cls, data):
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for name, field in cls.model_fields.items():
            if name not in out:
                continue
            ann = field.annotation
            origin = typing.get_origin(ann)
            val = out[name]
            if val is None:
                if ann is str:
                    out[name] = ""
                elif origin in (list, typing.List):
                    out[name] = []
                elif origin in (dict, typing.Dict):
                    out[name] = {}
            elif origin in (dict, typing.Dict) and isinstance(val, dict):
                # e.g. skills: {"Languages": null} -> []
                out[name] = {k: ([] if v is None else v) for k, v in val.items()}
            elif origin in (list, typing.List) and isinstance(val, list):
                args = typing.get_args(ann)
                if args and args[0] is str:
                    out[name] = [x for x in val if x is not None]
        return out


# ---------- structured CV shape (the canonical base CV format) ----------
class Contact(CoerceModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""


class Experience(CoerceModel):
    title: str = ""
    company: str = ""
    location: str = ""
    start: str = ""          # "Jan 2023"
    end: str = ""            # "Present"
    bullets: list[str] = []  # achievement bullets


class Education(CoerceModel):
    degree: str = ""
    institution: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    details: list[str] = []


class Project(CoerceModel):
    name: str = ""
    description: str = ""
    tech: list[str] = []
    bullets: list[str] = []
    link: str = ""


class CVData(CoerceModel):
    contact: Contact = Field(default_factory=Contact)
    summary: str = ""
    skills: dict[str, list[str]] = {}   # category -> skills, e.g. {"Languages": ["Python","Go"]}
    experience: list[Experience] = []
    projects: list[Project] = []
    education: list[Education] = []
    certifications: list[str] = []
    awards: list[str] = []
    languages: list[str] = []


# ---------- auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- cv ----------
class BaseCVOut(BaseModel):
    data: CVData
    updated_at: Optional[str] = None


class AddQualificationIn(BaseModel):
    # free text the user dumps; LLM slots it into the right section of base CV
    text: str = Field(min_length=3)


class BuildIn(BaseModel):
    # questionnaire answers: field name -> answer (string, list, or nested)
    answers: dict[str, object]


class CVStatus(BaseModel):
    has_base_cv: bool
    experience_count: int = 0
    education_count: int = 0
    project_count: int = 0
    skill_categories: int = 0


# ---------- billing ----------
class PlanOut(BaseModel):
    id: str
    name: str
    price_usd: float
    credits: int
    recurring: bool = False
    available: bool = False          # true when a Polar product is configured
    price_per_credit: float = 0.0
    margin_pct: float = 0.0
    min_ats_score: int = 0           # guaranteed minimum ATS score (0 = no guarantee)


class BillingSummary(BaseModel):
    billing_enabled: bool
    plan: str
    credits: int
    free_tier_mode: str
    credits_per_generation: int
    has_customer: bool = False
    plans: list[PlanOut] = []


class LedgerRow(BaseModel):
    delta: int
    reason: str
    balance_after: int
    created_at: str


class BillingOverview(BaseModel):
    summary: BillingSummary
    ledger: list[LedgerRow] = []


class CheckoutOut(BaseModel):
    checkout_url: str


class FetchUrlIn(BaseModel):
    url: str


class FetchUrlOut(BaseModel):
    title: str = ""
    text: str


# ---------- generation ----------
class GenerateIn(BaseModel):
    job_description: str = Field(min_length=20)
    job_title: str = ""
    company: str = ""


class CritiqueOut(BaseModel):
    ats_score: int
    keyword_matches: list[str] = []
    missing_keywords: list[str] = []
    human_tone_notes: list[str] = []
    suggestions: list[str] = []
    target_ats_score: int = 0
    meets_ats_guarantee: bool = True
    ats_iterations: int = 1


class GenerateOut(BaseModel):
    application_id: int
    tailored_cv: CVData
    cover_letter: str
    critique: CritiqueOut


# ---------- generation jobs (per-step pipeline) ----------
class GenerateStartOut(BaseModel):
    job_id: int
    status: str


class GenerateTailorOut(BaseModel):
    job_id: int
    status: str
    tailored_cv: CVData


class GenerateCoverOut(BaseModel):
    job_id: int
    status: str
    cover_letter: str


class GenerateCritiqueOut(BaseModel):
    job_id: int
    status: str
    application_id: int
    critique: CritiqueOut
    ats_score: int


class GenerateJobOut(BaseModel):
    job_id: int
    status: str
    job_title: str = ""
    company: str = ""
    tailored_cv: Optional[CVData] = None
    cover_letter: Optional[str] = None
    critique: Optional[CritiqueOut] = None
    ats_score: Optional[int] = None
    error: Optional[str] = None


# ---------- manual editing & templates ----------
class ApplicationPatchIn(BaseModel):
    """Partial update of an application. Any field left None is untouched.

    Editing ``tailored_cv`` marks the ATS score stale (the stored score no longer
    reflects the CV) until the user re-evaluates. Setting only template fields does
    not affect the score.
    """
    tailored_cv: Optional[CVData] = None
    cover_letter: Optional[str] = None
    template_id: Optional[str] = None
    template_overrides: Optional[dict] = None


class ApplicationOut(BaseModel):
    id: int
    job_title: str = ""
    company: str = ""
    tailored_cv: Optional[CVData] = None
    cover_letter: Optional[str] = None
    ats_score: Optional[int] = None
    critique: Optional[CritiqueOut] = None
    ats_stale: bool = False
    template_id: str = "ats_classic"
    template_overrides: Optional[dict] = None
    status: str
