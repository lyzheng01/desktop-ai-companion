import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


BACKEND_URL = "http://127.0.0.1:18080"
FRONTEND_URL = "http://127.0.0.1:1420"
NPM_COMMAND = "npm.cmd" if sys.platform == "win32" else "npm"
FRONTEND_BACKEND_ORIGINS = ("http://localhost:8080", "http://127.0.0.1:8080")


def wait_for_http_server(url: str, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code < 500:
                return
        except Exception as error:
            last_error = error
        time.sleep(0.2)

    raise RuntimeError(f"Timed out waiting for {url}") from last_error


def wait_for_condition(predicate, timeout_seconds: float = 10.0, interval_seconds: float = 0.2) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(interval_seconds)

    raise RuntimeError("Timed out waiting for condition")


def reset_local_state(repo_root: Path) -> None:
    data_dir = repo_root / "data"
    for file_name in ("companion.db", "config.json"):
        file_path = data_dir / file_name
        if file_path.exists():
            file_path.unlink()


def clear_companions(repo_root: Path) -> None:
    db_path = repo_root / "data" / "companion.db"
    if not db_path.exists():
        return

    with sqlite3.connect(db_path) as connection:
        connection.execute("DELETE FROM characters")
        connection.commit()


def list_companions() -> list[dict]:
    response = requests.get(f"{BACKEND_URL}/companions", timeout=5)
    response.raise_for_status()
    return response.json()


def load_active_companion() -> dict | None:
    response = requests.get(f"{BACKEND_URL}/companions/active", timeout=5)
    response.raise_for_status()
    return response.json()


def create_companion_via_api(name: str = "小艾") -> int:
    response = requests.post(
        f"{BACKEND_URL}/companions",
        json={
            "name": name,
            "character_type": "hiyori_pro_zh",
            "personality_tags": ["温柔"],
            "interaction_mode": "work",
        },
        timeout=5,
    )
    response.raise_for_status()
    return response.json()["id"]


def start_backend(repo_root: Path) -> subprocess.Popen:
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.server:app", "--host", "127.0.0.1", "--port", "18080"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_for_http_server(f"{BACKEND_URL}/companions")
    return process


def start_frontend(repo_root: Path) -> subprocess.Popen:
    process = subprocess.Popen(
        [NPM_COMMAND, "run", "dev", "--", "--host", "127.0.0.1"],
        cwd=repo_root / "tauri-app",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_for_http_server(FRONTEND_URL)
    return process


def proxy_backend_requests(page, fail_first_activate: bool = False) -> None:
    activation_failed = {"done": False}

    def forward(route) -> None:
        request_url = route.request.url
        proxied_url = request_url
        for origin in FRONTEND_BACKEND_ORIGINS:
            if request_url.startswith(origin):
                proxied_url = request_url.replace(origin, BACKEND_URL, 1)
                break

        if fail_first_activate and request_url.endswith("/activate") and not activation_failed["done"]:
            activation_failed["done"] = True
            route.fulfill(status=500, content_type="application/json", body='{"detail":"activate failed"}')
            return

        response = route.fetch(url=proxied_url)
        route.fulfill(response=response)

    for origin in FRONTEND_BACKEND_ORIGINS:
        page.route(f"{origin}/**", forward)


def proxy_backend_requests_with_stale_empty_list(page) -> None:
    companions_list_calls = {"count": 0}

    def forward(route) -> None:
        request_url = route.request.url
        proxied_url = request_url
        for origin in FRONTEND_BACKEND_ORIGINS:
            if request_url.startswith(origin):
                proxied_url = request_url.replace(origin, BACKEND_URL, 1)
                break

        if route.request.method == "GET" and request_url.endswith("/companions") and companions_list_calls["count"] == 0:
            companions_list_calls["count"] += 1
            route.fulfill(status=200, content_type="application/json", body="[]")
            return

        response = route.fetch(url=proxied_url)
        route.fulfill(response=response)

    for origin in FRONTEND_BACKEND_ORIGINS:
        page.route(f"{origin}/**", forward)


def proxy_backend_requests_with_multiple_companions(page) -> None:
    state = {
        "active_id": 201,
        "companions": {
            201: {
                "id": 201,
                "name": "小晴",
                "character_type": "natori_pro_zh",
                "personality_tags": ["元气", "温柔"],
                "interaction_mode": "daily",
            },
            202: {
                "id": 202,
                "name": "小艾",
                "character_type": "hiyori_pro_zh",
                "personality_tags": ["温柔"],
                "interaction_mode": "work",
            },
        },
    }

    def build_companions_payload() -> list[dict]:
        payload = []
        for companion_id in sorted(state["companions"]):
            companion = dict(state["companions"][companion_id])
            companion["is_active"] = companion_id == state["active_id"]
            payload.append(companion)
        return payload

    def build_config_payload() -> dict:
        active = state["companions"][state["active_id"]]
        return {
            "user_nickname": "小伙伴",
            "user_display_name": "你",
            "character_type": active["character_type"],
            "character_name": active["name"],
            "personality": active["personality_tags"],
            "interaction_mode": active["interaction_mode"],
            "proactive_mode": "quiet",
            "chat_model": "gpt",
            "window_x": 100,
            "window_y": 100,
            "window_scale": 1,
            "character_scales": {},
        }

    def forward(route) -> None:
        request_url = route.request.url
        method = route.request.method
        proxied_url = request_url
        for origin in FRONTEND_BACKEND_ORIGINS:
            if request_url.startswith(origin):
                proxied_url = request_url.replace(origin, BACKEND_URL, 1)
                break

        if method == "GET" and request_url.endswith("/companions"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(build_companions_payload()))
            return

        if method == "GET" and request_url.endswith("/companions/active"):
            active_companion = next(item for item in build_companions_payload() if item["is_active"])
            route.fulfill(status=200, content_type="application/json", body=json.dumps(active_companion))
            return

        if method == "POST" and "/companions/" in request_url and request_url.endswith("/activate"):
            companion_id = int(request_url.rstrip("/").split("/")[-2])
            state["active_id"] = companion_id
            route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')
            return

        if method == "GET" and request_url.endswith("/config"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(build_config_payload()))
            return

        if method == "POST" and request_url.endswith("/config"):
            route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')
            return

        if method == "GET" and request_url.endswith("/memory"):
            route.fulfill(status=200, content_type="application/json", body="[]")
            return

        response = route.fetch(url=proxied_url)
        route.fulfill(response=response)

    for origin in FRONTEND_BACKEND_ORIGINS:
        page.route(f"{origin}/**", forward)


def proxy_backend_requests_with_switch_drift(page, mode: str) -> None:
    state = {
        "active_id": 201,
        "companions": {
            201: {
                "id": 201,
                "name": "小晴",
                "character_type": "natori_pro_zh",
                "personality_tags": ["元气", "温柔"],
                "interaction_mode": "daily",
            },
            202: {
                "id": 202,
                "name": "小艾",
                "character_type": "hiyori_pro_zh",
                "personality_tags": ["温柔"],
                "interaction_mode": "work",
            },
        },
        "config_active_id": 201,
    }

    def build_companion_payload(companion_id: int, is_active: bool) -> dict:
        companion = dict(state["companions"][companion_id])
        companion["is_active"] = is_active
        return companion

    def build_companions_payload() -> list[dict]:
        return [
            build_companion_payload(companion_id, companion_id == state["active_id"])
            for companion_id in sorted(state["companions"])
        ]

    def build_config_payload() -> dict:
        active = state["companions"][state["config_active_id"]]
        return {
            "user_nickname": "小伙伴",
            "user_display_name": "你",
            "character_type": active["character_type"],
            "character_name": active["name"],
            "personality": active["personality_tags"],
            "interaction_mode": active["interaction_mode"],
            "proactive_mode": "quiet",
            "chat_model": "gpt",
            "window_x": 100,
            "window_y": 100,
            "window_scale": 1,
            "character_scales": {},
        }

    def forward(route) -> None:
        request_url = route.request.url
        method = route.request.method

        if method == "POST" and "/companions/" in request_url and request_url.endswith("/activate"):
            companion_id = int(request_url.rstrip("/").split("/")[-2])
            state["active_id"] = companion_id
            if mode != "stale-config":
                state["config_active_id"] = companion_id
            route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')
            return

        if method == "GET" and request_url.endswith("/companions/active"):
            active_id = state["active_id"]
            if mode == "stale-active":
                active_id = 201
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(build_companion_payload(active_id, True)),
            )
            return

        if method == "GET" and request_url.endswith("/companions"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(build_companions_payload()))
            return

        if method == "GET" and request_url.endswith("/config"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(build_config_payload()))
            return

        if method == "POST" and request_url.endswith("/config"):
            route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')
            return

        if method == "GET" and request_url.endswith("/memory"):
            route.fulfill(status=200, content_type="application/json", body="[]")
            return

        proxied_url = request_url
        for origin in FRONTEND_BACKEND_ORIGINS:
            if request_url.startswith(origin):
                proxied_url = request_url.replace(origin, BACKEND_URL, 1)
                break

        response = route.fetch(url=proxied_url)
        route.fulfill(response=response)

    for origin in FRONTEND_BACKEND_ORIGINS:
        page.route(f"{origin}/**", forward)


def open_settings(page) -> None:
    page.click("body", button="right")
    page.click('[data-action="settings"]')
    page.wait_for_selector("#settings-panel.visible", timeout=5000)


def assert_first_run_blocks_desktop(page) -> None:
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#first-run-panel.visible", timeout=5000)
    assert page.locator("#character-canvas canvas").count() == 0
    assert page.locator("#bootstrap-error-banner.visible").count() == 0


def assert_integrated_first_run_create_flow(page) -> None:
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#first-run-panel.visible", timeout=5000)
    page.fill("#creator-name-input", "小晴")
    page.select_option("#creator-character-select", "natori_pro_zh")
    page.select_option("#creator-mode-select", "daily")
    page.select_option("#creator-personality-select", ["温柔", "安静", "元气", "理性"])
    page.wait_for_function(
        """
        () => {
            const selected = Array.from(document.querySelectorAll('#creator-personality-select option:checked'));
            return selected.length === 3;
        }
        """,
        timeout=5000,
    )
    assert page.locator("#creator-personality-select option:checked").all_text_contents() == ["温柔", "安静", "元气"]

    page.click("#creator-submit-btn")
    page.wait_for_function(
        """
        () => {
            return document.querySelector('#first-run-panel.visible') === null
                && document.querySelector('#bootstrap-error-banner.visible') === null
                && document.querySelector('#chat-title')?.textContent === '小晴 AI';
        }
        """,
        timeout=10000,
    )
    assert page.locator("#current-character-label").inner_text() == "Natori"
    assert page.locator("#bootstrap-error-banner.visible").count() == 0

    companions = list_companions()
    assert len(companions) == 1
    assert companions[0]["name"] == "小晴"
    assert companions[0]["character_type"] == "natori_pro_zh"
    assert companions[0]["personality_tags"] == ["温柔", "安静", "元气"]
    assert companions[0]["interaction_mode"] == "daily"
    assert companions[0]["is_active"] is True

    active_companion = load_active_companion()
    assert active_companion is not None
    assert active_companion["id"] == companions[0]["id"]


def assert_active_companion_survives_bootstrap(page) -> None:
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_function(
        """
        () => {
            return document.querySelector('#first-run-panel.visible') === null
                && document.querySelector('#bootstrap-error-banner.visible') === null
                && document.querySelector('#chat-title')?.textContent === '小晴 AI';
        }
        """,
        timeout=10000,
    )
    assert page.locator("#current-character-label").inner_text() == "Natori"
    assert page.locator("#first-run-panel.visible").count() == 0


def assert_settings_show_current_companion(page) -> None:
    open_settings(page)
    page.wait_for_function(
        """
        () => {
            const summary = document.querySelector('#active-companion-summary');
            const activeButton = document.querySelector('#companion-list .companion-switch-btn[disabled]');
            return summary?.textContent?.includes('Natori') && activeButton !== null;
        }
        """,
        timeout=5000,
    )
    assert "Natori" in page.locator("#active-companion-summary").inner_text()
    assert page.locator("#companion-list .companion-switch-btn[disabled]").count() == 1


def assert_multi_companion_switching_surface(page) -> None:
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_function(
        """
        () => {
            return document.querySelector('#first-run-panel.visible') === null
                && document.querySelector('#bootstrap-error-banner.visible') === null;
        }
        """,
        timeout=10000,
    )

    open_settings(page)
    page.wait_for_function(
        """
        () => {
            const list = document.querySelector('#companion-list');
            return list !== null && list.textContent?.includes('小艾') && list.textContent?.includes('切换');
        }
        """,
        timeout=5000,
    )
    page.click('[data-companion-switch-id="202"]')
    page.wait_for_function(
        """
        () => {
            return document.querySelector('#current-character-label')?.textContent === 'Hiyori'
                && document.querySelector('#active-companion-summary')?.textContent?.includes('Hiyori')
                && document.querySelector('[data-companion-switch-id="202"]')?.disabled === true
                && document.querySelector('[data-companion-switch-id="201"]')?.disabled === false;
        }
        """,
        timeout=10000,
    )

    assert page.locator("#first-run-panel.visible").count() == 0
    assert "Hiyori" in page.locator("#active-companion-summary").inner_text()


def assert_switch_rejects_stale_active_confirmation(page) -> None:
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_function(
        """
        () => document.querySelector('#bootstrap-error-banner.visible') === null
            && document.querySelector('#current-character-label')?.textContent === 'Natori'
        """,
        timeout=10000,
    )

    open_settings(page)
    page.click('[data-companion-switch-id="202"]')
    page.wait_for_function(
        """
        () => document.querySelector('#bootstrap-error-banner.visible') !== null
            && document.querySelector('#current-character-label')?.textContent === 'Natori'
            && document.querySelector('[data-companion-switch-id="201"]')?.disabled === true
            && document.querySelector('[data-companion-switch-id="202"]')?.disabled === false
        """,
        timeout=10000,
    )

    assert "Natori" in page.locator("#active-companion-summary").inner_text()


def assert_switch_uses_active_companion_over_stale_config(page) -> None:
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_function(
        """
        () => document.querySelector('#bootstrap-error-banner.visible') === null
            && document.querySelector('#current-character-label')?.textContent === 'Natori'
        """,
        timeout=10000,
    )

    open_settings(page)
    page.click('[data-companion-switch-id="202"]')
    page.wait_for_function(
        """
        () => document.querySelector('#bootstrap-error-banner.visible') === null
            && document.querySelector('#current-character-label')?.textContent === 'Hiyori'
            && document.querySelector('#active-companion-summary')?.textContent?.includes('Hiyori')
            && document.querySelector('[data-companion-switch-id="202"]')?.disabled === true
        """,
        timeout=10000,
    )

    assert page.locator("#chat-title").inner_text() == "小艾 AI"


def assert_single_inactive_companion_is_reused_on_bootstrap(page) -> None:
    create_companion_via_api("小艾")

    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_function(
        """
        () => {
            return document.querySelector('#first-run-panel.visible') === null
                && document.querySelector('#bootstrap-error-banner.visible') === null
                && document.querySelector('#current-character-label')?.textContent === 'Hiyori';
        }
        """,
        timeout=10000,
    )

    assert page.locator("#first-run-panel.visible").count() == 0
    assert page.locator("#bootstrap-error-banner.visible").count() == 0
    assert page.locator("#chat-title").inner_text() == "小艾 AI"

    page.reload(wait_until="domcontentloaded")
    page.wait_for_function(
        """
        () => {
            return document.querySelector('#first-run-panel.visible') === null
                && document.querySelector('#bootstrap-error-banner.visible') === null
                && document.querySelector('#current-character-label')?.textContent === 'Hiyori';
        }
        """,
        timeout=10000,
    )


def assert_free_tier_limit_shows_specific_message(page) -> None:
    create_companion_via_api("小艾")

    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#first-run-panel.visible", timeout=5000)
    page.click("#creator-submit-btn")
    page.wait_for_selector("#bootstrap-error-banner.visible", timeout=5000)

    assert page.locator("#bootstrap-error-banner").inner_text() == "普通用户最多创建 1 个伙伴，请直接使用现有伙伴。"
    assert page.locator("#first-run-panel.visible").count() == 1


def assert_activation_retry_does_not_create_duplicates(page) -> None:
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#first-run-panel.visible", timeout=5000)
    page.click("#creator-submit-btn")
    page.wait_for_selector("#bootstrap-error-banner.visible", timeout=5000)
    assert page.locator("#first-run-panel.visible").count() == 1

    companions = list_companions()
    assert len(companions) == 1
    assert companions[0]["personality_tags"] == ["温柔"]
    assert load_active_companion() is None

    page.click("#creator-submit-btn")
    page.wait_for_function(
        """
        () => {
            return document.querySelector('#first-run-panel.visible') === null
                && document.querySelector('#chat-title')?.textContent === '小艾 AI';
        }
        """,
        timeout=10000,
    )

    companions = list_companions()
    assert len(companions) == 1
    active_companion = load_active_companion()
    assert active_companion is not None
    assert active_companion["id"] == companions[0]["id"]


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    reset_local_state(repo_root)
    backend_process = start_backend(repo_root)
    frontend_process = start_frontend(repo_root)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests(page)
                assert_first_run_blocks_desktop(page)
                page.close()

                clear_companions(repo_root)
                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests(page)
                assert_integrated_first_run_create_flow(page)
                page.close()

                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests(page)
                assert_active_companion_survives_bootstrap(page)
                assert_settings_show_current_companion(page)
                page.close()

                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests_with_multiple_companions(page)
                assert_multi_companion_switching_surface(page)
                page.close()

                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests_with_switch_drift(page, mode="stale-active")
                assert_switch_rejects_stale_active_confirmation(page)
                page.close()

                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests_with_switch_drift(page, mode="stale-config")
                assert_switch_uses_active_companion_over_stale_config(page)
                page.close()

                clear_companions(repo_root)
                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests(page)
                assert_single_inactive_companion_is_reused_on_bootstrap(page)
                page.close()

                clear_companions(repo_root)
                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests_with_stale_empty_list(page)
                assert_free_tier_limit_shows_specific_message(page)
                page.close()

                clear_companions(repo_root)
                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("**/live2dcubismcore.min.js", lambda route: route.abort())
                proxy_backend_requests(page, fail_first_activate=True)
                assert_activation_retry_does_not_create_duplicates(page)
                page.close()
            finally:
                browser.close()
    finally:
        frontend_process.terminate()
        frontend_process.wait(timeout=10)
        backend_process.terminate()
        backend_process.wait(timeout=10)


if __name__ == "__main__":
    main()
