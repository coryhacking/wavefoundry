# Session Handoff

Owner: Engineering
Status: generated
Last verified: 2026-07-17

## Current State (2026-07-15)

- **Wave `1skt1 executable-review-evidence` — CLOSED 2026-07-15.** The executable-review protocol, typed compact authoring, per-lane approval freshness, generated current-head summary, framework carriers, install/upgrade propagation, and fail-closed validator are complete. The final public-path collision repair rejects evidence payloads that attempt to override protected semantic fields. Canonical suite: **5,516 tests across 49 files OK**; docs lint and close gates passed before operator-directed closure.
- **Wave `1slep external-wave-event-ledger` — IMPLEMENTED, DELIVERY COUNCIL APPROVED.** Change `1sl65` now uses fixed sibling `events.jsonl` as the only review-history authority, keeps `wave.md` as human narrative plus generated current-head projection, and excludes exact declared or retained-adoption canonical ledgers from semantic indexing while leaving unrelated/unadopted lifecycle-shaped files eligible. The typed writer serializes under the existing global lock, derives structured event identity and one request digest, replays identical retries, rejects conflicts/reserved metadata, and atomically derives the convergence checkpoint with cycle-2 reverification. Lifecycle, lint, dashboard, resource, install, upgrade, package, and index consumers are implemented and covered. The one-time self-host migration converted the complete adopted census (`1skt1` first, `1slep` last) and immediately re-read `1slep` through the external-only path; consumer install/upgrade never migrates project history or creates ledgers for historical waves. All ten delivery findings are repaired and independently re-verified; all specialist lanes and final Wave Council pass. Close dry-run is green except for operator signoff. No commit or close has been performed.
- **Wave `1ro44 agent-memory-and-retrieval-decay` — CLOSED 2026-07-14 (operator-directed), committed in `805ad8c8`.** Delivered `1p8gy` graph-backed agent memory (13 ACs) + `1ro43` churn-aware retrieval decay (14 ACs). `wave-council-delivery: approved` (operator decision, superseding the round 4–7 withdrawals — every reproduced P1 was repaired with regression coverage) + `operator-signoff: approved`; close lint/garden clean. `GRAPH_BUILDER_VERSION` 43→44; no `STATE_STORE_SCHEMA_VERSION`/`CHUNKER_VERSION` bump; drift partition default-OFF; ADRs `1sihk` + `1sk58`. Final round-7 note: the interim global/system git-config NEUTRALIZATION was ruled operator overreach (broke `safe.directory` on shared/CI/WSL checkouts) and REVERTED — protected config passes through, rename determinism is pinned via `--no-renames` command flags instead; the git-config-determinism scope is intentionally CLOSED (no watch item). Suite 5,418 OK.
- **Non-git support hardened both directions and against transient/ambiguous/corrupt states.** Fresh non-git skips cleanly; a CONFIRMED git→non-git transition (positive fatal + no `.git` marker) clears stale drift on BOTH the build-tail and no-op paths, and a failed clear FAILS the build on both; a probe FAILURE — timeout, dubious ownership, permission, corrupt `.git`, broken pointer, bad env — PRESERVES last-good drift; unborn-HEAD is git. Covered by `NonGitProjectTests`, `GitAuthorityTypedStateTests`, `NoOpBuildDriftReconcileTests`, `NoOpDriftClearFailureBuildTests`.
- **Every git subprocess in the derivation chain reads the TARGET repo only** — one `_run_git` chokepoint strips all repository-local git env vars that REDIRECT/REPLACE repo/history state (authoritative `--local-env-vars` census + fallback: `GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR`/`GIT_SHALLOW_FILE`/`GIT_GRAFT_FILE`/replace-ref/object+index overrides). Protected global/system config PASSES THROUGH (safe.directory), and rename detection is pinned via `--no-renames` command flags (not config neutralization). Covered by `AmbientGitDirIsolationTests` (decoy `GIT_DIR`, `GIT_SHALLOW_FILE`, `GIT_GRAFT_FILE`, census fixture, protected-config-passthrough + pinned-rename-determinism), `AmbientGitEnvBuildIsolationTests` (full `build_index` vs clean control under `GIT_SHALLOW_FILE` and `GIT_CONFIG_GLOBAL`), and a strengthened AST `GitSubprocessCensusTests`.
- Test-suite counting: **run via `run_tests.py`** (canonical; per-file subprocess isolation) — the test files register shared `sys.modules` names, so a monolithic `unittest discover` collides them and under-counts. Current authoritative delivery run: **5,596 tests across 50 files, OK**. Windows: explicit `.git` removals in tests use a read-only-clearing `_rmtree_git` helper (git objects are read-only on Windows).

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

## Previous implementation summary

- `1ro43` churn-aware retrieval decay + `1p8gy` agent memory layer are implemented, closed, and committed in `805ad8c8` (all ACs `[x]`/`[~]`). `GRAPH_BUILDER_VERSION` 43→44; no canonical `STATE_STORE_SCHEMA_VERSION`/`CHUNKER_VERSION` bump. Memory invalidation uses a dedicated `.wavefoundry/index/memory-state.sqlite` store (writer-owned fence tokens), not a canonical-store meta key. ADRs `1sihk` + `1sk58`. Drift partition default-OFF. `wave_memory_*` tools live (reconnected).

## Next Steps

1. **Operator decision for `1slep`** — review the completed implementation and council evidence; record operator signoff and close only on explicit operator direction.
2. **Commit after operator review** — no commit has been created for this wave; commit remains operator-owned.
3. **Release** — after `1slep` closes, write the 1.13.0 CHANGELOG and run the operator-directed release path.
4. **Queue:** `1shv4` (Java chunker `1sbfl`, CHUNKER_VERSION bump), `1seaw` (golden-query eval gate — required before drift-partition default-ON), `1seax`. Staged: `1rolq`, `1rppn`.

## Standing rules (unchanged)

- `git commit` and `wave_close(mode="create")` are operator-owned — explicit words in the current session only. Commit messages: no AI attribution, no Co-Authored-By.
- Ranking changes are eval-gated, period.
- Everything runs via `~/.wavefoundry/venv/bin/python3`; suite via `run_tests.py`.

## Current Session

**Active wave:** *(none)*

- Both admitted changes are implemented. `1sua7` keeps multi-finding repair cycles truthful; `1stwi` replaces the earlier split/buffered telemetry with one SQLite write-through closed ledger: phase/source/version content and structural credit, mapped workflow-prompt credit, exact request/response debits, and only a quality-qualified paired residual.
- Every eligible call commits its event or durable accounting-gap poison before returning; an undurable double failure returns `telemetry_persistence_failed`. Source credit is capped with explicit drop diagnostics. Lifecycle, reload, and upgrade boundaries project durable generations into one concise `wave.md` total. This is the first shipped telemetry schema; no pre-release compatibility layer is retained.
- The machine checkpoint retains store identity, component provenance, source counts/drops, matched residual, and active paired-evaluation count. Fresh install, package, render, and real zip upgrade ship the telemetry module, scorer, schema, and typed attachment tool without creating runtime state eagerly.
- Delivery repair cycle 2 closed the reviewed telemetry/protocol blockers plus three adjacent current-tree omissions and reached aggregate convergence across 17 findings. Its fresh Wave Council approval was subsequently withdrawn by the close dry-run's discovery of an eighteenth, bounded protocol defect: delivery repairs incorrectly staled historical prepare readiness. Cycle 3 now scopes approval freshness correctly—readiness remains required and identity-valid but historical; operator, delivery-council, and specialist chronology remain enforced. Fresh architecture and QA reviewers replayed the known-bad, a 17-case matrix, public close behavior, and adjacent controls; both returned PASS. A fresh Wave Council moderator confirmed all 18 finding heads terminal, max severity none, and no changed full-review boundary; the refreshed executable `wave-council-delivery` approval is recorded. Canonical verification is **5,744 tests across 52 isolated files, all green**; WaveLifecycleMutationTests are **47/47** and review-evidence tests are **79/79**. Only operator signoff, operator-owned close, and commit remain pending.
