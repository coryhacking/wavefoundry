# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yzj9 sensor-advisory-decisions`
Title: Sensor Advisory Decisions

## Objective

Record, on field data, that the AC-locality docs-lint sensor stays advisory, and give the sensor registry a standing-decision field so the warning text and release checklist stop describing a pending flip.

## Changes

Change ID: `1yzj8-maint ac-locality-sensor-stays-advisory`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-25

## Wave Summary

Wave `1yzj9` (Sensor Advisory Decisions) delivered one change: Keep the AC-Locality Sensor Advisory by Recorded Decision. Notable adjustments during implementation: Keep the AC-Locality Sensor Advisory by Recorded Decision: Delivery repairs. DOCS-DEL-1: `change-workflow.md` and the `_AC_SCOPE_GAP_WORD` comment no longer say the rule is meant to block one day (seed 170 wording reused, absence pinned). QA-DEL-2: the CHANGELOG pin read only the first section and would fail at the release rollover; it now checks the whole history through `_changelog_records_the_decision`, with a rollover regression test that also proves removal still fails; Keep the AC-Locality Sensor Advisory by Recorded Decision: Implemented. `SENSOR_POLARITY_REGISTRY` entries `ac_asserts_repository_state` and `inert_record_layout_config` carry `decided_wave: 1yzj9`; `_route_sensor_findings` validates `decided_wave` (non-empty string, advisory only) before any branch on findings or the sink and emits the decided suffix; seed 170 (under the gate), `plan-feature.prompt.md`, the release checklist, `change-workflow.md`, `testing-architecture.md`, the `constants.py` comment, the sensor docstring and a CHANGELOG bullet state the decision. Readiness notes applied: shipped text describes the drop as an observed decline, not proven causation, and the CHANGELOG scopes the figures to this repository and makes no claim about consumer test health. Tests: CLI decided suffix, undecided suffix unchanged in-process, invalid `decided_wave` cases with and without findings or sink, both registry entries, prose pins; `test_docs_lint` 1117 OK. Mutation probe 8/8 killed by assertions. Full suite 9672 OK. Gapfill: the edits are a small validation branch plus prose in named files, located by the plan's exact anchors and read directly, so MCP retrieval added nothing.

**Changes delivered:**

- **Keep the AC-Locality Sensor Advisory by Recorded Decision** (`1yzj8-maint ac-locality-sensor-stays-advisory`) — 3 ACs completed. Key decisions: Keep the AC-locality sensor advisory permanently; Supersede the flip condition recorded by `1wujs` (field data from at least one release with no false-positive report, decided at the release checklist)
## Watchpoints

- Watchpoint: no sensor changes polarity, detection or scope.
- Watchpoint: undecided advisory sensors keep today's warning suffix and stay on the release checklist.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DOCS-DEL-1 | do_now | no | completed | — |
| QA-DEL-2 | do_now | no | completed | qa-reviewer, code-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| accounting_gap | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":61,"measurement_status":"accounting_gap","pending":false,"schema_version":1,"stages":{"implement":{"calls":19,"content_source_credit":2942,"derived_artifact_credit":0,"direct_net":-2699,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":792,"response_debit":6983,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2134},"plan":{"calls":21,"content_source_credit":760282,"derived_artifact_credit":1292,"direct_net":728559,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1900,"response_debit":36519,"source_credit_count":21,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5404},"review":{"calls":19,"content_source_credit":238447,"derived_artifact_credit":1035,"direct_net":194927,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3485,"response_debit":41070,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":59,"content_source_credit":1001671,"derived_artifact_credit":2327,"direct_net":920787,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6177,"response_debit":84572,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7538},"wave_id":"1yzj9 sensor-advisory-decisions"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 485,855 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":485855,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
