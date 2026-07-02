# docs-lint full-scan performance: shared file-read cache + a `--timings` measurement instrument

Change ID: `1p9c6-enh docs-lint-fullscan-perf-cache-and-timings`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bm install-experience-hardening`

## Rationale

The full corpus docs-lint runs at meaningful frequency — `wave_prepare` (readiness), `wave_close`, both
ends of **upgrade**, and **install** — so full-scan speed matters even though `1p9c1` made the post-edit
hook incremental. Two structural inefficiencies are cheap to remove:

1. **Redundant file reads.** The same doc is read multiple times per run — a wave record is read by
   `check_wave_docs`, `check_metadata`, and `check_markdown_links`, each calling `helpers.read_text`
   independently (~2–3 reads per doc that several validators touch).
2. **No measurement.** We have no instrument to quantify where the time goes, so we cannot tell how much
   the cache saves or which checks would benefit most from parallelization.

This change does the **simple wins first and measures**. Process-pool parallelization (the secrets
model — `ProcessPoolExecutor`, spawn + initializer + ppid watchdog for CPU-bound regex) stays firmly
**on the table** as the sequenced follow-up; it is deliberately out of scope here so we land the cheap,
zero-concurrency wins and get a measurement instrument first. The known Windows windowless-multiprocessing
risk (pool console-window flashes → `windowless_mp_context`/pythonw, `PYTHONUTF8` for cp1252 children) is
understood and addressable; it is a reason to sequence parallelization, not to avoid it.

## Requirements

1. `helpers.read_text` memoizes file content within a process, keyed on `(path, st_mtime_ns, st_size)`
   so repeated reads of the same unchanged file in one lint run hit the cache, while an edited file (new
   mtime/size) is re-read — safe even in the long-lived MCP server where the helpers module persists
   across `wave_validate` calls. A `read_text_cache_clear()` is exposed for tests.
2. The cache is transparent: every existing `read_text` caller benefits with **no signature change**;
   full-lint output is byte-for-byte unchanged (verified by the existing 253 docs-lint tests).
3. The cache never serves stale content: a file changed between two runs (or between a `wave_garden`
   rewrite and a lint in the same process) is re-read because its `(mtime_ns, size)` key changed.
4. `wave_lint_lib.cli` accepts a `--timings` flag. In full mode it times four coarse phases —
   `secrets`, `corpus` (the structural + cross-artifact checks), `metadata` (the per-doc metadata loop),
   and `links` (the per-doc link loop) — and prints `TIMING: <phase> <ms>` lines to stderr plus a
   `TIMING: total <ms>`, without altering pass/fail, the `docs-lint: ok` line, or the exit code. The
   coarse phases are chosen to separate the parallelization candidates (the per-file `metadata`/`links`
   loops) from the rest; finer per-check timing can be added when profiling a specific check. `--timings`
   is inert in incremental mode (the hot path stays quiet). Absent the flag, no timing output and no
   measurement overhead beyond a negligible branch.
5. `run_tests.py` + `wave_validate` pass; a test demonstrates the cache dedupes reads (read count drops
   when a path is read twice) and that a changed `(mtime_ns, size)` invalidates it.

## Scope

**Problem statement:** the full docs-lint re-reads each doc several times and offers no way to measure
where time goes — cheap to fix before deciding how far to take parallelization.

**In scope:**

- `wave_lint_lib/helpers.py`: memoized `read_text` (keyed on path + `stat` identity) + a cache-clear
  hook. *(framework_edit_allowed)*
- `wave_lint_lib/cli.py`: `--timings` flag; time each check in `_run_full_checks`; emit `TIMING:` lines;
  clear the read cache at the start of a run for determinism. *(framework_edit_allowed)*
- Tests: read-count dedupe; stat-identity invalidation; `--timings` emits per-check + total lines and
  does not change pass/fail or the ok line; full-lint output unchanged (253 regression).

**Out of scope (sequenced follow-up — NOT dropped):**

- **Process-pool parallelization** of the per-file validators (the secrets `ProcessPoolExecutor` model)
  and its Windows windowless-multiprocessing hardening — its own change/wave, informed by the `--timings`
  numbers this change produces.
- Single-tree-walk consolidation (each validator rglobs its own subtree) — deferred with parallelization;
  the read cache captures the dominant I/O cost first.

## Acceptance Criteria

- [x] AC-1: `read_text` returns cached content for a repeated read of an unchanged file within a run.
      Evidence: `test_read_cache_returns_cached_content_when_stat_identity_unchanged` — after caching, the
      bytes are overwritten same-length and the mtime restored (key unchanged) and the ORIGINAL content is
      still returned, proving the cache served without re-reading.
- [x] AC-2: a file whose `(st_mtime_ns, st_size)` changed between calls is re-read (no stale content).
      Evidence: `test_read_cache_invalidates_when_stat_identity_changes` — a different-length rewrite
      returns the new content.
- [x] AC-3: full-lint output is byte-for-byte unchanged with the cache — the existing 253 docs-lint tests
      pass untouched, AND `wave_validate` (which runs `docs_lint.py` as a subprocess with the updated code)
      is clean end-to-end. Evidence: docs-lint module green (257); `wave_validate` ok.
- [x] AC-4: `docs-lint --timings` prints `TIMING: <phase> <ms>` for the four coarse phases
      (secrets/corpus/metadata/links) + `TIMING: total <ms>`, keeps the `docs-lint: ok` line + exit 0, and
      no timing lines without the flag. Evidence: `test_timings_emits_per_phase_and_total_and_preserves_contract`
      + the live smoke output (secrets 4649.6 / corpus 630.1 / metadata 41.2 / links 138.5 / total 5459.4).
- [x] AC-5: `--timings` is inert in incremental mode. Evidence: `test_timings_is_inert_in_incremental_mode`
      (`--changed --timings` → no `TIMING:` lines, ok).
- [x] AC-6: `run_tests.py` + `wave_validate` pass. Evidence: `wave_validate` clean; full `run_tests.py`
      running (green result recorded in the Progress Log).

## Tasks

- [x] `helpers.py`: memoized `read_text` on `(path, st_mtime_ns, st_size)`; added `read_text_cache_clear()`.
- [x] `cli.py`: added `--timings`; clear the read cache at run start; time the four coarse phases in
      `_run_full_checks` via a `_timed` CM; emit `TIMING:` lines to stderr; keep the ok line + exit
      contract; inert in incremental mode.
- [x] Tests: `PerfCacheAndTimingsTests` (dedupe, stat-identity invalidation, `--timings` present/absent,
      incremental inertness); full-lint regression (253 unchanged).
- [x] Measured on this repo (see Progress Log): the docs per-file loops are cheap (~180ms); secrets +
      corpus dominate — the finding that reshapes the parallelization decision.
- [x] `run_tests.py` (running; result in Progress Log) + `wave_validate` (clean).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single lane in `wave_lint_lib` (`helpers` + `cli`); the cache is transparent (no validator signature change) and gated by the existing 253 docs-lint tests, then the new cache + timings tests. |

## Serialization Points

- `helpers.read_text` is called by every validator — the cache must be transparent (same return value)
  so the full-lint output is unchanged; the 253-test suite is the regression gate.

## Affected Architecture Docs

`N/A` — an internal performance optimization (transparent read cache) + an opt-in measurement flag; no
boundary, data-flow, or contract change. The authoritative docs gate is unchanged.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core win — dedupe redundant reads. |
| AC-2 | required | Correctness — never serve stale content. |
| AC-3 | required | No regression to the authoritative full lint. |
| AC-4 | required | The measurement instrument that guides the parallelization decision. |
| AC-5 | important | Keep the incremental hot path quiet. |
| AC-6 | required | Suite + docs gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned per operator direction: do the simple full-scan perf wins first + add measurement, KEEP process-pool parallelization on the table as the sequenced follow-up (operator has seen significant improvement from it; the Windows windowless-mp risk is known + addressable). Admitted to the open `1p9bm` wave (5th change). | operator direction; `helpers.read_text` call inventory (~2-3 reads/doc); secrets `ProcessPoolExecutor` precedent. |
| 2026-07-01 | Implemented under `framework_edit_allowed`: transparent `helpers.read_text` cache + `--timings`. Tests green (`PerfCacheAndTimingsTests`); docs-lint+render modules green; `wave_validate` (real subprocess of the updated code) clean. **Measurement finding (this repo, `--timings`):** secrets 4649.6ms / corpus 630.1 / metadata 41.2 / links 138.5 / total 5459.4. The docs per-file loops (metadata+links ≈ **180ms**) are NOT the bottleneck here — secrets (already a `ProcessPoolExecutor`, and inflated by the current large uncommitted working set since full mode is git-scoped) plus corpus dominate. **So on this repo the read-cache and per-file parallelization win little; the value is running `--timings` on a real LARGE repo to see whether metadata/links dominate there** — that measurement, not an assumption, should drive the process-pool follow-up. | `--timings` live output; `PerfCacheAndTimingsTests`. |
| 2026-07-01 | Full `run_tests.py` green — **3,998 OK** — with all five `1p9bm` changes; `wave_validate` clean. `framework_edit_allowed` closed. | run_tests.py; wave_validate. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Simple wins first (transparent read cache + `--timings`), parallelization sequenced after — not dropped. | The read cache is a zero-concurrency, zero-Windows-risk win that removes the dominant I/O cost; measure before paying for the process-pool + its Windows hardening. Parallelization stays planned (operator saw significant improvement). | Parallelize now (rejected as the FIRST step — re-opens Windows windowless-mp complexity before we've measured the cheap win); do nothing (rejected — full scan runs at prepare/close/upgrade). |
| 2026-07-01 | Cache key is `(path, st_mtime_ns, st_size)`, memoized at `helpers.read_text` (transparent). | Zero validator-signature churn; stat-identity invalidation is safe across runs in the long-lived MCP server (same approach the indexer's `_detect_changes` uses). | Thread a per-run cache object through every validator (rejected — large churn); naive `lru_cache` with no invalidation (rejected — stale content across runs in the persistent server). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The read cache serves stale content in the long-lived MCP server after a file edit. | Key on `(st_mtime_ns, st_size)` — an edit changes the key → cache miss → re-read; test AC-2 asserts invalidation. |
| Unbounded cache growth in a long-lived process. | Bounded by the docs-tree file count (small); the run clears it at start for determinism; add a simple size cap if a repo ever makes it material. |
| `--timings` overhead skews the numbers or leaks into normal output. | Timing wraps only top-level checks (coarse), prints to stderr behind the flag, and is inert without it / in incremental mode; AC-4/AC-5 assert the contract. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
