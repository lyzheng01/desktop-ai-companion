# Next Optimization Options Notes

## Purpose

Save the short design discussion about what the next product-optimization round should focus on after closing the P0 companion and alpha validation gaps.

## Current Confirmed State

- The code changes for the P0 companion and alpha validation round were committed to `master`.
- The latest commit at the time of this note is:
  - `4d6cb72 feat: close p0 companion and alpha validation gaps`
- Remaining worktree noise after that commit came from Rust build output under `tauri-app/src-tauri/target/debug/...`, not from uncommitted source code.

## Three Proposed Next Directions

### Option 1: More companion-like chat

Focus:

- make responses shorter and more natural,
- use recent context better,
- automatically convert nickname / preference cues into lightweight memory,
- reduce tool-tone and customer-service-tone replies.

Why it matters:

- this most directly changes whether the user feels "she is a companion" instead of "she is a wrapper around an API".

### Option 2: Tray and restore verification loop

Focus:

- add repeatable verification for hide / tray / restore flows,
- reduce the chance that desktop recovery behavior regresses,
- make the app safer to dogfood as a real desktop-resident product.

Why it matters:

- once hide/show is a real native path, losing recovery behavior would damage trust quickly.

### Option 3: Real do-not-disturb / quiet behavior

Focus:

- turn `dnd_enabled`, `dnd_start`, `dnd_end`, and `proactive_mode` from config fields into runtime behavior,
- make the companion feel calm and non-intrusive during work and rest.

Why it matters:

- this sharpens the "陪伴但不烦" product promise.

## Recommendation Given In Conversation

The recommended next direction was:

- **Option 1: More companion-like chat**

Reason:

- it most directly improves the felt experience,
- it sharpens the product's main differentiation,
- and it helps users feel that the desktop companion is more than a technical shell.

## Short Version

After the P0 gap-closure round, the next best product move is not broadening the feature surface again. It is choosing one strong next layer of felt experience.

The strongest recommendation from the discussion was:

- make the chat feel more like a desktop companion and less like a model endpoint.
