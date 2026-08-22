# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vry5 techdocs-pattern-fidelity`
Title: Techdocs Pattern Fidelity

## Objective

Remove the two remaining TechDocs exclusion-pattern gaps without reopening the aggregate timeout
design delivered in wave `1vqqi`: collapse semantically redundant adjacent floating prefixes,
and refuse escaped slash exactly where MkDocs/pathspec refuses it.

## Changes

Change ID: `1vqqj-enh techdocs-audit-cost-ceiling-and-pattern-fidelity`
Change Status: `implemented`


## Participants

- Coordinator: `wave-coordinator`
- Write-owning roles: `implementer`
- Requested review lanes: `architecture-reviewer`, `performance-reviewer`, `security-reviewer`
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-08-20

## Wave Summary

Wave `1vry5` (Techdocs Pattern Fidelity) delivered one change: TechDocs audit: close the two remaining pattern-fidelity gaps. Notable adjustments during implementation: TechDocs audit: close the two remaining pattern-fidelity gaps: Readiness repair cycle 1 separated emitted-fragment collapse from source-group budget accounting and expanded escaped-slash verification to an oracle-owned context matrix.; TechDocs audit: close the two remaining pattern-fidelity gaps: Readiness repair cycle 3 removed match-answer identity from oracle-unloadable forms while preserving exact identity for every loadable pattern and requiring the refused/unsupported/degraded public delta.; TechDocs audit: close the two remaining pattern-fidelity gaps: **Repair cycle 5:** removed the surviving universal “worst admitted” sentence, derived escaped-slash expectations from the live MkDocs/pathspec results with a stale-label falsifier, separated the 32 directed regressions from the random non-vacuity floor while adding the standalone backslash alphabet member, updated the load-bearing matcher comment from stale future tense to the delivered collapse plus surviving literal-separated reproduction, and scoped AC-5 provenance to current delivery evidence while labeling older motivating measurements historical pre-AC-5 context.

**Changes delivered:**

- **TechDocs audit: close the two remaining pattern-fidelity gaps** (`1vqqj-enh techdocs-audit-cost-ceiling-and-pattern-fidelity`) — 7 ACs completed. Key decisions: Selected a matcher-only follow-up that collapses the redundant adjacent floating prefix and refuses escaped slash while preserving the existing public deadline.; Keep the existing `_MAX_VARIABLE_GROUPS` source-group ceiling for this change, and record the divergence it preserves rather than silently carrying it.
## Watchpoints

- Watchpoint: do not modify or re-accept the isolated worker deadline; it is an inherited precondition.
- Watchpoint: collapsing emitted regex fragments must not reduce source-group accounting or widen
  the admitted-pattern boundary.
- Prove adjacent-prefix collapse by differential equivalence over oracle-loadable patterns, and
  treat oracle-refused escaped-slash forms as an explicit refusal/report delta rather than an
  undefined match-answer comparison.
- State every cost result with its exact pattern and subject shape; claim no universal local ceiling.
- Keep the MkDocs publication boundary at 0 fail-open and 0 fail-closed in the randomized oracle.

## Review Checkpoints

- Product-owner acknowledgment: the operator explicitly requested plan cleanup, creation of this
  wave, preparation, and review on 2026-08-19.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-19: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: preserve source-group admission and partition oracle-unloadable escaped-slash deltas from loadable-pattern identity; strongest-alternative: refuse every adjacent `**/` source form, rejected because it would degrade valid MkDocs configurations instead of removing redundant regex emissions.)
- **Prepare docs-contract seat — 2026-08-19: no additional finding.** The repaired plan consistently declared the pinned external-oracle harness, retained wave artifact, testing-architecture carrier, and dependency-free ordinary suite; implementation still required delivery-time carrier verification.

## Completion Criteria

- Required ACs AC-2 through AC-5 are complete with executable evidence; AC-1 remains a documented
  `not-this-scope` preservation constraint.
- Every required specialist lane approves the delivered bytes on the current receipt.
- The delivery council is terminal and the wave is eligible for explicit operator closure.

## Handoff or Next-Wave Notes

- No timeout redesign is carried forward from this wave. Any newly discovered aggregate matcher
  family remains contained by the existing worker deadline and requires a separately admitted
  change before expanding this scope.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | do_now | no | completed | — |
| PERF-DEL-1 | do_now | no | completed | — |
| PREP-ADVERSARIAL-SEARCH-UNIVERSE-004 | do_now | no | completed | wave-council-readiness, qa-reviewer, performance-reviewer |
| PREP-COST-PROVENANCE-005 | do_now | no | completed | wave-council-readiness |
| PREP-DIFFERENTIAL-POLARITY-002 | do_now | no | completed | wave-council-readiness, code-reviewer, qa-reviewer, performance-reviewer, security-reviewer |
| PREP-REFUSED-MATCH-DELTA-003 | do_now | no | completed | wave-council-readiness, code-reviewer, qa-reviewer, performance-reviewer, security-reviewer |
| PREP-SOURCE-GROUP-BUDGET-001 | do_now | no | completed | wave-council-readiness |
| QA-DEL-1 | do_now | no | completed | — |
| QA-DEL-2 | do_now | no | completed | — |

*Machine review state — 9 findings; current: do_now 9, maybe_later 0, dont_do_later 0, not_issue 0*
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
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 239 | 851,050 |
| implement | 55 | 86,941 |
| review | 767 | 11,788,635 |
| **Total** | **1,061** | **12,726,626** |

<!-- wave:context-efficiency-state {"generation":936,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":55,"content_source_credit":130833,"derived_artifact_credit":0,"direct_net":86941,"estimated_tokens_saved":86941,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2029,"response_debit":48183,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6320},"plan":{"calls":239,"content_source_credit":1490300,"derived_artifact_credit":942,"direct_net":851050,"estimated_tokens_saved":851050,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":41808,"response_debit":601890,"source_credit_count":101,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":767,"content_source_credit":14163340,"derived_artifact_credit":1250,"direct_net":11788635,"estimated_tokens_saved":11788635,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":77036,"response_debit":2300265,"source_credit_count":517,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1061,"content_source_credit":15784473,"derived_artifact_credit":2192,"direct_net":12726626,"estimated_tokens_saved":12726626,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":120873,"response_debit":2950338,"source_credit_count":624,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11172},"wave_id":"1vry5 techdocs-pattern-fidelity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 21 | 0 | 6 | 19,809,549 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":19809549,"surfaced_events":21} -->
<!-- wave:exploration-avoided end -->
