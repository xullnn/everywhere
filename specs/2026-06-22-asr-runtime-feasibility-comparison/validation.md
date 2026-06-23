# Validation - ASR Runtime Feasibility Comparison

## Completion rule

This feature can be marked `passes=true` only when all required checks pass and the comparison includes a ranked recommendation with evidence. A skipped check is acceptable only if listed as optional or not applicable below.

## Acceptance criteria

- A1: The comparison includes MiMo-V2.5-ASR MLX, Qwen3-ASR 0.6B, and Qwen3-ASR 1.7B.
- A2: The comparison separates file-level quality metrics from realtime partial/session behavior.
- A3: The comparison includes memory footprint, startup/model load considerations, model reuse, and context/hotword feasibility.
- A4: The comparison cites local result directories or local code/docs inspected.
- A5: No macOS app runtime code is changed.

## Automated checks

```bash
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-asr-runtime-feasibility-comparison/feature.json >/dev/null
bash eval/asr_streaming/validate.sh
```

## Optional / not-applicable checks

- Full re-run of Qwen3-ASR and MiMo evals is optional when existing validated result directories are sufficient.
- Swift build/test are not required unless Swift app runtime files are touched.

## Evidence required in `specs/progress.md`

- Local files inspected.
- Result directories used.
- Any commands run and their result.
- Final recommendation and open runtime risks.
