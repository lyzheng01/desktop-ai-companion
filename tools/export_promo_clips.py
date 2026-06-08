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


def build_mock_chat_reply(message: str) -> str:
    normalized = (message or '').strip()

    scripted_replies = {
        '我今天改项目改得有点累。': '那先别急着逼自己提速。你现在更需要的不是一口气做完，而是先把今天最小的一块收掉。',
        '而且现在有点不知道先改哪一块。': '那就别同时看三件事。先挑那个最容易验收、做完最能让你松一口气的小点，我陪你从那里开始。',
        '我今天做桌面搭子项目有点卡住了。': '卡住不一定是你不会，更像是你现在同时想着太多块了。我们先把问题缩小。',
        '我应该先做界面，还是先补功能？': '如果你已经知道大概要做什么，先补最影响体验的功能；如果你连流程都不顺，先把界面里最核心那一段走通。',
        '记住我喜欢 Changli': '好呀，我记住了。以后聊到角色口味时，我会默认你更偏爱 Changli 这种强势又很有魅力的类型。',
        '下次聊到角色偏好时提醒我。': '没问题，下次只要话题沾边，我就会顺手把这个偏好接上。',
        '我这周在准备考试，今天复习有点乱。': '先不要想着把所有科目一次排整齐。你现在最需要的是先稳住一门。',
        '我总觉得每科都要看，结果一门都没推进。': '那我们今天就别追求“都顾到”。先只救最急或者最容易拿分的那一门，推进一点点就比摊着强。',
        '你帮我先定一个最小目标吧。': '那就先给自己二十分钟，只做一章重点或者一套题里的前三题。做完这一小段，再决定下一步。',
        '我最近压力有点大，脑子一直绷着。': '我知道，这种不是单纯累，是整个人一直悬着。你先别要求自己立刻恢复状态。',
        '明明没在做事，心里还是一直很紧。': '因为你的脑子还在持续预演那些没处理完的事。我们先别全解，先挑最压着你的那一件。',
        '我现在该先缓一下，还是逼自己继续做？': '如果你已经绷到连下一步都看不清了，先缓五到十分钟更有用。缓完以后，只回来做最小的一步，不要一下子全开。',
        '今晚想打会儿游戏放松一下。': '可以呀，放松本来就不是坏事。关键是别让放松变成事后更有负担。',
        '但又怕一玩太久，明天更累。': '那就给今晚定一个边界，比如只玩一两局，或者到某个时间点就收。这样你既放松到了，也不会明天醒来后悔。',
        '我现在稍微好一点了。': '那就好一点了就先按“好一点”的节奏来，不用马上变回满电。',
        '不过今天还是有点提不起劲。': '那今天就别追求效率感了，先追求一点点启动感。只要你肯往前挪一步，今天就不算白过。',
    }

    if normalized in scripted_replies:
        return scripted_replies[normalized]

    if '记住我喜欢 Changli' in normalized:
        return '好呀，我记下来了。以后聊到角色口味时，我会记得你偏爱 Changli 这种强势又有魅力的类型。'

    if any(token in normalized for token in ['今天有点累', '有点累', '工作', '卡住', '先做哪个', '项目']):
        return '辛苦啦。你现在更像是有点累，不是不会做。先挑最小的一步推进一下，做完第一小块，后面会顺很多。'

    if any(token in normalized for token in ['学习', '复习', '考试', '背书', '作业']):
        return '先别一下子压太满。我们可以先定一个二十分钟的小目标，比如只过一章重点，做完再决定要不要继续。'

    if any(token in normalized for token in ['压力', '焦虑', '紧张', '烦', '崩溃']):
        return '我懂，这种时候脑子会一直绷着。你先别急着把所有问题一起解决，先把最压着你的那一件说出来，我陪你慢慢拆。'

    if any(token in normalized for token in ['游戏', '开黑', '排位', '打本', '副本']):
        return '好呀，今天就当轻松一下。你想打得认真一点，还是我陪你走休闲放松路线？'

    if '我现在稍微好一点了' in normalized:
        return '那就好，我刚刚还在惦记你。今天先别把自己拉得太满，能慢一点就慢一点。'

    return '我在呢。你继续说，我会顺着你的节奏陪你聊。'


def build_mock_chat_delay_seconds(message: str) -> float:
    normalized = (message or '').strip()

    if any(token in normalized for token in ['考试', '复习', '学习', '压力', '焦虑', '卡住', '项目']):
        return 4.2

    if any(token in normalized for token in ['游戏', '放松', '开黑']):
        return 3.4

    if '记住' in normalized:
        return 3.0

    return 3.6


def build_mock_chat_stream(reply: str) -> str:
    return (
        f'event: assistant_delta\n'
        f'data: {reply}\n\n'
        'event: done\n'
        'data: done\n\n'
    )


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
            body = route.request.post_data or '{}'
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {}
            message = str(payload.get('message') or '')
            time.sleep(build_mock_chat_delay_seconds(message))
            reply = build_mock_chat_reply(message)
            route.fulfill(
                status=200,
                headers={"Content-Type": "text/event-stream"},
                body=build_mock_chat_stream(reply),
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

    def show_panel(panel_id: str) -> None:
        page.evaluate(
            f"""
            (() => {{
              const panel = document.getElementById('{panel_id}');
              panel?.classList.add('visible');
            }})()
            """
        )

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
        show_panel("settings-panel")
        page.wait_for_timeout(4200)
        return

    if name == "open-model-panel":
        show_panel("model-panel")
        page.wait_for_timeout(4600)
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
        run_multi_turn_chat(
            page,
            [
                ("我今天改项目改得有点累。", 6200),
                ("而且现在有点不知道先改哪一块。", 7200),
            ],
        )
        return

    if name == "desktop-chat-flow":
        page.mouse.click(240, 180)
        page.wait_for_timeout(1200)
        run_multi_turn_chat(
            page,
            [
                ("我今天做桌面搭子项目有点卡住了。", 6200),
                ("我应该先做界面，还是先补功能？", 7600),
            ],
        )
        return

    if name == "weather-care":
        page.evaluate("window.__desktopCompanionDebug?.triggerProactiveBubble?.('weather_update', '合肥今天多云，出门记得带上好心情。')")
        page.wait_for_timeout(4200)
        return

    if name == "memory-chat":
        run_multi_turn_chat(
            page,
            [
                ("记住我喜欢 Changli", 5200),
                ("下次聊到角色偏好时提醒我。", 6800),
            ],
        )
        return

    if name == "study-support":
        run_multi_turn_chat(
            page,
            [
                ("我这周在准备考试，今天复习有点乱。", 6200),
                ("我总觉得每科都要看，结果一门都没推进。", 7600),
                ("你帮我先定一个最小目标吧。", 7200),
            ],
        )
        return

    if name == "stress-support":
        run_multi_turn_chat(
            page,
            [
                ("我最近压力有点大，脑子一直绷着。", 6200),
                ("明明没在做事，心里还是一直很紧。", 7600),
                ("我现在该先缓一下，还是逼自己继续做？", 7200),
            ],
        )
        return

    if name == "gaming-companion":
        run_multi_turn_chat(
            page,
            [
                ("今晚想打会儿游戏放松一下。", 5200),
                ("但又怕一玩太久，明天更累。", 7000),
            ],
        )
        return

    if name == "settings-live-adjust":
        show_panel("settings-panel")
        page.wait_for_selector("#settings-panel.visible", timeout=5000)
        page.wait_for_timeout(1200)
        page.select_option("#proactive-mode-select", "remind")
        page.wait_for_timeout(1400)
        page.evaluate(
            """
            (() => {
              const slider = document.getElementById('scale-slider');
              if (!slider) return;
              slider.value = '1.18';
              slider.dispatchEvent(new Event('input', { bubbles: true }));
              slider.dispatchEvent(new Event('change', { bubbles: true }));
            })()
            """
        )
        page.wait_for_timeout(1800)
        page.evaluate(
            """
            (() => {
              const slider = document.getElementById('scale-slider');
              if (!slider) return;
              slider.value = '0.92';
              slider.dispatchEvent(new Event('input', { bubbles: true }));
              slider.dispatchEvent(new Event('change', { bubbles: true }));
            })()
            """
        )
        page.wait_for_timeout(2200)
        return

    if name == "switch-models":
        page.evaluate("window.__desktopCompanionDebug?.switchCharacterAndWait?.('hiyori_pro_zh')")
        page.wait_for_timeout(1800)
        page.evaluate("window.__desktopCompanionDebug?.switchCharacterAndWait?.('mao_pro_zh')")
        page.wait_for_timeout(1800)
        return

    if name == "model-switch-showcase":
        show_panel("model-panel")
        page.wait_for_selector("#model-panel.visible", timeout=5000)
        page.wait_for_timeout(1300)
        page.evaluate("window.__desktopCompanionDebug?.switchCharacterAndWait?.('hiyori_pro_zh')")
        page.wait_for_timeout(2600)
        show_panel("model-panel")
        page.wait_for_selector("#model-panel.visible", timeout=5000)
        page.wait_for_timeout(1200)
        page.evaluate("window.__desktopCompanionDebug?.switchCharacterAndWait?.('mao_pro_zh')")
        page.wait_for_timeout(2800)
        return

    if name == "proactive-to-chat":
        page.evaluate("window.__desktopCompanionDebug?.triggerProactiveBubble?.('care_followup', '你前面好像有点累，我有点惦记你。')")
        page.wait_for_timeout(1800)
        page.click('#reaction-bubble')
        run_multi_turn_chat(
            page,
            [
                ("我现在稍微好一点了。", 5200),
                ("不过今天还是有点提不起劲。", 7000),
            ],
        )
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
    page.evaluate("window.__desktopCompanionDebug?.setPromoCaptureMode?.(true)")
    page.wait_for_timeout(500)


def style_chat_window_for_capture(page) -> None:
    page.evaluate(
        """
        (() => {
          const chat = document.getElementById('chat-window');
          if (!chat) return;
          Object.assign(chat.style, {
            top: '24px',
            left: '20px',
            right: '20px',
            bottom: 'auto',
            width: 'auto',
            height: '320px',
            borderRadius: '24px',
            boxShadow: '0 18px 44px rgba(31, 41, 55, 0.18)',
            background: 'rgba(255,255,255,0.96)',
            backdropFilter: 'blur(12px)',
          });

          const messages = chat.querySelector('.chat-messages');
          if (messages instanceof HTMLElement) {
            messages.style.padding = '14px 14px 8px';
          }

          const inputArea = chat.querySelector('.chat-input-area');
          if (inputArea instanceof HTMLElement) {
            inputArea.style.padding = '12px';
          }
        })()
        """
    )


def send_chat_message(page, message: str, wait_ms: int = 7600) -> None:
    page.evaluate(f"window.__desktopCompanionDebug?.sendChatMessage?.({json.dumps(message, ensure_ascii=False)})")
    page.wait_for_timeout(wait_ms)


def run_multi_turn_chat(page, messages: list[tuple[str, int]]) -> None:
    page.evaluate(
        """
        (() => {
          const chat = document.getElementById('chat-window');
          chat?.classList.add('visible');
        })()
        """
    )
    page.wait_for_selector('#chat-window.visible', timeout=5000)
    style_chat_window_for_capture(page)
    page.wait_for_timeout(600)
    for message, wait_ms in messages:
        send_chat_message(page, message, wait_ms)


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
        "desktop-chat-flow",
        "settings-live-adjust",
        "model-switch-showcase",
        "proactive-to-chat",
        "click-face",
        "click-belly",
        "click-legs",
        "chat-reply",
        "weather-care",
        "memory-chat",
        "study-support",
        "stress-support",
        "gaming-companion",
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
