# Packaging And Operations Module

Packaging and local operations are script-driven.

Stable responsibilities:

- `scripts/build_macos_app.sh` builds `LocalVoiceInputMac`, creates `dist/LocalVoiceInput.app`, writes `Info.plist`, and signs the app.
- The build script uses `LOCALVOICEINPUT_CODESIGN_IDENTITY` when set. If it is not set and exactly one valid code-signing identity exists, the script uses that identity automatically. Otherwise it falls back to ad-hoc signing.
- `scripts/show_codesign_status.sh` reports available code-signing identities and the app's code-signing details/designated requirement.
- `scripts/write_default_config.sh` writes the default config under `~/Library/Application Support/LocalVoiceInput/config.json`.
- `scripts/setup_funasr_venv.sh` and `scripts/run_funasr_python_server.sh` prepare and run the local FunASR server path.
- `scripts/download_funasr_smoke_models.sh` downloads repeatable local smoke-test models into `.external/models/`.
- `scripts/run_funasr_python_server.sh` prefers cached local model directories when present, defaults to CPU, and keeps punctuation and speaker verification disabled unless explicitly requested with environment variables.

Operational preference:

- Use a stable Apple Development or local code-signing identity for regular testing. Ad-hoc signatures change `cdhash` on rebuild and can force repeated macOS TCC permission prompts.

Go Deeper:

- See `../../insights/macos_tcc_codesigning.md` for the TCC/signing lesson.
