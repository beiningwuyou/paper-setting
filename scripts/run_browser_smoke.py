"""Run the production browser smoke test with an isolated local API."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = 8890


def wait_for_server(timeout_seconds: float = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"API did not start on {HOST}:{PORT}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="paper-setting-smoke-") as data_dir:
        env = os.environ.copy()
        env.update(
            {
                "PAPER_SETTING_ENV": "production",
                "PAPER_SETTING_HOST": HOST,
                "PAPER_SETTING_PORT": str(PORT),
                "PAPER_SETTING_DATA_DIR": data_dir,
                "PAPER_SETTING_DATABASE_URL": f"sqlite:///{data_dir}/smoke.db",
                "PAPER_SETTING_BROWSER_URL": f"http://{HOST}:{PORT}",
                "PAPER_SETTING_LOG_LEVEL": "WARNING",
            }
        )
        api = subprocess.Popen(
            [sys.executable, "-m", "paper_setting_api.main"],
            cwd=PROJECT_ROOT,
            env=env,
        )
        try:
            wait_for_server()
            completed = subprocess.run(
                [sys.executable, "scripts/browser_smoke.py"],
                cwd=PROJECT_ROOT,
                env=env,
                check=False,
            )
            return completed.returncode
        finally:
            api.terminate()
            try:
                api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
