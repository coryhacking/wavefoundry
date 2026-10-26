# Require intent fit on council approvals and give QA an intent-coverage duty

Change ID: `21kk5-enh require-intent-fit-on-council-approvals`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-10-24
Wave: 21j63

## Rationale

Change 21j62 asked the council-chair to report `intent_fit` at readiness and delivery, but nothing checks that it does: a council approval without it is accepted, and no specialist lane compares the ACs with the intent. Specialists approve against ACs, so ACs that miss the intent can pass every lane while the wave misses its goal; the council is the only catch, and its catch is self-reported. The operator asked who reviews ACs against the objective and intent, then asked for both fixes in this wave.

## Product Intent

Operators and coordinators get a council approval that cannot be recorded without an explicit intent verdict, and a second, independent reviewer (qa-reviewer) that maps each AC to the intent at readiness. Before: an approval with no intent judgment passes and only the council looks at intent. After: the typed approval path refuses a council approval without `intent_fit`, refuses a readiness approval of a plan that will not establish its intent, shows an honestly not-established delivery to the operator before sign-off, and the QA lane names any part of the intent no AC tests. Boundary: the verdict stays a reviewer judgment; the tool checks that it was given and is consistent with approving, not that it is right. Historical ledgers stay valid.

## Requirements

1. Recording a council approval through `wf_review_event` requires an `intent_fit` value in `evidence`. A council approval is one whose signoff key canonicalizes into `council-readiness` or `council-delivery` (`canonical_signoff_key(key) in COUNCIL_SIGNOFF_KEYS`), which includes the legacy `wave-council-*` spellings of those two keys and a distribution's extra legacy spellings, but not a custom `wave-council-<x>` key. A missing value is refused with a diagnostic naming `intent_fit` and its values. On `council-readiness`, `establishes` and `partially` are accepted and `does_not` is refused with a diagnostic that says to record a finding instead, because approving a plan that will not establish its intent is contradictory. On `council-delivery` all three values are accepted: the approval confirms that the `Intent outcome:` is supported, and an honest not-established outcome can be (Requirement 10 surfaces it before operator sign-off). Nothing is appended on refusal. The check runs after replay detection, so an identical retry of an approval recorded before this change still replays.
2. The value has one meaning: the worst verdict across every admitted change and the wave Objective (`does_not` worse than `partially` worse than `establishes`). At delivery the coordinator's confirmed `Intent outcome:` maps achieved to `establishes`, partial to `partially` and not established to `does_not`.
3. The accepted value is written to the approval evidence record as `intent_fit`. The ledger validator accepts the field as optional, requires `establishes` or `partially` on a readiness council approval and any of the three on a delivery council approval when present, and rejects it on any record that is not a council approval (recognized through `canonical_approval_claim_id`), including finding and other evidence records. Ledgers without the field, including every existing ledger, validate unchanged; nothing is rewritten.
4. Specialist, operator and custom council-key approvals are unchanged: they need no `intent_fit`, and carrying one is refused at write (previously the builder dropped it silently) and invalid in the ledger.
5. Callers see the requirement before a refused write, with values read from one exported registry: the guided schema (`review_action_input_schema`) has a separate council-approval entry, guided council approval actions from `wf_review_wave` name `intent_fit` and its values, the council verdict template and instructions that `wf_prepare_wave` returns (`_prepare_council_verdict_template` / `_prepare_council_instructions` in `lifecycle_gate_support.py`) include it, and the `wf_review_event` description names it. The dashboard next-action text stays as it is.
6. Every guidance surface that tells a caller how to record a council approval, or spells the `intent_fit` values, names the requirement and spells the not-established value `does_not`. Known carriers: seed 209 (Executable Evidence Record table and the `wf_review_event` paragraph), seed 215 and `docs/agents/specialists/council-chair.md` (including the worst-verdict rule from Requirement 2), the Prepare, Review and Close prompts (`docs/prompts/` and `.wavefoundry/framework/install/lifecycle-prompts/`, plus seed 190 for the Requirement 10 advisory), the typed-authority text in `review_policy_reconcile.py`, seed 100, seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md` (existing installs: an upgraded server refuses a council approval without the field and the diagnostic names it), `docs/specs/mcp-tool-surface.md` (the `wf_review_event` section and the Prepare council brief description) and `docs/contributing/review-and-evals.md`. The census is re-derived at implementation over seeds, lifecycle prompts, `docs/prompts/` and framework scripts, not copied from this list.
7. The qa-reviewer (seed 239 and the rendered `docs/agents/qa-reviewer.md`) gains an intent-coverage duty: at readiness, for each required AC, which part of the change's Product Intent or the wave Objective it proves, and which part no AC tests; an untested part that would leave the intent unestablished is a finding. At delivery, the ACs that carry the intent have executed evidence.
8. Existing tests and golden fixtures that record council approvals are updated to pass `intent_fit`, through shared helpers where they exist, from a re-derived census of council-key writers in the tests. A test that then fails for another reason is investigated as a regression, not patched.
9. `CHANGELOG.md` describes the requirement, including that a specialist or operator approval carrying `intent_fit` is now refused.
10. When the current `council-delivery` approval carries `intent_fit: does_not`, `wf_review_wave` and `wf_close_wave` (dry run and create) report an advisory diagnostic naming the verdict, and the `missing_operator_signoff` remedy says that signing off accepts that outcome. The operator's existing sign-off is the acknowledgment; nothing new is recorded and nothing blocks. Waves whose delivery verdict is `establishes` or `partially`, and waves with no `intent_fit`, behave exactly as before.
11. Every intent issue a reviewer finds is a typed finding triaged under seed 209's actionability rules, the same way as a defect: a council `intent_fit` gap (including one behind `partially`) and every qa-reviewer intent-coverage gap is recorded through `wf_review_event` with judgment fields and a disposition (fix now, later, or not, with rationale). Only the existing blocking derivation stops the wave; an intent issue is never left as prose and never settled by choosing a checkbox state. Seeds 215 and 239, their rendered copies and `docs/contributing/review-and-evals.md` say so.
12. Bounded delivery-coverage correction (operator direction, 2026-10-25): on every delivery review, before QA reviews the outcome, the coordinator drafts the dated `Intent outcome:` paragraph in the existing exact `## Review Checkpoints` section. QA independently confirms or corrects whether the delivered work achieves each change's Product Intent and the wave Objective using the delivery evidence and material limitations, whether or not delivery Council is required. The coordinator incorporates corrections before close. A required delivery Council reuses that draft and QA assessment in its existing judgment. This supersedes the council-conditional draft placement in 21j62 Requirement 3. Change only both Review prompts, seed 239 and the rendered QA role, with a bounded wording/placement regression in the existing carrier tests; no runtime code, new gate, approval type or universal Council requirement. The correction tests instruction coverage, not agent reliability; the matched delivery experiment, later-wave efficacy sampling and optional triage wording refinement remain outside this correction.

13. Roster-aware correction from the operator's separate review (2026-10-25): the coordinator drafts the outcome on every delivery review and assigns its independent check to QA when QA is in the current required delivery roster; otherwise assign one reviewer already in that roster. Do not add a lane, change Prepare's roster or grant specialist `intent_fit` authority. When the required delivery roster is empty, record that no independent lane check ran in `## Review Checkpoints`; do not claim one occurred. Any required Council still judges the same draft using the assigned reviewer's assessment when available. A correction identifying unachieved intent is a typed finding under Requirement 11; wording-only correction is editorial. Supersedes Requirement 12's unconditional assumption that QA exists and its five-path limit. Reconcile both Review prompts, seed 239/rendered QA, seed 100's intent summary, seed 160's upgrade baseline/rendered upgrade prompt, review-and-evals and CHANGELOG, with bounded carrier/placement regressions in the existing test file. The broader behavioral experiment and receipt-reconciliation implementation remain out of scope.

## Scope

**Problem statement:** the intent verdict is advisory and single-lane.

**In scope:**

- `review_evidence.py` write path, validator, guided schema and guided approval actions; the delivery `does_not` advisory in `lifecycle_gates.py`; `lifecycle_gate_support.py` council template and instructions; `review_policy_reconcile.py` typed-authority text; the `wf_review_event` description and its handler-digest pin
- Seeds 100, 160, 209, 215, 239 and their rendered copies; Prepare and Review prompts; mcp-tool-surface, review-and-evals and CHANGELOG
- New tests (write path, validator, schema and template contract, carriers) and updates to existing council-approval fixtures and golden files

**Out of scope:**

- Judging whether the verdict is correct (a reviewer judgment)
- Rewriting historical ledgers or closed waves
- Additional specialist lanes or approval types; a behavioral test of delivery judgment beyond instruction coverage. Requirement 13 assigns the outcome check to an already required lane when QA is absent.

## Acceptance Criteria

AC-1 and AC-6 together test the intent: the approval path refuses an approval with no intent verdict, and the qa-reviewer, on its own, finds an intent gap a plan's ACs miss.

- [x] AC-1: Through `wf_review_event_response` on a scratch wave: a `council-readiness` approval with no `intent_fit` is refused with a diagnostic naming `intent_fit` and appends nothing; one with `does_not` is refused with the finding-route diagnostic and appends nothing; one with `partially` is appended and its record carries `intent_fit: partially`. The missing and `partially` cases hold for `council-delivery` and the legacy `wave-council-readiness` spelling; a `council-delivery` approval with `does_not` is appended. An identical retry of an approval recorded without the field replays. Known-bad in a scratch copy: removing the missing-value check fails the missing case; removing the `does_not` branch fails the finding-route assertion.
- [x] AC-2: The validator accepts every `docs/waves/**/events.jsonl` ledger in this repository unchanged, rejects a council approval record with an unknown value, and rejects a specialist approval record and a finding evidence record carrying the field.
- [x] AC-3: Specialist, operator and custom `wave-council-x` approvals record without `intent_fit` as before; each is refused when it carries one.
- [x] AC-4: A contract test reads the exported registry and finds `intent_fit` with both accepted values in the guided schema's council entry, a council approval action returned by `wf_review_wave`, the `wf_prepare_wave` council template and instructions, and the `wf_review_event` description; the handler-digest pin and golden fixtures are refreshed and their diff reviewed.
- [x] AC-5: A carrier test finds the new clauses in seeds 209, 215 and 239, the rendered council-chair and qa-reviewer docs, both Prepare and both Review prompts and the upgrade carriers, including the worst-verdict rule and both QA clauses, and finds no "`does not`" token beside `intent_fit` in any carrier.
- [x] AC-6: Before the run, the coordinator writes down one specific intent gap. A separate agent writes two change docs in neutral wording (no hint in title, rationale or logs): one whose ACs can all pass while that gap leaves the Product Intent unestablished, and a well-aimed control. A fresh qa-reviewer, briefed only with `docs/agents/qa-reviewer.md` and "review this plan per your role", reviews each. An intent-coverage finding is a stated part of the Product Intent that the reviewer says no AC tests. Pass: on the mis-aimed doc it names the pre-declared gap as untested; on the control it raises no intent-coverage finding. A fail leads to repairing the seed 239 clause and one run on freshly authored docs, never retries until it passes. The gap note, both docs, the prompt and both verdicts are kept in the wave folder. *Met on the operator-directed follow-up (finding 21KK5-DEL-AC6, repaired and reverified): the mis-aimed plan drew the declared gap (run 1), and an independently authored and vetted gap-free control drew no intent-coverage finding (evidence/ac6-control-run-declaration.md, evidence/ac6-results.md). Caveat: one sample each way, on simple plans.*
- [x] AC-7: This wave's re-recorded council approvals carry `intent_fit`, recorded through the new path with new context ids.
- [x] AC-9: A carrier test finds the triage rule of Requirement 11 in seeds 215 and 239, the rendered council-chair and qa-reviewer docs and `docs/contributing/review-and-evals.md`; this wave's own intent issues found at delivery (including the AC-6 control result) are recorded as typed findings with dispositions.
- [x] AC-8: On a scratch wave whose current `council-delivery` approval carries `does_not`, `wf_review_wave` and `wf_close_wave(dry_run)` report the advisory by name and it does not block (close with every other gate satisfied succeeds); with `partially`, no advisory appears. Known-bad in a scratch copy: removing the advisory fails the first case.
- [x] AC-10: Both Review prompts put the coordinator's draft and the assigned reviewer's independent confirmation or correction in an unconditional delivery step before the conditional Council step, with the no-required-lane limitation from Requirement 13. Seed 239 and the rendered QA role name that duty when QA is assigned, covering each change's Product Intent plus the wave Objective. Existing Council judgment and council-only `evidence.intent_fit` authority remain intact. A small carrier regression fails on the previous conditional placement and when the QA outcome duty is removed; focused tests and full documentation validation pass. This proves instruction coverage only.

- [x] AC-11: Both Review prompts assign the independent outcome check from the current delivery roster: QA when present, otherwise one existing required lane; an empty roster produces an explicit no-independent-lane-check note. The check stays before conditional Council and adds no lane or specialist verdict field. Seed 100, seed 160 and the rendered upgrade prompt, review-and-evals and CHANGELOG describe the same routing; QA carriers distinguish substantive intent findings from editorial wording. Bounded regressions cover all three roster shapes and reject missing fallback/empty-roster guidance and stale upgrade guidance. Evidence is instruction coverage, not autonomous reviewer reliability.

## Tasks

- [x] Repair roster-aware delivery assignment and reconcile the install/upgrade/summary carriers in Requirement 13; verify AC-11 with independent review.

- [x] Add the `intent_fit` registry, write-path check (after replay) and record field in `review_evidence.py`
- [x] Extend the validator, the guided schema and guided council approval actions; update the council template and instructions, the typed-authority text and the `wf_review_event` description; refresh the handler-digest pin
- [x] Edit seeds 100, 160, 209, 215 and 239 and their rendered copies, the Prepare and Review prompts, mcp-tool-surface and review-and-evals (re-derived census)
- [x] Census the tests that record council approvals; update shared helpers, fixtures and golden files
- [x] Add tests for AC-1 to AC-5; probe both write-check mutants in a scratch copy
- [x] Run the AC-6 check and keep its evidence
- [x] Add the delivery `does_not` advisory to the shared delivery evaluator in `lifecycle_gates.py` and its tests (AC-8)
- [x] Update CHANGELOG
- [x] Add the Requirement 11 triage rule to seeds 215 and 239, their rendered copies and review-and-evals, with its carrier test (AC-9)
- [x] Re-record council approvals with `intent_fit` (AC-7); full suite last
- [x] Correct the non-council delivery guidance in both Review prompts and both QA carriers; verify AC-10 and independently review the bounded repair.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| evidence-path | implementer | — | write path, validator, schema, actions, template, description |
| guidance | implementer | — | seeds, prompts, rendered copies, specs |
| fixtures-and-tests | implementer | evidence-path | census and helper updates, new tests, mutants |
| intent-check | qa-reviewer (fresh) | guidance | AC-6; docs written by a separate agent |


## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/lifecycle_gates.py`, `.wavefoundry/framework/scripts/lifecycle_gate_support.py`, `.wavefoundry/framework/scripts/review_policy_reconcile.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`, `.wavefoundry/framework/seeds/215-council-chair.prompt.md`, `.wavefoundry/framework/seeds/239-qa-reviewer.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/`, `docs/prompts/`
- `docs/agents/specialists/council-chair.md`, `docs/agents/qa-reviewer.md`, `docs/contributing/review-and-evals.md`, `docs/specs/mcp-tool-surface.md`
- `.wavefoundry/framework/scripts/tests/`
- CHANGELOG.md at the repository root.

## Affected Architecture Docs

N/A: one optional field on an existing record type and its write-time check; no boundary, flow or layering change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | the enforcement itself |
| AC-2 | required | history must stay valid; the field must stay meaningful |
| AC-3 | required | no change for other approvals |
| AC-4 | required | callers see the requirement before a refused write |
| AC-5 | required | guidance and enforcement agree |
| AC-6 | required | the only behavioral test of the independent QA half of the intent |
| AC-7 | important | dogfood on the wave that adds it |
| AC-9 | required | intent issues get a decision, not a stop or a note |
| AC-8 | required | an honest not-established delivery is visible before sign-off and stays closable |
| AC-10 | required | independent delivery intent judgment must also cover ordinary targeted waves without delivery Council |
| AC-11 | required | the assigned reviewer must actually exist and install/upgrade guidance must preserve the correction |


## Platform Behavior

Pure in-process validation of JSON fields and Markdown guidance; identical on Windows, macOS, Linux and WSL2. No paths, subprocesses or encodings change.

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-25 | Final-source canonical qualification passed 12,132 tests across 209 files, 12 existing skips, 616.333s, exit 0. All ten reviewed hashes unchanged; gates closed before execution and no source edits during it. Current green receipt written. All affected specialist and focused Council delivery approvals restored from the disclosed fresh independent review; only operator signoff remains. Earlier invalidated run preserved; no unchanged repeat or retrospective receipt rewrite. | .wavefoundry/framework/test-cache.json; events.jsonl; /private/tmp/21j63-roster-r_pgcj57/framework-suite.log |
| 2026-10-25 | Requirement 13 independently reverified in fresh delivery context 21j63-roster-delivery-independent-20261025. All ten hashes match. Eighteen focused tests passed in 2.614s; three real roster fixtures pass; both saved QA-only prompts rejected; five stale install/upgrade/summary carriers produce 20 expected assertion failures and zero errors. Conditional-placement, missing-assessment, missing-fallback and missing-empty-roster-note controls detected. No blocker; code/QA/docs-contract/focused-Council approval proposals share one disclosed independent context. AC-10/11 and repair task complete. Final-source qualification pending; all source and gate edits finish before that run. | IntentFitCarrierTests; cycle-5 reverification; /private/tmp/21j63-roster-r_pgcj57/reviewed-source.json |
| 2026-10-25 | Requirement 13 implemented across the ten admitted guidance/test paths. Actual selector fixtures cover QA-present, docs-contract-only and empty rosters. Both Review prompts assign from the roster and record absence rather than adding a lane. Install/upgrade/summary carriers reconciled; substantive outcome corrections versus editorial wording clarified in Review and QA. Eighteen focused tests passed in 2.395s after correcting a test-only invalid vocabulary lookup; baseline QA-only and stale carrier text are rejected. Full docs validation and diff check passed. Source frozen for fresh independent delivery review; no new role or runtime gate. | IntentFitCarrierTests; IntentFitApprovalCarrierTests; test_intent_fit_approvals; /private/tmp/21j63-roster-r_pgcj57/repair.diff |
| 2026-10-25 | Readback for Requirement 13: use QA when required, otherwise an existing required delivery reviewer; if none, record the absence rather than inventing a review. Reconcile all ten guidance/test carriers and clarify that substantive shortfalls are findings, wording-only corrections editorial. Before: a docs-only roster had no QA despite QA-only instructions, and upgrade summaries retained Council-first placement. After: the actual roster determines the owner and every named delivery carrier agrees. AC-10 reopened; AC-11 added. Focused readiness passed; cycle-5 repair_start and both edit-gate opens recorded before source edits. | current receipt review-policy-29221440c61a25e8f33b; select_required_review_lanes three-shape probe |
| 2026-10-25 | IR-1 completed and independently reverified in cycle 4; code, QA, docs-contract and focused Council delivery approvals restored. One fresh delivery reviewer shared these lanes, explicitly disclosed; intent_fit remains partially. Final editorial numbering correction independently confirmed against the prior reviewed hash. Full canonical execution passed all 209 files (12,131 tests, 12 existing skips, 635.267s); qualification was rejected only for coordinator changes to the edit gates and local prompt numbering during the run. No valid current receipt claimed. Operator prohibited a repeat on the unchanged tree; attempted repeat cancelled before execution. Receipt reconciliation separately planned as 21lue. No source changed after final review; no memory candidates proposed; no closure or commit. | events.jsonl; IntentFitCarrierTests; /private/tmp/21j63-ir1-vgdgjrnv/framework-suite.log; final five-path hashes |
| 2026-10-25 | IR-1 implemented in the five readback paths. Outcome drafting is now an unconditional step before QA in the local Review prompt and an unconditional acceptance check in the shipped template. Both QA carriers require independent confirmation/correction against every change's Product Intent and the wave Objective without Council; Council reuses QA's assessment. 17 focused tests passed in 2.535s; both saved pre-fix prompt bodies fail the new placement assertion; embedded conditional-placement and QA-removal controls are detected. Full docs validation and diff whitespace checks passed. Frozen repair diff and five hashes prepared for fresh delivery review; full framework qualification follows on this source. | IntentFitCarrierTests, IntentFitApprovalCarrierTests, test_intent_fit_approvals; /private/tmp/21j63-ir1-vgdgjrnv/repair.diff |
| 2026-10-25 | Readback: AC-10 closes the independent-delivery-check gap without changing close or Council selection. Before: targeted waves without Council reach close with no independent overall outcome judgment. After: the coordinator drafts before QA's delivery review; QA confirms or corrects against Product Intent and Objective, and any required Council reuses that assessment. Exactly both Review prompts, seed 239, rendered QA and the existing carrier-test file are edited. Readiness approved on current receipt; repair_start for 21J63-DEL-NONCOUNCIL-INTENT recorded before these edits. | baseline /private/tmp/21j63-ir1-vgdgjrnv; focused readiness context 21j63-ir1-focused-readiness-20261025 |
| 2026-10-25 | Operator accepted independent review IR-1 and directed this bounded correction before closure. Requirement 12 and AC-10 own the guidance and test scope. One focused readiness round, implementation and independent delivery reverification; no expansion into the optional triage wording or behavioral evaluation campaign. | operator recommendation; wave Review Checkpoints |
| 2026-10-24 | Planned | Operator: "who is reviewing AC's vs. objective / intent?", then "Let's do that now." |
| 2026-10-24 | Readiness repair (one bounded pass). code-reviewer: worst-verdict meaning (Requirement 2), guided actions and schema entry, fixture census, canonical-key predicate, replay order, digest pin. docs-contract: `wf_prepare_wave` council template and golden fixtures, prompt/seed/upgrade carriers, `does_not` spelling. qa-reviewer (APPROVE): legacy and custom keys in AC-1/AC-3, second mutant, real-corpus ledger check, finding-record reject case, AC-6 redesigned with a pre-declared gap, separate author, QA-only brief and a control, now required. Delivery-time QA duty is carrier-text only (Scope). | readiness reviews |
| 2026-10-25 | Focused verification: code-reviewer, qa-reviewer (intent_fit establishes) and docs-contract-reviewer APPROVE; council BLOCK on R1 (delivery refusal of `does_not` blocks honest close). Escalated; operator chose "refuse on readiness and accept at delivery with user acknowledgment". Second bounded repair: Requirements 1, 4, 6, 10, AC-1, AC-6 (finding definition, no retry-until-pass), AC-8, Risks (reflex row is not test-mitigated), Decision Log, Objective. Low lane notes carried into implementation: validate closed ledgers with `closure=True` (AC-2), golden regeneration needs `WF_UPDATE_LIFECYCLE_GOLDEN=1` and `WF_OVERWRITE_LIFECYCLE_GOLDEN=1`, carrier test lists the extra Requirement 6 files or cites the census, seed 237 line 88 clause. | wave.md Review Checkpoints |
| 2026-10-25 | Second focused verification: code-reviewer, qa-reviewer and docs-contract-reviewer APPROVE; council PASS (intent_fit establishes for 21kk5 and the Objective). Carried into implementation without re-planning (Requirement 10 already requires them): AC-8 adds a stale-acknowledgment case (acknowledgment recorded before the `does_not` council approval still reports) and an order-dropping mutant; validator cases for a readiness council record with `does_not`, `intent_shortfall_acknowledged: false` and the field on a non-operator record; the check is a close-only gate (`CLOSE_HARD_GATES`) keyed on the canonical delivery council key, with the `missing_operator_signoff` remedy naming the acknowledgment when needed; carriers add the `wf_close_wave` spec section, `docs/specs/` in the census, seed 209 operator-evidence text, seed 190 and Close prompts in the carrier test. The 2026-10-24 Decision Log row "Refuse `does_not` on an approval" is superseded by the 2026-10-25 row. | readiness approvals, receipt review-policy-0e601d2a38fb888a72fe |
| 2026-10-25 | Operator simplification after implementation started: the acknowledgment field, its validator rule and the close gate are replaced by a non-blocking `delivery_intent_not_established` advisory in the shared delivery evaluator (Review and Close) plus a sentence in the `missing_operator_signoff` remedy (Requirement 10, AC-8, Decision Log). The acknowledgment items carried from the previous row (stale-acknowledgment case, ordering mutant, `false` and non-operator validator cases, `CLOSE_HARD_GATES` placement) no longer apply. Code already reverted to match. Deviation: `review_policy_reconcile.py` typed-authority strings are migration pairs for older target prompt text; changing them needs a further legacy pair, and the Prepare prompts carry their own `intent_fit` clause, so they stay unchanged. Ledger corpus: all 321 `docs/waves/**/events.jsonl` validate with `closure=False` and produce no intent-related error under either mode; 14 closed ledgers report pre-existing unresolved-synthesis errors under `closure=True`, unrelated to this change. | operator: "as little overhead as possible", "yes" |
| 2026-10-25 | Implementation: code, fixtures (12 files, about 100 tests), goldens and carriers done; AC-1 to AC-5 and AC-8 checked; six scratch-copy mutants killed (missing-value check, readiness `does_not` branch, delivery advisory, advisory made blocking, ledger rule, QA duty text). AC-6 runs recorded in `evidence/ac6-results.md`: the mis-aimed plan drew both halves of the declared gap as blocking; both controls drew different, genuine intent gaps, so the control condition failed. Operator then added Requirement 11 and AC-9 (intent issues triaged like defects); AC-6's result is to be recorded as a typed finding at delivery under that rule. MCP server reloaded; a dry-run council approval without `intent_fit` is refused. Seed 237 typed-authority sentence left unchanged with the reconcile Deviation. | tests, mutants, `evidence/ac6-results.md` |
| 2026-10-25 | Delivery review. Findings triaged through the standard flow (Requirement 11): 21KK5-DEL-AC6 (important_ac, dont_do_later; AC-6 `[~]`), 21KK5-DEL-AC1 (required_ac, do_now, blocking; two AC-1 assertions added; QA reverified with four mutants), 21KK5-DEL-CURRENCY (do_now, non-blocking; currency-gate test added; edit preceded its repair_start, recorded as such; code-reviewer reverified), 21J63-DEL-OUTCOME-PLACEMENT (council; do_now, blocking; Intent outcome moved from Wave Summary into Review Checkpoints and merged wave-wide; council reverified). Same pass: real `requires_intent_fit` predicate in fixture helpers, advisory gated on a current council-delivery approval, census-safe corpus path, CHANGELOG wording. code-reviewer, qa-reviewer, docs-contract-reviewer delivery APPROVE; council-delivery PASS with `intent_fit: partially`; readiness approvals re-recorded after the AC-6 deferral (council `intent_fit: partially`). AC-7 and AC-9 checked. | events.jsonl, test_intent_fit_approvals |
| 2026-10-25 | AC-6 follow-up on operator direction: pass rule written first (evidence/ac6-control-run-declaration.md); a separate agent authored plan D, an independent agent vetted it gap-free (one AC-4 revision by the author), the plan froze (sha256 76e97b9c...), and one fresh qa-reviewer raised no intent-coverage finding. 21KK5-DEL-AC6 re-opened as a cycle 3 repair (record written after the run, stated in it) and reverified by a fresh qa-reviewer; AC-6 changed from `[~]` to `[x]` with a one-sample-each-way caveat. Intent outcome updated. | evidence/ac6-results.md, events.jsonl |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-24 | Carry `intent_fit` in the existing `evidence` payload, not a new tool parameter | no tool-schema change, so no client reconnect; evidence is already digested into the request identity | new top-level parameter (forces reconnect) |
| 2026-10-24 | Require at write, optional at read | existing ledgers stay valid without a rewrite | require on read with a cutoff (rewrites history or needs a date rule) |
| 2026-10-24 | Refuse `does_not` on an approval | approving while saying the intent is unmet contradicts seed 215's finding rule | accept and rely on prose |
| 2026-10-24 | qa-reviewer, not docs-contract, takes the intent-coverage duty | QA already maps every AC to evidence; intent coverage extends that map | docs-contract (scoped to specs) |
| 2026-10-24 | One value: the worst verdict across changes and Objective | a single field cannot carry per-change verdicts; worst-case keeps the refusal meaningful | per-change map in the approval (schema growth) |
| 2026-10-25 | Intent issues are typed findings triaged like defects (fix now, later, or not), not automatic stops or notes | operator: "when we encounter issues with intent, they need to be evaluated like we do a bug. They don't have to stop like that, but we need to evaluate them and determine whether they should be fixed now, etc." | keep "a gap that would leave the intent unestablished is a finding" (only the severe case gets a decision) |
| 2026-10-25 | Replace the acknowledgment field and close gate with a non-blocking advisory in Review and Close; the operator's existing sign-off is the acknowledgment | operator, asked to keep overhead low: "We want to ensure that the evaluation is being done with as little overhead as possible", then "yes" to simplifying; removes one field, one validator rule, one gate and the ordering logic | keep the explicit acknowledgment (a stale earlier sign-off is the residual case it covered) |
| 2026-10-25 | Refuse `does_not` at readiness; accept it at delivery and require the operator's acknowledgment on `operator-signoff` before close (acknowledgment part superseded by the row above) | operator decision after the readiness council blocked on delivery refusal ("refuse on readiness and accept at delivery with user acknowledgment"); an honest not-established outcome stays closable and visible | refuse in both phases (honest failures cannot close); accept everywhere (readiness approval of a plan that misses its intent) |
| 2026-10-24 | Leave the dashboard next-action text unchanged | the guided schema, actions and template carry the hint; the text is test-pinned | add the field name there |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Council reviewers set `establishes` by reflex | not mitigated by a test: the Boundary sentence states the tool checks presence and consistency only; the qa-reviewer's independent map (sampled by AC-6) is the second look, and accepting `does_not` at delivery removes the pressure to soften an honest verdict |
| Older clients send council approvals without the field | the refusal names the field and values; no reconnect needed |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
