#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Manager};
use serde_json::Value;
use serde_json::json;
use std::fs;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

const MAIN_WINDOW_LABEL: &str = "main";
const CHAT_WINDOW_LABEL: &str = "chat";
const SETTINGS_WINDOW_LABEL: &str = "settings";
const MODEL_WINDOW_LABEL: &str = "model";
const BACKEND_PUBLIC_URL: &str = "http://119.91.32.174:8080";
const FRONTEND_CONFIG_FILE_NAME: &str = "frontend-config.json";
const FRONTEND_HISTORY_FILE_NAME: &str = "frontend-history.json";
const FRONTEND_MEMORY_FILE_NAME: &str = "frontend-memory.json";
const SPEECH_RUNTIME_DIR_NAME: &str = "speech-runtime";
const SPEECH_CLI_FILE_NAME: &str = "whisper-cli.exe";
const SPEECH_MODEL_FILE_NAME: &str = "ggml-base.bin";
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

fn resolve_speech_runtime_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))?;
    Ok(data_dir.join(SPEECH_RUNTIME_DIR_NAME))
}

fn resolve_speech_runtime_paths(app: &AppHandle) -> Result<(PathBuf, PathBuf), String> {
    let runtime_dir = resolve_speech_runtime_dir(app)?;
    let cli_path = std::env::var("DESKTOP_AI_COMPANION_SPEECH_CLI")
        .map(PathBuf::from)
        .unwrap_or_else(|_| runtime_dir.join(SPEECH_CLI_FILE_NAME));
    let model_path = std::env::var("DESKTOP_AI_COMPANION_SPEECH_MODEL")
        .map(PathBuf::from)
        .unwrap_or_else(|_| runtime_dir.join(SPEECH_MODEL_FILE_NAME));

    if !cli_path.exists() {
        return Err(format!(
            "speech runtime not installed: missing {}",
            cli_path.display()
        ));
    }
    if !model_path.exists() {
        return Err(format!(
            "speech runtime not installed: missing {}",
            model_path.display()
        ));
    }

    Ok((cli_path, model_path))
}

fn normalize_transcribed_text(text: &str) -> String {
    text.split_whitespace()
        .collect::<Vec<_>>()
        .join("")
        .replace(" ，", "，")
        .replace(" 。", "。")
        .replace(" ？", "？")
        .replace(" ！", "！")
        .replace(" ：", "：")
        .replace(" ；", "；")
        .replace(" 、", "、")
        .trim()
        .to_string()
}

fn show_main_window_inner(app: &AppHandle) {
    if let Some(window) = app.get_webview_window(MAIN_WINDOW_LABEL) {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn hide_main_window_inner(app: &AppHandle) {
    if let Some(window) = app.get_webview_window(MAIN_WINDOW_LABEL) {
        let _ = window.hide();
    }
}

#[tauri::command]
fn show_main_window(app: AppHandle) {
    show_main_window_inner(&app);
}

#[tauri::command]
fn hide_main_window(app: AppHandle) {
    hide_main_window_inner(&app);
}

#[tauri::command]
fn show_chat_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(CHAT_WINDOW_LABEL) {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn hide_chat_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(CHAT_WINDOW_LABEL) {
        let _ = window.hide();
    }
}

#[tauri::command]
fn show_settings_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(SETTINGS_WINDOW_LABEL) {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn hide_settings_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(SETTINGS_WINDOW_LABEL) {
        let _ = window.hide();
    }
}

#[tauri::command]
fn show_model_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(MODEL_WINDOW_LABEL) {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn hide_model_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(MODEL_WINDOW_LABEL) {
        let _ = window.hide();
    }
}

#[tauri::command]
fn quit_app(app: AppHandle) {
    app.exit(0);
}

#[tauri::command]
fn get_backend_base_url() -> String {
    std::env::var("DESKTOP_AI_COMPANION_BACKEND_URL").unwrap_or_else(|_| BACKEND_PUBLIC_URL.to_string())
}

#[tauri::command]
fn save_temp_audio_file(payload: Vec<u8>, extension: String) -> Result<String, String> {
    let temp_dir = std::env::temp_dir().join("desktop-ai-companion-audio")
        ;
    fs::create_dir_all(&temp_dir).map_err(|err| format!("failed to create temp audio dir: {err}"))?;

    let suffix = extension.trim().trim_start_matches('.');
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|err| format!("failed to read system clock: {err}"))?
        .as_millis();
    let file_path = temp_dir.join(format!("speech-{timestamp}.{suffix}"));
    fs::write(&file_path, payload).map_err(|err| format!("failed to write temp audio file: {err}"))?;
    Ok(file_path.to_string_lossy().to_string())
}

#[tauri::command]
fn get_speech_runtime_status(app: AppHandle) -> Result<Value, String> {
    let runtime_dir = resolve_speech_runtime_dir(&app)?;
    let cli_path = std::env::var("DESKTOP_AI_COMPANION_SPEECH_CLI")
        .map(PathBuf::from)
        .unwrap_or_else(|_| runtime_dir.join(SPEECH_CLI_FILE_NAME));
    let model_path = std::env::var("DESKTOP_AI_COMPANION_SPEECH_MODEL")
        .map(PathBuf::from)
        .unwrap_or_else(|_| runtime_dir.join(SPEECH_MODEL_FILE_NAME));

    match resolve_speech_runtime_paths(&app) {
        Ok((cli_path, model_path)) => Ok(json!({
            "available": true,
            "runtime_dir": runtime_dir,
            "cli_path": cli_path,
            "model_path": model_path,
        })),
        Err(error) => Ok(json!({
            "available": false,
            "runtime_dir": runtime_dir,
            "cli_path": cli_path,
            "model_path": model_path,
            "error": error,
        })),
    }
}

#[tauri::command]
fn transcribe_audio_file(app: AppHandle, path: String) -> Result<String, String> {
    let audio_path = PathBuf::from(path);
    if !audio_path.exists() {
        return Err("audio file not found".to_string());
    }

    let (cli_path, model_path) = resolve_speech_runtime_paths(&app)?;
    let output_base = audio_path.with_extension("");

    let mut command = Command::new(&cli_path);
    command
        .arg("-m")
        .arg(&model_path)
        .arg("-f")
        .arg(&audio_path)
        .arg("-l")
        .arg("zh")
        .arg("-nt")
        .arg("-otxt")
        .arg("-of")
        .arg(&output_base);
    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);

    let output = command
        .output()
        .map_err(|err| format!("failed to launch local speech runtime: {err}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if stderr.is_empty() { "local transcription failed".to_string() } else { stderr });
    }

    let txt_path = output_base.with_extension("txt");
    if !txt_path.exists() {
        return Err(format!("transcription output not found: {}", txt_path.display()));
    }

    let raw = fs::read_to_string(&txt_path)
        .map_err(|err| format!("failed to read transcription output: {err}"))?;
    Ok(normalize_transcribed_text(&raw))
}

fn resolve_frontend_memory_file_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))?;
    fs::create_dir_all(&data_dir).map_err(|err| format!("failed to create app data dir: {err}"))?;
    Ok(data_dir.join(FRONTEND_MEMORY_FILE_NAME))
}

fn resolve_frontend_config_file_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))?;
    fs::create_dir_all(&data_dir).map_err(|err| format!("failed to create app data dir: {err}"))?;
    Ok(data_dir.join(FRONTEND_CONFIG_FILE_NAME))
}

fn resolve_frontend_history_file_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))?;
    fs::create_dir_all(&data_dir).map_err(|err| format!("failed to create app data dir: {err}"))?;
    Ok(data_dir.join(FRONTEND_HISTORY_FILE_NAME))
}

#[tauri::command]
fn load_frontend_config_file(app: AppHandle) -> Result<String, String> {
    let file_path = resolve_frontend_config_file_path(&app)?;
    if !file_path.exists() {
        return Ok("{}".to_string());
    }

    let raw = fs::read_to_string(&file_path)
        .map_err(|err| format!("failed to read frontend config file: {err}"))?;
    let _: Value = serde_json::from_str(&raw)
        .map_err(|err| format!("invalid frontend config json: {err}"))?;
    Ok(raw)
}

#[tauri::command]
fn save_frontend_config_file(app: AppHandle, payload: String) -> Result<(), String> {
    let _: Value = serde_json::from_str(&payload)
        .map_err(|err| format!("invalid frontend config payload: {err}"))?;
    let file_path = resolve_frontend_config_file_path(&app)?;
    fs::write(&file_path, payload).map_err(|err| format!("failed to write frontend config file: {err}"))
}

#[tauri::command]
fn load_frontend_history_file(app: AppHandle) -> Result<String, String> {
    let file_path = resolve_frontend_history_file_path(&app)?;
    if !file_path.exists() {
        return Ok("[]".to_string());
    }

    let raw = fs::read_to_string(&file_path)
        .map_err(|err| format!("failed to read frontend history file: {err}"))?;
    let _: Value = serde_json::from_str(&raw)
        .map_err(|err| format!("invalid frontend history json: {err}"))?;
    Ok(raw)
}

#[tauri::command]
fn save_frontend_history_file(app: AppHandle, payload: String) -> Result<(), String> {
    let _: Value = serde_json::from_str(&payload)
        .map_err(|err| format!("invalid frontend history payload: {err}"))?;
    let file_path = resolve_frontend_history_file_path(&app)?;
    fs::write(&file_path, payload).map_err(|err| format!("failed to write frontend history file: {err}"))
}

#[tauri::command]
fn load_frontend_memory_file(app: AppHandle) -> Result<String, String> {
    let file_path = resolve_frontend_memory_file_path(&app)?;
    if !file_path.exists() {
        return Ok("[]".to_string());
    }

    let raw = fs::read_to_string(&file_path)
        .map_err(|err| format!("failed to read frontend memory file: {err}"))?;
    let _: Value = serde_json::from_str(&raw)
        .map_err(|err| format!("invalid frontend memory json: {err}"))?;
    Ok(raw)
}

#[tauri::command]
fn save_frontend_memory_file(app: AppHandle, payload: String) -> Result<(), String> {
    let _: Value = serde_json::from_str(&payload)
        .map_err(|err| format!("invalid frontend memory payload: {err}"))?;
    let file_path = resolve_frontend_memory_file_path(&app)?;
    fs::write(&file_path, payload).map_err(|err| format!("failed to write frontend memory file: {err}"))
}

fn dev_backend_command() -> Command {
    let repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .expect("failed to resolve repo root")
        .to_path_buf();

    let mut cmd = Command::new("python");
    cmd.current_dir(repo_root)
        .arg("-m")
        .arg("uvicorn")
        .arg("backend.server:app")
        .arg("--host")
        .arg("0.0.0.0")
        .arg("--port")
        .arg("8080");
    cmd
}

fn start_backend(app: &AppHandle) -> Result<Option<Child>, String> {
    if !cfg!(debug_assertions) {
        return Ok(None);
    }

    let _ = app;
    let mut cmd = dev_backend_command();

    cmd.stdout(Stdio::null()).stderr(Stdio::null());
    cmd.spawn()
        .map(Some)
        .map_err(|err| format!("failed to spawn backend: {err}"))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if let Err(err) = start_backend(&app.handle()) {
                eprintln!("backend startup warning: {err}");
            }

            let show_item = MenuItem::with_id(app, "show", "显示", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &quit_item])?;
            let tray_icon = app
                .default_window_icon()
                .cloned()
                .ok_or_else(|| "default tray icon is not available".to_string())?;

            let app_handle = app.handle().clone();
            TrayIconBuilder::with_id("main-tray")
                .icon(tray_icon)
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_tray_icon_event(move |_tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window_inner(&app_handle);
                    }
                })
                .on_menu_event(move |app, event| match event.id().as_ref() {
                    "show" => show_main_window_inner(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![show_main_window, hide_main_window, show_chat_window, hide_chat_window, show_settings_window, hide_settings_window, show_model_window, hide_model_window, quit_app, get_backend_base_url, save_temp_audio_file, get_speech_runtime_status, transcribe_audio_file, load_frontend_memory_file, save_frontend_memory_file, load_frontend_config_file, save_frontend_config_file, load_frontend_history_file, save_frontend_history_file])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
