# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yxyw retire-optional-server-aliases`
Title: Retire Optional Server Aliases

## Objective

Retire the ten optional flat server aliases that wave `1yzd0` kept for internal convenience, so `wf_server` modules have one spelling except the two (`server_impl`, `dashboard_handlers`) that installed 1.25/1.26 upgrade runners require.

## Changes

Change ID: `1yxwn-ref retire-optional-flat-server-aliases`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, release-reviewer, docs-contract-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-09-25

## Wave Summary

Wave `1yxyw` (Retire Optional Server Aliases) delivered one change: Retire The Ten Optional Flat Server Aliases. Notable adjustments during implementation: Retire The Ten Optional Flat Server Aliases: Operator-requested latency rerun (e4b, receipt not retained) against e3 (identical production digest and evaluator): zero quality violations, operator review for latency only (`code_ask` 6339 ms, `code_search` 1138 ms vs e3 4906 and 837). Identical code measured both fast and slow, so the latency is run-to-run variance, not this change. The first attempt (e4) was refused as `stale_index` after the reconnected MCP server's projection rewrote `wave.md`, and was removed. Both slow runs used `--baseline` and both fast runs were standalone (two samples each), noted for a separate look. Operator signed off and asked to close; Retire The Ten Optional Flat Server Aliases: Removal implemented and verified. Baseline `docs/reports/retrieval-quality-1yxyw-e1.json` on committed `85e6310c` (generation 2132, verdict `baseline`, bound to HEAD, clean worktree). Removal: `_RETIRED_FLAT_NAMES`, narrowed `_FLAT_ALIASES`, both-set purge, `retired_flat_leftovers` reported as a `wf_server_info` diagnostic and on stderr at surface registration, report-only `upgrade_extensions.post_pruning` with its own pinned name list; ten alias files deleted; `memory_cli.py`, `project_context_efficiency.py` and 17 test files switched to `wf_server.*` names; census with the stated predicate and controls, allowlisting the four tables and the two purge-pinning tests. Full suite 9669 tests OK. Mutation probe 14/14 killed by assertions. Upgrade matrix (installed runners, paths with spaces): proven prune pruned 10 items from v1.26.0 and 902f7edc and none from v1.25.0; unproven prune kept all 10, and the hook, stderr and `wf_server_info` each warned; every case reached `--dry-run` and stdio `wf_server_info` ok. In-process reload from v1.26.0, 902f7edc and 599039d9 hosts served an edited handler with one live module object per moved module and no stale flat module. Fresh install carries only the two aliases. Graph ownership unchanged except `server_impl` +2 definitions; 248 handler call edges unchanged. After receipt `docs/reports/retrieval-quality-1yxyw-e2c.json`: same evaluator and fixture digest, 27 fixture keys, zero quality violations, `operator_review_required` for latency only, attributed to sustained machine load (load average 8 to 11 from long-running processes outside this work). Two earlier E2 attempts were invalid and removed: a concurrent background index build (`index_not_ready`), then a comment edit to `retrieval_eval.py` that changed evaluator identity; the comment was set aside for the run and reapplied after it (AST-identical). Deviation: AC-3's known-bad full flat copy is a copy of the package implementation rather than the `902f7edc` file, since tests do not read git history; the matrix and reload probe use the real `902f7edc` tree. Gapfill: the patch-target and import rewrites across tests were bulk-mechanical, done with scripted replacements and checked by the census and full suite rather than MCP retrieval.

**Changes delivered:**

- **Retire The Ten Optional Flat Server Aliases** (`1yxwn-ref retire-optional-flat-server-aliases`) — 6 ACs completed. Key decisions: Keep `server_impl` and `dashboard_handlers` flat; Guard the retired names with `_RETIRED_FLAT_NAMES` (refuse, purge, reserve); refuse narrowed to warn by the operator decision below
## Watchpoints

- Watchpoint: implementation starts only after wave `1yzd0` closes (operator instruction, 2026-09-25); readiness may complete before that.
- Watchpoint: the evaluator step is its own reviewed, operator-committed step before any alias is removed.
- Watchpoint: `server_impl.py` and `dashboard_handlers.py` stay flat and byte-identical.
- Watchpoint: no pack is cut and no version is tagged from a tree containing wave `1yzd0` without this change; both ship in one release.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DOCS-DEL-1 | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 35 | 8,140 |
| implement | 43 | 153,312 |
| review | 56 | 869,322 |
| **Total** | **134** | **1,030,774** |

<!-- wave:context-efficiency-state {"generation":141,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":43,"content_source_credit":202723,"derived_artifact_credit":1583,"direct_net":153312,"estimated_tokens_saved":153312,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4392,"response_debit":49698,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3096},"plan":{"calls":35,"content_source_credit":35980,"derived_artifact_credit":1859,"direct_net":8140,"estimated_tokens_saved":8140,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3537,"response_debit":32673,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":56,"content_source_credit":984377,"derived_artifact_credit":2433,"direct_net":869322,"estimated_tokens_saved":869322,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8632,"response_debit":111172,"source_credit_count":48,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":134,"content_source_credit":1223080,"derived_artifact_credit":5875,"direct_net":1030774,"estimated_tokens_saved":1030774,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16561,"response_debit":193543,"source_credit_count":84,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11923},"wave_id":"1yxyw retire-optional-server-aliases"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 11 | 0 | 8 | 5,684,142 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":5684142,"surfaced_events":11} -->
<!-- wave:exploration-avoided end -->
