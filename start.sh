#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Detect Python virtual environment
if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
else
    echo "❌ 未检测到 Python3 环境，请先安装 Python 3.10+"
    exit 1
fi

echo "===================================================================="
echo "🚀 启动 Paper Setting v1.1 学术论文排版工作台..."
echo "===================================================================="

exec "$PYTHON_BIN" v1.1/run.py "$@"
