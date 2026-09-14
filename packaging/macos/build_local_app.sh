#!/bin/bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOT="${1:-$SOURCE_ROOT}"
SHORTCUT_DIR="${2:-$HOME/Applications}"
APP_BUNDLE="$TARGET_ROOT/论文排版台.app"
SHORTCUT="$SHORTCUT_DIR/论文排版台.app"

if ! command -v swiftc >/dev/null 2>&1; then
  echo "未找到 Swift 编译器，无法构建 macOS 独立窗口应用" >&2
  exit 3
fi

if [[ -e "$TARGET_ROOT" ]]; then
  echo "目标目录已存在，未覆盖：$TARGET_ROOT" >&2
  exit 2
fi
if [[ -e "$SHORTCUT" || -L "$SHORTCUT" ]]; then
  echo "快捷方式已存在，未覆盖：$SHORTCUT" >&2
  exit 2
fi

SOFFICE_WRAPPER="$(command -v soffice || true)"
if [[ -z "$SOFFICE_WRAPPER" ]]; then
  echo "未找到 soffice，无法打包 DOCX 预览运行时" >&2
  exit 3
fi
DEPENDENCY_ROOT="$(cd "$(dirname "$SOFFICE_WRAPPER")/../.." && pwd)"
LIBREOFFICE_SOURCE="$DEPENDENCY_ROOT/native/libreoffice-headless"
if [[ ! -d "$LIBREOFFICE_SOURCE" ]]; then
  echo "无法定位 LibreOffice 运行时：$LIBREOFFICE_SOURCE" >&2
  exit 3
fi

PYTHON_LINK="$(readlink "$SOURCE_ROOT/.venv/bin/python")"
PYTHON_EXECUTABLE="$(realpath "$PYTHON_LINK")"
PYTHON_SOURCE="$(dirname "$(dirname "$PYTHON_EXECUTABLE")")"
if [[ ! -x "$PYTHON_SOURCE/bin/python3.12" ]]; then
  echo "无法定位 Python 3.12 运行时：$PYTHON_SOURCE" >&2
  exit 3
fi

pnpm --dir "$SOURCE_ROOT/apps/web" build

mkdir -p "$TARGET_ROOT" "$SHORTCUT_DIR"
rsync -a \
  --exclude '.git/' \
  --exclude '.codex/' \
  --exclude '.venv/' \
  --exclude '.coverage' \
  --exclude '.DS_Store' \
  --exclude '.mypy_cache/' \
  --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' \
  --exclude 'data/' \
  --exclude 'node_modules/' \
  --exclude 'apps/web/node_modules/' \
  --exclude 'paper_setting.egg-info/' \
  "$SOURCE_ROOT/" "$TARGET_ROOT/"

mkdir -p "$TARGET_ROOT/runtime/python" "$TARGET_ROOT/runtime/codex-deps/bin/override"
rsync -a "$PYTHON_SOURCE/" "$TARGET_ROOT/runtime/python/"
rsync -a "$LIBREOFFICE_SOURCE/" "$TARGET_ROOT/runtime/codex-deps/native/libreoffice-headless/"
cp "$SOFFICE_WRAPPER" "$TARGET_ROOT/runtime/codex-deps/bin/override/soffice"
chmod +x "$TARGET_ROOT/runtime/codex-deps/bin/override/soffice"

cd "$TARGET_ROOT"
uv sync --frozen --no-dev --python "$TARGET_ROOT/runtime/python/bin/python3.12"
mkdir -p "$TARGET_ROOT/data/logs" "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
cp "$TARGET_ROOT/packaging/macos/Info.plist" "$APP_BUNDLE/Contents/Info.plist"
cp "$TARGET_ROOT/packaging/macos/AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
swiftc -parse-as-library -O \
  "$TARGET_ROOT/packaging/macos/PaperSettingApp.swift" \
  -o "$APP_BUNDLE/Contents/MacOS/论文排版台" \
  -framework AppKit \
  -framework WebKit
chmod +x "$APP_BUNDLE/Contents/MacOS/论文排版台"
printf 'APPL????' > "$APP_BUNDLE/Contents/PkgInfo"

PAPER_SETTING_ENV=production \
PAPER_SETTING_DATA_DIR="$TARGET_ROOT/data" \
PAPER_SETTING_DATABASE_URL="sqlite:///$TARGET_ROOT/data/paper-setting.db" \
PAPER_SETTING_WEB_DIST_DIR="$TARGET_ROOT/apps/web/dist" \
"$TARGET_ROOT/.venv/bin/paper-setting-init"

codesign --force --deep --sign - "$APP_BUNDLE"
codesign --verify --deep --strict "$APP_BUNDLE"

ln -s "$APP_BUNDLE" "$SHORTCUT"

echo "项目副本：$TARGET_ROOT"
echo "应用包：$APP_BUNDLE"
echo "快捷方式：$SHORTCUT"
