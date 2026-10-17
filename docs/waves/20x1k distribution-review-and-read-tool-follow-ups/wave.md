# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20x1k distribution-review-and-read-tool-follow-ups`
Title: Distribution Review And Read Tool Follow Ups

## Objective

Answer the distribution's K3 and K4 requests: closed review records are left alone with no migration prompt, and the Claude pre-edit hook exempts every effective read-tier tool a distribution declares.

## Changes

Change ID: `20wqa-enh closed-inline-review-records-left-alone`
Change Status: `implemented`

Change ID: `20wqb-enh distribution-read-tools-pre-edit-exemption`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator (agent)
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-17

## Wave Summary

Wave `20x1k` (Distribution Review And Read Tool Follow Ups) delivered two changes: Closed review records are left alone and Distribution read tools in the pre-edit exemption. Notable adjustments during implementation: Closed review records are left alone: Implemented. `review_evidence.closed_legacy_inline_record` added and exported. It normalises CRLF, matches the inline marker anywhere in the record (the same regex docs-lint and the gate classifier use), refuses any source header or source error, and reads only the first `Status:` line with the server's `^Status:\s+(\S+)`. It is used in `check_wave_docs` and in `server_impl._validated_wave_markdown`, and the gate classifier is unchanged. Seed 209 now carries the closed-records sentence, and the inline-records clause is scoped to open or reopened waves. Tests: `test_docs_lint.ClosedInlineRecordLintTests` (6 tests: closed and completed records pass with exit 0; a CRLF record passes through both docs-lint and the predicate on raw text; implementing, `Closed`, and implementing-then-closed records still fail with `migrate manually`; a wrong source and a duplicated source keep their errors; a missing Objective still reports; a closed declared record with a stale Finding Synthesis fails), and `test_server_tools.McpResourceReadTests.test_wave_resource_serves_closed_inline_record_as_written`. Scratch mutants: source-error clause, casefolded status, any-Status-line, lint guard and resource guard are all killed; the source-error mutant was killed only after the duplicated-source case was added. The no-CRLF-normalisation mutant is equivalent, because the status pattern stops at `\r`; normalisation stays as cheap insurance. Gapfill: shell edits and scratch runs for anchored edits and mutation probes.; Distribution read tools in the pre-edit exemption: Implemented. `_claude_core_read_contract` now exempts every name whose effective tier in `all_tool_tiers()` is read, under the same two-file contract, and its docstring is updated. No separate edit-gate exclusion was added because it is unreachable. `test_core_read_hook`: `test_overridden_core_and_aliases_are_not_exempt` was replaced by `test_declared_read_tier_names_are_exempt_and_write_tier_names_are_not`, which uses one validated declaration. It checks that override, alias, hidden-name alias, read replacement, both `alias_for_core` names and a declared read tool are exempt, and that a write tool, a write alias, an alias of `wf_open_gate`, a raised replacement, the hidden name, `wf_open_gate` and `wf_prepare_wave` are gated. `test_invalid_declaration_grants_no_exemption_at_all` adds a single-reason lower-to-read refusal, which grants nothing, core reads included. `test_hidden_core_name_and_its_alias_are_not_exempt` was folded into the new test. `_expected_core_read_names` was re-derived in four steps, and its unit test (renamed `test_expected_names_follow_effective_read_tiers`) adds the raised-replacement case. Docs updated: platform-mapping, the threat-model trust row and two hook rows, the spec `EXTENSION_TOOL_TIERS` entry and seed 050. AC-5 grep: no live doc or seed outside `docs/waves` says extension tools keep gating. Focused `test_core_read_hook`, `test_render_platform_surfaces` and `test_docs_lint` pass under default, `--profile second` and `--profile declared`. The committed `.claude/hooks/pre-edit.py` is unchanged. Scratch mutants M1 to M4 are all killed. Gapfill: shell edits and scratch runs for anchored edits and mutation probes.; Distribution read tools in the pre-edit exemption: Delivery repair cycle 1. DEL-2 (security): the digest covers only the bytes of `mcp_tool_extensions.py`, so a declaration that imports its tiers from another module could change them after render. Platform-mapping and the threat-model trust sentence now say declaration values must be literal assignments in that file. No AST check was added, because the actor already holds server authority.

**Changes delivered:**

- **Closed review records are left alone** (`20wqa-enh closed-inline-review-records-left-alone`) — 4 ACs completed. Key decisions: No conversion tool; leave closed records alone.; Do not add an early return to `wf_close_wave` for already closed waves.
- **Distribution read tools in the pre-edit exemption** (`20wqb-enh distribution-read-tools-pre-edit-exemption`) — 5 ACs completed. Key decisions: Exempt every effective read-tier tool, including self-declared extension read tools.; Keep the two-file digest contract.
## Watchpoints

- Watchpoint: framework and test edits only under `framework_edit_allowed`, seed edits only under `seed_edit_allowed`, each closed immediately after.
- Watchpoint: the committed `.claude/hooks/pre-edit.py` must stay byte-identical (no declaration in this repository).
- Follow-up: run the whole suite last; release qualification reports are regenerated separately before 1.32.0.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | security-reviewer, code-reviewer, qa-reviewer |
| DEL-2 | do_now | no | completed | security-reviewer, docs-contract-reviewer |
| DEL-3 | do_now | no | completed | qa-reviewer, code-reviewer |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 65 | 2,426,098 |
| implement | 28 | 48,502 |
| review | 23 | 346,310 |
| **Total** | **116** | **2,820,910** |

<!-- wave:context-efficiency-state {"generation":117,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":28,"content_source_credit":67017,"derived_artifact_credit":1738,"direct_net":48502,"estimated_tokens_saved":48502,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3527,"response_debit":21012,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4286},"plan":{"calls":65,"content_source_credit":2507229,"derived_artifact_credit":3947,"direct_net":2426098,"estimated_tokens_saved":2426098,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4862,"response_debit":87494,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7278},"review":{"calls":23,"content_source_credit":414733,"derived_artifact_credit":2218,"direct_net":346310,"estimated_tokens_saved":346310,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10845,"response_debit":62850,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3054}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":116,"content_source_credit":2988979,"derived_artifact_credit":7903,"direct_net":2820910,"estimated_tokens_saved":2820910,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19234,"response_debit":171356,"source_credit_count":96,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14618},"wave_id":"20x1k distribution-review-and-read-tool-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 2,099,757 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":2099757,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
