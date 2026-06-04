from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ReplyMetadata:
    text: str
    emotion: str
    context: str
    animation_hint: str
    should_speak: bool
    audio_url: str | None = None


def infer_reply_metadata(message: str, reply: str, config: Any) -> ReplyMetadata:
    text = (reply or "").strip()
    lowered_message = (message or "").lower()
    lowered_reply = text.lower()

    emotion = "calm"
    context = "general"
    animation_hint = "talk_soft"

    if any(token in message for token in ["累", "困", "烦", "难受", "压力", "焦虑"]):
        emotion = "concerned"
        context = "comfort"
        animation_hint = "comfort_talk"
    elif any(token in message for token in ["谢谢", "好耶", "开心", "喜欢", "太棒了"]) or any(
        token in lowered_reply for token in ["太好了", "真棒", "开心", "喜欢"]
    ):
        emotion = "happy"
        context = "praise"
        animation_hint = "happy_talk"
    elif any(token in lowered_message for token in ["怎么", "为什么", "如何", "explain", "help me understand"]):
        emotion = "serious"
        context = "explain"
        animation_hint = "explain_talk"
    elif any(token in message for token in ["记得", "提醒", "别忘了"]):
        emotion = "calm"
        context = "remind"
        animation_hint = "remind_talk"

    return ReplyMetadata(
        text=text,
        emotion=emotion,
        context=context,
        animation_hint=animation_hint,
        should_speak=bool(text),
        audio_url=None,
    )


def build_chat_response_payload(message: str, reply: str, config: Any) -> dict[str, Any]:
    meta = infer_reply_metadata(message, reply, config)
    return {
        "content": meta.text,
        "text": meta.text,
        "emotion": meta.emotion,
        "context": meta.context,
        "animation_hint": meta.animation_hint,
        "should_speak": meta.should_speak,
        "audio_url": meta.audio_url,
    }


def build_stream_final_meta(message: str, reply: str, config: Any) -> dict[str, Any]:
    meta = infer_reply_metadata(message, reply, config)
    return {
        "text": meta.text,
        "emotion": meta.emotion,
        "context": meta.context,
        "animation_hint": meta.animation_hint,
        "should_speak": meta.should_speak,
        "audio_url": meta.audio_url,
    }
