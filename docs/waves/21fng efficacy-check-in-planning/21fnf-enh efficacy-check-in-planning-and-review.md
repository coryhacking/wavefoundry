# Efficacy Check in Planning and Review

Change ID: `21fnf-enh efficacy-check-in-planning-and-review`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-23
Wave: 21fng efficacy-check-in-planning

## Rationale

Planning tests a plan against its own text (Divergent Pre-Plan, Product Intent, seed 209's outcome check), but rarely tests whether the chosen mechanism will achieve the goal in the real system. Seed 170 already requires "Code-grounded authoring" (execute the mechanism, run the census), yet in wave `21cw4` three readiness amendments were caused by mechanism flaws that block asks planners to catch: 21cw5 rounds 1 and 2 (an imported module's `__file__` is the link target; a relative `--model-bundle` after the directory change) and 21cw2 round 2 (the parser spans headings, so the closing change's own gate read the last status).

Two facts explain why the existing guidance did not help, and point at the levers that can:

- The self-hosted `docs/prompts/plan-change.prompt.md`, which agents in this repository read through the plan-change skill, does not contain the Code-grounded authoring block at all; only the 315-line seed does.
- The only review step that runs on every readied wave is the Wave Council's red-team primer at Prepare (`wave_review.enabled`); Review plan is optional and operator-invoked.

The 2026-10-23 review of seven harness-engineering proposals (`evidence/harness-items-efficacy-review.md`) showed what an explicit efficacy pass adds: replaying each proposal's motivating case, its leverage, its noise and a cheaper path changed four of the seven before any plan was written.

## Product Intent

Planners and Prepare reviewers test whether a plan's mechanism will achieve its goal. Before: the efficacy questions are absent from the plan-change prompt agents read, and the red-team primer has no standing efficacy check, so mechanism flaws surface late or not at all. After: the plan-change prompt carries the Code-grounded authoring block with an efficacy bullet, the red-team primer replays each change's motivating case through its mechanism at every Prepare, and close cites the plan's measure of success. Boundaries: guidance only; no new template section, gate, lane, signoff or lint rule; existing plans are not converted. AC-5 tests whether the intent was established; AC-1 to AC-3 prove delivery.

## Efficacy Check

- **Motivating case replay:** of the three 21cw4 mechanism rounds, the existing block already asked for execution and planners skipped it, so more seed text alone would not have caught them. What changes the outcome is (a) the block reaching the prompt agents actually read and (b) the Prepare primer replaying the case, which is where two of the three were in fact caught.
- **Leverage:** advice to planners; a fixed check for the red-team primer, which runs at every Prepare on this repository and on installs with `wave_review.enabled`. The primer is the only guaranteed lever; the plan-change text is best effort.
- **Evidence of need:** three mechanism-class readiness amendments in `21cw4`; four of seven proposals changed in the harness review. No wider measurement exists yet.
- **Precision and noise:** risk of one-line boilerplate. Mitigation: the efficacy bullet sits in an existing required block rather than a new heading, answers are proportional, and the primer's replay must name the case and the outcome, which boilerplate cannot satisfy.
- **Cheaper path:** this is the cheaper path. A new template section, a separate planning step and edits to Review plan and seed 209 were considered and dropped at readiness (Decision Log).
- **How we'll know it worked:** AC-5 now; later, mechanism-class readiness amendments per change before and after, from the closed-wave ledgers once the planned ledger-metrics change lands. A negative AC-5 result keeps only the prompt carry-over and the primer check.

## Requirements

1. Seed 170's existing "Code-grounded authoring" block gains one bullet, **Mechanism efficacy**: before selecting an approach, replay the motivating case through the mechanism; state whether it controls the outcome or only advises and what makes someone act on advice; name what it would flag wrongly, miss, or what would make it ignored; check whether existing data or a mechanism gives most of the value; and state how success will be measured after release. Answers are proportional (one sentence for a small fix) and are recorded with the selected approach in the Decision Log.
2. `docs/prompts/plan-change.prompt.md` carries the Code-grounded authoring block, including the new bullet, with the same text as seed 170 under the same heading.
3. The red-team `council-adversarial-primer` gains a fixed **efficacy replay** output, separate from the tiered `primer_questions` count: for each change, replay its motivating case through its mechanism and state whether the mechanism would catch or fix it, and what would make it fail or be ignored. The derived carrier set is every file that defines the primer or enumerates its outputs or the seats' obligation to engage with them (census: files naming `primer_questions`), so the council chair passes the replay through and every seat must engage with it. As found at planning: seeds 225, 215, 237, 007 and 100; `docs/prompts/prepare-wave.prompt.md`, `docs/prompts/review-wave.prompt.md`, `docs/prompts/council-review.prompt.md`; `docs/agents/specialists/red-team.md` and `docs/agents/specialists/council-chair.md`. The implementation re-runs the census. The two specialist files are maintained by hand outside their rendered marker regions and have drifted from their seeds, so they are edited by hand and pinned by clause, not by body equality.
4. Close guidance asks the `Intent outcome:` paragraph to cite the plan's stated measure of success when one exists and say whether it can be read yet. The derived carrier set is every file holding the `Intent outcome:` guidance: seed 190, `install/lifecycle-prompts/close-wave.prompt.md`, `docs/prompts/close-wave.prompt.md` (as found at planning).
5. Existing targets learn of the plan-change carry-over and the new guidance through seed 160's changed-carrier list and its self-hosted copy in `docs/prompts/upgrade-wavefoundry.prompt.md`; seed 100 is updated only where it enumerates the plan-change prompt's contents.
6. Tests pin the new text: a clause kind for the Code-grounded authoring block across seed 170 and the plan-change prompt (equal bodies, the prompt carrying the block verbatim under the same heading), and clause-only checks for the primer efficacy replay and the close measure-of-success sentence in each carrier.

## Scope

**Problem statement:** the plan-change prompt agents read lacks the code-grounded and efficacy guidance, and no review step that always runs asks whether a mechanism will achieve its goal.

**In scope:**

- Seeds 170, 225, 215, 237, 007, 190, 160 and 100; `docs/prompts/plan-change.prompt.md`, `docs/prompts/prepare-wave.prompt.md`, `docs/prompts/review-wave.prompt.md`, `docs/prompts/council-review.prompt.md`, `docs/prompts/close-wave.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`; `install/lifecycle-prompts/close-wave.prompt.md`; `docs/agents/specialists/red-team.md`, `docs/agents/specialists/council-chair.md`.
- Clause tests in `tests/test_render_agent_surfaces.py` (new kinds).
- The AC-5 comparison and its frozen inputs under the wave's `evidence/` folder.

**Out of scope:**

- A plan-template section, Review plan or seed 209 changes, any gate, lane, signoff or lint rule.
- Converting existing plans or waves.
- The ledger-metrics report and the harness items (planned separately).

## Acceptance Criteria

- [x] AC-1: Seed 170 and `docs/prompts/plan-change.prompt.md` carry the Code-grounded authoring block with the Mechanism efficacy bullet and identical text; the new clause test fails if the prompt copy lacks the block, if the bodies differ, or if any of the bullet's five questions is removed.
- [x] AC-2: Every file that defines the primer or enumerates its outputs or seat obligations carries the efficacy replay (as a fixed output separate from `primer_questions`, as a packet field the chair passes on, and as something every seat must engage with); the clause test fails if any carrier lacks it.
- [x] AC-3: Every carrier of the `Intent outcome:` guidance asks it to cite the plan's measure of success; seed 160's changed-carrier list and its self-hosted copy name the plan-change carry-over; the clause test fails if any carrier lacks the sentence.
- [x] AC-4: Readiness records, for each Efficacy Check claim in this plan (the replay, leverage, evidence, noise, cheaper path and measurement claims), whether it held against the code and the wave records.
- [x] AC-5: A controlled comparison with inputs authored and frozen in `evidence/` by an agent other than the planner, before any run, with each input's source recorded: (a) held-out case: the proposal "derive the close-time Intent outcome automatically from checked acceptance criteria", built from a rejected alternative in change `2124m`'s Decision Log stated without its rejection reason (its flaw, that checked ACs prove implementation rather than outcome, was not used to derive the questions); (b) derived case, a sanity check only: the scope-drift sensor from `evidence/harness-items-efficacy-review.md`, stated without the directory detail; (c) false-flag control: change `21ayv`'s sound proposal (treat Grep and Glob as non-edit tools in the pre-edit hook). Each case goes to fresh independent planning agents under the new plan-change guidance and under the current guidance, at least two runs per arm. Pre-stated reading: the guidance shows an effect only if the new arm names the held-out flaw in more runs than the current arm without flagging the control; equal detection is a negative result, recorded as such, and the change then keeps only Requirements 2 and 3.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the Mechanism efficacy bullet to seed 170's Code-grounded authoring block; carry the block into `docs/prompts/plan-change.prompt.md`.
- [x] Add the efficacy replay to every primer carrier (definition, packet and seat obligations), re-running the `primer_questions` census.
- [x] Add the measure-of-success sentence to every `Intent outcome:` carrier; update seed 160's changed-carrier list, its self-hosted copy, and seed 100 where it enumerates plan-change contents.
- [x] Add the clause tests.
- [x] Freeze the AC-5 inputs, run the comparison, record results and limitations.
- [x] CHANGELOG Unreleased entry (Changed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                   |
| ---------- | ----------- | ---------- | --------------------------------------- |
| guidance   | implementer | none       | seeds, prompts, specialist copy         |
| tests      | implementer | guidance   | clause kinds                            |
| comparison | reviewer    | guidance   | frozen inputs; fresh agents per run     |


## Serialization Points

- `.wavefoundry/framework/seeds/`, `.wavefoundry/framework/install/lifecycle-prompts/close-wave.prompt.md`
- `docs/prompts/`, `docs/agents/specialists/red-team.md`, `docs/agents/specialists/council-chair.md`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`

## Affected Architecture Docs

N/A: guidance text in the planning, review and close workflow; no code boundary, data flow or verification seam changes.

## Platform Behavior

Text only; identical on native Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority  | Rationale                                         |
| ---- | --------- | ------------------------------------------------- |
| AC-1 | required  | the guidance reaches the prompt agents read       |
| AC-2 | required  | the one lever that always runs                    |
| AC-3 | required  | measurement carried to close and to upgrades      |
| AC-4 | required  | the change's own efficacy claims are tested       |
| AC-5 | important | behavioural evidence, can come out negative       |
| AC-6 | required  | change-local verification                         |


## Progress Log


| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-10-23 | Planned | operator request after the harness-engineering efficacy review |
| 2026-10-23 | Readiness round 1 redesign: the plan's own efficacy check failed review. Seed 170 already required code-grounded execution that planners skipped; the self-hosted plan-change prompt lacks that block; Review plan is optional; AC-5 could not fail. Redesigned to the reviewer's cheaper path: one bullet in the existing block, carry the block into the prompt agents read, a fixed primer replay, the close measure; template section, Review plan and seed 209 edits dropped; AC-5 rebuilt with a held-out case, a false-flag control, two runs per arm and a pre-stated negative reading; 21bzn removed from the Rationale; harness review recorded in `evidence/`. | readiness subagent a7b98251 |
| 2026-10-23 | Readiness round 2 amendments: the primer carrier set now includes every file that enumerates primer outputs or seat obligations (seeds 215, 237, 007, 100; prepare-wave, review-wave and council-review prompts; council-chair specialist), so the replay reaches the seats; specialist files are hand-edited and clause-pinned; AC-5 names its held-out case (2124m's rejected "derive outcome from checked ACs"), its derived sanity case and its control (21ayv), authored and frozen by a non-planner agent. | readiness recheck a7b98251 (blocking 1 and 2) |
| 2026-10-23 | AC-5 comparison ran (12 runs, then a 5-run rerun with the identical brief and model). Comparison inconclusive: a safety classifier stopped every baseline run for cases (a) and (c), 8 runs in all, plus 2 new-arm control runs. The new arm caught the held-out flaw in 2 of 2 runs and did not flag the control in its 1 completed run; case (b) was caught in both arms. Case (a)'s Source line quotes the prior decision's title, a partial hint to both arms. The operator directed AC-5 marked complete as the most that could be done; the pre-stated reading was not reached, and the measure of success after release stands. | `evidence/ac5/results.md` |
| 2026-10-23 | Gapfill: implementation used shell reads and scripted exact-string replacements rather than the MCP retrieval tools. The edits were prose insertions at known anchors in carriers already named by the plan, each replacement asserted a unique match, and the carrier census is a literal-token search (`primer_questions`) that grep answers exactly; the clause tests now pin the same census. | implementation session |
| 2026-10-23 | Delivery repair CODE-DEL-1 (code-reviewer, confirmed by qa-reviewer and red-team): the primer test checked only the `efficacy_replay` token, so a carrier could drop its seat obligation or chair-packet field and stay green. Each carrier now has its own required clauses. Folded in from the same reviews: the census covers `install/` and only `docs/agents/specialists/` (memory and handoff records no longer false-fail it; pointer-form `docs/prompts/agents/` prompts describe the primer without enumerating outputs and stay outside); prepare and review paths resolve through the vocabulary profile; seed 160 and its copy are pinned; and, from the red-team's strongest challenge that the efficacy bullet came after Select, the Divergent Pre-Plan Critique step in seed 170 and the plan-change prompt now points to the efficacy questions before selection, pinned by a test. Six mutants, including the four that survived, now fail. | `scratchpad/repair_mutants.py`; focused suite 191 OK |
| 2026-10-23 | Measure of success, made readable (qa-reviewer finding 5): a mechanism-class readiness amendment is a readiness-round change to a plan's Requirements, ACs or selected approach made because the chosen mechanism, once executed or replayed, would not achieve its goal. The before-figure is a per-change rate over closed waves before this change; it is not computed yet and belongs to the planned ledger-metrics change, which must take it before reading the after-figure. | delivery review |
| 2026-10-23 | Efficacy Check claims against the readiness and delivery records (qa-reviewer finding 1). Replay: the round-1 claim was refuted at readiness; the amended claim (the block reaching the prompt agents read, plus the primer replay) stood at the council; at delivery the red-team found the bullet came after Select, repaired by the Critique pointer. Leverage: round 1 refuted; the amended claim (primer is the only guaranteed lever, plan-change text best effort) stood. Evidence of need: not separately checked at readiness; the 21cw4 count rests on this plan's own reading. Precision and noise: not separately checked at readiness; delivery reviewers named rote replay as the main residual risk, unenforced by design. Cheaper path: held; the council adopted the reviewer's cheaper path. Measurement: round 1 refuted; amended to AC-5 plus a ledger measure; AC-5 was inconclusive, and the ledger measure is not readable until the before-figure is taken (follow-up in `wave.md`). | `ev-approval-council-readiness`; readiness lane approvals; this delivery review |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-23 | One efficacy bullet in the existing Code-grounded authoring block, carried into the plan-change prompt agents read, plus a fixed replay in the red-team primer and a close measure | Existing required guidance went unread because the prompt copy lacked it; the primer is the only step that always runs; no new heading invites boilerplate | New template section and planning step (readiness: repeats the cause, adds boilerplate); reviewer question only (finds flaws a round later); a lint presence rule (rewards presence over substance); Review plan edits (optional step, low leverage) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Planners still skip the block | The primer replay at Prepare catches what planning misses; AC-5 measures planner effect directly |
| The primer replay becomes rote | It must name each change's motivating case and outcome |
| AC-5 is noisy | Two runs per arm, a false-flag control, inputs frozen first, and a pre-stated negative reading |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
