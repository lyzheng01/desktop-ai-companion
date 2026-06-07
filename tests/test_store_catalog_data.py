import backend.business_store as store_module


def test_list_store_products_returns_remote_point_items_only():
    products = store_module.list_store_products()

    assert products
    assert {item["product_type"] for item in products} == {"character_item", "dance_item"}

    avatar_products = [item for item in products if item["product_type"] == "character_item"]
    dance_products = [item for item in products if item["product_type"] == "dance_item"]

    assert avatar_products
    assert dance_products
    assert all(item["point_price"] == 500 for item in avatar_products)
    assert all(item["asset_key"].startswith("avatars/") for item in avatar_products)
    assert all(item["point_price"] == 100 for item in dance_products)
    assert all(item["asset_key"].startswith("dances/") for item in dance_products)


def test_get_user_points_balance_returns_zero_when_mysql_is_unconfigured(monkeypatch):
    monkeypatch.setattr(store_module, "mysql_is_configured", lambda: False)

    assert store_module.get_user_points_balance(101) == 0


def test_list_user_entitlements_returns_empty_list_when_mysql_is_unconfigured(monkeypatch):
    monkeypatch.setattr(store_module, "mysql_is_configured", lambda: False)

    assert store_module.list_user_entitlements(101) == []


def test_list_asset_catalog_products_scans_backend_asset_inventory(tmp_path, monkeypatch):
    remote_root = tmp_path / "remote-assets"
    avatars_dir = tmp_path / "avatars"
    dances_dir = tmp_path / "dances"
    remote_root.mkdir()
    avatars_dir.mkdir()
    dances_dir.mkdir()
    (avatars_dir / "Alpha.vrm").write_bytes(b"avatar-a")
    (dances_dir / "Dance One.unity3d").write_bytes(b"dance-a")

    monkeypatch.setattr(store_module, "REMOTE_ASSET_ROOT", remote_root)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_AVATAR_DIR", avatars_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_DANCE_DIR", dances_dir)

    products = store_module.list_asset_catalog_products()

    assert len(products) == 2
    assert [item["product_type"] for item in products] == ["character_item", "dance_item"]
    assert products[0]["point_price"] == 500
    assert products[0]["asset_key"].startswith("avatars/")
    assert products[1]["point_price"] == 100
    assert products[1]["asset_key"].startswith("dances/")


def test_build_asset_download_manifest_uses_backend_static_assets_paths(tmp_path, monkeypatch):
    static_assets_dir = tmp_path / "static_assets"
    remote_root = static_assets_dir / "remote-assets"
    avatars_dir = static_assets_dir / "remote-assets" / "avatars"
    dances_dir = static_assets_dir / "remote-assets" / "dances"
    avatars_dir.mkdir(parents=True)
    dances_dir.mkdir(parents=True)
    asset_path = avatars_dir / "Alpha.vrm"
    asset_path.write_bytes(b"avatar-a")

    monkeypatch.setattr(store_module, "STATIC_ASSET_ROOT", static_assets_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_ROOT", remote_root)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_AVATAR_DIR", avatars_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_DANCE_DIR", dances_dir)

    product = store_module.list_asset_catalog_products(kind="avatar")[0]
    manifest = store_module.build_asset_download_manifest(product["product_code"], "http://127.0.0.1:8080")

    assert manifest["download_url"] == "http://127.0.0.1:8080/static-assets/remote-assets/avatars/Alpha.vrm"
    assert manifest["files"][0]["path"] == "Alpha.vrm"
    assert manifest["files"][0]["size"] == len(b"avatar-a")


def test_list_asset_catalog_products_prefers_cached_index(tmp_path, monkeypatch):
    static_assets_dir = tmp_path / "static_assets"
    remote_root = static_assets_dir / "remote-assets"
    covers_dir = static_assets_dir / "covers"
    remote_root.mkdir(parents=True)
    covers_dir.mkdir(parents=True)
    (covers_dir / "character_item_cached_alpha.png").write_bytes(b"\x89PNG\r\n\x1a\ncached")
    index_path = remote_root / "catalog-index.json"
    index_path.write_text(
        """
[
  {
    "product_code": "character_item_cached_alpha",
    "product_name": "Alpha",
    "product_type": "character_item",
    "point_price": 500,
    "status": "active",
    "asset_key": "avatars/alpha",
    "asset_version": "cached123",
    "cover_url": "/static-assets/covers/character_item_cached_alpha.png",
    "payload": {
      "title": "Alpha",
      "source_filename": "Alpha.vrm",
      "source_relative_path": "remote-assets/avatars/Alpha.vrm",
      "asset_hash": "sha256:test",
      "asset_size": 8,
      "kind": "avatar",
      "cover_path": "/static-assets/covers/character_item_cached_alpha.png"
    }
  }
]
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(store_module, "STATIC_ASSET_ROOT", static_assets_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_ROOT", remote_root)

    products = store_module.list_asset_catalog_products(kind="avatar")

    assert len(products) == 1
    assert products[0]["product_code"] == "character_item_cached_alpha"
    assert products[0]["cover_url"] == "/static-assets/covers/character_item_cached_alpha.png"


def test_list_asset_catalog_products_rebuilds_stale_cached_index_without_cover_url_for_vrm(tmp_path, monkeypatch):
    static_assets_dir = tmp_path / "static_assets"
    remote_root = static_assets_dir / "remote-assets"
    avatars_dir = remote_root / "avatars"
    dances_dir = remote_root / "dances"
    covers_dir = static_assets_dir / "covers"
    avatars_dir.mkdir(parents=True)
    dances_dir.mkdir(parents=True)
    covers_dir.mkdir(parents=True)

    source_vrm = store_module.REMOTE_ASSET_AVATAR_DIR / "CamomeCamome.vrm"
    target_vrm = avatars_dir / "CamomeCamome.vrm"
    target_vrm.write_bytes(source_vrm.read_bytes())

    index_path = remote_root / "catalog-index.json"
    index_path.write_text(
        """
[
  {
    "product_code": "character_item_cached_camome",
    "product_name": "CamomeCamome",
    "product_type": "character_item",
    "point_price": 500,
    "status": "active",
    "asset_key": "avatars/camomecamome",
    "asset_version": "cached123",
    "cover_url": "",
    "payload": {
      "title": "CamomeCamome",
      "source_filename": "CamomeCamome.vrm",
      "source_relative_path": "remote-assets/avatars/CamomeCamome.vrm",
      "asset_hash": "sha256:test",
      "asset_size": 8,
      "kind": "avatar"
    }
  }
]
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(store_module, "STATIC_ASSET_ROOT", static_assets_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_ROOT", remote_root)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_AVATAR_DIR", avatars_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_DANCE_DIR", dances_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_COVER_DIR", covers_dir)

    products = store_module.list_asset_catalog_products(kind="avatar")

    assert len(products) == 1
    assert products[0]["product_code"] != "character_item_cached_camome"
    assert products[0]["cover_url"].startswith("/static-assets/covers/")
    assert products[0]["payload"]["cover_path"] == products[0]["cover_url"]
