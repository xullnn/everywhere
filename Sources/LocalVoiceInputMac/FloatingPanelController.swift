#if os(macOS)
import Foundation
import AppKit
import LocalVoiceInputCore

final class FloatingPanelController {
    private var panel: NSPanel?
    private let titleLabel = NSTextField(labelWithString: "")
    private let transcriptLabel = NSTextField(labelWithString: "")
    private let detailLabel = NSTextField(labelWithString: "")
    private let cancelButton = NSButton(title: "取消", target: nil, action: nil)
    private let copyButton = NSButton(title: "复制", target: nil, action: nil)
    private let restoreButton = NSButton(title: "恢复剪切板", target: nil, action: nil)
    private let quitButton = NSButton(title: "退出 App", target: nil, action: nil)
    private var diagnosticText = ""

    var onCancel: (() -> Void)?
    var onCopy: (() -> Void)?
    var onRestoreClipboard: (() -> Void)?
    var onQuit: (() -> Void)?

    init() {
        setupControls()
    }

    func show(mode: OutputMode) {
        DispatchQueue.main.async {
            if self.panel == nil { self.createPanel() }
            self.updateMode(mode)
            self.panel?.orderFrontRegardless()
        }
    }

    func updateMode(_ mode: OutputMode) {
        DispatchQueue.main.async {
            let baseDetail: String
            switch mode {
            case .cursorPaste:
                self.titleLabel.stringValue = "🎙 正在听写到当前光标"
                baseDetail = "松开快捷键后将自动粘贴。"
            case .clipboardDraft:
                self.titleLabel.stringValue = "🎙 剪切板草稿模式"
                baseDetail = "未检测到输入框，结束后将自动复制。"
            case .fallbackCopy:
                self.titleLabel.stringValue = "⚠️ 复制兜底模式"
                baseDetail = "自动粘贴不可用，结果将保留在剪切板。"
            case .floatingDraft:
                self.titleLabel.stringValue = "🎙 浮窗草稿模式"
                baseDetail = "再次按快捷键结束，结果将复制并保存历史。"
            }
            self.detailLabel.stringValue = self.withDiagnostics(baseDetail)
        }
    }

    func updatePartial(_ text: String) {
        DispatchQueue.main.async {
            self.transcriptLabel.stringValue = text.isEmpty ? "正在等待语音…" : text
            self.detailLabel.stringValue = self.withDiagnostics("实时转写中…")
        }
    }

    func updateFinalizing() {
        DispatchQueue.main.async {
            self.detailLabel.stringValue = self.withDiagnostics("🧠 正在修正文字和标点…")
        }
    }

    func updateDone(status: PasteRouteStatus, text: String, restoredClipboard: Bool) {
        DispatchQueue.main.async {
            self.transcriptLabel.stringValue = text
            switch status {
            case .pasted:
                self.titleLabel.stringValue = "✅ 已粘贴"
                self.detailLabel.stringValue = self.withDiagnostics(restoredClipboard ? "结果已写入当前输入框，原剪切板已恢复。" : "结果已写入当前输入框，语音文本仍保留在剪切板。")
            case .copied:
                self.titleLabel.stringValue = "✅ 已复制"
                self.detailLabel.stringValue = self.withDiagnostics("点击任意输入框后按 ⌘V 粘贴。")
            case .copiedFallback:
                self.titleLabel.stringValue = "⚠️ 已复制"
                self.detailLabel.stringValue = self.withDiagnostics("自动粘贴失败或无法确认，结果已保留在剪切板。")
            case .cancelled:
                self.titleLabel.stringValue = "已取消"
                self.detailLabel.stringValue = self.withDiagnostics("本次内容未复制、未粘贴。")
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 5.0) { [weak self] in
                self?.hide()
            }
        }
    }

    func updateError(_ message: String) {
        DispatchQueue.main.async {
            if self.panel == nil { self.createPanel() }
            self.titleLabel.stringValue = "错误"
            self.transcriptLabel.stringValue = ""
            self.detailLabel.stringValue = self.withDiagnostics(message)
            self.panel?.orderFrontRegardless()
        }
    }

    func updateDiagnostics(_ text: String) {
        DispatchQueue.main.async {
            self.diagnosticText = text
            let current = self.detailLabel.stringValue
            if !current.isEmpty {
                self.detailLabel.stringValue = self.withDiagnostics(current.components(separatedBy: "\n").first ?? current)
            }
        }
    }

    func hide() {
        DispatchQueue.main.async { self.panel?.orderOut(nil) }
    }

    private func setupControls() {
        titleLabel.font = .systemFont(ofSize: 15, weight: .semibold)
        titleLabel.textColor = .labelColor
        transcriptLabel.font = .systemFont(ofSize: 18, weight: .regular)
        transcriptLabel.textColor = .labelColor
        transcriptLabel.lineBreakMode = .byTruncatingTail
        transcriptLabel.maximumNumberOfLines = 3
        detailLabel.font = .systemFont(ofSize: 12, weight: .regular)
        detailLabel.textColor = .secondaryLabelColor
        detailLabel.lineBreakMode = .byTruncatingTail
        detailLabel.maximumNumberOfLines = 2
        cancelButton.target = self
        cancelButton.action = #selector(cancelTapped)
        copyButton.target = self
        copyButton.action = #selector(copyTapped)
        restoreButton.target = self
        restoreButton.action = #selector(restoreTapped)
        quitButton.target = self
        quitButton.action = #selector(quitTapped)
    }

    private func createPanel() {
        let width: CGFloat = 720
        let height: CGFloat = 180
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let rect = NSRect(x: screen.midX - width / 2, y: screen.maxY - height - 30, width: width, height: height)
        let panel = NSPanel(contentRect: rect, styleMask: [.nonactivatingPanel, .hudWindow], backing: .buffered, defer: false)
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .transient]
        panel.hidesOnDeactivate = false
        panel.isFloatingPanel = true
        panel.titleVisibility = .hidden
        panel.titlebarAppearsTransparent = true
        panel.becomesKeyOnlyIfNeeded = false

        let content = NSView(frame: NSRect(x: 0, y: 0, width: width, height: height))
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.spacing = 10
        stack.alignment = .leading
        stack.translatesAutoresizingMaskIntoConstraints = false

        let buttonStack = NSStackView(views: [copyButton, restoreButton, cancelButton, quitButton])
        buttonStack.orientation = .horizontal
        buttonStack.spacing = 8
        buttonStack.alignment = .centerY

        stack.addArrangedSubview(titleLabel)
        stack.addArrangedSubview(transcriptLabel)
        stack.addArrangedSubview(detailLabel)
        stack.addArrangedSubview(buttonStack)
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 18),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -18),
            stack.topAnchor.constraint(equalTo: content.topAnchor, constant: 16),
            stack.bottomAnchor.constraint(lessThanOrEqualTo: content.bottomAnchor, constant: -16),
            transcriptLabel.widthAnchor.constraint(equalTo: stack.widthAnchor)
        ])
        panel.contentView = content
        self.panel = panel
    }

    @objc private func cancelTapped() {
        onCancel?()
    }

    @objc private func copyTapped() {
        onCopy?()
    }

    @objc private func restoreTapped() {
        onRestoreClipboard?()
    }

    @objc private func quitTapped() {
        onQuit?()
    }

    private func withDiagnostics(_ message: String) -> String {
        guard !diagnosticText.isEmpty else { return message }
        return "\(message)\n\(diagnosticText)"
    }
}
#endif
