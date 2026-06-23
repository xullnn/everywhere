import XCTest
@testable import LocalVoiceInputCore

final class FocusChangeTrackerTests: XCTestCase {
    func testSameFocusDoesNotMarkChanged() {
        let focus = FocusSnapshot(
            frontmostAppBundleId: "com.apple.Notes",
            frontmostAppPid: 100,
            focusedWindowTitle: "Note",
            focusedElementIdentifier: "body",
            elementRole: "AXTextArea",
            isEditable: true,
            isSecureTextField: false,
            canPaste: true,
            confidence: .high
        )
        var tracker = FocusChangeTracker(initial: focus)

        XCTAssertFalse(tracker.observe(focus))
        XCTAssertFalse(tracker.didChange)
    }

    func testAppSwitchMarksChangedAndStaysSticky() {
        let initial = FocusSnapshot(frontmostAppBundleId: "com.apple.Notes", frontmostAppPid: 100, elementRole: "AXTextArea", isEditable: true, canPaste: true, confidence: .high)
        let switched = FocusSnapshot(frontmostAppBundleId: "com.apple.Safari", frontmostAppPid: 200, elementRole: "AXTextArea", isEditable: true, canPaste: true, confidence: .high)
        var tracker = FocusChangeTracker(initial: initial)

        XCTAssertTrue(tracker.observe(switched))
        XCTAssertTrue(tracker.observe(initial))
    }

    func testSecurityChangeMarksChanged() {
        let initial = FocusSnapshot(frontmostAppPid: 100, elementRole: "AXTextField", isEditable: true, isSecureTextField: false, canPaste: true, confidence: .high)
        let secure = FocusSnapshot(frontmostAppPid: 100, elementRole: "AXSecureTextField", isEditable: true, isSecureTextField: true, canPaste: false, confidence: .high)
        var tracker = FocusChangeTracker(initial: initial)

        XCTAssertTrue(tracker.observe(secure))
    }

    func testWindowOrElementIdentityChangeMarksChanged() {
        let initial = FocusSnapshot(
            frontmostAppPid: 100,
            focusedWindowTitle: "Draft A",
            focusedElementIdentifier: "editor-a",
            elementRole: "AXTextArea",
            isEditable: true,
            canPaste: true,
            confidence: .high
        )
        let next = FocusSnapshot(
            frontmostAppPid: 100,
            focusedWindowTitle: "Draft B",
            focusedElementIdentifier: "editor-b",
            elementRole: "AXTextArea",
            isEditable: true,
            canPaste: true,
            confidence: .high
        )
        var tracker = FocusChangeTracker(initial: initial)

        XCTAssertTrue(tracker.observe(next))
    }
}
