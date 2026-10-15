# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20omx all-in-one-upgrade-pack`
Title: All In One Upgrade Pack

## Objective

Add an optional directly upgradeable ZIP containing the framework and its verified model companion, while preserving the lean and standalone package choices.

## Changes

Change ID: `20nt1-enh direct-upgrade-model-bundle`
Change Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer (single serialized owner)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-15

## Wave Summary

Delivered an optional combined ZIP for normal fresh installation and direct upgrade, preserving lean and standalone model assets. The exact companion is streamed only when needed; matching verified caches are reused. Recovery retains one verified source and completion removes only owned staging. Six ACs and all tasks are complete; all six delivery lanes approved and D1 cleanup is repaired. No ACs deferred. Timing investigation remains outside scope.

Final qualification: 11,684 tests across 187 files, 12 skips, 726.438 seconds, green receipt; docs validation passed. Both edit gates are closed. Bounded integration covers legacy protocol-1 and installed protocol-2 upgrade entry plus fresh-install extraction/model provisioning; no full onboarding, live inference or native-Windows qualification is claimed.

Retrospective: installed-version probes need packaging-generated protocol metadata absent from Git tag exports. Retained-source ownership must transfer to the canonical checkpoint even for lean executable upgrades. Existing regression tests and upgrade integrity guidance preserve these lessons; the proposed failed-attempt memory duplicates the regression, so no new candidate was selected.

Cleanup: only wave.md, the admitted change document and authoritative events.jsonl remain in the wave folder. No evidence folder was generated; cited diagnostic originals remain in temporary storage. No unique evidence or ledger history was deleted.

## Watchpoints

- Preserve old-runner entry compatibility, verified model publication, dry-run behavior and retained-source ownership. Timing investigation remains deferred; prior release exceptions do not silently cover new source qualification.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D1-owned-archive-cleanup | do_now | no | completed | code-reviewer, architecture-reviewer, qa-reviewer, security-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 78 | 486,479 |
| implement | 209 | 2,993,387 |
| review | 120 | 898,873 |
| **Total** | **407** | **4,378,739** |

<!-- wave:context-efficiency-state {"generation":344,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":209,"content_source_credit":3358094,"derived_artifact_credit":1340,"direct_net":2993387,"estimated_tokens_saved":2993387,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25171,"response_debit":425187,"source_credit_count":152,"source_credit_drop_count":0,"structural_source_credit":81207,"workflow_prompt_credit":3104},"plan":{"calls":78,"content_source_credit":596884,"derived_artifact_credit":2355,"direct_net":486479,"estimated_tokens_saved":486479,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11667,"response_debit":112992,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11899},"review":{"calls":120,"content_source_credit":1176176,"derived_artifact_credit":2445,"direct_net":898873,"estimated_tokens_saved":898873,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29844,"response_debit":252835,"source_credit_count":73,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":407,"content_source_credit":5131154,"derived_artifact_credit":6140,"direct_net":4378739,"estimated_tokens_saved":4378739,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":66682,"response_debit":791014,"source_credit_count":274,"source_credit_drop_count":0,"structural_source_credit":81207,"workflow_prompt_credit":17934},"wave_id":"20omx all-in-one-upgrade-pack"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 51 | 0 | 24 | 18,990,702 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":24,"estimated_exploration_avoided":18990702,"surfaced_events":51} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- 2026-10-15 closure delta: completed handoff prose rotated readiness binding; focused technical (code/architecture/security plus red-team) and QA/docs-contract/release contexts independently found no changed contract or source. The chair synthesized the red-team and rotating docs-contract seats; readiness refreshed without repeating delivery review or qualification. Operator explicitly authorized closure followed by commit/push.

- Operator acknowledged the product behavior and authorized prepare, review and implementation. Directly usable combined ZIP is the selected UX. Readiness approved; independent delivery reviews cleared the implementation and focused cleanup repair, with final no-edit canonical qualification passed.

## Progress Log

- 2026-10-15: Same combined ZIP verified for both fresh installation and upgrade. Existing shipped install instructions use the normal Install Wavefoundry flow and pass the original ZIP to setup; isolated fresh-target verification published three model components, then zero on reuse, without extracting a separate model ZIP. Full onboarding/index build was not exercised. This confirms the existing install contract, with no product changes or duplicate suite required.

- 2026-10-15: Final unchanged-tree qualification PASSED: 11,684 tests / 187 files / 12 skips in 726.438 seconds, exit 0. The current green receipt and default report are retained in their normal cache locations. Implementation and all required delivery lanes are complete; no open finding remains. Both edit gates are closed. Wave remains open pending operator-owned closure; no commit/push/release performed.

- 2026-10-15: All six required delivery lane approvals are current, D1 is terminal, and all acceptance criteria are checked. Full suite: 11,684 tests/187 files/12 skips passed in 780.158 seconds; receipt withheld because coordinator gate/record edits occurred during the run. Both gates and ledger are now settled; no-edit rerun is required before claiming complete qualification. No implementation or review repetition is needed for those administrative edits.

- 2026-10-15: Delivery used three independent contexts: code/architecture; QA/docs-contract/release; security. They unanimously found D1 retained-archive cleanup, which was repaired once and independently reverified for all four blocking lanes. The cleanup-disabled control still detects the original defect. No additional delivery council is required by this wave's receipt.
- 2026-10-15: Bounded integration checks passed for exact real companion materialization and matching-cache no-extraction reuse. Actual 1.31 tag-export probes exercise legacy protocol-1 because the source tag lacks generated protocol metadata; the corrected installed-target fixture copies that metadata from the official 1.31.0+pwp1 archive. Its protocol-2 preview changes no files; real primary apply reaches the expected storage restart checkpoint with exactly one owned ZIP and matching proof/guard/continuation paths. These do not claim a completed live downstream upgrade or inference run.
- 2026-10-15: Final source/test tree frozen after independent repair review; canonical qualification is running. Both edit gates are closed. No wave closure, commit, push or release performed.

- 2026-10-14: Readiness passed with full red-team primer and closing reconciliation; architecture/code and QA/docs/reality remits were grouped in two independent contexts, with separate security, rotating release and chair contexts. All six required lanes and council-readiness recorded typed approvals; prepare and implementation activation passed. Strongest challenge was the existing protocol-2 executable refusal, addressed explicitly in the plan. No implementation qualification is claimed by readiness.
- Thought: resolve concrete archive and old-parent contracts before the readiness primer, then use an independent full primer and grouped fixed-seat review with separate chair synthesis. One implementer owns code; reviewers remain read-only. No code edits before readiness.
