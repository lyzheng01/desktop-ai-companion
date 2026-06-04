import backend.business_store as store_module


def test_list_store_products_returns_active_items_with_hybrid_prices():
    products = store_module.list_store_products()

    assert [item["product_code"] for item in products] == [
        "role_item_miku_nt",
        "dance_item_world_is_mine",
        "music_item_world_is_mine",
    ]
    assert products[0]["product_type"] == "character_item"
    assert products[0]["cash_price_fen"] == 500
    assert products[0]["point_price"] == 500
    assert products[1]["product_type"] == "dance_item"
    assert products[1]["cash_price_fen"] == 500
    assert products[1]["point_price"] == 500
    assert products[2]["product_type"] == "music_item"
    assert products[2]["cash_price_fen"] == 100
    assert products[2]["point_price"] == 100
    assert products[2]["payload"]["asset_path"].endswith("World is Mine.mp3")


def test_list_user_entitlements_returns_empty_list_when_mysql_is_unconfigured(monkeypatch):
    monkeypatch.setattr(store_module, "mysql_is_configured", lambda: False)

    assert store_module.list_user_entitlements(101) == []
