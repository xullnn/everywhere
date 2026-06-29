#if os(macOS)
import Foundation
import AppKit
import LocalVoiceInputCore

final class FloatingPanelController {
    private enum Layout {
        static let panelWidth: CGFloat = 760
        static let panelHeight: CGFloat = 220
        static let cornerRadius: CGFloat = 18
        static let horizontalInset: CGFloat = 20
        static let verticalInset: CGFloat = 16
        static let transcriptHeight: CGFloat = 104
    }

    private var panel: NSPanel?
    private let titleLabel = NSTextField(labelWithString: "")
    private let transcriptScrollView = NSScrollView(frame: .zero)
    private let transcriptTextView = NSTextView(frame: .zero)
    private let detailLabel = NSTextField(labelWithString: "")
    private let finishButton = NSButton(title: "完成", target: nil, action: nil)
    private let cancelButton = NSButton(title: "取消", target: nil, action: nil)
    private let copyButton = NSButton(title: "复制", target: nil, action: nil)
    private let restoreButton = NSButton(title: "恢复剪切板", target: nil, action: nil)
    private let quitButton = NSButton(title: "退出 App", target: nil, action: nil)
    private var diagnosticText = ""
    private var presentationGeneration = 0
    private var pendingHideWorkItem: DispatchWorkItem?
    private var fadeTimer: DispatchSourceTimer?
    private var isMouseInsidePanel = false
    private var autoDismissEnabled = false
    private let autoDismissHoldSeconds: TimeInterval = 2.0
    private let fadeOutSeconds: TimeInterval = 4.0

    var onCancel: (() -> Void)?
    var onFinish: (() -> Void)?
    var onCopy: (() -> Void)?
    var onRestoreClipboard: (() -> Void)?
    var onQuit: (() -> Void)?

    init() {
        setupControls()
    }

    func show(mode: OutputMode) {
        DispatchQueue.main.async {
            self.startNewPresentation()
            self.ensureVisible()
            self.updateMode(mode)
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
            self.ensureVisible()
            self.setTranscriptText(text.isEmpty ? "正在等待语音…" : text)
            self.detailLabel.stringValue = self.withDiagnostics("实时转写中…")
        }
    }

    func updateFinalizing() {
        DispatchQueue.main.async {
            self.ensureVisible()
            self.detailLabel.stringValue = self.withDiagnostics("🧠 正在修正文字和标点…")
        }
    }

    func updateDone(status: PasteRouteStatus, text: String, restoredClipboard: Bool) {
        DispatchQueue.main.async {
            self.ensureVisible()
            self.setTranscriptText(text)
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
            self.autoDismissEnabled = true
            self.scheduleAutoHide(after: self.autoDismissHoldSeconds)
        }
    }

    func updateError(_ message: String) {
        DispatchQueue.main.async {
            self.startNewPresentation()
            self.ensureVisible()
            self.titleLabel.stringValue = "错误"
            self.setTranscriptText("")
            self.detailLabel.stringValue = self.withDiagnostics(message)
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
        DispatchQueue.main.async {
            self.cancelPendingHide()
            self.autoDismissEnabled = false
            self.presentationGeneration += 1
            self.panel?.orderOut(nil)
            self.panel?.alphaValue = 1.0
        }
    }

    private func setupControls() {
        titleLabel.font = .systemFont(ofSize: 15, weight: .semibold)
        titleLabel.textColor = .labelColor
        transcriptTextView.font = .systemFont(ofSize: 18, weight: .regular)
        transcriptTextView.textColor = .labelColor
        transcriptTextView.drawsBackground = false
        transcriptTextView.isEditable = false
        transcriptTextView.isSelectable = false
        transcriptTextView.isRichText = false
        transcriptTextView.importsGraphics = false
        transcriptTextView.textContainerInset = NSSize(width: 0, height: 0)
        transcriptTextView.textContainer?.lineFragmentPadding = 0
        transcriptTextView.textContainer?.widthTracksTextView = true
        transcriptTextView.textContainer?.containerSize = NSSize(width: 0, height: CGFloat.greatestFiniteMagnitude)
        transcriptTextView.isHorizontallyResizable = false
        transcriptTextView.isVerticallyResizable = true
        transcriptTextView.autoresizingMask = [.width]
        transcriptScrollView.drawsBackground = false
        transcriptScrollView.borderType = .noBorder
        transcriptScrollView.hasVerticalScroller = true
        transcriptScrollView.hasHorizontalScroller = false
        transcriptScrollView.autohidesScrollers = true
        transcriptScrollView.verticalScrollElasticity = .allowed
        transcriptScrollView.horizontalScrollElasticity = .none
        transcriptScrollView.contentView.drawsBackground = false
        transcriptScrollView.documentView = transcriptTextView
        detailLabel.font = .systemFont(ofSize: 12, weight: .regular)
        detailLabel.textColor = .secondaryLabelColor
        detailLabel.lineBreakMode = .byTruncatingTail
        detailLabel.maximumNumberOfLines = 2
        finishButton.target = self
        finishButton.action = #selector(finishTapped)
        cancelButton.target = self
        cancelButton.action = #selector(cancelTapped)
        copyButton.target = self
        copyButton.action = #selector(copyTapped)
        restoreButton.target = self
        restoreButton.action = #selector(restoreTapped)
        quitButton.target = self
        quitButton.action = #selector(quitTapped)
        [finishButton, cancelButton, copyButton, restoreButton, quitButton].forEach { button in
            button.bezelStyle = .rounded
            button.controlSize = .small
            button.font = .systemFont(ofSize: 12, weight: .medium)
        }
    }

    private func createPanel() {
        let width = Layout.panelWidth
        let height = Layout.panelHeight
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let rect = NSRect(x: screen.midX - width / 2, y: screen.maxY - height - 30, width: width, height: height)
        let panel = NSPanel(contentRect: rect, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .transient]
        panel.hidesOnDeactivate = false
        panel.isFloatingPanel = true
        panel.titleVisibility = .hidden
        panel.titlebarAppearsTransparent = true
        panel.becomesKeyOnlyIfNeeded = false

        let content = FloatingPanelContentView(frame: NSRect(x: 0, y: 0, width: width, height: height), cornerRadius: Layout.cornerRadius)
        content.onMouseEnteredPanel = { [weak self] in self?.pauseAutoDismissForHover() }
        content.onMouseExitedPanel = { [weak self] in self?.resumeAutoDismissAfterHover() }
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.spacing = 10
        stack.alignment = .leading
        stack.translatesAutoresizingMaskIntoConstraints = false

        let buttonStack = NSStackView(views: [copyButton, restoreButton, finishButton, cancelButton, quitButton])
        buttonStack.orientation = .horizontal
        buttonStack.spacing = 8
        buttonStack.alignment = .centerY

        stack.addArrangedSubview(titleLabel)
        stack.addArrangedSubview(transcriptScrollView)
        stack.addArrangedSubview(detailLabel)
        stack.addArrangedSubview(buttonStack)
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: Layout.horizontalInset),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -Layout.horizontalInset),
            stack.topAnchor.constraint(equalTo: content.topAnchor, constant: Layout.verticalInset),
            stack.bottomAnchor.constraint(lessThanOrEqualTo: content.bottomAnchor, constant: -Layout.verticalInset),
            transcriptScrollView.widthAnchor.constraint(equalTo: stack.widthAnchor),
            transcriptScrollView.heightAnchor.constraint(equalToConstant: Layout.transcriptHeight)
        ])
        panel.contentView = content
        self.panel = panel
    }

    private func startNewPresentation() {
        cancelPendingHide()
        autoDismissEnabled = false
        presentationGeneration += 1
        panel?.alphaValue = 1.0
    }

    private func cancelPendingHide() {
        pendingHideWorkItem?.cancel()
        pendingHideWorkItem = nil
        fadeTimer?.cancel()
        fadeTimer = nil
    }

    private func ensureVisible() {
        if panel == nil { createPanel() }
        panel?.alphaValue = 1.0
        panel?.orderFrontRegardless()
    }

    private func scheduleAutoHide(after delay: TimeInterval) {
        cancelPendingHide()
        guard autoDismissEnabled, !isMouseInsidePanel else { return }
        let generation = presentationGeneration
        let workItem = DispatchWorkItem { [weak self] in
            guard let self, self.presentationGeneration == generation else { return }
            self.beginFadeOut(generation: generation)
        }
        pendingHideWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: workItem)
    }

    private func beginFadeOut(generation: Int) {
        guard autoDismissEnabled, !isMouseInsidePanel, presentationGeneration == generation, let panel else {
            return
        }
        pendingHideWorkItem = nil
        fadeTimer?.cancel()

        let startedAt = Date()
        var timer: DispatchSourceTimer!
        timer = DispatchSource.makeTimerSource(queue: .main)
        timer.schedule(deadline: .now(), repeating: .milliseconds(33))
        timer.setEventHandler { [weak self, weak panel] in
            guard let self,
                  let panel,
                  self.presentationGeneration == generation,
                  self.autoDismissEnabled,
                  !self.isMouseInsidePanel else {
                timer.cancel()
                return
            }
            let progress = min(1.0, Date().timeIntervalSince(startedAt) / self.fadeOutSeconds)
            let easedProgress = progress * progress * (3.0 - 2.0 * progress)
            panel.alphaValue = max(0.0, 1.0 - easedProgress)

            if progress >= 1.0 {
                timer.cancel()
                self.fadeTimer = nil
                panel.orderOut(nil)
                panel.alphaValue = 1.0
                self.autoDismissEnabled = false
            }
        }
        fadeTimer = timer
        timer.resume()
    }

    private func pauseAutoDismissForHover() {
        guard panel?.isVisible == true else { return }
        isMouseInsidePanel = true
        cancelPendingHide()
        presentationGeneration += 1
        panel?.alphaValue = 1.0
    }

    private func resumeAutoDismissAfterHover() {
        isMouseInsidePanel = false
        guard autoDismissEnabled else { return }
        presentationGeneration += 1
        panel?.alphaValue = 1.0
        scheduleAutoHide(after: autoDismissHoldSeconds)
    }

    private func refreshAutoDismissAfterUserAction() {
        guard autoDismissEnabled else { return }
        presentationGeneration += 1
        panel?.alphaValue = 1.0
        scheduleAutoHide(after: autoDismissHoldSeconds)
    }

    @objc private func cancelTapped() {
        onCancel?()
    }

    @objc private func finishTapped() {
        onFinish?()
    }

    @objc private func copyTapped() {
        refreshAutoDismissAfterUserAction()
        onCopy?()
    }

    @objc private func restoreTapped() {
        refreshAutoDismissAfterUserAction()
        onRestoreClipboard?()
    }

    @objc private func quitTapped() {
        onQuit?()
    }

    private func withDiagnostics(_ message: String) -> String {
        guard !diagnosticText.isEmpty else { return message }
        return "\(message)\n\(diagnosticText)"
    }

    private func setTranscriptText(_ text: String) {
        transcriptTextView.string = text
        transcriptTextView.layoutManager?.ensureLayout(for: transcriptTextView.textContainer!)
        transcriptTextView.scrollRangeToVisible(NSRange(location: (text as NSString).length, length: 0))
    }
}

private final class FloatingPanelContentView: NSVisualEffectView {
    var onMouseEnteredPanel: (() -> Void)?
    var onMouseExitedPanel: (() -> Void)?
    private var trackingArea: NSTrackingArea?
    private let cornerRadius: CGFloat

    init(frame frameRect: NSRect, cornerRadius: CGFloat) {
        self.cornerRadius = cornerRadius
        super.init(frame: frameRect)
        configureAppearance()
    }

    required init?(coder: NSCoder) {
        self.cornerRadius = 18
        super.init(coder: coder)
        configureAppearance()
    }

    override func viewDidChangeEffectiveAppearance() {
        super.viewDidChangeEffectiveAppearance()
        updateLayerStyle()
    }

    private func configureAppearance() {
        blendingMode = .behindWindow
        material = .hudWindow
        state = .active
        wantsLayer = true
        updateLayerStyle()
    }

    private func updateLayerStyle() {
        layer?.cornerRadius = cornerRadius
        layer?.cornerCurve = .continuous
        layer?.masksToBounds = true
        layer?.borderWidth = 1
        layer?.borderColor = NSColor.separatorColor.withAlphaComponent(0.28).cgColor
    }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let trackingArea {
            removeTrackingArea(trackingArea)
        }
        let options: NSTrackingArea.Options = [.mouseEnteredAndExited, .activeAlways, .inVisibleRect]
        let area = NSTrackingArea(rect: .zero, options: options, owner: self, userInfo: nil)
        addTrackingArea(area)
        trackingArea = area
    }

    override func mouseEntered(with event: NSEvent) {
        super.mouseEntered(with: event)
        onMouseEnteredPanel?()
    }

    override func mouseExited(with event: NSEvent) {
        super.mouseExited(with: event)
        onMouseExitedPanel?()
    }

    override func acceptsFirstMouse(for event: NSEvent?) -> Bool {
        true
    }
}
#endif
