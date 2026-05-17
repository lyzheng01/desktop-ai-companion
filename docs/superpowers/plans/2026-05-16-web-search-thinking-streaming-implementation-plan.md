# Web Search, Thinking, And Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tool-assisted web-search path for current-information questions, while keeping the companion in `thinking` during lookup and streaming the final response into the frontend instead of rendering it all at once.

**Architecture:** Introduce a deterministic backend routing layer that decides whether a query needs live external information. Route those queries through a backend-owned search tool, then stream the final assistant reply through a dedicated endpoint. On the frontend, consume the stream incrementally so the user sees `thinking`, then a progressively appearing reply, then `idle`.

**Tech Stack:** FastAPI, Python, TypeScript, Vite, Tauri v2, existing OpenAI-compatible backend, streaming HTTP/SSE-style response handling, pytest, Playwright for Python

---

## File Structure Lock-In

**Modify:**
- `backend/server.py`
  Add search intent detection, search tool call, streaming endpoint, and final assistant buffering.
- `tauri-app/src/chat-client.ts`
  Add a streaming chat client path and chunk handling.
- `tauri-app/src/main.ts`
  Add `thinking`/`talking` streaming state behavior and progressive assistant rendering.

**Create:**
- `tests/test_search_routing.py`
  Unit tests for routing current-information questions to the search path.
- `tests/test_stream_prompt_flow.py`
  Backend tests for streamed response assembly.
- `tools/test_streaming_weather_chat.py`
  Browser-level regression for asking a weather question and seeing a streamed answer.

---

### Task 1: Add Deterministic Search Routing

**Files:**
- Modify: `backend/server.py`
- Create: `tests/test_search_routing.py`

- [ ] **Step 1: Write the failing routing test**

Create `tests/test_search_routing.py` with:

```python
from backend.server import needs_live_search


def test_weather_question_requires_search():
    assert needs_live_search("合肥今天天气如何") is True


def test_latest_fact_question_requires_search():
    assert needs_live_search("今天美元汇率是多少") is True


def test_general_companion_chat_does_not_require_search():
    assert needs_live_search("今天有点累") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_routing.py -q`
Expected: FAIL because `needs_live_search` does not exist yet.

- [ ] **Step 3: Add routing helper**

In `backend/server.py`, add:

```python
def needs_live_search(message: str) -> bool:
    search_tokens = [
        "天气", "气温", "温度", "下雨", "降雨",
        "今天", "现在", "最新", "实时", "新闻", "汇率",
    ]
    return any(token in message for token in search_tokens)
```

- [ ] **Step 4: Re-run tests**

Run: `python -m pytest tests/test_search_routing.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/server.py tests/test_search_routing.py
git commit -m "feat: add deterministic live-search routing"
```

---

### Task 2: Add Backend Search Tool Wrapper

**Files:**
- Modify: `backend/server.py`
- Modify: `tests/test_search_routing.py`

- [ ] **Step 1: Extend the failing test with a tool wrapper expectation**

Add a minimal tool-formatting test such as:

```python
from backend.server import build_search_context_block


def test_build_search_context_block_formats_search_result():
    result = build_search_context_block("合肥今天天气如何", "合肥今天多云，25°C")
    assert "合肥今天多云" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_routing.py -q`
Expected: FAIL because helper does not exist.

- [ ] **Step 3: Add search tool wrapper**

In `backend/server.py`, add a simple wrapper:

```python
def search_web(query: str) -> str:
    # temporary placeholder adapter; replace with actual provider integration
    raise NotImplementedError


def build_search_context_block(query: str, search_result: str) -> str:
    return f"外部检索结果（{query}）：\n{search_result.strip()}"
```

For this first implementation, `search_web()` should be designed so it can later plug into an actual provider call cleanly.

- [ ] **Step 4: Re-run tests**

Run: `python -m pytest tests/test_search_routing.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/server.py tests/test_search_routing.py
git commit -m "feat: add backend search tool wrapper"
```

---

### Task 3: Add Streaming Backend Endpoint

**Files:**
- Modify: `backend/server.py`
- Create: `tests/test_stream_prompt_flow.py`

- [ ] **Step 1: Write the failing stream-format test**

Create `tests/test_stream_prompt_flow.py` with:

```python
from backend.server import iter_stream_chunks


def test_stream_chunks_include_state_and_done_markers():
    chunks = list(iter_stream_chunks(["你好", "世界"]))
    joined = "\n".join(chunks)
    assert "event: state" in joined
    assert "event: assistant_delta" in joined
    assert "event: done" in joined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_stream_prompt_flow.py -q`
Expected: FAIL because stream helper does not exist.

- [ ] **Step 3: Add stream chunk helper and `/chat/stream`**

In `backend/server.py`, add:

```python
def iter_stream_chunks(parts: list[str]):
    yield "event: state\ndata: thinking\n\n"
    for part in parts:
        yield f"event: assistant_delta\ndata: {part}\n\n"
    yield "event: done\ndata: {}\n\n"
```

Then add a streaming endpoint skeleton:

```python
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    ...
```

Use `StreamingResponse` and buffer the final assistant text so only the full assistant message is saved when complete.

- [ ] **Step 4: Re-run tests**

Run: `python -m pytest tests/test_stream_prompt_flow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/server.py tests/test_stream_prompt_flow.py
git commit -m "feat: add streaming chat endpoint skeleton"
```

---

### Task 4: Route Weather / Current Questions Through Search And Stream Result

**Files:**
- Modify: `backend/server.py`
- Modify: `tests/test_stream_prompt_flow.py`

- [ ] **Step 1: Add failing search-path behavior test**

Add a backend test that monkeypatches `search_web()` and verifies search result is included in the assistant construction path for weather-style questions.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_stream_prompt_flow.py -q`
Expected: FAIL because `/chat/stream` does not yet branch through the search tool.

- [ ] **Step 3: Implement backend search branch**

In `/chat/stream`:

- save user message,
- detect `needs_live_search(message)`,
- if true, call `search_web(message)`,
- build a `search_context_block`,
- inject it into the assistant prompt,
- stream back the final assistant reply as chunks.

If search fails:

- return a safe fallback message that admits the search failed,
- do not hallucinate current facts.

- [ ] **Step 4: Re-run tests**

Run: `python -m pytest tests/test_search_routing.py tests/test_stream_prompt_flow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/server.py tests/test_search_routing.py tests/test_stream_prompt_flow.py
git commit -m "feat: route current questions through search stream"
```

---

### Task 5: Add Frontend Streaming Chat Consumption

**Files:**
- Modify: `tauri-app/src/chat-client.ts`
- Modify: `tauri-app/src/main.ts`
- Create: `tools/test_streaming_weather_chat.py`

- [ ] **Step 1: Write the failing browser regression**

Create `tools/test_streaming_weather_chat.py` with a browser test that:

- asks `合肥今天天气如何`
- expects the UI to enter `thinking`
- expects assistant text to appear progressively
- expects chat to end in `idle`

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_streaming_weather_chat.py`
Expected: FAIL because frontend still uses non-streaming `/chat`.

- [ ] **Step 3: Add streaming client path**

In `tauri-app/src/chat-client.ts`, add:

```ts
public async streamAndYield(content: string, onDelta: (chunk: string) => void, onState?: (state: string) => void): Promise<string> {
    ...
}
```

It should consume the `/chat/stream` endpoint and return the final buffered assistant message.

- [ ] **Step 4: Add progressive rendering in `main.ts`**

In `tauri-app/src/main.ts`:

- keep `listening`
- set `thinking`
- create an assistant placeholder message
- append chunks as they arrive
- switch to `talking` once deltas arrive
- finalize to `idle` when done

- [ ] **Step 5: Re-run browser regression**

Run: `python tools/test_streaming_weather_chat.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tauri-app/src/chat-client.ts tauri-app/src/main.ts tools/test_streaming_weather_chat.py
git commit -m "feat: stream tool-assisted replies into frontend"
```

---

## Final Verification Checklist

- [ ] Run: `python -m pytest tests/test_search_routing.py tests/test_stream_prompt_flow.py tests/test_memory_selection_rules.py tests/test_memory_prompt_assembly.py tests/test_backend_api.py tests/test_companion_chat_api.py tests/test_memory_api.py -q`
- [ ] Run: `python tools/test_streaming_weather_chat.py`
- [ ] Run: `npm run build` in `tauri-app`
- [ ] Verify asking a weather question keeps the companion in `thinking` while lookup happens.
- [ ] Verify the answer appears progressively, not all at once.

Expected result: time-sensitive questions can use live search, the companion visibly thinks during lookup, and replies stream into the chat UI instead of appearing all at once.
