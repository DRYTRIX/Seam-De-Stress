import os

from sqlalchemy.pool import StaticPool


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _database_uri():
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        # Normalize the legacy "postgres://" scheme some providers still emit.
        if explicit.startswith("postgres://"):
            explicit = explicit.replace("postgres://", "postgresql://", 1)
        return explicit

    driver = os.environ.get("DB_DRIVER", "postgresql")
    if driver == "sqlite":
        db_path = os.environ.get("SQLITE_PATH", "instance/seamdestress.db")
        return f"sqlite:///{db_path}"

    user = os.environ.get("POSTGRES_USER", "seamdestress")
    password = os.environ.get("POSTGRES_PASSWORD", "seamdestress")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    name = os.environ.get("POSTGRES_DB", "seamdestress")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APP_NAME = "Seam(De)Stress"

    # Sessions & cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), default=True)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), default=True)

    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Uploads
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/data/uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", "15")) * 1024 * 1024

    # i18n
    LANGUAGES = ["nl", "fr", "en"]
    BABEL_DEFAULT_LOCALE = os.environ.get("DEFAULT_LOCALE", "nl")
    BABEL_DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", "Europe/Brussels")
    BABEL_TRANSLATION_DIRECTORIES = "translations"

    # Currency / locale defaults (Belgian context)
    DEFAULT_CURRENCY = "EUR"
    DEFAULT_VAT_RATE = os.environ.get("DEFAULT_VAT_RATE", "21")
    WEEK_START = "monday"

    # Rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = "200 per hour"
    LOGIN_RATE_LIMIT = os.environ.get("LOGIN_RATE_LIMIT", "10 per minute")

    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "https")

    # Notifications (SMTP) — SMTP_HOST empty means "not configured"; the
    # notification service logs a skipped attempt rather than raising.
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = _bool(os.environ.get("SMTP_USE_TLS"), default=True)
    SMTP_FROM_ADDRESS = os.environ.get("SMTP_FROM_ADDRESS", "")


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), default=False)
    REMEMBER_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), default=False)
    TEMPLATES_AUTO_RELOAD = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER_TEST", "/tmp/seamdestress-test-uploads")
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name=None):
    name = name or os.environ.get("FLASK_ENV", "production")
    return CONFIG_BY_NAME.get(name, ProductionConfig)
