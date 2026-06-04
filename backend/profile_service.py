from __future__ import annotations

from app.config import AppConfig
from app.db import get_memories, get_messages
from backend.memory_service import dedupe_text_items


PERSONA_LABEL_MAP = {
    "warm": "温柔型",
    "energetic": "元气型",
    "companion": "陪伴型",
}


def get_persona_label(config: AppConfig) -> str:
    chat_model = (config.chat_model or "").strip().lower()
    return PERSONA_LABEL_MAP.get(chat_model, PERSONA_LABEL_MAP["warm"])


def get_interaction_mode_label(mode: str) -> str:
    labels = {
        "work": "工作陪伴",
        "daily": "日常陪伴",
        "quiet": "安静陪伴",
        "sleep": "休息模式",
        "study": "学习陪伴",
    }
    return labels.get(mode, mode or "工作陪伴")


def build_preferences_context_message(config: AppConfig, user_id: int, companion_id: int) -> str:
    preference_memories = [item["content"] for item in get_memories(user_id=user_id, companion_id=companion_id, scope="preference")[:8]]
    items = dedupe_text_items([
        "默认使用中文",
        "默认结构化输出",
        "优先给结论，再补解释",
        "默认简短回复，减少废话",
        *preference_memories,
    ])
    return "以下是用户已经表现出的输出与沟通偏好，请优先贴合这些偏好：\n" + "\n".join(f"- {item}" for item in items)


def build_reflection_context_message(config: AppConfig, user_id: int, companion_id: int) -> str | None:
    memories = get_memories(user_id=user_id, companion_id=companion_id)
    current_project = [item["content"] for item in memories if item.get("category") == "current_project"][:3]
    current_focus = [item["content"] for item in memories if item.get("category") == "current_focus"][:3]
    recent_user_topics = [item["content"].strip() for item in get_messages(user_id=user_id, companion_id=companion_id, limit=6) if item["role"] == "user" and item["content"].strip()]
    observations = dedupe_text_items([*current_project, *current_focus, *recent_user_topics])[:6]
    if not observations:
        return None
    return "以下是对用户当前阶段和近期状态的内部总结，请据此更贴合地回应：\n" + "\n".join(f"- {item}" for item in observations)


def build_user_profile_context_message(config: AppConfig, user_id: int, companion_id: int) -> str:
    memories = get_memories(user_id=user_id, companion_id=companion_id)
    current_project = [item["content"] for item in memories if item.get("category") == "current_project"][:3]
    stable_preferences = [item["content"] for item in memories if item.get("scope") == "preference"][:5]
    lines = dedupe_text_items([
        f"用户称呼偏好：{config.user_display_name or config.user_nickname or '你'}",
        f"当前人格原型：{get_persona_label(config)}",
        f"当前互动模式：{get_interaction_mode_label(config.interaction_mode)}",
        *current_project,
        *stable_preferences,
    ])
    return "以下是当前用户画像摘要，请把它当作长期理解背景：\n" + "\n".join(f"- {item}" for item in lines)


def build_interaction_rules_context_message(config: AppConfig) -> str:
    return "\n".join([
        "以下是陪伴互动规则，请严格遵守：",
        f"- 当前人格原型：{get_persona_label(config)}。",
        "- 默认简短回复，不抢注意力。",
        "- 用户忙时更克制，用户低落时更温柔。",
        "- 能给方案就不要只提问题。",
        "- 只有在有明确价值时才主动。",
        "- 用户没有要求时，不要长篇展开。",
    ])


def build_profile_context_messages(config: AppConfig, user_id: int, companion_id: int) -> list[str]:
    messages = [
        build_user_profile_context_message(config, user_id, companion_id),
        build_preferences_context_message(config, user_id, companion_id),
        build_reflection_context_message(config, user_id, companion_id),
        build_interaction_rules_context_message(config),
    ]
    return [message for message in messages if message]
