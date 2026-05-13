from playwright.sync_api import sync_playwright


POSITIONS = [
    ("face", 200, 80),
    ("chest", 200, 180),
    ("arms", 80, 220),
    ("belly", 200, 300),
    ("legs", 200, 500),
]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        logs: list[str] = []
        page.on("console", lambda msg: logs.append(msg.text))
        page.request.post(
            "http://127.0.0.1:8080/config",
            data={
                "user_nickname": "小伙伴",
                "user_display_name": "你",
                "character_type": "hiyori_pro_zh",
                "character_name": "小艾",
                "personality": ["温柔"],
                "interaction_mode": "work",
                "proactive_mode": "quiet",
                "chat_model": "gpt",
                "window_x": 100,
                "window_y": 100,
                "window_scale": 1.0,
                "character_scales": {},
            },
        )
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")

        for name, x, y in POSITIONS:
            before = len(logs)
            page.mouse.click(x, y)
            page.wait_for_timeout(500)
            new_logs = logs[before:]
            action_logs = [line for line in new_logs if "ACTION:" in line or "点击区域" in line]
            print(name)
            for line in action_logs:
                print(line.encode("unicode_escape").decode("ascii"))
            close_btn = page.locator('.close-btn')
            if close_btn.count() > 0 and close_btn.first.is_visible():
                close_btn.click()
                page.wait_for_timeout(150)

        browser.close()


if __name__ == "__main__":
    main()
