# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1t1uo dashboard-multiline-ac-tasks`
Title: Dashboard Multiline Ac Tasks

## Objective

Restore complete AC and task text in dashboard detail dialogs by preserving
hard-wrapped Markdown list-item continuation lines in the backend snapshot.

## Changes

Change ID: `1t1un-bug dashboard-ac-task-continuation-lines`
Change Status: `complete`

Completed At: 2026-07-20

## Wave Summary

Wave `1t1uo` (Dashboard Multiline Ac Tasks) delivered one change: Dashboard AC and Task Continuation Lines.

**Changes delivered:**

- **Dashboard AC and Task Continuation Lines** (`1t1un-bug dashboard-ac-task-continuation-lines`) — 7 ACs completed. Key decisions: Repair backend list-item extraction, not CSS or frontend rendering.; Use a small bounded section-list helper rather than a full Markdown parser.
## Journal Watchpoints

- Open `framework_edit_allowed` before changing dashboard backend or tests and
  close it after verification.
- Preserve sibling boundaries and existing checkbox/deferred/priority/count
  semantics while joining only genuine continuation lines.
- Do not solve missing backend text with a frontend or CSS workaround.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a shared starter rule could accidentally introduce ordered-task support and continuation parsing could absorb unrelated structural prose; strongest-alternative: use caller-specific starters plus an indentation- and structure-bounded continuation grammar with executable extracted-package and post-upgrade probes.)
- red-team: PASS — ACs retain `-`/`N.` starters, Tasks retain `-` only, and structural boundaries are explicit.
- docs-contract-reviewer: PASS — package/install/upgrade execution, CSS scope, Wave metadata, and positive/negative fixtures are explicit.
- **Delivery review cycle 1 [delivery-review-1] — 2026-07-20: CHANGES REQUESTED** (technical attack review reproduced two parser defects: common indentation was skewed by section-edge stripping, and pipe-less Markdown tables were absorbed as prose. Both repairs are implemented and under independent re-verification.)
- **Delivery review cycle 2 [delivery-review-2] — 2026-07-20: PASS (technical + QA + docs/release)** (the exact common-indentation and pipe-less-table attacks close; adjacent ordered-task, nested-list, inline-pipe, Setext-heading, thematic-break, scale, snapshot, frontend, package/install, and post-upgrade probes pass. The live dashboard was restarted and independently confirmed to serve the new parser. Docs/release re-verification closed the historical-wording and edit-gate findings; docs lint and diff hygiene are clean.)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 5 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
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
| plan | 235 | 3,032,657 |
| implement | 1 | 1,210 |
| review | 5 | 523 |
| **Total** | **241** | **3,034,390** |

<!-- wave:context-efficiency-state {"generation":13,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"direct_net":1210,"estimated_tokens_saved":1210,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9,"response_debit":206,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1425},"plan":{"calls":235,"content_source_credit":3719572,"direct_net":3032657,"estimated_tokens_saved":3032657,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8172,"response_debit":681929,"source_credit_count":153,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3186},"review":{"calls":5,"content_source_credit":0,"direct_net":-392,"estimated_tokens_saved":523,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":50,"response_debit":1378,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1036}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":241,"content_source_credit":3719572,"direct_net":3033475,"estimated_tokens_saved":3034390,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8231,"response_debit":683513,"source_credit_count":153,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5647},"wave_id":"1t1uo dashboard-multiline-ac-tasks"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
