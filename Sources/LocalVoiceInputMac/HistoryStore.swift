#if os(macOS)
import Foundation
import LocalVoiceInputCore

final class HistoryStore {
    private let url: URL
    private let policy: HistoryPolicy
    private var items: [HistoryItem]

    init(url: URL = ConfigPaths.historyURL, policy: HistoryPolicy) {
        self.url = url
        self.policy = policy
        self.items = []
        load()
    }

    func append(text: String, outputMode: OutputMode, correctionRules: [String]) {
        let item = HistoryItem(text: text, outputMode: outputMode, correctionRules: correctionRules)
        items = HistoryReducer.append(item, to: items, policy: policy)
        save()
    }

    func latest() -> HistoryItem? {
        items.first
    }

    func all() -> [HistoryItem] {
        items
    }

    func clear() {
        items.removeAll()
        save()
    }

    private func load() {
        ConfigPaths.ensureDirectories()
        guard let data = try? Data(contentsOf: url),
              let decoded = try? JSONDecoder().decode([HistoryItem].self, from: data) else { return }
        items = decoded
    }

    private func save() {
        ConfigPaths.ensureDirectories()
        guard policy.enabled else { return }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        if let data = try? encoder.encode(items) {
            try? data.write(to: url, options: [.atomic])
        }
    }
}
#endif
