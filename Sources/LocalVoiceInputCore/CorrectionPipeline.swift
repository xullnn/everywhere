import Foundation

public enum CorrectionMode: String, Codable, Equatable, Sendable {
    case raw
    case clean
    case structured
}

public struct CorrectionConfig: Codable, Equatable, Sendable {
    public var mode: CorrectionMode
    public var hotwords: [String: String]
    public var homophones: [String: String]
    public var removeFillers: Bool
    public var ensureTerminalPunctuation: Bool

    public init(
        mode: CorrectionMode = .clean,
        hotwords: [String: String] = [:],
        homophones: [String: String] = [:],
        removeFillers: Bool = true,
        ensureTerminalPunctuation: Bool = true
    ) {
        self.mode = mode
        self.hotwords = hotwords
        self.homophones = homophones
        self.removeFillers = removeFillers
        self.ensureTerminalPunctuation = ensureTerminalPunctuation
    }

    public static let `default` = CorrectionConfig()
}

public struct CorrectionResult: Codable, Equatable, Sendable {
    public let original: String
    public let corrected: String
    public let appliedRules: [String]
}

public struct CorrectionPipeline: Sendable {
    public var config: CorrectionConfig

    public init(config: CorrectionConfig = .default) {
        self.config = config
    }

    public func correct(_ input: String) -> CorrectionResult {
        var text = input
        var rules: [String] = []

        let trimmed = normalizeWhitespace(text)
        if trimmed != text {
            rules.append("normalize_whitespace")
            text = trimmed
        }

        if config.removeFillers && config.mode != .raw {
            let cleaned = removeCommonFillers(text)
            if cleaned != text {
                rules.append("remove_fillers")
                text = cleaned
            }
        }

        let hotwordText = applyDictionary(text, dictionary: config.hotwords)
        if hotwordText != text {
            rules.append("hotwords")
            text = hotwordText
        }

        let homophoneText = applyDictionary(text, dictionary: config.homophones)
        if homophoneText != text {
            rules.append("homophones")
            text = homophoneText
        }

        let punctuationNormalized = normalizePunctuation(text)
        if punctuationNormalized != text {
            rules.append("normalize_punctuation")
            text = punctuationNormalized
        }

        if config.ensureTerminalPunctuation && config.mode != .raw {
            let punctuated = ensurePunctuation(text)
            if punctuated != text {
                rules.append("ensure_terminal_punctuation")
                text = punctuated
            }
        }

        return CorrectionResult(original: input, corrected: text, appliedRules: rules)
    }

    private func normalizeWhitespace(_ text: String) -> String {
        let parts = text
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "\t", with: " ")
            .split(whereSeparator: { $0.isWhitespace })
        return parts.joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func removeCommonFillers(_ text: String) -> String {
        var result = text
        let fillerPatterns = [
            "嗯嗯", "嗯", "呃", "啊", "额", "唔", "呃呃",
            "然后呢", "就是呢", "那个", "这个这个"
        ]
        for filler in fillerPatterns {
            result = result.replacingOccurrences(of: filler + "，", with: "")
            result = result.replacingOccurrences(of: filler + ",", with: "")
            result = result.replacingOccurrences(of: filler + " ", with: "")
        }
        // Leading filler without punctuation.
        for filler in fillerPatterns {
            while result.hasPrefix(filler) {
                result.removeFirst(filler.count)
                result = result.trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }
        return result
    }

    private func applyDictionary(_ text: String, dictionary: [String: String]) -> String {
        guard !dictionary.isEmpty else { return text }
        var result = text
        for (from, to) in dictionary.sorted(by: { $0.key.count > $1.key.count }) {
            result = result.replacingOccurrences(of: from, with: to)
        }
        return result
    }

    private func normalizePunctuation(_ text: String) -> String {
        var result = text
        let replacements: [(String, String)] = [
            (",", "，"), ("?", "？"), ("!", "！"), (";", "；"), (":", "："),
            ("。。", "。"), ("，，", "，"), ("？？", "？"), ("！！", "！"),
            (" ，", "，"), (" 。", "。"), (" ？", "？"), (" ！", "！"),
            ("， ", "，"), ("。 ", "。"), ("？ ", "？"), ("！ ", "！")
        ]
        for (from, to) in replacements {
            result = result.replacingOccurrences(of: from, with: to)
        }
        return result
    }

    private func ensurePunctuation(_ text: String) -> String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return trimmed }
        let terminals = Set("。！？.!?；;：:")
        if let last = trimmed.last, terminals.contains(last) {
            return trimmed
        }
        return trimmed + "。"
    }
}
