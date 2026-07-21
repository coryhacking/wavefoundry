# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-21
review-evidence-source: events.jsonl

wave-id: `1t69a retrieval-posture-coverage`
Title: Retrieval Posture Coverage

## Objective

Make the MCP-first retrieval posture reach every project with full lifecycle scope: the in-band directive and the seed-rendered instructions must name review-repair investigation and briefed subagents, not just implementation, so the 1seax review-window lapse (harness grep/sed substituting for the retrieval tools) cannot recur from instruction ambiguity. No new tracking; instruction surfaces only.

## Changes

Change ID: `1t699-enh retrieval-posture-repair-and-subagent-coverage`
Change Status: `implemented`

Completed At: 2026-07-21

## Wave Summary

Wave `1t69a` (Retrieval Posture Coverage) delivered one change: Retrieval Posture: Repair-Window and Subagent Coverage in Every Project's Instructions. Notable adjustments during implementation: Retrieval Posture: Repair-Window and Subagent Coverage in Every Project's Instructions: Implemented: directive constant extended (two additions: repair/reverification scope with executed-probes carve-out; subagent-brief carry); content test strengthened with three new phrase assertions (62/62 OK). Seed 180 preamble reframed stage-neutral with the seed-020 scope pointer; tool order untouched. Seed 100: both one-line pointers appended (close-wave, review-wave bullets), no seed-180 text copied. Local renders updated: implement-wave posture bullet reframed stage-neutral; review-wave and close-wave gained the pointer line.; Retrieval Posture: Repair-Window and Subagent Coverage in Every Project's Instructions: Deviation (surfaced, not silent): the framework's shipped lifecycle-prompt templates (`install/lifecycle-prompts/review-wave.prompt.md`, `close-wave.prompt.md`) carried no retrieval line at all and are the most direct review/close instruction surface target projects receive; added the same one-line seed-020 pointer to each under `framework_edit_allowed`. In-scope by the wave objective (every project's instructions), not named in the original scope list.

**Changes delivered:**

- **Retrieval Posture: Repair-Window and Subagent Coverage in Every Project's Instructions** (`1t699-enh retrieval-posture-repair-and-subagent-coverage`) — 5 ACs completed. Key decisions: No new sensor or tracking bucket; instruction-surface change only.; Point at seed 020 for the lane/subagent scope instead of restating it.
## Journal Watchpoints

- Watchpoint (no-restate): new text points at seed 020's Retrieval Rules for lane/subagent scope; do not restate the full rule in any surface (drift risk is the failure mode this wave exists to close).
- Watchpoint (no new tracking): operator explicitly declined windowed/per-cycle posture sensing; reviewers should flag any telemetry addition as silent scope expansion.
- Watchpoint (gates): directive edit needs `framework_edit_allowed`; seed edits need `seed_edit_allowed`; open before, close immediately after.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 6 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Prepare Review Evidence

Readiness council pass, 2026-07-21 (single change, instruction-surface scope):

- reality-checker: all plan claims were retrieved live this session through the MCP tools — the directive constant at server_impl.py:13316 (code_read) says "implementation AND review" and names neither repair windows nor subagent briefs; seed 180's exploration order opens "exploration before any code edit" (docs_search citation); seed 020's Retrieval Rules already carry the lane/subagent scope ("for every lane, including reviewer and builder subagents"); role seeds 214/239 already front-load tool posture. The gap census is accurate and the out-of-scope list matches what already exists.
- docs-contract-reviewer: the change doc is internally consistent (Requirements 1-5 map onto AC-1..AC-5; AC-3 is correctly framed audit-and-skip; Affected Architecture Docs names the context-efficiency reference audit rather than claiming N/A blindly). One note: the directive content test named in AC-1 must assert the NEW phrases, not merely still-pass, and the AC wording already requires that.
- red-team: strongest challenge is that instruction wording alone does not change behavior; the honest answer is recorded in the change doc's Decision Log — the operator explicitly chose instruction-surface scope over enforcement/tracking, and the 1seax lapse was specifically an instruction pattern-match failure (the agent followed the implementation-framed wording as written). Second challenge, directive bloat: bounded by the one-sentence-per-addition risk mitigation. Third, seed-100 render drift: answered by same-wave surface regeneration under the docs gate.
- qa-reviewer: every AC is verifiable — AC-1 by the existing four-path source-census test plus a content assertion, AC-2/AC-3 by seed text inspection with the audit result recorded in the Progress Log, AC-4 by render + docs-lint, AC-5 by the suite. No fixture generation is needed; no vacuous-pass risk identified.

Synthesis verdict: READY. Scope is deliberately narrow (two seeds + one constant + regeneration), the no-restate and no-new-tracking constraints are recorded as watchpoints, and the failure it repairs is operator-observed with evidence in the 1seax CE ledger.

Delta pass, 2026-07-21 (operator plan-review repair to 1t699): the operator sharpened Requirement 3 / AC-3 from audit-and-skip to two definite insertions — seed 100's `review-wave` and `close-wave` bullets each get a one-line pointer to seed 020's Retrieval Rules, with an explicit prohibition on copying seed 180's exploration list or delegation text. Claim re-verified against the current tree via code_read: seed 100 line 92 (`implement-wave`) carries seed 180's full rule; lines 98 (`close-wave`) and 100 (`review-wave`) carry no retrieval pointer. Two stale in-doc phrases ("audit-and-skip" in Scope and the AEG seeds row) were reconciled to the revised requirement. No scope growth, no new surfaces; verdict unchanged READY.

## Review Checkpoints

- pre-implementation-review: passed (2026-07-21) — pre-mortem: (1) directive tests may pin exact text, update in same edit; (2) new phrases must avoid review-evidence severity tokens; (3) seed-100 insertions must not restate seed 180 (watchpoint); (4) surface regeneration may touch unexpected files, inspect the render diff; (5) context-efficiency reference may quote superseded directive text, audit after. Packet complete: ACs prioritized, audit resolved at plan time, lanes assigned, no open unknowns.
- **Delivery-phase Wave Council [wave-council-delivery] — 2026-07-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer; strongest-challenge: the shipped lifecycle templates are missing-only baselines, so existing projects' prompt files do not update deterministically on upgrade; accepted because existing projects receive the lines through the seed-100-governed upgrade reconciliation and the always-on in-band directive covers every activation and review call regardless of prompt-file state; no material disagreements. Live evidence: the wf_review_wave envelope served the extended directive post-reload; content test asserts the new phrases; suite 6,086/6,086 OK; docs-lint clean.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer, reality-checker, qa-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: instruction wording alone does not change behavior, answered on the record by the operator's explicit instruction-only scope decision and the evidence that the 1seax lapse was an instruction pattern-match failure; strongest-alternative: windowed per-repair-cycle posture sensing, declined by operator direction and recorded in the change doc Decision Log)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- wave-council-readiness: approved 2026-07-21 — readiness council synthesis READY; seats unanimous; full synthesis in Prepare Review Evidence.
- wave-council-delivery: approved 2026-07-21 — delivery council PASS; zero findings; live in-band serve verified; full synthesis in Review Checkpoints.
- operator-signoff: approved 2026-07-21 — operator instructed "close the wave and commit" after the delivery report.

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 18 | 364,906 |
| implement | 12 | 11,275 |
| review | 27 | 1,449,963 |
| **Total** | **57** | **1,826,144** |

<!-- wave:context-efficiency-state {"generation":52,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":12,"content_source_credit":15183,"derived_artifact_credit":0,"direct_net":11275,"estimated_tokens_saved":11275,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":184,"response_debit":5236,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1512},"plan":{"calls":18,"content_source_credit":388049,"derived_artifact_credit":817,"direct_net":364906,"estimated_tokens_saved":364906,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1514,"response_debit":27717,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5271},"review":{"calls":27,"content_source_credit":1564678,"derived_artifact_credit":286,"direct_net":1449963,"estimated_tokens_saved":1449963,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2215,"response_debit":113875,"source_credit_count":138,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1089}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":57,"content_source_credit":1967910,"derived_artifact_credit":1103,"direct_net":1826144,"estimated_tokens_saved":1826144,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3913,"response_debit":146828,"source_credit_count":160,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7872},"wave_id":"1t69a retrieval-posture-coverage"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
