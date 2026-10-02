from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    env: str = "development"

    # Two distinct DB credentials: migrator owns/alters schema, app is restricted
    # (requirement: separate migration-owner and restricted application DB roles).
    database_url_migrator: str = (
        "postgresql+psycopg://matrisathi_migrator:matrisathi_migrator_dev_pw@localhost:5433/matrisathi"
    )
    database_url_app: str = (
        "postgresql+psycopg://matrisathi_app:matrisathi_app_dev_pw@localhost:5433/matrisathi"
    )

    jwt_secret: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14

    # Browser storage: both tokens ride as httpOnly cookies, never localStorage,
    # so they are unreachable from page JavaScript (XSS mitigation).
    cookie_secure: bool = False  # must be True behind HTTPS in any real deployment
    cookie_domain: str | None = None

    # CSRF mitigation for the cookie-based session: the frontend must send this
    # header on every mutating request; a cross-site form post cannot set it,
    # and CORS blocks a cross-origin script from setting it either.
    csrf_header_name: str = "X-MatriSathi-Client"
    csrf_header_value: str = "web"

    cors_allowed_origin: str = "http://localhost:5173"

    login_throttle_max_attempts: int = 5
    login_throttle_window_minutes: int = 15

    # Not read anywhere in the app yet (see .env.example) — declared
    # explicitly so a teammate filling in the optional Supabase/GitHub
    # section of .env doesn't hit a validation error on startup. Any other
    # unrecognized key still fails loudly, which is what we want for
    # catching real typos in the required settings above.
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    github_token: str | None = None


settings = Settings()
