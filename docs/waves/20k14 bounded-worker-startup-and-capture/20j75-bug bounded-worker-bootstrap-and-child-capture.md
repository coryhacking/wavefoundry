# Bounded worker bootstrap and child capture

Change ID: `20j75-bug bounded-worker-bootstrap-and-child-capture`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-13
Wave: 20k14 bounded-worker-startup-and-capture

## Rationale

Repair worker startup and child-result handling at their existing boundaries so qualification remains portable, protected record writes remain refused, and verbose upgrade children cannot retain unlimited captured text. Preserve ordinary subprocess results and the pruning recovery contract. This is an accidental-write guard and resource bound, not a hostile-code sandbox or approval identity mechanism.

Discovery: `worker_environment` retains empty inherited search-path components; the bootstrap uses a bytecode-capable file loader; publication invokes the guard before its normal unavailable-error boundary; and `child_tee.run(capture_output=True)` accumulates every scrubbed fragment. The sole production capture consumer is `upgrade_wavefoundry.phase_pruning`, which extracts its count from stderr. The restricted-import checker test rejects empty-name relative imports. The original test passed locally on Python 3.11.17; no claim is made that its failure reproduces on that patch release.

## Requirements

1. Build the worker Python search path from nonempty components only. Treat absent and empty inherited `PYTHONPATH` identically; preserve ordered nonempty entries and nested-bootstrap deduplication.
2. Load the bootstrap's guard from its Python source without consulting or emitting adjacent bytecode. Keep the existing module name, metadata, installation order, nested-root protection and legitimate chained customization. A source-load or install failure must stop guarded startup. This does not authenticate source, the shim itself, standard-library imports or user customization.
3. Normalize expected guard refusals and invalid-marker failures at `project_state_publication_lock` to `ProjectPublicationUnavailable` before lock acquisition or mutation. Preserve protection even in descendants that skipped site initialization. Unmarked processes and unrelated roots keep current behavior; malformed markers remain fail-closed.
4. Bound retained captured output to 1 MiB of UTF-8 text per stream, including any elision marker, with a head and final tail. Both pipes continue draining, console forwarding and capped log handling after the capture limit. Preserve exact below-limit scrubbed text, return codes and existing timeout/check behavior. Expose which streams were truncated using additive result metadata; stream assembly/redaction occurs before retention limits.
5. Preserve pruning's ordinary count parsing. When captured stderr is truncated, report pruning as unproven and retain the original manifest snapshot instead of interpreting partial evidence as a proven zero count. Stdout truncation alone must not discard an intact stderr summary. No checkpoint bypass or extra upgrade phase is introduced.
6. The isolated stdlib-only test fence must accept legitimate relative imports, including empty names with a positive relative level, while refusing non-stdlib absolute imports. Do not rely on preloading a module to hide the portability defect.

## Scope

**In scope:** worker environment and source-loader boundary; publication error translation; bounded child capture and its pruning consumer; focused portable regression tests; documentation of changed limits and preserved trust boundaries.

**Out of scope:** authenticating workers or approvers; changing general Python import semantics or all subprocess capture sites; production cache redesign; replacing the audit guard with process isolation; timing threshold changes; new review gates; diagnostic archives; release packaging and closure.

Implementation files are declared below. One implementer owns source writes; reviewers are read-only. Serialize shared `review_evidence.py` and architecture/changelog edits with adjacent waves. Protected seeds, host settings and rendered entry surfaces are not write targets. Add no new bootstrap dependency or configuration knob unless a reviewed requirement needs it.

## Acceptance Criteria

- [x] AC-1: Isolated environment/child controls show absent, empty and mixed-empty search paths introduce no implicit working-directory entry, while nonempty ordering, nested protection and legitimate customization remain intact.
- [x] AC-2: Guarded child controls show the guard executes current source independent of adjacent cached bytecode, including bytecode-disabled execution; source-load and installation failures stop startup, and unmarked startup remains unchanged.
- [x] AC-3: Protected-root and malformed-marker publication attempts expose `ProjectPublicationUnavailable` before writes or lock acquisition; unmarked and unrelated-root controls still publish under the existing lock contract.
- [x] AC-4: Real-child and deterministic boundary controls demonstrate the per-stream encoded-byte cap, exact below-limit output, valid multibyte text, visible truncation, retained final tails and uninterrupted draining of both streams; existing redaction, timeout and nonzero-exit controls remain correct.
- [x] AC-5: Pruning controls preserve an intact count when stdout alone is truncated and return unproven with the manifest snapshot retained when stderr is truncated; ordinary successful pruning and retry behavior remain correct.
- [x] AC-6: Isolated import-fence controls exercise relative empty-name imports and reject a non-stdlib absolute import; the checker still executes without third-party dependencies on available supported Python versions, with unexecuted versions disclosed.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change edits validate; no failure elsewhere is attributable to this change. Durable documentation accurately states capture limits, bootstrap source scope and cooperative-guard limitations.

## Tasks

- [x] Implement environment normalization and source-only guard initialization with focused child controls.
- [x] Translate expected publication guard errors without weakening refusal or changing lock order.
- [x] Bound capture and preserve pruning recovery semantics with boundary and integration controls.
- [x] Repair the restricted-import test fence and add a negative import control.
- [x] Update architecture prose and changelog; remove obsolete capture-cap exclusions.
- [x] Run focused tests and independent code, QA, architecture, security, performance and docs-contract review; record concise results in wave.md and typed evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Boundary implementation | implementer | readiness | Single writer; inherited capable model allocation for cross-process semantics |
| Independent verification | reviewer lanes | implementation | Negative controls, trust limits, parser compatibility and byte accounting |
| Delivery synthesis | council-chair | required reviews | Compact wave record; retain no evidence folder |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/test_worker_guard.py`
- `.wavefoundry/framework/scripts/test_worker_bootstrap/sitecustomize.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/child_tee.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_bytecode_cache.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_repo_guard.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_child_tee.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
Root CHANGELOG.md carries the concise user-visible entry.
- `docs/architecture/testing-architecture.md`
- `docs/architecture/threat-model.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md`: worker import semantics and capture qualification; remove the obsolete parser-capture exclusion from the cap claim.
- `docs/architecture/threat-model.md`: source-only guard loader's narrow guarantee, continuing source trust and inherited-marker refusal.
- `docs/architecture/data-and-control-flow.md`: captured-output limits and unproven pruning when stderr evidence is incomplete.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevent implicit search-path expansion |
| AC-2 | required | Execute source and preserve startup refusal |
| AC-3 | required | Maintain the established refusal contract |
| AC-4 | required | Bound memory without blocking producers |
| AC-5 | required | Do not turn incomplete output into recovery authority |
| AC-6 | required | Correct test portability without weakening its purpose |
| AC-7 | required | Verify owned behavior and document exact limits |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | Publication translation and documentation complete. All 196 review-evidence tests pass; three focused marker controls prove refusal precedes locking/writing and path-free returned detail. Removing translation is detected for both marker cases. Full docs validation passes. Implementation paused pending final combined qualification and independent delivery review; native Windows unexecuted. | test_review_evidence.WorkerPublicationRefusalTests; test_review_evidence; wf_validate_docs |
| 2026-10-13 | Worker startup, capture, pruning and import fence implemented. 64 focused tests pass on Python 3.14.8; 13 boundary tests pass on Python 3.11.17. Restored empty-path, uncapped capture and missing truncation guard controls fail; planted unchecked cache executes only through the ordinary-loader control. Publication translation/shared prose pending adjacent review freeze. | test_bytecode_cache.WorkerBootstrapSourceTests and RunnerTopLevelAndChildTests; test_child_tee; test_upgrade_wavefoundry.PhasePruningCountTests and UpgradeManifestRecoveryTests; restricted-import test; protected workers |
| 2026-10-13 | Readiness approved; readied and opened canonically. Readback: normalize empty worker search entries, load guard source under fatal startup handling, cap per-stream capture, keep truncated pruning evidence unproven and correct relative import fencing. Coordinator serializes publication translation and shared documentation after adjacent readiness review. | Current typed readiness; AC-1..AC-7; live MCP source reads |
| 2026-10-13 | Planned from current source; no implementation or readiness claimed | Named function and consumer inspection above |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-13 | Repair existing boundaries with local compatibility controls | Smallest change covering mechanisms without a new runtime subsystem | Documentation-only leaves behavior unchanged; general isolation and a new streaming protocol expand scope and startup cost |
| 2026-10-13 | Preserve marker enforcement and translate errors at publication | Site-disabled descendants still need protection | Ignoring markers outside an installed hook silently weakens protection |
| 2026-10-13 | Per-stream bounded head/tail capture; conservative pruning on truncated stderr | Keeps ordinary parser bytes and useful diagnostics with an explicit maximum | Dropping capture breaks counts; parsing partial evidence can falsely prove completion; a new summary protocol adds migration work |
| 2026-10-13 | Correct relative-import handling in the test fence | Exercises actual stdlib behavior across interpreter patch releases | Pre-importing re masks the narrow failure without correcting the rule |

## Risks

| Risk | Mitigation |
| --- | --- |
| Capture cuts multibyte text or redaction tokens | Scrub assembled fragments first; count UTF-8 bytes and test boundaries |
| Truncation changes pruning's completion claim | Explicit stream metadata; retain recovery snapshot on truncated stderr |
| Loader failure is swallowed by Python site startup | Put source loading and installation under the same fatal boundary |
| Error translation ignores invalid protection | Negative controls verify no lock acquisition or protected mutation |
| Platform/runtime behavior is overclaimed | Use available supported runtimes; disclose unexecuted native platforms |

## Session Handoff

See `docs/agents/session-handoff.md` for coordinator-owned state. This is a plan; implementation awaits readiness.
