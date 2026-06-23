import Foundation

public struct HistoryItem: Codable, Equatable, Sendable, Identifiable {
    public let id: UUID
    public var text: String
    public var createdAt: Date
    public var outputMode: OutputMode
    public var correctionRules: [String]

    public init(
        id: UUID = UUID(),
        text: String,
        createdAt: Date = Date(),
        outputMode: OutputMode,
        correctionRules: [String] = []
    ) {
        self.id = id
        self.text = text
        self.createdAt = createdAt
        self.outputMode = outputMode
        self.correctionRules = correctionRules
    }
}

public struct HistoryPolicy: Codable, Equatable, Sendable {
    public var enabled: Bool
    public var maxItems: Int

    public init(enabled: Bool = true, maxItems: Int = 20) {
        self.enabled = enabled
        self.maxItems = maxItems
    }
}

public enum HistoryReducer {
    public static func append(_ item: HistoryItem, to items: [HistoryItem], policy: HistoryPolicy) -> [HistoryItem] {
        guard policy.enabled else { return [] }
        var next = [item] + items.filter { $0.id != item.id }
        if next.count > policy.maxItems {
            next = Array(next.prefix(policy.maxItems))
        }
        return next
    }
}
