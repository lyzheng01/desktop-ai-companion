# Web Search, Thinking State, And Streaming Response Design

## Goal

Add real-time answer capability for time-sensitive questions by introducing a web-search tool path, while preserving the companion feeling through visible `thinking` behavior and streaming response delivery in the frontend.

## Product Intent

When the user asks something like:

- 合肥今天天气如何
- 现在几点
- 今天有什么新闻
- 某件事的最新情况是什么

the product should not guess. It should feel like:

1. she understood the question,
2. she thought for a moment,
3. she looked something up,
4. she replied in-character,
5. and the answer arrived progressively instead of appearing all at once.

The target user feeling is:

> 她不是在瞎答，而是在查完以后一点点告诉我。

## Core Decision

The user approved two linked requirements:

1. add a **web search tool** for current / external information,
2. keep the frontend **streaming** the reply instead of waiting and showing the whole answer at once.

This means the product should not just swap in a different model endpoint. It needs a full request flow change.

## Recommended Architecture

Split the feature into three layers.

### 1. Request routing layer

The backend decides whether the user question is:

- normal companion chat, or
- tool-assisted query.

Good candidates for tool-assisted routing:

- weather
- time-sensitive facts
- current events
- “today / now / latest” questions

This should be deterministic first, not AI-decided first.

### 2. Tool execution layer

If the message needs live information, the backend calls a search tool first.

Suggested shape:

```python
def search_web(query: str) -> str:
    ...
```

The result should be reduced to a compact text block that can be injected into the model prompt.

### 3. Streaming reply layer

After the backend has enough information, it should stream the final companion reply token-by-token or chunk-by-chunk to the frontend.

The frontend then renders:

- `listening`
- `thinking`
- streaming assistant output
- `talking`
- `idle`

## Why Streaming Matters

If the product waits for the full tool call and full model completion before updating the UI, it feels dead.

Streaming gives two benefits:

1. better perceived responsiveness,
2. stronger character presence.

The user sees the answer forming, which feels closer to a desktop companion than a blocked tool request.

## Tooling Strategy

There are two possible ways to add search.

### Option A: Let the model own tool calling

Pros:

- elegant if the provider supports it well,
- generalizable to other tools later.

Cons:

- provider-dependent,
- harder to control deterministically,
- more opaque failure behavior.

### Option B: Backend-owned routing plus tool call (recommended)

Pros:

- predictable,
- easy to debug,
- easy to expand gradually,
- lets you decide which questions deserve search.

Cons:

- a little more backend logic.

## Recommendation

Use **Option B** first.

That means:

- backend detects weather/current-info intent,
- backend calls web search,
- backend passes compact search result into model prompt,
- backend streams the final response to the frontend.

This is the most practical and product-safe first version.

## Streaming Contract

The backend should expose a streaming chat path.

Possible shape:

- keep `/chat` for simple compatibility, or
- add `/chat/stream` for streaming specifically.

Recommended first version:

- add `/chat/stream`
- keep `/chat` temporarily for backwards compatibility if needed

The stream should send structured chunks such as:

```text
event: state
data: thinking

event: assistant_delta
data: "合肥今天"

event: assistant_delta
data: "多云，当前气温..."

event: done
data: {}
```

This makes frontend state handling much cleaner than raw text only.

## Frontend State Behavior

### On send

- immediately add user message
- set `listening`
- switch to `thinking`

### During tool call and model wait

- remain in `thinking`
- optionally show a subtle typing / searching cue

### When stream begins

- create an assistant message placeholder
- append streamed deltas into it
- set `talking`

### On completion

- finalize stored assistant message
- return to `idle`

## Storage Behavior

Streaming changes how messages are persisted.

Suggested approach:

- save user message immediately
- buffer assistant text on the frontend or backend during stream
- only persist final assistant message once the stream completes successfully

This avoids saving half-finished replies.

## Failure Handling

### Search failure

If search fails:

- do not silently hallucinate a fake current answer,
- either fall back to a non-current disclaimer,
- or say the search failed and invite retry.

### Streaming failure

If stream breaks mid-way:

- close the partial stream state,
- show a short failure message,
- do not leave the companion stuck in `thinking` or `talking`.

## Memory Interaction

Search-based questions should not automatically become long-term memory.

Good rule:

- external facts are not remembered by default,
- user preferences or self-descriptions still may be extracted separately.

This prevents the memory system from being polluted by transient external data.

## Scope Boundaries

This first version should support:

- weather
- current / latest factual questions
- streaming output
- visible thinking state during tool use

This first version should **not** yet support:

- many tools at once
- arbitrary multi-step agent workflows
- complex autonomous browsing
- citation-rich search UX
- deep tool planning layer

## Acceptance Criteria

This design is successful when:

- the product can answer current-information questions more accurately than the plain model path,
- the companion visibly stays in `thinking` while the tool path runs,
- the final answer streams into the UI instead of appearing all at once,
- failures do not leave the companion stuck in the wrong state,
- and the user experience still feels companion-like rather than technical.

## Recommendation Summary

The best implementation is not just “enable internet.”

It is:

> deterministic backend routing -> web search tool -> streaming companion reply -> visible thinking state.

That is the smallest architecture that gives live-answer capability without sacrificing product feel.
