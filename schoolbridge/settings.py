"""
Django settings for Schoolbridge.

All environment-specific values are read from environment variables (or a
local `.env` file). See `.env.example` for the full list.
"""
import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Environment helpers
# --------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    """Minimal .env loader so the project has no extra dependencies."""
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(f"{name} must be an integer.") from exc


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG or TESTING:
        SECRET_KEY = "django-insecure-development-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Schoolbridge apps
    "accounts",
    "core",
    "questions",
    "staffroom",
    "dashboard",
    "notifications",
    "feedback",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "schoolbridge.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.schoolbridge",
            ],
        },
    },
]

WSGI_APPLICATION = "schoolbridge.wsgi.application"
ASGI_APPLICATION = "schoolbridge.asgi.application"

# --------------------------------------------------------------------------
# Database: SQLite by default, PostgreSQL when DB_ENGINE=postgres
# (PostgreSQL requires `pip install "psycopg[binary]"`).
# --------------------------------------------------------------------------
if env("DB_ENGINE", "sqlite").lower() in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "schoolbridge"),
            "USER": env("DB_USER", "schoolbridge"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / env("SQLITE_NAME", "db.sqlite3"),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if TESTING:
    # Fast hashing for tests only.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "core:home"

# --------------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Africa/Harare")
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static & media
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Staff-room uploads are NOT served publicly; they are streamed through a
# permission-checked view (see staffroom.views.AttachmentDownloadView).
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))
MEDIA_URL = "/media/"

# --------------------------------------------------------------------------
# Cache (used for privacy-preserving rate limiting)
# --------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "schoolbridge",
    }
}
if env("REDIS_URL"):
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }

# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Schoolbridge <no-reply@localhost>")

# --------------------------------------------------------------------------
# Security (production hardening when DEBUG is off)
# --------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if not DEBUG and not TESTING:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    if env_bool("DJANGO_BEHIND_PROXY", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# --------------------------------------------------------------------------
# Schoolbridge settings
# --------------------------------------------------------------------------
SB_SITE_NAME = env("SB_SITE_NAME", "Schoolbridge")
SB_INSTITUTION_NAME = env("SB_INSTITUTION_NAME", "Our Institution")
SB_SITE_URL = env("SB_SITE_URL", "http://localhost:8000")
SB_ADMIN_URL = env("SB_ADMIN_URL", "admin/")

# Agreed response period for departments (can be overridden per department).
SB_DEFAULT_RESPONSE_HOURS = env_int("SB_DEFAULT_RESPONSE_HOURS", 48)

# Rate limits. Clients are identified by a salted, daily-rotating hash that
# only ever lives in the cache; IP addresses are never written to the database.
SB_ASK_RATE_LIMIT = env_int("SB_ASK_RATE_LIMIT", 5)
SB_ASK_RATE_WINDOW = env_int("SB_ASK_RATE_WINDOW", 3600)
SB_TRACK_RATE_LIMIT = env_int("SB_TRACK_RATE_LIMIT", 20)
SB_TRACK_RATE_WINDOW = env_int("SB_TRACK_RATE_WINDOW", 3600)
SB_FEEDBACK_RATE_LIMIT = env_int("SB_FEEDBACK_RATE_LIMIT", 5)
SB_FEEDBACK_RATE_WINDOW = env_int("SB_FEEDBACK_RATE_WINDOW", 3600)
SB_TRUST_X_FORWARDED_FOR = env_bool("SB_TRUST_X_FORWARDED_FOR", False)

# Extra words that are not allowed in questions (comma separated).
SB_BLOCKED_WORDS = env_list("SB_BLOCKED_WORDS", "")

SB_EMAIL_NOTIFICATIONS = env_bool("SB_EMAIL_NOTIFICATIONS", False)

SB_MAX_UPLOAD_MB = env_int("SB_MAX_UPLOAD_MB", 10)
SB_ALLOWED_UPLOAD_EXTENSIONS = env_list(
    "SB_ALLOWED_UPLOAD_EXTENSIONS",
    "pdf,doc,docx,ppt,pptx,xls,xlsx,odt,ods,odp,txt,csv,png,jpg,jpeg,zip",
)
