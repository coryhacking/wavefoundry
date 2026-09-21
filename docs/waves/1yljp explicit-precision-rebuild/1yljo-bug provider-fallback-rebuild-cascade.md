# Refuse implicit precision-changing index rebuilds

Change ID: `1yljo-bug provider-fallback-rebuild-cascade`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-21
Wave: 1yljp explicit-precision-rebuild

## Rationale

An ordinary update must not turn a transient provider failure into an expensive corpus re-embedding job without an explicit rebuild request. During preparation of 1ymzk, the sandbox blocked CoreML's temporary working directory. Setup selected CPU, the indexer predicted INT8 instead of the persisted full precision, and a five-file documentation update expanded into a 2,394-file all-layer rebuild. The existing index was valid. A host GPU diagnostic passed; stopping the CPU run and performing a host update reused the stored embeddings and returned the index to complete. Model bundle 3 was a false lead: its embedding compatibility fingerprint is intentionally identical to bundle 2.

This cost can be substantial on CPU-only Windows hosts and when an index moves between machines. The bounded fix is an early refusal, not vector relabeling and not bypassing a failed provider probe. Actual full/INT8 vectors are not interchangeable. Explicit full rebuild remains the intentional conversion path.

## Requirements

1. On non-full updates, detect any recognized persisted semantic precision class that differs from the currently selected build precision for that layer, wherever the update would otherwise select or escalate to semantic work. Refuse before resolving embedding models, encoding content, beginning a build epoch, or changing canonical vectors/bookkeeping for a schema-current index. Existing schema/recovery settlement is not bypassed; the refusal is not a promise that opening a database creates no coordination files. Cover docs, code and all-layer calls, including an untouched semantic sibling which would otherwise cause scoped convergence. Graph-only work must not accidentally bypass this guard by escalating to semantic work.
2. Return an observable structured build failure using the existing failure contract, naming affected layer(s), recorded and requested precision, and actionable recovery: restore the compatible provider environment or deliberately request the existing full-rebuild operation. Existing CLI/MCP callers must report failure rather than successful/no-op completion. In particular, setup_index.main currently claims every CalledProcessError left an incomplete epoch; replace that unsupported blanket state claim with neutral failure wording or verified state, and pin the new refusal path. Do not add a new flag, config key, model rank, or interactive prompt inside tools.
3. Preserve the index's prior published state and recorded identity on refusal; do not stamp CPU INT8 identity over full vectors or re-enable a provider rejected by setup. Do not promise that every query environment can load its recorded model; preserve current reader behavior.
4. Explicit full rebuild may transition precision and must really re-embed before publishing the new identity. An existing same-precision update remains incremental; a fresh CPU-only install remains allowed. Genuine model/fingerprint revisions within the same precision retain existing compatibility behavior. Missing/unknown legacy provenance follows existing recovery behavior rather than being treated as proven compatible. Dry-run exposes the same refusal without mutating canonical state.
5. Prove the public build decision with a real small producer-built index and deterministic embedding spies: a provider-driven precision change is refused without embedding or epoch mutation, restoring the compatible provider permits an incremental update, and an explicit rebuild permits conversion. Exercise both precision directions and scoped sibling escalation. Include a guard-removal mutant; tests must require neither GPU hardware nor network/model downloads.

## Scope

**Problem statement:** transient execution-provider selection can silently convert an ordinary update into an incompatible precision migration and full re-embedding.

**In scope:** indexer preflight, existing failure propagation where needed, focused producer-built tests and user-facing update guidance.

**Out of scope:** changing embedding weights, precision equivalence, provider probe policy, CPU performance tuning, preserving a precision via a new factory policy, suppressing genuine model migrations, changing query fallbacks, and handler-module extraction. Wave 1ymzk is paused and will resume after this repair.

## Acceptance Criteria

- [x] AC-1: Implicit precision changes on existing semantic layers return an actionable failure before embedding or canonical epoch/state changes, including scoped escalation; a producer-built fixture proves refusal and preserved identity/content/state.
- [x] AC-2: Explicit full conversion, fresh CPU-only creation, same-precision incremental updates and genuine same-precision model revisions retain their intended behavior, with contrasting executable cases.
- [x] AC-3: CLI/MCP build consumers expose the refusal truthfully; dry-run preserves state; the guard-removal mutant is detected by the build-path regression.
- [x] AC-4: The change's own suites pass, edited documentation validates, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Verify build-entry, scoped-escalation and failure-consumer paths; add a reproducer against real small index fixtures.
- [x] Implement the bounded preflight and clear existing-contract failure; preserve explicit full intent before internal escalation.
- [x] Exercise the precision/provenance matrix, failure consumers and guard-removal mutant.
- [x] Update guidance and record validation; run independent delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| guard and tests | implementer | readiness | One writer; no changes to provider policy. |
| verification | code-reviewer, qa-reviewer, architecture-reviewer | delivered diff | Independent contexts; real build path and preserved epoch oracle. |

## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/README.md`
- `docs/architecture/chunking-and-indexing-pipeline.md`

## Affected Architecture Docs

No dependency or storage-schema change. Update framework README indexing guidance to state that precision conversion is explicit, with the refusal and recovery options. Also update docs/architecture/chunking-and-indexing-pipeline.md Stage 4 and precision-version discussion, which currently say every precision change forces re-encoding; qualify that conversion requires explicit full. Existing build/failure contracts remain authoritative.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevent unrequested corpus cost and state transition. |
| AC-2 | required | Preserve intended CPU and migration workflows. |
| AC-3 | required | A hidden refusal recreates the operational hazard. |
| AC-4 | required | Scoped correctness. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Incident traced before any handler source edits. Native reads used after MCP index-runtime-stale refusals. Host update recovered complete state at generation 1848 with unchanged full-class identities. | indexer._build_index_locked; accel_embedder._available_gpu_providers; model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT. |
| 2026-09-21 | Readback: an ordinary update against full-class vectors currently switches to INT8 and rebuilds when provider selection falls back to CPU; after this change it returns a clear failure without embedding or altering the published epoch. Explicit full conversion and compatible incremental updates remain available. AC-1–4 cover the boundary and its consumers. Scope is indexer/setup, focused tests and update guidance; provider factories, query ranking and handler extraction are unchanged. | Operator-approved benchmark exception; prepared implementation and producer-built test matrix. |
| 2026-09-21 | Thought: serialize guard and consumer edits through one implementer, update README/pipeline guidance in parallel, then integrate focused test and mutant evidence before independent delivery review and the full suite. Gapfill: MCP index navigation reported runtime staleness; targeted native reads validate the affected build and consumer paths. | Implementer owns code/tests; coordinator owns documentation, integration and evidence. |
| 2026-09-21 | Implementer readback: ordinary updates currently escalate recognized precision differences into re-embedding. Smallest repair is an early explicit-token comparison using current-schema provenance and original caller full intent; provider/query policy stays unchanged. Verification will compare a real producer-built canonical snapshot, spy model/epoch entry, exercise both precision directions and consumer failures, and remove the guard as a negative control. Gapfill: native inspection used while MCP index/runtime currency was unavailable. | indexer._build_index_locked; setup_index.main; public failure consumers. |
| 2026-09-21 | Implemented current-schema explicit full/int8 preflight before targeted/scoped escalation; original full intent is retained. Both setup paths now report nonzero build failure without inferring epoch/reader state. Twenty-one focused tests passed in 13.383s: real producer matrix, both directions, full/docs/code/graph/dry-run/targeted/rechunk/sibling, unchanged canonical SQL state and zero model/epoch entry, compatible changed-file reuse, explicit conversion, fresh non-full CPU install, real provider predictor, revision/legacy controls, guard-removal mutant, and real CLI/setup/MCP refusal consumers. Full indexer/setup modules remain running. | /private/tmp/1yljp-focused.log; test_indexer.ExplicitPrecisionRebuildTests and PrecisionClassVersionTests. |
| 2026-09-21 | Observe: two independent contexts approved the frozen product boundary and killed six focused mutants each. Integration exposed a new test isolation issue: in-process server loading purged a module required by a later identity assertion. Reflect: exercise this stateful consumer in a child interpreter so its module lifecycle cannot contaminate neighboring tests. Product code unchanged. Thought: verify the repaired test and identity pin together, refresh affected reviewer judgments, then rerun the full suite. | First full run: 9,479 tests, failed only test_indexer.py. Repaired focused run: 22 passed; canonical-interpreter setup/consumer/identity run: 165 passed. First raw-host combined run had five additional dependency-environment failures, absent with the canonical interpreter. |
| 2026-09-21 | Observe: the second canonical full run exposed two old fixtures (three failing assertions) that changed precision while testing fingerprint/model currency. Repair preserves producer precision for fingerprint mutation and pins recorded precision for targeted identity variation; original assertions remain and an explicit no-failure assertion was added. Both independent contexts rechecked these exact tests successfully; product/docs hashes unchanged. | Final test hash 8f54ab184a6851b237fae09b946c71fa562e8304; independent runs 2 passed each, zero skips. Full-suite final run pending. |
| 2026-09-21 | Observe: final full suite passed; independent delivery approvals are recorded and the framework receipt matches the current tree. No live corpus rebuild used for verification. All required behavior is delivered; terminal closure/commit remain operator-owned. | 9,479 tests, 12 skipped, 278.162s; receipt f9fd14354f9b28459f3cb3cc718dfe5538c8839f874f0d355d43c4d1a9d904b3. See delivery-review.md for all attempts, mutants and limitations. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Refuse implicit precision conversion; use existing explicit full request. | Small boundary fix prevents surprise cost and incompatible mixed vectors. | Preserve existing precision on CPU: useful future option but requires coordinated factory/cache/identity policy. Silently accept or relabel vectors: invalid full/INT8 equivalence and hidden cost. |
| 2026-09-21 | Separate incident repair from handler wave. | Index build policy is unrelated to mechanical handler extraction. | Widen 1ymzk: invalidates its zero-behavior-change objective. |
| 2026-09-21 | Operator explicitly waived the standing retrieval benchmark pair for this fix. Retain both invalid reports; require producer-built regression tests, a guard-removal test, independent review and the full suite instead. | Before runs for 1ymzk and 1yljp were invalidated by concurrent index activity. This exception is scoped to 1yljo and does not waive the handler split's evaluation obligations. | Retry the benchmark after isolating concurrent activity: not required for this bounded build-policy repair. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Internal escalation erases whether full was explicitly requested. | Capture caller intent before escalation; test scoped and all-layer entries. |
| A refusal mutates state before returning. | Compare producer-built canonical state and epoch and spy embedding entry, not just output text. |
| Existing precision-change tests expect automatic conversion. | Update those expectations explicitly and retain an explicit-full positive case. |

## Session Handoff

See `docs/agents/session-handoff.md`. Precision guard implementation is underway; handler wave remains paused.
