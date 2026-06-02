from backend.server import build_search_context_block, extract_weather_location, is_datetime_query, needs_live_search


def test_weather_question_requires_search():
    assert needs_live_search("合肥今天天气如何") is True


def test_latest_fact_question_requires_search():
    assert needs_live_search("今天美元汇率是多少") is True


def test_general_companion_chat_does_not_require_search():
    assert needs_live_search("今天有点累") is False


def test_build_search_context_block_formats_search_result():
    result = build_search_context_block("合肥今天天气如何", "合肥今天多云，25°C")
    assert "合肥今天多云" in result


def test_iter_local_search_result_stream_emits_searching_before_lookup():
    from backend.server import iter_local_search_result_stream

    calls = []

    def fake_lookup():
        calls.append("called")
        return "合肥今天多云，25°C"

    iterator = iter_local_search_result_stream(fake_lookup)

    assert next(iterator) == "event: state\ndata: thinking\n\n"
    assert calls == []
    assert next(iterator) == "event: phase\ndata: searching\n\n"
    assert calls == []


def test_extract_weather_location_drops_freshness_words():
    assert extract_weather_location("合肥今天天气如何") == "合肥"


def test_current_date_question_requires_live_path():
    assert needs_live_search("今天几号") is True


def test_current_date_question_with_duoshaohao_requires_live_path():
    assert needs_live_search("今天多少号") is True


def test_detects_datetime_query():
    assert is_datetime_query("今天几号") is True


def test_detects_datetime_query_variants():
    assert is_datetime_query("今天多少号") is True
    assert is_datetime_query("今天几月几日") is True
