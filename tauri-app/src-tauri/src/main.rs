#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// 命令：退出应用
#[tauri::command]
fn quit_app(app: tauri::AppHandle) {
    app.exit(0);
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![quit_app])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
