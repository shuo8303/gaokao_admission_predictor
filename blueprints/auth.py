"""Authentication routes for phone verification-code login."""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from utils.sms_service import SmsSendError, send_verification_code, verify_code


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _normalize_nickname(nickname):
    """Validate and normalize the display nickname."""
    normalized = str(nickname or "").strip()

    if not normalized:
        raise ValueError("请输入昵称。")

    if len(normalized) > 20:
        raise ValueError("昵称不能超过 20 个字符。")

    return normalized


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render login page and verify submitted SMS codes."""
    next_url = request.args.get("next") or request.form.get("next") or url_for("main.index")
    nickname = request.form.get("nickname", "")
    phone = request.form.get("phone", "")

    if request.method == "POST":
        code = request.form.get("code", "")

        try:
            user_nickname = _normalize_nickname(nickname)
            user_phone = verify_code(phone, code, current_app.config)
            session["user_phone"] = user_phone
            session["user_nickname"] = user_nickname
            flash("登录成功。", "success")
            return redirect(next_url)
        except ValueError as exc:
            flash(str(exc), "error")

    return render_template(
        "login.html",
        next_url=next_url,
        nickname=nickname,
        phone=phone,
    )


@auth_bp.route("/send-code", methods=["POST"])
def send_code():
    """Send a verification code to the submitted phone number."""
    phone = request.form.get("phone", "")
    nickname = request.form.get("nickname", "")
    next_url = request.form.get("next") or url_for("main.index")

    try:
        normalized_nickname = _normalize_nickname(nickname)
        normalized_phone = send_verification_code(phone, current_app.config)
        flash("验证码已发送，请查收短信。开发环境请查看控制台输出。", "success")
        return render_template(
            "login.html",
            nickname=normalized_nickname,
            phone=normalized_phone,
            next_url=next_url,
        )
    except (ValueError, SmsSendError) as exc:
        flash(str(exc), "error")
        return render_template(
            "login.html",
            nickname=nickname,
            phone=phone,
            next_url=next_url,
        ), 400


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Log the current user out."""
    session.pop("user_phone", None)
    session.pop("user_nickname", None)
    flash("已退出登录。", "success")
    return redirect(url_for("auth.login"))
