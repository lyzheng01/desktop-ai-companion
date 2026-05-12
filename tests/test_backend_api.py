from fastapi.testclient import TestClient

from app.config import AppConfig, CONFIG_FILE, save_config
from app.db import clear_messages, get_messages
from backend.server import app


client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_round_trip_persists_values():
    save_config(AppConfig())

    payload = {
        "user_nickname": "测试用户",
        "user_display_name": "阿泽",
        "character_type": "kei",
        "character_name": "千岁",
        "personality": ["元气", "治愈"],
        "interaction_mode": "daily",
        "proactive_mode": "greet",
        "chat_model": "deepseek",
        "window_x": 123,
        "window_y": 456,
        "window_scale": 0.88,
        "character_scales": {"kei": 0.88, "hiyori": 0.72},
    }

    save_response = client.post("/config", json=payload)
    assert save_response.status_code == 200

    load_response = client.get("/config")
    assert load_response.status_code == 200
    data = load_response.json()
    assert data["user_nickname"] == "测试用户"
    assert data["user_display_name"] == "阿泽"
    assert data["character_name"] == "千岁"
    assert data["personality"] == ["元气", "治愈"]
    assert data["interaction_mode"] == "daily"
    assert data["proactive_mode"] == "greet"
    assert data["chat_model"] == "deepseek"
    assert data["window_x"] == 123
    assert data["window_y"] == 456
    assert data["window_scale"] == 0.88
    assert data["character_scales"]["hiyori"] == 0.72

    persisted = AppConfig.load(CONFIG_FILE)
    assert persisted.user_nickname == "测试用户"
    assert persisted.user_display_name == "阿泽"
    assert persisted.character_name == "千岁"
    assert persisted.personality == ["元气", "治愈"]
    assert persisted.interaction_mode == "daily"
    assert persisted.proactive_mode == "greet"
    assert persisted.chat_model == "deepseek"
    assert persisted.window_x == 123
    assert persisted.window_y == 456
    assert persisted.window_scale == 0.88
    assert persisted.character_scales["kei"] == 0.88


def test_chat_writes_history():
    clear_messages()
    client.delete("/history")
    chat_response = client.post("/chat", json={"message": "你好", "context": []})
    assert chat_response.status_code == 200

    history_response = client.get("/history")
    history = history_response.json()
    assert len(history) >= 2
    assert history[-2]["role"] == "user"
    assert history[-1]["role"] == "assistant"

    stored = get_messages(limit=10)
    assert len(stored) >= 2
    assert stored[-2]["role"] == "user"
    assert stored[-1]["role"] == "assistant"
