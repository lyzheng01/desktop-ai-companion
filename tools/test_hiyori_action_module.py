from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")
        result = page.evaluate(
            """
            () => {
              const state = window.__live2dDebugState
              return {
                hasActions: Boolean(state?.hiyoriActions),
                keys: state?.hiyoriActions ? Object.keys(state.hiyoriActions) : []
              }
            }
            """
        )
        print(result)
        browser.close()

    assert result["hasActions"] is True
    assert result["keys"] == ["nod", "shake", "chinRest", "wave", "reject", "crouch"]


if __name__ == "__main__":
    main()
