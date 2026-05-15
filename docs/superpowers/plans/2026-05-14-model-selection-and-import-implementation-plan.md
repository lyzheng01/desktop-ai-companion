# Model Selection And Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the long right-click model list with a dedicated model-selection panel, then add a clean import path for already-unzipped external model folders without making the app depend on `Downloads` as a runtime source.

**Architecture:** Keep model switching lightweight by splitting it into two independent tasks. First, move built-in model browsing into a dedicated selection panel and keep the context menu short. Second, add a small imported-model registry plus folder-based import flow that copies validated external models into app-managed storage before they become selectable.

**Tech Stack:** TypeScript, Vite, Tauri v2, FastAPI, SQLite, pytest, Playwright for Python

---

## File Structure Lock-In

**Modify:**
- `tauri-app/index.html`
  Add the model selection panel UI and remove direct model listing from the context menu.
- `tauri-app/src/main.ts`
  Add model panel orchestration, built-in model list rendering, switching, and imported-model UI wiring.
- `backend/server.py`
  Add model-registry endpoints for imported models.
- `app/db.py`
  Add imported-model registry persistence.
- `tauri-app/src/chat-client.ts`
  Add frontend helpers for model registry and import APIs.

**Create:**
- `tests/test_model_registry_api.py`
  Backend regression for imported-model registry CRUD and validation.
- `tools/test_model_selection_panel.py`
  Browser regression for built-in model panel rendering and switching.
- `tools/test_model_import_flow.py`
  Browser or backend-assisted regression for importing an already-unzipped model folder.

---

### Task 1: Replace Context Menu Model List With A Model Selection Panel

**Files:**
- Modify: `tauri-app/index.html`
- Modify: `tauri-app/src/main.ts`
- Create: `tools/test_model_selection_panel.py`

- [ ] **Step 1: Write the failing browser test**

Create `tools/test_model_selection_panel.py` with a flow that verifies:

- right-click menu shows `选择模型`,
- the model panel opens,
- built-in models appear there,
- switching updates the current model summary.

Use this shape:

```python
from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 420, "height": 760})
        page.goto("http://127.0.0.1:1420", wait_until="domcontentloaded")
        page.wait_for_selector("#character-hit-area", timeout=5000)
        page.click("#character-hit-area", button="right")
        page.wait_for_selector('#context-menu.visible', timeout=3000)
        assert page.locator('#context-menu [data-action="model-picker"]').count() == 1
        browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_model_selection_panel.py`
Expected: FAIL because the current menu still lists models directly and has no dedicated selection action.

- [ ] **Step 3: Replace the context menu model section**

In `tauri-app/index.html`, replace the direct model buttons in `#context-menu` with:

```html
<button data-action="model-picker">🗂 选择模型</button>
```

Keep hide, settings, and quit.

- [ ] **Step 4: Add a dedicated model panel**

In `tauri-app/index.html`, add a new panel:

```html
<div id="model-panel">
  <div class="settings-header">
    <h3>选择模型</h3>
    <button class="model-close-btn">×</button>
  </div>
  <div class="settings-body">
    <div class="settings-item">
      <strong>当前模型</strong>
      <div id="active-model-summary"></div>
    </div>
    <div class="settings-item">
      <strong>内置模型</strong>
      <div id="builtin-model-list"></div>
    </div>
    <div class="settings-item">
      <strong>导入模型</strong>
      <div id="imported-model-list"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 5: Add panel orchestration in `main.ts`**

Add:

```ts
function openModelPanel() { ... }
function closeModelPanel() { ... }
function renderBuiltInModelList() { ... }
```

Each built-in row should show:

- model name
- `当前使用中` badge if active
- switch button if inactive

- [ ] **Step 6: Add model-picker action binding**

Update context-menu action binding in `main.ts` so `data-action="model-picker"` opens the panel instead of switching directly.

- [ ] **Step 7: Make built-in switching update summary and active model**

After switching a built-in model:

- update `currentCharacter`,
- reload the Live2D model,
- refresh `active-model-summary`,
- refresh the built-in list state.

- [ ] **Step 8: Run browser test to verify it passes**

Run: `python tools/test_model_selection_panel.py`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add tauri-app/index.html tauri-app/src/main.ts tools/test_model_selection_panel.py
git commit -m "feat: add dedicated model selection panel"
```

---

### Task 2: Add Imported Model Registry Persistence

**Files:**
- Modify: `app/db.py`
- Create: `tests/test_model_registry_api.py`

- [ ] **Step 1: Write the failing registry test**

Create `tests/test_model_registry_api.py` with:

```python
from app.db import create_imported_model, list_imported_models


def test_create_and_list_imported_model_entry():
    create_imported_model(
        name="Shizuku Imported",
        model_path="models/imported/shizuku/runtime/shizuku.model3.json",
        source="imported",
    )

    items = list_imported_models()
    assert any(item["name"] == "Shizuku Imported" for item in items)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_model_registry_api.py -q`
Expected: FAIL because imported-model registry helpers do not exist yet.

- [ ] **Step 3: Add registry table and helpers**

In `app/db.py`, add a small `imported_models` table and helpers:

```python
def create_imported_model(name: str, model_path: str, source: str = "imported") -> int:
    ...

def list_imported_models() -> List[Dict]:
    ...
```

Minimum table fields:

- `id`
- `name`
- `model_path`
- `source`
- `is_active`
- `created_at`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_model_registry_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_model_registry_api.py
git commit -m "feat: add imported model registry persistence"
```

---

### Task 3: Add Backend Imported Model API

**Files:**
- Modify: `backend/server.py`
- Modify: `tests/test_model_registry_api.py`

- [ ] **Step 1: Extend the failing API test**

Add API-level assertions:

```python
from fastapi.testclient import TestClient
from backend.server import app


client = TestClient(app)


def test_imported_model_registry_api_list():
    response = client.get("/models/imported")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_model_registry_api.py -q`
Expected: FAIL because `/models/imported` route does not exist.

- [ ] **Step 3: Add imported model API route**

In `backend/server.py`, add:

```python
@app.get("/models/imported")
async def get_imported_models():
    return list_imported_models()
```

Do not add folder import yet in this task.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_model_registry_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/server.py tests/test_model_registry_api.py
git commit -m "feat: add imported model registry api"
```

---

### Task 4: Add Frontend Imported Model Listing

**Files:**
- Modify: `tauri-app/src/chat-client.ts`
- Modify: `tauri-app/src/main.ts`
- Modify: `tools/test_model_selection_panel.py`

- [ ] **Step 1: Extend failing browser expectations**

Make the browser test also expect an imported-model section in the panel.

- [ ] **Step 2: Add chat-client helper**

In `tauri-app/src/chat-client.ts`, add:

```ts
export interface ImportedModelItem {
    id: number;
    name: string;
    model_path: string;
    source: string;
    is_active: boolean;
}

public async loadImportedModels(): Promise<ImportedModelItem[]> { ... }
```

- [ ] **Step 3: Add imported-model rendering**

In `tauri-app/src/main.ts`, add:

```ts
async function refreshImportedModelList() { ... }
function renderImportedModelList(models: ImportedModelItem[]) { ... }
```

For now, imported models can be shown as read-only if no imported entries exist.

- [ ] **Step 4: Open model panel with both lists refreshed**

When opening the model panel, refresh:

- active model summary
- built-in model list
- imported model list

- [ ] **Step 5: Re-run browser test**

Run: `python tools/test_model_selection_panel.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tauri-app/src/chat-client.ts tauri-app/src/main.ts tools/test_model_selection_panel.py
git commit -m "feat: show imported models in selection panel"
```

---

### Task 5: Add Already-Unzipped Folder Import Flow

**Files:**
- Modify: `backend/server.py`
- Modify: `tauri-app/index.html`
- Modify: `tauri-app/src/chat-client.ts`
- Modify: `tauri-app/src/main.ts`
- Create: `tools/test_model_import_flow.py`

- [ ] **Step 1: Write the failing import flow test**

Create `tools/test_model_import_flow.py` that uses one already-unzipped sample folder and verifies the app can register it.

The first test can use a development-local known path, for example:

```python
KNOWN_MODEL = r"C:\Users\lenovo\Downloads\shizuku\shizuku\runtime\shizuku.model3.json"
```

Expected flow:

- submit import request
- backend validates path exists
- backend copies to managed storage
- imported registry now includes `Shizuku Imported`

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_model_import_flow.py`
Expected: FAIL because import route and copy flow do not exist.

- [ ] **Step 3: Add backend import endpoint**

In `backend/server.py`, add a route like:

```python
class ImportedModelRequest(BaseModel):
    model_path: str
    name: str


@app.post("/models/imported")
async def import_model(payload: ImportedModelRequest):
    ...
```

Behavior:

- verify the source `model3.json` exists,
- copy the containing model folder into a managed app-side model library,
- register the copied model path in the imported-model registry,
- reject invalid paths with a clear error.

- [ ] **Step 4: Add a simple import UI entry**

In `tauri-app/index.html`, add a small imported-model action area:

```html
<button id="import-model-btn">导入已解压模型</button>
```

No zip support yet.

- [ ] **Step 5: Wire import flow on the frontend**

In `tauri-app/src/chat-client.ts` and `main.ts`, add:

```ts
public async importModel(payload: { name: string; model_path: string }): Promise<void> { ... }
```

In the panel, the button can trigger a minimal prompt-based flow in development first if necessary, before later improving the UX.

- [ ] **Step 6: Re-run import flow test**

Run: `python tools/test_model_import_flow.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/server.py tauri-app/index.html tauri-app/src/chat-client.ts tauri-app/src/main.ts tools/test_model_import_flow.py
git commit -m "feat: import already-unzipped external models"
```

---

## Final Verification Checklist

- [ ] Run: `python -m pytest tests/test_model_registry_api.py -q`
- [ ] Run: `python tools/test_model_selection_panel.py`
- [ ] Run: `python tools/test_model_import_flow.py`
- [ ] Run: `npm run build` in `tauri-app`
- [ ] Confirm right-click menu no longer lists every built-in model directly.
- [ ] Confirm the model panel shows the current model clearly.
- [ ] Confirm imported models are copied into managed storage before being used.

Expected result: the model experience scales cleanly, right-click stays simple, and external models move through a controlled import path instead of relying on `Downloads` as live runtime storage.
