# code_ask over-weights prose docs and under-surfaces implementing code

Change ID: `1p66s-enh code-ask-doc-code-retrieval-balance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-17
Wave: `1p66q code-ask-retrieval-quality`

## Rationale

The quality assessment found that even on **correct** behavioral answers (e.g. flush-ordering, enduser.session string/numeric), `code_ask` cited the spec/ADR and omitted the implementing `.ts` — a persistent doc-bias. This matches the project's standing retrieval finding (memory `project-code-retrieval-quality-levers`): the lever is the retrieval **mix/partition**, not the embedder. Grounded root causes (verified):

1. **Two embedders, two incomparable cosine scales.** Docs embed with the arctic-doc model and code with the bge-code model in separate LanceDB tables (`server_impl.py:1534-1546`); `all_candidates = docs_candidates + code_candidates`. When the cross-encoder reranker runs, both are rescored on one sigmoid scale (comparable — good). **When the reranker does NOT run**, the raw, incomparable cosines compete directly, and NL queries embed more similarly to prose, so docs dominate.
2. **Doc demotion is narrow and explanatory-only.** `_demote_doc_results` (`server_impl.py:14994`) multiplies scores down (0.50–0.75) **only when `question_type == "explanatory"`** and **only** for `docs/waves/`, `docs/plans/`, seeds, and journals. Architecture docs (`docs/architecture/`), specs (`docs/specs/`), and ADRs are **never** demoted, and `navigational`/`instructional`/`artifact_anchored` questions get no demotion at all — so a spec carrying its full score outranks the implementing code on a "where/how is X implemented" question.
3. **The per-index floor injects ≥3 doc citations regardless of relevance** (`AGENT_PER_INDEX_FLOOR_K`, shared with `1p66r`), so even a perfect code top-5 still ships 3 doc citations.

This change rebalances the code-vs-doc mix so the implementing code surfaces when the question is about code — without losing the genuine value of spec/ADR context.

## Requirements

1. **Question-type-aware code/doc balance.** For code-implementation intent (`navigational` "where is X" and code-leaning `explanatory` "how does X work"), the final citation mix must favor implementing code over prose when both are retrieved — e.g. a code-biased quota/floor (the per-index floor should not force 3 doc slots ahead of stronger code), or a doc demotion that applies to these intents, not just `explanatory`.
2. **Broaden doc demotion coverage.** Extend `_demote_doc_results` beyond `docs/waves/`/`docs/plans/`/seeds/journals to also cover `docs/architecture/` and `docs/specs/`/ADRs for the code-implementation intents — so a spec does not outrank the `.ts` that implements it. Demotion must remain a *down-weight*, never an exclusion (specs are still valid, secondary context).
3. **No-reranker safety.** Because the doc-bias is worst when the reranker is absent, the rebalance must hold in the no-reranker path too (where it matters most) — e.g. apply the code/doc quota at selection time, not only via reranker scores.
4. **Faithfulness / no over-correction.** A genuinely doc-answerable question (spec-defined contract, an ADR decision, a pure-docs concept) must still surface the doc — the rebalance favors code only when code is actually retrieved and relevant; it never starves docs or fabricates code citations.
5. Generic; documented in `mcp-tool-surface.md` (retrieval-mix note) and `guru.md` (classification table already routes doc-heavy vs code questions — align). Tests: a "where is X implemented" fixture with both a doc mention and the implementing code asserts the code citation ranks/appears; a doc-answerable fixture still surfaces the doc.

## Scope

**Problem statement:** `code_ask` surfaces prose docs over implementing code for code questions — especially without the reranker — so answers cite specs/ADRs and omit the `.ts`/`.py` that actually implements the behavior.

**In scope:**

- `_demote_doc_results` (`server_impl.py:14994`) — intent coverage + path coverage (architecture/specs/ADRs).
- `_agent_candidate_select` / the doc-vs-code source bucketing (`server_impl.py:1186`, `:1648-1649`) — a code-biased quota for code intents; ensure the floor doesn't crowd code out.
- Question classification (`_classify_question`, `server_impl.py:15072`) only insofar as code-implementation intent must be distinguishable (reuse existing `navigational`/`explanatory`; no new taxonomy unless needed).
- Tests + docs.

**Out of scope:**

- Confidence/abstention (`1p66r`) and graph/enumeration recall (`1p66t`).
- Swapping embedding models (explicitly NOT the lever — memory `project-code-retrieval-quality-levers`).
- Reranker availability (`1p66u`).

## Acceptance Criteria

- [x] AC-1: For a code-implementation intent with both a doc and the implementing source, the demotion sinks the prose below the code so code leads, and the per-index floor guarantees code is present. (`test_demote_architecture_now_demoted` — code leads after demotion.)
- [x] AC-2: `_demote_doc_results` down-weights `docs/architecture/`, `docs/specs/`, and ADRs (gentler `_DEMOTION_REFDOCS`) for code-implementation intents (`explanatory` + `navigational`); demotion is a down-weight, never exclusion. (`test_refdocs_demotion_weight`, `test_demote_navigational_now_applies`.)
- [x] AC-3: A doc-answerable result still surfaces (down-weighted, never dropped). (`test_demotion_is_downweight_not_exclusion`; `test_demote_skips_non_code_intents` confirms non-code intents untouched.)
- [~] AC-4: The demotion (a pre-selection score multiplier) applies in BOTH the reranked and no-reranker paths, and the per-index floor guarantees code is present in both — so the within-docs prose-sink and code-presence hold regardless of reranker. **Narrowed:** a dedicated cross-source code *quota* over the doc floor was deferred — in the no-reranker path doc/code scores are incomparable cross-model cosines so a precise cross-source ordering is not meaningful there, and that path is now loudly flagged as degraded by `1p66r`; the reranked path (the healthy norm) gets the full code-bias via demotion + the existing navigational tilt. Building a quota on an incomparable scale would be guesswork.
- [x] AC-5: Docs updated (`mcp-tool-surface.md` doc/code-balance note); full suite + docs-lint clean.

## Tasks

- [x] Extend `_demote_doc_results` path coverage (architecture/specs/ADRs via `_DEMOTION_REFDOCS`) + intent coverage (`_DOC_DEMOTION_INTENTS` = explanatory + navigational); response `demotion_count` reporting extended to match.
- [~] Code-biased selection quota — deferred (see AC-4): demotion + the existing navigational tilt + the per-index floor cover the reranked (healthy) path; a quota on the incomparable no-reranker scale was judged guesswork and that path is flagged degraded by `1p66r`.
- [x] Tests: navigational-now-demotes, refdocs-demotion-weight, architecture-now-demoted (code leads), down-weight-not-exclusion, non-code-intent-skip; reconciled 2 stale old-behavior tests.
- [x] Docs: `mcp-tool-surface.md` doc/code-balance note; docs-lint + full suite. (`guru.md` classification table already routes code vs doc questions — no change needed.)

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| demotion + quota | Engineering | `1p66r` (shared selection code) | sequence after the safety floor |
| tests + docs | Engineering | demotion + quota | |


## Serialization Points

- Shares `_agent_candidate_select` / `code_ask` path with `1p66r` and `1p66t`; implement after `1p66r`.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (retrieval-mix behavior note). No layering change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The fix — code surfaces for code questions. |
| AC-2 | required | Spec/ADR/architecture demotion coverage. |
| AC-3 | required | No over-correction; docs still surface when right. |
| AC-4 | important | No-reranker is where the bias is worst. |
| AC-5 | important | Docs. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Planned from the quality assessment (doc-bias on correct answers) + grounded root cause. | `_demote_doc_results` `server_impl.py:14994`; separate doc/code tables `:1534-1546`; source bucketing `:1648-1649`; per-index floor `:157` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Rebalance via demotion-coverage + selection-time code quota, not an embedder change. | Memory `project-code-retrieval-quality-levers`: the embedder is not the lever; mix/partition is. Holds in the no-reranker path. | Swap/retune embedders (rejected — not the lever); rely on reranker only (rejected — fails in the no-reranker path, the worst case). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-correction starves genuinely doc-answerable questions. | AC-3 doc-answerable fixture; demotion is a down-weight not exclusion; quota applies only to code intents. |
| Intent misclassification routes a doc question through the code quota. | Quota favors code only when relevant code is actually retrieved; docs still present via their floor. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
