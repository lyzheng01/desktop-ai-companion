from fastapi.testclient import TestClient

from backend.server import app
import backend.server as server_module


client = TestClient(app)


def test_assets_catalog_endpoint_returns_avatar_items(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "list_asset_catalog_products",
        lambda kind=None: [
            {
                "product_code": "avatar_miku_nt_v2",
                "product_name": "Hatsune Miku NT",
                "product_type": "character_item",
                "point_price": 500,
                "status": "active",
                "asset_key": "avatars/miku-nt-v2",
                "asset_version": "2026.06.05",
                "cover_url": "/static-assets/covers/avatar_miku_nt_v2.png",
                "payload": {"title": "Hatsune Miku NT"},
            }
        ],
    )

    response = client.get("/assets/catalog?kind=avatar")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["product_code"] == "avatar_miku_nt_v2"
    assert data[0]["cover_url"] == "/static-assets/covers/avatar_miku_nt_v2.png"


def test_assets_acquire_endpoint_returns_manifest_and_retry_token(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {"id": 101, "phone": "13800138000", "nickname": "owner", "avatar_url": None, "status": "active"},
    )
    monkeypatch.setattr(
        server_module,
        "acquire_remote_asset_for_user",
        lambda user_id, product_code, retry_token=None: {
            "points_balance": 700,
            "retry_token": "retry-token-1",
            "retry_token_expires_at": None,
            "manifest": {
                "product_code": product_code,
                "asset_key": "avatars/miku-nt-v2",
                "asset_version": "2026.06.05",
                "asset_hash": "sha256:test",
                "asset_size": 123,
                "download_url": "http://127.0.0.1:8080/static-assets/avatars/avatar_miku_nt_v2/2026.06.05.zip",
                "files": [{"path": "HatsuneMikuNT.vrm", "size": 123}],
            },
        },
    )

    response = client.post(
        "/assets/acquire",
        json={"product_code": "avatar_miku_nt_v2"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["points_balance"] == 700
    assert data["retry_token"] == "retry-token-1"
    assert data["manifest"]["asset_key"] == "avatars/miku-nt-v2"


def test_point_topup_payment_page_renders_html(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "build_point_topup_payment_page_context",
        lambda order_no: {
            "order_no": order_no,
            "product_name": "500 Points",
            "amount_fen": 500,
            "code_url": "weixin://wxpay/mock",
            "status_token": "status-token-1",
            "status_path": f"/payments/points/{order_no}/status?token=status-token-1",
        },
    )

    response = client.get("/payments/points/DACP202606050001")

    assert response.status_code == 200
    assert "DACP202606050001" in response.text
    assert "/payments/points/DACP202606050001/status?token=status-token-1" in response.text


def test_point_topup_payment_status_endpoint_returns_public_status(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "get_point_topup_public_status",
        lambda order_no, token: {
            "order_no": order_no,
            "status": "paid",
            "paid_at": None,
        },
    )

    response = client.get("/payments/points/DACP202606050001/status?token=status-token-1")

    assert response.status_code == 200
    data = response.json()
    assert data["order_no"] == "DACP202606050001"
    assert data["status"] == "paid"
