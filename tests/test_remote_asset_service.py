from datetime import datetime

import backend.server as server_module


def test_acquire_remote_asset_builds_manifest_before_deducting_points(monkeypatch):
    calls: list[str] = []

    def _build_manifest(product_code: str, public_base_url: str):
        calls.append("build")
        raise ValueError("Asset file not found")

    def _redeem_points(user_id: int, product_code: str):
        calls.append("redeem")
        raise AssertionError("points should not be redeemed when manifest build fails")

    monkeypatch.setattr(server_module, "build_asset_download_manifest", _build_manifest)
    monkeypatch.setattr(server_module, "redeem_store_product", _redeem_points)

    try:
        server_module.acquire_remote_asset_for_user(101, "avatar_miku_nt_v2")
    except ValueError as error:
        assert str(error) == "Asset file not found"
    else:
        raise AssertionError("expected manifest build failure")

    assert calls == ["build"]


def test_acquire_remote_asset_returns_manifest_after_successful_deduction(monkeypatch):
    manifest = {
        "product_code": "avatar_miku_nt_v2",
        "asset_key": "avatars/miku-nt-v2",
        "asset_version": "2026.06.05",
        "asset_hash": "sha256:test",
        "asset_size": 123,
        "download_url": "http://127.0.0.1:8080/static-assets/remote-assets/avatars/Alpha.vrm",
        "files": [{"path": "Alpha.vrm", "size": 123}],
    }
    expiry = int(datetime(2026, 6, 11, 0, 0, 0).timestamp())

    monkeypatch.setattr(server_module, "build_asset_download_manifest", lambda product_code, public_base_url: manifest)
    monkeypatch.setattr(
        server_module,
        "redeem_store_product",
        lambda user_id, product_code: {
            "points_balance": 700,
            "entitlement": {
                "entitlement_code": "dance.world_is_mine",
                "entitlement_type": "permanent",
                "source_product_code": product_code,
                "status": "active",
                "expires_at": None,
                "payload": {"asset_key": "dances/world-is-mine"},
            },
        },
    )
    monkeypatch.setattr(server_module, "sign_local_token", lambda payload, ttl_seconds: "retry-token-1")
    monkeypatch.setattr(server_module, "verify_local_token", lambda token: {"exp": expiry})

    result = server_module.acquire_remote_asset_for_user(101, "avatar_miku_nt_v2")

    assert result["points_balance"] == 700
    assert result["retry_token"] == "retry-token-1"
    assert result["manifest"] == manifest
