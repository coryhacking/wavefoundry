# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uzwi review-signal-and-carrier-integrity`
Title: Review Signal And Carrier Integrity

## Objective

Make the review system's own signals truthful: a lapsed approval currently reports "invalid actor or independence" when the real cause is receipt supersession (hit live twice during `1uwpf`), a shipped citation rule sits in a prompt copy no mechanism keeps aligned with its seed, carrier parity between `REVIEW_POLICY_SURFACE_BLOCKS` and rendered regions is unenforced, and a wall-clock perf budget fails the suite on machine load — at unmodified HEAD — burying real signal under false red.

## Changes

Change ID: `1v0lz-bug lapsed-approval-reason-misattributes-the-cause`
Change Status: `implemented`

Change ID: `1v1c4-debt council-review-citation-paragraph-has-no-renderer-sync`
Change Status: `implemented`

Change ID: `1v1c5-debt carrier-parity-unenforced-between-blocks-and-rendered-regions`
Change Status: `implemented`

Change ID: `1v1c6-maint perf-budget-tests-flake-under-parallel-suite-load`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-11

## Wave Summary

Wave `1uzwi` (Review Signal And Carrier Integrity) delivered 4 changes: A Lapsed Approval's Reason String Misattributes The Cause, The Council-Review Citation Paragraph Has No Renderer Sync, Carrier Parity Is Unenforced Between Policy Blocks And Rendered Regions, and Perf-Budget Tests Flake Under Parallel Suite Load. Notable adjustments during implementation: A Lapsed Approval's Reason String Misattributes The Cause: Readiness council (red-team and docs-contract seats): citation corrected to the symbol anchor `review_authority_projection` (the module-level-constant-block label misapplied the line-anchor exemption), and the no-current-receipt edge added to Requirement 1 and AC-1 with a stated message shape; A Lapsed Approval's Reason String Misattributes The Cause: Implemented. Red observed: 7 of 8 new tests failed against current code with the misattributed string on the supersession fixture (executed output pinned the exact sentence). Green: 8/8 after the conjunct split; `test_review_evidence` 152/152 and `test_dashboard_server` 189/189 file-scope. AC-3 executed with the qa lane's protocol: `derive_states.py` serialization (sorted wave/key/state JSON lines from `review_status_rows` over every real `docs/waves/*/events.jsonl`), old code from a clean `git archive HEAD` extract vs new working tree, 373 rows, ZERO state diffs (zero why diffs too: the live corpus currently holds only valid or absent approvals, so the changed strings are exercised by the unit fixtures). AC-4 asserted on `review_status_human_table` output, the projection's table renderer. Extra cause beyond the plan's three: malformed verification context gets its own message, per the qa lane's fourth-shape note; The Council-Review Citation Paragraph Has No Renderer Sync: Carrier census (AC-2) executed, repo-wide sweep on the rule's distinctive phrase plus both marker families. 1uu9y carriers: (1) live `docs/prompts/council-review.prompt.md` paragraph (line 50, outside both renderer-owned regions): was sync-less, NOW PINNED; (2) seed 237 authoring paragraph: was sync-less (the pre-existing exact pin covers only the older code-grounded verification bullet, so the plan's "seeds 209/237 pinned" premise was wrong for the authoring text), NOW PINNED byte-exact by the same test; (3) seed 209 authoring variant: was sync-less, NOW PINNED (audience head, shared carve-out middle, immutability tail); (4) `_prepare_council_instructions` runtime brief: already clause-pinned by `test_brief_carries_the_finding_authoring_citation_rule`, verified. Adjacent discovery OUTSIDE 1uu9y's set: seed 170 carries the `1urlb`-era change-document variant ("When a change document cites code...", expanded multi-paragraph wording) with no exact pin; recorded for the delivery review to disposition rather than pinned here, per scope discipline.

**Changes delivered:**

- **A Lapsed Approval's Reason String Misattributes The Cause** (`1v0lz-bug lapsed-approval-reason-misattributes-the-cause`) — 5 ACs completed. Key decisions: Name the first failed conjunct in evaluation order rather than all failed conjuncts
- **The Council-Review Citation Paragraph Has No Renderer Sync** (`1v1c4-debt council-review-citation-paragraph-has-no-renderer-sync`) — 3 ACs completed. Key decisions: Follow the `1tmb4` precedent by default
- **Carrier Parity Is Unenforced Between Policy Blocks And Rendered Regions** (`1v1c5-debt carrier-parity-unenforced-between-blocks-and-rendered-regions`) — 5 ACs completed. Key decisions: Compare via the renderer's own composition helper; Error, not warning
- **Perf-Budget Tests Flake Under Parallel Suite Load** (`1v1c6-maint perf-budget-tests-flake-under-parallel-suite-load`) — 4 ACs completed. Key decisions: Keep the budget, fix the measurement conditions
## Watchpoints

- Watchpoint (readiness council): cross-wave overlap with `1uzwh`. `.wavefoundry/framework/scripts/tests/test_docs_lint.py` is a review target of both `1v1c4`/`1v1c5` (here) and `1v0lx` (there), and both waves change docs-lint behavior in `wave_lint_lib` (`1v1c5`: new parity check in `core_validators.py` plus `cli.py` registration; `1v0lx`: existence-check gating in `wave_validators.py`). Whichever wave lands second rebases its red-first lint fixtures over the first's changes; single-OPEN serialization bounds the conflict.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-10: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the wave's own plans exhibited the drift class they target (a marker census missing a region, a misapplied citation exemption, an AC unable to falsify an inflated budget), all corrected pre-receipt and re-verified to final APPROVE by both seats; strongest-alternative: a reconciler-idempotence lint gate covering every marker family instead of composed per-destination comparison, recorded in 1v1c5's Decision Log and kept open for implementation measurement)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
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
| plan | 55 | 1,407,887 |
| implement | 233 | 1,276,907 |
| review | 341 | 1,909,409 |
| **Total** | **629** | **4,594,203** |

<!-- wave:context-efficiency-state {"generation":542,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":233,"content_source_credit":1841170,"derived_artifact_credit":0,"direct_net":1276907,"estimated_tokens_saved":1276907,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8926,"response_debit":558808,"source_credit_count":69,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3471},"plan":{"calls":55,"content_source_credit":1527972,"derived_artifact_credit":1191,"direct_net":1407887,"estimated_tokens_saved":1407887,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6769,"response_debit":116697,"source_credit_count":67,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2190},"review":{"calls":341,"content_source_credit":2951415,"derived_artifact_credit":1300,"direct_net":1909409,"estimated_tokens_saved":1909409,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15552,"response_debit":1029100,"source_credit_count":116,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":629,"content_source_credit":6320557,"derived_artifact_credit":2491,"direct_net":4594203,"estimated_tokens_saved":4594203,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31247,"response_debit":1704605,"source_credit_count":252,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7007},"wave_id":"1uzwi review-signal-and-carrier-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 24 | 0 | 12 | 10,332,743 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":12,"estimated_exploration_avoided":10332743,"surfaced_events":24} -->
<!-- wave:exploration-avoided end -->
