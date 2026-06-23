import Foundation

public enum HotkeyInputEvent: Equatable, Sendable {
    case rightOptionDown
    case rightOptionUp
    case pushToTalkDebounceFired
    case optionSpace
    case escape
    case externalSessionEnded
}

public enum HotkeyAction: Equatable, Sendable {
    case armPushToTalk
    case cancelPendingPushToTalk
    case startPushToTalk
    case stopPushToTalk
    case toggleLongDraft
    case cancelActiveSession
    case consumeEvent
}

public enum HotkeyMode: Equatable, Sendable {
    case idle
    case pendingPushToTalk
    case pushToTalk
    case longDraft
}

public struct HotkeyStateMachine: Equatable, Sendable {
    public private(set) var mode: HotkeyMode
    public private(set) var isRightOptionDown: Bool

    public init(mode: HotkeyMode = .idle, isRightOptionDown: Bool = false) {
        self.mode = mode
        self.isRightOptionDown = isRightOptionDown
    }

    @discardableResult
    public mutating func send(_ event: HotkeyInputEvent) -> [HotkeyAction] {
        switch event {
        case .rightOptionDown:
            guard !isRightOptionDown else { return [.consumeEvent] }
            isRightOptionDown = true
            guard mode == .idle else { return [.consumeEvent] }
            mode = .pendingPushToTalk
            return [.armPushToTalk, .consumeEvent]

        case .rightOptionUp:
            guard isRightOptionDown else { return [.consumeEvent] }
            isRightOptionDown = false
            switch mode {
            case .pendingPushToTalk:
                mode = .idle
                return [.cancelPendingPushToTalk, .consumeEvent]
            case .pushToTalk:
                mode = .idle
                return [.stopPushToTalk, .consumeEvent]
            case .longDraft, .idle:
                return [.consumeEvent]
            }

        case .pushToTalkDebounceFired:
            guard mode == .pendingPushToTalk, isRightOptionDown else { return [] }
            mode = .pushToTalk
            return [.startPushToTalk]

        case .optionSpace:
            switch mode {
            case .idle:
                mode = .longDraft
                return [.toggleLongDraft, .consumeEvent]
            case .pendingPushToTalk:
                mode = .longDraft
                return [.cancelPendingPushToTalk, .toggleLongDraft, .consumeEvent]
            case .longDraft:
                mode = .idle
                return [.toggleLongDraft, .consumeEvent]
            case .pushToTalk:
                return [.consumeEvent]
            }

        case .escape:
            switch mode {
            case .idle:
                return []
            case .pendingPushToTalk:
                mode = .idle
                isRightOptionDown = false
                return [.cancelPendingPushToTalk, .cancelActiveSession, .consumeEvent]
            case .pushToTalk, .longDraft:
                mode = .idle
                isRightOptionDown = false
                return [.cancelActiveSession, .consumeEvent]
            }

        case .externalSessionEnded:
            mode = .idle
            isRightOptionDown = false
            return [.cancelPendingPushToTalk]
        }
    }
}
