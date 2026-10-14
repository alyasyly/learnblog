"""
Django settings for the learning blog.

Most things you may want to change are controlled by environment variables
so you never have to edit this file for deployment:

    DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS,
    SITE_NAME, SITE_TAGLINE, AUTHOR_NAME, GITHUB_URL
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
_DEV_KEY = "dev-only-insecure-key-change-me"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _DEV_KEY)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

if not DEBUG and SECRET_KEY == _DEV_KEY:
    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY to a long random value when DJANGO_DEBUG=0."
    )

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "blog.apps.BlogConfig",
    "studio.apps.StudioConfig",
    "accounts.apps.AccountsConfig",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "blog.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# Internationalisation (Persian, right-to-left, Tehran time)
# --------------------------------------------------------------------------
LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static files
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The writing studio (/studio/) is the main place to log in.
LOGIN_URL = "studio:login"
LOGIN_REDIRECT_URL = "studio:dashboard"

# --------------------------------------------------------------------------
# Blog settings
# --------------------------------------------------------------------------
SITE_NAME = os.environ.get("SITE_NAME", "alyasyly blog")
SITE_TAGLINE = os.environ.get(
    "SITE_TAGLINE", "هر چیزی که یاد می‌گیرم را اینجا می‌نویسم تا فراموش نشود."
)
AUTHOR_NAME = os.environ.get("AUTHOR_NAME", "")
# Link to your GitHub profile; the GitHub icon is shown only when this is set.
GITHUB_URL = os.environ.get("GITHUB_URL", "")
POSTS_PER_PAGE = 9

# --------------------------------------------------------------------------
# Accounts & comments
# --------------------------------------------------------------------------
# Anyone can sign up at /accounts/signup/ and comment on posts.
# Set COMMENTS_AUTO_APPROVE=0 to hold every new comment until you approve it
# in the studio (/studio/comments/). Staff comments are always shown at once.
COMMENTS_AUTO_APPROVE = os.environ.get("COMMENTS_AUTO_APPROVE", "1") == "1"
COMMENT_COOLDOWN_SECONDS = 20       # minimum gap between two comments by one user
SIGNUPS_PER_IP_PER_HOUR = 5         # new accounts allowed per IP address per hour
