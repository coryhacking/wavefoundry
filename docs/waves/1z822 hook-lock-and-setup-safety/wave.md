# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z822 hook-lock-and-setup-safety`
Title: Hook Lock And Setup Safety

## Objective

<Describe the wave's load-bearing goal in 1–3 sentences — what changes in the project state when this wave closes, and why now. This text is displayed in the dashboard wave card.>

## Changes

Change ID: `1z823-bug edit-hook-gates-bypassed-by-absolute-paths`
Change Status: `implemented`

Change ID: `1z824-bug lock-symlinks-and-timeout-process-trees`
Change Status: `implemented`

Change ID: `1z825-bug fresh-install-resolves-mcp-2`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-27

## Wave Summary

Wave `1z822` (Hook Lock And Setup Safety) delivered 3 changes: Edit Hook Gates Bypassed by Absolute Paths, Lock Files Follow Symlinks and Timeouts Leave Process Trees, and Fresh Installs Resolve MCP 2 and Cannot Start the Server. Notable adjustments during implementation: Lock Files Follow Symlinks and Timeouts Leave Process Trees: Readiness round 1 blocked on F1: the plan claimed `isolated_run` starts children in a new session; it does not (only `isolated_popen` does), and `_mcp_subprocess_run` calls `subprocess.run` directly, so a `killpg` on that premise could signal the server's own group. Amended: `run_with_tree_kill` creates the group itself and signals only `pgid == child pid`. Notes folded in: kill on any exception while waiting, the timed-call scope stated as a rule with the census, Windows refusal only on a positive reparse finding, `O_APPEND`/`O_BINARY` semantics, and AC-1 covering the dangling-symlink case instead of a vacuous `write_metadata` check.

**Changes delivered:**

- **Edit Hook Gates Bypassed by Absolute Paths** (`1z823-bug edit-hook-gates-bypassed-by-absolute-paths`) — 4 ACs completed. Key decisions: One classifier in the shared helpers, used by every prefix check; Implement fail-closed with `sys.excepthook` rather than a `try` statement
- **Lock Files Follow Symlinks and Timeouts Leave Process Trees** (`1z824-bug lock-symlinks-and-timeout-process-trees`) — 4 ACs completed. Key decisions: Refuse a symlinked carrier rather than resolve it; New `run_with_tree_kill`, applied to the two timed call sites
- **Fresh Installs Resolve MCP 2 and Cannot Start the Server** (`1z825-bug fresh-install-resolves-mcp-2`) — 3 ACs completed. Key decisions: Pin `<2` now; migrate to the 2.x API later; Document the guard rather than ship a lock file
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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
| plan | 125 | 3,033,400 |
| implement | 22 | 899,611 |
| review | 44 | 2,374,186 |
| **Total** | **191** | **6,307,197** |

<!-- wave:context-efficiency-state {"generation":132,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":22,"content_source_credit":885405,"derived_artifact_credit":40514,"direct_net":899611,"estimated_tokens_saved":899611,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1864,"response_debit":24444,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":125,"content_source_credit":3168608,"derived_artifact_credit":4205,"direct_net":3033400,"estimated_tokens_saved":3033400,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5044,"response_debit":140880,"source_credit_count":92,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":44,"content_source_credit":2443814,"derived_artifact_credit":41505,"direct_net":2374186,"estimated_tokens_saved":2374186,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2937,"response_debit":110512,"source_credit_count":83,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":191,"content_source_credit":6497827,"derived_artifact_credit":86224,"direct_net":6307197,"estimated_tokens_saved":6307197,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9845,"response_debit":275836,"source_credit_count":200,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1z822 hook-lock-and-setup-safety"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 17 | 0 | 12 | 10,746,172 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":12,"estimated_exploration_avoided":10746172,"surfaced_events":17} -->
<!-- wave:exploration-avoided end -->
