# Performance Budget

Owner: Engineering
Status: active
Last verified: 2026-07-12

## Current Performance Expectations

| Operation | Expected Duration | Notes |
|-----------|-----------------|-------|
| `wf docs-lint` on this repo | < 5 seconds | Validates docs/ tree; should be fast |
| `wf docs-gardener` on this repo | < 5 seconds | Metadata refresh; local file I/O |
| `lifecycle_id.py` | < 1 second | Pure computation + config read |
| `build_pack.py` | < 30 seconds | Zip creation; depends on framework/ tree size |
| `render_platform_surfaces.py` | < 5 seconds | File generation; small number of hook files |
| Framework script test suite | < 30 seconds | Unit tests on fixture files |

## Semantic-Index State Budgets (wave 1sed7)

Structural budgets, not brittle timings — the invariants are about *shape* (how many probes, which durability class), with locally measured reference numbers:

| Operation | Budget (structural) | Reference measurement |
|-----------|--------------------|----------------------|
| Reader epoch probe (`build_epoch_token`) | Exactly two short read-only queries per indexed operation (one pre, one post); no state held across the operation | ~0.31 ms median / ~0.38 ms p95 per probe (M2 Max) |
| Build boundary commits | Exactly two small `FULL`-synchronous commits per mutating build (fence + completion CAS); everything else stays `synchronous=NORMAL` | sub-millisecond each; invisible next to embedding time |
| True no-op build | Zero epoch writes, generation unchanged (read-only reap/heal preflight only) | — |
| Dashboard index stats | Cached/event-driven collection; the store read is `read_build_summary` (scalars + one COUNT) and Lance reads are `count_rows` metadata only — no per-file rows and no table materialization. Exception: the daemon's periodic staleness timer reads the full per-file snapshot because it IS the input-hash compare; it never runs on the HTTP request path | — |
| Whole-store reset convergence | One all-layer re-chunk pass with Lance vector reuse (no re-embedding of unchanged chunks) | minutes-class worst case, same as a `--rechunk` pass |

## Performance Hotspots

None currently; all operations are local file I/O with small data volumes.

## Future: MCP Server

| Operation | Target | Notes |
|-----------|--------|-------|
| `code.search` exact search | < 2 seconds for repos ≤ 100k files | TBD based on index implementation |
| `wave.current` | < 1 second | Read a few docs/ files |
| `wave.validate` | < 5 seconds | Validate docs/ tree |

The local SQLite index (future) should make exact search faster than full-tree scanning. Index build time is a one-time cost; keep it under 60 seconds for typical target repos.
