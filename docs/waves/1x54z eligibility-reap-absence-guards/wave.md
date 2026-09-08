# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1x54z eligibility-reap-absence-guards`
Title: Eligibility Reap Absence Guards

## Objective

Stop a transiently unreadable subtree from silently destroying its own index state. The shipped Lance eligibility reap trusts a walk that drops unreadable directories without a word, so a permissions incident, an unmounted volume, or a sandbox restriction reaps the subtree's rows, drops its layer hashes, and forces a full re-embed on recovery. The protections already exist for the sibling reconciliation at the same seam; this wave gives the reap the same absence classification and mass-removal breaker. Disclosed 2026-08-01 and deferred twice; not deferred a third time.

## Changes

Change ID: `1u8o3-debt eligibility-reap-mass-removal-hazard`
Change Status: `implementing`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Product-owner admission review: operator-approved on 2026-09-04 by the instruction to open the next wave after `1u8o3` was recommended as the immediate follow-up to `1x4ol`.

Completed At: 2026-09-04

## Wave Summary

Wave `1x54z` (Eligibility Reap Absence Guards) delivered one change: Shipped Eligibility Reap Lacks the Mass-Removal Protections Its Sibling Now Has. Notable adjustments during implementation: Shipped Eligibility Reap Lacks the Mass-Removal Protections Its Sibling Now Has: Filed as the close-surviving record of the hazard disclosed and deliberately descoped during wave 1u8o2 (architecture lane prepare P3 and delivery P3-4; code lane concurrence).; Shipped Eligibility Reap Lacks the Mass-Removal Protections Its Sibling Now Has: Plan review (Review plan, batch): every branch in Requirements, ACs and Scope self-answered from the tree; one operator-visible consequence flagged rather than asked (the Lance breaker keeps deferred rows searchable, unlike the sidecar breaker). Self-answers: breaker unit is distinct paths per table, the unit `_plan_orphan_store_reconcile` already counts; both guards live in the reap's scanning branch, which is what the zero-change preflight and the build-path seam run, and the zero-change execute replays `paths_by_table` so it cannot reap what the plan refused; the collector is a keyword-only out-parameter on `walk_repo` so its 13 call sites (three in the indexer, five archived evidence scripts, tests) keep their contract; the collector is load-bearing, not a fast path, because a search-but-no-read directory fails `scandir` while `stat` on its children succeeds. Follow-on candidates recorded, not folded in: the graph merge's walk-parity prune and the secrets ledger's removal handling see the same walk omission.; Shipped Eligibility Reap Lacks the Mass-Removal Protections Its Sibling Now Has: Gapfill: range-scoped `awk`/`sed` reads of `_build_index_locked` (a 1,400-line function) for the `removed` consumers and the bookkeeping construction, after `code_keyword` located the anchors; `code_read`, `code_definition`, `code_references` and `code_keyword` carried the rest of the investigation.

**Changes delivered:**

- **Shipped Eligibility Reap Lacks the Mass-Removal Protections Its Sibling Now Has** (`1u8o3-debt eligibility-reap-mass-removal-hazard`) — 7 ACs completed. Key decisions: Surface the walk's omissions through an `onerror` collector AND classify at the stat seam, rather than either alone.; Reuse the `1u8nz` breaker constants rather than introduce reap-specific ones.
## Watchpoints

- **Watchpoint: a conservative reap must not strand genuine deletions.** `absent` (`ENOENT`/`ENOTDIR`) and `present`-but-out-of-scope both keep reaping; only `unreadable` preserves. AC-4 pins the unchanged paths before anything else lands.
- **Red first.** The loss is demonstrated with injection at the stat seam before the reap is touched, so the fix is judged against a reproduced failure rather than a described one.
- **Inject at the seam, never `chmod`.** A permissions-based test is vacuous under root and flaky across platforms; `_orphan_path_stat` and the new `onerror` collector are the injection points.
- **Both seams or neither.** The reap runs at the zero-change preflight and at the build path; a protection that lands at one seam leaves the hazard reachable from the other.
- **Follow-up boundary: the guard-skip visibility gap in the secrets scanner (`1x4om`) stays parked and is not folded in here.**
- **Same constants as `1u8nz`.** Two thresholds at one seam with no measured basis for the difference is a second thing to reason about; the breaker reuses `ORPHAN_RECONCILE_BREAKER_FRACTION` and `ORPHAN_RECONCILE_BREAKER_MIN_ROWS`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | do_now | no | completed | — |
| ARCH-DEL-2 | do_now | no | completed | — |
| ARCH-DEL-3 | do_now | no | completed | — |
| ARCH-DEL-4 | not_issue | no | not_required | — |
| ARCH-RV1-1 | do_now | no | completed | — |
| ARCH-RV1-2 | do_now | no | completed | — |
| ARCH-RV1-3 | do_now | no | completed | — |
| ARCH-RV2-1 | do_now | no | completed | — |
| ARCH-RV3-1 | dont_do_later | no | not_required | — |
| ARCH-RV3-2 | do_now | no | completed | — |
| CODE-DEL-1 | do_now | no | completed | — |
| CODE-DEL-2 | do_now | no | completed | — |
| CODE-DEL-3 | do_now | no | completed | — |
| CODE-RV1-1 | do_now | no | completed | — |
| CODE-RV2-1 | do_now | no | completed | — |
| QA-DEL-1 | do_now | no | completed | — |
| QA-DEL-2 | do_now | no | completed | — |
| QA-DEL-3 | do_now | no | completed | — |
| QA-DEL-4 | do_now | no | completed | — |
| QA-DEL-5 | do_now | no | completed | — |
| QA-DEL-6 | do_now | no | completed | — |
| QA-DEL-7 | dont_do_later | no | not_required | — |
| QA-RV1-1 | do_now | no | completed | — |
| QA-RV3-1 | do_now | no | completed | — |
| RED-DEL-1 | do_now | no | completed | — |
| RED-DEL-2 | do_now | no | completed | — |
| RED-DEL-3 | maybe_later | no | completed | — |
| RED-DEL-4 | do_now | no | completed | — |
| RED-RV1-1 | maybe_later | no | completed | — |
| RED-RV2-1 | dont_do_later | no | not_required | — |
| SEC-DEL-1 | do_now | no | completed | — |
| SEC-DEL-2 | do_now | no | completed | — |
| SEC-DEL-3 | dont_do_later | no | not_required | — |
| SEC-RV1-1 | do_now | no | completed | — |

*Machine review state — 34 findings; current: do_now 27, maybe_later 2, dont_do_later 4, not_issue 1*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Follows the `1u8nz` orphan-store reconciliation (landed in wave `1u8o2`), whose classification seam and breaker this wave reuses rather than duplicates.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the plan's mechanism rests on a claim about the standard library rather than this codebase, that `os.walk` drops an unreadable directory silently while a per-file permission error is loud, and a plan built on the wrong half of that would guard the wrong seam; both halves were reproduced by injection before approval; strongest-alternative: classify only at the stat seam and leave the walk silent, rejected because it stats every stranded candidate under an unreadable parent and leaves the operator with no signal that a subtree vanished from the corpus)
  - red-team seat: the mechanism was reproduced, not read. With `os.scandir` injected to raise `EACCES` for one directory, `os.walk` under the default `onerror=None` yields the parent and its readable sibling and omits the locked directory with no error; with `os.stat` injected to raise `EACCES` for one file, `Path.is_file()` on Python 3.13.5 raises rather than returning `False`, so the per-file case crashes the walk loudly and the directory case is the silent hazard the plan targets. Every symbol the plan cites resolves: `walk_repo`, `_reap_stranded_lance_rows` (with `plan_only`), `_cleanup_layer_state_for_reaped`, `_classify_orphan_path`, `_orphan_path_stat`, `_store_log_safe`, `ORPHAN_RECONCILE_BREAKER_FRACTION` 0.5 and `ORPHAN_RECONCILE_BREAKER_MIN_ROWS` 8; the reap runs at the zero-change preflight/execute seam and at the build-path seam, each followed by `_plan_orphan_store_reconcile`. The sibling's own tests (`test_enoent_removes_unreadable_preserves`, `test_mass_removal_circuit_breaker_defers_with_log`) already inject at `_orphan_path_stat`, so the plan's injection method has precedent in this suite. No findings.
  - security-reviewer seat: the change moves the reap in the conservative direction only. `absent` and `present` keep reaping, so scope narrowing and genuine deletion behave as today and AC-4 pins them; only `unreadable` preserves, and preserving rows together with their layer hashes is a consistent state (the sibling reconciliation makes the same choice). The breaker's deferral is loud through `_store_log_safe` and repeats each build, the accepted `1u8nz` posture. The one integrity risk, a conservative reap stranding rows that should go, is covered by the pinned paths and by the reconciliation backstop. No findings.
  - Plan repairs made before this verdict, not raised as findings because they were fixed on admission: line-number anchors from the 2026-08-01 filing replaced with symbols; AC Priority populated before the council rather than at Prepare; review targets declared in block form; AC-3 reworded from a repository-wide suite claim to the local form; Requirement 4 resolved with a recorded decision and a Decision Log seeded.
- **Delivery-phase Wave Council [delivery-council] — 2026-09-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; lanes: code-reviewer, qa-reviewer, architecture-reviewer; cycles: initial delivery on tree `9cda3df7e86be742` with 21 findings, repair cycle 1 and reverification on `18fce6098ed81741`, repair cycle 2 and reverification on `b76b94ce414dcc1e`, repair cycle 3 and reverification on `6d7036e928850830`, two prose repairs reverified after it; 34 findings, every actionable one repaired and reverified by its own lane in fresh context, four parked with plans; strongest-challenge: the graph merge derives its own removal set from the walk, so the cycle-1 carry-forward left the shadowed subtree pruned and never restored, and under a real mode-000 outage the merge's impacted-docs rescan crashed every build, neither reachable by the class's scandir-only injection; strongest-alternative: a persisted quarantine of deferred and preserved rows with a read-side filter and a skipped-set rescan on recovery, rejected as disproportionate to the residuals, which are disclosed and parked in plans `1x551`, `1x5pc` and `1x550`; disagreements: none between seats or lanes on the final tree)
  - red-team seat: on the cycle-2 tree all four RED-DEL findings reproduced as fixed against a pre-wave control rebuilt from HEAD and eight further break attempts held (nested unreadable directory, files created or deleted inside during the outage, true orphans retired beside a shadowed subtree, full-rebuild parity, `files_shadowed` never persisted, mixed present and absent strands, a path in both tables); RED-RV1-1 (link edges from an outside doc edited during the outage) was repaired in cycle 2 and reverified with the pre-wave control still losing both edges; RED-RV2-1 (a dangling doc-link edge after a linked doc is deleted) is pre-existing, identical on HEAD, and parked as plan `1x5pc`. Supports delivery.
  - security-reviewer seat: every confidentiality shape (ignore rule, `include_tests` narrowing) reaps immediately and never defers; the envelope fields carry counts only; the cycle-2 widening admits store-known paths only (a ghost link mints nothing) and a gitignored-but-known path is served as of the last readable build in parity with the carry-forward; SEC-RV1-1 established that no registered tool relays the build result, recorded in item 15 and plan `1x551`. Residual risk: deferral and preservation are log-only under MCP or hook builds until `1x551` lands. Supports delivery.
  - the cycle-3 delta (the impacted-docs skip, its faithful mode-000 test, the edge-oracle fix) was reverified by the architecture lane with a real chmod probe, by the code lane with the interpreter's own `Path.exists` semantics, and by the QA lane's re-established approval evidence; the seats' positions were taken on the cycle-2 tree and the delta lies inside the architecture lane's remit.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 32 | 560 |
| implement | 100 | 184,532 |
| review | 664 | 8,049,798 |
| **Total** | **796** | **8,234,890** |

<!-- wave:context-efficiency-state {"generation":804,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":100,"content_source_credit":271037,"derived_artifact_credit":478,"direct_net":184532,"estimated_tokens_saved":184532,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4717,"response_debit":84845,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2579},"plan":{"calls":32,"content_source_credit":29403,"derived_artifact_credit":1067,"direct_net":560,"estimated_tokens_saved":560,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6133,"response_debit":33853,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10076},"review":{"calls":664,"content_source_credit":9491876,"derived_artifact_credit":5345,"direct_net":8049798,"estimated_tokens_saved":8049798,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":114128,"response_debit":1335184,"source_credit_count":332,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":796,"content_source_credit":9792316,"derived_artifact_credit":6890,"direct_net":8234890,"estimated_tokens_saved":8234890,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":124978,"response_debit":1453882,"source_credit_count":377,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14544},"wave_id":"1x54z eligibility-reap-absence-guards"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 19 | 0 | 8 | 6,964,875 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":6964875,"surfaced_events":19} -->
<!-- wave:exploration-avoided end -->
