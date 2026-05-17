# Phase 2 Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the current memory system from a flat list of records into a lightweight, selective, layered memory model that supports stable preferences, short-term context, long-term memory, and better prompt assembly without increasing user management burden.

**Architecture:** Keep memory local-first and simple, but split it into three scopes: `preference`, `short_term`, and `long_term`. Add a candidate-extraction layer inside the backend that turns some user messages into memory candidates, then apply deterministic selection rules before saving. Finally, improve prompt assembly so the model sees stable preferences first, then the most relevant short-term and long-term memory.

**Tech Stack:** FastAPI, SQLite, Python, pytest, TypeScript frontend, local JSON config, OpenAI-compatible model backend

---

## File Structure Lock-In

**Modify:**
- `app/db.py`
  Add memory scope support, short-term expiry helpers, and improved memory query functions.
- `backend/server.py`
  Add memory candidate extraction, selection rules, improved prompt assembly, and memory endpoint refinements.
- `tauri-app/src/main.ts`
  Adjust memory display grouping if needed, without turning memory into a heavy edit UI.
- `tauri-app/index.html`
  Add lightweight grouped memory display labels if needed.

**Create:**
- `tests/test_memory_selection_rules.py`
  Unit tests for candidate extraction and save rules.
- `tests/test_memory_prompt_assembly.py`
  Regression tests for layered memory injection order.
- `tools/test_memory_grouping_ui.py`
  Browser-level regression for grouped memory display.

---

### Task 1: Add Memory Scope And Layered Retrieval

**Files:**
- Modify: `app/db.py`
- Create: `tests/test_memory_selection_rules.py`

- [ ] **Step 1: Write the failing scope test**

Create `tests/test_memory_selection_rules.py` with:

```python
from app.db import get_memories, save_memory


def test_memory_scope_is_stored_and_filtered():
    save_memory("用户喜欢简短回复", category="preference", importance=3, scope="preference")
    save_memory("最近在做桌面 AI 项目", category="project", importance=2, scope="short_term")
    save_memory("长期喜欢治愈风格", category="preference", importance=2, scope="long_term")

    preference = get_memories(scope="preference")
    short_term = get_memories(scope="short_term")
    long_term = get_memories(scope="long_term")

    assert any(item["content"] == "用户喜欢简短回复" for item in preference)
    assert any(item["content"] == "最近在做桌面 AI 项目" for item in short_term)
    assert any(item["content"] == "长期喜欢治愈风格" for item in long_term)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memory_selection_rules.py -q`
Expected: FAIL because `save_memory()` and `get_memories()` do not support `scope` yet.

- [ ] **Step 3: Add memory scope field and DB migration**

In `app/db.py`:

```python
cursor.execute("PRAGMA table_info(memories)")
memory_columns = {row["name"] for row in cursor.fetchall()}
if "scope" not in memory_columns:
    cursor.execute("ALTER TABLE memories ADD COLUMN scope TEXT DEFAULT 'long_term'")
```

Then update helpers:

```python
def save_memory(content: str, category: str = "fact", importance: int = 1, scope: str = "long_term"):
    ...

def get_memories(category: Optional[str] = None, scope: Optional[str] = None) -> List[Dict]:
    ...
```

- [ ] **Step 4: Add short-term cleanup helper**

Still in `app/db.py`, add a minimal expiry helper:

```python
def delete_expired_short_term_memories(max_age_hours: int = 168):
    ...
```

For Phase 2, a simple age-based cleanup is enough.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_memory_selection_rules.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/db.py tests/test_memory_selection_rules.py
git commit -m "feat: add layered memory scopes"
```

---

### Task 2: Add Candidate Memory Extraction And Selection Rules

**Files:**
- Modify: `backend/server.py`
- Modify: `tests/test_memory_selection_rules.py`

- [ ] **Step 1: Write the failing extraction tests**

Extend `tests/test_memory_selection_rules.py` with:

```python
from backend.server import extract_memory_candidates


def test_extracts_explicit_preference_candidate():
    candidates = extract_memory_candidates("你以后叫我阿泽就好")
    assert any(item["scope"] == "preference" for item in candidates)


def test_extracts_short_term_project_candidate():
    candidates = extract_memory_candidates("我最近在做一个桌面 AI 项目")
    assert any(item["scope"] == "short_term" for item in candidates)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_memory_selection_rules.py -q`
Expected: FAIL because candidate extraction does not exist.

- [ ] **Step 3: Add candidate extraction in `backend/server.py`**

Add a small deterministic extractor:

```python
def extract_memory_candidates(message: str) -> list[dict]:
    candidates = []
    if "叫我" in message:
        candidates.append({
            "content": message.strip(),
            "category": "preference",
            "importance": 3,
            "scope": "preference",
        })
    if any(token in message for token in ["最近在做", "最近在准备", "这周在做"]):
        candidates.append({
            "content": message.strip(),
            "category": "project",
            "importance": 2,
            "scope": "short_term",
        })
    return candidates
```

- [ ] **Step 4: Add duplicate / conservative save rule**

Also in `backend/server.py`, add a helper like:

```python
def persist_memory_candidates(candidates: list[dict]):
    existing = {item["content"] for item in get_memories()}
    for candidate in candidates:
        if candidate["content"] in existing:
            continue
        save_memory(
            candidate["content"],
            category=candidate["category"],
            importance=candidate["importance"],
            scope=candidate["scope"],
        )
```

- [ ] **Step 5: Wire extraction into `/chat`**

Inside `/chat`, after saving the user message and before generating the final assistant reply:

```python
candidates = extract_memory_candidates(request.message)
persist_memory_candidates(candidates)
```

- [ ] **Step 6: Re-run tests**

Run: `python -m pytest tests/test_memory_selection_rules.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/server.py tests/test_memory_selection_rules.py
git commit -m "feat: add deterministic memory candidate extraction"
```

---

### Task 3: Improve Prompt Assembly Order

**Files:**
- Modify: `backend/server.py`
- Create: `tests/test_memory_prompt_assembly.py`

- [ ] **Step 1: Write the failing prompt-assembly test**

Create `tests/test_memory_prompt_assembly.py` with:

```python
from backend.server import build_memory_block


def test_memory_block_orders_preference_short_and_long_term():
    memory_block = build_memory_block(
        preference=[{"content": "叫用户阿泽"}],
        short_term=[{"content": "最近在做桌面 AI 项目"}],
        long_term=[{"content": "长期喜欢治愈风格"}],
    )

    assert memory_block.index("叫用户阿泽") < memory_block.index("最近在做桌面 AI 项目")
    assert memory_block.index("最近在做桌面 AI 项目") < memory_block.index("长期喜欢治愈风格")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memory_prompt_assembly.py -q`
Expected: FAIL because the helper does not exist.

- [ ] **Step 3: Add layered prompt-assembly helper**

In `backend/server.py`, add:

```python
def build_memory_block(preference: list[dict], short_term: list[dict], long_term: list[dict]) -> str:
    lines = []
    if preference:
        lines.append("稳定偏好：")
        lines.extend(f"- {item['content']}" for item in preference[:3])
    if short_term:
        lines.append("近期情况：")
        lines.extend(f"- {item['content']}" for item in short_term[:3])
    if long_term:
        lines.append("长期记忆：")
        lines.extend(f"- {item['content']}" for item in long_term[:3])
    return "\n".join(lines) if lines else "- 暂无额外记忆"
```

- [ ] **Step 4: Replace flat `get_memories()[:5]` usage**

Use:

```python
preference = get_memories(scope="preference")
short_term = get_memories(scope="short_term")
long_term = get_memories(scope="long_term")
memory_block = build_memory_block(preference, short_term, long_term)
```

- [ ] **Step 5: Re-run tests**

Run: `python -m pytest tests/test_memory_prompt_assembly.py tests/test_memory_selection_rules.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/server.py tests/test_memory_prompt_assembly.py
git commit -m "feat: add layered memory prompt assembly"
```

---

### Task 4: Add Lightweight Grouped Memory Display

**Files:**
- Modify: `tauri-app/index.html`
- Modify: `tauri-app/src/main.ts`
- Create: `tools/test_memory_grouping_ui.py`

- [ ] **Step 1: Write the failing grouped-UI test**

Create `tools/test_memory_grouping_ui.py` with a browser test that expects the memory area to show grouped headings such as:

- `稳定偏好`
- `近期记忆`
- `长期记忆`

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_memory_grouping_ui.py`
Expected: FAIL because memory is still rendered as one flat list.

- [ ] **Step 3: Group the memory UI**

In `tauri-app/src/main.ts`, update memory rendering so the frontend groups by `scope` and renders lightweight section headings instead of a flat list.

Do not add large edit forms.

- [ ] **Step 4: Re-run grouped UI test**

Run: `python tools/test_memory_grouping_ui.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tauri-app/index.html tauri-app/src/main.ts tools/test_memory_grouping_ui.py
git commit -m "feat: group memory display by scope"
```

---

## Final Verification Checklist

- [ ] Run: `python -m pytest tests/test_memory_selection_rules.py tests/test_memory_prompt_assembly.py tests/test_backend_api.py tests/test_companion_chat_api.py tests/test_memory_api.py -q`
- [ ] Run: `python tools/test_memory_grouping_ui.py`
- [ ] Verify explicit preference messages become stable preference memories.
- [ ] Verify recent-project style messages become short-term memories.
- [ ] Verify prompt assembly prefers stable preferences, then short-term, then long-term memory.

Expected result: the memory system becomes layered, more selective, more coherent in prompts, and still simple for the user.
