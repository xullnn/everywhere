import Foundation

public enum ASREventDisposition: Equatable, Sendable {
    case updatePartial
    case finalize
}

public enum ASREventRouter {
    public static func disposition(
        for event: ASREvent,
        state: VoiceSessionState,
        userRequestedFinish: Bool
    ) -> ASREventDisposition {
        switch event.mode {
        case .online:
            return .updatePartial
        case .offline:
            return (state == .finalizingASR || userRequestedFinish) ? .finalize : .updatePartial
        case .unknown:
            return (event.isFinal && (state == .finalizingASR || userRequestedFinish)) ? .finalize : .updatePartial
        }
    }
}

public enum PasteRouteStatus: String, Codable, Equatable, Sendable {
    case pasted
    case copied
    case copiedFallback
    case cancelled
}

public enum PasteVerificationStatus: String, Codable, Equatable, Sendable {
    case confirmed
    case unknown
    case notAttempted
}

public struct PasteRouteDecision: Codable, Equatable, Sendable {
    public let status: PasteRouteStatus
    public let shouldRestoreClipboard: Bool
    public let shouldKeepResultOnClipboard: Bool
    public let verification: PasteVerificationStatus

    public init(
        status: PasteRouteStatus,
        shouldRestoreClipboard: Bool,
        shouldKeepResultOnClipboard: Bool,
        verification: PasteVerificationStatus
    ) {
        self.status = status
        self.shouldRestoreClipboard = shouldRestoreClipboard
        self.shouldKeepResultOnClipboard = shouldKeepResultOnClipboard
        self.verification = verification
    }
}

public enum PasteRoutePlanner {
    public static func decisionForNonPasteMode(_ mode: OutputMode) -> PasteRouteDecision {
        switch mode {
        case .clipboardDraft, .floatingDraft:
            return PasteRouteDecision(
                status: .copied,
                shouldRestoreClipboard: false,
                shouldKeepResultOnClipboard: true,
                verification: .notAttempted
            )
        case .fallbackCopy:
            return PasteRouteDecision(
                status: .copiedFallback,
                shouldRestoreClipboard: false,
                shouldKeepResultOnClipboard: true,
                verification: .notAttempted
            )
        case .cursorPaste:
            return PasteRouteDecision(
                status: .copiedFallback,
                shouldRestoreClipboard: false,
                shouldKeepResultOnClipboard: true,
                verification: .unknown
            )
        }
    }

    public static func decisionAfterCursorPaste(
        verification: PasteVerificationStatus,
        policy: OutputPolicy
    ) -> PasteRouteDecision {
        switch verification {
        case .confirmed:
            return PasteRouteDecision(
                status: .pasted,
                shouldRestoreClipboard: policy.restoreClipboardAfterPaste,
                shouldKeepResultOnClipboard: !policy.restoreClipboardAfterPaste,
                verification: .confirmed
            )
        case .unknown, .notAttempted:
            return PasteRouteDecision(
                status: .copiedFallback,
                shouldRestoreClipboard: false,
                shouldKeepResultOnClipboard: true,
                verification: .unknown
            )
        }
    }
}
