import XCTest
@testable import LocalVoiceInputCore

final class StateMachineTests: XCTestCase {
    func testHappyPath() {
        var sm = VoiceSessionStateMachine()
        XCTAssertEqual(sm.state, .idle)
        XCTAssertEqual(sm.send(.hotkeyDown), .preflightFocusCheck)
        XCTAssertEqual(sm.send(.focusChecked), .recording)
        XCTAssertEqual(sm.send(.hotkeyUp), .finalizingASR)
        XCTAssertEqual(sm.send(.finalASRReceived), .correcting)
        XCTAssertEqual(sm.send(.correctionFinished), .routingOutput)
        XCTAssertEqual(sm.send(.outputRouted), .done)
    }

    func testCancelFromRecording() {
        var sm = VoiceSessionStateMachine(state: .recording)
        XCTAssertEqual(sm.send(.cancel), .cancelled)
    }

    func testErrorFromAnyState() {
        var sm = VoiceSessionStateMachine(state: .correcting)
        XCTAssertEqual(sm.send(.error), .failed)
    }

    func testResetAfterErrorReturnsToIdle() {
        var sm = VoiceSessionStateMachine(state: .recording)
        XCTAssertEqual(sm.send(.error), .failed)
        XCTAssertEqual(sm.send(.reset), .idle)
    }
}
