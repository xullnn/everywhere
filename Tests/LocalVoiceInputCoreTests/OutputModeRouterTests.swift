import XCTest
@testable import LocalVoiceInputCore

final class OutputModeRouterTests: XCTestCase {
    func testHighConfidenceEditableRoutesToCursorPaste() {
        let snapshot = FocusSnapshot(isEditable: true, isSecureTextField: false, canPaste: true, confidence: .high)
        XCTAssertEqual(OutputModeRouter.decide(snapshot: snapshot, sessionType: .pushToTalk), .cursorPaste)
    }

    func testNoInputFocusRoutesToClipboardDraft() {
        let snapshot = FocusSnapshot(isEditable: false, isSecureTextField: false, canPaste: false, confidence: .low)
        XCTAssertEqual(OutputModeRouter.decide(snapshot: snapshot, sessionType: .pushToTalk), .clipboardDraft)
    }

    func testSecureTextFieldNeverAutoPastesByDefault() {
        let snapshot = FocusSnapshot(isEditable: true, isSecureTextField: true, canPaste: true, confidence: .high)
        XCTAssertEqual(OutputModeRouter.decide(snapshot: snapshot, sessionType: .pushToTalk), .clipboardDraft)
    }

    func testLongDraftRoutesToFloatingDraftEvenWhenCursorExists() {
        let snapshot = FocusSnapshot(isEditable: true, isSecureTextField: false, canPaste: true, confidence: .high)
        XCTAssertEqual(OutputModeRouter.decide(snapshot: snapshot, sessionType: .longDraft), .floatingDraft)
    }

    func testFocusChangeDowngradesToClipboard() {
        let snapshot = FocusSnapshot(isEditable: true, isSecureTextField: false, canPaste: true, confidence: .high)
        XCTAssertEqual(OutputModeRouter.decide(snapshot: snapshot, sessionType: .pushToTalk, focusChangedDuringRecording: true), .clipboardDraft)
    }

    func testAutoPasteDisabledRoutesToClipboard() {
        let snapshot = FocusSnapshot(isEditable: true, isSecureTextField: false, canPaste: true, confidence: .high)
        let policy = OutputPolicy(autoPasteEnabled: false)
        XCTAssertEqual(OutputModeRouter.decide(snapshot: snapshot, sessionType: .pushToTalk, policy: policy), .clipboardDraft)
    }

    func testLowConfidenceEditableRoutesToClipboardByDefault() {
        let snapshot = FocusSnapshot(isEditable: true, isSecureTextField: false, canPaste: true, confidence: .low)
        XCTAssertEqual(OutputModeRouter.decide(snapshot: snapshot, sessionType: .pushToTalk), .clipboardDraft)
    }

    func testNonPasteableEditableRoutesToClipboard() {
        let snapshot = FocusSnapshot(isEditable: true, isSecureTextField: false, canPaste: false, confidence: .high)
        XCTAssertEqual(OutputModeRouter.decide(snapshot: snapshot, sessionType: .pushToTalk), .clipboardDraft)
    }
}
