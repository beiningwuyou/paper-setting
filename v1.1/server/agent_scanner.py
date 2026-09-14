"""Local agent scanner and auto-configuration helper for Paper Setting.

Specifically caters to mainland Chinese workflows (WorkBuddy, Trae, Doubao/Coze,
DeepSeek, Cherry Studio, etc.) with real-time detection and one-click injection.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def find_executable(name: str, fallback_paths: list[str] | None = None) -> str | None:
    """Find executable in PATH or fallback locations."""
    found = shutil.which(name)
    if found:
        return found
    if fallback_paths:
        for p in fallback_paths:
            path_obj = Path(p).expanduser()
            if path_obj.is_file() and os.access(path_obj, os.X_OK):
                return str(path_obj)
    return None


def get_uv_path() -> str:
    """Resolve uv executable path."""
    uv = find_executable("uv", ["~/.local/bin/uv", "/opt/homebrew/bin/uv", "/usr/local/bin/uv"])
    return uv or "uv"


def scan_local_agents() -> dict[str, Any]:
    """Scan Mac system for installed Agent applications and CLI tools."""
    home = Path.home()
    uv_path = get_uv_path()
    python_path = find_executable("python3", ["/usr/bin/python3", "/opt/homebrew/bin/python3"]) or "python3"
    node_path = find_executable("node", ["/opt/homebrew/bin/node", "/usr/local/bin/node"]) or "node"
    code_path = find_executable("code", ["/opt/homebrew/bin/code", "/usr/local/bin/code"])

    # 1. WorkBuddy
    workbuddy_app_paths = [
        Path("/Applications/WorkBuddy.app"),
        home / "Applications/AI Agents/WorkBuddy.app",
        home / "Applications/WorkBuddy.app",
    ]
    workbuddy_installed = any(p.exists() for p in workbuddy_app_paths)
    workbuddy_config_path = home / ".workbuddy" / "mcp.json"
    workbuddy_config_exists = workbuddy_config_path.exists()
    workbuddy_injected = False
    if workbuddy_config_exists:
        try:
            content = json.loads(workbuddy_config_path.read_text(encoding="utf-8"))
            workbuddy_injected = "paper-setting" in content.get("mcpServers", {})
        except Exception:
            pass

    # 2. Trae (ByteDance AI IDE)
    trae_app_paths = [
        Path("/Applications/Trae.app"),
        home / "Applications/Trae.app",
    ]
    trae_installed = any(p.exists() for p in trae_app_paths)
    trae_config_path = home / ".trae" / "mcp.json"
    trae_injected = False
    if trae_config_path.exists():
        try:
            content = json.loads(trae_config_path.read_text(encoding="utf-8"))
            trae_injected = "paper-setting" in content.get("mcpServers", {})
        except Exception:
            pass

    # 3. 豆包 (Doubao) / 扣子 (Coze)
    doubao_app_paths = [
        Path("/Applications/豆包.app"),
        home / "Applications/豆包.app",
    ]
    doubao_installed = any(p.exists() for p in doubao_app_paths)
    doubao_container = (home / "Library/Containers/com.bot.neotix.doubao.FinderSyncExtension").exists()

    # 4. DeepSeek Harness / Desktop
    deepseek_paths = [
        home / "Applications/AI Agents/Deepseek Harness Desktop.app",
        Path("/Applications/Deepseek Harness Desktop.app"),
    ]
    deepseek_installed = any(p.exists() for p in deepseek_paths)

    # 5. Cherry Studio / Chatbox
    cherry_installed = Path("/Applications/Cherry Studio.app").exists()
    chatbox_installed = Path("/Applications/Chatbox.app").exists()

    # 6. VS Code / Cursor
    vscode_installed = Path("/Applications/Visual Studio Code.app").exists() or bool(code_path)
    cursor_installed = Path("/Applications/Cursor.app").exists() or bool(find_executable("cursor"))
    claude_installed = Path("/Applications/Claude.app").exists() or (home / "Applications/AI Agents/Claude.app").exists()

    # MCP config snippet
    mcp_config = {
        "command": uv_path,
        "args": [
            "run",
            "--directory",
            str(PROJECT_ROOT),
            "paper-setting-mcp",
        ],
        "env": {},
        "disabled": False,
    }

    return {
        "project_root": str(PROJECT_ROOT),
        "uv_path": uv_path,
        "mcp_server_config": mcp_config,
        "agents": {
            "workbuddy": {
                "name": "WorkBuddy (腾讯智能工作伙伴)",
                "category": "domestic",
                "installed": workbuddy_installed,
                "config_path": str(workbuddy_config_path),
                "config_exists": workbuddy_config_exists,
                "injected": workbuddy_injected,
                "can_auto_inject": True,
                "desc": "国内领先的企业级 AI 智能工作伙伴，原生支持 MCP 协议连接本地工具。",
            },
            "trae": {
                "name": "Trae (字节跳动 AI 原生 IDE)",
                "category": "domestic",
                "installed": trae_installed,
                "config_path": str(trae_config_path),
                "injected": trae_injected,
                "can_auto_inject": True,
                "desc": "字节跳动国内首发 AI IDE，支持 Claude/GPT/DeepSeek，原生适配 .trae/mcp.json。",
            },
            "doubao": {
                "name": "豆包 / 扣子 (Coze)",
                "category": "domestic",
                "installed": doubao_installed or doubao_container,
                "api_endpoint": "http://127.0.0.1:8765/openapi.json",
                "desc": "字节跳动国民级 AI 助手。支持在扣子中一键导入 Paper Setting OpenAPI 规范创建论文排版智能体。",
            },
            "deepseek": {
                "name": "DeepSeek 本地栈 / 客户端",
                "category": "domestic",
                "installed": deepseek_installed,
                "desc": "国内顶尖推理大模型客户端，支持通过本地 stdio MCP 或 API 进行协同排版。",
            },
            "cherry_studio": {
                "name": "Cherry Studio",
                "category": "domestic",
                "installed": cherry_installed,
                "desc": "国内广受欢迎的多模型桌面客户端（内置 DeepSeek/通义/智谱等），全面支持 MCP。",
            },
            "chatbox": {
                "name": "Chatbox",
                "category": "domestic",
                "installed": chatbox_installed,
                "desc": "跨平台开源 AI 对话客户端，支持国内主流大模型与工具扩展。",
            },
            "vscode": {
                "name": "Visual Studio Code (Cline / Roo Code)",
                "category": "developer",
                "installed": vscode_installed,
                "desc": "通过 Cline / Roo Code / Continue 插件支持 MCP 协同服务。",
            },
            "cursor": {
                "name": "Cursor",
                "category": "international",
                "installed": cursor_installed,
                "desc": "海外流行 AI 编辑器，通过 .cursor/mcp.json 配置服务。",
            },
            "claude": {
                "name": "Claude Desktop",
                "category": "international",
                "installed": claude_installed,
                "desc": "Anthropic 官方桌面端，需海外网络环境与专用配置。",
            },
        },
        "environment": {
            "uv_available": bool(shutil.which("uv") or Path(uv_path).exists()),
            "python_available": bool(python_path),
            "node_available": bool(node_path),
        },
    }


def inject_workbuddy_mcp() -> dict[str, Any]:
    """Safely inject paper-setting MCP server configuration into ~/.workbuddy/mcp.json."""
    home = Path.home()
    workbuddy_dir = home / ".workbuddy"
    workbuddy_dir.mkdir(parents=True, exist_ok=True)
    config_file = workbuddy_dir / "mcp.json"

    data: dict[str, Any] = {"mcpServers": {}}
    if config_file.exists():
        try:
            content = config_file.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                data = {"mcpServers": {}}
            if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
                data["mcpServers"] = {}
        except Exception:
            # Backup broken file
            backup_broken = workbuddy_dir / f"mcp.json.broken.{int(time.time())}"
            shutil.copy2(config_file, backup_broken)
            data = {"mcpServers": {}}

        # Backup current file before writing
        backup_file = workbuddy_dir / f"mcp.json.bak.{int(time.time())}"
        try:
            shutil.copy2(config_file, backup_file)
        except Exception:
            pass

    uv_path = get_uv_path()
    data["mcpServers"]["paper-setting"] = {
        "command": uv_path,
        "args": [
            "run",
            "--directory",
            str(PROJECT_ROOT),
            "paper-setting-mcp",
        ],
        "env": {},
        "disabled": False,
    }

    config_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "message": "已成功为 WorkBuddy 自动注入 paper-setting MCP 协同配置！",
        "config_path": str(config_file),
        "server_key": "paper-setting",
    }


def inject_trae_mcp() -> dict[str, Any]:
    """Inject paper-setting MCP server configuration into ~/.trae/mcp.json."""
    home = Path.home()
    trae_dir = home / ".trae"
    trae_dir.mkdir(parents=True, exist_ok=True)
    config_file = trae_dir / "mcp.json"

    data: dict[str, Any] = {"mcpServers": {}}
    if config_file.exists():
        try:
            content = config_file.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                data = {"mcpServers": {}}
            if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
                data["mcpServers"] = {}
        except Exception:
            data = {"mcpServers": {}}

    uv_path = get_uv_path()
    data["mcpServers"]["paper-setting"] = {
        "command": uv_path,
        "args": [
            "run",
            "--directory",
            str(PROJECT_ROOT),
            "paper-setting-mcp",
        ],
        "env": {},
        "disabled": False,
    }

    config_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "message": "已成功为 Trae 自动写入 ~/.trae/mcp.json 协同配置！",
        "config_path": str(config_file),
        "server_key": "paper-setting",
    }


def launch_local_app(app_name: str) -> dict[str, Any]:
    """Safely launch detected local application by name."""
    allowed_apps = {
        "workbuddy": "WorkBuddy",
        "doubao": "豆包",
        "vscode": "Visual Studio Code",
        "trae": "Trae",
        "cherry": "Cherry Studio",
        "deepseek": "Deepseek Harness Desktop",
    }
    target = allowed_apps.get(app_name.lower())
    if not target:
        return {"success": False, "message": "不支持的应用类型"}
    try:
        subprocess.run(["open", "-a", target], check=True)
        return {"success": True, "message": f"已成功启动 {target}"}
    except Exception as e:
        return {"success": False, "message": f"拉起应用失败: {e}"}
