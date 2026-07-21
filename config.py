"""Project configuration values."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Default Flask configuration for local development."""

    DEBUG = True
    SECRET_KEY = "replace-this-secret-key-before-deployment"
    ADMIN_STATS_TOKEN = os.getenv("ADMIN_STATS_TOKEN", "")
    SITE_CLOSED = os.getenv("SITE_CLOSED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    DATA_DIR = BASE_DIR / "data"
    SCORE_RANK_DIR = BASE_DIR / "data" / "score_rank"
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
