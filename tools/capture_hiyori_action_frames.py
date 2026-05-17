from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    out_dir = Path(r"C:\Users\lenovo\AppData\Local\Temp\opencode\hiyori-frames")
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")

        points = {
            "face": (200, 80),
            "chest": (200, 180),
            "arms": (80, 220),
            "belly": (200, 300),
            "legs": (200, 500),
        }

        for name, (x, y) in points.items():
            page.screenshot(path=str(out_dir / f"{name}-before.png"))
            page.mouse.click(x, y)
            page.wait_for_timeout(220)
            page.screenshot(path=str(out_dir / f"{name}-after.png"))
            close_btn = page.locator('.close-btn')
            if close_btn.count() > 0:
                close_btn.click()
                page.wait_for_timeout(120)

        browser.close()


if __name__ == "__main__":
    main()
