# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20gx1 distribution-test-fixtures`
Title: Distribution Test Fixtures

## Objective

Make journal, historical-upgrade and qualification fixtures independent of a distribution checkout while preserving the behavior each regression verifies.

## Changes

Change ID: `20gfi-bug distribution-independent-upgrade-fixtures`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer; coordinator owns lifecycle records and integration
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-10-12

## Wave Summary

Wave `20gx1` (Distribution Test Fixtures) delivered one change: Distribution-independent Upgrade and Qualification Fixtures. Notable adjustments during implementation: Distribution-independent Upgrade and Qualification Fixtures: Implemented synthetic full baselines, verbatim plaintext history and generic identity/layout rename control. New positive gate/qualification/renamed old-current resume controls pass. Every remaining encoded entry including metadata/body equals its prior value.; Distribution-independent Upgrade and Qualification Fixtures: Final implementation and required independent delivery review completed; all admitted ACs are supported. Paused for operator closure. See `wave.md` Review Checkpoints for consolidated findings, limits, source identity and reviewer roster.

**Changes delivered:**

- **Distribution-independent Upgrade and Qualification Fixtures** (`20gfi-bug distribution-independent-upgrade-fixtures`) — 5 ACs completed. Key decisions: Select explicit declaration baselines and move only the v122 runner into the established plaintext historical fixture convention; remove its encoded duplicate.
Retrospective and memory: Synthetic fixtures own their declaration baseline; historical runners that undergo layout renaming need editable text fixtures with verified original bytes. Owning tests preserve both rules. Bounded memory proposal returned no eligible candidates; no duplicate memory record was created. No AC or task was deferred.

Cleanup disposition: Only wave.md, the admitted change document and the authoritative ledger are retained. Routine probes and logs remain temporary; no permanent evidence folder or duplicate readiness file was created.

## Watchpoints

- Watchpoint: Operator authorized implementation and pause after review; no closure, commit or push. Use generic repository examples and existing wave/change records only. Qualify the combined source tree before final delivery approvals; intermediate pauses may carry pending combined qualification.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 32 | 170,095 |
| implement | 28 | 499,721 |
| review | 9 | 0 |
| **Total** | **69** | **669,816** |

<!-- wave:context-efficiency-state {"generation":72,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":28,"content_source_credit":535488,"derived_artifact_credit":0,"direct_net":499721,"estimated_tokens_saved":499721,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":832,"response_debit":36982,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2047},"plan":{"calls":32,"content_source_credit":214857,"derived_artifact_credit":1180,"direct_net":170095,"estimated_tokens_saved":170095,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10386,"response_debit":39361,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":9,"content_source_credit":18051,"derived_artifact_credit":0,"direct_net":-5956,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":206,"response_debit":26732,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":69,"content_source_credit":768396,"derived_artifact_credit":1180,"direct_net":663860,"estimated_tokens_saved":669816,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11424,"response_debit":103075,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8783},"wave_id":"20gx1 distribution-test-fixtures"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 867,111 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":867111,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Work allocation: focused implementation and routine independent reviews request gpt-6.1-sol/high; the ambiguous bookkeeping boundary requests gpt-6-astra/high. These are requested settings; runtime identity beyond host reporting is unknown. Tasks are scoped per role with independent review contexts, shared source reads and serialized writes.

- Readiness specialist review: independent code, QA and architecture approved all four plans; security approved the three runtime/qualification waves and participated in all councils. Required docs-contract and release lanes approved their assigned scopes. Current-tree controls only; no future delivery execution is claimed. Review working reports stay in temporary storage.

- Readiness council: pass; fixed architecture, security, QA and reality seats plus rotating docs-contract, preceded by isolated red-team primer and anonymous-first synthesis. Agreement unanimous; maximum severity none; no challenge round needed. Primer depth standard. Red-team closing confirmed all original questions addressed and the admitted plan unchanged. Compare original executable bytes before rename; keep digest as provenance afterward and reach actual old/current resume in positive rename control. Deliberately retarget inventory/sample keys and verify every remaining encoded byte/digest; retain real invalid declaration/report and altered-pack refusals, with no new skips. Final implementation qualification and delivery approval remain pending.

- Delivery complete (2026-10-12): independent code, QA and architecture reviewers approved; no unresolved findings. Journal controls install the shipped declaration before explicit fixture overrides; nested default/second/declared qualification controls remain isolated from valid ambient extension declarations. Real renamed old/current upgrade processes preserve pause, restart, relocated-pack retry and altered-pack refusal.

- Historical integrity and profiles: the renameable v1.22.0 runner is byte-identical to the prior decoded source (269,025 bytes; SHA256 `ae18d63246bc55f398bb6ae10303044f7701b68dbbf7ecff8e8e54230df0fb24`). All 13 remaining encoded historical entries retain their exact bytes and metadata. Only that duplicate encoded entry was removed. Focused default qualification passed 926 tests/six files; second and declared profile checks passed 810 tests/three files each, with the two pre-existing native-Windows junction skips. Independent declaration-reset and historical-integrity negative controls were detected; production validation was not weakened.

- Limits: these are fixture and source qualification results, not a released pack, complete native Windows qualification or live consumer upgrade.

- Final default qualification (2026-10-12): canonical `python3 -B .wavefoundry/framework/scripts/run_tests.py --qualification-report .wavefoundry/cache/qualification/default.json` with bytecode disabled, CPU provider and reranker disabled passed **12,402 tests across 185 files**, **12 existing skips**, in **798.065 seconds**. All 185 exact worker records are complete and green; skip IDs/reasons match the pre-repair baseline. The existing green receipt and exact report both match current framework inputs `d1ab96d12d77d992c99b700656f18ac2044068c89188efa82e531f416816d5ce`. Recording routine typed reviews during the run did not invalidate qualification. No additional suite was run solely for ledger/progress recording.

- Evidence retention: final outcomes and limits are consolidated here and in the admitted change record; the existing typed `events.jsonl` is machine authority. Routine reviewer reports, raw logs and disposable probes stay outside the repository. The wave remains paused for operator review/closure; no closure, commit, push or new package build was performed.
