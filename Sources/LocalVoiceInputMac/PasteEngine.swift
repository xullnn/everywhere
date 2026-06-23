#if os(macOS)
import Foundation
import ApplicationServices
import LocalVoiceInputCore

struct OutputResult {
    let status: PasteRouteStatus
    let restoredClipboard: Bool
    let verification: PasteVerificationStatus
}

final class PasteEngine {
    private let clipboard: ClipboardManaging
    private let keyboard: KeyboardSimulating
    private let verifier: PasteVerifying
    private let policy: OutputPolicy

    init(
        clipboard: ClipboardManaging,
        keyboard: KeyboardSimulating,
        verifier: PasteVerifying = AXFocusTextVerifier(),
        policy: OutputPolicy
    ) {
        self.clipboard = clipboard
        self.keyboard = keyboard
        self.verifier = verifier
        self.policy = policy
    }

    func route(text: String, mode: OutputMode) -> OutputResult {
        switch mode {
        case .cursorPaste:
            return pasteToCursor(text)
        case .clipboardDraft, .floatingDraft:
            let decision = PasteRoutePlanner.decisionForNonPasteMode(mode)
            _ = clipboard.capture()
            clipboard.writeString(text)
            return OutputResult(
                status: decision.status,
                restoredClipboard: decision.shouldRestoreClipboard,
                verification: decision.verification
            )
        case .fallbackCopy:
            let decision = PasteRoutePlanner.decisionForNonPasteMode(mode)
            _ = clipboard.capture()
            clipboard.writeString(text)
            return OutputResult(
                status: decision.status,
                restoredClipboard: decision.shouldRestoreClipboard,
                verification: decision.verification
            )
        }
    }

    private func pasteToCursor(_ text: String) -> OutputResult {
        let original = clipboard.capture()
        let before = verifier.captureFocusedTextSnapshot()
        clipboard.writeString(text)
        keyboard.pressCommandV(targetPid: before.focusSignature?.pid)

        let verification = waitForInsertion(of: text, before: before)
        let decision = PasteRoutePlanner.decisionAfterCursorPaste(verification: verification, policy: policy)
        if decision.shouldRestoreClipboard {
            clipboard.restore(original)
        } else if decision.shouldKeepResultOnClipboard {
            // Do not restore the previous clipboard unless insertion is confirmed. This prevents
            // losing the dictated text when the target rejected Cmd+V or AX verification is unavailable.
            clipboard.writeString(text)
        }
        return OutputResult(
            status: decision.status,
            restoredClipboard: decision.shouldRestoreClipboard,
            verification: decision.verification
        )
    }

    private func waitForInsertion(of text: String, before: PasteVerificationSnapshot) -> PasteVerificationStatus {
        let intervals: [TimeInterval] = [0.12, 0.18, 0.25, 0.35, 0.45]
        for interval in intervals {
            Thread.sleep(forTimeInterval: interval)
            let verification = verifier.verifyInsertion(of: text, before: before)
            if verification == .confirmed {
                return .confirmed
            }
        }
        return .unknown
    }
}

protocol PasteVerifying {
    func captureFocusedTextSnapshot() -> PasteVerificationSnapshot
    func verifyInsertion(of insertedText: String, before: PasteVerificationSnapshot) -> PasteVerificationStatus
}

struct PasteVerificationSnapshot {
    let text: String?
    let characterCount: Int?
    let selectedRange: TextRange?
    let focusSignature: FocusElementSignature?
}

struct TextRange: Equatable {
    let location: Int
    let length: Int
}

struct FocusElementSignature: Equatable {
    let pid: pid_t
    let role: String?
    let subrole: String?
    let windowTitle: String?

    func matchesSameTextTarget(as other: FocusElementSignature) -> Bool {
        // Notes and several document apps can update the window title immediately
        // after paste. Keep title as diagnostics only; insertion still requires an
        // explicit text/count/range confirmation below.
        pid == other.pid && role == other.role && subrole == other.subrole
    }
}

private struct AXFocusTextVerifier: PasteVerifying {
    func captureFocusedTextSnapshot() -> PasteVerificationSnapshot {
        guard AXIsProcessTrusted(),
              let element = focusedElement(),
              !isSecure(element) else {
            return PasteVerificationSnapshot(text: nil, characterCount: nil, selectedRange: nil, focusSignature: nil)
        }

        return PasteVerificationSnapshot(
            text: textValue(element),
            characterCount: intAttribute(element, kAXNumberOfCharactersAttribute as CFString),
            selectedRange: textRangeAttribute(element, kAXSelectedTextRangeAttribute as CFString),
            focusSignature: focusSignature(element)
        )
    }

    func verifyInsertion(of insertedText: String, before: PasteVerificationSnapshot) -> PasteVerificationStatus {
        let after = captureFocusedTextSnapshot()
        guard let beforeSignature = before.focusSignature,
              let afterSignature = after.focusSignature,
              beforeSignature.matchesSameTextTarget(as: afterSignature) else {
            return .unknown
        }

        if let beforeText = before.text,
           let afterText = after.text,
           afterText != beforeText,
           afterText.contains(insertedText) {
            return .confirmed
        }

        let insertedLength = (insertedText as NSString).length
        let replacedLength = before.selectedRange?.length ?? 0
        if let beforeCount = before.characterCount,
           let afterCount = after.characterCount,
           afterCount == beforeCount - replacedLength + insertedLength {
            return .confirmed
        }

        if let beforeRange = before.selectedRange,
           let afterRange = after.selectedRange,
           afterRange.length == 0,
           afterRange.location >= beforeRange.location + insertedLength {
            return .confirmed
        }

        return .unknown
    }

    private func focusedElement() -> AXUIElement? {
        let systemWide = AXUIElementCreateSystemWide()
        var focusedRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(systemWide, kAXFocusedUIElementAttribute as CFString, &focusedRef) == .success,
              let focusedRef,
              CFGetTypeID(focusedRef) == AXUIElementGetTypeID() else {
            return nil
        }
        return (focusedRef as! AXUIElement)
    }

    private func textValue(_ element: AXUIElement) -> String? {
        var valueRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, kAXValueAttribute as CFString, &valueRef) == .success,
              let valueRef else {
            return nil
        }
        if let string = valueRef as? String {
            return string
        }
        if let attributedString = valueRef as? NSAttributedString {
            return attributedString.string
        }
        return nil
    }

    private func textRangeAttribute(_ element: AXUIElement, _ attribute: CFString) -> TextRange? {
        var valueRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute, &valueRef) == .success,
              let valueRef,
              CFGetTypeID(valueRef) == AXValueGetTypeID() else {
            return nil
        }
        var range = CFRange()
        guard AXValueGetValue((valueRef as! AXValue), .cfRange, &range) else { return nil }
        return TextRange(location: range.location, length: range.length)
    }

    private func intAttribute(_ element: AXUIElement, _ attribute: CFString) -> Int? {
        var valueRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute, &valueRef) == .success,
              let valueRef else {
            return nil
        }
        if let number = valueRef as? NSNumber {
            return number.intValue
        }
        return valueRef as? Int
    }

    private func stringAttribute(_ element: AXUIElement, _ attribute: CFString) -> String? {
        var valueRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute, &valueRef) == .success else { return nil }
        return valueRef as? String
    }

    private func elementAttribute(_ element: AXUIElement, _ attribute: CFString) -> AXUIElement? {
        var valueRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute, &valueRef) == .success,
              let valueRef,
              CFGetTypeID(valueRef) == AXUIElementGetTypeID() else {
            return nil
        }
        return (valueRef as! AXUIElement)
    }

    private func focusSignature(_ element: AXUIElement) -> FocusElementSignature? {
        var pid: pid_t = 0
        guard AXUIElementGetPid(element, &pid) == .success else { return nil }
        let window = elementAttribute(element, kAXWindowAttribute as CFString)
        return FocusElementSignature(
            pid: pid,
            role: stringAttribute(element, kAXRoleAttribute as CFString),
            subrole: stringAttribute(element, kAXSubroleAttribute as CFString),
            windowTitle: window.flatMap { stringAttribute($0, kAXTitleAttribute as CFString) }
        )
    }

    private func isSecure(_ element: AXUIElement) -> Bool {
        var roleRef: CFTypeRef?
        var subroleRef: CFTypeRef?
        let role = AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleRef) == .success ? roleRef as? String : nil
        let subrole = AXUIElementCopyAttributeValue(element, kAXSubroleAttribute as CFString, &subroleRef) == .success ? subroleRef as? String : nil
        return role == "AXSecureTextField" || subrole == "AXSecureTextField"
    }
}
#endif
