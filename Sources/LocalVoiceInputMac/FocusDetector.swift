#if os(macOS)
import Foundation
import AppKit
import ApplicationServices
import LocalVoiceInputCore

final class FocusDetector {
    func snapshot() -> FocusSnapshot {
        let app = NSWorkspace.shared.frontmostApplication
        let systemWide = AXUIElementCreateSystemWide()
        var focusedRef: CFTypeRef?
        let error = AXUIElementCopyAttributeValue(systemWide, kAXFocusedUIElementAttribute as CFString, &focusedRef)
        guard error == .success, let focused = focusedRef else {
            return FocusSnapshot(
                frontmostAppBundleId: app?.bundleIdentifier,
                frontmostAppPid: app?.processIdentifier,
                confidence: .low
            )
        }

        guard CFGetTypeID(focused) == AXUIElementGetTypeID() else {
            return FocusSnapshot(
                frontmostAppBundleId: app?.bundleIdentifier,
                frontmostAppPid: app?.processIdentifier,
                confidence: .low
            )
        }
        let element = focused as! AXUIElement
        let role = copyStringAttribute(element, kAXRoleAttribute as CFString)
        let subrole = copyStringAttribute(element, kAXSubroleAttribute as CFString)
        let editable = copyBoolAttribute(element, "AXEditable" as CFString)
        let enabled = copyBoolAttribute(element, kAXEnabledAttribute as CFString)
        let windowTitle = focusedWindowTitle(for: element)
        let elementIdentifier = focusedElementIdentifier(for: element)
        let roleEditable = isTextEditingRole(role)
        let secure = isSecure(role: role, subrole: subrole)

        // Do not treat every settable AXValue as text input: sliders and other controls
        // can also expose settable values. For MVP safety, auto-paste only into known
        // text roles or elements that explicitly expose AXEditable=true.
        let isEditable = (editable == true) || roleEditable
        let confidence: FocusConfidence
        if secure {
            confidence = .high
        } else if roleEditable && enabled != false {
            confidence = .high
        } else if editable == true {
            confidence = .medium
        } else {
            confidence = .low
        }

        return FocusSnapshot(
            frontmostAppBundleId: app?.bundleIdentifier,
            frontmostAppPid: app?.processIdentifier,
            focusedWindowTitle: windowTitle,
            focusedElementIdentifier: elementIdentifier,
            elementRole: role,
            elementSubrole: subrole,
            isEditable: isEditable,
            isSecureTextField: secure,
            canPaste: isEditable && !secure && enabled != false,
            confidence: confidence
        )
    }

    static func promptForAccessibilityIfNeeded() {
        let key = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
        let options = [key: true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
    }

    static var isAccessibilityTrusted: Bool {
        AXIsProcessTrusted()
    }

    private func copyStringAttribute(_ element: AXUIElement, _ attr: CFString) -> String? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attr, &value) == .success else { return nil }
        return value as? String
    }

    private func copyBoolAttribute(_ element: AXUIElement, _ attr: CFString) -> Bool? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attr, &value) == .success else { return nil }
        return value as? Bool
    }

    private func copyElementAttribute(_ element: AXUIElement, _ attr: CFString) -> AXUIElement? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attr, &value) == .success,
              let value,
              CFGetTypeID(value) == AXUIElementGetTypeID() else {
            return nil
        }
        return (value as! AXUIElement)
    }

    private func focusedWindowTitle(for element: AXUIElement) -> String? {
        guard let window = copyElementAttribute(element, kAXWindowAttribute as CFString) else { return nil }
        return copyStringAttribute(window, kAXTitleAttribute as CFString)
    }

    private func focusedElementIdentifier(for element: AXUIElement) -> String? {
        let attributes = [
            "AXIdentifier",
            "AXDOMIdentifier",
            "AXTitle",
            "AXDescription",
            "AXPlaceholderValue"
        ]
        for attribute in attributes {
            if let value = copyStringAttribute(element, attribute as CFString),
               !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return value
            }
        }
        return nil
    }

    private func isTextEditingRole(_ role: String?) -> Bool {
        guard let role else { return false }
        let editableRoles = [
            "AXTextField",
            "AXTextArea",
            "AXTextView",
            "AXComboBox",
            "AXSearchField"
        ]
        return editableRoles.contains(role)
    }

    private func isSecure(role: String?, subrole: String?) -> Bool {
        if let subrole, subrole == "AXSecureTextField" { return true }
        if let role, role == "AXSecureTextField" { return true }
        return false
    }
}
#endif
