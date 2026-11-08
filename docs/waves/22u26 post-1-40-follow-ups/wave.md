# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-07
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22u26 post-1-40-follow-ups`
Title: Post 1 40 Follow Ups

## Objective

Maintainers and downstream distributions get the post-1.40.0 follow-ups: scanner tests and guidance that stay accurate outside the canonical runner, a discoverable way to record accepted residual risks, every container close fixture routed through the distribution profile, `index_compatibility` importable from a zipped framework, and the uv bootstrap pin at 0.13.5, clear of a published TLS advisory. Scanner policy, the review ledger semantics and how uv is discovered are unchanged.

## Changes

Change ID: `22qr7-debt scanner-review-minor-follow-ups`
Change Status: `implemented`

Change ID: `22r95-enh review-event-accepted-not-repaired`
Change Status: `implemented`

Change ID: `22sfu-debt retained-upgrade-preview-fixture-helper`
Change Status: `implemented`

Change ID: `22u24-enh index-compatibility-zip-import`
Change Status: `implemented`

Change ID: `22u27-maint bump-uv-bootstrap-pin-0-13-5`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-08

## Wave Summary

Wave `22u26` (Post 1 40 Follow Ups) delivered 5 changes: Scanner review minor follow-ups, Record accepted-not-repaired findings through the review-event tool, Route the upgrade-preview close calls through the container fixture helper, Read index producer sources through the module loader, and Bump the uv Bootstrap Pin to 0.13.5. Notable adjustments during implementation: Scanner review minor follow-ups: Scheduled at operator request. Added ACs 5 and 6 for items 4 and 5. Chose `\z`: RE2 reads it as end of text, Python 3.14 accepts it natively, and older Python reaches it through `_re2_to_re`, which `_path_matches_allowlist` does not call today, so a `\z` entry would be silently skipped there.; Record accepted-not-repaired findings through the review-event tool: Readiness feedback applied: Requirement 3 narrowed to `promotion_trigger`; AC-1 marked a regression guard; digest refresh made a task; seed 209 `categorical` wording added (docs-contract review found it disagrees with `review_evidence`'s synthesis check).; Record accepted-not-repaired findings through the review-event tool: Implemented. `review_evidence.PROMOTION_TRIGGER_REJECTION_BASES` used at both validator sites; `review_action_input_schema` lists `promotion_trigger` under `evidence.finding.conditional_fields`; the `wf_review_event` docstring, `docs/specs/mcp-tool-surface.md` and seed 209 (under `seed_edit_allowed`, opened and closed) state the placement and the require/refuse rule; only the `wf_review_event` digest in `register-surface-handler-digests.json` changed. `tests/test_review_event_promotion_trigger.py` 7 OK; `test_mcp_tool_registry.py`, `test_server_tools_retrieval.py` and `test_review_evidence.py` 1312 OK. Mutation probes in a scratch copy: description, seed revert and schema-set drift each fail one test.

**Changes delivered:**

- **Scanner review minor follow-ups** (`22qr7-debt scanner-review-minor-follow-ups`) — 6 ACs completed. Key decisions: Deferred from 22qr6.
- **Record accepted-not-repaired findings through the review-event tool** (`22r95-enh review-event-accepted-not-repaired`) — 4 ACs completed. Key decisions: Document the existing `evidence` placement instead of adding a parameter
- **Route the upgrade-preview close calls through the container fixture helper** (`22sfu-debt retained-upgrade-preview-fixture-helper`) — 3 ACs completed. Key decisions: Convert now rather than wait for a Waveforge report
- **Read index producer sources through the module loader** (`22u24-enh index-compatibility-zip-import`) — 3 ACs completed. Key decisions: Fix `index_compatibility` only
- **Bump the uv Bootstrap Pin to 0.13.5** (`22u27-maint bump-uv-bootstrap-pin-0-13-5`) — 3 ACs completed. Key decisions: Pin 0.13.5 as an exception to the 21-day package-age window
## Watchpoints

- Watchpoint: no ledger writes or file edits during a full suite run; retry the run if the tree changes.
- Open `framework_edit_allowed` before any framework edit, whatever the tool.
- Probe scratch work with `python3 -B`; no framework bytecode.
- The uv pin 0.13.5 is an operator-approved security exception to the 21-day package-age window (2026-11-07).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 22u26-code-uv-tls-advisory | do_now | no | completed | code-reviewer |
| 22u26-qa-unguarded-children | maybe_later | no | completed | qa-reviewer |

*Machine review state — 2 findings; current: do_now 1, maybe_later 1, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 52 | 1,802,633 |
| implement | 42 | 159,053 |
| review | 45 | 548,773 |
| **Total** | **139** | **2,510,459** |

<!-- wave:context-efficiency-state {"generation":133,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":42,"content_source_credit":173690,"derived_artifact_credit":0,"direct_net":159053,"estimated_tokens_saved":159053,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1462,"response_debit":14619,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1444},"plan":{"calls":52,"content_source_credit":1901761,"derived_artifact_credit":5615,"direct_net":1802633,"estimated_tokens_saved":1802633,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25080,"response_debit":85165,"source_credit_count":69,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":45,"content_source_credit":655452,"derived_artifact_credit":9263,"direct_net":548773,"estimated_tokens_saved":548773,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9071,"response_debit":110647,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":139,"content_source_credit":2730903,"derived_artifact_credit":14878,"direct_net":2510459,"estimated_tokens_saved":2510459,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35613,"response_debit":210431,"source_credit_count":108,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10722},"wave_id":"22u26 post-1-40-follow-ups"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
