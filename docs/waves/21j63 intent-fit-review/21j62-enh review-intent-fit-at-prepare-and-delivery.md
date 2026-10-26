# Review Intent Fit at Prepare and Delivery

Change ID: `21j62-enh review-intent-fit-at-prepare-and-delivery`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-24
Wave: 21j63 intent-fit-review

## Rationale

Close asks for an `Intent outcome:` paragraph (seed 190 line 70), but nothing before close judges whether the plan or the delivered work meets the intent. Prepare and Review wave carry one generic preamble sentence (`prepare-wave.prompt.md:15`, `review-wave.prompt.md:15`, seed 209 line 11) that no council seat, lane or output field owns: seeds 215 and 237 never mention Product Intent, the wave Objective or a measure of success. The paragraph is written after `council-delivery` approves, so no reviewer sees the claim that the intent was met. Wave 21ilj shows the shape: its readiness record has no intent-fit statement and its `Intent outcome:` was written after delivery approval. The operator wants plans and implementation judged against the actual intent during Prepare and Review.

## Product Intent

Operators get a reviewer's judgement of intent fit twice before close: at readiness, whether meeting the Requirements and ACs would establish each change's Product Intent and the wave Objective, and whether its measure of success can be read; at delivery, whether the delivered work achieved it, judged against an `Intent outcome:` paragraph drafted before `council-delivery`. Close behaviour is unchanged, and no new gate or schema is added.

## Requirements

1. The council-chair's output (seed 215 `## Output Shape`) gains an `intent_fit` item:
   - at readiness, for each admitted change and the wave Objective: whether meeting its Requirements and ACs would establish its Product Intent (`establishes`, `partially` or `does not`), the measure of success it cites and whether that can be read, and why;
   - at delivery: whether the drafted `Intent outcome:` paragraph is supported by the delivery evidence, confirming or correcting its achieved, partial or not established statement.
   A gap that would leave the intent unestablished goes through seed 209's finding path like any other finding. When the delivery council corrects the paragraph, the coordinator revises it before close; the close-summary composer carries the last one.
2. The Prepare wave prompt (lifecycle template and this repo's rendered copy) adds the council's intent-fit statement to the readiness verdict conditions.
3. The Review wave prompt (lifecycle template and rendered copy) adds a step before the council delivery pass: the coordinator drafts one `Intent outcome:` paragraph, prefixed `YYYY-MM-DD: `, in the existing exact `## Review Checkpoints` section (never a second such section, because the composer reads the first) from the delivery evidence, and the council delivery pass judges it.
4. `wf_create_wave` scaffolds an empty exact `## Review Checkpoints` section as the last section, after `## Dependencies`, so the heading the close-summary composer reads exists from creation. (A position before `## Finding Synthesis` breaks three lifecycle tests that cut the record at that heading.)
5. In the files this change edits, backticked references to the `## Review checkpoints` heading use the exact `## Review Checkpoints` spelling.
6. The upgrade baseline in seed 160 (the seed 209 `prepare-wave`/`review-wave` bullet) and the intent summary in seed 100 carry the readiness and delivery `intent_fit` statement and the pre-delivery `Intent outcome:` draft, so upgraded targets receive the guidance (missing-only rendering never updates authored prompts).
7. The close prompt, seed 190, the close-summary composer and its exact-heading match are unchanged.

## Scope

**Problem statement:** intent fit is judged only at close, by the coordinator, after every approval.

**In scope:**

- Seed 215 Responsibilities and Output Shape; the seed 160 upgrade baseline bullet; the seed 100 intent summary sentence.
- `install/lifecycle-prompts/prepare-wave.prompt.md`, `install/lifecycle-prompts/review-wave.prompt.md` and their rendered copies under `docs/prompts/`.
- The `wf_create_wave` scaffold text in `server_impl.py` and its tests.
- A CHANGELOG bullet.

**Out of scope:**

- Close-wave prompt and seed 190 text, and the composer (Requirement 7).
- Case-insensitive heading matching: the composer's exact match is a recorded 2124l decision that keeps legacy summaries byte-identical.
- A sensor or gate that checks for the paragraph or the verdict.
- Lowercase `Review checkpoints` mentions in files this change does not otherwise edit.
- Existing wave records.

## Acceptance Criteria

- [x] AC-1: Seed 215 names `intent_fit` in its Output Shape with the readiness and delivery content of Requirement 1; a test reading the seed fails when the item is absent.
- [x] AC-2: Both Prepare wave prompts list the intent-fit statement among the readiness verdict conditions, both Review wave prompts carry the step that drafts `Intent outcome:` in the existing exact `## Review Checkpoints` before the council delivery pass, and the seed 160 baseline names both; a test reading these files fails when any is missing.
- [x] AC-3: A wave created by `wf_create_wave` ends with an exact `## Review Checkpoints` heading, the scaffold is lint-clean, and the close-summary composer run on a scaffolded record with an `Intent outcome:` paragraph added under that heading carries it into Wave Summary; the test fails with the heading removed from the scaffold.
- [x] AC-4: Intent fit is exercised on this wave itself: the typed `council-readiness` approval's `observed` string and the `## Review Checkpoints` summary state `intent_fit` for this change, and its dated `Intent outcome:` is drafted before `council-delivery` and judged in that approval's evidence.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add `intent_fit` to seed 215 Responsibilities and Output Shape, and update seeds 160 and 100 (seed gate).
- [x] Edit both Prepare wave and both Review wave prompts (framework gate).
- [x] Add `## Review Checkpoints` to the `wf_create_wave` scaffold and extend its tests.
- [x] Add the guidance tests for AC-1 and AC-2.
- [x] Add a CHANGELOG bullet under 1.37.0.
- [x] Run the touched suites, then the full suite.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| intent-fit | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/seeds/215-council-chair.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`, `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md`
- `docs/prompts/prepare-wave.prompt.md`, `docs/prompts/review-wave.prompt.md`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`

## Platform Behavior

Unchanged on Windows, macOS, Linux and WSL2: the change is prompt prose and one scaffold string written through the existing record writer, with no path, process or encoding change.

## Affected Architecture Docs

N/A: review guidance and one scaffold heading; no module boundary, data flow or verification seam changes.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The readiness and delivery verdict owner is the core of the change |
| AC-2 | required  | The prompts are where agents run Prepare and Review |
| AC-3 | important | Makes the composer's heading exist without hand authoring |
| AC-4 | required  | The only direct evidence that reviewers act on the guidance |
| AC-5 | required  | Change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-24 | Planned | Operator: "we should add this during prepare and review. The plans and implementation need to match the actual intent." Then: "prepare, review, and implement this before we release" |
| 2026-10-24 | Readiness repair (one bounded pass): code-reviewer F1/F2, docs-contract F1-F3 and council notes 1-3 folded in as Requirements 3-6, AC-2/3/4 wording and seeds 160/100 scope. No finding was blocking. | readiness reviews |
| 2026-10-24 | Implemented. Seed 215 Responsibilities + Output Shape `intent_fit`; seeds 160 (seed 209 prepare/review baseline bullet) and 100 (intent summary); Prepare/Review lifecycle templates and rendered copies; backticked `## Review checkpoints` references in edited files now exact. Discovered during implementation and kept in Requirement 1/6 scope: this repo's rendered copies of the same carriers, `docs/agents/specialists/council-chair.md` (Output Shape) and `docs/prompts/upgrade-wavefoundry.prompt.md` (same baseline bullet), updated identically and covered by the new carrier test. Scaffold: `## Review Checkpoints` appended after `## Dependencies` (last scaffold section; the context-efficiency projection may append its own section later). Tests: `IntentFitCarrierTests` (render suite, 193 OK) and `test_scaffold_carries_review_checkpoints_for_the_intent_composer` (lifecycle, 655 OK). Known-bad in a scratch copy: scaffold heading removed fails the scaffold test (`0 != 1`); the review-wave clause removed fails the carrier test; both pass on clean code. Gapfill: prompt and seed text edited by short scripts (bulk-mechanical string insertion), and the mutation copy run by shell. | implementation |
| 2026-10-24 | Delivery review. code-reviewer APPROVE (lifecycle 655 OK, render 193 OK, scratch mutants killed, `create_wave` is the only wave-record writer; advisory: lifecycle fixtures that append a second checkpoints heading). docs-contract APPROVE (`wf_validate_docs` clean). Delivery council PASS, `intent_fit` confirmed the drafted `partial` Intent outcome. Editorial repairs inline from council notes: L1 added the seed 215 Responsibilities bullet to `docs/agents/specialists/council-chair.md`; L2 added "after release" to both Prepare prompts' measure clause. L3 (`docs/contributing/review-and-evals.md` has no intent_fit wording) is self-hosted drift outside this change, left as a follow-up. | delivery review |
| 2026-10-24 | L3 folded in by operator direction ("Let's add docs/contributing/review-and-evals.md to this wave"). Added an `intent_fit` paragraph after the existing intent paragraph (readiness verdict values, measure of success read after release, dated `Intent outcome:` draft in the one exact `## Review Checkpoints` section, delivery confirms or corrects) and corrected five backticked `## Review checkpoints` references to the exact heading. Docs-only self-hosted surface outside `.wavefoundry/framework/`; the framework test receipt is unaffected. | `wf_validate_docs` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-24 | Make intent fit a named council-chair output item at both phases, and draft `Intent outcome:` before `council-delivery` | The chair's Output Shape is the checklist every council synthesis follows and approvals cite, so a named item gets an answer each wave; drafting before delivery puts the close claim in front of a reviewer | A per-seat duty in seed 237 (five answers per wave, more cost, same judgement); a lint sensor requiring the paragraph before `council-delivery` (a new gate the operator did not ask for, and it checks presence, not fit); strengthen only the generic seed 209 sentence (the status quo shows it is not acted on) |
| 2026-10-24 | Mechanism efficacy | Replay 21ilj: readiness would have had to state `intent_fit: establishes` with the measure (bootstrap installs 0.12.22, hash-verified), and the delivery council would have judged the drafted paragraph. It advises rather than controls: the council is the actor, and the item's absence from a synthesis is visible to the operator. It can be answered perfunctorily; AC-4 checks one real wave. Success after release: the next waves' records show readiness `intent_fit` lines and an `Intent outcome:` dated before `council-delivery` | |
| 2026-10-24 | Keep the composer's exact heading match; scaffold the heading instead | The exact match is a recorded 2124l decision for byte-identical legacy summaries; a scaffolded heading fixes new waves without changing old output | Case-insensitive match |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The intent-fit line becomes boilerplate | Requirement 1 asks for the measure and a reason; AC-4 exercises it on this wave |
| A scaffold test compares the whole scaffold text | Extend that test with the new heading |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
