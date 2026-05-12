from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")

        page.locator("#character-container").click(position={"x": 200, "y": 300})
        visible = page.evaluate(
            "document.getElementById('chat-window')?.classList.contains('visible') ?? false"
        )

        browser.close()

    assert visible is True


if __name__ == "__main__":
    main()
