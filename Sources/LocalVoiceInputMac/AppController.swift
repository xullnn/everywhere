#if os(macOS)
import Foundation
import AppKit
import LocalVoiceInputCore

final class AppController {
    private let config: AppConfig
    private let menu = MenuBarController()
    private let panel = FloatingPanelController()
    private let focusDetector = FocusDetector()
    private let hotkeys = HotkeyController()
    private let audio = AudioCapture()
    private let clipboard = ClipboardManager()
    private let keyboard = KeyboardSimulator()
    private lazy var pasteEngine = PasteEngine(clipboard: clipboard, keyboard: keyboard, policy: config.outputPolicy)
    private lazy var history = HistoryStore(policy: HistoryPolicy(maxItems: config.historyMaxItems))

    private var activeASR: ASRClientProtocol?
    private var stateMachine = VoiceSessionStateMachine()
    private var transcript: TranscriptBuffer?
    private var activeSessionId: String?
    private var activeSessionType: SessionType = .pushToTalk
    private var initialFocus = FocusSnapshot.unknown
    private var activeOutputMode: OutputMode = .clipboardDraft
    private var lastFinalText: String = ""
    private var didFinalize = false
    private var forceMockForCurrentSession = false
    private var userRequestedFinish = false
    private var focusTracker: FocusChangeTracker?
    private var focusMonitorTimer: Timer?
    private var activeASRClientId: ObjectIdentifier?

    init(config: AppConfig) {
        self.config = config
    }

    func start() {
        ConfigPaths.ensureDirectories()
        PermissionManager.requestMicrophoneIfNeeded()
        if !PermissionManager.accessibilityTrusted {
            PermissionManager.promptAccessibilityIfNeeded()
        }
        if !PermissionManager.inputMonitoringTrusted {
            PermissionManager.requestInputMonitoringIfNeeded()
        }
        setupCallbacks()
        hotkeys.start()
        menu.setStatus("🎙")
    }

    func stop() {
        hotkeys.stop()
        cancelSession()
    }

    private func setupCallbacks() {
        menu.onStartMock = { [weak self] in self?.beginSession(type: .pushToTalk, forceMock: true) }
        menu.onStop = { [weak self] in self?.finishSession() }
        menu.onCopyLast = { [weak self] in self?.copyLastResult() }
        menu.onClearHistory = { [weak self] in self?.history.clear() }
        menu.onPromptPermissions = {
            PermissionManager.requestMicrophoneIfNeeded()
            PermissionManager.promptAccessibilityIfNeeded()
            PermissionManager.requestInputMonitoringIfNeeded()
        }

        panel.onCancel = { [weak self] in self?.cancelSession() }
        panel.onCopy = { [weak self] in
            guard let self else { return }
            let text = self.lastFinalText.isEmpty ? self.transcript?.latestText ?? "" : self.lastFinalText
            if !text.isEmpty {
                self.clipboard.writeString(text)
                self.panel.updateDone(status: .copied, text: text, restoredClipboard: false)
            }
        }
        panel.onRestoreClipboard = { [weak self] in self?.clipboard.restoreLastSavedSnapshot() }
        panel.onQuit = {
            NSApplication.shared.terminate(nil)
        }

        hotkeys.onPushToTalkStart = { [weak self] in self?.beginSession(type: .pushToTalk, forceMock: false) }
        hotkeys.onPushToTalkStop = { [weak self] in self?.finishSession() }
        hotkeys.onToggleLongDraft = { [weak self] in self?.toggleLongDraft() }
        hotkeys.onCancel = { [weak self] in self?.cancelSession() }
        hotkeys.onError = { [weak self] message in self?.panel.updateError(message) }

        audio.onPCMChunk = { [weak self] data in
            DispatchQueue.main.async { self?.sendPCMToActiveASR(data) }
        }
        audio.onError = { [weak self] error in
            DispatchQueue.main.async { self?.handleError(error) }
        }
    }

    private func beginSession(type: SessionType, forceMock: Bool) {
        DispatchQueue.main.async {
            guard self.activeSessionId == nil else { return }
            self.stateMachine = VoiceSessionStateMachine()
            self.stateMachine.send(.hotkeyDown)
            self.activeSessionType = type
            self.forceMockForCurrentSession = forceMock
            self.didFinalize = false
            self.userRequestedFinish = false
            self.lastFinalText = ""
            self.initialFocus = self.focusDetector.snapshot()
            self.focusTracker = FocusChangeTracker(initial: self.initialFocus)
            self.activeOutputMode = OutputModeRouter.decide(
                snapshot: self.initialFocus,
                sessionType: type,
                focusChangedDuringRecording: false,
                policy: self.config.outputPolicy
            )
            self.panel.updateDiagnostics(self.focusDiagnostic(self.initialFocus, mode: self.activeOutputMode, changed: false))
            let sessionId = UUID().uuidString
            self.activeSessionId = sessionId
            self.transcript = TranscriptBuffer(sessionId: sessionId)
            self.stateMachine.send(.focusChecked)
            self.hotkeys.noteSessionStarted(type: type)
            self.panel.show(mode: self.activeOutputMode)
            self.menu.setStatus("🔴")
            self.startFocusMonitoring(sessionId: sessionId)
            self.startASR(sessionId: sessionId, forceMock: forceMock)
            guard self.activeSessionId == sessionId else { return }
            if !(self.config.mockASR || forceMock) {
                self.audio.start()
            }
        }
    }

    private func startASR(sessionId: String, forceMock: Bool) {
        let client: ASRClientProtocol
        if config.mockASR || forceMock {
            client = MockASRClient(transcript: config.mockTranscript)
        } else {
            client = FunASRClient(urlString: config.asrURL)
        }
        let clientId = ObjectIdentifier(client)
        client.onEvent = { [weak self, sessionId, clientId] event in
            DispatchQueue.main.async {
                self?.handleASREvent(event, expectedSessionId: sessionId, clientId: clientId)
            }
        }
        client.onError = { [weak self, sessionId, clientId] error in
            DispatchQueue.main.async {
                self?.handleError(error, expectedSessionId: sessionId, clientId: clientId)
            }
        }
        activeASR = client
        activeASRClientId = clientId
        client.start(sessionId: sessionId, hotwords: config.hotwords)
    }

    private func finishSession() {
        DispatchQueue.main.async {
            guard let sessionId = self.activeSessionId, !self.userRequestedFinish else { return }
            self.userRequestedFinish = true
            if self.stateMachine.state == .recording {
                self.stateMachine.send(.hotkeyUp)
            }
            self.panel.updateFinalizing()
            self.recomputeOutputModeForFocusChange()

            if self.config.mockASR || self.forceMockForCurrentSession {
                self.activeASR?.finish()
                self.scheduleFinalizeTimeout(seconds: 2.0, sessionId: sessionId)
                return
            }

            self.audio.stopAndFlush { [weak self, sessionId] remainingChunks in
                guard let self else { return }
                guard self.activeSessionId == sessionId, self.userRequestedFinish else { return }
                for chunk in remainingChunks {
                    self.activeASR?.sendPCM(chunk)
                }
                self.activeASR?.finish()
                self.scheduleFinalizeTimeout(seconds: 3.5, sessionId: sessionId)
            }
        }
    }

    private func scheduleFinalizeTimeout(seconds: TimeInterval, sessionId: String) {
        DispatchQueue.main.asyncAfter(deadline: .now() + seconds) { [weak self] in
            self?.finalizeIfNeeded(reason: "timeout", expectedSessionId: sessionId)
        }
    }

    private func cancelSession() {
        DispatchQueue.main.async {
            guard self.activeSessionId != nil else { return }
            self.stateMachine.send(.cancel)
            self.audio.cancel()
            self.activeASR?.cancel()
            self.activeASR = nil
            self.activeASRClientId = nil
            self.activeSessionId = nil
            self.transcript = nil
            self.didFinalize = false
            self.userRequestedFinish = false
            self.forceMockForCurrentSession = false
            self.focusTracker = nil
            self.stopFocusMonitoring()
            self.hotkeys.noteSessionEnded()
            self.menu.setStatus("🎙")
            self.panel.updateDone(status: .cancelled, text: "", restoredClipboard: false)
        }
    }

    private func toggleLongDraft() {
        if activeSessionId == nil {
            beginSession(type: .longDraft, forceMock: false)
        } else if activeSessionType == .longDraft {
            finishSession()
        }
    }

    private func handleASREvent(_ event: ASREvent, expectedSessionId: String, clientId: ObjectIdentifier) {
        guard isCurrentASR(sessionId: expectedSessionId, clientId: clientId) else { return }
        guard event.sessionId == expectedSessionId else { return }
        guard var buffer = transcript else { return }
        buffer.apply(event)
        transcript = buffer

        switch ASREventRouter.disposition(for: event, state: stateMachine.state, userRequestedFinish: userRequestedFinish) {
        case .updatePartial:
            panel.updatePartial(buffer.latestText)
        case .finalize:
            finalizeIfNeeded(reason: event.mode == .offline ? "offline_final" : "unknown_final", expectedSessionId: expectedSessionId)
        }
    }

    private func recomputeOutputModeForFocusChange() {
        let latest = focusDetector.snapshot()
        updateFocusTracker(with: latest)
        updateOutputModeForCurrentFocusState()
    }

    private func updateFocusTracker(with latest: FocusSnapshot) {
        if focusTracker == nil {
            focusTracker = FocusChangeTracker(initial: initialFocus)
        }
        guard var tracker = focusTracker else { return }
        tracker.observe(latest)
        focusTracker = tracker
    }

    private func updateOutputModeForCurrentFocusState() {
        let changed = focusTracker?.didChange ?? false
        let newMode = OutputModeRouter.decide(
            snapshot: initialFocus,
            sessionType: activeSessionType,
            focusChangedDuringRecording: changed,
            policy: config.outputPolicy
        )
        if newMode != activeOutputMode {
            activeOutputMode = newMode
            panel.updateMode(newMode)
        }
        panel.updateDiagnostics(focusDiagnostic(initialFocus, mode: activeOutputMode, changed: changed))
    }

    private func startFocusMonitoring(sessionId: String) {
        stopFocusMonitoring()
        focusMonitorTimer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
            self?.recordFocusSample(sessionId: sessionId)
        }
    }

    private func stopFocusMonitoring() {
        focusMonitorTimer?.invalidate()
        focusMonitorTimer = nil
    }

    private func recordFocusSample(sessionId: String) {
        guard activeSessionId == sessionId else { return }
        let wasChanged = focusTracker?.didChange ?? false
        updateFocusTracker(with: focusDetector.snapshot())
        let changed = focusTracker?.didChange ?? false
        if changed && !wasChanged {
            updateOutputModeForCurrentFocusState()
        }
    }

    private func finalizeIfNeeded(reason: String, expectedSessionId: String? = nil) {
        guard !didFinalize, let currentSessionId = activeSessionId else { return }
        if let expectedSessionId, expectedSessionId != currentSessionId { return }
        didFinalize = true
        stateMachine.send(.finalASRReceived)
        activeASR?.cancel()
        activeASR = nil
        activeASRClientId = nil
        audio.cancel()
        stopFocusMonitoring()

        let raw = transcript?.finalText.isEmpty == false ? transcript!.finalText : (transcript?.latestText ?? "")
        let fallbackText = raw.isEmpty && (config.mockASR || forceMockForCurrentSession) ? config.mockTranscript : raw
        guard !fallbackText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            panel.updateError("没有识别到文本。")
            cleanupSession(resetLastText: false)
            return
        }

        let correction = CorrectionPipeline(config: CorrectionConfig(
            mode: config.correctionMode,
            hotwords: config.hotwords,
            homophones: config.homophones,
            removeFillers: true,
            ensureTerminalPunctuation: true
        )).correct(fallbackText)
        stateMachine.send(.correctionFinished)

        let finalText = correction.corrected
        lastFinalText = finalText
        let output = pasteEngine.route(text: finalText, mode: activeOutputMode)
        panel.updateDiagnostics(outputDiagnostic(output))
        stateMachine.send(.outputRouted)
        history.append(text: finalText, outputMode: activeOutputMode, correctionRules: correction.appliedRules)
        panel.updateDone(status: output.status, text: finalText, restoredClipboard: output.restoredClipboard)
        cleanupSession(resetLastText: false)
    }

    private func cleanupSession(resetLastText: Bool) {
        activeASR?.cancel()
        activeASR = nil
        activeASRClientId = nil
        activeSessionId = nil
        transcript = nil
        didFinalize = false
        userRequestedFinish = false
        forceMockForCurrentSession = false
        focusTracker = nil
        stopFocusMonitoring()
        hotkeys.noteSessionEnded()
        if resetLastText { lastFinalText = "" }
        menu.setStatus("🎙")
    }

    private func copyLastResult() {
        guard let latest = history.latest() else { return }
        clipboard.writeString(latest.text)
        panel.show(mode: .clipboardDraft)
        panel.updateDone(status: .copied, text: latest.text, restoredClipboard: false)
    }

    private func sendPCMToActiveASR(_ data: Data) {
        guard activeSessionId != nil else { return }
        activeASR?.sendPCM(data)
    }

    private func isCurrentASR(sessionId: String, clientId: ObjectIdentifier) -> Bool {
        guard activeSessionId == sessionId, let activeASRClientId else { return false }
        return activeASRClientId == clientId
    }

    private func handleError(_ error: Error, expectedSessionId: String? = nil, clientId: ObjectIdentifier? = nil) {
        if let expectedSessionId, let clientId, !isCurrentASR(sessionId: expectedSessionId, clientId: clientId) {
            return
        }
        let salvage = transcript?.latestText.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if activeSessionId != nil, !salvage.isEmpty {
            stateMachine.send(.error)
            lastFinalText = salvage
            let output = pasteEngine.route(text: salvage, mode: .fallbackCopy)
            history.append(text: salvage, outputMode: .fallbackCopy, correctionRules: ["error_salvage"])
            panel.updateDone(status: output.status, text: salvage, restoredClipboard: output.restoredClipboard)
            cleanupSession(resetLastText: false)
        } else {
            if activeSessionId != nil {
                stateMachine.send(.error)
            }
            panel.updateError(error.localizedDescription)
            cleanupSession(resetLastText: false)
        }
        menu.setStatus("⚠️")
    }

    private func focusDiagnostic(_ snapshot: FocusSnapshot, mode: OutputMode, changed: Bool) -> String {
        let app = snapshot.frontmostAppBundleId ?? "nil"
        let role = snapshot.elementRole ?? "nil"
        let subrole = snapshot.elementSubrole ?? "nil"
        let editable = snapshot.isEditable ? "T" : "F"
        let paste = snapshot.canPaste ? "T" : "F"
        let secure = snapshot.isSecureTextField ? "T" : "F"
        return "Focus \(app) role=\(role) sub=\(subrole) edit=\(editable) paste=\(paste) secure=\(secure) conf=\(snapshot.confidence.rawValue) mode=\(mode.rawValue) changed=\(changed ? "T" : "F")"
    }

    private func outputDiagnostic(_ output: OutputResult) -> String {
        let changed = focusTracker?.didChange ?? false
        return "Output verify=\(output.verification.rawValue) status=\(output.status.rawValue) restored=\(output.restoredClipboard ? "T" : "F") | \(focusDiagnostic(initialFocus, mode: activeOutputMode, changed: changed))"
    }
}
#endif
