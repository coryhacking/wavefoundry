# Review-Cycle Churn Controls: Mutation Evidence, Tree Freeze, Lane Budgets, Blocker Escalation

Change ID: `1wujr-enh review-cycle-churn-controls`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-01
Wave: 1wuju review-churn-and-evaluator-baseline

## Rationale

Wave `1wur7` spent five repair rounds on one finding. Every round through the
fourth was closed by the implementer and reopened by an independent lane that
deleted a mechanism and watched the suite stay green: the implementer verified
by writing tests that pass, never by removing the guard. The tree also moved
under the review lanes three times in one round, forcing each lane to
re-snapshot and re-sweep, and one lane spent over an hour running a whole
test file per mutant. Separately, a close-blocking failure owned by another
wave sat for hours with a one-token fix in hand because the coordinator
deferred it instead of presenting the fix and a decision. None of these are
properties of that wave's subject; they are gaps in the seeds that govern how
implementers land guards and how coordinators run review rounds.

## Requirements

1. Seeds `180-implement-feature` and `209-agent-harness-core` SHALL state the landing rule: a guard, validator member, or tuning constant is landed only when a named test fails with it deleted or loosened, and the implementer records the mutant and the failing test in the change document's Progress Log before requesting review. A pin that passes for an unrelated reason is not a pin. The rule is the implementer-side counterpart of seed `239`'s evidence-integrity condition 5 ("a pre-fix failure, a focused mutation, or injected old behavior") and SHALL cite it so there is one vocabulary; the same seed-209 edit adds one sentence to the existing bounded-census paragraph: a census is re-derived whenever its predicate moves, never carried forward (memory `1wud5-mem`).
2. Seed `209-agent-harness-core` SHALL own the review-round protocol (readiness DOCS-RDY-1: seed 190 is a closure checklist; the brief and the round already live in 209): a `tree_fingerprint` row in the `## Briefing Packet` required-fields table, computed as `git hash-object` over the reviewed paths (working-tree content, so untracked and modified files are covered) and recorded in every lane brief; a **Frozen tree per round** behavior under `## Harness Behaviors` (no edit under the reviewed paths while a lane runs; collect every lane's findings; repair once per round; re-snapshot once); and a once-per-round repair sentence under `### Repair re-verification`. A lane that recomputes the fingerprint and sees it changed reports a process finding rather than silently re-sweeping. The seed text SHALL state that this is new: `frozen_boundary` freezes the finding SET at convergence and `policy_input_digest` hashes change-document bodies, so neither freezes code. Seed `190` keeps one close-side hook: do not finalize with an unreconciled fingerprint-change finding.
3. Seed `209`'s Briefing Packet SHALL gain `time_budget` and `sweep_rule` required fields (targeted tests per mutant, whole-file runs only for survivors, a stated wall-clock budget), and the lane seeds `221-code-reviewer`, `239-qa-reviewer`, and `214-architecture-reviewer` SHALL require a mutation table in their `## Verdict Format` sections. The mutation table is the per-mechanism prose projection of the Executable Evidence Record's existing `known_bad_detected` / `known_bad_detection_method: focused-mutation` fields (one row per landed mechanism: mechanism, mutation, failing test or NOT CAUGHT); it is report prose, not a new `events.jsonl` field, so lanes produce one evidence shape.
4. Seed `209` (`## Harness Behaviors`) and seed `180` (the coordinator `Escalation:` bullet) SHALL state the external-blocker rule: when a gate is blocked by an artifact the wave does not own, the coordinator presents the exact fix and a yes/no decision to the operator in the same message that reports the block, instead of deferring until asked.
5. The project prompt surfaces `docs/prompts/implement-wave.prompt.md`, `docs/prompts/review-wave.prompt.md`, and `docs/prompts/close-wave.prompt.md` AND the three lane role docs `docs/agents/architecture-reviewer.md`, `docs/agents/code-reviewer.md`, `docs/agents/qa-reviewer.md` (their bodies are hand-owned; the renderer owns only the marker regions, readiness DOCS-RDY-3) SHALL be hand-reconciled with the seed sentences outside the renderer-owned regions, following the seed-150 parity instruction; `wf_sync_surfaces` runs after the seed edits and `check_review_protocol_carrier_parity` stays green. Each load-bearing sentence SHALL be pinned by an `assertIn` test in the seed-pin pattern established by `test_ac_locality_rule_pinned_in_seed_170_and_reconciled_prompt`, and the Progress Log SHALL enumerate the pinned sentences at delivery. A `CHANGELOG.md` `## [Unreleased]` bullet SHALL announce the seed rules, since every consumer receives them.

## Scope

**Problem statement:** Implementers claim guards landed without a discriminating test, coordinators edit under running lanes, lane briefs carry no sweep rule or budget, and external blockers are deferred instead of escalated; each of these turned into rounds and hours in `1wur7`.

**In scope:**

- Seed text in `180`, `190`, `209`, `214`, `221`, `239`, the three reconciled prompt surfaces, and the three lane role docs.
- Pin tests for every load-bearing sentence this change adds.
- One paragraph in `docs/architecture/testing-architecture.md` naming the landing rule as a verification tenet.

**Out of scope:**

- A framework mutation-testing tool (a candidate follow-up once the seed rule has field data).
- Changes to the typed review ledger or its record shapes.
- Any change to what lanes review; this change governs how rounds run.

## Acceptance Criteria

- [x] AC-1: Seed `209` carries the landing rule, the census sentence, the `tree_fingerprint`, `time_budget`, and `sweep_rule` briefing fields, the frozen-tree behavior, the once-per-round repair sentence, and the external-blocker rule; seed `180` carries the landing rule and the blocker rule; seed `190` carries the close-side hook; and each load-bearing sentence is pinned by an `assertIn` test this change adds.
- [x] AC-2: Lane seeds `221`, `239`, and `214` require a mutation table in every delivery report, pinned the same way.
- [x] AC-3: The three prompt surfaces and the three lane role docs are reconciled with the seed sentences outside the renderer-owned regions, the parity tests this change adds pass, and the CHANGELOG bullet is present.
- [x] AC-4: The tests this change adds pass, the documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Draft the landing rule, round protocol, sweep rule, and blocker rule as seed text; open and close `seed_edit_allowed` around the edits.
- [x] Hand-reconcile the three prompt surfaces and the three lane role docs; run `wf_sync_surfaces`.
- [x] Add the seed-pin and prompt-parity tests; enumerate the pinned sentences in the Progress Log.
- [x] Add the CHANGELOG Unreleased bullet.
- [x] Add the verification-tenet paragraph to `docs/architecture/testing-architecture.md`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Seed text | implementer | — | Six seeds, gate opened and closed around the edits; 209 owns the round protocol |
| Prompt reconciliation | implementer | Seed text | Three prompt surfaces plus three lane role docs; `wf_sync_surfaces` after |
| Pins | implementer | Prompt reconciliation | `assertIn` on load-bearing sentences only |


## Serialization Points

- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`, `.wavefoundry/framework/seeds/190-finalize-feature.prompt.md`, `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/214-architecture-reviewer.prompt.md`, `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md`, `.wavefoundry/framework/seeds/239-qa-reviewer.prompt.md`
- `docs/prompts/implement-wave.prompt.md`, `docs/prompts/review-wave.prompt.md`, `docs/prompts/close-wave.prompt.md`
- `docs/agents/architecture-reviewer.md`, `docs/agents/code-reviewer.md`, `docs/agents/qa-reviewer.md`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`, `docs/architecture/testing-architecture.md`
- The root `CHANGELOG.md` Unreleased section (a root-level file cannot be declared as a path; it is named here in prose).

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` (verification tenets: the landing rule)

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The rules are the change; unpinned seed text drifts. |
| AC-2 | required | Lane reports without a mutation table cannot be checked for the landing rule. |
| AC-3 | required | Prompt surfaces are what agents in this repository read. |
| AC-4 | required | The replacement shape, applied to itself. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-01 | AC on the change's own evidence, the replacement shape applied to itself: the tests this change adds pass, the documents it authors or edits validate (`wf_validate_docs` green), and the coordinator's full run on the implemented tree shows no failure elsewhere (8,026 tests across 69 files, all green, receipt `ok`). | `full_suite_1wuju2.log` in session scratch; `.wavefoundry/framework/test-cache.json` 8,026 ok. |
| 2026-09-01 | Gapfill: the first full-suite run on the implemented tree failed `test_declaration_change_loses_no_lane_anywhere_in_the_corpus` on this wave's own three change documents. Cause: a bare root-level `CHANGELOG.md` inside a Serialization Points bullet is not a repo-relative path to the stricter parser, so the whole bullet became prose and the tests and architecture paths sharing it went undeclared, losing lanes. Fixed by naming the CHANGELOG in its own prose bullet; all three documents now declare every path their legacy scan saw with no lane lost. The same trap caught wave `1wpig`'s document a day earlier with a glob; the scaffold's guidance names neither shape, which is a docs-contract note for the lanes. | `test_review_policy.py` corpus probe over the three documents (legacy 14/12/5, new 14/12/5, lost none); `docs-lint: ok`. |
| 2026-09-01 | Implemented (seed gate opened and closed around the edits; `wf_sync_surfaces` run afterwards). Seed 209: three Briefing Packet required fields (`tree_fingerprint` by `git hash-object` over `files_in_scope`, `time_budget`, `sweep_rule`), the **Frozen tree per round** and **External blocker escalation** harness behaviours with the `tree_moved_under_review` process finding and the statement that `frozen_boundary` and `policy_input_digest` freeze neither code, the once-per-round repair sentence under Repair re-verification, the **Landing rule for guards** under Code-Grounded Verification bound to qa condition 5's `focused-mutation` vocabulary, and the census re-derivation sentence. Seed 180: the landing rule beside "Reading code is not executing it" and the blocker rule on the coordinator Escalation bullet. Seed 190: the `tree_moved_under_review` closure guardrail. Seeds 214, 221, 239: the mutation-table requirement in each Verdict Format as the prose projection of `known_bad_detection_method: focused-mutation`. Reconciled outside renderer-owned regions: `implement-wave.prompt.md` (two guardrails), `review-wave.prompt.md` (packet fields and frozen-tree sub-bullets under step 2), `close-wave.prompt.md` (closure bullet), `docs/agents/{architecture,qa}-reviewer.md` Output Shape and `code-reviewer.md` Review Rubric; `testing-architecture.md` gained a Landing Rule section; CHANGELOG bullet added. Pinned sentences (each an `assertIn` in `ReviewCycleChurnControlPinTests`): the three packet rows; the Frozen-tree sentence; the neither-freezes-code sentence; the `tree_moved_under_review` sentence; the External-blocker heading and its same-message sentence; the once-per-round sentence; the Landing-rule sentence and its focused-mutation binding; the census sentence; the seed-180 landing and escalation sentences; the seed-190 guardrail; the three lane-seed mutation-table sentences; the two implement-wave guardrails; the two review-wave sub-bullets; the close-wave bullet; the two role-doc bullets and the code-reviewer rubric line; the architecture section heading; the CHANGELOG bullet. Prose pins are landed by construction (deleting the sentence fails its assertion), which is the honest limit of a seed-text change. | `ReviewCycleChurnControlPinTests` 4 tests OK; `test_docs_lint.py` full file run recorded at the wave's suite run; `wf_validate_docs`; `check_review_protocol_carrier_parity` green under the full lint. |
| 2026-09-01 | Delivery round 1. DOCS-DEL-1 parity: the plan-feature prompt now carries the release-checklist clause (every sensor still advisory is listed so the flip is decided, not defaulted) and states that the diagnostic supplies the replacement sentence; the review-wave prompt states that neither `frozen_boundary` nor `policy_input_digest` freezes code, that a repair landed under a running lane invalidates its evidence, and that lanes report at the budget and list what was not run; the three lane role docs carry the report-at-budget clause; `testing-architecture.md` carries the census re-derivation sentence; `change-workflow.md`'s carrier count was re-derived with the sensor itself (still eight across four non-closed waves, five in parked plans) and is dated to this wave with its predicate. QA-DEL-1: the four seed clauses that were deletable with the pins green (the Progress Log recording sentence in seeds 209 and 180, the unrelated-reason sentence, the working-tree clause of the `tree_fingerprint` row, the collect-repair-resnapshot sentence) are pinned by extended `assertIn` strings. | `ReviewCycleChurnControlPinTests`; `wf_validate_docs`. |
| 2026-09-01 | Landing rule, delivery round 1: four scratch-copy seed deletions under `mut10`, each caught by the extended pins: the `tree_fingerprint` working-tree clause, the collect-repair-resnapshot sentence, and the Progress Log recording sentence in seed 209 (`test_seed_209_owns_the_round_protocol_and_the_landing_rule`); the recording sentence in seed 180 (`test_seeds_180_and_190_carry_the_implementer_and_close_hooks`). | `mut10_run.py` log. |
| 2026-09-01 | Delivery round 2. DOCS-DEL-2: every clause the round-1 repair added to the prompts, role docs, and `testing-architecture.md`, and the report-at-budget tail on seeds 209/214/221/239, is now pinned by an extended `assertIn` (each was deletable with the pins green). The plan-feature prompt says "decided, not forgotten" as seed 170 does; the allowlist comment in `wave_validators.py` no longer says a false positive is a hard stop today. | `ReviewCycleChurnControlPinTests`, `AdvisoryFirstRulePinTests`; scratch deletions in round 2. |
| 2026-09-01 | Landing rule, delivery round 2: seven scratch-copy clause deletions under `mut11`, each caught by the extended pins: the review-wave prompt clause, the qa role-doc clause, and the `testing-architecture.md` census sentence (`test_prompt_surfaces_and_role_docs_are_reconciled`); the plan-feature release-checklist and replacement-sentence clauses (`test_prompt_surfaces_and_contributing_docs_are_reconciled`); the seed 214 report-at-budget tail (`test_lane_seeds_require_the_mutation_table`); the seed 209 `time_budget` row tail (`test_seed_209_owns_the_round_protocol_and_the_landing_rule`). | `mut11_run.py` log. |
| 2026-09-01 | Drafted from the `1wur7` retrospective: five repair rounds on one finding, each reopened by a lane deleting an unpinned mechanism; three mid-round tree snapshots; an hour-long whole-file sweep; a one-token external fix deferred for hours. | `1wur7` wave record, Review Evidence and Progress Logs; memory `1wvo1-mem`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-01 | Readiness council amendments adopted (RT-RDY-9, RT-RDY-10, DOCS-RDY-1, DOCS-RDY-2, DOCS-RDY-3, DOCS-RDY-11): seed 209 owns the round protocol and the briefing fields; the mutation table is the prose projection of the existing `known_bad_*` evidence fields, not a new ledger field; the fingerprint command is named; the three lane role docs join the reconciled set; a CHANGELOG bullet is added. | Seed 190 is a closure checklist and cannot own a round protocol; a second evidence shape would fork the vocabulary seed 239 already defines; a rule a lane cannot recompute is unfalsifiable; the role docs are what this repository's lanes read. | **Keep 190 as owner:** the brief and round text would sit apart from the packet they govern. **New ledger field:** out of scope and duplicative. |
| 2026-09-01 | Seed rules and pins first; no mutation-testing tool in this change. | The rule can be stated and pinned now and produces field data on whether a tool is needed; a tool built before the rule has no calibration. | **Build a framework mutation harness now:** larger, and its scope (which mechanisms, which tests) is unknown until the rule has been applied a few times. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Seed text is read but not followed. | Each rule names the artifact a reviewer can check (mutant plus failing test in the Progress Log; fingerprint in the brief; mutation table in the report). |
| Freezing the tree slows a round. | Batching repairs per round is what removes re-sweeps; the round is shorter overall. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
