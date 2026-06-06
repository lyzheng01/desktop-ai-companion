import backend.business_store as store_module


def test_list_store_products_returns_remote_point_items_only():
    products = store_module.list_store_products()

    assert [item["product_code"] for item in products] == [
        "role_item_miku_nt_remote",
        "dance_item_world_is_mine_remote",
        "music_item_world_is_mine_remote",
    ]
    assert products[0]["product_type"] == "character_item"
    assert products[0]["point_price"] == 500
    assert products[0]["asset_key"] == "avatars/hatsune-miku-nt"
    assert products[1]["product_type"] == "dance_item"
    assert products[1]["point_price"] == 500
    assert products[1]["asset_version"] == "2026.06.04"
    assert products[2]["product_type"] == "music_item"
    assert products[2]["point_price"] == 100
    assert products[2]["payload"]["title"] == "World is Mine Song"


def test_get_user_points_balance_returns_zero_when_mysql_is_unconfigured(monkeypatch):
    monkeypatch.setattr(store_module, "mysql_is_configured", lambda: False)

    assert store_module.get_user_points_balance(101) == 0


def test_list_user_entitlements_returns_empty_list_when_mysql_is_unconfigured(monkeypatch):
    monkeypatch.setattr(store_module, "mysql_is_configured", lambda: False)

    assert store_module.list_user_entitlements(101) == []
