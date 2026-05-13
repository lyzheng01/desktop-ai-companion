# P0 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a stable P0 desktop companion that can stay on the desktop, open chat reliably, restore history, expose basic desktop controls, and show clear idle/listening/thinking/talking states.

**Architecture:** Keep the current Tauri + TypeScript + FastAPI structure, but close the missing MVP loops instead of broadening features. The work centers on five vertical slices: unified settings, restored history and chat state, explicit companion states, tray/window controls, and minimal user-facing memory. Avoid new expressive behavior systems until the basic desktop product loop is stable.

**Tech Stack:** Tauri v2, TypeScript, PixiJS, pixi-live2d-display, FastAPI, SQLite, JSON config, Playwright for Python, pytest

---

## File Structure Lock-In

**Modify:**
- `app/config.py`
  Responsible for the canonical stored desktop companion settings model.
- `backend/server.py`
  Responsible for exposing the front-end-facing config, chat, history, and memory APIs.
- `app/db.py`
  Responsible for SQLite-backed chat history and memory access.
- `tauri-app/src/main.ts`
  Responsible for current UI orchestration, character state transitions, chat send flow, history restore, and window interactions.
- `tauri-app/src/chat-client.ts`
  Responsible for chat API calls and front-end chat/history helpers.
- `tauri-app/src-tauri/src/main.rs`
  Responsible for native desktop commands and system tray behavior.
- `tauri-app/src-tauri/tauri.conf.json`
  Responsible for window defaults and Tauri capability alignment.
- `tauri-app/index.html`
  Responsible for chat/settings/tray-recoverable UI controls already rendered in the webview.

**Create:**
- `tests/test_memory_api.py`
  Backend regression tests for minimal memory CRUD.
- `tools/test_chat_history_restore.py`
  Browser-level regression test for restored history in the chat window.
- `tools/test_companion_state_logs.py`
  Browser-level regression test for idle/listening/thinking/talking state transitions.

---

### Task 1: Unify P0 Settings Contract

**Files:**
- Modify: `app/config.py:20-56`
- Modify: `backend/server.py:34-47`
- Test: `tests/test_backend_api.py`

- [ ] **Step 1: Write the failing test**

Extend `tests/test_backend_api.py` to assert that the backend config API round-trips the P0-critical settings fields that already exist in storage but are not fully exposed yet.

```python
def test_config_round_trip_includes_p0_desktop_fields(client):
    payload = {
        "user_nickname": "小伙伴",
        "user_display_name": "你",
        "character_type": "hiyori_pro_zh",
        "character_name": "小艾",
        "personality": ["温柔"],
        "interaction_mode": "work",
        "proactive_mode": "quiet",
        "chat_model": "gpt",
        "dnd_enabled": True,
        "dnd_start": "22:00",
        "dnd_end": "08:00",
        "window_x": 160,
        "window_y": 240,
        "window_scale": 0.92,
        "character_scales": {"hiyori_pro_zh": 0.92},
        "auto_start": False,
        "always_on_top": True,
        "click_through": False,
        "opacity": 1.0,
    }

    response = client.post("/config", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["dnd_enabled"] is True
    assert data["dnd_start"] == "22:00"
    assert data["dnd_end"] == "08:00"
    assert data["auto_start"] is False
    assert data["always_on_top"] is True
    assert data["click_through"] is False
    assert data["opacity"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backend_api.py -v`
Expected: FAIL because the current backend `Config` model does not expose the full P0 desktop settings contract.

- [ ] **Step 3: Write minimal implementation**

Add the missing P0 fields to `AppConfig` and the backend `Config` API model, then map them in both `/config` handlers.

```python
@dataclass
class AppConfig:
    user_nickname: str = "小伙伴"
    user_display_name: str = "你"
    character_type: str = "hiyori_pro_zh"
    character_name: str = "小艾"
    personality: list[str] = field(default_factory=lambda: ["温柔"])
    interaction_mode: str = "work"
    proactive_mode: str = "quiet"
    chat_model: str = "gpt"
    dnd_enabled: bool = False
    dnd_start: str = "22:00"
    dnd_end: str = "08:00"
    window_x: int = 100
    window_y: int = 100
    window_scale: float = 1.0
    character_scales: dict[str, float] = field(default_factory=dict)
    auto_start: bool = False
    always_on_top: bool = True
    click_through: bool = False
    opacity: float = 1.0
```

```python
class Config(BaseModel):
    user_nickname: str = "小伙伴"
    user_display_name: str = "你"
    character_type: str = "hiyori_pro_zh"
    character_name: str = "小艾"
    personality: list[str] = Field(default_factory=lambda: ["温柔"])
    interaction_mode: str = "work"
    proactive_mode: str = "quiet"
    chat_model: str = "gpt"
    dnd_enabled: bool = False
    dnd_start: str = "22:00"
    dnd_end: str = "08:00"
    window_x: int = 100
    window_y: int = 100
    window_scale: float = 1.0
    character_scales: dict[str, float] = Field(default_factory=dict)
    auto_start: bool = False
    always_on_top: bool = True
    click_through: bool = False
    opacity: float = 1.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backend_api.py -v`
Expected: PASS, including the new config round-trip assertion.

- [ ] **Step 5: Commit**

```bash
git add app/config.py backend/server.py tests/test_backend_api.py
git commit -m "fix: unify p0 companion settings contract"
```

### Task 2: Restore Chat History in the Front End

**Files:**
- Modify: `tauri-app/src/chat-client.ts:17-133`
- Modify: `tauri-app/src/main.ts:1207-1330`
- Test: `tools/test_chat_history_restore.py`

- [ ] **Step 1: Write the failing test**

Create `tools/test_chat_history_restore.py` to seed history via the backend and verify that opening chat restores previous messages.

```python
from playwright.sync_api import sync_playwright
import requests


def main() -> None:
    requests.delete("http://127.0.0.1:8080/history", timeout=5)
    requests.post("http://127.0.0.1:8080/chat", json={"message": "第一条", "context": []}, timeout=5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")
        page.dblclick("#character-hit-area")
        page.wait_for_timeout(300)
        text = page.locator("#chat-messages").inner_text()
        browser.close()

    assert "第一条" in text


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_chat_history_restore.py`
Expected: FAIL because the chat window currently does not load `/history` on open or startup.

- [ ] **Step 3: Write minimal implementation**

Add a front-end history loader and use it when opening chat for the first time.

```ts
export class ChatClient {
    // ...existing fields...

    public async loadHistory(limit = 20): Promise<ChatMessage[]> {
        const response = await fetch(`http://localhost:8080/history?limit=${limit}`);
        if (!response.ok) {
            throw new Error(`History request failed: ${response.status}`);
        }
        const data = await response.json() as ChatMessage[];
        this.messages = data;
        return data;
    }
}
```

```ts
let chatHistoryLoaded = false;

async function ensureChatHistoryLoaded() {
    if (chatHistoryLoaded) return;

    const messages = await chatClient.loadHistory(50);
    const container = document.getElementById('chat-messages');
    if (container) {
        container.innerHTML = '';
    }
    messages.forEach((message) => addMessage(message.role, message.content));
    chatHistoryLoaded = true;
}

async function openChat() {
    const chatWindow = document.getElementById('chat-window');
    if (chatWindow) {
        chatWindow.classList.add('visible');
        chatWindowVisible = true;
    }
    await ensureChatHistoryLoaded();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_chat_history_restore.py`
Expected: PASS, and the restored seeded message appears in the chat window.

- [ ] **Step 5: Commit**

```bash
git add tauri-app/src/chat-client.ts tauri-app/src/main.ts tools/test_chat_history_restore.py
git commit -m "feat: restore chat history in desktop ui"
```

### Task 3: Add Explicit Listening, Thinking, and Talking UI States

**Files:**
- Modify: `tauri-app/src/main.ts:57-62,830-888,1292-1312`
- Modify: `tauri-app/index.html:155-170,334-405`
- Test: `tools/test_companion_state_logs.py`

- [ ] **Step 1: Write the failing test**

Create `tools/test_companion_state_logs.py` to verify the front end logs or exposes transitions for listening, thinking, and talking during one message send.

```python
from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        logs: list[str] = []
        page.on("console", lambda msg: logs.append(msg.text))
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")
        page.dblclick("#character-hit-area")
        page.fill("#chat-input", "你好")
        page.click("#send-btn")
        page.wait_for_timeout(1200)
        browser.close()

    assert any("STATE: listening" in line for line in logs)
    assert any("STATE: thinking" in line for line in logs)
    assert any("STATE: talking" in line for line in logs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_companion_state_logs.py`
Expected: FAIL because the front end has no explicit thinking/listening state transitions yet.

- [ ] **Step 3: Write minimal implementation**

Add a simple explicit state marker and use it in the send lifecycle.

```ts
type CompanionState = 'idle' | 'listening' | 'thinking' | 'talking';

let companionState: CompanionState = 'idle';

function setCompanionState(next: CompanionState) {
    companionState = next;
    console.log(`STATE: ${next}`);
    document.body.dataset.companionState = next;
}

async function sendMessage() {
    const input = document.getElementById('chat-input') as HTMLTextAreaElement;
    if (!input) return;

    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    addMessage('user', text);
    setCompanionState('listening');
    void triggerCharacterAttention();
    setCompanionState('thinking');

    try {
        const response = await chatClient.sendAndReturn(text);
        addMessage('assistant', response.content);
        setCompanionState('talking');
        startTalkingAnimation(response.content);
    } catch (error) {
        console.error('❌ 发送消息失败:', error);
        addMessage('assistant', '抱歉，我遇到了一些问题，请稍后再试。');
        setCompanionState('idle');
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_companion_state_logs.py`
Expected: PASS, with logs showing `listening`, `thinking`, and `talking` in order.

- [ ] **Step 5: Run focused regression**

Run: `python tools/test_single_click_action.py`
Expected: PASS, proving the state work did not reintroduce removed Hiyori action playback.

- [ ] **Step 6: Commit**

```bash
git add tauri-app/src/main.ts tauri-app/index.html tools/test_companion_state_logs.py tools/test_single_click_action.py
git commit -m "feat: add explicit p0 companion states"
```

### Task 4: Add Native Tray and Recoverable Hide/Show Flow

**Files:**
- Modify: `tauri-app/src-tauri/src/main.rs:1-15`
- Modify: `tauri-app/src/main.ts:1332-1411`
- Test: `tauri-app/src-tauri/tauri.conf.json`

- [ ] **Step 1: Write the failing test**

Because the tray is native, use a narrow behavioral check in Rust-free config and front-end command wiring: add a browser-facing assertion that hide no longer makes the app unrecoverable because a native show command exists.

```ts
const showButton = menu.querySelector<HTMLElement>('[data-action="show"]');
showButton?.addEventListener('click', showMainWindow);
```

Add a temporary console assertion path:

```ts
function showMainWindow() {
    console.log('WINDOW: show');
    invoke('show_main_window');
}
```

- [ ] **Step 2: Run verification to confirm it fails conceptually**

Run: `cargo check`
Workdir: `tauri-app/src-tauri`
Expected: FAIL after wiring `show_main_window` from the front end, because the Rust command does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add native show/hide commands and create a system tray with show and quit entries.

```rust
#[tauri::command]
fn hide_main_window(window: tauri::WebviewWindow) {
    let _ = window.hide();
}

#[tauri::command]
fn show_main_window(window: tauri::WebviewWindow) {
    let _ = window.show();
    let _ = window.set_focus();
}
```

Use Tauri tray APIs to add:

- `Show Companion`
- `Quit`

and wire those menu items to show the main window or exit the app.

- [ ] **Step 4: Run verification to confirm it passes**

Run: `cargo check`
Workdir: `tauri-app/src-tauri`
Expected: PASS, with the new tray and command handlers compiling successfully.

- [ ] **Step 5: Manual smoke test**

Run: `npm run tauri:dev`
Workdir: `tauri-app`
Expected: the app can be hidden and restored from the tray without disappearing permanently.

- [ ] **Step 6: Commit**

```bash
git add tauri-app/src-tauri/src/main.rs tauri-app/src/main.ts tauri-app/src-tauri/tauri.conf.json
git commit -m "feat: add recoverable tray workflow"
```

### Task 5: Persist and Restore Window Position

**Files:**
- Modify: `tauri-app/src/main.ts:1143-1205,1450-1499`
- Modify: `backend/server.py:85-134`
- Test: `tests/test_config_paths.py`

- [ ] **Step 1: Write the failing test**

Add a backend config persistence assertion that `window_x` and `window_y` survive round-trip updates used by the front end.

```python
def test_window_position_persists_in_config(client):
    payload = client.get("/config").json()
    payload["window_x"] = 333
    payload["window_y"] = 444

    response = client.post("/config", json=payload)
    assert response.status_code == 200

    restored = client.get("/config").json()
    assert restored["window_x"] == 333
    assert restored["window_y"] == 444
```

- [ ] **Step 2: Run test to verify it fails if needed**

Run: `pytest tests/test_backend_api.py -v`
Expected: if already green, treat this as proof the storage contract exists and continue to the front-end implementation. If it fails, fix the backend mapping before moving on.

- [ ] **Step 3: Write minimal implementation**

Save position after drag completes and restore it on startup.

```ts
hitArea.addEventListener('pointerup', async () => {
    if (pointerDown && dragStarted) {
        const position = await getCurrentWindow().outerPosition();
        appSettings.window_x = position.x;
        appSettings.window_y = position.y;
        void saveAppSettings();
    }
    // ...existing click logic...
});
```

```ts
async function restoreWindowPosition() {
    await getCurrentWindow().setPosition(
        new PhysicalPosition(appSettings.window_x, appSettings.window_y),
    );
}

window.addEventListener('DOMContentLoaded', () => {
    initPixi().then(() => restoreWindowPosition());
    // ...existing bindings...
});
```

- [ ] **Step 4: Run verification to confirm it passes**

Run: `pytest tests/test_backend_api.py -v`
Expected: PASS for the config persistence assertion.

- [ ] **Step 5: Manual smoke test**

Run: `npm run tauri:dev`
Workdir: `tauri-app`
Expected: after moving the character window and relaunching, the window reopens at the stored position.

- [ ] **Step 6: Commit**

```bash
git add tauri-app/src/main.ts tests/test_backend_api.py
git commit -m "feat: persist companion window position"
```

### Task 6: Ship Minimal User-Facing Memory CRUD

**Files:**
- Modify: `app/db.py:157-211`
- Modify: `backend/server.py:18-19,145-169`
- Test: `tests/test_memory_api.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_memory_api.py` to verify save, list, and delete behavior for a minimal memory API.

```python
def test_memory_crud(client):
    created = client.post("/memories", json={
        "content": "用户喜欢安静模式",
        "category": "preference",
        "importance": 2,
    })
    assert created.status_code == 200

    listed = client.get("/memories")
    assert listed.status_code == 200
    memories = listed.json()
    assert any(item["content"] == "用户喜欢安静模式" for item in memories)

    memory_id = next(item["id"] for item in memories if item["content"] == "用户喜欢安静模式")
    deleted = client.delete(f"/memories/{memory_id}")
    assert deleted.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory_api.py -v`
Expected: FAIL because the backend has database helpers but no memory API endpoints yet.

- [ ] **Step 3: Write minimal implementation**

Expose memory CRUD in the backend with a minimal request model.

```python
class MemoryRequest(BaseModel):
    content: str
    category: str = "fact"
    importance: int = 1


@app.get("/memories")
async def list_memories():
    return get_memories()


@app.post("/memories")
async def create_memory(request: MemoryRequest):
    save_memory(request.content, request.category, request.importance)
    return {"status": "ok"}


@app.delete("/memories/{memory_id}")
async def remove_memory(memory_id: int):
    delete_memory(memory_id)
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory_api.py -v`
Expected: PASS for memory create/list/delete behavior.

- [ ] **Step 5: Commit**

```bash
git add app/db.py backend/server.py tests/test_memory_api.py
git commit -m "feat: add minimal memory api"
```

### Task 7: Add P0 Settings for DND and Basic Desktop Controls

**Files:**
- Modify: `tauri-app/index.html:472-533`
- Modify: `tauri-app/src/main.ts:208-283,1225-1240`
- Test: `tools/test_settings_panel.py`

- [ ] **Step 1: Write the failing test**

Extend `tools/test_settings_panel.py` so it opens settings and verifies the presence of P0-critical controls for DND, always-on-top, startup, click-through, opacity, and reset position.

```python
assert page.locator('#dnd-enabled-input').count() == 1
assert page.locator('#always-on-top-input').count() == 1
assert page.locator('#auto-start-input').count() == 1
assert page.locator('#click-through-input').count() == 1
assert page.locator('#opacity-slider').count() == 1
assert page.locator('#reset-position-btn').count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_settings_panel.py`
Expected: FAIL because those controls do not exist in the current settings panel.

- [ ] **Step 3: Write minimal implementation**

Add the controls to `index.html` and bind them in `main.ts` using the unified settings contract from Task 1.

```html
<label><input id="dnd-enabled-input" type="checkbox"> 免打扰</label>
<label><input id="always-on-top-input" type="checkbox"> 窗口置顶</label>
<label><input id="auto-start-input" type="checkbox"> 开机启动</label>
<label><input id="click-through-input" type="checkbox"> 点击穿透</label>
<label for="opacity-slider">透明度</label>
<input id="opacity-slider" type="range" min="0.4" max="1" step="0.05" value="1">
<button id="reset-position-btn">重置位置</button>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_settings_panel.py`
Expected: PASS with the new controls visible in the settings panel.

- [ ] **Step 5: Commit**

```bash
git add tauri-app/index.html tauri-app/src/main.ts tools/test_settings_panel.py
git commit -m "feat: add p0 desktop settings controls"
```

### Task 8: Final P0 Verification Sweep

**Files:**
- Verify only

- [ ] **Step 1: Run backend test suite**

Run: `pytest tests/test_backend_api.py tests/test_memory_api.py -v`
Expected: PASS with 0 failures.

- [ ] **Step 2: Run browser regression scripts**

Run: `python tools/test_single_click_action.py`
Expected: PASS.

Run: `python tools/test_hiyori_actions.py`
Expected: PASS.

Run: `python tools/test_chat_history_restore.py`
Expected: PASS.

Run: `python tools/test_companion_state_logs.py`
Expected: PASS.

Run: `python tools/test_settings_panel.py`
Expected: PASS.

- [ ] **Step 3: Run Tauri compile verification**

Run: `cargo check`
Workdir: `tauri-app/src-tauri`
Expected: PASS.

- [ ] **Step 4: Manual acceptance check**

Run: `npm run tauri:dev`
Workdir: `tauri-app`
Expected:

- character appears with transparent desktop window,
- window can be moved and relaunched in the same position,
- tray can hide and restore the app,
- chat opens and restores previous messages,
- sending a message visibly transitions through listening, thinking, and talking,
- settings expose the P0 desktop controls.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "feat: complete p0 desktop companion loop"
```
