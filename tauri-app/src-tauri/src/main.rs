#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Manager};

const MAIN_WINDOW_LABEL: &str = "main";

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
fn quit_app(app: AppHandle) {
    app.exit(0);
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
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
        .invoke_handler(tauri::generate_handler![show_main_window, hide_main_window, quit_app])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
