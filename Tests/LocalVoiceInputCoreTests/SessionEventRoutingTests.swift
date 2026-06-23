import XCTest
@testable import LocalVoiceInputCore

final class SessionEventRoutingTests: XCTestCase {
    func testOnlinePartialOnlyUpdatesPartial() {
        let event = ASREvent(sessionId: "s1", mode: .online, text: "实时", isFinal: false)

        XCTAssertEqual(ASREventRouter.disposition(for: event, state: .recording, userRequestedFinish: false), .updatePartial)
    }

    func testOfflineSegmentBeforeUserStopDoesNotFinalizeSession() {
        let event = ASREvent(sessionId: "s1", mode: .offline, text: "中途分段。", isFinal: true)

        XCTAssertEqual(ASREventRouter.disposition(for: event, state: .recording, userRequestedFinish: false), .updatePartial)
    }

    func testOfflineSegmentAfterUserStopFinalizesSession() {
        let event = ASREvent(sessionId: "s1", mode: .offline, text: "最终分段。", isFinal: true)

        XCTAssertEqual(ASREventRouter.disposition(for: event, state: .finalizingASR, userRequestedFinish: true), .finalize)
    }

    func testUnknownFinalOnlyFinalizesAfterUserStop() {
        let event = ASREvent(sessionId: "s1", mode: .unknown, text: "最终。", isFinal: true)

        XCTAssertEqual(ASREventRouter.disposition(for: event, state: .recording, userRequestedFinish: false), .updatePartial)
        XCTAssertEqual(ASREventRouter.disposition(for: event, state: .finalizingASR, userRequestedFinish: true), .finalize)
    }
}
