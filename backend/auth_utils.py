import base64
import hashlib
import hmac
import json
import os
import secrets
import time


ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("DESKTOP_AI_COMPANION_ACCESS_TOKEN_TTL", "7200"))
REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("DESKTOP_AI_COMPANION_REFRESH_TOKEN_TTL", str(30 * 24 * 60 * 60)))


def _get_auth_secret() -> str:
    return os.getenv("DESKTOP_AI_COMPANION_AUTH_SECRET", "dev-auth-secret-change-me")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def sign_access_token(user_id: int, phone: str) -> str:
    payload = {
        "uid": user_id,
        "phone": phone,
        "exp": int(time.time()) + ACCESS_TOKEN_TTL_SECONDS,
    }
    payload_raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_part = _b64url_encode(payload_raw)
    signature = hmac.new(_get_auth_secret().encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64url_encode(signature)}"


def verify_access_token(token: str) -> dict | None:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = hmac.new(
        _get_auth_secret().encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256
    ).digest()
    actual_signature = _b64url_decode(signature_part)
    if not hmac.compare_digest(expected_signature, actual_signature):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None

    if int(payload.get("exp", 0)) <= int(time.time()):
        return None
    if not isinstance(payload.get("uid"), int):
        return None
    if not isinstance(payload.get("phone"), str):
        return None
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_sms_code(phone: str, scene: str, code: str) -> str:
    base = f"{phone}:{scene}:{code}:{_get_auth_secret()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
