#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Manager};
use serde::Serialize;
use serde_json::Value;
use serde_json::json;
use std::collections::HashMap;
use std::fs;
#[cfg(windows)]
use std::os::windows::fs::MetadataExt;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, LazyLock, Mutex};
use std::thread;
use std::time::{SystemTime, UNIX_EPOCH};

const MAIN_WINDOW_LABEL: &str = "main";
const CHAT_WINDOW_LABEL: &str = "chat";
const SETTINGS_WINDOW_LABEL: &str = "settings";
const MODEL_WINDOW_LABEL: &str = "model";
const CLEANUP_WINDOW_LABEL: &str = "cleanup";
const POMODORO_WINDOW_LABEL: &str = "pomodoro";
const BACKEND_PUBLIC_URL: &str = "http://119.91.32.174:8080";
const FRONTEND_CONFIG_FILE_NAME: &str = "frontend-config.json";
const FRONTEND_HISTORY_FILE_NAME: &str = "frontend-history.json";
const FRONTEND_MEMORY_FILE_NAME: &str = "frontend-memory.json";
const FRONTEND_USER_PROFILE_FILE_NAME: &str = "user_profile.md";
const FRONTEND_PREFERENCES_FILE_NAME: &str = "preferences.md";
const FRONTEND_REFLECTION_FILE_NAME: &str = "reflection.md";
const FRONTEND_INTERACTION_RULES_FILE_NAME: &str = "interaction_rules.md";
const SPEECH_RUNTIME_DIR_NAME: &str = "speech-runtime";
const SPEECH_CLI_FILE_NAME: &str = "whisper-cli.exe";
const SPEECH_MODEL_FILE_NAME: &str = "ggml-base.bin";
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;
#[cfg(windows)]
const FILE_ATTRIBUTE_REPARSE_POINT: u32 = 0x0400;
const CLEANUP_ROOT_SCAN_DEPTH: usize = 2;
const CLEANUP_CHILD_SCAN_DEPTH: usize = 2;
const CLEANUP_TARGETED_SCAN_DEPTH: usize = 4;
const CLEANUP_SOFTWARE_SCAN_DEPTH: usize = 2;
const CLEANUP_USERS_SCAN_DEPTH: usize = 2;
const CLEANUP_MIN_RESULT_BYTES: u64 = 150 * 1024 * 1024;
const CLEANUP_MIN_DRILLDOWN_BYTES: u64 = 50 * 1024 * 1024;
const CLEANUP_UNINSTALL_STALE_DAYS: u64 = 90;

#[derive(Serialize, Clone)]
struct CleanupCandidate {
    display_name: String,
    software_name: Option<String>,
    path: String,
    category: String,
    size_bytes: u64,
    size_label: String,
    priority: String,
    advice: String,
    tier: String,
    risk_level: String,
    suggested_action: String,
    reason_short: String,
    stale_days: Option<u64>,
}

#[derive(Serialize, Clone)]
struct CleanupDeepScanTaskSnapshot {
    task_id: String,
    status: String,
    progress: u8,
    message: String,
    results: Vec<CleanupCandidate>,
    error: Option<String>,
}

struct CleanupDeepScanTask {
    snapshot: CleanupDeepScanTaskSnapshot,
    cancelled: Arc<AtomicBool>,
}

static CLEANUP_DEEP_SCAN_TASKS: LazyLock<Mutex<HashMap<String, CleanupDeepScanTask>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

fn classify_slimming_subdir(name: &str) -> Option<(&'static str, &'static str, &'static str, &'static str, &'static str)> {
    let lower = name.to_lowercase();
    if lower.contains("cache") || lower.contains("gpucache") || lower.contains("code cache") || lower.contains("temp") {
        return Some(("软件缓存", "这部分通常是软件缓存，删除后大多可以重新生成。", "safe_to_clean", "clean", "缓存可再生，适合优先瘦身。"));
    }
    if lower.contains("log") || lower.contains("crash") || lower.contains("dump") {
        return Some(("软件日志", "这部分通常是日志或崩溃记录。近期不需要排查问题时，可以优先清理。", "safe_to_clean", "clean", "日志和崩溃记录通常可清理。"));
    }
    if lower.contains("download") || lower.contains("update") || lower.contains("installer") || lower.contains("package") || lower.contains("backup") {
        return Some(("软件历史文件", "这部分更像下载残留、更新包或备份文件，建议先查看内容再处理。", "review_recommended", "open_for_review", "历史下载或更新残留更适合先查看。"));
    }
    if lower.contains("draft") || lower.contains("project") || lower.contains("export") || lower.contains("media") || lower.contains("resource") {
        return Some(("软件工作数据", "这部分可能包含草稿、导出、媒体或项目文件，建议先确认是否还需要。", "review_recommended", "open_for_review", "可能是草稿、导出或项目数据，先确认再处理。"));
    }
    None
}

fn build_cleanup_display_name(path: &PathBuf) -> String {
    path.file_name()
        .and_then(|name| name.to_str())
        .map(|name| name.trim().to_string())
        .filter(|name| !name.is_empty())
        .unwrap_or_else(|| path.display().to_string())
}

fn is_priority_high(category: &str, tier: &str, size_bytes: u64) -> bool {
    if tier == "do_not_delete_directly" {
        return false;
    }
    if category == "已安装软件" {
        return size_bytes >= 4 * 1024 * 1024 * 1024;
    }
    size_bytes >= 2 * 1024 * 1024 * 1024
}

fn build_priority_label(category: &str, tier: &str, size_bytes: u64) -> String {
    if tier == "do_not_delete_directly" {
        return "提示".to_string();
    }
    if is_priority_high(category, tier, size_bytes) {
        return "高".to_string();
    }
    if size_bytes >= 700 * 1024 * 1024 {
        return "中".to_string();
    }
    "低".to_string()
}

fn format_size_label(size_bytes: u64) -> String {
    let gb = size_bytes as f64 / 1024_f64 / 1024_f64 / 1024_f64;
    if gb >= 1.0 {
        format!("{gb:.2} GB")
    } else {
        let mb = size_bytes as f64 / 1024_f64 / 1024_f64;
        format!("{mb:.0} MB")
    }
}

fn classify_cleanup_category(path: &PathBuf) -> (String, String, String, String, String, String) {
    let lower = path.to_string_lossy().to_lowercase();
    if lower.contains("program files\\") || lower.contains("program files (x86)\\") || lower.contains("appdata\\local\\programs\\") {
        return (
            "已安装软件".to_string(),
            "这是已安装软件目录。体积大时更适合通过系统卸载应用，而不是直接删除文件夹。".to_string(),
            "review_recommended".to_string(),
            "medium".to_string(),
            "uninstall_app".to_string(),
            "这是已安装软件，优先考虑卸载不常用的应用。".to_string(),
        );
    }
    if path.is_file() {
        return (
            "大文件".to_string(),
            "这是单个大文件。确认不再需要后，可以考虑删除、移动到其他盘，或归档到外部存储。".to_string(),
            "review_recommended".to_string(),
            "medium".to_string(),
            "open_for_review".to_string(),
            "大文件需要人工确认后再处理。".to_string(),
        );
    }
    if lower == "c:\\windows" || lower.starts_with("c:\\windows\\") {
        return (
            "系统目录".to_string(),
            "这是 Windows 系统目录，占用大不代表可以直接删除。建议只通过系统自带清理或进一步定位到具体缓存子目录后再处理。".to_string(),
            "do_not_delete_directly".to_string(),
            "high".to_string(),
            "show_info_only".to_string(),
            "系统目录只适合查看，不适合直接删除。".to_string(),
        );
    }
    if lower == "c:\\program files" || lower == "c:\\program files (x86)" || lower.contains("program files") {
        return (
            "软件目录".to_string(),
            "这里主要是已安装软件本体。体积大时优先考虑卸载不用的软件，不要手动删安装目录里的文件。".to_string(),
            "do_not_delete_directly".to_string(),
            "high".to_string(),
            "uninstall_app".to_string(),
            "软件目录应优先通过卸载处理。".to_string(),
        );
    }
    if lower.contains("downloads") || lower.contains("desktop") || lower.contains("documents") || lower.contains("pictures") || lower.contains("videos") || lower.contains("music") {
        return (
            "用户目录".to_string(),
            "这里更可能是用户自己的文件、安装包或素材。建议先打开看内容，再决定删除、移动还是归档。".to_string(),
            "review_recommended".to_string(),
            "medium".to_string(),
            "open_for_review".to_string(),
            "这是用户资产目录，先看内容再处理更安全。".to_string(),
        );
    }
    if lower.contains("appdata\\roaming") {
        return (
            "用户目录".to_string(),
            "这是应用配置和账户状态目录，通常不建议直接删除。可以先定位具体缓存子目录。".to_string(),
            "do_not_delete_directly".to_string(),
            "high".to_string(),
            "show_info_only".to_string(),
            "Roaming 常包含应用配置和登录状态。".to_string(),
        );
    }
    if lower.contains("appdata") || lower.contains("users\\") {
        return (
            "用户目录".to_string(),
            "这是用户数据目录。建议先打开看看具体是哪类文件在占空间，再决定清缓存、迁移资料还是删除旧文件。".to_string(),
            "review_recommended".to_string(),
            "medium".to_string(),
            "open_for_review".to_string(),
            "用户目录适合先查看，不适合直接清理。".to_string(),
        );
    }
    if lower.contains("windows\\temp") {
        return (
            "临时文件".to_string(),
            "这是系统临时目录。只建议先查看较旧的临时文件，不要批量删除看不懂的系统内容。拿不准时优先用系统存储设置清理。".to_string(),
            "safe_to_clean".to_string(),
            "low".to_string(),
            "clean".to_string(),
            "命中系统临时目录，通常可安全清理旧文件。".to_string(),
        );
    }
    if lower.contains("temp") {
        return (
            "临时文件".to_string(),
            "优先检查这里，通常是安装残留、临时解压和运行缓存。确认不是正在使用的内容后，再手动清理。".to_string(),
            "safe_to_clean".to_string(),
            "low".to_string(),
            "clean".to_string(),
            "临时目录可再生性强，通常优先清理。".to_string(),
        );
    }
    if lower.contains("cache") {
        return (
            "缓存".to_string(),
            "这是缓存目录，通常可以重新生成。建议先看体积大的缓存，再按需清理。".to_string(),
            "safe_to_clean".to_string(),
            "low".to_string(),
            "clean".to_string(),
            "缓存目录通常可以重新生成，风险较低。".to_string(),
        );
    }
    if lower.contains("log") || lower.contains("crash") {
        return (
            "日志/崩溃记录".to_string(),
            "如果近期不需要排查问题，可以优先清理较老的日志和崩溃转储文件。".to_string(),
            "safe_to_clean".to_string(),
            "low".to_string(),
            "clean".to_string(),
            "日志和崩溃记录通常是可再生的低风险项。".to_string(),
        );
    }
    (
        "大目录".to_string(),
        "这是占用空间较大的目录，建议先打开看看具体内容，再决定是否手动清理。".to_string(),
        "review_recommended".to_string(),
        "medium".to_string(),
        "open_for_review".to_string(),
        "目录较大，但需要先看具体内容。".to_string(),
    )
}

fn is_reparse_point(metadata: &fs::Metadata) -> bool {
    #[cfg(windows)]
    {
        metadata.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0
    }

    #[cfg(not(windows))]
    {
        let _ = metadata;
        false
    }
}

fn is_scan_cancelled(cancelled: Option<&Arc<AtomicBool>>) -> bool {
    cancelled.is_some_and(|flag| flag.load(Ordering::Relaxed))
}

fn folder_metrics_recursive(path: &PathBuf, max_depth: Option<usize>, cancelled: Option<&Arc<AtomicBool>>) -> (u64, Option<SystemTime>) {
    fn inner(path: &PathBuf, depth: usize, max_depth: Option<usize>, cancelled: Option<&Arc<AtomicBool>>) -> (u64, Option<SystemTime>) {
        if is_scan_cancelled(cancelled) {
            return (0, None);
        }
        if max_depth.is_some_and(|limit| depth > limit) {
            return (0, None);
        }

        let metadata = match fs::symlink_metadata(path) {
            Ok(metadata) => metadata,
            Err(_) => return (0, None),
        };

        if is_reparse_point(&metadata) {
            return (0, None);
        }

        let mut latest_modified = metadata.modified().ok();

        if metadata.is_file() {
            return (metadata.len(), latest_modified);
        }

        if !metadata.is_dir() {
            return (0, latest_modified);
        }

        let entries = match fs::read_dir(path) {
            Ok(entries) => entries,
            Err(_) => return (0, latest_modified),
        };

        let mut total = 0_u64;
        for entry in entries.flatten() {
            if is_scan_cancelled(cancelled) {
                break;
            }
            let (size_bytes, child_modified) = inner(&entry.path(), depth + 1, max_depth, cancelled);
            total = total.saturating_add(size_bytes);
            if let Some(child_modified) = child_modified {
                latest_modified = match latest_modified {
                    Some(current) if current >= child_modified => Some(current),
                    _ => Some(child_modified),
                };
            }
        }

        (total, latest_modified)
    }

    inner(path, 0, max_depth, cancelled)
}

fn folder_size_recursive(path: &PathBuf, max_depth: Option<usize>) -> u64 {
    folder_metrics_recursive(path, max_depth, None).0
}

fn days_since(time: SystemTime) -> Option<u64> {
    SystemTime::now().duration_since(time).ok().map(|duration| duration.as_secs() / 86_400)
}

fn push_cleanup_candidate(results: &mut Vec<CleanupCandidate>, path: PathBuf, max_depth: Option<usize>) {
    if !path.exists() {
        return;
    }

    let (size_bytes, latest_modified) = folder_metrics_recursive(&path, max_depth, None);

    if size_bytes < CLEANUP_MIN_RESULT_BYTES {
        return;
    }

    let (category, advice, tier, risk_level, suggested_action, reason_short) = classify_cleanup_category(&path);
    let priority = build_priority_label(&category, &tier, size_bytes);
    results.push(CleanupCandidate {
        display_name: build_cleanup_display_name(&path),
        software_name: None,
        path: path.display().to_string(),
        category,
        size_bytes,
        size_label: format_size_label(size_bytes),
        priority,
        advice,
        tier,
        risk_level,
        suggested_action,
        reason_short,
        stale_days: latest_modified.and_then(days_since),
    });
}

fn build_cleanup_candidate(path: PathBuf, size_bytes: u64) -> Option<CleanupCandidate> {
    if size_bytes < CLEANUP_MIN_DRILLDOWN_BYTES {
        return None;
    }

    let (category, advice, tier, risk_level, suggested_action, reason_short) = classify_cleanup_category(&path);
    let priority = build_priority_label(&category, &tier, size_bytes);

    Some(CleanupCandidate {
        display_name: build_cleanup_display_name(&path),
        software_name: None,
        path: path.display().to_string(),
        category,
        size_bytes,
        size_label: format_size_label(size_bytes),
        priority,
        advice,
        tier,
        risk_level,
        suggested_action,
        reason_short,
        stale_days: None,
    })
}

fn build_install_app_candidate(path: PathBuf, size_bytes: u64, latest_modified: Option<SystemTime>) -> Option<CleanupCandidate> {
    if size_bytes < CLEANUP_MIN_RESULT_BYTES {
        return None;
    }

    let stale_days = latest_modified.and_then(days_since);
    let should_recommend_uninstall = stale_days.is_some_and(|days| days >= CLEANUP_UNINSTALL_STALE_DAYS);
    let priority = build_priority_label("已安装软件", "review_recommended", size_bytes);
    let advice = if should_recommend_uninstall {
        format!("这是安装软件目录，估算体积较大，而且最近约 {} 天没有明显活动迹象。更适合先确认是否还在用，再通过系统卸载。", stale_days.unwrap_or(CLEANUP_UNINSTALL_STALE_DAYS))
    } else {
        "这是安装软件目录。即使体积较大，也建议先确认是否仍在使用，再决定是否卸载。".to_string()
    };
    let reason_short = if should_recommend_uninstall {
        format!("体积较大，且最近约 {} 天没有明显活动迹象。", stale_days.unwrap_or(CLEANUP_UNINSTALL_STALE_DAYS))
    } else {
        "这是已安装软件，需要先确认使用情况。".to_string()
    };

    Some(CleanupCandidate {
        display_name: build_cleanup_display_name(&path),
        software_name: Some(build_cleanup_display_name(&path)),
        path: path.display().to_string(),
        category: "已安装软件".to_string(),
        size_bytes,
        size_label: format_size_label(size_bytes),
        priority,
        advice,
        tier: "review_recommended".to_string(),
        risk_level: if should_recommend_uninstall { "medium".to_string() } else { "high".to_string() },
        suggested_action: if should_recommend_uninstall { "uninstall_app".to_string() } else { "open_for_review".to_string() },
        reason_short,
        stale_days,
    })
}

fn build_appdata_slimming_candidate(software_root: &PathBuf, child_path: PathBuf, size_bytes: u64, latest_modified: Option<SystemTime>) -> Option<CleanupCandidate> {
    if size_bytes < CLEANUP_MIN_RESULT_BYTES {
        return None;
    }
    let child_name = build_cleanup_display_name(&child_path);
    let (category, advice, tier, suggested_action, reason_short) = classify_slimming_subdir(&child_name)?;
    let priority = build_priority_label(category, tier, size_bytes);
    Some(CleanupCandidate {
        display_name: format!("{} · {}", build_cleanup_display_name(software_root), child_name),
        software_name: Some(build_cleanup_display_name(software_root)),
        path: child_path.display().to_string(),
        category: category.to_string(),
        size_bytes,
        size_label: format_size_label(size_bytes),
        priority,
        advice: advice.to_string(),
        tier: tier.to_string(),
        risk_level: if tier == "safe_to_clean" { "low".to_string() } else { "medium".to_string() },
        suggested_action: suggested_action.to_string(),
        reason_short: reason_short.to_string(),
        stale_days: latest_modified.and_then(days_since),
    })
}

fn collect_top_level_candidates(root: &PathBuf) -> Vec<PathBuf> {
    let mut candidates = Vec::new();
    let entries = match fs::read_dir(root) {
        Ok(entries) => entries,
        Err(_) => return candidates,
    };

    for entry in entries.flatten() {
        let path = entry.path();
        let metadata = match fs::symlink_metadata(&path) {
            Ok(metadata) => metadata,
            Err(_) => continue,
        };
        if is_reparse_point(&metadata) || !metadata.is_dir() {
            continue;
        }
        candidates.push(path);
    }

    candidates
}

fn build_install_root_candidates(local_app_data: &PathBuf) -> Vec<PathBuf> {
    let mut roots = vec![
        PathBuf::from("C:\\Program Files"),
        PathBuf::from("C:\\Program Files (x86)"),
        local_app_data.join("Programs"),
    ];
    roots.retain(|path| path.exists());
    roots
}

fn collect_install_app_candidates(local_app_data: &PathBuf) -> Vec<PathBuf> {
    let mut apps = Vec::new();
    for root in build_install_root_candidates(local_app_data) {
        apps.extend(collect_top_level_candidates(&root));
    }
    apps
}

fn collect_users_focus_candidates(user_profile: &PathBuf, local_app_data: &PathBuf, roaming_app_data: &PathBuf) -> Vec<PathBuf> {
    let mut results = collect_top_level_candidates(user_profile);
    results.extend(collect_top_level_candidates(local_app_data));
    results.extend(collect_top_level_candidates(roaming_app_data));
    let local_low = user_profile.join("AppData").join("LocalLow");
    results.extend(collect_top_level_candidates(&local_low));
    results
}

fn analyze_install_app_candidates(local_app_data: &PathBuf) -> Vec<CleanupCandidate> {
    let mut results = Vec::new();
    for path in collect_install_app_candidates(local_app_data) {
        let (size_bytes, latest_modified) = folder_metrics_recursive(&path, Some(CLEANUP_SOFTWARE_SCAN_DEPTH), None);
        if let Some(candidate) = build_install_app_candidate(path, size_bytes, latest_modified) {
            results.push(candidate);
        }
    }
    results.sort_by(|left, right| right.size_bytes.cmp(&left.size_bytes));
    results.truncate(12);
    results
}

fn analyze_install_app_candidates_with_cancel(local_app_data: &PathBuf, cancelled: &Arc<AtomicBool>) -> Vec<CleanupCandidate> {
    let mut results = Vec::new();
    for path in collect_install_app_candidates(local_app_data) {
        if is_scan_cancelled(Some(cancelled)) {
            break;
        }
        let (size_bytes, latest_modified) = folder_metrics_recursive(&path, Some(CLEANUP_SOFTWARE_SCAN_DEPTH), Some(cancelled));
        if let Some(candidate) = build_install_app_candidate(path, size_bytes, latest_modified) {
            results.push(candidate);
        }
    }
    results.sort_by(|left, right| right.size_bytes.cmp(&left.size_bytes));
    results.truncate(12);
    results
}

fn analyze_appdata_software_slimming_candidates(local_app_data: &PathBuf, roaming_app_data: &PathBuf, user_profile: &PathBuf) -> Vec<CleanupCandidate> {
    let mut results = Vec::new();
    let local_low = user_profile.join("AppData").join("LocalLow");
    for software_root in collect_users_focus_candidates(user_profile, local_app_data, roaming_app_data)
        .into_iter()
        .chain(collect_top_level_candidates(&local_low).into_iter())
    {
        let entries = match fs::read_dir(&software_root) {
            Ok(entries) => entries,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let child_path = entry.path();
            let metadata = match fs::symlink_metadata(&child_path) {
                Ok(metadata) => metadata,
                Err(_) => continue,
            };
            if is_reparse_point(&metadata) {
                continue;
            }
            let child_name = child_path.file_name().and_then(|name| name.to_str()).unwrap_or("");
            if classify_slimming_subdir(child_name).is_none() {
                continue;
            }
            let (size_bytes, latest_modified) = folder_metrics_recursive(&child_path, Some(CLEANUP_CHILD_SCAN_DEPTH), None);
            if let Some(candidate) = build_appdata_slimming_candidate(&software_root, child_path, size_bytes, latest_modified) {
                results.push(candidate);
            }
        }
    }
    results.sort_by(|left, right| right.size_bytes.cmp(&left.size_bytes));
    results.truncate(20);
    results
}

fn analyze_cleanup_children(path: &PathBuf) -> Vec<CleanupCandidate> {
    let entries = match fs::read_dir(path) {
        Ok(entries) => entries,
        Err(_) => return Vec::new(),
    };

    let mut results = Vec::new();
    for entry in entries.flatten() {
        let entry_path = entry.path();
        let metadata = match fs::symlink_metadata(&entry_path) {
            Ok(metadata) => metadata,
            Err(_) => continue,
        };
        if is_reparse_point(&metadata) {
            continue;
        }

        let size_bytes = if metadata.is_file() {
            metadata.len()
        } else if metadata.is_dir() {
            folder_size_recursive(&entry_path, Some(CLEANUP_CHILD_SCAN_DEPTH))
        } else {
            0
        };

        if let Some(candidate) = build_cleanup_candidate(entry_path, size_bytes) {
            results.push(candidate);
        }
    }

    results.sort_by(|left, right| right.size_bytes.cmp(&left.size_bytes));
    results.truncate(20);
    results
}

fn build_targeted_cleanup_candidates(user_profile: &PathBuf, local_app_data: &PathBuf) -> Vec<PathBuf> {
    vec![
        std::env::temp_dir(),
        PathBuf::from("C:\\Windows\\Temp"),
        user_profile.join("Downloads"),
        user_profile.join("Desktop"),
        local_app_data.join("CrashDumps"),
        local_app_data.join("Microsoft").join("Windows").join("INetCache"),
        local_app_data.join("Google").join("Chrome").join("User Data").join("Default").join("Cache"),
        local_app_data.join("Microsoft").join("Edge").join("User Data").join("Default").join("Cache"),
        local_app_data.join("NVIDIA").join("DXCache"),
        local_app_data.join("pip").join("Cache"),
        local_app_data.join("npm-cache"),
    ]
}

fn collect_cleanup_full_candidates(cancelled: &Arc<AtomicBool>, mut update_progress: impl FnMut(u8, &str)) -> Vec<CleanupCandidate> {
    let mut results: Vec<CleanupCandidate> = Vec::new();
    let drive_root = PathBuf::from("C:\\");
    let user_profile = std::env::var("USERPROFILE").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("C:\\Users\\Public"));
    let local_app_data = std::env::var("LOCALAPPDATA").map(PathBuf::from).unwrap_or_else(|_| user_profile.join("AppData").join("Local"));
    let roaming_app_data = std::env::var("APPDATA").map(PathBuf::from).unwrap_or_else(|_| user_profile.join("AppData").join("Roaming"));

    update_progress(5, "正在分析重点缓存和临时目录...");
    for path in build_targeted_cleanup_candidates(&user_profile, &local_app_data) {
        if is_scan_cancelled(Some(cancelled)) {
            return Vec::new();
        }
        let (size_bytes, latest_modified) = folder_metrics_recursive(&path, None, Some(cancelled));
        if size_bytes >= CLEANUP_MIN_RESULT_BYTES {
            let (category, advice, tier, risk_level, suggested_action, reason_short) = classify_cleanup_category(&path);
            results.push(CleanupCandidate {
                display_name: build_cleanup_display_name(&path),
                software_name: None,
                path: path.display().to_string(),
                category: category.clone(),
                size_bytes,
                size_label: format_size_label(size_bytes),
                priority: build_priority_label(&category, &tier, size_bytes),
                advice,
                tier,
                risk_level,
                suggested_action,
                reason_short,
                stale_days: latest_modified.and_then(days_since),
            });
        }
    }

    update_progress(28, "正在分析安装软件体积...");
    results.extend(analyze_install_app_candidates_with_cancel(&local_app_data, cancelled));
    if is_scan_cancelled(Some(cancelled)) {
        return Vec::new();
    }

    update_progress(52, "正在分析 Users 和 AppData 目录...");
    for path in collect_users_focus_candidates(&user_profile, &local_app_data, &roaming_app_data) {
        if is_scan_cancelled(Some(cancelled)) {
            return Vec::new();
        }
        let (size_bytes, latest_modified) = folder_metrics_recursive(&path, None, Some(cancelled));
        if size_bytes >= CLEANUP_MIN_RESULT_BYTES {
            let (category, advice, tier, risk_level, suggested_action, reason_short) = classify_cleanup_category(&path);
            results.push(CleanupCandidate {
                display_name: build_cleanup_display_name(&path),
                software_name: None,
                path: path.display().to_string(),
                category: category.clone(),
                size_bytes,
                size_label: format_size_label(size_bytes),
                priority: build_priority_label(&category, &tier, size_bytes),
                advice,
                tier,
                risk_level,
                suggested_action,
                reason_short,
                stale_days: latest_modified.and_then(days_since),
            });
        }
    }

    update_progress(78, "正在分析软件可瘦身数据...");
    results.extend(analyze_appdata_software_slimming_candidates(&local_app_data, &roaming_app_data, &user_profile));
    if is_scan_cancelled(Some(cancelled)) {
        return Vec::new();
    }

    update_progress(92, "正在整理 C 盘主要大目录...");
    for path in collect_top_level_candidates(&drive_root) {
        if is_scan_cancelled(Some(cancelled)) {
            return Vec::new();
        }
        let (size_bytes, latest_modified) = folder_metrics_recursive(&path, None, Some(cancelled));
        if size_bytes >= CLEANUP_MIN_RESULT_BYTES {
            let (category, advice, tier, risk_level, suggested_action, reason_short) = classify_cleanup_category(&path);
            results.push(CleanupCandidate {
                display_name: build_cleanup_display_name(&path),
                software_name: None,
                path: path.display().to_string(),
                category: category.clone(),
                size_bytes,
                size_label: format_size_label(size_bytes),
                priority: build_priority_label(&category, &tier, size_bytes),
                advice,
                tier,
                risk_level,
                suggested_action,
                reason_short,
                stale_days: latest_modified.and_then(days_since),
            });
        }
    }

    results.sort_by(|left, right| right.size_bytes.cmp(&left.size_bytes));
    results.dedup_by(|left, right| left.path == right.path);
    results.truncate(20);
    update_progress(100, "深度分析完成，正在整理结果...");
    results
}

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
fn show_cleanup_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(CLEANUP_WINDOW_LABEL) {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn hide_cleanup_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(CLEANUP_WINDOW_LABEL) {
        let _ = window.hide();
    }
}

#[tauri::command]
fn show_pomodoro_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(POMODORO_WINDOW_LABEL) {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn hide_pomodoro_window(app: AppHandle) {
    if let Some(window) = app.get_webview_window(POMODORO_WINDOW_LABEL) {
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
fn open_windows_storage_settings() -> Result<(), String> {
    #[cfg(windows)]
    {
        let mut command = Command::new("cmd");
        command.args(["/C", "start", "", "ms-settings:storagesense"]);
        command.stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
        command.creation_flags(CREATE_NO_WINDOW);
        command.spawn().map_err(|err| format!("failed to open storage settings: {err}"))?;
        return Ok(());
    }

    #[cfg(not(windows))]
    {
        Err("storage settings shortcut is only supported on Windows right now".to_string())
    }
}

#[tauri::command]
fn open_temp_folder() -> Result<(), String> {
    let temp_dir = std::env::temp_dir();

    #[cfg(windows)]
    {
        let mut command = Command::new("explorer.exe");
        command.arg(&temp_dir);
        command.stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
        command.creation_flags(CREATE_NO_WINDOW);
        command.spawn().map_err(|err| format!("failed to open temp folder: {err}"))?;
        return Ok(());
    }

    #[cfg(not(windows))]
    {
        Err(format!("open temp folder is only supported on Windows right now: {}", temp_dir.display()))
    }
}

#[tauri::command]
fn open_path_in_explorer(path: String) -> Result<(), String> {
    let target = PathBuf::from(path);
    if !target.exists() {
        return Err("path not found".to_string());
    }

    #[cfg(windows)]
    {
        let mut command = Command::new("explorer.exe");
        command.arg(&target);
        command.stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
        command.creation_flags(CREATE_NO_WINDOW);
        command.spawn().map_err(|err| format!("failed to open path: {err}"))?;
        return Ok(());
    }

    #[cfg(not(windows))]
    {
        Err("open path is only supported on Windows right now".to_string())
    }
}

#[tauri::command]
fn scan_cleanup_candidates() -> Result<Vec<CleanupCandidate>, String> {
    #[cfg(windows)]
    {
        let mut results: Vec<CleanupCandidate> = Vec::new();
        let drive_root = PathBuf::from("C:\\");
        let user_profile = std::env::var("USERPROFILE").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("C:\\Users\\Public"));
        let local_app_data = std::env::var("LOCALAPPDATA").map(PathBuf::from).unwrap_or_else(|_| user_profile.join("AppData").join("Local"));
        let roaming_app_data = std::env::var("APPDATA").map(PathBuf::from).unwrap_or_else(|_| user_profile.join("AppData").join("Roaming"));

        for path in build_targeted_cleanup_candidates(&user_profile, &local_app_data) {
            push_cleanup_candidate(&mut results, path, Some(CLEANUP_TARGETED_SCAN_DEPTH));
        }

        results.extend(analyze_install_app_candidates(&local_app_data));
        results.extend(analyze_appdata_software_slimming_candidates(&local_app_data, &roaming_app_data, &user_profile));

        for path in collect_users_focus_candidates(&user_profile, &local_app_data, &roaming_app_data) {
            push_cleanup_candidate(&mut results, path, Some(CLEANUP_USERS_SCAN_DEPTH));
        }

        for path in collect_top_level_candidates(&drive_root) {
            push_cleanup_candidate(&mut results, path, Some(CLEANUP_ROOT_SCAN_DEPTH));
        }

        results.sort_by(|left, right| right.size_bytes.cmp(&left.size_bytes));
        results.dedup_by(|left, right| left.path == right.path);
        results.truncate(12);
        return Ok(results);
    }

    #[cfg(not(windows))]
    {
        Err("cleanup scan is only supported on Windows right now".to_string())
    }
}

#[tauri::command]
fn scan_cleanup_full_candidates() -> Result<Vec<CleanupCandidate>, String> {
    #[cfg(windows)]
    {
        let cancelled = Arc::new(AtomicBool::new(false));
        return Ok(collect_cleanup_full_candidates(&cancelled, |_progress, _message| {}));
    }

    #[cfg(not(windows))]
    {
        Err("cleanup scan is only supported on Windows right now".to_string())
    }
}

fn update_cleanup_deep_scan_task(task_id: &str, progress: u8, message: String) {
    if let Ok(mut tasks) = CLEANUP_DEEP_SCAN_TASKS.lock() {
        if let Some(task) = tasks.get_mut(task_id) {
            task.snapshot.progress = progress;
            task.snapshot.message = message;
        }
    }
}

#[tauri::command]
fn start_cleanup_deep_scan_task() -> Result<String, String> {
    #[cfg(windows)]
    {
        let task_id = format!("cleanup-deep-{}", SystemTime::now().duration_since(UNIX_EPOCH).map_err(|err| format!("failed to read system clock: {err}"))?.as_millis());
        let cancelled = Arc::new(AtomicBool::new(false));
        let snapshot = CleanupDeepScanTaskSnapshot {
            task_id: task_id.clone(),
            status: "running".to_string(),
            progress: 0,
            message: "准备开始深度分析...".to_string(),
            results: Vec::new(),
            error: None,
        };

        {
            let mut tasks = CLEANUP_DEEP_SCAN_TASKS.lock().map_err(|_| "failed to lock cleanup task state".to_string())?;
            tasks.insert(task_id.clone(), CleanupDeepScanTask { snapshot, cancelled: cancelled.clone() });
        }

        let task_id_for_thread = task_id.clone();
        thread::spawn(move || {
            let results = collect_cleanup_full_candidates(&cancelled, |progress, message| {
                update_cleanup_deep_scan_task(&task_id_for_thread, progress, message.to_string());
            });

            if let Ok(mut tasks) = CLEANUP_DEEP_SCAN_TASKS.lock() {
                if let Some(task) = tasks.get_mut(&task_id_for_thread) {
                    if task.cancelled.load(Ordering::Relaxed) {
                        task.snapshot.status = "cancelled".to_string();
                        task.snapshot.message = "已取消深度分析。".to_string();
                        task.snapshot.progress = 0;
                        task.snapshot.results.clear();
                    } else {
                        task.snapshot.status = "completed".to_string();
                        task.snapshot.progress = 100;
                        task.snapshot.message = "深度分析完成。".to_string();
                        task.snapshot.results = results;
                    }
                }
            }
        });

        return Ok(task_id);
    }

    #[cfg(not(windows))]
    {
        Err("cleanup scan is only supported on Windows right now".to_string())
    }
}

#[tauri::command]
fn get_cleanup_deep_scan_task(task_id: String) -> Result<Value, String> {
    let tasks = CLEANUP_DEEP_SCAN_TASKS.lock().map_err(|_| "failed to lock cleanup task state".to_string())?;
    let task = tasks.get(&task_id).ok_or_else(|| "cleanup task not found".to_string())?;
    serde_json::to_value(task.snapshot.clone()).map_err(|err| format!("failed to serialize cleanup task state: {err}"))
}

#[tauri::command]
fn cancel_cleanup_deep_scan_task(task_id: String) -> Result<(), String> {
    let mut tasks = CLEANUP_DEEP_SCAN_TASKS.lock().map_err(|_| "failed to lock cleanup task state".to_string())?;
    let task = tasks.get_mut(&task_id).ok_or_else(|| "cleanup task not found".to_string())?;
    task.cancelled.store(true, Ordering::Relaxed);
    task.snapshot.status = "cancelling".to_string();
    task.snapshot.message = "正在取消深度分析...".to_string();
    Ok(())
}

#[tauri::command]
fn scan_cleanup_children(path: String) -> Result<Vec<CleanupCandidate>, String> {
    #[cfg(windows)]
    {
        let target = PathBuf::from(path);
        if !target.exists() {
            return Err("path not found".to_string());
        }
        if !target.is_dir() {
            return Err("path is not a directory".to_string());
        }
        return Ok(analyze_cleanup_children(&target));
    }

    #[cfg(not(windows))]
    {
        let _ = path;
        Err("cleanup scan is only supported on Windows right now".to_string())
    }
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

fn resolve_frontend_preferences_file_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))?;
    fs::create_dir_all(&data_dir).map_err(|err| format!("failed to create app data dir: {err}"))?;
    Ok(data_dir.join(FRONTEND_PREFERENCES_FILE_NAME))
}

fn resolve_frontend_user_profile_file_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))?;
    fs::create_dir_all(&data_dir).map_err(|err| format!("failed to create app data dir: {err}"))?;
    Ok(data_dir.join(FRONTEND_USER_PROFILE_FILE_NAME))
}

fn resolve_frontend_reflection_file_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))?;
    fs::create_dir_all(&data_dir).map_err(|err| format!("failed to create app data dir: {err}"))?;
    Ok(data_dir.join(FRONTEND_REFLECTION_FILE_NAME))
}

fn resolve_frontend_interaction_rules_file_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("failed to resolve app data dir: {err}"))?;
    fs::create_dir_all(&data_dir).map_err(|err| format!("failed to create app data dir: {err}"))?;
    Ok(data_dir.join(FRONTEND_INTERACTION_RULES_FILE_NAME))
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

#[tauri::command]
fn save_frontend_user_profile_file(app: AppHandle, payload: String) -> Result<(), String> {
    let file_path = resolve_frontend_user_profile_file_path(&app)?;
    fs::write(&file_path, payload).map_err(|err| format!("failed to write frontend user profile file: {err}"))
}

#[tauri::command]
fn save_frontend_preferences_file(app: AppHandle, payload: String) -> Result<(), String> {
    let file_path = resolve_frontend_preferences_file_path(&app)?;
    fs::write(&file_path, payload).map_err(|err| format!("failed to write frontend preferences file: {err}"))
}

#[tauri::command]
fn save_frontend_reflection_file(app: AppHandle, payload: String) -> Result<(), String> {
    let file_path = resolve_frontend_reflection_file_path(&app)?;
    fs::write(&file_path, payload).map_err(|err| format!("failed to write frontend reflection file: {err}"))
}

#[tauri::command]
fn save_frontend_interaction_rules_file(app: AppHandle, payload: String) -> Result<(), String> {
    let file_path = resolve_frontend_interaction_rules_file_path(&app)?;
    fs::write(&file_path, payload).map_err(|err| format!("failed to write frontend interaction rules file: {err}"))
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
        .invoke_handler(tauri::generate_handler![show_main_window, hide_main_window, show_chat_window, hide_chat_window, show_settings_window, hide_settings_window, show_model_window, hide_model_window, show_cleanup_window, hide_cleanup_window, show_pomodoro_window, hide_pomodoro_window, quit_app, get_backend_base_url, open_windows_storage_settings, open_temp_folder, open_path_in_explorer, scan_cleanup_candidates, scan_cleanup_full_candidates, start_cleanup_deep_scan_task, get_cleanup_deep_scan_task, cancel_cleanup_deep_scan_task, scan_cleanup_children, save_temp_audio_file, get_speech_runtime_status, transcribe_audio_file, load_frontend_memory_file, save_frontend_memory_file, save_frontend_user_profile_file, save_frontend_preferences_file, save_frontend_reflection_file, save_frontend_interaction_rules_file, load_frontend_config_file, save_frontend_config_file, load_frontend_history_file, save_frontend_history_file])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
