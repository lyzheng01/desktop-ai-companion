from __future__ import annotations

from typing import Any

from app.db import get_memories


def dedupe_text_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def build_memory_summary(user_id: int, companion_id: int) -> list[dict[str, Any]]:
    memories = get_memories(user_id=user_id, companion_id=companion_id)
    return memories[:30]


def build_memory_context_message(user_id: int, companion_id: int) -> str | None:
    memories = build_memory_summary(user_id, companion_id)
    if not memories:
        return None

    preference = [item for item in memories if item.get("scope") == "preference"][:4]
    short_term = [item for item in memories if item.get("scope") == "short_term"][:3]
    long_term = [item for item in memories if item.get("scope") == "long_term"][:3]

    sections: list[str] = []
    if preference:
        sections.append("稳定偏好：\n" + "\n".join(f"- {item['content']}" for item in preference))
    if short_term:
        sections.append("近期情况：\n" + "\n".join(f"- {item['content']}" for item in short_term))
    if long_term:
        sections.append("长期记忆：\n" + "\n".join(f"- {item['content']}" for item in long_term))

    if not sections:
        return None

    return "以下是你已经记住的陪伴信息，请自然地参考，不要生硬复述，也不要假装知道更多：\n" + "\n\n".join(sections)
