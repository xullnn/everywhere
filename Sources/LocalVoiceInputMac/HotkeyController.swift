#if os(macOS)
import Foundation
import ApplicationServices
import LocalVoiceInputCore

final class HotkeyController {
    var onPushToTalkStart: (() -> Void)?
    var onPushToTalkStop: (() -> Void)?
    var onToggleLongDraft: (() -> Void)?
    var onCancel: (() -> Void)?
    var onError: ((String) -> Void)?

    private var eventTap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?
    private var stateMachine = HotkeyStateMachine()
    private var appSessionActive = false
    private var appSessionType: SessionType?
    private var pendingPushToTalk: DispatchWorkItem?
    private let pushToTalkDebounce: TimeInterval = 0.14

    func start() {
        guard PermissionManager.accessibilityTrusted else {
            PermissionManager.promptAccessibilityIfNeeded()
            onError?("辅助功能权限尚未生效。请在系统设置 → 隐私与安全性 → 辅助功能中启用 LocalVoiceInput，然后退出并重新打开 App。")
            return
        }
        guard PermissionManager.inputMonitoringTrusted else {
            PermissionManager.requestInputMonitoringIfNeeded()
            onError?("输入监控权限尚未生效。请在系统设置 → 隐私与安全性 → 输入监控中启用 LocalVoiceInput，然后退出并重新打开 App。")
            return
        }

        let mask = (1 << CGEventType.flagsChanged.rawValue)
            | (1 << CGEventType.keyDown.rawValue)
        let refcon = Unmanaged.passUnretained(self).toOpaque()
        guard let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .defaultTap,
            eventsOfInterest: CGEventMask(mask),
            callback: HotkeyController.handleEvent,
            userInfo: refcon
        ) else {
            onError?("无法创建全局快捷键事件监听。请确认 LocalVoiceInput 已同时拥有辅助功能和输入监控权限；如果刚授权，请退出并重新打开 App。")
            return
        }
        eventTap = tap
        runLoopSource = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
        if let runLoopSource {
            CFRunLoopAddSource(CFRunLoopGetMain(), runLoopSource, .commonModes)
        }
        CGEvent.tapEnable(tap: tap, enable: true)
    }

    func stop() {
        let wasPushToTalk = stateMachine.mode == .pushToTalk
        resetSessionTracking()
        if wasPushToTalk { onPushToTalkStop?() }
        if let runLoopSource {
            CFRunLoopRemoveSource(CFRunLoopGetMain(), runLoopSource, .commonModes)
        }
        if let eventTap {
            CGEvent.tapEnable(tap: eventTap, enable: false)
        }
        eventTap = nil
        runLoopSource = nil
    }

    func noteSessionStarted(type: SessionType) {
        appSessionActive = true
        appSessionType = type
        if type == .longDraft {
            stateMachine = HotkeyStateMachine(mode: .longDraft, isRightOptionDown: stateMachine.isRightOptionDown)
        }
    }

    func noteSessionEnded() {
        resetSessionTracking()
    }

    private static let handleEvent: CGEventTapCallBack = { _, type, event, refcon in
        guard let refcon else { return Unmanaged.passUnretained(event) }
        let controller = Unmanaged<HotkeyController>.fromOpaque(refcon).takeUnretainedValue()
        return controller.process(type: type, event: event)
    }

    private func process(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        let keyCode = event.getIntegerValueField(.keyboardEventKeycode)

        if type == .flagsChanged, keyCode == 61 { // right Option on Apple keyboards
            let optionDown = event.flags.contains(.maskAlternate)
            let actions = stateMachine.send(optionDown ? .rightOptionDown : .rightOptionUp)
            perform(actions)
            return nil
        }

        if type == .keyDown {
            let isRepeat = event.getIntegerValueField(.keyboardEventAutorepeat) != 0
            if keyCode == 49 && event.flags.contains(.maskAlternate) { // Option + Space
                if !isRepeat {
                    if appSessionActive && appSessionType != .longDraft {
                        return nil
                    }
                    perform(stateMachine.send(.optionSpace))
                }
                return nil
            }
            if keyCode == 53 { // Esc
                if !isRepeat {
                    let actions = stateMachine.send(.escape)
                    if !actions.isEmpty {
                        perform(actions)
                        return nil
                    }
                    if appSessionActive {
                        onCancel?()
                        return nil
                    }
                }
                return Unmanaged.passUnretained(event)
            }
        }

        return Unmanaged.passUnretained(event)
    }

    private func armPushToTalkAfterDebounce() {
        pendingPushToTalk?.cancel()
        let item = DispatchWorkItem { [weak self] in
            guard let self else { return }
            self.perform(self.stateMachine.send(.pushToTalkDebounceFired))
        }
        pendingPushToTalk = item
        DispatchQueue.main.asyncAfter(deadline: .now() + pushToTalkDebounce, execute: item)
    }

    private func perform(_ actions: [HotkeyAction]) {
        for action in actions {
            switch action {
            case .armPushToTalk:
                armPushToTalkAfterDebounce()
            case .cancelPendingPushToTalk:
                pendingPushToTalk?.cancel()
                pendingPushToTalk = nil
            case .startPushToTalk:
                onPushToTalkStart?()
            case .stopPushToTalk:
                onPushToTalkStop?()
            case .toggleLongDraft:
                onToggleLongDraft?()
            case .cancelActiveSession:
                onCancel?()
            case .consumeEvent:
                break
            }
        }
    }

    private func resetSessionTracking() {
        pendingPushToTalk?.cancel()
        pendingPushToTalk = nil
        _ = stateMachine.send(.externalSessionEnded)
        appSessionActive = false
        appSessionType = nil
    }
}
#endif
