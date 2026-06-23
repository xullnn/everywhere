# macOS TCC And Code Signing

macOS TCC permissions such as Accessibility, Input Monitoring, and Microphone are user-controlled and cannot be silently granted by the app, normal shell scripts, or automation. Computer automation can help navigate System Settings, but the user still controls final approval and may need to enter a password or use Touch ID.

Ad-hoc signing identifies each build by a changing `cdhash`. Rebuilding an ad-hoc signed app can make macOS treat it as a different binary for TCC purposes, causing repeated permission prompts or stale permission state.

Use a stable signing identity for regular testing:

- Keep `CFBundleIdentifier` stable: `dev.localvoiceinput.mvp`.
- Sign with the same Apple Development or local code-signing identity across rebuilds.
- Ensure the Apple WWDR G3 intermediate certificate is available when using Apple Development certificates.
- Use `scripts/show_codesign_status.sh` to inspect the active identity and designated requirement.

The desired designated requirement is certificate-based rather than pure `cdhash`-based. That lets macOS recognize rebuilds as the same app identity when the bundle id and signing identity remain stable.
