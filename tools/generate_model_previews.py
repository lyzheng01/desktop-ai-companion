import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / 'tauri-app' / 'dist'
PREVIEW_ROOT = REPO_ROOT / 'assets' / 'model-previews'
FRONTEND_URL = 'http://127.0.0.1:4175'
PREVIEW_SIZE = (360, 640)

def wait_for_server(url: str, timeout: float = 12.0) -> None:
    import requests

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=1)
            if response.ok:
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(url)


def load_imported_models() -> list[dict]:
    response = requests.get('http://127.0.0.1:8080/models/imported', timeout=20)
    response.raise_for_status()
    return response.json()


def ensure_dirs() -> None:
    (PREVIEW_ROOT / 'builtin').mkdir(parents=True, exist_ok=True)
    (PREVIEW_ROOT / 'imported').mkdir(parents=True, exist_ok=True)


def clear_existing_previews() -> None:
    for folder in (PREVIEW_ROOT / 'builtin', PREVIEW_ROOT / 'imported'):
        for path in folder.glob('*.png'):
            path.unlink(missing_ok=True)


def save_preview_bytes(png_bytes: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)


def build_thumbnail_from_canvas(png_bytes: bytes) -> bytes:
    image = Image.open(BytesIO(png_bytes)).convert('RGBA')
    alpha = image.getchannel('A')
    bbox = alpha.getbbox()
    if not bbox:
        output = Image.new('RGBA', PREVIEW_SIZE, (0, 0, 0, 0))
        buffer = BytesIO()
        output.save(buffer, format='PNG')
        return buffer.getvalue()

    cropped = image.crop(bbox)
    target_width, target_height = PREVIEW_SIZE
    scale = min(target_width / cropped.width, target_height / cropped.height)
    resized = cropped.resize((max(1, int(cropped.width * scale)), max(1, int(cropped.height * scale))), Image.LANCZOS)

    output = Image.new('RGBA', PREVIEW_SIZE, (0, 0, 0, 0))
    x = (target_width - resized.width) // 2
    y = int(target_height * 0.56 - resized.height / 2)
    y = max(0, min(target_height - resized.height, y))
    output.alpha_composite(resized, (x, y))

    buffer = BytesIO()
    output.save(buffer, format='PNG')
    return buffer.getvalue()


def main() -> None:
    ensure_dirs()
    clear_existing_previews()
    imported_models = load_imported_models()

    server = subprocess.Popen(
        [sys.executable, '-m', 'http.server', '4175', '--bind', '127.0.0.1'],
        cwd=DIST_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server(FRONTEND_URL)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 420, 'height': 760})
            page.goto(FRONTEND_URL, wait_until='domcontentloaded')
            page.wait_for_selector('#character-hit-area', timeout=5000)

            def open_panel():
                page.click('#character-hit-area', button='right')
                page.wait_for_selector('#context-menu.visible', timeout=3000)
                page.locator('#context-menu button').filter(has_text='选择模型').click()
                page.wait_for_selector('#model-panel.visible', timeout=3000)
                page.wait_for_timeout(1200)

            def save_current_character_preview(path: Path):
                page.wait_for_timeout(2200)
                page.evaluate("window.__desktopCompanionDebug?.fitCurrentModelForPreview?.()")
                page.wait_for_timeout(250)
                canvas = page.locator('#character-canvas canvas').first
                png_bytes = canvas.screenshot(type='png')
                save_preview_bytes(build_thumbnail_from_canvas(png_bytes), path)

            open_panel()

            builtin_cards = page.locator('#builtin-model-list .model-card')
            builtin_count = builtin_cards.count()
            for index in range(builtin_count):
                card = builtin_cards.nth(index)
                button = card.locator('button').first
                model_key = card.get_attribute('data-model-key')
                if not model_key:
                    continue
                if button.is_enabled():
                    button.click()
                    save_current_character_preview(PREVIEW_ROOT / 'builtin' / f'{model_key}.png')
                    open_panel()
                    builtin_cards = page.locator('#builtin-model-list .model-card')
                else:
                    save_current_character_preview(PREVIEW_ROOT / 'builtin' / f'{model_key}.png')

            for item in imported_models:
                model_key = f"imported:{item['id']}"
                card = page.locator(f'.model-card[data-model-key="{model_key}"]').first
                if card.count() == 0:
                    continue
                button = card.locator('button').first
                if button.is_enabled():
                    button.click()
                    save_current_character_preview(PREVIEW_ROOT / 'imported' / f"{item['id']}.png")
                    open_panel()
                    card = page.locator(f'.model-card[data-model-key="{model_key}"]').first
                else:
                    save_current_character_preview(PREVIEW_ROOT / 'imported' / f"{item['id']}.png")

            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == '__main__':
    main()
