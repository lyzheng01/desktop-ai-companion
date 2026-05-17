# Model Selection And External Import Design

## Goal

Design a model-selection experience that scales beyond a handful of built-in models, while supporting later expansion through imported user models.

The immediate problem is that the current right-click menu does not scale if every model is listed directly in the menu.

## Product Intent

The model experience should feel like:

- lightweight,
- understandable,
- expandable,
- visually tidy.

It should **not** feel like:

- a long technical file picker,
- a bloated right-click menu,
- or a developer-only asset list.

## Core Decision

The user approved this direction:

1. the right-click menu should no longer show every model directly,
2. the right-click menu should instead expose a single `选择模型` entry,
3. clicking it should open a model-selection panel,
4. external models should be handled as a separate import path,
5. zip import can come later,
6. first support should focus on built-in models plus already-unzipped external model folders.

## Why The Current Menu Model Fails

The current menu works for a few built-in roles, but it breaks down once many models exist.

Problems:

- the menu becomes too long,
- model discovery becomes harder,
- users cannot easily understand which model is current,
- future search/filter/preview options become awkward.

So the menu should stop being the primary browsing surface.

## Recommended Structure

Split the feature into two independent product tasks.

### Task A: Model Selection Panel

This is the immediate UI cleanup and scaling solution.

Scope:

- keep right-click menu minimal,
- add a dedicated model selection panel,
- list built-in models there,
- show the current active model,
- switch models from the panel.

### Task B: External Model Import

This is the expansion path.

Scope:

- allow importing already-unzipped model folders,
- copy imported models into an app-managed library,
- expose them in the selection panel,
- leave zip import for later.

These should remain separate tasks.

## Recommended UX

### Right-click menu

The menu should become:

- 选择模型
- 隐藏
- 设置
- 退出

This keeps it short and usable.

### Model selection panel

The panel should be a lightweight selection surface, not a full asset manager.

Minimum contents:

- current active model summary,
- model list,
- built-in vs imported grouping,
- switch action.

Optional later additions:

- search,
- model preview image,
- favorites,
- tags.

## Two-Source Model System

The system should distinguish two model sources.

### 1. Built-in models

These come from the repo-controlled library, such as:

- `assets/live2d/...`

These are trusted, stable, and bundled with the app.

### 2. Imported models

These come from user-provided external folders.

The app should not depend on the original `Downloads` path long-term.

Instead:

- the user selects an already-unzipped folder,
- the app validates it,
- the app copies it into an app-managed model library,
- the model becomes selectable from there.

This avoids fragile absolute-path dependence on `Downloads`.

## Why Not Read Downloads Directly Forever

Using `Downloads` as a live runtime source is fragile because:

- files move,
- names change,
- zip archives may not be extracted,
- unrelated clutter accumulates,
- model references become unreliable.

So `Downloads` should be treated as a temporary input source, not the permanent asset library.

## MVP Import Rule

For the next implementation step, support only:

- already-unzipped model folders,
- where a valid `*.model3.json` can be found.

Do **not** support yet:

- zip ingestion,
- automatic extraction,
- partial malformed folder repair,
- remote downloads.

## Validation Rule For Imported Models

An imported folder should only be accepted if:

- a `model3.json` file exists,
- the referenced textures and runtime files are present,
- the app can resolve the files after copying them into its own library.

If validation fails, the UI should reject the import with a simple user-facing message.

## Minimal Data Model

Each selectable model entry should have at least:

- `id`
- `name`
- `source` (`builtin` or `imported`)
- `model_path`
- `is_active`

Optional later fields:

- `preview_path`
- `author`
- `license_note`
- `tags`

## Recommended Technical Direction

### Built-in layer

The app should stop hardcoding the full model list only inside front-end source.

Instead, the model list should move toward a backend-servable registry or a shared model manifest.

For the first cleanup step, it is acceptable to keep a frontend-backed list if the selection panel is introduced first.

### Imported layer

Imported models should be copied into a stable app-managed directory, for example:

- app data model library,
- or a managed local models folder inside the project during development.

The selection panel should treat built-in and imported models through the same UI model.

## Visual Behavior

The model panel should emphasize clarity over density.

Recommended list item contents:

- model display name,
- source label (`内置` / `导入`),
- current-state badge (`当前使用中`),
- switch button.

Do not try to build a card gallery yet unless you already have stable preview assets.

## Recommended Implementation Order

### First implementation task

1. replace the long model list in the context menu with `选择模型`
2. add a model-selection panel
3. list all built-in models there
4. show current model clearly
5. switch current model from the panel

### Second implementation task

1. add imported-model registry support
2. add folder-based import flow for already-unzipped models
3. copy imported models into managed storage
4. show imported models in the same panel

### Third implementation task (later)

1. zip import
2. search/filter
3. preview assets
4. favorites or premium gating

## Non-Goals

Do not include yet:

- zip auto-import,
- giant gallery browser,
- cloud model sync,
- marketplace,
- license-management workflow,
- auto-scan the entire `Downloads` directory on every launch.

## Acceptance Criteria

This design is successful when:

- right-click menu stays short,
- users can find and switch models without a huge menu,
- built-in models remain easy to access,
- imported models have a clean future path,
- the app no longer depends on `Downloads` as its permanent runtime source.

## Recommendation Summary

The best next move is not to keep expanding the right-click menu.

It is:

> keep the context menu small, move model browsing into a dedicated panel, and treat external models as imported assets instead of live `Downloads` files.
