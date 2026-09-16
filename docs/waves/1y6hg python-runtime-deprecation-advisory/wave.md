# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y6hg python-runtime-deprecation-advisory`
Title: Python Runtime Deprecation Advisory

## Objective

Recommend Python3.13+ with once-only entry-point warnings for3.11/3.12, retaining execution and health behavior.

## Changes

Change ID: `1y61c-enh python-runtime-deprecation-advisory`
Change Status: `complete`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer (runtime/tests); coordinator (docs and isolated transition verification)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-16

## Wave Summary

Wave `1y6hg` (Python Runtime Deprecation Advisory) delivered one change: Warn once for deprecated Python runtimes.

**Changes delivered:**

- **Warn once for deprecated Python runtimes** (`1y61c-enh python-runtime-deprecation-advisory`) — 5 ACs completed. Key decisions: Emit notices at wf and the separate direct MCP entry only; Keep shared advisory classification pure and nonblocking
## Watchpoints

- Watchpoint: setup nests MCP dry-run; retain one notice. Shared environment replacement belongs to existing setup, never advisory emission.

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
| plan | 60 | 728,321 |
| implement | 4 | 240 |
| review | 48 | 431,315 |
| **Total** | **112** | **1,159,876** |

<!-- wave:context-efficiency-state {"generation":84,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":4,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":240,"estimated_tokens_saved":240,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":174,"response_debit":1489,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1903},"plan":{"calls":60,"content_source_credit":807982,"derived_artifact_credit":1097,"direct_net":728321,"estimated_tokens_saved":728321,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5124,"response_debit":79241,"source_credit_count":35,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3607},"review":{"calls":48,"content_source_credit":523270,"derived_artifact_credit":1373,"direct_net":431315,"estimated_tokens_saved":431315,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5539,"response_debit":89791,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":112,"content_source_credit":1331252,"derived_artifact_credit":2470,"direct_net":1159876,"estimated_tokens_saved":1159876,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10837,"response_debit":170521,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7512},"wave_id":"1y6hg python-runtime-deprecation-advisory"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 2 | 944,296 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":944296,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

Operator selected entry-owned once-only warnings and authorized Prepare/review/implementation. Previous test-only wave1y4j8 is paused, not closed. Standard red-team primer found nested dry-run duplicate risk and existing shared-venv replacement semantics; plan revised before readiness. Independent architecture/security and code/QA/docs seats verify source contracts; runtime implementer owns code/tests, coordinator owns docs. No commit, close or release requested.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: setup nests MCP dry-run and must not duplicate warning; strongest-alternative: CLI-only misses direct MCP users). Independent architecture/security advisory and QA/docs seats approved corrected PATH/shared-environment constraints. Moderator15readiness controls preserve formatting/exit/nooutput for3statuses; badreason/status variants rejected. Typedreadiness and allfourlanes approved; activation succeeded.

- **Delivery Council — PASS, 2026-09-16.** Standard red-team primer; architecture reviewer plus independent code/QA/docs reviewer; rotating docs-contract seat. All three challenges resolved: nested dry-run silence, nonblocking readiness, and interpreter/shared-environment guidance. No material disagreements or unresolved findings. Frozen21-file aggregate `2f03d09540d49dd73bca0de72c4b5baf8f46650c54c152a62b6665d9ea7e02d7`; independent Python3.11/3.13 controls and bad-count/status/policy mutants rejected. Transport construction stubbed; full implementation hot reload partly source-inferred; no nativeWindows/Linux/full model setup qualification. Final framework suite pending. Memory proposal produced zero candidates.

- **Verification completion:** docs gate clean; all AC/tasks complete. Two full9104-test runs exposed sandbox dashboard limitations and then unchanged timing flakiness (184ms/150ms); dashboard passed with host access, all86TechDocs tests passed independently. No fresh all-green test receipt claimed. Wave remains implementing, awaiting operator closure authorization and a current green receipt; no commit/push performed.

## Closure reconciliation

Operator explicitly authorized closure on 2026-09-16 after reviewing the delivery summary. All changes are complete and all AC/task checkboxes are checked; none deferred. Code, QA, architecture, docs-contract and readiness/delivery council approvals are recorded and current; no unresolved findings or moving-tree issue. Docs-contract review was performed for the changed MCP spec. Retrospective and memory capture are complete, with zero new candidates and durable guidance in canonical docs. The closure tool will write final chronology after the fresh suite receipt and docs gate pass; handoff will then record idle state while preserving paused wave1y4j8. No commit or push authorized.

- **Final closure validation:** the unchanged complete suite passed9104tests across95files,12skips, in655.088s with two concurrent workers and host process/socket access. No threshold or test changed. The runner wrote a fresh green framework receipt. Docs gate and prior close preview passed all other checks; operator closure is authorized.
