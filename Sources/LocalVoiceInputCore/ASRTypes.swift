import Foundation

public enum ASRResultMode: String, Codable, Equatable, Sendable {
    case online
    case offline
    case unknown

    public init(rawMode: String) {
        switch rawMode.lowercased() {
        case "online", "2pass-online", "online-2pass": self = .online
        case "offline", "2pass-offline", "offline-2pass": self = .offline
        default: self = .unknown
        }
    }
}

public struct ASREvent: Codable, Equatable, Sendable {
    public var sessionId: String
    public var segmentId: Int
    public var mode: ASRResultMode
    public var text: String
    public var isFinal: Bool
    public var receivedAt: Date

    public init(
        sessionId: String,
        segmentId: Int = 0,
        mode: ASRResultMode,
        text: String,
        isFinal: Bool = false,
        receivedAt: Date = Date()
    ) {
        self.sessionId = sessionId
        self.segmentId = segmentId
        self.mode = mode
        self.text = text
        self.isFinal = isFinal
        self.receivedAt = receivedAt
    }
}

public struct SegmentState: Codable, Equatable, Sendable {
    public enum Status: String, Codable, Equatable, Sendable {
        case partial
        case offlineFinal
        case refined
        case committed
    }

    public var sessionId: String
    public var segmentId: Int
    public var onlineText: String
    public var offlineText: String?
    public var refinedText: String?
    public var status: Status

    public init(
        sessionId: String,
        segmentId: Int,
        onlineText: String = "",
        offlineText: String? = nil,
        refinedText: String? = nil,
        status: Status = .partial
    ) {
        self.sessionId = sessionId
        self.segmentId = segmentId
        self.onlineText = onlineText
        self.offlineText = offlineText
        self.refinedText = refinedText
        self.status = status
    }

    public var bestText: String {
        refinedText ?? offlineText ?? onlineText
    }
}

public struct TranscriptBuffer: Codable, Equatable, Sendable {
    public private(set) var sessionId: String
    public private(set) var segments: [Int: SegmentState]
    public private(set) var currentSegmentId: Int

    public init(sessionId: String) {
        self.sessionId = sessionId
        self.segments = [:]
        self.currentSegmentId = 0
    }

    public mutating func apply(_ event: ASREvent) {
        guard event.sessionId == sessionId else { return }
        var segment = segments[event.segmentId] ?? SegmentState(sessionId: event.sessionId, segmentId: event.segmentId)

        switch event.mode {
        case .online:
            if segment.status == .committed || segment.status == .offlineFinal || segment.status == .refined {
                // Do not allow a late partial to downgrade or overwrite a finalized segment.
            } else {
                segment.onlineText = event.text
                segment.status = .partial
            }
        case .offline:
            segment.offlineText = event.text
            segment.status = .offlineFinal
            currentSegmentId = max(currentSegmentId, event.segmentId + 1)
        case .unknown:
            if event.isFinal {
                segment.offlineText = event.text
                segment.status = .offlineFinal
                currentSegmentId = max(currentSegmentId, event.segmentId + 1)
            } else if segment.status != .offlineFinal && segment.status != .refined && segment.status != .committed {
                segment.onlineText = event.text
                segment.status = .partial
            }
        }

        segments[event.segmentId] = segment
    }

    public mutating func refine(segmentId: Int, text: String) {
        guard var segment = segments[segmentId] else { return }
        segment.refinedText = text
        segment.status = .refined
        segments[segmentId] = segment
    }

    public mutating func markCommitted(segmentId: Int) {
        guard var segment = segments[segmentId] else { return }
        segment.status = .committed
        segments[segmentId] = segment
    }

    public var finalText: String {
        segments.keys.sorted().compactMap { segments[$0]?.bestText }.joined(separator: "")
    }

    public var latestText: String {
        if segments.isEmpty { return "" }
        return segments.keys.sorted().compactMap { segments[$0]?.bestText }.joined(separator: "")
    }
}
