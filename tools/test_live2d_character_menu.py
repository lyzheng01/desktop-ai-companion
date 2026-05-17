from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")

        page.click("body", button="right", position={"x": 200, "y": 300})
        labels = page.locator("#context-menu [data-character]").all_text_contents()
        browser.close()

    assert labels == ["📦 Kei", "🌸 Chitose", "☀️ Hiyori"]


if __name__ == "__main__":
    main()
