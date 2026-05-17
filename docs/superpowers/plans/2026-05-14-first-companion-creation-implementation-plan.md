# First Companion Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-run companion creation flow that blocks entry until the user creates a companion, then supports a future VIP-only multi-companion model with one active companion at runtime.

**Architecture:** Keep the current Tauri + TypeScript + FastAPI architecture, but separate app-wide settings from companion identity. Store companion profiles in SQLite, expose a small companion API from the backend, and let the front end decide on startup whether to show the first-run creator or jump straight into the desktop experience.

**Tech Stack:** FastAPI, SQLite, TypeScript, Vite, Tauri v2, pytest, Playwright for Python

---

## File Structure Lock-In

**Modify:**
- `app/db.py`
  Add companion-profile persistence and active-companion helpers.
- `backend/server.py`
  Add companion API models and endpoints, and bind current config/chat identity to the active companion.
- `tauri-app/src/chat-client.ts`
  Add companion API helpers.
- `tauri-app/src/main.ts`
  Add first-run flow orchestration, active-companion loading, and simple VIP gating.
- `tauri-app/index.html`
  Add a first-run creator surface and a simple companion-management entry in settings.
- `tests/test_backend_api.py`
  Extend backend coverage for companion creation and active-companion behavior.

**Create:**
- `tests/test_companion_profiles_api.py`
  Backend regression tests for create/list/activate companion flows.
- `tools/test_first_companion_creation.py`
  Browser-level regression for first-launch companion creation.

---

### Task 1: Add Companion Profile Persistence

**Files:**
- Modify: `app/db.py`
- Create: `tests/test_companion_profiles_api.py`

- [ ] **Step 1: Write the failing persistence test**

Create `tests/test_companion_profiles_api.py` with:

```python
from app.db import create_companion, get_active_companion, list_companions, set_active_companion


def test_create_and_activate_companion_flow():
    first_id = create_companion(
        name="小艾",
        character_type="hiyori_pro_zh",
        personality_tags=["温柔"],
        interaction_mode="work",
        is_active=True,
    )

    second_id = create_companion(
        name="小晴",
        character_type="natori_pro_zh",
        personality_tags=["元气"],
        interaction_mode="daily",
        is_active=False,
    )

    companions = list_companions()
    assert len(companions) == 2
    assert get_active_companion()["id"] == first_id

    set_active_companion(second_id)
    assert get_active_companion()["id"] == second_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_companion_profiles_api.py -q`
Expected: FAIL because the DB layer does not expose companion CRUD helpers yet.

- [ ] **Step 3: Add DB helper functions**

In `app/db.py`, add helper functions around the existing `characters` table:

```python
def create_companion(name: str, character_type: str, personality_tags: list[str], interaction_mode: str, is_active: bool = False) -> int:
    ...

def list_companions() -> List[Dict]:
    ...

def get_active_companion() -> Optional[Dict]:
    ...

def set_active_companion(companion_id: int):
    ...
```

Store `personality_tags` as JSON text in the existing `personality` column.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_companion_profiles_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_companion_profiles_api.py
git commit -m "feat: add companion profile persistence helpers"
```

---

### Task 2: Add Backend Companion API

**Files:**
- Modify: `backend/server.py`
- Modify: `tests/test_backend_api.py`
- Modify: `tests/test_companion_profiles_api.py`

- [ ] **Step 1: Write the failing API test**

Extend `tests/test_companion_profiles_api.py` with:

```python
from fastapi.testclient import TestClient
from backend.server import app


client = TestClient(app)


def test_create_list_and_activate_companions_via_api():
    create_response = client.post(
        "/companions",
        json={
            "name": "小艾",
            "character_type": "hiyori_pro_zh",
            "personality_tags": ["温柔"],
            "interaction_mode": "work",
        },
    )
    assert create_response.status_code == 200

    list_response = client.get("/companions")
    assert list_response.status_code == 200
    companions = list_response.json()
    assert len(companions) == 1
    companion_id = companions[0]["id"]

    activate_response = client.post(f"/companions/{companion_id}/activate")
    assert activate_response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_companion_profiles_api.py -q`
Expected: FAIL because companion API routes do not exist.

- [ ] **Step 3: Add companion API models and endpoints**

In `backend/server.py`, add:

```python
class CompanionCreateRequest(BaseModel):
    name: str
    character_type: str
    personality_tags: list[str] = Field(default_factory=list)
    interaction_mode: str = "work"


@app.get("/companions")
async def get_companions():
    return list_companions()


@app.get("/companions/active")
async def get_active_companion_endpoint():
    return get_active_companion()


@app.post("/companions")
async def create_companion_endpoint(payload: CompanionCreateRequest):
    companion_id = create_companion(...)
    return {"status": "ok", "id": companion_id}


@app.post("/companions/{companion_id}/activate")
async def activate_companion(companion_id: int):
    set_active_companion(companion_id)
    return {"status": "ok"}
```

- [ ] **Step 4: Bind app identity to the active companion**

In `backend/server.py`, when serving `/config`, if an active companion exists, project its `name`, `character_type`, `personality_tags`, and `interaction_mode` into the config response.

This keeps the desktop runtime tied to the active companion.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_companion_profiles_api.py tests/test_backend_api.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/server.py tests/test_backend_api.py tests/test_companion_profiles_api.py
git commit -m "feat: add companion profile api"
```

---

### Task 3: Add First-Run Creator UI

**Files:**
- Modify: `tauri-app/index.html`
- Modify: `tauri-app/src/main.ts`
- Modify: `tauri-app/src/chat-client.ts`
- Create: `tools/test_first_companion_creation.py`

- [ ] **Step 1: Write the failing browser flow test**

Create `tools/test_first_companion_creation.py` with:

```python
import requests
from playwright.sync_api import sync_playwright


def main() -> None:
    requests.delete("http://127.0.0.1:8080/history", timeout=5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = p.chromium.launch(headless=True).new_page()
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 420, "height": 760})
        page.goto("http://127.0.0.1:1420", wait_until="domcontentloaded")
        page.wait_for_selector("#first-run-panel.visible", timeout=5000)
        browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_first_companion_creation.py`
Expected: FAIL because there is no first-run creator surface.

- [ ] **Step 3: Add frontend companion API helpers**

In `tauri-app/src/chat-client.ts`, add helpers:

```ts
export interface CompanionProfile {
    id: number;
    name: string;
    type: string;
    personality_tags: string[];
    interaction_mode: string;
    is_active: boolean;
}

public async loadCompanions(): Promise<CompanionProfile[]> { ... }
public async loadActiveCompanion(): Promise<CompanionProfile | null> { ... }
public async createCompanion(payload: {...}): Promise<number> { ... }
public async activateCompanion(companionId: number): Promise<void> { ... }
```

- [ ] **Step 4: Add a minimal first-run panel in HTML**

In `tauri-app/index.html`, add a full-screen overlay panel:

```html
<div id="first-run-panel">
  <div class="first-run-card">
    <h2>创建你的伙伴</h2>
    <select id="creator-character-select">...</select>
    <input id="creator-name-input" />
    <select id="creator-personality-select" multiple>...</select>
    <select id="creator-mode-select">...</select>
    <button id="creator-submit-btn">完成创建</button>
  </div>
</div>
```

- [ ] **Step 5: Add first-run orchestration logic**

In `tauri-app/src/main.ts`, add:

```ts
let firstRunRequired = false;

async function determineCompanionBootstrapState() {
    const active = await chatClient.loadActiveCompanion();
    firstRunRequired = !active;
    if (active) {
        applyActiveCompanion(active);
    }
}

function showFirstRunPanel() { ... }
function hideFirstRunPanel() { ... }
function bindFirstRunCreator() { ... }
```

On `DOMContentLoaded`, call the bootstrap decision before allowing normal desktop flow.

- [ ] **Step 6: Run browser test to verify it passes**

Run: `python tools/test_first_companion_creation.py`
Expected: PASS, and first-run panel appears when there is no active companion.

- [ ] **Step 7: Commit**

```bash
git add tauri-app/index.html tauri-app/src/main.ts tauri-app/src/chat-client.ts tools/test_first_companion_creation.py
git commit -m "feat: add first-run companion creator"
```

---

### Task 4: Add Free vs VIP Multi-Companion Rules

**Files:**
- Modify: `backend/server.py`
- Modify: `tauri-app/src/main.ts`
- Modify: `tauri-app/index.html`
- Modify: `tests/test_companion_profiles_api.py`

- [ ] **Step 1: Write the failing free-limit test**

Extend `tests/test_companion_profiles_api.py` with:

```python
def test_free_user_cannot_create_second_companion():
    first = client.post("/companions", json={
        "name": "小艾",
        "character_type": "hiyori_pro_zh",
        "personality_tags": ["温柔"],
        "interaction_mode": "work",
    })
    assert first.status_code == 200

    second = client.post("/companions", json={
        "name": "小晴",
        "character_type": "natori_pro_zh",
        "personality_tags": ["元气"],
        "interaction_mode": "daily",
    })
    assert second.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_companion_profiles_api.py -q`
Expected: FAIL because no free-vs-VIP rule exists.

- [ ] **Step 3: Add minimal free-tier rule in backend**

Use a simple placeholder tier rule in config for now:

```python
def is_vip_user() -> bool:
    return False
```

Then block a second companion creation unless VIP is true.

- [ ] **Step 4: Add simple frontend upsell state**

In `tauri-app/src/main.ts` and `index.html`, add a simple message region in settings:

```html
<div id="companion-limit-note">普通用户最多创建 1 个伙伴，更多伙伴为 VIP 功能。</div>
```

Do not add full billing flow.

- [ ] **Step 5: Verify tests pass**

Run: `python -m pytest tests/test_companion_profiles_api.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/server.py tauri-app/src/main.ts tauri-app/index.html tests/test_companion_profiles_api.py
git commit -m "feat: add free-tier companion limit"
```

---

### Task 5: Add Active Companion Switching Surface

**Files:**
- Modify: `tauri-app/index.html`
- Modify: `tauri-app/src/main.ts`
- Modify: `tools/test_first_companion_creation.py`

- [ ] **Step 1: Extend the browser test for later-entry behavior**

Add assertions that after a companion exists:

- later app launch skips the first-run creator,
- settings can show the current companion,
- switching surface exists when multiple companions are present.

- [ ] **Step 2: Add current-companion UI section**

In `tauri-app/index.html`, add:

```html
<div class="settings-item">
  <strong>当前伙伴</strong>
  <div id="active-companion-summary"></div>
  <button id="create-companion-btn">创建新伙伴</button>
  <div id="companion-list"></div>
</div>
```

- [ ] **Step 3: Add switching logic in frontend**

In `tauri-app/src/main.ts`, add:

```ts
async function refreshCompanionList() { ... }
function renderCompanionList(companions: CompanionProfile[]) { ... }
async function switchActiveCompanion(companionId: number) { ... }
```

After switching:

- refresh config,
- refresh current character,
- reload model,
- refresh labels.

- [ ] **Step 4: Run browser verification**

Run: `python tools/test_first_companion_creation.py`
Expected: PASS, with first-run and later-launch behaviors both covered.

- [ ] **Step 5: Commit**

```bash
git add tauri-app/index.html tauri-app/src/main.ts tools/test_first_companion_creation.py
git commit -m "feat: add active companion switching surface"
```

---

## Final Verification Checklist

- [ ] Run: `python -m pytest tests/test_backend_api.py tests/test_companion_profiles_api.py -q`
- [ ] Run: `python tools/test_first_companion_creation.py`
- [ ] Run: `npm run build` in `tauri-app`
- [ ] Confirm first launch requires companion creation when no active companion exists.
- [ ] Confirm later launches skip creation and load the active companion.
- [ ] Confirm free users cannot create a second companion.

Expected result: the product now has emotional ownership on first launch and a lightweight future VIP multi-companion path without becoming a heavy management tool.
