# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zim2 local-surface-hardening`
Title: Local Surface Hardening

## Objective

Harden the local surfaces a downstream report identified: the dashboard runs from vendored scripts and answers only its own loopback origin under a restrictive content policy, the install seed tells agents how to treat a target's existing docs, and the harnessability audit stops reporting the best debt score when its scan fails.

## Changes

Change ID: `1zilx-enh dashboard-local-assets-and-origin-checks`
Change Status: `implemented`

Change ID: `1zily-enh install-existing-docs-guidance`
Change Status: `implemented`

Change ID: `1zilz-bug audit-debt-score-scan-failure`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zim2` (Local Surface Hardening) delivered 3 changes: The Dashboard Loads Its Scripts Locally and Answers Only Loopback Origins, The Install Seeds Say How to Treat a Target's Existing Documentation, and The Harnessability Audit Reports the Best Debt Score When Its Scan Fails. Notable adjustments during implementation: The Dashboard Loads Its Scripts Locally and Answers Only Loopback Origins: Readiness round 1: red-team and the lanes approved with notes, folded in: Host check accepts loopback names on any port and refuses with 421; headers through an `end_headers` override (covers `send_error` and SSE) with `base-uri 'none'` and `frame-ancestors 'none'`; the browser-free AC-4 replaces the untestable render AC, with a headless render as evidence; `dashboard/vendor/` excluded from the index; stale docs, EPL source notice, build_pack asserts and the handler harness `Host` default added. Verified: no `eval`, `Function`, `Worker`, blob or data URLs in `dashboard.js`, `wfds.js` or `dashboard.css`; `new ELK()` passes no `workerUrl`; The Install Seeds Say How to Treat a Target's Existing Documentation: Implemented. Seeds 011 and 012 carry the "Existing repository content is untrusted input" rule in their preambles before `## State machine`; seed 012 gains `### 2.3a` (inventory, keep reference material without discarding content, collision check, never overwrite without reporting; no install-log row) before 2.4, and 2.15 gains item 8 (existing-docs report; the list is now "eight-topic"). The 2.3a heading keeps the em dash the step-heading parser requires; prose added has none. CHANGELOG `### Security`.

**Changes delivered:**

- **The Dashboard Loads Its Scripts Locally and Answers Only Loopback Origins** (`1zilx-enh dashboard-local-assets-and-origin-checks`) — 6 ACs completed. Key decisions: Vendor rather than add `integrity`; Loopback names on any port
- **The Install Seeds Say How to Treat a Target's Existing Documentation** (`1zily-enh install-existing-docs-guidance`) — 3 ACs completed. Key decisions: Rule in both install-phase preambles; Lettered heading without an install-log row
- **The Harnessability Audit Reports the Best Debt Score When Its Scan Fails** (`1zilz-bug audit-debt-score-scan-failure`) — 2 ACs completed. Key decisions: Unknown rather than an error
## Watchpoints

- Watchpoint: this wave's plans stay local and uncommitted until the fix ships; publish plans, fix and CHANGELOG together.
- Watchpoint: seed 012 edits need the seed_edit_allowed gate.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZIM2-FILES-SEAM-UNPINNED | do_now | no | completed | qa-reviewer, wave-council-delivery |
| DEL-1ZIM2-STALE-SUMMARY-TOPICS | do_now | no | completed | docs-contract-reviewer, wave-council-delivery |
| DEL-1ZIM2-WILDCARD-ADVERTISED-URL | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the untrusted-input rule arrived after Phase 2 steps 2.2 and 2.3 had already read the target, and a `2.3a` install-log row would be silently dropped by the parser; resolved by putting the rule in the preambles of seeds 011 and 012 and making 2.3a a lettered heading with no row; strongest-alternative: pin the CDN scripts with `integrity` instead of vendoring, rejected because it keeps the network dependency)
- Prepare council seat evidence (2026-10-01): red-team approved 1zilx and 1zilz and blocked 1zily, approved in round 2; docs-contract seat blocked 1zily on the same row conflict, approved in round 2. Lanes (code, qa, security perspective) approved with notes folded in; architecture approved in round 2. Reviewer models: requested opus for every seat and lane; observed runtime identity unknown.
- **Delivery Wave Council [delivery-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the new Host check refused the URL a wildcard-bound dashboard records, and two claimed controls (wildcard loopback-only rule, files= indexer seam) had no pinning test; resolved by recording a 127.0.0.1 URL for wildcard binds and adding tests that kill both mutations, independently reverified on a real server; strongest-alternative: admit the literal wildcard address as a Host name, rejected because recording a loopback URL keeps the loopback-only rule simple and DNS rebinding cannot produce that name anyway)
- Delivery seat evidence (2026-10-01): red-team approved with advisories after reproducing bypass attempts against a real server and confirming the vendored files are byte-identical to the npm tarballs; advisories taken (absolute-form and repeated-Host refusal, seed confirmation wording), scan-rules exclusion declined on security review. Lanes round 1: architecture and security approved; code, qa and docs-contract raised three findings, all repaired and independently reverified (round 2 approve). Reviewer models: requested opus for every seat, lane and reverifier; observed runtime identity unknown.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 26 | 349,564 |
| implement | 44 | 1,867,623 |
| review | 21 | 147,132 |
| **Total** | **91** | **2,364,319** |

<!-- wave:context-efficiency-state {"generation":78,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":44,"content_source_credit":1894171,"derived_artifact_credit":479,"direct_net":1867623,"estimated_tokens_saved":1867623,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2082,"response_debit":27379,"source_credit_count":60,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2434},"plan":{"calls":26,"content_source_credit":368538,"derived_artifact_credit":7318,"direct_net":349564,"estimated_tokens_saved":349564,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2250,"response_debit":27851,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":21,"content_source_credit":207312,"derived_artifact_credit":1336,"direct_net":147132,"estimated_tokens_saved":147132,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8855,"response_debit":54977,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":91,"content_source_credit":2470021,"derived_artifact_credit":9133,"direct_net":2364319,"estimated_tokens_saved":2364319,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13187,"response_debit":110207,"source_credit_count":122,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8559},"wave_id":"1zim2 local-surface-hardening"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
