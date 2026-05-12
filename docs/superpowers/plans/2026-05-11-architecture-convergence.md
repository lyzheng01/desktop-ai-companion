# Desktop AI Companion Architecture Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the project onto one production path: `Tauri + Web frontend + FastAPI backend`, while demoting the current `PyQt6` code to prototype-only status.

**Architecture:** The Tauri app becomes the only desktop shell and UI runtime. FastAPI becomes the only chat/config/history service. Existing Python persistence code in `app/config.py` and `app/db.py` is reused by the backend instead of maintaining separate in-memory state. The current PyQt widgets stay in the repo temporarily but are removed from the main README, entry points, and startup flow.

**Tech Stack:** Tauri v2, TypeScript, Vite, PixiJS, `pixi-live2d-display`, Rust commands only for shell/window integration, Python 3.10+, FastAPI, SQLite, pytest.

---

## File Map

- Modify: `E:/python/desktop-ai-companion/README.md`
- Modify: `E:/python/desktop-ai-companion/ARCHITECTURE.md`
- Modify: `E:/python/desktop-ai-companion/README_NEW_ARCH.md`
- Modify: `E:/python/desktop-ai-companion/backend/server.py`
- Modify: `E:/python/desktop-ai-companion/app/config.py`
- Modify: `E:/python/desktop-ai-companion/app/db.py`
- Modify: `E:/python/desktop-ai-companion/tauri-app/index.html`
- Modify: `E:/python/desktop-ai-companion/tauri-app/src/main.ts`
- Modify: `E:/python/desktop-ai-companion/tauri-app/src/chat-client.ts`
- Modify: `E:/python/desktop-ai-companion/tauri-app/src-tauri/src/main.rs`
- Create: `E:/python/desktop-ai-companion/tests/test_backend_api.py`
- Create: `E:/python/desktop-ai-companion/tests/test_config_paths.py`

### Task 1: Freeze The Main Architecture Contract

**Files:**
- Modify: `E:/python/desktop-ai-companion/README.md`
- Modify: `E:/python/desktop-ai-companion/ARCHITECTURE.md`
- Modify: `E:/python/desktop-ai-companion/README_NEW_ARCH.md`

- [ ] **Step 1: Rewrite the top-level README to name one supported runtime path**

Replace the current mixed-stack summary with a short architecture section like this:

```md
## 当前正式架构

- 桌面壳: Tauri
- 前端渲染: Vite + TypeScript + PixiJS + Live2D
- 后端服务: FastAPI
- 本地存储: SQLite + JSON 配置

## 当前仓库状态

- `tauri-app/` 是主前端与桌面入口
- `backend/server.py` 是主 API 服务入口
- `app/` 目录中的 PyQt6 代码当前仅保留为早期原型参考，不作为正式运行链路
```

- [ ] **Step 2: Remove stale file references from `README.md`**

Delete or replace references to files that do not exist, including examples like:

```md
- `app/ai/client.py`
- `app/ui/main_window.py`
- `app/ui/tray.py`
- `app/models/user.py`
```

Expected result: every path shown in `README.md` must exist in the repo.

- [ ] **Step 3: Update `ARCHITECTURE.md` so data ownership is explicit**

Use this architecture statement near the communication section:

```md
## 单一职责边界

- Tauri/Web: 负责窗口、交互、Live2D 渲染、聊天 UI
- FastAPI: 负责聊天 API、配置 API、聊天历史 API
- SQLite/JSON: 由 Python 后端统一读写
- Rust IPC: 只负责窗口级命令，例如退出、托盘、窗口控制
```

- [ ] **Step 4: Mark the PyQt path as deprecated in `README_NEW_ARCH.md`**

Add a warning block like this:

```md
> 注意：仓库仍保留 `app/` 下的 PyQt6 原型代码，仅用于历史参考与资源复用，不再作为主启动方式维护。
```

- [ ] **Step 5: Verify docs are internally consistent**

Run: `rg -n "PyQt6|main_window.py|tray.py|app/ai/client.py" "E:/python/desktop-ai-companion/README.md" "E:/python/desktop-ai-companion/ARCHITECTURE.md" "E:/python/desktop-ai-companion/README_NEW_ARCH.md"`

Expected: no stale production claims remain.

### Task 2: Make FastAPI The Only Source Of Chat And Persistence

**Files:**
- Modify: `E:/python/desktop-ai-companion/backend/server.py`
- Modify: `E:/python/desktop-ai-companion/app/config.py`
- Modify: `E:/python/desktop-ai-companion/app/db.py`
- Test: `E:/python/desktop-ai-companion/tests/test_backend_api.py`
- Test: `E:/python/desktop-ai-companion/tests/test_config_paths.py`

- [ ] **Step 1: Write the failing backend API tests**

Create `E:/python/desktop-ai-companion/tests/test_backend_api.py` with:

```python
from fastapi.testclient import TestClient

from backend.server import app


client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_round_trip_persists_values():
    payload = {
        "user_nickname": "测试用户",
        "character_type": "kei",
        "window_x": 123,
        "window_y": 456,
    }

    save_response = client.post("/config", json=payload)
    assert save_response.status_code == 200

    load_response = client.get("/config")
    assert load_response.status_code == 200
    data = load_response.json()
    assert data["user_nickname"] == "测试用户"
    assert data["window_x"] == 123
    assert data["window_y"] == 456


def test_chat_writes_history():
    client.delete("/history")
    chat_response = client.post("/chat", json={"message": "你好", "context": []})
    assert chat_response.status_code == 200
    history_response = client.get("/history")
    history = history_response.json()
    assert len(history) >= 2
    assert history[-2]["role"] == "user"
    assert history[-1]["role"] == "assistant"
```

- [ ] **Step 2: Write the failing config path test**

Create `E:/python/desktop-ai-companion/tests/test_config_paths.py` with:

```python
from app.config import DATA_DIR, CONFIG_FILE, DB_PATH


def test_data_paths_point_to_repo_data_dir():
    assert DATA_DIR.name == "data"
    assert CONFIG_FILE.name == "config.json"
    assert DB_PATH.name == "companion.db"
```

- [ ] **Step 3: Run tests to verify current failures**

Run: `pytest E:/python/desktop-ai-companion/tests/test_backend_api.py E:/python/desktop-ai-companion/tests/test_config_paths.py -v`

Expected: at least the config round-trip and chat persistence tests fail under the current in-memory backend behavior.

- [ ] **Step 4: Fix `app/config.py` path ownership before touching the API**

Ensure the module points to the repo root `data/` directory instead of `app/data/`.

Use this shape:

```python
APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "companion.db"
CONFIG_FILE = DATA_DIR / "config.json"
```

Note: keep `DATA_DIR.mkdir(exist_ok=True)`.

- [ ] **Step 5: Replace in-memory config/history in `backend/server.py` with shared persistence helpers**

Refactor imports toward this shape:

```python
from app.config import AppConfig, get_config, save_config as persist_config
from app.db import clear_messages, get_messages, save_message
```

Then rewrite the endpoint logic to follow this shape:

```python
@app.get("/config")
async def get_config_endpoint():
    return get_config()


@app.post("/config")
async def save_config_endpoint(config: Config):
    current = get_config()
    current.user_nickname = config.user_nickname
    current.character_type = config.character_type
    current.window_x = config.window_x
    current.window_y = config.window_y
    persist_config(current)
    return current


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    save_message("user", request.message)
    response_content = generate_fallback_response(request.message)
    save_message("assistant", response_content)
    return ChatResponse(content=response_content)


@app.get("/history")
async def get_history(limit: int = 50):
    return get_messages(limit=limit)


@app.delete("/history")
async def clear_history():
    clear_messages()
    return {"status": "ok"}
```

- [ ] **Step 6: Avoid mutable default request values in `backend/server.py`**

Change:

```python
context: List[ChatMessage] = []
```

To:

```python
from pydantic import BaseModel, Field

context: List[ChatMessage] = Field(default_factory=list)
```

- [ ] **Step 7: Run backend tests until green**

Run: `pytest E:/python/desktop-ai-companion/tests/test_backend_api.py E:/python/desktop-ai-companion/tests/test_config_paths.py -v`

Expected: PASS.

### Task 3: Make The Tauri Frontend Use The Real Backend Path

**Files:**
- Modify: `E:/python/desktop-ai-companion/tauri-app/index.html`
- Modify: `E:/python/desktop-ai-companion/tauri-app/src/main.ts`
- Modify: `E:/python/desktop-ai-companion/tauri-app/src/chat-client.ts`

- [ ] **Step 1: Fix the Pixi mount container in `index.html`**

Replace:

```html
<canvas id="character-canvas"></canvas>
```

With:

```html
<div id="character-canvas"></div>
```

This matches the current `appendChild(app.canvas)` logic.

- [ ] **Step 2: Make `src/main.ts` delegate chat requests to `ChatClient`**

Import the client:

```ts
import { ChatClient } from './chat-client';

const chatClient = new ChatClient({
  apiEndpoint: 'http://localhost:8080/chat',
});
```

Replace the placeholder `setTimeout()` response path inside `sendMessage()` with:

```ts
addMessage('user', text);
input.value = '';

try {
  const response = await chatClient.sendAndReturn(text);
  addMessage('assistant', response.content);
} catch (error) {
  addMessage('assistant', '抱歉，我遇到了一些问题，请稍后再试。');
}
```

- [ ] **Step 3: Extend `src/chat-client.ts` with a direct response API**

Add a method like this:

```ts
public async sendAndReturn(content: string): Promise<ChatMessage> {
  const userMsg: ChatMessage = {
    role: 'user',
    content,
    timestamp: new Date().toISOString(),
  };
  this.messages.push(userMsg);

  const response = await this.callAI(content);
  return response;
}
```

Keep `send()` only if you still need listener-style usage. If not used anywhere, remove it to keep one message path.

- [ ] **Step 4: Remove duplicate inline HTML handlers if TypeScript already binds events**

In `index.html`, remove:

```html
onclick="toggleChat()"
onclick="sendMessage()"
onclick="switchCharacter('kei')"
```

Then bind those actions in `src/main.ts` with `addEventListener()`. This prevents two sources of UI behavior.

- [ ] **Step 5: Build the frontend**

Run: `npm run build`

Workdir: `E:/python/desktop-ai-companion/tauri-app`

Expected: successful Vite build with no TypeScript import or DOM usage errors.

### Task 4: Reduce Rust IPC To Window-Level Commands Only

**Files:**
- Modify: `E:/python/desktop-ai-companion/tauri-app/src-tauri/src/main.rs`

- [ ] **Step 1: Remove duplicated config/chat business commands from Rust**

Delete these commands and related structs if the frontend no longer uses them:

```rust
fn get_config() -> Result<AppConfig, String>
fn save_config(config: AppConfig) -> Result<(), String>
async fn chat(message: String, context: Vec<ChatMessage>) -> Result<ChatResponse, String>
```

Keep only shell/window integration commands.

- [ ] **Step 2: Replace hard process exit with app-handle based shutdown**

Refactor toward this shape:

```rust
#[tauri::command]
fn quit_app(app: tauri::AppHandle) {
    app.exit(0);
}
```

- [ ] **Step 3: Keep the invoke handler minimal**

Target shape:

```rust
.invoke_handler(tauri::generate_handler![quit_app])
```

- [ ] **Step 4: Validate the Tauri Rust build**

Run: `cargo check`

Workdir: `E:/python/desktop-ai-companion/tauri-app/src-tauri`

Expected: successful compile check.

### Task 5: Demote PyQt From Mainline Without Deleting It Yet

**Files:**
- Modify: `E:/python/desktop-ai-companion/run.py`
- Modify: `E:/python/desktop-ai-companion/README.md`

- [ ] **Step 1: Stop advertising `run.py` as the main startup path**

Replace Python-first startup instructions with:

```md
## 开发启动

### 1. 启动后端
cd backend
python server.py

### 2. 启动桌面前端
cd tauri-app
npm run tauri:dev
```

- [ ] **Step 2: Add a prototype note to `run.py` if it stays in the repo**

Update the file docstring to clarify status:

```python
"""
Legacy PyQt prototype launcher.
Not part of the current production startup path.
"""
```

- [ ] **Step 3: Verify no top-level docs still claim `python app/main.py` is the primary way to run the product**

Run: `rg -n "python app/main.py|run.py|PyQt6" "E:/python/desktop-ai-companion/README.md" "E:/python/desktop-ai-companion/README_NEW_ARCH.md" "E:/python/desktop-ai-companion/ARCHITECTURE.md"`

Expected: only prototype/deprecation references remain.

## Rollout Order

1. Task 1 first, so contributors stop following conflicting docs.
2. Task 2 second, because backend persistence is the system-of-record change.
3. Task 3 third, to connect the frontend to the real backend.
4. Task 4 fourth, to remove duplicated business logic from Rust.
5. Task 5 last, to finish repository-level cleanup.

## Verification Checklist

- `pytest E:/python/desktop-ai-companion/tests/test_backend_api.py E:/python/desktop-ai-companion/tests/test_config_paths.py -v`
- `python -m compileall E:/python/desktop-ai-companion/app E:/python/desktop-ai-companion/backend`
- `npm run build` in `E:/python/desktop-ai-companion/tauri-app`
- `cargo check` in `E:/python/desktop-ai-companion/tauri-app/src-tauri`
- Manual smoke test:

```text
1. Start FastAPI on :8080
2. Start Tauri app
3. Click character to open chat
4. Send one message
5. Refresh or reopen app
6. Confirm /history returns the saved messages
7. Change config and confirm /config returns persisted values
```
