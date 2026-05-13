from fastapi.testclient import TestClient

import app.config as config_module
from app.config import AppConfig, save_config
from backend.server import app


client = TestClient(app)


def reset_config() -> None:
    config_module.config = AppConfig(
        user_nickname="阿泽",
        user_display_name="阿泽",
        character_name="小艾",
        personality=["温柔"],
    )
    save_config(config_module.config)


def test_chat_reply_mentions_user_or_companion_tone():
    reset_config()

    response = client.post("/chat", json={"message": "今天有点累", "context": []})

    assert response.status_code == 200
    content = response.json()["content"]
    assert isinstance(content, str)
    assert content.strip() != ""
    assert any(token in content for token in ["阿泽", "小艾", "辛苦", "陪", "休息"])
