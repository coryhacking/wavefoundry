# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `215xx reconcile-scan-configured-evidence-folders`
Title: Reconcile Scan Configured Evidence Folders

## Objective

A project or distribution can declare evidence folders in `docs/workflow-config.json` that the retired-surface reconcile scan skips, so Waveforge's merge baselines stop producing thousands of findings. The live operating surface cannot be excluded, and the upgrade summary lists every excluded or refused folder.

## Changes

Change ID: `215xw-enh reconcile-scan-configured-evidence-folders`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-10-20

## Wave Summary

Wave `215xx` (Reconcile Scan Configured Evidence Folders) delivered one change: Reconcile scan skips folders a project declares as evidence. Notable adjustments during implementation: Reconcile scan skips folders a project declares as evidence: Readiness round 1: release-reviewer and docs-contract-reviewer PASS; code-reviewer, qa-reviewer and red-team BLOCK on one shared gap: shape rules alone let `AGENTS.md` (a root carrier) or `agents`/`prompts` (matched as a bare component anywhere by `_directory_excluded`) hide the live surface, and excluding a folder hid per-folder instruction files. Rewritten before readying: separate prefix-only matching (Req 2), the instruction-file carve-out (Req 3), ordered single-reason refusals including `protected_carrier` from the scanner's own registries plus the plans and waves roots, and `not_a_directory` (Req 4), the summary line format (Req 5), the contributing doc and identical-paragraph check (Req 7, AC-4), `### Added` for the CHANGELOG, and isolated mutant cases per rule (AC-2).; Reconcile scan skips folders a project declares as evidence: Implemented. `reconcile_scan.configured_excluded_dirs(root)` reads `docs/workflow-config.json` with `read_contained_bytes` (cap `DEFAULT_SCAN_FILE_BYTES`) and returns accepted folders plus diagnostics; `_excluded_dir_refusal` applies the eight ordered rules (rule 8 pairs `lstat` with `contained_files._is_windows_link`); `_configured_excluded` is prefix-only with the `AGENTS.md`/`CLAUDE.md`/`WARP.md` carve-out and is added to `eligible()` in `_iter_scannable_files`, so both the mandatory-path branch and the walk honour it while directories are still descended; `disposition_diagnostics` appends the entries. `upgrade_wavefoundry._reconciliation_recommendation_lines` prints `excluded directory <entry> [<state>]` plus `reason=`. Tests: `ConfiguredEvidenceFolderTests` (6) and `test_store_diagnostics_render_configured_excluded_directories`, including the registered-carrier guard test (every `_mandatory_paths` carrier and mandatory directory is listed, under `docs/`, or under a dot-directory). Seed 160 and the upgrade prompt copy gained the same sentence (paragraphs diffed identical); contributing doc and CHANGELOG `### Added` bullet added. Scratch mutants, each detected: (a) configured matching dropped, (b) carve-out dropped, (c) bare-component matching, each of the eight refusal rules, record roots dropped from `protected_carrier`, both `not_a_list` branches, duplicates kept, diagnostics not reported, and the summary renderer branch disabled. Gapfill: shell reads, a Python edit script for the two identical prompt paragraphs, and a mutation driver; MCP used for review claims.

**Changes delivered:**

- **Reconcile scan skips folders a project declares as evidence** (`215xw-enh reconcile-scan-configured-evidence-folders`) — 5 ACs completed. Key decisions: A workflow-config list of folders, prefix-matched, refused where it overlaps a carrier the scan must inspect, with instruction files still scanned inside.; Report entries through `disposition_diagnostics`.
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | code-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 13 | 329,902 |
| implement | 25 | 0 |
| review | 13 | 65,021 |
| **Total** | **51** | **394,923** |

<!-- wave:context-efficiency-state {"generation":51,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":25,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2143,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":793,"response_debit":5042,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3692},"plan":{"calls":13,"content_source_credit":345923,"derived_artifact_credit":2774,"direct_net":329902,"estimated_tokens_saved":329902,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2332,"response_debit":20891,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":13,"content_source_credit":94591,"derived_artifact_credit":1663,"direct_net":65021,"estimated_tokens_saved":65021,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5169,"response_debit":29278,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":51,"content_source_credit":440514,"derived_artifact_credit":4437,"direct_net":392780,"estimated_tokens_saved":394923,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8294,"response_debit":55211,"source_credit_count":36,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11334},"wave_id":"215xx reconcile-scan-configured-evidence-folders"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
