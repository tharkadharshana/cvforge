from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    credits: Mapped[int] = mapped_column(Integer, default=0)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    polar_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    monthly_refill_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    base_cv: Mapped["BaseCV"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    ledger: Mapped[list["CreditLedger"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class BaseCV(Base):
    """Master record. Structured JSON holding everything the user has ever done/knows."""
    __tablename__ = "base_cvs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # CVData schema shape
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="base_cv")


class Application(Base):
    """One generated CV + cover letter for one job description.

    Also doubles as the generation job record: a row is created (status=pending)
    as soon as /generate/start validates the request, then filled in
    progressively by the per-step endpoints (tailor -> cover -> critique)."""
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_title: Mapped[str] = mapped_column(String(255), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    job_description: Mapped[str] = mapped_column(Text)
    tailored_cv: Mapped[dict | None] = mapped_column(JSON, nullable=True)        # tailored CVData
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    ats_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critique: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # True after the user hand-edits the tailored CV: the stored ats_score/critique
    # no longer reflect the current CV, so the UI hides the score until re-evaluated.
    ats_stale: Mapped[bool] = mapped_column(default=False)
    # chosen render template (see cv/templates.py). "ats_classic" is the default,
    # ATS-safe layout that also feeds the critic and the safe PDF/DOCX download.
    template_id: Mapped[str] = mapped_column(String(50), default="ats_classic")
    # optional per-application style tweaks (e.g. {"accent": "#0b5"}); shape is the
    # template style-token dict, applied on top of the template's defaults.
    template_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|tailored|covered|done|failed
    # job-fit evaluation (see cv/prompts.py::fit_score) computed pre-generation and
    # persisted here once a job exists, for the application history's record.
    fit_score: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    charged: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # application tracker (separate from the `status` pipeline field above).
    # not_applied|applied|screening|interview_1|interview_2|offer|hired|rejected|withdrawn|ghosted
    tracker_status: Mapped[str] = mapped_column(String(20), default="not_applied")
    tracker_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="applications")


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    delta: Mapped[int] = mapped_column(Integer)            # +granted / -spent
    reason: Mapped[str] = mapped_column(String(80))
    balance_after: Mapped[int] = mapped_column(Integer)
    ref: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="ledger")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    provider_ref: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(50))
    amount_usd: Mapped[float] = mapped_column(default=0.0)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="paid")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="payments")


class LinkedInJobCache(Base):
    """Shared cache of LinkedIn listings, keyed by LinkedIn's own job id — not
    per-user (the listing itself is public data). See app/jobs/linkedin.py."""
    __tablename__ = "linkedin_jobs_cache"

    job_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    posted_at: Mapped[str] = mapped_column(String(40), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    description_hash: Mapped[str] = mapped_column(String(64), default="")
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobSearchPreference(Base):
    __tablename__ = "job_search_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    keywords: Mapped[list] = mapped_column(JSON, default=list)   # ["backend engineer", ...]
    location: Mapped[str] = mapped_column(String(255), default="")
    experience_level: Mapped[str] = mapped_column(String(20), default="")  # see linkedin.EXPERIENCE_LEVELS
    time_filter: Mapped[str] = mapped_column(String(20), default="week")   # see linkedin.TIME_FILTERS
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobSearchResult(Base):
    """Links a user to a cached listing they've seen, so save/dismiss state is per-user
    even though the underlying listing (LinkedInJobCache) is shared."""
    __tablename__ = "job_search_results"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_search_results_user_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("linkedin_jobs_cache.job_id"), index=True)
    search_keywords: Mapped[str] = mapped_column(String(255), default="")
    saved: Mapped[bool] = mapped_column(default=False)
    dismissed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobSearchUsage(Base):
    """Per-day search count for the free-tier daily limit. Date-based, not a sliding
    window — resets at UTC midnight. Good enough at this volume."""
    __tablename__ = "job_search_usage"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_job_search_usage_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[str] = mapped_column(String(10))  # "YYYY-MM-DD", UTC
    search_count: Mapped[int] = mapped_column(Integer, default=0)


class GeminiJobCache(Base):
    """Shared cache of Gemini google_search-grounded listings, keyed by sha256(url).
    Unlike LinkedIn, the grounded search response already returns the full
    description in the search step, so there's no separate detail-fetch. Kept
    as its own table (not reusing linkedin_jobs_cache/job_search_*) so the two
    sources stay independent. See app/jobs/gemini_search.py."""
    __tablename__ = "gemini_jobs_cache"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    posted_at: Mapped[str] = mapped_column(String(40), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GeminiSearchUsage(Base):
    """Per-day search count for Gemini job search's free-tier daily limit.
    Independent counter from job_search_usage (LinkedIn's)."""
    __tablename__ = "gemini_search_usage"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_gemini_search_usage_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[str] = mapped_column(String(10))  # "YYYY-MM-DD", UTC
    search_count: Mapped[int] = mapped_column(Integer, default=0)


class GeminiSearchResult(Base):
    """Links a user to a cached Gemini listing they've seen, so save/dismiss
    state is per-user even though the underlying listing is shared."""
    __tablename__ = "gemini_search_results"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_gemini_search_results_user_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("gemini_jobs_cache.job_id"), index=True)
    search_keywords: Mapped[str] = mapped_column(String(255), default="")
    saved: Mapped[bool] = mapped_column(default=False)
    dismissed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    """Durable, queryable record of every meaningful action — the support/investigation backbone."""
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    request_id: Mapped[str] = mapped_column(String(16), default="", index=True)
    event: Mapped[str] = mapped_column(String(60), index=True)     # e.g. login, generate, webhook_received
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | failed | blocked | rejected
    # indexed: the public ATS checker's per-IP daily quota counts rows by (event, ip, created_at)
    ip: Mapped[str] = mapped_column(String(64), default="", index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)          # non-PII context only
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
