# Desktop AI Companion P0 Product Goals And Marketing Design

## Goal

Define what `P0` is actually trying to prove for Desktop AI Companion, and translate that into a small set of product and marketing tasks that fit this product's real shape: AI companion, character presence, desktop experience, and community co-creation.

## Core Product Thesis

This product should not be marketed like a generic SaaS AI tool.

The user is not buying:

- Live2D + AI
- another chat window
- a desktop wrapper around an LLM

The user is buying:

- a small companion that lives on the desktop,
- reacts with visible presence,
- remembers a little,
- feels calming, interesting, and lightly personal.

The shortest correct description is:

> 一个住在桌面上的 AI 小伙伴。

The more explicit version is:

> 一个会陪你聊天、会有表情动作、会记住你一点点的桌面 AI 伙伴。

## P0 Product Goal

`P0` is not trying to prove scale, monetization, or deep emotional simulation.

`P0` is trying to prove three things:

1. Users are willing to keep the companion open on their desktop for long sessions.
2. Users feel it has presence, not just utility.
3. A small group of users voluntarily comes back for multiple days.

## P0 Success Condition

P0 is successful if early users say things like:

- "她真的像在桌面上陪着我。"
- "我会顺手点她聊两句。"
- "她不像普通聊天机器人。"
- "工作时她在旁边待着，感觉挺治愈。"

P0 is not successful just because:

- the model answers correctly,
- the UI looks polished,
- there are many characters,
- there are many settings.

## P0 Positioning

### One-line positioning

一个住在桌面上的 AI 小伙伴。

### Expanded positioning

不是聊天窗口，而是住在你桌面上的 AI 小伙伴。

她会陪你聊天、会有表情动作、会记住你一点点，也会在你专注时安静陪着你。

### What to avoid

Avoid positioning like:

- 全球领先的 AI 虚拟伴侣平台
- 下一代 AI 桌面操作系统
- 高度智能的情感计算产品

These are too abstract for P0 and weaken trust.

## P0 Target Users

P0 should not target everyone.

### Primary seed users

1. 二次元 / Live2D / 桌宠用户
2. AI 工具重度用户
3. 长时间电脑办公或创作的人

### Secondary seed users

4. 对轻陪伴有兴趣，但不希望产品过度侵入的人

### Why these users first

They already understand at least one of the product's strongest surfaces:

- character presence,
- desktop staying power,
- AI convenience,
- light companionship.

## P0 User Value Promise

The product needs to make these five things obvious quickly.

### 1. Desktop presence

The AI is already there. The user does not need to open a separate tool.

### 2. Character reaction

The companion should visibly react through idle, listening, thinking, and talking states.

### 3. Low-friction chat

When the user is stuck, lonely, bored, or wants a quick answer, they can click and ask.

### 4. Light memory

The companion remembers nickname and a few preferences, enough to feel personal, not invasive.

### 5. Non-intrusive behavior

The companion should feel present without becoming noisy or annoying.

## P0 Product Non-Goals

Do not let `P0` expand into these areas yet:

- many deep character systems,
- complex proactive behavior,
- marketplace or role shop,
- voice-heavy product loop,
- broad multi-character positioning,
- heavy automation or agent workflows,
- deep emotional dependency framing.

## Current P0 Status From Repo

### Already in place

- Tauri desktop shell
- Live2D rendering with multiple models
- chat window and backend request path
- SQLite history persistence
- config persistence
- explicit idle/listening/thinking/talking loop
- basic hide/settings/quit controls
- history restore regression coverage

### Still weak or unfinished for P0

- first-run product framing is not yet packaged as a user-facing alpha flow
- tray/recoverability needs to be treated as a core user story, not just a technical feature
- default hero-character path is still diluted by too many models
- memory is still small and mostly technical, not yet framed as user value
- onboarding and feedback loop for seed users is not yet built
- marketing assets and testing loop are not yet formalized

## The 8 P0 Tasks

These are the eight things P0 should do next.

### Task 1: Lock the hero experience

Pick one default character path for P0 and make the first-run experience centered on her.

Why:

- P0 should sell one clear feeling, not a menu of options.
- A single hero character makes demo videos and user memory stronger.

Definition of done:

- one default character is used in screenshots, videos, onboarding, and README copy
- other characters can remain in repo, but are not the main story

### Task 2: Make the desktop loop feel reliable

The user must be able to:

- launch,
- see the character,
- drag it,
- scale it,
- hide it,
- restore it,
- keep it open for a long session.

Why:

- if the desktop loop feels unstable, the companion feeling collapses immediately.

Definition of done:

- no "where did it go" failure
- hide and recover path is obvious
- position and scale feel persistent and predictable

### Task 3: Strengthen visible presence

Keep the state model small, but make it feel alive:

- idle
- listening
- thinking
- talking

Why:

- this is the product difference users can see in 3 seconds.

Definition of done:

- each state is visually distinct
- transition timing feels natural enough in demo recordings
- user immediately understands "she is reacting"

### Task 4: Make chat feel like companion chat, not just API chat

The chat path must remain short and reliable.

Why:

- P0 does not need advanced prompting features.
- It does need a feeling that clicking the desktop companion is worth it.

Definition of done:

- open chat reliably
- send and receive reliably
- restore local history reliably
- failure path is calm and understandable

### Task 5: Turn memory into a safe, light product loop

P0 memory should stay small:

- nickname
- preferred form of address
- a few editable preferences

Why:

- memory is one of the strongest "not just another chatbot" signals
- but too much memory too early can feel invasive

Definition of done:

- user understands what is remembered
- user can edit or clear it
- product can truthfully say "会记住你一点点"

### Task 6: Ship an alpha onboarding and feedback loop

P0 is not ready for wide launch. It is ready for a small alpha.

Why:

- the next real proof is not code correctness, it is repeated use.

Definition of done:

- there is an alpha description page or doc
- there is a test-user intake form
- there is a feedback group and a weekly question loop

### Task 7: Produce the minimum marketing assets

At minimum P0 needs:

- one sentence positioning
- one 15-second demo video
- one alpha signup page
- one FAQ/privacy note
- one roadmap snapshot

Why:

- this product is hard to explain with text only
- video is the shortest path to user understanding

Definition of done:

- a stranger can watch one short clip and understand why this is not a normal chatbot

### Task 8: Measure whether presence is real

P0 should track whether people actually keep it open and return.

Core P0 signals:

- install success
- first successful launch
- chat success rate
- history restore success
- D1 and D3 reuse in alpha group
- average daily conversations
- user quotes about presence, companionship, and annoyance

Why:

- P0 wins on repeated voluntary use, not on novelty alone.

## P0 Marketing Plan

### Main narrative

Lead with:

> 我做了一个住在桌面上的 AI 小伙伴。

Do not lead with:

- Tauri
- FastAPI
- Live2D SDK
- model routing

Those belong in builder-facing posts, not user-facing first contact.

### Content angles to test first

1. 陪伴感
2. 效率辅助
3. 角色反应感

### Best-fit early channels

- 小红书
- B站
- 即刻
- V2EX
- QQ 群 / Discord 社群

### P0 launch mode

Use limited alpha, not broad launch.

Target:

- first 20-50 real test users

## P0 Messaging Rules

Always emphasize:

- 在桌面上
- 会反应
- 会记住一点点
- 安静陪着你
- 不是普通聊天窗口

Avoid overclaiming:

- psychological healing
- deep emotional understanding
- human-like attachment
- perfect long-term memory

## Recommended Immediate Next Steps

1. Freeze the P0 hero positioning around one default character.
2. Record a 15-second demo focused on presence, not tech.
3. Write an alpha signup page and small feedback questionnaire.
4. Add one visible, user-editable memory surface.
5. Decide the exact P0 metrics to review weekly.

## P0 Summary

P0 is not "ship more features."

P0 is:

> prove that users want a calm AI companion living on their desktop, and that they come back because it feels present.

If users do not feel presence, no amount of extra features will save the product.

If users do feel presence, then P1 can deepen memory, rhythm, and emotional quality with confidence.
