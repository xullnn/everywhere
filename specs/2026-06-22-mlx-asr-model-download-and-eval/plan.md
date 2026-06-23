# Plan - MLX ASR Model Download And Local Evaluation

## Implementation sequence

1. Confirm AMD SSH access, disk space, Python/Hugging Face tooling, and a durable model cache directory.
2. Add repeatable acquisition notes or scripts for AMD download plus Mac `rsync`/resume transfer.
3. Download the first priority model, `mlx-community/Qwen3-ASR-0.6B-8bit`, on AMD.
4. Sync the model to `.external/models/` on the Mac and verify file presence/size.
5. Add model registry metadata for the MLX candidates as they enter evaluation.
6. Build or reuse a Mac-local MLX runtime path for Qwen3-ASR MLX.
7. Run smoke test on one WAV case, then full 10-case evaluation for each runnable candidate.
8. Repeat the download/sync/smoke/full-eval loop for the remaining candidates.
9. Add a runtime feasibility check for partial/token streaming, session behavior, startup, model reuse, and memory footprint.
10. Produce a final comparison artifact and recommendation for the next backend-integration feature.

## Touched areas

- `eval/asr_streaming/`
- `.external/models/` for local model caches
- `.external/repos/` if an MLX runtime source checkout is required
- `specs/2026-06-22-mlx-asr-model-download-and-eval/`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation implementation notes

- Prefer deterministic shell commands and JSON outputs over chat-only notes.
- Use existing `eval/asr_streaming/validate.sh` for harness sanity checks after changing registry or runner code.
- Use `python3 -m json.tool` for JSON files.
- Use per-model result directories under `eval/asr_streaming/results/`.

## PMB promotion candidates

- Promote the final selected backend direction only after validation and closeout.
- Do not promote transient download progress or partial failed attempts.

## Risks and mitigations

- Risk: AMD download succeeds but Mac runtime cannot load the model.
  Mitigation: Treat AMD as cache-only and require Mac smoke/full-run evidence before recommending.
- Risk: A model has strong file-level accuracy but no usable realtime partial path.
  Mitigation: Keep runtime feasibility as a separate acceptance criterion.
- Risk: MLX community model metadata differs from upstream vendor metadata.
  Mitigation: Record both upstream model identity and MLX conversion identity.
- Risk: Network interruption corrupts or partially syncs a model.
  Mitigation: Use resumable download/sync commands and verify local directories before testing.
