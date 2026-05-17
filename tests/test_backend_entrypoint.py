from pathlib import Path
import subprocess
import sys


def test_backend_server_script_starts_from_backend_directory():
    repo_root = Path(__file__).resolve().parent.parent
    backend_dir = repo_root / "backend"

    process = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=5)
        return

    assert "No module named 'app'" not in stderr
    assert process.returncode == 0
