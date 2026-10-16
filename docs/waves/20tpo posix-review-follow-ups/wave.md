# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-10-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20tpo posix-review-follow-ups`
Title: Posix Review Follow Ups

## Objective

Repair working-directory trust exclusions, verified-pack cleanup portability, core MCP read classification and bounded layout handling. Preserve existing containment and lock checks. Native platform qualification remains delivery work; timing stays deferred.

## Changes

Change ID: `20qxn-bug uv-trust-refuses-cwd-ancestor-paths`
Change Status: `implemented`

Change ID: `20tpl-bug pack-ownership-proofs-posix-portability`
Change Status: `implemented`

Change ID: `20tpm-bug pre-edit-hook-blocks-mcp-read-tools`
Change Status: `implemented`

Change ID: `20tpn-debt layout-dependent-posix-follow-ups`
Change Status: `implemented`

## Participants

- Coordinator: Coordinator
- Write-owning roles: Implementer after readiness; coordinator owns lifecycle records
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

## Wave Summary

Delivered trusted PATH lookup without ancestor-cwd overreach, recorded temporary-parent ownership for verified-pack cleanup, conservative generated core-read hook classification, root-alias lock refusal and safe uncached diagnostics after failed cache rename. Existing staging hashes and renderer lexical no-link policy remain; no extra cleanup hash pass or permission registry was introduced. No acceptance criteria were deferred. Native/mount/reboot qualification and timing investigation remain separate follow-ups.

## Watchpoints

- Watchpoint: Dependent portability work was implemented first and shared edits serialized. The core-read hook was generated through the canonical renderer, with write/override/stale-contract negative controls. Security review passed. Native qualification and the unsupported warm-up follow-up are not claimed; framework and seed gates are closed.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-TPO-DECLARATION | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer |
| QA-TPO-LAYOUT | do_now | no | completed | qa-reviewer, code-reviewer, docs-contract-reviewer |
| TPO-RD1 | do_now | no | completed | architecture-reviewer, security-reviewer, release-reviewer, docs-contract-reviewer, council-readiness |
| TPO-RD2 | do_now | no | completed | qa-reviewer, architecture-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer, council-readiness |
| TPO-RD3 | do_now | no | completed | architecture-reviewer, security-reviewer, docs-contract-reviewer, code-reviewer, council-readiness |
| TPO-RD4 | do_now | no | completed | qa-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer, council-readiness |
| TPO-RD5 | do_now | no | completed | docs-contract-reviewer, architecture-reviewer, security-reviewer, council-readiness |

*Machine review state — 7 findings; current: do_now 7, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

Implement 20qrv before this wave's verified-pack consumer repair. Coordinate shared upgrade files with 20ppj. No intra-wave prerequisite changes; preserve those waves' existing approvals.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 143 | 2,359,624 |
| implement | 24 | 48,810 |
| review | 309 | 3,464,252 |
| **Total** | **476** | **5,872,686** |

<!-- wave:context-efficiency-state {"generation":428,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":24,"content_source_credit":67317,"derived_artifact_credit":0,"direct_net":48810,"estimated_tokens_saved":48810,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":845,"response_debit":20674,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3012},"plan":{"calls":143,"content_source_credit":2842607,"derived_artifact_credit":8157,"direct_net":2359624,"estimated_tokens_saved":2359624,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29863,"response_debit":471565,"source_credit_count":125,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10288},"review":{"calls":309,"content_source_credit":4203109,"derived_artifact_credit":6505,"direct_net":3464252,"estimated_tokens_saved":3464252,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":38702,"response_debit":706660,"source_credit_count":163,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":476,"content_source_credit":7113033,"derived_artifact_credit":14662,"direct_net":5872686,"estimated_tokens_saved":5872686,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":69410,"response_debit":1198899,"source_credit_count":299,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13300},"wave_id":"20tpo posix-review-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 46 | 0 | 24 | 13,876,670 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":24,"estimated_exploration_avoided":13876670,"surfaced_events":46} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

2026-10-15 final delivery: Four POSIX follow-ups are implemented: trusted executable lookup, portable verified temporary-pack ownership, conservative generated core-read exemptions and bounded lock/cache/layout handling. Existing staging integrity checks remain; cleanup adds no new content-hash pass. The format-only tests-target amendment retains all seven lanes; current readiness is review-policy-8a69b7fb8dbb99059a23. Original full isolated red-team primer preceded separate architecture, security, QA and reality seats plus rotating docs. Chair grouped code/release/performance in one disclosed independent context. Six test/doc integration findings were collected, repaired in one bounded pass and independently reverified by fresh QA/code/docs contexts (39, 9 and 7 selected passing tests respectively, each with known-bad controls and zero skips). Original architecture/security source judgments were retained against unchanged production hashes; no second full council is claimed. Council agreed on scoped delivery with no remaining material finding or disagreement. The alternative of extra cleanup hashing/session markers was rejected in favor of existing proof and fresh identity controls. Final 47-path binding: 3090aafeb2c958ac40e3f6997800ba241f9f5f50c32cdbcc847307618ed9524f. These are implementation and review results, not release or native-platform qualification.

2026-10-15: operator requested preparation and review. Independent council checks the four plans against current source and already-readied 20ppj/20qrv contracts. Full isolated primer precedes fixed seats and rotating docs coverage; chair may group code/release/performance with disclosure. Inherited capable reviewers used for cross-module reasoning, runtime model identity not exposed. Source frozen; no implementation, full suite, close, commit or push requested. Preserve existing waves and resolve overlap in this wave only.

## Readiness repair

2026-10-15: one bounded plan repair addresses TPO-RD1–RD5. Guard-pack duplication and replacement fallback removed; verified cleanup requires proven ownership beyond a locator. Hook classification uses the existing observational permission roster. Lock aliases receive bounded refusal without hidden coverage loss. Failed cache rename stays uncached with a diagnostic, without unsafe in-place removal. Renderer lexical no-link policy is preserved and documented. Scratch/in-memory controls reproduced the rejected alternatives; no source implementation or native qualification is claimed.

## Readiness outcome

2026-10-15: all seven required readiness lanes and council approved after one bounded plan repair and one focused verification. TPO-RD1–RD5 are terminal. Initial roster: isolated full red-team primer; separate architecture, security, QA, reality and rotating docs reviewers. Chair covered code, release and performance in a shared independent context. Focused verification reused original source controls and checked repaired contracts; no second primer or reality pass claimed. Actual lifecycle, generated-hook and cache controls plus negative in-memory/publication controls support plan decisions, not delivered fixes. No implementation, full suite, native-platform qualification, close, commit or push. Timing remains deferred.

## Implementation allocation

2026-10-15: coordinator owns trusted PATH lookup and generated core-read hook; independent implementers own verified-temp cleanup and lock/cache layout handling. Shared upgrade/lock source follows 20qrv. Capable inherited model for guard and cross-module reasoning; actual runtime identity unknown. Source remains uncommitted; final shared qualification and independent delivery review pending.

## Implementation checkpoint

2026-10-15: all four changes implemented and focused controls passed. Verified-temp plan correction preserves existing staging hash checks without adding a cleanup hash pass; affected readiness rechecked independently and current. Layout controls: 134 tests, no skips; trusted lookup 28 tests, no skips; verified-pack ownership 11 tests and consumer controls; core-read hook 4 tests plus three detected mutants. No new evidence folder. Final canonical suite and independent delivery review now pending on settled source.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |

| 2026-10-15 | Implementation and independent repair review complete; leave paused for operator closure. Full shared qualification ran 11,816 tests / 200 files / 12 skips in 736.347 seconds. It was red from the repaired test-integration failures and the unrelated deferred checklist scaling ratio (8.47 versus limit 8); no timing waiver, benchmark pass or fresh green full-suite receipt is claimed. After the bounded test/doc repairs, the stable protected focused run passed 420 tests / 11 modules / zero skips, including the repository-state guard, and the exact identity census separately passed with its three existing mutation controls. Unchanged production coverage comes from the full run plus earlier focused and independent guard controls; the entire full suite was not repeated merely for a timing pass. | Typed terminal findings: QA-TPO-LAYOUT; CODE-TPO-DECLARATION; shipped test modules and native-support probe notes. No new evidence folder, close, commit, push or package. |
| 2026-10-15 | Closure retrospective and cleanup: reviewed concrete memory proposals without creating candidates. Drafts duplicate canonical contracts/tests or infer source fragility from readiness findings; no distinct durable action was justified. Keep rationale here and current support guidance. Folder contains only wave.md, admitted change docs and immutable events.jsonl; no redundant evidence folder or scratch artifact needs deletion. Operator authorized close, commit and push; a fresh repaired-tree full suite is required for the stale receipt. Timing investigation stays deferred, without a new waiver. | memory_propose dry-runs; existing regression controls; current close dry-runs. |
| 2026-10-15 | Operator authorized close, commit and push. Final repaired-tree canonical run completed 11,816 tests / 200 files / 12 skips in 841.468 seconds; every check except test_indexer.SQLiteDriftDetectionScaleTests.test_100k_rows_contention_safe_budget passed (1.063578 seconds versus 1.000 seconds). Timing investigation remains deferred; no threshold change, waiver, unchanged retry or green receipt was produced. Closure stays paused because the existing close tool requires a current green receipt and has no exception path. Commit/push the reviewed implementation with this explicit limitation. | python .wavefoundry/framework/scripts/run_tests.py; exact result in this record; temporary full log /private/tmp/three-wave-close-qualified-default.log. |
