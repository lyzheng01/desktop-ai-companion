"""
配置管理模块
"""
import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional


# 应用目录
APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "companion.db"
CONFIG_FILE = DATA_DIR / "config.json"

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)

TIME_PATTERN = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


@dataclass
class AppConfig:
    """应用配置"""

    # 用户信息
    user_nickname: str = "小伙伴"
    user_display_name: str = "你"

    # 角色设置
    character_type: str = "kei"
    character_name: str = "小艾"
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
