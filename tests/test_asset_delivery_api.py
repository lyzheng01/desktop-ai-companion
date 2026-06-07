from fastapi.testclient import TestClient

from backend.server import app
import backend.server as server_module


client = TestClient(app)


def test_download_manifest_endpoint_returns_manifest_for_owned_product(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {"id": 101, "phone": "13800138000", "nickname": "owner", "avatar_url": None, "status": "active"},
    )
    monkeypatch.setattr(
        server_module,
        "get_download_manifest_for_user_product",
        lambda user_id, product_code: {
            "product_code": product_code,
            "asset_key": "music/world-is-mine",
            "asset_version": "2026.06.04",
            "asset_hash": "sha256:abc123",
            "asset_size": 123456,
            "download_url": "https://assets.example.com/music/world-is-mine.zip",
            "files": [
                {"path": "World is Mine.mp3", "size": 123456},
            ],
        },
    )

    response = client.get(
        "/assets/download-manifest/music_item_world_is_mine_remote",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["asset_key"] == "music/world-is-mine"
    assert data["asset_version"] == "2026.06.04"
    assert data["files"][0]["path"] == "World is Mine.mp3"


def test_download_manifest_endpoint_rejects_unowned_product(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {"id": 101, "phone": "13800138000", "nickname": "owner", "avatar_url": None, "status": "active"},
    )

    def _raise_unowned(user_id, product_code):
        raise PermissionError("Product not owned")

    monkeypatch.setattr(server_module, "get_download_manifest_for_user_product", _raise_unowned)

    response = client.get(
        "/assets/download-manifest/music_item_world_is_mine_remote",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Product not owned"
