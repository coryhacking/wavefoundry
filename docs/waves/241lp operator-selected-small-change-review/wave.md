# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `241lp operator-selected-small-change-review`
Title: Operator Selected Small Change Review

## Objective

An operator can select a single independent code reviewer for a bounded internal change. The ordinary review process takes over when the scope grows or needs another specialist, and the operator retains control of closure.

## Changes

Change ID: `240t6-enh operator-selected-small-change-lane`
Change Status: `implemented`

Change ID: `2136q-change small-change-lane`
Change Status: `complete`

## Participants

- Coordinator: Lifecycle coordinator
- Write-owning roles: Lifecycle implementer and documentation builder
- Requested review lanes: code-reviewer, architecture-reviewer, security-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-11-22

## Wave Summary

Wave `241lp` (Operator Selected Small Change Review) delivered two changes: Let an operator select one reviewer for a small internal change and Decide whether one-sentence changes get a lighter lifecycle lane.

Intent outcome: The council confirmed that the delivery establishes 2136q, 240t6 and the wave Objective on the qualified fixtures. Eligible changes used one independent reviewer in each phase. Independent QA verified that both close previews require ordinary Council approval after detected expansion, restoration and pause. Both previews required fresh code review after a byte-identical file replacement. The comparison arms found the same three material problems on four inputs, including the old-stamp case from 210eb. They recorded 14 versus 40 reviewer-seconds. Production cycle time, queue time and comparative suite time remain unmeasured.

**Changes delivered:**

- **Let an operator select one reviewer for a small internal change** (`240t6-enh operator-selected-small-change-lane`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: Select the permanent lane explicitly and use existing review records; Propose one spec and up to three named files for initial qualification.
- **Decide whether one-sentence changes get a lighter lifecycle lane** (`2136q-change small-change-lane`) — AC-1 and AC-2 completed. Key decisions: Plan as a decision, not as code; Operator selected A: “Plan the permanent small-change lane”.

## Watchpoints

- Watchpoint: a public behavior change can originate in an internal file. Verify the escalation and approval checks through both close routes.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DOCS-DEL-3 | do_now | no | completed | docs-contract-reviewer, council-delivery |
| IDENTITY-DEL-2 | do_now | no | completed | architecture-reviewer, code-reviewer, qa-reviewer, security-reviewer, council-delivery |
| REVIEW-CONTRACT-DEL-4 | do_now | no | completed | security-reviewer, docs-contract-reviewer, council-delivery |
| SCOPE-DEL-1 | do_now | no | completed | architecture-reviewer, code-reviewer, qa-reviewer, security-reviewer, council-delivery |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
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
| security-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| security-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-22: Intent outcome: The council confirmed that the delivery establishes 2136q, 240t6 and the wave Objective on the qualified fixtures. Eligible changes used one independent reviewer in each phase. Independent QA verified that both close previews require ordinary Council approval after detected expansion, restoration and pause. Both previews required fresh code review after a byte-identical file replacement. The comparison arms found the same three material problems on four inputs, including the old-stamp case from 210eb. They recorded 14 versus 40 reviewer-seconds. Production cycle time, queue time and comparative suite time remain unmeasured.

2026-11-22: The full-depth delivery primer asked when scope expansion becomes permanent, how approval binds file identity, and how an independent reviewer would detect a persisted-state regression like 210eb. The fixed architecture, security, QA and reality-checker seats found that restoration could revive the old approval. Architecture and QA exercised both registered close previews in disposable Git checkouts. The separate code reviewer confirmed the scope and identity defects. The rotating docs-contract reviewer also found that shipped instructions still required Council and QA after the receipt selected one code reviewer. Its alternative would have an explicit lifecycle action persist expansion. The panel agreed that the original delivery needed repair. The ledger records SCOPE-DEL-1, IDENTITY-DEL-2 and DOCS-DEL-3.

2026-11-22: All five required delivery specialists and the delivery council approved after repair. The first observed expansion now persists under the publication lock. Prepare issues the ordinary receipt. The rotating docs-contract seat withheld until the main tool entry and architecture both explained that repeat Review preserves the escalation marker and receipt while telemetry may refresh Context Efficiency. The chair and docs reviewer independently injected the prior broad promise into both descriptions and each check rejected it. The final roster agreed. The ledger records the fourth finding as REVIEW-CONTRACT-DEL-4 and all four repairs as complete. Operator signoff remains separate.

The operator chose the permanent lane in decision 240go and directed admission of the completed decision and its implementation spec into this wave. This wave uses ordinary review because it changes a public lifecycle contract.

The chair selected a full-depth adversarial primer for changes to admission authority and closure. A fresh independent red-team context replayed 210eb. Its council caught a compatibility promise that a lone reviewer accepted on a two-line edit. The review asks how dirty work is attributed, which check would catch an existing-state compatibility error, and how both close paths retain escalation after resume. The alternative adds a consumer trace and a prior-state check to the existing code review. Decision 2136q establishes the operator's choice. Spec 240t6 makes effectiveness and elapsed time observable in qualification. The seats review the two admitted specs and that primer against the published policy receipt. The coordinator selected independent reviewer contexts for the authority and verification decisions. The host did not report the reviewers' runtime model or reasoning settings.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 216 | 1,141,297 |
| implement | 81 | 795,857 |
| review | 209 | 3,562,479 |
| **Total** | **506** | **5,499,633** |

<!-- wave:context-efficiency-state {"generation":315,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":81,"content_source_credit":879847,"derived_artifact_credit":0,"direct_net":795857,"estimated_tokens_saved":795857,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4724,"response_debit":83394,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4128},"plan":{"calls":216,"content_source_credit":1947598,"derived_artifact_credit":1603,"direct_net":1141297,"estimated_tokens_saved":1141297,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9189,"response_debit":804643,"source_credit_count":104,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":209,"content_source_credit":4268361,"derived_artifact_credit":1502,"direct_net":3562479,"estimated_tokens_saved":3562479,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":41948,"response_debit":672214,"source_credit_count":118,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":506,"content_source_credit":7095806,"derived_artifact_credit":3105,"direct_net":5499633,"estimated_tokens_saved":5499633,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":55861,"response_debit":1560251,"source_credit_count":248,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":16834},"wave_id":"241lp operator-selected-small-change-review"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 15 | 0 | 13 | 5,372,266 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":5372266,"surfaced_events":15} -->
<!-- wave:exploration-avoided end -->
