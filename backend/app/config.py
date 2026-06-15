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

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_model_pro: str = "deepseek-v4-pro"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_model_pro: str = "gemini-3.5-flash"

    drafter_provider: str = "gemini"
    critic_provider: str = "deepseek"

    # --- generation pipeline limits (Vercel: each request does ONE LLM call,
    # must stay well under the 60s function limit) ---
    # "fast": always use the non-pro/flash models (typical 5-25s/call). Required on Vercel Hobby.
    # "quality": tailor/critique may use pro models (current behavior) - only safe on hosts without a 60s cap.
    generation_tier: str = "fast"
    # cap LLM output tokens per call, applied to every provider.
    llm_max_tokens: int = 4000
    # per-call HTTP timeout (seconds). Keeps a stuck provider from being killed
    # by the platform with no useful error.
    llm_timeout_s: float = 50.0

    # if the primary provider above fails (incl. 503/overloaded after retries),
    # retry the same call on this provider instead. empty = no fallback.
    drafter_fallback_provider: str = "deepseek"
    critic_fallback_provider: str = "gemini"

    # comma-separated emails granted admin/support access (audit + manual credit adjust)
    admin_emails: str = ""

    # --- billing / credits ---
    billing_enabled: bool = True
    app_url: str = "http://localhost:5173"          # frontend base, for checkout return
    credits_per_generation: int = 1                  # credits a single tailored CV costs

    # --- ATS score guarantee ---
    # plans can promise a minimum ATS score (see Plan.min_ats_score in BILLING_PLANS_JSON).
    # if the first pass scores below that, the pipeline auto-improves and re-scores,
    # up to this many total passes (1 initial + retries), without extra credit charge.
    ats_guarantee_max_iterations: int = 3
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


settings = Settings()
