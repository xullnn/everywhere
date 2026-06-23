#if os(macOS)
import Foundation
import AppKit

final class MenuBarController {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)

    var onStartMock: (() -> Void)?
    var onStop: (() -> Void)?
    var onCopyLast: (() -> Void)?
    var onClearHistory: (() -> Void)?
    var onPromptPermissions: (() -> Void)?

    init() {
        setup()
    }

    func setStatus(_ text: String) {
        DispatchQueue.main.async {
            self.configureButton(for: text)
        }
    }

    private func setup() {
        configureButton(for: "🎙")
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Local Voice Input", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "开始一次模拟听写", action: #selector(startMock), keyEquivalent: "m"))
        menu.addItem(NSMenuItem(title: "停止/完成", action: #selector(stop), keyEquivalent: "s"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "复制上一条结果", action: #selector(copyLast), keyEquivalent: "v"))
        menu.addItem(NSMenuItem(title: "清空历史", action: #selector(clearHistory), keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "检查/申请权限", action: #selector(promptPermissions), keyEquivalent: "p"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "q"))
        for item in menu.items { item.target = self }
        statusItem.menu = menu
    }

    @objc private func startMock() { onStartMock?() }
    @objc private func stop() { onStop?() }
    @objc private func copyLast() { onCopyLast?() }
    @objc private func clearHistory() { onClearHistory?() }
    @objc private func promptPermissions() { onPromptPermissions?() }
    @objc private func quit() { NSApplication.shared.terminate(nil) }

    private func configureButton(for status: String) {
        guard let button = statusItem.button else { return }
        let symbolName: String
        let tooltip: String
        switch status {
        case "🔴":
            symbolName = "record.circle.fill"
            tooltip = "LocalVoiceInput - recording"
        case "⚠️":
            symbolName = "exclamationmark.triangle.fill"
            tooltip = "LocalVoiceInput - needs attention"
        default:
            symbolName = "mic.circle.fill"
            tooltip = "LocalVoiceInput - click for controls"
        }

        if let image = NSImage(systemSymbolName: symbolName, accessibilityDescription: tooltip) {
            image.isTemplate = true
            button.image = image
            button.title = ""
        } else {
            button.image = nil
            button.title = "LVI"
        }
        button.toolTip = tooltip
    }
}
#endif
