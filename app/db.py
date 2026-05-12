"""
数据库模块 - SQLite 本地存储
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from .config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()

    # 用户配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 角色配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            personality TEXT,
            avatar_path TEXT,
            is_active BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 聊天记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,  -- user 或 assistant
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT
        )
    """)

    # 记忆表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT,  -- preference, fact, event
            importance INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ============== 用户配置 CRUD ==============

def save_setting(key: str, value: Any):
    """保存设置"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO user_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (key, json.dumps(value, ensure_ascii=False)))
    conn.commit()
    conn.close()


def get_setting(key: str, default: Any = None) -> Any:
    """获取设置"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM user_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return default


# ============== 聊天记录 CRUD ==============

def save_message(role: str, content: str, session_id: Optional[str] = None):
    """保存聊天消息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages (role, content, session_id)
        VALUES (?, ?, ?)
    """, (role, content, session_id))
    conn.commit()
    conn.close()


def get_messages(limit: int = 50, session_id: Optional[str] = None) -> List[Dict]:
    """获取聊天记录"""
    conn = get_connection()
    cursor = conn.cursor()

    if session_id:
        cursor.execute("""
            SELECT role, content, timestamp
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (session_id, limit))
    else:
        cursor.execute("""
            SELECT role, content, timestamp
            FROM chat_messages
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]}
        for row in rows
    ][::-1]  # 正序返回


def clear_messages(session_id: Optional[str] = None):
    """清空聊天记录"""
    conn = get_connection()
    cursor = conn.cursor()
    if session_id:
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    else:
        cursor.execute("DELETE FROM chat_messages")
    conn.commit()
    conn.close()


# ============== 记忆 CRUD ==============

def save_memory(content: str, category: str = "fact", importance: int = 1):
    """保存记忆"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO memories (content, category, importance)
        VALUES (?, ?, ?)
    """, (content, category, importance))
    conn.commit()
    conn.close()


def get_memories(category: Optional[str] = None) -> List[Dict]:
    """获取记忆"""
    conn = get_connection()
    cursor = conn.cursor()

    if category:
        cursor.execute("""
            SELECT id, content, category, importance, created_at
            FROM memories
            WHERE category = ?
            ORDER BY importance DESC, created_at DESC
        """, (category,))
    else:
        cursor.execute("""
            SELECT id, content, category, importance, created_at
            FROM memories
            ORDER BY importance DESC, created_at DESC
        """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "content": row["content"],
            "category": row["category"],
            "importance": row["importance"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


def delete_memory(memory_id: int):
    """删除记忆"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()


# 初始化数据库
init_db()
