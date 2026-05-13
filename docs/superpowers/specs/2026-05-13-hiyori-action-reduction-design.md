# Hiyori Action Reduction Design

## Goal

Temporarily remove Hiyori's recently added region-triggered actions except for the existing `shake` implementation, while preserving click feedback.

## Scope

- Keep region hit detection unchanged.
- Keep region click logging unchanged.
- Keep lightweight click feedback such as focus movement unchanged.
- Disable Hiyori region-triggered actions for `face`, `chest`, `arms`, `belly`, and `legs`.
- Do not remove the underlying `shake` implementation from the codebase.
- Do not change behavior for `chitose` or other characters.

## Recommended Approach

Use the smallest possible behavior change in `tauri-app/src/main.ts`:

- For Hiyori region handlers, stop calling `triggerHiyoriAction(...)` for all current regions.
- Leave the surrounding region logging and `animateFocus(...)` calls in place.
- Leave `HIYORI_ACTIONS`, action handlers, and `shake` implementation in place so they can be reused later.

## Behavior After Change

- Clicking Hiyori's face, chest, arms, belly, or legs still counts as a click interaction.
- Region logs such as `ACTION: region-face for hiyori` still appear.
- Focus animation still runs.
- No Hiyori action animation is triggered from those region clicks.

## Testing

- Update any tests that currently expect Hiyori region clicks to trigger `nod`, `chinRest`, `wave`, `reject`, or `crouch`.
- Verify that click interactions still produce region logs.
- Verify that no `hiyori-*-module` action log is emitted for those disabled region clicks.

## Risks

- The debug action registry may still list disabled actions because the implementations remain registered. This is acceptable for this temporary rollback because runtime region behavior is the only target change.
