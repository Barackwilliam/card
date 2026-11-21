"""
Mipangilio ya mfumo wa michango ya harusi.

Kila kitu cha siri au kinachobadilika kati ya mazingira kinasomwa kutoka
environment variables (angalia .env.example).
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    return env(name, str(default)).lower() in ("1", "true", "yes", "ndio")


DEBUG = env_bool("DEBUG", False)
SECRET_KEY = env("SECRET_KEY") or ("dev-only-insecure-key" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("Weka SECRET_KEY kwenye environment variables.")

ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "michango",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: Supabase Postgres kupitia DATABASE_URL.
# Tumia "Session pooler" connection string ya Supabase (port 5432) kwa server
# inayokaa hewani muda wote.
DATABASE_URL = env("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(env("DB_CONN_MAX_AGE", "60")),
            conn_health_checks=True,
            ssl_require=env_bool("DB_SSL_REQUIRE", True),
        )
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "sw"
TIME_ZONE = "Africa/Dar_es_Salaam"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
NUMBER_GROUPING = 3
THOUSAND_SEPARATOR = ","

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Picha (kadi na template za kadi): Supabase Storage kupitia S3 protocol.
# Bila vigezo hivi, picha zinahifadhiwa kwenye folda ya "media/" (kwa majaribio tu).
SUPABASE_URL = env("SUPABASE_URL", "").rstrip("/")
SUPABASE_BUCKET = env("SUPABASE_BUCKET", "kadi")
if env("SUPABASE_S3_ACCESS_KEY_ID"):
    STORAGES = {
        "default": {
            "BACKEND": "michango.storage.SupabaseStorage",
            "OPTIONS": {
                "bucket_name": SUPABASE_BUCKET,
                "endpoint_url": f"{SUPABASE_URL}/storage/v1/s3",
                "access_key": env("SUPABASE_S3_ACCESS_KEY_ID"),
                "secret_key": env("SUPABASE_S3_SECRET_ACCESS_KEY"),
                "region_name": env("SUPABASE_S3_REGION", "eu-central-1"),
                "addressing_style": "path",
                "signature_version": "s3v4",
                "file_overwrite": True,
                "querystring_auth": False,
            },
        },
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Anwani kamili ya mfumo ukiwa hewani, mfano https://michango.example.com
# Inatumika kutengeneza link za picha WhatsApp ikiwa picha ziko "media/".
SITE_URL = env("SITE_URL", "http://localhost:8000").rstrip("/")

# WhatsApp Cloud API (Meta). Bila WHATSAPP_TOKEN mfumo unafanya "majaribio":
# unaandika ujumbe kwenye kumbukumbu bila kuutuma.
WHATSAPP = {
    "TOKEN": env("WHATSAPP_TOKEN", ""),
    "PHONE_NUMBER_ID": env("WHATSAPP_PHONE_NUMBER_ID", ""),
    "API_VERSION": env("WHATSAPP_API_VERSION", "v21.0"),
    "VERIFY_TOKEN": env("WHATSAPP_VERIFY_TOKEN", ""),
    "APP_SECRET": env("WHATSAPP_APP_SECRET", ""),
    "LANGUAGE": env("WHATSAPP_TEMPLATE_LANGUAGE", "sw"),
    "TEMPLATES": {
        "kadi": env("WHATSAPP_TEMPLATE_KADI", "kadi_mchango"),
        "kikumbusho": env("WHATSAPP_TEMPLATE_KIKUMBUSHO", "kikumbusho_mchango"),
        "kikumbusho_salio": env("WHATSAPP_TEMPLATE_KIKUMBUSHO_SALIO", "kikumbusho_salio"),
        "shukrani": env("WHATSAPP_TEMPLATE_SHUKRANI", "shukrani_mchango"),
    },
}

# Siri ya kuruhusu huduma ya nje (cron) kuanzisha utumaji wa vikumbusho.
CRON_SECRET = env("CRON_SECRET", "")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashibodi"
LOGOUT_REDIRECT_URL = "login"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"michango": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")}},
}
