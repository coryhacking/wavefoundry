# Memory eval scores situation-language queries against baselines

Change ID: `245sp-enh memory-eval-situation-queries-and-baselines`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-23
Wave: 245na memory-eval-production-path

## Rationale

`wf_memory_eval` cannot say whether memory retrieval helps in this repository. Its curated pass queries up to 12 sampled records with each record's own summary. That is a near-duplicate lookup, so it measures the index round trip rather than retrieval. The research assessment explains why such probes inflate scores and can reorder systems ([assessment, "Evaluation: the current design measures the index, not the memory"](../../arcs/244cm%20memory-quality/research/agent-memory-systems-assessment.md)). The same pass labels a production variant (`memory_rrf_summary5`) that it never runs, and its experimental row measures policy order instead of relevance. Superseded spec `243hz-bug memory-eval-measures-production-path` diagnosed both defects against `.wavefoundry/framework/scripts/memory_eval.py` and `.wavefoundry/framework/scripts/wf_server/memory_handlers.py` on 2026-11-23. Its Rationale and Progress Log hold the evidence, and this spec carries its two fixes.

The evaluation is the first wave of arc `244cm-arc memory-quality`. Later waves change indexing freshness, admission and maintenance, and each one needs a measurement that can show whether it helped. The arc pauses retrieval-stack investment until production retrieval is shown to beat the grep, BM25-only and full-context baselines. This spec produces the report the operator reads to make that call; it decides nothing automatically.

**Kind: `enh`.** The frozen query set, the baseline arms and the index signals are new capability. The production-row fix inherited from `243hz` is a bug fix, carried here because both rows share one report.

## Product Intent

**Who benefits:** maintainers and agents who decide whether to change memory admission, indexing, maintenance or retrieval, and who need a number that reflects what an agent would see.

**Before:** the report's only query source is each record's own summary. No baseline exists, so a high score cannot be compared with grep or with loading every record. The headline label names a production path that the pass never ran.

**After:** the curated pass scores a frozen, independently authored set of situation-language queries. The set includes null queries, where the right answer is nothing, and stale cases, where a retired record coexists with its successor. Every arm ranks the same corpus and is scored on the same cases: no memory, grep, BM25-only, dense-only, hybrid without rerank, the production `memory_search` path and full context. The report leads with recall@5 and MRR, then precision of the shown set, false-show rate and stale-shown rate, each with a cluster bootstrap interval. An arm that shows few records cannot read as better than BM25 while recalling less. The report also carries memory index signals: vector coverage that separates stale from missing sources, and whether each record is reachable by its own target path. The self-summary probe survives only as a labeled sanity floor.

**Boundary:** measurement only. The report makes no adoption or pause decision; lifting the retrieval-stack pause is the operator's decision, made from this report. Production ranking, `memory_policy_sort_key`, `_memory_query_records`, `memory_search_response`, `lexical_bm25_order`, `reciprocal_rank_fusion`, the indexer and the hermetic `run()` pass are unchanged. MCP output stays aggregate-only. The downstream task-outcome tier (assessment tier four) is out of scope.

**First outcome:** a maintainer calls `wf_memory_eval` on this repository with a current index and reads the held-out metrics of every arm, production included, with intervals (AC-13). A run whose production arm fell back does not count as that outcome.

## Requirements

1. The curated pass reads a project query set from `docs/evals/memory-query-set.json` and its freeze record from `docs/evals/memory-query-set.lock.json`. When the query set is absent, the report sets `query_set.available: false` with `query_set.reason: "query_set_absent"`, and only the sanity floor is computed.
1. Each case has a stable `id`, a `query`, a `case_type` of `answerable`, `null` or `stale`, a `source_id`, `relevant_ids` (empty for `null`), `stale_ids` (nonempty for `stale`, empty otherwise), `grep_terms` and an `author` field naming the authoring agent and model.
   1. `source_id` is the memory id the query was authored for. For a null case it equals the case `id`.
   1. `grep_terms` is required on every case, null and stale cases included: 1 to 3 terms, the plausible search a user would type for that query. The loader refuses a set in which any case lacks it, with `unavailable_reason: "query_set_invalid"`.
1. The split is derived per record, not per case. Every case's cluster key is its `source_id`, and a cluster is `heldout` when `int(sha256(source_id)[:8], 16) % 10 >= 3`, and `dev` otherwise. All cases of one record therefore fall in one split. A case-level `split` field, if present, is ignored.
1. The freeze hash is the SHA-256 of the canonical JSON of the parsed query set (`sort_keys=True`, separators `(",", ":")`, `ensure_ascii=False`). It is not a hash of the file bytes, so a checkout with CRLF line endings yields the same hash. When the computed hash differs from the lock's `query_set_sha256`, the report sets `available: false` and `unavailable_reason: "query_set_hash_mismatch"`, and carries no `metrics` key.
1. The run-time leakage filter excludes a case when `difflib.SequenceMatcher(None, query.lower(), summary.lower()).ratio()` is 0.9 or higher for the summary of any record in its `relevant_ids`. The report counts exclusions in `query_set.leakage_rejected`.
1. A freeze command, `memory_eval.py --freeze-query-set <root>`, applies the sequence filter. It also embeds each query and each relevant record's summary with the docs model and records each case's maximum cosine. Cases at 0.95 or higher are excluded at run time by reading the lock; the query file is not rewritten. The lock holds `query_set_sha256`, `docs_model`, `sequence_ratio_threshold: 0.9`, `cosine_threshold: 0.95`, `sequence_rejected` and `cosine_rejected`, listing excluded cases by case id, never by query text. When the embedding model is unavailable, the command exits 2 and writes nothing, with the message `freeze requires the docs embedding model`.
1. Every arm ranks the same corpus: the records `memory_search_response` ranks for a query, which are the surfaced records plus the archive register entries. Each arm yields, per case, a ranked list and a shown set:
   1. `no_memory`: both empty.
   1. `grep`: the corpus items whose text contains every `grep_terms` entry, case-insensitively, ranked by total occurrence count descending, then memory id. A record's text is its file; a register entry's text is its register section. The shown set is every match.
   1. `bm25_only`: `lexical_bm25_order(corpus, query)[:MEMORY_QUERY_CHECK_CAP]`, ranked and shown.
   1. `dense_only`: the order of `WaveIndex._memory_candidate_scores(query, body_paths, expected_hashes=...)`, called with the same body paths and source hashes that `_memory_query_records` builds, top `MEMORY_QUERY_CHECK_CAP`, ranked and shown. No arm calls `index.search_docs` or `_semantic_order`.
   1. `hybrid_no_rerank`: `reciprocal_rank_fusion([semantic, lexical[:MEMORY_SEARCH_CAP]])[:MEMORY_QUERY_CHECK_CAP]`, where `semantic` is the `dense_only` stream before the cut. This equals production's candidate order before the reranker screen, so the difference from `production` isolates the reranker.
   1. `production`: the record order returned by `memory_handlers.memory_search_response(root, query=<case query>, index=<index>, limit=MEMORY_QUERY_CHECK_CAP)`, ranked and shown.
   1. `full_context`: every corpus item, ranked by memory id, and all of them shown.
1. Metrics per arm and split, in this order, rounded to 4 decimal places:
   1. `recall_at_5`: over answerable and stale cases, the mean fraction of `relevant_ids` in the first 5 ranked records.
   1. `mrr`: over answerable and stale cases, the mean of 1/rank of the first relevant record, with 0 when none is ranked.
   1. `precision_shown`: pooled over answerable and stale cases, relevant shown records divided by all shown records. It is `null` when nothing is shown.
   1. `false_show_rate`: over null cases, the fraction with a nonempty shown set.
   1. `stale_shown_rate`: over stale cases, the fraction whose shown set contains any `stale_ids` entry.
   1. `mean_shown`: the mean shown-set size over all cases, which states the cost of an arm such as `full_context`.
1. Each metric except `mean_shown` carries a 95% cluster bootstrap interval:
   1. One resample draws as many clusters as the split holds, with replacement, from that split's clusters, using one `random.Random(0)` per split and metric. There are 1000 resamples.
   1. The metric is recomputed over every case of the drawn clusters, a cluster drawn twice counting twice.
   1. A resample in which the metric is undefined (no eligible case, or nothing shown for `precision_shown`) is skipped and counted in `undefined_resamples`.
   1. With `v` the sorted defined values and `n = len(v)`, the interval is `[v[floor(0.025 * n)], v[ceil(0.975 * n) - 1]]`, which is `[v[25], v[974]]` when `n` is 1000. When `n` is below 100, the interval is `null`.
1. The report ranks arms per split by `recall_at_5`, then `mrr`, both descending, in `arm_order`. An arm whose `recall_at_5` interval upper bound is below `bm25_only`'s `recall_at_5` point value carries `flags: ["recall_below_bm25"]`. No field states that one arm beats another, and the report carries no pause or adoption verdict.
1. The production row keeps `243hz`'s screening rule. The report carries `production_retrieval` with `model_screened_probes`, `fallback_probes` and `fallback_reasons` (sorted by key). When `fallback_probes` is above 0, the `production` arm is omitted from every split's metrics, and the report sets `production_measured: false` and `production_unavailable_reason: "production_path_fell_back"`. Otherwise `production_measured` is `true`.
1. `run_curated` accepts an optional `index`. `wf_memory_eval_response` passes one, and the `wf_memory_eval` handler in `server_impl.py` passes `get_handler().index`, the same object that the `memory_search` handler passes. With `index=None`, `run_curated` constructs `WaveIndex(root)`, so the CLI keeps working.
1. Two embedded-text ablation arms are informational. `dense_summary_only` ranks by the cosine of the query embedding against each record's summary embedding. `dense_compact` uses the title, summary, target paths and keywords joined by newlines. Both are computed in-process through `WaveIndex._get_embedder(DOCS_MODEL)` and never write the index. The report records `embedded_text` as `{"dense": "record_markdown_chunks", "lexical": "summary_title_evidence_targets_keywords", "screen": "summary"}`, which describes current production behavior.
1. The report names `embedded_text_preferred` by one rule: among `dense_only`, `dense_summary_only` and `dense_compact`, the arm with the highest held-out `recall_at_5`; on an equal value at 4 decimal places, the arm whose embedded text has the smallest mean character count. The field changes nothing; a later indexer spec acts on it. The report notes that the ablations use one vector per record, while `dense_only` uses the best chunk per record, so the comparison mixes text choice with chunking.
1. The curated experimental rows bound each stream before `_policy_order`. `candidate` policy-orders `reciprocal_rank_fusion([lexical[:MEMORY_SEARCH_CAP], semantic])[:MEMORY_QUERY_CHECK_CAP]`. `lexical_only` policy-orders `lexical[:MEMORY_QUERY_CHECK_CAP]`. `semantic_only` policy-orders `semantic[:MEMORY_QUERY_CHECK_CAP]`. The caps come from `memory_handlers`. The bound applies only to the curated pass, and `run()` keeps its unbounded behavior.
1. Labels: `production_variant: "memory_search_hybrid_rrf"`, `experimental_variant: "policy_ordered_rrf_shortlist5"`, `baseline_variant: "legacy_policy_ordering"`, `headline_variant: "production"` and `headline_split: "heldout"`. The string `memory_rrf_summary5` no longer appears.
1. The existing 12-record self-summary sample moves under `sanity_floor`, with `label: "self_summary_sanity_floor"` and `headline: false`.
1. The report carries `index_signals`:
   1. `memory_vector_coverage`: `requested_paths`, `covered_paths`, `stale_paths` and `missing_paths` over every surfaced record body path. A path is covered when the docs layer holds chunks for it and its `layer_path_state` hash equals the current file hash. It is stale when chunks exist and the hash differs. It is missing when no chunks exist. One stale path therefore never zeroes the covered count.
   1. The counts come from a model-free helper, `memory_vector_coverage(index_dir, layer, expected_hashes)` in `sqlite_vector_store.py`, that reads `chunks_docs` and `layer_path_state` and embeds nothing. Track 2 of the arc reuses it from `index_health`.
   1. `target_retrievable`: `records_with_file_targets`, `retrievable` and `crowded_past_search_cap`. A record is retrievable when `memory_records.match_targets` matches it for at least one of its file targets, the same predicate `memory_search_response` filters with, applied with no result cap. It is crowded when `memory_search_response(root, target=<path>, index=<index>, limit=MEMORY_SEARCH_CAP)` returns it for none of its file targets. `symbol:` and `community:` refs are not file targets.
1. The report never carries query text, record bodies, summaries, memory ids, target refs or case ids. An exception in any arm is not echoed. The report sets `available: false` with an `unavailable_reason` that names the arm, for example `"production query measurement unavailable"`.
1. `qualifying: false` and `adoption_gate` stay unchanged. This report does not qualify a ranking change under the qualification contract in `docs/references/memory-retrieval-eval.md`.

## Scope

**Problem statement:** the memory eval measures an index round trip with self-summary probes, has no baselines, and mislabels a production variant it never runs.

**In scope:**

- The query-set schema, loader, record-level split, freeze command, hash check and both leakage filters.
- The seven arms over one corpus, the two ablation arms, the metrics, the cluster bootstrap and the recall-first arm order.
- The production row and bounded experimental rows carried from `243hz`, and the shared-index plumbing.
- The model-free coverage helper, the memory index signals and the sanity floor.
- Authoring, spot-checking and freezing this repository's query set under the rules in Tasks.
- Tests, the handler-digest fixture, the tool-surface contract, the eval reference, the search-architecture and testing-architecture docs, and CHANGELOG entries.

**Out of scope:**

- Any automatic pause, adoption or "beats" verdict. The operator decides from the report.
- Any change to production ranking, indexing or the text the indexer embeds. A change chosen from `embedded_text_preferred` is a later spec.
- Index freshness repair after a git pull and memory coverage in `index_health` (arc track 2), admission hardening (track 3) and target revalidation (track 4).
- The downstream paired task suite (assessment tier four) and an LLM-judged full-context arm.
- The tool's input schema. `tool-surface-golden.json` and `tool-surface-golden/declared.json` pin annotations, input schema and tier for `wf_memory_eval`, and none of them change.
- The hermetic `run()` pass and its recorded fusion-gate values.

## Acceptance Criteria

- [ ] AC-1: The metrics and fixed baselines score as defined on one fixture. The corpus is active records `r1` to `r5` plus register entry `r9`. The six cases are all held out, because their `source_id` values `r1`, `r2`, `r4`, `q-004` and `q-005` hash to held out:
   1. `q-001` answerable, source `r1`, relevant `r1`, ranked and shown `[r1, r2]`.
   1. `q-002` answerable, source `r2`, relevant `r2`, ranked and shown `[r3, r2]`.
   1. `q-003` answerable, source `r4`, relevant `r4`, ranked and shown `[r1]`.
   1. `q-004` null, shown `[]`.
   1. `q-005` null, shown `[r5]`.
   1. `q-006` stale, source `r2`, relevant `r2`, stale `r9`, ranked and shown `[r9, r2]`.
   The scorer returns `recall_at_5` 0.75, `mrr` 0.5, `precision_shown` 0.4286, `false_show_rate` 0.5 and `stale_shown_rate` 1.0. On the same cases, `full_context` returns 1.0, 0.5625, 0.1667, 1.0 and 1.0 with `mean_shown` 6.0, and `no_memory` returns 0.0, 0.0, `null`, 0.0 and 0.0. When `q-004` carries `grep_terms: ["lockfile"]`, and `r1`'s file contains that term twice and `r3`'s once, `grep` ranks `[r1, r3]` for `q-004`, shows both, and its `false_show_rate` is 1.0 on a split holding only `q-004`.
- [ ] AC-2: The cluster bootstrap is pinned and cannot be faked. Two runs on the AC-1 fixture return identical intervals. On that fixture the `mrr` interval satisfies `low < 0.5 < high`; the test fails when the bootstrap is replaced by one returning `[point, point]`, and the implementer records that failing run in the Progress Log. A fixture whose every case has reciprocal rank 1.0 returns `[1.0, 1.0]`. A fixture with one answerable cluster and one null cluster reports `undefined_resamples` above 0 for `recall_at_5`.
- [ ] AC-3: The sequence leakage filter excludes a near-copy, and removing it is detected. A case whose query equals its relevant record's summary is excluded, with `query_set.leakage_rejected` equal to 1. A case with the query `"setup reports the package installed but the new API import fails after upgrade"` against the summary of the AC-1 fixture's `r1` is scored. With the filter call removed, the test fails because `leakage_rejected` is 0; the implementer records that failing run in the Progress Log.
- [ ] AC-4: The freeze binds the scored set. After a fixture set is frozen, editing one query yields `available: false`, `unavailable_reason: "query_set_hash_mismatch"` and no `metrics` key. Rewriting the unedited file with CRLF line endings yields the same `query_set_sha256`. With a stub embedder that gives one case cosine 0.97 against its relevant summary, the lock records that case id in `cosine_rejected`, and the next run excludes it. With no embedding model, the command exits 2, prints `freeze requires the docs embedding model` and writes no lock. A set in which one case lacks `grep_terms` yields `unavailable_reason: "query_set_invalid"`.
- [ ] AC-5: The split keeps each record's cases together. Cases `q-001` and `q-002`, whose own ids hash to held out, both carry `source_id` `r3`, which hashes to dev; both land in `dev`. A null case `n-001` lands in `dev` and `n-005` in `heldout`, by their own ids. The report carries metrics under both `heldout` and `dev`, and `headline_split` is `"heldout"`. With the split keyed on case id instead, the test fails.
- [ ] AC-6: The production arm runs the production path with the shared index. A test stubs `memory_handlers.memory_search_response` and runs `run_curated` on a fixture with 4 scored cases and a supplied stub index. The recorder sees 4 query calls, each passing the supplied index object (`is`), the case's query and `limit` equal to `MEMORY_QUERY_CHECK_CAP`. A second test drives the registered `wf_memory_eval` handler with a handler whose `index` is a sentinel, and a spy on `run_curated` receives that sentinel. A direct call with `index=None` constructs `WaveIndex(root)`, proved by a stubbed `WaveIndex` that records its construction.
- [ ] AC-7: A fallen-back production arm is reported as not measured. When the stub returns `qualification: "unavailable"` with `fallback_reason: "memory_vector_coverage_incomplete"` for 1 of 4 cases, the report has no `production` arm under any split, `production_measured` is `false`, `production_unavailable_reason` is `"production_path_fell_back"`, and `production_retrieval` is `{"model_screened_probes": 3, "fallback_probes": 1, "fallback_reasons": {"memory_vector_coverage_incomplete": 1}}`.
- [ ] AC-8: The arms share production's corpus and dense stream. With a spy on `WaveIndex.search_docs`, a full curated run makes 0 calls to it. `dense_only` and `hybrid_no_rerank` call `_memory_candidate_scores` with the same body paths and expected hashes that `_memory_query_records` builds for the same corpus. On a fixture where register entry `r9` matches a case's `grep_terms` and BM25 tokens, `grep`, `bm25_only` and `full_context` each show `r9`.
- [ ] AC-9: The bounded experimental row measures relevance, and removing the bound is detected. The fixture has a probe record at BM25 rank 1 and an empty semantic stream. It has at least 4 decoys at BM25 positions 6 and beyond that sort ahead of the probe under `memory_policy_sort_key`, and fillers at positions 2 to 5 that sort behind it. The curated `candidate` and `lexical_only` rankings place the probe first. With the unbounded `lexical_bm25_order` list passed to `_policy_order`, as on 2026-11-23, the probe ranks 5th or lower and the test fails; the implementer records that failing run in the Progress Log.
- [ ] AC-10: The index signals separate stale from missing and need no model. With an embedder stub that raises on any call, `memory_vector_coverage` on a 4-path fixture returns `{"requested_paths": 4, "covered_paths": 4, "stale_paths": 0, "missing_paths": 0}` when all sources are fresh. It returns `{"requested_paths": 4, "covered_paths": 3, "stale_paths": 1, "missing_paths": 0}` after one source file changes, and `{"requested_paths": 4, "covered_paths": 3, "stale_paths": 0, "missing_paths": 1}` when one path has no chunks. On a fixture where 21 records share one file target, `target_retrievable` reports `records_with_file_targets` 21, `retrievable` 21 and `crowded_past_search_cap` 1.
- [ ] AC-11: An arm that abstains cannot read as better than BM25. On a held-out fixture of 10 clusters with one answerable case each, production shows only the relevant record in 1 case and nothing in the other 9, while `bm25_only` shows 5 records with the relevant one in 6 cases. The report gives production `recall_at_5` 0.1 and `precision_shown` 1.0, and `bm25_only` `recall_at_5` 0.6 and `precision_shown` 0.12. `arm_order` lists `bm25_only` before `production`, and production carries `flags: ["recall_below_bm25"]`. No report key contains `beats` or `pause`, and no key other than the unchanged `adoption_gate` contains `gate`.
- [ ] AC-12: Labels, the sanity floor and the privacy boundary hold. The report carries the five labels in Requirement 16, and `sanity_floor.label` is `"self_summary_sanity_floor"` with `headline: false`. The string `memory_rrf_summary5` appears nowhere in `memory_eval.py` or the report. A walk of the whole available-path envelope finds none of the keys `memory_id`, `summary`, `records`, `target_refs`, `body`, `query` or `case_id`, and no fixture query, summary or case id as any value. A stubbed production call that raises an exception carrying a summary yields `available: false` and `unavailable_reason: "production query measurement unavailable"`, and that summary appears nowhere in the envelope.
- [ ] AC-13: This repository's query set is authored, spot-checked and scored with production measured. `docs/evals/memory-query-set.json` holds at least 2 answerable cases for each active record that has a file target and a summary, at least 40 null cases and 1 stale case for each archive register entry that names a successor, and every case carries `grep_terms`. The Progress Log records the operator's spot-check of about 10 cases before the freeze, with its outcome. The lock records both filters. After an MCP restart, and with `index_health` reporting the docs layer current, `wf_memory_eval` returns `available: true`, `production_measured: true` and `production_retrieval.fallback_probes` 0. The implementer records the held-out metrics, intervals, `arm_order`, `embedded_text_preferred` and `index_signals` in the Progress Log. A run with `production_measured: false` does not satisfy this AC.
- [ ] AC-14: Nothing else regresses. `run()` on the golden fixture returns the same metrics and invariant results before and after the change, compared as sorted JSON. The change's own suites and every test it adds pass. The documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Add the query-set loader, `grep_terms` and `source_id` validation, record-level split, canonical hash check and sequence leakage filter to `memory_eval.py`.
- [ ] Add the `--freeze-query-set` command with the cosine filter and lock writer.
- [ ] Add the seven arms over production's corpus, the two ablation arms, the metrics, the cluster bootstrap, `arm_order`, the `recall_below_bm25` flag and `embedded_text_preferred`.
- [ ] Add the production arm, `production_retrieval`, `production_measured` and the all-screened rule, and pass the shared index from the `wf_memory_eval` handler.
- [ ] Bound the curated experimental streams and rename the labels.
- [ ] Add the model-free `memory_vector_coverage` helper to `sqlite_vector_store.py`, the `index_signals` section and the `sanity_floor` section.
- [ ] Write the AC-1 to AC-12 and AC-14 tests in `tests/test_memory_eval.py`, and record the AC-2, AC-3 and AC-9 known-bad runs in the Progress Log.
- [ ] Refresh `register-surface-handler-digests.json` for the changed `wf_memory_eval` handler.
- [ ] Author this repository's query set under the authoring rules below.
- [ ] Ask the operator to spot-check about 10 cases before the freeze, fix or drop the cases the operator rejects, and record the outcome in the Progress Log.
- [ ] Freeze the query set.
- [ ] Rewrite the `wf_memory_eval` response field list in `docs/specs/mcp-tool-surface.md` (`query_set`, `metrics` per split and arm, `arm_order`, `production_retrieval`, `production_measured`, `index_signals`, `embedded_text`, `embedded_text_preferred`, `sanity_floor`), and drop "sampled self-summary" from that section's first sentence. Keep the Tool Index line.
- [ ] Update the curated sections of `docs/references/memory-retrieval-eval.md`, the memory-evaluator sentence in `docs/architecture/search-architecture.md`, and the memory-retrieval row of `docs/architecture/testing-architecture.md`.
- [ ] Add a `### Added` entry under `## [Unreleased]` in `CHANGELOG.md`. Draft: "`wf_memory_eval` now scores a frozen set of situation-language queries, with null and stale cases, against no-memory, grep, BM25-only, dense-only, hybrid, production and full-context baselines over one corpus. The report leads with recall@5 and MRR, then precision of the shown set, false-show rate and stale-shown rate, each with a bootstrap interval that resamples records. It also reports memory vector coverage, separating stale from missing sources, and records that their own target path cannot reach."
- [ ] Add a `### Changed` entry under `## [Unreleased]` in `CHANGELOG.md`. Draft: "`wf_memory_eval` labels are renamed: `production_variant` is now `memory_search_hybrid_rrf`, because the old `memory_rrf_summary5` named a path the pass never ran, and `experimental_variant` is now `policy_ordered_rrf_shortlist5`. The self-summary sample fields move under `sanity_floor`, which is never the headline."
- [ ] After an MCP restart, run `wf_memory_eval` on this repository and record the AC-13 values in the Progress Log.

### Query-set authoring rules

The query set is the main effort, so authoring is one task with these rules:

1. **Author isolation.** An authoring subagent writes queries for one record at a time. It sees the record's kind, target paths, evidence refs and the Rationale of the source change. It never sees the record's title, Summary, Action delta or Validation rationale, so its wording cannot copy the lesson.
1. **Author model.** The authoring model must differ from the model that wrote most records, and the case's `author` field names it. All models available on this host are from one family, so model-family independence is not achievable (operator decision, 2026-11-23).
1. **Situation language.** Each record gets 2 or 3 queries written as what an agent has before it knows the lesson: a task statement, an error or symptom text, and a touched path or diff excerpt. `source_id` names the record.
1. **Grep terms.** Every case, null and stale cases included, carries 1 to 3 `grep_terms`: the plausible search a user would type for that query.
1. **Labeling.** A second agent, independent of the author, labels each query against the target record and the top 10 BM25 and top 10 dense records. It adds every other record that would apply to `relevant_ids`. The labeler may reject a query that no record answers.
1. **Null cases.** At least 40 queries describe plausible work in this repository that no active record addresses. The labeler confirms that no record among the top 10 BM25 and top 10 dense results applies.
1. **Stale cases.** Each archive register entry with a `Successor:` gets one query written for the successor's situation, with `source_id` and `relevant_ids` set to the successor and `stale_ids` set to the archived id.
1. **Operator spot-check.** Before the freeze, the operator reviews about 10 cases, chosen as the 10 lowest `sha256(id)` values, for situation language and leakage. Rejected cases are fixed or dropped, and the outcome goes in the Progress Log.
1. **Freeze before scoring.** The implementer runs `--freeze-query-set` before any arm is scored and before any tuning. After that, only the `dev` split may guide changes, and any edit to the set requires a new freeze with the reason recorded in the Progress Log.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| eval-engine | implementer | none | `memory_eval.py`, `memory_handlers.py`, `server_impl.py`, `sqlite_vector_store.py` |
| tests | implementer | eval-engine | AC-1 to AC-12 and AC-14, digest refresh |
| query-set | implementer | eval-engine | authoring and labeling subagents, operator spot-check, then the freeze command |
| docs | implementer | eval-engine | tool-surface contract, eval reference, search and testing architecture, CHANGELOG |
| live-check | implementer | tests, query-set, docs | MCP restart, `index_health`, then `wf_memory_eval` for AC-13 |

## Serialization Points

- `.wavefoundry/framework/scripts/memory_eval.py`
- `.wavefoundry/framework/scripts/sqlite_vector_store.py`
- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_memory_eval.py`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/evals/memory-query-set.json`
- `docs/evals/memory-query-set.lock.json`
- `docs/specs/mcp-tool-surface.md`
- `docs/references/memory-retrieval-eval.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/testing-architecture.md`
- `CHANGELOG.md`

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`: the sentence "The memory evaluator's sampled self-summary output remains nonqualifying" goes stale. It becomes a statement that the evaluator scores a frozen independent query set, that the self-summary probe is only a sanity floor, and that the report remains nonqualifying.
- `docs/architecture/testing-architecture.md`: the memory-retrieval eval row gains the query set, the baseline arms, the cluster bootstrap and the index signals.

No other architecture doc changes. The eval already imports `memory_handlers` through `server_impl` and reads the index without writing it. The new coverage helper sits beside `dense_path_scores` in `sqlite_vector_store.py` and reads the same tables.

## Platforms

The change is pure Python. It reads two JSON files through `pathlib` as UTF-8 and writes only the lock file, and only from the explicit freeze command.

- **Windows:** the freeze hash covers parsed JSON, so a checkout with `core.autocrlf` producing CRLF files matches the LF lock (AC-4). The lock is written with LF endings through the framework's generated-file writer. Paths in the query set are repo-relative with forward slashes and are compared as POSIX strings. The coverage helper compares source hashes computed on the same machine that built the index, so CRLF checkouts stay consistent. The production arm uses the qualified Tensorwell pair where available, otherwise the CPU fallback. Where neither loads, its probes fall back, `production_measured` is `false` per Requirement 11, and AC-13 is not met on that machine.
- **macOS and Linux:** identical behavior. Apple silicon may serve the docs model through Tensorwell, and the eval reports whichever provider served it.
- **WSL2:** identical to Linux. A checkout under `/mnt/c` reads files more slowly, which lengthens the run but does not change results.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The metric definitions and baselines are the measurement. |
| AC-2 | required | The intervals are the statistical claim; a fake bootstrap must fail. |
| AC-3 | required | Leakage is the defect this spec replaces. |
| AC-4 | required | Freezing prevents silent tuning on the scored set. |
| AC-5 | required | A record-level split keeps dev tuning out of the held-out split. |
| AC-6 | required | The production arm must run the real path with the shared index. |
| AC-7 | required | A fallback must never pass as a measured production number. |
| AC-8 | required | Arms are comparable only on one corpus and the production dense stream. |
| AC-9 | important | The experimental row measures relevance. |
| AC-10 | required | Index signals are part of track 1, and track 2 reuses the helper. |
| AC-11 | required | Abstention must not read as quality. |
| AC-12 | required | Honest labels and the existing privacy boundary. |
| AC-13 | required | Proves the intent: a real query set scored with production measured. |
| AC-14 | required | Guards the hermetic pass and change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-23 | Planned as the first wave of arc `244cm-arc memory-quality`, superseding `243hz`. Code read through `code_search` (healthy, hybrid) plus targeted `sed` reads of `memory_eval.py`, `memory_handlers.py` and `server_impl.py`. On 2026-11-23 this repository has 175 active records and 1 candidate under `docs/agents/memory/`, and 23 archive register entries, all of which name a successor. | `grep` counts on `docs/agents/memory/*.md` and `docs/agents/memory-archive.md`. |
| 2026-11-23 | Readiness repair cycle 1, context `245na-planner-repair-1`. Repair starts recorded for all 7 readiness findings before any edit: `245na-rt-gate-rewards-abstention`, `245na-rt-split-and-resample-unit-is-case`, `245na-cr-grep-null-gate`, `245na-cr-arm-corpus-and-signals`, `245na-qa-bootstrap-untested`, `245na-arch-dense-stream-unspecified` and `245na-qa-ac18-vacuous-live-check`. The spec now drops the automatic gate, leads with recall, splits and resamples by record, pins the bootstrap, puts every arm on production's corpus and dense stream, separates stale from missing coverage, requires a measured production arm in the live run, and merges 20 ACs into 14. Reviewers noted that the corpus now holds 174 active records and no candidate. | `wf_review_event` repair_start records; reviewer notes in `.wavefoundry/work/245na/review/`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-23 | Hash the parsed JSON, not the file bytes. | Windows checkouts may rewrite line endings, and a byte hash would then refuse a valid set. | A byte hash with `.gitattributes` pinning LF. |
| 2026-11-23 | Run the cosine filter only at freeze; run the sequence filter at every run. | Planner default. The sequence filter is deterministic and needs no model. The cosine result is fixed in the lock, so a run does not depend on the model for filtering. | Both filters at run time, which would make availability depend on the model. |
| 2026-11-23 | Define `full_context` as every corpus item shown, ranked by id, and report its `mean_shown`. | Planner default. In retrieval terms, full context shows everything, so it bounds recall and states the cost of showing everything. | An LLM run with all records in the prompt; declined below. |
| 2026-11-23 | Keep the embedded text unchanged and measure it with two in-process ablations. | Planner default within the operator's "decide what text is embedded and evaluate that choice". Dense retrieval already embeds the whole record markdown, which includes the body and target paths. | Change the indexer now; weakness: no evidence yet that it helps here. |
| 2026-11-23 | Accept query authors from the same model family, mitigated: queries are authored in a separate context that never sees the record text, pass the similarity filter, and the operator spot-checks about 10 before the set is frozen. | Operator decision, 2026-11-23. Only one model family is available here. | Require a different model family: declined, not available. |
| 2026-11-23 | Score full context only as "every record shown"; no LLM-judged full-context arm. | Operator decision, 2026-11-23. The shown-all arm already gives the recall bound and the cost of showing everything; a judged arm adds judge variance and cost for a question not yet asked. | An LLM-judged full-context arm: declined. |
| 2026-11-23 | Exclude candidate records from the query set; the eval measures the active corpus. | Operator decision, 2026-11-23. Candidates are short-lived and are validated or rejected; briefings rely on active records. | Author queries for candidates: declined. |
| 2026-11-23 | Remove the automatic retrieval-stack gate. The wave measures only; the report leads with recall@5 and MRR, then precision, false-show and stale-shown, and flags an arm whose recall falls below BM25's. Lifting the retrieval pause is the operator's decision, made from this report. | Coordinator decision, 2026-11-23, reversible, for findings `245na-rt-gate-rewards-abstention` and `245na-cr-grep-null-gate`. The precision-led gate let an arm that shows almost nothing beat BM25 and full context. | A matched-budget gate (red-team proposal); weakness: still an automatic verdict on a decision the operator owns. |
| 2026-11-23 | Require `grep_terms` on every case, null cases included. | Coordinator decision, 2026-11-23, reversible, for `245na-cr-grep-null-gate`. Without terms on null cases, grep's false-show rate is 0 by construction. | Optional terms; weakness: grep's results depend on which cases an author chose to give terms. |
| 2026-11-23 | Split dev and held-out by record, and use a cluster bootstrap that resamples records. | Coordinator decision, 2026-11-23, reversible, for `245na-rt-split-and-resample-unit-is-case`. A case-level split put 109 of 175 records' queries on both sides, and case resampling understates intervals. | Case-level split and resampling. |
| 2026-11-23 | Pin the bootstrap: percentile indexes `floor(0.025n)` and `ceil(0.975n) - 1`, `random.Random(0)`, 1000 resamples, undefined resamples skipped and counted, and a known-bad `[point, point]` AC. | Coordinator decision, 2026-11-23, reversible, for `245na-qa-bootstrap-untested`. A no-op bootstrap passed the earlier ACs. | A literal interval for the fixture; weakness: brittle to the resampling order. |
| 2026-11-23 | Every arm ranks production's corpus, including register entries; `dense_only` and `hybrid_no_rerank` use `_memory_candidate_scores`; target retrievability uses the uncapped `match_targets` predicate and counts crowding separately; coverage comes from a model-free helper that separates stale from missing. | Coordinator decision, 2026-11-23, reversible, for `245na-cr-arm-corpus-and-signals` and `245na-arch-dense-stream-unspecified`. `memory_search_response` caps every result at `MEMORY_SEARCH_CAP` (20), and 28 records share `server_impl.py` as a target, so no call through it covers every record; the uncapped predicate does, and the crowding count keeps the capped view visible. | `memory_search_response(target=...)` with the default limit 10; weakness: cap truncation reads as unretrievable. |
| 2026-11-23 | A fallen-back production arm reports `production_measured: false` with its reason, and the live-run AC fails on it; the operator spot-check moves into the authoring rules, Tasks and AC-13. | Coordinator decision, 2026-11-23, reversible, for `245na-qa-ac18-vacuous-live-check`. | Accept an omitted production arm; weakness: the first outcome would pass with no production number. |
| 2026-11-23 | Store the query set under the existing `docs/evals/` convention as `memory-query-set.json` and its lock. | Coordinator decision, 2026-11-23, reversible, from the architecture advisory. The repository already keeps eval fixtures there, and the docs layer indexes only `.md` files, so neither file enters retrieval. | `docs/references/memory-eval/`, the planner's earlier default. |
| 2026-11-23 | `embedded_text_preferred` picks the highest held-out recall@5, ties to the shortest mean text; it is informational. | Coordinator decision, 2026-11-23, reversible, from the architecture advisory. | No rule; weakness: a later spec could choose after seeing the numbers. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| All available authoring models are from one family, so the queries may match model-written records better in embedding space, which favors dense and production arms over grep and BM25. | Author isolation from the record text, a separate labeler, both leakage filters and the operator spot-check. The eval reference states the limit. |
| The labeler pools only BM25 and dense candidates, so records only grep finds may be labeled irrelevant, which biases against grep. | The limit is stated beside the metrics in the eval reference; pooling grep hits is a candidate refinement if the dev split shows grep-only hits. |
| About 28 held-out null clusters and 16 held-out stale cases give wide intervals. | Intervals are reported, and the report makes no verdict; the operator reads them. |
| A full run makes about 400 production calls, each with up to 5 reranks, so `wf_memory_eval` may take minutes. | The live check records the duration. If it exceeds the MCP call budget, the CLI `--curated-root` path is the documented route. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
