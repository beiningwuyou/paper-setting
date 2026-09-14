from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import webbrowser


def main() -> None:
    processes = [
        subprocess.Popen([sys.executable, "-m", "paper_setting_worker.main"]),
        subprocess.Popen([sys.executable, "-m", "paper_setting_api.main"]),
    ]

    def stop(_: int | None = None, __: object | None = None) -> None:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    time.sleep(1.5)
    if os.getenv("PAPER_SETTING_OPEN_BROWSER", "1") != "0":
        webbrowser.open("http://127.0.0.1:8765")
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    finally:
        stop()
    failed = [process.returncode for process in processes if process.returncode not in {0, -15}]
    if failed:
        raise SystemExit(failed[0])


if __name__ == "__main__":
    main()
