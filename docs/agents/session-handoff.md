# Session Handoff

Owner: Engineering
Status: generated
Last verified: 2026-07-20

## Current Session

- **Active wave:** `1t1uo dashboard-multiline-ac-tasks`. Change `1t1un` is
  implemented and complete; the wave remains `implementing` pending the final
  delivery record and operator-owned close.
- The dashboard backend now joins hard-wrapped AC/task prose through one bounded
  caller-specific list parser while preserving checkbox/deferred state, AC ID,
  priority, counts, sibling boundaries, ordered-AC support, and dash-only Task
  starters. Common list indentation survives section extraction. Structural
  lines stop absorption, including ATX/`=` Setext headings, tables with or
  without outer pipes, fences, blockquotes, list markers, and thematic breaks.
- Independent delivery review reproduced common-indentation and pipe-less-table
  defects; both repairs and the adjacent Setext/thematic ambiguity are now
  regression-pinned. Technical and QA re-verification pass with no remaining
  code finding. Package/install and post-upgrade probes import and execute the
  copied parser rather than checking asset presence.
- The live dashboard was restarted on the repaired backend. Active AC and Task
  dialogs contain the complete strings; long rows span multiple rendered lines,
  row scroll width equals available width, and the 1280px viewport has no
  page-level horizontal overflow.
- Verification: final canonical suite **5,978/5,978 across 56 isolated files**;
  dashboard **188 OK** (one existing skip); package **97 OK**; upgrade **332
  OK**; docs lint and `git diff --check` clean.
- No commit or wave close has been performed. Both remain operator-owned.

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

## Prior Session Archive (superseded)

**Active wave:** *(none)*

- `1sxj7 self-populating-memory-and-telemetry-reconciliation` is closed by
  operator direction. Follow-up wave `1t3dm` admits three planned changes:
  `1t0u4` adds Git-independent, resumable historical-memory backfill to install,
  upgrade, and migration; `1t3dl` keeps complete review history in
  `events.jsonl` while rendering one causal current-state row per approval lane
  in `wave.md`; and `1t3dn` repairs the dashboard's shared wave/change Markdown
  renderer so ownership markers stay hidden and hard-wrapped prose/lists use
  normal paragraph spacing and available width. The wave is planned, not
  readied or opened, and no implementation or commit has started.

- `1sxxx` is implemented: one shared `runtime_lock.py` owns the common
  cross-platform mechanics; producer, review-adoption, dashboard-start, and
  dashboard-server carriers now live under `.wavefoundry/locks/` with lazy
  creator-owned provisioning. The index build lock remains co-located and keeps
  its F_GETLK/interruption policy. Upgrade performs a pre-extract, one-way
  stop/check/delete cutover with no runtime fallback, persists dashboard restart
  intent, and restarts on successful cleanup. The dashboard launch mutex is a
  persistent carrier and the dashboard remains read-only with respect to
  indexing. Canonical verification: 5,868 tests across 55 files, OK; docs-lint
  clean. The wave is implemented but not delivery-reviewed or closed.
- The two retrospective repair changes are implemented: `1sxmz` makes commit provenance canonical, typed, complete across mixed blame, relevance-labeled, and exact-one-mode; `1sxmy` repairs real-ledger memory supply, admitted decision parsing, mutation idempotency, Unicode/evidence identity, response honesty, and canonical wave lookup.
- Estimated exploration-avoided events now use the existing Context Efficiency SQLite authority in a distinct table. Stable event keys deduplicate repeats, one source origin has a bounded phase budget, unmatched/default surfacing earns zero, explicit and passive callers share the same stage/phase/cited API, live SQLite source cost is authoritative, and lifecycle/reload/upgrade flush a separate `wave.md` projection that never enters measured Context Efficiency totals.
- `1syle` is implemented: evidence extraction is candidate-only; stable wave-scoped
  source identities suppress every durable disposition; `wave_memory_validate`
  records promote/retain/reject/rewrite with compact agent judgment; close blocks
  missing/pending eligible candidates but permits zero-memory waves; rewrite retry
  converges after a partial failure; setup and upgrade deliver the same review/close
  checkpoint.
- Historical backfill now covers 56 closed waves. Thirty-nine correctly produced
  zero memories. Twenty-nine generated candidates were evidence/current-target
  reviewed: 12 were rewritten into active actionable records and 17 were rejected
  as stale, interim, wave-local, invalid-target, or canonical-contract duplicates.
  The active corpus now covers Java differential verification, unittest discovery,
  secret-scan candidate semantics, POSIX child reaping, upgrade bootstrap imports,
  model-download TLS path census, dependency-version convergence, MCP stdout
  isolation, generated-vs-patched newline handling, tolerant subprocess decoding,
  filename-aware Python parsing, and static-analysis origin checks. Generated
  drafts remain as superseded/rejected provenance; reruns suppress all 29 source
  events and no candidate remains pending.
- Historical corrections were appended to the closed `1sufq` and `1stwm` change docs. Their nine retrospective findings now have honest cycle-1 `repair_start` records. Both closed waves remain closed and their delivery approvals remain withdrawn; independent code-reviewer and QA reverification is still required before those findings can become terminal.
- `1sxxw` is implemented. Random producer identities now hold crash-released OS
  leases; create/prepare transfers its own general bucket and claims only
  provably abandoned peers under one SQLite transaction. Close publication seals
  the exact generation, replaces payload rows with a cumulative floor, retains
  compact event replay tombstones, and reopens into a new phase. Failed lifecycle
  calls do not transfer. The one-time self-host reconciliation moved 280 legacy
  events, cleared all 17 general buckets, and correctly collapsed repeated source
  versions from 10,524,850 gross tokens to 4,454,801 unique pre-wave credit.
- Verification on the complete diff: **5,853 tests across 54 isolated files, all green**; focused telemetry **38 OK**; server context-efficiency **34 OK**; setup **18 OK**; upgrade **302 OK**; docs-lint clean. One intervening canonical run hit the pre-existing background-refresh cross-test timing flake; its exact fixture passed alone and the final canonical rerun was fully green. Live provenance probe for `context_efficiency.py:1` resolves only `1stwj`.
- No commit or close has been performed. The current wave still requires review reconciliation and operator-owned closure.
- Delivery repair pass (2026-07-19): exploration estimates now survive telemetry compaction; failed upgrade cleanup retains both failure and dashboard restart intent and carries it through a full recovery run; the superseded 1svr6 auto-promotion plan/ADR now defer to 1syle; the literal pre-implementation verdict maps to the genuine prepare councils; checkpoint normalization/render/parse/replace is fixture-pinned. A premature `unittest.main()` in `test_memory_records.py` was moved to EOF, increasing the actually executed file from 16 to 141 tests. Canonical `run_tests.py`: **5,873 tests across 55 files, OK**; docs-lint and diff check clean. All 12 findings have cycle-1 repair starts; independent required-lane reverification is the remaining delivery gate.
