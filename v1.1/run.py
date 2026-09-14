#!/usr/bin/env python3
"""Paper Setting v1.1 One-Click Local Launcher.

Starts the local FastAPI server and serves the dual-view workbench.
"""

from __future__ import annotations

import os
import socket
import sys
import webbrowser
from pathlib import Path

V1_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = V1_ROOT.parent

# Set up Python paths
if str(V1_ROOT) not in sys.path:
    sys.path.insert(0, str(V1_ROOT))

for pkg in [
    "packages/core/src",
    "packages/runtime/src",
    "packages/contracts",
    "apps/api/src",
]:
    p = str(WORKSPACE_ROOT / pkg)
    if p not in sys.path:
        sys.path.insert(1, p)


def find_available_port(preferred: int = 8770) -> int:
    """Find an available port starting from preferred."""
    for p in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return preferred


def main():
    import uvicorn

    host = "127.0.0.1"
    requested_port = int(os.environ.get("PORT", 8770))
    port = find_available_port(requested_port)
    url = f"http://{host}:{port}"

    print("=" * 68)
    print("🌿 Paper Setting v1.1 论文排版工作台 (双视图 MVP)")
    print("=" * 68)
    print(f"• 本地服务地址: {url}")
    print("• 安全与隐私: 100% 纯本地单机运行 · 零外网请求 · 零 Token 消耗")
    print("• 默认视图: 极简 4 步向导 (上传 -> 选标 -> 秒级排版 -> 导出)")
    print("• 详细视图: 详细与 Agent 智排 (规则推导, 段落级 Diff, AI 盲审质检)")
    print("=" * 68)

    # Open browser automatically if not running headlessly
    if os.environ.get("NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run("server.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
