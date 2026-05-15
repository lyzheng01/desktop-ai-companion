# Phase 2 Memory Architecture Checklist

## Goal

Define the next practical evolution of the memory system after the current MVP-stage memory model.

Phase 2 should make memory feel more natural and useful without turning it into a heavy user-managed system.

## Phase 2 Objective

Move from:

- flat config preferences,
- flat memory rows,
- simple prompt injection,

to:

- stable preference memory,
- short-term memory,
- long-term memory,
- candidate-memory extraction,
- basic memory selection rules.

## What Phase 2 Should Achieve

By the end of Phase 2, the companion should be able to:

1. remember some things only for the current period,
2. keep only important things for the long term,
3. avoid remembering everything automatically,
4. use memory more intelligently in replies,
5. stay simple for the user.

## Core Principle

The user should not feel like they are managing a database.

The system should do most of the remembering work itself, while still keeping:

- visibility,
- deletion control,
- and clear boundaries.

## Target Layers

### Layer 1: Stable preference memory

This is the most durable memory.

Examples:

- nickname
- preferred form of address
- interaction mode
- proactive preference
- maybe preferred language or reply tone

These can mostly keep living in config-derived storage.

### Layer 2: Short-term memory

This is memory that matters for the current period but should not live forever.

Examples:

- current project
- recent concern
- what the user is focused on this week
- temporary emotional or situational context

### Layer 3: Long-term memory

This is memory worth keeping across longer time spans.

Examples:

- stable interests
- recurring preferences
- ongoing relationship details

## Practical Implementation Checklist

### 1. Add a memory scope field

Current memory rows should evolve to include a scope such as:

- `preference`
- `short_term`
- `long_term`

This is the minimum structural change needed to stop treating all memory equally.

### 2. Add candidate-memory extraction

Do not write every candidate directly into long-term memory.

Instead:

- extract candidates from user messages,
- classify them,
- only persist when they pass a lightweight rule.

## Candidate examples

Good candidate patterns:

- "我最近在准备考试"
- "你以后叫我阿泽就好"
- "我最近在做一个桌面 AI 项目"
- "我更喜欢你简短一点回复"

Bad candidate patterns:

- one-off small talk
- filler expressions
- generic short replies

### 3. Add selection rules before persistence

Before writing memory, ask simple questions like:

- is this explicit preference?
- is this repeated enough?
- is this likely useful again?
- is this already stored?
- should it expire later?

This should be implemented as deterministic rules first, not as a fully AI-judged memory engine.

### 4. Introduce expiry for short-term memory

Short-term memory should not stay forever.

Phase 2 should define one of:

- age-based expiry,
- last-used expiry,
- or manual periodic cleanup.

Even a simple rule is enough for Phase 2.

### 5. Keep long-term memory conservative

Long-term memory should be hard to grow.

Examples of conservative rules:

- only explicit preference statements,
- only repeated project/topic references,
- only manually pinned stable facts.

### 6. Improve prompt assembly

Prompt assembly should stop doing only:

- `get_memories()[:5]`

Instead it should become something closer to:

- stable preferences first,
- then 1-3 most relevant short-term items,
- then 1-3 long-term items.

This makes the reply feel more coherent and less noisy.

### 7. Add memory visibility without heavy editing

Phase 2 should still avoid turning memory into a management UI.

Good:

- "她记住的内容"
- grouped by type
- delete if needed

Avoid:

- large edit forms
- dozens of memory rows
- complicated categorization for users

### 8. Prepare for future companion-scoped memory

Even if full multi-companion memory isolation is later, Phase 2 should avoid making that impossible.

So memory rows should be designed with future extensibility in mind, such as a possible later:

- `companion_id`

Even if it is not yet active everywhere.

## Recommended Build Order

1. Add memory scope field
2. Add candidate extraction rules
3. Add short-term vs long-term persistence logic
4. Add short-term expiry
5. Improve prompt assembly order
6. Refine memory display by type

## What Not To Build Yet

Do not build yet:

- full memory graph
- vector search stack
- semantic retrieval service
- heavy manual editing workflows
- per-companion deep memory branching
- cloud memory sync

## Success Criteria

Phase 2 memory is successful when:

- the companion feels more consistent,
- memory feels more relevant,
- useless memory buildup is reduced,
- the user still feels low management burden,
- and the system is structurally ready for later companion-scoped memory.

## Summary

Phase 2 memory is not about making memory bigger.

It is about making memory:

- smaller,
- more selective,
- more structured,
- and more useful.
