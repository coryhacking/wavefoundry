# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-17

wave-id: `1p66q code-ask-retrieval-quality`
Title: Code Ask Retrieval Quality

## Objective

Act on a ground-truthed `code_ask` quality assessment (C+, bimodal: strong single-source lookups + abstention, a real floor on cross-file/enumeration/freshness). `1p66r` (bug, safety) makes the tool honest — relevance-aware confidence + an abstention path so it stops emitting confidently-wrong citations on zero-signal retrieval, preserving the zero-fabrication citation fidelity. `1p66s` (enh) rebalances retrieval so implementing code surfaces over prose docs for code questions. `1p66t` (enh) raises the recall floor — the already-computed graph signal reaches citations (cross-file chains) and enumerations widen instead of silently truncating. `1p66v` (enh) tunes the reranker's static batch — decoupled from the embedder's index-time `STATIC_BATCH=64` and sized to the query-time ≤40-candidate pool. When this wave closes, `code_ask` is honest about what it didn't find, surfaces code for code questions, recovers cross-file/enumeration recall, and reranks with a right-sized batch.

## Changes

Change ID: `1p66r-bug code-ask-confidence-calibration-abstention`
Change Status: `implemented`

Change ID: `1p66s-enh code-ask-doc-code-retrieval-balance`
Change Status: `implemented`

Change ID: `1p66t-enh code-ask-graph-signal-and-enumeration`
Change Status: `implemented`

Change ID: `1p66v-enh reranker-batch-size-tuning`
Change Status: `implemented`

Completed At: 2026-06-17

## Wave Summary

Wave `1p66q` (Code Ask Retrieval Quality) delivered 4 changes: code_ask reports high confidence and emits citations on zero-signal retrieval, code_ask over-weights prose docs and under-surfaces implementing code, code_ask misses cross-file chains and enumerations; the graph rescue never reaches citations, and Reranker static batch size is the embedder's 64; tune it to the query-time pool.

**Changes delivered:**

- **code_ask reports high confidence and emits citations on zero-signal retrieval** (`1p66r-bug code-ask-confidence-calibration-abstention`) — 6 ACs completed. Key decisions: --------; Add an abstention *signal* (confidence=low + gaps + weak-marking), not hard silence.
- **code_ask over-weights prose docs and under-surfaces implementing code** (`1p66s-enh code-ask-doc-code-retrieval-balance`) — 4 ACs completed. Key decisions: --------; Rebalance via demotion-coverage + selection-time code quota, not an embedder change.
- **code_ask misses cross-file chains and enumerations; the graph rescue never reaches citations** (`1p66t-enh code-ask-graph-signal-and-enumeration`) — 4 ACs completed. Key decisions: --------; Surface the EXISTING graph signal into citations rather than build new retrieval.
- **Reranker static batch size is the embedder's 64; tune it to the query-time pool** (`1p66v-enh reranker-batch-size-tuning`) — 5 ACs completed. Key decisions: --------; Scope is reranker batch size, not GPU-vs-CPU.
## Journal Watchpoints

- Blocking: only one wave may be OPEN at a time. `1p66c codebase-map-round4` is currently OPEN (implemented, awaiting operator close). This wave can be planned + readied in parallel, but cannot be activated (`Implement wave`) until `1p66c` closes.
- All four changes need `framework_edit_allowed`. No seed edits expected (audit; `1p66r`/`1p66s`/`1p66t` touch `docs/agents/guru.md` + `docs/specs/mcp-tool-surface.md`, which are docs not seeds).
- Sequencing: `1p66r` (safety floor) first — it defines the abstention/confidence behavior `1p66s` and `1p66t` build on. `1p66s` then `1p66t` (both touch `_agent_candidate_select` / `code_ask` selection — serialize to avoid overlapping edits). `1p66v` is independent (`accel_embedder.py` reranker only) and can land in parallel.
- Shared-file serialization point: `1p66r`/`1p66s`/`1p66t` all edit the `code_ask` path in `server_impl.py` (`_heuristic_confidence`, `_agent_candidate_select`, `_demote_doc_results`, `_graph_signal_candidates`, `_classify_question`). One change at a time through that path.
- Faithfulness gate (`1p66r`): the zero-fabrication citation property must not regress — every emitted citation still resolves to a real `file:line` with matching text. Abstention is a signal, not silence (anti-starvation preserved).
- `1p66v` faithfulness: batch size is a latency knob only — ranking output (order + scores) must be identical across batch sizes (regression guard incl. the multi-chunk path); the embedder's `STATIC_BATCH` is untouched.
- No version bump expected (no chunker/graph extractor shape change — `code_ask` is a query-time consumer; the reranker batch change is graph-cache-keyed by batch dim, a one-time recompile, not a builder-version bump).
- Follow-up: validate downstream on the consumer that produced the assessment — re-run the 12-probe set; confirm the confidently-wrong cases (C2/E2/A2) now abstain, code surfaces for code questions, cross-file/enumeration recall improves, and check their `reranked` field is `true` (if the reranker isn't active on their box, that's a separate deployment signal). Possible small follow-on: surface the resolved reranker provider for the "is the reranker active?" diagnostic (dropped from `1p66v` scope per operator direction).

## Review Evidence

- wave-council-readiness: approved (READY) — prepare-council passed 2026-06-17 (seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer; rotating: docs-contract-reviewer) over all four changes. Strongest challenge: `1p66r`'s abstention floor cannot use an absolute cosine floor in the no-reranker path (two embedders, incomparable cosine scales) — condition carried into implement: cap confidence (never `high`) + a relative signal there, reserve the absolute floor for the reranked sigmoid path (anchor `CONF_AGENT_RERANK_LOW=0.1`). Strongest alternative (one mega code_ask change) rejected — the four are independently testable and the safety fix must verify on its own. Conditions into implement (non-blocking): (1) `1p66r` no-reranker confidence uses cap+relative signal, not an absolute cosine floor; (2) every retrieval change tested with reranker ON and OFF; (3) citation fidelity preserved + graph-merged citations resolve to real verified `file:line` (faithfulness gate); (4) `1p66v` ranking byte-identical across batch sizes incl. multi-chunk. Sequence `1p66r → 1p66s → 1p66t` through the shared `code_ask` path; `1p66v` isolated in `accel_embedder.py`, parallel-safe. `confidence` enum stays `{low,medium,high}` (back-compatible). Faithfulness gate (security seat): zero-fabrication citation property is non-negotiable.
- wave-council-delivery: approved (PASS) — delivery-council 2026-06-17 over all four changes (seats: reality-checker, red-team, qa-reviewer, security-reviewer, architecture-reviewer, docs-contract-reviewer; rotating: docs-contract-reviewer). Faithfulness gate passed: citation zero-fabrication preserved (`1p66r` only adds confidence/gaps/weak; `1p66t` graph-merged citations are faithful by construction — real on-disk `file:line`, reranked, floor-gated, deduped); `1p66v` ranking byte-identical across batch sizes incl. multi-chunk (tested). Prepare conditions met: `1p66r` no-reranker capped at `medium` (no absolute cosine floor), abstention on the reranked sigmoid only, plus a loud `reranked=false` degraded-fallback gap (answering the operator "it should always rerank" — a healthy install always reranks, the fallback is now visible). `1p66v` overturned the operator's 32 hypothesis WITH data (recorded benchmark table — 40 wins: single-pass at every pool ≤40, least padding; the missing `batch=` arg to `build_static_onnx` was the real decoupling bug + the earlier stale-cache crash cause). Red-team caught + fixed an enumeration-regex false positive ("what IS the value" via a `\w+s` catch-all → tightened to require a collection word + membership verb, negative test added). 3308 green (+11 net; 5 stale old-behavior tests reconciled, not deleted); docs-lint clean. Honest limitations logged (accepted): `1p66s` AC-4 no-reranker cross-source quota deferred (incomparable cosine scales; degraded path flagged by `1p66r`); `1p66t` AC-1 full graph-merge-through-`search_combined` path is building-block-tested + downstream-validated (in-suite harness is graph-only, no semantic LanceDB — same pattern as `1p66e`), AC-3 set-completeness routed to exact tools rather than overclaiming a count. No `GRAPH_BUILDER_VERSION` bump (query-time consumer; reranker batch is a cache-keyed recompile). CHANGELOG entry deferred to the next release.
- operator-signoff: approved when operator confirms closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-17: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1p66r`'s no-reranker confidence path scores raw cosines from two different embedders on incomparable scales, so an absolute abstention floor there is miscalibrated — cap confidence + use a relative/rank-gap signal in the no-reranker path and reserve the absolute floor for the reranked sigmoid path; strongest-alternative: a single mega "improve code_ask" change — rejected, the four are independently testable and the safety fix must verify alone; conditions into implement (non-blocking): (1) `1p66r` no-reranker cap+relative signal not an absolute cosine floor; (2) test every retrieval change with reranker ON and OFF; (3) citation fidelity preserved + graph-merged citations resolve to real verified file:line (faithfulness gate); (4) `1p66v` ranking byte-identical across batch sizes incl. multi-chunk; sequence `1p66r → 1p66s → 1p66t` through the shared code_ask path, `1p66v` parallel-safe in accel_embedder.py; `confidence` enum stays {low,medium,high} back-compatible)

- **Delivery-phase Wave Council [delivery-council] — 2026-06-17: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, security-reviewer, architecture-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; scope: all 4 changes as delivered; faithfulness gate passed — citation zero-fabrication preserved (1p66r adds only confidence/gaps/weak; 1p66t graph citations faithful-by-construction; 1p66v ranking byte-identical across batches incl. multi-chunk); substantive-findings: enumeration-regex false positive ("what IS the value") caught + fixed by red-team; the reranker decoupling's real bug was the missing `batch=` arg to build_static_onnx (also the earlier stale-cache crash); operator 32-hypothesis overturned by the recorded benchmark (40 wins); honest limitations accepted — 1p66s AC-4 no-reranker quota deferred (incomparable scales; degraded path flagged loud by 1p66r), 1p66t AC-1 full search_combined-merge building-block-tested + downstream-validated (graph-only in-suite harness), AC-3 completeness routed to exact tools; 3308 green, docs-lint clean, no GRAPH_BUILDER_VERSION bump; CHANGELOG deferred to next release)

## Dependencies

- No external wave dependencies.
