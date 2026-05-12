from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")
        result = page.evaluate(
            """
            () => {
              const el = document.elementFromPoint(200, 10)
              if (!el) return null
              return {
                tag: el.tagName,
                id: el.id,
                dragRegion: el.hasAttribute('data-tauri-drag-region'),
                parentId: el.parentElement?.id ?? null,
                parentDragRegion: el.parentElement?.hasAttribute('data-tauri-drag-region') ?? false
              }
            }
            """
        )
        print(result)
        browser.close()


if __name__ == "__main__":
    main()
