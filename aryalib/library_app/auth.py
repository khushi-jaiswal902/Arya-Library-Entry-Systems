import hashlib
import hmac
import json
import os
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import timedelta

from library_app.config import (
    ADMIN_CONFIG_FILE,
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
)
from library_app.time_utils import now_utc

PASSWORD_RESET_OTP = {}
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 390000
SESSION_TIMEOUT = timedelta(hours=8)
SESSION_TOKEN_VERSION = 1


def _default_credentials():
    username = os.environ.get("LIBRARY_ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME).strip() or DEFAULT_ADMIN_USERNAME
    password = os.environ.get("LIBRARY_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    email = os.environ.get("LIBRARY_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip()
    return {
        "username": username,
        "password_hash": hash_password(password),
        "email": email,
    }


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, password_hash):
    if not password_hash:
        return False

    try:
        algorithm, iterations_text, salt_hex, digest_hex = password_hash.split("$", 3)
    except ValueError:
        return hmac.compare_digest(password, password_hash)

    if algorithm != PASSWORD_HASH_PREFIX:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations_text),
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def _write_credentials(payload):
    ADMIN_CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _b64_encode(value):
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64_decode(value):
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _session_secret():
    explicit_secret = os.environ.get("LIBRARY_SESSION_SECRET", "").strip()
    if explicit_secret:
        return explicit_secret.encode("utf-8")

    env_password = os.environ.get("LIBRARY_ADMIN_PASSWORD", "")
    if env_password:
        return env_password.encode("utf-8")

    credentials = load_admin_credentials()
    return credentials.get("password_hash", DEFAULT_ADMIN_PASSWORD).encode("utf-8")


def _sign_session_payload(payload_bytes):
    return hmac.new(_session_secret(), payload_bytes, hashlib.sha256).hexdigest()


def verify_admin_password(password, credentials):
    env_password = credentials.get("password")
    if env_password is not None:
        return hmac.compare_digest(password, env_password)
    return verify_password(password, credentials.get("password_hash", ""))


def mask_email(email):
    email = str(email or "").strip()
    if "@" not in email:
        return ""
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 2:
        visible_local = local_part[:1]
    else:
        visible_local = f"{local_part[:2]}{'*' * max(len(local_part) - 2, 1)}"
    return f"{visible_local}@{domain}"


def load_admin_credentials():
    env_username = os.environ.get("LIBRARY_ADMIN_USERNAME", "").strip()
    env_password = os.environ.get("LIBRARY_ADMIN_PASSWORD", "")
    env_email = os.environ.get("LIBRARY_ADMIN_EMAIL", "").strip()
    if env_username and env_password:
        return {
            "username": env_username,
            "password": env_password,
            "email": env_email,
        }

    default_credentials = _default_credentials()

    if not ADMIN_CONFIG_FILE.exists():
        return _write_credentials(default_credentials)

    try:
        config = json.loads(ADMIN_CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _write_credentials(default_credentials)

    username = str(config.get("username", "")).strip()
    email = str(config.get("email", default_credentials["email"])).strip()
    password_hash = str(config.get("password_hash", "")).strip()
    legacy_password = str(config.get("password", ""))

    if not username:
        return _write_credentials(default_credentials)

    if password_hash:
        normalized = {
            "username": username,
            "password_hash": password_hash,
            "email": email,
        }
        if normalized != config:
            return _write_credentials(normalized)
        return normalized

    if legacy_password:
        return _write_credentials(
            {
                "username": username,
                "password_hash": hash_password(legacy_password),
                "email": email,
            }
        )

    return _write_credentials(default_credentials)


def create_session(username):
    payload = {
        "v": SESSION_TOKEN_VERSION,
        "u": username,
        "exp": int((now_utc() + SESSION_TIMEOUT).timestamp()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = _sign_session_payload(payload_bytes)
    return f"{_b64_encode(payload_bytes)}.{signature}"


def remove_session(session_id):
    return None


def is_authenticated(session_id):
    if not session_id:
        return False

    try:
        payload_b64, signature = session_id.split(".", 1)
        payload_bytes = _b64_decode(payload_b64)
    except (ValueError, TypeError):
        return False

    expected_signature = _sign_session_payload(payload_bytes)
    if not hmac.compare_digest(signature, expected_signature):
        return False

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False

    if payload.get("v") != SESSION_TOKEN_VERSION:
        return False
    if not payload.get("u"):
        return False

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        return False

    if now_utc().timestamp() > expires_at:
        return False

    credentials = load_admin_credentials()
    return payload["u"] == credentials["username"]


def save_admin_credentials(username, password, email):
    payload = {
        "username": username,
        "password_hash": hash_password(password),
        "email": email,
    }
    return _write_credentials(payload)


def create_password_reset_otp():
    return f"{secrets.randbelow(1000000):06d}"


def store_password_reset_otp(username, code):
    PASSWORD_RESET_OTP[username] = {
        "code": code,
        "expires_at": now_utc() + timedelta(minutes=10),
    }


def verify_password_reset_otp(username, code):
    otp_data = PASSWORD_RESET_OTP.get(username)
    if not otp_data:
        return False, "No OTP request found for this username."
    if now_utc() > otp_data["expires_at"]:
        PASSWORD_RESET_OTP.pop(username, None)
        return False, "OTP expired. Please request a new one."
    if str(code).strip() != otp_data["code"]:
        return False, "Invalid OTP."
    return True, ""


def clear_password_reset_otp(username):
    PASSWORD_RESET_OTP.pop(username, None)
