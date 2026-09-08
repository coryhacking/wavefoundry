# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xfbh upgrade-retry-pruning`
Title: Upgrade Retry Pruning

## Objective

Preserve the original framework MANIFEST across failed upgrade attempts so an at-target retry still prunes retired files safely.

## Changes

Change ID: `1w3bs-bug upgrade-retry-pruning-loses-old-manifest`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, release-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-09-08

## Wave Summary

Wave `1xfbh` (Upgrade Retry Pruning) delivered one change: Preserve Pruning Across a Failed Upgrade Retry.

**Changes delivered:**

- **Preserve Pruning Across a Failed Upgrade Retry** (`1w3bs-bug upgrade-retry-pruning-loses-old-manifest`) — 5 ACs completed. Key decisions: Retain the existing repository-local snapshot design; explicitly cover partial mutation and inherited retry state.; Use one repository-local snapshot and the existing phase boundaries.

## Watchpoints

- Watchpoint: readiness required before framework edits.
- Preserve exact original MANIFEST bytes until observed prune success, including partial extraction and repeated failure.
- Review fresh-runner versus already-running old-code behavior before claiming installing-upgrade coverage.
- Operator requested prepare, review, and implement; no closure or commit authorization.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-DEL-VERIFY-1 | do_now | no | completed | qa-reviewer, release-reviewer, wave-council-delivery |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Review checkpoints

### Final repair verification — 2026-09-08

**PASS: all required specialist delivery reviews and delivery council are current.** The operator authorized preserving the 1.22.0 release section and the two historical-test repair. `QA-DEL-VERIFY-1` cycle 1 is complete after distinct independent QA and release reverifications. All five ACs and all tasks are complete. Framework and seed edit gates are closed; the wave remains open and uncommitted.

QA executed 22 tests: seven current/valid controls passed, 13 omission/wrong-owner/forbidden-content mutants failed by assertion, and two original HEAD methods reproduced the old IndexError. Release independently ran 15 invocations across 12 cases, detecting missing heading, all six required-fragment omissions, forbidden policy, and future-section-only content, while valid newer/Unreleased sections passed. Council independently ran six executions across four scenarios, catching two historical omissions even when their required phrases appeared in a future release. Each reviewer confirmed the repair fingerprints: tests `eb6c8404979100408e0370500c3f5ba836f1ac52`; CHANGELOG `467bd759087b55b7a8efa0ec57c5a674e200e879`. No reviewed source edits landed during replay.

The canonical suite passed **8,542 tests across 75 files**, with three reported skips, including all 1,096 docs-lint tests. QA and release independently recomputed the framework hash matching the green receipt at `2026-09-08T14:59:39.307870+00:00`: `39460d39c25457c54ac81fa52539cdf80ada29f742e81eefadcf5ceb65975356`. This verifies the existing verification obligation; no production requirement was narrowed.

The authorized Design amendment refreshed readiness authority to `review-policy-0395e4bc83bdf887f471`, retaining the same five required lanes, standard depth, and targeted red-team/docs seats. The independent amendment primer challenged test weakening and stale authority; docs and council verified unchanged ACs and all seven content assertions. Readiness and focused delivery council both passed (`seat_agreement: unanimous`, `max_severity: none`). A shared heading parser and stronger archive-install fixture remain outside this bounded repair. The 1w3bs user-benefit entry stays under 1.22.0. Focused memory curation rewrote the generated candidate into active memory `1xgfv`, documenting historical-release ownership and isolation controls.

### Delivery specialist reports — 2026-09-08

**Release-reviewer: delivery approval withheld.** Independently passed all 11 recovery tests warning-strict, zero skips; an overwrite-inherited-authority mutation was caught by the full-retry test. The exact AC-5 has sufficient bounded evidence, but complete staged-archive dependency/preflight behavior was not executed. Both old changelog test errors were independently reproduced. Release and QA jointly block on `QA-DEL-VERIFY-1`; a focused historical-section repair, omission controls, and current green full-suite receipt are required. No packaging or source mutation occurred.

**Delivery Council: BLOCKED.** The current receipt selects targeted red-team and docs-contract seats, informed by all five required specialist lanes; release supplied the rotating best-alternative perspective after fixed-seat evidence. Merit-first synthesis weighed anonymized nonblocking evidence while retaining QA/release blocker attribution. Lanes agree on the bounded recovery behavior and unresolved receipt requirement. Severity wording differed (QA initially material/detect-only, release low/preventive); observed behavior is a preventive verification/closure block with no runtime authority delta, so the synthesized residual impact is low and the required blocker remains intact. `seat_agreement: unanimous` on behavior and the closure condition; `max_severity: low` after this evidence-based reconciliation. No challenge round was needed because no material disagreement remained.

The concrete improvement is to pin the two historical assertions to their owning 1.22.0 section, retain their omission-detection assertions, and rerun the canonical suite after independent focused reverification. Operator scope authorization remains pending for the protected test file. The stronger complete-pack staged-entry check remains a packaging verification opportunity, not a newly invented required AC or backlog. No delivery council approval is granted while the finding remains open. Framework/seed gates are closed; this review does not close or commit the wave.

**Docs-contract-reviewer: approved, including the targeted council seat.** Three selected warning-strict tests passed with zero skips: both-carrier guidance, fresh-process recovery, and partial MANIFEST/VERSION retry. The carrier test detected 18 omission controls, nine per carrier: entry override, separate staging, absolute root, absolute pack, dry-run evidence, complete framework staging, same-runner/pack retry, success-only retirement, and unrecoverable previously lost authority. These test instruction presence, not agent adherence. Current code and instructions agree; complete archive installation remains outside this bounded proof. This lane independently reproduced the two changelog errors and the passing heading-only control. For a durable repair, pin the historical 1.22.0 section containing these announcements: selecting the latest section indefinitely would break again after the next release. No new docs-contract defect was found.

**Code-reviewer: approved.** Independent fresh reviewer passed 11 warning-strict recovery tests and 17 pruning tests, zero skips. Six targeted in-memory mutations were detected: overwrite inherited authority, late mutation marking, failed-prune-as-success, different-target acceptance, inherited pre-mutation cleanup, and missing-runner-as-success. Detecting test mappings are in the change Progress Log. An independently authored equal-manifest main-path control proved successful zero-deletion cleanup preserves listed and unmanifested files. No implementation defect found. Actual extraction/pruning ran with unrelated phases isolated; complete archive installation and the full suite were not rerun by this lane.

**Security-reviewer: approved.** Three independently executed main-path probes passed warning-strict, zero skips: real retry/pruning preserves project files; valid JSON behind a snapshot symlink refuses before extraction and preserves external bytes; four invalid-schema shapes refuse before mutation. Removing the path guard made `SecurityBoundaryProbe.test_valid_snapshot_symlink_refuses_main` observe return/extraction `(0, 1)` rather than `(1, 0)`, detecting the mutation. No credible security finding in the trusted-local-operator model. This reviewer retained the intentionally shared primer only, with no implementation/repair or other-seat context. No concurrent-adversary or complete archive-install claim.

**QA-reviewer: delivery approval withheld.** Independently passed 523 upgrade tests and 17 pruning tests with ResourceWarning treated as an error, plus all 11 recovery tests with all warnings treated as errors; zero skips. Six targeted recovery mutants were detected. All required AC rows have supporting evidence: AC-1 full retry; AC-2 cleanup/failure controls; AC-3 MANIFEST-only pruning; AC-4 partial-write/isolation/refusal controls; AC-5 fresh-process recovery and both instruction carriers. There are no deferred ACs. Complete unmocked archive installation is stronger than the admitted AC-5 and is not a new blocker. The remaining verification task is blocked by two old changelog pins: both independently reproduce `IndexError` on the missing Unreleased heading, and both pass an in-memory heading-only control. Preserve 1.22.0 and repair the historical test assumptions after scope authorization, then independently reverify and run the full suite for a current receipt.

Every completed lane verified the frozen five-file fingerprint. No reviewed source edits landed during this round. Code/security/docs typed delivery approvals are recorded; QA and release share the single typed blocking finding `QA-DEL-VERIFY-1`. Close dry-run confirms the stale framework receipt, unfinished verification task, and withheld QA/release/council approvals. Memory proposal produced zero candidates.

Delivery review started 2026-09-08 on the current typed receipt, with standard primer depth and targeted council seats `red-team` and `docs-contract-reviewer`. Required specialist lanes are code, QA, docs-contract, release, and security. No reviewed source edits are permitted during this round. Reviewer reports are recorded here; typed findings/approvals remain in the sibling events ledger.

Red-team primer: three focused main-path recovery tests passed warning-strict with zero skips; an in-memory overwrite-inherited-authority mutant was caught by the full-retry test. The strongest challenge is evidence scope: the fresh-process fixture stages scripts and isolates preflight/extensions, so it is not complete archive-install proof. The strongest alternative retains the small snapshot design and adds a bounded complete-pack staged-entry check. Seats must answer whether staged dependencies and pre-mutation snapshot creation are sufficiently established, and how the existing changelog-heading errors will be resolved before a current green receipt. No recovery implementation defect was demonstrated by the primer.

Round fingerprint (`git hash-object`, verified by primer): upgrade script `c781cffaa6c1d11b47d68cabcbabf8ebae0835a8`; upgrade tests `1bf49271544f6dfa6d3b089e8dbe5b8b3f970b1e`; seed 160 `81c5a05fe5666b418239a608ce80f2235507fe49`; project upgrade prompt `24b8a073d8c3f5645946eea48450d7c64dad5d40`; CHANGELOG `467bd759087b55b7a8efa0ec57c5a674e200e879`. Each lane receives a four- or five-minute budget and targeted tests per mutant, with whole-file mutant runs reserved for survivors.

Readiness Council PASS (2026-09-08), receipt `review-policy-f238f5c09d899be1e9b1`. Primer exposed the already-running old upgrader and partial extraction with new MANIFEST but old VERSION. The revised plan answers both: stage the fresh runner outside the destination before its first mutation, and retain target-bound original manifest authority across retries regardless of VERSION. Code, QA, docs-contract, security, and release perspectives agree; `seat_agreement: unanimous`, `max_severity: none`. Two independent agents supplied paired code/QA and security/release perspectives; a third reviewed docs and synthesized, rather than five separately sampled reviewers. Evidence includes 22 warning-strict pruning tests, a real prune negative/control pair preserving unmanifested files, and CLI/plan omission controls. Typed lane approvals are recorded above.

Merit-first synthesis found no unresolved disagreement or blocking finding. The strongest alternatives, general rollback/re-extraction and an extension compatibility bridge, add scope and risk overwriting recovery edits or coupling old hooks; bounded staging costs one explicit operator step but keeps the existing pruning boundary. Delivery must prove the staged fresh-process two-attempt path and partial-write controls. Place the staged-runner exception before the existing MCP-first upgrade default and preserve same-target retry instructions. Readiness is not a claim that the unimplemented recovery behavior already works.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 78 | 314,262 |
| implement | 19 | 336,816 |
| review | 192 | 497,465 |
| **Total** | **289** | **1,148,543** |

<!-- wave:context-efficiency-state {"generation":200,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":19,"content_source_credit":370569,"derived_artifact_credit":0,"direct_net":336816,"estimated_tokens_saved":336816,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":944,"response_debit":34670,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1861},"plan":{"calls":78,"content_source_credit":515540,"derived_artifact_credit":1128,"direct_net":314262,"estimated_tokens_saved":314262,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11004,"response_debit":197098,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":192,"content_source_credit":1208448,"derived_artifact_credit":2125,"direct_net":497465,"estimated_tokens_saved":497465,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18733,"response_debit":696264,"source_credit_count":84,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":289,"content_source_credit":2094557,"derived_artifact_credit":3253,"direct_net":1148543,"estimated_tokens_saved":1148543,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":30681,"response_debit":928032,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9446},"wave_id":"1xfbh upgrade-retry-pruning"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 4 | 3,486,892 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":3486892,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
