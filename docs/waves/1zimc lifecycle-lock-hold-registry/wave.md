# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zimc lifecycle-lock-hold-registry`
Title: Lifecycle Lock Hold Registry

## Objective

Lifecycle-lock holds register in the in-process holder registry, so re-entering the lock in the same process is refused and the publication lock's lifecycle probe never opens the lock file while this process holds it; a second process can no longer take the lifecycle lock while its owner is still mutating.

## Changes

Change ID: `1zimg-bug lifecycle-lock-holds-survive-reentry-and-probe`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zimc` (Lifecycle Lock Hold Registry) delivered one change: Lifecycle Lock Holds Survive Re-entry and the Publication Probe. Notable adjustments during implementation: Lifecycle Lock Holds Survive Re-entry and the Publication Probe: Requirement 9 / AC-11 implemented and met (boxes left for the coordinator to mark), resolving the secrets-scan residual recorded in Risks. New `secrets_validators.is_wavefoundry_lock_path` (everything under `.wavefoundry/locks/` and every `.wavefoundry/**/*.lock`, case-insensitive, `/` separators) is applied before any read in the `git ls-files` branch, the rglob fallback (inside and outside a git worktree), the `_get_changed_files` loop and an explicit `files=` list, and a recorded finding for such a file is swept like the allowlist sweep; scan-rules hash and `SCANNER_VERSION` unchanged. Tests written first failed on the unmodified scanner (outside git a second process acquired the lifecycle lock after the in-process scan); `test_secret_scan_cache` git-branch expectations updated for the two lock paths it pinned as candidates. Full suite 10386 tests OK; each exclusion branch, the `files=` filter, the sweep and case folding removed in a scratch copy fails a named test; Lifecycle Lock Holds Survive Re-entry and the Publication Probe: Repair round for DEL-1ZIMC-UNPINNED-GUARD-MECHANISMS, test-only: four mutations survived the focused file, so four tests now pin the mechanisms they removed. The in-guard re-entry re-check (two threads held past the up-front check by a barrier; one acquires, the other is refused), the thread test of the own-publication refusal (another thread's transaction hold gets the ordinary busy refusal), registration under the guard before the metadata write, and the probe's open under the guard. In a scratch copy all twelve mutations (M1 to M12) now fail named tests in the 45-test file; full suite 10377 tests OK. CHANGELOG bullet now names the two intended behaviour changes (cross-thread publication wait fails fast; Windows lifecycle holder waits).

**Changes delivered:**

- **Lifecycle Lock Holds Survive Re-entry and the Publication Probe** (`1zimg-bug lifecycle-lock-holds-survive-reentry-and-probe`) — 11 ACs completed. Key decisions: Keep the lifecycle lock on process-owned record locks and add the registry, rather than switching it to `flock`; Refuse re-entry (raise `LifecycleLockBusy`) rather than count it
## Watchpoints

- Watchpoint: nothing from this wave is committed or pushed until the operator says; the fix and its notes are published together.
- Watchpoint: write the multi-process regression tests first and record their failure on the current code before changing the lock.
- Watchpoint: mutation checks run in a scratch copy of the tree, never in the working tree.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZIMC-SECRETS-FALLBACK-OPENS-LOCK | dont_do_later | no | not_required | — |
| DEL-1ZIMC-UNPINNED-GUARD-MECHANISMS | do_now | no | completed | — |

*Machine review state — 2 findings; current: do_now 1, maybe_later 0, dont_do_later 1, not_issue 0*
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
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the registry protects only code that consults it, so any unregistered in-process open and close of the lifecycle lock file (a generic walker, an extension module, a forked child trusting an inherited entry) still drops the hold on POSIX; implementation records walker exclusion evidence; strongest-alternative: make the lock immune at the mechanism level with flock or a dedicated holder handle, rejected because the bridge and older installed runtimes take it as a record lock at the same offset and flock and record locks do not exclude each other during a mixed-version upgrade)
- Prepare council seat evidence (2026-10-01): one independent Opus reviewer ran both seats and the code, qa, architecture and security lanes, with real-process probes against the live tree on macOS: re-entry, the publication probe and the transaction self-deadlock all reproduce; no shipped path re-enters the lifecycle lock (middleware serialized on the event loop, core_handler unwrapped, setup and upgrade in separate processes); MCP reload keeps one runtime_lock registry. No blockers; its edits R1-R9 (POSIX-only deadlock scope, check ordering, release ordering, registration-interrupt AC, spawn-only child processes, census literals, suite list, flock decision, security lane) were applied verbatim.

- **Delivery Wave Council [delivery-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the registry is cooperative, so any in-process opener that does not consult it still drops a POSIX hold; the one live example, the secrets scan, now excludes every .wavefoundry lock file at every selection path, and safety otherwise rests on sync tools being serialized; strongest-alternative: use F_OFD_SETLK on Linux so ownership moves to the open file description, keeping the registry only for macOS; recorded as a possible follow-up)
- Delivery seat evidence (2026-10-01): one independent Opus reviewer reproduced both advisory scenarios and the transaction self-deadlock with fresh-interpreter processes before and after the fix; found four unpinned mechanisms (repaired with tests and reverified: M1-M12 all killed), the secrets-scan fallback opener (fixed in this wave by operator direction, Requirement 9; the hold now survives scans outside git, in git without ignore lines and with lock files force-tracked; mutants S1-S6 and X1-X4 killed) and a sweep-scope test gap (fixed). Full suite 10386 OK.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 38 | 597,414 |
| implement | 32 | 89,664 |
| review | 64 | 779,891 |
| **Total** | **134** | **1,466,969** |

<!-- wave:context-efficiency-state {"generation":95,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":32,"content_source_credit":103487,"derived_artifact_credit":0,"direct_net":89664,"estimated_tokens_saved":89664,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4328,"response_debit":12015,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2520},"plan":{"calls":38,"content_source_credit":656426,"derived_artifact_credit":2669,"direct_net":597414,"estimated_tokens_saved":597414,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3631,"response_debit":69965,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11915},"review":{"calls":64,"content_source_credit":930642,"derived_artifact_credit":4143,"direct_net":779891,"estimated_tokens_saved":779891,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8708,"response_debit":148502,"source_credit_count":62,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":134,"content_source_credit":1690555,"derived_artifact_credit":6812,"direct_net":1466969,"estimated_tokens_saved":1466969,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16667,"response_debit":230482,"source_credit_count":129,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":16751},"wave_id":"1zimc lifecycle-lock-hold-registry"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 643,483 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":643483,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
