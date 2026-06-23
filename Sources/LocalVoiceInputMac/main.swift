import Foundation

#if os(macOS)
import AppKit
import LocalVoiceInputCore

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var appController: AppController?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let config = AppConfig.loadFromDefaultLocation(commandLine: CommandLine.arguments)
        appController = AppController(config: config)
        appController?.start()
    }

    func applicationWillTerminate(_ notification: Notification) {
        appController?.stop()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()

#else
print("LocalVoiceInputMac is a macOS-only menu-bar app. Run this target on macOS 13 or later.")
#endif
