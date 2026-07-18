# Memory-retrieval evaluation baseline

Change ID: `1sufm-enh memory-retrieval-eval-baseline`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-18

Wave: `1sufo memory-retrieval-eval-and-fusion`

## Rationale

Any change to how the memory layer ranks records must be measured, not assumed. We validated a real defect to measure against: `wave_memory_search` computes the decay/centrality order via `_memory_ranked`, then re-sorts wholesale by semantic rank when a query has semantic hits (`server_impl.py:8002-8004`), so relevance can override the trust/decay policy. Before we touch that (the companion fusion change), we need a memory-specific golden set and a recorded baseline.

The project already has a standing golden-query retrieval eval policy for code/docs retrieval (wave `1seaw`, change `1sear`). This change adds the analogous, memory-specific harness: fixtures over synthetic memory records with known expected results, so ranking changes are gated on measured improvement without regressing the policy invariants (exact-target, decay, supersession, degraded no-index).

## Requirements

1. **Golden fixtures.** A memory-specific fixture set of `(query or target/symbol) → expected record ID(s)` over a synthetic, in-fixture memory corpus. Coverage must include: paraphrased queries (semantic), exact target/symbol lookups (structural), degraded no-index operation (text-containment fallback), decay behavior (a decayed record ranks below a fresh one of equal base confidence), and supersession (a superseded record is excluded from default surfacing).
2. **A deterministic runner** that executes the current `wave_memory_search`/`wave_memory_brief` paths against the fixtures and reports recall@k / MRR plus explicit pass/fail on the policy-invariant cases.
3. **Recorded baseline.** The runner records the current behavior's metrics as the baseline the fusion change must beat, and also measures lexical-only and semantic-only configurations for comparison.
4. **Gate, not ranking change.** This change measures only; it does not alter `_memory_ranked`, the semantic re-sort, or any surfaced behavior. The companion fusion change consumes this harness as its adoption gate.
5. **Deterministic and hermetic.** Fixtures build their own memory corpus and index (or exercise the no-index fallback deterministically); no dependency on this repo's live (empty) corpus.

## Scope

**Problem statement:** there is no way to measure memory-retrieval quality, so a ranking change (the fusion companion) has no baseline or invariant guard. The current path also has a validated relevance-overrides-policy defect that a baseline should capture.

**In scope:**
- A memory-retrieval eval fixture set + runner under the framework test/eval area (mirroring the `1sear` golden-query harness where practical).
- Synthetic memory-record corpus fixtures covering the five categories.
- Reuse of `wave_memory_search_response` / `wave_memory_brief_response` / `_memory_ranked` (server_impl.py) and `load_memory_records`/`match_targets` (memory_records.py) as the measured surface.
- Docs — a short reference for the memory eval set + how it gates ranking changes; a pointer from the code/docs eval doc.

**Out of scope:**
- **Any ranking/behavior change** — companion change `1sufn` owns that; this only measures.
- **The code/docs golden-query suite (`1sear`)** — related policy, separate corpus; this is memory-specific.
- **A live standing CI gate** — this lands the fixtures + runner + baseline; wiring it into a standing gate can follow.

## Acceptance Criteria

- [x] AC-1: A memory-specific golden fixture set exists covering all five categories: paraphrase, exact target/symbol, degraded no-index, decay, supersession. (required) — `tests/eval/memory_golden.json` (6 records, 5 cases, one per category); `test_fixture_covers_all_five_categories`.
- [x] AC-2: A deterministic runner scores the current `wave_memory_search`/`brief` paths on the fixtures (recall@k / MRR) and asserts explicit pass/fail on the policy-invariant cases. (required) — `tests/eval/run_memory_eval.py` reports recall@k/MRR per case + `top_is`/`ranked_above`/`excludes` invariant pass/fail; `test_all_policy_invariants_pass`, `test_recall_and_mrr_reported_per_case`.
- [x] AC-3: The runner records a baseline plus lexical-only and semantic-only comparison points, consumable by the fusion change as its adoption gate. (required) — `comparison` block (paraphrase recall@1: baseline 1.00 vs semantic_only 0.00 vs lexical_only 0.00); `test_recorded_baseline_beats_semantic_and_lexical_only`.
- [x] AC-4: This change alters no ranking or surfaced behavior — `_memory_ranked` and the search/brief paths are unchanged; the harness is measurement-only. (required) — 1sufm adds only fixtures/runner/test/docs; it touches no product ranking code (the runner only calls the shipped paths).
- [x] AC-5: Fixtures are hermetic (build their own corpus/index or the deterministic no-index fallback); no dependency on the live corpus. (required) — `build_corpus` writes the synthetic records into a throwaway repo; a fixed `_StubIndex` models semantic retrieval; `test_hermetic_reproducible` (two independent runs agree).
- [x] AC-6: Full framework suite green; docs-lint clean. (required) — full suite 5797 OK; `wave_validate` docs-lint ok.

## Tasks

- [x] Author the synthetic memory-record corpus + `(query/target) → expected` fixtures for the five categories. — `tests/eval/memory_golden.json`.
- [x] Build the deterministic runner over `wave_memory_search`/`brief`; report recall@k / MRR + invariant pass/fail; record baseline + lexical-only + semantic-only. — `tests/eval/run_memory_eval.py` (+ CLI); `test_memory_eval.py` (5 tests).
- [x] Reference doc for the memory eval set + gating; pointer from the code/docs eval doc. — `docs/references/memory-retrieval-eval.md`; `docs/architecture/testing-architecture.md` tier row. (Brief note: exercised via search-path fixtures; `wave_memory_brief` shares the same `_memory_ranked` policy.)
- [x] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fixtures | framework | — | synthetic corpus + expected-result fixtures (5 categories) |
| runner | framework | fixtures | deterministic scoring over current search/brief; baseline record |
| verify | framework | runner | suite + docs |


## Serialization Points

- Measurement-only; no serialized code surface. Consumed by `1sufn` (fusion) as its adoption gate.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` gets a memory-retrieval eval tier note; a short reference doc describes the set. No behavior change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The golden set is the whole point; must cover policy invariants |
| AC-2 | required | Deterministic scoring + invariant pass/fail |
| AC-3 | required | Baseline + comparisons gate the fusion change |
| AC-4 | required | Measurement-only; must not perturb ranking |
| AC-5 | required | Hermetic — cannot depend on the empty live corpus |
| AC-6 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-17 | Change doc authored; validated the relevance-overrides-policy defect to baseline | `server_impl.py:8002-8004` (semantic re-sort overrides `_memory_ranked`) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-17 | Eval baseline before any fusion change | Ranking changes require measured improvement + invariant guard | Ship fusion and eyeball it (rejected — the whole lesson from the agentmemory review) |
| 2026-07-17 | Memory-specific harness, hermetic fixtures | Live corpus is empty; policy invariants are memory-specific | Reuse the code/docs `1sear` suite directly (rejected — different corpus/invariants) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Fixtures too small to be meaningful | Cover all five categories explicitly; report per-category so gaps are visible |
| Harness accidentally changes behavior | AC-4 measurement-only; `_memory_ranked`/search paths untouched |
| Baseline drifts as corpus grows | Hermetic fixtures (own corpus), so the baseline is reproducible |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
