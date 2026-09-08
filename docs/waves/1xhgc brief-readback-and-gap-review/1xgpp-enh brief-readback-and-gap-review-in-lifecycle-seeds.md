# A Brief Before Planning, a Readback Before Editing, a Gap Review Before Questions

Change ID: `1xgpp-enh brief-readback-and-gap-review-in-lifecycle-seeds`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-07
Wave: 1xhgc brief-readback-and-gap-review

## Rationale

Goal: catch consequential misunderstandings before drafting or implementation.
Consumer: the operator and the agents planning, implementing, and reviewing the work.
Approach: reuse established context, clarify material gaps, restate the task, then produce and evaluate the result.
Constraints: prompt-focused; use existing documents and review workflows; add no gate or mandatory confirmation.
Deliverable: concise lifecycle guidance, safe destination upgrade instructions, and focused verification.
Avoid: repeated questions, assumed product intent, and ceremonial checklists for clear tasks.
Good result: an ambiguous requirement is resolved before dependent work, while an already-clear request proceeds without an unnecessary interview.

The operator supplied the full text of [The PyCoach's briefing-loop article](https://medium.com/artificial-corner/how-to-get-10x-better-ai-answers-without-writing-better-prompts-7f1ed8e86edc). Its relevant sequence is to reuse context, ask only questions that change the output, restate the brief, produce the first result, and optionally compare that result against the brief. The article explicitly exempts simple tasks and recommends question budgets rather than exhaustive interviews. This change adapts those principles to the existing wave lifecycle; it makes no quantitative improvement claim.

Prior findings RED-DEL-9 and RED-DEL-10 in wave `1x5tr` motivate checking the implementer's interpretation before editing. A readback may expose a narrowed interpretation, but its presence alone cannot prove understanding or prevent missed code paths. Behavioral examples and existing independent reviews remain necessary.

## Requirements

1. Before the Divergent Pre-Plan, `Plan feature` SHALL reuse the operator's request, prior answers, and relevant project context to establish a brief. Cover goal, consumer/audience, intended angle or approach, constraints, deliverable/format, exclusions, and observable success where relevant. Record it in existing Rationale and summarize it to the operator before dependent drafting. Clear tasks may use one concise sentence; no mandatory field-filling interview or confirmation is added.
2. Ask the fewest questions whose answers materially change the result. Use at most three for small tasks and five for complex tasks per briefing pass, as ceilings rather than quotas; do not automatically restart questioning to evade the budget. Reuse known answers. Explicit assumptions are allowed for reversible implementation choices within established scope, but unresolved goal, scope, acceptance, or authorization decisions SHALL remain unresolved until answered. Continue independent work while waiting; absence of a reply is neither an answer nor approval.
3. Before the first implementation edit of each change, `Implement wave` and `Implement feature` SHALL record a concise `Readback:` in the existing Progress Log and surface its substance to the operator. Explain intended behavior, relevant ACs, the important scope boundary, and expected affected files; include one before/after example for nontrivial behavior changes. Correct the agent's own mistaken reading directly. Route an actual contradictory requirement or missing consequential decision back to planning using existing escalation rules; do not classify every readback correction as Level 3 or require a second approval. Refresh only materially changed understanding after scope changes or handoff.
4. Optional `Review plan` SHALL begin by comparing the drafted Requirements, ACs, and Scope against the brief in Rationale, the operator's request, and relevant established context. Consider strengths, vagueness, omissions, removable content, and consumer usefulness; report only meaningful observations and feed unresolved discrepancies into the existing decision-branch walk. Amend its section restrictions to allow reading the brief as reference without reopening all of Rationale or resolved decisions. Preserve current-wave fallback and existing no-new-scope rules; new ideas remain proposals, not inferred authorization.
5. Guidance SHALL stay concise and proportional, reuse existing Rationale/Progress Log/output, and add no new document, template section, lint gate, approval, or MCP field. Preserve the existing no-em-dash style preference. Replace the arbitrary eight-line limit with a review for duplication and unnecessary mandatory output.
6. Canonical seeds/baseline SHALL be edited first. Reconcile the four existing project prompt counterparts by bounded authored-prose merges, preserving metadata, unrelated customizations, and renderer-owned regions; render only the regions the renderer owns. Upgrade guidance SHALL map each changed source to its existing destination, retain the pre-apply change evidence, and require same-run reconciliation with refusal on ambiguous/conflicting local clauses. Do not rely on missing-only baseline rendering to update existing prompts.
7. Source-only tests SHALL require nonempty canonical instruction blocks, pin their required semantics and corresponding project blocks, and reject independent removal or reversal in either copy. Equality alone is insufficient. Exercise fresh baseline creation and an existing customized destination to demonstrate the renderer's preservation boundary; use a bounded manual reconciliation rehearsal for authored content without inventing a runtime migration.
8. Delivery evidence SHALL include a small behavioral rehearsal using the actual revised prompts: an already-clear task, a reversible low-impact ambiguity, a missing consequential decision, a draft that conflicts with its brief, and an agent readback mistaken about an otherwise-clear requirement. Record request/context, observed response, expected action, and pass/fail in this change's existing Progress Log. Distinguish observed agent behavior from static text tests and do not claim general effectiveness from this finite sample.
9. This change SHALL use its own brief and implementation readback. Preserve established preferences in existing project context; do not create another permanent brief file or repeat questions already answered.

## Design

Edit seeds `170`, `175`, and `180`, plus the implement-wave lifecycle baseline. Add a conditional briefing step, a behavioral readback guardrail, and a comparison against the brief at the start of optional plan review. Update the existing review-plan section restrictions in the same edit so they do not prohibit consulting Rationale.

The four destination prompts are `plan-feature`, `review-plan`, `implement-feature`, and `implement-wave`. They are not all whole-file renderer outputs. `render_agent_surfaces.reconcile_lifecycle_prompt_baselines` explicitly skips existing files. Therefore synchronize only the new authored clauses after canonical edits, preserve managed markers, and run the renderer for managed regions afterward.

Extend seed `160` and its self-hosted upgrade prompt with source-to-destination mappings for seeds `170`, `175`, `180`, and the extracted implement-wave baseline. Reuse the existing retained pre-apply diff and merge-safe reconciliation rules. An existing customized destination must receive an unambiguous bounded merge or a visible conflict; neither silent omission nor wholesale replacement is acceptable.

Extend the existing surface tests with nonempty block checks, semantic negative controls, and parity checks for all four counterparts and both upgrade instructions. Rehearse fresh/existing destination behavior in temporary fixtures. Separately execute the five behavioral scenarios and summarize observations in the existing change record. No new runtime renderer, server, or lint behavior is planned.

## Prompt-Surface Maintenance Plan

Intended edits: seeds `160`, `170`, `175`, `180`; `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md`; their five named `docs/prompts/` counterparts; `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`; and the existing Unreleased changelog. The change and wave records hold all planning/review evidence.

Protected: `AGENTS.md`, `CLAUDE.md`, hook configuration, `docs/prompts/index.md`, renderer/server/lint implementation, and all other seeds. Open and close `seed_edit_allowed` for seeds and `framework_edit_allowed` for baseline/tests during readied implementation.

One implementer owns the edits; code, QA, docs-contract, and release reviewers inspect them independently through the existing review workflow. This plan revision edits only the admitted change and wave records.

## Scope

**Problem statement:** Missing context or a narrowed interpretation can survive into implementation; recording an assumption or repeating an AC does not resolve that uncertainty.

**In scope:** proportional briefing, reuse of known context, bounded material questions, behavior-focused readback, optional draft-versus-brief gap review, all four prompt counterparts, safe upgrade reconciliation, source-only contract tests, and five behavioral rehearsals.

**Out of scope:** Guru changes, new gates or schemas, mandatory operator approval of every brief, new Markdown artifacts, automated runtime prompt migrations, and new readiness/delivery review stages. Existing delivery review continues to assess the implemented result against requirements and ACs.

## Acceptance Criteria

- [x] AC-1: The plan seed and project counterpart require context reuse and an operator-visible brief before dependent drafting, cover relevant brief dimensions, permit concise treatment of clear tasks, and apply three/five question ceilings without quotas or repeated known questions. Consequential unknowns cannot become assumed intent; independent work may continue while awaiting answers.
- [x] AC-2: Both implementation sources and counterparts require the behavioral Readback, relevant ACs and scope boundary, proportional example/files detail, direct correction of agent misreadings, and planning escalation only for actual contract contradictions or missing consequential decisions; no second approval is introduced.
- [x] AC-3: Review-plan source and counterpart compare the draft against its brief and request, explicitly permit Rationale as reference, report meaningful gaps into the existing branch walk, and preserve optional/current-wave behavior and scope authority.
- [x] AC-4: Named source-only tests reject empty, deleted, and semantically reversed instruction blocks independently in sources and counterparts; both upgrade carriers are checked. Fresh/existing destination probes and a bounded merge rehearsal demonstrate preservation of project additions, metadata, and managed regions, plus explicit conflict refusal.
- [x] AC-5: The revised guidance adds no gate, required approval, template section, or extra Markdown artifact; clear-task handling is concise, repeated known context is reused, and the instruction blocks contain no em-dash.
- [x] AC-6: This change records its own brief/readback and five executed behavioral rehearsals with observed actions and honest limitations; these cover clear intent, harmless ambiguity, a consequential unknown, a draft/brief discrepancy, and an agent-only misreading.
- [x] AC-7: This change's own suites and every test it adds pass, the documents it authors or edits validate, and no failure elsewhere is attributable to it.
- [x] AC-8: Both upgrade instructions map the four changed planning/implementation sources to their existing project prompts and require same-run bounded reconciliation using retained pre-apply evidence, with no wholesale replacement, silent omission, or overwrite of conflicting local intent.

## Tasks

- [x] Record the implementation Readback before the first seed/baseline edit.
- [x] Add proportional Brief guidance to seed 170 and the behavioral readback to seed 180 and the implement-wave baseline.
- [x] Add draft-versus-brief gap review to seed 175 and reconcile its section restrictions.
- [x] Add the four explicit upgrade mappings to seed 160.
- [x] Merge authored clauses into all five project counterparts, preserving project content and managed regions, then render owned surfaces.
- [x] Add source-only nonempty, semantic mutation, and parity tests; run fresh/existing destination probes and the safe merge/conflict rehearsal.
- [x] Execute the five behavioral scenarios and record observations in the existing Progress Log.
- [x] Update the Unreleased changelog with external behavior and user benefit.
- [x] Run focused verification, validate docs, and run the full framework suite last before closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| readback | implementer | none | AC-6 before implementation edits. |
| canonical-guidance | implementer | readback | Brief, readback, gap review, and upgrade mappings. |
| counterparts | implementer | canonical-guidance | Five bounded authored merges, then managed render. |
| verification | implementer | counterparts | Contract mutants, destination probes, behavioral rehearsals. |
| delivery-review | reviewers | verification | Existing required lanes; no new lifecycle stage. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `.wavefoundry/framework/seeds/175-review-plan.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/prompts/plan-feature.prompt.md`
- `docs/prompts/review-plan.prompt.md`
- `docs/prompts/implement-wave.prompt.md`
- `docs/prompts/implement-feature.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `CHANGELOG.md`

## Affected Architecture Docs

N/A: the change edits prompt content and adds a test; no module boundary, data or
control path, or verification seam moves. `docs/prompts/index.md` keeps its entries
because no command is added or renamed.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Resolve material uncertainty before drafting. |
| AC-2 | required | Verify the implementer's behavioral interpretation. |
| AC-3 | required | Compare the draft with the actual brief. |
| AC-4 | required | Detect missing guidance and unsafe propagation. |
| AC-5 | important | Keep the workflow proportional. |
| AC-6 | required | Observe the proposed habit on bounded scenarios. |
| AC-7 | required | Change-local verification. |
| AC-8 | required | Existing destinations receive the new guidance safely. |

## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-08 | Final review PASS: code, QA, docs-contract, release; no findings or deferrals. Gapfill: canonical/test MCP orientation and targeted reads occurred before activation; implementation used shell for bounded mechanical prose insertion and executed tests, not code navigation. Review lanes independently used MCP retrieval. Memory proposal returned zero; lesson about parity versus observed behavior is already in canonical guidance and this record. | Typed delivery approvals; wave Review checkpoints contain mutation tables and limitations; operator explicitly requested final review then closure. |
| 2026-09-07 | Observe: final framework suite PASS, 8,531 tests across 75 files, three expected skips; current receipt written. All eight ACs and tasks complete. Framework and seed gates closed. Delivery Review wave remains next; no closure or commit performed. | Canonical run_tests.py completed in 196.977 seconds; full docs validation and diff check pass. |
| 2026-09-07 | Observe: fresh-context upgrade agent used retained pre-apply and extracted source evidence to merge all four customized destinations. Independent verification removed each insertion and recovered original bytes; metadata/custom additions/managed regions preserved. Conflict project assumed unanswered intent was approved: agent stopped before any write, all four files unchanged. Actual renderer after successful merge preserves all four new blocks and additions; rerun writes nothing. | AC-4/8; bounded temporary fixtures at /tmp/1xhgc-upgrade-rehearsal; 1xhgc_upgrade_rehearsal. This is authored reconciliation plus real rendering, not an end-to-end archive installation. |
| 2026-09-07 | Observe: independent QA checkpoint PASS, new class 3/3; complete test_render_agent_surfaces suite 120/120; managed surface sync wrote nothing; gardener stamped four changed prompt dates; full docs validation and diff check pass. | 1xhgc_readiness_qa implementation checkpoint; full framework suite running. |
| 2026-09-07 | Observe: canonical guidance and five bounded project merges written; existing metadata and managed regions preserved. Focused BriefingLoopCarrierTests pass 3/3. Initial test probe found an unrelated earlier upgrade phrase intercepted a mutant; scoped mutations to the extracted block and verified deleted/empty/reversed controls now fail for the intended clause. | AC-1/2/3/5/8; seed 175 exclusion repaired; no renderer implementation change. |
| 2026-09-07 | Behavioral A: README recieve-to-receive only. Observed: one-sentence brief, no questions, targeted plan next. Expected: proceed without interview. PASS. B: internal case-insensitive report sort, tie order unspecified. Observed: retain existing tie order as explicit reversible assumption, draft next. Expected: state reversible choice and proceed. PASS. | Fresh-context 1xhgc_behavior_planning consumed actual plan-feature prompt; no expected answers supplied. |
| 2026-09-07 | Behavioral C: automatic inactive-account deletion, retention and legal holds undecided. Observed: asked retention/hold questions, kept policy open, paused deletion rules/ACs while recording known goal. Expected: do not assume policy. PASS. | Same isolated planning rehearsal; scenario contexts evaluated separately. |
| 2026-09-07 | Behavioral D: brief filtered rows/local CSV/display order versus draft all rows/cloud/alphabetic. Observed: identified all three discrepancies, self-answered from request/Rationale, no operator questions. Expected: compare against brief and correct scoped draft. PASS. E: intact table rows required, prior readback wrongly split oversized rows. Observed: corrected Readback, kept headers and whole oversized row, proceeded without new approval. Expected: correct agent-only error directly. PASS. | Fresh-context 1xhgc_behavior_review consumed actual review-plan/implement-feature prompts; no expected answers supplied. Five finite observations, no comparative benchmark or universal adherence claim. |
| 2026-09-07 | Readback: reuse context and clarify consequential unknowns before dependent drafting; implementers describe behavior/ACs/boundaries/files and correct their own misreading directly. Example: unanswered scope stays open while independent work proceeds; a clear requirement misread by the agent is corrected without another approval. Thought: edit canonical guidance, merge five authored counterparts, render owned regions, test contracts and blind scenarios, then validate. | AC-1/2/3/6/8; exact file scope above; no runtime migration or new approval. Readiness council and four lanes PASS; operator authorized prepare/review/implement. |
| 2026-09-07 | Revised on operator direction after reviewing the supplied full article: proportional briefing, consequential unknowns, brief comparison, existing-destination reconciliation, and behavioral verification. | Operator-supplied article; requirements 1-9 and AC-1 through AC-8. |
| 2026-09-07 | Planned from the 1x5tr delivery review and the operator's request to apply the briefing-loop principle. | Change doc; findings RED-DEL-9 and RED-DEL-10 in the 1x5tr ledger. |


## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-07 | Use proportional prompt guidance, existing records, and explicit upgrade reconciliation. | Applies the operator-supplied article while preserving autonomy on clear or independently actionable work. | Mandatory interview/confirmation: adds friction even when intent is known. Unconditional assumption fallback: silently substitutes intent. New code gates or brief files: premature enforcement and duplicated context. |
| 2026-09-07 | Supplement contract tests with five behavioral rehearsals. | Text presence proves distribution, not understanding. | Parity only: matching copies may both prescribe the wrong behavior. Broad benchmark framework: exceeds this bounded wave. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Briefing becomes ceremony. | Clear tasks get concise treatment; no question quotas or mandatory acknowledgement. |
| The agent substitutes guessed intent. | Keep consequential decisions unresolved and pause only dependent work. |
| Gap review ignores the brief. | Explicitly permit Rationale as comparison input while preserving scope restrictions. |
| Existing projects miss new prose. | Named upgrade mappings, bounded merges, and existing-destination rehearsal. |
| Tests prove only matching text. | Independent semantic mutants plus observed behavioral scenarios. |
| Rehearsals overstate effectiveness. | Record finite observations and limitations; no general quality or speed claim. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
