# Organize writing around a governing thought

Change ID: `22sqi-enh governing-thought-writing-guidance`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-08
Wave: 22sqj governing-thought-writing

## Rationale

The shared writing guide already says to lead with the answer, but does not explicitly connect a governing thought with logically grouped support. Envision already separates alternatives-first authoring from vision-first presentation. Extend these working instructions with the useful organizational principles of Barbara Minto's Pyramid Principle, without turning clear writing into a fixed template or prematurely choosing a destination.

## Product Intent

Agents and readers should recover a document's main point, how its supporting argument justifies it, and the evidence and uncertainty behind consequential claims. Envision should make the destination-to-roadmap connection easier to explain while preserving fair exploration and operator choice. This supports the adopted vision's living project understanding and continuity of intent; it does not change that vision. AC-1 and AC-2 establish delivered guidance; AC-3 observes its application to a bounded example, not comparative improvement or human comprehension.

## Requirements

1. Extend the canonical writing guide with a concise, attributed explanation: lead with the reader-relevant answer/outcome; develop distinct supporting points; each summary must faithfully represent its support; group comparable ideas in a useful logical order; expose missing support, duplication and certainty beyond the evidence. Keep conditions and uncertainty near the claims they qualify.
2. Apply the principle across existing artifact types, including specifications, architecture, plans, waves, ADRs, memories, prompts and handoffs, through the shared guide rather than duplicated rules. Preserve schemas, required headings, exact obligations, chronology where required, and project/operator formats. Do not impose point counts, strict MECE scoring, compulsory SCQ headings, word ceilings or new review gates. SCQ may help identify the reader's question when useful; it must not displace the requested answer-first opening.
3. Envision's core applies the shared organizing principle to the unified vision paragraph, Roadmap and supporting argument. Keep concrete alternatives before recommendation during authoring and the vision first during delivery. Horizons, arcs and waves organize work; supporting reasons organize an argument and need not map one-to-one to lifecycle containers. Preserve ambition, provisional status, operator-owned decisions and current review bounds.
4. Refine the existing reader reconstruction within its assigned review, so the roadmap stage asks how useful advances support the destination. During the subsequent full-packet review, check whether consequential conclusions follow from the evidence and whether uncertainty survives summary. Do not give scoring anchors before reconstruction or add another reviewer, loop or approval.
5. Mirror changed Envision core/phase text to the corresponding self-hosted prompts, using existing changed-seed reconciliation and packaging paths. Keep skill pointers, renderer, catalogs, seed 160 delivery ownership and public workflow surface unchanged. Record the source changes in the current unreleased changelog section.

## Scope

**In scope:** `.wavefoundry/framework/docs/writing-guide.md`; seed 179 and its local prompt; the Envision review companion and its local copy; changelog; change/wave records. Review guidance and a bounded application exercise use existing reviewer remits.

**Out of scope:** Rewriting existing visions, other project documents or history; lifecycle hierarchy changes; new templates, tools, dependencies, tests that merely pin wording, reviewers or gates; skill registry or renderer changes; publication or commits without current operator direction.

## Acceptance Criteria

- [x] AC-1: The guide explicitly connects the governing thought, grouped support and evidence, applies generally, attributes its basis, and preserves uncertainty, artifact contracts and flexible organization. A restatement of answer-first alone or a mandatory fixed pyramid fails.
- [x] AC-2: Canonical and local Envision core/review bodies agree and preserve alternatives-first authoring, vision/Roadmap-first delivery, staged reconstruction and bounded review while adding the destination/support check. Existing writing-guide delivery tests establish that the revised guide travels through the unchanged package owner.
- [x] AC-3: In one bounded application exercise, an independent existing QA reviewer reconstructs the revised example's main point and roadmap relationship before seeing its source brief or judging anchors, then checks consequential claims and uncertainty against the source. A supplied unsupported-conclusion control must be rejected. Report observed success or limits without a causal superiority claim; material failure returns to the operator before another batch.

## Tasks

- [x] Revise the shared writing guide and Envision core/review guidance, mirroring local copies.
- [x] Update the changelog and inspect exact scope, source/local parity and existing delivery checks.
- [x] Run the bounded staged reader exercise and required independent delivery review; record results and limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guidance and local parity | implementer | readiness | One writer; no native skill edits |
| Staged understanding and contract review | qa-reviewer, docs-contract-reviewer | frozen candidate | Read-only independent contexts; one application batch |

## Serialization Points

- `.wavefoundry/framework/docs/writing-guide.md`
- `.wavefoundry/framework/seeds/179-envision-project.prompt.md`
- `.wavefoundry/framework/seeds/envision/review.prompt.md`
- `docs/prompts/envision-project.prompt.md`
- `docs/prompts/agents/envision/review.prompt.md`

Changelog is a root-level documentation edit. Source writers finish before qualification and independent delivery review. Preserve unrelated admitted work in 22upa.

## Affected Architecture Docs

N/A: existing guide ownership, phased prompt delivery, skill pointers, reconciliation and lifecycle authority remain unchanged. This edits communication instructions within those contracts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Deliver the requested organizational principle without rigid process |
| AC-2 | required | Preserve Envision reasoning order and actual delivery |
| AC-3 | required | Check usable application beyond wording presence |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-08 | Planning only; current guide, core and review companion read directly after indexed search refused stale loaded runtime. No setup/rebuild or source edits. | Guide lines 13–21; seed 179 lines 39–55; review companion staged input order. |
| 2026-11-08 | Readiness passed for receipt review-policy-30877f589f79c1dd5f11. No source edit: activation refused because 22upa is OPEN in another session. Six-path proposal saved in the owned work area and passes git apply --check; application and delivery qualification remain pending. | Current typed QA, docs-contract and Council approvals; Implement response another_wave_active; proposed-guidance.patch. |
| 2026-11-08 | Implemented after 22upa was paused. The saved proposal was applied for the five guidance paths (base identities matched); the CHANGELOG hunk no longer applied because of 22upa bullets, so the 22sqj bullet was added by hand under `[Unreleased]` / Changed. Seed and local copies are byte-identical for the changed Envision core and review blocks. Staged exercise: the implementer wrote `.wavefoundry/work/22sqj/application-sample.md` from the saved source brief; a fresh QA reader got the opening alone, then the Roadmap alone, then the full packet. Anchors: four recovered, one partial (the shadow test's repeated-entry purpose, not material); no unsupported claim or lost uncertainty; the 20% pilot/migration control rejected. Limits: one agent reader and one application; no human-comprehension or superiority claim. Gapfill: shell `git apply` and diff for the mechanical patch application and parity check. | test_writing_guide_delivery 5 OK; test_render_agent_surfaces and test_vocabulary_prompt_names 237 OK; wf_validate_docs pass; typed delivery approvals qa-reviewer (22sqj-delivery-qa-reviewer-1) and docs-contract-reviewer (22sqj-delivery-docs-contract-reviewer-1) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-08 | Add concise argument organization at the existing guide owner, with targeted Envision application. | Existing invocation paths already deliver the guide; this is advisory writing behavior, not a mechanical correctness guarantee. The bounded reader exercise checks whether a resulting argument remains grounded. Field benefit requires later observations. | Leave answer-first alone: misses grouping and support; impose a standalone pyramid template: duplicates guidance and risks forced structure, premature conclusions and flattened dependencies. |
| 2026-11-08 | Use the existing QA remit for one staged application check. | Prevent another review mechanism while checking meaning and an unsupported conclusion. | Whole new Envision field trial: disproportionate to this small organizational addition; source-text checks alone: cannot observe meaning recovery. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Polished hierarchy hides weak evidence | Preserve contrary evidence and qualifications; test an unsupported conclusion |
| Answer-first becomes conclusion-before-exploration | Explicitly retain distinct authoring and presentation orders |
| MECE or fixed counts add artificial process | Flexible grouping, visible cross-cutting dependencies and no mandatory counts |
| Agent reader succeeds without proving human value | State this limit and do not claim demonstrated superiority |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
