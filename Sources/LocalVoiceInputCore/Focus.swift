import Foundation

public enum FocusConfidence: String, Codable, Equatable, Sendable {
    case high
    case medium
    case low
}

public struct FocusSnapshot: Codable, Equatable, Sendable {
    public var timestamp: Date
    public var frontmostAppBundleId: String?
    public var frontmostAppPid: Int32?
    public var focusedWindowTitle: String?
    public var focusedElementIdentifier: String?
    public var elementRole: String?
    public var elementSubrole: String?
    public var isEditable: Bool
    public var isSecureTextField: Bool
    public var canPaste: Bool
    public var confidence: FocusConfidence

    public init(
        timestamp: Date = Date(),
        frontmostAppBundleId: String? = nil,
        frontmostAppPid: Int32? = nil,
        focusedWindowTitle: String? = nil,
        focusedElementIdentifier: String? = nil,
        elementRole: String? = nil,
        elementSubrole: String? = nil,
        isEditable: Bool = false,
        isSecureTextField: Bool = false,
        canPaste: Bool = false,
        confidence: FocusConfidence = .low
    ) {
        self.timestamp = timestamp
        self.frontmostAppBundleId = frontmostAppBundleId
        self.frontmostAppPid = frontmostAppPid
        self.focusedWindowTitle = focusedWindowTitle
        self.focusedElementIdentifier = focusedElementIdentifier
        self.elementRole = elementRole
        self.elementSubrole = elementSubrole
        self.isEditable = isEditable
        self.isSecureTextField = isSecureTextField
        self.canPaste = canPaste
        self.confidence = confidence
    }

    public static var unknown: FocusSnapshot {
        FocusSnapshot(confidence: .low)
    }
}

public struct FocusChangeTracker: Equatable, Sendable {
    public let initial: FocusSnapshot
    public private(set) var didChange: Bool

    public init(initial: FocusSnapshot, didChange: Bool = false) {
        self.initial = initial
        self.didChange = didChange
    }

    @discardableResult
    public mutating func observe(_ latest: FocusSnapshot) -> Bool {
        if Self.hasMeaningfulChange(from: initial, to: latest) {
            didChange = true
        }
        return didChange
    }

    public static func hasMeaningfulChange(from initial: FocusSnapshot, to latest: FocusSnapshot) -> Bool {
        if initial.frontmostAppPid != latest.frontmostAppPid { return true }
        if initial.frontmostAppBundleId != latest.frontmostAppBundleId { return true }
        if initial.focusedWindowTitle != latest.focusedWindowTitle { return true }
        if initial.focusedElementIdentifier != latest.focusedElementIdentifier { return true }
        if initial.elementRole != latest.elementRole { return true }
        if initial.elementSubrole != latest.elementSubrole { return true }
        if initial.isEditable != latest.isEditable { return true }
        if initial.isSecureTextField != latest.isSecureTextField { return true }
        if initial.canPaste != latest.canPaste { return true }
        return false
    }
}
