# Golden-Query Retrieval Eval Suite (the Standing Gate for Ranking Changes)

Change ID: `1sear-enh golden-query-retrieval-eval-suite`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-12
Wave: TBD

## Rationale

External code review (2026-07-12) + this repo's own history converge on the same gap: ranking/classification changes here ship eval-gated (the AC-8 gate that killed `code_risk_score` v1; the AC-10 recall comparison for agent-mode `code_ask`), but every gate so far has been BESPOKE — assembled per change, then discarded. There is no standing, repeatable retrieval evaluation, so (a) each ranking change re-pays the harness cost, (b) regressions between changes are invisible, and (c) observed quality issues (the review session's "where are the gaps?" queries ranking `.aiignore` comments above implementation; the session-8 "what value is X" constant-ranking weakness; the multi-token summary-first behavior) are recorded as memory anecdotes instead of failing test cases.

This change builds the suite; `1seas` (classifier/ranking improvements) is gated on it. It also seeds the review's proposed scheduled evaluation without committing to CI infrastructure yet.

## Requirements

1. **Golden-query corpus, versioned in-repo:** known-answer queries against THIS repo's indexed content, each with expected top-hit path(s)/symbol(s) and question-type expectations. Seed classes (from live evidence): architecture/review intent ("where are the biggest gaps in X"), known-symbol navigational, constant-value lookup, exact-identifier lexical, error-string lookup, enumeration ("which X are…"), direct ignore-file/manifest questions (the ONLY class where low-information paths are the right answer), and abstention cases (absent topics must return low confidence, not fabrication).
2. **Metrics:** Recall@k and nDCG@k against expected hits; abstention correctness on the negative controls; p95 latency and response size per tool (`code_ask`, `code_search`, `docs_search`, `code_lexical`). Cached-model runs only (no network).
3. **Runnable locally in one command** (a `run_tests.py`-adjacent entry or `wf` verb), producing a comparable scored report artifact; deterministic enough to diff across runs on the same index.
4. **Baseline recorded:** the current scores land in the change doc / a report artifact as the reference line `1seas` must beat-or-hold.
5. **Gate wiring:** documented (contributing/review docs) as the required evidence for future ranking/classification/chunking-relevance changes — the standing replacement for bespoke gates.

## Scope

**Problem statement:** ranking changes need an eval gate, and each one has been built from scratch and thrown away; known quality anecdotes aren't executable.

**In scope:** eval harness + golden corpus + metrics + baseline + gate documentation.
**Out of scope:** any ranking change itself (that is `1seas`); CI scheduling (operator infra decision — the suite must merely be CI-invocable later); consumer-repo query packs (the multi-language test-pack `p4ea` can extend this later).

## Acceptance Criteria

- [ ] AC-1: The suite runs in one local command against the current index with cached models and emits a scored report (Recall@k, nDCG@k, abstention, p95 latency, response size) per tool.
- [ ] AC-2: The corpus covers all eight seeded query classes, including the review session's misranked queries and at least two abstention controls.
- [ ] AC-3: The baseline run is recorded and reproducible (two consecutive runs on the same index agree within a documented tolerance).
- [ ] AC-4: The gate is documented in the contributing/review surfaces as required evidence for ranking-behavior changes.
- [ ] AC-5: Full suite bytecode-free + docs validation (the eval itself is NOT part of the default test run — it needs the built index).

## Tasks

- [ ] Harness (query runner + scoring + report artifact) under `scripts/benchmarks/` or eval-adjacent home.
- [ ] Golden corpus with the eight classes; encode the session's misranked queries verbatim.
- [ ] Baseline run + tolerance check; record scores.
- [ ] Gate documentation; suite + validate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| harness | implementer | — | Runner + metrics + report |
| corpus | qa-reviewer | — | Eight classes + negatives |
| baseline-docs | qa-reviewer | both | Scores + gate wiring |


## Serialization Points

- `1seas` (same wave) is BLOCKED on this change's baseline — the suite must exist and score before any ranking edit lands.

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` (the eval tier); `docs/contributing/review-and-evals.md` (gate requirement). N/A otherwise.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The deliverable. |
| AC-2 | required | Coverage is the value; anecdotes become executable. |
| AC-3 | required | An unreproducible gate gates nothing. |
| AC-4 | required | The standing-gate contract. |
| AC-5 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-12 | Drafted from the external code review (P1 CI/eval finding, the retrieval-eval kernel) + accumulated quality-log anecdotes that should be executable cases (session-8 constant ranking, review-session ignore-file misranking, multi-token summary-first). Positioned as the gate `1seas` requires. | Review report; quality-log memory; AC-8/AC-10 gate precedents (1p41o gate-out, 1p4hj recall comparison). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-12 | Suite is local-first and index-dependent (NOT in the default unit-test run); CI scheduling deferred to an explicit operator infra decision. | The default suite must stay hermetic/fast; the eval needs a built index + cached models. CI is a separate adoption question the suite must not block on. | **Bundle into run_tests.py:** breaks hermeticity. **Wait for CI decision:** the gate is needed by `1seas` now. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Index drift makes runs incomparable | Report records the index meta signature; comparisons are valid same-signature only, and the tolerance check quantifies noise. |
| Corpus overfits to this repo | Acceptable for the gate's purpose (this repo IS the dogfood); consumer packs (p4ea) extend later. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
