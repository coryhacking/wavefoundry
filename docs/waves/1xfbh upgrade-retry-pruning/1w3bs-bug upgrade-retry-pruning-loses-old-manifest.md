# Preserve Pruning Across a Failed Upgrade Retry

Change ID: `1w3bs-bug upgrade-retry-pruning-loses-old-manifest`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-08
Wave: `1xfbh upgrade-retry-pruning`

## Rationale

Brief: make failed-upgrade retries reliable for destination-project operators by retaining the exact original MANIFEST until successful pruning. Preserve MANIFEST-only deletion and extraction idempotence; no general rollback or prompt-migration redesign. Success is a two-attempt upgrade that removes the retired seed and leaves project-created files intact.

A downstream `1.17.1` → `1.19.0` upgrade failed safely during Phase 1 surface rendering after pack extraction. The full recovery run correctly skipped re-extraction because the framework tree was already at the target version, but the first failure had deleted the saved pre-upgrade MANIFEST. The retry therefore saved the new MANIFEST as its "old" input, pruning compared new against new, and the retired plan-review seed survived until the operator removed it manually. The recovery path must retain the original diff authority until pruning succeeds.

## Requirements

1. Save the exact pre-upgrade framework MANIFEST and selected target version in one atomic repository-local snapshot before extraction. Every retry of that target reuses the snapshot even when partial extraction left VERSION old. An unresolved snapshot for a different target causes a visible refusal; complete recovery for its recorded target first.
2. Preserve the snapshot across any failure after extraction begins. Phase 2 must distinguish a nonzero prune exit from a successful zero-deletion prune; retain the snapshot after the former and remove it only after observed prune success. Remove a newly created snapshot on a failure proven to occur before framework-tree mutation. A snapshot inherited from a prior failed attempt is not discarded by a retry that fails before its first new mutation. Mark extraction/surface mutation as begun before invoking writers, so partial failures retain recovery evidence.
3. Keep pruning diff-based and MANIFEST-scoped: only paths present in the preserved old MANIFEST and absent from the installed new MANIFEST may be deleted.
5. Upgrade guidance in seed 160 and its project counterpart SHALL direct unfixed destinations to the staged fresh-runner entry before their first destination mutation, with temporary staging separate from the destination and retries using the same target pack.
4. Keep the existing fail-closed Review-plan prompt migration unchanged. Pre-extraction prompt classification and generalized recovery state are outside this repair.

## Design

Authorized delivery repair (2026-09-08): the operator confirmed 1.22.0 is the intended changelog section and approved completing this wave before local packaging. Scope additionally includes only the two historical changelog test methods in `test_docs_lint.py`: select their owning 1.22.0 section and rename their Unreleased-specific method names, preserving every content assertion. This satisfies the existing verification obligation without changing AC semantics or production behavior.

Use one repository-local JSON snapshot outside the replaced framework directory containing only selected target version and exact UTF-8 MANIFEST text. Reuse matching-target snapshots regardless of installed VERSION. Refuse a different target while the snapshot remains unresolved. Stage its exact MANIFEST bytes into a temporary file only when invoking the existing pruning subprocess; the JSON remains durable authority. Publish the initial snapshot atomically and stop before extraction if it cannot be saved. Keep the manifest bytes exact. A pruning result must distinguish failure/missing runner from successful zero deletion; only successful pruning retires the snapshot. Existing nonfatal prune behavior can remain, but must retain retry authority. Missing/unreadable source or installed MANIFEST and missing prune runner are not proven success; do not delete the snapshot on those paths.

Patch `upgrade_wavefoundry.py` and its existing test file, seed 160 and its project upgrade prompt, plus the Unreleased changelog. Pruning implementation/policy, other seeds/prompts, platform surfaces, and review-policy logic are protected; `prune_framework.py` and its tests are read-only regression references. One implementer owns edits; code, QA, release, and security reviewers inspect. Rehearse real extraction and pruning through the main upgrade path, with unrelated network/index stages isolated. For the first upgrade delivering this fix to an unfixed protocol-2 destination, instructions must stage the new pack in a separate temporary directory and invoke its new `upgrade_wavefoundry.py --root <destination> --pack <pack> --yes` with normal upgrade flags. Never stage by extracting into the destination. Once the runner is installed, ordinary entry points use the fix. Pin this bounded entry through a fresh-process regression against an old target; do not modify the protocol bridge or monkeypatch an old running orchestrator.

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

- [x] AC-1: A disposable old-pack tree containing the retired plan-review seed fails after extraction, retains its exact pre-upgrade MANIFEST snapshot, then a full retry against the same target pack skips extraction and still prunes that seed.
- [x] AC-2: A successful first-attempt upgrade removes the repository-local snapshot immediately after pruning and a pre-mutation failure leaves no snapshot behind; a nonzero or unavailable Phase 2 prune retains the snapshot, and the next at-target retry uses it to prune the retired seed.
- [x] AC-4: Partial extraction replacing MANIFEST but not VERSION, followed by a complete same-target retry, still prunes from the exact original snapshot. Inherited-snapshot failures preserve it, different-target retries refuse without mutation, repositories are isolated, and snapshot-save failure stops before extraction.
- [x] AC-5: Both upgrade instruction carriers name the staged fresh-runner path; a fresh-process old-destination regression proves preservation before first installing mutation and correct pruning on retry, without requiring the installed old runner to reload.
- [x] AC-3: Pruning still refuses to delete an unmanifested project-created file, and the existing pruning suite remains green.

## Tasks

- [x] Add one repository-local old-MANIFEST snapshot path and use it in the existing save/prune flow.
- [x] Make failure cleanup conditional on whether the framework tree was mutated, and make Phase 2 expose prune success separately from the deleted-file count; keep cleanup after observed prune success unconditional.
- [x] Add the two-attempt failure/retry regression plus pre-mutation, successful-prune, and nonzero-prune snapshot controls.
- [x] Exercise partial extraction, inherited-snapshot retry failure, snapshot-write failure, and cross-repository isolation controls.
- [x] Update the user-facing changelog and record the installing-upgrade entry/limitations.
- [x] Run warning-strict focused upgrade/pruning tests, the full framework suite, docs validation, and diff check.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Retry-safe snapshot | implementer | — | Small upgrade-orchestrator change; no pruning-policy redesign |
| Recovery regression | qa-reviewer | Retry-safe snapshot | Exercise two complete attempts, not isolated helpers only |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/prune_framework.py`
- `.wavefoundry/framework/scripts/tests/test_prune_framework.py`
- `CHANGELOG.md`

## Affected Architecture Docs

Upgrade prompt documents the temporary staged-runner entry and bounded persistent snapshot. No module ownership or phase-order change; existing pruning subprocess policy is unchanged.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Reproduces the field failure and proves the retired file is pruned on recovery. |
| AC-2 | required | Prevents both premature deletion and stale snapshot residue. |
| AC-3 | required | Preserves the pruning safety boundary. |
| AC-4 | required | Prevents loss at partial-write/retry boundaries and across repositories. |
| AC-5 | required | Makes the installing upgrade benefit, not only later upgrades. |


## Progress Log

Observe (repair cycle 1 complete): canonical suite PASS, 8,542 tests across 75 files, three reported skips; all 1,096 docs-lint tests pass. QA and release independently recomputed the framework input hash and confirmed the current green receipt; both typed reverifications clear `QA-DEL-VERIFY-1`. All tasks and ACs are complete. The authorized Design amendment requires a new policy receipt with the same lanes and council depth; bounded readiness reconciliation is underway, without additional source edits. The 1w3bs changelog entry remains in 1.22.0.

Observe (repair cycle 1 focused checks): both repaired tests pass warning-strict. Independent QA executed 17 scenarios / 20 test invocations with zero skips/errors; 13 negative controls failed by assertion. Release independently confirmed presence, omission, forbidden-policy, missing-heading, and future-release controls. Each reviewer verified the unchanged repair fingerprint: test_docs_lint.py `eb6c8404979100408e0370500c3f5ba836f1ac52`, CHANGELOG `467bd759087b55b7a8efa0ec57c5a674e200e879`. Framework gate closed; full suite running before final lane clearance.

Readback / Thought (repair cycle 1): keep the existing user-facing 1w3bs entry under 1.22.0. Before, two historical tests errored on an absent Unreleased heading; after, they select the release that owns their announcements and continue detecting missing or contradictory content even when a newer release is added. `QA-DEL-VERIFY-1` repair_start is recorded; operator authorized this bounded two-method edit. Reverify with independent QA/release controls, then run the full suite last.

Observe (delivery review, 2026-09-08): all five required lanes ran on the frozen tree. Code, security, and docs-contract approved; QA and release verified the bounded ACs but withheld delivery approval on shared finding `QA-DEL-VERIFY-1`. Council agrees closure is blocked by the existing changelog-test coupling and stale full-suite receipt. Reviewer reports and mutation evidence are in this wave's existing Review checkpoints and typed ledger. Refined repair recommendation: pin the historical announcements to 1.22.0 rather than whichever release is latest, preserve content assertions, independently verify omission controls, then run the canonical suite last. No source repair, closure, or commit occurred; scope authorization remains pending. Full docs lint and diff check pass.

Observe: canonical full suite ran 8,542 tests across 75 files with three skips; 74 files passed, but test_docs_lint.py had two errors. Existing EvaluatorEditBaselinePolicyPinTests.test_the_unreleased_changelog_states_one_policy and SerializationPointsTokenGrammarPinTests.test_the_unreleased_changelog_announces_the_wave split on `## [Unreleased]`, which the operator's concurrent release-heading edit replaced with `## [1.22.0]`. Full docs lint and diff check pass. No new green full-suite receipt was written. Implementation verification remains incomplete pending an operator decision to expand scope to these two release-sensitive tests. Both edit gates are closed; the release heading is preserved.

Observe (2026-09-08): 11 warning-strict recovery tests pass. Real extraction/pruning through main prove surface-failure retry (no re-extract), partial MANIFEST-before-VERSION retry, failed prune retention, successful and pre-mutation cleanup, inherited failures, target mismatch refusal, repository isolation, atomic-save/lock-setup failures, malformed/symlink snapshot refusal, missing/unreadable prune inputs, and staged fresh-interpreter recovery. All 17 existing pruning tests pass. The staged test invokes the staged main/parser with actual extraction/pruning while isolating unrelated preflight/network/docs/memory/index phases; it is not a complete archive-install test. Upgrade instructions precede normal entry guidance and preserve later lifecycle requirements. The operator's concurrent CHANGELOG heading change to 1.22.0 is preserved.

Mutation controls (in memory, no source edits): overwriting retry authority, clearing partial-write mutation state, treating failed pruning as success, deleting inherited snapshots, allowing another target, and treating a missing runner as success were each killed by a named UpgradeManifestRecoveryTests case. No survivors. Source and test changes are confined to the declared files; prune_framework policy remains unchanged.

| Mutant | Detecting test in UpgradeManifestRecoveryTests |
| --- | --- |
| Overwrite inherited snapshot | test_full_retry_after_surface_failure_skips_extract_and_prunes_original |
| Mark extraction mutation only after the writer returns | test_partial_manifest_write_before_version_then_retry |
| Treat failed pruning as successful zero | test_failed_prune_retains_authority_and_retry_recovers |
| Delete inherited snapshot on pre-mutation failure | test_full_retry_after_surface_failure_skips_extract_and_prunes_original |
| Allow a different pending target | test_pending_different_target_refuses_main_before_extract |
| Treat missing prune runner as successful zero | test_missing_or_unreadable_prune_inputs_never_retire_snapshot |

The first four controls produced missing-required-state errors; the last two produced assertion failures. These are detected regressions, not a claim that every control failed by assertion alone.

Observe: independent implementation checkpoint PASS, no actionable findings. Reviewer reran all 11 recovery tests warning-strict with zero skips, independently detected four recovery mutations, and checked that successful zero-deletion pruning retires the snapshot while preserving unmanifested files. This checkpoint does not replace the pending delivery lanes/council. Thought: run the canonical full suite, then finalize implementation evidence and close edit gates.

Readback: after extraction fails, retry the same target using the exact original MANIFEST even if VERSION remained old. Successful pruning alone retires the snapshot; failure keeps it. Only old-manifest-listed retired files may be removed. AC-1 through AC-5 govern source/test changes and staged-runner guidance. Thought: implement snapshot/prune boundaries, add two-attempt main-path and fresh-process tests, merge upgrade instructions, then focused and full verification.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-08 | Primer found old-runner installing window and VERSION-lagging partial extraction. Revised Requirements/Design/AC-4/5 before readiness: target-bound atomic snapshot, pending-other-target refusal, staged new-runner instructions and subprocess proof. | Primer 1w3bs_primer; no code edits. |
| 2026-08-22 | Planned from a reproduced downstream two-attempt failure. | Direct probe: first prune deleted one retired seed; retry with new-as-old MANIFEST pruned zero and left the seed. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-08 | Retain the existing repository-local snapshot design; explicitly cover partial mutation and inherited retry state. | A two-field local atomic snapshot is the smallest durable authority; general recovery-state redesign or re-extraction on an already-at-target tree broadens the repair and risks project changes. | Re-extract on retry; general transaction journal. |
| 2026-08-22 | Use one repository-local snapshot and the existing phase boundaries. | It is the smallest change that survives process failure and avoids cross-repository `/tmp` collisions. | Re-extract on retry risks overwriting recovery edits; storing manifest contents in the JSON lock expands the lock contract; inferring retired files is unsafe. |
| 2026-08-22 | Do not add pre-extraction prompt classification in this change. | The exact migration already fails closed; sharing fresh-pack classification before extraction would add a second execution seam to a narrow pruning repair. | Duplicate the classifier in the extension or build a new shared pre-extract loader. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A stale snapshot could affect a later release. | Bind the snapshot to the selected target, reuse for that target even if VERSION is old, refuse another target until recovery completes, and remove only after observed pruning success. |
| Snapshot cleanup could erase recovery evidence too early. | Tie deletion to the existing `tree_mutated` failure decision and an explicit successful Phase 2 prune result; retain it on nonzero prune exit. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
