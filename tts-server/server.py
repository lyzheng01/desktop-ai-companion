import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


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
    "warm-female": 101001,
    "cheerful-female": 101002,
    "calm-male": 101003,
    "cute-child": 101004,
}

EMOTION_MAP = {
    "calm": "default",
    "happy": "default",
    "shy": "default",
    "concerned": "default",
    "serious": "default",
}

app = FastAPI(title="Desktop AI Companion TTS Server")


def build_cache_key(text: str, voice: str, emotion: str, fmt: str) -> str:
    raw = f"{text}\n{voice}\n{emotion}\n{fmt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sanitize_text(text: str) -> str:
    return " ".join(text.strip().split())


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


def map_tencent_emotion_style(emotion: str) -> str:
    return EMOTION_MAP.get(emotion, "default")


def sign_tc3(secret_key: str, date: str, service: str, string_to_sign: str) -> str:
    def _hmac(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    secret_date = _hmac(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac(secret_date, service)
    secret_signing = _hmac(secret_service, "tc3_request")
    return hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()


async def request_tencent_tts(text: str, voice: str, emotion: str) -> bytes:
    if not TENCENT_SECRET_ID or not TENCENT_SECRET_KEY:
        raise RuntimeError("Tencent TTS credentials are not configured")

    service = "tts"
    host = TENCENT_TTS_ENDPOINT
    endpoint = f"https://{host}"
    action = "TextToVoice"
    version = "2019-08-23"
    region = TENCENT_TTS_REGION
    timestamp = int(time.time())
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

    payload = {
        "Text": text,
        "SessionId": hashlib.md5(f"{text}-{timestamp}".encode("utf-8")).hexdigest(),
        "ModelType": 1,
        "VoiceType": map_tencent_voice(voice),
        "Codec": "mp3",
        "PrimaryLanguage": 1,
        "SampleRate": 16000,
        "Volume": map_tencent_volume(emotion),
        "Speed": map_tencent_speed(emotion),
        "EmotionCategory": map_tencent_emotion_style(emotion),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    http_request_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    canonical_headers = (
        f"content-type:application/json; charset=utf-8\n"
        f"host:{host}\n"
        f"x-tc-action:{action.lower()}\n"
    )
    signed_headers = "content-type;host;x-tc-action"
    hashed_request_payload = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    canonical_request = (
        f"{http_request_method}\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{hashed_request_payload}"
    )

    algorithm = "TC3-HMAC-SHA256"
    credential_scope = f"{date}/{service}/tc3_request"
    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = (
        f"{algorithm}\n"
        f"{timestamp}\n"
        f"{credential_scope}\n"
        f"{hashed_canonical_request}"
    )

    signature = sign_tc3(TENCENT_SECRET_KEY, date, service, string_to_sign)
    authorization = (
        f"{algorithm} "
        f"Credential={TENCENT_SECRET_ID}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": version,
        "X-TC-Region": region,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(endpoint, headers=headers, content=payload_json.encode("utf-8"))

    response.raise_for_status()
    data = response.json()
    if "Response" not in data:
        raise RuntimeError("Invalid Tencent TTS response")

    result = data["Response"]
    if "Error" in result:
        raise RuntimeError(f"Tencent TTS error: {result['Error']}")

    audio_b64 = result.get("Audio")
    if not audio_b64:
        raise RuntimeError("Tencent TTS returned empty audio")

    return base64.b64decode(audio_b64)


async def synthesize_with_tencent(text: str, voice: str, emotion: str, output_path: Path) -> Optional[int]:
    sample = BASE_DIR / "sample.mp3"
    if sample.exists():
        output_path.write_bytes(sample.read_bytes())
        return None

    audio_bytes = await request_tencent_tts(text, voice, emotion)
    output_path.write_bytes(audio_bytes)
    return None


@app.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(payload: SynthesizeRequest):
    text = sanitize_text(payload.text)
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    fmt = payload.format.lower()
    if fmt not in {"mp3", "wav"}:
        raise HTTPException(status_code=400, detail="Unsupported format")

    cache_key = build_cache_key(text, payload.voice, payload.emotion, fmt)
    file_name = f"{cache_key}.{fmt}"
    output_path = AUDIO_DIR / file_name

    duration_ms = None
    if not output_path.exists():
        try:
            duration_ms = await synthesize_with_tencent(text, payload.voice, payload.emotion, output_path)
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"TTS synthesis failed: {error}") from error

    return SynthesizeResponse(
        audio_url=f"{BASE_URL}/audio/{file_name}",
        duration_ms=duration_ms,
    )


app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
