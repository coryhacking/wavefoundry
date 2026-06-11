# CoreML Available Is Acceptable

Change ID: `1p4u1-enh coreml-available-is-acceptable`
Change Status: `planned`
Owner: implementer
Status: planned
Last verified: 2026-06-11
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

## Requirements

1. Keep CoreML as the Apple Silicon provider path when ONNX Runtime exposes it.
2. Accept CPU fallback as the normal behavior for unsupported CoreML ops or partial provider
   partitioning, as long as setup and indexing complete successfully.
3. Keep CUDA/NVIDIA, named secondary ONNX providers, and CPU fallback behavior unchanged.
4. Continue to emit clear provider diagnostics so operators can see when CoreML was selected and
   when CPU handled unsupported work.
5. Update docs and tests if the CoreML gate becomes less strict than the current bounded speedup
   check.

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

- [ ] AC-1: On Apple Silicon where ONNX Runtime exposes `CoreMLExecutionProvider`, setup may select
  CoreML without requiring a full-corpus benchmark win over CPU.
- [ ] AC-2: When CoreML cannot execute an operator, the model continues via CPU fallback and setup
  still completes successfully.
- [ ] AC-3: Provider diagnostics still show CoreML or CPU clearly enough for operators to understand
  what happened.
- [ ] AC-4: Existing framework tests continue to pass.

## Tasks

- [ ] Review whether the current CoreML speedup threshold should be relaxed or removed.
- [ ] Update any setup/indexer logic that over-constrains CoreML selection.
- [ ] Adjust tests to match the new CoreML acceptance policy.
- [ ] Update operator docs if the CoreML guidance changes.

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
