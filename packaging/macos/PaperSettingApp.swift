import AppKit
import Foundation
import WebKit

private let appName = "论文排版台"
private let appURL = URL(string: "http://127.0.0.1:8770")!
private let webKitFrameLoadInterruptedByPolicyChange = 102

private enum LocalServiceState: Equatable {
    case ready
    case unavailable
    case differentInstance
}

@main
enum PaperSettingApplication {
    private static let appDelegate = AppDelegate()

    static func main() {
        let application = NSApplication.shared
        application.setActivationPolicy(.regular)
        application.delegate = appDelegate
        application.run()
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var loadingView: NSView!
    private var statusLabel: NSTextField!
    private var serverProcess: Process?
    private var serverLog: FileHandle?
    private var ownsServer = false
    private var isTerminating = false
    private var projectRoot: URL!
    private var recoveryWorkItem: DispatchWorkItem?
    // WKDownload does not retain itself while the delegate callbacks are in flight.
    // Keep each download alive until WebKit reports completion or failure.
    private var activeDownloads: [ObjectIdentifier: WKDownload] = [:]
    private var userCancelledDownloads: Set<ObjectIdentifier> = []

    func applicationDidFinishLaunching(_ notification: Notification) {
        projectRoot = findProjectRoot()
        configureMenu()
        configureWindow()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        prepareLocalService()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            window.makeKeyAndOrderFront(nil)
        }
        NSApp.activate(ignoringOtherApps: true)
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        isTerminating = true
        stopOwnedServer()
    }

    private func configureMenu() {
        let mainMenu = NSMenu()
        let applicationItem = NSMenuItem()
        mainMenu.addItem(applicationItem)
        let applicationMenu = NSMenu()
        applicationItem.submenu = applicationMenu
        applicationMenu.addItem(withTitle: "关于\(appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        applicationMenu.addItem(NSMenuItem.separator())
        applicationMenu.addItem(withTitle: "退出\(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")

        let editItem = NSMenuItem()
        mainMenu.addItem(editItem)
        let editMenu = NSMenu(title: "编辑")
        editItem.submenu = editMenu
        editMenu.addItem(withTitle: "撤销", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "重做", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "剪切", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "复制", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "粘贴", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "全选", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")

        let windowItem = NSMenuItem()
        mainMenu.addItem(windowItem)
        let windowMenu = NSMenu(title: "窗口")
        windowItem.submenu = windowMenu
        windowMenu.addItem(withTitle: "最小化", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "显示\(appName)", action: #selector(showMainWindow), keyEquivalent: "0")
        NSApp.windowsMenu = windowMenu
        NSApp.mainMenu = mainMenu
    }

    @objc private func showMainWindow() {
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func configureWindow() {
        let frame = NSRect(x: 0, y: 0, width: 1280, height: 850)
        window = NSWindow(
            contentRect: frame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "\(appName) v1.1 - 本地排版工作台"
        window.minSize = NSSize(width: 960, height: 680)
        window.center()
        window.isReleasedWhenClosed = false
        window.backgroundColor = NSColor(red: 0.933, green: 0.949, blue: 0.937, alpha: 1)

        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.applicationNameForUserAgent = "\(appName)/1.1"
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.translatesAutoresizingMaskIntoConstraints = false
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsMagnification = true

        loadingView = NSView()
        loadingView.translatesAutoresizingMaskIntoConstraints = false
        loadingView.wantsLayer = true
        loadingView.layer?.backgroundColor = NSColor(red: 0.933, green: 0.949, blue: 0.937, alpha: 1).cgColor

        let spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.controlSize = .large
        spinner.translatesAutoresizingMaskIntoConstraints = false
        spinner.startAnimation(nil)

        statusLabel = NSTextField(labelWithString: "正在启动本地排版引擎…")
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        statusLabel.font = NSFont.systemFont(ofSize: 14, weight: .medium)
        statusLabel.textColor = NSColor(red: 0.09, green: 0.31, blue: 0.29, alpha: 1)

        let content = NSView()
        content.addSubview(webView)
        content.addSubview(loadingView)
        loadingView.addSubview(spinner)
        loadingView.addSubview(statusLabel)
        window.contentView = content

        NSLayoutConstraint.activate([
            webView.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            webView.topAnchor.constraint(equalTo: content.topAnchor),
            webView.bottomAnchor.constraint(equalTo: content.bottomAnchor),
            loadingView.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            loadingView.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            loadingView.topAnchor.constraint(equalTo: content.topAnchor),
            loadingView.bottomAnchor.constraint(equalTo: content.bottomAnchor),
            spinner.centerXAnchor.constraint(equalTo: loadingView.centerXAnchor),
            spinner.centerYAnchor.constraint(equalTo: loadingView.centerYAnchor, constant: -14),
            statusLabel.centerXAnchor.constraint(equalTo: loadingView.centerXAnchor),
            statusLabel.topAnchor.constraint(equalTo: spinner.bottomAnchor, constant: 18),
        ])
    }

    private func findProjectRoot() -> URL {
        var candidate = Bundle.main.bundleURL.deletingLastPathComponent()
        for _ in 0..<7 {
            let launcher11 = candidate.appendingPathComponent("v1.1/run.py")
            let launcherLegacy = candidate.appendingPathComponent("scripts/start_local.py")
            if FileManager.default.fileExists(atPath: launcher11.path) || FileManager.default.fileExists(atPath: launcherLegacy.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        return Bundle.main.bundleURL.deletingLastPathComponent()
    }

    private func findPythonExecutable() -> URL? {
        let venvPython = projectRoot.appendingPathComponent(".venv/bin/python")
        if FileManager.default.isExecutableFile(atPath: venvPython.path) {
            return venvPython
        }
        let systemPython = URL(fileURLWithPath: "/usr/bin/python3")
        if FileManager.default.isExecutableFile(atPath: systemPython.path) {
            return systemPython
        }
        return nil
    }

    private func findLauncherScript() -> URL? {
        let launcher11 = projectRoot.appendingPathComponent("v1.1/run.py")
        if FileManager.default.fileExists(atPath: launcher11.path) {
            return launcher11
        }
        let legacy = projectRoot.appendingPathComponent("scripts/start_local.py")
        if FileManager.default.fileExists(atPath: legacy.path) {
            return legacy
        }
        return nil
    }

    private func prepareLocalService() {
        checkHealth { [weak self] state in
            guard let self else { return }
            switch state {
            case .ready:
                self.loadApplication()
            case .unavailable:
                self.startLocalService()
            case .differentInstance:
                self.showStartupFailure("端口 8770 正被另一份论文排版台或旧版本服务占用。请先退出另一份应用后重试。")
            }
        }
    }

    private func startLocalService() {
        guard let python = findPythonExecutable(), let launcher = findLauncherScript() else {
            showStartupFailure("本地 Python 运行时或启动脚本缺失。请确认工程目录完整。")
            return
        }

        let logDirectory = projectRoot.appendingPathComponent("data/logs", isDirectory: true)
        let runDirectory = projectRoot.appendingPathComponent("data/run", isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: logDirectory, withIntermediateDirectories: true)
            try FileManager.default.createDirectory(at: runDirectory, withIntermediateDirectories: true)
            let logURL = logDirectory.appendingPathComponent("论文排版台.log")
            if !FileManager.default.fileExists(atPath: logURL.path) {
                FileManager.default.createFile(atPath: logURL.path, contents: nil)
            }
            serverLog = try FileHandle(forWritingTo: logURL)
            try serverLog?.seekToEnd()

            let process = Process()
            process.executableURL = python
            process.arguments = [launcher.path]
            process.currentDirectoryURL = projectRoot
            var environment = ProcessInfo.processInfo.environment
            environment["PATH"] = [
                projectRoot.appendingPathComponent(".venv/bin").path,
                "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
            ].joined(separator: ":")
            environment["PAPER_SETTING_ENV"] = "production"
            environment["PAPER_SETTING_INSTANCE_ID"] = expectedInstanceID()
            environment["PORT"] = "8770"
            environment["NO_BROWSER"] = "1"
            environment["PYTHONUNBUFFERED"] = "1"
            process.environment = environment
            process.standardOutput = serverLog
            process.standardError = serverLog
            process.terminationHandler = { [weak self] terminated in
                DispatchQueue.main.async {
                    guard let self, !self.isTerminating, self.ownsServer else { return }
                    self.showStartupFailure("本地排版引擎已停止（退出码 \(terminated.terminationStatus)）。请查看 data/logs/论文排版台.log。")
                }
            }
            try process.run()
            serverProcess = process
            ownsServer = true
            let pidURL = runDirectory.appendingPathComponent("paper-setting-native.pid")
            try String(process.processIdentifier).write(to: pidURL, atomically: true, encoding: .utf8)
            waitForServer(attempt: 0)
        } catch {
            showStartupFailure("无法启动本地排版引擎：\(error.localizedDescription)")
        }
    }

    private func waitForServer(attempt: Int) {
        checkHealth { [weak self] state in
            guard let self else { return }
            if state == .ready {
                self.loadApplication()
                return
            }
            if state == .differentInstance {
                self.showStartupFailure("端口 8770 已被另一份论文排版台占用。请先退出另一份应用后重试。")
                return
            }
            if let process = self.serverProcess, !process.isRunning {
                self.showStartupFailure("本地排版引擎启动失败。请查看 data/logs/论文排版台.log。")
                return
            }
            guard attempt < 300 else {
                self.showStartupFailure("本地排版引擎未在 30 秒内就绪。")
                return
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                self.waitForServer(attempt: attempt + 1)
            }
        }
    }

    private func expectedInstanceID() -> String {
        Data(projectRoot.path.utf8).base64EncodedString()
    }

    private func checkHealth(completion: @escaping (LocalServiceState) -> Void) {
        var request = URLRequest(url: appURL.appendingPathComponent("ready"))
        request.timeoutInterval = 1
        URLSession.shared.dataTask(with: request) { _, response, _ in
            guard let httpResponse = response as? HTTPURLResponse else {
                DispatchQueue.main.async { completion(.unavailable) }
                return
            }
            let instanceID = httpResponse.value(forHTTPHeaderField: "X-Paper-Setting-Instance")
            let state: LocalServiceState
            if let instanceID, !instanceID.isEmpty, instanceID != self.expectedInstanceID() {
                state = .differentInstance
            } else {
                state = httpResponse.statusCode == 200 ? .ready : .unavailable
            }
            DispatchQueue.main.async { completion(state) }
        }.resume()
    }

    private func loadApplication() {
        recoveryWorkItem?.cancel()
        recoveryWorkItem = nil
        loadingView.isHidden = false
        statusLabel.stringValue = "正在打开论文排版台…"
        var request = URLRequest(url: appURL)
        request.cachePolicy = .useProtocolCachePolicy
        webView.load(request)
    }

    private func isExpectedNavigationInterruption(_ error: Error) -> Bool {
        let navigationError = error as NSError
        if navigationError.domain == WKError.errorDomain,
           navigationError.code == webKitFrameLoadInterruptedByPolicyChange {
            return true
        }
        return navigationError.domain == NSURLErrorDomain && navigationError.code == NSURLErrorCancelled
    }

    private func recoverNavigation(after error: Error, attempt: Int = 0) {
        recoveryWorkItem?.cancel()
        loadingView.isHidden = false
        statusLabel.stringValue = attempt == 0
            ? "本地服务连接中断，正在自动恢复…"
            : "正在重新连接本地服务…（\(attempt)/30）"

        let workItem = DispatchWorkItem { [weak self] in
            guard let self, !self.isTerminating else { return }
            self.checkHealth { [weak self] state in
                guard let self, !self.isTerminating else { return }
                if state == .ready {
                    self.loadApplication()
                } else if state == .differentInstance {
                    self.statusLabel.stringValue = "端口 8770 已被另一份论文排版台占用。"
                } else if attempt < 30 {
                    self.recoverNavigation(after: error, attempt: attempt + 1)
                } else {
                    self.statusLabel.stringValue = "本地服务暂时不可用，请重新打开应用。"
                }
            }
        }
        recoveryWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + (attempt == 0 ? 0.2 : 0.5), execute: workItem)
    }

    private func stopOwnedServer() {
        guard ownsServer, let process = serverProcess, process.isRunning else { return }
        ownsServer = false
        process.terminate()
        let pidURL = projectRoot.appendingPathComponent("data/run/paper-setting-native.pid")
        try? FileManager.default.removeItem(at: pidURL)
        try? serverLog?.close()
    }

    private func showStartupFailure(_ message: String) {
        statusLabel.stringValue = message
        let alert = NSAlert()
        alert.alertStyle = .critical
        alert.messageText = "\(appName)无法启动"
        alert.informativeText = message
        alert.addButton(withTitle: "重试")
        alert.addButton(withTitle: "退出")
        alert.beginSheetModal(for: window) { [weak self] response in
            if response == .alertFirstButtonReturn {
                self?.prepareLocalService()
            } else {
                NSApp.terminate(nil)
            }
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        recoveryWorkItem?.cancel()
        recoveryWorkItem = nil
        loadingView.isHidden = true
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        if isExpectedNavigationInterruption(error) {
            loadingView.isHidden = true
            return
        }
        recoverNavigation(after: error)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        if isExpectedNavigationInterruption(error) {
            loadingView.isHidden = true
            return
        }
        recoverNavigation(after: error)
    }

    func webView(
        _ webView: WKWebView,
        runOpenPanelWith parameters: WKOpenPanelParameters,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping ([URL]?) -> Void
    ) {
        let panel = NSOpenPanel()
        panel.title = "选择本地文件"
        panel.message = "文件只会交给本机运行的论文排版台处理。"
        panel.prompt = "选择"
        panel.canChooseFiles = true
        panel.canChooseDirectories = parameters.allowsDirectories
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.resolvesAliases = true
        NSApp.activate(ignoringOtherApps: true)
        panel.beginSheetModal(for: window) { response in
            completionHandler(response == .OK ? panel.urls : nil)
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if #available(macOS 11.3, *), navigationAction.shouldPerformDownload {
            loadingView.isHidden = true
            decisionHandler(.download)
            return
        }
        if let url = navigationAction.request.url,
           let host = url.host,
           host != "127.0.0.1" && host != "localhost",
           navigationAction.navigationType == .linkActivated {
            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationResponse: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        if #available(macOS 11.3, *), !navigationResponse.canShowMIMEType {
            loadingView.isHidden = true
            decisionHandler(.download)
        } else {
            decisionHandler(.allow)
        }
    }

    @available(macOS 11.3, *)
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        loadingView.isHidden = true
        activeDownloads[ObjectIdentifier(download)] = download
        download.delegate = self
    }

    @available(macOS 11.3, *)
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        loadingView.isHidden = true
        activeDownloads[ObjectIdentifier(download)] = download
        download.delegate = self
    }

    @available(macOS 11.3, *)
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let identifier = ObjectIdentifier(download)
        let panel = NSSavePanel()
        panel.nameFieldStringValue = suggestedFilename
        panel.canCreateDirectories = true
        panel.beginSheetModal(for: window) { result in
            guard result == .OK, let destination = panel.url else {
                self.userCancelledDownloads.insert(identifier)
                completionHandler(nil)
                return
            }

            // WKDownload requires a destination that does not already exist. The
            // save panel has already confirmed replacement, so remove the old file
            // before handing the URL back to WebKit.
            if FileManager.default.fileExists(atPath: destination.path) {
                do {
                    try FileManager.default.removeItem(at: destination)
                } catch {
                    self.activeDownloads.removeValue(forKey: identifier)
                    completionHandler(nil)
                    self.presentDownloadError(error)
                    return
                }
            }
            completionHandler(destination)
        }
    }

    @available(macOS 11.3, *)
    func downloadDidFinish(_ download: WKDownload) {
        let identifier = ObjectIdentifier(download)
        activeDownloads.removeValue(forKey: identifier)
        userCancelledDownloads.remove(identifier)
    }

    @available(macOS 11.3, *)
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        let identifier = ObjectIdentifier(download)
        activeDownloads.removeValue(forKey: identifier)
        let wasCancelledByUser = userCancelledDownloads.remove(identifier) != nil
        let cocoaError = error as NSError
        if wasCancelledByUser ||
            (cocoaError.domain == NSURLErrorDomain && cocoaError.code == NSURLErrorCancelled) {
            return
        }
        presentDownloadError(error)
    }

    private func presentDownloadError(_ error: Error) {
        let alert = NSAlert()
        alert.alertStyle = .warning
        alert.messageText = "下载失败"
        alert.informativeText = error.localizedDescription
        alert.beginSheetModal(for: window)
    }
}
