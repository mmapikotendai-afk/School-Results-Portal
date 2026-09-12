"""Application configuration.

All settings are loaded from environment variables (or a local `.env` file).
No credential is ever hard-coded in the source tree.
"""

from functools import lru_cache
from typing import Annotated, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


# A signing key shorter than this is not worth having; 64 random bytes is the
# recommended size and what the setup instructions generate.
MIN_SECRET_KEY_LENGTH = 32

# Values that appear in documentation and example files. Any of them is public
# knowledge, so a key set to one of them protects nothing.
WEAK_SECRET_KEYS = {
    "change_me_to_a_long_random_string",
    "changeme",
    "change_me",
    "secret",
    "secret_key",
    "your-secret-key",
    "test",
    "development",
}


class Settings(BaseSettings):
    """Environment-driven settings for the portal backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "School Results Portal"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- MySQL ---
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = ""
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "school_results_portal"

    # Full override. When empty, the URL is assembled from the parts above.
    DATABASE_URL: str = ""

    # --- Security ---
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # bcrypt work factor. Higher is stronger but slower: on a modest server
    # 12 costs roughly half a second per sign-in, 10 about a tenth. Do not go
    # below 10.
    BCRYPT_ROUNDS: int = 12

    # --- CORS ---
    # `NoDecode` stops pydantic-settings from JSON-parsing the raw env value, so
    # the validator below can accept a plain comma-separated string.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Sign-in domain given to learners who have no mailbox of their own. It is
    # an identifier, not an inbox, so it must be syntactically valid but need
    # not be routable. Reserved names such as .local and .invalid are rejected
    # by email validation and must not be used here.
    STUDENT_EMAIL_DOMAIN: str = "students.internal"

    # --- Uploads ---
    # Where the school logo and, later, result CSV files are written.
    UPLOAD_DIR: str = "uploads"

    # --- Branding (report cards) ---
    SCHOOL_NAME: str = "Your School Name"
    SCHOOL_MOTTO: str = ""

    # --- Email delivery ---
    # The master switch. Off by default so a fresh checkout, or a test run,
    # cannot post real mail to real people by accident. Turning it on is a
    # deliberate act.
    EMAIL_ENABLED: bool = False

    # "smtp" talks to any transactional provider (SendGrid, Mailgun, Postmark,
    # SES, Resend - they all expose SMTP). "file" writes the rendered message
    # to EMAIL_OUTBOX_DIR instead of sending, for local development only.
    EMAIL_PROVIDER: str = "smtp"

    EMAIL_HOST: str = ""
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""

    # STARTTLS on 587 is the usual choice; set EMAIL_USE_SSL for implicit TLS
    # on 465. Turning both off is only sensible against a local relay.
    EMAIL_USE_TLS: bool = True
    EMAIL_USE_SSL: bool = False
    EMAIL_TIMEOUT: int = 20

    # Refuse to create an account whose address cannot receive mail.
    #
    # Credentials are delivered by email and the password is not recoverable
    # afterwards, so an account created against an unreachable address is an
    # account nobody can ever sign in to. With this on, the domain is checked
    # for a mail exchanger before anything is written, and a send failure
    # discards the account rather than leaving it stranded.
    #
    # This catches a mistyped domain (gmial.com, nosuchschool.zw). It cannot
    # catch a well-formed address at a real domain whose mailbox does not
    # exist - no synchronous check can, because the receiving server only
    # reports that in a bounce, minutes later.
    EMAIL_REQUIRE_DELIVERABLE: bool = True

    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = ""

    # Where the "file" provider drops rendered messages. Development only.
    EMAIL_OUTBOX_DIR: str = "var/outbox"

    # Public origin of the React app, used to build the sign-in link in the
    # credential email. No trailing slash.
    FRONTEND_URL: str = "http://localhost:5173"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        """Accept a comma-separated string as well as a real list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _no_wildcard_origin(cls, value):
        """Refuse "*" as an allowed origin.

        The API is mounted with allow_credentials=True. A wildcard origin
        combined with credentials lets any website on the internet make
        authenticated requests on a signed-in user's behalf, so the two must
        never be configured together.
        """
        if any(origin.strip() == "*" for origin in value):
            raise ValueError(
                "CORS_ORIGINS must not contain '*'. The API sends credentials, "
                "so every allowed origin has to be named explicitly, for example "
                "CORS_ORIGINS=https://portal.yourschool.edu"
            )
        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def _usable_secret(cls, value: str) -> str:
        """Refuse to run on a signing key that cannot protect anything.

        This key is the only thing standing between a stranger and an
        administrator session: anyone who knows it can mint a token for any
        account. An empty key signs perfectly valid tokens, and the placeholder
        shipped in .env.example is published in the repository, so both are the
        same as having no authentication at all. Failing at startup is the only
        safe response - a warning gets skimmed past and reaches production.
        """
        key = (value or "").strip()

        if not key:
            raise ValueError(
                "SECRET_KEY is not set. Generate one with:\n"
                "    python -c \"import secrets; print(secrets.token_urlsafe(64))\"\n"
                "then put it in backend/.env as SECRET_KEY=<the generated value>."
            )

        if key.lower() in WEAK_SECRET_KEYS or key.lower().startswith("change_me"):
            raise ValueError(
                "SECRET_KEY is still the example placeholder, which is public. "
                "Generate a real one with:\n"
                "    python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )

        if len(key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY is only {len(key)} characters. Use at least "
                f"{MIN_SECRET_KEY_LENGTH}, generated with:\n"
                "    python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )

        return key

    @field_validator("EMAIL_PROVIDER")
    @classmethod
    def _known_provider(cls, value: str) -> str:
        provider = (value or "").strip().lower() or "smtp"
        if provider not in {"smtp", "file"}:
            raise ValueError(
                "EMAIL_PROVIDER must be 'smtp' (any transactional provider) or "
                "'file' (development only)."
            )
        return provider

    @field_validator("FRONTEND_URL")
    @classmethod
    def _tidy_frontend_url(cls, value: str) -> str:
        """A trailing slash here would produce '//login' in every email."""
        return (value or "").strip().rstrip("/")

    @property
    def email_from_address(self) -> str:
        """Envelope sender. Falls back to the SMTP username when unset."""
        return (self.EMAIL_FROM or self.EMAIL_USERNAME).strip()

    @property
    def email_from_name(self) -> str:
        return (self.EMAIL_FROM_NAME or self.SCHOOL_NAME).strip()

    def email_configuration_error(self) -> Optional[str]:
        """Why email cannot be sent, or None when it is ready.

        Checked before an account is provisioned so a misconfiguration shows up
        as a clear message to the administrator rather than a failed delivery
        discovered days later.
        """
        if not self.EMAIL_ENABLED:
            return "Email delivery is disabled (EMAIL_ENABLED=false)."
        if self.EMAIL_PROVIDER == "file":
            if self.ENVIRONMENT.strip().lower() in {"production", "prod"}:
                return (
                    "EMAIL_PROVIDER=file writes messages to disk instead of "
                    "sending them, and must not be used in production."
                )
            return None
        if not self.EMAIL_HOST:
            return "EMAIL_HOST is not set."
        if not self.email_from_address:
            return "EMAIL_FROM is not set."
        # An unauthenticated relay is legitimate, but only on a local or
        # internal one. Every hosted provider requires credentials, so a
        # public host with no username is a misconfiguration we can name now
        # rather than let fail as an opaque SMTP error later.
        host = self.EMAIL_HOST.strip().lower()
        is_local = host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local")
        if not is_local and not self.EMAIL_USERNAME:
            return (
                f"EMAIL_USERNAME is not set. {self.EMAIL_HOST} requires "
                "credentials; only a local relay may be used without them."
            )
        # Catching this here turns a confusing SMTP auth failure into a
        # sentence that names the variable to fill. The hint is per-provider,
        # because the thing to paste differs and every one of them rejects the
        # account password people reach for first.
        if self.EMAIL_USERNAME and not self.EMAIL_PASSWORD:
            hints = {
                "smtp.gmail.com": (
                    "a 16-character App Password from "
                    "https://myaccount.google.com/apppasswords - not the "
                    "account password, which Google refuses over SMTP"
                ),
                "smtp-relay.brevo.com": (
                    "the SMTP key from https://app.brevo.com -> SMTP & API -> "
                    "SMTP tab - not your Brevo account password"
                ),
                "smtp.sendgrid.net": "a SendGrid API key",
                "smtp.resend.com": "a Resend API key",
            }
            hint = hints.get(host, "the API key or SMTP password for that host")
            return f"EMAIL_USERNAME is set but EMAIL_PASSWORD is empty. Use {hint}."
        return None

    @property
    def sqlalchemy_database_uri(self) -> str:
        """The SQLAlchemy connection URL for MySQL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        from urllib.parse import quote_plus

        user = quote_plus(self.MYSQL_USER)
        password = quote_plus(self.MYSQL_PASSWORD)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def is_configured(self) -> bool:
        """True when the minimum required secrets have been supplied."""
        return bool(self.SECRET_KEY) and bool(self.MYSQL_USER)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so the `.env` file is parsed only once."""
    return Settings()


settings = get_settings()
