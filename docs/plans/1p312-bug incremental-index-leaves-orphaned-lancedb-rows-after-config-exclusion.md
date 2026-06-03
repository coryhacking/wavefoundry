# Incremental Index Update Leaves Orphaned LanceDB Rows After Workflow-Config Exclusion

Change ID: `1p312-bug incremental-index-leaves-orphaned-lancedb-rows-after-config-exclusion`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-03
Wave: TBD (UX-polish / index-hygiene follow-on; could pair with `1p30y` / `1p310`)

## Rationale

`wave_audit` on the self-hosted wavefoundry repo flagged 96 paths under the project layer as "removed" — all of them framework files (`.wavefoundry/framework/scripts/*`, `.wavefoundry/framework/dashboard/*`, etc.) that the project-layer `workflow-config.json` now excludes via include-prefixes. Investigation shape:

- `current_hash_count: 693` — `meta.json` already reflects the post-exclusion eligible set (correct).
- `removed_paths_count: 96` — these 96 paths are still present in LanceDB but no longer in `meta.json`.
- `files_total: 787` ≈ `693 + 96` — the table physically holds 789 rows, only 693 of which are tracked.

Root cause hypothesis: the incremental update path (`indexer.py` / `setup_index.py` `mode='update'`) walks the **current eligible set forward** — enumerates files that match current include-prefixes, computes their hashes, diffs against `meta.json`, and adds/modifies/removes entries for files in the eligible set. It does **not** enumerate the *opposite* direction: "what's in LanceDB but no longer in the current eligible set." When `workflow-config.json` changes to exclude a directory (e.g. `.wavefoundry/framework/**` was moved into the framework index layer), the next incremental run drops those paths from `meta.json` but leaves their LanceDB rows orphaned.

Once the orphans accumulate they pollute project-layer docs-search results — semantic queries can return chunks from framework-internal files even though those files are supposed to be served only by the framework layer. The only thing that reaps them today is a full `mode='rebuild'`, which is a heavy operation (~minutes) for a once-per-config-change cost.

This is a hook-blind-spot bug: every operator whose workflow-config has evolved over time accumulates orphans silently, only surfaced when they run `wave_audit`.

## Requirements

1. The incremental update path (`mode='update'`) must reconcile the LanceDB row set against the current-eligible path set. Any LanceDB row whose `path` is not in the current eligible set must be deleted from LanceDB, regardless of whether the file still exists on disk.
2. The reconciliation pass must run on **every** incremental update, not just when `meta.json` indicates a workflow-config change — the bug is undetectable from meta.json's perspective alone (meta.json was already updated; only LanceDB is out of sync).
3. The reconciliation pass must be cheap: O(LanceDB row count) at most. No file I/O for files that aren't currently eligible.
4. Operator-facing logging: when the reaper deletes orphans, the `wave_index_build` response should include a `stranded_rows_reaped` count so operators see the cleanup happened.
5. Regression test: a fixture that simulates the workflow-config-evolution scenario (build with broad include-prefix → narrow include-prefix → run `mode='update'`) and asserts LanceDB no longer contains rows for the excluded paths.

## Scope

**Problem statement:** The incremental update path only iterates the current-eligible set forward, so LanceDB rows for paths that became ineligible after a `workflow-config.json` change are never deleted. Orphans accumulate until a full `mode='rebuild'` runs.

**In scope:**

- `indexer.py` `_build_lance_index` — add a stranded-row reaper pass during the incremental update.
- `dashboard_lib.py` / `wave_audit` — surface the orphan condition so operators see it earlier (already present today; verify no regression).
- `wave_index_build_response` — include `stranded_rows_reaped` count in the response.
- Regression test in `test_indexer.py` covering the workflow-config-evolution scenario.

**Out of scope:**

- Detecting workflow-config edits and proactively triggering a build (separate UX question).
- Cross-layer orphans (project paths erroneously indexed in framework, or vice versa). Same shape but separate bug surface.
- Forcing operators to rebuild after a workflow-config edit (high friction; the reaper makes incremental sufficient).

## Acceptance Criteria

- [ ] AC-1: `_build_lance_index` `mode='update'` enumerates LanceDB's `path` column and compares against the current-eligible set. Any path in the table but not in the eligible set is removed via a single `DELETE WHERE path IN (...)`.
- [ ] AC-2: The reaper pass runs on every incremental update, not gated on detected workflow-config change.
- [ ] AC-3: Performance: the reaper adds < 100ms to incremental update wall-time on a 5,000-row table.
- [ ] AC-4: `wave_index_build` response carries `stranded_rows_reaped: int` showing the count of orphans removed in this run.
- [ ] AC-5: `wave_audit` on a repo whose workflow-config has just been narrowed shows `removed_paths_count: 0` after a subsequent `mode='update'` (the orphans are gone).
- [ ] AC-6: Regression test in `test_indexer.py` covers the workflow-config-evolution scenario end-to-end.
- [ ] AC-7: No regression on existing `test_indexer.py` and `test_setup_index.py` tests.

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Add reaper pass to `_build_lance_index` in `indexer.py`
- [ ] Wire `stranded_rows_reaped` field into the index-build response
- [ ] Regression test for the config-evolution scenario
- [ ] Run framework tests
- [ ] Field-validate by rerunning `wave_audit` on the wavefoundry self-host and verifying `removed_paths_count: 0` after the next `wave_index_build(mode='update')`
- [ ] Close gate; mark change `implemented`

## Affected Architecture Docs

`N/A` — bug fix in an existing module. The reaper is a new step within the existing incremental update path; the public contract (response shape gains a new field; doesn't change existing fields) is backwards-compatible.

## Risks

| Risk | Mitigation |
|---|---|
| Reaper deletes rows for paths that are legitimately eligible but temporarily off-disk (e.g., a file being renamed mid-build) | Reconcile against the eligibility-set computation, not against disk presence. Renamed/moved files within scope stay indexed; only paths definitively excluded by current include-prefixes get deleted. |
| Performance regression on large LanceDB tables (10K+ rows) | Bench before/after with a synthetic fixture; the reaper is a set-difference + single DELETE, expected sub-100ms even at 50K rows. |
| Operators relying on the orphaned rows for some legacy search workflow | Acceptable: the orphans are by definition outside the configured project-layer scope. If they're useful they should be in their proper layer (e.g., framework). |
| The reaper runs while another build is in flight | The existing flock guard on the index-build path serializes builds; the reaper inherits that guarantee. |

## Related Work

- Discovered during the close-readiness review for `1p2q3 field-feedback-round-4`. The self-hosted project layer had accumulated 96 orphaned framework paths over several workflow-config evolutions. Not part of 1p2q3 scope; deferred to a follow-on (this change).
- Companion to `1p30y-enh dashboard-rendering-fidelity-phase-2` and `1p310-enh mcp-protocol-surface-phase-1b-2` (other follow-ons from the same close-readiness review).
- Hook context: post-edit hooks (`.cursor/hooks/after-file-edit.py` and equivalents) trigger `mode='update'` on every file edit. Once this change ships, hook-driven incremental updates also reap orphans transparently — no manual `mode='rebuild'` needed after a workflow-config narrowing.

## Session Handoff

Unattached future-wave plan. Admit when a Wave Council readiness review accepts the follow-on UX-polish / index-hygiene wave.
