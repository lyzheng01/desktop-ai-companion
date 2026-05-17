import app.config as config_module
import app.db as db_module
from fastapi.testclient import TestClient
import pytest
from app.db import create_companion, get_active_companion, list_companions, set_active_companion
from app.config import AppConfig, save_config
from backend.server import app


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


def test_create_and_activate_companion_flow(tmp_path):
    config_module.DB_PATH = tmp_path / "companion.db"
    db_module.DB_PATH = tmp_path / "companion.db"
    db_module.init_db()

    first_id = create_companion(
        name="小艾",
        character_type="hiyori_pro_zh",
        personality_tags=["温柔"],
        interaction_mode="work",
        is_active=True,
    )

    second_id = create_companion(
        name="小晴",
        character_type="natori_pro_zh",
        personality_tags=["元气"],
        interaction_mode="daily",
        is_active=False,
    )

    companions = list_companions()
    assert len(companions) == 2
    assert companions[0]["id"] == first_id
    assert companions[0]["character_type"] == "hiyori_pro_zh"
    assert companions[0]["personality_tags"] == ["温柔"]
    assert companions[0]["interaction_mode"] == "work"
    assert companions[0]["is_active"] is True
    assert companions[1]["id"] == second_id
    assert companions[1]["character_type"] == "natori_pro_zh"
    assert companions[1]["personality_tags"] == ["元气"]
    assert companions[1]["interaction_mode"] == "daily"
    assert companions[1]["is_active"] is False
    assert get_active_companion()["id"] == first_id

    set_active_companion(second_id)
    assert get_active_companion()["id"] == second_id

    companions = list_companions()
    assert companions[0]["is_active"] is False
    assert companions[1]["is_active"] is True


def test_set_active_companion_keeps_existing_active_when_target_missing(tmp_path):
    config_module.DB_PATH = tmp_path / "companion.db"
    db_module.DB_PATH = tmp_path / "companion.db"
    db_module.init_db()

    first_id = create_companion(
        name="小艾",
        character_type="hiyori_pro_zh",
        personality_tags=["温柔"],
        interaction_mode="work",
        is_active=True,
    )

    set_active_companion(first_id + 999)

    active = get_active_companion()
    assert active is not None
    assert active["id"] == first_id


def test_create_list_and_activate_companions_via_api():
    create_response = client.post(
        "/companions",
        json={
            "name": "小艾",
            "character_type": "hiyori_pro_zh",
            "personality_tags": ["温柔"],
            "interaction_mode": "work",
        },
    )
    assert create_response.status_code == 200

    list_response = client.get("/companions")
    assert list_response.status_code == 200
    companions = list_response.json()
    assert len(companions) == 1
    assert companions[0]["name"] == "小艾"
    assert companions[0]["is_active"] is False

    active_response = client.get("/companions/active")
    assert active_response.status_code == 200
    assert active_response.json() is None

    companion_id = companions[0]["id"]
    activate_response = client.post(f"/companions/{companion_id}/activate")
    assert activate_response.status_code == 200

    config_response = client.get("/config")
    assert config_response.status_code == 200
    config_data = config_response.json()
    assert config_data["character_name"] == companions[0]["name"]
    assert config_data["character_type"] == "hiyori_pro_zh"
    assert config_data["personality"] == companions[0]["personality_tags"]
    assert config_data["interaction_mode"] == "work"

    active_response = client.get("/companions/active")
    assert active_response.status_code == 200
    assert active_response.json()["id"] == companion_id

    list_response = client.get("/companions")
    companions = list_response.json()
    assert companions[0]["is_active"] is True


def test_activate_companion_via_api_returns_404_and_keeps_active_state_when_missing():
    first_create_response = client.post(
        "/companions",
        json={
            "name": "小艾",
            "character_type": "hiyori_pro_zh",
            "personality_tags": ["温柔"],
            "interaction_mode": "work",
        },
    )
    assert first_create_response.status_code == 200

    valid_id = first_create_response.json()["id"]
    activate_response = client.post(f"/companions/{valid_id}/activate")
    assert activate_response.status_code == 200

    invalid_activate_response = client.post(f"/companions/{valid_id + 999}/activate")
    assert invalid_activate_response.status_code == 404

    active_response = client.get("/companions/active")
    assert active_response.status_code == 200
    assert active_response.json()["id"] == valid_id

    config_response = client.get("/config")
    assert config_response.status_code == 200
    assert config_response.json()["character_name"] == "小艾"


def test_free_user_cannot_create_second_companion():
    first_response = client.post(
        "/companions",
        json={
            "name": "小艾",
            "character_type": "hiyori_pro_zh",
            "personality_tags": ["温柔"],
            "interaction_mode": "work",
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/companions",
        json={
            "name": "小晴",
            "character_type": "natori_pro_zh",
            "personality_tags": ["元气"],
            "interaction_mode": "daily",
        },
    )
    assert second_response.status_code == 403
