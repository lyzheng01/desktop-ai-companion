import json

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

import app.config as config_module
import app.db as db_module
from app.config import AppConfig, save_config
from app.db import create_companion, get_active_companion, set_active_companion
from app.db import clear_messages, get_messages
from backend.server import app
import backend.server as server_module


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_test_storage(tmp_path):
    config_module.CONFIG_FILE = tmp_path / "config.json"
    config_module.DB_PATH = tmp_path / "companion.db"
    db_module.DB_PATH = tmp_path / "companion.db"
    config_module.config = AppConfig()
    save_config(config_module.config)
    db_module.init_db()
    yield


def reset_live_config(cfg: AppConfig | None = None):
    if cfg is None:
        cfg = AppConfig()
    config_module.config = cfg
    save_config(cfg)


def test_health_endpoint_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_resolve_llm_settings_prefers_env_overrides(monkeypatch):
    monkeypatch.delenv("DESKTOP_AI_COMPANION_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DESKTOP_AI_COMPANION_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("DESKTOP_AI_COMPANION_OPENAI_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-chat")

    api_key, base_url, model = server_module.resolve_llm_settings(AppConfig())

    assert api_key == "env-key"
    assert base_url == "https://api.deepseek.com/v1"
    assert model == "deepseek-chat"


def test_resolve_llm_settings_prefers_desktop_specific_env_over_generic(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "generic-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.generic.example/v1")
    monkeypatch.setenv("OPENAI_MODEL", "generic-model")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_API_KEY", "desktop-key")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_MODEL", "deepseek-chat")

    api_key, base_url, model = server_module.resolve_llm_settings(AppConfig())

    assert api_key == "desktop-key"
    assert base_url == "https://api.deepseek.com/v1"
    assert model == "deepseek-chat"


def test_resolve_live_search_llm_settings_uses_default_search_provider_when_primary_chat_is_deepseek(monkeypatch):
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_API_KEY", "desktop-key")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_MODEL", "deepseek-chat")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.aixhan.com/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("DESKTOP_AI_COMPANION_LIVE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DESKTOP_AI_COMPANION_LIVE_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("DESKTOP_AI_COMPANION_LIVE_OPENAI_MODEL", raising=False)

    api_key, base_url, model = server_module.resolve_live_search_llm_settings(AppConfig())

    assert bool(api_key) is True
    assert base_url == server_module.DEFAULT_LLM_BASE_URL
    assert model == server_module.DEFAULT_LLM_MODEL


def test_resolve_live_search_llm_settings_prefers_dedicated_live_search_env(monkeypatch):
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_API_KEY", "desktop-key")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_OPENAI_MODEL", "deepseek-chat")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_LIVE_OPENAI_API_KEY", "live-key")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_LIVE_OPENAI_BASE_URL", "https://live-search.example/v1")
    monkeypatch.setenv("DESKTOP_AI_COMPANION_LIVE_OPENAI_MODEL", "live-model")

    api_key, base_url, model = server_module.resolve_live_search_llm_settings(AppConfig())

    assert api_key == "live-key"
    assert base_url == "https://live-search.example/v1"
    assert model == "live-model"


def test_chat_prefers_native_live_response_for_live_queries(monkeypatch):
    monkeypatch.setattr(server_module, "generate_native_live_response", lambda message, context, config: "你，今天是 2026年05月16日，星期六。")
    monkeypatch.setattr(server_module, "search_web", lambda query: (_ for _ in ()).throw(AssertionError("search_web should not be called")))

    response = client.post("/chat", json={"message": "今天多少号", "context": []})

    assert response.status_code == 200
    assert "2026年05月16日" in response.json()["content"]


def test_passthrough_route_uses_frontend_prompt_without_persisting_user_display_name(monkeypatch):
    reset_live_config(AppConfig(user_nickname="小伙伴", user_display_name="你"))

    captured = {}
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {
            "id": 101,
            "phone": "13800138000",
            "nickname": "owner",
            "avatar_url": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        server_module,
        "get_user_membership",
        lambda user_id: {
            "plan_code": "vip_monthly",
            "tier": "vip",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": {"daily_message_quota": 30, "model_access_level": "vip"},
        },
    )
    monkeypatch.setattr(server_module, "consume_chat_quota_or_raise", lambda user_id, membership: None, raising=False)

    monkeypatch.setattr(
        server_module,
        "resolve_llm_settings",
        lambda config: ("key", "http://example.test/v1", "demo-model"),
    )
    class DummyResponse:
        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"主人，你好"}}]}'
            yield "data: [DONE]"

    class DummyStream:
        def __enter__(self):
            return DummyResponse()

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_stream(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return DummyStream()

    monkeypatch.setattr("backend.passthrough_chat.httpx.stream", fake_stream)

    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "你正在陪伴的用户叫主人。",
            "message": "你好",
            "context": [],
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert captured["method"] == "POST"
    assert captured["url"] == "http://example.test/v1/chat/completions"
    assert captured["json"]["messages"][0] == {"role": "system", "content": "你正在陪伴的用户叫主人。"}
    assert AppConfig.load(config_module.CONFIG_FILE).user_display_name == "你"
    assert config_module.config.user_display_name == "你"

def test_passthrough_route_requires_login_before_streaming(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "iter_passthrough_stream",
        lambda **kwargs: iter([b"event: done\ndata: {}\n\n"]),
    )

    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "persona",
            "message": "hello",
            "context": [],
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "请先登录账号后再使用大模型对话"


def test_passthrough_route_rejects_when_daily_quota_is_exhausted(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {
            "id": 101,
            "phone": "13800138000",
            "nickname": "owner",
            "avatar_url": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        server_module,
        "get_user_membership",
        lambda user_id: {
            "plan_code": "free",
            "tier": "free",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": {"daily_message_quota": 10, "model_access_level": "free"},
        },
    )

    def raise_quota_exhausted(user_id, membership):
        raise HTTPException(status_code=403, detail="今日大模型对话次数已用完，请明天再试或开通 VIP")

    monkeypatch.setattr(server_module, "consume_chat_quota_or_raise", raise_quota_exhausted, raising=False)
    monkeypatch.setattr(
        server_module,
        "iter_passthrough_stream",
        lambda **kwargs: iter([b"event: done\ndata: {}\n\n"]),
    )

    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "persona",
            "message": "hello",
            "context": [],
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "今日大模型对话次数已用完，请明天再试或开通 VIP"


def test_proactive_weather_endpoint_returns_content(monkeypatch):
    monkeypatch.setattr(server_module, "build_proactive_weather_line", lambda location='合肥': f"{location}今天晴天，适合出门。")

    response = client.get("/proactive/weather?location=合肥")

    assert response.status_code == 200
    assert response.json()["content"] == "合肥今天晴天，适合出门。"
    assert response.json()["trigger"] == "weather_update"


def test_proactive_followup_endpoint_returns_content(monkeypatch):
    monkeypatch.setattr(server_module, "build_care_followup_line", lambda: "昨天你好像有点不舒服，今天好一点了吗？")

    response = client.get("/proactive/followup")

    assert response.status_code == 200
    assert response.json()["trigger"] == "care_followup"
    assert response.json()["content"] == "昨天你好像有点不舒服，今天好一点了吗？"


def test_data_dir_endpoint_returns_current_runtime_dir(tmp_path):
    config_module.set_data_dir(tmp_path / 'chosen-data')

    response = client.get('/data-dir')

    assert response.status_code == 200
    assert response.json()['data_dir'] == str((tmp_path / 'chosen-data').resolve())


def test_data_dir_endpoint_updates_runtime_dir(tmp_path):
    target = tmp_path / 'new-data-home'

    response = client.post('/data-dir', json={'data_dir': str(target)})

    assert response.status_code == 200
    assert response.json()['data_dir'] == str(target.resolve())
    assert config_module.get_data_dir() == target.resolve()


def test_data_dir_endpoint_can_migrate_existing_files(tmp_path):
    source = tmp_path / 'source-data'
    source.mkdir(parents=True)
    config_module.set_data_dir(source)
    (source / 'config.json').write_text('{"hello":"world"}', encoding='utf-8')

    target = tmp_path / 'target-data'
    response = client.post('/data-dir', json={'data_dir': str(target), 'migrate_existing': True})

    assert response.status_code == 200
    assert (target / 'config.json').exists()


def test_config_name_update_syncs_active_companion():
    companion_id = create_companion(
        name="小艾",
        character_type="hiyori_pro_zh",
        personality_tags=["温柔"],
        interaction_mode="work",
        is_active=True,
    )
    set_active_companion(companion_id)

    response = client.post("/config", json={"character_name": "小天"})

    assert response.status_code == 200
    assert response.json()["character_name"] == "小天"
    assert get_active_companion()["name"] == "小天"


def test_config_round_trip_persists_values():
    reset_live_config()

    payload = {
        "user_nickname": "测试用户",
        "user_display_name": "阿泽",
        "character_type": "kei",
        "character_name": "千岁",
        "personality": ["元气", "治愈"],
        "interaction_mode": "daily",
        "proactive_mode": "greet",
        "chat_model": "deepseek",
        "dnd_enabled": True,
        "dnd_start": "21:30",
        "dnd_end": "07:45",
        "window_x": 123,
        "window_y": 456,
        "window_scale": 0.88,
        "character_scales": {"kei": 0.88, "hiyori": 0.72},
        "auto_start": True,
        "always_on_top": True,
        "click_through": True,
        "opacity": 0.76,
        "api_provider": "custom",
        "model_name": "deepseek-chat",
        "show_notifications": False,
        "sound_enabled": False,
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
    assert data["dnd_enabled"] is True
    assert data["dnd_start"] == "21:30"
    assert data["dnd_end"] == "07:45"
    assert data["window_x"] == 123
    assert data["window_y"] == 456
    assert data["window_scale"] == 0.88
    assert data["character_scales"]["hiyori"] == 0.72
    assert data["auto_start"] is True
    assert data["always_on_top"] is True
    assert data["click_through"] is True
    assert data["opacity"] == 0.76
    assert data["api_provider"] == "custom"
    assert data["model_name"] == "deepseek-chat"
    assert data["show_notifications"] is False
    assert data["sound_enabled"] is False

    persisted = AppConfig.load(config_module.CONFIG_FILE)
    assert persisted.user_nickname == "测试用户"
    assert persisted.user_display_name == "阿泽"
    assert persisted.character_name == "千岁"
    assert persisted.personality == ["元气", "治愈"]
    assert persisted.interaction_mode == "daily"
    assert persisted.proactive_mode == "greet"
    assert persisted.chat_model == "deepseek"
    assert persisted.dnd_enabled is True
    assert persisted.dnd_start == "21:30"
    assert persisted.dnd_end == "07:45"
    assert persisted.window_x == 123
    assert persisted.window_y == 456
    assert persisted.window_scale == 0.88
    assert persisted.character_scales["kei"] == 0.88
    assert persisted.auto_start is True
    assert persisted.always_on_top is True
    assert persisted.click_through is True
    assert persisted.opacity == 0.76
    assert persisted.api_provider == "custom"
    assert persisted.model_name == "deepseek-chat"
    assert persisted.show_notifications is False
    assert persisted.sound_enabled is False

    reset_live_config()


def test_config_partial_update_preserves_unrelated_fields():
    reset_live_config(
        AppConfig(
            user_nickname="测试用户",
            character_type="kei",
            dnd_enabled=True,
            dnd_start="21:30",
            dnd_end="07:45",
            auto_start=True,
            always_on_top=True,
            click_through=True,
            opacity=0.55,
        )
    )

    response = client.post("/config", json={"opacity": 0.76})

    assert response.status_code == 200
    data = response.json()
    assert data["opacity"] == 0.76
    assert data["user_nickname"] == "测试用户"
    assert data["character_type"] == "kei"
    assert data["dnd_enabled"] is True
    assert data["dnd_start"] == "21:30"
    assert data["dnd_end"] == "07:45"
    assert data["auto_start"] is True
    assert data["always_on_top"] is True
    assert data["click_through"] is True

    persisted = AppConfig.load(config_module.CONFIG_FILE)
    assert persisted.opacity == 0.76
    assert persisted.user_nickname == "测试用户"
    assert persisted.character_type == "kei"
    assert persisted.dnd_enabled is True
    assert persisted.dnd_start == "21:30"
    assert persisted.dnd_end == "07:45"
    assert persisted.auto_start is True
    assert persisted.always_on_top is True
    assert persisted.click_through is True

    reset_live_config()


def test_config_partial_update_ignores_explicit_null_values():
    reset_live_config(AppConfig(user_nickname="测试用户"))

    response = client.post("/config", json={"user_nickname": None})

    assert response.status_code == 200
    assert response.json()["user_nickname"] == "测试用户"

    persisted = AppConfig.load(config_module.CONFIG_FILE)
    assert persisted.user_nickname == "测试用户"

    reset_live_config()


def test_config_get_does_not_expose_api_key():
    reset_live_config(AppConfig(api_key="secret-key"))

    response = client.get("/config")

    assert response.status_code == 200
    assert "api_key" not in response.json()


def test_config_rejects_invalid_dnd_time_strings():
    reset_live_config()

    response = client.post(
        "/config",
        json={
            "dnd_start": "25:99",
            "dnd_end": "07:45",
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"][-1] == "dnd_start" for error in errors)


def test_config_rejects_opacity_outside_desktop_range():
    reset_live_config()

    response = client.post(
        "/config",
        json={
            "opacity": 1.5,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"][-1] == "opacity" for error in errors)


def test_config_get_sanitizes_invalid_persisted_values():
    with open(config_module.CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "dnd_start": "25:99",
                "dnd_end": "abc",
                "opacity": 9.9,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    config_module.config = AppConfig.load(config_module.CONFIG_FILE)

    response = client.get("/config")

    assert response.status_code == 200
    data = response.json()
    assert data["dnd_start"] == "22:00"
    assert data["dnd_end"] == "08:00"
    assert data["opacity"] == 1.0

    reset_live_config()


def test_config_get_sanitizes_invalid_persisted_scalar_field():
    with open(config_module.CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "window_x": None,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    config_module.config = AppConfig.load(config_module.CONFIG_FILE)

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json()["window_x"] == 100

    reset_live_config()


def test_config_load_falls_back_on_malformed_json():
    with open(config_module.CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write("{")

    loaded = AppConfig.load(config_module.CONFIG_FILE)

    assert loaded == AppConfig()


def test_config_get_sanitizes_invalid_persisted_personality_shape():
    with open(config_module.CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "personality": "温柔",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    config_module.config = AppConfig.load(config_module.CONFIG_FILE)

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json()["personality"] == ["温柔"]

    reset_live_config()


def test_config_get_sanitizes_invalid_persisted_character_scales_shape():
    with open(config_module.CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "character_scales": ["bad"],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    config_module.config = AppConfig.load(config_module.CONFIG_FILE)

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json()["character_scales"] == {}

    reset_live_config()


def test_config_projects_active_companion_identity():
    reset_live_config(
        AppConfig(
            character_name="全局角色",
            character_type="global",
            personality=["冷静"],
            interaction_mode="study",
        )
    )

    companion_id = create_companion(
        name="小艾",
        character_type="hiyori_pro_zh",
        personality_tags=["温柔", "治愈"],
        interaction_mode="work",
        is_active=False,
    )
    set_active_companion(companion_id)

    response = client.get("/config")

    assert response.status_code == 200
    data = response.json()
    assert data["character_name"] == "小艾"
    assert data["character_type"] == "hiyori_pro_zh"
    assert data["personality"] == ["温柔", "治愈"]
    assert data["interaction_mode"] == "work"

    reset_live_config()


def test_chat_uses_active_companion_identity_for_reply_shaping():
    reset_live_config(
        AppConfig(
            user_display_name="阿泽",
            character_name="全局角色",
            character_type="global",
            personality=["冷静"],
            interaction_mode="study",
        )
    )

    companion_id = create_companion(
        name="小艾",
        character_type="hiyori_pro_zh",
        personality_tags=["温柔"],
        interaction_mode="work",
        is_active=False,
    )
    set_active_companion(companion_id)

    response = client.post("/chat", json={"message": "我今天有点累", "context": []})

    assert response.status_code == 200
    content = response.json()["content"]
    assert content.startswith("阿泽，辛苦啦。小艾在这儿陪你一下。")
    assert "全局角色" not in content

    reset_live_config()


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
