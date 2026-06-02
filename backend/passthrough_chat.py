from __future__ import annotations

import json
from typing import Iterable, Iterator

import httpx


STREAM_TIMEOUT = 300


def sse_event(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def build_passthrough_messages(
    system_prompt: str,
    context: list[dict],
    message: str,
    search_context_block: str | None = None,
) -> list[dict]:
    system_content = system_prompt or ""
    if search_context_block:
        system_content = f"{system_content}\n\n{search_context_block}".strip()

    return [
        {"role": "system", "content": system_content},
        *[
            {"role": item["role"], "content": item["content"]}
            for item in context
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


def iter_upstream_deltas(response: httpx.Response) -> Iterator[str]:
    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data:
            continue
        if data == "[DONE]":
            break
        payload = json.loads(data)
        delta = extract_stream_delta(payload)
        if delta:
            yield delta


def iter_passthrough_events(deltas: Iterable[str]) -> Iterator[str]:
    yielded_any = False
    yield sse_event("state", "thinking")
    yield sse_event("phase", "composing")
    for delta in deltas:
        yielded_any = True
        yield sse_event("assistant_delta", delta)
    if not yielded_any:
        raise ValueError("No streamed chat response received")
    yield sse_event("done", "done")


def iter_passthrough_live_events(deltas: Iterable[str]) -> Iterator[str]:
    yielded_any = False
    yield sse_event("state", "thinking")
    yield sse_event("phase", "searching")
    for delta in deltas:
        if not yielded_any:
            yield sse_event("phase", "composing")
            yielded_any = True
        yield sse_event("assistant_delta", delta)
    if not yielded_any:
        raise ValueError("No streamed live response received")
    yield sse_event("done", "done")


def iter_passthrough_stream(
    *,
    system_prompt: str,
    context: list[dict],
    message: str,
    search_context_block: str | None = None,
    api_key: str,
    base_url: str,
    model: str,
    timeout: int = STREAM_TIMEOUT,
) -> Iterator[str]:
    yield sse_event("state", "thinking")
    yield sse_event("phase", "composing")

    payload = {
        "model": model,
        "messages": build_passthrough_messages(
            system_prompt,
            context,
            message,
            search_context_block=search_context_block,
        ),
        "temperature": 0.8,
        "stream": True,
    }
    with httpx.stream(
        "POST",
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        yielded_any = False
        for delta in iter_upstream_deltas(response):
            yielded_any = True
            yield sse_event("assistant_delta", delta)
        if not yielded_any:
            raise ValueError("No streamed chat response received")
        yield sse_event("done", "done")


def iter_passthrough_live_stream(
    *,
    system_prompt: str,
    context: list[dict],
    message: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout: int = STREAM_TIMEOUT,
) -> Iterator[str]:
    payload = {
        "model": model,
        "input": build_passthrough_messages(system_prompt, context, message),
        "tools": [{"type": "web_search_preview"}],
        "stream": True,
    }
    with httpx.stream(
        "POST",
        f"{base_url}/responses",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        yield from iter_passthrough_live_events(iter_upstream_deltas(response))
