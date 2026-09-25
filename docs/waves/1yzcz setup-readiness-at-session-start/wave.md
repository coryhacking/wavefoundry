# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yzcz setup-readiness-at-session-start`
Title: Setup Readiness At Session Start

## Objective

Surface setup readiness to the agent at session start so a checkout that needs `wf setup` after a pulled framework update is reported and the operator is asked, and make the setup fingerprint present on upgraded and legacy installs so that report is accurate.

## Changes

Change ID: `1yzcy-enh setup-fingerprint-completeness`
Change Status: `implemented`

Change ID: `1yzcx-enh session-start-setup-readiness-hook`
Change Status: `implemented`
Depends On: `1yzcy-enh setup-fingerprint-completeness`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-09-24

## Wave Summary

Wave `1yzcz` (Setup Readiness At Session Start) delivered two changes: Setup Fingerprint Completeness and Session-Start Setup Readiness Hook. Notable adjustments during implementation: Setup Fingerprint Completeness: Implemented: `projected_environment`, `COMPARED_ENV_KEYS`, `read_setup_stamp`, `write_setup_stamp(provenance, identity, exclusive)`, `adopt_setup_stamp`, `assess_setup(use_stamp)` in `setup_readiness.py`; `_record_setup_baseline` in `upgrade_wavefoundry.phase_cleanup` after lock removal and the lifecycle backstop; `_adopt_setup_baseline` in `server.main` after the dry-run return, gated on a ready status. Deviation from Requirement 2/5 wording: adoption publishes create-only when the stamp is absent and replaces an unreadable or other-schema file (a create-only publish cannot replace it); a readable current-schema stamp is never replaced. New `tests/setup_ready_fixture.py` (subprocess-ready fixture) reused by the hook tests; tests in `test_setup_readiness.py`, `test_setup_stamp_writers.py`, `test_upgrade_wavefoundry.PhaseCleanupSetupBaselineTests`; 17 mutants in evidence/mutants.py all killed (a duplicate-call lock-order mutant was equivalent and was replaced by a move). Docs: domain-map (paragraph and edge row), data-and-control-flow, build-and-verification, mcp-tool-surface, CHANGELOG Fixed and Added. Gapfill: code reads by shell over anchors verified during readiness; Setup Fingerprint Completeness: Delivery repair DEL-STAMP-WRITER-DOCS and non-blocking notes: docs state setup writes after reconciliation and adoption is create-only only when absent; `wf setup` guidance after config edits (RT-DEL-3) in mcp-tool-surface; cleanup logs the skipped baseline when the index update failed (QA-DEL-4); tests for adoption-before-transport ordering (QA-DEL-1), other-schema adoption (QA-DEL-2), upgrade identity guard (QA-DEL-3/RT-DEL-2); readiness tests independent of the runner's pinned provider environment; identity-comparison census updated for the two new comparisons; five mutants added to evidence. Requirement 2/5 `exclusive=True` wording stays superseded by the recorded adoption deviation; Session-Start Setup Readiness Hook: Delivery repair DEL-HOOK-NAME-COLLISION (red-team RT-DEL-1): the hook is renamed `wf-session-start` so the render never deletes or overwrites an operator's own `session-start` hook; regression test renders over operator `session-start{,.sh,.py,.cmd}` files and entries and requires them unchanged (fails against the old name). Also SEC-DEL-1/RT-DEL-4: an overlong recommended command is replaced by a pointer to `wf setup --check` instead of being cut. Seeds 050/160 updated under the seed gate; this repository's never-shipped old entry and body removed by hand before re-render.

**Changes delivered:**

- **Setup Fingerprint Completeness** (`1yzcy-enh setup-fingerprint-completeness`) — 8 ACs completed. Key decisions: Write the stamp from a live ready assessment at upgrade cleanup and adopt a missing one at MCP startup; Compare only operator-controlled, setup-relevant environment fields
- **Session-Start Setup Readiness Hook** (`1yzcx-enh session-start-setup-readiness-hook`) — 6 ACs completed. Key decisions: Agent-host session-start hook, report and ask; Claude Code only
## Watchpoints

- Watchpoint: nothing may run setup automatically (operator decision 2026-09-24, `1y3hc` rule); the hook and `wf setup --check` stay read-only.
- Watchpoint: adoption must never replace a readable current-schema stamp.
- Watchpoint: no git hooks are introduced.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-HOOK-NAME-COLLISION | do_now | no | completed | — |
| DEL-STAMP-WRITER-DOCS | do_now | no | completed | — |

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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 51 | 810,764 |
| implement | 8 | 0 |
| review | 22 | 233,452 |
| **Total** | **81** | **1,044,216** |

<!-- wave:context-efficiency-state {"generation":51,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":8,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-396,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36,"response_debit":360,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":51,"content_source_credit":908752,"derived_artifact_credit":4222,"direct_net":810764,"estimated_tokens_saved":810764,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3882,"response_debit":102137,"source_credit_count":73,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":22,"content_source_credit":291691,"derived_artifact_credit":3461,"direct_net":233452,"estimated_tokens_saved":233452,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7906,"response_debit":56110,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":81,"content_source_credit":1200443,"derived_artifact_credit":7683,"direct_net":1043820,"estimated_tokens_saved":1044216,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11824,"response_debit":158607,"source_credit_count":113,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6125},"wave_id":"1yzcz setup-readiness-at-session-start"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 388,974 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":388974,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
