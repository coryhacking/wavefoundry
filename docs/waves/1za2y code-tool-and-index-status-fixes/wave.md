# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1za2y code-tool-and-index-status-fixes`
Title: Code Tool And Index Status Fixes

## Objective

Code-navigation tools stop serving unfiltered files after framework edits and match `**/` globs across zero directories; index build status stops calling finished builds running and stops releasing the server's own build lock; and the last timed git call left unrouted in 1z8ox ends its process tree, with both graph-quality reports re-measured.

## Changes

Change ID: `1z9u7-bug navigation-walker-fallback-leaks-unfiltered-files`
Change Status: `complete`

Change ID: `1z9ya-bug code-tool-glob-double-star-skips-top-level`
Change Status: `complete`

Change ID: `1z9yb-bug index-build-status-false-running-and-self-lock-release`
Change Status: `complete`
Depends On: `1z9u7-bug navigation-walker-fallback-leaks-unfiltered-files`

Change ID: `1za2x-debt graph-quality-probe-tree-kill-remeasure`
Change Status: `complete`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-09-29

## Wave Summary

Wave `1za2y` (Code Tool And Index Status Fixes) delivered 4 changes: Code Navigation Never Walks Unfiltered Files, Code Tool Globs Match `**/` Across Zero Directories, Index Build Status Neither Misreports Nor Releases the Build Lock, and Graph-Quality Evaluator's Git Probe Ends Its Process Tree. Notable adjustments during implementation: Code Navigation Never Walks Unfiltered Files: Implemented. `_indexer_module()` returns `_load_script("indexer")` and keeps the last good module under `sys.modules["_wavefoundry_indexer_last_good"]`; the rglob fallback is removed; `_walk_repo_for_navigation` raises `NavigationWalkerUnavailable` (converted by the tool wrapper to a `navigation_indexer_unavailable` error, including the `code_impact` heuristic path) and records an `index_runtime_stale` warning from a stat-signature cache over the index producer sources; `register_mcp_surface` loads the indexer at start; the lock-owner read in `index_handlers.py` uses the shared module. Scratch mutants: restoring the old rglob fallback fails `MissingIndexerTests` for every tool in `TOOL_CALLS` and the source pin in `SharedModuleTests`; dropping the stale notice fails `StaleRuntimeTests` for every tool and `WrapperMechanismTests`; forcing a rehash on every call fails `FreshnessCacheTests`. Gapfill: call sites were enumerated with grep and AST walks, not `code_references`, because the index runtime these tools depend on is the one being changed and `code_keyword` globs had the `**/` defect fixed by 1z9ya; Code Navigation Never Walks Unfiltered Files: Readiness review folded in: `_indexer_module` returns the cached module (shared with 1z9yb), every fresh indexer execution removed, startup load, stat-cached freshness check, affected tools derived through to the public tools, spec contract.; Index Build Status Neither Misreports Nor Releases the Build Lock: Delivery repair round 2, DEL-F3 (operator review, blocking): `_index_build_lock` unlinked a lock file whose metadata looked stale before its own acquire, so a contender refused because another build had just locked that inode had already deleted the carrier, and a third process locked a fresh file alongside the running build (AC-3). The unlink is removed in `indexer._index_build_lock`: the carrier is never deleted and `write_metadata` truncates and rewrites the same inode after acquire, which keeps wave 1p2q3's goal (status never shows the dead owner). `test_indexer.test_stale_lock_file_is_unlinked_before_acquire` (which pinned a fresh inode) is replaced by `test_stale_lock_file_is_reused_and_its_metadata_replaced`; new cross-process test `test_a_refused_acquire_never_replaces_a_held_carrier` (holder process with dead-pid metadata; contender refused; inode unchanged; third-process lockf probe still held) and the review's interleaving as `test_a_contender_paused_after_classifying_stale_keeps_the_hold` (contender paused after classifying stale, another thread acquires, external exclusion checked throughout). Scratch mutant restoring the unlink fails all three. `chunking-and-indexing-pipeline.md` last-owner paragraph and the CHANGELOG 1za2y status bullet updated. No other code deletes `index-build.lock` (census: unlink/os.remove/rmtree near lock in non-test scripts; the upgrade runner's unlink is the separate legacy root lock).

**Changes delivered:**

- **Code Navigation Never Walks Unfiltered Files** (`1z9u7-bug navigation-walker-fallback-leaks-unfiltered-files`) — 6 ACs completed. Key decisions: Recommend restarting the MCP server, not `wf_reload_mcp`; Use the walker the server already loaded, with a stale-runtime warning
- **Code Tool Globs Match `**/` Across Zero Directories** (`1z9ya-bug code-tool-glob-double-star-skips-top-level`) — 4 ACs completed. Key decisions: One shared matcher where `**/` also matches zero directories, keeping every current match
- **Index Build Status Neither Misreports Nor Releases the Build Lock** (`1z9yb-bug index-build-status-false-running-and-self-lock-release`) — 7 ACs completed. Key decisions: Share one indexer module (via 1z9u7), record ownership there, refuse a second in-process acquire; Track in-process ownership and skip the probe while held; reuse the reap-and-command-line liveness check
- **Graph-Quality Evaluator's Git Probe Ends Its Process Tree** (`1za2x-debt graph-quality-probe-tree-kill-remeasure`) — 6 ACs completed. Key decisions: Post report takes the live graph-source hashes; Route in place and re-measure both reports
## Watchpoints

- Watchpoint: 1z9u7 and 1z9ya both edit `wf_server/codenav_handlers.py`; implement 1z9u7 first.
- Watchpoint: 1z9yb depends on 1z9u7's shared indexer module (`_indexer_module()` returning the cached module); implement 1z9u7 before 1z9yb.
- Watchpoint: 1za2x edits the shipped graph-quality reports; re-measure them last, after every other framework edit, and never hand-edit a report field.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: 1z9yb's in-process ownership flag would be invisible to the lock status path, which re-executed indexer.py per call, so the probe would keep releasing the lock; strongest-alternative: make server_impl._indexer_module return the cached _load_script module, fixing the per-call re-execution for navigation and lock status together, adopted into 1z9u7 and 1z9yb). Security seat: BLOCK on S1 (invisible flag) and S2 (incomplete opener list, second in-process acquire), both folded into 1z9yb; advisories S3, S4, S6 folded into 1z9u7 and 1z9ya. Red-team seat: PASS; R1 (pin controls and bounds) folded into 1za2x. Docs-contract seat (rotating after seed 140 joined the targets): D1 to D3 folded into 1z9yb, 1za2x and 1z9u7.
- **Prepare-phase Wave Council [prepare-council] — 2026-09-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: keeping a last-good indexer after a producer edit runs the old walker's filter rules until restart, with only a warning; strongest-alternative: measure the post graph-quality report from the 5a30d7a5 scripts to keep its production hashes, rejected because it would certify graph code that no longer ships). Re-readiness after plan corrections to 1z9u7 and 1za2x; docs-contract F2 (reload wording) fixed before approval.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-F1 | do_now | no | completed | — |
| DEL-F2 | do_now | no | completed | — |
| DEL-F3 | do_now | no | completed | code-reviewer, qa-reviewer, security-reviewer, architecture-reviewer, wave-council-delivery |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 63 | 1,123,343 |
| implement | 16 | 41,731 |
| review | 66 | 1,115,236 |
| **Total** | **145** | **2,280,310** |

<!-- wave:context-efficiency-state {"generation":113,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":16,"content_source_credit":58002,"derived_artifact_credit":1495,"direct_net":41731,"estimated_tokens_saved":41731,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3030,"response_debit":14736,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":63,"content_source_credit":1198383,"derived_artifact_credit":6109,"direct_net":1123343,"estimated_tokens_saved":1123343,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3498,"response_debit":84162,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":66,"content_source_credit":1247817,"derived_artifact_credit":3643,"direct_net":1115236,"estimated_tokens_saved":1115236,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15387,"response_debit":123153,"source_credit_count":65,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":145,"content_source_credit":2504202,"derived_artifact_credit":11247,"direct_net":2280310,"estimated_tokens_saved":2280310,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":21915,"response_debit":222051,"source_credit_count":120,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1za2y code-tool-and-index-status-fixes"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 2 | 553,374 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":553374,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
