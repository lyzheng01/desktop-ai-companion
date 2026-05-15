import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / 'tauri-app' / 'dist'
PREVIEW_ROOT = REPO_ROOT / 'assets' / 'model-previews'
FRONTEND_URL = 'http://127.0.0.1:4175'

BUILTIN_LABELS = [
    'Kei',
    'Chitose',
    'Hiyori JP',
    'Shizuku',
    'Hiyori',
    'Mao',
    'Miara',
    'Miku',
    'Natori',
    'Ren',
]


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


def save_preview(locator, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    locator.screenshot(path=str(path))


def main() -> None:
    ensure_dirs()
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
                save_preview(page.locator('#character-container'), path)

            open_panel()

            for label in BUILTIN_LABELS:
                card = page.locator('.model-card').filter(has_text=label).first
                if card.count() == 0:
                    continue
                button = card.locator('button').first
                if button.is_enabled():
                    button.click()
                    save_current_character_preview(PREVIEW_ROOT / 'builtin' / f'{card.get_attribute("data-model-key")}.png')
                    open_panel()
                    card = page.locator('.model-card').filter(has_text=label).first
                else:
                    save_current_character_preview(PREVIEW_ROOT / 'builtin' / f'{card.get_attribute("data-model-key")}.png')

            for item in imported_models:
                label = item['name']
                card = page.locator('.model-card').filter(has_text=label).first
                if card.count() == 0:
                    continue
                button = card.locator('button').first
                if button.is_enabled():
                    button.click()
                    save_current_character_preview(PREVIEW_ROOT / 'imported' / f"{item['id']}.png")
                    open_panel()
                    card = page.locator('.model-card').filter(has_text=label).first
                else:
                    save_current_character_preview(PREVIEW_ROOT / 'imported' / f"{item['id']}.png")

            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == '__main__':
    main()
