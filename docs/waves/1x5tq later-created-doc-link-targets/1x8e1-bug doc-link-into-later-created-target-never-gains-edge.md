# A Doc Link Into a Target Created Later Never Gains Its Edge Until the Doc Is Re-Scanned

Change ID: `1x8e1-bug doc-link-into-later-created-target-never-gains-edge`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-05
Completed at: 2026-09-05
Wave: 1x5tq later-created-doc-link-targets

## Rationale

Found by the code lane's cycle-2 reverification of wave `1x6ti` (CODE-RV2-1)
while probing the assembly-time dangling-endpoint filter, and reproduced
without any outage. Doc link resolution in the graph merge is
extraction-time against the session's current paths: a doc scanned while
its link target is absent (a doc written before the file it links to, or a
first build during a walk outage) stores a fragment with no edge, is pruned
as a zero-edge doc, and is not re-scanned when the target appears in a later
build without the doc itself changing. The served payload then lacks the
edge and the doc node while a from-scratch build carries both; nothing
re-emits the edge until the doc is edited. The impacted-docs rescan in
`GraphIndexSession.finalize` keys on changed symbols (`mentioned_symbols`),
not on newly current paths, so the create side has no trigger symmetric to
the delete side that wave `1x6ti` repaired. The filter never sees these
edges (`edges_dropped_dangling` stays 0), so the gap is silent.

## Requirements

1. The impacted-docs rescan SHALL consider a stored document eligible when
   its unresolved normalized local targets intersect current paths, including
   node-less targets. Evaluate this condition before the zero-change return,
   even when no extracted file changed. The obligation belongs to each doc;
   a global newly-added-path delta SHALL NOT consume it. Preserve unresolved
   targets through unreadable-directory skips and failed reads, replacing
   them only after successful extraction, so unchanged recovery retries.
2. Persist unresolved target paths in both extraction artifacts and merge
   fragment summaries, including zero-edge documents whose served nodes are
   pruned. Reuse existing Markdown/backtick candidate, normalization, and
   exclusion rules; this repair does not broaden path or URL semantics.
   Eligibility uses a set intersection rather than rereading every doc.
   Reusing one loaded merge-state blob before the fast return is acceptable;
   its decode cost scales with the whole blob and is not claimed to be free.
   Preserve existing zero-change no-row-hydration/no-write assertions and
   avoid duplicate merge-state reads or text reads for unaffected docs.
3. Differential tests SHALL assert the exact referring doc node and expected
   edge source, target, and relation, plus `assert_equivalent`, immediately
   after target-only creation, then on unchanged and unrelated builds, for
   noded and node-less targets. The latter must remain without a target node.
   Inspect unresolved state across closed/reopened sessions and unrelated
   merges; cover skipped/failed doc reads followed by unchanged recovery,
   never-appearing targets, and absence of repeated rescans after resolution.

## Scope

**Problem statement:** a doc's link into a path that did not exist when the
doc was last scanned never appears in the served graph until the doc is
edited.

**In scope:**

- The impacted-docs rescan trigger, zero-change eligibility, and unresolved-link
  persistence/retry on doc artifacts and fragments in `graph_indexer.py`.
- Differential tests in `test_graph_incremental_merge.py`.
- `GRAPH_BUILDER_VERSION` moves (fragment shape changes).
- The zero-change caller integration in `indexer.py` and its tests in
  `test_indexer.py`: detect pending graph recovery without mutation, and run
  needed graph repair under the existing real-build lock/epoch while preserving
  `1x81w` dry-run purity. An idle build with no pending graph work stays a no-op.
- Builder-version pins in `test_graph_indexer.py` and the generated
  `docs/reports/graph-quality-post.json` must follow the new builder version.

**Out of scope:**

- Doc mentions of symbols (already covered by the symbol-keyed rescan).
- The delete side (wave `1x6ti`, change `1x5pc`).

## Acceptance Criteria

- [x] AC-1: After a doc linking to an absent target is scanned and the target is created in a later build, the next merge serves the edge and the doc node, equivalent to a from-scratch build under `assert_equivalent`, for a noded and a node-less target. Verification follows Requirement 3: direct edge/node and persisted-state assertions, target-only/unchanged/unrelated builds, and unchanged recovery after skipped or failed doc reads.
- [x] AC-2: A doc whose unresolved targets never appear is not re-scanned on unrelated or unchanged builds (stored unresolved targets intersect current paths, pinned by a rescan spy); successfully resolved targets stop repair rescans. Preserve the existing zero-change row/write cost assertions and reuse the loaded merge-state blob.
- [x] AC-3: The change's own suites pass; the documents it edits validate; no failure elsewhere is attributable to it.

## Tasks

- [x] Red first: Requirement 3's differential and absolute assertions for the doc-before-target sequence and deferred-read recovery, failing on the current merge. Include Markdown/backtick and local-path cases with external/self/anchor-only negative controls under existing semantics.
- [x] Record unresolved targets in doc artifacts and fragment summaries; add persistent per-doc eligibility before zero-change and retain-until-success rescans; bump `GRAPH_BUILDER_VERSION` with its pins. Verify zero-edge fragment persistence, unchanged cost controls, and cessation of resolved-target rescans.
- [x] Integrate and verify unchanged recovery through `build_index` and its CLI entry path, preserving locked/epoch-fenced real graph repair, dry-run no-write reporting, and the genuine idle no-op. The readiness fit probe executed `build_index` and observed zero graph-build calls on an unchanged build; caller integration is explicitly admitted for this Prepare pass.
- [x] Mutations in a scratch copy; record the table.
- [x] Docs: `docs/architecture/graph-index-system.md` (the impacted-docs rescan passage); CHANGELOG under Unreleased.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                 |
| ---------- | ----------- | ---------- | ------------------------------------- |
| record     | implementer | —          | Unresolved link targets on fragments. |
| trigger    | implementer | record     | Retained unresolved-current eligibility and retry. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `docs/architecture/graph-index-system.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/reports/graph-quality-post.json`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` (the impacted-docs rescan and the
incremental-equals-full invariant) gains the create-side trigger. No boundary
change. `docs/architecture/data-and-control-flow.md` also records selective
zero-change graph dispatch under the build lock/epoch and its dry-run boundary.

## AC Priority


| AC   | Priority | Rationale                                    |
| ---- | -------- | -------------------------------------------- |
| AC-1 | required | The user-visible defect is missing edges/nodes; persisted obligations and recovery checks distinguish a durable fix from one happy-path build. |
| AC-2 | required | Selectivity prevents an every-doc rescan regression; absent and already-resolved controls plus existing zero-change cost assertions make the bound observable. |
| AC-3 | required | Relevant suites, builder pins, and edited-doc validation must establish correctness without attributing unrelated failures to this fix. |


## Progress Log

- 2026-09-05 — Operator authorized closure and commit after delivery review. All required ACs and tasks complete; no deferrals. Changelog covers both changes and the interrupted-publication repair.

- 2026-09-05 — Delivery repair cycle 2 (ARCH-DEL-1): independent publication-failure probe found a consumed obligation could bypass unchanged retry while the graph payload remained unbound. Shared the existing read-only payload binding predicate between preflight and finalize, including summary fingerprint agreement; retained the existing locked full-merge fallback. Added public interruption/retry and missing/size/mtime/summary-fingerprint controls. Five idle recovery tests pass. Fresh architecture and QA reverification cleared ARCH-DEL-1; all five technical lanes and the delivery council approved. Final framework run: 8,480 tests/74 files, 3 skips, OK; full docs validation clean. Requirements and AC scope unchanged. See delivery-review.md and delivery-evidence.json.

Thought: implement the admitted repair after current combined Prepare and activation. Root owns `indexer.py` and its tests, landing the dry-run gate first; a separate implementer owns graph persistence/rescan and its differential tests. Root integrates the read-only pending-work plan, documentation and full verification.

Gapfill: MCP keyword lookup excludes framework test files and returned no hits; used scoped shell search for fixture helpers after the MCP outline and targeted reads.


| Date       | Update                                                                                       | Evidence                                              |
| ---------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-09-05 | Filed from the wave `1x6ti` delivery review (CODE-RV2-1): reproduced without an outage through the merge harness; oracle-only edges and node after the target is created; re-scanning the doc restores equality. | Wave `1x6ti` events ledger, finding CODE-RV2-1; the code lane's `rv2_code_1x6ti/probe_b_classify.py`. |
| 2026-09-05 | Admitted to wave `1x5tq`; readiness council COUNCIL-READY-1 required bounded plan clarification. Requirements, AC evidence, tasks, and priorities now specify durable per-doc retry before zero-change, both persisted representations, unchanged recovery, exact graph assertions, and cost controls. No implementation task or AC is complete. | Wave events ledger, readiness finding and cycle-1 repair; readiness review report. |
| 2026-09-05 | Thought: include the demonstrated outer idle-build dispatch gap in this fresh combined Prepare pass, before any code edits. Coordinate its read-only pending-work decision and real graph repair with `1x81w`. | Fit probe: healthy unchanged `build_index` returned up_to_date with zero `_build_graph_artifacts` calls; current `_build_index_locked` returns before the normal graph call. |


Observe: graph scope completed with 52 incremental-merge tests, 547 graph-indexer tests, and 90 graph-quality tests passing; builder 51 report retains 10 true positives, 0 false positives and 2 false negatives. New `LaterCreatedDocTargetTests` directly checks exact doc/edge output plus full-build equality, persisted artifact/summary state, absent/resolved selectivity, read/exists/directory failures, normalization controls, preflight snapshot reuse/version migration, and missing-summary recovery. Public `IdleDocLinkRecoveryTests` passed 3 cases: unchanged noded recovery, node-less recovery combined with dirty epoch, and graph recovery combined with orphan/reap work. They assert dry-run persisted-state identity, explicit pending flags, real CLI entry, actual lock/epoch at repair, exactly one graph merge and no next-idle dispatch. The full indexer suite passed 354 tests.

Thought: the full framework run found the documented builder-50 constant in `docs/RELIABILITY.md:42`; update that version reference to 51 as the directly related builder-pin follow-through, then revalidate. This is a documentation-only Level 1 correction; no runtime scope change.


### Implementation mutation evidence

All mutations ran in isolated scratch copies or in-memory modules; the working tree retained the repair. Each row names an observed failing assertion, with no errors or unintended skips.

| Mutation | Named failing test | Result |
| --- | --- | --- |
| `drop_full_merge_artifact_retry` | `LaterCreatedDocTargetTests.test_full_merge_recovery_uses_retained_artifact_obligation` | FAILED (failures=1) |
| `hide_invalid_merge_state` | `LaterCreatedDocTargetTests.test_full_merge_recovery_uses_retained_artifact_obligation` | FAILED (failures=1) |
| `drop_artifact_obligation` | `LaterCreatedDocTargetTests.test_candidates_keep_existing_normalization_and_exclusions` | FAILED (failures=8) |
| `drop_fragment_obligation` | `LaterCreatedDocTargetTests.test_candidates_keep_existing_normalization_and_exclusions` | FAILED (failures=7) |
| `remove_early_retry_gate` | `LaterCreatedDocTargetTests.test_failed_or_unreadable_doc_retries_on_unchanged_recovery` | FAILED (failures=5) |
| `remove_retry_trigger` | `LaterCreatedDocTargetTests.test_candidates_keep_existing_normalization_and_exclusions` | FAILED (failures=8) |
| `rescan_absent_and_resolved` | `LaterCreatedDocTargetTests.test_read_only_preflight_reuses_blob_and_detects_version_mismatch` | FAILED (failures=3) |
| `consume_failed_read` | `LaterCreatedDocTargetTests.test_failed_or_unreadable_doc_retries_on_unchanged_recovery` | FAILED (failures=2) |
| `reread_cached_blob` | `LaterCreatedDocTargetTests.test_read_only_preflight_reuses_blob_and_detects_version_mismatch` | FAILED (failures=1) |
| `ignore_version_mismatch` | `LaterCreatedDocTargetTests.test_read_only_preflight_reuses_blob_and_detects_version_mismatch` | FAILED (failures=1) |
| `allow_self_candidates` | `LaterCreatedDocTargetTests.test_candidates_keep_existing_normalization_and_exclusions` | FAILED (failures=1) |
| `skip_idle_summary_validation` | `LaterCreatedDocTargetTests.test_full_merge_recovery_uses_retained_artifact_obligation` | 1 assertion failure, no errors/skips |
| `remove-dryrun-gate` | `DryRunIdleMaintenanceTests.test_dirty_epoch_dry_run_is_byte_identical_and_reports_recovery` | 1 assertion failure, no errors/skips |
| `ignore-graph-at-idle-return` | `IdleDocLinkRecoveryTests.test_unchanged_public_recovery_after_failed_doc_read` | 1 assertion failure, no errors/skips |
| `repeat-orphan-graph-merge` | `IdleDocLinkRecoveryTests.test_pending_link_and_orphan_reap_share_one_graph_merge` | 1 assertion failure, no errors/skips |

Sources: `test_graph_incremental_merge.py` and `test_indexer.py`. The graph mutants remove artifact/fragment obligations, the pre-idle retry condition, retained retry execution, read selectivity, failed-read retention, cached-blob reuse, version invalidation, self-link rejection, artifact-backed full-merge recovery, or invalid-summary recovery. Caller mutants remove the dry-run return, omit pending graph work from the idle-return condition, or repeat graph orphan retirement after the repair merge.

Observe: final consistency check exposed a missing merge-summary blob with a still-valid bound graph payload. The earlier fixture removed both and could not detect the idle return. The revised test removes only the blob, passes the cached read-only plan, and fails the exact doc-node assertion before repair. Shared merge-summary validity now gates preflight, the idle return and incremental selection; a cached missing-blob sentinel is reused without a second query. All 52 incremental tests pass; deleting only the new idle summary condition fails the revised test. This is a bounded Level 1 completion of artifact-backed recovery, not new scope. Graph mutation total is 12; with the 3 caller mutations, all 15 are rejected.

Observe: final frozen-tree `python3 .wavefoundry/framework/scripts/run_tests.py` passed 8,478 tests across 74 files in 185.569 seconds (3 skips). Fresh receipt: `result=ok`, `inputs_hash=4f1428e2657d73f3235f39674788fd5f5c29477e398a70ed96a61766492d78b6`. Full documentation lint and `git diff --check` pass. Framework edit gate closed. Computational implementation is complete; delivery-phase inferential reviews remain the next workflow. Final suite log: `/tmp/1x5tq-framework-tests-final-frozen.log`.

Observe: operator-requested additional smoke pass passed 16 focused tests (zero skips) and 12 independent real CLI invocations across noded and node-less targets. Dry-run persistence, dirty-epoch reporting/recovery, exact edge/doc output, unchanged referring text, stopped repair dispatch and full-build equivalence verified. See [smoke test evidence](smoke-tests.md), including the graph-only cold-index fixture limitation.

## Decision Log


| Date       | Decision                                              | Reason                                                        | Alternatives                                                        |
| ---------- | ----------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------- |
| 2026-09-05 | Park as its own plan rather than repair in `1x6ti`. | Pre-existing, create-side, fragment-shape change with a builder bump. | Repair in-wave: a second builder bump and rescan redesign in a delivery cycle. |
| 2026-09-05 | Use retained per-doc unresolved-target intersection with current paths, clearing only after successful extraction. | A global creation transition loses retry after skipped reads; the retained obligation reuses existing rescan machinery. One reusable merge-state blob read is acceptable, with its whole-blob decode cost explicit. | Global path snapshot adds acknowledgment state; unconditional scans violate selectivity; assembly-time raw-candidate resolution reduces source I/O but broadens edge ownership and deletion/outage handling beyond this repair. |


## Risks


| Risk                                                        | Mitigation                                                     |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| The trigger re-scans many docs on a large path addition.    | Intersection with recorded unresolved targets only; no whole-doc scan. |
| Early eligibility loads a potentially large merge-state blob. | Load once and reuse; preserve row/write cost tests; no unmeasured latency claim or new sidecar. |
| A referring doc cannot be read at target creation. | Keep its unresolved obligation until successful extraction and test unchanged recovery. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
