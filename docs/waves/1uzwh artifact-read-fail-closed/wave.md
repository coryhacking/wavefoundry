# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uzwh artifact-read-fail-closed`
Title: Artifact Read Fail Closed

## Objective

Close the fail-open siblings wave `1uwpf` disclosed but declared out of scope: an undecodable `wave.md` crashes all eight probed lifecycle tools (including both recovery tools), a missing admitted change document passes the close hard gate while the summary fabricates an empty record of it, and the rollback double-fault path re-leaks the absolute paths `1uu9z`'s helper exists to strip. All three extend contracts `1uwpf` shipped and six lanes verified; every premise was executed against the tree before these plans were written.

## Changes

Change ID: `1v0lw-bug wave-record-reads-crash-every-lifecycle-tool`
Change Status: `implemented`

Change ID: `1v0lx-bug close-gate-silently-passes-a-missing-admitted-doc`
Change Status: `implemented`

Change ID: `1v0ly-bug rollback-failure-detail-embeds-absolute-paths`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-11

## Wave Summary

Wave `1uzwh` (Artifact Read Fail Closed) delivered 3 changes: An Undecodable Wave Record Crashes Every Lifecycle Tool, The Close Hard Gate Silently Passes A Missing Admitted Document, and Rollback-Failure Detail Embeds Absolute Paths That Defeat The Leak Helper. Notable adjustments during implementation: An Undecodable Wave Record Crashes Every Lifecycle Tool: Readiness council (red-team and docs-contract seats): plan repaired pre-receipt. The "no read-failure handling" claim was falsified (the resolution path swallows `OSError` and misreports `wave_not_found`), and AC-2's single-exception red-first contract was unsatisfiable for the permission cause. Requirement 5 and AC-9 added; AC-2 and AC-5 rewritten with per-cause, per-site-class expectations; `wf_mark_task` added to the probe matrix; An Undecodable Wave Record Crashes Every Lifecycle Tool: AC-1 census (implementer, by RESOLVED TARGET, pre-edit): 119 `read_text` sites in `server_impl.py`; 26 reach `wave.md`. The receiver-name key finds 24; resolution adds L7490 (`contained_wave`, produced by `_contained_wave_review_paths`) and L16884 (`_wave_has_gapfill_note`, mixed-target `*.md` loop that includes `wave.md`), and excludes one name-era false positive (L5503 `_detect_wave_status_drift` skips `wave.md` explicitly and reads change docs). Dispositions: (a) shared parse helper L2847 `_parse_wave_record` rebuilt on the seam as `_read_wave_record` (readable payload unchanged, degraded record with `read_error` on failure; covers `wf_list_waves`, `wf_current_wave`, cache, `_review_evidence_cost_focus`); (b) resolution sites L6078 `_wave_match_payload` plus the `_resolve_wave_md_matches` loop stop swallowing `OSError` and carry `read_error` / skipped-candidate payloads (Requirement 5); (c) 15 decision/mutation boundary reads across 12 tool bodies refuse via the seam with `wave_record_unreadable`: L5719 get_change-bulk, L6413 mark refresh re-read, L7701 create_wave, L7830 add_change, L8003 remove_change, L15403+L15512 review_event, L15859+L15976+L16270 prepare, L16312 pause, L16556 review_wave, L16950 implement, L17470 close, L17673 reopen; (d) mid-transaction re-read L7490 raises a sanitized ValueError into the existing structured handlers; (e) 8 internal consumers degrade via the seam preserving current shape, extended to the decode cause: L14821 (False), L14855 (sanitized detail), L15224 (list sub-path diagnostic, ok envelope), L16799 (None), L16884 (continue), L25542 (empty checkpoint), L25572/L25682 (persistence failed); (f) resource readers L30858/L30869 (`_validated_wave_markdown`) stay out of scope per Scope and are allowlisted by the residue test; An Undecodable Wave Record Crashes Every Lifecycle Tool: Implemented (implementer lane). Seam: `_read_wave_record_text(wave_md) -> (text, read_error)` is the sole raw-read boundary; `_read_wave_record(root, wave_md)` replaces `_parse_wave_record` (readable payload byte-identical, degraded record with `read_error` on failure); resolution returns `(matches, unreadable)` and `_find_wave_md_detailed` adds the requested-record read_error plus skipped siblings. Twelve by-id tools plus `create_wave` refuse with `wave_record_unreadable`; `wf_list_waves`/`wf_current_wave` degrade per entry including the only-unreadable-wave case; eight internal consumers degrade through the seam; the `wavefoundry://wave/{wave_id}` resource renders `# Unreadable Wave` instead of raising or `# Not Found`. Red-first record: 38 failures across 9 tests against pre-seam code (decode raised `UnicodeDecodeError` at all nine probed boundaries and the six census-added tools; permission raised `PermissionError` at both enumeration tools and `create_wave` and misreported `wave_not_found` at every by-id boundary; sibling-decode crash and zero-match `wave_not_found` pinned). Green: 9/9 new tests; the residue census test enforces the seam by resolved target. AC-6 executed half: 16 readable-fixture surfaces byte-identical before-build vs after-build (canonical JSON, sorted keys, temp-root token normalized), plus the durable regression test. AC-5 kill probe executed: restoring the raw read at `wf_close_wave` in a scratch tree flipped exactly the two close subTests plus the residue test naming the restored line. Suites: test_server_tools 1672 OK twice, test_review_evidence 152 OK, test_dashboard_server 189 OK (1 pre-existing skip), docs-lint ok.

**Changes delivered:**

- **An Undecodable Wave Record Crashes Every Lifecycle Tool** (`1v0lw-bug wave-record-reads-crash-every-lifecycle-tool`) — 9 ACs completed. Key decisions: New diagnostic code `wave_record_unreadable` rather than reusing `change_doc_unreadable`; Fix at the shared parse helpers, not the 24 call sites
- **The Close Hard Gate Silently Passes A Missing Admitted Document** (`1v0lx-bug close-gate-silently-passes-a-missing-admitted-doc`) — 6 ACs completed. Key decisions: A distinct diagnostic (`change_doc_missing`) for the missing case rather than reusing `change_doc_unreadable`; The ghost summary branch raises rather than staying as a documented backstop
- **Rollback-Failure Detail Embeds Absolute Paths That Defeat The Leak Helper** (`1v0ly-bug rollback-failure-detail-embeds-absolute-paths`) — 5 ACs completed. Key decisions: Fix at the raise site, not the helper
## Watchpoints

- Watchpoint (readiness council): cross-wave overlap with `1uzwi`. `.wavefoundry/framework/scripts/tests/test_docs_lint.py` is a review target of both `1v0lx` (here) and `1v1c4`/`1v1c5` (there), and both waves change docs-lint behavior in `wave_lint_lib` (`1v0lx`: existence-check gating in `wave_validators.py`; `1v1c5`: new parity check in `core_validators.py` plus `cli.py` registration). Whichever wave lands second rebases its red-first lint fixtures over the first's changes; single-OPEN serialization bounds the conflict.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-10: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the red-team seat falsified the plan's core premise (the resolution path already swallows OSError and misreports a permission-unreadable wave.md as wave_not_found, and AC-2's one-exception red-first contract was unsatisfiable), repaired pre-receipt via Requirement 5, AC-9, and per-site-class expectations, then re-verified to final APPROVE by both seats; strongest-alternative: a single read_wave_record seam plus a no-read_text-outside-the-seam residue census (the 1to78 facade shape), recorded in 1v0lw's Decision Log as the implementer's option if the census finds bypass sites)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 103 | 3,053,975 |
| implement | 254 | 2,002,551 |
| review | 9 | 28,038 |
| **Total** | **366** | **5,084,564** |

<!-- wave:context-efficiency-state {"generation":180,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":254,"content_source_credit":2449182,"derived_artifact_credit":0,"direct_net":2002551,"estimated_tokens_saved":2002551,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9579,"response_debit":440849,"source_credit_count":69,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3797},"plan":{"calls":103,"content_source_credit":3246490,"derived_artifact_credit":1058,"direct_net":3053975,"estimated_tokens_saved":3053975,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7372,"response_debit":190581,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4380},"review":{"calls":9,"content_source_credit":45099,"derived_artifact_credit":1245,"direct_net":28038,"estimated_tokens_saved":28038,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3552,"response_debit":16100,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":366,"content_source_credit":5740771,"derived_artifact_credit":2303,"direct_net":5084564,"estimated_tokens_saved":5084564,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20503,"response_debit":647530,"source_credit_count":156,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9523},"wave_id":"1uzwh artifact-read-fail-closed"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 8 | 0 | 6 | 3,312,215 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":3312215,"surfaced_events":8} -->
<!-- wave:exploration-avoided end -->
