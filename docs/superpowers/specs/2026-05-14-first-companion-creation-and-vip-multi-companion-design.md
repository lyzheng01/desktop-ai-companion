# First Companion Creation And VIP Multi-Companion Design

## Goal

Design a simple first-companion creation flow for the MVP, while leaving room for a future VIP-only multi-companion model.

The system should make the user feel they are creating **their own companion**, without turning the product into a heavy management tool.

## Product Intent

The first creation flow should answer one core emotional need:

> 这不是一个系统默认角色，这是我创建出来、属于我的伙伴。

At the same time, it should preserve a future monetization direction:

- free users can keep one companion,
- VIP users can create multiple companions,
- only one companion is active at a time.

## Core Decision

The user explicitly chose this product direction:

- first launch must create a companion,
- later launches should go straight into the desktop experience,
- users should be able to create additional companions later,
- multiple companions should be a VIP-only capability,
- different companions should differ at least by:
  - name,
  - role,
  - positioning / interaction mode.

## Recommended MVP Model

Use a **simple multi-companion data model with a single active companion**.

That means:

- the system may store multiple companion profiles,
- but runtime only uses one active companion,
- the desktop shell, chat, and companion state machine always bind to the active one.

This is much simpler than treating multiple companions as simultaneously active presences.

## Why This Is The Right Scope

Three possible approaches exist.

### Approach A: Single companion forever

Pros:

- smallest implementation scope,
- simplest user model.

Cons:

- blocks a meaningful future VIP path,
- makes the first creation flow feel more disposable.

### Approach B: Store multiple companions, activate one at a time (recommended)

Pros:

- supports first-launch emotional ownership,
- supports future VIP monetization,
- keeps runtime logic simple,
- avoids multi-character desktop complexity.

Cons:

- requires a small profile-management layer,
- adds a little more persistence logic than a strict single-profile MVP.

### Approach C: Full multi-companion system now

Pros:

- strongest future-facing feature set.

Cons:

- too large for current MVP,
- increases UI and persistence complexity,
- distracts from validating the first companion relationship.

## Recommendation

Use **Approach B: multiple stored companions, single active companion**.

This gives the product the right emotional framing and future monetization path without blowing up complexity.

## User Experience Flow

### First launch

If there is no existing companion:

1. show first-companion creation flow,
2. user selects a base role,
3. user names the companion,
4. user chooses personality tags,
5. user chooses interaction mode,
6. user completes creation,
7. new companion becomes active,
8. user enters the desktop experience.

### Later launches

If there is already an active companion:

- skip creation,
- launch directly into the desktop companion experience.

### Later companion creation

From settings:

- free user:
  - sees a create-new-companion entry,
  - but is blocked with a simple VIP upsell if they already have one companion.
- VIP user:
  - can create additional companions,
  - can switch which companion is active.

## Minimum Companion Fields

Each companion should store:

- `id`
- `name`
- `character_type`
- `personality_tags`
- `interaction_mode`
- `is_active`
- `created_at`

Optional later fields can be added, but these are enough for MVP.

## Persistence Model

The system should move away from treating companion identity as only a flat global config block.

Instead:

- keep app-wide desktop config in the main config area,
- store companion-specific identity in a companion collection,
- keep a simple pointer to the active companion.

Suggested split:

- global app config:
  - window position
  - scale
  - DND settings
  - proactive settings
  - VIP flag / account tier placeholder
- companion profile:
  - name
  - character type
  - personality
  - interaction mode

This keeps companion identity separate from desktop behavior.

## Free vs VIP Rules

### Free user

- may create one companion,
- may edit that companion,
- may not create a second one,
- sees a clear but lightweight VIP prompt when trying to add another.

### VIP user

- may create multiple companions,
- may switch active companion,
- still only runs one active companion at a time on desktop.

## Settings Surface

The settings panel should evolve to include a simple companion section.

Minimum user-visible actions:

- view current companion name,
- edit current companion profile,
- create new companion,
- switch active companion (VIP only),
- see simple VIP restriction messaging.

Do **not** turn this into a big account-management dashboard.

## Creation Flow Shape

The first creation flow should stay lightweight.

Recommended steps:

1. choose companion role / visual base
2. enter companion name
3. choose 1-3 personality tags
4. choose interaction mode
5. finish

This should feel more like a warm setup ritual than a technical form.

## Companion Identity And Chat

When a companion is active, these values should feed the chat layer:

- companion name,
- personality tags,
- interaction mode,
- user display name.

That ensures chat style changes with the active companion profile.

## Companion Identity And Memory

The current MVP memory direction stays intentionally simple.

That means:

- no heavy per-companion memory management UI,
- no user-maintained memory database,
- only light preference and profile-derived context.

Companion identity should influence memory interpretation, but not expand memory complexity.

## What This Design Does Not Include Yet

Do not include in this version:

- simultaneous multiple desktop companions,
- full companion library management,
- complex delete / archive / recovery flows,
- per-companion long-term memory branching,
- paid role marketplace,
- advanced role progression mechanics.

## Acceptance Criteria

This design is successful when:

- a first-time user must create a companion before entering the product,
- later launches feel immediate,
- the user feels the current companion is theirs,
- free users are limited to one companion without confusion,
- VIP users can create and switch companions,
- runtime always uses one clear active companion.

## Recommendation Summary

The correct MVP move is not a full multi-companion system.

It is:

> first-companion creation now, multiple stored companions later, one active companion at runtime.

That gives the product emotional ownership and a future VIP path without making the current MVP too heavy.
