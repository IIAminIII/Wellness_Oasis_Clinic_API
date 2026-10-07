"""Django settings for Wellness Oasis Clinic.

Every deployment-specific value can be supplied through environment variables.
The defaults are intentionally convenient for local development, while production
settings fail closed when DEBUG is disabled.
"""

from pathlib import Path

import dj_database_url
import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
    REQUIRE_EMAIL_VERIFICATION=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DJANGO_DEBUG")
SECRET_KEY = env(
    "SECRET_KEY",
    default="local-development-only-change-me",
)
if not DEBUG and SECRET_KEY == "local-development-only-change-me":
    raise RuntimeError("SECRET_KEY must be set when DEBUG=False")

# Set by Vercel in both build and runtime environments.
ON_VERCEL = bool(env("VERCEL", default=""))

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "127.0.0.1",
        "localhost",
        "wellness-oasis-clinic-api.onrender.com",
        ".vercel.app",
    ],
)
FRONTEND_URL = env(
    "FRONTEND_URL",
    default="http://127.0.0.1:5500",
).rstrip("/")
BACKEND_URL = env(
    "BACKEND_URL",
    default="http://127.0.0.1:8000",
).rstrip("/")
REQUIRE_EMAIL_VERIFICATION = env.bool("REQUIRE_EMAIL_VERIFICATION")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "operations.apps.OperationsConfig",
    "appointments",
    "doctors",
    "patients",
    "services",
    "contact_us",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://wellness-oasis-clinic-front-end.vercel.app",
    ],
)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://wellness-oasis-clinic-front-end.vercel.app",
        "https://*.vercel.app",
    ],
)

ROOT_URLCONF = "Wellness_Oasis_Clinic.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "Wellness_Oasis_Clinic.wsgi.application"
ASGI_APPLICATION = "Wellness_Oasis_Clinic.asgi.application"

# PgBouncer in transaction-pooling mode hands a different backend connection to
# each statement, so Django must not hold connections open or use server-side
# cursors. Supabase's transaction pooler listens on 6543; Neon's pooler keeps
# port 5432 but marks the endpoint hostname with "-pooler".
DATABASE_URL = env("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
USING_TRANSACTION_POOLER = ":6543" in DATABASE_URL or "-pooler" in DATABASE_URL

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=0 if USING_TRANSACTION_POOLER else env.int("DB_CONN_MAX_AGE", default=600),
        conn_health_checks=not USING_TRANSACTION_POOLER,
        ssl_require=env.bool("DB_SSL_REQUIRE", default=False),
    )
}
if USING_TRANSACTION_POOLER:
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ]
    if not DEBUG
    else [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("API_ANON_RATE", default="100/hour"),
        "user": env("API_USER_RATE", default="1000/hour"),
        "auth": env("API_AUTH_RATE", default="20/hour"),
    },
    "EXCEPTION_HANDLER": "Wellness_Oasis_Clinic.exceptions.api_exception_handler",
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Asia/Dhaka")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # On Vercel the collectstatic output (and its manifest) lives in a
        # separate static deployment, not inside the Python function, so the
        # manifest cannot be read at runtime. Plain hashed-free storage keeps
        # {% static %} emitting predictable /static/... URLs there.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"
        if ON_VERCEL
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default=env("EMAIL", default=""))
EMAIL_HOST_PASSWORD = env(
    "EMAIL_HOST_PASSWORD",
    default=env("EMAIL_PASSWORD", default=""),
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="Wellness Oasis <no-reply@wellness-oasis.local>",
)

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = env.int(
    "SECURE_HSTS_SECONDS",
    default=31536000 if not DEBUG else 0,
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
