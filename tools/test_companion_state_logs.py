from playwright.sync_api import sync_playwright


FRONTEND_URL = "http://127.0.0.1:1420"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        logs: list[str] = []
        page.on("console", lambda msg: logs.append(msg.text))

        page.route(
            "**/config",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=(
                    '{"user_nickname":"小伙伴","user_display_name":"你","character_type":"kei",'
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
        page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
        responses = iter([
            '{"content":"第一条回复会说得久一点久一点"}',
            '{"content":"第二条回复也要继续说话确保状态不会被旧计时器重置"}',
        ])
        page.route(
            "**/chat",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=next(responses),
            ),
        )

        page.goto(FRONTEND_URL, wait_until="networkidle")

        initial_state = page.evaluate("document.body.dataset.companionState || null")
        assert initial_state == "idle", initial_state

        page.click("#character-hit-area", position={"x": 200, "y": 300})
        page.wait_for_function(
            "document.getElementById('chat-window')?.classList.contains('visible') === true",
            timeout=3000,
        )

        page.fill("#chat-input", "你好，第一条")
        page.click("#send-btn")

        page.wait_for_function(
            """
            () => {
                const state = document.body.dataset.companionState;
                const messages = document.querySelectorAll('#chat-messages .message.assistant .message-content');
                return state === 'talking' && messages.length > 0;
            }
            """,
            timeout=3000,
        )

        page.fill("#chat-input", "你好，第二条")
        page.click("#send-btn")

        page.wait_for_timeout(1700)
        state_during_overlap = page.evaluate("document.body.dataset.companionState || null")
        assert state_during_overlap == "talking", state_during_overlap

        page.wait_for_function(
            "document.body.dataset.companionState === 'idle'",
            timeout=5000,
        )

        state_logs = [line for line in logs if "COMPANION_STATE:" in line]
        assert state_logs[:7] == [
            "COMPANION_STATE: idle",
            "COMPANION_STATE: listening",
            "COMPANION_STATE: thinking",
            "COMPANION_STATE: talking",
            "COMPANION_STATE: listening",
            "COMPANION_STATE: thinking",
            "COMPANION_STATE: talking",
        ], state_logs
        assert state_logs[-1] == "COMPANION_STATE: idle", state_logs

        browser.close()


if __name__ == "__main__":
    main()
