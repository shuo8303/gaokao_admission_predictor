"""Project configuration values."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Default Flask configuration for local development."""

    DEBUG = True
    SECRET_KEY = "replace-this-secret-key-before-deployment"
    DATA_DIR = BASE_DIR / "data"
    SCORE_RANK_DIR = BASE_DIR / "data" / "score_rank"
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "console")
    SMS_CODE_EXPIRES_SECONDS = 5 * 60
    SMS_SEND_INTERVAL_SECONDS = 60
    ALIYUN_SMS_SIGN_NAME = os.getenv("ALIYUN_SMS_SIGN_NAME", "速通互联验证服务")
    ALIYUN_SMS_TEMPLATE_CODE = os.getenv("ALIYUN_SMS_TEMPLATE_CODE", "100001")
    ALIYUN_SMS_TEMPLATE_PARAM = os.getenv(
        "ALIYUN_SMS_TEMPLATE_PARAM",
        '{"code":"##code##"}',
    )
    ALIYUN_SMS_ENDPOINT = os.getenv(
        "ALIYUN_SMS_ENDPOINT",
        "dypnsapi.aliyuncs.com",
    )
