#if os(macOS)
import Foundation
import AppKit

struct ClipboardItemSnapshot: Codable {
    let type: String
    let data: Data
}

struct ClipboardSnapshot: Codable {
    let changeCount: Int
    let items: [[ClipboardItemSnapshot]]
    let capturedAt: Date

    var isEmpty: Bool { items.isEmpty }
}

protocol ClipboardManaging: AnyObject {
    func capture() -> ClipboardSnapshot
    @discardableResult func writeString(_ text: String) -> Int
    @discardableResult func restore(_ snapshot: ClipboardSnapshot) -> Int
}

final class ClipboardManager: ClipboardManaging {
    private let pasteboard = NSPasteboard.general
    private(set) var lastSavedSnapshot: ClipboardSnapshot?

    func capture() -> ClipboardSnapshot {
        let itemGroups = pasteboard.pasteboardItems?.map { item -> [ClipboardItemSnapshot] in
            item.types.compactMap { type in
                guard let data = item.data(forType: type) else { return nil }
                return ClipboardItemSnapshot(type: type.rawValue, data: data)
            }
        }.filter { !$0.isEmpty } ?? []
        let snapshot = ClipboardSnapshot(changeCount: pasteboard.changeCount, items: itemGroups, capturedAt: Date())
        lastSavedSnapshot = snapshot
        return snapshot
    }

    @discardableResult
    func writeString(_ text: String) -> Int {
        pasteboard.clearContents()
        if !pasteboard.setString(text, forType: .string) {
            pasteboard.declareTypes([.string], owner: nil)
            pasteboard.setString(text, forType: .string)
        }
        return pasteboard.changeCount
    }

    @discardableResult
    func restore(_ snapshot: ClipboardSnapshot) -> Int {
        pasteboard.clearContents()
        guard !snapshot.items.isEmpty else { return pasteboard.changeCount }
        let restoredItems = snapshot.items.map { group -> NSPasteboardItem in
            let item = NSPasteboardItem()
            for snapshotItem in group {
                item.setData(snapshotItem.data, forType: NSPasteboard.PasteboardType(snapshotItem.type))
            }
            return item
        }
        pasteboard.writeObjects(restoredItems)
        return pasteboard.changeCount
    }

    func restoreLastSavedSnapshot() {
        guard let snapshot = lastSavedSnapshot else { return }
        restore(snapshot)
    }

    var currentChangeCount: Int { pasteboard.changeCount }
}
#endif
