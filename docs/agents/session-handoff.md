# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-07-11

## Current State

**Wave `1rsh9 sqlite-index-substrate` — CLOSED 2026-07-11 (operator-approved) and committed to `main` as `241b350e`. NOT yet released.**

Four changes delivered (three on 2026-07-10; `1sauc` late-admitted by operator direction on 2026-07-11):

- `1rq4h-enh sqlite-index-state-store` — `index_state_store.py` substrate (graph store untouched), freshness/attribution tables + `freshness_for_path` read primitive, maintenance primitives, unified `wave_index_optimize` (Lance + both SQLite stores), two-layer integrity probe in `wave_index_health`.
- `1rrr0-enh sqlite-fts5-and-index-internals` — contentful FTS5 tables (`unicode61 tokenchars '_'`, detail=full kept deliberately), ordered-consistency sync + reconcile, BM25 fusion pre-rerank in `search_combined` (default ON; eval improved=1/regressed=0/unchanged=11), `meta.json` exported snapshot, registry-backed incremental skip (0.14s vs 1.68s per table).
- `1rsha-enh incremental-secret-scan-cache` — per-file content+rules scan cache (differential equivalence proven with the real scanner; fail-toward-full-scan; 6.7s full vs 0.07s warm live); fixed the latent rules-hash bug (framework ruleset was outside the fingerprint).
- `1sauc-enh retire-lance-tantivy-fts` — Lance/Tantivy FTS fully retired: no Lance FTS created anywhere (source-locked), `search_code`'s lexical half reads the FTS5 tables (filter parity; store schema v4), legacy indices dropped by the reclaim path at upgrade. LIVE: 148 MB reclaimed (docs.lance 163→51 MB, code.lance 73→37 MB). Eval: 0 regressed / 10 unchanged.

**Verification at close:** full suite 4,818 tests OK bytecode-free; `wave_validate` clean; readiness extension + delivery council (incl. `1sauc` addendum) recorded in the wave record; ADR `1s5u9-adr`. The live MCP server on this repo was hot-reloaded 2026-07-11 (`wave_mcp_reload`) — fusion, FTS5-backed `code_search`, and the `state_store` health block are serving.

## Next Steps

1. **Release when ready** — the next version bundles wave `1rsh9` (CHANGELOG section written at release time; commit-style bullets, no build numbers/wave IDs; `build_pack.py --release` needs a clean tree and the `## [X]` CHANGELOG section; gh account `coryhacking`).
2. Field-upgrade behavior to expect: store provisions/backfills with the calm cold-provisioning note; legacy Tantivy indices dropped + reclaimed automatically; one-time full secret scan (cold cache + corrected rules hash); `wave_mcp_reload` needed for running servers.
3. Wave `1ro44` (agent memory + churn decay) is READIED and now unblocked — `1ro43` consumes the freshness tables shipped here as-is.

## Follow-ups recorded (not blocking)

- Retire the `1rycf` close-time bloat gate once field data confirms the leak source is gone (it band-aided the Tantivy `_indices/` leak `1sauc` removed at the source; harmless meanwhile).
- Stale-content Lance drift class (file_meta current but rows predate an edit): candidate detection via a freshness-store cross-check.
- Tier 2 rule-delta secret scanning (spike: partially viable; needs an additive rules-subset param + a rule_id-keyed ledger-sweep decision re confirmation history).
- `meta.json` reader migration to the store (explicitly deferred by 1rrr0).
- Graph store automatic build-path maintenance (on-demand only this wave, per AC-7).

## Session Notes

- The pre-edit hook fails when the shell cwd is inside `.wavefoundry/framework/scripts/` — `cd` back to repo root before Edit calls.
