# Review and Planning Guidance Follow-ups

Change ID: `23zbe-doc review-and-planning-guidance-follow-ups`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 23zbg review-and-planning-guidance

## Rationale

Five operator-accepted verdicts from the v1.46.0 field feedback (2026-11-21) found gaps in planning and review guidance. Each one is closed with seed and prompt prose only. Evaluations: `.wavefoundry/work/23zbg/eval/permissions-security-reviewplan.md` (items 12, 11a), `.wavefoundry/work/23zbg/eval/plan-template.md` (items 10.2, 10.3) and `.wavefoundry/work/23zbg/eval/upgrade-and-backlog.md` (item 13.6).

- **Item 12.** Seed 070 gives no shape for `docs/SECURITY.md` (Task 2 only says "Create or update reliability, security, and performance posture docs"). Seed 213 already tells the security reviewer to read `docs/SECURITY.md` for trust classes (seed 213, Credible-Threat Gate, first bullet). Per-finding dispositions live in each wave's ledger, so a classification the operator settled in one wave is invisible to the reviewer in the next, and the reviewer re-flags it.
- **Item 11a.** Seed 175 "Compare the draft with its brief" asks what is "strong, vague, missing, removable, or less useful to the consumer". It does not ask whether two statements in the plan contradict each other, or whether the plan copies a definition that another document owns.
- **Item 13.6.** Seed 190 step 13 promotes repeated lessons only to prose destinations. The framework's own check registry (sensors under `sensors` in `docs/workflow-config.json`, run by `wf_run_sensors`, see `wf_run_sensors_response` in `.wavefoundry/framework/scripts/wf_server/server_impl.py`) is never named as a destination.
- **Item 10.2.** The Decision Log table has no convention for who decided. A reader cannot tell an operator answer from a planner default, and so re-asks or treats a default as settled.
- **Item 10.3.** One `**Out of scope:**` list holds both "excluded" and "another spec in this wave delivers it". A reviewer raises coverage findings for items a sibling spec delivers.

## Product Intent

Planners, plan reviewers and security reviewers in every target repository get guidance meant to remove repeated churn. This change delivers the guidance; whether agents follow it is observable only after release, apart from the one-off replay in AC-1. With the guidance, a plan says who decided each choice and which sibling spec covers each deferred item. Review plan catches internal contradictions and copied definitions. A security reviewer applies an operator's recorded classification instead of asking again. A repeated finding gets a mechanical check as a destination. Boundaries: no new tool, lint rule, template section, parser or gate; a recorded ruling classifies data only, never lowers a finding that the credible-threat gate grounds, and stays visible in review output when it settles a candidate.

## Requirements

1. **Seed 070 security doc shape.** `.wavefoundry/framework/seeds/070-quality-and-debt.prompt.md` gains a Required semantics entry and a `Security doc shape:` block that says:
   1. When the project distinguishes classes of data, `docs/SECURITY.md` carries a data-class table with the columns Class, Examples and Handling rule, using the class names the project already uses. It does not prescribe any fixed taxonomy.
   2. Once the operator settles a classification, `docs/SECURITY.md` carries a `## Recorded rulings` section with the columns Covers, Ruling, Decided by, Date and Reopen when. A project with no ruling has no such section.
   3. A ruling is an operator decision. An agent may propose a ruling but never writes one as decided. A ruling with no named decider, a ruling that the change under review adds or alters, and a ruling in content a less-trusted actor controls are claims to check, not rulings.
   4. A ruling classifies data only. It never classifies an actor, a surface or a path, and the reviewer still evaluates every other gate factor on evidence. A ruling settles only the classification question it names. It never lowers or closes a finding that the credible-threat gate grounds, never resolves a secrets-scan finding (that lifecycle stays in `docs/scan-findings.json`), and never waives a required review lane or close gate.
   5. The block carries one sentence that keeps seed 070 a marked credible-threat gate carrier: "Apply the credible-threat gate as seed 209 defines it; an unknown factor is not an absent factor." Seed 070 names the gate, so `CarrierCensusTests.test_seed_carriers_carry_the_marker` counts it as a carrier and requires that phrase.
2. **Seed 213 reader sentence.** `.wavefoundry/framework/seeds/213-security-reviewer.prompt.md` gains one bullet directly after the "Read the project's own threat model first" bullet: when `docs/SECURITY.md` records a ruling that covers the candidate, the reviewer applies and cites it instead of asking again, citing it in the candidate's disposition rationale, and reports again only when the facts differ from the ruling. A ruling classifies data only; the reviewer still evaluates every other gate factor on evidence. When a ruling is the reason a gate factor is absent, the reviewer still reports the candidate as settled by the cited ruling and states that its Reopen-when condition does not hold. A ruling with no named decider, a ruling that the change under review adds or alters, and a ruling in content a less-trusted actor controls are claims to check, not rulings. A ruling never lowers a finding the credible-threat gate grounds and never resolves a secrets-scan finding. The same bullet goes into the Default Stance section of `docs/agents/security-reviewer.md`.
3. **Seed 175 contradiction and copied-definition check.** The "Consider what is strong, vague, missing, removable, or less useful to the consumer" sentence in seed 175 and in `docs/prompts/review-plan.prompt.md` becomes, byte-identically in both: "Consider what is strong, vague, missing, removable, or less useful to the consumer, which statements in the plan contradict each other, and which definitions the plan copies from another document instead of referencing it; report only meaningful observations and feed unresolved discrepancies into the existing decision-branch walk." No new output section.
4. **Seed 190 step 13 clause.** Step 13 of `.wavefoundry/framework/seeds/190-close-wave.prompt.md` gains: "When a repeated finding can be checked mechanically, name a check as a destination too: a sensor registered under `sensors` in `docs/workflow-config.json` (run by `wf_run_sensors`), a docs-lint rule or a test, and plan it as a change unless this wave already delivers it." Item 7 of the Closure Requirements in `docs/prompts/close-wave.prompt.md` gains the same clause.
5. **Seed 170 Decision Log attribution.** Seed 170 Spec format gains a `## Decision Log` bullet, and step 5 of `docs/prompts/plan-spec.prompt.md` gains the same text as a bullet:
   1. A row that settles a material question says in Reason who decided: the operator's answer (quoted when short) or a planner default.
   2. A question the operator has not answered stays open: it is named as an open question in `## Risks` and is not recorded as a decision.
   3. The Decision Log is inside the review-policy digest. An operator answer that arrives after readiness is recorded in `## Progress Log`; an answer that changes scope, requirements, acceptance or authority also amends its owning section and needs re-Prepare.
   4. Before treating a Decision Log row as a planner default, a reader checks `## Progress Log` for a later operator answer.
6. **Seed 170 Out of scope ids.** Seed 170 Spec format gains a `## Scope` bullet, and the `## Scope` bullet in step 5 of `docs/prompts/plan-spec.prompt.md` gains the same rule: when another spec admitted to the same wave delivers an Out of scope item, the bullet names that spec's change id; a bullet with no change id means the item is excluded.
7. Seed prose names no wave id or change id. New sentences use no em-dash, active voice and present tense.
8. The brief block (`**Brief before drafting:**`) and the `Code-grounded authoring` block of seed 170 and `docs/prompts/plan-spec.prompt.md` stay unchanged, so their byte-identity pins hold without edits.

## Scope

**Problem statement:** Planning and review guidance lacks five small rules, so reviewers re-flag settled classifications, plans hide who decided, sibling coverage reads as exclusion, internal contradictions pass Review plan, and repeated findings stay prose-only.

**In scope:**

- Seeds 070, 170, 175, 190 and 213 under `seed_edit_allowed`. Seed 070 becomes a credible-threat gate carrier counted by `CarrierCensusTests` in `.wavefoundry/framework/scripts/tests/test_credible_threat_unknown_factor.py`; the census needs no test edit because the seed carries the marker.
- Hand edits to `docs/prompts/plan-spec.prompt.md`, `docs/prompts/review-plan.prompt.md`, `docs/prompts/close-wave.prompt.md` and `docs/agents/security-reviewer.md`.
- Two new clauses in `CLAUSES["gap"]` of `BriefingLoopCarrierTests` in `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py` under `framework_edit_allowed`.
- One Unreleased CHANGELOG.md bullet.

**Out of scope:**

- Item 11b, a fixed-id report shape for Review plan. DECLINE: Review plan records no evidence and feeds no gate, so nothing reads the ids.
- Items 10.1, 10.4, 10.5 and 10.6 (source digests, cross-wave readiness, operator-action table, related-work fields). DECLINE: each is a new mechanism for a need that existing sections or git already meet (see `.wavefoundry/work/23zbg/eval/plan-template.md`).
- A template heading split for Out of scope, or a new Decision Log column. DECLINE: one sentence of guidance gives the same information without touching both template producers.
- Automatic detection of repeated findings across waves. DECLINE: a new mechanism with no finding identity across waves; the close step clause is enough.
- Adding data classes or a Recorded rulings section to this repository's own `docs/SECURITY.md`. DECLINE. Operator decision 2026-11-21: this repository's `docs/SECURITY.md` stays unchanged. Reason: the seed 070 block applies when a project distinguishes data classes, no ruling has been made here, and an empty section breaks seed 070's evidence-based guardrail.
- `install/lifecycle-prompts/review-plan.prompt.md` and `install/lifecycle-prompts/close-wave.prompt.md`. DECLINE: both delegate to the seed and carry no copy of the edited paragraphs.
- Seed 209 and seed 229 for item 12. DECLINE: only seed 213 reads `docs/SECURITY.md` for review.
- A clause on sibling change ids in the `explicit_non_goals` row of seed 209's briefing field table (item 10.3). DECLINE: a coverage reviewer reads the spec's Out of scope bullet itself, where the sibling id sits next to the item; a second carrier in seed 209 adds a seed to the set for no new information.
- Extending seed 160's upgrade reconciliation to the item 12 role-doc bullet. DECLINE: the change would add seed 213 to the "Changed project-owned review carriers" list, whose literal "seeds `170`, `180`, `190`, `209`, `214`, `221`, or `239` changed" `test_render_agent_surfaces.py` pins in seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md`, so it is not a one-line edit. The seeds ship in the pack, and existing targets keep their own role doc until an operator or agent merges the bullet.

## Acceptance Criteria

Prose ACs use a fixed-string search (`grep -F`) or a pinned test as the oracle. Each fails when the sentence is absent or reworded.

- [x] AC-1: Intent. A reviewer replaying the item 12 case (a sample identifier the operator already classified) through seed 213 and a `docs/SECURITY.md` built from seed 070 finds a rule that makes the reviewer cite the ruling and not re-ask, a rule that keeps a gate-grounded finding at full severity and the ruling-settled candidate visible in output, and a rule that does not apply a ruling the change under review adds or one held in less-trusted content. Fails if any rule is missing. Evidence at delivery: a one-off replay, recorded in the Progress Log, runs a reviewer subagent against a fixture `docs/SECURITY.md` holding a decided ruling, an undecided ruling and an over-broad ruling, with and without the new seed 213 bullet. The replay is evidence, not a test or a gate.
- [x] AC-2: Seed 070 carries `Security doc shape:` with the four Requirement 1 rules, including the exact phrases `Class, Examples and Handling rule`, `## Recorded rulings`, `Covers, Ruling, Decided by, Date and Reopen when`, `never writes one as decided`, `classifies data only`, `that the change under review adds or alters`, `never lowers or closes a finding that the credible-threat gate grounds` and `an unknown factor is not an absent factor`. `CarrierCensusTests.test_seed_carriers_carry_the_marker` passes with seed 070 counted as a carrier. The Required semantics list names the security doc entry. Seed 070 contains no `protected, restricted` taxonomy.
- [x] AC-3: Seed 213 and `docs/agents/security-reviewer.md` each contain the Requirement 2 bullet, found with `grep -F` on `applies and cites it instead of asking again`, `classifies data only`, `settled by the cited ruling`, `that the change under review adds or alters` and `never lowers a finding the credible-threat gate grounds`, with the seed copy directly after the "Read the project's own threat model first" bullet. `test_credible_threat_unknown_factor.py` stays green.
- [x] AC-4: Seed 175 and `docs/prompts/review-plan.prompt.md` carry the Requirement 3 sentence byte-identically. `CLAUSES["gap"]` gains `which statements in the plan contradict each other` and `which definitions the plan copies from another document instead of referencing it`. Known-bad: removing either clause from one carrier fails `test_deleted_empty_and_reversed_clauses_are_detected_in_every_carrier`, and a carrier mismatch fails `test_each_carrier_independently_satisfies_contract_and_matches`.
- [x] AC-5: Seed 190 step 13 and item 7 of `docs/prompts/close-wave.prompt.md` each contain `a sensor registered under \`sensors\` in \`docs/workflow-config.json\` (run by \`wf_run_sensors\`), a docs-lint rule or a test`.
- [x] AC-6: Seed 170 Spec format and `docs/prompts/plan-spec.prompt.md` step 5 each contain the Requirement 5 rules, found with `grep -F` on `says in Reason who decided`, `is not recorded as a decision`, `checks \`## Progress Log\` for a later operator answer` and `arrives after readiness is recorded in \`## Progress Log\``.
- [x] AC-7: Seed 170 Spec format and `docs/prompts/plan-spec.prompt.md` step 5 each contain `a bullet with no change id means the item is excluded`.
- [x] AC-8: No new sentence in any seed names a wave id or change id or contains an em-dash, checked by a reviewer against the seed diff.
- [x] AC-9: `python3 .wavefoundry/framework/scripts/run_tests.py --file test_render_agent_surfaces.py --file test_credible_threat_unknown_factor.py --file test_docs_lint.py --file test_compact_review_artifacts.py` passes, and the same files pass under `--profile declared` and `--profile second`. The full `python3 .wavefoundry/framework/scripts/run_tests.py` run writes a green receipt last.
- [x] AC-10: CHANGELOG.md `## [Unreleased]` has one bullet for this change that ends `Wave 23zbg / 23zbe.`, and `wf_validate_docs` passes.

## Tasks

- [x] Open `seed_edit_allowed` with `wf_open_gate(gate="seed_edit_allowed")`.
- [x] Edit seed 070: Required semantics entry and `Security doc shape:` block, including the gate marker sentence (Requirement 1).
- [x] Edit seed 213: ruling bullet after the threat-model bullet (Requirement 2).
- [x] Edit seed 175: extend the comparison sentence (Requirement 3).
- [x] Edit seed 190: step 13 clause (Requirement 4).
- [x] Edit seed 170: `## Scope` and `## Decision Log` bullets in Spec format (Requirements 5 and 6), outside the brief and Code-grounded blocks.
- [x] Close `seed_edit_allowed` with `wf_close_gate(gate="seed_edit_allowed")`.
- [x] Hand-edit `docs/prompts/review-plan.prompt.md`, `docs/prompts/plan-spec.prompt.md`, `docs/prompts/close-wave.prompt.md` and `docs/agents/security-reviewer.md` to match.
- [x] Open `framework_edit_allowed`, add the two clauses to `CLAUSES["gap"]` in `test_render_agent_surfaces.py`, record the known-bad mutant result in the Progress Log, then close `framework_edit_allowed`.
- [x] Add the Unreleased CHANGELOG.md bullet ending "Wave 23zbg / 23zbe.".
- [x] Run the AC-1 replay with a reviewer subagent against a fixture `docs/SECURITY.md` under `.wavefoundry/work/23zbg/`, with and without the seed 213 bullet, and record the result in the Progress Log.
- [x] Run the focused and profile test commands in AC-9, then `wf_validate_docs`, then the full suite last.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seed-edits | implementer | none | Seeds 070, 170, 175, 190, 213 under `seed_edit_allowed` |
| local-surfaces | implementer | seed-edits | Hand edits; render-surfaces does not propagate seed prose |
| test-pin | implementer | seed-edits | `CLAUSES["gap"]` under `framework_edit_allowed` |
| verification | implementer | local-surfaces, test-pin | AC-9 commands, then `wf_validate_docs`, full suite last |


## Serialization Points

- `.wavefoundry/framework/seeds/070-quality-and-debt.prompt.md`
- `.wavefoundry/framework/seeds/170-plan-spec.prompt.md`
- `.wavefoundry/framework/seeds/175-review-plan.prompt.md`
- `.wavefoundry/framework/seeds/190-close-wave.prompt.md`
- `.wavefoundry/framework/seeds/213-security-reviewer.prompt.md`
- `docs/prompts/plan-spec.prompt.md`
- `docs/prompts/review-plan.prompt.md`
- `docs/prompts/close-wave.prompt.md`
- `docs/agents/security-reviewer.md`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`

## Affected Architecture Docs

N/A. The change is prompt prose in five seeds and their local copies; it changes no module boundary, data or control flow, or verification seam.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Proves the item 12 intent and the no-suppression boundary |
| AC-2 | required | Item 12 template content |
| AC-3 | required | Item 12 reader rule; without it the rulings are never read |
| AC-4 | required | Item 11a, with a pinned known-bad check |
| AC-5 | required | Item 13.6 |
| AC-6 | required | Item 10.2 |
| AC-7 | required | Item 10.3 |
| AC-8 | important | Seed hygiene rule |
| AC-9 | required | Byte-identity pins and receipt |
| AC-10 | important | Release notes and docs validity |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-21 | The final default run passed 13,160 tests in 253 files with 12 skips (778.566 seconds). Its receipt matched the framework inputs. The docs-contract reviewer independently confirmed the prior install-format mismatch and byte equality after the one-line date correction (10,757 bytes). | Final receipt 431b8fca946d. Targeted reviewers for code, QA, docs contract and security approved with no delivery findings. QA verified the focused profile results and both six-case transcripts; the coordinator verified the final suite receipt. |
| 2026-11-21 | The four specified test files passed on the shipped and declared profiles (604 tests, zero skips per profile) and the second profile (604 tests, four skips). The first full run reported one failure in 13,160 tests. Commit 737d742e had updated both install-log format documents but dated only the project copy. Synced the shipped last-verified date to 2026-11-21. This one-line qualification repair brings the existing reference copies back into agreement. | The original failed ShippedReferenceDocParityTests.test_shipped_templates_are_byte_identical_to_canonical. After the repair the two files compared byte for byte and all 29 shipped-reference tests passed. |
| 2026-11-21 | Both versions handled all six fictional cases as expected. Each independent reviewer cited Casey for the offline sample, kept the undecided badge open, reopened the synthetic-only ruling for tenant input, retained the cross-tenant address finding at high severity, and rejected the new and untrusted rulings as publication authority. The revised instruction explicitly requires keeping the settled candidate visible. | Two fresh, read-only Codex sessions used the same model, the same fixture and the full pre-change or delivered seed 213. Both kept the settled case visible and requested no new classification for it. This trial shows the guidance works on these examples. It establishes no improvement over the baseline and does not measure downstream adoption. |
| 2026-11-21 | Each original comparison paragraph passed the briefing contract. Individually removing either new clause from the seed or its local prompt made the contract assertion fail in all four cases. Docs validation passed with one advisory about AC-9 asserting full-suite health. | BriefingLoopCarrierTests compared both source carriers independently. Gapfill: the checkout diff and exact literal checks established the authored wording and mutant results. |
| 2026-11-21 | Readback: planners attribute decisions and name the sibling spec responsible for shared scope. Reviewers check contradictions, use trusted operator rulings only for the classification in scope, and plan mechanical checks for recurring findings. | Update five seeds, four local documents, the gap-test clauses and release notes. For AC-1, replay the same six cases in fresh contexts with each version of seed 213. Check the settled example, undecided and overly broad rulings, an independent grounded finding, a new ruling and a less-trusted claim. Report both arms and any miss. Fixtures exercise review instructions; adoption remains a field question. |
| 2026-11-21 | Planned. Byte-exact census: searched the tests for literal phrases from every edited paragraph. | `test_render_agent_surfaces.py` `BriefingLoopCarrierTests` pins the seed 175 "gap" block (byte identity with `docs/prompts/review-plan.prompt.md`, no em-dash, clauses including `strong, vague, missing, removable, or less useful to the consumer`) and the seed 170 "brief" block. `EfficacyCheckCarrierTests` pins the seed 170 Code-grounded block verbatim in `docs/prompts/plan-spec.prompt.md`. No test quotes the edited text of seeds 190 step 13 or 213 line 74. Corrected in the readiness repair: `CarrierCensusTests` in `test_credible_threat_unknown_factor.py` scans every seed by name, so seed 070 becomes a carrier that must carry the marker once it names the gate; `test_credible_threat_unknown_factor.py` needs the seed 213 marker phrase kept; `test_docs_lint.py` and `test_compact_review_artifacts.py` pin other seed 190 lines. |
| 2026-11-21 | Readiness repair cycle 1 (implementer). Repaired R1-23zbe-seed070-census-marker, R1-23zbe-seed-070-credible-threat-carrier and R1-23zbe-seed070-gate-marker-census with one change: Requirement 1.5 marker sentence, AC-2 phrases, Scope carrier note and a corrected census row. Repaired R1-23zbe-ruling-bound-and-provenance with the bound, trace and provenance rules in Requirements 1.3, 1.4 and 2, AC-1 to AC-3 phrases and the Risks row. Absorbed the non-blocking notes: conditional Recorded rulings section (1.2), Progress Log check clause (5.4), AC-3 search phrase, honest Product Intent with the AC-1 replay, the requested security lane in Risks, the narrowed upgrade-reach claim, and DECLINEs for seed 160 and the seed 209 `explicit_non_goals` row. New review surface: the AC-1 replay task; the rule sentences are prose only. | repair_start events in `events.jsonl` for all four findings, context `23zbg-implementer-repair-1`; reviewer notes under `.wavefoundry/work/23zbg/review/`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-21 | Prose guidance in existing seed paragraphs, no template or tool change. | Operator verdicts of 2026-11-21 accept all five items as prose only. Efficacy: each rule only advises; the reader acts because the reviewer and planner already read these seeds at the step in question. Item 12 replay: the reviewer reads `docs/SECURITY.md` first (seed 213), finds the ruling, cites it. Success measure: no repeated classification question in field feedback after release. | A typed findings register (parked plan `1wq0b`): rejected as a mechanism the verdict declined. A template heading split: rejected, touches both template producers for no new information. |
| 2026-11-21 | Late operator answers go in the Progress Log. | Verified: `canonical_review_policy_body` in `.wavefoundry/framework/scripts/gardener_metadata.py` normalizes only workflow-status metadata, the date line, the Progress Log body, a boilerplate Session Handoff and checkbox markers; the Decision Log is digested byte for byte, so a Decision Log row added after readiness supersedes the receipt. Planner default. | Record late answers in the Decision Log: rejected, it lapses readiness approvals for narration. |
| 2026-11-21 | Seed 170 rules go in new Spec format bullets, and the local copies in step 5. | Keeps the pinned brief and Code-grounded blocks unchanged (Requirement 8). Planner default. | Extend the briefing paragraph: rejected, it forces a byte-identical edit to a pinned block. |
| 2026-11-21 | Seed 190 counterpart is item 7 of `docs/prompts/close-wave.prompt.md`. | The local prompt has no step 13 copy; item 7 is its lesson-promotion requirement. Planner default. | No local edit: rejected, the self-hosted close prompt would lack the rule. |
| 2026-11-21 | This repository's `docs/SECURITY.md` stays unchanged. | Operator decision 2026-11-21: accepted the planner recommendation; no data classes or rulings are recorded here yet. | Add empty data-class and Recorded rulings sections. |
| 2026-11-21 | Mirror the seed 213 ruling bullet into `docs/agents/security-reviewer.md`. | Operator decision 2026-11-21: accepted the planner recommendation, so this repository's own security reviewer applies recorded rulings. | Seed only, leaving the local persona without the rule. |
| 2026-11-21 | An unanswered material question is named as an open question in `## Risks`. | Operator decision 2026-11-21: accepted the planner recommendation; Risks is an existing template section, so no new heading is added. | A new Open Questions section. |
| 2026-11-21 | Seed edits do not rotate readiness receipts of other waves. | `policy_input_digest` covers the admitted specs and project policy, not seed files (`policy_input_snapshot` in `.wavefoundry/framework/scripts/review_policy.py`). Inferred from the receipt schema fields (`changes`, `project_policy_sha256`), not executed. | |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Recorded rulings become a suppression channel. | The bound (a ruling classifies data only and every other gate factor is evaluated on evidence), the trace (a ruling-settled candidate is still reported as settled by the cited ruling) and the provenance rule (a ruling with no named decider, one the change under review adds or alters, or one in less-trusted content is a claim to check) in Requirements 1.3, 1.4 and 2. The carve-out for gate-grounded findings protects only classification-independent findings. The coordinator made security-reviewer a requested lane on this wave. Prompt policy only, the same strength as the rest of the gate. |
| The seed 175 edit breaks the gap-block byte identity. | Edit both carriers with the same sentence; AC-4 tests catch a mismatch. |
| Seed 070 becomes a credible-threat gate carrier and fails the census. | Requirement 1.5 adds the marker sentence; AC-2 and AC-9 run `CarrierCensusTests`. |
| Profile vocabularies reject a new pinned clause. | The two new clauses carry no tier noun; AC-9 runs `--profile declared` and `--profile second`. |
| Existing targets keep old prose. | Seeds ship in the pack. Seed 160 reconciles the local copies for items 11a (briefing-loop carriers), 10.2, 10.3 and 13.6 (project-owned review carriers, seeds 170 and 190). It does not reconcile the item 12 bullet into an existing `docs/agents/security-reviewer.md`, or the seed 070 block into an existing `docs/SECURITY.md`: item 12 reaches new installs, and existing targets get it only when someone merges it. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
