# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xxcb index-restart-envelope`
Title: Index Restart Envelope

## Objective

Present a validated index-writer restart checkpoint as action_required instead of an outer upgrade error, including the ppjy installing hop through its newly loaded restart reader.

## Changes

Change ID: `1xxca-bug first-hop-index-restart-envelope`
Change Status: `complete`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer (response compatibility and tests), technical-writer (upgrade guidance)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-14

## Wave Summary

Wave `1xxcb` (Index Restart Envelope) delivered one change: First-hop index restart envelope. Notable adjustments during implementation: First-hop index restart envelope: Readback: expected index restart becomes action_required in current and newly loaded ppjy reader paths, preserving exact CLI and genuine errors (AC-1–4). Thought: implement response/reader adapter, run historical and negative controls, then update guidance and full verification. Generic implementer owns scoped writes. Prepare/create opened after clean readiness; wf_implement_wave still requests obsolete extra prepare lanes, so the documented prepare-and-open path was used.; First-hop index restart envelope: Observe: 192 focused tests pass (one existing platform skip); latest public wrapper and guard suite 24/24 pass. Both removed-reader and removed-final-normalizer mutants fail the positive legacy-wrapper test for the expected wrong status. Oversized child output remains bounded while exact argv survives the archived original bounder. Thought: freeze scoped source for independent delivery review and full suite.

**Changes delivered:**

- **First-hop index restart envelope** (`1xxca-bug first-hop-index-restart-envelope`) — 4 ACs completed. Key decisions: Reuse validated installed action-reader and bounded response seams for the pre-guard wrapper, plus direct current-wrapper normalization.
## Watchpoints

- Watchpoint: already-cached older readers cannot acquire incoming behavior; retain the documented checkpoint and exact external CLI recovery.
- Source and tests match the reviewed fingerprint; full verification passes 8,984 tests (12 existing skips). Historical restriction superseded for closure only by the operator on 2026-09-14; no new commit or package requested.

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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Delivery council — 2026-09-13: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: old wrapper overwrites action identity and recovery guidance; strongest-alternative: current-wrapper-only correction misses the installing hop). Isolated code, QA and docs lanes approved. Exact invocation capability, altered-action refusal and unchanged original bounder verified. No unresolved findings or disagreements. Evidence: `delivery-review.json`.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 50 | 1,722,906 |
| implement | 43 | 799,425 |
| review | 163 | 2,191,164 |
| **Total** | **256** | **4,713,495** |

<!-- wave:context-efficiency-state {"generation":232,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":43,"content_source_credit":856113,"derived_artifact_credit":0,"direct_net":799425,"estimated_tokens_saved":799425,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1489,"response_debit":55659,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":460},"plan":{"calls":50,"content_source_credit":1784160,"derived_artifact_credit":1409,"direct_net":1722906,"estimated_tokens_saved":1722906,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2428,"response_debit":65931,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":163,"content_source_credit":2641244,"derived_artifact_credit":2875,"direct_net":2191164,"estimated_tokens_saved":2191164,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9927,"response_debit":444917,"source_credit_count":81,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":256,"content_source_credit":5281517,"derived_artifact_credit":4284,"direct_net":4713495,"estimated_tokens_saved":4713495,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13844,"response_debit":566507,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8045},"wave_id":"1xxcb index-restart-envelope"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 31 | 0 | 13 | 22,587,749 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":22587749,"surfaced_events":31} -->
<!-- wave:exploration-avoided end -->
## Closure Reconciliation

- All four ACs and every task are complete, independently checked against shipped code; no deferred ACs.
- Required code, QA and docs-contract lanes reconciled; current typed readiness and prior targeted delivery council retained for the unchanged boundary.
- Docs-contract review performed: seed, customized prompt and MCP spec preserve exact CLI, no invented storage receipt and cached-reader limitation. No findings.
- Chronology reconciled: change complete; closure tool owns final wave status/date.
- Retrospective: a newly loaded reader can adapt the old final envelope, but a cached reader cannot acquire incoming code; existing canonical guidance already captures this lesson.
- Memory proposal returned zero candidates; no additional durable record or promotion warranted.
- Handoff carries released 1.24.0, the next paused wave and existing deferred decisions; set idle after this closure.
- No unchecked or intentionally deferred AC/task remains.
- Verification: Luna 32 focused tests; independent Astra 12 controls, four fake-proof controls, two killed mutants. Source frozen; full framework receipt current at 9,008 tests.
- Operator authorized sequential reopen, verification and closure on 2026-09-14.
