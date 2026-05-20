# Test Cache for run_tests.py

Change ID: `12r7e-maint test-cache`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

The framework test suite takes over a minute to run. Agents routinely invoke it immediately before packaging, even when no framework file has changed since the last green run. A content-hash cache records a SHA-256 digest of all test-relevant files under the framework directory after each successful run. On re-entry, `run_tests.py` recomputes the digest — if it matches the cache, it prints a one-line summary and exits immediately without running any tests.

The hash covers every file under `.wavefoundry/framework/` except packaging artifacts (`VERSION`, `MANIFEST`), the cache file itself, and the binary index directory. This includes Python scripts, seed documents, dashboard assets, and test fixture files — anything that could change a test result. Packaging artifacts are excluded so that running `build_pack.py` (which rewrites MANIFEST) does not invalidate the cache.

## Requirements

1. After a successful run, `run_tests.py` writes `.wavefoundry/framework/test-cache.json` with `inputs_hash` (SHA-256 of all files under the framework directory, excluding `VERSION`, `MANIFEST`, `test-cache.json` by name, and `index/`, `__pycache__`, `.pytest_cache` by directory), `ran_at` (ISO-8601 UTC), `test_count`, and `result: "ok"`.
2. On entry, `run_tests.py` recomputes `inputs_hash`. If it matches the cache and the prior run passed, the suite is skipped and the cached count is printed.
3. `_hash_inputs()` is called exactly once (before any test execution) and that same hash value is used for both the cache-hit check and the cache write — preventing a double-hash bug where post-run file changes could cause mismatches.
4. Before running the suite, `_clean_pycache()` removes all `__pycache__` directories under the framework directory so stale bytecode cannot affect test behaviour.
5. `--no-cache` bypasses the cache check (forces a full run) but still writes the cache on success, so subsequent normal invocations can skip.
6. `--no-cache` is stripped from argv before it is forwarded to `unittest discover` — unittest must never see it.
7. Cache write failure is non-fatal (silent `except`). Cache read failure returns `None` gracefully.
8. `test-cache.json` is gitignored (`.gitignore`), excluded from the distribution zip (`build_pack.py` `EXCLUDED_REL_PATHS`).

## Scope

**In scope:**

- `scripts/run_tests.py` — `_hash_inputs`, `_clean_pycache`, `_read_cache`, `_write_cache`, `_cache_hit`, `_HASH_EXCLUDE_NAMES`, `_HASH_EXCLUDE_DIRS` (includes `__pycache__` and `.pytest_cache`), updated `main()` with single-hash computation and `--no-cache` flag
- `scripts/tests/test_run_tests_cache.py` — `HashInputsTests` (11 tests), `CleanPycacheTests` (4 tests), `CacheFileTests` (7 tests), `MainCacheBehaviorTests` (9 tests)
- `.gitignore` — add `.wavefoundry/framework/test-cache.json`
- `scripts/build_pack.py` — add `"test-cache.json"` to `EXCLUDED_REL_PATHS`

**Out of scope:**

- Cache for individual test files or test modules — whole-suite granularity is sufficient
- Cache TTL / expiry — the content hash is the authoritative freshness signal

## Acceptance Criteria

- AC-1: `run_tests.py` skips the suite and reports cached count when the inputs hash matches the last green run.
- AC-2: `run_tests.py` runs the suite when any tracked framework file has changed.
- AC-3: `VERSION`, `MANIFEST`, and `test-cache.json` changes do not invalidate the cache.
- AC-4: Seed documents and test fixture files are included in the hash (changes to them invalidate the cache).
- AC-5: A failing run does not write the cache.
- AC-6: `--no-cache` forces a full run regardless of cache state and writes the cache on success.
- AC-7: `--no-cache` is not forwarded to `unittest discover`.
- AC-8: `test-cache.json` is excluded from the distribution zip.
- AC-9: Cache helpers are silent on I/O failure (no exceptions propagated to caller).

## Tasks

- Add `_hash_inputs`, `_clean_pycache`, `_read_cache`, `_write_cache`, `_cache_hit`, exclusion constants to `run_tests.py`
- Update `main()`: compute hash once at entry, strip `--no-cache`, check cache, clean pycache, run suite, write cache on success
- Add `.wavefoundry/framework/test-cache.json` to `.gitignore`
- Add `"test-cache.json"` to `EXCLUDED_REL_PATHS` in `build_pack.py`
- Write `test_run_tests_cache.py` with `HashInputsTests`, `CleanPycacheTests`, `CacheFileTests`, `MainCacheBehaviorTests`

## Affected Architecture Docs

N/A — development-tooling change confined to `run_tests.py`; no MCP surface, schema, or architecture boundary impact.

## AC Priority

| AC   | Priority  | Rationale                                              |
| ---- | --------- | ------------------------------------------------------ |
| AC-1 | required  | Core deliverable — skip on hit                         |
| AC-2 | required  | Must run when any relevant file changes                |
| AC-3 | required  | Packaging must not invalidate the cache                |
| AC-4 | required  | Seed/fixture changes must be detected                  |
| AC-5 | required  | Failed run must not block subsequent skips             |
| AC-6 | required  | Escape hatch writes cache so next call can skip        |
| AC-7 | required  | `--no-cache` must not break unittest discover          |
| AC-8 | required  | Cache file must not ship in the distribution zip       |
| AC-9 | required  | I/O errors must not crash the test runner              |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-19 | Implemented with content-hash approach (SHA-256 of all framework files, excluding packaging artifacts and binary index). Initial design hashed only `.py` files; expanded to include seed documents and test fixture files so changes to those are detected. `--no-cache` writes cache on success. 24 unit tests. 1466 tests pass. | `python3 .wavefoundry/framework/scripts/run_tests.py --no-cache` — 1466 OK; immediate cache hit on second call. |
| 2026-05-19 | Post-review fixes: (1) `__pycache__` and `.pytest_cache` added to `_HASH_EXCLUDE_DIRS`; (2) `_clean_pycache()` added — removes all `__pycache__` dirs before each run; (3) `_hash_inputs()` now called exactly once in `main()` (pre-run hash reused for cache write, eliminating double-hash bug); (4) `CleanPycacheTests` (4 tests) and two new `HashInputsTests` added; `MainCacheBehaviorTests` setUp patches `_clean_pycache` globally. 31 new tests total. 1473 tests pass. | `python3 .wavefoundry/framework/scripts/run_tests.py --no-cache` — 1473 OK. |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | Content hash of framework files (not git tree SHA) | Answers "did anything change since the last test run?" directly — git state is irrelevant. Works without git, in detached HEAD, uncommitted state. | Git tree SHA + dirty check (failed: MANIFEST/VERSION changes from packaging marked tree dirty) |
| 2026-05-19 | Hash all framework files except `VERSION`, `MANIFEST`, `test-cache.json`, `index/` | Packaging artifacts change on every `build_pack` run but don't affect tests; binary index is per-machine and large; everything else (Python, seeds, fixtures) is test-relevant | Hash only `.py` files (misses seed and fixture changes); hash everything (includes build artifacts, invalidates cache on every package) |
| 2026-05-19 | `--no-cache` writes cache on success | After a forced run, subsequent normal calls should benefit from the skip | Suppress write on `--no-cache` (leaves no cache, so every subsequent call re-runs) |
| 2026-05-19 | Cache in `.wavefoundry/framework/test-cache.json` | Co-located with the framework it reflects; gitignored alongside other local runtime artifacts | `.wavefoundry/` root (further from the scripts it serves) |
| 2026-05-19 | Compute `inputs_hash` once at top of `main()`, reuse for both skip check and write | Eliminates double-hash bug: if any non-excluded file changes between skip check and write (e.g. test execution writes a file), the two calls would return different digests and the cache entry would be stale | Re-compute at write time (causes spurious cache miss on next call if tests write files) |
| 2026-05-19 | Exclude `__pycache__` and `.pytest_cache` by directory name in addition to calling `_clean_pycache()` | Belt-and-suspenders: exclusion ensures pycache never enters the hash even if cleanup is skipped; cleanup ensures a clean test environment regardless | Exclusion only (pycache still on disk, affects bytecode loading); cleanup only (hash would include pycache if cleanup fails) |
| 2026-05-19 | Do not hash inode or mtime | Causes spurious invalidation on git checkout, editor atomic-save (temp-then-move), or any touch; path + content is the authoritative freshness signal | Include mtime in hash (faster on large trees but fragile) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
