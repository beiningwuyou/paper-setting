#!/bin/bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_BUNDLE="$SOURCE_ROOT/论文排版台.app"
SHORTCUT_DIR="${SHORTCUT_DIR:-$HOME/Applications}"
SHORTCUT="$SHORTCUT_DIR/论文排版台.app"
DIST_DIR="$SOURCE_ROOT/dist"
DMG_PATH="$DIST_DIR/论文排版台-v1.1.dmg"

echo "========================================================"
echo "🔨 开始构建 macOS 本地应用: 论文排版台.app (v1.1.0)"
echo "========================================================"

if ! command -v swiftc >/dev/null 2>&1; then
  echo "❌ 错误: 未找到 Swift 编译器 (swiftc)" >&2
  exit 1
fi

# 1. 确保目标 Bundle 目录结构存在
echo "📦 [1/6] 准备 App Bundle 目录结构..."
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# 2. 编译 Swift 原生 AppKit + WKWebView 桌面外壳
echo "⚡ [2/6] 编译 Swift 原生桌面外壳 (PaperSettingApp.swift)..."
swiftc -parse-as-library -O \
  "$SOURCE_ROOT/packaging/macos/PaperSettingApp.swift" \
  -o "$APP_BUNDLE/Contents/MacOS/论文排版台" \
  -framework AppKit \
  -framework WebKit
chmod +x "$APP_BUNDLE/Contents/MacOS/论文排版台"

# 3. 复制元数据与应用图标
echo "🎨 [3/6] 同步 Info.plist、PkgInfo 与高清图标..."
cp "$SOURCE_ROOT/packaging/macos/Info.plist" "$APP_BUNDLE/Contents/Info.plist"
cp "$SOURCE_ROOT/packaging/macos/AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
printf 'APPL????' > "$APP_BUNDLE/Contents/PkgInfo"

# 4. 执行 macOS 本地代码签名 (Ad-hoc) 与校验
echo "🔐 [4/6] 执行本地 Ad-hoc 代码签名并验证严格模式..."
codesign --force --deep --sign - "$APP_BUNDLE"
codesign --verify --deep --strict "$APP_BUNDLE"
echo "✅ 签名校验通过!"

# 5. 更新用户启动快捷方式
echo "🔗 [5/6] 同步更新启动快捷方式..."
mkdir -p "$SHORTCUT_DIR"
rm -f "$SHORTCUT"
ln -s "$APP_BUNDLE" "$SHORTCUT"
echo "✅ 快捷方式已更新: $SHORTCUT"

# 6. 生成标准 DMG 安装镜像
echo "💿 [6/6] 生成分发安装镜像 (.dmg)..."
mkdir -p "$DIST_DIR"
DMG_STAGING="$(mktemp -d /tmp/paper_setting_dmg.XXXXXX)"
cp -R "$APP_BUNDLE" "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Applications"

rm -f "$DMG_PATH"
hdiutil create -volname "论文排版台" -srcfolder "$DMG_STAGING" -ov -format UDZO "$DMG_PATH"
rm -rf "$DMG_STAGING"

echo "========================================================"
echo "🎉 论文排版台本地桌面应用构建完成！"
echo "• 应用位置: $APP_BUNDLE"
echo "• 快捷方式: $SHORTCUT"
echo "• DMG镜像:  $DMG_PATH ($(du -sh "$DMG_PATH" | cut -f1))"
echo "========================================================"
