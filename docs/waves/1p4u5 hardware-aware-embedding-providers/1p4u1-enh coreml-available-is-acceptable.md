# CoreML Available Is Acceptable

Change ID: `1p4u1-enh coreml-available-is-acceptable`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-06-13
Wave: `1p4u5 hardware-aware-embedding-providers`

## Rationale

The current hardware-aware provider work already proves that Apple Silicon can expose
`CoreMLExecutionProvider` and still fall back to `CPUExecutionProvider` when the active model or
operator path cannot use CoreML fully. That is acceptable for Wavefoundry's local setup contract:
we do not need CoreML to saturate the entire model graph, only to prefer it when it is available and
let unsupported pieces fall back cleanly to CPU.

This follow-on change narrows the policy so CoreML is treated as a valid Apple Silicon provider
without requiring a stronger full-corpus speedup gate than the practical fallback behavior itself.
The goal is to keep setup simple for operators on Apple hardware while still preserving the CPU
fallback path when CoreML does not help.

Observed on the local macOS machine: `setup_index.py` selected `CoreMLExecutionProvider`, but the
full framework docs rebuild still took about the same wall time as the previous CPU-heavy run
(`420.13s` vs `422.08s`) and CPU usage stayed high throughout the rebuild. That means CoreML is a
valid provider choice, but it does not materially accelerate this particular FastEmbed model on the
full corpus. The write-up below captures that as acceptable behavior instead of treating it as a
failure condition.

## Requirements

1. Keep CoreML as the Apple Silicon provider path when ONNX Runtime exposes it.
2. Accept CPU fallback as the normal behavior for unsupported CoreML ops or partial provider
   partitioning, as long as setup and indexing complete successfully.
3. Keep CUDA/NVIDIA, named secondary ONNX providers, and CPU fallback behavior unchanged.
4. Continue to emit clear provider diagnostics so operators can see when CoreML was selected and
   when CPU handled unsupported work.
5. Document the observed full-corpus timing so operators understand that CoreML selection does not
   imply a large acceleration on the current model.

## Scope

**In scope:**

- Relax the CoreML acceptance policy if the active model remains usable with CPU fallback.
- Preserve the existing setup-time provider diagnostics and runtime provider selection contract.
- Keep the change local-only and offline-safe.

**Out of scope:**

- Changing the model family itself.
- Introducing new non-ONNX runtimes.
- Removing CPU fallback.
- Treating CoreML as a requirement for good performance on Apple Silicon.

## Acceptance Criteria

- [x] AC-1: On Apple Silicon where ONNX Runtime exposes `CoreMLExecutionProvider`, setup may select
  CoreML without requiring a full-corpus benchmark win over CPU. The probe now accepts CoreML on
  correctness alone (no `min_speedup` gate). Verified by `test_coreml_probe_accepts_on_correctness_without_speedup_gate`.
- [x] AC-2: When CoreML cannot execute an operator, the model continues via CPU fallback and setup
  still completes successfully. The selected providers remain `(CoreML, CPU)` so ONNX partitions
  unsupported ops to CPU; the probe validates correct (finite, same-shape) embeddings before accepting.
- [x] AC-3: Provider diagnostics still show CoreML or CPU clearly enough for operators to understand
  what happened (the `Embedding provider: selected=…; reason=…` line + the probe reason string).
- [x] AC-4: Existing framework tests continue to pass — full `run_tests.py` **3139 green**.

## Tasks

- [x] Review whether the current CoreML speedup threshold should be relaxed or removed → relaxed:
  removed for CoreML (accept on correctness), KEPT for the secondary ONNX providers + CUDA bypass.
- [x] Update any setup/indexer logic that over-constrains CoreML selection (`_probe_embedding_provider`
  in `setup_index.py` — CoreML short-circuit before the `min_speedup` gate).
- [x] Adjust tests to match the new CoreML acceptance policy (`test_coreml_probe_accepts_on_correctness_without_speedup_gate`).
- [x] Update operator docs (`docs/contributing/build-and-verification.md` — CoreML accepted on correctness, not speedup; timing recorded).
- [x] Record the observed full-corpus timing (≈420.13s CoreML vs ≈422.08s prior CPU) — in the code comment + the operator doc.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Policy refinement | implementer | existing provider-selection change | Narrow CoreML to the practical Apple Silicon path. |
| Tests | qa-reviewer | Policy refinement | Validate CPU fallback remains the default safety net. |
| Docs | docs-contract-reviewer | Policy refinement | Keep operator guidance aligned with the new policy. |

## Serialization Points

- `setup_index.py` and `indexer.py` remain the shared provider-policy entry points.
- Any relaxation of the CoreML gate should keep the diagnostics contract intact.

## Notes

This change is intentionally narrower than `1p4u0`: it refines the Apple Silicon policy after the
hardware behavior was observed on the local macOS machine.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | CoreML acceptance is documented as an Apple Silicon provider path, not a guaranteed full-corpus speedup. | `setup_index.py` selected `CoreMLExecutionProvider`; full framework docs rebuild took `420.13s` after the provider handoff fix, versus `422.08s` for the prior run. CPU usage remained high, which is consistent with provider partitioning / CPU fallback. |
| 2026-06-11 | IMPLEMENTED. `_probe_embedding_provider` now accepts `CoreMLExecutionProvider` on correctness alone (finite, same-shape embeddings) and short-circuits BEFORE the `min_speedup` gate; the gate is unchanged for the secondary ONNX providers, and CUDA still bypasses the probe. Operator doc updated; observed timing recorded. +1 test. Full suite 3139 green. | `setup_index.py` `_probe_embedding_provider`; `tests/test_setup_index.py`; `docs/contributing/build-and-verification.md`. |
