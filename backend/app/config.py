from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-insecure-change-me"
    access_token_expire_minutes: int = 10080
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./cvforge.db"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_model_pro: str = "deepseek-v4-pro"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_model_pro: str = "gemini-3.1-pro"

    drafter_provider: str = "gemini"
    critic_provider: str = "deepseek"

    # comma-separated emails granted admin/support access (audit + manual credit adjust)
    admin_emails: str = ""

    # --- billing / credits ---
    billing_enabled: bool = True
    app_url: str = "http://localhost:5173"          # frontend base, for checkout return
    credits_per_generation: int = 1                  # credits a single tailored CV costs
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
    billing_plans_json: str = (
        '[{"id":"starter","name":"Starter","price_usd":9,"credits":100,"polar_product_id":"","recurring":false},'
        '{"id":"pro","name":"Pro Monthly","price_usd":29,"credits":500,"polar_product_id":"","recurring":true}]'
    )


settings = Settings()
