import XCTest
@testable import LocalVoiceInputCore

final class HistoryReducerTests: XCTestCase {
    func testAppendPrependsAndTrimsToMaxItems() {
        let policy = HistoryPolicy(enabled: true, maxItems: 2)
        let one = HistoryItem(text: "一", outputMode: .clipboardDraft)
        let two = HistoryItem(text: "二", outputMode: .cursorPaste)
        let three = HistoryItem(text: "三", outputMode: .floatingDraft)
        var items: [HistoryItem] = []
        items = HistoryReducer.append(one, to: items, policy: policy)
        items = HistoryReducer.append(two, to: items, policy: policy)
        items = HistoryReducer.append(three, to: items, policy: policy)
        XCTAssertEqual(items.map(\.text), ["三", "二"])
    }

    func testDisabledHistoryReturnsEmpty() {
        let item = HistoryItem(text: "一", outputMode: .clipboardDraft)
        let items = HistoryReducer.append(item, to: [], policy: HistoryPolicy(enabled: false, maxItems: 20))
        XCTAssertTrue(items.isEmpty)
    }
}
