"""
Test-only settings module.

Overrides the production settings with:
- In-memory SQLite database (no PostgreSQL needed)
- Dummy values for required environment variables
- Disabled dotenv loading (already set via env vars below)

Usage:
    python manage.py test submissions --settings=config.test_settings --verbosity=2
"""

import os

# ---- Inject required env vars before config.settings is evaluated ----------
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("N8N_WEBHOOK_URL", "https://test.example.com/webhook")
os.environ.setdefault("N8N_WEBHOOK_SECRET", "test-secret-123")

# ---- Import everything from the real settings ------------------------------
from config.settings import *  # noqa: E402, F403, F401

# ---- Override database to SQLite (no PostgreSQL needed for unit tests) ------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ---- Speed up password hashing in tests ------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ---- Silence logging noise during test runs --------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
    },
    "loggers": {
        "submissions": {"handlers": ["null"], "propagate": False},
    },
}
