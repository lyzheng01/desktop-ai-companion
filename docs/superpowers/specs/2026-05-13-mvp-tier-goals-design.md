# Desktop AI Companion MVP Tier Goals Design

## Goal

Define a practical P0, P1, and P2 scope for the current Desktop AI Companion codebase so development stays focused on validating whether users want a lightweight AI companion living on their desktop.

## Product Principle

The first success condition is not "many features shipped." The first success condition is:

- users willingly keep the companion on their desktop,
- users interact with it repeatedly,
- users feel light companionship rather than friction.

Everything in the tiering should serve that validation goal.

## Current Project Assessment

### Already present in the codebase

- Transparent always-on-top Tauri window.
- Live2D model loading with multiple model options.
- Basic drag interaction for the desktop character window.
- Scale control and persisted scale config.
- Chat window with send flow.
- Backend config persistence and SQLite chat history persistence.
- Basic idle and talking animation hooks.
- In-app context menu with hide, settings, and quit actions.

### Not complete enough for MVP validation yet

- No real system tray workflow.
- No front-end history restore loop.
- No true streaming reply flow.
- No clear thinking state in the character state model.
- No complete desktop controls for always-on-top, click-through, startup, opacity, and reset position.
- Config fields are drifting between front-end, backend API, and stored config model.
- Memory exists in the database layer but not as a real user-facing product loop.

## Tier Definitions

## P0 Design Goal

### Purpose

Validate whether a user is willing to keep one AI companion on their desktop and chat with it repeatedly.

### Product target

P0 is a stable, minimal, testable desktop companion. It is not yet a fully expressive companion product.

### P0 feature goals

- One default hero character experience.
- Transparent desktop character window.
- Dragging and scaling that feel reliable.
- Position restore on relaunch.
- Show, hide, and quit flows that feel like a desktop app.
- Real tray entry so the app is recoverable after hiding.
- Click character to open chat.
- Stable request-response chat.
- Local message history restored in the chat window.
- Four clear character states only: idle, listening, thinking, talking.
- Minimal memory loop: user nickname, user-facing name, and a few editable preferences.
- Basic settings only for the MVP-critical controls.

### P0 acceptance criteria

- App launches reliably and keeps the character visible for long sessions.
- User can move and scale the character without confusion.
- User can hide and restore the app without losing it.
- User can open chat, send a message, receive a reply, and see previous messages later.
- Character visibly changes state during idle, input attention, thinking, and reply playback.
- User can set how the companion addresses them.
- At least a few early users are willing to keep it open for multiple days.

### P0 engineering goals

- Unify config fields across `app/config.py`, `backend/server.py`, and front-end `AppSettings`.
- Add front-end history loading from `/history`.
- Introduce explicit UI state for chat sending, thinking, success, and failure.
- Add a true system tray path in Tauri Rust.
- Persist and restore window position.
- Keep the animation system intentionally small and stable.

## P1 Design Goal

### Purpose

Validate whether the product feels like companionship instead of a generic chatbot with a Live2D shell.

### Product target

P1 deepens the emotional feel without expanding into a large feature surface.

### P1 feature goals

- More natural micro-motions while idle.
- Clearer listening, thinking, and talking transitions.
- Manual and scheduled do-not-disturb.
- Lower activity behavior during quiet mode.
- Lightweight visible memory: nickname, preferences, recent topics.
- User controls to view and remove stored memory.
- Better chat ergonomics: copy reply, clear session, retry failed send.
- Optional streamed response if the model path supports it.

### P1 acceptance criteria

- Users can describe the companion as calm, present, or attentive.
- Do-not-disturb makes the product feel less intrusive, not more complicated.
- Returning users notice that the companion remembers something meaningful.
- Session quality improves without requiring more major features.

### P1 engineering goals

- Replace scattered animation triggers with an explicit state machine.
- Connect existing DND-related config fields to real runtime behavior.
- Add front-end surfaces for memory read, delete, and clear controls.
- Improve failure recovery in chat flows.
- Measure basic usage events needed to judge retention.

## P2 Design Goal

### Purpose

Validate product differentiation and the beginnings of retention and monetization potential.

### Product target

P2 is where the companion becomes recognizably distinct from a normal AI chat window.

### P2 feature goals

- Stable role voice and behavioral rhythm.
- Carefully limited proactive behavior.
- Better long-term memory strategy and user control.
- Relationship depth cues such as companion days or continuity markers.
- Real model integration quality, latency, and cost tracking.
- Basic product telemetry to understand stickiness.

### P2 acceptance criteria

- Users can clearly say why this feels different from ordinary AI chat.
- A meaningful subset of users keep it on desktop long-term.
- The team can identify which behaviors increase retention versus which are only visually impressive.

### P2 engineering goals

- Move from raw memory storage to memory selection strategy.
- Add observability for latency, failures, and usage.
- Add controlled proactive logic backed by settings and product evidence.
- Support deeper iteration on one polished character rather than broadening too early.

## Recommended Development Order

1. Finish P0 infrastructure before adding new expressive behaviors.
2. Reduce surface area by focusing on one default character path.
3. Unify settings and state handling before adding more UI options.
4. Add tray, history restore, and thinking state before advanced memory.
5. Add DND and memory controls in P1 before exploring multi-character depth.
6. Delay broad differentiation work until retention evidence appears.

## Non-Goals For Early Tiers

- Character marketplace.
- Many deep Live2D action packs.
- Voice-heavy experience.
- Multi-model routing complexity.
- Plugin ecosystem.
- Large-scale automation features.
- Broad multi-character product positioning.

## Success Metrics By Tier

### P0

- installation success,
- launch stability,
- chat success rate,
- history restore success,
- multi-day voluntary reuse by a small test cohort.

### P1

- do-not-disturb usage,
- repeated daily opens,
- repeated conversations,
- positive feedback about comfort, presence, or companionship.

### P2

- sustained retention,
- differentiated user quotes,
- evidence of preferred behaviors,
- model cost and latency within acceptable bounds.
