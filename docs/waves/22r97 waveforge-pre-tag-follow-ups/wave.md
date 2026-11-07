# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22r97 waveforge-pre-tag-follow-ups`
Title: Waveforge Pre Tag Follow Ups

## Objective

Downstream distributions get accurate, actionable outcomes for the four gaps Waveforge reported against `2b6b985a`: a lasting remedy for deterministic scan limits, a named rule-file parse error, repository-selected setup remedies everywhere, and a visible notice when setup withholds a skill. Completion policy, readiness policy and exit codes are unchanged.

## Changes

Change ID: `22r96-bug waveforge-pre-tag-follow-ups`
Change Status: `implemented`

## Participants

- Coordinator: root agent session
- Write-owning roles: implementer; coordinator owns shared documentation and integration.
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, security-reviewer

Completed At: 2026-11-07

## Wave Summary

Wave `22r97 waveforge-pre-tag-follow-ups` (Waveforge Pre Tag Follow Ups) delivered one change: Waveforge pre-tag follow-ups. Notable adjustments during implementation: Waveforge pre-tag follow-ups: Related suites green: `test_sqlite_storage_migration` 133, `test_tensorwell_integration` 31, `test_tree_kill_routing` 33, `test_upgrade_recovery_guidance` 7, `test_mcp_tool_registry` 27, `test_betterleaks_engine` 30, `test_distribution_seams` 48, `test_render_platform_surfaces` 169, `test_secrets_validators` 171, `test_scan_secrets` 28, `test_scan_completion` 12, `test_scanner_skips` 12, `test_scanner_worker_config` 7, `test_old_parent_publication` 9, `test_mcp_scan_completion` 1, `test_scanner_fixture_hygiene` 1. No `__pycache__` under `.wavefoundry/framework/`. Changelog Unreleased Fixed bullet added. `docs/specs/mcp-tool-surface.md` names neither the codes nor the remedy text, so it is unchanged. Gapfill: source reads used Bash `sed`/`grep` alongside the loaded MCP tools, for speed on known paths.

Intent outcome: achieved. All four of Waveforge's `2b6b985a` follow-up items are delivered:

**Changes delivered:**

- **Waveforge pre-tag follow-ups** (`22r96-bug waveforge-pre-tag-follow-ups`) — 5 ACs completed. Key decisions: The match cap gets the full fixed-limit remedy; a worker timeout gets the remedy only as recurring-timeout guidance, with retry first.; Bounded readiness repair after the first full round: token-specific remedies (security S1); `worker_response_too_large` added as a deterministic work limit (QA `22r97-qa-response-cap-intent-gap`); a fixed summary-line prefix (code C1); structured versus prose AC-3 oracles, with the memory `recovery_usage` reduced to the command (QA `22r97-qa-ac3-oracle`); AC-2 negative controls (QA `22r97-qa-ac2-overbroad-control`); path-check timeouts get retry only.
## Watchpoints

- Follow-up: the release tag waits for this wave; version selection remains operator-owned.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 22r97-qa-ac2-overbroad-control | maybe_later | no | pending | — |
| 22r97-qa-ac3-oracle | do_now | no | completed | qa-reviewer |
| 22r97-qa-del-response-cap-mapping-untested | do_now | no | completed | qa-reviewer |
| 22r97-qa-response-cap-intent-gap | maybe_later | no | pending | — |

*Machine review state — 4 findings; current: do_now 2, maybe_later 2, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-07: Intent outcome: achieved. All four of Waveforge's `2b6b985a` follow-up items are delivered:
- deterministic work limits (`match_limit`, `result_limit`, `component_set_limit`, `worker_response_too_large`) are recorded by exact token, each with its own lasting remedy; scan timeouts get retry-first guidance and path-check timeouts get retry only;
- a malformed project rule file reports `project_rules_parse_error`;
- the bare `wf setup` remedies (storage migration, including graph reads; memory query fallback; checkpoint recovery tail) use `setup_recovery(root)`;
- `wf setup` and `wf render-surfaces` print one `PARTIAL SKILL DELIVERY` summary line, with exit codes unchanged.

Evidence: default suite 12,568 tests / 228 files / 12 skips green; `second` (12,550) and `declared` (12,568) profiles green with no framework bytecode; code, QA and security delivery approvals; council-delivery `ev-approval-council-delivery`. These runs were on macOS only. Retained in `evidence/`: council readiness and delivery syntheses, the red-team primer and `qualification-summary.json`; routine logs stayed in the disposable work area. The final default run (12,568 OK) followed the operator-requested "disposable work area" wording edit; the two profile runs predate that prose-only edit.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 30 | 1,876,144 |
| implement | 22 | 0 |
| review | 41 | 108,396 |
| **Total** | **93** | **1,984,540** |

<!-- wave:context-efficiency-state {"generation":92,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":22,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-4121,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":781,"response_debit":4864,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1524},"plan":{"calls":30,"content_source_credit":1956948,"derived_artifact_credit":2360,"direct_net":1876144,"estimated_tokens_saved":1876144,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14388,"response_debit":74284,"source_credit_count":62,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5508},"review":{"calls":41,"content_source_credit":200112,"derived_artifact_credit":1495,"direct_net":108396,"estimated_tokens_saved":108396,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13340,"response_debit":83649,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":93,"content_source_credit":2157060,"derived_artifact_credit":3855,"direct_net":1980419,"estimated_tokens_saved":1984540,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28509,"response_debit":162797,"source_credit_count":82,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10810},"wave_id":"22r97 waveforge-pre-tag-follow-ups"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
