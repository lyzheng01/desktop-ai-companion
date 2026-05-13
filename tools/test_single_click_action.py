from playwright.sync_api import sync_playwright


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
        page.mouse.click(200, 180)
        page.wait_for_timeout(400)
        action_logs = [line for line in logs if "ACTION:" in line or "点击区域" in line]
        print([line.encode("unicode_escape").decode("ascii") for line in action_logs])
        browser.close()

    assert any("点击区域: chest" in line for line in action_logs)
    assert any("ACTION: region-chest for hiyori" in line for line in action_logs)
    assert not any("hiyori-chinRest-module" in line for line in action_logs)


if __name__ == "__main__":
    main()
