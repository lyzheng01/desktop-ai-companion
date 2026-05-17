from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 400, "height": 600})
        page.goto("http://127.0.0.1:1420", wait_until="networkidle")

        result = page.evaluate(
            """
            () => {
              const el = document.elementFromPoint(200, 300)
              if (!el) return null
              return {
                tag: el.tagName,
                id: el.id,
                className: el.className,
                dragRegion: el.hasAttribute('data-tauri-drag-region'),
                parentTag: el.parentElement?.tagName ?? null,
                parentId: el.parentElement?.id ?? null,
                parentClass: el.parentElement?.className ?? null,
                parentDragRegion: el.parentElement?.hasAttribute('data-tauri-drag-region') ?? false
              }
            }
            """
        )
        print(result)
        browser.close()


if __name__ == "__main__":
    main()
