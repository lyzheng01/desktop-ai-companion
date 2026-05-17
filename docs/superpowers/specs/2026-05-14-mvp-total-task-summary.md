# MVP Total Task Summary

## Purpose

Summarize the full current MVP task set after combining:

- the original Obsidian MVP plan,
- later P0 gap-closure work,
- the simplification decision around memory,
- the new proactive communication task,
- and the separate companion progression / pass task.

This file is the current high-level product task map.

## Overall Product Goal

The MVP is not trying to be a full AI companion platform.

It is trying to validate:

- whether users want to keep an AI character on the desktop,
- whether they will use it instead of opening a browser AI tab for some questions,
- whether character + presence + lightweight memory can create habit,
- whether users feel "this is my AI companion,"
- and eventually whether parts of that experience can support paid upgrades.

The core sentence remains:

> 先验证“桌面常驻的私人 AI 伙伴”这个产品形态是否成立。

## Total MVP Task Groups

### A. Core visibility and baseline desktop experience

#### Task 1: Fix real character visibility

This is the highest-priority blocker.

The app cannot count as MVP-ready if the user still cannot reliably see the desktop character with their own eyes, even if rendering evidence exists internally.

This includes:

- desktop window visibility,
- character placement inside the window,
- actual desktop-level visual verification.

#### Task 2: Add first-run companion creation flow

The first-time experience should let the user feel:

- this is my companion,
- I named her,
- I chose how she feels,
- I chose how we get along.

Minimum first-run flow:

- choose role type,
- choose base role,
- set name,
- choose personality,
- choose interaction mode,
- complete creation.

#### Task 3: Complete the desktop-resident loop

This includes:

- transparent desktop character,
- drag,
- scaling,
- click interaction,
- hide / restore,
- tray menu,
- stable stay-on-desktop behavior,
- not blocking normal work too much.

### B. Chat and memory

#### Task 4: Improve companion-like chat quality

The product should feel like the role is answering, not like a plain API response.

This means:

- shorter replies,
- more natural rhythm,
- less tool-tone,
- stronger role consistency,
- better use of recent context.

#### Task 5: Keep memory lightweight and option-driven

Memory stays in the MVP, but must remain simple for users.

Do:

- nickname,
- interaction mode,
- proactive preference,
- a few lightweight option-driven preferences.

Do not do:

- manual add-memory workflow,
- direct memory editing workflow,
- heavy user-managed memory page.

The product should feel like it remembers a little, not like the user is maintaining a database.

#### Task 6: Complete local history and local data flow

This includes:

- view recent chat history,
- restore recent chat history,
- clear history,
- make local data controls understandable,
- preserve the local-first principle.

### C. Quietness and interruption control

#### Task 7: Make do-not-disturb real

DND cannot remain just stored config values.

It needs runtime behavior, including at minimum:

- DND time window,
- whether proactive reminders are allowed,
- whether work-time prompts are allowed,
- whether desktop bubbles are allowed,
- a default behavior that is calm and restrained.

The rule is:

> 角色绝不能太烦。

### D. Proactive communication system

#### Task 8: Proactive communication system

This is now a distinct task.

Its MVP scope should include:

- morning / night greetings,
- long-work reminders,
- meal-time reminders,
- weather / temperature updates,
- lightweight text bubble,
- click bubble to open chat dialog.

This should be built as a small state machine with:

- trigger sources,
- gating / eligibility rules,
- bubble-first presentation,
- click-to-chat continuation.

Principles:

- high value,
- low interruption,
- predictable,
- easy to ignore,
- easy to continue.

### E. Companion progression / pass

#### Task 9: Companion level / pass system

This is a separate task from proactive communication.

Purpose:

- improve retention,
- create a sense of growth,
- avoid gambling-style reward design.

Possible unlocks:

- 饰品
- 台词
- 表情
- 小动作
- 气泡皮肤
- 纪念徽章

Principles:

- feels like growing with the companion,
- not heavy daily grind,
- not task-pressure driven,
- not lottery-like.

### F. Alpha and validation loop

#### Task 10: Alpha testing and feedback loop

This includes:

- recruitment copy,
- signup form,
- feedback group,
- daily and weekly feedback prompts,
- small seed-user testing cohort.

The immediate target remains a small real-user cohort, not mass launch.

#### Task 11: Minimum marketing assets

This includes:

- one-line positioning,
- short demo scripts,
- companion-feel content,
- utility-angle content,
- reaction-angle content,
- basic invite / FAQ / roadmap copy.

#### Task 12: Presence validation metrics

This includes:

- install success,
- first-creation completion rate,
- D1 / D3 return,
- average daily question count,
- average conversation depth,
- whether users keep the role on desktop,
- whether users set personality / interaction preferences,
- whether users look at memory summaries,
- whether users disable proactive behavior.

## Recommended Order

### P0 blockers first

1. Fix real character visibility
2. Add first-run companion creation flow
3. Make do-not-disturb actually work
4. Complete local history / local data loop
5. Improve companion-like chat quality

### P0.5 strongly recommended next

6. Proactive communication system

### P1 retention enhancement

7. Companion level / pass system

### Continuous parallel work

8. Alpha testing and feedback loop
9. Minimum marketing assets
10. Presence validation metrics

## Summary

The MVP is no longer just "make the app run." It is now the combination of three layers:

1. **Close the remaining core product loops**
2. **Add a careful proactive communication system**
3. **Add a later companion-growth retention layer**

The product should stay simple for the user throughout.

If a feature makes the user feel they are managing a complicated system rather than living with a calm companion, it is probably too heavy for this stage.
