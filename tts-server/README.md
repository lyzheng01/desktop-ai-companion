# TTS Server

## Goal

Provide a small standalone TTS service for Desktop AI Companion.

## Endpoints

- `POST /synthesize`
- static audio files under `/audio/...`

## Start Service

Start the service:

```bash
uvicorn server:app --host 0.0.0.0 --port 9000
```

## Main Backend Integration

Set this on the main backend machine:

```bash
DESKTOP_AI_COMPANION_TTS_SERVER_URL=http://127.0.0.1:9000
```

## Request Example

```json
{
  "text": "今天累的话，就先休息一下吧。",
  "voice": "warm-female",
  "emotion": "concerned",
  "format": "mp3"
}
```

## Response Example

```json
{
  "audio_url": "http://127.0.0.1:9000/audio/<hash>.mp3",
  "duration_ms": null
}
```

## Implementation

This service calls Tencent TTS directly and writes the returned audio to the local `audio/` cache.
