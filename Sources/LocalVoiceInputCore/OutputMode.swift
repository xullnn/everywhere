import Foundation

public enum SessionType: String, Codable, Equatable, Sendable {
    case pushToTalk
    case longDraft
}

public enum OutputMode: String, Codable, Equatable, Sendable {
    case cursorPaste
    case clipboardDraft
    case fallbackCopy
    case floatingDraft
}

public struct OutputPolicy: Codable, Equatable, Sendable {
    public var autoPasteEnabled: Bool
    public var restoreClipboardAfterPaste: Bool
    public var downgradeToClipboardWhenFocusChanges: Bool
    public var pasteSecureFields: Bool
    public var preferClipboardForLowConfidence: Bool

    public init(
        autoPasteEnabled: Bool = true,
        restoreClipboardAfterPaste: Bool = true,
        downgradeToClipboardWhenFocusChanges: Bool = true,
        pasteSecureFields: Bool = false,
        preferClipboardForLowConfidence: Bool = true
    ) {
        self.autoPasteEnabled = autoPasteEnabled
        self.restoreClipboardAfterPaste = restoreClipboardAfterPaste
        self.downgradeToClipboardWhenFocusChanges = downgradeToClipboardWhenFocusChanges
        self.pasteSecureFields = pasteSecureFields
        self.preferClipboardForLowConfidence = preferClipboardForLowConfidence
    }

    public static let `default` = OutputPolicy()
}

public enum OutputModeRouter {
    public static func decide(
        snapshot: FocusSnapshot,
        sessionType: SessionType,
        focusChangedDuringRecording: Bool = false,
        policy: OutputPolicy = .default
    ) -> OutputMode {
        if sessionType == .longDraft {
            return .floatingDraft
        }

        if focusChangedDuringRecording && policy.downgradeToClipboardWhenFocusChanges {
            return .clipboardDraft
        }

        if snapshot.isSecureTextField && !policy.pasteSecureFields {
            return .clipboardDraft
        }

        guard policy.autoPasteEnabled else {
            return .clipboardDraft
        }

        if snapshot.isEditable && snapshot.canPaste {
            switch snapshot.confidence {
            case .high, .medium:
                return .cursorPaste
            case .low:
                return policy.preferClipboardForLowConfidence ? .clipboardDraft : .cursorPaste
            }
        }

        return .clipboardDraft
    }
}
