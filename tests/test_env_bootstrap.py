import os


def test_load_project_env_prefers_env_local_and_keeps_process_env(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "DESKTOP_AI_COMPANION_WECHAT_PAY_PROVIDER=mock\n"
        "WECHAT_PAY_NOTIFY_URL=https://env.example/notify\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "DESKTOP_AI_COMPANION_WECHAT_PAY_PROVIDER=wechat\n"
        "WECHAT_PAY_NOTIFY_URL=https://env-local.example/notify\n"
        "DESKTOP_AI_COMPANION_PUBLIC_BASE_URL=http://127.0.0.1:8080\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("DESKTOP_AI_COMPANION_WECHAT_PAY_PROVIDER", raising=False)
    monkeypatch.setenv("WECHAT_PAY_NOTIFY_URL", "https://process.example/notify")
    monkeypatch.delenv("DESKTOP_AI_COMPANION_PUBLIC_BASE_URL", raising=False)

    from backend.env_bootstrap import load_project_env

    loaded_files = load_project_env(tmp_path)

    assert [path.name for path in loaded_files] == [".env.local", ".env"]
    assert os.getenv("DESKTOP_AI_COMPANION_WECHAT_PAY_PROVIDER") == "wechat"
    assert os.getenv("WECHAT_PAY_NOTIFY_URL") == "https://process.example/notify"
    assert os.getenv("DESKTOP_AI_COMPANION_PUBLIC_BASE_URL") == "http://127.0.0.1:8080"
