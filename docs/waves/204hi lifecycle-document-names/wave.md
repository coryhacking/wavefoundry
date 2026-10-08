# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `204hi lifecycle-document-names`
Title: Lifecycle Document Names

## Objective

Replace three feature-named lifecycle documents with change-neutral names and safely migrate downstream project documents while preserving review-policy coverage.

## Changes

Change ID: `203di-enh lifecycle-document-names`
Change Status: `implemented`

## Participants

- Coordinator: Codex coordinator
- Write-owning roles: implementer coordinator
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-08

## Wave Summary

Wave `204hi` (Lifecycle Document Names) delivered one change: Give lifecycle documents change-neutral names.

**Changes delivered:**

- **Give lifecycle documents change-neutral names** (`203di-enh lifecycle-document-names`) — 5 ACs completed. Key decisions: Use explicit document rename pairs with existing contained publication primitives and early renderer ordering.; Preserve historical evidence and report downstream moved links.
## Watchpoints

- Watchpoint: migrate project documents before policy rendering; preflight collisions; freeze every repository writer during the full suite. Required independent council seats and review lanes use fresh contexts; implementation remains serialized under the coordinator.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-204HI-001 | do_now | no | completed | qa-reviewer |
| QA-204HI-002 | do_now | no | completed | qa-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: approved by explicit operator close/commit/push instruction on 2026-10-08.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 137 | 1,160,459 |
| implement | 7 | 0 |
| review | 157 | 1,350,752 |
| **Total** | **301** | **2,511,211** |

<!-- wave:context-efficiency-state {"generation":208,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":7,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-50,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":146,"response_debit":1281,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1377},"plan":{"calls":137,"content_source_credit":1503532,"derived_artifact_credit":2341,"direct_net":1160459,"estimated_tokens_saved":1160459,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6657,"response_debit":342562,"source_credit_count":132,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":157,"content_source_credit":1699524,"derived_artifact_credit":1416,"direct_net":1350752,"estimated_tokens_saved":1350752,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14117,"response_debit":338455,"source_credit_count":115,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":301,"content_source_credit":3203056,"derived_artifact_credit":3757,"direct_net":2511161,"estimated_tokens_saved":2511211,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20920,"response_debit":682298,"source_credit_count":247,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7566},"wave_id":"204hi lifecycle-document-names"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 12 | 0 | 11 | 6,912,850 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":11,"estimated_exploration_avoided":6912850,"surfaced_events":12} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

### Prepare wave — readiness review

Full adversarial primer (five stances, three questions) preceded isolated architecture, security, QA and reality seats; rotating docs-contract proposed explicit pairs with separate move-boundary and public-upgrade evidence, report-only links. Each fixed seat weighed and accepted that refinement. Anonymized merit pass ordered seats docs-contract/reality/security/architecture/QA before identities were reattached; all supported bounded ownership and independent authority/wiring proofs. seat_agreement_aggregate: seat_agreement=unanimous; max_severity=none. No blockers or repair round. Required code, QA, docs-contract and security lanes approved current plan using current-source readiness controls, not unimplemented behavior.

Implementation notes: exact bytes/modes at move only; managed regions may reconcile; two-pair preflight is not whole-upgrade rollback; distinguish contained parent links from escapes; disable only new migration in extracted-renderer negative control; new-path policy/phase-anchor rejection and measured receipt effects; preserve history while reporting links. Model allocation: fresh independent review contexts, inherited host model, bounded sequential seat batches; coordinator owns implementation. Strongest alternative refines accepted design; aliases duplicate authority and generic migration framework adds coupling.

### Waveforge integration handoff

The source change renames seed 001 to `001-framework-lifecycle-overview.md`, the delivery guide to `docs/contributing/delivery-workflow.md`, and the lifecycle companion to `docs/contributing/lifecycle-overview.md`. Fresh seeding uses those names. Installing upgrades migrate existing project guides before policy reconciliation, preserving bytes/modes at the move boundary and authored prose outside managed regions afterward. Collisions refuse the document migration; deliberately merge competing authored content before removing the obsolete copy and retrying. Reports identify Markdown links to moved files without rewriting history. Reconcile live titles and references during the upgrade editing pass; raise historical-link/docs-gate conflicts for explicit resolution.

The rename alone does not rotate policy receipts or require re-Prepare; unrelated policy migrations retain their normal requirements. Actual Waveforge-tree qualification and release-pack publication are not claimed. Focused tests pass under default, second and prompt-names profiles; installing-upgrade negative control passes. Canonical host run passes 11,894 tests across 174 files with 20 existing skips. Independent code, QA, docs-contract and security delivery approvals are current, with both fixture findings terminal. Ready for Waveforge review; operator authorized closure, commit and push on 2026-10-08.

### Delivery review complete

All required lanes approved. Two profile-fixture findings were repaired and independently cleared; no production repair was required after initial implementation. Code mutants removed preflight, exclusive publication and mode preservation; each targeted test failed. Security replaced a source with an outside symlink before reading; the real renderer refused, while a following-read mutant copied outside data and failed the safety assertions. QA removed the manifest and hardcoded the history root in separate scratch controls; each failed the intended assertion. Docs review confirmed live references and migration guidance, preserving historical evidence. Final source fingerprint: `359a3bd1808f8236105880804096fdf690d46e337dd12344d8d0a4cb845786aa`. The unchanged host-permission suite passed after sandbox-only failures; receipt input hash `660d1a46ca27f86aab3f159a26b3685cbf28484ade8a820791e10e29e09f2c15`.

### Closure reconciliation

All five required ACs and every task are complete; no intentional deferrals. All required review lanes and typed readiness authority are current; delivery council was not selected by the receipt. Docs-contract review approved the seed/local guidance and live-reference census. Retrospective: migration bytes and later managed-region reconciliation are distinct boundaries; profile fixtures must explicitly activate carriers and use configured history paths. Memory checkpoint found no remaining candidates; validated memory 20472 captures both fixture repairs. Positive confirmation: existing contained primitives plus fresh extracted-renderer ordering preserved customization and detected unsafe states without new migration abstractions. Wave folder retains only the admitted plan, wave record and authoritative ledger; unique evidence recipes/fingerprints remain in those records, temporary logs stay outside the repository, and no historical evidence was deleted. Close tool records final chronology; session handoff becomes idle after successful closure.
