# Shipped Eligibility Reap Lacks the Mass-Removal Protections Its Sibling Now Has

Change ID: `1u8o3-debt eligibility-reap-mass-removal-hazard`
Change Status: `implementing`
Owner: Engineering
Status: implementing
Last verified: 2026-09-04
Wave: `1x54z eligibility-reap-absence-guards`

## Rationale

Disclosed during wave `1u8o2`'s prepare and delivery reviews on 2026-08-01 and
deliberately kept out of that wave's scope; this record has carried the hazard
since so it would not evaporate with a session handoff. It was deferred once
more at the close of `1x4ol` on 2026-09-04 and is now admitted.

The shipped Lance eligibility reap, `_reap_stranded_lance_rows`, deletes every
row whose path is not in the current eligible set: `stranded = lance_paths -
eligible`, then a batched `DELETE` per table, then
`_cleanup_layer_state_for_reaped` drops the layer hashes for those paths. The
eligible sets, `docs_eligible_rel` and `code_eligible_rel`, are comprehensions
over the repository walk. That walk is `os.walk(root)` with the default
`onerror=None`, which silently drops any directory whose `scandir` raises. A
subtree that is transiently unreadable, from a permissions incident, an
unmounted volume, or an agent sandbox restriction, therefore reads as
ineligible: its rows are reaped, its layer hashes are dropped, and when it
returns every file in it is re-embedded from scratch.

The protections that would prevent this already exist a few hundred lines
below, in the `1u8nz` orphan-store reconciliation that runs at the same two
seams. That code classifies each candidate at a discrete stat seam
(`_orphan_path_stat` / `_classify_orphan_path`: `ENOENT` and `ENOTDIR` are
positive evidence of deletion and remove; every other `OSError` reads as
`unreadable` and preserves), and it defers loudly when a store would lose more
than `ORPHAN_RECONCILE_BREAKER_FRACTION` of its rows and at least
`ORPHAN_RECONCILE_BREAKER_MIN_ROWS`. The Lance reap has neither, and its
`plan_only` preflight is exactly where a breaker belongs. The two reaps run
back to back at both call sites, one protected and one not.

Re-derived against the current tree on 2026-09-04: `walk_repo`,
`_reap_stranded_lance_rows`, `_cleanup_layer_state_for_reaped`,
`_classify_orphan_path`, `_orphan_path_stat` and the breaker constants all
resolve; the reap is invoked at the zero-change seam (`plan_only=True`
preflight, then execute, then cleanup) and at the build-path seam (execute,
then cleanup), each immediately followed by `_plan_orphan_store_reconcile`.

## Requirements

1. The eligibility reap SHALL classify each stranded candidate before deleting
   it, reusing `_classify_orphan_path` and its `_orphan_path_stat` seam rather
   than a second classifier: `absent` (`ENOENT`/`ENOTDIR`) reaps as today;
   `present` reaps as today, because a present-but-out-of-scope path IS the
   scope-narrowing case the reap exists for; `unreadable` (any other
   `OSError`) preserves the rows AND the layer hashes.
2. The reap SHALL carry a mass-removal circuit breaker with the same shape and
   the same constants as the `1u8nz` reconciliation: a would-reap count that is
   at least `ORPHAN_RECONCILE_BREAKER_MIN_ROWS` and more than
   `ORPHAN_RECONCILE_BREAKER_FRACTION` of the table's rows defers loudly,
   naming the situation and the remedy, leaves both the rows and the layer
   hashes untouched, and lets the build succeed. Below the breaker the reap
   proceeds exactly as today.
3. Both protections SHALL apply at both seams, the zero-change preflight and
   the build-path reap, because the hazard is reachable from either; the
   `plan_only` preflight SHALL report a deferral so the execute step never
   reaps what the plan refused.
4. The walk's silent omission of unreadable directories SHALL be surfaced:
   `walk_repo` SHALL collect `os.walk` errors through `onerror` and expose the
   affected directories, so the reap can treat every candidate under an
   unreadable directory as `unreadable` without a stat per file. The decision
   between surfacing and stat-only classification is recorded in the Decision
   Log; surfacing is chosen because a stat per stranded candidate under an
   unreadable parent returns `EACCES` anyway, and the collector turns an
   invisible condition into a visible one for the build log.
5. Tests SHALL drive both protections by error injection at the seams
   (`_orphan_path_stat` for classification, the `onerror` collector for the
   walk), never by `chmod`, which is vacuous under root and flaky across
   platforms; a breaker fixture SHALL exercise both sides of the threshold; and
   the existing reap behaviour for genuine deletions and for scope departures
   SHALL be pinned unchanged.
6. Recovery SHALL require no re-embed: after an unreadable subtree becomes
   readable again, the next build finds its rows and layer hashes intact and
   treats the files as unchanged.

## Scope

**Problem statement:** a transient IO failure can silently reap and force a
full re-embed of an entire subtree because the shipped reap trusts
walk-derived eligibility without absence classification or a breaker.

**In scope:**

- `_reap_stranded_lance_rows`, its two call seams, and
  `_cleanup_layer_state_for_reaped` in `indexer.py`.
- An `onerror` collector on `walk_repo` and its surface to the reap.
- Reuse of the `1u8nz` classification seam and breaker constants.
- Regression tests with injection at the seams.

**Out of scope:**

- The `1u8nz` orphan-store reconciliation itself, which is already protected.
- Ignore-rule semantics and the eligibility definitions.
- The reap's genuine-deletion and scope-departure behaviour, which is pinned,
  not changed.

## Acceptance Criteria

- [x] AC-1: With the stat seam injected to raise `EACCES` for a subtree, a
      build preserves that subtree's Lance rows and layer hashes; with the
      injection removed, the next build reports those files unchanged and
      re-embeds nothing.
- [x] AC-2: A would-reap count over the breaker defers loudly, the build
      succeeds, rows and layer hashes are untouched, and the message names the
      remedy; one row under the breaker reaps as today. Asserted at both seams.
- [x] AC-3: `walk_repo` surfaces a directory `os.walk` could not read, and a
      candidate under it classifies `unreadable` without a per-file stat.
- [x] AC-4: A genuinely deleted file and a scope-departed file are still
      reaped, with their layer hashes dropped, exactly as before this change.
- [x] AC-5: Deleting the classification makes a named test fail; deleting the
      breaker makes a named test fail; both recorded as mutations before
      review.
- [x] AC-6: `docs/architecture/data-and-control-flow.md` describes the reap's
      protections beside the reconciliation's, and the changelog carries the
      fix.
- [x] AC-7: This change's own suites and every test it adds pass, the documents
      it authors or edits validate, and no failure elsewhere is attributable to
      it.

## Tasks

- [x] Red first: inject `EACCES` at the stat seam for a subtree and demonstrate
      the current reap-and-rehash loss and the forced re-embed on recovery.
- [x] Add the `onerror` collector to `walk_repo` and surface unreadable
      directories.
- [x] Classify stranded candidates through `_classify_orphan_path`, with the
      collector as a fast path, and preserve `unreadable`.
- [x] Add the breaker to the reap using the `1u8nz` constants, at both seams,
      with the preflight reporting deferral.
- [x] Pin genuine-deletion and scope-departure reaping.
- [x] Record both mutations.
- [x] Update the data-and-control-flow document and the changelog.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| red-first | implementer | — | Demonstrate the loss before touching the reap. |
| walk-surface | implementer | red-first | The `onerror` collector. |
| classify-and-break | implementer | walk-surface | Reuse the `1u8nz` seams; both call sites. |
| pins-and-docs | implementer | classify-and-break | Unchanged-behaviour pins, mutations, docs. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: the reap's absence
classification and breaker are described beside the `1u8nz` reconciliation's,
so the two seams read as one policy (item 15; item 11 carries the
carried-forward authority clause). `docs/architecture/graph-index-system.md`:
the orphan-retirement paragraph names the directory-shadowed exception the
merge now honours (added in delivery review, ARCH-RV1-3).
`docs/architecture/testing-architecture.md`: one row for the guard class. No
layering change: the reap keeps its place and its callers, and the graph merge
gains one keyword on three signatures.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The hazard the change exists to remove, asserted end to end including recovery. |
| AC-2 | required | The second protection, and the one that catches what classification cannot see. |
| AC-3 | required | Turns an invisible walk condition into a visible one; the fast path for classification. |
| AC-4 | required | A conservative reap that strands genuine deletions is a new bug. |
| AC-5 | required | Both guards must fail when deleted. |
| AC-6 | important | The two seams should read as one policy in the architecture record. |
| AC-7 | required | Standard delivery gate. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-01 | Filed as the close-surviving record of the hazard disclosed and deliberately descoped during wave 1u8o2 (architecture lane prepare P3 and delivery P3-4; code lane concurrence). | Wave 1u8o2 lane reports 2026-08-01. |
| 2026-09-04 | Admitted to wave `1x54z` after a second deferral at the close of `1x4ol`; anchors re-derived against the current tree. | `walk_repo` uses `os.walk` with the default `onerror=None`; `_reap_stranded_lance_rows` computes `stranded = lance_paths - eligible` with no classification and no breaker; `_classify_orphan_path`, `_orphan_path_stat`, `ORPHAN_RECONCILE_BREAKER_FRACTION` (0.5) and `ORPHAN_RECONCILE_BREAKER_MIN_ROWS` (8) exist for the sibling reconciliation; the reap runs at the zero-change preflight/execute seam and at the build-path seam, each followed by `_plan_orphan_store_reconcile`. Stale line anchors from the 2026-08-01 filing were replaced with symbols. |
| 2026-09-04 | Plan review (Review plan, batch): every branch in Requirements, ACs and Scope self-answered from the tree; one operator-visible consequence flagged rather than asked (the Lance breaker keeps deferred rows searchable, unlike the sidecar breaker). Self-answers: breaker unit is distinct paths per table, the unit `_plan_orphan_store_reconcile` already counts; both guards live in the reap's scanning branch, which is what the zero-change preflight and the build-path seam run, and the zero-change execute replays `paths_by_table` so it cannot reap what the plan refused; the collector is a keyword-only out-parameter on `walk_repo` so its 13 call sites (three in the indexer, five archived evidence scripts, tests) keep their contract; the collector is load-bearing, not a fast path, because a search-but-no-read directory fails `scandir` while `stat` on its children succeeds. Follow-on candidates recorded, not folded in: the graph merge's walk-parity prune and the secrets ledger's removal handling see the same walk omission. | `code_references walk_repo` (13 call sites); `_plan_orphan_store_reconcile` counts `store_rows` as a set of paths; POSIX directory permission semantics. |
| 2026-09-04 | Thought: reproduce before touching the reap. Observe (red, pre-fix tree, `EligibilityReapAbsenceGuardTests`): with `os.scandir` denied for `vault/`, the first incremental build reaped every vault row and dropped its layer hashes (`{'vault/a.py': set(), ...}` against the seeded ids); with `EACCES` injected at `_orphan_path_stat` for stranded rows at the zero-change seam, 6 rows reaped; nine absent paths of ten reaped 18 rows with no deferral at either seam. 5 failures, 2 errors (the two tests that call the new keyword arguments), 2 passes (the under-breaker pins, which hold pre-fix by construction). | Red run recorded in the session scratchpad (`red_run.txt`), then the class went green. |
| 2026-09-04 | Level 2 finding at the build-path seam (Reflect): the reap is not the first deleter there. Read from the tree, not the plan: the incremental Lance write receives `layer_stale | removed` and deletes `removed` rows before the reap runs, the layer-hash commit passes `remove_paths=removed_broad`, and the secrets ledger receives `removed=removed_broad`; all three act on the walk-derived removal set. A guard inside the reap alone therefore cannot satisfy AC-1 or Requirement 6 on the first unreadable build. Repair: neutralise the walk omission at its source in change detection, carrying the prior bookkeeping entry forward for every previously indexed path under an unreadable directory and withholding it from the removal set; the reap still receives `unreadable_dirs` because its per-table eligibility is walk-derived. Boundary recorded in the architecture doc and below: a first-time mass absence with NO walk error (an unmounted volume reads as ENOENT) is still removed by the write path on that build; the zero-change preflight, where the reap is the only deletion path, is fully guarded, and the build-path reap guards what survives the write. | `_write_docs_incr` / `_write_code_incr` (`_stale=(layer_stale[...] | removed)`), `update_layer_hashes(remove_paths=removed_broad)`, `_write_secrets(_removed=removed_broad)`; new block after `_detect_changes` in `_build_index_locked`. |
| 2026-09-04 | Implemented: `walk_repo(unreadable_dirs=...)` with an `onerror` collector (root-relative, `.` for the root, stderr line); `_shadowed_by_unreadable`; the change-detection carry-forward; `_reap_stranded_lance_rows(root=..., unreadable_dirs=...)` with classification through `_classify_orphan_path` and the `1u8nz` breaker in distinct paths, returning `preserved_by_table` and `deferred_by_table`; all three call seams updated (the source-pinned `_reap_stranded_lance_rows(\n            lance_db_path` prefix kept). Green: the 10 new tests, the whole `test_indexer.py` (325), `test_index_state_store.py` (52), the server-tools walk/reap tests (5). | `EligibilityReapAbsenceGuardTests`; `IndexerWiringTests.test_build_index_locked_wires_store_flow_after_meta_build` still passes. |
| 2026-09-04 | Mutations (AC-5), each in a scratch copy of the scripts tree, never the working tree. Classification deleted (`classification[rel] = "absent"`): `test_walk_dropped_subtree_is_preserved_and_recovers_without_reembed`, `test_stat_seam_eacces_preserves_at_the_zero_change_seam_and_recovers`, `test_candidate_under_a_surfaced_directory_classifies_unreadable_without_stat` fail. Breaker deleted (condition replaced by `False`): `test_breaker_defers_at_zero_change_preflight_and_execute_never_reaps_refused`, `test_breaker_defers_at_the_build_path_seam` fail. Two guards beyond the plan's pair, landed under the same rule: collector deleted (`os.walk(root)` without `onerror`): `test_walk_dropped_subtree_is_preserved_and_recovers_without_reembed`, `test_walk_repo_surfaces_the_unreadable_directory` fail; carry-forward deleted: `test_walk_dropped_subtree_is_preserved_and_recovers_without_reembed` fails. Working tree byte-identical throughout (`git status` shows only the two intended files). | Scratch runs `mut_classification.txt`, `mut_breaker.txt`, `mut_collector.txt`, `mut_carry_forward.txt`. |
| 2026-09-04 | Test-fixture observation, not a defect in this change: in a non-git fixture the secrets scanner's candidate walk sometimes picks up Lance internals under `.wavefoundry/index/` (a scan-versus-Lance-write race), which changes the sidecar breaker's `secret_scan_cache` denominator between runs and lets the sidecar reconcile open an epoch on its own. The zero-change breaker test neutralises `_plan_orphan_store_reconcile` so its epoch assertion is about the reap alone; production candidate sets are git-tracked files, where the index directory is ignored. | Probe: 14 vs 26 `secret_scan_cache` rows for the same fixture depending on test order. |
| 2026-09-04 | Gapfill: range-scoped `awk`/`sed` reads of `_build_index_locked` (a 1,400-line function) for the `removed` consumers and the bookkeeping construction, after `code_keyword` located the anchors; `code_read`, `code_definition`, `code_references` and `code_keyword` carried the rest of the investigation. | MCP-first posture kept for symbol location; shell used for line-ranged reads only. |
| 2026-09-04 | AC-7: full framework suite run LAST after every framework edit: 8,431 tests across 74 files, OK, 3 skipped (the standing environment skips); receipt `test-cache.json` green for the current tree (`framework_test_receipt: proven` on the close dry-run). `wf_validate_docs` clean. Close dry-run blocks only on delivery evidence (three lanes, delivery council, operator signoff), which is the next lifecycle step. | `run_tests.py --no-cache` at 2026-09-04T22:17:41Z; `wf_close_wave(mode='dry_run')`. |
| 2026-09-04 | Delivery review round 1 on frozen tree `9cda3df7e86be742`: five independent actors (code, QA and architecture lanes; red-team primer at standard depth; security-reviewer rotating seat) recorded 21 findings, 17 `do_now`. Two real regressions the implementation introduced: the graph merge derives its own removal set from the walk, so a build-path run during the outage pruned the shadowed subtree and, because recovery is a stat-cache hit, never re-extracted it (CODE-DEL-1 / QA-DEL-1 / RED-DEL-1, proven against a pre-wave control where recovery re-graphed); and the breaker counted present candidates, so an `include_tests` narrowing of ten of thirteen code paths deferred for ever where the pre-wave tree reaped 20 rows (RED-DEL-2). The walk-case test's first build was a zero-change build, so the build-path seam was untested and two carry-forward mutants survived (ARCH-DEL-1 / QA-DEL-2 / CODE-DEL-2); five further guards had no pin (CODE-DEL-3, QA-DEL-3, QA-DEL-4); the reconcile did not share the walk's report (RED-DEL-3); the preserved and deferred states were invisible to every tool surface (SEC-DEL-1); five documentation claims overstated the mechanism (ARCH-DEL-2/3, QA-DEL-5, RED-DEL-4, SEC-DEL-2). | `docs/waves/1x54z .../events.jsonl` records ARCH-DEL-1..4, QA-DEL-1..7, RED-DEL-1..4, CODE-DEL-1..3, SEC-DEL-1..3. |
| 2026-09-04 | Repair cycle 1 (Reflect: the Level 2 finding enumerated the consumers that delete on the removal set and missed the one keyed on the walk itself). `GraphIndexSession` takes `unreadable_dirs`; known paths under a reported directory count as current in the merge's known-minus-current prune (neither pruned nor re-extracted) at the ordinary merge and at `retire_orphaned_graph_paths`; a full rebuild passes none so the graph keeps parity with Lance. The extractor's output shape is unchanged, so `GRAPH_BUILDER_VERSION` is not bumped. The breaker counts `absent` candidates only; `present` reaps whatever its number. `_plan_orphan_store_reconcile` takes `unreadable_dirs` and classifies shadowed candidates unreadable without a stat. Both seams return `stranded_reap_deferred` and `stranded_reap_preserved`; the walk and carry-forward messages name the root as the repository root. The reap docstring, the reconcile docstring and the deferral message state the boundaries. Tests: `test_walk_dropped_subtree_survives_a_build_path_run`, `test_root_unreadable_is_a_loud_no_op_through_the_real_build`, `test_shadow_prefix_is_a_directory_boundary`, `test_walk_error_without_a_filename_is_recorded_as_the_root`, `test_breaker_thresholds_are_pinned_on_both_legs`, `test_present_scope_departures_reap_whatever_their_count`, `test_orphan_reconcile_treats_shadowed_candidates_as_unreadable`; the vacuous absent leg rewritten; the walk test's label corrected to the zero-change seam; envelope assertions in the walk, build-path and both breaker tests. Green: the class (17), `test_indexer.py` (332), `test_graph_indexer.py` (547), `test_graph_incremental_merge.py` (40), `test_index_state_store.py` (52), `test_graph_query.py` (90). | Scratch runs `repair_*.txt`. |
| 2026-09-04 | Mutations for the repair, each in a scratch copy, each killed by a named test: build-path reap collector wiring removed and bookkeeping carry removed and graph preservation removed, all three fail `test_walk_dropped_subtree_survives_a_build_path_run`; breaker counting present candidates fails `test_present_scope_departures_reap_whatever_their_count`; reconcile ignoring the walk fails `test_orphan_reconcile_treats_shadowed_candidates_as_unreadable`; min-rows leg loosened and fraction leg loosened each fail `test_breaker_thresholds_are_pinned_on_both_legs`; prefix boundary loosened fails `test_shadow_prefix_is_a_directory_boundary`; root rule removed fails that test and `test_root_unreadable_is_a_loud_no_op_through_the_real_build`; the no-filename fallback removed fails `test_walk_error_without_a_filename_is_recorded_as_the_root`; the deferral envelope key removed fails `test_breaker_defers_at_zero_change_preflight_and_execute_never_reaps_refused`. Working tree untouched by the mutants. | Scratch runs `r1mut_*.txt`. |
| 2026-09-04 | Follow-ons recorded, not folded in: an `index_health` diagnostic while a deferral persists (SEC-DEL-1's second half) needs epoch-free persistence of the deferral and a `server_impl.py` change; the explicit `files=` build seam wipes every unlisted path (SEC-DEL-3, pre-existing, no supported caller; the carry-forward is a walk-seam claim); a non-git repository's secrets candidate walk includes index internals (QA-DEL-7, parked as `docs/plans/1x550-debt non-git-secrets-candidate-walk-includes-index-internals.md`); the red-team primer's single classified removal plan consumed by every deleter, and the security seat's quarantine-instead-of-serve alternative for deferred and preserved rows. Primer question 7 (a legacy non-dict bookkeeping value through the carry-forward): the store materialises every entry as a dict and no consumer dereferences a carried entry (the layer-stale loop and the layer commit iterate walk-derived sets), so no guard was added. | Review reports in the session scratchpad; `1x550` plan. |
| 2026-09-04 | Reverification round on tree `18fce6098ed81741`: five fresh-context actors re-executed their own round-1 probes (the red-team and security seats against a pre-wave control rebuilt from `git show HEAD`). Every repaired finding verified and terminal in the ledger: ARCH-DEL-1 to 4, QA-DEL-1 to 7, RED-DEL-1 to 4, CODE-DEL-1 to 3, SEC-DEL-1 to 3. Residue recorded as new findings: the retirement-seam forwarding of the walk report and the full-rebuild carve-out were correct but unpinned, a mutant survived the class and the whole file for each (ARCH-RV1-1, ARCH-RV1-2, QA-RV1-1, CODE-RV1-1); the graph architecture record still described the prune as pure walk parity (ARCH-RV1-3); the envelope wording implied a registered tool relays the two new fields where `index_build` returns a spawn acknowledgement (SEC-RV1-1); a doc re-extracted during the outage lost its link edge into the subtree until its next edit, narrower than pre-wave, which lost both edges and restored neither (RED-RV1-1). Eight further break attempts by the red-team seat held (nested unreadable directory, file created or deleted inside during the outage, true orphans retired beside a shadowed subtree, full-rebuild parity, `files_shadowed` never persisted, mixed present and absent strands in one table, a path in both tables). | `events.jsonl` reverification records; scratch `rv_code`, `rv_qa`, `rv_arch`, `rv_redteam`, `rv_security`. |
| 2026-09-04 | Repair cycle 2 (implementer). `GraphIndexSession.__init__` widens the session's current-path set with the store's known paths under the reported directories, so a doc re-extracted during the outage resolves its links into the shadowed subtree (the prune in `finalize` widens the same set). Three named tests lifted from the lanes' probes: `test_retirement_seam_keeps_the_shadowed_subtree` (real residue retired while the subtree stays; recovery hashes nothing), `test_full_rebuild_during_outage_drops_the_subtree_in_parity` (graph and Lance both drop it; recovery re-extracts exactly the subtree), `test_doc_edited_during_outage_keeps_its_link_edges_into_the_subtree` (edge set equal before, during and after). `graph-index-system.md`'s retirement paragraph names the directory-shadowed exception at both entry points; item 15 states that the result is the Python return value and names plan `1x551`; Affected Architecture Docs lists the three documents. Class 20 OK. Mutants in scratch copies, each failing exactly its named test: the retirement forwarding removed, the carve-out replaced by an unconditional pass-through, the current-path widening removed. | Scratch `r2_class.txt`, `r2mut/m_retire.txt`, `r2mut/m_full.txt`, `r2mut/m_widen.txt`. |
| 2026-09-04 | Suites on the cycle-2 tree with the `framework_edit_allowed` gate closed: `test_graph_indexer.py` 547, `test_graph_incremental_merge.py` 40, `test_index_state_store.py` 52, `test_indexer.py` 335, all OK; the whole framework suite 8,441 tests across 74 files OK (3 skipped by design) with the receipt written; `wf_validate_docs` clean. | Scratch `r2_test_*.txt`, `full_suite_r2.txt`; `.wavefoundry/framework/test-cache.json`. |
| 2026-09-04 | Cycle-2 reverification on tree `b76b94ce414dcc1e` (five fresh-context actors; the first launch was cut off by a session limit and relaunched). ARCH-RV1-1/2/3, QA-RV1-1, CODE-RV1-1, SEC-RV1-1 and RED-RV1-1 all verified repaired with their mutants killed at class level (the widening mutant at whole-file level too), the red-team seat's eight further break attempts held, the security seat found no exposure in the widening (store-known paths only; a ghost link mints nothing; a gitignored-but-known path is served as of the last readable build in parity with the carry-forward). Residue: the architecture lane reproduced a crash the wave introduced under a REAL mode-000 outage: a code-symbol change whose old name a shadowed doc mentions makes the merge's impacted-docs rescan call `Path.exists` on the unreadable doc, which raises EACCES on Python 3.13, so every build during the outage raises until recovery (ARCH-RV2-1; the class's scandir injection leaves stat succeeding, so no shipped test reached it); the link-edge test's helper read a payload key that does not exist, so its tuples carried no relation (CODE-RV2-1); a `doc_references_doc` edge into a deleted doc resurfaces on the next unrelated build, identical on the pre-wave tree (RED-RV2-1, parked as `docs/plans/1x5pc-bug dangling-doc-link-edge-after-linked-doc-deletion.md`). | `events.jsonl` cycle-2 reverification records; scratch `rv2_*`. |
| 2026-09-04 | Repair cycle 3 (implementer). The impacted-docs pass in `GraphIndexSession.finalize` skips records under the reported directories, keeping their stored artifacts (the served-as-of-last-readable-build posture); `test_symbol_rename_during_outage_leaves_the_shadowed_doc_untouched` models a mode-000 directory faithfully (scandir denied AND stat on every child raising EACCES) and asserts the build completes, the subtree's rows and hashes are untouched, and recovery holds. The link-edge helper reads the edge's `relation` and the test asserts both relations by name. Disclosures: item 15, the retirement paragraph and the CHANGELOG state that a symbol change elsewhere does not rescan a doc inside the unreadable directory until it is readable again. Plan `1x551` names the retrieval test shard. Class 21 OK. Mutants in scratch copies: the skip removed fails exactly the new test (the build raises); the widening removed fails exactly the link-edge test under the corrected oracle. | Scratch `r3_class.txt`, `r3mut/m_impacted.txt`, `r3mut/m_widen.txt`. |
| 2026-09-04 | Suites on the cycle-3 tree (`6d7036e928850830`) with the gate closed: `test_graph_indexer.py` 547, `test_graph_incremental_merge.py` 40, `test_index_state_store.py` 52, `test_indexer.py` 336, all OK; the whole framework suite 8,442 tests across 74 files OK (3 skipped by design) with the receipt written; `wf_validate_docs` clean. | Scratch `r3_test_*.txt`, `full_suite_r3.txt`; `.wavefoundry/framework/test-cache.json`. |
| 2026-09-04 | Cycle-3 reverification on tree `6d7036e928850830`: the architecture lane re-ran its real-chmod probe (the outage build completes, the subtree's rows, hashes, store rows and fragment untouched, recovery holds, a later edit refreshes the doc's edges; the ENOENT branch keeps then reconciles) and killed the skip mutant at the original crash site; the code lane confirmed the edge oracle carries relation names and that the test's stat injection matches a real mode-000 directory on the shipped interpreter (`Path.exists` raises, `os.path.exists` returns False, the directory's own stat succeeds); the QA lane re-established its approval evidence (class 21, four mutants including the cycle-0 classification and breaker guards, three probes, AC matrix verified). Residue: the stale fragment edge a preserved doc keeps to a renamed symbol is masked for one build and re-emitted with no target node by a later merge (ARCH-RV3-1; parked in plan `1x5pc`, widened to filter fragment edges to absent nodes at payload assembly), and three clauses stated the residual with the wrong sign (ARCH-RV3-2, QA-RV3-1; corrected, reverified by fresh-context architecture and QA runs against a five-stage executed trace). The ledger's cycle 2 is aggregate-complete with the convergence checkpoint over all 34 findings. | `events.jsonl` (run-convergence-2); scratch `rv3_*`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-04 | Surface the walk's omissions through an `onerror` collector AND classify at the stat seam, rather than either alone. | The collector makes an invisible condition visible in the build log and gives the reap a fast path for every candidate under an unreadable parent; the stat classification covers the case the collector cannot, a path whose parent walked fine but which itself is unreadable. Both reuse existing seams. | **Stat-only classification:** correct but stats every stranded candidate under an unreadable tree and leaves the walk silent. **Collector only:** misses per-file unreadability. |
| 2026-09-04 | Reuse the `1u8nz` breaker constants rather than introduce reap-specific ones. | Two stores at the same seam with two thresholds would be a second thing to reason about with no measured basis for the difference. | **Reap-specific constants:** no evidence they should differ. |
| 2026-09-04 | Neutralise the walk omission at change detection (carry the bookkeeping entry forward, withhold the path from the removal set), in addition to the reap's own classification. | Three consumers delete on the walk-derived removal set ahead of the reap (the incremental Lance write, the layer-hash commit, the secrets ledger), so a guard inside the reap alone cannot keep the rows or the hashes on the first unreadable build, and dropping the bookkeeping entry would make recovery re-hash every file until some other edit ran the build path. One edit point covers all of them and makes recovery a stat-cache hit. | **Filter each consumer separately:** five edits for one condition, and the bookkeeping still forgets the subtree. **Reap-only guard (the plan as written):** proven insufficient by the red test at the build-path seam. |
| 2026-09-04 | The collector is treated as the correctness path for candidates under an unreadable directory, not merely a fast path. | A directory with search-but-no-read permission fails `scandir` while `stat` on its children succeeds, so stat-only classification reads them as `present` and reaps them as a scope departure. | **Stat-only classification:** wrong for that permission shape. |
| 2026-09-04 | Breaker unit is distinct paths per table, for both legs. | The sibling breaker counts `store_rows` as a set of paths; chunk rows would weight large files and make the two thresholds mean different things at one seam. AC-2's "one row" reads as one path. | **Chunk rows:** a different unit from the sibling with no basis for the difference. |
| 2026-09-04 | Accept that a deferred Lance table keeps its stranded rows searchable until the fraction dilutes or the operator rebuilds; the deferral message names `index_build(content='all', mode='rebuild')`. | The same posture the sidecar breaker records, but with a user-visible consequence the sidecars did not have (deleted files can surface in search results after a mass deletion). Flagged for the operator in the plan review rather than asked, because the readied plan already accepts it in Risks. | **No breaker on the Lance reap:** leaves the unmounted-volume case at the zero-change seam unprotected. **A smaller fraction for Lance:** no measured basis. |
| 2026-09-04 | The breaker counts only `absent` candidates; `present` candidates reap whatever their number (delivery review RED-DEL-2). | The breaker exists for transient invisibility, which reads as ENOENT in bulk; a stat-confirmed scope departure is positive evidence of an operator decision, and deferring it kept content the operator excluded searchable for ever. | **Count both classes (as delivered):** an `include_tests` narrowing of ten files deferred indefinitely. **Persisted quarantine of deferred rows with a read-side filter (security seat's alternative):** stronger, not required for this wave, recorded as a follow-on so the repair does not foreclose it. |
| 2026-09-04 | The graph merge receives the walk's unreadable directories and counts their known paths as current (delivery review CODE-DEL-1). | The merge derives its own removal set from the walk, not from `removed`, so the carry-forward did not reach it; adding shadowed paths to the merge's `files` list (the code lane's suggestion) was rejected because the session filters that list through `Path.is_file`, which raises on a genuinely unreadable directory, so it would pass under injection and fail in the field. No builder-version bump: the extractor's output shape is unchanged. | **Re-extract walked-but-unknown paths on recovery (red-team's alternative):** self-healing but re-extracts on every recovery; the preserved rows are correct until a file changes, which recovery already detects. |
| 2026-09-04 | The build result carries `stranded_reap_deferred` and `stranded_reap_preserved` at both seams (SEC-DEL-1); an `index_health` diagnostic is a recorded follow-on. | The envelope is the contract surface of `index_build`, and a control the operator cannot observe is a control they cannot act on; persisting the deferral for `index_health` needs an epoch-free store write and a `server_impl.py` change that belongs to its own change. | **stderr and the store log only (as delivered):** invisible under an MCP-driven build. |
| 2026-09-04 | RED-RV1-1 (a doc re-extracted during the outage loses its link edge into the subtree) is repaired in cycle 2 rather than parked. | The CHANGELOG claims the subtree's edges survive the outage; the fix is a few lines beside the cycle-1 change, pinned by one test, and the same seat reverifies it with the rest of the cycle. The widening reads the store's known paths, not the `files` list, because the session filters that list through `Path.is_file`, which raises on a genuinely unreadable directory. | **Park as maybe_later (both seats' suggestion):** self-heals on the doc's next edit, but leaves a documented claim partly untrue while a repair cycle was running anyway. |
| 2026-09-04 | The envelope decision is qualified (SEC-RV1-1): the build result is the Python `build_index` return value; the registered `index_build` tool returns a spawn acknowledgement and `index_build_status` and `index_health` surface neither state. | Reading `run_index_rebuild`, `index_build_status_response` and `main` showed no registered tool relays the result; the follow-on is parked as plan `1x551` so a planner finds it through `wf_list_plans`. | **Relay the result through `index_build`:** the tool is a detached spawn by design. |
| 2026-09-04 | A shadowed doc is excluded from the merge's impacted-docs rescan rather than read through a guarded stat (ARCH-RV2-1). | Reading it cannot succeed during a real outage, and dropping its record on ENOENT would desync the merge from the store; keeping the stored artifact matches the carry-forward, at the cost of a stale stored artifact until the doc is next re-scanned (a new edge is missed, and the fragment's edge to a removed symbol can be re-emitted by a later merge), which is disclosed. | **Guard the stat and pop the record:** desyncs the merge from the store for the outage. **Persist the skipped set and rescan on recovery:** more machinery than the residual warrants; recorded as a possible follow-on if the stale edge proves visible. |
| 2026-09-04 | The stale symbol edge a preserved doc keeps after a rename during the outage (ARCH-RV3-1: masked for one build, re-emitted with no target node by the next merge until the doc is re-scanned) is recorded in plan `1x5pc`, widened to cover both fragment re-emission variants, rather than repaired here. | It is the merge's pre-existing fragment re-emission behaviour applied to a fragment this wave now keeps; the in-wave alternative (persist the skipped set and rescan on the first readable build) is disproportionate to one dangling edge per affected doc, and the payload-assembly filter that fixes both variants belongs with the removed-doc-path variant. | **Persist and rescan on recovery:** rejected as above. **Prune fragment edges to absent nodes in this wave:** the right fix, but it changes what the merge serves for every removed doc path too and needs its own differential against a full rebuild (plan `1x5pc` AC-2). |


## Risks


| Risk | Mitigation |
| --- | --- |
| Making the reap conservative strands genuinely deleted rows. | AC-4 pins the genuine-deletion path; `absent` still reaps; the `1u8nz` reconciliation is the backstop for anything the conservative reap misses. |
| The breaker defers indefinitely on a legitimately shrunk corpus. | Same accepted posture as `1u8nz`: deferral is loud, repeats each build, and dilutes as newly indexed files enter; the message names the remedy. |
| Injection at the seam does not reflect a real permissions failure. | The seam is the same one `1u8nz` chose for the same reason; a `chmod`-based test is vacuous under root and flaky across platforms. |
| A first-time mass absence with no walk error (an unmounted volume, ENOENT on every path) is deleted by the incremental write at the build-path seam before the reap can defer. | Recorded boundary, not closed here: the write path's `removed` set has no breaker, and adding one changes ordinary deletion semantics for every build. The zero-change preflight is fully guarded; the walk-omission case (the disclosed hazard) is neutralised at change detection. Follow-on candidate for the operator. |
| A full rebuild while a directory is unreadable rebuilds from the current corpus, drops the subtree from bookkeeping, Lance and the graph, and re-embeds it on recovery. | Rebuild semantics pre-exist; the deferral message and the documents ask for the rebuild once every directory and volume is readable again. |
| While a directory is unreadable its subtree is served as of the last readable build, including files since modified or deleted inside it, and a doc inside it keeps its stored artifact, cached mentions and fragment edges included, even when a symbol it mentions changed elsewhere, so a new edge is missed until its next edit and a stale fragment edge can resurface (plan `1x5pc`). | Disclosed in item 15 and the CHANGELOG; the first readable build re-embeds a modified file and drops a deleted one (verified by the security seat's probe). |
| A doc preserved through an outage keeps a `doc_references_code` edge to a symbol renamed during the outage; the next merge for any change serves that edge with no target node until the doc is re-scanned or a full rebuild. | Disclosed in item 15, the retirement paragraph and the CHANGELOG; plan `1x5pc` filters fragment edges to absent nodes at payload assembly. |
| A persistent deferral or preservation is visible in the Python build result, on stderr and in the index-state log, but no registered tool relays it: under an MCP-driven or hook-driven build only the logs show it. | Parked plan `1x551` persists both states epoch-free and reports them through `index_build_status` and `index_health`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
