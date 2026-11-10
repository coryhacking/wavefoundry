# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `230k8 security-and-distribution-follow-ups`
Title: Security And Distribution Follow Ups

## Objective

Operators and downstream distributions retain unresolved security evidence through closure, refuse typed closure without readable authority, and avoid automatic dependency installation through an affected or unverifiable uv. Distribution fixtures and generated guidance follow their active declarations and vocabulary. Preserve legacy compatibility, append-only history and operator-owned environment changes.

## Changes

Change ID: `230k6-bug security-factor-closure-integrity`
Change Status: `implemented`

Change ID: `230k7-bug startup-installer-distribution-compatibility`
Change Status: `implemented`

## Participants

- Coordinator: root coordinator
- Write-owning roles: implementer (source after readiness); coordinator (planning records)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-11-10

## Wave Summary

Wave `230k8` (Security And Distribution Follow Ups) delivered two changes: Keep unresolved security evidence visible through closure and Guard startup installs and preserve distribution fixture boundaries. Notable adjustments during implementation: Keep unresolved security evidence visible through closure: Readback: a real finding with a non-none `authority_domain` whose `observable_impact` or `containment` is `unverified` will derive `security_unsettled` (today: `dont_do_later`); unknown reachability or authority delta keep their domain-independent rule, as do `do_now` precedence, the shown-unreachable exception and correctness-only unknowns (AC-1). Change close will read review authority through `resolve_review_authority` and refuse a typed container whose ledger is missing or invalid with `review_ledger_unreadable`, writing nothing; legacy containers are unchanged (AC-2). Scope boundary: no new scoring, no ledger migration, closed records untouched. Expected files: `review_evidence.py`, `lifecycle_gates.py`, `wf_server/server_impl.py`, the security disposition tests and fixture support, seeds 007/209/237/239 and their mirrors, `docs/contributing/review-and-evals.md`, `docs/specs/mcp-tool-surface.md`, the two architecture docs, `CHANGELOG.md`. This serves Product Intent by keeping missing evidence distinguishable from a settled decision.; Keep unresolved security evidence visible through closure: Implemented. `unsettled_security_factors` adds impact and containment for a non-`none` domain; `wf_close_change` reads `resolve_review_authority` and shares `security_candidate_diagnostics` with Review and Close; the builder refuses a reconsideration of a `not_issue` finding; the served writer refuses a repair start on a closed record (`wave_closed`); `security_candidate_state` names unverified factors and a superseded waiver. Tests: factor matrix over all 15 combinations with four controls each; closure parity; four corrupt ledgers in both modes with whole-tree byte comparison; a legacy control; reconsideration from a pre-repair terminal head; five refusal controls; a reconsidered operator waiver; the served-close seam with an overriding handler; the scoped census. The handler digest pin moved only for `wf_review_event` and `wf_close_change`.; Keep unresolved security evidence visible through closure: Landing rule: each guard deleted or loosened in a scratch copy of the tree, baseline green, mutant killed. Factor tuple emptied: `DerivationTests.test_the_factor_matrix_covers_each_factor_alone_and_in_combination`. Domain qualifier removed: `test_correctness_unknowns_and_settled_factors_derive_as_before`. Ledger refusal disabled, and the missing/invalid distinction forced: `ClosureAuthorityTests.test_an_unreadable_typed_ledger_refuses_the_close_and_writes_nothing`. Shared candidates emptied: `test_review_change_close_and_wave_close_name_the_same_pending_candidate`. Real-predecessor guard removed: `ReconsiderationTests.test_unrelated_terminal_findings_are_not_reopened`. Closed refusal disabled: `test_a_closed_record_takes_no_reconsideration`. Superseded waiver dropped: `test_a_reconsidered_operator_waiver_stays_in_the_ledger_and_is_decided_again`.

Intent outcome: established for the scoped promises, on macOS. Evidence: a real finding with a named authority domain and an unknown impact or containment now stays `security_unsettled` and is named identically by Review, change close and wave close; change close refuses a typed record whose review authority cannot be established and writes nothing; a terminal finding takes fresh evidence under its own identity with its history and any superseded waiver kept; MCP startup refuses to install through a uv below 0.13.4 or with an unreadable version and reports the `--upgrade-uv` remedy; fixture arguments follow the active declaration; the Plan arc skill and the lifecycle-id reminder use current names. Full suite 12,709 tests OK; the changed test files pass under the `second` and `declared` profiles; 18 implementer mutants and 19 reviewer mutants were killed. Limits: no native Windows, Linux or WSL2 run; no real uv install or downstream distribution run; the uv guard trusts the version string uv prints; `wf_review_event` kinds other than `repair_start` can still append to a closed record, which predates this wave.

**Changes delivered:**

- **Keep unresolved security evidence visible through closure** (`230k6-bug security-factor-closure-integrity`) — 5 ACs completed. Key decisions: Extend the existing disposition and authority mechanisms, with a narrowly scoped append-only reconsideration route
- **Guard startup installs and preserve distribution fixture boundaries** (`230k7-bug startup-installer-distribution-compatibility`) — 5 ACs completed. Key decisions: Guard automatic installation using the existing version probe and fix fixture/profile owners
## Watchpoints

- Preserve concurrent writing-guide work and historical ledgers.
- Loaded MCP is stale for indexed retrieval; use disclosed targeted source fallback and verify receipt/tool compatibility.
- Full primer depth: security authority, startup installation and cross-module contracts. One initial readiness review, one bounded repair and focused verification; escalate remaining blockers.
- Work allocation: coordinator owns packet; independent council chair orchestrates isolated primer and seats with at most three concurrent workers. Disposable work: .wavefoundry/work/230k8/. No source edits in readiness.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | code-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

- 2026-11-10: Readiness review PASS, intent fit establishes for both changes and the wave Objective. Full-depth red-team primer; isolated architecture, security, QA and reality seats; rotating docs-contract seat; separate required code lane; council-chair merit-first synthesis. All five required lane approvals and council-readiness recorded against review-policy-fa9184697b9842843f67. No findings or repair round. Typed ledger is authority; disposable reports are in .wavefoundry/work/230k8/.
- Implementation notes: preserve existing unknown reachability/authority treatment even with authority_domain=none. Prefer security-only repair-start eligibility with restored coverage, then unchanged independent reverification. Before protocol edits, record eligibility, predecessor/cycle, coverage, waiver and closed-container handling. Probe the actual selected uv after the under-lock dependency recheck and retain refusal status through reassessment. Use producer-built ledgers and served distribution overrides in tests.
- Evidence limits: bounded source/plan checks, pure disposition probes and installer-routing controls support readiness; delivery behavior, real installs and downstream deployment remain unverified. Shared host/model and primer are correlated. No source implementation or wave activation authorized by this review.

- 2026-11-10: Delivery review PASS. Required lanes code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer and docs-contract-reviewer each ran in a fresh, independent context and approved; a delivery council is not required by the review-policy receipt. One finding, CODE-DEL-1 (low; two diagnostics misdescribed their cause), was repaired in cycle 1 and reverified by a fresh code-reviewer context. The typed ledger is authority.
- Intent outcome: established for the scoped promises, on macOS. Evidence: a real finding with a named authority domain and an unknown impact or containment now stays `security_unsettled` and is named identically by Review, change close and wave close; change close refuses a typed record whose review authority cannot be established and writes nothing; a terminal finding takes fresh evidence under its own identity with its history and any superseded waiver kept; MCP startup refuses to install through a uv below 0.13.4 or with an unreadable version and reports the `--upgrade-uv` remedy; fixture arguments follow the active declaration; the Plan arc skill and the lifecycle-id reminder use current names. Full suite 12,709 tests OK; the changed test files pass under the `second` and `declared` profiles; 18 implementer mutants and 19 reviewer mutants were killed. Limits: no native Windows, Linux or WSL2 run; no real uv install or downstream distribution run; the uv guard trusts the version string uv prints; `wf_review_event` kinds other than `repair_start` can still append to a closed record, which predates this wave.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 21 | 0 |
| implement | 45 | 560,237 |
| review | 55 | 1,806,746 |
| **Total** | **121** | **2,366,983** |

<!-- wave:context-efficiency-state {"generation":120,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":45,"content_source_credit":582967,"derived_artifact_credit":0,"direct_net":560237,"estimated_tokens_saved":560237,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1596,"response_debit":25441,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4307},"plan":{"calls":21,"content_source_credit":38145,"derived_artifact_credit":1623,"direct_net":-26080,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3058,"response_debit":68292,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":55,"content_source_credit":1916651,"derived_artifact_credit":1626,"direct_net":1806746,"estimated_tokens_saved":1806746,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6754,"response_debit":108553,"source_credit_count":52,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":121,"content_source_credit":2537763,"derived_artifact_credit":3249,"direct_net":2340903,"estimated_tokens_saved":2366983,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11408,"response_debit":202286,"source_credit_count":83,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13585},"wave_id":"230k8 security-and-distribution-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 8 | 0 | 5 | 7,543,853 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":7543853,"surfaced_events":8} -->
<!-- wave:exploration-avoided end -->
