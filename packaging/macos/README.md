# 论文排版台本地应用 (macOS App)

## v1.1 构建与打包 (`package_app.sh`)

`packaging/macos/package_app.sh` 是 Paper Setting v1.1 推荐的原生 macOS 应用编译与分发打包脚本：

1. **编译原生外壳**：使用 `swiftc` 将 `PaperSettingApp.swift` (AppKit + WKWebView) 编译为独立二进制。
2. **同步元数据与图标**：复制 `Info.plist` (v1.1.0)、`PkgInfo` 与 `AppIcon.icns` 高清图标。
3. **本地代码签名**：执行 macOS 本地 Ad-hoc 签名与严格模式校验 (`codesign --verify --deep --strict`)。
4. **生成桌面快捷方式**：自动在 `~/Applications/vibe app/论文排版台.app` 创建软链接。
5. **生成 DMG 安装镜像**：生成 `dist/论文排版台-v1.1.dmg` 供分发。

执行命令：
```bash
./packaging/macos/package_app.sh
```

---

## 历史脚本说明

- `build_local_app.sh`：早期 v1.0 全量依赖隔离打包脚本（包含 LibreOffice 预览运行时）。
- `论文排版台`：早期 v1.0 服务端口 8765 的 Shell 启动封装。

