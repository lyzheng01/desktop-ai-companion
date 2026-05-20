import shutil
import subprocess
import sys
import time
import os
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "tauri-app" / "dist"
OUTPUT_DIR = REPO_ROOT / "exports" / "promo-clips"
FRONTEND_URL = "http://127.0.0.1:4175"
NPM_COMMAND = "npm.cmd" if sys.platform == "win32" else "npm"
VIDEO_PRESETS = {
    "portrait": {"width": 540, "height": 960},
    "landscape": {"width": 1280, "height": 720},
    "square": {"width": 1080, "height": 1080},
}


def wait_for_http_server(url: str, timeout_seconds: float = 20.0) -> None:
    import requests

    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code < 500:
                return
        except Exception as error:
            last_error = error
        time.sleep(0.2)

    raise RuntimeError(f"Timed out waiting for {url}") from last_error


def start_static_server() -> subprocess.Popen:
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "4175", "--bind", "127.0.0.1"],
        cwd=DIST_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_for_http_server(FRONTEND_URL)
    return process


def find_ffmpeg() -> str | None:
    env_path = os.getenv("FFMPEG_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    candidates = [
        shutil.which("ffmpeg"),
        shutil.which("ffmpeg.exe"),
    ]
    for candidate in candidates:
        if candidate:
            return candidate
    return None


def convert_webm_to_mp4(webm_path: Path) -> Path | None:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return None

    mp4_path = webm_path.with_suffix(".mp4")
    if mp4_path.exists():
        mp4_path.unlink()

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i", str(webm_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(mp4_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return mp4_path


def parse_args() -> tuple[str, list[str]]:
    preset = "portrait"
    scenarios: list[str] = []
    args = iter(sys.argv[1:])
    for arg in args:
        if arg == "--preset":
            preset = next(args, "portrait").strip().lower() or "portrait"
            continue
        scenarios.append(arg)
    if preset not in VIDEO_PRESETS:
        raise SystemExit(f"Unknown preset: {preset}. Use one of: {', '.join(VIDEO_PRESETS)}")
    return preset, scenarios


def mock_backend(page) -> None:
    active_companion = {
        "id": 1,
        "name": "Mao",
        "character_type": "mao_pro_zh",
        "personality_tags": ["温柔"],
        "interaction_mode": "work",
        "is_active": True,
    }

    def route_handler(route) -> None:
        url = route.request.url
        method = route.request.method

        if method == "GET" and url.endswith("/companions/active"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(active_companion, ensure_ascii=False))
            return

        if method == "GET" and url.endswith("/companions"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps([active_companion], ensure_ascii=False))
            return

        if method == "POST" and "/companions/" in url and url.endswith("/activate"):
            route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')
            return

        if method == "GET" and url.endswith("/models/imported"):
            route.fulfill(status=200, content_type="application/json", body="[]")
            return

        if method == "GET" and url.endswith("/models/catalog"):
            route.fulfill(status=200, content_type="application/json", body="[]")
            return

        if method == "GET" and url.endswith("/proactive/weather?location=合肥"):
            route.fulfill(status=200, content_type="application/json", body='{"trigger":"weather_update","content":"合肥今天多云，出门记得带上好心情。"}')
            return

        if method == "GET" and url.endswith("/proactive/followup"):
            route.fulfill(status=200, content_type="application/json", body='{"trigger":"care_followup","content":"主人，今天也别太辛苦啦。"}')
            return

        if method == "POST" and url.endswith("/chat/stream"):
            route.fulfill(
                status=200,
                headers={"Content-Type": "text/event-stream"},
                body=(
                    "event: state\n"
                    "data: thinking\n\n"
                    "event: phase\n"
                    "data: composing\n\n"
                    "event: assistant_delta\n"
                    "data: 主人，我在呢。今天也一起慢慢来吧。\n\n"
                    "event: done\n"
                    "data: done\n\n"
                ),
            )
            return

        route.continue_()

    page.route("**/*", route_handler)


def install_tauri_mocks(page) -> None:
    page.add_init_script(
        """
        (() => {
          const listeners = new Map();
          const makeWindow = (label) => ({
            label,
            async emitTo(target, event, payload) {
              const key = `${target}:${event}`;
              const callbacks = listeners.get(key) || [];
              for (const callback of callbacks) {
                await callback({ payload });
              }
            },
            async listen(event, callback) {
              const key = `${label}:${event}`;
              const callbacks = listeners.get(key) || [];
              callbacks.push(callback);
              listeners.set(key, callbacks);
              return () => {
                const current = listeners.get(key) || [];
                listeners.set(key, current.filter((item) => item !== callback));
              };
            },
            async show() {},
            async hide() {},
            async setFocus() {},
            async startDragging() {},
            async setSize() {},
            async setPosition() {},
            async outerPosition() { return { x: 0, y: 0 }; },
          });

          window.__TAURI_INTERNALS__ = {
            metadata: {
              currentWindow: { label: 'main' },
              currentWebview: { label: 'main' },
            },
            invoke: async (cmd, args) => {
              if (cmd === 'load_frontend_config_file') {
                return JSON.stringify({
                  user_nickname: '小伙伴',
                  user_display_name: '主人',
                  character_type: 'mao_pro_zh',
                  character_name: 'Mao',
                  personality: ['温柔'],
                  interaction_mode: 'work',
                  proactive_mode: 'greet',
                  window_x: 100,
                  window_y: 100,
                  window_scale: 1,
                  character_scales: {},
                });
              }
              if (cmd === 'load_frontend_memory_file' || cmd === 'load_frontend_history_file') {
                return '[]';
              }
              if (cmd === 'save_frontend_config_file' || cmd === 'save_frontend_memory_file' || cmd === 'save_frontend_history_file') {
                return null;
              }
              if (cmd === 'get_backend_base_url') {
                return 'http://127.0.0.1:8080';
              }
              return null;
            },
            transformCallback: (callback) => callback,
            convertFileSrc: (path) => path,
          };

          window.__TAURI_MOCK_WINDOWS__ = {
            main: makeWindow('main'),
            chat: makeWindow('chat'),
            settings: makeWindow('settings'),
            model: makeWindow('model'),
          };
        })();
        """
    )


def run_scenario(page, name: str) -> None:
    page.wait_for_selector("#character-hit-area", timeout=5000)
    page.wait_for_timeout(1200)

    if name == "idle-mao":
        page.evaluate("window.__desktopCompanionDebug?.fitCurrentModelForPreview?.()")
        page.wait_for_timeout(4000)
        return

    if name == "greeting-bubble":
        page.evaluate("window.__desktopCompanionDebug?.fitCurrentModelForPreview?.()")
        page.evaluate("window.__desktopCompanionDebug?.showBubble?.('主人，欢迎回来。')")
        page.wait_for_timeout(3500)
        return

    if name == "open-settings":
        page.evaluate("window.__desktopCompanionDebug?.openSettings?.()")
        page.wait_for_timeout(3200)
        return

    if name == "open-model-panel":
        page.evaluate("window.__desktopCompanionDebug?.openModelPanel?.()")
        page.wait_for_timeout(3600)
        return

    if name == "click-face":
        page.mouse.click(240, 160)
        page.wait_for_timeout(4200)
        return

    if name == "click-belly":
        page.mouse.click(240, 380)
        page.wait_for_timeout(3200)
        page.evaluate("window.__desktopCompanionDebug?.showBubble?.('主人，突然摸这里会害羞的。')")
        page.wait_for_timeout(2400)
        page.mouse.click(240, 380)
        page.wait_for_timeout(3200)
        page.evaluate("window.__desktopCompanionDebug?.showBubble?.('我会乖乖在你身边的。')")
        page.wait_for_timeout(2400)
        page.mouse.click(240, 380)
        page.wait_for_timeout(1800)
        return

    if name == "click-legs":
        page.mouse.click(240, 650)
        page.wait_for_timeout(4200)
        return

    if name == "chat-reply":
        page.evaluate("window.__desktopCompanionDebug?.openChat?.()")
        page.wait_for_timeout(600)
        page.evaluate("window.__desktopCompanionDebug?.sendChatMessage?.('主人今天有点累')")
        page.wait_for_timeout(4500)
        return

    if name == "weather-care":
        page.evaluate("window.__desktopCompanionDebug?.triggerProactiveBubble?.('weather_update', '合肥今天多云，出门记得带上好心情。')")
        page.wait_for_timeout(4200)
        return

    if name == "memory-chat":
        page.evaluate("window.__desktopCompanionDebug?.openChat?.()")
        page.wait_for_timeout(600)
        page.evaluate("window.__desktopCompanionDebug?.sendChatMessage?.('记住我喜欢 Changli')")
        page.wait_for_timeout(4500)
        return

    if name == "switch-models":
        page.evaluate("window.__desktopCompanionDebug?.switchCharacterAndWait?.('hiyori_pro_zh')")
        page.wait_for_timeout(1800)
        page.evaluate("window.__desktopCompanionDebug?.switchCharacterAndWait?.('mao_pro_zh')")
        page.wait_for_timeout(1800)
        return

    raise ValueError(f"Unknown scenario: {name}")


def prepare_capture_scene(page) -> None:
    page.evaluate(
        """
        (() => {
          document.body.style.background = 'radial-gradient(circle at top, #fff3fa 0%, #f4ebff 48%, #efe8ff 100%)';
          const app = document.getElementById('app');
          if (app) {
            app.style.justifyContent = 'center';
          }
        })();
        """
    )
    page.evaluate("window.__desktopCompanionDebug?.fitCurrentModelForPreview?.()")
    page.wait_for_timeout(500)


def wait_for_canvas_content(page, timeout_ms: int = 10000) -> None:
    page.wait_for_function(
        """
        () => {
          const canvas = document.querySelector('#character-canvas canvas');
          if (!canvas) return false;
          const rect = canvas.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0;
        }
        """,
        timeout=timeout_ms,
    )


def export_clip(browser, scenario_name: str, preset: str) -> None:
    video_size = VIDEO_PRESETS[preset]
    context = browser.new_context(
        viewport=video_size,
        record_video_dir=str(OUTPUT_DIR),
        record_video_size=video_size,
    )
    page = context.new_page()
    install_tauri_mocks(page)
    mock_backend(page)
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    prepare_capture_scene(page)
    wait_for_canvas_content(page)
    run_scenario(page, scenario_name)
    page.close()
    context.close()

    video_path = Path(page.video.path())
    target_path = OUTPUT_DIR / f"{scenario_name}-{preset}.webm"
    if target_path.exists():
        target_path.unlink()
    shutil.move(str(video_path), target_path)
    mp4_path = convert_webm_to_mp4(target_path)
    if mp4_path:
        print(f"exported {target_path} and {mp4_path}")
    else:
        print(f"exported {target_path} (ffmpeg not found, skipped mp4 conversion)")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    preset, requested_scenarios = parse_args()
    scenarios = requested_scenarios or [
        "idle-mao",
        "greeting-bubble",
        "open-settings",
        "open-model-panel",
        "click-face",
        "click-belly",
        "click-legs",
        "chat-reply",
        "weather-care",
        "memory-chat",
    ]

    static_server = start_static_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for scenario in scenarios:
                export_clip(browser, scenario, preset)
            browser.close()
    finally:
        static_server.terminate()
        static_server.wait(timeout=5)


if __name__ == "__main__":
    main()
