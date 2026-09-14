#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-run}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.codex/run"
APP_BUNDLE="$RUN_DIR/论文排版台.app"
APP_EXECUTABLE="$APP_BUNDLE/Contents/MacOS/论文排版台"
APP_PID_FILE="$RUN_DIR/paper-setting-app.pid"
SERVER_PID_FILE="$ROOT_DIR/data/run/paper-setting-native.pid"
LOG_FILE="$ROOT_DIR/data/logs/论文排版台.log"
URL="http://127.0.0.1:8765"

mkdir -p "$RUN_DIR" "$ROOT_DIR/data/logs" "$ROOT_DIR/data/run"
cd "$ROOT_DIR"

stop_pid_file() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 0
  local pid
  pid="$(<"$pid_file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    for _ in {1..40}; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.1
    done
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
}

stop_existing() {
  stop_pid_file "$APP_PID_FILE"
  stop_pid_file "$SERVER_PID_FILE"
}

check_port() {
  if curl --silent --fail --max-time 1 "$URL/ready" >/dev/null 2>&1; then
    echo "端口 8765 已被另一份论文排版台占用；请先退出已安装的应用后重试。" >&2
    exit 1
  fi
}

build_project() {
  command -v swiftc >/dev/null 2>&1 || { echo "未找到 Swift 编译器" >&2; exit 1; }
  uv run paper-setting-init
  pnpm --dir apps/web build
  rm -rf "$APP_BUNDLE"
  mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
  cp packaging/macos/Info.plist "$APP_BUNDLE/Contents/Info.plist"
  cp packaging/macos/AppIcon.icns "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
  printf 'APPL????' > "$APP_BUNDLE/Contents/PkgInfo"
  swiftc -parse-as-library -O packaging/macos/PaperSettingApp.swift \
    -o "$APP_EXECUTABLE" -framework AppKit -framework WebKit
  codesign --force --deep --sign - "$APP_BUNDLE" >/dev/null
}

launch_app() {
  /usr/bin/open -n "$APP_BUNDLE"
  for _ in {1..80}; do
    local pid
    pid="$(pgrep -f "$APP_EXECUTABLE" | head -n 1 || true)"
    if [[ -n "$pid" ]]; then
      echo "$pid" > "$APP_PID_FILE"
    fi
    if [[ -n "$pid" ]] && curl --silent --fail --max-time 1 "$URL/ready" >/dev/null 2>&1; then
      echo "论文排版台已在独立窗口中运行。"
      echo "日志：$LOG_FILE"
      return 0
    fi
    sleep 0.25
  done
  echo "论文排版台未能在 20 秒内就绪。" >&2
  tail -n 40 "$LOG_FILE" >&2 || true
  exit 1
}

stop_existing
check_port
build_project

case "$MODE" in
  run)
    launch_app
    ;;
  --verify|verify)
    launch_app
    curl --silent --fail "$URL/health"
    echo
    stop_existing
    ;;
  --logs|logs)
    launch_app
    tail -f "$LOG_FILE"
    ;;
  --telemetry|telemetry)
    launch_app
    /usr/bin/log stream --style compact --predicate 'process == "论文排版台"'
    ;;
  --debug|debug)
    lldb "$APP_EXECUTABLE"
    ;;
  *)
    echo "usage: $0 [run|--debug|--logs|--telemetry|--verify]" >&2
    exit 2
    ;;
esac
