# Proactive Communication System Design

## Goal

Design a small, low-interruption proactive communication system for Desktop AI Companion so the companion can speak first in a few high-value moments without becoming noisy, unpredictable, or annoying.

## Product Intent

The purpose of proactive communication is not to simulate full autonomy.

The purpose is to make the companion feel:

- present,
- lightly caring,
- context-aware,
- and still respectful of the user's attention.

The user should feel:

> 她会在合适的时候轻轻提醒我一下，而不是一直打扰我。

## Core Principle

Proactive communication should be:

- **low frequency**,
- **high confidence**,
- **easy to ignore**,
- **easy to continue into chat**.

The system should prefer saying less, not more.

## Recommended MVP Scope

For the first proactive version, only implement these trigger types:

1. 早安 / 晚安
2. 久坐提醒
3. 饭点提醒
4. 天气 / 气温播报

These are good first triggers because they are:

- easy to understand,
- easy to explain in product copy,
- emotionally soft,
- low risk if phrased briefly.

## Triggers Are Not Messages

A trigger only means:

> "the companion may have a reason to speak now"

It does **not** mean:

> "the companion must speak now"

This distinction is the key design boundary.

Every trigger must pass through a gating layer before anything is shown to the user.

## Architecture Overview

The proactive system should be split into four parts.

### 1. Trigger Sources

These detect moments that may justify proactive communication.

Examples:

- `morning_greeting`
- `night_greeting`
- `long_work_session`
- `meal_time`
- `weather_update`

Each trigger should be a structured event, not inline UI logic.

Suggested shape:

```ts
type ProactiveTriggerType =
  | 'morning_greeting'
  | 'night_greeting'
  | 'long_work_session'
  | 'meal_time'
  | 'weather_update';

type ProactiveTrigger = {
  type: ProactiveTriggerType;
  occurredAt: string;
  metadata?: Record<string, unknown>;
};
```

### 2. Eligibility / Gating Layer

This decides whether the companion is allowed to speak.

This is the most important layer.

Without it, the product becomes a reminder engine instead of a companion.

At minimum, this layer should check:

- whether DND is active,
- whether the user selected a quiet mode,
- whether the user recently interacted,
- whether a similar proactive message was already shown today,
- whether the cooldown window is still active,
- whether chat is already open.

Suggested output:

```ts
type ProactiveDecision = {
  allowed: boolean;
  reason:
    | 'allowed'
    | 'dnd'
    | 'quiet_mode'
    | 'cooldown'
    | 'already_shown_today'
    | 'chat_open'
    | 'user_recently_active';
};
```

### 3. Presentation Layer

If a trigger is allowed, the companion should not immediately open a large chat window.

Instead, presentation should be:

1. a small visual state cue,
2. a short one-line text bubble,
3. a non-forced invitation to continue.

This means:

- no modal feeling,
- no focus steal,
- no large interruption.

The default proactive surface should be a lightweight bubble.

### 4. Continuation Into Chat

If the user clicks the bubble, then the system should open the regular chat panel and seed the companion's proactive line into the conversation context.

This creates a soft progression:

- gentle nudge first,
- full conversation only if the user opts in.

This is much better than auto-opening the full chat panel.

## Why Bubble-First Is Better

Three possible approaches exist.

### Approach A: Auto-open full chat panel

Pros:

- strongest immediate visibility
- easiest to implement conceptually

Cons:

- feels intrusive
- risks breaking focus
- makes the product feel needy

### Approach B: Bubble-first, click to expand into chat (recommended)

Pros:

- low interruption
- user keeps control
- feels closer to a desktop companion than a system alert

Cons:

- weaker visibility than a full panel
- requires one extra click for continuation

### Approach C: Silent visual-only cues

Pros:

- least disruptive
- visually elegant

Cons:

- too easy to miss
- weak for validating whether proactive communication is useful

## Recommendation

Use **Approach B: bubble-first, click to expand into chat**.

It best fits the product's identity:

- companion-like,
- non-pushy,
- visible but not aggressive.

## Trigger Rules By Type

### 1. Morning greeting

Purpose:

- create a soft sense of companionship,
- establish that the companion notices the start of the day.

Rules:

- at most once per local calendar day,
- only after the app first becomes active during the morning window,
- suppressed by DND and strict quiet mode.

### 2. Night greeting

Purpose:

- create gentle day-ending presence,
- reinforce that the companion has a daily rhythm.

Rules:

- at most once per day,
- only within the configured evening window,
- never if the user already interacted heavily in the last short interval.

### 3. Long work session reminder

Purpose:

- add practical value,
- support the "work companion" mode.

Rules:

- only after a sufficiently long active desktop session,
- strong cooldown,
- at most once in a long interval,
- phrased softly, not as a command.

### 4. Meal-time reminder

Purpose:

- create light lifestyle presence,
- make the companion feel attentive.

Rules:

- only once per meal window,
- lower priority than DND and quiet mode,
- should not fire if the user just chatted moments ago.

### 5. Weather / temperature update

Purpose:

- give a small "ambient assistant" feeling.

Rules:

- should be opt-in or low-frequency,
- best used as a small info bubble,
- can be more effective when paired with time-of-day triggers.

## Companion Copy Rules

Proactive messages should follow these rules:

- one sentence,
- short enough to scan instantly,
- warm but not theatrical,
- no emotional overreach,
- no guilt-inducing language,
- no repeated punctuation spam,
- no sounding like a phone notification system.

Good examples:

- `早呀，今天也一起慢慢开始吧。`
- `你已经坐挺久啦，要不要起身活动一下？`
- `差不多到饭点了，记得照顾一下自己。`

Bad examples:

- `主人！你已经很久没有理我了！`
- `检测到你连续工作 127 分钟，建议立即休息。`
- `你是不是情绪不好，我来安慰你。`

## Settings Design

This system should remain simple for users.

Users should not configure ten different automation rules.

Instead, use a few understandable controls:

- proactive mode:
  - quiet
  - greet
  - remind
- DND enabled
- DND start / end
- optional toggles for:
  - weather
  - meal reminders
  - long-work reminders

This keeps control visible without turning the product into a settings-heavy tool.

## State Model Impact

The companion should gain one small extra internal concept:

- `proactive bubble visible`

This does not need to become a full new major character animation state yet.

It can simply be:

- slight attention cue,
- bubble shown,
- click transitions into normal chat state.

## Persistence Needs

The system should persist:

- last shown timestamp per proactive trigger type,
- whether today's greeting has already fired,
- simple user proactive preferences,
- DND config.

This can be stored locally with existing config/history patterns.

No cloud dependency is required for the first version.

## MVP Implementation Order

Build in this order:

1. gating layer
2. bubble presentation
3. click-to-chat continuation
4. morning / night greetings
5. long work reminder
6. meal reminder
7. optional weather trigger

This order matters because the product becomes dangerous if trigger types are added before suppression and cooldown logic exist.

## Acceptance Criteria

This design is successful when:

- the companion can proactively speak in a few predictable moments,
- it does not interrupt the user with large modal behavior,
- users can ignore a bubble without penalty,
- clicking the bubble naturally opens the chat panel,
- proactive behavior feels calm and intentional,
- users do not describe it as annoying.

## Non-Goals

This design does not include:

- freeform emotional inference,
- high-frequency autonomous chatting,
- complex agenda planning,
- large-scale reminder automation,
- voice-first proactive behavior,
- multi-character differentiated scheduling logic.

## Retention Extension: Companion Progression Track

The user additionally proposed a retention-friendly progression idea:

### Option C: Pass / Companion Level

The core idea is:

- users interact a little every day,
- optionally complete small companion-facing tasks,
- earn experience,
- unlock lightweight cosmetic or emotional rewards.

Candidate unlocks:

- 饰品
- 台词
- 表情
- 小动作
- 气泡皮肤
- 纪念徽章

### Why this direction is attractive

Compared with heavier monetization or random reward systems, this approach has three clear product advantages:

1. stronger retention,
2. it does not require immediate payment,
3. it can feel like "growing with the companion" instead of gambling-like progression.

### Recommended placement

This should **not** be mixed into the first proactive communication MVP itself.

Reason:

- proactive communication is a presence and interruption-control system,
- companion progression is a retention and reward system,
- combining both at once would increase complexity and blur success criteria.

### Better sequencing

Use it as a **later layer after proactive communication is stable**.

Recommended order:

1. first make proactive bubbles feel calm and useful,
2. then measure whether users return voluntarily,
3. then add a lightweight companion progression system to reinforce the habit loop.

### Good MVP version of progression

If introduced early, keep it very small:

- daily interaction gives a little companion EXP,
- no loot-box feeling,
- no pressure to grind,
- no giant task list,
- no aggressive "come back now" mechanics.

The progression loop should feel like:

> 我们在一起待久一点，她会慢慢变得更像我的伙伴。

not:

> 我必须每天打卡做任务，不然就亏了。

### Design warning

This system only works if the unlocked content is emotionally meaningful but operationally light.

Best unlock types for this product are:

- small visual changes,
- new reactions,
- warm lines,
- tiny personalization markers.

Worst unlock types for this product are:

- heavy reward pressure,
- repeated busywork tasks,
- progression that feels like a mobile game treadmill.

### Current recommendation

Treat **Companion Level / Pass** as a strong **P1-to-P2 retention layer**, not a blocker for the first proactive communication rollout.

It is a good idea, but it should sit on top of a calm companion foundation, not replace that foundation.

## Recommendation Summary

The best next version is not "more proactive features." It is:

> a small proactive communication state machine with a bubble-first interaction model.

That gives the product a stronger feeling of presence without making it noisy.
