import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


FRONTEND_URL = "http://127.0.0.1:4173"


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    dist_dir = repo_root / "tauri-app" / "dist"
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "4173", "--bind", "127.0.0.1"],
        cwd=dist_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 400, "height": 600})
            deleted_ids: list[str] = []

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
            page.route(
                "**/history?limit=20",
                lambda route: route.fulfill(status=200, content_type="application/json", body="[]"),
            )

            def handle_memory(route) -> None:
                if route.request.method == "DELETE":
                    deleted_ids.append(route.request.url.rsplit("/", 1)[-1])
                    route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')
                    return

                body = (
                    '[]'
                    if deleted_ids
                    else '[{"id":1,"content":"用户喜欢被叫阿泽","category":"preference","importance":2,"created_at":"2026-05-13T00:00:00"}]'
                )
                route.fulfill(status=200, content_type="application/json", body=body)

            page.route("**/memory", handle_memory)
            page.route("**/memory/*", handle_memory)

            page.goto(FRONTEND_URL, wait_until="domcontentloaded")
            page.wait_for_selector("#character-hit-area", timeout=3000)
            page.click("#character-hit-area", button="right")
            page.wait_for_selector('#context-menu.visible', timeout=3000)
            page.evaluate(
                "document.querySelector('#context-menu [data-action=\"settings\"]')?.dispatchEvent(new MouseEvent('click', { bubbles: true }))"
            )
            page.wait_for_selector('#settings-panel.visible', timeout=3000)
            page.wait_for_selector('#memory-list', timeout=3000, state='attached')
            page.wait_for_timeout(500)
            assert "用户喜欢被叫阿泽" in page.locator("#memory-list").inner_text()
            page.click('#memory-list button[data-memory-id="1"]')
            page.wait_for_timeout(300)
            assert "暂时还没有记住新的内容。" in page.locator("#memory-list").inner_text()
            browser.close()
        finally:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()
