from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    output_dir = Path(r"C:\Users\lenovo\AppData\Local\Temp\opencode")
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = output_dir / "live2d-check.png"

    logs: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.on("console", lambda msg: logs.append(f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: logs.append(f"pageerror: {err}"))
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")
        page.screenshot(path=str(screenshot_path))

        print("core=", page.evaluate("Boolean(window.Live2DCubismCore)"))
        print("canvas=", page.evaluate("document.querySelectorAll('canvas').length"))
        print("scripts=", page.evaluate("[...document.scripts].map(s => s.src)"))
        print("logs:")
        for line in logs:
            print(line.encode("utf-8", errors="replace").decode("utf-8"))

        browser.close()


if __name__ == "__main__":
    main()
