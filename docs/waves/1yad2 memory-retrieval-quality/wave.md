# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yad2 memory-retrieval-quality`
Title: Memory Retrieval Quality

## Objective

Improve the relevance and speed of project-memory retrieval through an independently qualified comparison of plain RRF and score-based fusion. Separate eligibility, relevance and authority; adopt a production change only after quality, abstention, fallback and performance gates pass.

## Changes

Change ID: `1yad1-enh memory-retrieval-relevance-and-fusion`
Change Status: `complete`

## Participants

- Coordinator: Engineering / lifecycle coordinator
- Write-owning roles: implementer; documentation writer (assigned during Prepare wave)
- Requested review lanes: architecture-reviewer, code-reviewer, qa-reviewer, performance-reviewer, docs-contract-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-09-17

## Wave Summary

Delivered **memory-scoped RRF with at most five CPU summary relevance checks**, source-hash freshness validation and explicit recovery. Calling agents still judge relevance, applicability and support; ranking does not establish authority. Briefing, unsolicited advisory ordering and ordinary code/docs search are unchanged.

The delivered public path improved expected useful queries from 12/16 to 15/16 and warm p95 from 614.0 ms to 192.2 ms; no useful baseline query lost all useful support, and all eight no-match queries remained empty. Six adjacent records remain. Evidence and limits: [summary](evidence/README.md), [production qualification](evidence/summary5-production-qualification.md), [final verification](evidence/summary5-final-verification.md).

All eight ACs and tasks completed; no intentional deferrals. Six delivery lanes approved, including docs-contract review. Both findings repaired and independently reverified; operator authorized closure on 2026-09-17. The current canonical receipt proves 9,126 tests across 95 files with 12 disclosed skips. Native qualification is macOS ARM64 only.

Key decisions: compare fusion separately from answerability; qualify only checked candidates; retain explicit caller judgment. The operator accepted an empty response replacing an irrelevant baseline hit while forbidding loss of useful support. The post-observation gate revision is disclosed in [integration preflight](evidence/summary5-integration-preflight.md).

Retrospective completed: relative ranking cannot establish answerability, frozen independent judgments matter, and source/vector freshness must share one read transaction. These lessons are carried in the canonical search architecture, memory evaluation reference and retained qualification evidence. Close-time memory_propose produced zero candidates; no validation or promotion remains pending. Session handoff was set idle after successful closure. Operator-requested memory maintenance follows separately. No commit, push or package performed.

## Watchpoints

- Watchpoint: plain RRF and score fusion are finalists, not selected production defaults.
- Freeze independent labels, effect-size/budget gates and parameters before final holdout scoring.
- Relevance-first ranking changes an existing trust invariant; resolve that contract before integration.
- Historical no-match cutoffs failed to generalize; one good result must not validate an unrelated tail.
- Code/docs retrieval, memory curation, storage migrations and automatic conflict resolution are outside this wave.
- A failed adoption gate leaves production ranking unchanged; completed evaluation is still useful delivery.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| S5-MODEL-RECOVERY-GUIDANCE | do_now | no | completed | code-reviewer, docs-contract-reviewer |
| S5-STALE-SOURCE | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- Operator closure authorization recorded in the typed ledger on 2026-09-17.

## Dependencies

- No external wave dependencies. Current unified SQLite and existing local embedding runtime are inputs, not migration targets.

## Current assumptions

- Local-only operation; no new model or native dependency.
- Existing exact-target, history and no-index behavior remain protected.
- Independent holdout judgment and the final policy/latency thresholds are readiness decisions, not implicitly settled by this plan.

## Outputs produced

- Completed change `1yad1-enh memory-retrieval-relevance-and-fusion` and production memory retrieval integration.
- [Evidence summary](evidence/README.md), [production qualification](evidence/summary5-production-qualification.md), frozen inputs and blind judgments.
- [Final verification](evidence/summary5-final-verification.md), [delivery review](evidence/summary5-final-delivery-review.md), [QA](evidence/summary5-final-qa.md).
- Canonical search architecture, memory evaluation reference and tool contract updated. Historical non-adoption reports retained as decision history.

## Review checkpoints

- Operator acknowledgment: current instruction “implement this change” authorizes the gated evaluation and conditional integration described in the admitted plan.
- Work allocation: coordinator owns activation, public response integration and documentation; implementer owns evaluation helpers and their tests; independent QA owns unseen holdout judgments; local targeted readiness council uses red-team and docs-contract-reviewer, with primer-context council synthesis distinct from the coordinator and docs seat; moderator shares primer context, which is disclosed. Selected existing model for complex measurement/policy judgment; bounded tasks and shared-file serialization constrain overhead.

- Prepare/readiness: resolve quality effect size, runtime budget, authority decision and holdout ownership before code edits.
- Architecture/policy: approve any relevance-versus-trust contract change before integration.
- Delivery: independent public-path verification of quality, failure behavior, privacy and runtime bounds.

## Completion criteria

- Every admitted AC/task is reconciled with current evidence.
- Required reviews and adoption/non-adoption decision are recorded; operator owns closure.

## Handoff or next-wave notes

Production summary5 integration is complete and independently reviewed. Explicit memory queries use memory-scoped dense20 + lexical20 RRF, five CPU summary checks, source-hash freshness validation and explicit lexical recovery. Calling agents assess relevance/support; ranking does not establish authority. Actual public results match the frozen candidate on all 24 cases; useful expected-set queries 15/16 versus12/16 and warm p95 192.2ms versus614.0ms. Six adjacent results remain disclosed.

The canonical suite passed 9,126 tests (12 skips) with a current matching receipt; full MCP docs validation passed. Both typed repair findings have no unresolved lanes. See [final integration verification](evidence/summary5-final-verification.md), [production qualification](evidence/summary5-production-qualification.md) and fresh delivery/QA reports. Earlier non-adoption reports are preserved as historical evidence. No memory candidates were created. Operator authorized closure on 2026-09-17; no commit/push/package authorized or performed. Attached MCP runner still needs a full host restart; fresh-process verification is complete. Regular code/docs retrieval evaluation remains separate future work.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 148 | 1,680,070 |
| implement | 116 | 2,495,368 |
| review | 303 | 4,418,277 |
| **Total** | **567** | **8,593,715** |

<!-- wave:context-efficiency-state {"generation":418,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":116,"content_source_credit":2692166,"derived_artifact_credit":1614,"direct_net":2495368,"estimated_tokens_saved":2495368,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8448,"response_debit":191867,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1903},"plan":{"calls":148,"content_source_credit":1809330,"derived_artifact_credit":2753,"direct_net":1680070,"estimated_tokens_saved":1680070,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8188,"response_debit":209326,"source_credit_count":94,"source_credit_drop_count":0,"structural_source_credit":77312,"workflow_prompt_credit":8189},"review":{"calls":303,"content_source_credit":5228768,"derived_artifact_credit":4592,"direct_net":4418277,"estimated_tokens_saved":4418277,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35899,"response_debit":781186,"source_credit_count":161,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":567,"content_source_credit":9730264,"derived_artifact_credit":8959,"direct_net":8593715,"estimated_tokens_saved":8593715,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":52535,"response_debit":1182379,"source_credit_count":335,"source_credit_drop_count":0,"structural_source_credit":77312,"workflow_prompt_credit":12094},"wave_id":"1yad2 memory-retrieval-quality"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 28 | 0 | 13 | 16,904,914 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":16904914,"surfaced_events":28} -->
<!-- wave:exploration-avoided end -->
