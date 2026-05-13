# P0 Gap Closure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the real P0 gaps so Desktop AI Companion stops being only a working desktop AI shell and becomes a testable companion product with better companion-style chat, visible lightweight memory, and a runnable alpha validation loop.

**Architecture:** Keep the current Tauri + TypeScript + FastAPI architecture and avoid broad feature expansion. Split the work into two parallel tracks: product-experience improvements inside the app, and alpha-validation assets plus metrics outside the app. Companion chat and memory should stay intentionally small and controllable. Use the provided OpenAI-compatible test route for model integration testing, but never write raw secrets into the repo.

**Tech Stack:** Tauri v2, TypeScript, FastAPI, SQLite, pytest, Playwright for Python, Markdown planning docs, OpenAI-compatible chat API using `gpt-5.4` via custom `base_url`

---

## File Structure Lock-In

**Modify:**
- `backend/server.py`
  Responsible for companion-style chat shaping, memory APIs, and model call integration.
- `app/db.py`
  Responsible for minimal memory CRUD and any helper queries needed for user-facing memory.
- `app/config.py`
  Responsible for canonical stored nickname / preferred-address configuration defaults.
- `tauri-app/src/chat-client.ts`
  Responsible for frontend chat calls and new memory API helpers.
- `tauri-app/src/main.ts`
  Responsible for wiring companion chat UX, visible memory entry points, and metrics event points.
- `tauri-app/index.html`
  Responsible for minimal memory UI surface and any P0-visible feedback affordances.
- `.agents/product-marketing-context.md`
  Responsible for the reusable product/marketing truth source.
- `docs/superpowers/specs/2026-05-13-p0-analysis-notes.md`
  Responsible for preserving the reasoning trail behind this plan.

**Create:**
- `tests/test_companion_chat_api.py`
  Regression tests for companion-style response shaping and memory-aware chat behavior.
- `tests/test_memory_api.py`
  Backend regression tests for visible memory CRUD endpoints.
- `tools/test_memory_panel_flow.py`
  Browser-level check that memory can be displayed and removed from the UI.
- `docs/alpha/alpha-invite.md`
  Alpha recruitment copy.
- `docs/alpha/alpha-signup-form.md`
  Signup questions and screening logic.
- `docs/alpha/alpha-feedback-loop.md`
  Welcome copy, daily prompts, weekly prompts, and bug report format.
- `docs/alpha/p0-metrics-template.md`
  Weekly review template for presence validation.
- `docs/marketing/p0-demo-scripts.md`
  15-second demo scripts and asset checklist.

---

## Shared Constraints

- [ ] Do **not** write the raw API key into any committed file.
- [ ] Use environment variables for model testing:

```text
OPENAI_API_KEY=<provided-by-user-at-runtime>
OPENAI_BASE_URL=https://api.hanbbq.top/v1
OPENAI_MODEL=gpt-5.4
```

- [ ] Keep memory scope tiny for P0:
  - nickname
  - preferred form of address
  - a few explicit user preferences
- [ ] Keep companion response shaping lightweight and reversible. No large persona engine.
- [ ] Do not add broad multi-agent, voice, or marketplace work.

---

### Task 1: Add Companion Chat Layer Over Raw Chat Replies

**Files:**
- Create: `tests/test_companion_chat_api.py`
- Modify: `backend/server.py`
- Modify: `app/config.py`

- [ ] **Step 1: Write the failing backend chat personality test**

Create `tests/test_companion_chat_api.py` with these minimal assertions:

```python
from fastapi.testclient import TestClient

import app.config as config_module
from app.config import AppConfig, save_config
from backend.server import app


client = TestClient(app)


def reset_config() -> None:
    config_module.config = AppConfig(
        user_nickname="阿泽",
        user_display_name="阿泽",
        character_name="小艾",
        personality=["温柔"],
    )
    save_config(config_module.config)


def test_chat_reply_mentions_user_or_companion_tone():
    reset_config()

    response = client.post("/chat", json={"message": "今天有点累", "context": []})

    assert response.status_code == 200
    content = response.json()["content"]
    assert isinstance(content, str)
    assert content.strip() != ""
    assert any(token in content for token in ["阿泽", "小艾", "辛苦", "陪", "休息"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_companion_chat_api.py -q`
Expected: FAIL because current fallback replies are random and not shaped around the user or companion identity.

- [ ] **Step 3: Add a small companion response shaper**

In `backend/server.py`, add a small helper that wraps the generated model/fallback answer using config-driven tone.

Use this shape:

```python
def shape_companion_reply(message: str, raw_reply: str, config: AppConfig) -> str:
    user_name = config.user_display_name.strip() or config.user_nickname.strip() or "你"
    companion_name = config.character_name.strip() or "小艾"

    if any(word in message for word in ["累", "困", "烦", "难受", "压力"]):
        return f"{user_name}，辛苦啦。{companion_name}在这儿陪你一下。{raw_reply}"

    return f"{user_name}，{raw_reply}"
```

Then change `/chat` so it does:

```python
current = get_config()
response_content = shape_companion_reply(
    request.message,
    generate_chat_response(request.message, request.context, current),
    current,
)
```

- [ ] **Step 4: Add model call support with safe environment-variable wiring**

Still in `backend/server.py`, add a minimal model helper. Do not add SDK sprawl. Use `httpx` if already available or add it as a dependency if missing.

Use this shape:

```python
import os
import httpx


def generate_chat_response(message: str, context: list[ChatMessage], config: AppConfig) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.hanbbq.top/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()

    if not api_key:
        return generate_fallback_response(message)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个住在桌面上的 AI 小伙伴。"
                    "回复简短、温柔、有一点陪伴感，不要像客服，不要长篇大论。"
                ),
            },
            *[
                {"role": item.role, "content": item.content}
                for item in context[-8:]
            ],
            {"role": "user", "content": message},
        ],
        "temperature": 0.8,
    }

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return generate_fallback_response(message)
```

- [ ] **Step 5: Run the new tests**

Run: `python -m pytest tests/test_companion_chat_api.py tests/test_backend_api.py -q`
Expected: PASS.

- [ ] **Step 6: Verify model path manually with the provided test route**

Run in the shell for this session only:

```powershell
$env:OPENAI_API_KEY = "<provided-by-user-at-runtime>"; $env:OPENAI_BASE_URL = "https://api.hanbbq.top/v1"; $env:OPENAI_MODEL = "gpt-5.4"; python -m pytest tests/test_companion_chat_api.py -q
```

Expected: PASS, and `/chat` uses the configured model path when the key is present.

- [ ] **Step 7: Commit**

```bash
git add backend/server.py app/config.py tests/test_companion_chat_api.py requirements.txt
git commit -m "feat: add companion-style chat response layer"
```

---

### Task 2: Turn Lightweight Memory Into A User-Facing Loop

**Files:**
- Create: `tests/test_memory_api.py`
- Create: `tools/test_memory_panel_flow.py`
- Modify: `app/db.py`
- Modify: `backend/server.py`
- Modify: `tauri-app/src/chat-client.ts`
- Modify: `tauri-app/src/main.ts`
- Modify: `tauri-app/index.html`

- [ ] **Step 1: Write failing backend memory CRUD tests**

Create `tests/test_memory_api.py` with:

```python
from fastapi.testclient import TestClient

from backend.server import app


client = TestClient(app)


def test_memory_create_list_delete_flow():
    create_response = client.post(
        "/memory",
        json={"content": "用户喜欢被叫阿泽", "category": "preference", "importance": 2},
    )
    assert create_response.status_code == 200

    list_response = client.get("/memory")
    assert list_response.status_code == 200
    memories = list_response.json()
    assert any(item["content"] == "用户喜欢被叫阿泽" for item in memories)

    memory_id = next(item["id"] for item in memories if item["content"] == "用户喜欢被叫阿泽")
    delete_response = client.delete(f"/memory/{memory_id}")
    assert delete_response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memory_api.py -q`
Expected: FAIL because `/memory` routes do not exist yet.

- [ ] **Step 3: Add backend memory routes**

In `backend/server.py`, add models and endpoints:

```python
from app.db import clear_messages, delete_memory, get_memories, get_messages, save_memory, save_message


class MemoryCreateRequest(BaseModel):
    content: str
    category: str = "preference"
    importance: int = 1


@app.get("/memory")
async def list_memory():
    return get_memories()


@app.post("/memory")
async def create_memory(payload: MemoryCreateRequest):
    save_memory(payload.content, payload.category, payload.importance)
    return {"status": "ok"}


@app.delete("/memory/{memory_id}")
async def remove_memory(memory_id: int):
    delete_memory(memory_id)
    return {"status": "ok"}
```

- [ ] **Step 4: Make chat actually use memory**

Still in `backend/server.py`, fetch top memories and insert them into the system prompt.

Use this shape inside `generate_chat_response`:

```python
memories = get_memories()[:5]
memory_block = "\n".join(f"- {item['content']}" for item in memories)
system_prompt = (
    "你是一个住在桌面上的 AI 小伙伴。"
    "回复简短、温柔、有一点陪伴感。\n"
    "你已知的用户信息：\n"
    f"{memory_block or '- 暂无额外记忆'}"
)
```

- [ ] **Step 5: Add frontend memory helpers**

In `tauri-app/src/chat-client.ts`, add:

```ts
export interface MemoryItem {
    id: number;
    content: string;
    category: string;
    importance: number;
    created_at: string;
}

public async loadMemory(): Promise<MemoryItem[]> {
    const response = await fetch(this.getEndpointUrl('memory'));
    if (!response.ok) throw new Error(`Memory request failed: ${response.status}`);
    return await response.json() as MemoryItem[];
}

public async deleteMemory(memoryId: number): Promise<void> {
    const response = await fetch(`${this.getEndpointUrl('memory')}/${memoryId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(`Delete memory failed: ${response.status}`);
}
```

Also extend `getEndpointUrl` to support `'memory'`.

- [ ] **Step 6: Add a minimal visible memory panel**

In `tauri-app/index.html`, add a small memory section inside settings:

```html
<div class="settings-item">
  <strong>她记住的内容</strong>
  <div id="memory-list"></div>
</div>
```

In `tauri-app/src/main.ts`, add:

```ts
async function refreshMemoryList() {
    const container = document.getElementById('memory-list');
    if (!container) return;

    const memories = await chatClient.loadMemory();
    container.innerHTML = '';

    memories.forEach((memory) => {
        const row = document.createElement('div');
        row.className = 'memory-row';
        row.innerHTML = `<span>${memory.content}</span><button data-memory-id="${memory.id}">删除</button>`;
        container.appendChild(row);
    });

    container.querySelectorAll<HTMLButtonElement>('button[data-memory-id]').forEach((button) => {
        button.addEventListener('click', async () => {
            await chatClient.deleteMemory(Number(button.dataset.memoryId));
            await refreshMemoryList();
        });
    });
}
```

Call `refreshMemoryList()` when settings opens.

- [ ] **Step 7: Add browser-level memory UI regression**

Create `tools/test_memory_panel_flow.py` with:

```python
import requests
from playwright.sync_api import sync_playwright


def main() -> None:
    requests.post(
        "http://127.0.0.1:8080/memory",
        json={"content": "用户喜欢被叫阿泽", "category": "preference", "importance": 2},
        timeout=5,
    ).raise_for_status()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
        page.goto("http://127.0.0.1:1420", wait_until="domcontentloaded")
        page.click('[data-action="settings"]')
        page.wait_for_timeout(500)
        assert "用户喜欢被叫阿泽" in page.locator("#memory-list").inner_text()
        browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run tests to verify the memory loop works**

Run: `python -m pytest tests/test_memory_api.py -q`
Run: `python tools/test_memory_panel_flow.py`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add app/db.py backend/server.py tauri-app/src/chat-client.ts tauri-app/src/main.ts tauri-app/index.html tests/test_memory_api.py tools/test_memory_panel_flow.py
git commit -m "feat: add visible lightweight memory loop"
```

---

### Task 3: Define And Prepare Presence Metrics In Product Surfaces

**Files:**
- Modify: `tauri-app/src/main.ts`
- Create: `docs/alpha/p0-metrics-template.md`

- [ ] **Step 1: Add minimal event logging points in the front end**

In `tauri-app/src/main.ts`, add a tiny helper:

```ts
function logProductEvent(name: string, payload: Record<string, unknown> = {}) {
    console.log(`PRODUCT_EVENT ${name} ${JSON.stringify(payload)}`);
}
```

Then log at least these events:

- `app_loaded`
- `chat_opened`
- `message_sent`
- `history_restored`
- `settings_opened`
- `memory_viewed`
- `memory_deleted`

- [ ] **Step 2: Write the weekly P0 metrics template**

Create `docs/alpha/p0-metrics-template.md` with sections:

```md
# P0 Weekly Presence Review

## Behavior Metrics
- Install success
- First successful launch
- Chat success rate
- History restore success
- Average daily conversation count
- Long-session open behavior

## User Quotes
- Presence
- Comfort / companionship
- Annoyance / friction

## Key Questions
1. Did users come back?
2. Did they describe her as present?
3. What made her feel real?
4. What felt gimmicky?
```

- [ ] **Step 3: Verify event points exist**

Run: `rg -n "PRODUCT_EVENT|history_restored|memory_viewed|message_sent" tauri-app/src/main.ts`
Expected: all required event hooks are present.

- [ ] **Step 4: Commit**

```bash
git add tauri-app/src/main.ts docs/alpha/p0-metrics-template.md
git commit -m "chore: add p0 presence metrics hooks and template"
```

---

### Task 4: Create Alpha Recruitment And Feedback Ops Pack

**Files:**
- Create: `docs/alpha/alpha-invite.md`
- Create: `docs/alpha/alpha-signup-form.md`
- Create: `docs/alpha/alpha-feedback-loop.md`
- Modify: `.agents/product-marketing-context.md`

- [ ] **Step 1: Write alpha invite copy**

Create `docs/alpha/alpha-invite.md` with sections:

```md
# Desktop AI Companion Alpha Invite

我在做一个住在桌面上的 AI 小伙伴。

她不是普通聊天窗口，而是一个会常驻在桌面上、会有表情动作、会记住你一点点的小伙伴。

现在想找 30 位内测用户，一起打磨第一版。

如果你喜欢 AI、桌宠、Live2D，或者想要一个安静陪着你的桌面角色，欢迎来试试。

目前版本可能会有 bug，但我会根据反馈快速迭代。
```

- [ ] **Step 2: Write signup form questions**

Create `docs/alpha/alpha-signup-form.md` with:

```md
# Alpha Signup Questions

1. 你的系统是 Windows 还是 macOS？
2. 你是否用过桌宠 / Live2D / AI 聊天产品？
3. 你更想要陪伴感还是效率辅助？
4. 你能否接受早期版本 bug？
5. 你愿意加入反馈群吗？
6. 你每天大概有多长时间在电脑前？
```

- [ ] **Step 3: Write feedback loop doc**

Create `docs/alpha/alpha-feedback-loop.md` with:

```md
# Alpha Feedback Loop

## Welcome Message
欢迎来测这个住在桌面上的 AI 小伙伴。这个版本还很早期，我最想知道的是：她有没有真的让你觉得“在桌面上陪着你”。

## Daily Questions
- 今天有没有打开她？
- 哪个瞬间让你觉得她“活了”？
- 哪个地方最烦？

## Weekly Questions
- 你更把她当工具还是伙伴？
- 如果只能保留一个功能，你会保留什么？
- 你明天还会继续开着她吗？

## Bug Report Format
- 发生了什么
- 你当时在做什么
- 是否稳定复现
- 你原本期待什么
```

- [ ] **Step 4: Update product marketing context with alpha ops reality**

Append or refine `.agents/product-marketing-context.md` so `Goals` and `Proof Points` state that the immediate objective is a 20-50 person alpha focused on repeated voluntary use and presence feedback.

- [ ] **Step 5: Review docs for consistency**

Run: `rg -n "内测|alpha|陪伴|桌面上的 AI 小伙伴" docs/alpha .agents/product-marketing-context.md`
Expected: copy is consistent with the product thesis.

- [ ] **Step 6: Commit**

```bash
git add docs/alpha/alpha-invite.md docs/alpha/alpha-signup-form.md docs/alpha/alpha-feedback-loop.md .agents/product-marketing-context.md
git commit -m "docs: add alpha recruitment and feedback pack"
```

---

### Task 5: Create Minimum Marketing Asset Scripts

**Files:**
- Create: `docs/marketing/p0-demo-scripts.md`
- Modify: `docs/superpowers/plans/2026-05-13-p0-marketing-task-list.md`

- [ ] **Step 1: Write the three short demo scripts**

Create `docs/marketing/p0-demo-scripts.md` with:

```md
# P0 Demo Scripts

## Script A: Presence
1. 角色待在桌面角落
2. 用户点击角色
3. 输入“今天有点累”
4. 角色进入思考状态
5. 回复一句温柔的话
6. 回到安静待机

## Script B: Utility
1. 用户正在写文档或代码
2. 卡住了
3. 点击角色提问
4. 角色思考
5. 给出简洁帮助
6. 用户继续工作，角色安静待着

## Script C: Reaction
1. 待机
2. listening
3. thinking
4. talking
5. hide / quiet presence
```

- [ ] **Step 2: Add asset checklist**

In the same file, add:

```md
## Asset Checklist
- 1 个 15 秒 MP4
- 1 个 GIF
- 3 张截图
- 1 句标题
- 1 句副标题
```

- [ ] **Step 3: Update the existing marketing task list to reference this asset file**

In `docs/superpowers/plans/2026-05-13-p0-marketing-task-list.md`, add a note under demo asset work pointing to `docs/marketing/p0-demo-scripts.md` as the source script file.

- [ ] **Step 4: Verify the file contains all three launch angles**

Run: `rg -n "Presence|Utility|Reaction|Asset Checklist" docs/marketing/p0-demo-scripts.md`
Expected: all sections are present.

- [ ] **Step 5: Commit**

```bash
git add docs/marketing/p0-demo-scripts.md docs/superpowers/plans/2026-05-13-p0-marketing-task-list.md
git commit -m "docs: script minimum p0 marketing assets"
```

---

## Final Verification Checklist

- [ ] Run: `python -m pytest tests/test_backend_api.py tests/test_companion_chat_api.py tests/test_memory_api.py -q`
- [ ] Run: `python tools/test_chat_history_restore.py`
- [ ] Run: `python tools/test_companion_state_logs.py`
- [ ] Run: `python tools/test_memory_panel_flow.py`
- [ ] Run: `npm run build` in `tauri-app`
- [ ] Run: `rg -n "一个住在桌面上的 AI 小伙伴|会记住你一点点|陪伴" docs/alpha docs/marketing .agents/product-marketing-context.md`

Expected result: the app feels more companion-like, memory becomes user-visible, and the team has a runnable alpha ops + measurement pack.
