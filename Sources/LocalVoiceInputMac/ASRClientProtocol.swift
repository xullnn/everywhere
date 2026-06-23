#if os(macOS)
import Foundation
import LocalVoiceInputCore

protocol ASRClientProtocol: AnyObject {
    var onEvent: ((ASREvent) -> Void)? { get set }
    var onError: ((Error) -> Void)? { get set }

    func start(sessionId: String, hotwords: [String: String])
    func sendPCM(_ data: Data)
    func finish()
    func cancel()
}

enum ASRClientError: Error, LocalizedError {
    case invalidURL(String)
    case notConnected
    case websocketFailed(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL(let value): return "Invalid ASR URL: \(value)"
        case .notConnected: return "ASR websocket is not connected"
        case .websocketFailed(let message): return "ASR websocket failed: \(message)"
        }
    }
}
#endif
