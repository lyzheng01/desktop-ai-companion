from pathlib import Path

from dotenv import load_dotenv


def load_project_env(project_root: Path | str | None = None) -> list[Path]:
    root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parent.parent
    loaded_files: list[Path] = []
    for filename in (".env.local", ".env"):
        env_path = root / filename
        if not env_path.is_file():
            continue
        load_dotenv(env_path, override=False)
        loaded_files.append(env_path)
    return loaded_files
