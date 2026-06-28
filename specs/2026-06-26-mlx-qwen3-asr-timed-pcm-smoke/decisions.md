# Decisions - mlx-qwen3-asr Timed PCM Smoke

## Confirmed Decisions

- D1: Treat `mlx-qwen3-asr` as a candidate streaming route only after model-loaded timed PCM smoke, not from README/source claims alone.
- D2: Keep the smoke independent from macOS app behavior. App integration is out of scope.
- D3: Count incompatibility failures as useful selection evidence if they are structured and reproducible.
- D4: Use existing local long prepared cases first; public corpus acquisition remains a separate feature.
- D5: Do not mark a backend route as app-integration eligible from partial/final timing alone. It must also meet configured accuracy thresholds.
- D6: Validation on `existing_long_120_001` proves the local `mlx-qwen3-asr` session API can produce timed PCM partial/final output, but the tested 0.6B 8bit route fails selection due high CER, so it is not an app-integration target yet.

## Open Questions / Unresolved Choices

- O1: Whether the existing `mlx-community__Qwen3-ASR-0.6B-8bit` snapshot is compatible with the community loader without conversion.
- O2: If compatible, whether realtime-paced chunk feed remains fast enough for LocalVoiceInput's floating panel.
- O3: If compatible, whether stable-prefix behavior is acceptable for Chinese long dictation where earlier words may need correction.
- O4: Whether quality can be improved enough through chunk size, language/context hints, package-side fixes, or a larger compatible model to justify a later tuning feature.

## PMB Promotion Candidates

- Validated conclusion about `mlx-qwen3-asr` local timed PCM suitability, only after smoke evidence exists.
