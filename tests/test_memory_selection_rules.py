import sqlite3
from datetime import datetime, timedelta

import pytest

import app.db as db_module
from backend.server import extract_memory_candidates


@pytest.fixture(autouse=True)
def isolate_memory_db(tmp_path):
    db_module.DB_PATH = tmp_path / "memory-phase2.db"
    db_module.init_db()
    yield


def test_memory_scope_is_stored_and_filtered():
    db_module.save_memory("用户喜欢简短回复", category="preference", importance=3, scope="preference")
    db_module.save_memory("最近在做桌面 AI 项目", category="project", importance=2, scope="short_term")
    db_module.save_memory("长期喜欢治愈风格", category="preference", importance=2, scope="long_term")

    preference = db_module.get_memories(scope="preference")
    short_term = db_module.get_memories(scope="short_term")
    long_term = db_module.get_memories(scope="long_term")

    assert any(item["content"] == "用户喜欢简短回复" for item in preference)
    assert any(item["content"] == "最近在做桌面 AI 项目" for item in short_term)
    assert any(item["content"] == "长期喜欢治愈风格" for item in long_term)


def test_delete_expired_short_term_memories_removes_old_rows():
    db_module.save_memory("最近在准备考试", category="project", importance=2, scope="short_term")
    db_module.save_memory("长期偏好安静回复", category="preference", importance=2, scope="long_term")

    conn = sqlite3.connect(db_module.DB_PATH)
    conn.execute(
        "UPDATE memories SET created_at = ? WHERE content = ?",
        ((datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"), "最近在准备考试"),
    )
    conn.commit()
    conn.close()

    db_module.delete_expired_short_term_memories(max_age_hours=24)
    remaining = db_module.get_memories()

    assert all(item["content"] != "最近在准备考试" for item in remaining)
    assert any(item["content"] == "长期偏好安静回复" for item in remaining)


def test_extracts_explicit_preference_candidate():
    candidates = extract_memory_candidates("你以后叫我阿泽就好")
    assert any(item["scope"] == "preference" for item in candidates)


def test_extracts_short_term_project_candidate():
    candidates = extract_memory_candidates("我最近在做一个桌面 AI 项目")
    assert any(item["scope"] == "short_term" for item in candidates)
