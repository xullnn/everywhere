import Foundation

public enum VoiceSessionState: String, Codable, Equatable, Sendable {
    case idle
    case preflightFocusCheck
    case recording
    case finalizingASR
    case correcting
    case routingOutput
    case done
    case cancelled
    case failed
}

public enum VoiceSessionEvent: String, Codable, Equatable, Sendable {
    case hotkeyDown
    case focusChecked
    case hotkeyUp
    case finalASRReceived
    case correctionFinished
    case outputRouted
    case cancel
    case error
    case reset
}

public struct VoiceSessionStateMachine: Equatable, Sendable {
    public private(set) var state: VoiceSessionState = .idle

    public init(state: VoiceSessionState = .idle) {
        self.state = state
    }

    @discardableResult
    public mutating func send(_ event: VoiceSessionEvent) -> VoiceSessionState {
        switch (state, event) {
        case (.idle, .hotkeyDown): state = .preflightFocusCheck
        case (.preflightFocusCheck, .focusChecked): state = .recording
        case (.recording, .hotkeyUp): state = .finalizingASR
        case (.finalizingASR, .finalASRReceived): state = .correcting
        case (.correcting, .correctionFinished): state = .routingOutput
        case (.routingOutput, .outputRouted): state = .done
        case (_, .cancel): state = .cancelled
        case (_, .error): state = .failed
        case (_, .reset): state = .idle
        default: break
        }
        return state
    }
}
