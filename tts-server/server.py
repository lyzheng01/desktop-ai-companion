import hashlib
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tts.v20190823 import models, tts_client


BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = os.getenv("TTS_PUBLIC_BASE_URL", "http://127.0.0.1:9000").rstrip("/")
TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID", "").strip()
TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY", "").strip()
TENCENT_TTS_ENDPOINT = os.getenv("TENCENT_TTS_ENDPOINT", "tts.tencentcloudapi.com").strip()
TENCENT_TTS_REGION = os.getenv("TENCENT_TTS_REGION", "ap-guangzhou").strip()


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "warm-female"
    emotion: str = "calm"
    format: str = "mp3"


class SynthesizeResponse(BaseModel):
    audio_url: str
    duration_ms: Optional[int] = None


VOICE_MAP = {
    "warm-female": 1001,
    "female_1": 1001,
    "cheerful-female": 101001,
    "calm-male": 101004,
    "cute-child": 101016,
}

app = FastAPI(title="Desktop AI Companion TTS Server")
logger = logging.getLogger("desktop-ai-companion-tts")


def build_cache_key(text: str, voice: str, emotion: str, fmt: str) -> str:
    raw = f"{text}\n{voice}\n{emotion}\n{fmt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sanitize_text(text: str) -> str:
    return " ".join(text.strip().split()).replace("\n", " ").replace("\r", " ")


def normalize_tts_text(text: str, max_length: int = 120) -> str:
    sanitized = sanitize_text(text)
    sanitized = re.sub(r"https?://\S+", "这个链接", sanitized)
    sanitized = sanitized.replace("```", " ").replace("`", " ")
    sanitized = re.sub(r"[*_~#>\[\]\(\)\{\}|\\]+", " ", sanitized)
    sanitized = re.sub(r"\b[A-Za-z0-9_]{18,}\b", "这段内容", sanitized)

    allowed = []
    for char in sanitized:
        category = unicodedata.category(char)
        if category.startswith("C"):
            continue
        if category == "So":
            continue
        allowed.append(char)

    sanitized = "".join(allowed)
    sanitized = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9，。！？；：、“”‘’（）《》,.!?:;()\-\s]", " ", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
    return sanitized


def map_tencent_voice(voice: str) -> int:
    return VOICE_MAP.get(voice, VOICE_MAP["warm-female"])


def map_tencent_speed(emotion: str) -> float:
    speed_map = {
        "calm": 0.0,
        "happy": 0.4,
        "shy": -0.1,
        "concerned": -0.2,
        "serious": -0.1,
    }
    return speed_map.get(emotion, 0.0)


def map_tencent_volume(emotion: str) -> float:
    volume_map = {
        "calm": 0.0,
        "happy": 0.2,
        "shy": -0.2,
        "concerned": -0.1,
        "serious": -0.1,
    }
    return volume_map.get(emotion, 0.0)


def request_tencent_tts(text: str, voice: str, emotion: str) -> bytes:
    if not TENCENT_SECRET_ID or not TENCENT_SECRET_KEY:
        raise RuntimeError("Tencent TTS credentials are not configured")

    try:
        cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY)
        client = tts_client.TtsClient(cred, TENCENT_TTS_REGION)
        req = models.TextToVoiceRequest()
        req.Text = text
        req.SessionId = hashlib.md5(f"{text}-{voice}-{emotion}".encode("utf-8")).hexdigest()
        req.ModelType = 1
        req.VoiceType = map_tencent_voice(voice)
        req.Codec = "mp3"
        req.PrimaryLanguage = 1
        req.SampleRate = 16000
        response = client.TextToVoice(req)
        audio_b64 = response.Audio
        if not audio_b64:
            raise RuntimeError("Tencent TTS returned empty audio")
        return __import__("base64").b64decode(audio_b64)
    except TencentCloudSDKException as error:
        raise RuntimeError(f"Tencent TTS error: {error}") from error


async def synthesize_with_tencent(text: str, voice: str, emotion: str, output_path: Path) -> Optional[int]:
    audio_bytes = request_tencent_tts(text, voice, emotion)
    output_path.write_bytes(audio_bytes)
    return None


@app.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(payload: SynthesizeRequest):
    text = sanitize_text(payload.text)
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    normalized_text = normalize_tts_text(text)
    if not normalized_text:
        raise HTTPException(status_code=400, detail="Empty text after normalization")

    fmt = payload.format.lower()
    if fmt not in {"mp3", "wav"}:
        raise HTTPException(status_code=400, detail="Unsupported format")

    cache_key = build_cache_key(text, payload.voice, payload.emotion, fmt)
    file_name = f"{cache_key}.{fmt}"
    output_path = AUDIO_DIR / file_name

    duration_ms = None
    if not output_path.exists():
        try:
            duration_ms = await synthesize_with_tencent(normalized_text, payload.voice, payload.emotion, output_path)
        except Exception as error:
            logger.warning(
                "Primary TTS synthesis failed. original=%r normalized=%r voice=%s emotion=%s error=%s",
                text[:200],
                normalized_text[:200],
                payload.voice,
                payload.emotion,
                error,
            )
            fallback_text = normalize_tts_text(normalized_text[:40])
            if fallback_text and fallback_text != normalized_text:
                fallback_key = build_cache_key(fallback_text, payload.voice, payload.emotion, fmt)
                fallback_name = f"{fallback_key}.{fmt}"
                fallback_output_path = AUDIO_DIR / fallback_name
                if not fallback_output_path.exists():
                    try:
                        duration_ms = await synthesize_with_tencent(
                            fallback_text,
                            payload.voice,
                            payload.emotion,
                            fallback_output_path,
                        )
                    except Exception:
                        logger.exception(
                            "Fallback TTS synthesis failed. fallback=%r voice=%s emotion=%s",
                            fallback_text[:200],
                            payload.voice,
                            payload.emotion,
                        )
                        raise HTTPException(status_code=502, detail=f"TTS synthesis failed: {error}") from error
                output_path = fallback_output_path
                file_name = fallback_name
            else:
                logger.exception(
                    "TTS synthesis failed without fallback. original=%r normalized=%r voice=%s emotion=%s",
                    text[:200],
                    normalized_text[:200],
                    payload.voice,
                    payload.emotion,
                )
                raise HTTPException(status_code=502, detail=f"TTS synthesis failed: {error}") from error

    return SynthesizeResponse(
        audio_url=f"{BASE_URL}/audio/{file_name}",
        duration_ms=duration_ms,
    )


app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
