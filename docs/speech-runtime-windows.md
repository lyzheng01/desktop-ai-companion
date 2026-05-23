# Windows Local Speech Runtime

## Goal

Use local speech-to-text on Windows without requiring the user to install Python.

## Expected Runtime Directory

By default the app looks for the local speech runtime in:

`%APPDATA%\\com.ai-companion.desktop\\speech-runtime\\`

On this machine that resolves to a path like:

`C:\Users\lenovo\AppData\Roaming\com.ai-companion.desktop\speech-runtime\`

## Required Files

Place these files in that directory:

- `whisper-cli.exe`
- `ggml-base.bin`

## Optional Overrides

You can override the default paths with environment variables:

- `DESKTOP_AI_COMPANION_SPEECH_CLI`
- `DESKTOP_AI_COMPANION_SPEECH_MODEL`

## Current Behavior

When the user enters voice mode, the app first checks whether the runtime exists.

- If both files are present, the app will try local speech recognition.
- If either file is missing, the app shows a clear setup message instead of trying the old Python path.

## Notes

- This document only covers the runtime layout and detection path.
- The actual `whisper-cli.exe` binary and model file still need to be provided separately.
