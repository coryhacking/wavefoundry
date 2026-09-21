# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ycrj task-fit-agent-model-policy`
Title: Task Fit Agent Model Policy

## Objective

Make model and effort selection a per-assignment decision using the controls and capabilities available in the current agent host. Remove generated defaults that silently override that choice while preserving deliberate operator preferences.

## Changes

Change ID: `1yb52-enh task-fit-model-effort-defaults`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (renderer and tests), technical-writer (canonical policy and local guidance)
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-21

## Wave Summary

Wave `1ycrj` (Task Fit Agent Model Policy) delivered one change: Task-Fit Model And Effort Defaults. Notable adjustments during implementation: Task-Fit Model And Effort Defaults: Readiness lanes code-reviewer, qa-reviewer and docs-contract-reviewer ran in fresh independent contexts; all three approved with nonblocking refinements, folded into Rationale, Requirements 2, 5 and 6, Scope, AC-2, AC-3, Tasks and the Decision Log. Claude Code frontmatter claims verified against the current docs.; Task-Fit Model And Effort Defaults: Observe: seed 050 now omits generated pins; seed 180 adds delegation-time selection and requested/observed/unknown notes; seed 160/local upgrade guidance covers preservation, proven ownership, fresh agents and protected settings. Five provenance-proven local pins removed with tool allowlists untouched. Upgrade source places extraction before phase_surface_rendering, whose fresh subprocess loaded replaced disk code in a disposable probe; no installing-run old-writer window on that normal path

**Changes delivered:**

- **Task-Fit Model And Effort Defaults** (`1yb52-enh task-fit-model-effort-defaults`) — 5 ACs completed. Key decisions: Omit generated defaults; select per assignment when controls permit; Preserve ambiguous legacy pins
## Watchpoints

- Watchpoint: operator authorized the bounded plan repair and implementation on 2026-09-21; activate only after current readiness is restored.
- Preserve explicit and ambiguous operator settings; a model name alone is not evidence of framework ownership.
- Record requested settings separately from observed execution; unavailable model or effort identity stays unknown.
- No new policy registry, telemetry, provider matrix, or approval gate.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| MODEL-BOM-1 | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer |
| MODEL-READY-1 | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, wave-council-readiness |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: destructive rendering can erase deliberate settings; strongest-alternative: omit fresh defaults and conservatively preserve existing preferences). Both isolated seats approved without blockers; per-seat synthesis and executed temporary-render controls are in [readiness review](readiness-review.md).
- Optional plan review: brief, Requirements, ACs and Scope agree. Delegation-time selection, unavailable-control fallback, preservation and ownership decisions are resolved; no operator questions remain. Stop condition reached; delivery behavior remains unverified.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 174 | 1,930,703 |
| implement | 35 | 963,805 |
| review | 154 | 928,474 |
| **Total** | **363** | **3,822,982** |

<!-- wave:context-efficiency-state {"generation":277,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":35,"content_source_credit":1024055,"derived_artifact_credit":0,"direct_net":963805,"estimated_tokens_saved":963805,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":943,"response_debit":61708,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2401},"plan":{"calls":174,"content_source_credit":2232030,"derived_artifact_credit":2272,"direct_net":1930703,"estimated_tokens_saved":1930703,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17963,"response_debit":300061,"source_credit_count":101,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14425},"review":{"calls":154,"content_source_credit":1287276,"derived_artifact_credit":1474,"direct_net":928474,"estimated_tokens_saved":928474,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":23379,"response_debit":338899,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":363,"content_source_credit":4543361,"derived_artifact_credit":3746,"direct_net":3822982,"estimated_tokens_saved":3822982,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":42285,"response_debit":700668,"source_credit_count":207,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18828},"wave_id":"1ycrj task-fit-agent-model-policy"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 30 | 0 | 8 | 29,909,548 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":29909548,"surfaced_events":30} -->
<!-- wave:exploration-avoided end -->
- 2026-09-21: Work allocation: one implementer owns coupled renderer/tests; coordinator owns policy, local guidance and upgrade-path verification. Keep host-default model/effort for these bounded code-grounded tasks; no explicit override requested, actual runtime identity unknown. Independent readiness-delta context owns the focused repair review, and fresh delivery contexts will review implementation.

- Delivery complete: all five ACs and tasks satisfied; code, QA and docs-contract delivery approvals recorded across two independent contexts (code/docs share one). Final suite: 9,452 tests, 12 skips, current green receipt. Full docs validation passed. Wave remains open pending operator closure; changes uncommitted.

- BOM follow-up complete: MODEL-BOM-1 repair cycle 2 independently reverified; code/docs/QA delivery approvals restored. Focused readiness delta approved and re-Prepare succeeded. Full suite remains 9,452 tests (new BOM rows added to existing methods), 12 skips, current receipt verified. No closure or commit performed.

## Closure reconciliation

All admitted changes are complete; every AC and task is checked, with no deferrals. Required code/QA/docs delivery reviews and readiness council are current; delivery council is not selected by the receipt. Both finding chains are terminal. Operator verified the repair and authorized close/commit. Docs-contract review passed; no specs were changed. Retrospective: BOM recognition and whole-render preservation are retained in tests; ownership and stale-allowlist guidance are canonical. Generated memory candidate 1yk7h-mem was validated and rejected (disposable target, no additional durable action). Evidence helpers are grouped under evidence/; ledger-cited review paths remain stable. Close records final chronology and idle handoff.
