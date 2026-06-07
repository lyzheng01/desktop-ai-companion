import json
import os
import uuid
import hashlib
import re
import struct
import unicodedata
import io
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pymysql
from pymysql.cursors import DictCursor
from PIL import Image


FREE_BENEFITS = {
    "max_companions": 1,
    "daily_message_quota": 10,
    "monthly_message_quota": 300,
    "model_access_level": "free",
    "voice_access_level": "free",
}

VIP_BENEFITS = {
    "max_companions": 3,
    "daily_message_quota": 30,
    "monthly_message_quota": 900,
    "model_access_level": "vip",
    "voice_access_level": "vip",
}

SVIP_BENEFITS = {
    "max_companions": 10,
    "daily_message_quota": -1,
    "monthly_message_quota": -1,
    "model_access_level": "svip",
    "voice_access_level": "svip",
}

CHAT_USAGE_TIMEZONE = timezone(timedelta(hours=8))

PLAN_DEFINITIONS = [
    {
        "plan_code": "free",
        "plan_name": "免费版",
        "price_fen": 0,
        "duration_days": 0,
        "status": "active",
        "benefits_json": json.dumps(FREE_BENEFITS, ensure_ascii=False),
    },
    {
        "plan_code": "vip_monthly",
        "plan_name": "VIP 月卡",
        "price_fen": 1990,
        "duration_days": 30,
        "status": "active",
        "benefits_json": json.dumps(VIP_BENEFITS, ensure_ascii=False),
    },
    {
        "plan_code": "svip_monthly",
        "plan_name": "SVIP 月卡",
        "price_fen": 3990,
        "duration_days": 30,
        "status": "active",
        "benefits_json": json.dumps(SVIP_BENEFITS, ensure_ascii=False),
    },
]

REMOTE_STORE_PRODUCT_DEFINITIONS = [
    {
        "product_code": "role_item_miku_nt_remote",
        "product_name": "Hatsune Miku NT",
        "product_type": "character_item",
        "point_price": 500,
        "status": "active",
        "asset_key": "avatars/hatsune-miku-nt",
        "asset_version": "2026.06.04",
        "payload": {"title": "Hatsune Miku NT", "cover_path": "/static-assets/covers/role_item_miku_nt_remote.png"},
    },
    {
        "product_code": "dance_item_world_is_mine_remote",
        "product_name": "World is Mine Dance",
        "product_type": "dance_item",
        "point_price": 500,
        "status": "active",
        "asset_key": "dances/world-is-mine",
        "asset_version": "2026.06.04",
        "payload": {"title": "World is Mine Dance", "cover_path": "/static-assets/covers/dance_item_world_is_mine_remote.png"},
    },
    {
        "product_code": "music_item_world_is_mine_remote",
        "product_name": "World is Mine Song",
        "product_type": "music_item",
        "point_price": 100,
        "status": "active",
        "asset_key": "music/world-is-mine",
        "asset_version": "2026.06.04",
        "payload": {"title": "World is Mine Song"},
    },
]

REMOTE_ASSET_MANIFEST_DEFINITIONS = {
    "music/world-is-mine": {
        "asset_key": "music/world-is-mine",
        "asset_version": "2026.06.04",
        "asset_hash": "sha256:abc123",
        "asset_size": 123456,
        "download_url": "https://assets.example.com/music/world-is-mine.zip",
        "files": [{"path": "World is Mine.mp3", "size": 123456}],
    },
    "avatars/hatsune-miku-nt": {
        "asset_key": "avatars/hatsune-miku-nt",
        "asset_version": "2026.06.04",
        "asset_hash": "sha256:def456",
        "asset_size": 456789,
        "download_url": "https://assets.example.com/avatars/hatsune-miku-nt.zip",
        "files": [{"path": "HatsuneMikuNT.vrm", "size": 456789}],
    },
    "dances/world-is-mine": {
        "asset_key": "dances/world-is-mine",
        "asset_version": "2026.06.04",
        "asset_hash": "sha256:ghi789",
        "asset_size": 234567,
        "download_url": "https://assets.example.com/dances/world-is-mine.zip",
        "files": [
            {"path": "World is Mine Dance.unity3d", "size": 200000},
            {"path": "World is Mine.mp3", "size": 34567},
        ],
    },
}

POINT_TOPUP_PRODUCT_DEFINITIONS = [
    {
        "product_code": "points_pack_500",
        "product_name": "500 Points",
        "points_amount": 500,
        "price_fen": 500,
        "status": "active",
        "payload": {"badge": "starter"},
    },
    {
        "product_code": "points_pack_1100",
        "product_name": "1100 Points",
        "points_amount": 1100,
        "price_fen": 1000,
        "status": "active",
        "payload": {"badge": "bonus"},
    },
    {
        "product_code": "points_pack_2300",
        "product_name": "2300 Points",
        "points_amount": 2300,
        "price_fen": 2000,
        "status": "active",
        "payload": {"badge": "best-value"},
    },
]

STATIC_ASSET_ROOT = Path(
    os.getenv("DESKTOP_AI_COMPANION_STATIC_ASSETS_DIR", str(Path(__file__).resolve().parent / "static_assets"))
)
REMOTE_ASSET_ROOT = STATIC_ASSET_ROOT / "remote-assets"
REMOTE_ASSET_AVATAR_DIR = Path(
    os.getenv("DESKTOP_AI_COMPANION_REMOTE_AVATAR_DIR", str(REMOTE_ASSET_ROOT / "avatars"))
)
REMOTE_ASSET_DANCE_DIR = Path(
    os.getenv("DESKTOP_AI_COMPANION_REMOTE_DANCE_DIR", str(REMOTE_ASSET_ROOT / "dances"))
)
REMOTE_ASSET_COVER_DIR = STATIC_ASSET_ROOT / "covers"

for _directory in (
    STATIC_ASSET_ROOT,
    REMOTE_ASSET_ROOT,
    REMOTE_ASSET_AVATAR_DIR,
    REMOTE_ASSET_DANCE_DIR,
    REMOTE_ASSET_COVER_DIR,
):
    _directory.mkdir(parents=True, exist_ok=True)

DEFAULT_REMOTE_AVATAR_FILENAMES = {"HatsuneMikuNT.vrm"}
DEFAULT_REMOTE_DANCE_FILENAMES = {
    "MMD-Ageage Again.unity3d",
    "MMD-World is Mine.unity3d",
}
REMOTE_AVATAR_DISPLAY_NAME_MAP = {
    "1773659974728287682": "Noah",
    "2642273128111274791": "Mira",
    "2684253542222290860": "Luna",
    "3034936425218793929": "Sketch",
    "3810254632681458717": "Blush",
    "4043018172957611916": "Iris",
    "4516400572461202757": "Frost",
    "4718117629272938204": "Mist",
    "5075840185788639488": "Pearl",
    "5587815854662789051": "Nyx",
    "6112490815508488228": "Aqua",
    "6823478844411844649": "Chibi",
    "6972866312692243350": "Hinata",
    "7122791886834244869": "Rex",
    "7270968377500925804": "Clara",
    "7643054104406740418": "Kai",
    "7735610165628982316": "Peony",
    "8183619569923460562": "Nova",
    "9188314527792034396": "Silk",
    "CamomeCamome": "Momo",
}


def mysql_is_configured() -> bool:
    return all(
        os.getenv(key, "").strip()
        for key in [
            "DESKTOP_AI_COMPANION_MYSQL_HOST",
            "DESKTOP_AI_COMPANION_MYSQL_USER",
            "DESKTOP_AI_COMPANION_MYSQL_PASSWORD",
            "DESKTOP_AI_COMPANION_MYSQL_DATABASE",
        ]
    )


def get_mysql_connection() -> pymysql.connections.Connection:
    if not mysql_is_configured():
        raise RuntimeError("MySQL is not configured")
    return pymysql.connect(
        host=os.getenv("DESKTOP_AI_COMPANION_MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("DESKTOP_AI_COMPANION_MYSQL_PORT", "3306")),
        user=os.getenv("DESKTOP_AI_COMPANION_MYSQL_USER", "root"),
        password=os.getenv("DESKTOP_AI_COMPANION_MYSQL_PASSWORD", ""),
        database=os.getenv("DESKTOP_AI_COMPANION_MYSQL_DATABASE", "desktop_ai_companion"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def now_utc() -> datetime:
    return datetime.utcnow()


def current_chat_usage_date() -> date:
    return now_utc().replace(tzinfo=timezone.utc).astimezone(CHAT_USAGE_TIMEZONE).date()


def normalize_daily_chat_limit(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    if parsed < 0:
        return None
    return parsed


def _slugify_filename(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "asset"


def _compute_file_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_remote_asset_cover_dir() -> Path:
    cover_dir = Path(os.getenv("DESKTOP_AI_COMPANION_REMOTE_COVER_DIR", str(STATIC_ASSET_ROOT / "covers")))
    cover_dir.mkdir(parents=True, exist_ok=True)
    return cover_dir


def _read_glb_json_and_binary_chunks(path: Path) -> tuple[dict, bytes] | tuple[None, None]:
    try:
        with path.open("rb") as handle:
            header = handle.read(12)
            if len(header) != 12:
                return None, None

            magic, version, _ = struct.unpack("<III", header)
            if magic != 0x46546C67 or version != 2:
                return None, None

            json_chunk_header = handle.read(8)
            if len(json_chunk_header) != 8:
                return None, None

            json_chunk_length, json_chunk_type = struct.unpack("<II", json_chunk_header)
            if json_chunk_type != 0x4E4F534A:
                return None, None

            json_document = json.loads(handle.read(json_chunk_length).decode("utf-8"))
            binary_chunk = b""

            binary_chunk_header = handle.read(8)
            if len(binary_chunk_header) == 8:
                binary_chunk_length, binary_chunk_type = struct.unpack("<II", binary_chunk_header)
                if binary_chunk_type == 0x004E4942:
                    binary_chunk = handle.read(binary_chunk_length)

            return json_document, binary_chunk
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError, struct.error):
        return None, None


def _extract_vrm_embedded_cover(path: Path, *, product_code: str, covers_dir: Path) -> Path | None:
    document, binary_chunk = _read_glb_json_and_binary_chunks(path)
    if not document or not binary_chunk:
        return None

    extensions = document.get("extensions") or {}
    vrm_meta = (extensions.get("VRM") or {}).get("meta") or {}
    vrmc_meta = (extensions.get("VRMC_vrm") or {}).get("meta") or {}

    image_index = vrm_meta.get("texture")
    if image_index is None:
        image_index = vrmc_meta.get("thumbnailImage")

    images = document.get("images") or []
    textures = document.get("textures") or []
    buffer_views = document.get("bufferViews") or []

    if "texture" in vrm_meta and isinstance(image_index, int):
        if image_index < 0 or image_index >= len(textures):
            return None
        image_index = (textures[image_index] or {}).get("source")

    if not isinstance(image_index, int) or image_index < 0 or image_index >= len(images):
        return None

    image_entry = images[image_index] or {}
    buffer_view_index = image_entry.get("bufferView")
    mime_type = str(image_entry.get("mimeType") or "").lower()

    if not isinstance(buffer_view_index, int) or buffer_view_index < 0 or buffer_view_index >= len(buffer_views):
        return None

    buffer_view = buffer_views[buffer_view_index] or {}
    byte_offset = int(buffer_view.get("byteOffset") or 0)
    byte_length = int(buffer_view.get("byteLength") or 0)
    if byte_length <= 0:
        return None

    image_bytes = binary_chunk[byte_offset : byte_offset + byte_length]
    if not image_bytes:
        return None

    suffix = ".jpg" if mime_type == "image/jpeg" else ".png"
    covers_dir.mkdir(parents=True, exist_ok=True)
    destination = covers_dir / f"{product_code}{suffix}"
    try:
        destination.write_bytes(image_bytes)
    except OSError:
        return None
    return destination


def _select_vrm_fallback_image_index(document: dict) -> int | None:
    images = document.get("images") or []
    textures = document.get("textures") or []
    materials = document.get("materials") or []

    if not images or not textures:
        return None

    preferred_keywords = (
        "face",
        "facial",
        "head",
        "portrait",
        "表情",
        "脸",
        "顔",
        "顏",
        "头",
        "頭",
    )

    for index, image_entry in enumerate(images):
        image_name = str((image_entry or {}).get("name") or "").strip().lower()
        if not image_name:
            continue
        if any(keyword in image_name for keyword in preferred_keywords):
            return index

    texture_usage: dict[int, int] = {}
    for material in materials:
        pbr = (material or {}).get("pbrMetallicRoughness") or {}
        base_color_texture = pbr.get("baseColorTexture") or {}
        texture_index = base_color_texture.get("index")
        if not isinstance(texture_index, int):
            continue
        if texture_index < 0 or texture_index >= len(textures):
            continue
        texture_usage[texture_index] = texture_usage.get(texture_index, 0) + 1

    if texture_usage:
        for texture_index, _ in sorted(texture_usage.items(), key=lambda item: (-item[1], item[0])):
            image_index = (textures[texture_index] or {}).get("source")
            if isinstance(image_index, int) and 0 <= image_index < len(images):
                return image_index

    for texture_entry in textures:
        image_index = (texture_entry or {}).get("source")
        if isinstance(image_index, int) and 0 <= image_index < len(images):
            return image_index

    return None


def _extract_vrm_fallback_cover(path: Path, *, product_code: str, covers_dir: Path) -> Path | None:
    document, binary_chunk = _read_glb_json_and_binary_chunks(path)
    if not document or not binary_chunk:
        return None

    images = document.get("images") or []
    buffer_views = document.get("bufferViews") or []
    image_index = _select_vrm_fallback_image_index(document)
    if not isinstance(image_index, int) or image_index < 0 or image_index >= len(images):
        return None

    image_entry = images[image_index] or {}
    buffer_view_index = image_entry.get("bufferView")
    if not isinstance(buffer_view_index, int) or buffer_view_index < 0 or buffer_view_index >= len(buffer_views):
        return None

    buffer_view = buffer_views[buffer_view_index] or {}
    byte_offset = int(buffer_view.get("byteOffset") or 0)
    byte_length = int(buffer_view.get("byteLength") or 0)
    if byte_length <= 0:
        return None

    image_bytes = binary_chunk[byte_offset : byte_offset + byte_length]
    if not image_bytes:
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as source_image:
            cover = source_image.convert("RGBA")
            cover.thumbnail((512, 512))
            covers_dir.mkdir(parents=True, exist_ok=True)
            destination = covers_dir / f"{product_code}.png"
            cover.save(destination, format="PNG")
            return destination
    except (OSError, ValueError):
        return None


def _ensure_remote_asset_cover(path: Path, *, product_code: str, kind: str) -> str:
    if kind != "avatar" or path.suffix.lower() != ".vrm":
        return ""

    cover_path = _extract_vrm_embedded_cover(path, product_code=product_code, covers_dir=_get_remote_asset_cover_dir())
    if cover_path is None:
        cover_path = _extract_vrm_fallback_cover(path, product_code=product_code, covers_dir=_get_remote_asset_cover_dir())
    if cover_path is None:
        return ""

    try:
        relative_path = cover_path.relative_to(STATIC_ASSET_ROOT).as_posix()
    except ValueError:
        return ""
    return f"/static-assets/{relative_path}"


def _resolve_remote_asset_display_name(kind: str, stem: str) -> str:
    if kind == "avatar":
        return REMOTE_AVATAR_DISPLAY_NAME_MAP.get(stem, stem)
    return stem


def _build_remote_asset_product(
    path: Path,
    *,
    kind: str,
    point_price: int,
    product_type: str,
    asset_prefix: str,
) -> dict:
    stat = path.stat()
    sha256_hex = _compute_file_sha256(path)
    stem = path.stem
    display_name = _resolve_remote_asset_display_name(kind, stem)
    slug = _slugify_filename(stem)
    try:
        relative_source_path = path.relative_to(STATIC_ASSET_ROOT).as_posix()
    except ValueError:
        relative_source_path = path.name
    product_code = f"{product_type}_{slug}_{sha256_hex[:12]}"
    asset_key = f"{asset_prefix}/{slug}-{sha256_hex[:12]}"
    cover_url = _ensure_remote_asset_cover(path, product_code=product_code, kind=kind)
    payload = {
        "title": display_name,
        "source_filename": path.name,
        "source_relative_path": relative_source_path,
        "asset_hash": f"sha256:{sha256_hex}",
        "asset_size": int(stat.st_size),
        "kind": kind,
    }
    if cover_url:
        payload["cover_path"] = cover_url
    return {
        "product_code": product_code,
        "product_name": display_name,
        "product_type": product_type,
        "point_price": point_price,
        "status": "active",
        "asset_key": asset_key,
        "asset_version": sha256_hex[:12],
        "cover_url": cover_url,
        "payload": payload,
        "_source_path": str(path),
    }


def _iter_remote_asset_products() -> list[dict]:
    cached_products = _load_cached_remote_asset_products()
    if cached_products is not None:
        return cached_products

    products: list[dict] = []

    if REMOTE_ASSET_AVATAR_DIR.exists():
        for path in sorted(REMOTE_ASSET_AVATAR_DIR.rglob("*.vrm")):
            if path.name in DEFAULT_REMOTE_AVATAR_FILENAMES:
                continue
            products.append(
                _build_remote_asset_product(
                    path,
                    kind="avatar",
                    point_price=500,
                    product_type="character_item",
                    asset_prefix="avatars",
                )
            )

    if REMOTE_ASSET_DANCE_DIR.exists():
        for path in sorted(REMOTE_ASSET_DANCE_DIR.rglob("*.unity3d")):
            if path.name in DEFAULT_REMOTE_DANCE_FILENAMES:
                continue
            products.append(
                _build_remote_asset_product(
                    path,
                    kind="dance",
                    point_price=100,
                    product_type="dance_item",
                    asset_prefix="dances",
                )
            )

    products.sort(key=lambda item: (item["product_type"], item["product_name"].lower(), item["product_code"]))
    _write_cached_remote_asset_products(products)
    return products


def _load_cached_remote_asset_products() -> list[dict] | None:
    index_path = _get_remote_asset_index_path()
    if not index_path.exists():
        return None
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list):
        return None
    products: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        products.append(dict(item))
    if _cached_remote_asset_products_need_rebuild(products):
        return None
    return products


def _cached_remote_asset_products_need_rebuild(products: list[dict]) -> bool:
    for item in products:
        product_type = str(item.get("product_type") or "").lower()
        payload = item.get("payload") or {}
        kind = str(payload.get("kind") or "")
        source_relative_path = str(payload.get("source_relative_path") or "")
        source_path = REMOTE_ASSET_ROOT.parent / source_relative_path if source_relative_path else None

        if product_type.startswith("character") and source_path is not None and source_path.suffix.lower() == ".vrm":
            expected_display_name = _resolve_remote_asset_display_name(kind, source_path.stem) if kind == "avatar" else source_path.stem
            if str(item.get("product_name") or "") != expected_display_name:
                return True
            if str(payload.get("title") or "") != expected_display_name:
                return True
            cover_url = str(item.get("cover_url") or "").strip()
            if not cover_url:
                return True
            cover_relative = cover_url.removeprefix("/static-assets/").strip("/")
            cover_path = STATIC_ASSET_ROOT / cover_relative if cover_relative else None
            if cover_path is None or not cover_path.exists():
                return True

    return False


def _write_cached_remote_asset_products(products: list[dict]) -> None:
    serializable: list[dict] = []
    for item in products:
        serializable.append(dict(item))
    index_path = _get_remote_asset_index_path()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _get_remote_asset_index_path() -> Path:
    return REMOTE_ASSET_ROOT / "catalog-index.json"


def _parse_benefits(row: dict | None) -> dict:
    if not row:
        return FREE_BENEFITS.copy()
    raw = row.get("benefits_json")
    if not isinstance(raw, str):
        return FREE_BENEFITS.copy()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return FREE_BENEFITS.copy()
    return parsed if isinstance(parsed, dict) else FREE_BENEFITS.copy()


def plan_code_to_tier(plan_code: str) -> str:
    if plan_code.startswith("svip"):
        return "svip"
    if plan_code.startswith("vip"):
        return "vip"
    return "free"


def init_business_tables() -> None:
    if not mysql_is_configured():
        return

    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(32) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NULL,
                    nickname VARCHAR(64) NULL,
                    avatar_url VARCHAR(255) NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sms_codes (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(32) NOT NULL,
                    scene VARCHAR(32) NOT NULL,
                    code_hash VARCHAR(128) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    consumed_at DATETIME NULL,
                    send_ip VARCHAR(64) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_sms_codes_phone_scene (phone, scene)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL,
                    refresh_token_hash VARCHAR(128) NOT NULL UNIQUE,
                    device_id VARCHAR(128) NULL,
                    device_name VARCHAR(128) NULL,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_sessions_user_id (user_id),
                    CONSTRAINT fk_user_sessions_user FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS membership_plans (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    plan_code VARCHAR(64) NOT NULL UNIQUE,
                    plan_name VARCHAR(64) NOT NULL,
                    price_fen INT NOT NULL,
                    duration_days INT NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    benefits_json JSON NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memberships (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL,
                    plan_code VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    started_at DATETIME NOT NULL,
                    expires_at DATETIME NOT NULL,
                    source_order_no VARCHAR(64) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user_memberships_user_id (user_id),
                    CONSTRAINT fk_user_memberships_user FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_daily_chat_usage (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL,
                    usage_date DATE NOT NULL,
                    used_count INT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_daily_chat_usage (user_id, usage_date),
                    INDEX idx_user_daily_chat_usage_user_id (user_id),
                    CONSTRAINT fk_user_daily_chat_usage_user FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_point_accounts (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL UNIQUE,
                    balance BIGINT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_user_point_accounts_user FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_point_ledger (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL,
                    change_amount BIGINT NOT NULL,
                    balance_after BIGINT NOT NULL,
                    source_type VARCHAR(32) NOT NULL,
                    source_order_no VARCHAR(64) NULL,
                    remark VARCHAR(255) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_point_ledger_user_id (user_id),
                    CONSTRAINT fk_user_point_ledger_user FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_entitlements (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL,
                    entitlement_code VARCHAR(128) NOT NULL,
                    entitlement_type VARCHAR(32) NOT NULL,
                    source_product_code VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    expires_at DATETIME NULL,
                    payload_json JSON NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_entitlements_code (user_id, entitlement_code),
                    INDEX idx_user_entitlements_user_id (user_id),
                    CONSTRAINT fk_user_entitlements_user FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS point_topup_orders (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    order_no VARCHAR(64) NOT NULL UNIQUE,
                    user_id BIGINT NOT NULL,
                    product_code VARCHAR(64) NOT NULL,
                    points_amount BIGINT NOT NULL,
                    amount_fen INT NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    pay_channel VARCHAR(32) NOT NULL DEFAULT 'wechat_native',
                    wechat_prepay_id VARCHAR(128) NULL,
                    wechat_code_url TEXT NULL,
                    wechat_transaction_id VARCHAR(128) NULL,
                    paid_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_point_topup_orders_user_id (user_id),
                    CONSTRAINT fk_point_topup_orders_user FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_orders (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    order_no VARCHAR(64) NOT NULL UNIQUE,
                    user_id BIGINT NOT NULL,
                    plan_code VARCHAR(64) NOT NULL,
                    amount_fen INT NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    pay_channel VARCHAR(32) NOT NULL DEFAULT 'wechat_native',
                    wechat_prepay_id VARCHAR(128) NULL,
                    wechat_code_url TEXT NULL,
                    wechat_transaction_id VARCHAR(128) NULL,
                    paid_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_payment_orders_user_id (user_id),
                    CONSTRAINT fk_payment_orders_user FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_callbacks (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    provider VARCHAR(32) NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    payload_json JSON NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for plan in PLAN_DEFINITIONS:
                cursor.execute(
                    """
                    INSERT INTO membership_plans (plan_code, plan_name, price_fen, duration_days, status, benefits_json)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        plan_name = VALUES(plan_name),
                        price_fen = VALUES(price_fen),
                        duration_days = VALUES(duration_days),
                        status = VALUES(status),
                        benefits_json = VALUES(benefits_json)
                    """,
                    (
                        plan["plan_code"],
                        plan["plan_name"],
                        plan["price_fen"],
                        plan["duration_days"],
                        plan["status"],
                        plan["benefits_json"],
                    ),
                )
            cursor.execute("SHOW COLUMNS FROM users LIKE 'password_hash'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL AFTER phone")
        conn.commit()
    finally:
        conn.close()


def create_sms_code(phone: str, scene: str, code_hash: str, expires_at: datetime, send_ip: str | None) -> None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT created_at FROM sms_codes
                WHERE phone = %s AND scene = %s
                ORDER BY id DESC LIMIT 1
                """,
                (phone, scene),
            )
            latest = cursor.fetchone()
            if latest and (now_utc() - latest["created_at"]).total_seconds() < 60:
                raise ValueError("Please wait before requesting another code")

            cursor.execute(
                """
                INSERT INTO sms_codes (phone, scene, code_hash, expires_at, send_ip)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (phone, scene, code_hash, expires_at, send_ip),
            )
        conn.commit()
    finally:
        conn.close()


def consume_sms_code(phone: str, scene: str, code_hash: str) -> bool:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM sms_codes
                WHERE phone = %s AND scene = %s AND code_hash = %s
                  AND consumed_at IS NULL AND expires_at > %s
                ORDER BY id DESC LIMIT 1
                """,
                (phone, scene, code_hash, now_utc()),
            )
            row = cursor.fetchone()
            if not row:
                return False
            cursor.execute("UPDATE sms_codes SET consumed_at = %s WHERE id = %s", (now_utc(), row["id"]))
        conn.commit()
        return True
    finally:
        conn.close()


def get_or_create_user_by_phone(phone: str) -> dict:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE phone = %s LIMIT 1", (phone,))
            user = cursor.fetchone()
            if user:
                return user
            nickname = f"用户{phone[-4:]}" if len(phone) >= 4 else "新用户"
            cursor.execute(
                "INSERT INTO users (phone, nickname, status) VALUES (%s, %s, 'active')",
                (phone, nickname),
            )
            cursor.execute("SELECT * FROM users WHERE id = LAST_INSERT_ID()")
            created = cursor.fetchone()
        conn.commit()
        return created
    finally:
        conn.close()


def get_user_by_phone(phone: str) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE phone = %s LIMIT 1", (phone,))
            return cursor.fetchone()
    finally:
        conn.close()


def create_user_with_password(phone: str, password_hash: str) -> dict:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            nickname = f"用户{phone[-4:]}" if len(phone) >= 4 else "新用户"
            cursor.execute(
                """
                INSERT INTO users (phone, password_hash, nickname, status)
                VALUES (%s, %s, %s, 'active')
                """,
                (phone, password_hash, nickname),
            )
            cursor.execute("SELECT * FROM users WHERE id = LAST_INSERT_ID()")
            created = cursor.fetchone()
        conn.commit()
        return created
    finally:
        conn.close()


def set_user_password(user_id: int, password_hash: str) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s
                """,
                (password_hash, user_id),
            )
            cursor.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (user_id,))
            updated = cursor.fetchone()
        conn.commit()
        return updated
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s LIMIT 1", (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def create_user_session(user_id: int, refresh_token_hash: str, device_id: str | None, device_name: str | None, expires_at: datetime) -> None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_sessions (user_id, refresh_token_hash, device_id, device_name, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, refresh_token_hash, device_id, device_name, expires_at),
            )
        conn.commit()
    finally:
        conn.close()


def get_session_by_refresh_token_hash(refresh_token_hash: str) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM user_sessions
                WHERE refresh_token_hash = %s AND expires_at > %s
                LIMIT 1
                """,
                (refresh_token_hash, now_utc()),
            )
            return cursor.fetchone()
    finally:
        conn.close()


def delete_session_by_refresh_token_hash(refresh_token_hash: str) -> None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM user_sessions WHERE refresh_token_hash = %s", (refresh_token_hash,))
        conn.commit()
    finally:
        conn.close()


def list_membership_plans() -> list[dict]:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT plan_code, plan_name, price_fen, duration_days, status, benefits_json FROM membership_plans WHERE status = 'active' ORDER BY price_fen ASC"
            )
            rows = cursor.fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        result.append(
            {
                "plan_code": row["plan_code"],
                "plan_name": row["plan_name"],
                "price_fen": row["price_fen"],
                "duration_days": row["duration_days"],
                "tier": plan_code_to_tier(row["plan_code"]),
                "benefits": _parse_benefits(row),
            }
        )
    return result


def get_plan(plan_code: str) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM membership_plans WHERE plan_code = %s LIMIT 1", (plan_code,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_user_membership(user_id: int) -> dict:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT um.plan_code, um.status, um.started_at, um.expires_at, mp.benefits_json
                FROM user_memberships um
                JOIN membership_plans mp ON mp.plan_code = um.plan_code
                WHERE um.user_id = %s AND um.status = 'active' AND um.expires_at > %s
                ORDER BY um.expires_at DESC
                LIMIT 1
                """,
                (user_id, now_utc()),
            )
            row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return {
            "plan_code": "free",
            "tier": "free",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": FREE_BENEFITS.copy(),
        }

    return {
        "plan_code": row["plan_code"],
        "tier": plan_code_to_tier(row["plan_code"]),
        "status": row["status"],
        "started_at": row["started_at"],
        "expires_at": row["expires_at"],
        "benefits": _parse_benefits(row),
    }


def get_user_daily_chat_usage(user_id: int, usage_date: date | None = None) -> int:
    if not mysql_is_configured():
        return 0

    resolved_usage_date = usage_date or current_chat_usage_date()
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT used_count
                FROM user_daily_chat_usage
                WHERE user_id = %s AND usage_date = %s
                LIMIT 1
                """,
                (user_id, resolved_usage_date),
            )
            row = cursor.fetchone()
            return int(row["used_count"]) if row else 0
    finally:
        conn.close()


def consume_user_daily_chat_usage(user_id: int, daily_limit: int | None, usage_date: date | None = None) -> dict:
    if not mysql_is_configured():
        raise RuntimeError("MySQL is not configured")

    resolved_usage_date = usage_date or current_chat_usage_date()
    normalized_limit = normalize_daily_chat_limit(daily_limit)
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, used_count
                FROM user_daily_chat_usage
                WHERE user_id = %s AND usage_date = %s
                FOR UPDATE
                """,
                (user_id, resolved_usage_date),
            )
            row = cursor.fetchone()
            used_before = int(row["used_count"]) if row else 0

            if normalized_limit is not None and used_before >= normalized_limit:
                conn.rollback()
                return {
                    "allowed": False,
                    "daily_limit": normalized_limit,
                    "daily_used": used_before,
                    "daily_remaining": 0,
                    "is_unlimited": False,
                }

            daily_used = used_before + 1
            if row:
                cursor.execute(
                    """
                    UPDATE user_daily_chat_usage
                    SET used_count = %s
                    WHERE id = %s
                    """,
                    (daily_used, row["id"]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_daily_chat_usage (user_id, usage_date, used_count)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, resolved_usage_date, daily_used),
                )

            conn.commit()
            return {
                "allowed": True,
                "daily_limit": normalized_limit,
                "daily_used": daily_used,
                "daily_remaining": None if normalized_limit is None else max(normalized_limit - daily_used, 0),
                "is_unlimited": normalized_limit is None,
            }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_store_products() -> list[dict]:
    products: list[dict] = []
    for item in _iter_remote_asset_products():
        products.append(
            {
                "product_code": item["product_code"],
                "product_name": item["product_name"],
                "product_type": item["product_type"],
                "point_price": int(item["point_price"]),
                "status": item["status"],
                "asset_key": item["asset_key"],
                "asset_version": item["asset_version"],
                "payload": dict(item.get("payload") or {}),
            }
        )
    return products


def _catalog_kind_for_product(item: dict) -> str | None:
    product_type = str(item.get("product_type") or "").lower()
    asset_key = str(item.get("asset_key") or "").lower()
    if product_type.startswith("character") or asset_key.startswith("avatars/"):
        return "avatar"
    if product_type.startswith("dance") or asset_key.startswith("dances/"):
        return "dance"
    return None


def list_asset_catalog_products(kind: str | None = None) -> list[dict]:
    normalized_kind = (kind or "").strip().lower() or None
    products: list[dict] = []
    for item in _iter_remote_asset_products():
        product_kind = _catalog_kind_for_product(item)
        if product_kind is None:
            continue
        if normalized_kind and product_kind != normalized_kind:
            continue
        payload = dict(item.get("payload") or {})
        products.append(
            {
                "product_code": item["product_code"],
                "product_name": item["product_name"],
                "product_type": item["product_type"],
                "point_price": int(item["point_price"]),
                "status": item["status"],
                "asset_key": item["asset_key"],
                "asset_version": item["asset_version"],
                "cover_url": str(payload.get("cover_path") or ""),
                "payload": payload,
            }
        )
    return products


def get_asset_catalog_product(product_code: str) -> dict | None:
    for item in _iter_remote_asset_products():
        if item["product_code"] == product_code:
            return item
    return None


def get_store_product(product_code: str) -> dict | None:
    for item in list_store_products():
        if item["product_code"] == product_code:
            return item
    return None


def get_user_points_balance(user_id: int) -> int:
    if not mysql_is_configured():
        return 0

    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT balance FROM user_point_accounts WHERE user_id = %s LIMIT 1", (user_id,))
            row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return 0
    return int(row["balance"])


def deduct_points_for_asset_product(user_id: int, product_code: str) -> int:
    product = get_asset_catalog_product(product_code)
    if not product:
        raise ValueError("Invalid product")

    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT balance FROM user_point_accounts WHERE user_id = %s LIMIT 1 FOR UPDATE", (user_id,))
            account = cursor.fetchone()
            current_balance = int(account["balance"]) if account else 0
            point_price = int(product["point_price"])
            if current_balance < point_price:
                raise ValueError("Insufficient points")

            new_balance = current_balance - point_price
            if account:
                cursor.execute("UPDATE user_point_accounts SET balance = %s WHERE user_id = %s", (new_balance, user_id))
            else:
                cursor.execute("INSERT INTO user_point_accounts (user_id, balance) VALUES (%s, %s)", (user_id, new_balance))

            cursor.execute(
                """
                INSERT INTO user_point_ledger (user_id, change_amount, balance_after, source_type, source_order_no, remark)
                VALUES (%s, %s, %s, 'asset_acquire', NULL, %s)
                """,
                (user_id, -point_price, new_balance, product_code),
            )
        conn.commit()
        return new_balance
    finally:
        conn.close()


def list_point_topup_products() -> list[dict]:
    products: list[dict] = []
    for item in POINT_TOPUP_PRODUCT_DEFINITIONS:
        if item["status"] != "active":
            continue
        products.append(
            {
                "product_code": item["product_code"],
                "product_name": item["product_name"],
                "points_amount": int(item["points_amount"]),
                "price_fen": int(item["price_fen"]),
                "status": item["status"],
                "payload": dict(item.get("payload") or {}),
            }
        )
    return products


def get_point_topup_product(product_code: str) -> dict | None:
    for item in POINT_TOPUP_PRODUCT_DEFINITIONS:
        if item["product_code"] == product_code and item["status"] == "active":
            return {
                "product_code": item["product_code"],
                "product_name": item["product_name"],
                "points_amount": int(item["points_amount"]),
                "price_fen": int(item["price_fen"]),
                "status": item["status"],
                "payload": dict(item.get("payload") or {}),
            }
    return None


def create_point_topup_order(
    user_id: int,
    product_code: str,
    pay_channel: str,
    points_amount: int | None = None,
    amount_fen: int | None = None,
    wechat_code_url: str | None = None,
    wechat_prepay_id: str | None = None,
) -> dict:
    resolved_product_code = str(product_code or "").strip()
    resolved_points_amount = points_amount
    resolved_amount_fen = amount_fen

    if resolved_points_amount is None or resolved_amount_fen is None:
        product = get_point_topup_product(resolved_product_code)
        if not product:
            raise ValueError("Invalid point topup product")
        resolved_product_code = product["product_code"]
        resolved_points_amount = int(product["points_amount"])
        resolved_amount_fen = int(product["price_fen"])

    if int(resolved_points_amount) <= 0 or int(resolved_amount_fen) <= 0:
        raise ValueError("Invalid point topup amount")

    order_no = f"DACP{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO point_topup_orders (
                    order_no, user_id, product_code, points_amount, amount_fen, status, pay_channel, wechat_prepay_id, wechat_code_url
                ) VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s, %s)
                """,
                (
                    order_no,
                    user_id,
                    resolved_product_code,
                    int(resolved_points_amount),
                    int(resolved_amount_fen),
                    pay_channel,
                    wechat_prepay_id,
                    wechat_code_url,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return get_point_topup_order(order_no)


def get_point_topup_order(order_no: str) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM point_topup_orders WHERE order_no = %s LIMIT 1", (order_no,))
            return cursor.fetchone()
    finally:
        conn.close()


def update_point_topup_order_provider_fields(order_no: str, wechat_code_url: str | None, wechat_prepay_id: str | None) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE point_topup_orders
                SET wechat_code_url = %s, wechat_prepay_id = %s
                WHERE order_no = %s
                """,
                (wechat_code_url, wechat_prepay_id, order_no),
            )
        conn.commit()
    finally:
        conn.close()
    return get_point_topup_order(order_no)


def mark_point_topup_order_paid(order_no: str, transaction_id: str | None) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM point_topup_orders WHERE order_no = %s LIMIT 1 FOR UPDATE", (order_no,))
            order = cursor.fetchone()
            if not order:
                conn.rollback()
                return None
            if order["status"] == "paid":
                conn.commit()
                return order

            paid_at = now_utc()
            cursor.execute(
                """
                UPDATE point_topup_orders
                SET status = 'paid', wechat_transaction_id = %s, paid_at = %s
                WHERE order_no = %s
                """,
                (transaction_id, paid_at, order_no),
            )

            cursor.execute("SELECT balance FROM user_point_accounts WHERE user_id = %s LIMIT 1 FOR UPDATE", (order["user_id"],))
            account = cursor.fetchone()
            current_balance = int(account["balance"]) if account else 0
            new_balance = current_balance + int(order["points_amount"])

            if account:
                cursor.execute(
                    "UPDATE user_point_accounts SET balance = %s WHERE user_id = %s",
                    (new_balance, order["user_id"]),
                )
            else:
                cursor.execute(
                    "INSERT INTO user_point_accounts (user_id, balance) VALUES (%s, %s)",
                    (order["user_id"], new_balance),
                )

            cursor.execute(
                """
                INSERT INTO user_point_ledger (user_id, change_amount, balance_after, source_type, source_order_no, remark)
                VALUES (%s, %s, %s, 'topup', %s, %s)
                """,
                (order["user_id"], int(order["points_amount"]), new_balance, order_no, order["product_code"]),
            )
            cursor.execute("SELECT * FROM point_topup_orders WHERE order_no = %s LIMIT 1", (order_no,))
            updated_order = cursor.fetchone()
        conn.commit()
        return updated_order
    finally:
        conn.close()


def redeem_store_product(user_id: int, product_code: str) -> dict:
    product = get_store_product(product_code)
    if not product:
        raise ValueError("Invalid product")

    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT entitlement_code, entitlement_type, source_product_code, status, expires_at, payload_json
                FROM user_entitlements
                WHERE user_id = %s AND source_product_code = %s AND status = 'active'
                LIMIT 1 FOR UPDATE
                """,
                (user_id, product_code),
            )
            existing = cursor.fetchone()
            if existing:
                payload = existing.get("payload_json")
                if isinstance(payload, str):
                    payload = json.loads(payload)
                return {
                    "points_balance": get_user_points_balance(user_id),
                    "entitlement": {
                        "entitlement_code": existing["entitlement_code"],
                        "entitlement_type": existing["entitlement_type"],
                        "source_product_code": existing["source_product_code"],
                        "status": existing["status"],
                        "expires_at": existing["expires_at"],
                        "payload": payload if isinstance(payload, dict) else {},
                    },
                }

            cursor.execute("SELECT balance FROM user_point_accounts WHERE user_id = %s LIMIT 1 FOR UPDATE", (user_id,))
            account = cursor.fetchone()
            current_balance = int(account["balance"]) if account else 0
            if current_balance < int(product["point_price"]):
                raise ValueError("Insufficient points")

            new_balance = current_balance - int(product["point_price"])
            if account:
                cursor.execute("UPDATE user_point_accounts SET balance = %s WHERE user_id = %s", (new_balance, user_id))
            else:
                cursor.execute("INSERT INTO user_point_accounts (user_id, balance) VALUES (%s, %s)", (user_id, new_balance))

            entitlement_code = f"{product['product_type'].replace('_item', '')}.{product['asset_key'].replace('/', '.')}"
            payload_json = json.dumps(
                {
                    "asset_key": product["asset_key"],
                    "asset_version": product["asset_version"],
                },
                ensure_ascii=False,
            )
            cursor.execute(
                """
                INSERT INTO user_entitlements (user_id, entitlement_code, entitlement_type, source_product_code, status, expires_at, payload_json)
                VALUES (%s, %s, 'permanent', %s, 'active', NULL, %s)
                """,
                (user_id, entitlement_code, product_code, payload_json),
            )
            cursor.execute(
                """
                INSERT INTO user_point_ledger (user_id, change_amount, balance_after, source_type, source_order_no, remark)
                VALUES (%s, %s, %s, 'redeem', NULL, %s)
                """,
                (user_id, -int(product["point_price"]), new_balance, product_code),
            )
        conn.commit()
    finally:
        conn.close()

    entitlements = list_user_entitlements(user_id)
    matched = next(item for item in entitlements if item["source_product_code"] == product_code)
    return {"points_balance": new_balance, "entitlement": matched}


def list_user_entitlements(user_id: int) -> list[dict]:
    if not mysql_is_configured():
        return []

    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT entitlement_code, entitlement_type, source_product_code, status, expires_at, payload_json
                FROM user_entitlements
                WHERE user_id = %s
                  AND status = 'active'
                  AND (expires_at IS NULL OR expires_at > %s)
                ORDER BY id ASC
                """,
                (user_id, now_utc()),
            )
            rows = cursor.fetchall()
    finally:
        conn.close()

    entitlements: list[dict] = []
    for row in rows:
        payload = row.get("payload_json")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        elif payload is None:
            payload = {}

        entitlements.append(
            {
                "entitlement_code": row["entitlement_code"],
                "entitlement_type": row["entitlement_type"],
                "source_product_code": row["source_product_code"],
                "status": row["status"],
                "expires_at": row["expires_at"],
                "payload": payload if isinstance(payload, dict) else {},
            }
        )
    return entitlements


def get_download_manifest_for_user_product(user_id: int, product_code: str) -> dict:
    entitlements = list_user_entitlements(user_id)
    owned = next((item for item in entitlements if item["source_product_code"] == product_code), None)
    if not owned:
        raise PermissionError("Product not owned")

    payload = owned.get("payload") or {}
    asset_key = str(payload.get("asset_key") or "")
    product = get_asset_catalog_product(product_code)
    if not product or product["asset_key"] != asset_key:
        raise ValueError("Asset manifest not found")
    return build_asset_download_manifest(product_code, os.getenv("DESKTOP_AI_COMPANION_PUBLIC_BASE_URL", "http://127.0.0.1:8080"))


def build_asset_download_manifest(product_code: str, public_base_url: str) -> dict:
    product = get_asset_catalog_product(product_code)
    if not product:
        raise ValueError("Invalid product")

    source_path_raw = product.get("_source_path")
    if not source_path_raw:
        raise ValueError("Asset manifest not found")
    source_path = Path(source_path_raw)
    if not source_path.exists():
        raise ValueError("Asset file not found")

    normalized_base_url = (public_base_url or "").rstrip("/")
    relative_static_path = source_path.relative_to(STATIC_ASSET_ROOT).as_posix()
    download_relative_path = "/static-assets/" + quote(relative_static_path, safe="/-_.()")
    stat = source_path.stat()
    asset_hash = str(product.get("payload", {}).get("asset_hash") or "")
    if not asset_hash:
        asset_hash = f"sha256:{_compute_file_sha256(source_path)}"

    return {
        "product_code": product_code,
        "asset_key": product["asset_key"],
        "asset_version": str(product["asset_version"]),
        "asset_hash": asset_hash,
        "asset_size": int(stat.st_size),
        "download_url": f"{normalized_base_url}{download_relative_path}",
        "files": [{"path": source_path.name, "size": int(stat.st_size)}],
    }


def create_payment_order(user_id: int, plan_code: str, pay_channel: str, wechat_code_url: str | None = None, wechat_prepay_id: str | None = None) -> dict:
    plan = get_plan(plan_code)
    if not plan or plan["status"] != "active" or plan_code == "free":
        raise ValueError("Invalid plan")

    order_no = f"DAC{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO payment_orders (
                    order_no, user_id, plan_code, amount_fen, status, pay_channel, wechat_prepay_id, wechat_code_url
                ) VALUES (%s, %s, %s, %s, 'pending', %s, %s, %s)
                """,
                (
                    order_no,
                    user_id,
                    plan_code,
                    plan["price_fen"],
                    pay_channel,
                    wechat_prepay_id,
                    wechat_code_url,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return get_payment_order(order_no)


def update_payment_order_provider_fields(order_no: str, wechat_code_url: str | None, wechat_prepay_id: str | None) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE payment_orders
                SET wechat_code_url = %s, wechat_prepay_id = %s
                WHERE order_no = %s
                """,
                (wechat_code_url, wechat_prepay_id, order_no),
            )
        conn.commit()
    finally:
        conn.close()
    return get_payment_order(order_no)


def get_payment_order(order_no: str) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM payment_orders WHERE order_no = %s LIMIT 1", (order_no,))
            return cursor.fetchone()
    finally:
        conn.close()


def store_payment_callback(provider: str, event_type: str, payload: dict) -> None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO payment_callbacks (provider, event_type, payload_json) VALUES (%s, %s, %s)",
                (provider, event_type, json.dumps(payload, ensure_ascii=False)),
            )
        conn.commit()
    finally:
        conn.close()


def mark_order_paid(order_no: str, transaction_id: str | None) -> dict | None:
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM payment_orders WHERE order_no = %s LIMIT 1 FOR UPDATE", (order_no,))
            order = cursor.fetchone()
            if not order:
                conn.rollback()
                return None
            if order["status"] == "paid":
                conn.commit()
                return order

            paid_at = now_utc()
            cursor.execute(
                """
                UPDATE payment_orders
                SET status = 'paid', wechat_transaction_id = %s, paid_at = %s
                WHERE order_no = %s
                """,
                (transaction_id, paid_at, order_no),
            )

            cursor.execute("SELECT * FROM membership_plans WHERE plan_code = %s LIMIT 1", (order["plan_code"],))
            plan = cursor.fetchone()
            if not plan:
                conn.rollback()
                raise ValueError("Plan not found for paid order")

            cursor.execute(
                """
                SELECT * FROM user_memberships
                WHERE user_id = %s AND status = 'active' AND expires_at > %s
                ORDER BY expires_at DESC LIMIT 1 FOR UPDATE
                """,
                (order["user_id"], now_utc()),
            )
            active_membership = cursor.fetchone()
            started_at = paid_at
            expires_at = paid_at + timedelta(days=int(plan["duration_days"]))

            if active_membership and active_membership["plan_code"] == order["plan_code"]:
                started_at = active_membership["started_at"]
                expires_at = active_membership["expires_at"] + timedelta(days=int(plan["duration_days"]))
                cursor.execute(
                    """
                    UPDATE user_memberships
                    SET expires_at = %s, source_order_no = %s
                    WHERE id = %s
                    """,
                    (expires_at, order_no, active_membership["id"]),
                )
            else:
                if active_membership:
                    cursor.execute("UPDATE user_memberships SET status = 'superseded' WHERE id = %s", (active_membership["id"],))
                cursor.execute(
                    """
                    INSERT INTO user_memberships (user_id, plan_code, status, started_at, expires_at, source_order_no)
                    VALUES (%s, %s, 'active', %s, %s, %s)
                    """,
                    (order["user_id"], order["plan_code"], started_at, expires_at, order_no),
                )

            cursor.execute("SELECT * FROM payment_orders WHERE order_no = %s LIMIT 1", (order_no,))
            updated_order = cursor.fetchone()
        conn.commit()
        return updated_order
    finally:
        conn.close()
