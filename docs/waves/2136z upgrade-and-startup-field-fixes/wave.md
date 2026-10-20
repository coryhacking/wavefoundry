# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2136z upgrade-and-startup-field-fixes`
Title: Upgrade And Startup Field Fixes

## Objective

Upgrades leave no stray rollback record after success, a graph-only build no longer refuses on an embedding precision it does not use, and deployments can turn off MCP startup installs with one environment variable. Default behaviour is otherwise unchanged.

## Changes

Change ID: `2134y-bug bridge-rollback-record-left-after-upgrade`
Change Status: `implemented`

Change ID: `2134z-bug graph-only-build-precision-refusal`
Change Status: `implemented`

Change ID: `2136x-enh mcp-startup-install-opt-out`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `2136z` (Upgrade And Startup Field Fixes) delivered 3 changes: Remove the bridge rollback record after a successful upgrade, Graph-only builds must not apply the embedding precision guard, and An environment switch to turn off MCP startup installs. Notable adjustments during implementation: Remove the bridge rollback record after a successful upgrade: Implemented: `_remove_bridge_rollback_record` in `upgrade_wavefoundry.py`, called in `phase_cleanup` after the lock-release branches (beside the "Upgrade lock removed" log); lstat, missing record tolerated, `contained_files.unlink_contained` with the lstat identity, any refusal or OS error only warns and leaves the entry. Ignore rule added to `_GITIGNORE_BLOCK`; repo `.gitignore` re-rendered with `render_platform_surfaces.render_gitignore_block` (one added line). Seed 050's verbatim copy of the block still needs the same line under `seed_edit_allowed` (left to the coordinator), so `test_seed_050_canonical_block_matches_the_renderer_constant` fails until then. Old-code window: a 1.32 runner will not remove the record; the next successful upgrade on new code does. Windows/macOS/Linux/WSL2: same path through the contained file operations; the symlink test skips where symlinks are unavailable.; Remove the bridge rollback record after a successful upgrade: Coordinator: added `.wavefoundry/framework/BRIDGE-ROLLBACK.json` to seed 050's canonical gitignore block (seed gate opened and closed around the one-line edit) so `test_seed_050_canonical_block_matches_the_renderer_constant` matches the renderer list; CHANGELOG bullet added. Combined focused run (test_upgrade_wavefoundry, test_render_platform_surfaces, test_indexer, test_startup_install, test_inference_provider, test_upgrade_protocol): 1430 OK.; Graph-only builds must not apply the embedding precision guard: Implemented. `build_index` skips the implicit precision guard for graph-only content (guard factored into `_implicit_precision_refusal`); the model-set escalation widens a graph-only build only on a model-name change; when a graph-only build is widened to embed (model-name or 1sed6 unprovenanced escalation) the guard is re-applied there, so no silent re-embed at a new precision. Updated three tests that asserted the old graph refusal; added two. Targeted (`files=`) graph builds still refuse on identity mismatch via the targeted-currency check (unchanged, out of scope). Platform-neutral.

**Changes delivered:**

- **Remove the bridge rollback record after a successful upgrade** (`2134y-bug bridge-rollback-record-left-after-upgrade`) — 3 ACs completed. Key decisions: Delete on success and ignore.
- **Graph-only builds must not apply the embedding precision guard** (`2134z-bug graph-only-build-precision-refusal`) — 2 ACs completed. Key decisions: Skip the guard for graph-only builds.
- **An environment switch to turn off MCP startup installs** (`2136x-enh mcp-startup-install-opt-out`) — 3 ACs completed. Key decisions: One environment variable.
## Watchpoints

- Watchpoint: open `framework_edit_allowed` before framework edits, whatever the edit tool, and close it after.
- Watchpoint: `2134y` touches the upgrade runner; follow the upgrade-runner phase playbook memory and test the interrupted case.
- Watchpoint: reply to Waveforge once both waves close.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 93 | 2,602,052 |
| implement | 38 | 450,391 |
| review | 12 | 15,402 |
| **Total** | **143** | **3,067,845** |

<!-- wave:context-efficiency-state {"generation":70,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":38,"content_source_credit":462284,"derived_artifact_credit":0,"direct_net":450391,"estimated_tokens_saved":450391,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":910,"response_debit":14073,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3090},"plan":{"calls":93,"content_source_credit":2778362,"derived_artifact_credit":1432,"direct_net":2602052,"estimated_tokens_saved":2602052,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5264,"response_debit":176906,"source_credit_count":105,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":12,"content_source_credit":36966,"derived_artifact_credit":1114,"direct_net":15402,"estimated_tokens_saved":15402,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2104,"response_debit":23788,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":143,"content_source_credit":3277612,"derived_artifact_credit":2546,"direct_net":3067845,"estimated_tokens_saved":3067845,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8278,"response_debit":214767,"source_credit_count":132,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10732},"wave_id":"2136z upgrade-and-startup-field-fixes"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 1,246,157 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":1246157,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
