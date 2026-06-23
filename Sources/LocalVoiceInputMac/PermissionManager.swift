#if os(macOS)
import Foundation
import AVFoundation
import ApplicationServices

final class PermissionManager {
    static func requestMicrophoneIfNeeded() {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .audio) { _ in }
        default:
            break
        }
    }

    static func promptAccessibilityIfNeeded() {
        let key = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
        let options = [key: true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
    }

    static func requestInputMonitoringIfNeeded() {
        guard !inputMonitoringTrusted else { return }
        _ = CGRequestListenEventAccess()
    }

    static var accessibilityTrusted: Bool {
        AXIsProcessTrusted()
    }

    static var inputMonitoringTrusted: Bool {
        CGPreflightListenEventAccess()
    }
}
#endif
