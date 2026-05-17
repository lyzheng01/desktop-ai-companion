# Click Reaction And Bubble Response Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make single-click interaction feel like a lightweight social response by combining attention cues, controlled reaction pools, and short bubble replies, while keeping double-click reserved for opening the chat dialog.

**Architecture:** Layer a click-response dispatcher on top of the current model interaction system instead of rewriting the whole animation stack. Use the existing hit-region detection to bias response pools, add a compact bubble UI anchored to the character, and introduce enough scripted lines to avoid mechanical repetition.

**Tech Stack:** TypeScript, Vite, Tauri v2, existing PixiJS / Live2D front-end, Playwright for Python

---

## File Structure Lock-In

**Modify:**
- `tauri-app/index.html`
  Add the bubble UI surface and any supporting styles.
- `tauri-app/src/main.ts`
  Add bubble state, click-response dispatcher, response pools, region mapping, and double-click separation.

**Create:**
- `tools/test_click_bubble_response.py`
  Browser-level regression for single-click bubble behavior and double-click chat behavior.

---

### Task 1: Add Bubble UI Surface

**Files:**
- Modify: `tauri-app/index.html`
- Create: `tools/test_click_bubble_response.py`

- [ ] **Step 1: Write the failing browser test**

Create `tools/test_click_bubble_response.py` with:

```python
from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 420, "height": 760})
        page.goto("http://127.0.0.1:1420", wait_until="domcontentloaded")
        page.wait_for_selector("#character-hit-area", timeout=5000)
        page.click("#character-hit-area", position={"x": 200, "y": 160})
        page.wait_for_selector("#reaction-bubble.visible", timeout=3000)
        browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_click_bubble_response.py`
Expected: FAIL because no click bubble UI exists yet.

- [ ] **Step 3: Add a bubble element in `index.html`**

Add this near the character container:

```html
<div id="reaction-bubble">
  <div id="reaction-bubble-text"></div>
</div>
```

Add styles so it:

- appears near the head area,
- fades in/out,
- looks like a lightweight speech bubble,
- does not take over the whole chat surface.

- [ ] **Step 4: Run test to verify it still fails for behavior, not missing DOM**

Run: `python tools/test_click_bubble_response.py`
Expected: still FAIL, but now because the bubble never becomes visible on click.

- [ ] **Step 5: Commit**

```bash
git add tauri-app/index.html tools/test_click_bubble_response.py
git commit -m "feat: add reaction bubble ui shell"
```

---

### Task 2: Add Click Response Dispatcher

**Files:**
- Modify: `tauri-app/src/main.ts`
- Modify: `tools/test_click_bubble_response.py`

- [ ] **Step 1: Extend the failing test to lock single vs double click behavior**

Update the browser test so it checks:

- single click shows bubble,
- single click does **not** open chat,
- double click opens chat.

Use this shape:

```python
page.click("#character-hit-area", position={"x": 200, "y": 160})
page.wait_for_selector("#reaction-bubble.visible", timeout=3000)
assert not page.locator("#chat-window").evaluate("el => el.classList.contains('visible')")

page.dblclick("#character-hit-area", position={"x": 200, "y": 160})
page.wait_for_selector("#chat-window.visible", timeout=3000)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tools/test_click_bubble_response.py`
Expected: FAIL because click still only triggers region motion and there is no bubble lifecycle.

- [ ] **Step 3: Add minimal bubble state and show/hide helpers**

In `tauri-app/src/main.ts`, add:

```ts
let bubbleTimer: number | null = null;
let lastBubbleLine = '';

function showReactionBubble(text: string) {
    const bubble = document.getElementById('reaction-bubble');
    const textNode = document.getElementById('reaction-bubble-text');
    if (!bubble || !textNode) return;

    textNode.textContent = text;
    bubble.classList.add('visible');

    if (bubbleTimer !== null) {
        window.clearTimeout(bubbleTimer);
    }
    bubbleTimer = window.setTimeout(() => {
        bubble.classList.remove('visible');
        bubbleTimer = null;
    }, 1800);
}
```

- [ ] **Step 4: Add click dispatcher entry point**

Add a small single-click dispatcher, called from `pointerup` after region detection:

```ts
async function handleCompanionSingleClick(region: CharacterRegion) {
    await triggerRegionReaction(region);
    const bubbleLine = getBubbleLineForRegion(region);
    showReactionBubble(bubbleLine);
}
```

Then replace the old direct region trigger in the single-click path with this helper.

- [ ] **Step 5: Keep double click opening chat**

Ensure:

- single click does not call `openChat()`
- double click still does `void openChat()`

- [ ] **Step 6: Run browser test to verify it passes**

Run: `python tools/test_click_bubble_response.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tauri-app/src/main.ts tools/test_click_bubble_response.py
git commit -m "feat: add click bubble response dispatcher"
```

---

### Task 3: Add Bubble Categories And 20+ Lines

**Files:**
- Modify: `tauri-app/src/main.ts`

- [ ] **Step 1: Add grouped bubble line pools**

In `tauri-app/src/main.ts`, add four line groups with at least 5 lines each:

```ts
const bubbleLines = {
  gentle: [
    '我在呢。',
    '怎么啦？',
    '嗯，我听到了。',
    '有事找我吗？',
    '我在旁边陪着你。',
  ],
  cheerful: [
    '嘿嘿，你点到我啦。',
    '我有在认真看你哦。',
    '今天也想陪你一下。',
    '诶嘿，我在这儿。',
    '要不要和我说一句话？',
  ],
  shy: [
    '欸？',
    '突然点我呀。',
    '唔，被发现了。',
    '嗯？怎么啦？',
    '我还以为你在忙呢。',
  ],
  calm: [
    '我会在这儿待着的。',
    '慢慢来也没关系。',
    '如果你想说话，我在。',
    '先陪你一下。',
    '我没有走开哦。',
  ],
} as const;
```

- [ ] **Step 2: Add no-repeat line selection**

Implement a helper like:

```ts
function pickNonRepeatingLine(lines: readonly string[]) {
    const filtered = lines.filter((line) => line !== lastBubbleLine);
    const pool = filtered.length > 0 ? filtered : lines;
    const next = pool[Math.floor(Math.random() * pool.length)] ?? lines[0];
    lastBubbleLine = next;
    return next;
}
```

- [ ] **Step 3: Map click regions to preferred bubble groups**

Use a simple mapping:

```ts
function getBubbleLineForRegion(region: CharacterRegion) {
    switch (region) {
        case 'face':
            return pickNonRepeatingLine(bubbleLines.gentle);
        case 'arms':
            return pickNonRepeatingLine(bubbleLines.cheerful);
        case 'belly':
            return pickNonRepeatingLine(bubbleLines.shy);
        case 'legs':
        default:
            return pickNonRepeatingLine(bubbleLines.calm);
    }
}
```

- [ ] **Step 4: Run the existing browser test**

Run: `python tools/test_click_bubble_response.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tauri-app/src/main.ts
git commit -m "feat: add grouped bubble response lines"
```

---

### Task 4: Add Light Attention Cue Timing

**Files:**
- Modify: `tauri-app/src/main.ts`

- [ ] **Step 1: Insert a slight response cadence**

Before showing the bubble, add a small delay after region reaction starts so the sequence feels like:

- notice
- react
- speak

Use a minimal delay such as:

```ts
await new Promise((resolve) => window.setTimeout(resolve, 160));
```

Place it inside `handleCompanionSingleClick()` before `showReactionBubble()`.

- [ ] **Step 2: Re-run browser verification**

Run: `python tools/test_click_bubble_response.py`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tauri-app/src/main.ts
git commit -m "feat: add attention-to-bubble timing"
```

---

## Final Verification Checklist

- [ ] Run: `python tools/test_click_bubble_response.py`
- [ ] Run: `npm run build` in `tauri-app`
- [ ] Verify single click shows bubble without opening chat.
- [ ] Verify double click still opens chat.
- [ ] Verify bubble text does not immediately repeat.

Expected result: single-click interaction feels like a small social response rather than a random motion trigger, and the companion appears noticeably more alive.
