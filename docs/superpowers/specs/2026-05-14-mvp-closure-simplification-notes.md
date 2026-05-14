# MVP Closure Simplification Notes

## Purpose

Capture the product decision that the remaining MVP closure work should bias toward user simplicity, especially around memory.

## User Decision

The user explicitly clarified:

- the product should stay as simple as possible for end users,
- memory should **not** become a manual management workflow,
- users should **not** manually add memory,
- users should **not** directly modify memory entries,
- the remaining MVP closure should continue following the earlier closure direction, except memory should be simplified.

## Memory Interpretation Going Forward

Memory is still part of the MVP, but it should be expressed as:

- a small amount of option-driven companion context,
- derived from user-selected settings,
- plus lightweight system inference where appropriate,
- without exposing a heavy "knowledge base" UI.

### Good MVP memory examples

- how the companion addresses the user
- current interaction mode
- quiet vs proactive preference
- a few small preference choices the user selected in setup

### Bad MVP memory examples

- a page where users manually maintain memory notes
- editable free-form memory records
- user-managed long-term memory database behavior

## Revised Minimal Closure List

Given this simplification, the smallest remaining path to satisfy the user's MVP intent is:

1. **Fix real character visibility on desktop**
   The product cannot count as MVP-complete if the user still cannot reliably see the desktop character.

2. **Add a simple first-run companion creation/setup flow**
   This should be lightweight and guided. It should feel like "creating my companion," not configuring a dashboard.

3. **Keep memory as option-driven companion context**
   The user should choose a few simple options. The product can say it remembers preferences, but should not require memory management work.

4. **Make do-not-disturb actually work**
   The companion needs real quiet behavior, not just stored config fields.

5. **Keep settings and local-data actions simple**
   History clearing and local-data controls should exist, but without making the product feel like a settings-heavy utility app.

## Product Principle

The product should feel like:

- a calm desktop companion,
- with a little personalization,
- and very little maintenance burden.

If a feature makes the user feel like they are "managing a system" instead of "living with a companion," it is probably too heavy for the MVP.
