"""
配置管理模块
"""
import json
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


@dataclass
class AppConfig:
    """应用配置"""

    # 用户信息
    user_nickname: str = "小伙伴"
    user_display_name: str = "你"

    # 角色设置
    character_type: str = "robot"  # anime, pet, robot
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
    show_notifications: bool = True
    sound_enabled: bool = True

    def save(self, path: Path = CONFIG_FILE):
        """保存配置到文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "AppConfig":
        """从文件加载配置"""
        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return cls(**data)


# 全局配置实例
config = AppConfig.load()


def get_config() -> AppConfig:
    """获取全局配置"""
    return config


def save_config(cfg: Optional[AppConfig] = None):
    """保存配置"""
    if cfg is None:
        cfg = config
    cfg.save()
