# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zim5 profile-portable-test-suite`
Title: Profile Portable Test Suite

## Objective

Make the framework test suite verify a distribution's own vocabulary, layout profile and tool declarations: profile-aware fixture builders, a default-profile-only marker for tests whose subject is the default, an on-demand second-profile run, and a suite that stays meaningful with declarations present.

## Changes

Change ID: `1zim1-debt profile-portable-test-fixtures`
Change Status: `implemented`

Change ID: `1zim4-debt suite-under-distribution-declarations`
Change Status: `implemented`
Depends On: `1zim1-debt profile-portable-test-fixtures`

Change ID: `1zim6-debt migrate-tests-to-profile-builders`
Change Status: `implemented`
Depends On: `1zim1-debt profile-portable-test-fixtures`

Change ID: `1zim7-bug archive-root-left-untouched`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zim5` (Profile Portable Test Suite) delivered 4 changes: Test Infrastructure for Running the Suite Under a Vocabulary and Layout Profile, The Framework Test Suite Runs With a Distribution's Tool Declarations, Migrate the Framework Tests to Profile-Aware Fixtures, and The Read-Only Archive Root Is Never Rewritten or Reported as Live. Notable adjustments during implementation: Test Infrastructure for Running the Suite Under a Vocabulary and Layout Profile: DEL-1ZIM5-PROFILE-SYMLINK-WRITE reverification follow-ups (coordinator): the independent reverifier confirmed the repair (end-to-end runs with tracked symlinks to outside targets left them byte-identical) and found one residual path of the same class: `_copy_listed_tree` itself could copy a listed file through a tracked directory replaced on disk by a relative symlink, landing outside the copy. Now a listed file beneath a directory the copy already holds as a symlink is skipped (`_beneath_copied_symlink`), since the link carries what the working tree shows. Tests: `test_the_copy_never_writes_through_a_directory_replaced_by_a_link` (fails with the skip removed: the file landed in the outside directory) and `test_a_sibling_that_shares_the_root_prefix_is_outside` (fails when confinement is a string prefix check). Both mutations run in a scratch framework copy; Test Infrastructure for Running the Suite Under a Vocabulary and Layout Profile: Delivery-review repairs. CR-1: the run's temporary tree is removed with a read-only retry (entry and parent made writable; git objects are read-only on Windows) on every exit; SIGTERM raises an interrupt during the run (not on Windows) and the previous handler is restored; on any exit the copy's runner group is ended and reaped before removal; the child runner gets no `GIT_*` variables and runs in its own process group; temp-repository git commands pass `gc.auto=0` and `maintenance.auto=false`; malformed `--file` selectors are refused before copying. Red-team: the canonical-tree refusal test patches `SCRIPTS_DIR` to a copy, so it can never write the repository. QA: `test_loaded_constants_are_shipped_or_a_declared_profile` (loaded constants equal `SHIPPED_DEFAULTS` or it overlaid with an asset in `tests/fixtures/profiles/`); tests for the receipt-change check, `GIT_*` stripping, every loaded module copy, back-reference localization; the method-form marker now skips before `setUp`. `apply_profile` keeps CRLF line endings. The localized fixture's README follows the profile. New helpers `localize_record_text` (used by the fixture), `waves_dir`, `waves_rel`, `declared_profile_match`. Testing-architecture: plan count dropped, a distribution adds its asset, cleanup described. `test_tree_kill_routing` pin renamed to the git loop's new enclosing function `_profile_run_in`. 13 scratch-copy mutations each failed the new tests (the SIGTERM one killed the test process); the gc and maintenance flags have no test; Test Infrastructure for Running the Suite Under a Vocabulary and Layout Profile: Second-profile run against the real tree (`run_tests.py --profile second`, all 147 files, 3,160 files copied): 1,429 failures and errors in 44 of 147 files (103 passed, 34 skipped), copy of the tree at this change's implementation. Largest: `test_docs_lint` 750 (732 failures, 18 errors), `test_server_tools_lifecycle` 299, `test_dashboard_server` 104, `test_server_context_efficiency` 37, `test_server_tools` 22, `test_lifecycle_gates` 20, `test_memory_records` 19, `test_record_paths` 14, `test_review_evidence` 14, `test_upgrade_wavefoundry` 13, `test_review_policy` 12, `test_dashboard_terminology` 8, `test_phase_gates` 8, `test_server_tools_retrieval` 8, `test_vocabulary_profile` 8, `test_archive_root` 7, `test_indexer` 7; 27 more files with 1 to 6 each. 12 of the 1,429 were this change's own two files, which built from the running tree rather than the shipped defaults; fixed (copies now reset to the shipped defaults first) and both files pass under the profile run, so the migration scope is 1,417 in 42 files. This tree's receipt was byte-identical before and after (SHA-1 `f230d8a3`). Separately, this repository's own documents do not lint clean under the profile (12 plans in the default vocabulary lack `Member ID:`; the prompt-surface manifest names `docs/waves/`).

**Changes delivered:**

- **Test Infrastructure for Running the Suite Under a Vocabulary and Layout Profile** (`1zim1-debt profile-portable-test-fixtures`) — 6 ACs completed. Key decisions: Split infrastructure from migration; Full git-tracked copy for the run
- **The Framework Test Suite Runs With a Distribution's Tool Declarations** (`1zim4-debt suite-under-distribution-declarations`) — 3 ACs completed. Key decisions: Separate from `1zim1`
- **Migrate the Framework Tests to Profile-Aware Fixtures** (`1zim6-debt migrate-tests-to-profile-builders`) — 6 ACs completed. Key decisions: Scope from a fresh measurement with the shared asset
- **The Read-Only Archive Root Is Never Rewritten or Reported as Live** (`1zim7-bug archive-root-left-untouched`) — 4 ACs completed. Key decisions: Fix inside wave 1zim5 rather than leave the two tests failing; Leave retrieval treatment of archived records out of scope
## Watchpoints

- Watchpoint: large mechanical migration; builders and runner first, then file groups in census order with one owner per file.
- Follow-up: `1zim4` uses `1zim1`'s runner mode; its parameter-mapped sample waits for `1zim0`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZIM5-CANONICAL-TREE-TEST | do_now | no | completed | qa-reviewer, wave-council-delivery |
| DEL-1ZIM5-PROFILE-RUN-CLEANUP | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| DEL-1ZIM5-PROFILE-SYMLINK-WRITE | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| DEL-1ZIM5-SNAPSHOT-GUARD | do_now | no | completed | qa-reviewer, wave-council-delivery |
| DEL-1ZIM5-STALE-PLAN-COUNT | do_now | no | completed | docs-contract-reviewer, wave-council-delivery |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the census measured a full git clone while the plan built a minimal scaffold, and two ACs could not pass as written; resolved by a full-tree git copy, reworded ACs and splitting infrastructure (1zim1) from migration (1zim6); strongest-alternative: parametrize every test over profiles, rejected because it doubles runtime and hides default-subject pins)
- Prepare council seat evidence (2026-10-01): red-team blocked 1zim1 round 1, approved all three changes round 2; docs-contract seat approved, noting the testing-architecture text must say whether the second-profile run lints this repository's own documents. Lanes approved round 1 and re-approved the revised docs in round 2, with an upstream declarations measurement (22 failures in 6 of 8 sampled files). Reviewer models: requested opus for every seat and lane; the census agent used sonnet (bounded measurement); observed runtime identity unknown.
- Readiness for late-admitted `1zim7-bug archive-root-left-untouched` (2026-10-01): independent red-team seat and code, qa, architecture and docs-contract lanes approved after reproducing both defects under the second profile and checking every other walk that could reach the archive root; their AC and scope wording (default-profile tests with a patched archive root as delivery evidence, the memory-root branch decided first, `docs/agents/**` walks out of scope) applied verbatim. Strongest alternative (one shared under-archive predicate in `record_paths`) noted for the implementer as optional. The other three changes' documents are unchanged since their readiness approvals. Reviewer model: requested opus; observed runtime identity unknown.
- **Delivery Wave Council [delivery-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the snapshot and ships-empty guards accept any committed profile asset in the canonical tree, so the suite cannot tell a canonical repo accidentally left on a sample profile from a profile run (narrow, exact-match only, docs-lint backstops the record profile but nothing backstops declarations); left as an operator follow-up with the fix named (the run mode records its active profile and the guards require it); strongest-alternative: parametrize every test over profiles, rejected at planning because it doubles runtime and hides default-subject pins)
- Delivery seat evidence (2026-10-01): 1zim1 round 1 raised four findings (temp-repo cleanup on Windows and SIGTERM, a refusal test that could write the real tree, no value-level snapshot guard, a stale count), all repaired and independently reverified by real runs and mutations. The migration found two production defects (archived records rewritten by the memory id migration and reported by the review-policy preflight), fixed in late-admitted 1zim7 with default-profile tests. Whole-suite results: default 10319 OK (16 skips), `--profile second` 0 of 149 files failed with every extra skip a default-only marker, `--profile declared` 0 of 149 failed. Advisories for the operator: the run mode should name its active profile; a second SIGTERM or SIGHUP during cleanup can leak the temp tree; a non-file runner failure is reported as 0 files failed; the census misses `Path("docs") / "waves"` and concatenation; the checklist's extra-skip rule is not visible in the run output; archived records are not demoted in retrieval (1z827 left this open). Reviewer models: requested opus for every implementer, reviewer and seat; observed runtime identity unknown.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 32 | 84,026 |
| implement | 26 | 1,580,923 |
| review | 45 | 743,635 |
| **Total** | **103** | **2,408,584** |

<!-- wave:context-efficiency-state {"generation":107,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":26,"content_source_credit":1614479,"derived_artifact_credit":1147,"direct_net":1580923,"estimated_tokens_saved":1580923,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":837,"response_debit":35040,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1174},"plan":{"calls":32,"content_source_credit":114891,"derived_artifact_credit":2912,"direct_net":84026,"estimated_tokens_saved":84026,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5659,"response_debit":34629,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":45,"content_source_credit":863212,"derived_artifact_credit":3376,"direct_net":743635,"estimated_tokens_saved":743635,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12865,"response_debit":112404,"source_credit_count":63,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":103,"content_source_credit":2592582,"derived_artifact_credit":7435,"direct_net":2408584,"estimated_tokens_saved":2408584,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19361,"response_debit":182073,"source_credit_count":122,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10001},"wave_id":"1zim5 profile-portable-test-suite"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 7 | 3,660,345 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":3660345,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
