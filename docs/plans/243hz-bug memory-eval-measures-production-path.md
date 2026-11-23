# Memory eval measures the production search path

Change ID: `243hz-bug memory-eval-measures-production-path`
Change Status: `withdrawn`
Owner: Engineering
Status: withdrawn
Last verified: 2026-11-23
Wave: TBD

> **SUPERSEDED 2026-11-23 by `245sp-enh memory-eval-situation-queries-and-baselines`, by operator direction. Do not implement this spec as written.**
>
> Its probes are each sampled record's own summary, which measures an index round trip rather than retrieval (see the [memory systems assessment](../arcs/244cm%20memory-quality/research/agent-memory-systems-assessment.md), section "Evaluation"). The replacement spec carries this spec's production-path row (Requirements 1 to 6, AC-1 to AC-4) and its bounded experimental row (Requirements 7 to 9, AC-5 and AC-6) onto an independently authored situation-language query set. The diagnosis below stays valid and is the evidence for those rows. The spec was removed from wave `245na memory-eval-production-path` with `wf_remove_change` on 2026-11-23 and is in no wave. Arc: `244cm-arc memory-quality`.

## Rationale

`wf_memory_eval` reports a production variant that it never runs, and its experimental row measures policy order rather than relevance. On this repository's 12-record self-summary sample it reports `candidate` and `lexical_only` recall@3 0.25 and MRR 0.2628, against `semantic_only` 1.0. A reader takes 0.25 as the quality of memory search. Over the same 12 probes, the real `memory_search` path returns the target first in 12 of 12 cases: recall@3 1.0, MRR 1.0, no fallbacks, across the full 174-record surfaced corpus. The planner measured this on 2026-11-23 by calling `memory_handlers.memory_search_response` with a real `WaveIndex`.

The causes, verified against `.wavefoundry/framework/scripts/memory_eval.py` and `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`:

1. `run_curated` names `production_variant: memory_rrf_summary5` but computes no row through `memory_search_response` or `_memory_query_records`.
1. `_candidate_and_controls` passes the full `lexical_bm25_order` list to `_policy_order`. BM25 admits every record that shares any token with the query: 12 of 12 on every probe, although BM25 ranks the target first in all 12.
1. `_policy_order` calls `_memory_ranked`, which sorts by `memory_policy_sort_key`, with policy fields ahead of relevance rank. Relevance only breaks ties, so the target reaches the top 3 at about the chance rate of 3/12.
1. `semantic_only` scores 1.0 only because `_semantic_order` admits the few sampled records in the `search_docs` top 20.

**Kind: `bug`.** The shipped tool reports a label that claims a production measurement it does not make, and its headline experimental number measures an artifact of the eval, not retrieval. Both are defects in what the tool already claims to do. The fix adds no new capability beyond making the existing claim true (planner default).

## Product Intent

**Who benefits:** maintainers and agents who read `wf_memory_eval` to judge whether memory search finds the right record.

**Before:** the report's only rows are an unbounded, policy-sorted experimental fusion and its single-stream controls. It labels a production variant it never ran, and the low experimental number reads as production quality.

**After:** the report's headline `production` row is computed through the same `memory_search_response` path and index that `memory_search` uses, with reranker screening. Any probe on which that path falls back is counted by reason, and no number is presented as model-screened unless every probe was screened. The experimental rows rank a shortlist the size of production's before the policy sort, and their label says what they measure.

**Boundary:** measurement only. Production ranking, `memory_policy_sort_key`, the shared `lexical_bm25_order` and `reciprocal_rank_fusion` primitives, and the hermetic `run()` pass are unchanged. The output stays aggregate-only.

**First outcome:** the production row (AC-1, AC-2, AC-3, AC-4) is the outcome worth shipping on its own: it replaces a misleading headline with a true one. The bounded experimental row (AC-5, AC-6) ships with it because the two rows share one report and labels. A maintainer demonstrates the outcome by calling `wf_memory_eval` after an MCP restart. This repository should report `production` recall@3 1.0 and MRR 1.0 on the current sample, and `production_retrieval.fallback_probes` 0. Those live values are `inferred` from the planner's out-of-tree probe and will drift as the corpus changes.

## Requirements

1. `run_curated` computes a `production` metrics row. For each sampled record it calls `memory_handlers.memory_search_response(root, query=<record summary>, index=<index>, limit=MEMORY_QUERY_CHECK_CAP)` and scores the returned record order against that record, using the same recall@k and MRR helpers as the other rows. The call uses the public path's own record loading, so the production row ranks against the full surfaced corpus plus archive register entries, not only the sample.
1. `run_curated` accepts an optional `index` argument. When it is given, the semantic order for the experimental rows and the production row both use that object. When it is `None`, `run_curated` builds `WaveIndex(root)` as it does today, which keeps the CLI `--curated-root` path working.
1. `wf_memory_eval_response` accepts an optional `index` and passes it to `run_curated`. The `wf_memory_eval` tool handler in `server_impl.py` passes `get_handler().index`, the same object the `memory_search` handler passes.
1. The report carries `production_retrieval` with three aggregate fields: `model_screened_probes`, `fallback_probes`, and `fallback_reasons`. `model_screened_probes` counts probes whose `retrieval.qualification` is `model_relevance`. `fallback_probes` counts every other probe. `fallback_reasons` maps each `retrieval.fallback_reason` value to a count, sorted by key.
1. When `fallback_probes` is 0, `metrics.production` holds the row. When it is greater than 0, `metrics` has no `production` key and the report sets `production_unavailable_reason: "production_path_fell_back"`. A partly screened number is never reported as the production metric.
1. The report sets `headline_variant: "production"`. `production_variant` names the path the row runs: `memory_search_hybrid_rrf`.
1. The curated experimental rows bound each relevance stream before `_policy_order`. `candidate` policy-orders `reciprocal_rank_fusion([lexical[:MEMORY_SEARCH_CAP], semantic])[:MEMORY_QUERY_CHECK_CAP]`. `lexical_only` policy-orders `lexical[:MEMORY_QUERY_CHECK_CAP]`. `semantic_only` policy-orders `semantic[:MEMORY_QUERY_CHECK_CAP]`. The caps come from `memory_handlers`, not new literals.
1. The bound applies only to the curated pass. The hermetic `run()` pass keeps its current unbounded `_candidate_and_controls` behavior and recorded results.
1. `experimental_variant` becomes `policy_ordered_rrf_shortlist5`. `baseline_variant` stays `legacy_policy_ordering`. No label other than `production_variant` and `headline_variant` names production.
1. The report never carries record bodies, summaries, memory ids or target refs, including in `production_retrieval` and any diagnostic text. An exception during the production call is not echoed. The report sets `unavailable_reason: "production query measurement unavailable"` and `available: false`, matching the existing semantic-query failure handling.
1. The `qualifying: false` notice and `adoption_gate` are unchanged. A production row computed from self-summary probes is still a diagnostic, not qualification.

## Scope

**Problem statement:** the curated memory eval mislabels a production variant it never measures, and its experimental row measures policy order because an unbounded lexical stream reaches the policy sort.

**In scope:**

- A `production` row and `production_retrieval` fallback counts in `run_curated`.
- Passing the server's shared index from the `wf_memory_eval` handler to `run_curated`.
- Bounding the curated experimental streams to production's caps and relabelling the variants.
- Tests, the tool-surface contract text, the memory-retrieval eval reference, the handler-digest fixture, and a CHANGELOG entry.

**Out of scope:**

- An independent holdout query set, so the production row still uses self-summary probes (a later follow-up).
- Any change to production ranking, `memory_policy_sort_key`, `_memory_query_records`, `memory_search_response`, `lexical_bm25_order` or `reciprocal_rank_fusion`.
- The hermetic `run()` pass and its recorded fusion-gate values.
- The tool's input schema. `tool-surface-golden.json` and `tool-surface-golden/declared.json` pin only annotations, input schema and tier for `wf_memory_eval`, so they do not change. The planner checked both files on 2026-11-23.

## Acceptance Criteria

- [ ] AC-1: The production row runs the production code path, proved by a spy, not by inspection. A test stubs `memory_handlers.memory_search_response` with a recorder and runs `run_curated` on a 4-record fixture corpus with a supplied stub index. The recorder sees exactly 4 calls. Each call passes the supplied index object (identity, `is`), a `query` equal to one sampled record's summary, and `limit` equal to `MEMORY_QUERY_CHECK_CAP`. The test fails if the production row is computed from `_candidate_and_controls` or any other function.
- [ ] AC-2: The production row scores what the production path returns. The stub from AC-1 returns the probe's own record first for 3 of the 4 probes, and returns an empty list with `qualification: "model_relevance"` for the fourth. The report then carries:
  1. `metrics.production` equal to `{"recall_at_k": 0.75, "mrr": 0.75}`;
  1. `production_retrieval` equal to `{"model_screened_probes": 4, "fallback_probes": 0, "fallback_reasons": {}}`;
  1. `headline_variant` equal to `"production"`.
  A mutant that computes the production row from the experimental `candidate` ranking fails this test, because the experimental ranking on that fixture differs from the stub's.
- [ ] AC-3: A fallback is reported in aggregate and never as a screened number. The stub returns `qualification: "unavailable"` with `fallback_reason: "memory_vector_coverage_incomplete"` for 1 of 4 probes, and `"model_relevance"` for the rest. The report then carries:
  1. no `production` key in `metrics`;
  1. `production_unavailable_reason` equal to `"production_path_fell_back"`;
  1. `production_retrieval` equal to `{"model_screened_probes": 3, "fallback_probes": 1, "fallback_reasons": {"memory_vector_coverage_incomplete": 1}}`.
  A second case with all 4 probes returning `fallback_reason: "semantic_index_unavailable"` reports `{"model_screened_probes": 0, "fallback_probes": 4, "fallback_reasons": {"semantic_index_unavailable": 4}}`.
- [ ] AC-4: The tool handler passes the server's shared index. A test drives the registered `wf_memory_eval` handler with a handler whose `index` is a sentinel object and spies on `run_curated`. The spy receives that sentinel as `index`. With `index=None` passed directly, `run_curated` constructs `WaveIndex(root)`, proved by a stubbed `WaveIndex` that records its construction.
- [ ] AC-5: The bounded experimental row measures relevance on a fixture where the policy sort would otherwise bury the target. The fixture has a probe record whose BM25 rank is 1 and an empty semantic stream. It has at least 4 decoy records that share a query token, sit at BM25 positions 6 and beyond, and sort ahead of the probe under `memory_policy_sort_key`. It also has filler records at BM25 positions 2 to 5 that sort behind the probe. For that probe, the curated `candidate` and `lexical_only` rankings place the probe first, giving recall@3 1.0 and reciprocal rank 1.0.
- [ ] AC-6: Known-bad for the bound. The AC-5 test fails when the bound is removed, that is, when the curated pass passes the unbounded `lexical_bm25_order` list to `_policy_order` as it does on 2026-11-23. With the bound removed the probe ranks 5th or lower, giving recall@3 0.0 for that probe. The implementer records the observed failing run in the Progress Log.
- [ ] AC-7: Labels are honest. The curated report carries `production_variant: "memory_search_hybrid_rrf"`, `experimental_variant: "policy_ordered_rrf_shortlist5"`, `baseline_variant: "legacy_policy_ordering"` and `headline_variant: "production"`. The string `memory_rrf_summary5` appears nowhere in `memory_eval.py` or the tool's report.
- [ ] AC-8: The hermetic pass is unchanged. `run()` on the golden fixture returns the same metrics and invariant results before and after the change, compared byte-for-byte as sorted JSON in a test or a recorded before and after run.
- [ ] AC-9: The privacy boundary holds for the new fields. `test_memory_eval_tool_reports_aggregate_only` and a new available-path test walk the full envelope, including `production_retrieval`. They find none of the keys `memory_id`, `summary`, `records`, `target_refs` or `body`, and no sampled summary string as any value. A stubbed production call that raises an exception whose message holds a summary yields `available: false` and `unavailable_reason: "production query measurement unavailable"`, and that summary appears nowhere in the envelope.
- [ ] AC-10: The change's own suites and every test it adds pass. The documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Add the `index` parameter to `run_curated` and `wf_memory_eval_response`, and pass `get_handler().index` from the `wf_memory_eval` handler in `server_impl.py`.
- [ ] Compute the `production` row and `production_retrieval` in `run_curated`, with the all-screened rule and the non-echoing exception handling.
- [ ] Add a curated-only bound to the experimental streams using `MEMORY_SEARCH_CAP` and `MEMORY_QUERY_CHECK_CAP`, leaving `run()` and the shared primitives unchanged.
- [ ] Rename the variant labels and add `headline_variant`.
- [ ] Write the AC-1 to AC-9 tests in `tests/test_memory_eval.py`, and record the AC-6 known-bad run.
- [ ] Refresh `register-surface-handler-digests.json` for the changed `wf_memory_eval` handler.
- [ ] Update the `wf_memory_eval` section of `docs/specs/mcp-tool-surface.md`, the curated sections of `docs/references/memory-retrieval-eval.md`, and the memory-retrieval row of `docs/architecture/testing-architecture.md`.
- [ ] Add a `### Fixed` entry under `## [Unreleased]` in `CHANGELOG.md`.
- [ ] After an MCP restart, call `wf_memory_eval` on this repository and record the aggregate production and experimental values in the Progress Log.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| eval-engine | implementer | none | `memory_eval.py`, `memory_handlers.py`, `server_impl.py` |
| tests | implementer | eval-engine | AC-1 to AC-9, digest refresh |
| docs | implementer | eval-engine | tool-surface contract, reference, testing architecture, CHANGELOG |
| live-check | implementer | tests, docs | MCP restart, then `wf_memory_eval` |

## Serialization Points

- `.wavefoundry/framework/scripts/memory_eval.py`
- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_memory_eval.py`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/specs/mcp-tool-surface.md`
- `docs/references/memory-retrieval-eval.md`
- `docs/architecture/testing-architecture.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: its memory-retrieval eval row describes the curated diagnostic and gains the production row and the bounded experimental row. No other architecture doc changes, because module boundaries and data flow are unchanged. The eval already imports `memory_handlers` through `server_impl`.

## Platforms

The change is pure Python with no new paths, processes or file writes, so it behaves the same on Windows, macOS, Linux and WSL2. The production row runs whichever reranker provider the platform has: qualified local Tensorwell where available, otherwise the CPU fallback. Where neither loads, `_memory_query_records` returns `memory_relevance_model_unavailable`. The report then counts those probes in `production_retrieval.fallback_reasons` and omits `metrics.production`, per Requirement 5. On native Windows the shared server index removes a second model load per call, the same as on the other platforms.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core claim: the production row runs the real path. |
| AC-2 | required | The row reports what that path returns. |
| AC-3 | required | Fallbacks must never pass as screened numbers. |
| AC-4 | required | Same index as `memory_search`, as the operator directed. |
| AC-5 | required | The experimental row measures relevance. |
| AC-6 | required | The known-bad proof that AC-5 can fail. |
| AC-7 | required | Nothing claims production unless it is. |
| AC-8 | important | Guards the out-of-scope hermetic pass. |
| AC-9 | required | The existing privacy boundary. |
| AC-10 | required | Change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-23 | Planner probe, out of tree in a scratch script, aggregate output only. Current `run_curated`: candidate and lexical_only 0.25 / 0.2628, semantic_only 1.0 / 1.0, baseline 1.0 / 1.0. Fused shortlist of 5 before the policy sort: candidate and lexical_only 0.5 / 0.5194. `memory_search_response` with `WaveIndex(root)` and `limit=5` over the same 12 probes: 1.0 / 1.0, fallback reason `none` for 12 of 12, surfaced corpus 174 records. | `run_curated` on this repository, plus a probe calling `memory_search_response` per sampled summary. |
| 2026-11-23 | Gapfill: the planner read code with grep and sed rather than the `code_*` tools. `docs_search` and `memory_search` were used and were healthy. | Planning session. |
| 2026-11-23 | Superseded by `245sp-enh memory-eval-situation-queries-and-baselines` and removed from wave `245na`, by operator direction. The production-path row and the bounded experimental row move to that spec; the self-summary probes are replaced by a frozen situation-language query set. | Operator decision 2026-11-23; `wf_remove_change` result. |
| 2026-11-23 | Header set to `Status: withdrawn` and `Wave: TBD`, because the spec is in no wave. Docs-contract readiness advisory for wave `245na`. | Readiness repair cycle 1, context `245na-planner-repair-1`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-23 | Record this spec as withdrawn with `Wave: TBD`, keeping its body as history. | Coordinator decision, 2026-11-23, reversible, applying the docs-contract advisory and the repository convention for withdrawn plans. | Delete the spec; declined, because its diagnosis is the evidence for `245sp`. |
| 2026-11-23 | The production row calls `memory_search_response` end to end, ranking against the full surfaced corpus. | Planner default, within the operator's direction to measure "the actual production query path, with the reranker". Only the public entry point exercises production's record loading, archive register entries, caps, screening and order preservation together. Mechanism efficacy: replaying the motivating case through this row gave 1.0 / 1.0, where the current report says 0.25. The row controls the headline rather than advising, and its known gap is that self-summary probes stay easy, which the holdout follow-up addresses. | Calling `_memory_query_records` on the 12 sampled records only. Weakness: it skips the public path's loading and ordering, so it could drift from production unnoticed. |
| 2026-11-23 | Report `metrics.production` only when every probe was model-screened, and otherwise report the fallback counts and `production_path_fell_back`. | Planner default implementing the operator's rule that no number is reported "as if it were model-screened". A partly screened average mixes lexical recovery with screened results under one label. | Report a partial average with a screened-probe count. Weakness: readers quote the number and drop the count. |
| 2026-11-23 | Bound the curated experimental streams to production's caps: lexical top `MEMORY_SEARCH_CAP`, fused top `MEMORY_QUERY_CHECK_CAP`, and single-stream controls top `MEMORY_QUERY_CHECK_CAP`. | Planner default within the operator's "bound the lexical stream before the policy sort". On a 12-record sample a lexical cap of 20 bounds nothing, so the fused cap of 5 is what binds. Reusing production's caps makes the row answer one clear question: what policy-ordering production's shortlist would do. Measured live: 0.5 / 0.5194, so the row still shows a policy effect, now within a five-record shortlist. | A lexical cap of 3 (`DEFAULT_K`). Weakness: recall@3 becomes nearly guaranteed, measured 1.0 recall and 0.625 MRR, which is self-fulfilling. A BM25 score threshold. Weakness: it needs a tuned constant with no production counterpart. |
| 2026-11-23 | Apply the bound only in the curated pass. | Planner default. The hermetic `run()` pass carries the recorded 1sufn and 1yad2 fusion-gate values, and the BM25 and RRF primitives are shared with production search. Changing either is outside the approved scope. | Bound inside `_candidate_and_controls` for both passes. Weakness: it rewrites recorded gate evidence. |
| 2026-11-23 | Kind `bug`, not `enhancement`. | Planner default. The tool already claims a production variant and reports a misleading headline, so the fix makes an existing claim true rather than adding capability. | `enh`, because a new row is added. Weakness: it frames a mislabelled measurement as missing polish. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The production row runs the reranker 12 times per call, slowing `wf_memory_eval`. | Twelve screenings of at most 5 summaries each. The live-check task records the observed duration. |
| Self-summary probes overstate production quality, because a record's own summary is an easy query. | `qualifying: false` stays. The holdout query set is the named follow-up. |
| The production row ranks against the full corpus while the experimental rows rank against the sample, so readers may compare unlike rows. | The tool-surface contract and reference doc state the difference next to the row definitions. |
| Open question for the operator: should the experimental row also get an unscreened relevance-order ablation, meaning production without the reranker, to isolate the reranker's contribution? | Not planned. Raise it at Prepare. Silence keeps it out of scope. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
