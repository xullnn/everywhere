#if os(macOS)
import Foundation
import LocalVoiceInputCore

struct AppConfig: Codable {
    var asrURL: String
    var mockASR: Bool
    var mockTranscript: String
    var hotwords: [String: String]
    var homophones: [String: String]
    var outputPolicy: OutputPolicy
    var correctionMode: CorrectionMode
    var historyMaxItems: Int

    static let `default` = AppConfig(
        asrURL: "ws://127.0.0.1:10095",
        mockASR: false,
        mockTranscript: "这是一次本地语音输入测试，松开快捷键以后会自动粘贴或者复制到剪切板。",
        hotwords: [
            "qwen三": "Qwen3",
            "fun asr": "FunASR",
            "麦克不 pro": "MacBook Pro",
            "麦克布克 pro": "MacBook Pro"
        ],
        homophones: [:],
        outputPolicy: .default,
        correctionMode: .clean,
        historyMaxItems: 20
    )

    static func loadFromDefaultLocation(commandLine: [String]) -> AppConfig {
        var config = AppConfig.default
        let url = ConfigPaths.configURL
        if let data = try? Data(contentsOf: url), let decoded = try? JSONDecoder().decode(AppConfig.self, from: data) {
            config = decoded
        }
        if commandLine.contains("--mock-asr") {
            config.mockASR = true
        }
        if let idx = commandLine.firstIndex(of: "--asr-url"), commandLine.indices.contains(commandLine.index(after: idx)) {
            config.asrURL = commandLine[commandLine.index(after: idx)]
        }
        if let idx = commandLine.firstIndex(of: "--mock-transcript"), commandLine.indices.contains(commandLine.index(after: idx)) {
            config.mockTranscript = commandLine[commandLine.index(after: idx)]
        }
        return config
    }
}

enum ConfigPaths {
    static var appSupportDirectory: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support")
        return base.appendingPathComponent("LocalVoiceInput", isDirectory: true)
    }

    static var configURL: URL {
        appSupportDirectory.appendingPathComponent("config.json")
    }

    static var historyURL: URL {
        appSupportDirectory.appendingPathComponent("history.json")
    }

    static func ensureDirectories() {
        try? FileManager.default.createDirectory(at: appSupportDirectory, withIntermediateDirectories: true)
    }
}
#endif
