# Findings Register as a Typed Assessment Surface

Change ID: `1wq0b-enh findings-register-assessment-surface`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-31
Wave: TBD

## Rationale

Wave `1seaw` measured that a broad assessment question (the review session's gaps question, fixture `architecture-review-calibration-gaps`) cannot retrieve the repository's current findings register (`docs/reports/index-quality-audit-dispositions.md`) through any content mechanism of the local model stack: the labeled sections rank 18 to 28 inside their own five-document report class and the cross-encoder scores findings tables near zero for assessment vocabulary. The cycle-2 council removed a `docs/reports/` path-class injector with a synthetic score because a subject-blind prior is not retrieval and it distorted every off-subject assessment answer. The operator then accepted assessment retrieval as a measured baseline weakness (option (a), 1seas Decision Log 2026-08-31) with this plan as the follow-up: if an agent should see the findings register while answering an assessment question, it must arrive through a typed, labeled surface it can choose to consult, not through `code_ask` citations.

## Requirements

1. **Typed surface, not a ranking prior:** expose the repository's findings registers through a structural surface with its own contract (an MCP resource such as `wavefoundry://reports/findings`, or a `report` kind on `docs_search` with explicit section rows), the same shape the graph signal uses (`graph_related`): labeled, separate from `citations`, never merged into organic ranking with a synthetic score.
2. **Register membership is declared, not inferred from a path prefix:** a report opts in through metadata (for example a `Register:` line or a `kind: findings` marker) so prompt templates, validation plans, and smoke checklists under `docs/reports/` are not mistaken for findings; a currentness predicate (`Last verified` recency or explicit supersession) is part of the declaration, so the surface never carries a "current" claim it does not evaluate.
3. **Guru routing:** seed 211 teaches when an assessment question should consult the surface (subject-conditioned: the query's content terms must overlap the register's declared subjects) and how to cite it; `code_ask` stays reranker-ordered.
4. **Gate coverage:** the standing retrieval gate scores the surface explicitly for the assessment class (a fixture-declared `surface`), so recall on findings registers is measured where the evidence actually appears and never through `citations` recall.

## Scope

**Problem statement:** assessment questions cannot reach the findings register through semantic retrieval, and the only mechanism that could was a fixture-shaped prior.

**In scope:**

- The typed surface and its declaration contract; Guru routing prose in seed 211 and the rendered `docs/agents/guru.md`; evaluator support for a fixture-declared surface; fixtures for two register subjects.

**Out of scope:**

- Any change to `code_ask` candidate generation, scores, or selection; embedding or reranker model changes; a currentness predicate inside the `code_ask` report-class prior (that prior stays score-only and documented as evaluating no currentness).

## Acceptance Criteria

- [ ] AC-1: An assessment question about a declared register subject returns the register's sections through the typed surface with true relevance metadata, while `code_ask` citations for the same question are byte-identical to the surface-less response.
- [ ] AC-2: A report without the register declaration never appears on the surface; a superseded or stale register is labeled as such by the declared currentness rule.
- [ ] AC-3: The standing gate scores the surface for the assessment class through a fixture-declared `surface`, with the original 1seaw assessment fixtures re-labeled to that surface and an unconsulted holdout authored by a reviewer who has not read the mechanism.
- [ ] AC-4: Full suite bytecode-free, docs validation, and five-value parity remain green; the wave's receipts show no change to any other class.

## Tasks

- [ ] Define the register declaration and currentness rule; migrate `docs/reports/index-quality-audit-dispositions.md` to it.
- [ ] Implement the surface (resource or `docs_search` kind) with tests against real in-memory Lance tables.
- [ ] Extend `retrieval_eval.py` with the fixture-declared `surface` and add the assessment fixtures plus the unconsulted holdout.
- [ ] Update seed 211, `docs/agents/guru.md`, `docs/specs/mcp-tool-surface.md`, and `docs/architecture/search-architecture.md`.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

[Declare review targets in either form below, then delete this bracketed note.]

Declare a target with a bullet whose content is entirely repo-relative paths, for example `` - `src/app/handler.py`, `docs/specs/` ``. When a target contains a space, declare it inside an explicit block instead:

```
**Review targets (repo-relative paths):**

- `docs/waves/1abc some slug/wave.md`
```

Prepare uses declared paths—not Scope, Rationale, or other narrative—to select automatic review lanes, and prose declares nothing in either form: a bullet containing one stray English word is prose (including inside the block, so a sentence there that merely quotes a path declares no target), a wrapped bullet is prose in its entirety, and a fenced example declares nothing. Adoption is per document, so declaring targets here never suppresses a sibling change doc's scoring, and declaring none keeps this document's whole-document coverage rather than emptying it. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

Which of `docs/ARCHITECTURE.md`, `docs/architecture/{current-state,domain-map,layering-rules,cross-cutting-concerns,data-and-control-flow,testing-architecture}.md`, or `docs/architecture/decisions/`* need updates, or `N/A` with rationale when the change is confined to a single module with no boundary/flow/verification impact.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required / important / nice-to-have / not-this-scope |           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
