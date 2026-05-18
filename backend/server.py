"""
Desktop AI Companion - Python 后端服务
提供 AI 对话接口和数据库访问
"""
import os
import re
import shutil
import sys
import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from typing import List
import uvicorn

from app.config import (
    AppConfig,
    TIME_PATTERN,
    get_config,
    get_data_dir,
    get_imported_models_dir,
    get_imported_preview_dir,
    save_config as persist_config,
    set_data_dir,
)
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
    update_companion,
)

MODEL_CATALOG = [
    {
        "key": "kei",
        "name": "Kei",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "kei_en" / "kei_basic_free",
        "preview_path": "/model-previews/builtin/kei.png",
        "builtin": False,
    },
    {
        "key": "chitose",
        "name": "Chitose",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "chitose",
        "preview_path": "/model-previews/builtin/chitose.png",
        "builtin": False,
    },
    {
        "key": "hiyori",
        "name": "Hiyori",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "hiyori",
        "preview_path": "/model-previews/builtin/hiyori.png",
        "builtin": False,
    },
    {
        "key": "shizuku",
        "name": "Shizuku",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "shizuku",
        "preview_path": "/model-previews/builtin/shizuku.png",
        "builtin": False,
    },
    {
        "key": "hiyori_pro_zh",
        "name": "Hiyori CN",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "hiyori_pro_zh" / "runtime",
        "preview_path": "/model-previews/builtin/hiyori_pro_zh.png",
        "builtin": True,
    },
    {
        "key": "mao_pro_zh",
        "name": "Mao",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "mao_pro_zh" / "runtime",
        "preview_path": "/model-previews/builtin/mao_pro_zh.png",
        "builtin": True,
    },
    {
        "key": "miara_pro_en",
        "name": "Miara",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "miara_pro_en" / "runtime",
        "preview_path": "/model-previews/builtin/miara_pro_en.png",
        "builtin": False,
    },
    {
        "key": "miku_pro_jp",
        "name": "Miku",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "miku_pro_jp" / "runtime",
        "preview_path": "/model-previews/builtin/miku_pro_jp.png",
        "builtin": False,
    },
    {
        "key": "natori_pro_zh",
        "name": "Natori",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "natori_pro_zh" / "runtime",
        "preview_path": "/model-previews/builtin/natori_pro_zh.png",
        "builtin": False,
    },
    {
        "key": "catalog-chino11",
        "name": "Chino11",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "chino11---chino11-model3---3",
        "preview_path": "/model-previews/builtin/7.png",
        "builtin": False,
    },
    {
        "key": "catalog-epsilon",
        "name": "Epsilon",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "epsilon---epsilon-model3---1",
        "preview_path": "/model-previews/builtin/8.png",
        "builtin": False,
    },
    {
        "key": "catalog-haru-greeter",
        "name": "Haru Greeter",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "haru-greeter-pro-jp---haru-greeter-t05-model3---1",
        "preview_path": "/model-previews/builtin/10.png",
        "builtin": False,
    },
    {
        "key": "catalog-izumi",
        "name": "Izumi",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "izumi---izumi-illust-model3---1",
        "preview_path": "/model-previews/builtin/11.png",
        "builtin": False,
    },
    {
        "key": "catalog-kitu17",
        "name": "KITU17",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "kitu17---kitu17-model3---1",
        "preview_path": "/model-previews/builtin/12.png",
        "builtin": False,
    },
    {
        "key": "catalog-neko",
        "name": "Neko",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "neko---neko--1-0-model3---1",
        "preview_path": "/model-previews/builtin/13.png",
        "builtin": False,
    },
    {
        "key": "catalog-nicole",
        "name": "Nicole",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "nicole---nicole-model3---1",
        "preview_path": "/model-previews/builtin/14.png",
        "builtin": False,
    },
    {
        "key": "catalog-raiga",
        "name": "Raiga",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "raiga-free---raiga-model3---1",
        "preview_path": "/model-previews/builtin/15.png",
        "builtin": False,
    },
    {
        "key": "catalog-toki",
        "name": "Toki",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "toki20220227---20220227toki-model3---1",
        "preview_path": "/model-previews/builtin/17.png",
        "builtin": False,
    },
    {
        "key": "catalog-hijiki",
        "name": "Hijiki",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "tororo-hijiki---hijiki-model3---1",
        "preview_path": "/model-previews/builtin/18.png",
        "builtin": False,
    },
    {
        "key": "catalog-tororo",
        "name": "Tororo",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "tororo-hijiki---tororo-model3---2",
        "preview_path": "/model-previews/builtin/19.png",
        "builtin": False,
    },
    {
        "key": "catalog-wanderer",
        "name": "Wanderer",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "散兵-流浪者免费模型---散兵-model3---1",
        "preview_path": "/model-previews/builtin/4.png",
        "builtin": False,
    },
    {
        "key": "catalog-changli",
        "name": "Changli",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "长离带水印---长离-model3---1",
        "preview_path": "/model-previews/builtin/22.png",
        "builtin": False,
    },
    {
        "key": "catalog-witch",
        "name": "Witch",
        "source_dir": PROJECT_ROOT / "assets" / "live2d" / "imported" / "魔女---魔女-model3---1",
        "preview_path": "/model-previews/builtin/23.png",
        "builtin": False,
    },
]

BUILTIN_MODEL_KEYS = {item["key"] for item in MODEL_CATALOG if item["builtin"]}

def get_model_catalog_item(model_key: str) -> dict | None:
    for item in MODEL_CATALOG:
        if item["key"] == model_key:
            return item
    return None


def _resolve_catalog_manifest_path(item: dict) -> tuple[Path, str]:
    source_manifest = _resolve_model_manifest(item["source_dir"])
    relative_manifest = source_manifest.relative_to(item["source_dir"]).as_posix()
    return source_manifest, relative_manifest


def _expected_catalog_public_model_path(item: dict) -> str:
    _, relative_manifest = _resolve_catalog_manifest_path(item)
    slug = item["key"]
    return f"/live2d/imported/{slug}/{relative_manifest}"

def model_to_response(item: dict) -> dict:
    expected_public_path = _expected_catalog_public_model_path(item) if not item["builtin"] else None
    return {
        "key": item["key"],
        "name": item["name"],
        "preview_path": item["preview_path"],
        "builtin": item["builtin"],
        "installed": item["key"] in BUILTIN_MODEL_KEYS or any(
            model["model_path"] == expected_public_path for model in list_imported_models()
        ),
    }

# ============== 数据模型 ==============

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    context: List[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    content: str


class ProactiveMessageResponse(BaseModel):
    trigger: str | None = None
    content: str


class DataDirResponse(BaseModel):
    data_dir: str


class DataDirUpdateRequest(BaseModel):
    data_dir: str
    migrate_existing: bool = True


def migrate_data_dir_contents(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if not source.exists() or source.resolve() == target.resolve():
        return

    for entry in source.iterdir():
        destination = target / entry.name
        if entry.is_dir():
            shutil.copytree(entry, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, destination)


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


class CatalogModelInstallRequest(BaseModel):
    model_key: str

class Config(BaseModel):
    user_nickname: str = "小伙伴"
    user_display_name: str = "你"
    character_type: str = "mao_pro_zh"
    character_name: str = "Mao"
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


def needs_live_search(message: str) -> bool:
    domain_tokens = [
        "天气", "气温", "温度", "下雨", "降雨", "新闻", "汇率", "几号", "多少号", "星期", "周几", "几点", "时间", "日期", "几月几号", "几月几日",
    ]
    freshness_tokens = ["今天", "现在", "最新", "实时", "目前"]

    has_domain = any(token in message for token in domain_tokens)
    has_freshness = any(token in message for token in freshness_tokens)
    return has_domain and has_freshness


def search_web(query: str) -> str:
    normalized = query.strip()

    if is_datetime_query(normalized):
        return get_current_datetime_context(normalized)
    if is_weather_query(normalized):
        return search_weather(normalized)
    if is_exchange_rate_query(normalized):
        return search_exchange_rate(normalized)
    if is_news_query(normalized):
        return search_news(normalized)
    return search_general_web(normalized)


def build_search_context_block(query: str, search_result: str) -> str:
    return f"外部检索结果（{query}）：\n{search_result.strip()}"


def is_weather_query(message: str) -> bool:
    return any(token in message for token in ["天气", "气温", "温度", "下雨", "降雨"])


def is_datetime_query(message: str) -> bool:
    return any(
        token in message
        for token in [
            "今天几号",
            "今天多少号",
            "今天几月几号",
            "今天几月几日",
            "今天星期",
            "今天周几",
            "现在几点",
            "现在时间",
            "今天日期",
            "日期",
            "时间",
        ]
    )


def is_exchange_rate_query(message: str) -> bool:
    return "汇率" in message


def is_news_query(message: str) -> bool:
    return any(token in message for token in ["新闻", "头条", "最新消息"])


def extract_weather_location(query: str) -> str:
    city_match = re.search(r"([\u4e00-\u9fa5]{2,10}?)(?:今天|现在|最近)?(?:天气|气温|温度|会下雨)", query)
    if city_match:
        return city_match.group(1)

    location_match = re.search(r"(?:在|去|到)([\u4e00-\u9fa5]{2,10})", query)
    if location_match:
        return location_match.group(1)

    return "合肥"


def search_weather(query: str) -> str:
    location = extract_weather_location(query)
    latitude, longitude, resolved_name = geocode_location(location)
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Shanghai",
            "forecast_days": 1,
        },
        headers={"User-Agent": "desktop-ai-companion/0.1"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    current = data.get("current", {})
    daily = data.get("daily", {})
    desc = describe_weather_code(current.get("weather_code"))
    temp_c = current.get("temperature_2m", "?")
    feels_like = current.get("apparent_temperature", "?")
    humidity = current.get("relative_humidity_2m", "?")
    max_values = daily.get("temperature_2m_max") or ["?"]
    min_values = daily.get("temperature_2m_min") or ["?"]
    dates = daily.get("time") or [datetime.now().strftime("%Y-%m-%d")]
    max_temp = max_values[0]
    min_temp = min_values[0]
    date = dates[0]
    return (
        f"{resolved_name} {date}天气：{desc}。"
        f"当前温度 {temp_c}°C，体感 {feels_like}°C，湿度 {humidity}%。"
        f"今天最高 {max_temp}°C，最低 {min_temp}°C。"
    )


def geocode_location(location: str) -> tuple[float, float, str]:
    response = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "zh", "format": "json"},
        headers={"User-Agent": "desktop-ai-companion/0.1"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    if not results:
        raise ValueError(f"Could not geocode location: {location}")

    top = results[0]
    return float(top["latitude"]), float(top["longitude"]), top.get("name") or location


def describe_weather_code(code: int | None) -> str:
    mapping = {
        0: "晴天",
        1: "大致晴朗",
        2: "局部多云",
        3: "阴天",
        45: "有雾",
        48: "雾凇",
        51: "小毛毛雨",
        53: "毛毛雨",
        55: "较强毛毛雨",
        61: "小雨",
        63: "中雨",
        65: "大雨",
        71: "小雪",
        73: "中雪",
        75: "大雪",
        80: "阵雨",
        81: "较强阵雨",
        82: "强阵雨",
        95: "雷暴",
    }
    return mapping.get(code, "未知")


def get_current_datetime_context(query: str) -> str:
    now = datetime.now()
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_names[now.weekday()]

    if any(token in query for token in ["几点", "时间"]):
        return f"当前本地时间：{now.strftime('%Y-%m-%d %H:%M')}，{weekday}。"
    if any(token in query for token in ["星期", "周几"]):
        return f"今天是 {now.strftime('%Y年%m月%d日')}，{weekday}。"
    return f"今天的日期是 {now.strftime('%Y年%m月%d日')}，{weekday}。"


def build_proactive_weather_line(location: str = "合肥") -> str:
    latitude, longitude, resolved_name = geocode_location(location)
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Shanghai",
            "forecast_days": 1,
        },
        headers={"User-Agent": "desktop-ai-companion/0.1"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    current = data.get("current", {})
    daily = data.get("daily", {})
    weather_code = current.get("weather_code")
    desc = describe_weather_code(weather_code)
    temp_c = float(current.get("temperature_2m", 0) or 0)
    max_temp = float((daily.get("temperature_2m_max") or [0])[0] or 0)
    min_temp = float((daily.get("temperature_2m_min") or [0])[0] or 0)

    rainy_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95}
    if weather_code in rainy_codes:
        return f"{resolved_name}今天{desc}，出门可能会淋到雨，记得带伞。"
    if max_temp >= 30 or temp_c >= 29:
        return f"{resolved_name}今天{desc}，气温偏高，出门记得补水，别晒太久。"
    if min_temp <= 12 or temp_c <= 10:
        return f"{resolved_name}今天{desc}，会有点凉，出门记得多穿一件。"
    return f"{resolved_name}今天{desc}，现在大约{temp_c:.1f}°C，白天大概 {min_temp:.1f}°C 到 {max_temp:.1f}°C。"


def build_care_followup_line() -> str | None:
    discomfort_tokens = ["不舒服", "难受", "头疼", "胃疼", "感冒", "发烧", "恶心", "疼", "不太舒服"]
    yesterday = datetime.now().date().fromordinal(datetime.now().date().toordinal() - 1)
    for item in reversed(get_messages(limit=200)):
        if item.get("role") != "user":
            continue
        timestamp = item.get("timestamp")
        if not timestamp:
            continue
        try:
            message_day = datetime.fromisoformat(str(timestamp)).date()
        except ValueError:
            try:
                message_day = datetime.strptime(str(timestamp), "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                continue
        if message_day != yesterday:
            continue
        content = str(item.get("content") or "")
        if any(token in content for token in discomfort_tokens):
            return "昨天你好像有点不舒服，今天好一点了吗？"
    return None


def detect_base_currency(query: str) -> str:
    mapping = {
        "美元": "USD",
        "美金": "USD",
        "欧元": "EUR",
        "英镑": "GBP",
        "日元": "JPY",
        "港币": "HKD",
    }
    for token, code in mapping.items():
        if token in query:
            return code
    return "USD"


def search_exchange_rate(query: str) -> str:
    base = detect_base_currency(query)
    response = httpx.get(
        f"https://open.er-api.com/v6/latest/{base}",
        headers={"User-Agent": "desktop-ai-companion/0.1"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    cny_rate = data.get("rates", {}).get("CNY")
    if cny_rate is None:
        raise ValueError("CNY rate missing from exchange response")

    updated_at = data.get("time_last_update_utc", "")
    return f"最新汇率参考：1 {base} 约等于 {cny_rate:.4f} CNY。更新时间：{updated_at}。"


def search_news(query: str) -> str:
    response = httpx.get(
        "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        headers={"User-Agent": "desktop-ai-companion/0.1"},
        timeout=10,
    )
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    items = root.findall("./channel/item")[:3]
    headlines = []
    for item in items:
        title = (item.findtext("title") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if not title:
            continue
        if pub_date:
            try:
                parsed = parsedate_to_datetime(pub_date)
                headlines.append(f"- {title}（{parsed.strftime('%m-%d %H:%M')}）")
                continue
            except Exception:
                pass
        headlines.append(f"- {title}")

    if not headlines:
        raise ValueError("No news headlines found")
    return "最新新闻摘要：\n" + "\n".join(headlines)


def search_general_web(query: str) -> str:
    response = httpx.get(
        "https://api.duckduckgo.com/",
        params={
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        },
        headers={"User-Agent": "desktop-ai-companion/0.1"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        heading = (data.get("Heading") or query).strip()
        return f"{heading}：{abstract}"

    related = data.get("RelatedTopics") or []
    for item in related:
        text = (item.get("Text") or "").strip() if isinstance(item, dict) else ""
        if text:
            return text
        for nested in item.get("Topics", []) if isinstance(item, dict) else []:
            nested_text = (nested.get("Text") or "").strip()
            if nested_text:
                return nested_text

    raise ValueError("No general search summary found")


def sse_event(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def iter_stream_chunks(parts: list[str]):
    yield sse_event("state", "thinking")
    for part in parts:
        yield sse_event("assistant_delta", part)
    yield sse_event("done", "done")


def split_reply_for_stream(reply: str) -> list[str]:
    text = reply.strip()
    if not text:
        return []

    for separator in ["。", "！", "？", "\n"]:
        index = text.find(separator)
        if index != -1 and index + 1 < len(text):
            first = text[: index + 1]
            rest = text[index + 1 :].lstrip()
            return [first, rest] if rest else [first]

    midpoint = max(1, len(text) // 2)
    return [text[:midpoint], text[midpoint:]]


def iter_stream_reply(reply: str, phase: str = "composing"):
    yield sse_event("state", "thinking")
    yield sse_event("phase", phase)
    for part in split_reply_for_stream(reply):
        if part:
            yield sse_event("assistant_delta", part)
    yield sse_event("done", "done")


def build_assistant_reply(
    message: str,
    context: list[ChatMessage],
    config: AppConfig,
    search_context_block: str | None = None,
) -> str:
    return shape_companion_reply(
        message,
        generate_chat_response(message, context, config, search_context_block=search_context_block),
        config,
    )


def build_live_tool_reply(message: str, tool_result: str, config: AppConfig) -> str:
    cleaned = tool_result.strip()

    if is_datetime_query(message):
        return shape_companion_reply(message, cleaned, config)

    if is_weather_query(message):
        return shape_companion_reply(message, cleaned, config)

    if is_exchange_rate_query(message):
        return shape_companion_reply(message, cleaned, config)

    if is_news_query(message):
        return shape_companion_reply(message, cleaned, config)

    search_context_block = build_search_context_block(message, cleaned)
    return build_assistant_reply(message, [], config, search_context_block=search_context_block)


def build_companion_system_prompt(config: AppConfig, memory_block: str) -> str:
    companion_name = config.character_name.strip() or "小艾"
    user_name = config.user_display_name.strip() or config.user_nickname.strip() or "你"
    personality = "、".join(config.personality[:4]) if config.personality else "温柔"
    return (
        f"你是一个住在桌面上的 AI 小伙伴，你的名字是{companion_name}。"
        f"你正在陪伴的用户叫{user_name}。"
        f"你的说话气质偏{personality}。"
        "回复简短、温柔、有一点陪伴感，不要像客服，不要长篇大论。"
        f"当用户问你叫什么、你的名字、你是谁时，要明确回答你叫{companion_name}。"
        "不要说自己没有名字。"
        "\n你已知的用户信息：\n"
        f"{memory_block or '- 暂无额外记忆'}"
    )


def build_memory_prompt_block() -> str:
    preference = get_memories(scope="preference")
    short_term = get_memories(scope="short_term")
    long_term = get_memories(scope="long_term")
    return build_memory_block(preference, short_term, long_term)


def build_chat_messages(config: AppConfig, message: str, context: list[ChatMessage], search_context_block: str | None = None) -> list[dict]:
    memory_block = build_memory_prompt_block()
    return [
        {
            "role": "system",
            "content": build_companion_system_prompt(config, memory_block)
            + (f"\n\n{search_context_block}" if search_context_block else ""),
        },
        *[
            {"role": item.role, "content": item.content}
            for item in context[-8:]
        ],
        {"role": "user", "content": message},
    ]


def extract_stream_delta(payload: dict) -> str:
    payload_type = payload.get("type")
    if payload_type == "response.output_text.delta":
        return str(payload.get("delta") or "")

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

    return ""


def iter_upstream_sse_lines(response: httpx.Response):
    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        delta = extract_stream_delta(payload)
        if delta:
            yield delta


def generate_native_live_response(message: str, context: list[ChatMessage], config: AppConfig) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.hanbbq.top/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()

    if not api_key:
        return None

    input_items = build_chat_messages(config, message, context)

    payload = {
        "model": model,
        "input": input_items,
        "tools": [{"type": "web_search_preview"}],
    }

    try:
        response = httpx.post(
            f"{base_url}/responses",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        output_text = (data.get("output_text") or "").strip()
        if output_text:
            return shape_companion_reply(message, output_text, config)
    except Exception:
        return None

    return None


def iter_native_live_response_stream(message: str, context: list[ChatMessage], config: AppConfig):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.hanbbq.top/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()

    if not api_key:
        return

    payload = {
        "model": model,
        "input": build_chat_messages(config, message, context),
        "tools": [{"type": "web_search_preview"}],
        "stream": True,
    }

    with httpx.stream(
        "POST",
        f"{base_url}/responses",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=60,
    ) as response:
        response.raise_for_status()
        yield from iter_upstream_sse_lines(response)


def iter_chat_response_stream(message: str, context: list[ChatMessage], config: AppConfig, search_context_block: str | None = None):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.hanbbq.top/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()

    if not api_key:
        return

    payload = {
        "model": model,
        "messages": build_chat_messages(config, message, context, search_context_block=search_context_block),
        "temperature": 0.8,
        "stream": True,
    }

    with httpx.stream(
        "POST",
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=60,
    ) as response:
        response.raise_for_status()
        yield from iter_upstream_sse_lines(response)


def resolve_live_response(message: str, context: list[ChatMessage], config: AppConfig) -> str:
    native_live_response = generate_native_live_response(message, context, config)
    if native_live_response:
        return native_live_response

    search_result = search_web(message)
    return build_live_tool_reply(message, search_result, config)


def stream_native_live_response(message: str, context: list[ChatMessage], config: AppConfig):
    collected: list[str] = []
    yielded_any = False
    yield sse_event("state", "thinking")
    yield sse_event("phase", "searching")

    for delta in iter_native_live_response_stream(message, context, config) or []:
        if not yielded_any:
            yield sse_event("phase", "composing")
            yielded_any = True
        collected.append(delta)
        yield sse_event("assistant_delta", delta)

    final_text = "".join(collected).strip()
    if not final_text:
        raise ValueError("No streamed live response received")

    final_reply = shape_companion_reply(message, final_text, config)
    save_message("assistant", final_reply)
    yield sse_event("done", "done")


def stream_chat_response(message: str, context: list[ChatMessage], config: AppConfig):
    collected: list[str] = []
    yielded_any = False
    yield sse_event("state", "thinking")
    yield sse_event("phase", "composing")

    for delta in iter_chat_response_stream(message, context, config) or []:
        yielded_any = True
        collected.append(delta)
        yield sse_event("assistant_delta", delta)

    final_text = "".join(collected).strip()
    if not yielded_any or not final_text:
        raise ValueError("No streamed chat response received")

    final_reply = shape_companion_reply(message, final_text, config)
    save_message("assistant", final_reply)
    yield sse_event("done", "done")


def safe_stream_chat_response(message: str, context: list[ChatMessage], config: AppConfig):
    try:
        yield from stream_chat_response(message, context, config)
        return
    except Exception:
        response_content = build_assistant_reply(message, context, config)
        save_message("assistant", response_content)
        yield sse_event("assistant_delta", response_content)
        yield sse_event("done", "done")


def safe_stream_native_live_response(message: str, context: list[ChatMessage], config: AppConfig):
    try:
        yield from stream_native_live_response(message, context, config)
        return
    except Exception:
        try:
            response_content = resolve_live_response(message, context, config)
        except Exception:
            response_content = "抱歉，我暂时没能查到最新信息，所以现在不想乱说。你可以稍后再让我查一次。"

        save_message("assistant", response_content)
        yield sse_event("phase", "searching")
        yield sse_event("assistant_delta", response_content)
        yield sse_event("done", "done")

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

BUILTIN_LIVE2D_DIR = PROJECT_ROOT / "assets" / "public" / "live2d"
BUILTIN_PREVIEW_DIR = PROJECT_ROOT / "assets" / "public" / "model-previews" / "builtin"

app.mount("/live2d/imported", StaticFiles(directory=get_imported_models_dir()), name="imported-live2d")
app.mount("/model-previews/imported", StaticFiles(directory=get_imported_preview_dir()), name="imported-previews")
app.mount("/live2d", StaticFiles(directory=BUILTIN_LIVE2D_DIR), name="builtin-live2d")
app.mount("/model-previews/builtin", StaticFiles(directory=BUILTIN_PREVIEW_DIR), name="builtin-previews")

# ============== API 端点 ==============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/proactive/weather", response_model=ProactiveMessageResponse)
async def proactive_weather(location: str = "合肥"):
    return ProactiveMessageResponse(trigger="weather_update", content=build_proactive_weather_line(location))


@app.get("/proactive/followup", response_model=ProactiveMessageResponse)
async def proactive_followup():
    line = build_care_followup_line()
    return ProactiveMessageResponse(trigger="care_followup", content=line or "")


@app.get("/data-dir", response_model=DataDirResponse)
async def get_data_dir_endpoint():
    return DataDirResponse(data_dir=str(get_data_dir()))


@app.post("/data-dir", response_model=DataDirResponse)
async def set_data_dir_endpoint(payload: DataDirUpdateRequest):
    data_dir = payload.data_dir.strip()
    if not data_dir:
        raise HTTPException(status_code=400, detail="data_dir is required")

    source_dir = get_data_dir()
    target_dir = Path(data_dir).expanduser().resolve()
    if payload.migrate_existing:
        migrate_data_dir_contents(source_dir, target_dir)

    resolved = set_data_dir(target_dir, persist_bootstrap=True)
    return DataDirResponse(data_dir=str(resolved))

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

    if needs_live_search(request.message):
        try:
            response_content = resolve_live_response(request.message, request.context, current)
            save_message("assistant", response_content)
            return ChatResponse(content=response_content)
        except Exception:
            response_content = "抱歉，我暂时没能查到最新信息，所以现在不想乱说。你可以稍后再让我查一次。"
            save_message("assistant", response_content)
            return ChatResponse(content=response_content)

    response_content = build_assistant_reply(request.message, request.context, current)

    save_message("assistant", response_content)

    return ChatResponse(content=response_content)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    save_message("user", request.message)

    candidates = extract_memory_candidates(request.message)
    persist_memory_candidates(candidates)

    current = apply_active_companion(get_config())
    if needs_live_search(request.message):
        return StreamingResponse(
            safe_stream_native_live_response(request.message, request.context, current),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        safe_stream_chat_response(request.message, request.context, current),
        media_type="text/event-stream",
    )

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


@app.get("/models/catalog")
async def get_model_catalog_endpoint():
    return [model_to_response(item) for item in MODEL_CATALOG if not item["builtin"]]


def _resolve_model_manifest(source_dir: Path) -> Path:
    candidates = sorted(source_dir.glob("**/*.model3.json"))
    if not candidates:
        raise HTTPException(status_code=404, detail="Model manifest not found")
    return candidates[0]


def _install_catalog_model(item: dict) -> dict:
    source_dir = item["source_dir"]
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="Source model directory not found")

    source_manifest, relative_manifest = _resolve_catalog_manifest_path(item)
    slug = item["key"]
    target_root = get_imported_models_dir() / slug
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_dir, target_root)

    public_model_path = f"/live2d/imported/{slug}/{relative_manifest}"
    model_id = create_imported_model(item["name"], public_model_path, source="catalog")
    return {"status": "ok", "id": model_id, "model_path": public_model_path, "key": item["key"]}


@app.post("/models/catalog/install")
async def install_catalog_model_endpoint(payload: CatalogModelInstallRequest):
    item = get_model_catalog_item(payload.model_key)
    if item is None or item["builtin"]:
        raise HTTPException(status_code=404, detail="Catalog model not found")
    return _install_catalog_model(item)


@app.post("/models/imported")
async def import_model(payload: ImportedModelRequest):
    source_model = Path(payload.model_path).expanduser()
    if not source_model.exists() or not source_model.name.endswith('.model3.json'):
        raise HTTPException(status_code=400, detail="Invalid model3.json path")

    source_dir = source_model.parent
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in payload.name).strip('-') or 'imported-model'
    target_root = get_imported_models_dir() / slug
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
    updates = config.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        setattr(current, field, value)

    active_companion = get_active_companion()
    if active_companion is not None:
        update_companion(
            active_companion["id"],
            name=updates.get("character_name"),
            character_type=updates.get("character_type"),
            personality_tags=updates.get("personality"),
            interaction_mode=updates.get("interaction_mode"),
        )

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


def generate_chat_response(
    message: str,
    context: list[ChatMessage],
    config: AppConfig,
    search_context_block: str | None = None,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.hanbbq.top/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()

    if not api_key:
        return generate_fallback_response(message)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": build_companion_system_prompt(config, build_memory_prompt_block())
                + (f"\n\n{search_context_block}" if search_context_block else ""),
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
