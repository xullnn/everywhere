#if os(macOS)
import Foundation
import AVFoundation

final class AudioCapture {
    private let engine = AVAudioEngine()
    private var converter: AVAudioConverter?
    private var outputFormat: AVAudioFormat?
    private var pendingPCM = Data()
    private let pendingLock = NSLock()
    private let queue = DispatchQueue(label: "localvoiceinput.audio.capture")
    private let chunkBytes = 16000 * 2 * 480 / 1000 // 480ms, 16kHz, int16 mono
    private var isRunning = false

    var onPCMChunk: ((Data) -> Void)?
    var onError: ((Error) -> Void)?

    func start() {
        queue.async { [weak self] in
            self?.startInternal()
        }
    }

    func cancel() {
        queue.async { [weak self] in
            guard let self else { return }
            self.stopEngineIfNeeded()
            self.pendingLock.lock()
            self.pendingPCM.removeAll(keepingCapacity: true)
            self.pendingLock.unlock()
        }
    }

    func stopAndFlush(completion: @escaping ([Data]) -> Void) {
        queue.async { [weak self] in
            guard let self else {
                DispatchQueue.main.async { completion([]) }
                return
            }
            self.stopEngineIfNeeded()
            let remaining = self.drainPendingChunks(includePartial: true)
            DispatchQueue.main.async { completion(remaining) }
        }
    }

    private func startInternal() {
        do {
            pendingLock.lock()
            pendingPCM.removeAll(keepingCapacity: true)
            pendingLock.unlock()

            let input = engine.inputNode
            let inputFormat = input.outputFormat(forBus: 0)
            guard let outFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16_000, channels: 1, interleaved: true) else {
                throw NSError(domain: "LocalVoiceInput.Audio", code: 1, userInfo: [NSLocalizedDescriptionKey: "Unable to create 16kHz PCM output format"])
            }
            outputFormat = outFormat
            converter = AVAudioConverter(from: inputFormat, to: outFormat)

            input.removeTap(onBus: 0)
            input.installTap(onBus: 0, bufferSize: 4096, format: inputFormat) { [weak self] buffer, _ in
                self?.handle(buffer: buffer, inputFormat: inputFormat)
            }

            engine.prepare()
            try engine.start()
            isRunning = true
        } catch {
            DispatchQueue.main.async { self.onError?(error) }
        }
    }

    private func stopEngineIfNeeded() {
        guard isRunning || engine.isRunning else { return }
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        isRunning = false
    }

    private func handle(buffer: AVAudioPCMBuffer, inputFormat: AVAudioFormat) {
        guard let converter, let outputFormat else { return }
        let ratio = outputFormat.sampleRate / inputFormat.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 16
        guard let outBuffer = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: capacity) else { return }

        var didProvideInput = false
        var error: NSError?
        let inputBlock: AVAudioConverterInputBlock = { _, outStatus in
            if didProvideInput {
                outStatus.pointee = .noDataNow
                return nil
            }
            didProvideInput = true
            outStatus.pointee = .haveData
            return buffer
        }
        converter.convert(to: outBuffer, error: &error, withInputFrom: inputBlock)
        if let error {
            DispatchQueue.main.async { self.onError?(error) }
            return
        }
        guard let bytes = pcmBytes(from: outBuffer) else { return }
        appendAndFlush(bytes)
    }

    private func pcmBytes(from buffer: AVAudioPCMBuffer) -> Data? {
        let audioBuffer = buffer.audioBufferList.pointee.mBuffers
        guard let data = audioBuffer.mData else { return nil }
        return Data(bytes: data, count: Int(audioBuffer.mDataByteSize))
    }

    private func appendAndFlush(_ data: Data) {
        pendingLock.lock()
        pendingPCM.append(data)
        var chunks: [Data] = []
        while pendingPCM.count >= chunkBytes {
            let chunk = pendingPCM.prefix(chunkBytes)
            chunks.append(Data(chunk))
            pendingPCM.removeFirst(chunkBytes)
        }
        pendingLock.unlock()

        for chunk in chunks {
            DispatchQueue.main.async { self.onPCMChunk?(chunk) }
        }
    }

    private func drainPendingChunks(includePartial: Bool) -> [Data] {
        pendingLock.lock()
        var chunks: [Data] = []
        while pendingPCM.count >= chunkBytes {
            let chunk = pendingPCM.prefix(chunkBytes)
            chunks.append(Data(chunk))
            pendingPCM.removeFirst(chunkBytes)
        }
        if includePartial && !pendingPCM.isEmpty {
            chunks.append(pendingPCM)
            pendingPCM.removeAll(keepingCapacity: true)
        }
        pendingLock.unlock()
        return chunks
    }
}
#endif
