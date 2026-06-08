import httpx
from fastapi.testclient import TestClient

import backend.server as server_module
from backend.server import app


client = TestClient(app)


def test_build_passthrough_messages_keeps_frontend_prompt_and_context():
    from backend.passthrough_chat import build_passthrough_messages

    messages = build_passthrough_messages(
        system_prompt="frontend prompt",
        context=[
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
        ],
        message="u2",
    )

    assert messages == [
        {"role": "system", "content": "frontend prompt"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]


def test_iter_passthrough_events_emits_state_delta_and_done():
    from backend.passthrough_chat import iter_passthrough_events

    chunks = list(iter_passthrough_events(["\u4f60", "\u597d"]))
    joined = "\n".join(chunks)

    assert "event: state" in joined
    assert "event: phase" in joined
    assert joined.count("event: assistant_delta") == 2
    assert "event: done" in joined


def test_iter_passthrough_stream_emits_state_before_opening_upstream(monkeypatch):
    from backend.passthrough_chat import iter_passthrough_stream

    opened = False

    class DummyResponse:
        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"hello"}}]}'
            yield "data: [DONE]"

    class DummyStream:
        def __enter__(self):
            nonlocal opened
            opened = True
            return DummyResponse()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("backend.passthrough_chat.httpx.stream", lambda *args, **kwargs: DummyStream())

    iterator = iter_passthrough_stream(
        system_prompt="frontend prompt",
        context=[],
        message="hello",
        api_key="key",
        base_url="http://example.test/v1",
        model="demo-model",
    )

    assert next(iterator) == "event: state\ndata: thinking\n\n"
    assert opened is False
    assert next(iterator) == "event: phase\ndata: composing\n\n"
    assert opened is False


def test_iter_upstream_deltas_stops_consuming_after_done_marker():
    from backend.passthrough_chat import iter_upstream_deltas

    class DummyResponse:
        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"hello"}}]}'
            yield "data: [DONE]"
            raise AssertionError("iterator should stop after [DONE]")

    assert list(iter_upstream_deltas(DummyResponse())) == ["hello"]


def test_iter_passthrough_live_stream_returns_visible_error_when_upstream_lacks_responses_api(monkeypatch):
    from backend.passthrough_chat import iter_passthrough_live_stream

    class DummyResponse:
        def raise_for_status(self):
            request = httpx.Request("POST", "https://example.test/v1/responses")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("not found", request=request, response=response)

        def iter_lines(self):
            yield "data: [DONE]"

    class DummyStream:
        def __enter__(self):
            return DummyResponse()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("backend.passthrough_chat.httpx.stream", lambda *args, **kwargs: DummyStream())

    chunks = list(
        iter_passthrough_live_stream(
            system_prompt="frontend prompt",
            context=[],
            message="\u4eca\u5929\u7f8e\u56fd\u6709\u4ec0\u4e48\u65b0\u95fb",
            api_key="key",
            base_url="https://example.test/v1",
            model="demo-model",
        )
    )
    joined = "\n".join(chunks)

    assert "event: phase\ndata: searching" in joined
    assert "event: phase\ndata: composing" in joined
    assert "\u4e0d\u652f\u6301\u8054\u7f51\u641c\u7d22" in joined
    assert "Responses API" in joined
    assert "event: done" in joined


def test_passthrough_route_skips_backend_companion_and_history(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {
            "id": 101,
            "phone": "13800138000",
            "nickname": "owner",
            "avatar_url": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        server_module,
        "get_user_membership",
        lambda user_id: {
            "plan_code": "vip_monthly",
            "tier": "vip",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": {"daily_message_quota": 30, "model_access_level": "vip"},
        },
    )
    monkeypatch.setattr(server_module, "consume_chat_quota_or_raise", lambda user_id, membership: None, raising=False)
    monkeypatch.setattr(
        server_module,
        "apply_active_companion",
        lambda config: (_ for _ in ()).throw(AssertionError("should not call apply_active_companion")),
    )
    monkeypatch.setattr(
        server_module,
        "save_message",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not save history")),
    )
    monkeypatch.setattr(
        server_module,
        "resolve_llm_settings",
        lambda config: ("key", "http://example.test/v1", "demo-model"),
    )

    class DummyResponse:
        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"\u4f60"}}]}'
            yield 'data: {"choices":[{"delta":{"content":"\u597d"}}]}'
            yield "data: [DONE]"

    class DummyStream:
        def __enter__(self):
            return DummyResponse()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("backend.passthrough_chat.httpx.stream", lambda *args, **kwargs: DummyStream())

    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "frontend prompt",
            "message": "hello",
            "context": [{"role": "assistant", "content": "existing"}],
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert "event: assistant_delta" in response.text
    assert "data: \\u4f60" not in response.text
    assert "data: \u4f60" in response.text
    assert "event: done" in response.text


def test_passthrough_route_uses_live_search_stream_for_search_queries(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {
            "id": 101,
            "phone": "13800138000",
            "nickname": "owner",
            "avatar_url": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        server_module,
        "get_user_membership",
        lambda user_id: {
            "plan_code": "vip_monthly",
            "tier": "vip",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": {"daily_message_quota": 30, "model_access_level": "vip"},
        },
    )
    monkeypatch.setattr(server_module, "consume_chat_quota_or_raise", lambda user_id, membership: None, raising=False)
    monkeypatch.setattr(
        server_module,
        "resolve_live_search_llm_settings",
        lambda config: ("key", "http://example.test/v1", "demo-model"),
    )

    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield 'data: {"type":"response.output_text.delta","delta":"\u6700\u65b0"}'
            yield 'data: {"type":"response.output_text.delta","delta":"\u5929\u6c14"}'
            yield "data: [DONE]"

    class DummyStream:
        def __enter__(self):
            return DummyResponse()

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_stream(method, url, headers=None, json=None, timeout=None):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyStream()

    monkeypatch.setattr("backend.passthrough_chat.httpx.stream", fake_stream)

    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "frontend prompt",
            "message": "\u5408\u80a5\u4eca\u5929\u5929\u6c14\u600e\u4e48\u6837",
            "context": [{"role": "assistant", "content": "existing"}],
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert captured["method"] == "POST"
    assert captured["url"] == "http://example.test/v1/responses"
    assert captured["json"]["tools"] == [{"type": "web_search_preview"}]
    assert captured["json"]["input"][-1] == {
        "role": "user",
        "content": "\u5408\u80a5\u4eca\u5929\u5929\u6c14\u600e\u4e48\u6837",
    }
    assert "event: phase" in response.text
    assert "data: searching" in response.text
    assert "data: composing" in response.text
    assert "\u6700\u65b0" in response.text
    assert "\u5929\u6c14" in response.text
    assert "event: done" in response.text


def test_passthrough_route_returns_visible_error_for_known_unsupported_live_search_provider(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {
            "id": 101,
            "phone": "13800138000",
            "nickname": "owner",
            "avatar_url": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        server_module,
        "get_user_membership",
        lambda user_id: {
            "plan_code": "vip_monthly",
            "tier": "vip",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": {"daily_message_quota": 30, "model_access_level": "vip"},
        },
    )
    monkeypatch.setattr(server_module, "consume_chat_quota_or_raise", lambda user_id, membership: None, raising=False)
    monkeypatch.setattr(
        server_module,
        "resolve_llm_settings",
        lambda config: ("key", "https://api.deepseek.com/v1", "deepseek-chat"),
    )
    monkeypatch.setattr(
        "backend.passthrough_chat.httpx.stream",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call upstream live search")),
    )

    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "frontend prompt",
            "message": "\u4eca\u5929\u6709\u4ec0\u4e48\u5a31\u4e50\u65b0\u95fb",
            "context": [],
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert "data: searching" in response.text
    assert "data: composing" in response.text
    assert "\u4e0d\u652f\u6301\u8054\u7f51\u641c\u7d22" in response.text
    assert "Responses API" in response.text
    assert "event: done" in response.text


def test_passthrough_route_uses_standard_stream_for_non_search_queries(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {
            "id": 101,
            "phone": "13800138000",
            "nickname": "owner",
            "avatar_url": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        server_module,
        "get_user_membership",
        lambda user_id: {
            "plan_code": "vip_monthly",
            "tier": "vip",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": {"daily_message_quota": 30, "model_access_level": "vip"},
        },
    )
    monkeypatch.setattr(server_module, "consume_chat_quota_or_raise", lambda user_id, membership: None, raising=False)
    monkeypatch.setattr(
        server_module,
        "resolve_llm_settings",
        lambda config: ("key", "http://example.test/v1", "demo-model"),
    )

    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"reply"}}]}'
            yield "data: [DONE]"

    class DummyStream:
        def __enter__(self):
            return DummyResponse()

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_stream(method, url, headers=None, json=None, timeout=None):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyStream()

    monkeypatch.setattr("backend.passthrough_chat.httpx.stream", fake_stream)

    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "frontend prompt",
            "message": "hello",
            "context": [{"role": "assistant", "content": "existing"}],
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert response.text.count("event: state") == 1
    assert captured["method"] == "POST"
    assert captured["url"] == "http://example.test/v1/chat/completions"
    assert captured["json"]["messages"][-1] == {"role": "user", "content": "hello"}
    assert "data: searching" not in response.text
    assert "data: composing" in response.text
    assert "reply" in response.text
    assert "event: done" in response.text


def test_passthrough_route_rejects_invalid_context_role():
    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "frontend prompt",
            "message": "hello",
            "context": [{"role": "system", "content": "not allowed"}],
        },
    )

    assert response.status_code == 422
