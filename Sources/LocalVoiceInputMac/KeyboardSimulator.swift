#if os(macOS)
import Foundation
import ApplicationServices

protocol KeyboardSimulating: AnyObject {
    func pressCommandV()
    func pressCommandV(targetPid: pid_t?)
}

final class KeyboardSimulator: KeyboardSimulating {
    func pressCommandV() {
        pressCommandV(targetPid: nil)
    }

    func pressCommandV(targetPid: pid_t?) {
        guard let source = CGEventSource(stateID: .hidSystemState) else { return }
        source.localEventsSuppressionInterval = 0

        // The trigger key is Right Option. Because the event tap consumes that
        // flagsChanged event, explicitly publish a key-up before synthesizing
        // Cmd+V so the target app does not receive Command-Option-V.
        postKey(keyCode: 61, keyDown: false, flags: [], source: source, targetPid: targetPid) // Right Option
        shortDelay()
        postKey(keyCode: 55, keyDown: true, flags: .maskCommand, source: source, targetPid: targetPid) // Command
        shortDelay()
        postKey(keyCode: 9, keyDown: true, flags: .maskCommand, source: source, targetPid: targetPid) // V
        shortDelay()
        postKey(keyCode: 9, keyDown: false, flags: .maskCommand, source: source, targetPid: targetPid)
        shortDelay()
        postKey(keyCode: 55, keyDown: false, flags: [], source: source, targetPid: targetPid)
    }

    func pressReturn() {
        pressKey(keyCode: 36, flags: [])
    }

    private func pressKey(keyCode: CGKeyCode, flags: CGEventFlags) {
        guard let source = CGEventSource(stateID: .combinedSessionState) else { return }
        let down = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: true)
        down?.flags = flags
        let up = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: false)
        up?.flags = flags
        down?.post(tap: .cghidEventTap)
        up?.post(tap: .cghidEventTap)
    }

    private func postKey(
        keyCode: CGKeyCode,
        keyDown: Bool,
        flags: CGEventFlags,
        source: CGEventSource,
        targetPid: pid_t? = nil
    ) {
        let event = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: keyDown)
        event?.flags = flags
        if let targetPid, targetPid > 0 {
            event?.postToPid(targetPid)
        } else {
            event?.post(tap: .cghidEventTap)
        }
    }

    private func shortDelay() {
        Thread.sleep(forTimeInterval: 0.025)
    }
}
#endif
