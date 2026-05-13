# Hiyori Action Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Disable Hiyori's current region-triggered actions while keeping click feedback, logs, and non-Hiyori character behavior unchanged.

**Architecture:** Make the smallest possible runtime change in the region reaction handlers inside `tauri-app/src/main.ts` so Hiyori clicks still flow through the existing region detection and focus feedback but no longer dispatch action animations. Update the lightweight Playwright regression script so it asserts the new no-action behavior for Hiyori clicks.

**Tech Stack:** TypeScript, Tauri, Vite, Playwright for Python

---

### Task 1: Remove Hiyori Region Action Dispatch

**Files:**
- Modify: `tauri-app/src/main.ts:919-995`
- Test: `tools/test_single_click_action.py`

- [ ] **Step 1: Write the failing test**

Update `tools/test_single_click_action.py` so it still clicks Hiyori's chest region and verifies the region click log exists, but now asserts that no Hiyori action dispatch log is present.

```python
from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        logs: list[str] = []
        page.on("console", lambda msg: logs.append(msg.text))
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")
        page.mouse.click(200, 180)
        page.wait_for_timeout(400)
        action_logs = [line for line in logs if "ACTION:" in line or "点击区域" in line]
        print(action_logs)
        browser.close()

    assert any("点击区域: chest" in line for line in action_logs)
    assert any("ACTION: region-chest for hiyori" in line for line in action_logs)
    assert not any("hiyori-chinRest-module" in line for line in action_logs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_single_click_action.py`
Expected: FAIL because the current code still emits `hiyori-chinRest-module` for Hiyori chest clicks.

- [ ] **Step 3: Write minimal implementation**

Edit the Hiyori branches in `tauri-app/src/main.ts` so they no longer call `triggerHiyoriAction(...)`, while keeping the rest of each region handler intact.

```ts
async function triggerFaceReaction() {
    console.log(`ACTION: region-face for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const changed = await playExpressionByCandidates(['Surprised.exp3.json', 'Smile.exp3.json', 'f01.exp3.json']);
        if (!changed) {
            await playMotionByCandidates(['Tap', 'Idle']);
        }
    } else if (isHiyoriCharacter()) {
        // Intentionally keep click feedback only.
    } else {
        await playMotionByCandidates(['']);
        setLipSyncValue(0.35);
        window.setTimeout(() => setLipSyncValue(0), 260);
    }
    animateFocus(app.screen.width * 0.44, app.screen.height * 0.2, 1600);
}

async function triggerChestReaction() {
    console.log(`ACTION: region-chest for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const changed = await playExpressionByCandidates(['Blushing.exp3.json', 'Surprised.exp3.json', 'Smile.exp3.json']);
        if (!changed) {
            await playMotionByCandidates(['Tap']);
        }
    } else if (isHiyoriCharacter()) {
        // Intentionally keep click feedback only.
    } else {
        await playMotionByCandidates(['']);
    }
    animateFocus(app.screen.width * 0.5, app.screen.height * 0.34, 1400);
}

async function triggerArmsReaction() {
    console.log(`ACTION: region-arms for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const moved = await playMotionByCandidates(['Flick', 'Tap']);
        if (!moved) {
            await playExpressionByCandidates(['Smile.exp3.json', 'Normal.exp3.json']);
        }
    } else if (isHiyoriCharacter()) {
        // Intentionally keep click feedback only.
    } else {
        await playMotionByCandidates(['']);
    }
    animateFocus(app.screen.width * 0.56, app.screen.height * 0.36, 1200);
}

async function triggerBellyReaction() {
    console.log(`ACTION: region-belly for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const changed = await playExpressionByCandidates(['Sad.exp3.json', 'Angry.exp3.json', 'Blushing.exp3.json']);
        if (!changed) {
            await playMotionByCandidates(['Tap']);
        }
    } else if (isHiyoriCharacter()) {
        // Intentionally keep click feedback only.
    } else {
        await playMotionByCandidates(['']);
        setLipSyncValue(0.55);
        window.setTimeout(() => setLipSyncValue(0), 320);
    }
    animateFocus(app.screen.width * 0.5, app.screen.height * 0.48, 1400);
}

async function triggerLegsReaction() {
    console.log(`ACTION: region-legs for ${currentCharacter}`);
    if (currentCharacter === 'chitose') {
        const moved = await playMotionByCandidates(['Idle', 'Tap']);
        if (!moved) {
            await playExpressionByCandidates(['Normal.exp3.json', 'Smile.exp3.json']);
        }
    } else if (isHiyoriCharacter()) {
        // Intentionally keep click feedback only.
    } else {
        await playMotionByCandidates(['']);
    }
    animateFocus(app.screen.width * 0.5, app.screen.height * 0.62, 1000);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tools/test_single_click_action.py`
Expected: no assertion failures, and the printed logs still include the chest click region log but no Hiyori action dispatch log.

- [ ] **Step 5: Run a broader regression check**

Run: `python tools/test_hiyori_actions.py`
Expected: printed output still shows region click logs for Hiyori interactions, without Hiyori action dispatch logs for the clicked regions.

- [ ] **Step 6: Commit**

```bash
git add tauri-app/src/main.ts tools/test_single_click_action.py docs/superpowers/specs/2026-05-13-hiyori-action-reduction-design.md docs/superpowers/plans/2026-05-13-hiyori-action-reduction.md
git commit -m "fix: disable hiyori region actions"
```
