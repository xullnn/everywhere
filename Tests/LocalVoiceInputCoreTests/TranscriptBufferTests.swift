import XCTest
@testable import LocalVoiceInputCore

final class TranscriptBufferTests: XCTestCase {
    func testOnlineThenOfflineReplacesPartial() {
        var buffer = TranscriptBuffer(sessionId: "s1")
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .online, text: "我想要做一个", isFinal: false))
        XCTAssertEqual(buffer.latestText, "我想要做一个")
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .offline, text: "我想要做一个本地语音输入工具。", isFinal: true))
        XCTAssertEqual(buffer.finalText, "我想要做一个本地语音输入工具。")
        XCTAssertEqual(buffer.segments[0]?.status, .offlineFinal)
    }

    func testLatePartialDoesNotDowngradeFinalSegment() {
        var buffer = TranscriptBuffer(sessionId: "s1")
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .offline, text: "最终文本。", isFinal: true))
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .online, text: "临时文本", isFinal: false))
        XCTAssertEqual(buffer.segments[0]?.bestText, "最终文本。")
        XCTAssertEqual(buffer.segments[0]?.status, .offlineFinal)
    }

    func testMultipleSegmentsJoinInOrder() {
        var buffer = TranscriptBuffer(sessionId: "s1")
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 1, mode: .offline, text: "第二句。", isFinal: true))
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .offline, text: "第一句。", isFinal: true))
        XCTAssertEqual(buffer.finalText, "第一句。第二句。")
    }

    func testOfflineSegmentAndCurrentPartialMergeForDraftDisplay() {
        var buffer = TranscriptBuffer(sessionId: "s1")
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .offline, text: "第一句。", isFinal: true))
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 1, mode: .online, text: "第二句正在说", isFinal: false))

        XCTAssertEqual(buffer.latestText, "第一句。第二句正在说")
        XCTAssertEqual(buffer.finalText, "第一句。第二句正在说")
    }

    func testRefinedTextWinsOverOfflineText() {
        var buffer = TranscriptBuffer(sessionId: "s1")
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .offline, text: "原始最终文本", isFinal: true))
        buffer.refine(segmentId: 0, text: "修正后的最终文本。")
        XCTAssertEqual(buffer.finalText, "修正后的最终文本。")
        XCTAssertEqual(buffer.segments[0]?.status, .refined)
    }
    func testIgnoresEventsFromDifferentSession() {
        var buffer = TranscriptBuffer(sessionId: "current")
        buffer.apply(ASREvent(sessionId: "old", segmentId: 0, mode: .offline, text: "旧会话文本", isFinal: true))
        XCTAssertTrue(buffer.latestText.isEmpty)
        XCTAssertTrue(buffer.segments.isEmpty)
    }

    func testUnknownLatePartialDoesNotOverwriteOfflineFinal() {
        var buffer = TranscriptBuffer(sessionId: "s1")
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .offline, text: "最终文本。", isFinal: true))
        buffer.apply(ASREvent(sessionId: "s1", segmentId: 0, mode: .unknown, text: "未知临时文本", isFinal: false))
        XCTAssertEqual(buffer.finalText, "最终文本。")
        XCTAssertEqual(buffer.segments[0]?.status, .offlineFinal)
    }

}
