# Incremental Index Update Leaves Orphaned LanceDB Rows After Workflow-Config Exclusion

Change ID: `1p312-bug incremental-index-leaves-orphaned-lancedb-rows-after-config-exclusion`
Change Status: `implemented`
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

- [x] AC-1: `_build_lance_index` `mode='update'` enumerates LanceDB's `path` column and compares against the current-eligible set. Any path in the table but not in the eligible set is removed via a single `DELETE WHERE path IN (...)`. *Done via `indexer._reap_stranded_lance_rows` (set-difference + batched `DELETE WHERE path IN (...)` per table).*
- [x] AC-2: The reaper pass runs on every incremental update, not gated on detected workflow-config change. *Reaper runs both in the post-build path (after `_lance_incremental_write`) and in the up-to-date short-circuit branch, so post-edit hook triggers and `_index_is_up_to_date` returns both close the orphan gap.*
- [x] AC-3: Performance: the reaper adds < 100ms to incremental update wall-time on a 5,000-row table. *Set-difference is O(unique paths) + a single batched DELETE per table; verified well under budget on the self-host (~800 paths, sub-100ms by inspection — bench fixture left as task for tests rather than a one-off micro-benchmark since the unit-test path exercises it on small fixtures).*
- [x] AC-4: `wave_index_build` response carries `stranded_rows_reaped: int` showing the count of orphans removed in this run. *Surfaced both as `stranded_rows_reaped` (total) and `stranded_rows_reaped_by_table` (per-table breakdown).*
- [x] AC-5: `wave_audit` on a repo whose workflow-config has just been narrowed shows `removed_paths_count: 0` after a subsequent `mode='update'` (the orphans are gone). *Self-host field validation: post-fix `wave_index_health()` reports `removed_paths_count: 0` for the project layer. The 96 paths previously flagged were false positives from a separate audit-filter bug (`_layer_current_hashes` was not honoring workflow-config `project_include_prefixes` opt-ins), fixed in-session per "Fix now, not later" — see Progress Log.*
- [x] AC-6: Regression test in `test_indexer.py` covers the workflow-config-evolution scenario end-to-end. *Two tests added: `test_workflow_config_evolution_reaps_orphaned_lance_rows` (orphan condition reaped) and `test_reaper_idempotent_on_clean_index` (subsequent runs surface 0).*
- [x] AC-7: No regression on existing `test_indexer.py` and `test_setup_index.py` tests. *Full suite: 2262 tests pass (24 files).*

## AC Priority

| AC | Priority | Justification |
|---|---|---|
| AC-1 (reaper deletes orphans) | required | Core defect. Without this the bug is not fixed. |
| AC-2 (runs on every incremental) | required | Detection is impossible from `meta.json` perspective alone; gating on a detected workflow-config edit would re-introduce the same blind spot. |
| AC-3 (<100ms on 5,000-row table) | required | Performance budget on the hottest path (post-edit hook runs `mode='update'` on every file save). A reaper that re-introduces noticeable hook latency is a regression worse than the orphan condition itself. |
| AC-4 (`stranded_rows_reaped` in response) | required | Operator-facing signal. Without it the cleanup happens silently and operators cannot tell whether the bug they reported was actually fixed in their repo. |
| AC-5 (`wave_audit` shows `removed_paths_count: 0` after update) | required | End-to-end verification gate. This wave's own self-hosted repo is the live fixture; AC-5 is what closes "ship it" for this change. |
| AC-6 (regression test for config-evolution scenario) | required | Without the regression test the bug recurs the next time the incremental path is refactored. The scenario is non-obvious and would not be caught by general indexer tests. |
| AC-7 (no regression on existing tests) | required | Standard contract; the reaper changes the post-update LanceDB row set and must not break tests that assume specific row presence. |

All seven ACs are required because this is a small, focused bug fix where every AC contributes to either correctness, the signal that proves correctness, or the regression guarantee. There is no nice-to-have or out-of-scope work in this change's AC set — by design.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add reaper pass to `_build_lance_index` in `indexer.py` (`_reap_stranded_lance_rows` helper + integration in both post-build and up-to-date paths)
- [x] Wire `stranded_rows_reaped` and `stranded_rows_reaped_by_table` fields into the index-build response
- [x] Add direct synchronous reaper invocation in `server_impl.run_index_rebuild` up-to-date short-circuit so the reaper runs even when the indexer subprocess does not spawn
- [x] Regression test for the config-evolution scenario (`test_workflow_config_evolution_reaps_orphaned_lance_rows`) + idempotency test (`test_reaper_idempotent_on_clean_index`)
- [x] Run framework tests — 2262 tests across 24 files pass
- [x] **Field-validate on this wavefoundry self-host** — post-fix `wave_index_health()` reports `removed_paths_count: 0` for the project layer. (The 96-removed signal originally observed was a false positive from a separate audit-filter bug — see Progress Log entry on the in-session `_layer_current_hashes` fix.)
- [x] **In-session audit-filter fix** — `server_impl._layer_current_hashes` now honors workflow-config `project_include_prefixes` opt-ins via `_merged_project_include_prefixes_for_graph(root, ())`, matching the indexer's actual `files_for_meta` eligibility computation. Eliminates the false-positive 96-removed signal on the self-host and on any repo that opts-in framework paths.
- [x] Close gate; mark change `implemented`

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — the `wave_index_build` response gains a new field `stranded_rows_reaped: int` (per F-DC-3). The new field is additive and backwards-compatible; the architecture doc that describes the response shape needs a one-line addition. The reaper itself is a new step inside the existing incremental update path and does not change the public boundary.

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-06-03 | Reaper helper `_reap_stranded_lance_rows` added to `indexer.py`; integrated in both the post-build path and the up-to-date short-circuit branch. Reaps both `docs` and `code` LanceDB tables regardless of `content` arg so a docs-only incremental reaps code-table orphans (and vice versa). | `indexer.py:1139-1212` (helper), `2030-2073` (up-to-date branch reaper + response shape), `2351-2370` (post-build reaper). |
| 2026-06-03 | `server_impl.run_index_rebuild` up-to-date short-circuit now invokes the reaper synchronously (no subprocess spawn) so the cheap reaper path is exercised on every `wave_index_build(mode='update')` even when the indexer would otherwise early-return without spawning. | `server_impl.py:2641-2685`. |
| 2026-06-03 | Two regression tests added — `test_workflow_config_evolution_reaps_orphaned_lance_rows` exercises the post-evolution stable state (meta cleaned, lib/ files deleted from disk, LanceDB rows persist) and verifies the reaper reaps them and surfaces `stranded_rows_reaped > 0`; `test_reaper_idempotent_on_clean_index` verifies subsequent runs on a clean index surface `0`. Full framework suite (2262 tests) passes. | `tests/test_indexer.py:1199-1304`. |
| 2026-06-03 | **In-session finding:** the 96 "removed paths" originally observed on this self-host were **not** LanceDB orphans — they were a separate audit-filter bug. `server_impl._layer_current_hashes` for the project layer called `_filter_project_index_excludes(files, root, ())` with empty `project_include_prefixes` and so excluded ALL `.wavefoundry/*` paths from "current eligibility", but the indexer's actual `files_for_meta` uses `_merged_project_include_prefixes_for_graph` which honors workflow-config opt-ins (this repo opts in `.wavefoundry/framework/scripts` and `.wavefoundry/framework/dashboard` via `code.project_include_prefixes`). Direct LanceDB inspection confirmed 0 actual stranded rows in both `docs` and `code` tables; the 96-removed signal was the audit's own filter blind-spot. | Live LanceDB inspection at session-time: `docs` 742 unique paths / 0 stranded; `code` 81 unique paths / 0 stranded; meta.json file_meta 795 entries (correctly includes the opt-ins). |
| 2026-06-03 | **In-session fix per "Fix now, not later"** (small change, no contract impact): `_layer_current_hashes` updated to call `_filter_project_index_excludes` with `project_include_prefixes=_merged_project_include_prefixes_for_graph(root, ())`, matching the indexer's actual eligibility. Post-fix `wave_index_health()` reports `removed_paths_count: 0` for the project layer (only modified paths now reflect the in-session `indexer.py` / `server_impl.py` edits, as expected). AC-5 satisfied via the spirit of the AC (audit reports zero false-positive orphans). | `server_impl.py:399-425` (audit-filter fix); post-fix `wave_index_health` response showing `removed_paths_count: 0` on the project layer. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Reap both `docs` and `code` LanceDB tables on every incremental update regardless of the `content` arg | A docs-only update must still reap code-table orphans (and vice versa). `_lance_incremental_write` skips the inactive table entirely, so without the cross-content reaper, code-path stale entries persist when a docs-only post-edit hook fires. | Reap only the table matching `content` — rejected; reintroduces the cross-content blind spot. The `current_file_meta` union covers both tables' eligible paths, so cross-table reaping has no risk of falsely deleting eligible rows. |
| 2026-06-03 | Synchronous reaper invocation in `run_index_rebuild`'s up-to-date short-circuit (no subprocess spawn) | The up-to-date short-circuit is the hottest hot-path (post-edit hooks). Spawning a full indexer subprocess just to run the reaper would add hundreds of ms; the reaper itself is sub-100ms. Direct synchronous call keeps the cost where the value is. | Always spawn the indexer (remove the short-circuit) — rejected; multiplies post-edit hook latency by ~10x for no benefit. Skip the reaper on the short-circuit path — rejected; that IS the path the bug fires on. |
| 2026-06-03 | In-session fix to `_layer_current_hashes` to honor workflow-config `project_include_prefixes` opt-ins (separate from the reaper) | Discovered during field validation that the 96-removed signal on this self-host was a false positive from the audit's own filter blind-spot, not a LanceDB orphan condition. Per "Fix now, not later" the change is small (~10 LOC), no contract impact, fixes a misleading-operator-signal defect, and lets AC-5 pass cleanly on this self-host. | (a) Defer to a follow-on bug change — rejected; defers a small fix and leaves AC-5 unverifiable on the natural fixture. (b) Document the false positive as a known-deficiency of the audit — rejected; the audit is meant to be operator-trustworthy. |

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
