# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20st7 release-profile-fixture-isolation`
Title: Release Profile Fixture Isolation

## Objective

Repair release-profile fixture assumptions without changing shipped guards or skipping coverage. Make private temporary-pack aliases and distribution-aware hook tests meaningful under shipped, renamed and declared profiles before official 1.32.0 qualification.

## Changes

Change ID: `20rvq-bug release-profile-fixture-isolation`
Change Status: `implemented`

## Participants

- Coordinator: Coordinator
- Write-owning roles: Coordinator implementer after current readiness
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-17

## Wave Summary

Wave `20st7` (Release Profile Fixture Isolation) delivered one change: Release profile fixture isolation. Notable adjustments during implementation: Release profile fixture isolation: Qualification on the frozen tree, sequential: canonical default passed 11,857 tests / 200 files / 12 existing skips in 620.219s, exit 0, receipt inputs_hash `ea4a928052921c825aa182b78cf0a75b976009fbbd8b0ddb296446a347b64065`; `--qualify-profile second` passed 11,849 tests / 200 files, complete, scope `200 of 200 files (full fallback: coverage unproven)`; `--qualify-profile declared` passed 11,857 tests / 200 files, complete, same scope. The indexer 600 s cutoffs and the TechDocs child-result errors seen in the earlier concurrent runs did not recur in these sequential runs; their timing cause remains uninvestigated and no threshold was changed. AC-5 met. Council-delivery approved after four lane approvals. Not a 1.32.0 release qualification by itself: the operator owns the release decision.; Release profile fixture isolation: Delivery lanes: code, QA, release and docs-contract PASS; code and QA independently reverified DEL-1 (resolve mutant fails exactly the three legacy tests, unmutated 15/15). QA non-blocking note applied: `test_known_bad_shapes_are_refused` now keeps equal line counts where the shape allows and asserts each case's own reason substring (render file 147/147 after the edit). Release note applied: a default focused run of all four files is logged (170/170, 0 skips). Windows note from code: on `nt` the temp root is the plain owned parent, so the gettempdir-side resolve is uncovered there, as before the wave; native Windows qualification stays out of scope.; Release profile fixture isolation: Implemented the four repairs: verified-pack tests stage under an owned private parent (`tempfile.tempdir` patched for the whole test); legacy-hook tests use the production roster arguments and assert each case's exact message, with the renderer refusal asserted on stderr; core-read tests own their declaration through `apply_base_declaration`/`base_declaration` with byte-copied modules, a paired positive read in every refusal test and a new explicit hidden-name test; hook parity selects the declaration-aware branch only from the JSON-normalized loaded declaration and compares through `_declaration_aware_pre_edit_parity` with an independent names derivation and byte-exact roster digest, plus `DeclarationAwareHookParityTests` running the known-bad shapes in every profile. Focused runs: default 23/23 and 147/147, second 170/170, declared 170/170, zero skips. Controls in a scratch clone: AC-1 unrepaired test under `second` gave 3 ERRORs naming `temporary-parent-alias`; AC-4 one unrelated hook byte under `declared` failed with `bytes differ outside the declaration data`, a comment edit to `mcp_tool_extensions.py` without resync failed the default byte-exact path, and a renderer mutant that stops dropping hidden names failed with `fresh CORE_READ_TOOLS does not equal the expected names`. Test-ID inventory: 166 before, 170 after, none removed, four added; no new skip, expectedFailure, early return or exception swallowing in the diff. Gapfill: file reads during implementation used the shell because the four target files and their anchors were already named by readiness.

**Changes delivered:**

- **Release profile fixture isolation** (`20rvq-bug release-profile-fixture-isolation`) — 5 ACs completed. Key decisions: Select targeted fixture isolation and declaration-aware parity.; Full release qualification remains mandatory and sequential after final edits.
## Watchpoints

- Watchpoint: preserve production guards, default byte parity, declaration-dependent permission checks and explicit positive/negative controls. No extra profile skips.
- Watchpoint: full qualification follows settled edits and runs sequentially. The two incomplete indexer workers and TechDocs child-result failures are not accepted exceptions; timing investigation remains deferred.
- Follow-up: the complete repair scope supersedes the earlier single-file waiver question. Normal readiness or an explicit named waiver is required before repository test edits.
- Watchpoint: operator closure is not authorized; 20tpp remains paused.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |

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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 102 | 717,440 |
| implement | 20 | 0 |
| review | 29 | 170,257 |
| **Total** | **151** | **887,697** |

<!-- wave:context-efficiency-state {"generation":121,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":20,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1824,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":723,"response_debit":4457,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3356},"plan":{"calls":102,"content_source_credit":884659,"derived_artifact_credit":2789,"direct_net":717440,"estimated_tokens_saved":717440,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7506,"response_debit":166770,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":29,"content_source_credit":224539,"derived_artifact_credit":1767,"direct_net":170257,"estimated_tokens_saved":170257,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7513,"response_debit":51590,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3054}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":151,"content_source_credit":1109198,"derived_artifact_credit":4556,"direct_net":885873,"estimated_tokens_saved":887697,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15742,"response_debit":222817,"source_credit_count":68,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10678},"wave_id":"20st7 release-profile-fixture-isolation"} -->
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
## Review Checkpoints

- 2026-10-16: Consolidated release-blocker plan only. Independent readiness and delivery reviews have not run. No blocking gate or test failure was waived.
- 2026-10-17: Delivery complete. AC-5 met: the four repaired files pass focused under default (170/170), second (170/170) and declared (170/170) with zero skips; on the frozen tree the canonical default passed 11,857 / 200 / 12 skips (receipt current) and both `--qualify-profile` runs passed 11,849 and 11,857 tests across 200 files, complete, scope `full fallback: coverage unproven` because the inventory classifies only one of the four files. The earlier indexer 600 s cutoffs and TechDocs child-result errors did not recur when the suites ran one at a time; the timing cause is not investigated and nothing was waived. Coverage statement: the committed `mcp_tool_extensions.py` digest in the pre-edit hook is verified only on the byte-exact path (default and second); under declared the extensions digest is checked against the on-disk source only and the roster digest against both source and committed value. DEL-1 (red-team) repaired in cycle 1 and reverified by fresh code and QA contexts; four lane approvals and council-delivery recorded. This pass is not a 1.32.0 release qualification; the release decision and closure are the operator's.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-17 | Readiness approved (six seats), wave opened, four test repairs implemented and profile-verified, delivery finding DEL-1 repaired in cycle 1; per-step detail and evidence are in the change doc Progress Log. Qualification runs pending review settlement. | `20rvq-bug release-profile-fixture-isolation.md` Progress Log; events.jsonl |
| 2026-10-16 | Default passed 11,867 tests/200 files/12 skips in 779.246s. Second completed 197 passing files and three failed/incomplete files; declared completed 195 passing and five failed/incomplete files. Both indexer workers exceeded 600 seconds; deterministic report comparison refuses incomplete qualification. No 1.32.0 archive, tag or GitHub release was created. | Existing ignored release-1.32.0 qualification reports; /private/tmp/release-1.32.0-{default,second,declared}-final.log |
| 2026-10-16 | Operator requested local field testing before the planned repairs. Built and archive-verified lean 1.32.0+px1p using the unchanged current 11,867-test default receipt. Compatibility reports remain failed/incomplete; no fixture edit, qualification waiver, wave closure or official release is implied. | ~/.wavefoundry/dist/wavefoundry-1.32.0.px1p.zip; SHA-256 756bc68333569285704c04d8330dcec445fda1a2f53bb017ea6b91930f193d7d; existing session handoff |
