"""
Desktop AI Companion - Python 后端服务
提供 AI 对话接口和数据库访问
"""
import os
import shutil
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List
import uvicorn

from app.config import AppConfig, TIME_PATTERN, get_config, save_config as persist_config
from app.db import (
    clear_messages,
    create_companion,
    create_imported_model,
    delete_memory,
    get_active_companion,
    get_memories,
    get_messages,
    list_imported_models,
    list_companions,
    save_memory,
    save_message,
    set_active_companion,
)

# ============== 数据模型 ==============

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    context: List[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    content: str


class MemoryCreateRequest(BaseModel):
    content: str
    category: str = "preference"
    importance: int = 1


class CompanionCreateRequest(BaseModel):
    name: str
    character_type: str
    personality_tags: list[str] = Field(default_factory=list)
    interaction_mode: str = "work"


class ImportedModelRequest(BaseModel):
    model_path: str
    name: str

class Config(BaseModel):
    user_nickname: str = "小伙伴"
    user_display_name: str = "你"
    character_type: str = "hiyori_pro_zh"
    character_name: str = "小艾"
    personality: list[str] = Field(default_factory=lambda: ["温柔"])
    interaction_mode: str = "work"
    proactive_mode: str = "quiet"
    chat_model: str = "gpt"
    dnd_enabled: bool = False
    dnd_start: str = "22:00"
    dnd_end: str = "08:00"
    window_x: int = 100
    window_y: int = 100
    window_scale: float = 1.0
    character_scales: dict[str, float] = Field(default_factory=dict)
    api_provider: str = "default"
    model_name: str = "default"
    auto_start: bool = False
    always_on_top: bool = False
    click_through: bool = False
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    show_notifications: bool = True
    sound_enabled: bool = True

    @field_validator("dnd_start", "dnd_end")
    @classmethod
    def validate_time_string(cls, value: str) -> str:
        if not TIME_PATTERN.fullmatch(value):
            raise ValueError("must be a valid HH:MM time")
        return value


class ConfigUpdate(BaseModel):
    user_nickname: str | None = None
    user_display_name: str | None = None
    character_type: str | None = None
    character_name: str | None = None
    personality: list[str] | None = None
    interaction_mode: str | None = None
    proactive_mode: str | None = None
    chat_model: str | None = None
    dnd_enabled: bool | None = None
    dnd_start: str | None = None
    dnd_end: str | None = None
    window_x: int | None = None
    window_y: int | None = None
    window_scale: float | None = None
    character_scales: dict[str, float] | None = None
    api_provider: str | None = None
    model_name: str | None = None
    auto_start: bool | None = None
    always_on_top: bool | None = None
    click_through: bool | None = None
    opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    show_notifications: bool | None = None
    sound_enabled: bool | None = None

    @field_validator("dnd_start", "dnd_end")
    @classmethod
    def validate_optional_time_string(cls, value: str | None) -> str | None:
        if value is not None and not TIME_PATTERN.fullmatch(value):
            raise ValueError("must be a valid HH:MM time")
        return value


def apply_active_companion(current: AppConfig) -> AppConfig:
    active_companion = get_active_companion()
    config_data = current.__dict__.copy()
    if active_companion is not None:
        config_data["character_name"] = active_companion["name"]
        config_data["character_type"] = active_companion["character_type"]
        config_data["personality"] = active_companion["personality_tags"]
        config_data["interaction_mode"] = active_companion["interaction_mode"]
    return AppConfig(**config_data)


def to_api_config(current: AppConfig) -> Config:
    config_data = apply_active_companion(current).__dict__.copy()
    return Config.model_validate(config_data)


def is_vip_user() -> bool:
    return False


def extract_memory_candidates(message: str) -> list[dict]:
    candidates = []
    if "叫我" in message:
        candidates.append(
            {
                "content": message.strip(),
                "category": "preference",
                "importance": 3,
                "scope": "preference",
            }
        )
    if any(token in message for token in ["最近在做", "最近在准备", "这周在做"]):
        candidates.append(
            {
                "content": message.strip(),
                "category": "project",
                "importance": 2,
                "scope": "short_term",
            }
        )
    return candidates


def persist_memory_candidates(candidates: list[dict]):
    existing = {item["content"] for item in get_memories()}
    for candidate in candidates:
        if candidate["content"] in existing:
            continue
        save_memory(
            candidate["content"],
            category=candidate["category"],
            importance=candidate["importance"],
            scope=candidate["scope"],
        )


def build_memory_block(preference: list[dict], short_term: list[dict], long_term: list[dict]) -> str:
    lines = []
    if preference:
        lines.append("稳定偏好：")
        lines.extend(f"- {item['content']}" for item in preference[:3])
    if short_term:
        lines.append("近期情况：")
        lines.extend(f"- {item['content']}" for item in short_term[:3])
    if long_term:
        lines.append("长期记忆：")
        lines.extend(f"- {item['content']}" for item in long_term[:3])
    return "\n".join(lines) if lines else "- 暂无额外记忆"

# ============== FastAPI 应用 ==============

app = FastAPI(title="Desktop AI Companion API")

# 允许跨域 (Tauri 前端调用)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== API 端点 ==============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    AI 对话接口
    - message: 用户消息
    - context: 历史消息 (最近 10 条)
    """
    save_message("user", request.message)

    candidates = extract_memory_candidates(request.message)
    persist_memory_candidates(candidates)

    current = apply_active_companion(get_config())
    response_content = shape_companion_reply(
        request.message,
        generate_chat_response(request.message, request.context, current),
        current,
    )

    save_message("assistant", response_content)

    return ChatResponse(content=response_content)

@app.get("/config", response_model=Config)
async def get_config_endpoint():
    """获取配置"""
    return to_api_config(get_config())


@app.get("/companions")
async def get_companions():
    return list_companions()


@app.get("/companions/active")
async def get_active_companion_endpoint():
    return get_active_companion()


@app.post("/companions")
async def create_companion_endpoint(payload: CompanionCreateRequest):
    if len(list_companions()) >= 1 and not is_vip_user():
        raise HTTPException(status_code=403, detail="Free tier allows only one companion")

    companion_id = create_companion(
        name=payload.name,
        character_type=payload.character_type,
        personality_tags=payload.personality_tags,
        interaction_mode=payload.interaction_mode,
    )
    return {"status": "ok", "id": companion_id}


@app.post("/companions/{companion_id}/activate")
async def activate_companion(companion_id: int):
    if not any(companion["id"] == companion_id for companion in list_companions()):
        raise HTTPException(status_code=404, detail="Companion not found")
    set_active_companion(companion_id)
    return {"status": "ok"}


@app.get("/models/imported")
async def get_imported_models_endpoint():
    return list_imported_models()


@app.post("/models/imported")
async def import_model(payload: ImportedModelRequest):
    source_model = Path(payload.model_path).expanduser()
    if not source_model.exists() or not source_model.name.endswith('.model3.json'):
        raise HTTPException(status_code=400, detail="Invalid model3.json path")

    source_dir = source_model.parent
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in payload.name).strip('-') or 'imported-model'
    target_root = PROJECT_ROOT / 'assets' / 'live2d' / 'imported' / slug
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_dir, target_root)

    public_model_path = f"/live2d/imported/{slug}/{source_model.name}"
    model_id = create_imported_model(payload.name, public_model_path)
    return {"status": "ok", "id": model_id, "model_path": public_model_path}

@app.post("/config", response_model=Config)
async def save_config_endpoint(config: ConfigUpdate):
    """保存配置"""
    current = get_config()
    for field, value in config.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(current, field, value)
    persist_config(current)
    return to_api_config(current)

@app.get("/history")
async def get_history(limit: int = 50):
    """获取聊天记录"""
    return get_messages(limit=limit)

@app.delete("/history")
async def clear_history():
    """清空聊天记录"""
    clear_messages()
    return {"status": "ok"}


@app.get("/memory")
async def list_memory():
    """获取轻量记忆"""
    return get_memories()


@app.post("/memory")
async def create_memory(payload: MemoryCreateRequest):
    """创建轻量记忆"""
    save_memory(payload.content, payload.category, payload.importance)
    return {"status": "ok"}


@app.delete("/memory/{memory_id}")
async def remove_memory(memory_id: int):
    """删除轻量记忆"""
    delete_memory(memory_id)
    return {"status": "ok"}

# ============== 占位回复生成 ==============

def shape_companion_reply(message: str, raw_reply: str, config: AppConfig) -> str:
    user_name = config.user_display_name.strip() or config.user_nickname.strip() or "你"
    companion_name = config.character_name.strip() or "小艾"

    if any(word in message for word in ["累", "困", "烦", "难受", "压力"]):
        return f"{user_name}，辛苦啦。{companion_name}在这儿陪你一下。{raw_reply}"

    return f"{user_name}，{raw_reply}"


def generate_chat_response(message: str, context: list[ChatMessage], config: AppConfig) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.hanbbq.top/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()

    if not api_key:
        return generate_fallback_response(message)

    preference = get_memories(scope="preference")
    short_term = get_memories(scope="short_term")
    long_term = get_memories(scope="long_term")
    memory_block = build_memory_block(preference, short_term, long_term)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个住在桌面上的 AI 小伙伴。"
                    "回复简短、温柔、有一点陪伴感，不要像客服，不要长篇大论。"
                    "\n你已知的用户信息：\n"
                    f"{memory_block or '- 暂无额外记忆'}"
                ),
            },
            *[
                {"role": item.role, "content": item.content}
                for item in context[-8:]
            ],
            {"role": "user", "content": message},
        ],
        "temperature": 0.8,
    }

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return generate_fallback_response(message)

def generate_fallback_response(message: str) -> str:
    """生成占位回复 (后续替换为真实 AI)"""
    responses = [
        "嗯嗯，我明白了！",
        "这个话题很有趣呢～",
        "让我想想... 🤔",
        "你说得对！",
        "好哒，交给我吧！",
        "原来如此，涨知识了！",
        "嘿嘿，我也这么觉得～",
    ]
    import random
    return random.choice(responses)

# ============== 启动服务 ==============

if __name__ == "__main__":
    print("[INFO] Starting Desktop AI Companion Backend...")
    print("[INFO] URL: http://localhost:8080")
    print("[INFO] Docs: http://localhost:8080/docs")
    uvicorn.run(app, host="0.0.0.0", port=8080)
