"""
Real notification delivery channels — Telegram and SMTP email.

These are best-effort: if a channel isn't configured, sending is a no-op that
returns False. Failures never raise to the caller (price monitor / API), they
are logged and swallowed so a broken channel can't crash a scan cycle.
"""
import smtplib
import traceback
from email.mime.text import MIMEText

import requests

import config


def telegram_configured() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN)


def email_configured() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD)


def send_telegram(chat_id: str, text: str) -> bool:
    """Send a Telegram message. `chat_id` is the user's Telegram chat id."""
    if not telegram_configured() or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception:
        traceback.print_exc()
        return False


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a plain-text email via configured SMTP server."""
    if not email_configured() or not to_email:
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = config.SMTP_FROM
        msg["To"] = to_email

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_FROM, [to_email], msg.as_string())
        return True
    except Exception:
        traceback.print_exc()
        return False


def deliver_to_user(user: dict, title: str, message: str) -> dict:
    """
    Best-effort delivery of a notification to a user across all enabled channels.

    `user` is a row dict from the users table. We use:
      - email (if user.notify_email and SMTP configured)
      - telegram (if user.push_subscription holds a telegram chat id)

    Returns a dict describing which channels succeeded.
    """
    result = {"email": False, "telegram": False}
    if not user:
        return result

    # Email channel
    if user.get("notify_email") and user.get("email"):
        result["email"] = send_email(user["email"], title, f"{title}\n\n{message}")

    # Telegram channel — push_subscription stores the chat id for simplicity.
    chat_id = (user.get("push_subscription") or "").strip()
    if chat_id:
        result["telegram"] = send_telegram(chat_id, f"<b>{title}</b>\n{message}")

    return result
