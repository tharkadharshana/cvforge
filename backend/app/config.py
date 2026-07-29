from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-insecure-change-me"
    access_token_expire_minutes: int = 10080
    algorithm: str = "HS256"

    # Local/test default is SQLite. In production use the Supabase Postgres
    # transaction-mode pooler (port 6543), e.g.:
    # postgresql+psycopg://postgres.<ref>:<password>@<region>.pooler.supabase.com:6543/postgres?sslmode=require
    database_url: str = "sqlite:///./cvforge.db"

    # single key (back-compat) and/or comma-separated list of keys. If
    # *_API_KEYS is set, it's used and *_API_KEY is ignored. Extra keys let a
    # provider rotate past a key that hits its own rate limit (429) instead
    # of failing the request, multiplying your effective requests/minute.
    deepseek_api_key: str = ""
    deepseek_api_keys: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_model_pro: str = "deepseek-v4-pro"

    gemini_api_key: str = ""
    gemini_api_keys: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_model_pro: str = "gemini-3.5-flash"

    openai_model: str = "gpt-4o-mini"
    openai_model_pro: str = "gpt-4o-mini"

    # --- generation pipeline limits (Vercel: a request may chain through
    # every provider below before giving up -- all of them must fit inside
    # the 60s function limit) ---
    # "fast": always use the non-pro/flash models (typical 5-25s/call). Required on Vercel Hobby.
    # "quality": tailor/critique may use pro models (current behavior) - only safe on hosts without a 60s cap.
    generation_tier: str = "fast"
    # cap LLM output tokens per call, applied to every provider.
    llm_max_tokens: int = 4000
    # per-call HTTP timeout (seconds). Keeps a stuck provider from being killed
    # by the platform with no useful error. Sized so the whole llm_provider_chain
    # stalling out still fits under Vercel's 60s function limit
    # (3 providers x 15s = 45s, leaving ~15s headroom for everything else) --
    # do not raise this without also shortening the chain or the limit.
    llm_timeout_s: float = 15.0

    # same chain used for both drafting and critiquing: tries each provider in
    # order, falling through to the next on any error (incl. 503/overloaded/
    # timeout after that provider's own key-rotation retries are exhausted).
    llm_provider_chain: str = "gemini,openai,deepseek"

    # --- job aggregator (Adzuna free tier) ---
    # Legal job-search feed so users can find roles and generate a CV against one
    # without pasting the description by hand. Register at developer.adzuna.com
    # (free: ~250 req/day). Leave blank to disable the /jobs/search endpoint.
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "us"          # Adzuna country code: us, gb, ca, au, de, ...

    # --- LinkedIn job discovery (public jobs-guest pages, no API key) ---
    # Off by default: this reads LinkedIn's unauthenticated guest HTML pages,
    # which is against LinkedIn's Terms of Service (see docs/LEGAL_NOTES.md).
    # Explicit opt-in only — do not enable without accepting that risk.
    linkedin_search_enabled: bool = False
    linkedin_free_daily_searches: int = 3
    linkedin_free_results_per_search: int = 10
    linkedin_paid_results_per_search: int = 50

    # --- Gemini job discovery (google_search grounding tool) ---
    # Auto-enabled whenever a Gemini key is configured (gemini_api_key/gemini_api_keys) —
    # this legitimately uses Google's own search grounding API, no ToS risk like the
    # LinkedIn scraper, so there's no separate opt-in flag.
    gemini_search_model: str = "gemini-2.0-flash"   # must be a model version that supports the google_search tool
    gemini_free_daily_searches: int = 3
    gemini_free_results_per_search: int = 10
    gemini_paid_results_per_search: int = 50

    # --- OpenAI web_search fallback for job discovery ---
    # Used only when the Gemini grounding call above fails (e.g. its google_search
    # quota isn't provisioned) -- not a separate feature, just a backup engine for
    # the same "AI search" results. Leave blank to disable the fallback.
    openai_api_key: str = ""
    openai_api_keys: str = ""
    openai_search_model: str = "gpt-4o-mini"

    # comma-separated emails granted admin/support access (audit + manual credit adjust)
    admin_emails: str = ""

    # extra CORS origins beyond app_url/localhost, comma-separated (e.g. a custom
    # domain that differs from app_url, or a www. alias). app_url is always allowed.
    cors_origins: str = ""

    # --- billing / credits ---
    billing_enabled: bool = True
    app_url: str = "http://localhost:5173"          # frontend base, for checkout return
    credits_per_generation: int = 1                  # credits a single tailored CV costs

    # --- ATS score guarantee ---
    # plans can promise a minimum ATS score (see Plan.min_ats_score in BILLING_PLANS_JSON).
    # the critique step annotates whether the score meets the user's plan guarantee.
    # guarantee for users on a plan that doesn't set min_ats_score (e.g. free/trial). 0 = no guarantee.
    default_min_ats_score: int = 0
    free_tier_mode: str = "trial"                    # "trial" | "forever_free"
    free_trial_credits: int = 10                     # granted once on signup (trial mode)
    free_monthly_credits: int = 5                    # refilled monthly (forever_free mode)
    cost_per_generation_usd: float = 0.02            # YOUR est. LLM cost per generation (for margin math)

    # --- Polar payment gateway (Merchant of Record) ---
    polar_access_token: str = ""                     # Organization Access Token (server-side secret)
    polar_webhook_secret: str = ""                   # Webhook signing secret from Polar
    polar_server: str = "sandbox"                    # sandbox | production
    polar_success_url: str = "http://localhost:5173/billing?status=success"
    billing_provider: str = "polar"
    # Plans: map your Polar product to credits. polar_product_id from Polar dashboard. recurring=true for subscriptions.
    # min_ats_score: guaranteed minimum ATS score for this plan (0 = no guarantee).
    billing_plans_json: str = (
        '[{"id":"starter","name":"Starter","price_usd":9,"credits":100,"polar_product_id":"","recurring":false,"min_ats_score":80},'
        '{"id":"pro","name":"Pro Monthly","price_usd":29,"credits":500,"polar_product_id":"","recurring":true,"min_ats_score":85}]'
    )


    def _key_list(self, multi: str, single: str) -> list[str]:
        keys = [k.strip() for k in multi.split(",") if k.strip()]
        return keys or ([single] if single else [])

    @property
    def deepseek_api_keys_list(self) -> list[str]:
        return self._key_list(self.deepseek_api_keys, self.deepseek_api_key)

    @property
    def gemini_api_keys_list(self) -> list[str]:
        return self._key_list(self.gemini_api_keys, self.gemini_api_key)

    @property
    def openai_api_keys_list(self) -> list[str]:
        return self._key_list(self.openai_api_keys, self.openai_api_key)


settings = Settings()
