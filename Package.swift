// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "LocalVoiceInput",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .library(name: "LocalVoiceInputCore", targets: ["LocalVoiceInputCore"]),
        .executable(name: "LocalVoiceInputMac", targets: ["LocalVoiceInputMac"])
    ],
    targets: [
        .target(
            name: "LocalVoiceInputCore",
            dependencies: []
        ),
        .executableTarget(
            name: "LocalVoiceInputMac",
            dependencies: ["LocalVoiceInputCore"]
        ),
        .testTarget(
            name: "LocalVoiceInputCoreTests",
            dependencies: ["LocalVoiceInputCore"]
        )
    ]
)
