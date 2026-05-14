import json
import os
import smtplib
from email.message import EmailMessage

from library_app.config import EMAIL_CONFIG_FILE
from library_app.time_utils import now_local


def _parse_bool(value, default=True):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def load_email_config():
    default_config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "",
        "sender_name": "Arya Central Library",
        "sender_password": "",
        "use_tls": True,
    }

    if not EMAIL_CONFIG_FILE.exists():
        EMAIL_CONFIG_FILE.write_text(json.dumps(default_config, indent=2), encoding="utf-8")
        return default_config

    try:
        config = json.loads(EMAIL_CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_config

    merged = default_config | config
    merged["smtp_host"] = str(os.environ.get("LIBRARY_SMTP_HOST", merged.get("smtp_host", ""))).strip() or default_config["smtp_host"]
    merged["smtp_port"] = int(os.environ.get("LIBRARY_SMTP_PORT", merged.get("smtp_port", 587)) or 587)
    merged["sender_email"] = str(os.environ.get("LIBRARY_SMTP_SENDER_EMAIL", merged.get("sender_email", ""))).strip()
    merged["sender_name"] = str(os.environ.get("LIBRARY_SMTP_SENDER_NAME", merged.get("sender_name", default_config["sender_name"]))).strip() or default_config["sender_name"]
    merged["sender_password"] = str(os.environ.get("LIBRARY_SMTP_SENDER_PASSWORD", merged.get("sender_password", ""))).strip()
    merged["use_tls"] = _parse_bool(os.environ.get("LIBRARY_SMTP_USE_TLS", merged.get("use_tls", True)))
    return merged


def send_password_recovery_email(admin_email, requested_username, otp_code):
    config = load_email_config()
    admin_email = str(admin_email).strip()
    sender_email = str(config.get("sender_email", "")).strip()
    sender_password = str(config.get("sender_password", "")).strip()

    if not admin_email:
        return False, "Admin email is not configured yet."
    if not sender_email or not sender_password:
        return False, "Email sending is not configured yet. Add sender email and app password in environment variables or email_config.json."

    message = EmailMessage()
    message["Subject"] = "Arya Central Library Password Reset OTP"
    message["From"] = f"{config.get('sender_name', 'Arya Central Library')} <{sender_email}>"
    message["To"] = admin_email
    timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
    body = (
        "A password reset request was submitted for the library dashboard.\n\n"
        f"Username: {requested_username or 'Not provided'}\n"
        f"OTP: {otp_code}\n"
        f"Requested at: {timestamp}\n\n"
        "This OTP is valid for 10 minutes.\n"
        "Enter this OTP on the login page to set a new password."
    )
    message.set_content(body)

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=20) as server:
            server.ehlo()
            if config["use_tls"]:
                server.starttls()
                server.ehlo()
            server.login(sender_email, sender_password)
            server.send_message(message)
    except Exception as error:
        return False, f"Could not send recovery email: {error}"

    return True, f"OTP sent to {admin_email}."
