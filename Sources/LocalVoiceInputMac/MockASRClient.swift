#if os(macOS)
import Foundation
import LocalVoiceInputCore

final class MockASRClient: ASRClientProtocol {
    var onEvent: ((ASREvent) -> Void)?
    var onError: ((Error) -> Void)?

    private let transcript: String
    private var timer: DispatchSourceTimer?
    private var sessionId: String = ""
    private var partialIndex = 0
    private var partials: [String] = []

    init(transcript: String) {
        self.transcript = transcript
    }

    func start(sessionId: String, hotwords: [String: String]) {
        self.sessionId = sessionId
        partialIndex = 0
        partials = makePartials(from: transcript)
        let timer = DispatchSource.makeTimerSource(queue: DispatchQueue.global(qos: .userInitiated))
        timer.schedule(deadline: .now() + 0.25, repeating: 0.45)
        timer.setEventHandler { [weak self] in
            guard let self else { return }
            guard self.partialIndex < self.partials.count else { return }
            let text = self.partials[self.partialIndex]
            self.partialIndex += 1
            self.onEvent?(ASREvent(sessionId: sessionId, segmentId: 0, mode: .online, text: text, isFinal: false))
        }
        self.timer = timer
        timer.resume()
    }

    func sendPCM(_ data: Data) {
        // Intentionally ignored in mock mode.
    }

    func finish() {
        timer?.cancel()
        timer = nil
        DispatchQueue.global(qos: .userInitiated).asyncAfter(deadline: .now() + 0.2) { [weak self] in
            guard let self else { return }
            self.onEvent?(ASREvent(sessionId: self.sessionId, segmentId: 0, mode: .offline, text: self.transcript, isFinal: true))
        }
    }

    func cancel() {
        timer?.cancel()
        timer = nil
        onEvent = nil
        onError = nil
    }

    private func makePartials(from text: String) -> [String] {
        var result: [String] = []
        var current = ""
        for char in text {
            current.append(char)
            if current.count % 7 == 0 {
                result.append(current)
            }
        }
        if result.last != text { result.append(text) }
        return result
    }
}
#endif
