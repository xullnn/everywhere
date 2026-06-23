#if os(macOS)
import Foundation
import LocalVoiceInputCore

final class FunASRClient: NSObject, ASRClientProtocol {
    var onEvent: ((ASREvent) -> Void)?
    var onError: ((Error) -> Void)?

    private let urlString: String
    private var task: URLSessionWebSocketTask?
    private var session: URLSession?
    private var sessionId: String = ""
    private var segmentCounter: Int = 0
    private let decoder = JSONDecoder()

    init(urlString: String) {
        self.urlString = urlString
        super.init()
    }

    func start(sessionId: String, hotwords: [String: String]) {
        self.sessionId = sessionId
        self.segmentCounter = 0
        guard let url = URL(string: urlString) else {
            onError?(ASRClientError.invalidURL(urlString))
            return
        }
        let session = URLSession(configuration: .default, delegate: nil, delegateQueue: OperationQueue())
        self.session = session
        let task = session.webSocketTask(with: url)
        self.task = task
        task.resume()
        sendStartMessage(hotwords: hotwords)
        listen()
    }

    private func sendStartMessage(hotwords: [String: String]) {
        let hotwordString: String
        if hotwords.isEmpty {
            hotwordString = "{}"
        } else {
            let weighted = Dictionary(uniqueKeysWithValues: hotwords.values.map { ($0, 30) })
            if let data = try? JSONSerialization.data(withJSONObject: weighted), let json = String(data: data, encoding: .utf8) {
                hotwordString = json
            } else {
                hotwordString = "{}"
            }
        }

        let message: [String: Any] = [
            "mode": "2pass",
            "wav_name": sessionId,
            "is_speaking": true,
            "wav_format": "pcm",
            "audio_fs": 16000,
            "chunk_size": [8, 8, 4],
            "hotwords": hotwordString,
            "itn": true
        ]
        sendJSON(message)
    }

    func sendPCM(_ data: Data) {
        guard let task = task else {
            onError?(ASRClientError.notConnected)
            return
        }
        task.send(.data(data)) { [weak self] error in
            if let error { self?.onError?(error) }
        }
    }

    func finish() {
        sendJSON(["is_speaking": false])
    }

    func cancel() {
        onEvent = nil
        onError = nil
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        session?.invalidateAndCancel()
        session = nil
    }

    private func sendJSON(_ object: [String: Any]) {
        guard let task = task else { return }
        do {
            let data = try JSONSerialization.data(withJSONObject: object)
            let text = String(data: data, encoding: .utf8) ?? "{}"
            task.send(.string(text)) { [weak self] error in
                if let error { self?.onError?(error) }
            }
        } catch {
            onError?(error)
        }
    }

    private func listen() {
        task?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let message):
                self.handle(message)
                self.listen()
            case .failure(let error):
                self.onError?(error)
            }
        }
    }

    private func handle(_ message: URLSessionWebSocketTask.Message) {
        switch message {
        case .string(let text):
            parseServerText(text)
        case .data(let data):
            if let text = String(data: data, encoding: .utf8) {
                parseServerText(text)
            }
        @unknown default:
            break
        }
    }

    private func parseServerText(_ text: String) {
        guard let data = text.data(using: .utf8),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }
        let modeRaw = (object["mode"] as? String) ?? "unknown"
        let mode = ASRResultMode(rawMode: modeRaw)
        let eventText = (object["text"] as? String) ?? ""
        guard !eventText.isEmpty else { return }

        let isFinal: Bool
        if let boolValue = object["is_final"] as? Bool {
            isFinal = boolValue
        } else {
            isFinal = mode == .offline
        }

        let segmentId: Int
        if mode == .offline {
            segmentId = segmentCounter
            segmentCounter += 1
        } else {
            segmentId = segmentCounter
        }

        onEvent?(ASREvent(
            sessionId: sessionId,
            segmentId: segmentId,
            mode: mode,
            text: eventText,
            isFinal: isFinal
        ))
    }
}
#endif
