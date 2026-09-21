# Bound Readiness Review With Focused Repair Verification

Change ID: `1yfzt-enh readiness-converges-after-settlement`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-20
Wave: 1yfzu readiness-convergence

## Rationale

**Brief.** Goal: bound automatic readiness review effort without guaranteeing approval or suppressing defects. Audience: coordinators, reviewers and operators running Prepare wave. Approach: one full review, one bounded repair pass, one focused verification round, then explicit operator escalation for every remaining blocker. Focused review is the default after the first full review, whether or not the council describes the design as settled; its packet contains existing findings, the repair diff and directly affected contracts. Required approvals still bind the current receipt. Settlement is optional descriptive prose, never a control state. Prepare exposes missing lane approvals and unusually frequent receipt publications as advisories. Constraints: no ledger schema change, no automatic activation, no waiver of required lanes, and no change to delivery review or actionability derivations. Success: the automatic sequence either reaches readiness or stops with a concrete operator decision; it does not restart a whole-document review loop.

The operator set the rule on 2026-09-19, after waves `1y0h0 typed-phase-gates` and `1yd97 phase-gate-follow-ups` each spent about ten readiness rounds. In `1yd97` the code was settled by round 4, and rounds 5 to 10 were spent on the amendment-record criteria. In `1y0h0` independent lanes confirmed the structure at round 6, red-team later called the wave implementable, and three more full rounds followed, blocked on precision in how verification was specified.

The census behind the rule counts, for every wave whose ledger has an `initial_delivery` run, the `review_policy_receipt` records appended before the first such run. A receipt is appended only when Prepare publishes after a digested input changed, so the count measures Prepare publications rather than review passes; several passes between two publications collapse into one receipt. Across the 140 waves that reached delivery, the median is 2 and the 90th percentile is 5; 40 of those waves predate receipts, and the median over the other 100 is also 2. The overrun is a tail: `1vj4e` 14, and `1yd97`, `1y0h0` and `1wpig` at 10 each. The four worst recorded no typed readiness findings, so no finding had an owner or a terminal state, and every repair pass re-ran every seat against the whole document. Typed findings alone are not a cap, though: `1u8r2` used them and still reached 8.

Delivery review converges through seed 209's convergence checkpoint, which freezes review scope once two repair cycles complete: afterwards fresh adjacency work needs a recorded deviation and moderator acknowledgment, and widening task scope needs the operator. Readiness-origin repair cycles count toward that rule, so a wave that runs two readiness repair cycles spends its only checkpoint before delivery, as `1u8r2` and `1xa00` did. Nothing bounds readiness before that point. Seed 215's "at most one challenge round" governs disagreement between seats, not repair rounds.

The rule was trialled on 2026-09-19 on waves `1y0h1 tool-registry-dispatch` and `1y0h2 handler-module-split`, whose settled designs had been readied against a tree two waves had since changed. One drift round ran with three lanes, each covering both waves. `1y0h1` drew no blocking finding. Its notes were applied in one pass, which rotated its receipt, so its approving lanes re-read the repair diff and re-recorded their approvals: in practice the diff-scoped re-approval this change now specifies. `1y0h2` drew one blocking finding, recorded as typed readiness finding `READY-B1` and owned by the two lanes that raised it, which are also that wave's whole required roster, so the trial did not exercise excluding a lane. `READY-B1` closed in the scoped round, and the same round caught a regression the repair itself introduced: to prove retrieval unchanged, the repair had added a before-and-after evaluation comparison that the evaluator's fixture-digest rule makes impossible. Under the rule that defect went to the operator instead of starting a third round. The regression was the kind the plan-shape rule in Requirement 3 forbids, because the repair elaborated a claim instead of deleting one it could not verify. The trial also found that both waves had been treated as ready without the per-lane readiness approvals `wf_implement_wave` requires, because Prepare's only approval blocker is the council signoff.

This change's own first readiness round blocked on the first version of the design, which recorded settlement as a new typed run kind and counted rounds from it. All four seats found it incoherent with receipt-bound approvals, three found that the run kind broke two ledger invariants and that the council whose rounds were budgeted could reset the count, and the rotating seat proposed dropping the record altogether. This version takes that proposal (see Decision Log).

## Requirements

1. Seed `215-wave-council` gains the bounded readiness protocol in its Council Protocol:
   a. Run the first full readiness review as today. Record blocking findings as typed readiness findings with their originating `source_lanes` and applicable `blocking_required_lanes`; collect the findings before repairing.
   b. After that full review, focused review is the default. The council may summarize design settlement in `## Review Checkpoints`, but neither settlement nor its absence changes review scope, the automatic budget, blocking authority or receipt currency. Reopening an accepted design decision requires a concrete defect under Requirement 2 or an explicit operator decision.
   c. Perform one bounded repair pass, publish the repaired packet with `wf_prepare_wave(mode="ready")`, and conduct one focused verification round. Each finding's source and blocking lanes replay that finding; other previously approving lanes and the council review the repair's effects and re-record required readiness approvals against the current receipt. A newly required lane reviews its remit once. The packet includes original findings, the repair diff and directly affected requirements, code and contracts, including unchanged context needed to detect contradictions and regressions. Reviewers do not solicit unrelated findings or repeat a whole-document sweep. A blocker already discovered is never suppressed because it lies outside that packet.
   d. At the end of that verification round, every remaining blocker, whether an unsuccessful repair or a new defect, goes to the operator. No further automatic repair/review round begins. The operator chooses another bounded repair and focused verification, or replanning; the decision and its scope are recorded in `## Review Checkpoints`. Material scope or authority changes follow existing replanning/full-council rules. Approval is not promised and required-lane authority is never waived. Notes are carried in the wave record as implementation notes rather than triggering another plan edit/publication. Existing aggregate repair-cycle bookkeeping and the single convergence checkpoint remain unchanged: review rounds are not equated with cycle numbers, and earlier readiness repairs may already have consumed the checkpoint.
   e. A preference for different wording or a different valid design is an untyped note, not grounds to reopen an accepted decision. A demonstrated build-changing defect remains blocking and follows 1d even when framed as disagreement with an accepted decision. A substantive unresolved choice that prevents correct implementation is not a wording preference.
   f. The seed carries a focused-review briefing template: original findings, repair diff, affected contracts/context, current receipt, required lanes, concrete verification questions and the stop/escalation rule. Reverification preserves the original judgment unless evidence changes it. The boundary excludes unrelated exploration, not the context needed to check the repair.
2. Seed `209-agent-harness-core` states the readiness finding bar: identify how the plan, followed as written on the current tree, would ship wrong behavior, could not be implemented correctly because a substantive decision is unresolved, or has a required acceptance criterion that cannot pass or cannot fail. Genuine design defects may block from the first review onward; preferences without such consequences remain untyped notes. Existing actionability and blocking derivations are unchanged. Its Repair re-verification and convergence guidance explicitly applies Requirement 1's bounded orchestration to readiness: record findings and repair starts normally, but after focused verification do not automatically repair remaining blockers; escalate to the operator. Delivery's automatic repair behavior is unchanged.
3. Seed `170-plan-feature` gains three plan-shape rules. A requirement naming a set the implementer must act on states the rule deriving that set, and the derived set governs. An acceptance criterion names the observable outcome and kind of oracle; exact mutation, known-bad and fixture mechanics are designed during implementation and judged at delivery. A readiness repair narrows or deletes a claim it cannot verify rather than elaborating it, and explicitly identifies any new mechanism it introduces as new review surface.
4. Seed `100-project-prompt-surface-bootstrap`'s prepare-wave guidance summarizes the bounded protocol and points to seed 215. The readiness checklists state that every required lane has a current readiness approval: the Readiness Verdict list in `docs/prompts/prepare-wave.prompt.md`, the Readiness Checklist in `docs/contributing/review-and-evals.md`, and seed 215's Relationship To Implementation Activation section.
5. `wf_prepare_wave` reports `readiness_receipts`: the number of `review_policy_receipt` records before the wave ledger's first `initial_delivery` run, or all receipts if none exists, evaluated after any publication by the call. Report it on success and error responses for a resolved readable ledger; unavailable or unresolved ledger counts are `null`, not fabricated zeroes. A readable empty ledger counts as zero. When the count exceeds a named constant of 5, emit advisory `readiness_receipt_publications_high`, describing unusually frequent Prepare publications and inviting inspection of review churn. Five is the census's historical 90th percentile, not an allowed review-round budget. This is supporting telemetry: multiple review passes can share one receipt, so the count neither measures actual rounds nor proves convergence. Nothing resets the ledger-derived count; settlement prose is irrelevant. The diagnostic is emitted only by Prepare and never changes its outcome.
6. `wf_prepare_wave` emits advisory `readiness_lane_approvals_missing` naming required lanes without a current readiness approval, derived exactly as `wf_implement_wave` derives its lane set and approval currency and computed after any receipt the call publishes. The implement-time requirement is unchanged. An unresolved wave or unavailable authority does not invent a lane result or replace existing errors.
7. Update seed `007-review-system-overview`, `docs/specs/mcp-tool-surface.md` (response field, both advisories and sanctioned advisory sites), and the hand-edited self-hosted surfaces: seed 215 into `docs/agents/specialists/wave-council.md`, seed 170 into `docs/prompts/plan-feature.prompt.md`, seed 100 into `docs/prompts/prepare-wave.prompt.md`, and seed 209 into `docs/contributing/review-and-evals.md`. Seed 007 has no rendered surface. Preserve `review_evidence.RUN_KINDS`, ledger validation semantics and projection behavior.
8. Validate the protocol with bounded scenario evaluation as well as essential instruction pins. Exercise reviewer/coordinator behavior using the authored briefing and instructions on five fixed cases: wording preference, successful repair, repair regression against an unchanged affected contract, surviving original blocker, and receipt rotation. Record the packet, observed decision and scope, expected decision, and any mismatch. Use fresh independent reviewer context for the behavioral evaluation; do not substitute string-presence tests for observed decisions or claim universal convergence from five cases. No new evaluation service or runtime review state machine is introduced.

## Scope

**Problem statement:** Repeated whole-document readiness reviews reopen valid decisions and elaborate verification details, while existing convergence bookkeeping does not bound automatic readiness review effort.

**In scope:**

- Seed text in 215, 209, 170, 100 and 007, the hand-edited self-hosted surfaces, essential instruction pins and bounded behavioral scenario evaluation.
- The `readiness_receipts` field and the two advisories in `wf_prepare_wave`.

**Out of scope:**

- Any ledger schema change, including a typed settlement record.
- Delivery review, the convergence checkpoint and the actionability gate's existing derivations.
- An operator waiver path for readiness findings.
- Making either advisory blocking.
- Rewriting closed waves' ledgers or plans.

## Acceptance Criteria

- [x] AC-1: Essential pins protect the focused-review default, affected-context allowance, remaining-blocker escalation, required-lane authority and receipt refresh in the canonical instructions and their matching self-hosted surfaces. Each pin fails when its protected rule is removed; pins make no claim about agent behavior. The plan-shape rules and cross-references are consistent across the authored documents.
- [x] AC-2: `readiness_receipts` equals the count Requirement 5 defines on ledgers built by the canonical producers with zero, one, five and six receipts before the first `initial_delivery` run, and on one with receipts after that run, which are not counted. `readiness_receipt_publications_high` appears with `advisory: true` exactly on the six-receipt ledger. The field reflects any receipt published by that call, is present on success and error responses (including unavailable-count null cases), and the Prepare outcome is identical with and without the diagnostic. Its message describes publication frequency rather than an exhausted round budget.
- [x] AC-3: On a fixture where one required lane has no readiness approval and another holds one bound to a superseded receipt, `readiness_lane_approvals_missing` names exactly the lanes `wf_implement_wave` names as `prepare_review_incomplete` on the same fixture, with `advisory: true`, and names none once every lane holds a current approval; the Prepare outcome is identical with and without it.
- [x] AC-4: `review_evidence.RUN_KINDS`, the set of ledger records the validator accepts, projection output for unchanged ledger inputs, and the tool registration/signature golden fixture are unchanged; ordinary lifecycle evidence and wave status projections may advance.
- [x] AC-6: In the five Requirement 8 scenarios, a wording preference does not reopen an accepted design; a successful repair closes without an unrelated sweep; a repair regression remains blocking using affected unchanged context; a surviving original blocker escalates without another automatic repair; and receipt rotation requires refreshed approvals from all required lanes. Observations and limitations are recorded, with no universal convergence claim.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `seed_edit_allowed`; edit seeds 215, 209, 170, 100 and 007 per Requirements 1 to 4 and 7; close the gate.
- [x] Hand-edit the self-hosted surfaces Requirement 7 names, and `docs/specs/mcp-tool-surface.md`.
- [x] Add essential pins per AC-1 and run the five bounded behavioral scenarios per AC-6, and update the advisory emit-site pin `test_advisory_tags_appear_only_at_the_sanctioned_sites` for the two new advisories.
- [x] Add `readiness_receipts`, `readiness_receipt_publications_high` and `readiness_lane_approvals_missing` to `wf_prepare_wave` through the Prepare response paths, with the tests AC-2 to AC-4 describe.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| protocol   | implementer | —          | seed text, hand-edited surfaces, pin tests |
| signals    | implementer | —          | readiness receipt count and both advisories |
| guards     | qa          | signals    | fixtures from canonical producers |


## Serialization Points

- `.wavefoundry/framework/seeds/`
- `.wavefoundry/framework/scripts/`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/review-and-evals.md`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/plan-feature.prompt.md`
- `docs/agents/specialists/wave-council.md`

## Affected Architecture Docs

`docs/contributing/review-and-evals.md` states the readiness recording contract and gains the round rule. No boundary, layering or data-flow change: the change adds prose rules, one derived response field and two advisories, and no ledger record type.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Essential instructions must survive surface maintenance |
| AC-2 | important | Supporting telemetry exposes publication churn without claiming to measure rounds |
| AC-3 | important | Surfaced by the field trial; readiness should not be mistaken for implementability |
| AC-4 | required  | Preserve ledger semantics and tool signatures while extending response data |
| AC-5 | required  | Standard change-local verification |
| AC-6 | required | Observed scenario decisions, rather than sentence presence, test the protocol objective |


## Progress Log

2026-09-20 Observe / complete: all ACs and tasks verified. Four required delivery lanes approve with no blocking findings (code/architecture/docs-contract share one independent non-author context; QA separate). Full suite 9,428 tests / 115 files / 12 existing skips, green current receipt; full docs validation clean. All review evidence and scope limitations are recorded in `delivery-evidence.md` and typed events. Both edit gates closed. Wave remains open and uncommitted pending operator review; no closure or commit authorization inferred.

2026-09-20 Observe: canonical-producer and compatibility checks pass: 57 focused tests, then 13 final tests after the two expected diagnostic-list updates; 77 instruction deletion controls and seven runtime mutants detected. The project-only-lane fixture was strengthened after its first mutant survived. See `delivery-evidence.md` for the mutation-to-test table. Source and final test artifacts are frozen for independent review; full framework suite running.

2026-09-20 Observe: protocol Requirements 1–4 and 7 implemented in the five seeds and matching self-hosted surfaces; seed gate closed. Prepare telemetry observes the final ledger after publication, shares activation roster/currency, and preserves nullable counts on outer refusals. Independent behavioral evaluation matched all five expected decisions; see `behavioral-scenarios.md` for packets, decisions and limitations.

2026-09-20 Gapfill: MCP exact-keyword retrieval and targeted reads identified runtime seams. `code_definition(read_review_event_ledger)` returned `index_runtime_stale`; targeted shell reads completed ledger/authority and response-wrapper inspection. No index deletion or rebuild was substituted.

2026-09-20 Thought: run meaningful canonical-producer, refusal, instruction-deletion and runtime mutation checks, then freeze the reviewed tree and collect independent delivery lanes before integrating any repairs.

2026-09-20 Thought / Readback: one full readiness review, one repair pass and one focused verification, then operator escalation for every remaining blocker. Implement bounded instructions and matching self-hosted surfaces in parallel with advisory-only Prepare telemetry. Preserve ledger kinds, accepted records, projections and public signatures. Example: sixth pre-delivery receipt emits a publication-frequency advisory while returning the same status; stale/missing required lane approvals are surfaced, never waived. Verify canonical producers, outer refusals and post-publication values, essential pins with negative controls, then five independent observed scenarios and delivery review. Required/important ACs all remain in scope.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-19 | Planned at the operator's direction after the rule was trialled on waves `1y0h1` and `1y0h2` | readiness census over wave ledgers; `1y0h2` `events.jsonl` findings `READY-B1` and `READY-R1` |
| 2026-09-19 | Readiness round 1: red-team primer, then code-reviewer, qa-reviewer and docs-contract-reviewer; all four blocked, and all judged the design core not settled. Five blocking findings recorded as typed readiness findings `RC-B1` to `RC-B5` with repair starts before this edit. Repaired in one pass: the typed settlement record and its count are removed in favor of a ledger-derived receipt count, the scoped round now re-approves by diff, the accept option is removed from the escalation, and the design-concern rule no longer overrides a required lane. The Rationale's claims that a repair rotates the receipt once and that readiness has no convergence equivalent were wrong and are corrected | `events.jsonl` findings `RC-B1` to `RC-B5` |
| 2026-09-19 | Operator requested the simpler approach: scoped review by default, affected contracts in the packet, all remaining blockers escalated, publication telemetry secondary, and behavioral scenarios. Existing RC-B1–RC-B5 repair starts remain open for independent verification; no implementation performed | Current request and revised Requirements 1–8 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-19 | Operator approved one full review, bounded repair, focused verification, then escalation | Directly bounds automatic effort while preserving honest blocking authority | Settlement-triggered convergence leaves a discretionary prerequisite |
| 2026-09-19 | Settlement is optional descriptive prose; no typed settlement record | Neither review scope nor telemetry needs a new control state; supersedes the earlier settlement-trigger design | Typed settlement broke ledger invariants and allowed a resettable counter |
| 2026-09-19 | Focused packets include directly affected unchanged context | A repair can contradict a contract outside its diff | Literal diff-only review misses regressions; whole-document rereview restarts churn |
| 2026-09-19 | Escalate old and new blockers after verification | A failed repair must not silently extend the automatic budget | Escalating only newly discovered defects leaves an unsuccessful-repair loophole |
| 2026-09-19 | Keep receipt count as advisory publication telemetry; rename diagnostic to readiness_receipt_publications_high | The census measures publications, not review rounds; five is descriptive, not a permitted budget | A hard round budget inferred from receipts would misclassify review effort |
| 2026-09-19 | Apply a concrete consequence bar without suppressing substantive unresolved design choices | Wording preferences and genuine inability to implement need different handling from the first review | Settlement-dependent classification prolongs early churn |
| 2026-09-19 | Keep essential pins and add five bounded observed scenarios | Instructions surviving edits and agents following them are separate claims | Pin every sentence: high maintenance with no behavioral proof |
| 2026-09-19 | No accept-as-note option for a blocking finding | No new waiver path; remaining blockers require repair or replanning | Inventing a terminal waiver state would expand the ledger contract |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Focused review misses a repair regression | Include directly affected unchanged contracts and preserve every safely demonstrated blocker |
| A real design needs more than one repair | Escalate a concrete packet for operator-authorized repair or replanning; never promise approval |
| Receipt publications under-count actual review passes | Label the signal honestly and assess protocol behavior through scenario observations |
| Scenario results depend on reviewer/model behavior | Record the exact brief and observations with limitations; no universal guarantee |
| Readiness repairs consume the existing convergence checkpoint | Preserve aggregate cycle semantics and report actual ledger state, not round-number assumptions |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
