from backend.server import AppConfig, build_assistant_reply, build_companion_system_prompt, build_live_tool_reply, extract_stream_delta, iter_stream_chunks, iter_stream_reply


def test_stream_chunks_include_state_and_done_markers():
    chunks = list(iter_stream_chunks(["你好", "世界"]))
    joined = "\n".join(chunks)
    assert "event: state" in joined
    assert "event: assistant_delta" in joined
    assert "event: done" in joined


def test_stream_reply_includes_phase_and_deltas():
    chunks = list(iter_stream_reply("第一句。第二句。", phase="searching"))
    joined = "\n".join(chunks)
    assert "event: phase" in joined
    assert "data: searching" in joined
    assert joined.count("event: assistant_delta") >= 1


def test_build_assistant_reply_passes_search_context(monkeypatch):
    captured = {}

    def fake_generate_chat_response(message, context, config, search_context_block=None):
        captured["search_context_block"] = search_context_block
        return "查到了"

    monkeypatch.setattr("backend.server.generate_chat_response", fake_generate_chat_response)

    reply = build_assistant_reply(
        "合肥今天天气如何",
        [],
        AppConfig(),
        search_context_block="外部检索结果（合肥今天天气如何）：\n合肥今天多云，25°C",
    )

    assert "查到了" in reply
    assert "合肥今天多云" in captured["search_context_block"]


def test_build_live_tool_reply_for_datetime_does_not_need_model():
    reply = build_live_tool_reply(
        "今天几号",
        "今天的日期是 2026年05月16日，星期六。",
        AppConfig(),
    )

    assert "2026年05月16日" in reply


def test_build_companion_system_prompt_includes_memory_block():
    prompt = build_companion_system_prompt(AppConfig(character_name="小满", user_display_name="主人", personality=["温柔", "治愈"]), "稳定偏好：\n- 喜欢晴天")
    assert "桌面上的 AI 小伙伴" in prompt
    assert "喜欢晴天" in prompt
    assert "你的名字是小满" in prompt
    assert "用户叫主人" in prompt


def test_extract_stream_delta_from_responses_payload():
    payload = {"type": "response.output_text.delta", "delta": "你好"}
    assert extract_stream_delta(payload) == "你好"


def test_extract_stream_delta_from_chat_completions_payload():
    payload = {"choices": [{"delta": {"content": "世界"}}]}
    assert extract_stream_delta(payload) == "世界"
