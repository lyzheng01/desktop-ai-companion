"""
Desktop AI Companion - Python 后端服务
提供 AI 对话接口和数据库访问
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List
import uvicorn

from app.config import AppConfig, TIME_PATTERN, get_config, save_config as persist_config
from app.db import clear_messages, get_messages, save_message

# ============== 数据模型 ==============

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    context: List[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    content: str

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


def to_api_config(current: AppConfig) -> Config:
    return Config.model_validate(current.__dict__)

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

    # TODO: 调用真实 AI 接口 (硅基流动/DeepSeek 等)
    # 暂时返回占位回复
    response_content = generate_fallback_response(request.message)

    save_message("assistant", response_content)

    return ChatResponse(content=response_content)

@app.get("/config", response_model=Config)
async def get_config_endpoint():
    """获取配置"""
    return to_api_config(get_config())

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

# ============== 占位回复生成 ==============

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
