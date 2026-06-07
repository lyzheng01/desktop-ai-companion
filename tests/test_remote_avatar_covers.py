from pathlib import Path

import backend.business_store as store_module


def test_extract_vrm_embedded_cover_writes_png(tmp_path):
    source_vrm = Path(
        "E:/python/desktop-ai-companion/backend/static_assets/remote-assets/avatars/CamomeCamome.vrm"
    )
    covers_dir = tmp_path / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    cover_path = store_module._extract_vrm_embedded_cover(
        source_vrm,
        product_code="character_item_camome_test",
        covers_dir=covers_dir,
    )

    assert cover_path is not None
    assert cover_path.exists()
    assert cover_path.suffix.lower() == ".png"
    assert cover_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_list_asset_catalog_products_includes_generated_cover_url_for_vrm(tmp_path, monkeypatch):
    static_assets_dir = tmp_path / "static_assets"
    remote_root = static_assets_dir / "remote-assets"
    avatars_dir = remote_root / "avatars"
    dances_dir = remote_root / "dances"
    covers_dir = static_assets_dir / "covers"
    avatars_dir.mkdir(parents=True)
    dances_dir.mkdir(parents=True)
    covers_dir.mkdir(parents=True)

    source_vrm = Path(
        "E:/python/desktop-ai-companion/backend/static_assets/remote-assets/avatars/CamomeCamome.vrm"
    )
    target_vrm = avatars_dir / "CamomeCamome.vrm"
    target_vrm.write_bytes(source_vrm.read_bytes())

    monkeypatch.setattr(store_module, "STATIC_ASSET_ROOT", static_assets_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_ROOT", remote_root)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_AVATAR_DIR", avatars_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_DANCE_DIR", dances_dir)

    products = store_module.list_asset_catalog_products(kind="avatar")

    assert len(products) == 1
    assert products[0]["product_type"] == "character_item"
    assert products[0]["cover_url"].startswith("/static-assets/covers/")
    assert products[0]["payload"]["cover_path"] == products[0]["cover_url"]
    generated_cover = static_assets_dir / products[0]["cover_url"].removeprefix("/static-assets/")
    assert generated_cover.exists()


def test_list_asset_catalog_products_uses_english_avatar_display_name_mapping(tmp_path, monkeypatch):
    static_assets_dir = tmp_path / "static_assets"
    remote_root = static_assets_dir / "remote-assets"
    avatars_dir = remote_root / "avatars"
    dances_dir = remote_root / "dances"
    covers_dir = static_assets_dir / "covers"
    avatars_dir.mkdir(parents=True)
    dances_dir.mkdir(parents=True)
    covers_dir.mkdir(parents=True)

    source_vrm = Path(
        "E:/python/desktop-ai-companion/backend/static_assets/remote-assets/avatars/CamomeCamome.vrm"
    )
    target_vrm = avatars_dir / "CamomeCamome.vrm"
    target_vrm.write_bytes(source_vrm.read_bytes())

    monkeypatch.setattr(store_module, "STATIC_ASSET_ROOT", static_assets_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_ROOT", remote_root)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_AVATAR_DIR", avatars_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_DANCE_DIR", dances_dir)

    products = store_module.list_asset_catalog_products(kind="avatar")

    assert len(products) == 1
    assert products[0]["product_name"] == "Momo"
    assert products[0]["payload"]["title"] == "Momo"


def test_select_vrm_fallback_image_index_prefers_face_named_image():
    document = {
        "images": [
            {"name": "衣服"},
            {"name": "脸"},
            {"name": "头发"},
        ],
        "textures": [
            {"source": 0},
            {"source": 1},
            {"source": 2},
        ],
        "materials": [
            {"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}},
            {"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}},
            {"pbrMetallicRoughness": {"baseColorTexture": {"index": 1}}},
        ],
    }

    image_index = store_module._select_vrm_fallback_image_index(document)

    assert image_index == 1


def test_list_asset_catalog_products_generates_fallback_cover_for_vrm_without_thumbnail(tmp_path, monkeypatch):
    static_assets_dir = tmp_path / "static_assets"
    remote_root = static_assets_dir / "remote-assets"
    avatars_dir = remote_root / "avatars"
    dances_dir = remote_root / "dances"
    covers_dir = static_assets_dir / "covers"
    avatars_dir.mkdir(parents=True)
    dances_dir.mkdir(parents=True)
    covers_dir.mkdir(parents=True)

    source_vrm = Path(
        "E:/python/desktop-ai-companion/backend/static_assets/remote-assets/avatars/6823478844411844649.vrm"
    )
    target_vrm = avatars_dir / "6823478844411844649.vrm"
    target_vrm.write_bytes(source_vrm.read_bytes())

    monkeypatch.setattr(store_module, "STATIC_ASSET_ROOT", static_assets_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_ROOT", remote_root)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_AVATAR_DIR", avatars_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_DANCE_DIR", dances_dir)

    products = store_module.list_asset_catalog_products(kind="avatar")

    assert len(products) == 1
    assert products[0]["cover_url"].startswith("/static-assets/covers/")
    assert products[0]["payload"]["cover_path"] == products[0]["cover_url"]
    generated_cover = static_assets_dir / products[0]["cover_url"].removeprefix("/static-assets/")
    assert generated_cover.exists()
    assert generated_cover.suffix.lower() == ".png"
    assert generated_cover.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert products[0]["product_name"] == "Chibi"
    assert products[0]["payload"]["title"] == "Chibi"


def test_cached_remote_asset_products_without_kind_do_not_apply_avatar_name_mapping(tmp_path, monkeypatch):
    static_assets_dir = tmp_path / "static_assets"
    remote_root = static_assets_dir / "remote-assets"
    avatars_dir = remote_root / "avatars"
    dances_dir = remote_root / "dances"
    covers_dir = static_assets_dir / "covers"
    avatars_dir.mkdir(parents=True)
    dances_dir.mkdir(parents=True)
    covers_dir.mkdir(parents=True)

    source_vrm = Path(
        "E:/python/desktop-ai-companion/backend/static_assets/remote-assets/avatars/CamomeCamome.vrm"
    )
    target_vrm = avatars_dir / "CamomeCamome.vrm"
    target_vrm.write_bytes(source_vrm.read_bytes())
    cover_path = covers_dir / "character_item_camome_cached.png"
    cover_path.write_bytes(b"\x89PNG\r\n\x1a\ncached")

    monkeypatch.setattr(store_module, "STATIC_ASSET_ROOT", static_assets_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_ROOT", remote_root)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_AVATAR_DIR", avatars_dir)
    monkeypatch.setattr(store_module, "REMOTE_ASSET_DANCE_DIR", dances_dir)

    products = [
        {
            "product_code": "character_item_camome_cached",
            "product_name": "CamomeCamome",
            "product_type": "character_item",
            "point_price": 500,
            "status": "active",
            "asset_key": "avatars/camomecamome-cached",
            "asset_version": "cached123",
            "cover_url": "/static-assets/covers/character_item_camome_cached.png",
            "payload": {
                "title": "CamomeCamome",
                "source_filename": "CamomeCamome.vrm",
                "source_relative_path": "remote-assets/avatars/CamomeCamome.vrm",
                "asset_hash": "sha256:test",
                "asset_size": len(source_vrm.read_bytes()),
            },
        }
    ]

    assert store_module._cached_remote_asset_products_need_rebuild(products) is False
