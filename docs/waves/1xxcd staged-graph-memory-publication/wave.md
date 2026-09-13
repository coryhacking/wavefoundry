# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xxcd staged-graph-memory-publication`
Title: Staged Graph Memory Publication

## Objective

Unblock unified-index upgrades with active memory backfill while retaining live publication and forward-recovery guards.

## Changes

Change ID: `1xxcc-bug staged-graph-memory-publication`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, release-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-09-13

## Wave Summary

Wave `1xxcd` (Staged Graph Memory Publication) delivered one change: Isolate staged graph builds from live memory publication. Notable adjustments during implementation: Isolate staged graph builds from live memory publication: Reflect: the real memory-document CLI fixture creates the pre-existing disposable memory cache, as _staging_allowlist documents. Corrected the overbroad no-file assertion to no staged historical-backfill authority. No memory-invalidation bypass is needed or added; re-Prepare this clarified criterion.

**Changes delivered:**

- **Isolate staged graph builds from live memory publication** (`1xxcc-bug staged-graph-memory-publication`) — 5 ACs completed. Key decisions: Context-local scope bound to validated candidate path and identity
## Watchpoints

- Watchpoint: retain the original package and receipt. No target edits, commit or closure authorized.

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
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 20 | 0 |
| implement | 91 | 421,447 |
| review | 153 | 1,548,122 |
| **Total** | **264** | **1,969,569** |

<!-- wave:context-efficiency-state {"generation":225,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":91,"content_source_credit":603020,"derived_artifact_credit":0,"direct_net":421447,"estimated_tokens_saved":421447,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3028,"response_debit":178545,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":20,"content_source_credit":3971,"derived_artifact_credit":229,"direct_net":-13779,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1521,"response_debit":22154,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":153,"content_source_credit":1751456,"derived_artifact_credit":4322,"direct_net":1548122,"estimated_tokens_saved":1548122,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17001,"response_debit":192544,"source_credit_count":104,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":264,"content_source_credit":2358447,"derived_artifact_credit":4551,"direct_net":1955790,"estimated_tokens_saved":1969569,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":21550,"response_debit":393243,"source_credit_count":134,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7585},"wave_id":"1xxcd staged-graph-memory-publication"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 12 | 0 | 7 | 10,925,155 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":10925155,"surfaced_events":12} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Delivery council: pass; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; moderator: wave-council. Unanimous, max severity none; no challenge round. The primer required distinguishing verified publication from post-edit cleanup and disposable cache from historical-backfill authority. The docs seat verified both against current code and exact ppol replay; root-only redirection and global environment stripping remain rejected alternatives. No material disagreement. Evidence: `delivery-primer.json`, `docs-architecture-review.json` (council_delivery), and specialist reports. Full framework suite is tracked separately; no pending result is claimed passed.

## Closure Reconciliation

- All five ACs and all tasks are complete; no deferrals.
- Required code, QA, architecture, security, release and docs-contract reviews performed; targeted readiness/delivery councils refreshed at closure.
- Delivered receipt-bound candidate isolation, ordinary live-memory publication, native fresh/interrupted conversion coverage, and source-host-only repair packaging.
- Retrospective: candidate work must not consume live publication authority; archive paths locate content and both supported archive forms need coverage. These rules and tests remain in canonical code/docs.
- Memory proposal returned zero durable candidates; existing fragile-file guidance already covers parent-owned memory authorization.
- Operator explicitly authorized closure, commit and official1.24.0 publication. The close tool owns final statuses/dates and summary.
- Handoff will retain paused waves and native-platform qualification limits; full current receipt is required before close.
