# Preserve Pruning Across a Failed Upgrade Retry

Change ID: `1w3bs-bug upgrade-retry-pruning-loses-old-manifest`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-22
Wave: `1w047 review-plan-naming`

## Rationale

A downstream `1.17.1` → `1.19.0` upgrade failed safely during Phase 1 surface rendering after pack extraction. The full recovery run correctly skipped re-extraction because the framework tree was already at the target version, but the first failure had deleted the saved pre-upgrade MANIFEST. The retry therefore saved the new MANIFEST as its "old" input, pruning compared new against new, and the retired plan-review seed survived until the operator removed it manually. The recovery path must retain the original diff authority until pruning succeeds.

## Requirements

1. Save the pre-upgrade framework MANIFEST in one repository-local upgrade snapshot before extraction. A recovery run whose framework VERSION already equals the selected pack version reuses that snapshot instead of overwriting it with the installed new MANIFEST.
2. Preserve the snapshot across any failure after extraction begins. Phase 2 must distinguish a nonzero prune exit from a successful zero-deletion prune; retain the snapshot after the former and remove it only after observed prune success. Remove it on a failure proven to occur before framework-tree mutation.
3. Keep pruning diff-based and MANIFEST-scoped: only paths present in the preserved old MANIFEST and absent from the installed new MANIFEST may be deleted.
4. Keep the existing fail-closed Review-plan prompt migration unchanged. Pre-extraction prompt classification and generalized recovery state are outside this repair.

## Scope

**Problem statement:** A post-extraction failure discards the only old-MANIFEST snapshot, so a full at-target retry cannot prune files retired by the selected release.

**In scope:**

- Replace the process-global temporary old-MANIFEST path with one repository-local upgrade snapshot.
- Reuse the snapshot on an at-target retry.
- Preserve/delete the snapshot at the existing failure and successful-prune boundaries.
- Make the Phase 2 prune result expose success separately from its deleted-file count.
- Add a two-attempt regression that reproduces extraction, Phase 1 failure, recovery, and retired-file pruning.

**Out of scope:**

- Changing which files are eligible for MANIFEST-driven pruning.
- Re-extracting an already-at-target framework tree.
- Broadening or guessing project-owned prompt migration.
- General transaction rollback or concurrent-adversary filesystem hardening.

## Acceptance Criteria

- [ ] AC-1: A disposable old-pack tree containing the retired plan-review seed fails after extraction, retains its exact pre-upgrade MANIFEST snapshot, then a full retry against the same target pack skips extraction and still prunes that seed.
- [ ] AC-2: A successful first-attempt upgrade removes the repository-local snapshot immediately after pruning and a pre-mutation failure leaves no snapshot behind; a nonzero Phase 2 prune retains the snapshot, and the next at-target retry uses it to prune the retired seed.
- [ ] AC-3: Pruning still refuses to delete an unmanifested project-created file, and the existing pruning suite remains green.

## Tasks

- [ ] Add one repository-local old-MANIFEST snapshot path and use it in the existing save/prune flow.
- [ ] Make failure cleanup conditional on whether the framework tree was mutated, and make Phase 2 expose prune success separately from the deleted-file count; keep cleanup after observed prune success unconditional.
- [ ] Add the two-attempt failure/retry regression plus pre-mutation, successful-prune, and nonzero-prune snapshot controls.
- [ ] Run warning-strict focused upgrade/pruning tests, the full framework suite, docs validation, and diff check.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Retry-safe snapshot | implementer | — | Small upgrade-orchestrator change; no pruning-policy redesign |
| Recovery regression | qa-reviewer | Retry-safe snapshot | Exercise two complete attempts, not isolated helpers only |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/prune_framework.py`
- `.wavefoundry/framework/scripts/tests/test_prune_framework.py`
- `CHANGELOG.md`

## Affected Architecture Docs

N/A — this repairs persistence at an existing upgrade/pruning seam without changing module ownership or the documented phase order.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Reproduces the field failure and proves the retired file is pruned on recovery. |
| AC-2 | required | Prevents both premature deletion and stale snapshot residue. |
| AC-3 | required | Preserves the pruning safety boundary. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-22 | Planned from a reproduced downstream two-attempt failure. | Direct probe: first prune deleted one retired seed; retry with new-as-old MANIFEST pruned zero and left the seed. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-22 | Use one repository-local snapshot and the existing phase boundaries. | It is the smallest change that survives process failure and avoids cross-repository `/tmp` collisions. | Re-extract on retry risks overwriting recovery edits; storing manifest contents in the JSON lock expands the lock contract; inferring retired files is unsafe. |
| 2026-08-22 | Do not add pre-extraction prompt classification in this change. | The exact migration already fails closed; sharing fresh-pack classification before extraction would add a second execution seam to a narrow pruning repair. | Duplicate the classifier in the extension or build a new shared pre-extract loader. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A stale snapshot could affect a later release. | Reuse only when the installed tree already equals the selected target; otherwise replace it from the current pre-extract MANIFEST, and always remove it after successful pruning. |
| Snapshot cleanup could erase recovery evidence too early. | Tie deletion to the existing `tree_mutated` failure decision and an explicit successful Phase 2 prune result; retain it on nonzero prune exit. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
