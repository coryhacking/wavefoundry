# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zim9 dashboard-target-test-fidelity`
Title: Dashboard Target Test Fidelity

## Objective

Make the dashboard request-target tests match what a real server receives: the network-path `//...` case is pinned on a real server, where CPython's request parser normalizes it, and the harness case is labelled as defence in depth.

## Changes

Change ID: `1zim8-bug dashboard-network-path-target-test-fidelity`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zim9` (Dashboard Target Test Fidelity) delivered one change: The Dashboard Request-Target Tests Match What a Real Server Receives.

**Changes delivered:**

- **The Dashboard Request-Target Tests Match What a Real Server Receives** (`1zim8-bug dashboard-network-path-target-test-fidelity`) — 3 ACs completed. Key decisions: Keep the `netloc` check and its harness case, labelled as defence in depth
## Watchpoints

- Watchpoint: no production code changes; the `netloc` check stays.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: a real-server assertion generalized to every `//` target would be wrong, since `//api/project` legitimately serves the payload under a loopback Host; resolved by scoping AC-2 to network-path targets naming another host; strongest-alternative: delete the harness `//` case because the `netloc` clause cannot fire on a real server, rejected because the clause guards entry points that bypass `parse_request` and the labelled case keeps it covered)
- Prepare council seat evidence (2026-10-01): one independent Opus reviewer ran both seats and the code and qa lanes against the code and a real server in a scratch copy: CPython collapses a leading `//` from 3.11.0 through 3.14; about 20 raw request targets with loopback and non-loopback Hosts found no Host-check bypass and showed the `netloc` clause unreachable on a real server; every response carried the CSP and nosniff. Its plan edits (Requirement 3 settled, AC-2 tightened with the payload check and `///`, rationale version note) were applied verbatim.
- **Delivery Wave Council [delivery-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the loopback 404 depends on CPython's gh-87389 normalization; a simulated parser without it turned the 404 into a 421, so the test fails loudly rather than passing, and the Host check still refuses the request; strongest-alternative: assert only that the payload is never served, rejected because pinning the real status documents what a client actually sees)
- Delivery seat evidence (2026-10-01): one independent Opus reviewer ran both seats and the code and qa lanes in a scratch copy: no assertion weakened (same six harness cases, reordered and labelled); the target reaches the wire unchanged; five mutations (route suffix match, Host check skipped, payload served on the 404, parser normalization removed, security headers dropped) each failed the new test; ten repeated runs passed; no production code changed; default, second and declared profile runs pass. Full suite 10338 OK.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 14 | 9,870 |
| implement | 1 | 0 |
| review | 6 | 11,551 |
| **Total** | **21** | **21,421** |

<!-- wave:context-efficiency-state {"generation":20,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-56,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9,"response_debit":47,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":14,"content_source_credit":18054,"derived_artifact_credit":2189,"direct_net":9870,"estimated_tokens_saved":9870,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1410,"response_debit":12772,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":6,"content_source_credit":19282,"derived_artifact_credit":769,"direct_net":11551,"estimated_tokens_saved":11551,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1056,"response_debit":9760,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":21,"content_source_credit":37336,"derived_artifact_credit":2958,"direct_net":21365,"estimated_tokens_saved":21421,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2475,"response_debit":22579,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6125},"wave_id":"1zim9 dashboard-target-test-fidelity"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
