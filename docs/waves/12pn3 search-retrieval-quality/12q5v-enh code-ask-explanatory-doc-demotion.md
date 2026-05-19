# code_ask — Unified Weighted Demotion (replaces hard partition)

Change ID: `12q5v-enh code-ask-explanatory-doc-demotion`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: 12pn3 search-retrieval-quality

## Rationale

`code_ask` fuses results from `code_search` and `docs_search` into a single ranked pool. The current system uses a hard binary partition (`_partition_feedback_artifacts`) that pushes seeds and journal/feedback docs unconditionally to the back of all results, regardless of their actual cross-encoder score. This causes two problems:

1. **Too blunt:** a journal scoring 1.0 for a framework-agent behavioral question is buried behind a README at 0.828, even though the journal IS the ground truth. Hard partition fires for all question types — including navigational, where the journal may be exactly the right answer.
2. **Incomplete:** wave change docs (`docs/waves/`) and staged plan docs (`docs/plans/`) are not covered at all by the existing partition, yet calibration testing shows they outrank implementation chunks for explanatory questions 2 out of 6 times.

The fix is a unified four-tier weighted demotion system applied to post-rerank scores, for `question_type == "explanatory"` only. Weighted demotion is:
- **Calibrated:** weights are derived from observed score gaps, not arbitrary
- **Soft:** demoted sources remain in the pool and can still rank above code if no competing implementation exists
- **Question-type-aware:** navigational and instructional queries are unchanged — journals and seeds surface freely for "where is X?" or "how do I configure Y?"

The existing `_partition_feedback_artifacts` hard partition and its helpers are removed.

## Requirements

1. In the `code_ask` result fusion path, after the reranker produces the final ranked pool, a demotion multiplier is applied to `score` for results in demoted source zones, but only when `question_type == "explanatory"`.
2. Demotion multipliers (four tiers):
   - `docs/plans/` (staged, pre-admission drafts): **0.60×**
   - `docs/waves/` (historical change docs): **0.75×**
   - Seeds (`kind == "seed"` or path under `.wavefoundry/framework/seeds/`): **0.60×**
   - Journals / feedback / reports (path containing `"journals"`, `"reports"`, or filename containing `"feedback"` or `"journal"`): **0.50×**
3. Architecture docs (`docs/architecture/`), prompts (`docs/prompts/`), reference docs (`docs/references/`), and implementation code are **not** demoted.
4. For `question_type == "navigational"` and `"instructional"`, no demotion is applied — seeds and journals are often the right answer for those query types.
5. After applying multipliers, the pool is re-sorted by descending `score`.
6. `demotion_count` in the `code_ask` response reflects the number of results whose score was reduced.
7. `_partition_feedback_artifacts`, `_is_code_ask_demoted_artifact`, `_is_feedback_artifact`, `CODE_ASK_FEEDBACK_PATH_SEGMENTS`, and `CODE_ASK_FEEDBACK_KINDS` are removed. All demotion logic lives in the new helper.

## Scope

**Problem statement:** The existing hard binary partition is too blunt (fires for all question types, buries high-scoring journals for behavioral questions) and incomplete (wave/plan docs not covered). A calibrated four-tier weighted system is more principled and covers all demoted source types.

**In scope:**

- Replace `_partition_feedback_artifacts` with `_demote_doc_results(results, question_type)` in `server.py`
- Four demotion tiers: plans 0.60×, waves 0.75×, seeds 0.60×, journals 0.50×
- Explanatory queries only
- Remove `_partition_feedback_artifacts`, `_is_code_ask_demoted_artifact`, `_is_feedback_artifact`, `CODE_ASK_FEEDBACK_PATH_SEGMENTS`, `CODE_ASK_FEEDBACK_KINDS`
- Update `partition_applied` and `demotion_count` response fields
- Unit tests for all four tiers and the navigational/instructional passthrough

**Out of scope:**

- Demotion in `docs_search` or `code_search` standalone tools
- Changing the reranker or RRF weights
- Chunker or index changes

## Acceptance Criteria

- AC-1: For an explanatory question naming a function that exists in both a wave change doc and as an implementation chunk, the implementation chunk ranks above the change doc.
- AC-2: `docs/plans/` results have score × 0.60 when `question_type == "explanatory"`.
- AC-3: `docs/waves/` results have score × 0.75 when `question_type == "explanatory"`.
- AC-4: Seed results (`kind == "seed"`) have score × 0.60 when `question_type == "explanatory"`.
- AC-5: Journal/feedback/report results have score × 0.50 when `question_type == "explanatory"`.
- AC-6: No demotion is applied when `question_type` is `"navigational"` or `"instructional"`.
- AC-7: Architecture docs, prompts, reference docs, and code chunks are not demoted regardless of question type.
- AC-8: `_partition_feedback_artifacts`, `_is_code_ask_demoted_artifact`, `_is_feedback_artifact`, `CODE_ASK_FEEDBACK_PATH_SEGMENTS`, and `CODE_ASK_FEEDBACK_KINDS` no longer exist in `server.py`.
- AC-9: `demotion_count` reflects the number of results whose score was reduced.
- AC-10: All existing tests pass.

## Tasks

- In `server.py`, add `_demote_doc_results(results: list[dict], question_type: str) -> tuple[list[dict], int]`:
  - Returns `(results, 0)` unchanged unless `question_type == "explanatory"`
  - For each result, determine demotion tier by checking `result.get("path", "")` and `result.get("kind", "")`:
    - Path starts with `"docs/plans/"` → × 0.60
    - Path starts with `"docs/waves/"` → × 0.75
    - `kind == "seed"` or path starts with `".wavefoundry/framework/seeds/"` → × 0.60
    - Path parts contain `"journals"` or `"reports"`, or filename contains `"feedback"` or `"journal"` → × 0.50
    - Otherwise → no change
  - Multiply `result["score"]` by the tier weight; count demoted results
  - Re-sort `results` by `score` descending
  - Return `(results, demotion_count)`
- Replace the `_partition_feedback_artifacts(broad_hits)` call in `code_ask` with `_demote_doc_results(broad_hits, question_type)`; wire `demotion_count` into response
- Remove `_partition_feedback_artifacts`, `_is_code_ask_demoted_artifact`, `_is_feedback_artifact`, `CODE_ASK_FEEDBACK_PATH_SEGMENTS`, `CODE_ASK_FEEDBACK_KINDS`
- Remove `partition_reason` field from citation dicts (or update to reflect tier name rather than binary "feedback"/"seed")
- Add unit tests:
  - `test_demote_waves_explanatory`: × 0.75 applied
  - `test_demote_plans_explanatory`: × 0.60 applied
  - `test_demote_seeds_explanatory`: × 0.60 applied
  - `test_demote_journals_explanatory`: × 0.50 applied
  - `test_demote_navigational_passthrough`: no demotion for navigational
  - `test_demote_architecture_not_demoted`: architecture docs unaffected
  - `test_demote_count_accurate`: demotion_count matches number of modified results

## Agent Execution Graph

| Workstream     | Owner              | Depends On    | Notes                                              |
| -------------- | ------------------ | ------------- | -------------------------------------------------- |
| server-demote  | framework-engineer | —             | _demote_doc_results + wiring + removal of old code |
| tests          | framework-engineer | server-demote | Unit tests for all four tiers                      |

## Serialization Points

- None — single file change in server.py

## Affected Architecture Docs

N/A — confined to `code_ask` result fusion in `server.py`; no boundary, data-flow, or index impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     |           |
| AC-2 | required     |           |
| AC-3 | required     |           |
| AC-4 | required     |           |
| AC-5 | required     |           |
| AC-6 | required     |           |
| AC-7 | required     |           |
| AC-8 | required     | Hard partition removal is the whole point of this change |
| AC-9 | nice-to-have |           |
| AC-10 | required    |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Implemented. Replaced `_partition_feedback_artifacts` hard partition with `_demote_doc_results` four-tier weighted demotion (waves 0.75×, plans 0.60×, seeds 0.60×, journals 0.50×, explanatory-only). Removed `_is_feedback_artifact`, `_is_code_ask_demoted_artifact`, `_partition_feedback_artifacts`, `CODE_ASK_FEEDBACK_PATH_SEGMENTS`, `CODE_ASK_FEEDBACK_KINDS`. Updated existing demotion tests; added 7 new unit tests for all four tiers and passthrough cases. 1337 tests pass. | `run_tests.py` OK |
| 2026-05-18 | Post-fix live calibration (6 queries via `code_ask`). Results: `_rrf_merge` — impl now rank 1 (0.848) vs wave doc 0.750 post-demotion ✅ fixed. `_create_fts_index` — impl rank 1 (1.000), wave doc 0.679 ✅. `_stream_embed_write` — impl rank 1 (1.000), wave doc 0.688 ✅. `_lance_incremental_write` — impl rank 1 (1.000), wave doc 0.658 ✅. `_embed_query` — wave doc absent from top 7 (demotion effective); arch doc now leads at 1.000 (valid answer for query-behavior question); impl still absent (retrieval gap, not a demotion failure). `_rerank` normalize — wave docs at 0.750 post-demotion still lead; impl absent from pool (retrieval gap addressed by 12q63 injection, but reranker scores prose above code for this query — see 12q63 AC-1 status). | `code_ask` live run |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-18 | Four tiers: plans 0.60×, waves 0.75×, seeds 0.60×, journals 0.50× | All weights calibrated from live query data (see Calibration Data below). Binding constraints: wave docs w < 0.818; seeds w must put 0.886-scoring seed below 1.0 implementation; journals w must put 1.0-scoring journal below 0.828 README while still surfacing it. | Single tier for all (loses source-type distinctions); hard partition (too blunt, question-type-blind) |
| 2026-05-18 | Explanatory only | Navigational/instructional queries legitimately target journals and seeds ("where is the wave-coordinator journal?", "how do I configure X per the seed?") | Demote for all question types (buries correct answers for navigational queries) |
| 2026-05-18 | Apply to post-rerank cross-encoder scores, re-sort | Post-rerank scores are normalized [0,1] and directly comparable to calibration data; consistent with where existing partition fires | Apply before reranker |
| 2026-05-18 | Remove hard partition entirely | Unified system is simpler, more principled, and covers all source types; no reason to maintain two competing demotion mechanisms | Keep hard partition as safety net (contradicts weighted system) |
| 2026-05-18 | Journals at 0.50× (most aggressive) | Journals are observational session notes — rarely implementation ground truth; calibration: journal at 1.0 → 0.50, stays below README at 0.828 but still surfaces at rank 3 | 0.60× (less aggressive; journal at 0.6 could beat a weak implementation at 0.55) |
| 2026-05-18 | Seeds at 0.60× (same as plans) | Seeds are authoritative on framework behavior but not code implementation; calibration: seed at 0.886 × 0.60 = 0.532, safely below 1.0 implementation; 0.60× allows seeds to outrank weak implementations (score < 0.532), which is appropriate when they are the only signal | 0.50× (too aggressive for authoritative framework docs) |

### Calibration Data (2026-05-18)

**Wave/plan tier** — 6 explanatory queries, post-rerank cross-encoder scores:

| Query symbol | Top wave doc score | Implementation score | Impl rank | Outcome |
| --- | --- | --- | --- | --- |
| `_rrf_merge` | 1.000 | 0.893 | 6/7 | ❌ wave wins — fixed by 0.75× (→ 0.750 < 0.893) |
| `_create_fts_index` | 0.872 | 1.000 | 1/7 | ✅ impl already #1 |
| `_stream_embed_write` | 0.893 | 1.000 | 1/7 | ✅ impl already #1 |
| `_rerank` normalize | 1.000 | absent | — | ⚠️ retrieval gap — addressed by 12q63 |
| `_embed_query` | 1.000 | 0.818 | 6/7 | ❌ wave wins — fixed by 0.75× (→ 0.750 < 0.818) |
| `_lance_incremental_write` | 0.976 | 1.000 | 1/7 | ✅ impl already #1 |

Binding constraint: w < 0.818. Chosen 0.75× leaves 6.8-point margin.

**Seed tier** — `_build_index_locked` explanatory query:

| Source | Score | Post 0.60× | Competing impl | Outcome |
| --- | --- | --- | --- | --- |
| `140-reindex-ongoing` seed | 0.886 | 0.532 | 1.000 | ✅ safely below impl |

**Journal tier** — wave-coordinator stage gate query:

| Source | Score | Post 0.50× | Best non-demoted | Outcome |
| --- | --- | --- | --- | --- |
| `wave-coordinator.md` journal | 1.000 | 0.500 | 0.828 (README) | ✅ below README; surfaces at rank 3 |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Demotion too aggressive — valid wave doc suppressed | 0.75× is a soft nudge; wave docs remain in pool and can still rank above code if no implementation chunk competes |
| Journal 0.50× buries the only relevant source | 0.50× demotes but does not exclude; at score 1.0 → 0.50, journal still surfaces in top-3 unless 2+ non-demoted sources score above 0.50 |
| Seed 0.60× wrong for a highly relevant seed | Seeds can still outrank implementation chunks scoring below 0.60× × seed_score; appropriate when seed is the only signal |
| Removing hard partition leaves a gap if tier logic has a bug | Unit tests cover all four tiers explicitly; `demotion_count` field provides observability |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
