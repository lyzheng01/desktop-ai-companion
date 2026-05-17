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
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")

        for name, x, y in POSITIONS:
            before = len(logs)
            page.mouse.click(x, y)
            page.wait_for_timeout(300)
            region_logs = [line for line in logs[before:] if "点击区域" in line]
            print(f"{name}: {region_logs[-1] if region_logs else 'no-region-log'}")
            close_btn = page.locator('.close-btn')
            if close_btn.count() > 0:
                close_btn.click()
                page.wait_for_timeout(150)

        browser.close()


if __name__ == "__main__":
    main()
