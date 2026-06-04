from fastapi.testclient import TestClient

from backend.server import app
import backend.server as server_module


client = TestClient(app)


def test_store_products_endpoint_returns_active_content_items(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "list_store_products",
        lambda: [
            {
                "product_code": "role_item_miku_nt",
                "product_name": "Hatsune Miku NT",
                "product_type": "character_item",
                "cash_price_fen": 500,
                "point_price": 500,
                "status": "active",
                "payload": {"asset_path": "Defaults/Avatars/HatsuneMikuNT.vrm"},
            },
            {
                "product_code": "dance_item_world_is_mine",
                "product_name": "World is Mine Dance",
                "product_type": "dance_item",
                "cash_price_fen": 500,
                "point_price": 500,
                "status": "active",
                "payload": {"asset_path": "CustomDances/Defaults/MMD-World is Mine.unity3d"},
            },
            {
                "product_code": "music_item_world_is_mine",
                "product_name": "World is Mine Song",
                "product_type": "music_item",
                "cash_price_fen": 100,
                "point_price": 100,
                "status": "active",
                "payload": {"asset_path": "CustomDances/Defaults/World is Mine.mp3"},
            },
        ],
    )

    response = client.get("/store/products")

    assert response.status_code == 200
    data = response.json()
    assert [item["product_code"] for item in data] == [
        "role_item_miku_nt",
        "dance_item_world_is_mine",
        "music_item_world_is_mine",
    ]
    assert data[0]["cash_price_fen"] == 500
    assert data[0]["point_price"] == 500
    assert data[1]["product_type"] == "dance_item"
    assert data[2]["product_type"] == "music_item"
    assert data[2]["cash_price_fen"] == 100
    assert data[2]["point_price"] == 100
    assert data[2]["payload"]["asset_path"].endswith("World is Mine.mp3")


def test_me_endpoint_returns_membership_and_entitlements(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {
            "id": 101,
            "phone": "13800138000",
            "nickname": "owner",
            "avatar_url": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        server_module,
        "get_user_membership",
        lambda user_id: {
            "plan_code": "vip_monthly",
            "tier": "vip",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": {"model_access_level": "vip", "voice_access_level": "vip"},
        },
    )
    monkeypatch.setattr(
        server_module,
        "list_user_entitlements",
        lambda user_id: [
            {
                "entitlement_code": "role.miku_nt_default",
                "entitlement_type": "permanent",
                "source_product_code": "role_item_miku_nt",
                "status": "active",
                "expires_at": None,
                "payload": {"asset_path": "Defaults/Avatars/HatsuneMikuNT.vrm"},
            },
            {
                "entitlement_code": "dance.world_is_mine",
                "entitlement_type": "permanent",
                "source_product_code": "dance_item_world_is_mine",
                "status": "active",
                "expires_at": None,
                "payload": {"asset_path": "CustomDances/Defaults/MMD-World is Mine.unity3d"},
            },
            {
                "entitlement_code": "music.world_is_mine",
                "entitlement_type": "permanent",
                "source_product_code": "music_item_world_is_mine",
                "status": "active",
                "expires_at": None,
                "payload": {"asset_path": "CustomDances/Defaults/World is Mine.mp3"},
            },
        ],
    )

    response = client.get("/me", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["membership"]["tier"] == "vip"
    assert [item["entitlement_code"] for item in data["entitlements"]] == [
        "role.miku_nt_default",
        "dance.world_is_mine",
        "music.world_is_mine",
    ]
    assert data["entitlements"][0]["source_product_code"] == "role_item_miku_nt"
    assert data["entitlements"][2]["source_product_code"] == "music_item_world_is_mine"
