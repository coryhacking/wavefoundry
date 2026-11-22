# Add Sentence-Structure Guidance to the Writing Guide

Change ID: `240wz-doc writing-guide-sentence-structure`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 241c3 writing-guide-sentence-structure

## Rationale

On 2026-11-21 a read-only review compared Wavefoundry writing with ASD-STE100 (`.wavefoundry/work/241c3/eval/ste-review-report.md`). Where the writing guide states a rule, most writing produced since its adoption follows it. The exception is passive voice in the changelog and the handoff, which stayed flat at about 22% and 25% although the rule exists. Three structural shortfalls remain where the guide is silent or soft:

1. **Overloaded sentences.** In specs and the changelog, 18% to 23% of sentences pass 25 words. Each of the two passages that a sampled reader could not follow packs an inline list or several obligations into one sentence (report passages 4 and 10).
2. **Several actions in one checklist item.** In spec task sections, 43 of 118 imperative sentences (36.4%) hold a second instruction; before adoption the figure was 35.1%. A reader marks an item `[x]` as one unit, so a half-done item has no honest state.
3. **Noun stacks.** Stacks fell by half without a rule, but the handoff (33.3 per 1,000 words) and review `observed` text (28.3) still stack four or more words before a head noun. The heuristic over-counts by about half; read the rates as relative.

Fragments are a smaller, related problem. The report counted 23.6% of handoff sentences of eight or more words with no article or determiner. A readiness sample found only 7 of 30 such sentences were fragments, so the fragment rate is nearer 6%, and this spec uses no fragment figure as a measure.

The guide currently says "There is no universal word or sentence limit" and gives no test for when a long sentence is a defect. The operator accepted the four ADOPT sentences and two reviewer practices on 2026-11-21, and rejected any prose linter, sensor, gate or hard sentence limit.

## Product Intent

Authors and agents who write specs, changelog entries, handoffs and review evidence get four checks in the guide. Each sentence carries one action or point, and each checkable item holds one result. The head noun comes first, and records use complete sentences. Their readers then recover meaning without reconstructing it. Reviewers apply the reader task to changelog entries and the handoff. The package prompt's changelog step and the Pause wave handoff step point writers to the guide at the moment of writing.

Delivery proves only that the guidance exists. It does not prove that writing changes, and that effect is observable only after release. The decision rule, which is advisory and gates nothing:

1. **Measure:** the share of spec sentences over 25 words, from `measure.py` in the wave's `evidence/` folder (row `specs POST`, column `over25_pct`). The baseline is 18.0% of 2,062 sentences. It is the only figure with enough sentences to show a change of a few points.
2. **When:** once three waves have closed after the first release that contains this change, and their specs hold at least 700 sentences. With fewer sentences, wait for the next wave and read again.
3. **Who:** the operator reads the result, following the evidence README.
4. **Threshold:** at 700 sentences the 95% noise band is about 3.3 points either way, so only a fall of at least 4 points counts.
5. **Action:** at 14.0% or lower, keep the guidance. Above 14.0%, the operator plans a revision of these sentences in a later wave.

The other figures in the evidence README are descriptive and decide nothing. The figures assume independent sentences, which overstates precision.

## Requirements

1. The guide's "Understandable" section gains these sentences, appended to the first paragraph after "Make pronoun references clear.", in this order:
   1. "Do not stack four or more nouns and modifiers before a head noun."
   2. "Name the thing first and attach the rest with a preposition or a clause."
   3. "For example, write “the fixture for the known-bad case with renamed vocabulary”, not “renamed-vocabulary known-bad fixture”."
   4. "A defined project term counts as one word."
   5. "Write complete sentences in handoffs, status records and the prose fields of review evidence." The rule covers prose fields such as `observed`, not schema fields such as `command_or_fixture`.
   6. "Keep the subject, the verb and the articles, so the reader does not have to supply who did what."
2. The instruction paragraph of "Understandable" gains one sentence, directly after "Give each step one coherent instruction; separate independent actions when order or verification matters.": "A task, checklist item or acceptance criterion holds one action or one result, unless one command or one observation verifies every part."
3. The paragraph that starts "There is no universal word or sentence limit." changes as follows:
   1. Directly after that sentence, it gains "Length is a prompt to check, not a limit."
   2. Next comes the report's ADOPT 1 sentence, unchanged: "When an instruction passes about 20 words, or any other sentence passes about 25, check that it carries one action or one point."
   3. Next comes "If it carries more, split it."
   4. Next comes "When such a sentence carries three or more parallel cases, move them into a list." The list rule therefore applies only to a sentence that passes the length prompt.
   5. The existing "A long technical explanation can be necessary" becomes "An extended technical explanation can be necessary", so "long" keeps one meaning in the paragraph. The rest of that sentence stays unchanged.
4. The "Check the reader's task" section's third paragraph gains these sentences, directly after "Existing applicable reviewers use these same reader tasks within their assigned remit and normal stop rules.", in this order:
   1. "Apply the same reader tasks to changelog entries and the session handoff."
   2. "In each sentence, find the actor and the result."
   3. "The author who rewrites a paragraph or list item for substance applies the guide to all of it, and no wider."
   4. "A rewrite is for substance when it changes what the text requires, permits or describes."
   5. "Text that a test or machine contract quotes exactly keeps its wording." Pinned seed tests therefore still pass after such a rewrite.
5. In "Basis and limits", "with selected precision practices informed by" becomes "with selected precision and sentence-structure practices informed by". The rest of that paragraph stays unchanged. The guide still declines the STE dictionary and the STE word limits, so the rest of the paragraph stays true.
6. No other sentence, heading or table row of the guide changes, except its `Last verified` date. The sentence "This guide adds no review lane, council, approval gate or prose linter." stays unchanged and stays true: no script, sensor, hook or test inspects prose quality.
7. Each added sentence follows the rules it adds:
   1. It carries one action or one point.
   2. If it passes the length prompt, it carries no inline series of three or more parallel cases.
   3. It stacks no four or more nouns and modifiers before a head noun. The quoted bad example in Requirement 1.3 is an example of the defect, not an instance of it.
   4. Word counts are planning information, never a pass or fail test. Planning counted, by whitespace, 9, 23, 6 and 15 words for Requirement 3; 22 for Requirement 2; 13, 14, 16, 8, 14 and 19 for Requirement 1; 12, 9, 21, 15 and 12 for Requirement 4. The 23-word sentence passes the instruction prompt and carries one action, so it stands.
8. Three pointer sentences send writers to the guide where they write. Each is new review surface:
   1. In `docs/prompts/package-wavefoundry.prompt.md` step 6, directly after the sentence that begins "Bullets are git-commit-message-style", add "Terse bullets still follow `.wavefoundry/framework/docs/writing-guide.md`: each sentence names its actor and result and carries one point." The step's style and the guide agree, so the step keeps both. This prompt is local to this repository; no seed carries the changelog step.
   2. In `docs/prompts/pause-wave.prompt.md` step 2, directly before "Use these labeled sections:", add "Write each section in complete sentences, as `.wavefoundry/framework/docs/writing-guide.md` directs."
   3. In seed 100's **pause-wave** bullet (`.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`), directly after "Include one two-wave example using project vocabulary.", add "Tell the writer to apply `.wavefoundry/framework/docs/writing-guide.md` to the handoff sections, in complete sentences." Seed 100 is the canonical source for target pause-wave prompts.
9. The root `CHANGELOG.md` gains a `### Changed` subsection under the existing `## [Unreleased]` heading, after its `### Added` subsection, with one bullet ending "Wave 241c3 / 240wz.". Recommended text: "The writing guide adds sentence-structure checks. A long sentence carries one action or point, and a checklist item holds one result. Writers name the head noun first and write complete sentences in records. Reviewers apply the same reader tasks to changelog entries and the handoff. Pause wave points writers to the guide for the handoff. The guide adds no linter or sentence limit. Wave 241c3 / 240wz."

## Scope

**Problem statement:** the guide has no test for an overloaded sentence, a checklist item with several actions, a noun stack or a fragment in a record, and the measured writing still shows each.

**In scope:**

- `.wavefoundry/framework/docs/writing-guide.md`, per Requirements 1 to 6.
- The three pointer sentences in Requirement 8.
- One CHANGELOG bullet.
- The wave's `evidence/` folder: the measurement scripts, `check_sentences.py` and a README with the re-run steps and the script for each figure. It holds scripts only, no data output.

**Copies and quotations checked:**

- The guide has one copy, at `.wavefoundry/framework/docs/writing-guide.md`. No rendered or install-template copy exists under `docs/` or `.wavefoundry/framework/install/` (`find . -name 'writing-guide*'`).
- `AGENTS.md`, `docs/prompts/index.md`, `docs/agents/specialists/technical-writer.md`, seeds 020, 050, 100, 160, 171, 179, 209 and 233, and the `envision-project` and `plan-arc` prompts reference the guide by path only. A fixed-string search for each touched guide paragraph found no quotation outside the guide and historical wave records.
- Pointer carriers: the package prompt is local-only. The pause-wave prompt's canonical source is seed 100's **pause-wave** bullet; no install template renders it.

**Tests that read the touched text:**

- `.wavefoundry/framework/scripts/tests/test_writing_guide_delivery.py` packs and extracts the guide and compares its bytes with the repository copy. It also requires each backticked `writing-guide` reference in its listed files to be exactly the guide path. It reads no guide text, so it passes unchanged.
- `.wavefoundry/framework/scripts/tests/test_rust_practices_baseline.py` names the delivery test in a docstring only.
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py` (`test_the_release_checklist_lists_advisory_sensors`) pins other sentences of the package prompt's step 6. `tests/test_memory_records.py` pins `- **pause-wave**:` in seed 100 and `memory_add(status='candidate'` in the pause-wave prompt. `tests/test_render_agent_surfaces.py` and `tests/test_work_area_wording.py` read the pause-wave prompt for other text. Each pinned string survives an appended sentence.
- A fixed-string search of `.wavefoundry/framework/scripts/` for the touched sentences of the three pointer carriers ("terse, operator-impact-focused", "standardized structure beyond", "Include one two-wave example", "close-time distillation checkpoint decides") found no other pin.

**Out of scope, each a DECLINE:**

| Candidate | Verdict | Reason |
| --- | --- | --- |
| Controlled dictionary of approved words | DECLINE | It fights necessary technical vocabulary, needs a checker to mean anything, and term consistency is already good without it. |
| Hard limits of 20 and 25 words | DECLINE | Medians are 12 to 16 words. A count cannot separate a clear long sentence from an overloaded one, and a limit invites the linter the operator rejected. Requirement 3 keeps the useful part. |
| Paragraph limit of six sentences | DECLINE | Only 1.3% of spec blocks and 9% of new seed blocks pass six sentences, and the guide uses paragraphs for connected reasoning. |
| Active voice only in procedures | DECLINE | The preference already works (specs 17.8% to 11.1% passive, wave.md 21.8% to 7.5%). A ban would forbid the result statements the guide permits. |
| Imperative form for instructions | DECLINE | Practice already does it: 151 imperative sentences in 631 new seed sentences. |
| Condition before the instruction | DECLINE | New seed prose puts the condition first 37 times against 9 trailing clauses, which read clearly. "Close to the statement it qualifies" is enough. |
| Warnings and cautions placed first | DECLINE | The "Usable" section's first sentence covers it, and the review found no prohibition that arrived too late. |
| No -ing forms | DECLINE | It targets translation ambiguity; no sampled passage was unclear because of one, and project terms use them (indexing, chunking). |
| Verb, not noun, for actions as a separate rule | DECLINE | "Use familiar words and direct verbs" already states it. |
| Notes carry information, not instructions | DECLINE | The review found one instance (passage 8). |
| Contractions, punctuation, single spelling | DECLINE | No effect on meaning for these readers. |
| A project glossary as a controlled vocabulary | DECLINE | The guide already requires defining a term the reader cannot look up, and the term counts show no drift. |
| A prose linter, sensor, gate, review lane or readability score | DECLINE | The operator rejected it on 2026-11-21, and the guide says it adds none. |
| A repository test that pins the new sentences | DECLINE | Coordinator decision 2026-11-21. A pinned-prose test turns every later wording repair into a test edit. The reviewer presence check in AC-2 gives the known-bad oracle without that cost. |
| The third reviewer practice in the report (word counts are a reason to look, never a finding) as its own sentence | DECLINE | Requirement 3.1 and the existing "not a readability score" sentence already state it. |
| A pre-release writer or reader replay on control and candidate guides | DECLINE | Wave 23041 ran a reader pair and tied. A one-time replay on five passages cannot show whether writers change across real work, which the post-release measure answers. |
| The article-free handoff rate as an intent measure | DECLINE | A readiness sample found 7 of 30 hits were fragments, so the figure does not measure fragments. |
| "That a reader marks complete" in the item rule | DECLINE | It pushes the sentence past the length prompt with an inline three-case series. The three named item kinds already are items a reader marks complete. |
| A separate paragraph with a bold lead-in for the record rules | DECLINE | The rules qualify the word-choice sentences they follow, and the operator favors the smallest change. |
| Guide pointers in the close-wave and close-spec handoff steps | DECLINE | The report's handoff gap is in the text a pause writes. Close rewrites the handoff to an idle format with little prose. |
| Rewriting existing records, released changelog sections or seed blocks | DECLINE | The guide applies to documents naturally touched later; it does not authorize rewriting history. Requirement 4.3 bounds a rewrite to the text an edit already changes. |

**Platform behavior:** documentation, plus measurement scripts that run only by hand. The guide and prompts are the same on Windows, macOS, Linux and WSL2. The README runs the scripts with `python3 -X utf8 -I`, so native Windows reads repository text as UTF-8. Delivery uses the existing pack and upgrade path that `test_writing_guide_delivery.py` checks.

## Acceptance Criteria

- [x] AC-1: A docs-contract reviewer diffs the revised guide against the frozen control copy (`.wavefoundry/work/241c3/planning/control-writing-guide.md`, the guide's bytes on 2026-11-21). Only the edits in Requirements 1 to 5 and the `Last verified` date differ, and "This guide adds no review lane, council, approval gate or prose linter." is unchanged.
- [x] AC-2: From the repository root, `check_sentences.py` from the wave's `evidence/` folder, run with `python3 -X utf8 -I` on `.wavefoundry/framework/docs/writing-guide.md --pointers`, exits 0 and prints `22/22 present`. Known-bad: on a copy with any one frozen sentence deleted, it exits 1 and prints one `MISSING` line naming that sentence. Planning ran it against the candidate guide at `.wavefoundry/work/241c3/planning/candidate-writing-guide.md`: 19/19 without `--pointers`, and each of the 19 deletions detected. In a scratch tree, `--pointers` reported 19/22 before the pointer sentences and 22/22 after.
- [x] AC-3: The docs-contract reviewer confirms each added sentence, including the three pointers and the CHANGELOG bullet, meets Requirement 7.1 to 7.3. The reviewer records word counts as information; a count alone never fails a sentence. Known-bad: the report's original "If it carries more, split it, and move three or more parallel cases into a list." carries two actions and fails this check.
- [x] AC-4: The diff of `git status --porcelain` taken before the first edit and after the last edit shows no new or changed file under `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/scan/`. The only seed in it is seed 100.
- [x] AC-5: `python3 .wavefoundry/framework/scripts/run_tests.py` writes an `ok` receipt; `test_writing_guide_delivery.py` runs within it.
- [x] AC-6: `wf_validate_docs` passes.
- [x] AC-7: `CHANGELOG.md` has a `### Changed` subsection under `## [Unreleased]` with one bullet ending "Wave 241c3 / 240wz.".
- [x] AC-8 (intent baseline, not intent proof): A listing of the wave's `evidence/` folder shows `measure.py`, its helpers, `check_sentences.py` and a README. The README names the script and row for each baseline, the run order and the re-run trigger.
- [x] AC-9 (intent baseline, not intent proof): `memory_search` for "240wz re-run" returns a memory record that points to the evidence README and states the Product Intent decision rule, so a later session can read the effect.

## Tasks

- [x] Save `git status --porcelain` before the first edit, for AC-4.
- [x] Open `framework_edit_allowed` with `wf_open_gate(gate="framework_edit_allowed")`.
- [x] Apply Requirements 1 to 6 to `.wavefoundry/framework/docs/writing-guide.md` and set its `Last verified` date.
- [x] Open `seed_edit_allowed` with `wf_open_gate(gate="seed_edit_allowed")`.
- [x] Add the seed 100 pointer sentence from Requirement 8.3.
- [x] Close `seed_edit_allowed` with `wf_close_gate(gate="seed_edit_allowed")`.
- [x] Add the two prompt pointer sentences from Requirements 8.1 and 8.2.
- [x] Close `framework_edit_allowed` with `wf_close_gate(gate="framework_edit_allowed")`.
- [x] Add the CHANGELOG bullet under `## [Unreleased]` / `### Changed`.
- [x] Run `check_sentences.py --pointers` against the revised guide, and record its output in the Progress Log.
- [x] Run `check_sentences.py` against one known-bad copy, and record its output in the Progress Log.
- [x] Record the AC-3 word counts in the Progress Log.
- [x] Record the AC-9 memory candidate with `memory_add`; `memory_validate` then promotes it.
- [x] Run `wf_validate_docs`.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last, after every framework edit.
- [x] Save `git status --porcelain` after the last edit and compare it for AC-4.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guide revision | implementer | readiness | One writer; the frozen sentences come from Requirements 1 to 5 |
| Pointer sentences | implementer | guide revision | Seed 100 under `seed_edit_allowed`; two local prompts |
| CHANGELOG and records | implementer | pointer sentences | Bullet, Progress Log, memory record |
| Presence and sentence checks | docs-contract-reviewer | CHANGELOG and records | AC-1 to AC-3 against the control copy |
| Verification | implementer | CHANGELOG and records | Full test run last |

## Serialization Points

- `.wavefoundry/framework/docs/writing-guide.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `docs/prompts/package-wavefoundry.prompt.md`
- `docs/prompts/pause-wave.prompt.md`

The same writer makes the root `CHANGELOG.md` edit.

## Affected Architecture Docs

N/A: the guide's ownership, delivery route and references are unchanged. This change adds content to one shared guidance document and three pointer sentences.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The change must add only the accepted text and keep the no-linter statement true |
| AC-2 | required | The known-bad oracle: removing any new sentence fails the check |
| AC-3 | required | The guide must obey the rules it adds, judged by its own test, not by a count |
| AC-4 | required | No script, sensor or test is added, so no prose check exists |
| AC-5 | required | Delivery and the suite must keep working |
| AC-6 | required | Docs validation must pass |
| AC-7 | required | Project release-note policy |
| AC-8 | important | Keeps the post-release measure runnable; it does not prove the effect |
| AC-9 | important | Lets a later session find the decision rule; it does not prove the effect |

## Progress Log

- 2026-11-21: The reality checker found that the spec measure included a supporting report. Cycle 4 changed the primary and secondary spec measures to read the wave record’s admitted changes. At review time the corrected 241c3 sample contained 182 spec sentences and 8.2% exceeded 25 words. Including the report had produced 277 and 11.2%. Independent controls confirmed that 699 sentences defer the decision and that 700 sentences at 13.7% retain the guidance. See `D2-240wz-spec-corpus-includes-supporting-docs`.

- 2026-11-21: The full default suite passed 13,194 tests across 253 files. All five tests in test_writing_guide_delivery.py passed. The release qualification report and close receipt correspond to this framework tree.

- 2026-11-21: The secondary measurement commands failed on a sparse sample of three waves. The six wave-only evidence scripts now limit each sample to the available observations and distinguish a missing rate from a measured zero. For runs with a custom `WF_BASE`, the output identifies the selected revision. The adoption baseline keeps its original labels. The primary measure still returns 18.0% for 2,062 historical spec sentences. The ledger records the original failure and repair under `D1-240wz-secondary-small-samples`.

- 2026-11-21: Code review found a small-sample failure in the optional examples. The original secondary script raised ValueError with three real waves and a current Git baseline. The repaired scripts bound each sample to the examples available and report when no observations exist. Six scripts passed on the 1,813-sentence example and on a fixture with zero secondary observations. The [original baseline review](source-review.md) preserves the cited assessment after work cleanup.

- 2026-11-21: The docs-contract reviewer reconstructed the guide from the control, checked each of the 22 deletion controls and reviewed the complete sentences. Word counts for Requirements 1–5 were 13/14/16/8/14/19, 22, 9/23/6/15/16, 12/9/21/15/12 and 24. The package, pause and seed pointers had 16/9/13 words. The changelog sentences had 6/8/6/6/6/10/9 words plus the wave reference. The 16-word negative example combines splitting and making a list. These counts informed the review.

- 2026-11-21: The active memory `240wz-rerun-writing-guide` points to the evidence README. The search “240wz re-run” returned it. The memory tool routes manually authored candidates to `memory_reconcile`, which promoted it after inspection. `memory_validate` accepts candidates generated from a source event.

- 2026-11-21: The presence check returned 22/22 and exited 0. Deleting “If it carries more, split it.” returned one MISSING line for that sentence, 21/22 and exit 1. I compared the before and after porcelain listings and all 655 paths under scripts, scan and seeds. Only seed 100 changed there.

- 2026-11-21: Readback: The guide gives an author a test for an overloaded sentence and a reviewer a test for an independently verifiable task. It also covers noun stacks and complete records. I will update the guide, seed 100, the two local prompts and the changelog. The effect on later specs has a separate post-release measurement.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-21 | Planned from the STE review and the operator's acceptance of ADOPT 1 to 4 and two reviewer practices. The report's scripts were in a session scratchpad, not the eval folder. Planning copied them and `check_sentences.py` into the wave's `evidence/` folder with a README. In that copy, `measure.py` reads the repository root from `WF_REPO` or `git rev-parse` instead of a fixed local path. | `.wavefoundry/work/241c3/planning/` (control-writing-guide.md, candidate-writing-guide.md); the wave's `evidence/` folder |
| 2026-11-21 | Readiness repair, cycle 1 (implementer, context `241c3-implementer-repair-1`), for R1-240wz-word-count-hard-limit, R1-240wz-item-exception-undecidable, R1-240wz-list-rule-unscoped and R1-240wz-measure-no-decision-rule, with reality-checker items RC-1 to RC-4. Requirement 7 and AC-3 now apply the one-action-or-one-point test; the counts are information only. The report's ADOPT 1 sentence is restored; "long" in the next sentence became "extended". The item exception now names one command or one observation, and AC-4 and AC-6 were split into AC-4 to AC-9. The list rule applies only to a sentence past the length prompt. Product Intent has one primary measure, a threshold, the operator as reader, a time and an action. The fragment measure is dropped. Requirement 4.3 is bounded to the author's own rewrite. Requirement 8 adds three pointer sentences (coordinator decision RC-3), with seed 100 under `seed_edit_allowed`. Evidence scripts: `WF_BASE`, `WF_POST_WAVES` and `WF_POST_VERSIONS` settings; `extra.py` and `extra2.py` read the same wave list; `measure.py` exits 1 when it finds no repository or every corpus is empty. The earlier "smoke run exited 0" claim showed nothing, because a run with no repository also exited 0. Re-run with `WF_REPO` set: exit 0, `specs POST` 2,062 sentences and 18.0% over 25; `spec tasks POST` 36.4%. Without `WF_REPO`, outside the repository: exit 1. Candidate guide 2,032 words (control 1,802). `check_sentences.py`: 19/19 on the candidate, 1/19 on the control, 19 of 19 deletions detected; `--pointers` in a scratch tree 19/22 before and 22/22 after the pointers. | `.wavefoundry/work/241c3/review/` notes; scratch runs in the session scratchpad |
| 2026-11-21 | Moved the task that closes the framework gate below the two prompt edits. An independent reviewer replayed the five planned edits using the rendered pre-edit hook. All five passed. Restoring the old order blocked the seed edit and both prompt edits. | Typed finding `R2-240wz-gate-order-blocks-pointer-edits`, cycle 2 reverification |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-21 | Add the accepted sentences to the existing paragraphs they qualify, and keep the report's ADOPT 1 wording. | Each rule sits next to the existing rule it sharpens. The 23-word ADOPT 1 sentence carries one action, so it passes its own check and shows the prompt is not a limit. | A new "Sentence structure" subsection: weakness, it splits the length rule from "There is no universal word or sentence limit". Splitting ADOPT 1 to fit 20 words: weakness, it treats the count as the defect, which readiness review rejected. |
| 2026-11-21 | Coordinator decision 2026-11-21: use a reviewer presence check as the known-bad oracle, not a repository test that pins prose, consistent with the operator's no-linter rule. | It fails when any sentence is removed and adds no test that pins prose. | A unittest that pins each sentence: weakness, every later wording repair needs a test edit, and it sits close to the rejected linter. No oracle: weakness, a no-op delivery could pass. |
| 2026-11-21 | Coordinator decision 2026-11-21: keep the measurement scripts and the presence check in the wave's `evidence/` folder. | Close removes the work folder, and the post-release re-run needs the scripts. | Keep them in the work folder: weakness, close deletes them. Commit their data output: weakness, it adds dumps nobody reads. |
| 2026-11-21 | Coordinator decision 2026-11-21 (RC-3): add guide pointers to the package changelog step and the Pause wave handoff step. | The report found that the changelog and the handoff did not follow rules that exist, and no step points writers to the guide when they write them. | No pointer: weakness, the practice gap gets no new lever. Pointers in every lifecycle prompt: weakness, wider than the measured gap. |
| 2026-11-21 | Decision rule: spec sentences over 25 words, a fall of at least 4 points, read by the operator after three post-release waves. | It is the only figure with enough sentences; at 700 sentences the noise band is about 3.3 points. | Four descriptive figures with no threshold: weakness, no result could lead to a decision. Task-item rate: weakness, n of 118 gives a noise band of about 12 points. |
| 2026-11-21 | Change only "precision practices" in the basis paragraph. | The new rules are structural, so "precision" alone understates what comes from ASD-STE100. The dictionary and word limits stay declined, so the rest of the paragraph stays true. | Leave it unchanged: weakness, it misdescribes the new rules' source. Add a sentence about STE word limits: weakness, it repeats "There is no universal word or sentence limit". |

## Risks

| Risk | Mitigation |
| --- | --- |
| A reviewer treats the 20 and 25 word prompts as a limit and files counts as findings | Requirement 3.1 says the length is a prompt, the 23-word ADOPT 1 sentence shows a long sentence can pass, and AC-3 forbids failing a sentence on its count |
| The seed 100 edit rotates receipts or drifts a rendered surface | The pointer is appended to the bullet, no test pins the touched sentences, and `run_tests.py` runs last |
| The post-release specs differ in topic from the baseline specs | Product Intent requires a 4-point fall, larger than the noise band, and states that the figures overstate precision |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
