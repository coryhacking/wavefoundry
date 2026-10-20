# Graph-only builds must not apply the embedding precision guard

Change ID: `2134z-bug graph-only-build-precision-refusal`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-19
Wave: `2136z upgrade-and-startup-field-fixes`

## Rationale

Waveforge reported that on a host where the accelerator probe fails, converting a legacy index fails in upgrade Phase 4b on a precision refusal. Verified: Phase 4a (`phase_index_update`) runs `setup_index.py`, whose `report_embedding_provider_decision` sets `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED=CPUExecutionProvider` only in its own process; Phase 4b builds a fresh environment for a `--graph-only` child, which in `indexer.build_index` still calls `_implicit_precision_changes` when the build is not explicitly full; that re-probes providers (`accel_embedder._available_gpu_providers`), predicts full precision, compares it with the int8 Phase 4a recorded, and refuses. On the native-conversion path no `--full` is passed and `migration_pending` makes the failure fatal. The graph build embeds nothing.

## Product Intent

An upgrade or graph rebuild on a host whose accelerator probe fails completes instead of refusing on a precision it does not use. Boundaries: semantic builds keep the guard unchanged. AC-1 tests the outcome.

## Requirements

1. `indexer.build_index` skips the implicit precision-change guard when the build's content is graph only, and a graph-only build is not escalated to an `all` build (the stale-identity escalation in `build_index` that widens a non-`all` build when the recorded and predicted embedding identity differ) when the only staleness is the predicted precision or embedding fingerprint. A graph-only build constructs no embedder.
2. Builds that embed (docs, code, all) keep the guard exactly as today.

## Scope

**Problem statement:** A graph-only build refuses on an embedding precision it never uses.

**In scope:**

- `indexer.py` (the guard call in `build_index`), tests, one CHANGELOG bullet.

**Out of scope:**

- Passing Phase 4a's provider choice to later phases.
- Accelerator probing.

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2; the guard is skipped by content type, not platform.

## Acceptance Criteria

- [x] AC-1: A graph-only build whose predicted precision differs from the recorded one completes without constructing an embedder or widening to `all`; a docs or code build in the same state is still refused. Oracle: tests patching the precision prediction and asserting the embedder factory is never called, with mutants that remove each exemption.
- [x] AC-2: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Skip the guard for graph-only content.
- [x] Add the tests.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| indexer | implementer | none | one guard |

## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`

## Affected Architecture Docs

N/A: a guard condition.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required | The reported defect. |
| AC-2 | required | Standard verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned. | Waveforge carried-forward note; investigation of Phase 4a/4b and `_implicit_precision_changes`. |
| 2026-10-19 | Readiness red-team blocker: bypassing the guard alone let a graph-only build with a precision mismatch escalate to `all` and silently re-embed at the new precision. Repaired before any approval: requirement 1 also exempts graph-only builds from that escalation when only predicted precision or fingerprint differs; AC-1 asserts no embedder construction. | Readiness red-team primer; receipt `review-policy-0b4525186c4d8166a8f7` superseded. |
| 2026-10-19 | Implemented. `build_index` skips the implicit precision guard for graph-only content (guard factored into `_implicit_precision_refusal`); the model-set escalation widens a graph-only build only on a model-name change; when a graph-only build is widened to embed (model-name or 1sed6 unprovenanced escalation) the guard is re-applied there, so no silent re-embed at a new precision. Updated three tests that asserted the old graph refusal; added two. Targeted (`files=`) graph builds still refuse on identity mismatch via the targeted-currency check (unchanged, out of scope). Platform-neutral. | `run_tests.py --file test_indexer.py`: 416 ok (repository-change flag from concurrent implementers' files only); `test_inference_provider.py` 11 ok. Scratch mutants: guard exemption removed, escalation exemption removed, re-guard removed, escalation+re-guard removed (embeds): each fails the new tests. |
| 2026-10-19 | Coordinator: CHANGELOG bullet added. Combined focused run of the wave's test files: 1430 OK, including test_indexer 416. | `scratchpad/2136z-focused.log`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Skip the guard for graph-only builds. | The graph child embeds nothing; fixing the cause, not the symptom. | Copy the provider choice into the graph child's environment: treats the symptom. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A graph-only path that does embed something. | The test asserts graph-only builds produce no embedding work; review confirms. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
