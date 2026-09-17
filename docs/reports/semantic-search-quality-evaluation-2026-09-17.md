# Quality-first code and documentation retrieval evaluation

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Recommendation

Park implementation and keep production retrieval unchanged. Wider retrieval, source context and restrained source/diversity preferences made specific living guidance easier to find, but this does not establish more correctly answered questions. The same changes did not recover the missing code mechanisms. The evidence does not yet justify a new implementation wave or release requirement; latency was not the selection criterion.

The promising outcome is better access to current operational instructions. It is not evidence that a source-path bonus, a two-results-per-file cap, or the memory relevance threshold should become a universal default.

## Method

Eighteen exploratory questions: six code-mechanism questions, six documentation questions, four absent-fact/premise controls, and two history questions. The first twelve came from the earlier probe; six were added before this run. Questions and code-owner checks were coordinator-authored and grounded in current source. This is development evidence, not an independent holdout or release qualification.

The current public `code_search_response` and `docs_search_response` paths supplied the baseline, with five final results and 30 candidates. The existing CPU reranker was pinned across comparisons, with cached models and networking disabled. The eight original answerable questions also ran through unchanged `code_ask_response` as separate controls. No repository runtime code, settings, index contents or model parameters were edited.

| Variant | Change from preceding comparison |
| --- | --- |
| Baseline | Existing 30-candidate public search path. |
| Wide | Increase the candidate window to 90; unchanged reranker input. |
| Hybrid wide | For docs, union the 90 dense candidates with up to 90 FTS candidates using existing RRF; code already uses hybrid retrieval. Score the entire resulting pool. |
| Source context | Prefix existing path and section metadata to the same candidate text before reranking. |
| Current-source preference | Add one raw-logit point to selected source-path classes: Python implementation, canonical seeds and living operational docs. Disable the preference for the two explicitly labeled historical questions. |
| Diversity | Apply a two-results-per-file cap after the preceding ranking. |

Two subsequent, explicitly post-observation ablations tested (a) bounded query reformulation on three misses plus one control, and (b) adding up to 600 characters of the existing Python module docstring across all eight code probes. Neither used an LLM service or modified production search. The history annotation and path preference are experimental fixtures/heuristics, not a tested automatic currentness classifier.

### Contamination control

The first pass retrieved the earlier evaluation report for two repeated questions. That pass is rejected as improvement evidence. The accepted rerun excludes both `docs/reports/semantic-search-quick-evaluation-2026-09-17` artifacts: seven docs chunks and eight code chunks. Each dense/FTS fetch overfetches by the full excluded-row census, filters these paths and then applies its original limit. Thus excluded rows cannot consume a candidate slot or silently shorten a source's prefix. Candidate and public-citation exclusion assertions passed.

The completed index epoch stayed at generation **1546** throughout the accepted comparison. All public baseline/wide calls were successful, reranked and without fallback; their returned ordering matched the captured model-score selection. This is a controlled corpus comparison using public handlers, not an unmodified live-corpus benchmark. The prior report remains in the real repository index.

## Results

The code diagnostic requires an actual code chunk from the known mechanism owner with a relevant symbol/content anchor; a whole-file summary listing a symbol does not count. The docs diagnostic asks whether a specific direct living-guide passage appears in the top five. Those narrower guide predicates were developed during inspection and are retained with the evidence; they are not independent labels or comprehensive answer recall.

| Variant | Known code mechanism in top five, of 6 | Targeted living-guide passage in top five, of 6 |
| --- | ---: | ---: |
| Baseline | 4 | 2 |
| Wide | 4 | 3 |
| Hybrid wide | 4 | 3 |
| Source context | 4 | 3 |
| Current-source preference | 4 | 4 |
| Diversity | 4 | 5 |

The final combination retained both baseline guide hits and added the memory evidence/authority guidance, the Guru caller-versus-reference guidance, and the current 64 MiB spill policy. Several baseline historical passages already supplied useful information, so **2→5 does not mean answer success rose from 2/6 to 5/6**. Intermediate variants lost some targeted guide hits even when their total increased. No single intermediate gain establishes non-regression.

### Code mechanism discovery

- Oversized chunk splitting, combined retrieval, overload-ID disambiguation and package-content verification retain mechanism evidence in the top five across the main comparisons.
- Stale-writer protection and setup reconciliation remain misses under the narrow mechanism criterion. Increasing the pool brings actual `check_ordered` and setup-session code into consideration, but the reranker still prefers adjacent material. The initial pool already contains the index-compatibility module summary; this is partly a selection/representation failure, not simply an absent index entry.
- Adding module docstrings leaves code mechanism coverage at **4/6**. It is not a demonstrated remedy.
- A targeted reformulation of stale-writer protection brings `ensure_runtime_current` to third place in ordinary code search. The setup reformulation still does not locate its reconciliation implementation. The close-wave reformulation returns historical closure examples rather than the procedure. This is a useful agent tactic on one observed miss, not an automatically qualified query-rewriting strategy.

### Documentation and complementary evidence

- Source context moves the Guru's explicit `code_callhierarchy`/`code_references` instructions into the leading results for the graph-navigation question.
- Broader retrieval recovers the living memory-evaluation reference explaining that returned records are evidence, with agent judgment still required. A source preference improves its position without changing the authority of the record.
- The diversity variant admits the framework README's exact retained-memory/spill policy. It also demonstrates the limitation of file caps: multiple passages from one source can answer different parts of a question. Distinct-file counts are not evidence of complementary answer coverage.
- The close-wave question remains poorly served: historical memory/closure discussions outrank the exact closing procedure. A generic source preference is insufficient; authoritative workflow-entry retrieval deserves a focused test.
- Both historical controls retain relevant historical evidence with the preference disabled. Two manually annotated examples do not qualify history-intent detection or establish broad history recall.

### Unsupported facts and public Q&A

Absent-fact controls still require agent interpretation. A model loader does not establish nightly model training, and a benchmark percentage does not establish a universal recall guarantee. Conversely, the architecture's statement that no hosted database is required helps correct the premise of a hosted-price question. These remain separate classes: direct support, supported premise correction, and adjacent material. No automatic abstention or support-verification claim is made.

The eight unchanged `code_ask` controls all succeeded in hybrid/reranked mode and often supplied useful current documentation. They still did not cite the two missing implementation owners for the stale-writer and setup questions. Its larger citation set and distinct selection rules make it an important separate validation surface, not evidence that a `docs_search` improvement automatically transfers to Q&A. Confidence is not a substitute for tracing the cited mechanism.

## If recurring user-visible misses justify revisiting

1. **Current operational documentation retrieval:** test hybrid candidate supply and informative source context, plus intent-sensitive retrieval of the canonical procedure. Judge direct support and retention of existing useful evidence, not only preferred-path counts.
2. **Code mechanism completion:** treat missing owner/leaf evidence as a reason for an agent-directed follow-up using existing exact/structural tools. Test any automatic candidate expansion or code-oriented reranking separately; the generic adjustments here did not establish an improvement.
3. **Complementary evidence selection:** evaluate symbol/section overlap and answer facets before adopting any per-file cap. Preserve supporting passages and historically requested evidence.

Revisit these directions when real queries repeatedly miss current guidance or the correct mechanism, rather than continuing parameter exploration without a demonstrated need. Before implementation, use new independent questions, blind per-record judgments and paired useful-answer retention. Require no lost useful answers and report unsupported tails, premise corrections and currentness separately. Performance remains a secondary constraint.

## Evidence and limits

[Compact evidence bundle](semantic-search-quality-evaluation-2026-09-17.json.gz) retains queries, candidate records, scores/selections, public results, source hashes, checks, the diagnostic scorer and scratch drivers. Repeated records are stored once per query. The earlier contaminated pass is not retained as qualifying data. The scripts contain local paths and require adaptation; no full frozen SQLite database is included. These observed questions are development material for future work.

This is a single-repository, CPU-only exploration using `cross-encoder/ms-marco-MiniLM-L-6-v2`. No blind independent review, GPU/platform qualification, universal recall guarantee, calibrated probability, new model comparison or production adoption is claimed. The closed memory wave and its evidence are unchanged.
