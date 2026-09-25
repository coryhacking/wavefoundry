# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yzd0 server-package-boundary`
Title: Server Package Boundary

## Objective

Move the server composition root, response handlers and tool registry into a `wf_server` package with flat compatibility modules, so the server has an explicit ownership boundary and a stable downstream integration surface without changing any public MCP contract, reload behavior or upgrade path.

## Changes

Change ID: `1yxql-ref server-package-boundary`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-09-25

## Wave Summary

Wave `1yzd0` (Server Package Boundary) delivered one change: Server Package Boundary. Notable adjustments during implementation: Server Package Boundary: Readiness round 1 (receipt `review-policy-32c232e62ee9cf27fdb2`): security and release approve; red-team, code, QA, docs-contract and architecture block. One bounded repair: harness-coherence carve-out; framework-file enumeration helper and census plus the full test-seam list; alias table pinned in `server_impl` with guarded eager registration; frozen `SOURCE_FILES` scope; exact alias bytes; evaluator workflow doc, receipts and doc-citation census; E0 as its own reviewed, operator-committed step with an E1 recovery path and exclusive alias matching; memory-record retargeting; AC-2 scoped to the runner path; AC-5 fixture sourcing; Server Package Boundary: Package renamed `wf_server` by operator decision; independent rename verification approves (completeness, shadowing demo, `find_spec` absence, no framework collision). Implementation note for the move (RENAME-1): add `wf_server` to `mcp_tool_extensions.RESERVED_MODULE_NAMES` so a conflicting extension declaration is refused at validation, not only at load; Server Package Boundary: M then E2: the incremental update and graph rebuild resolve every moved definition to its package file (definition counts identical per module, e.g. 550 for `server_impl`), 248 handler-to-`server_impl` call edges before and after, no flat-path definition ownership left, alias modules kept; live `code_definition` after `wf_reload_mcp` answers package paths. E2 `docs/reports/retrieval-quality-1yzd0-e2b.json`: `pass` against E1, same evaluator identity and fixture digest, no violations, zero metric differences. A first E2 attempt ran while the scratch baseline graph build shared the machine and reported only latency (quality identical); it and the two E1 attempts are not evidence and were removed from `docs/reports`.

**Changes delivered:**

- **Server Package Boundary** (`1yxql-ref server-package-boundary`) — 8 ACs completed. Key decisions: Select a server-owned package with retained flat compatibility/declarations; Proposed package name wavefoundry_server; preserve server.py (renamed `wf_server` on 2026-09-25, below)
## Watchpoints

- Watchpoint: no source edit before readiness freezes the module inventory and demonstrates the alias/reload strategy in disposable fixtures.
- Watchpoint: one module instance per implementation; flat aliases never execute a second copy.
- Watchpoint: distribution declarations (`mcp_tool_extensions.py`, `mcp_tool_roster.py`, `record_paths.py`) stay flat.
- Watchpoint: evaluator identity is inventoried before any retrieval measurement.

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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 24 | 40,289 |
| implement | 58 | 15,620 |
| review | 62 | 1,128,248 |
| **Total** | **144** | **1,184,157** |

<!-- wave:context-efficiency-state {"generation":126,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":58,"content_source_credit":58914,"derived_artifact_credit":2913,"direct_net":15620,"estimated_tokens_saved":15620,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4152,"response_debit":44437,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2382},"plan":{"calls":24,"content_source_credit":78610,"derived_artifact_credit":2932,"direct_net":40289,"estimated_tokens_saved":40289,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2615,"response_debit":42447,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":62,"content_source_credit":1237153,"derived_artifact_credit":4657,"direct_net":1128248,"estimated_tokens_saved":1128248,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5325,"response_debit":110553,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":144,"content_source_credit":1374677,"derived_artifact_credit":10502,"direct_net":1184157,"estimated_tokens_saved":1184157,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12092,"response_debit":197437,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8507},"wave_id":"1yzd0 server-package-boundary"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 60,668 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":60668,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
