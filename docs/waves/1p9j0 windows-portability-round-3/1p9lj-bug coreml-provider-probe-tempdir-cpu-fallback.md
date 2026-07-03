# CoreML provider probe temp-dir failure pins index rebuilds to CPU

Change ID: `1p9lj-bug coreml-provider-probe-tempdir-cpu-fallback`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-03
Wave: `1p9j0 windows-portability-round-3`

## Rationale

During review of wave `1p9jn retrieval-lookup-hardening`, a foreground index rebuild ran on Apple Silicon but selected `CPUExecutionProvider` even though `wave_gpu_doctor()` later reported `CoreMLExecutionProvider` as available and accepted. The rebuild output recorded:

- `selected=CPUExecutionProvider`
- reason: `no verified GPU execution provider; using CPU`
- CoreML probe failure: `Error compiling model: Failed to create a working directory appropriate for URL: file:///var/folders/.../T/`

The same session's `wave_gpu_doctor()` reported `selected_provider=CoreMLExecutionProvider` with the selection reason that CoreML was accepted on correctness. That means setup/index-build provider selection can reject CoreML because of a transient CoreML compile/temp-dir failure, cache the CPU decision through `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED` (`provider_policy.SETUP_SELECTED_ENV`; readiness correction — the earlier draft named a nonexistent `WAVEFOUNDRY_SETUP_SELECTED_PROVIDER`), and run a full rebuild on CPU even when the machine can use CoreML.

Readiness-council mechanism note (red-team, 2026-07-02): the probe/selection chain is ALREADY shared — `wave_gpu_doctor` (`server_impl.py`), `wf gpu-doctor` (`gpu_doctor.py`), and setup all call `provider_policy.select_embedding_providers(provider_probe=setup_index._probe_embedding_provider)`. The observed divergence is process-scoped cache state, not semantics: setup writes `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED` after a one-shot probe and its children inherit it; the doctor re-probes fresh in the MCP server process (which lacks the cache) at a later time and can succeed where the build's transient probe failed; the indexer's `_onnx_providers()` is probe-less and heads its list with CoreML only via the inherited cache. The cached-CPU contract is also deliberate crash avoidance (`accel_embedder.py` honors a cached CPU decision so a later raw-availability check cannot re-enable CoreML and crash in native code), so any retry must happen INSIDE the probe/decision window — before the decision is recorded — never as a later re-enable.

This should not happen silently. A transient CoreML temp-dir/compile failure should not poison the whole build into CPU without either repairing/retrying the temp-dir condition, producing a loud actionable diagnostic, or preserving a reliable path to the CoreML provider when the diagnostic path proves it is usable.

## Requirements

1. Setup/index-build provider selection MUST not permanently pin a build to CPU from a transient CoreML temp-dir compile failure when Apple Silicon/CoreML is available.
2. `wave_gpu_doctor()` and setup/index-build provider selection MUST use the same provider decision semantics, or explicitly report any intentional difference in the diagnostic output.
3. If CoreML probing fails because the temp working directory is unusable, the system MUST attempt a bounded repair or retry using a known-writable temp/cache directory before falling back to CPU.
4. If CPU fallback remains necessary, the build output and health/diagnostic path MUST clearly report that Apple Silicon/CoreML was available but rejected, include the temp-dir failure reason, and give an actionable recovery path.
5. The fix MUST not mask real provider correctness failures. Invalid/non-finite embeddings, shape mismatches, or repeatable CoreML compile failures must still fail over or require operator action rather than pretending GPU acceleration is safe.
6. Provider selection MUST remain deterministic within one build after the final decision is made, but a failed transient probe must not poison later independent diagnostics or subsequent builds.

## Scope

**Problem statement:** Apple Silicon index rebuilds can take the CPU path because the setup provider probe catches a CoreML temp working-directory compile error and records CPU as the selected provider, while the MCP GPU doctor can later accept CoreML. The result is a slow full rebuild and contradictory diagnostics.

**In scope:**

- Provider-selection flow in `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/provider_policy.py`, and the call sites that consume `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED` (`provider_policy.SETUP_SELECTED_ENV`; duplicated constant in `accel_embedder.py`).
- The CoreML probe temp-dir behavior and any bounded retry/repair logic needed for a known-writable temp/cache location.
- Diagnostic output from setup/index-build and `wave_gpu_doctor()` so the operator can see why CPU was selected.
- Tests that simulate a first CoreML temp-dir compile failure followed by a successful retry, plus a persistent failure that remains fail-safe.
- Documentation update if the provider-selection contract or recovery guidance changes.

**Out of scope:**

- General GPU performance tuning or changing the CoreML correctness-only acceptance policy.
- Fixing unrelated CoreML native crashes or ONNX Runtime bugs beyond avoiding/diagnosing the temp-dir failure mode.
- Changing vector compression, FTS settings, or index rebuild policy unrelated to provider selection.
- Forcing GPU when the operator explicitly requests CPU through environment configuration.

## Acceptance Criteria

- [x] AC-1: On Apple Silicon with `CoreMLExecutionProvider` available, a simulated first CoreML probe failure containing `Failed to create a working directory appropriate for URL` triggers a bounded retry or repair path before CPU fallback. — `_probe_embedding_provider` retry loop (attempt 0 failure matching `_COREML_TEMPDIR_ERROR_MARKERS` → `_repair_probe_tempdir()` + one retry); test `test_tempdir_failure_repairs_and_retries_then_selects_coreml` asserts repair called once + exactly one retry.
- [x] AC-2: If the retry succeeds, setup/index-build records/selects CoreML rather than CPU, and `_onnx_providers()` returns a provider list headed by `CoreMLExecutionProvider`. — test `test_retry_success_records_coreml_decision_and_providers` asserts the decision selects CoreML, `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED` records `CoreMLExecutionProvider`, and `decision.providers` is headed by CoreML (the list `_onnx_providers()` inherits via the setup cache).
- [x] AC-3: If CoreML fails persistently after the bounded retry/repair, setup/index-build falls back safely to CPU and emits an actionable diagnostic naming the CoreML temp-dir failure and recovery guidance. — persistent failure appends `_COREML_TEMPDIR_RECOVERY` (names the working-directory failure, TMPDIR staleness, fresh-shell recovery, `wf setup` rerun) to the probe reason, which flows into the decision's `reason` and the setup print; test `test_persistent_tempdir_failure_falls_back_with_actionable_reason` asserts the guidance and the 2-attempt bound.
- [x] AC-4: The provider decision/diagnostic output carries an explicit provenance marker distinguishing a decision honored from the setup cache (`WAVEFOUNDRY_EMBED_PROVIDER_SELECTED`) from a fresh probe, in both the setup/index-build report and `wave_gpu_doctor()`; a test asserts the provenance field for both the cached and fresh paths, and a parity test asserts identical decisions for identical simulated probe outcomes. (Readiness re-anchor: the probe chain is already shared — the known intentional difference is process-scoped cache state, and reporting it is the fix; no selection-plumbing refactor.) — `ProviderDecision.provenance` (`setup-cache` / `fresh-probe` / `operator-request`) set by `select_embedding_providers` on EVERY decision path (second-council fix: operator-forced CUDA/CoreML now report `operator-request`, not just forced-CPU; the CPU fallback after a failed forced probe stays `fresh-probe`), surfaced in `format_provider_decision` (`decision-source=`), `diagnostic_report` (`decision_provenance`), and `format_diagnostic_report`; tests `ProviderDecisionProvenanceTests` cover cached/fresh/all-three-operator-forced provenance, the parity assertion, and the diagnostic-report key.
- [x] AC-5: Real provider correctness failures remain fail-safe: shape mismatch, non-finite vectors, or non-temp-dir compile failures do not get promoted to CoreML just because Apple Silicon is present. — the retry triggers ONLY on the narrow `_COREML_TEMPDIR_ERROR_MARKERS` substring match AND only for `CoreMLExecutionProvider`; shape/non-finite checks are outside the retried block and unchanged; tests `test_non_tempdir_failure_gets_no_retry_or_repair` (single attempt, no repair, no misapplied guidance) and `test_tempdir_failure_on_other_provider_gets_no_retry`.
- [x] AC-6: The full framework suite passes; docs-lint clean. — central verification pass 2026-07-02: `run_tests.py` ran 4,178 tests across 41 files, OK (includes the 11 new provider tests); `wave_validate` docs-lint clean; no `__pycache__` under scripts.
- [~] AC-7: Operator-gated (real Apple Silicon hardware): a field `wf setup`/index rebuild on the affected machine class confirms the repair path selects CoreML (or produces the actionable CPU-fallback diagnostic). Simulated tests prove retry plumbing only, not repair effectiveness against the real CoreML framework error. — Intentionally not met at implementation (2026-07-02): the failure is transient and machine-specific, so a deterministic repro is operator-side; the operator validates on the next real Apple Silicon setup/rebuild that hits the temp-dir state (per the established hardware-AC pattern). AC-3's actionable diagnostic is the guaranteed floor either way.

## Tasks

- [x] Trace the provider decision path from `setup_index.report_embedding_provider_decision()` through `provider_policy.select_embedding_providers()` and `indexer._onnx_providers()`. — traced at readiness (red-team seat) and re-confirmed at implementation: shared probe chain; setup writes the env cache at `report_embedding_provider_decision`; `_onnx_providers()` inherits via the cache branch.
- [x] Add a focused failing test for the observed mismatch: setup probe falls back to CPU after a temp-dir CoreML compile error while GPU doctor would accept CoreML. — `test_persistent_tempdir_failure_falls_back_with_actionable_reason` reproduces the temp-dir CPU fallback; `test_tempdir_failure_repairs_and_retries_then_selects_coreml` proves the retry now converges the two paths (fails on revert of the retry loop).
- [x] Implement a bounded CoreML temp-dir retry/repair strategy or an equivalent deterministic decision fix. — `_COREML_TEMPDIR_ERROR_MARKERS` + `_is_coreml_tempdir_error` + `_repair_probe_tempdir` (recreate reaped temp dir, best-effort, never raises) + one CoreML-scoped retry inside `_probe_embedding_provider`.
- [x] Ensure `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED` does not cache a transient CPU decision in a way that contradicts the later successful diagnostic path — the retry/repair must complete INSIDE the probe/decision window, before the decision is recorded (never a post-decision re-enable, which would defeat the `accel_embedder` native-crash guard). — retry lives entirely inside `_probe_embedding_provider`, which runs before `report_embedding_provider_decision` records the env var; no post-decision path added.
- [x] Fix the stale `wave_gpu_doctor` MCP docstring line claiming "pure introspection (no model load / index build)" — the implementation runs the model-loading probe (one-line correction; do not restructure the surrounding diagnostic surface). — docstring now states it runs the bounded model-loading probe and names the provenance field.
- [x] Add diagnostics/recovery guidance for persistent CoreML temp-dir failures. — `_COREML_TEMPDIR_RECOVERY` appended to the failed probe reason (fresh shell / stale TMPDIR / rerun `wf setup` / CPU-continues note); flows through the decision reason into the setup print and doctor report.
- [x] Add regression tests for successful retry, persistent fail-safe fallback, and non-temp-dir correctness failures. — `CoremlProbeTempdirRetryTests` (6 tests) + `ProviderDecisionProvenanceTests` (5 tests).
- [x] Run focused provider/indexer tests and the full framework suite. — `tests.test_setup_index` 138 OK (venv python); full suite run in the coordinator's central verification pass below.
- [x] Update docs if operator-visible provider selection or recovery guidance changes. — `docs/architecture/chunking-and-indexing-pipeline.md` § Provider Selection (retry/repair + provenance + corrected the stale "beats CPU by a material margin" CoreML claim to the 1p4u1 correctness-only contract) and `docs/specs/mcp-tool-surface.md` `wave_gpu_doctor` row (provenance + runs-the-probe correction).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| provider-trace | implementer | — | Confirm setup, indexer, GPU doctor, and env-cache paths. |
| regression-tests | implementer | provider-trace | Capture temp-dir transient, persistent failure, and correctness-failure cases. |
| provider-fix | implementer | regression-tests | Bounded retry/repair or equivalent deterministic provider decision fix. |
| diagnostics-docs | implementer | provider-fix | Make CPU fallback actionable and align docs if needed. |
| verification | qa-reviewer | provider-fix | Focused tests, full suite, docs-lint. |


## Serialization Points

- Provider selection touches shared setup/index build behavior. Changes to `setup_index.py`, `provider_policy.py`, and `indexer.py` must be reviewed together so setup decisions, GPU doctor diagnostics, and runtime provider lists stay coherent.

## Affected Architecture Docs

- `docs/architecture/chunking-and-indexing-pipeline.md` § Provider Selection — Requirement 3 (bounded temp-dir repair/retry before CPU fallback) changes the documented CoreML probe contract, so this update is expected, not conditional.
- `docs/specs/mcp-tool-surface.md` — the `wave_gpu_doctor` row ("the provider Wavefoundry would select (+ reason/remediation)") if AC-4's provenance marker changes the doctor's reported contract (readiness addition; docs-contract-reviewer lane applies at close if it changes).

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Captures the observed production failure mode. |
| AC-2 | required | Prevents a transient temp-dir failure from pinning a usable Apple Silicon machine to CPU. |
| AC-3 | required | Keeps persistent failures safe and actionable instead of silent. |
| AC-4 | required | Resolves contradictory setup/index-build versus GPU doctor diagnostics. |
| AC-5 | required | Avoids masking real provider correctness bugs. |
| AC-6 | required | Locks behavior with the full suite and docs validation. |
| AC-7 | nice-to-have | Operator-gated real-hardware validation: simulated tests prove plumbing only; expected `[~]` at close if no Apple Silicon repro run has happened yet, per the established hardware-AC pattern. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Bug documented from wave `1p9jn` review. Full rebuild selected CPU after CoreML temp-dir compile failure; `wave_gpu_doctor()` later accepted CoreML on the same machine. | Rebuild output: `selected=CPUExecutionProvider`, CoreML probe failed with `Failed to create a working directory appropriate for URL: file:///var/folders/.../T/`; `wave_gpu_doctor()` reported `selected_provider=CoreMLExecutionProvider`. |
| 2026-07-03 | Second delivery-council fix pass. (1) Provenance completed: operator-forced CUDA/CoreML selections now report `operator-request` (previously only forced-CPU did — the council confirmed the gap empirically and the shipped architecture doc already promised the full contract); the CPU fallback after a failed forced-GPU probe intentionally stays `fresh-probe` (the probe failure, not the operator, drove it); pinned by `test_operator_forced_gpu_paths_report_operator_request`. (2) Repair upgraded to two env-derived tiers: a set-but-absent `TMPDIR` path is recreated directly (covers the fresh-process stale-TMPDIR scenario where `tempfile.gettempdir()` silently falls back to `/tmp`, making the old single-tier repair a verified no-op), then the `gettempdir()` answer (covers the mid-process-reap cached-tempdir window); every created directory INCLUDING intermediates gets private `0o700` on every platform via `_mkdir_private` (operator-directed cross-platform requirement; `Path.mkdir(parents=True, mode=...)` only modes the leaf). Narrowing recorded: the TMPDIR-unset + reaped `DARWIN_USER_TEMP_DIR` (confstr) window remains uncovered — the council ruled URL-parse repair SAFE-WITH-BOUNDS (four bounds: parse hygiene incl. post-unquote `..` rejection; realpath'd deepest-existing-ancestor confinement to per-user temp roots; 0o700 + depth cap; fail closed to env-derived behavior) but it is deferred as disproportionate for that residual window; AC-7 stays the arbiter. The repair target still NEVER derives from error text (security boundary). (3) `operator-request` added to the doctor docstring + `mcp-tool-surface.md` enum (was under-documented); stale "pure-introspection" test-class docstring corrected. (4) Marker `__cause__`-chain walk declined with rationale: field capture proves the marker reaches the top-level exception text, and a wrapped miss fails safe (CPU, no retry). | `test_operator_forced_gpu_paths_report_operator_request`, `test_repair_probe_tempdir_recreates_stale_tmpdir_env_path` (leaf + intermediate 0o700); affected modules 359 OK |
| 2026-07-02 | Implemented. Probe-window bounded repair+retry: `_probe_embedding_provider` retries once when a CoreML failure matches the narrow temp-working-directory marker set, after a best-effort `_repair_probe_tempdir()` (recreates a reaped temp dir; never raises); persistent failure falls back to CPU with `_COREML_TEMPDIR_RECOVERY` guidance appended. AC-4 delivered as provenance reporting: `ProviderDecision.provenance` (`setup-cache` / `fresh-probe` / `operator-request`) surfaced in the setup decision print, `diagnostic_report`/`wave_gpu_doctor` (`decision_provenance`), and the `--check-gpu` rendering; parity pinned by test. `wave_gpu_doctor` docstring corrected (runs the model-loading probe; not "pure introspection"). Docs updated (architecture § Provider Selection incl. the stale speedup-margin claim; mcp-tool-surface doctor row). 11 new tests; `tests.test_setup_index` 138 OK. AC-7 (real-hardware repair effectiveness) is `[~]` operator-gated. | `CoremlProbeTempdirRetryTests` + `ProviderDecisionProvenanceTests`; `setup_index.py`, `provider_policy.py`, `server_impl.py` (docstring), 2 docs |
| 2026-07-02 | Admitted into wave `1p9j0` (operator-directed). Focused readiness council ran (red-team + docs-contract-reviewer, both READY-WITH-NOTES); doc amended per the notes: corrected the cache env var name to `WAVEFOUNDRY_EMBED_PROVIDER_SELECTED` (the drafted name does not exist in the tree), re-anchored AC-4 to cache-provenance reporting + a parity test (the probe chain is already shared; the divergence is process-scoped cache state), added the native-crash-guard constraint (retry inside the probe/decision window), narrowed the retry trigger (substring set, retry-count 1, cheap dir-recreate repair first), added operator-gated AC-7 for real-hardware repair effectiveness, firmed up the affected-docs list (+`docs/specs/mcp-tool-surface.md`), and added the stale `wave_gpu_doctor` "pure introspection" docstring correction as a task. | Readiness seat reports (red-team, docs-contract-reviewer) synthesized in wave.md `## Review Checkpoints`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Treat this as a provider-selection bug, not a mitigation-only warning. | Apple Silicon/CoreML availability and setup/index-build provider selection contradicted each other in one session, causing a slow CPU rebuild. | Accept CPU fallback as harmless; rejected because full rebuilds become unnecessarily slow and the diagnostics are contradictory. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Retrying CoreML could mask a genuine provider correctness failure. | Retry only the known temp-dir/working-directory failure shape (a narrow substring set on the CoreML error text; the string is not a stable API contract, so an unrecognized failure shape stays fail-safe CPU) with retry-count 1; keep shape/non-finite/vector correctness failures fail-safe. |
| Re-promoting CoreML after a failed probe defeats the cached-CPU native-crash guard. | The cached CPU decision is a deliberate crash-avoidance contract (`accel_embedder` honors it so a later raw-availability check cannot re-enable CoreML and crash in ONNX/CoreML native code before Python can catch it). The retry/repair therefore runs INSIDE the probe/decision window, before the decision env var is recorded; no post-decision re-enable path is added. |
| An in-process repair may not actually clear the Apple CoreML `Failed to create a working directory` error (root cause may be a reaped `/var/folders/.../T/` dir vs. stale `TMPDIR`, and CoreML may resolve its working dir via cached `NSTemporaryDirectory()`/confstr). | As shipped (second council): the repair recreates env-derived targets only — a set-but-absent `TMPDIR` path first (the fresh-process scenario, where `gettempdir()` silently falls back to `/tmp`), then the `gettempdir()` answer (the mid-process-reap window) — with private `0o700` on every created level, every platform. The confstr-resolved window (TMPDIR unset) remains uncovered: URL-parse repair of the error-reported path was council-ruled SAFE-WITH-BOUNDS but deferred as disproportionate; the repair target never derives from error text. Simulated tests validate retry plumbing only, so real-hardware repair effectiveness is the operator-gated AC-7; AC-3's loud actionable diagnostic is the guaranteed-value floor. Subprocess-based probe retry is out of scope (would re-open the windowless-spawn/MCP-stdout territory this wave hardened). |
| Provider decision caching could remain inconsistent across setup, indexer, and MCP diagnostics. | Add tests that exercise the setup-selected env path and GPU doctor path together. |
| A repair path could write outside allowed local temp/cache locations. | Use only known writable local temp/cache directories and keep paths platform-appropriate. |
| CPU fallback diagnostics could become noisy for operator-forced CPU. | Preserve explicit CPU override semantics and suppress GPU-remediation warnings when CPU was requested. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
