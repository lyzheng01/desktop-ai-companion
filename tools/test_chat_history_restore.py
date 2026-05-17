import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


BACKEND_URL = "http://127.0.0.1:8080"
FRONTEND_URL = "http://127.0.0.1:1420"


def seed_history() -> list[dict]:
    requests.delete(f"{BACKEND_URL}/history", timeout=5).raise_for_status()

    seeded_messages = [
        "第一条用户消息",
        "第二条用户消息",
    ]
    for message in seeded_messages:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": message, "context": []},
            timeout=5,
        )
        response.raise_for_status()

    history_response = requests.get(f"{BACKEND_URL}/history", timeout=5)
    history_response.raise_for_status()
    return history_response.json()


def open_chat(page) -> None:
    page.locator("#character-hit-area").click()


def close_chat(page) -> None:
    page.locator("#chat-window .close-btn").click()


def get_chat_contents(page) -> list[str]:
    return page.locator("#chat-messages .message-content").all_text_contents()


def main() -> None:
    history = seed_history()
    assert len(history) >= 4
    expected_contents = [message["content"] for message in history]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        first_history_request = {"pending": True}

        # This flow only validates chat history restore, so avoid waiting on the external Live2D core script.
        page.route("**/live2dcubismcore.min.js", lambda route: route.abort())

        def fail_first_history(route) -> None:
            if first_history_request["pending"]:
                first_history_request["pending"] = False
                route.fulfill(status=500, body="history unavailable")
                return
            route.continue_()

        page.route("**/history?limit=20", fail_first_history)
        page.goto(FRONTEND_URL, wait_until="networkidle")

        try:
            open_chat(page)
            page.wait_for_timeout(500)
            assert get_chat_contents(page) == []

            close_chat(page)
            open_chat(page)

            page.wait_for_function(
                """
                () => {
                    const items = Array.from(document.querySelectorAll('#chat-messages .message-content'));
                    return items.length >= 4;
                }
                """,
                timeout=3000,
            )
        except PlaywrightTimeoutError:
            contents = get_chat_contents(page)
            raise AssertionError(f"chat history was not restored: {contents}")
        else:
            contents = get_chat_contents(page)
            assert contents == expected_contents
        finally:
            browser.close()


if __name__ == "__main__":
    main()
