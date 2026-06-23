import XCTest
@testable import LocalVoiceInputCore

final class PasteRoutePlannerTests: XCTestCase {
    func testConfirmedPasteRestoresClipboardWhenPolicyAllows() {
        let decision = PasteRoutePlanner.decisionAfterCursorPaste(
            verification: .confirmed,
            policy: OutputPolicy(restoreClipboardAfterPaste: true)
        )

        XCTAssertEqual(decision.status, .pasted)
        XCTAssertTrue(decision.shouldRestoreClipboard)
        XCTAssertFalse(decision.shouldKeepResultOnClipboard)
    }

    func testConfirmedPasteKeepsResultWhenRestoreDisabled() {
        let decision = PasteRoutePlanner.decisionAfterCursorPaste(
            verification: .confirmed,
            policy: OutputPolicy(restoreClipboardAfterPaste: false)
        )

        XCTAssertEqual(decision.status, .pasted)
        XCTAssertFalse(decision.shouldRestoreClipboard)
        XCTAssertTrue(decision.shouldKeepResultOnClipboard)
    }

    func testPasteFailureFallsBackToKeepingResultOnClipboard() {
        let decision = PasteRoutePlanner.decisionAfterCursorPaste(
            verification: .unknown,
            policy: .default
        )

        XCTAssertEqual(decision.status, .copiedFallback)
        XCTAssertFalse(decision.shouldRestoreClipboard)
        XCTAssertTrue(decision.shouldKeepResultOnClipboard)
    }

    func testClipboardDraftKeepsResultOnClipboard() {
        let decision = PasteRoutePlanner.decisionForNonPasteMode(.clipboardDraft)

        XCTAssertEqual(decision.status, .copied)
        XCTAssertFalse(decision.shouldRestoreClipboard)
        XCTAssertTrue(decision.shouldKeepResultOnClipboard)
    }

    func testFallbackCopyKeepsResultOnClipboard() {
        let decision = PasteRoutePlanner.decisionForNonPasteMode(.fallbackCopy)

        XCTAssertEqual(decision.status, .copiedFallback)
        XCTAssertFalse(decision.shouldRestoreClipboard)
        XCTAssertTrue(decision.shouldKeepResultOnClipboard)
    }
}
