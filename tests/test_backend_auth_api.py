from fastapi.testclient import TestClient

from backend.server import app
import backend.server as server_module


client = TestClient(app)


def _session_payload(user: dict, access_token: str = "access-token", refresh_token: str = "refresh-token") -> dict:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "phone": user["phone"],
            "nickname": user.get("nickname"),
            "avatar_url": user.get("avatar_url"),
            "status": user.get("status", "active"),
        },
        "membership": {
            "plan_code": "free",
            "tier": "free",
            "status": "active",
        },
    }


def test_register_endpoint_creates_new_user_and_returns_session(monkeypatch):
    created = {}

    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(server_module, "validate_phone_number", lambda phone: phone)
    monkeypatch.setattr(server_module, "consume_sms_code", lambda phone, scene, code_hash: True)
    monkeypatch.setattr(server_module, "hash_user_password", lambda password: f"hash::{password}")
    monkeypatch.setattr(server_module, "get_user_by_phone", lambda phone: None)

    def fake_create_user_with_password(phone: str, password_hash: str) -> dict:
        created["phone"] = phone
        created["password_hash"] = password_hash
        return {
            "id": 11,
            "phone": phone,
            "nickname": "用户8000",
            "status": "active",
        }

    monkeypatch.setattr(server_module, "create_user_with_password", fake_create_user_with_password)
    monkeypatch.setattr(
        server_module,
        "issue_auth_session",
        lambda user, device_id, device_name: _session_payload(user, "access-new", "refresh-new"),
    )

    response = client.post(
        "/auth/register",
        json={
            "phone": "13800138000",
            "password": "123456",
            "code": "123456",
            "device_id": "device-1",
            "device_name": "Mate-Engine",
            "scene": "register",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access-new"
    assert created == {"phone": "13800138000", "password_hash": "hash::123456"}


def test_register_endpoint_migrates_existing_sms_user_without_password(monkeypatch):
    updated = {}
    existing_user = {
        "id": 12,
        "phone": "13800138000",
        "nickname": "用户8000",
        "status": "active",
        "password_hash": None,
    }

    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(server_module, "validate_phone_number", lambda phone: phone)
    monkeypatch.setattr(server_module, "consume_sms_code", lambda phone, scene, code_hash: True)
    monkeypatch.setattr(server_module, "hash_user_password", lambda password: f"hash::{password}")
    monkeypatch.setattr(server_module, "get_user_by_phone", lambda phone: existing_user)

    def fake_set_user_password(user_id: int, password_hash: str) -> dict:
        updated["user_id"] = user_id
        updated["password_hash"] = password_hash
        return {
            **existing_user,
            "password_hash": password_hash,
        }

    monkeypatch.setattr(server_module, "set_user_password", fake_set_user_password)
    monkeypatch.setattr(
        server_module,
        "issue_auth_session",
        lambda user, device_id, device_name: _session_payload(user, "access-migrated", "refresh-migrated"),
    )

    response = client.post(
        "/auth/register",
        json={
            "phone": "13800138000",
            "password": "123456",
            "code": "123456",
            "device_id": "device-2",
            "device_name": "Mate-Engine",
            "scene": "register",
        },
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] == "refresh-migrated"
    assert updated == {"user_id": 12, "password_hash": "hash::123456"}


def test_register_endpoint_rejects_existing_user_with_password(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(server_module, "validate_phone_number", lambda phone: phone)
    monkeypatch.setattr(server_module, "consume_sms_code", lambda phone, scene, code_hash: True)
    monkeypatch.setattr(
        server_module,
        "get_user_by_phone",
        lambda phone: {"id": 13, "phone": phone, "status": "active", "password_hash": "hash::123456"},
    )

    response = client.post(
        "/auth/register",
        json={
            "phone": "13800138000",
            "password": "123456",
            "code": "123456",
        },
    )

    assert response.status_code == 409


def test_password_login_endpoint_returns_session(monkeypatch):
    user = {
        "id": 14,
        "phone": "13800138000",
        "nickname": "用户8000",
        "status": "active",
        "password_hash": "hash::123456",
    }

    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(server_module, "validate_phone_number", lambda phone: phone)
    monkeypatch.setattr(server_module, "get_user_by_phone", lambda phone: user)
    monkeypatch.setattr(server_module, "verify_user_password", lambda password, password_hash: password == "123456" and password_hash == "hash::123456")
    monkeypatch.setattr(
        server_module,
        "issue_auth_session",
        lambda auth_user, device_id, device_name: _session_payload(auth_user, "access-login", "refresh-login"),
    )

    response = client.post(
        "/auth/password/login",
        json={
            "phone": "13800138000",
            "password": "123456",
            "device_id": "device-3",
            "device_name": "Mate-Engine",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access-login"


def test_password_login_endpoint_rejects_wrong_password(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(server_module, "validate_phone_number", lambda phone: phone)
    monkeypatch.setattr(
        server_module,
        "get_user_by_phone",
        lambda phone: {"id": 15, "phone": phone, "status": "active", "password_hash": "hash::123456"},
    )
    monkeypatch.setattr(server_module, "verify_user_password", lambda password, password_hash: False)

    response = client.post(
        "/auth/password/login",
        json={
            "phone": "13800138000",
            "password": "654321",
        },
    )

    assert response.status_code == 401


def test_send_sms_endpoint_rejects_missing_captcha_when_tencent_captcha_enabled(monkeypatch):
    send_attempted = {"value": False}

    monkeypatch.setenv("DESKTOP_AI_COMPANION_CAPTCHA_PROVIDER", "tencent")
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(server_module, "validate_phone_number", lambda phone: phone)
    monkeypatch.setattr(server_module, "generate_sms_code", lambda: "123456")
    monkeypatch.setattr(server_module, "hash_sms_code", lambda phone, scene, code: f"hash::{phone}::{scene}::{code}")
    monkeypatch.setattr(server_module, "create_sms_code", lambda *args, **kwargs: None)

    def fake_send_login_sms(phone: str, code: str) -> dict:
        send_attempted["value"] = True
        return {"provider": "mock", "debug_code": code}

    monkeypatch.setattr(server_module, "send_login_sms", fake_send_login_sms)

    response = client.post(
        "/auth/sms/send",
        json={
            "phone": "13800138000",
            "scene": "register",
        },
    )

    assert response.status_code == 400
    assert send_attempted["value"] is False


def test_send_sms_endpoint_verifies_tencent_captcha_before_sending(monkeypatch):
    captured = {}

    monkeypatch.setenv("DESKTOP_AI_COMPANION_CAPTCHA_PROVIDER", "tencent")
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(server_module, "validate_phone_number", lambda phone: phone)
    monkeypatch.setattr(server_module, "generate_sms_code", lambda: "654321")
    monkeypatch.setattr(server_module, "hash_sms_code", lambda phone, scene, code: f"hash::{phone}::{scene}::{code}")

    def fake_verify_sms_send_captcha(phone: str, scene: str, captcha_ticket: str, captcha_randstr: str, user_ip: str | None) -> None:
        captured["captcha"] = {
            "phone": phone,
            "scene": scene,
            "captcha_ticket": captcha_ticket,
            "captcha_randstr": captcha_randstr,
            "user_ip": user_ip,
        }

    def fake_send_login_sms(phone: str, code: str) -> dict:
        captured["sms"] = {"phone": phone, "code": code}
        return {"provider": "mock", "debug_code": code}

    def fake_create_sms_code(phone: str, scene: str, code_hash: str, expires_at, request_ip: str | None) -> None:
        captured["stored"] = {
            "phone": phone,
            "scene": scene,
            "code_hash": code_hash,
            "request_ip": request_ip,
        }

    monkeypatch.setattr(server_module, "verify_sms_send_captcha", fake_verify_sms_send_captcha, raising=False)
    monkeypatch.setattr(server_module, "send_login_sms", fake_send_login_sms)
    monkeypatch.setattr(server_module, "create_sms_code", fake_create_sms_code)

    response = client.post(
        "/auth/sms/send",
        json={
            "phone": "13800138000",
            "scene": "register",
            "captcha_ticket": "ticket-123",
            "captcha_randstr": "rand-123",
        },
    )

    assert response.status_code == 200
    assert captured["captcha"] == {
        "phone": "13800138000",
        "scene": "register",
        "captcha_ticket": "ticket-123",
        "captcha_randstr": "rand-123",
        "user_ip": "testclient",
    }
    assert captured["sms"] == {"phone": "13800138000", "code": "654321"}
    assert captured["stored"]["phone"] == "13800138000"
    assert captured["stored"]["scene"] == "register"


def test_send_sms_endpoint_returns_429_when_provider_hits_daily_limit(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(server_module, "validate_phone_number", lambda phone: phone)
    monkeypatch.setattr(server_module, "generate_sms_code", lambda: "123456")
    monkeypatch.setattr(server_module, "hash_sms_code", lambda phone, scene, code: f"hash::{phone}::{scene}::{code}")
    monkeypatch.setattr(
        server_module,
        "send_login_sms",
        lambda phone, code: (_ for _ in ()).throw(
            RuntimeError("the number of sms messages sent from a single mobile number every day exceeds the upper limit")
        ),
    )
    monkeypatch.setattr(server_module, "create_sms_code", lambda *args, **kwargs: None)

    response = client.post(
        "/auth/sms/send",
        json={
            "phone": "13800138000",
            "scene": "register",
        },
    )

    assert response.status_code == 429
    assert "upper limit" in response.json()["detail"]
