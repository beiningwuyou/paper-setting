#!/bin/bash
# Paper Setting 双击快捷启动脚本 (macOS Finder 双击可用)
cd "$(dirname "$0")/../.."

echo "================================================="
echo "🌿 正在启动 Paper Setting v1.1 论文排版工作台..."
echo "================================================="

if [ -f ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 &>/dev/null; then
  PYTHON_BIN="python3"
else
  echo "错误: 未检测到可用 Python 环境"
  exit 1
fi

"$PYTHON_BIN" v1.1/run.py
