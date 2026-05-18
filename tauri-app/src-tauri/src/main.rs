#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Manager};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};

const MAIN_WINDOW_LABEL: &str = "main";
const CHAT_WINDOW_LABEL: &str = "chat";
const SETTINGS_WINDOW_LABEL: &str = "settings";
const MODEL_WINDOW_LABEL: &str = "model";
const BACKEND_PUBLIC_URL: &str = "http://119.91.32.174:8080";

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

            let app_handle = app.handle().clone();
            TrayIconBuilder::with_id("main-tray")
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
        .invoke_handler(tauri::generate_handler![show_main_window, hide_main_window, show_chat_window, hide_chat_window, show_settings_window, hide_settings_window, show_model_window, hide_model_window, quit_app, get_backend_base_url])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
