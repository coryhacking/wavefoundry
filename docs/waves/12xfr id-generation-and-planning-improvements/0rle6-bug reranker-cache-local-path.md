# Reranker Cache Local Path

Change ID: `0rle6-bug reranker-cache-local-path`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

The reranker cache is currently rooted in the system temp directory. That makes the model cache easy to lose between runs and exposes it to partial-download races when multiple dashboard or setup flows touch the same cache at once. We need the reranker cache to live under a stable local path and to recover by re-downloading when the cache is missing or clearly corrupt.

## Requirements

1. Move the FastEmbed cache default from the system temp directory to `~/.wavefoundry/cache/fastembed`.
2. Preserve `FASTEMBED_CACHE_PATH` as an override for tests and operators.
3. Treat missing reranker artifacts and corrupt cache contents as repairable state: quarantine the broken cache and retry the prewarm path once.
4. Keep the live search path tolerant of reranker failures by falling back to non-reranked ranking when the model cannot be loaded.

## Scope

**Problem statement:** The reranker model cache is transient and can be observed in a partially-written state, which causes startup prewarm to abort and leaves the cache vulnerable to repeated failures across launches.

**In scope:**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

**Out of scope:**

- Changing the reranker model itself.
- Changing the live reranking algorithm.
- Removing reranker prewarm entirely.

## Acceptance Criteria

- [x] AC-1: The default FastEmbed cache path resolves under `~/.wavefoundry/cache/fastembed` when `FASTEMBED_CACHE_PATH` is unset.
- [x] AC-2: If the reranker cache is missing or clearly corrupt, setup quarantines the broken cache and retries prewarm once.
- [x] AC-3: A reranker load failure during live search still falls back to non-reranked ranking instead of aborting the query path.
- [x] AC-4: Targeted setup/indexer/server tests pass.

## Tasks

- [x] Add a stable default FastEmbed cache path helper and apply it at module startup.
- [x] Expand reranker cache corruption detection to include missing model artifacts.
- [x] Update prewarm recovery to quarantine and retry once when the reranker cache is missing or corrupt.
- [x] Add regression tests for default cache location and recovery.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| cache-path | implementer | — | Stable `~/.wavefoundry/cache/fastembed` default |
| recovery | implementer | cache-path | Quarantine and retry broken reranker cache |
| tests | implementer | recovery | Setup and loader regressions |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/server_impl.py`

## Affected Architecture Docs

N/A. The change is contained to cache location and recovery behavior in framework scripts and their tests.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Stable default cache path |
| AC-2 | required | Recovery from missing/corrupt reranker cache |
| AC-3 | important | Preserve live search resilience |
| AC-4 | required | Prevent regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Change created to move reranker cache out of temp and make cache repair retryable. | Current reranker prewarm failures come from temp-cache model artifacts missing or partial during startup. |
| 2026-05-27 | Implemented stable cache default and repair retry for missing reranker artifacts. | `py_compile` passed; targeted `SetupIndexTests` for cache default, corruption detection, and retry/quarantine passed. |
| 2026-05-27 | Marked change complete after verification. | `wave_validate` passed after docs updates. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-27 | Use a stable `~/.wavefoundry/cache/fastembed` cache root rather than temp. | Temp directories can be cleaned between runs and are a poor home for shared model caches. | Keep temp cache and add more retries |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Temp cache may still contain old broken model state | Quarantine and retry once; if needed, clear the old temp cache during the transition |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
