# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-28
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zbrr memory-source-event-lint`
Title: Memory Source Event Lint

## Objective

Correct memory lint's false secret-assignment diagnosis on generated source-event identifiers, preserving provenance and detection of forbidden content. Cover all three existing proposal families without exempting arbitrary metadata payloads.

## Changes

Change ID: `1zbrq-bug memory-source-event-lint-false-positive`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, security-reviewer

Completed At: 2026-09-29

## Wave Summary

Wave `1zbrr` (Memory Source Event Lint) delivered one change: Memory Source Event Identifiers Do Not Trigger Secret-Assignment Lint.

**Changes delivered:**

- **Memory Source Event Identifiers Do Not Trigger Secret-Assignment Lint** (`1zbrq-bug memory-source-event-lint-false-positive`) — 4 ACs completed. Key decisions: Exempt only the decision-log hash separator; finding and repeated-repairs events get no exemption; Recognize complete generated metadata and exclude only validated structural false matches
## Watchpoints

- 2026-09-29: the operator directed this session to take over the wave and implement it after 1z8ox closed. The 2026-09-28 review-only deferral no longer applies; implementation still requires current typed readiness approvals.
- Keep any exception limited to validated event-level separator matches; source-event payloads are not trusted content.
- Readiness review and bounded current-behavior probes are recorded in readiness-review.md. Typed readiness approvals (code, QA, security, wave-council-readiness) were recorded on 2026-09-29 against receipt review-policy-2b0e840f7725b5f3a9f4 in events.jsonl.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: producer output is not a trust boundary, so any exempt separator is a smuggling channel, and an unvalidated wave token would let finding:token:<secret> pass; strongest-alternative: exempt only the decision-log hash separator on an anchored line and validate wave identifiers by the lifecycle grammar, adopted into Requirements 2 and 5). Security seat: PASS with SEC-1 (lifecycle-grammar wave ids plus negative controls), SEC-2 (scan every match) and SEC-3 (residual 16-hex channel documented) folded in. Red-team seat: PASS with RT-1 simplification folded in. Code and QA lanes approved separately; their advisories (every-match scanning, memory_handlers write-time scans unchanged, six-character producer fixture, AC-3 checks) are folded in.
- 2026-09-28: Plan review completed with an isolated red-team primer and independent code/architecture review. Corrected stale owner references and clarified benign-output acceptance; added a same-line multiple-match control. See readiness-review.md for evidence, limitations and remaining lifecycle approvals. No implementation changes or wave activation.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-1 | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 37 | 62,241 |
| implement | 23 | 22,379 |
| review | 51 | 786,836 |
| **Total** | **111** | **871,456** |

<!-- wave:context-efficiency-state {"generation":103,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":23,"content_source_credit":30576,"derived_artifact_credit":0,"direct_net":22379,"estimated_tokens_saved":22379,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1290,"response_debit":7483,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":576},"plan":{"calls":37,"content_source_credit":98932,"derived_artifact_credit":2261,"direct_net":62241,"estimated_tokens_saved":62241,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2469,"response_debit":40292,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":51,"content_source_credit":967195,"derived_artifact_credit":971,"direct_net":786836,"estimated_tokens_saved":786836,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4158,"response_debit":179488,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":111,"content_source_credit":1096703,"derived_artifact_credit":3232,"direct_net":871456,"estimated_tokens_saved":871456,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7917,"response_debit":227263,"source_credit_count":65,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6701},"wave_id":"1zbrr memory-source-event-lint"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 2 | 1,582,143 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":1582143,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
