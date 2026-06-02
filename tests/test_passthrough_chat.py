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

    chunks = list(iter_passthrough_events(["你", "好"]))
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


def test_passthrough_route_skips_backend_companion_and_history(monkeypatch):
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
            yield 'data: {"choices":[{"delta":{"content":"你"}}]}'
            yield 'data: {"choices":[{"delta":{"content":"好"}}]}'
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
    )

    assert response.status_code == 200
    assert "event: assistant_delta" in response.text
    assert "data: 你" in response.text
    assert "event: done" in response.text


def test_passthrough_route_streams_local_search_result_for_weather_queries(monkeypatch):
    monkeypatch.setattr(server_module, "search_weather", lambda query: "合肥今天多云，25°C")
    monkeypatch.setattr(
        "backend.passthrough_chat.httpx.stream",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call upstream model")),
    )

    response = client.post(
        "/chat/stream/passthrough",
        json={
            "system_prompt": "frontend prompt",
            "message": "合肥今天天气怎么样",
            "context": [{"role": "assistant", "content": "existing"}],
        },
    )

    assert response.status_code == 200
    assert "event: phase" in response.text
    assert "data: searching" in response.text
    assert "合肥今天多" in response.text
    assert "25°C" in response.text
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
