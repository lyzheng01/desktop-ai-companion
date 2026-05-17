# Click Reaction And Bubble Response Design

## Goal

Design a better tap-interaction response system for the desktop companion so a user click feels like a small social interaction, not just a random animation trigger.

## Product Intent

When the user clicks the companion, the experience should feel like:

1. she noticed the click,
2. she reacted emotionally,
3. she gave a short response,
4. she returned to a calm idle state.

The user should feel:

> 她不是被点一下就播一个动作，而是真的在回应我。

## Core Principle

The click response should not be modeled as:

- click -> random motion

It should instead be modeled as:

- click -> attention cue -> small emotion/motion -> short bubble response

This creates a much stronger sense of presence.

## Response Layers

### Layer 1: Attention cue

The companion should first show that she noticed the user.

Examples:

- slight head turn,
- short eye focus,
- tiny body reorientation,
- quick pause from idle.

This layer should be short, around:

- `150ms - 250ms`

Its purpose is not spectacle. Its purpose is acknowledgment.

### Layer 2: Emotion / motion response

After acknowledgment, trigger a lightweight emotional response.

This should come from a small structured pool, not a flat fully-random list.

#### Small response pool (high frequency)

- blink
- smile
- slight head tilt
- nod
- eye follow

#### Medium response pool (occasional)

- small wave
- short bounce
- short body shift

#### Large response pool (rare)

- a bigger motion clip,
- noticeable posture change,
- longer expressive reaction.

Recommended ratio:

- 80% small responses
- 18% medium responses
- 2% large responses

This keeps the character expressive without making her feel noisy or unstable.

### Layer 3: Bubble response

The click should usually end with a short bubble line near the character.

This is preferable to auto-opening the full chat panel.

Reason:

- lower interruption,
- feels more like light companionship,
- preserves a distinction between light interaction and full conversation.

## Click vs Double-Click

Recommended interaction contract:

- **Single click**: light response only
  - attention cue
  - small motion or expression
  - short bubble
- **Double click**: open full chat dialog

This cleanly separates:

- light affection / check-in,
- from intentional conversation.

## Region-Based Response Mapping

The current system already knows click regions. The new design should use them.

### Face

Prefer:

- blink
- smile
- head tilt
- soft acknowledgment bubble

### Arms / hand area

Prefer:

- wave-like micro reaction
- cheerful or playful bubble

### Torso / belly area

Prefer:

- light surprise
- tiny recoil
- short "欸？" style bubble

### Legs / lower area

Prefer:

- mild posture reset
- less dramatic feedback

This prevents all clicks from feeling identical.

## Bubble Behavior

### Placement

The bubble should appear near the character's head or upper body.

It should feel attached to the character, not to the page shell.

### Duration

Recommended default lifetime:

- `1.2s - 2.2s`

### Animation

Recommended entry animation:

- fade in
- slight upward float

Recommended sequencing:

- attention cue first
- bubble appears after `120ms - 250ms`

### Escalation

If the user clicks the bubble itself:

- open the full chat panel
- optionally seed the bubble text into the chat context as the companion's first line

## Bubble Writing Rules

Bubble lines should be:

- short,
- easy to scan,
- emotionally light,
- not repetitive,
- not cringe,
- not system-notification-like.

## Bubble Categories

At minimum, create these four categories:

### 1. Gentle

Use when the click feels affectionate or neutral.

### 2. Cheerful

Use for a brighter, more lively reaction.

### 3. Shy / surprised

Use for sudden or less expected clicks.

### 4. Calm companion

Use when the product should feel especially soft and present.

## Bubble Quantity Rule

Each category must contain **at least 5 lines**.

That means the system should ship with **20+ total bubble lines** at minimum.

This is important because too few lines immediately makes the companion feel mechanical.

## Recommended Bubble Sets

### Gentle (minimum 5)

- 我在呢。
- 怎么啦？
- 嗯，我听到了。
- 有事找我吗？
- 我在旁边陪着你。

### Cheerful (minimum 5)

- 嘿嘿，你点到我啦。
- 我有在认真看你哦。
- 今天也想陪你一下。
- 诶嘿，我在这儿。
- 要不要和我说一句话？

### Shy / surprised (minimum 5)

- 欸？
- 突然点我呀。
- 唔，被发现了。
- 嗯？怎么啦？
- 我还以为你在忙呢。

### Calm companion (minimum 5)

- 我会在这儿待着的。
- 慢慢来也没关系。
- 如果你想说话，我在。
- 先陪你一下。
- 我没有走开哦。

## Weighted Selection Rule

Bubble selection should not be fully random.

Use lightweight weighting by:

- click region,
- current interaction mode,
- recent repeated line suppression.

At minimum:

- do not repeat the same line twice in a row,
- avoid showing the same tiny set too often.

## Runtime State

This system should add one small UI state concept:

- `bubble visible`

It does **not** require a large animation-state rewrite.

The first version can remain a lightweight response dispatcher layered on top of the current state model.

## What This Design Should Not Become

Do not turn this into:

- a giant emote engine,
- a long text-chat fallback,
- a spammy assistant,
- a game-like tapping system.

The purpose is companionship polish, not interaction farming.

## Recommended Implementation Order

1. add bubble UI component
2. add click-response dispatcher
3. split response pools into small / medium / large
4. map region -> preferred response group
5. add 20+ bubble lines across categories
6. add no-repeat logic
7. keep double-click -> open chat

## Acceptance Criteria

This design is successful when:

- single click feels like a light social interaction,
- double click still clearly means "start chat",
- the bubble feels attached to the companion,
- click response is varied but not chaotic,
- bubble lines are numerous enough that repetition does not immediately break immersion.

## Recommendation Summary

The best click interaction is not:

- random motion only.

It is:

> click -> attention -> small emotion/motion -> short bubble response.

That is the smallest change that makes the companion feel much more alive.
