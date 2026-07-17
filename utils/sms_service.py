"""SMS verification code generation, delivery, and verification helpers."""

import random
import re
import time


PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
_VERIFICATION_CODES = {}


class SmsSendError(RuntimeError):
    """Raised when a verification code cannot be sent."""


def normalize_phone(phone):
    """Return a stripped phone number when it looks like a mainland number."""
    normalized = str(phone or "").strip()

    if not PHONE_PATTERN.match(normalized):
        raise ValueError("请输入有效的 11 位手机号。")

    return normalized


def send_verification_code(phone, config):
    """Send a one-time verification code with the configured provider."""
    normalized_phone = normalize_phone(phone)
    provider = config["SMS_PROVIDER"].lower()
    print(f"[短信服务] provider={provider}, phone=****{normalized_phone[-4:]}")

    if provider == "console":
        return _send_console_code(normalized_phone, config)

    if provider == "aliyun":
        _send_aliyun_code(normalized_phone, config)
        return normalized_phone

    if provider == "tencent":
        raise SmsSendError("腾讯云短信暂未接入，请先使用阿里云或 console 模式。")

    raise SmsSendError(f"未知短信服务商：{config['SMS_PROVIDER']}")


def verify_code(phone, code, config=None):
    """Validate a submitted verification code."""
    normalized_phone = normalize_phone(phone)
    submitted_code = str(code or "").strip()
    provider = (config["SMS_PROVIDER"].lower() if config else "console")

    if provider == "aliyun":
        _verify_aliyun_code(normalized_phone, submitted_code, config)
        return normalized_phone

    return _verify_console_code(normalized_phone, submitted_code)


def _send_console_code(phone, config):
    """Generate and print a local development verification code."""
    now = time.time()
    existing = _VERIFICATION_CODES.get(phone)

    if existing and now - existing["sent_at"] < config["SMS_SEND_INTERVAL_SECONDS"]:
        raise SmsSendError("验证码发送过于频繁，请稍后再试。")

    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    _VERIFICATION_CODES[phone] = {
        "code": code,
        "expires_at": now + config["SMS_CODE_EXPIRES_SECONDS"],
        "sent_at": now,
    }
    print(f"[短信验证码] 手机号：{phone}，验证码：{code}")
    return phone


def _verify_console_code(phone, submitted_code):
    """Verify a console-mode verification code."""
    record = _VERIFICATION_CODES.get(phone)

    if not record:
        raise ValueError("请先获取短信验证码。")

    if time.time() > record["expires_at"]:
        _VERIFICATION_CODES.pop(phone, None)
        raise ValueError("验证码已过期，请重新获取。")

    if submitted_code != record["code"]:
        raise ValueError("验证码错误，请重新输入。")

    _VERIFICATION_CODES.pop(phone, None)
    return phone


def _send_aliyun_code(phone, config):
    """Send verification code with Aliyun Dypnsapi."""
    client = _create_aliyun_client(config)
    models, runtime_models = _load_aliyun_models()
    request = models.SendSmsVerifyCodeRequest(
        phone_number=phone,
        sign_name=config["ALIYUN_SMS_SIGN_NAME"],
        template_code=config["ALIYUN_SMS_TEMPLATE_CODE"],
        template_param=config["ALIYUN_SMS_TEMPLATE_PARAM"],
        code_length=6,
        valid_time=config["SMS_CODE_EXPIRES_SECONDS"],
    )
    runtime = runtime_models.RuntimeOptions()

    try:
        response = client.send_sms_verify_code_with_options(request, runtime)
        print(f"[阿里云短信] SendSmsVerifyCode response: {_summarize_aliyun_response(response)}")
    except Exception as exc:
        raise SmsSendError(_format_aliyun_error(exc)) from exc


def _verify_aliyun_code(phone, submitted_code, config):
    """Verify an Aliyun-hosted SMS code."""
    client = _create_aliyun_client(config)
    models, runtime_models = _load_aliyun_models()
    request = models.CheckSmsVerifyCodeRequest(
        phone_number=phone,
        verify_code=submitted_code,
    )
    runtime = runtime_models.RuntimeOptions()

    try:
        response = client.check_sms_verify_code_with_options(request, runtime)
    except Exception as exc:
        raise ValueError(_format_aliyun_error(exc)) from exc

    verify_result = _extract_aliyun_verify_result(response)
    if verify_result != "PASS":
        raise ValueError("验证码错误或已过期，请重新获取。")


def _create_aliyun_client(config):
    """Create an Aliyun Dypnsapi client from environment credentials."""
    try:
        from alibabacloud_credentials.client import Client as CredentialClient
        from alibabacloud_dypnsapi20170525.client import (
            Client as Dypnsapi20170525Client,
        )
        from alibabacloud_tea_openapi import models as open_api_models
    except ImportError as exc:
        raise SmsSendError("缺少阿里云短信 SDK 依赖，请先安装 requirements.txt。") from exc

    credential = CredentialClient()
    aliyun_config = open_api_models.Config(credential=credential)
    aliyun_config.endpoint = config["ALIYUN_SMS_ENDPOINT"]
    return Dypnsapi20170525Client(aliyun_config)


def _load_aliyun_models():
    """Load Aliyun request and runtime models lazily."""
    try:
        from alibabacloud_dypnsapi20170525 import models as dypnsapi_models
        from alibabacloud_tea_util import models as util_models
    except ImportError as exc:
        raise SmsSendError("缺少阿里云短信 SDK 依赖，请先安装 requirements.txt。") from exc

    return dypnsapi_models, util_models


def _extract_aliyun_verify_result(response):
    """Extract Model.VerifyResult from an Aliyun SDK response."""
    body = getattr(response, "body", None)
    model = getattr(body, "model", None)
    return getattr(model, "verify_result", None)


def _summarize_aliyun_response(response):
    """Return a short printable summary of an Aliyun SDK response."""
    body = getattr(response, "body", None)
    if body is None:
        return str(response)

    return str(body)


def _format_aliyun_error(error):
    """Return a user-safe Aliyun error message."""
    message = getattr(error, "message", None) or str(error)
    data = getattr(error, "data", None)
    recommend = data.get("Recommend") if isinstance(data, dict) else None

    if recommend:
        return f"短信服务调用失败：{message}。诊断信息：{recommend}"

    return f"短信服务调用失败：{message}"
