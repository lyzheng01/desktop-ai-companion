import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


FRONTEND_URL = "http://127.0.0.1:4174"


def wait_for_server(url: str, timeout: float = 10.0) -> None:
    import requests

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=1)
            if response.ok:
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(f"server did not start: {url}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    dist_dir = repo_root / "tauri-app" / "dist"
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "4174", "--bind", "127.0.0.1"],
        cwd=dist_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server(FRONTEND_URL)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 420, "height": 760})
            page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
            page.route(
                "**/config",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=(
                        '{"user_nickname":"小伙伴","user_display_name":"你","character_type":"hiyori_pro_zh",'
                        '"character_name":"小艾","personality":["温柔"],"interaction_mode":"work",'
                        '"proactive_mode":"quiet","chat_model":"gpt","window_x":100,'
                        '"window_y":100,"window_scale":1,"character_scales":{}}'
                    ),
                ),
            )
            page.route("**/companions/active", lambda route: route.fulfill(status=200, content_type="application/json", body='{"id":1,"name":"小艾","character_type":"hiyori_pro_zh","personality_tags":["温柔"],"interaction_mode":"work","is_active":true}'))
            page.route("**/companions", lambda route: route.fulfill(status=200, content_type="application/json", body='[{"id":1,"name":"小艾","character_type":"hiyori_pro_zh","personality_tags":["温柔"],"interaction_mode":"work","is_active":true}]'))
            page.route("**/models/imported", lambda route: route.fulfill(status=200, content_type="application/json", body='[]'))
            page.route("**/history?limit=20", lambda route: route.fulfill(status=200, content_type="application/json", body="[]"))
            page.route("**/memory", lambda route: route.fulfill(status=200, content_type="application/json", body="[]"))

            page.goto(FRONTEND_URL, wait_until="domcontentloaded")
            page.wait_for_selector("#character-hit-area", timeout=5000)
            page.click("#character-hit-area", button="right")
            page.wait_for_selector('#context-menu.visible', timeout=3000)

            assert page.locator('#context-menu button').filter(has_text='选择模型').count() == 1
            assert page.locator('#context-menu [data-character]').count() == 0

            page.locator('#context-menu button').filter(has_text='选择模型').click()
            page.wait_for_selector('#model-panel.visible', timeout=3000)
            assert page.locator('#builtin-model-list .model-row').count() >= 1

            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    main()
