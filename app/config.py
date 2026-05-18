"""
配置管理模块
"""
import json
import os
import re
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional


# 应用目录
APP_DIR = Path(__file__).resolve().parent.parent

APP_NAME = "Desktop AI Companion"
DATA_DIR_ENV = "DESKTOP_AI_COMPANION_DATA_DIR"


def _default_bootstrap_dir() -> Path:
    if os.name == "nt":
        appdata = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
        if appdata:
            return Path(appdata) / APP_NAME
    return APP_DIR / "data"


BOOTSTRAP_DIR = _default_bootstrap_dir()
BOOTSTRAP_FILE = BOOTSTRAP_DIR / "bootstrap.json"


def _normalize_data_dir(path: Path) -> Path:
    return path.expanduser().resolve()


def _load_bootstrap_data_dir() -> Path | None:
    if not BOOTSTRAP_FILE.exists():
        return None
    try:
        with open(BOOTSTRAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_path = data.get("data_dir")
        if isinstance(raw_path, str) and raw_path.strip():
            return _normalize_data_dir(Path(raw_path))
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return None
    return None


def resolve_data_dir() -> Path:
    env_path = os.getenv(DATA_DIR_ENV, "").strip()
    if env_path:
        return _normalize_data_dir(Path(env_path))

    bootstrap_path = _load_bootstrap_data_dir()
    if bootstrap_path is not None:
        return bootstrap_path

    return APP_DIR / "data"


def _refresh_paths() -> None:
    global DATA_DIR, DB_PATH, CONFIG_FILE
    DATA_DIR = resolve_data_dir()
    DB_PATH = DATA_DIR / "companion.db"
    CONFIG_FILE = DATA_DIR / "config.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def set_data_dir(path: Path, persist_bootstrap: bool = False) -> Path:
    normalized = _normalize_data_dir(path)
    os.environ[DATA_DIR_ENV] = str(normalized)
    if persist_bootstrap:
        BOOTSTRAP_DIR.mkdir(parents=True, exist_ok=True)
        with open(BOOTSTRAP_FILE, "w", encoding="utf-8") as f:
            json.dump({"data_dir": str(normalized)}, f, ensure_ascii=False, indent=2)
    _refresh_paths()
    return DATA_DIR


def get_data_dir() -> Path:
    return DATA_DIR


def get_db_path() -> Path:
    return DB_PATH


def get_config_file() -> Path:
    return CONFIG_FILE


def get_imported_models_dir() -> Path:
    path = DATA_DIR / "live2d" / "imported"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_imported_preview_dir() -> Path:
    path = DATA_DIR / "model-previews" / "imported"
    path.mkdir(parents=True, exist_ok=True)
    return path

_refresh_paths()

TIME_PATTERN = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


@dataclass
class AppConfig:
    """应用配置"""

    # 用户信息
    user_nickname: str = "小伙伴"
    user_display_name: str = "你"

    # 角色设置
    character_type: str = "mao_pro_zh"  # default live2d model
    character_name: str = "Mao"
    personality: list[str] = field(default_factory=lambda: ["温柔"])  # 温柔/安静/元气/理性/治愈
    interaction_mode: str = "work"  # work, daily, quiet, sleep
    proactive_mode: str = "quiet"  # quiet, greet, remind
    chat_model: str = "gpt"  # gpt, deepseek

    # 免打扰设置
    dnd_enabled: bool = False
    dnd_start: str = "22:00"
    dnd_end: str = "08:00"

    # 窗口设置
    window_x: int = 100
    window_y: int = 100
    window_scale: float = 1.0
    character_scales: dict[str, float] = field(default_factory=dict)

    # AI 设置
    api_provider: str = "default"  # default, custom
    api_key: str = ""
    model_name: str = "default"

    # 高级设置
    auto_start: bool = False
    always_on_top: bool = False
    click_through: bool = False
    opacity: float = 1.0
    show_notifications: bool = True
    sound_enabled: bool = True

    def save(self, path: Path | None = None):
        """保存配置到文件"""
        if path is None:
            path = CONFIG_FILE
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def sanitize(cls, cfg: "AppConfig") -> "AppConfig":
        defaults = cls()

        string_fields = (
            "user_nickname",
            "user_display_name",
            "character_type",
            "character_name",
            "interaction_mode",
            "proactive_mode",
            "chat_model",
            "api_provider",
            "api_key",
            "model_name",
        )
        bool_fields = (
            "dnd_enabled",
            "auto_start",
            "always_on_top",
            "click_through",
            "show_notifications",
            "sound_enabled",
        )
        int_fields = ("window_x", "window_y")
        float_fields = ("window_scale",)

        for field in string_fields:
            if not isinstance(getattr(cfg, field), str):
                setattr(cfg, field, getattr(defaults, field))
        for field in bool_fields:
            if type(getattr(cfg, field)) is not bool:
                setattr(cfg, field, getattr(defaults, field))
        for field in int_fields:
            if type(getattr(cfg, field)) is not int:
                setattr(cfg, field, getattr(defaults, field))
        for field in float_fields:
            if not isinstance(getattr(cfg, field), (int, float)):
                setattr(cfg, field, getattr(defaults, field))

        if isinstance(cfg.personality, str):
            cfg.personality = [cfg.personality]
        elif not isinstance(cfg.personality, list) or not all(isinstance(item, str) for item in cfg.personality):
            cfg.personality = defaults.personality
        if not isinstance(cfg.character_scales, dict) or not all(
            isinstance(key, str) and isinstance(value, (int, float))
            for key, value in cfg.character_scales.items()
        ):
            cfg.character_scales = {}
        if not isinstance(cfg.dnd_start, str) or not TIME_PATTERN.fullmatch(cfg.dnd_start):
            cfg.dnd_start = cls.dnd_start
        if not isinstance(cfg.dnd_end, str) or not TIME_PATTERN.fullmatch(cfg.dnd_end):
            cfg.dnd_end = cls.dnd_end
        if not isinstance(cfg.opacity, (int, float)) or not 0.0 <= cfg.opacity <= 1.0:
            cfg.opacity = cls.opacity
        return cfg

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        """从文件加载配置"""
        if path is None:
            path = CONFIG_FILE
        if not path.exists():
            return cls()

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.sanitize(cls(**data))
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls()


# 全局配置实例
config = AppConfig.load()


def get_config() -> AppConfig:
    """获取全局配置"""
    return config


def save_config(cfg: Optional[AppConfig] = None, path: Path | None = None):
    """保存配置"""
    if cfg is None:
        cfg = config
    cfg.save(path)
