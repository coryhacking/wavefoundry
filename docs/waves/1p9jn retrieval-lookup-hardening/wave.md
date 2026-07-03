# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-02

wave-id: `1p9jn retrieval-lookup-hardening`
Title: Retrieval Lookup Hardening

## Objective

Harden retrieval-related lookup behavior in two places: first, make change/wave ID lookups surface ambiguity instead of silently collapsing colliding lifecycle IDs; second, reduce LanceDB FTS index size by switching to no-position storage while preserving docs/code retrieval through a paired query-shape fix. The wave must not ship any lookup path that hides ambiguity or any storage-only FTS change that leaves the existing quoted phrase query path incompatible with no-position FTS.

## Coordinator

- wave-coordinator: Engineering
- Decision rights: keep implementation scoped to the admitted lookup resolver and FTS query-shape changes, their tests, and required docs updates. Do not broaden into vector compression defaults, ID minting-scheme changes, or CoreML reranker crash handling without a separate admitted change.

## Participants

| Role | Responsibility |
|------|----------------|
| implementer | Implement lookup ambiguity handling, FTS query shaping, and focused regression tests. |
| code-reviewer | Review correctness of `server_impl.py`, `indexer.py`, and test changes. |
| qa-reviewer | Reconcile ACs against collision tests, FTS tests, full suite, index rebuild/health, and smoke evidence. |
| architecture-reviewer | Confirm MCP lookup response shapes and hybrid retrieval semantics remain coherent. |
| performance-reviewer | Confirm FTS storage optimization and query behavior preserve the benchmark rationale. |
| security-reviewer | Check user-supplied IDs/queries for unsafe parsing, namespace bleed, or silent failure modes. |
| product-owner | Confirm lookup ambiguity response and FTS phrase-search tradeoffs are acceptable. |
| wave-council | Synthesize readiness and delivery verdicts. |

## Changes

Change ID: `1p9ip-bug change-lookup-ambiguity-disambiguation`
Change Status: `implemented`

Change ID: `1p9j1-enh fts-no-position-query-shape`
Change Status: `implemented`

## Planned or Active Changes

- `1p9ip-bug change-lookup-ambiguity-disambiguation` — admitted and wave-owned at `docs/waves/1p9jn retrieval-lookup-hardening/1p9ip-bug change-lookup-ambiguity-disambiguation.md`.
- `1p9j1-enh fts-no-position-query-shape` — admitted and wave-owned at `docs/waves/1p9jn retrieval-lookup-hardening/1p9j1-enh fts-no-position-query-shape.md`.

## Dependencies

- Existing local benchmark report: `docs/reports/index-compression-and-fts-2026-07-02.md`.
- Paused wave `1p9j0 windows-portability-round-3` retains unrelated dirty implementation state. Do not edit its files for this wave except where files overlap and are intentionally in scope for `1p9j1`.

## Current Assumptions

- Lifecycle ID collisions can happen across branches; slug/path disambiguation is the durable recovery path, so lookup tools must expose all candidates.
- Wavefoundry's current FTS use is candidate recall for hybrid docs/code retrieval, identifiers, symbols, and reranked semantic workflows, not a user-facing exact phrase-search product.
- No-position FTS is acceptable only when query construction stops requiring positional phrase matching.
- The current tokenizer, lower-case, stemming, stop-word, and max-token-length settings remain unchanged unless implementation discovery finds a blocking compatibility issue.

## Outputs Produced or Expected

- List-aware change and wave lookup resolvers that report ambiguous matches.
- Updated MCP/resource callers for change/wave lookup ambiguity.
- Updated FTS index creation with `with_position=False`.
- Updated FTS query shaping compatible with no-position FTS.
- Focused server/indexer regression tests.
- Full framework test evidence.
- Local index rebuild or refresh plus index health evidence.
- Docs updates if implementation changes an operator-visible retrieval contract.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer; rotating-seat: performance-reviewer; strongest-challenge: this wave touches two retrieval correctness surfaces that can fail silently, so tests must prove both no silent ID ambiguity collapse and no no-position FTS phrase-query failure; strongest-alternative: split `1p9ip` and `1p9j1` into separate waves, but both are small retrieval-hardening changes in `server_impl.py`/index surfaces and the operator explicitly asked to bundle `1p9j1` with `1p9ip`. Required lanes: implementer, code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, security-reviewer, product-owner.)
- **Prepare wave readiness verdict — 2026-07-02: READY**. Both admitted change docs are wave-owned, required sections are present, AC priority is recorded on both, review lanes are selected, product-owner acknowledgment is recorded, and Wave Council readiness is recorded. Status remains `planned`; open/implementation is a later single-OPEN-gated action.

## Review Evidence

- wave-council-readiness: approved 2026-07-02 — READY. The wave is intentionally narrow: lookup ambiguity reporting plus FTS no-position storage/query-shape compatibility. Vector compression, ID minting redesign, and CoreML reranker crash handling remain out of scope. The strongest risk is silent behavioral regression in lookup or FTS candidate recall; ACs require ambiguity fixtures, query-shape tests, smoke checks, full tests, and index health evidence before delivery.
- product-owner: acknowledged 2026-07-02 — The product tradeoffs are acceptable: ambiguous ID lookups should surface all candidates, and Wavefoundry's FTS use prioritizes high-quality docs/code candidate recall over exact phrase-search semantics.
- code-reviewer: passed 2026-07-02 — reviewed the `server_impl.py` lookup resolver/resource/tool changes, `indexer.py` FTS setting change, and focused regression tests. No blocking findings. The implementation preserves the two load-bearing invariants: ambiguous change/wave IDs surface candidate lists instead of silently collapsing, and no-position FTS ships with no-position-safe query shaping. Scope stayed confined to lookup ambiguity and FTS storage/query shape; the separate CoreML reranker crash remains unmasked and out of scope.
- wave-council-delivery: passed 2026-07-02 — PASS. Delivery review covered both admitted changes. Evidence: `wave_get_change` single-mode ambiguity returns `data.changes` plus `ambiguous_change_id`; wave bulk ambiguity returns `data.waves` plus `ambiguous_wave_id`; resource templates return `# Ambiguous Change` / `# Ambiguous Wave`; `wave.md` is excluded from change lookup; matching is token-anchored; FTS index creation uses `with_position=False`; `_fts_query` avoids phrase-shaped identifier queries. Verification passed: focused `IndexReclaimTests`, `BulkWaveGetChangeTests`, and `FtsQueryShapeTests`; full framework suite `4161 tests across 41 files`; docs-lint clean; foreground index rebuild and subsequent incremental refresh left `wave_index_health` ready with no stale paths; FTS smoke returned docs/code results for natural-language, tool-name, dotted, uppercase, and snake_case queries. Review disposition: no dedicated FTS option-version stamp is required for this wave because FTS is rebuilt with the new no-position form during full index rebuilds and copy/rewrite compaction paths; operator accepted that migration behavior on 2026-07-03. The separate Apple Silicon CoreML temp-dir CPU fallback discovered during review is tracked as `1p9lj-bug coreml-provider-probe-tempdir-cpu-fallback` and is not a blocker for this FTS/query-shape wave. Operator signoff remains pending for close.
- operator-signoff: approved 2026-07-02 — operator explicitly requested close in-session ("close the open wave") after the delivery review passed.

## Journal Refs

- `docs/agents/journals/1p4wz-embedding-retrieval-architecture.md`
- `docs/agents/journals/guru.md`

## Journal Watchpoints

- Watchpoint: preserve namespace separation — change lookups return changes, wave lookups return waves.
- Watchpoint: do not broaden this wave into vector compression defaults; the benchmark report recommends `IVF_HNSW_SQ` separately, but this wave is FTS-only for vector-index purposes.
- Watchpoint: do not mask the CoreML reranker native crash found during benchmarking; keep it as a separate production issue.
- Watchpoint: preserve the paired-change invariant — no-position FTS and no-position-safe query shaping must land together.

## Completion Criteria

- All required ACs on `1p9ip` and `1p9j1` are complete or explicitly marked `[~]` with rationale.
- Focused lookup ambiguity, FTS, indexer, and server tests pass.
- Full framework suite passes.
- Local docs and code semantic index health is verified after rebuild or refresh.
- Review lanes are reconciled and delivery-council evidence is recorded.

## Handoff or Next-Wave Notes

- After this wave closes, resume `1p9j0 windows-portability-round-3` only when no other wave is open.
- If implementation reveals a real need for phrase-search semantics, stop and replan rather than forcing no-position FTS through.

Completed At: 2026-07-02

## Wave Summary

Wave `1p9jn` (Retrieval Lookup Hardening) delivered two changes: Change and wave lookups silently collapse colliding IDs; both must return all matches and stay namespace-separate and FTS No-Position Query Shape. Notable adjustments during implementation: Change and wave lookups silently collapse colliding IDs; both must return all matches and stay namespace-separate: Change scoped from the `1p9hh` collision observed landing wave `1p9hn`. Change resolver first-match-wins at `server_impl.py:2448` (`get_change`); list primitive `_resolve_change_doc_matches` at `:4515` unused on that path; wave resolver `_find_wave_md` at `:4490` returns `None` on multiple matches (needs a symmetric list variant).; Change and wave lookups silently collapse colliding IDs; both must return all matches and stay namespace-separate: Added regression coverage for ambiguous change lookup, ambiguous wave lookup, namespace separation, `wave.md` exclusion, token anchoring, and single-match compatibility.

**Changes delivered:**

- **Change and wave lookups silently collapse colliding IDs; both must return all matches and stay namespace-separate** (`1p9ip-bug change-lookup-ambiguity-disambiguation`) — 8 ACs completed. Key decisions: Both resolvers return all matches on ambiguity rather than one-pick (change) or None (wave).
- **FTS No-Position Query Shape** (`1p9j1-enh fts-no-position-query-shape`) — 7 ACs completed. Key decisions: Selected paired no-position FTS plus query-shape fix.
## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-07-02 | Created wave, admitted `1p9j1`, and recorded Prepare wave readiness. | Initial wave record. |
| 2026-07-02 | Revised per operator direction to bundle `1p9j1` with `1p9ip-bug change-lookup-ambiguity-disambiguation`; admitted `1p9ip` and re-recorded readiness for the two-change wave. | `docs/waves/1p9jn retrieval-lookup-hardening/1p9ip-bug change-lookup-ambiguity-disambiguation.md`; `docs/waves/1p9jn retrieval-lookup-hardening/1p9j1-enh fts-no-position-query-shape.md`. |
| 2026-07-02 | Implemented both admitted changes. | `server_impl.py` lookup ambiguity/query-shape changes; `indexer.py` no-position FTS setting; focused regression tests in `test_server_tools.py` and `test_indexer.py`; full framework suite passed (`4161 tests across 41 files`). |
| 2026-07-02 | Rebuilt docs/code indexes and verified health/smoke behavior after implementation. | Foreground rebuild completed with docs `17,690` rows, code `12,518` rows, graph `10,739` nodes / `30,791` edges; `wave_index_health_response` reported `semantic_ready=true`, no missing/stale layers, lock not held; FTS smoke returned docs/code results for natural-language, tool-name, dotted, uppercase, and snake_case queries. |
