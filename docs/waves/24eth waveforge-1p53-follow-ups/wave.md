# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-26
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24eth waveforge-1p53-follow-ups`
Title: Waveforge 1.53 follow-ups

## Objective

Distributions and operators upgrading to the next release keep their host restrictions on renamed spec tools that a distribution re-aliases, get a retired-token refusal that says it blocks the upgrade, receive a shared-cache warning before the first upgrade from 1.53 and see eligible retired components when the installed runner supports the preview, and get a model-build error that names the bad file. The extension contract states the `response_keys` echo rule beside its description. Upgrade phases, served tools and refusal sets are otherwise unchanged.

## Changes

Spec ID: `24cji-bug spec-alias-of-override-skips-permission-carry`
Spec Status: `implemented`

Spec ID: `24dsp-bug retired-token-preflight-blocks-on-records`
Spec Status: `implemented`

Spec ID: `24e91-bug retired-model-cleanup-dry-run-shows-nothing`
Spec Status: `implemented`

Spec ID: `24etf-bug model-manifest-mismatch-names-nothing`
Spec Status: `implemented`

Spec ID: `24etg-doc response-keys-echo-rename-guidance`
Spec Status: `implemented`

## Participants

- Coordinator: wave coordinator (this session)
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-11-26

## Wave Summary

Wave `24eth` (Waveforge 1.53 follow-ups) delivered 5 changes: A distribution alias for a renamed spec tool skips the permission carry-over, The retired-token preflight error says "report-only" while it blocks the upgrade, The upgrade dry run does not show which retired models the real run will delete, The model companion build error does not name the mismatched component or file, and State plainly that `response_keys` must not rename a key the parameter echo already renames.

Intent outcome: The focused fixtures establish permission carry-over and withholding for a distribution alias, a blocking preflight with recovery, a read-only preview of eligible cleanup components, actionable manifest differences and a validated echo-rule example. The release note and unsent handoff warn first-hop users before apply. Qualification uses scratch caches and a simulated no-directory-handle fallback on macOS. Native Windows and receipt of the notice by downstream users remain unmeasured.

**Changes delivered:**

- **A distribution alias for a renamed spec tool skips the permission carry-over** (`24cji-bug spec-alias-of-override-skips-permission-carry`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: Treat an aliased spec pair as a stock route for permissions only (carry, hold and withhold), leaving `stock_spec_routes()` and serving unchanged. Planner default; the operator asked for a single wave covering the DO items.
- **The retired-token preflight error says "report-only" while it blocks the upgrade** (`24dsp-bug retired-token-preflight-blocks-on-records`) — AC-1, AC-2 and AC-3 completed. Key decisions: Fix the message only; keep the scan's coverage and fail-closed behaviour. Operator: "A, narrow 24dsp to the message fix".
- **The upgrade dry run does not show which retired models the real run will delete** (`24e91-bug retired-model-cleanup-dry-run-shows-nothing`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: Add a read-only planned-removal list to the CLI dry run, and amend the seed's existing cleanup section; keep cleanup workstation-wide. Planner default; the operator asked for a single wave covering the DO items.
- **The model companion build error does not name the mismatched component or file** (`24etf-bug model-manifest-mismatch-names-nothing`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Name the differences in the existing error, bounded. Planner default; the operator asked for a single wave covering the DO items.
- **State plainly that `response_keys` must not rename a key the parameter echo already renames** (`24etg-doc response-keys-echo-rename-guidance`) — AC-1 and AC-2 completed. Key decisions: Add a sentence and example beside the `response_keys` description in the contract. Planner default; the operator asked for a single wave covering the DO items.

## Watchpoints

- `24cji` and `24e91` both edit seed `160` (different sections) and `upgrade_wavefoundry.py` (different functions); serialize those edits. Open `seed_edit_allowed` only for the seed edits.
- `24cji` also edits `docs/prompts/upgrade-wavefoundry.prompt.md`; `24e91` does not.
- `24e91` and `24etg` both edit `docs/architecture/contracts/mcp-tool-surface.md` (different paragraphs); serialize those edits.
- Follow-up: Waveforge is told the folder-registration request is declined; the corrected `24dsp` message is the answer.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| RDY-1 | do_now | no | completed | council-readiness |
| RDY-2 | do_now | no | completed | council-readiness |
| RDY-3 | do_now | no | completed | council-readiness |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| release-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-26: Intent outcome: The focused fixtures establish permission carry-over and withholding for a distribution alias, a blocking preflight with recovery, a read-only preview of eligible cleanup components, actionable manifest differences and a validated echo-rule example. The release note and unsent handoff warn first-hop users before apply. Qualification uses scratch caches and a simulated no-directory-handle fallback on macOS. Native Windows and receipt of the notice by downstream users remain unmeasured.

2026-11-26: Independent QA intent check: the served alias retained host restrictions and its hints named the callable predecessor during a hold. The cleanup preview agreed with removal on a disposable copy. The release note and draft handoff explain why a 1.53 runner cannot show the list on the first hop. The blocking error preserved the worklist and retry command, the bundle error named the missing member, and the declaration validator confirmed the echo example. Eighteen focused tests passed without skips. Making the manifest difference iterator return nothing broke the missing-member assertion. The coordinator verified the integrated tree with the canonical suite and full documentation validation.

2026-11-26: The delivery primer replayed one focused case per spec. Its strongest challenge was the scratch-checkout rehearsal that shares the workstation cache. Code, architecture and docs reviewers checked the warning, held aliases, cleanup ownership and the bounded diagnostics. The tracked delivery files produced fingerprint `38f3a63d2baffbc614005d54e0a1c5b9eeac784d` (ordered file hashes); the draft handoff was also inspected. Reviews ran on one macOS host and model family.

2026-11-26: The full suite caught two stale source hashes in the generated Claude pre-edit hook. Regeneration changed one line. The hook parity test passed on the repaired tree (tracked-file fingerprint `8ddb4d132dfc354c3e7dabe7704c8c4867189134`). The chair independently checked cleanup equivalence, missing-file diagnostics and the reporting cap. Suppressing the reported differences made the missing-file test fail. The final suite reported OK for 13,649 tests across 261 files, including 13 skips, in 933 seconds. Full documentation validation returned zero errors and warnings. All five delivery specialists and the council approved.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 75 | 1,937,319 |
| implement | 59 | 0 |
| review | 83 | 417,207 |
| **Total** | **217** | **2,354,526** |

<!-- wave:context-efficiency-state {"generation":195,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":59,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-5173,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1638,"response_debit":9642,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6107},"plan":{"calls":75,"content_source_credit":2103036,"derived_artifact_credit":9059,"direct_net":1937319,"estimated_tokens_saved":1937319,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17411,"response_debit":173200,"source_credit_count":82,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15835},"review":{"calls":83,"content_source_credit":527602,"derived_artifact_credit":1990,"direct_net":417207,"estimated_tokens_saved":417207,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6874,"response_debit":116646,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11135}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":217,"content_source_credit":2630638,"derived_artifact_credit":11049,"direct_net":2349353,"estimated_tokens_saved":2354526,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25923,"response_debit":299488,"source_credit_count":123,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":33077},"wave_id":"24eth waveforge-1p53-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 10 | 0 | 8 | 4,419,150 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":4419150,"surfaced_events":10} -->
<!-- wave:exploration-avoided end -->
