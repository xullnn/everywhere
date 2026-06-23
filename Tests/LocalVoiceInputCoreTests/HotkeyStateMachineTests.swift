import XCTest
@testable import LocalVoiceInputCore

final class HotkeyStateMachineTests: XCTestCase {
    func testRightOptionPushToTalkLifecycle() {
        var machine = HotkeyStateMachine()

        XCTAssertEqual(machine.send(.rightOptionDown), [.armPushToTalk, .consumeEvent])
        XCTAssertEqual(machine.mode, .pendingPushToTalk)
        XCTAssertEqual(machine.send(.pushToTalkDebounceFired), [.startPushToTalk])
        XCTAssertEqual(machine.mode, .pushToTalk)
        XCTAssertEqual(machine.send(.rightOptionUp), [.stopPushToTalk, .consumeEvent])
        XCTAssertEqual(machine.mode, .idle)
    }

    func testOptionSpaceCancelsPendingPushToTalkAndStartsLongDraft() {
        var machine = HotkeyStateMachine()

        _ = machine.send(.rightOptionDown)
        XCTAssertEqual(machine.send(.optionSpace), [.cancelPendingPushToTalk, .toggleLongDraft, .consumeEvent])
        XCTAssertEqual(machine.mode, .longDraft)
        XCTAssertEqual(machine.send(.pushToTalkDebounceFired), [])
    }

    func testLongDraftIgnoresRightOptionRelease() {
        var machine = HotkeyStateMachine(mode: .longDraft)

        XCTAssertEqual(machine.send(.rightOptionDown), [.consumeEvent])
        XCTAssertEqual(machine.mode, .longDraft)
        XCTAssertEqual(machine.send(.rightOptionUp), [.consumeEvent])
        XCTAssertEqual(machine.mode, .longDraft)
    }

    func testOptionSpaceStopsLongDraft() {
        var machine = HotkeyStateMachine(mode: .longDraft)

        XCTAssertEqual(machine.send(.optionSpace), [.toggleLongDraft, .consumeEvent])
        XCTAssertEqual(machine.mode, .idle)
    }

    func testOptionSpaceDoesNotInterruptActivePushToTalk() {
        var machine = HotkeyStateMachine(mode: .pushToTalk, isRightOptionDown: true)

        XCTAssertEqual(machine.send(.optionSpace), [.consumeEvent])
        XCTAssertEqual(machine.mode, .pushToTalk)
    }

    func testEscCancelsActiveSessionAndConsumesEvent() {
        var machine = HotkeyStateMachine(mode: .pushToTalk, isRightOptionDown: true)

        XCTAssertEqual(machine.send(.escape), [.cancelActiveSession, .consumeEvent])
        XCTAssertEqual(machine.mode, .idle)
    }
}
