# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-12

wave-id: `1seav search-freshness-degraded-retrieval`
Title: Search Freshness Degraded Retrieval

## Objective

Land the two highest-value findings from the 2026-07-12 external code review, both validated against source and both riding the substrate the 1sbfk/1sc7c waves just built: (1) `code_ask`'s per-question freshness check is simultaneously the most expensive part of its envelope (an O(corpus) hash walk its own docstring forbids on the hot path) and wrong (chunker-mismatch-only, exceptions read as "current") — replace it with the cheap per-layer signal and an honest three-state contract; (2) semantic-path failure currently disables search entirely (`code_search` errors when the model is unavailable) or triggers a per-call corpus re-chunk with silent filter loss (`docs_search`'s pre-FTS fallback) — degrade FTS-first with preserved filters and a uniform typed `search_mode`/`fallback_reason` contract. Candidate to fold into the 1.12.1 release alongside `1sbfl`.

## Changes

Change ID: `1sbxq-bug code-ask-freshness-signal`
Change Status: `planned`

Change ID: `1seaq-enh fts-first-degraded-search-fallback`
Change Status: `planned`

## Wave Summary

Two review-derived changes: honest, cheap `code_ask` freshness (three states, no hot-path walk, cache invalidated on build) and FTS-first degraded search for `code_search`/`docs_search` (filters preserved, live walk demoted to store-absent-only, typed degradation contract across the three search tools).

## Journal Watchpoints

- Watchpoint (shared envelope): both changes touch the search response envelopes — land the field names (`index_freshness` three-state, `search_mode`, `fallback_reason`) ONCE, coherently, in the same vocabulary across `code_ask`/`code_search`/`docs_search`.
- Watchpoint (honesty rule): exceptions/undeterminable states must surface as `unknown`/typed reasons — never silently `current` or bare empty results. This is the same lesson 1sbfj already paid for; do not re-learn it.
- Watchpoint (fail-soft preserved): degradation returns results wherever the derived store can serve; the live filesystem walk survives ONLY for the store-absent case, and a pin proves it unreachable when the store is healthy.
- Watchpoint (latency evidence): AC-1 of `1sbxq` requires before/after timing on this repo — the removed walk must be visible in the numbers, not asserted.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-12: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: the replacement freshness signal (stat-fast-path + chunker meta) can false-negative on a content change that preserves mtime/size/inode — resolved by accepting the SAME documented trade the staleness monitor already makes, with two containments: the per-layer build path (1sc7c) remains the authority (this is an advisory envelope signal, not a build trigger) and indeterminacy reports `unknown`, never `current`; strongest-alternative: drop `index_freshness` from `code_ask` entirely — rejected because seed-211 documents and routes on it; an honest cheap signal beats both an expensive wrong one and none)
- Council seat notes: reality-checker — every claim source-verified THIS session against `2952df8f`: `_layer_health` called per `code_ask` (~17305) in direct contradiction of its own docstring (~639), chunker-only staleness (~17306-08) discarding the `stale_paths` just computed, `except → current` (~17309-11); `search_code` embeds before any fallback (~1670); `_live_docs_chunks` per-call walk with its own hot-path warning (~766) and tag-filter loss (~836); the reviewer's `current`-while-stale live repro is consistent with the code as read. The claimed substrate exists: `project_index_inputs_stale` (monitor-proven), `layer_path_state` (1sc7c), and `code_lexical_response` as the reusable FTS-serving path. red-team — pressed lexical-fallback quality expectations (an agent treating BM25-only results as semantic recall): contained by the explicit `search_mode` field, seed-211 interpretation guidance, and the zero-hit token-semantics note; pressed cache poisoning on the freshness verdict: TTL is seconds-scale and invalidation keys on the build/meta signature, fixture-pinned (AC-4); pressed filter-preservation completeness: `tags` is empty in production corpora (known from 1sbfj) — the fixture must pin pass-through semantics, not invent tag data. qa-reviewer — the fixture matrix is enumerated in the ACs (stale-path, exception→unknown, cache invalidation, both tools' fallbacks with every filter, live-walk unreachable-when-healthy pin, disabled-embedder live probe) and the existing coverage gap is named (chunker-mismatch-only at ~10281). architecture-reviewer — the two changes share envelope territory and MUST land one vocabulary (`index_freshness` three-state, `search_mode`, `fallback_reason`) across the three search tools; the degradation ladder (semantic → hybrid → FTS → live-walk-only-if-store-absent) belongs in `search-architecture.md`; fail-soft is preserved, visibility added — the 1sbfj pattern applied to search. seat_agreement: unanimous.
- AC priority: confirmed at prepare as proposed (all required across both changes). Product-owner acknowledgment: operator-directed 2026-07-12 ("build these waves now"); release candidate 1.12.1 alongside `1sbfl`.

## Review Evidence

- wave-council-readiness: approved 2026-07-12 — prepare council synthesis verdict READY: both changes are source-validated repairs with the enabling substrate already shipped (1sbfk/1sc7c/`code_lexical`), the fixture matrices are enumerated in the ACs, and the one accepted trade (stat-fast-path false negatives) is contained by authority separation plus the `unknown` state. Seats unanimous; full synthesis in Review Checkpoints.
- operator-signoff: approved when operator confirms closure

## Dependencies

- No external wave dependencies. Builds on the shipped 1sbfk (trustworthy FTS) + 1sc7c (fresh FTS, per-layer state). Release candidate: fold into 1.12.1 with `1sbfl`.
