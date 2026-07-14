# Session Handoff

Owner: Engineering
Status: generated
Last verified: 2026-07-14

## Current State (2026-07-14)

- **Wave `1ro44 agent-memory-and-retrieval-decay` — CLOSED 2026-07-14 (operator-directed).** Delivered `1p8gy` graph-backed agent memory (13 ACs) + `1ro43` churn-aware retrieval decay (14 ACs). `wave-council-delivery: approved` (operator decision, superseding the round 4–7 withdrawals — every reproduced P1 was repaired with regression coverage) + `operator-signoff: approved`; close lint/garden clean. `GRAPH_BUILDER_VERSION` 43→44; no `STATE_STORE_SCHEMA_VERSION`/`CHUNKER_VERSION` bump; drift partition default-OFF; ADRs `1sihk` + `1sk58`. Final round-7 note: the interim global/system git-config NEUTRALIZATION was ruled operator overreach (broke `safe.directory` on shared/CI/WSL checkouts) and REVERTED — protected config passes through, rename determinism is pinned via `--no-renames` command flags instead; the git-config-determinism scope is intentionally CLOSED (no watch item). Suite 5,418 OK; UNCOMMITTED (operator commits).
- **Non-git support hardened both directions and against transient/ambiguous/corrupt states.** Fresh non-git skips cleanly; a CONFIRMED git→non-git transition (positive fatal + no `.git` marker) clears stale drift on BOTH the build-tail and no-op paths, and a failed clear FAILS the build on both; a probe FAILURE — timeout, dubious ownership, permission, corrupt `.git`, broken pointer, bad env — PRESERVES last-good drift; unborn-HEAD is git. Covered by `NonGitProjectTests`, `GitAuthorityTypedStateTests`, `NoOpBuildDriftReconcileTests`, `NoOpDriftClearFailureBuildTests`.
- **Every git subprocess in the derivation chain reads the TARGET repo only** — one `_run_git` chokepoint strips all repository-local git env vars that REDIRECT/REPLACE repo/history state (authoritative `--local-env-vars` census + fallback: `GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR`/`GIT_SHALLOW_FILE`/`GIT_GRAFT_FILE`/replace-ref/object+index overrides). Protected global/system config PASSES THROUGH (safe.directory), and rename detection is pinned via `--no-renames` command flags (not config neutralization). Covered by `AmbientGitDirIsolationTests` (decoy `GIT_DIR`, `GIT_SHALLOW_FILE`, `GIT_GRAFT_FILE`, census fixture, protected-config-passthrough + pinned-rename-determinism), `AmbientGitEnvBuildIsolationTests` (full `build_index` vs clean control under `GIT_SHALLOW_FILE` and `GIT_CONFIG_GLOBAL`), and a strengthened AST `GitSubprocessCensusTests`.
- Test-suite counting: **run via `run_tests.py`** (canonical; per-file subprocess isolation) — the test files register shared `sys.modules` names, so a monolithic `unittest discover` collides them and under-counts. Current authoritative count **5,418 tests across 48 files, OK** bytecode-free. Docs validation and `git diff --check` clean. Windows: explicit `.git` removals in tests use a read-only-clearing `_rmtree_git` helper (git objects are read-only on Windows).

## Delivery-review remediation history (all rounds in the wave record)

- **Round 1 (traversal):** `../` memory-id escape → grammar + containment; MemoryIdTraversalTests.
- **Round 2 (9 findings):** symlink-root escape, gardener-only committed anchor, fail-closed parse, atomic create, drift fingerprint, timestamp-topology, secret scan coverage, hot-path caches, exact wave matching.
- **Round 3 (7 findings), all FIXED with regressions:**
  1. Symlink boundary now covers READS + validates-before-mkdir via the single `canonical_memory_root` chokepoint (SymlinkReadAndMkdirTests).
  2. Runtime `parse_memory_record` mirrors all load-bearing lint rules — superseded-link + section bullets (ParserLintParityTests).
  3. `_gardener_only_pairs` returns typed `(ok, pairs)`; drift preserved on detector failure (GardenerDetectorFailClosedTests).
  4. Normalization scoped to the canonical header `Last verified: <date>` line only (HeaderScopedNormalizationTests).
  5. Churn counted over `anchor..HEAD` ancestry via the `%P` parent graph, merge-DAG correct (MergeDagAncestryTests, matches `git rev-list`).
  6. Advisory cache keyed on a bounded monotonic memory generation (tool + indexer bumped) — no O(N) walk, no aliasing (GenerationCacheTests).
  7. Centrality task checked + AC-5 warm-cache wording corrected; no unchecked `[ ]` remains.
- **Round 4 re-verification (1) (3 P1s): superseded by re-review (2).** (1) `memory_invalidate` fail-closed; (2) `clear_attribution_and_drift` on the git→non-git path; (3) two-instance cache tests + real `build_index` matrix.
- **Round 4 re-verification (2) (4 P1s): superseded by re-review (3).** fully-wedged invalidation fails before bookkeeping; writer-owned fence tokens; typed `_git_authority`; evidence reconciled.
- **Round 4 re-verification (3) (2 P1s): superseded by re-review (4).** no-op drift-clear failure fails publicly; ambiguous git failures → probe_failed.
- **Round 4 re-verification (4) (2 P1s): superseded by re-review (5).** corrupt-git states preserve; changed-build clear failure fails before finalize.
- **Round 4 re-verification (5) (1 P1): superseded by re-review (6).** derived git state read the ambient `GIT_DIR` — every git subprocess in the derivation chain now routes through one sanitized `_run_git` wrapper.
- **Round 4 re-verification (6) (1 P1): superseded by re-review (7).** strip-set is the authoritative `--local-env-vars` census + fallback (`GIT_SHALLOW_FILE`/graft covered).
- **Round 4 re-verification (7): SCOPE-CORRECTED (operator decision), awaiting independent re-verification.** The interim config-neutralization was ruled overreach + a safe.directory breaker. REVERTED it (protected config passes through → safe.directory works); pinned rename detection via `--no-renames` command flags instead; git-config-determinism scope intentionally CLOSED (no watch item, revisit only on field evidence). Suite 5,418 via `run_tests.py`. See the newest wave checkpoint for the scope-correction rationale + evidence.

## Implementation summary (uncommitted, still)

- `1ro43` churn-aware retrieval decay + `1p8gy` agent memory layer are implemented and their wave is CLOSED (all ACs `[x]`/`[~]`). `GRAPH_BUILDER_VERSION` 43→44; no canonical `STATE_STORE_SCHEMA_VERSION`/`CHUNKER_VERSION` bump. Memory invalidation uses a dedicated `.wavefoundry/index/memory-state.sqlite` store (writer-owned fence tokens), not a canonical-store meta key. ADRs `1sihk` + `1sk58`. Drift partition default-OFF. `wave_memory_*` tools live (reconnected). Uncommitted pending operator commit.

## Next Steps

1. **Commit `1ro44`** — CLOSED but uncommitted; the working tree carries 1seav + 1ro44. Commit when directed (operator-owned).
2. **Release** — main 5 commits ahead of origin. When directed: commit → CHANGELOG (1.13.0 bundling 1sc7c + 1sed7 + 1seav + 1ro44) → `build_pack.py --version 1.13.0 --release`.
3. **Queue:** `1skt1` (executable review evidence protocol; change `1siu0` admitted, readiness dry-run clean except required council signoff), `1shv4` (Java chunker `1sbfl`, CHUNKER_VERSION bump), `1seaw` (golden-query eval gate — required before drift-partition default-ON), `1seax`. Staged: `1rolq`, `1rppn`.

## Standing rules (unchanged)

- `git commit` and `wave_close(mode="create")` are operator-owned — explicit words in the current session only. Commit messages: no AI attribution, no Co-Authored-By.
- Ranking changes are eval-gated, period.
- Everything runs via `~/.wavefoundry/venv/bin/python3`; suite via `run_tests.py`.

## Current Session

**Active wave:** *(none)*
