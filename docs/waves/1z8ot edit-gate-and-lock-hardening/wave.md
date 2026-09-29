# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-28
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8ot edit-gate-and-lock-hardening`
Title: Edit Gate And Lock Hardening

## Objective

Every Claude edit tool runs the edit gates, edit payloads the gates cannot read are blocked, lock writes cannot be redirected through symlinked directories, and onnxruntime telemetry is disabled.

## Changes

Change ID: `1z8op-bug claude-edit-hook-coverage`
Change Status: `complete`

Change ID: `1z8oq-bug lock-paths-refuse-symlinked-directories`
Change Status: `complete`

Change ID: `1z8or-bug disable-onnxruntime-telemetry`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-09-28

## Wave Summary

Wave `1z8ot` (Edit Gate And Lock Hardening) delivered 3 changes: Claude Edit Hooks Cover Every Edit Tool and Fail Closed, Lock Paths Refuse Symlinked Directories, and Disable onnxruntime Telemetry. Notable adjustments during implementation: Claude Edit Hooks Cover Every Edit Tool and Fail Closed: Readiness review. B1 adopted: seeds 050 and 160 state the matcher and are in scope. N1: the Copilot gate may be inert; AC-4 requires cited per-host fixtures, Copilot first. N2: strict parse is pre-edit only, with a tool-name rule. N3: Windsurf uses `maybe_trigger_reindex` and has no reindex today. N4: MCP write tools added as a limit; limits live in seed 050, with `threat-model.md` rows pointing at them. N5: host hook paths added; re-render only after a subprocess test; Disable onnxruntime Telemetry: Readiness review. On a scratch onnxruntime 1.29.0 venv: 9 files under the home without the variable; nothing with `1`; telemetry with `0` or an empty string; no effect when set after import. `disable_telemetry_events` exists in 1.27 and 1.29. The tool venv has 1.27.0, so AC-2 needs recorded 1.29 evidence (N9). Adopted N10 (empty counts as unset) and N11 (`embed_bench` added, scan test, helper on every platform).

**Changes delivered:**

- **Claude Edit Hooks Cover Every Edit Tool and Fail Closed** (`1z8op-bug claude-edit-hook-coverage`) — 7 ACs completed. Key decisions: Fail closed on unparseable and pathless edit payloads, with a pre-edit-only parser; State the limits in seed 050 and point `threat-model.md` at it
- **Lock Paths Refuse Symlinked Directories** (`1z8oq-bug lock-paths-refuse-symlinked-directories`) — 6 ACs completed. Key decisions: No exception for a relocated index symlink; Find the boundary lexically at the last `.wavefoundry` component
- **Disable onnxruntime Telemetry** (`1z8or-bug disable-onnxruntime-telemetry`) — 5 ACs completed. Key decisions: Set the variable in `venv_bootstrap`; call the helper on every platform; Treat an empty value as unset and keep any other value
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-F1 | do_now | no | completed | — |
| DEL-F2 | do_now | no | completed | — |
| DEL-F3 | do_now | no | completed | — |
| DEL-F4 | do_now | no | completed | code-reviewer, qa-reviewer, security-reviewer |
| DEL-F5 | do_now | no | completed | code-reviewer, docs-contract-reviewer |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 29 | 357,686 |
| implement | 105 | 2,256,214 |
| review | 92 | 1,268,996 |
| **Total** | **226** | **3,882,896** |

<!-- wave:context-efficiency-state {"generation":206,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":105,"content_source_credit":2317647,"derived_artifact_credit":1553,"direct_net":2256214,"estimated_tokens_saved":2256214,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5401,"response_debit":61019,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3434},"plan":{"calls":29,"content_source_credit":388047,"derived_artifact_credit":6106,"direct_net":357686,"estimated_tokens_saved":357686,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2475,"response_debit":40503,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":92,"content_source_credit":1484223,"derived_artifact_credit":3027,"direct_net":1268996,"estimated_tokens_saved":1268996,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19753,"response_debit":200817,"source_credit_count":90,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":226,"content_source_credit":4189917,"derived_artifact_credit":10686,"direct_net":3882896,"estimated_tokens_saved":3882896,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":27629,"response_debit":302339,"source_credit_count":212,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12261},"wave_id":"1z8ot edit-gate-and-lock-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 6 | 2,298,133 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":2298133,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
