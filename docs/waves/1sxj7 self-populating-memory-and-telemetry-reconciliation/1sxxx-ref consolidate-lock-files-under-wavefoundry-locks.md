# Consolidate dedicated lock files under `.wavefoundry/locks/`

Change ID: `1sxxx-ref consolidate-lock-files-under-wavefoundry-locks`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-19
Wave: `1sxj7 self-populating-memory-and-telemetry-reconciliation`

## Rationale

The framework's dedicated lock files are scattered:
`.wavefoundry/review-evidence-adoptions.lock`, `.wavefoundry/dashboard-start.lock`, and
`.wavefoundry/dashboard-server.lock` sit at the `.wavefoundry/` root, and the new
context-efficiency producer leases live under
`.wavefoundry/logs/context-efficiency-producers/`. There is no single, discoverable home or
naming convention. Consolidating the dedicated lock files under one
`.wavefoundry/locks/` folder gives one place to find and gitignore lock carriers and one
convention for future locks. The directory is runtime coordination state, not a recovery
surface: operators must not delete it while a lock may be held.

One deliberate exception: `.wavefoundry/index/index-build.lock` stays co-located with the
index. It is resource-scoped coordination state with established index status, crash-owner
metadata, and recovery semantics; its presence does not indicate that a build is running,
and the index directory must not be deleted while the OS lock is held. The other locks'
root/log placement is not load-bearing (the producer leases in particular are self-healing:
an abandoned lease with no live holder is probed, found free, and unlinked on the next
flush).

This is primarily a location/organization refactor. The same OS locks (`flock` /
`msvcrt.locking`) are held on the same logical resources, but the upgrade path must perform
a one-way cutover to the new canonical paths. The dashboard start lock is simplified from a
transient, post-success-unlinked file to a persistent OS-lock carrier: its lock state, not
pathname existence, remains authoritative. Note: locks held *on* a resource file (the SQLite
seqlocks/fences in `index_state_store.py`, `memory_records.py`, `graph_query.py`, etc.) are
intrinsic to those files and are NOT in scope; only dedicated `.lock` carriers move.

## Requirements

1. **New home.** Dedicated lock files live under `.wavefoundry/locks/`:
   - context-efficiency producer leases -> `.wavefoundry/locks/producers/<producer_id>.lock`
     (a short subfolder, since these are many and ephemeral),
   - adoption-ledger lock -> `.wavefoundry/locks/review-evidence-adoptions.lock`,
   - dashboard launch mutex -> `.wavefoundry/locks/dashboard-start.lock`,
   - dashboard singleton lock -> `.wavefoundry/locks/dashboard-server.lock`.
2. **Index lock unchanged.** `.wavefoundry/index/index-build.lock` stays where it is
   (resource-scoped to the index and governed by the existing held/status contract).
3. **Ship at the final location, no move-later.** The producer leases were introduced by the
   sibling change `1sxxw` (still open in this wave). Coordinate so the producer-lease constant
   ships directly at `.wavefoundry/locks/producers/`, rather than landing under
   `.wavefoundry/logs/…` and being relocated afterward.
4. **One shared runtime-lock engine.** Add a small framework-internal lock module used by
   every in-scope dedicated project-runtime OS lock. It owns canonical parent creation,
   binary file opening, POSIX/Windows acquire and release, blocking/non-blocking mode,
   configurable lock-byte offset/range, handle closure, held probing, and in-place JSON
   process metadata (`pid`, timestamps, and caller-supplied fields). The default is a
   persistent lock inode; deletion is never an implicit generic cleanup action. Acquisition
   failures are typed (busy versus I/O failure) rather than collapsed into a false
   not-held/success result.
5. **Policy stays with resource wrappers.** Thin dashboard, adoption, producer, and index
   wrappers configure and compose the shared engine. The engine does NOT infer producer
   abandonment/reaping, dashboard launch ordering, adoption re-entrancy, index stale-owner
   classification, `ended_at` interpretation, or upgrade migration policy. The index lock
   keeps its current path and record-lock/F_GETLK status contract while reusing common
   open/acquire/release/metadata mechanics where behavior is exactly equivalent.
6. **Creator-owned lazy provisioning.** The shared lock engine resolves only its canonical
   path and calls `lock_path.parent.mkdir(parents=True, exist_ok=True)` immediately before
   opening/creating the lock. Setup is not a prerequisite; a fresh install with no
   `.wavefoundry/locks/` directory works, and the directory/subdirectory is created lazily by
   the first lock creator. `.gitignore` covers the canonical `.lock` paths (confirm they are
   not accidentally tracked).
7. **One-way upgrade cutover; no fallback.** Upgrade records whether the dashboard was
   running and its port, stops it through the verified dashboard-stop path, and confirms the
   old dashboard lifetime/start locks are not held before removing the old root-level files.
   The adoption lock must also be acquirable before cutover; a held old lock blocks upgrade
   rather than allowing split serialization. Upgrade then installs code that uses only
   `.wavefoundry/locks/`; old paths are never read or recreated. After successful cleanup it
   restarts the dashboard on the prior port only when it was previously running. A failed
   upgrade retains the restart intent in `upgrade-in-progress.json` and leaves the dashboard
   stopped until successful recovery/cleanup. Existing MCP/lifecycle writers must be
   quiesced and reloaded for the no-compatibility cutover.
8. **Persistent dashboard launch mutex.** `dashboard-start.lock` remains the cross-process
   gate spanning the parent launcher's check -> spawn -> readiness window, but its file is no
   longer unlinked after success. OS-lock ownership is authoritative; an unlocked leftover
   file is harmless and re-acquirable. Preserve the post-acquire state recheck before spawn.
9. **Convention documented.** Record the rule: a dedicated lock file lives under
   `.wavefoundry/locks/`, EXCEPT the atomicity token for a nuke-and-rebuild resource directory
   (the index), which stays co-located with that directory.
10. **Lock taxonomy explicit.** `.wavefoundry/upgrade-in-progress.json` remains a root-level
   upgrade transaction/state marker, not a dedicated OS-lock carrier. Locks intrinsic to
   SQLite/Lance/resource files and the framework test-run lock remain outside this runtime
   path convention.
11. **Steady-state behavior preserved.** Locking, crash-release, reaping, dashboard singleton,
   adoption serialization, and producer contracts behave identically after cutover. Existing
   path assertions are updated, and upgrade/start concurrency is verified directly.

## Scope

**Problem statement:** dedicated lock files are scattered across `.wavefoundry/` root and a
`logs/` subfolder, while their OS-specific open/acquire/release/metadata mechanics are
duplicated across several modules. Consolidate the non-index paths under
`.wavefoundry/locks/` and make one bounded runtime-lock engine the mechanical authority.

**In scope (edited under `framework_edit_allowed`):**
- New shared runtime-lock module — typed cross-platform lock handle, lazy parent creation,
  blocking/non-blocking acquisition, byte-range configuration, held probe, persistent inode,
  and in-place process metadata.
- `context_efficiency.py` — `PRODUCER_LEASE_RELATIVE_DIR` -> `.wavefoundry/locks/producers`
  (coordinated with `1sxxw`) and producer lease mechanics delegated to the shared engine;
  abandonment/reap transaction remains local.
- `review_evidence.py` — adoption lock path -> `.wavefoundry/locks/`; OS locking delegated to
  the shared engine; thread-local re-entrancy remains local.
- `dashboard_lib.py` / `dashboard_server.py` — dashboard paths -> `.wavefoundry/locks/`;
  acquire/release/metadata mechanics delegated to the shared engine.
- `indexer.py` — keep the index lock path and status semantics; reuse the shared engine only
  for mechanically equivalent file/record-lock/metadata operations, with regression pins for
  F_GETLK holder PID and interrupted-build reporting.
- `server_impl.py` — retain the dashboard launch mutex but remove its post-success unlink
  lifecycle; preserve check -> lock -> recheck -> spawn ordering.
- Upgrade cutover — stop/migrate/restart dashboard state, gate on the old adoption lock, and
  retain restart intent across failed/recovered upgrade phases.
- Creator-owned lazy provisioning and `.gitignore` verification for `.wavefoundry/locks/`.
- Docs — the lock-location convention (architecture note or the relevant reference).
- Tests — path assertions, creator-with-missing-parent coverage, upgrade cutover, and
  dashboard/adoption concurrency.

**Out of scope:**
- **`.wavefoundry/index/index-build.lock`** — intentionally left co-located.
- **Locks held on a resource file** (SQLite seqlocks/fences) — intrinsic to those files.
- **`.wavefoundry/upgrade-in-progress.json`** — stateful upgrade transaction marker, not an
  OS-lock carrier.
- **Runtime fallback to old paths or dual-path compatibility** — explicitly rejected; upgrade
  performs one canonical cutover.
- **A universal policy engine.** The common module does not decide when a lock is stale,
  whether a process should be killed, which domain transaction is protected, or whether an
  unlocked file should be removed.

## Acceptance Criteria

- [x] AC-1: The producer leases, adoption lock, dashboard start lock, and dashboard server lock resolve under `.wavefoundry/locks/` (producer leases in `.wavefoundry/locks/producers/<id>.lock`); `RuntimeFileLockTests.test_resource_wrappers_create_only_canonical_paths_from_absent_directory` asserts every path. (required)
- [x] AC-2: `.wavefoundry/index/index-build.lock` is unchanged and pinned by the shared wrapper-path fixture. (required)
- [x] AC-3: `runtime_lock.py` is the shared mechanical implementation for parent creation, file opening, POSIX/Windows acquire/release, byte-range selection, typed busy/I/O outcomes, held probing, handle cleanup, and in-place JSON metadata. The 10-test engine suite plus dashboard Windows-sentinel and crash-leftover fixtures exercise contention, release, metadata inode identity, platform behavior, and error propagation. (required)
- [x] AC-4: Every migrated wrapper succeeds from an absent `.wavefoundry/locks/` tree through creator-owned lazy parent provisioning; setup does not provision the directory. (required)
- [x] AC-5: Resource policy remains in thin wrappers: producer abandonment/reap, dashboard launch handoff, adoption re-entrancy, and index F_GETLK/stale-owner/interrupted-build regressions all pass. (required)
- [x] AC-6: Upgrade performs the one-way, no-fallback cutover before extraction, stops and conditionally restarts the dashboard on its prior port, retains the failed lock and restart intent until a successful recovery cleanup, carries that intent into a full replacement run, checks all old carriers before deleting any, and blocks on held adoption/dashboard/producer locks. `RuntimeLockCutoverMigrationTests`, `test_failed_cleanup_retains_dashboard_restart_intent`, `test_full_retry_preserves_failed_dashboard_restart_intent`, and successful cleanup restart tests execute the paths. (required)
- [x] AC-7: Dashboard start serialization remains race-safe with a persistent `dashboard-start.lock`; the existing double-spawn/crash-leftover fixtures and the five-test persistent-start focused suite pass. (required)
- [x] AC-8: Cross-process adoption serialization and producer claim/delete/unlink behavior remain intact; the 79-test review-evidence and 38-test context-efficiency suites pass, including concurrent abandoned-producer claims. (required)
- [x] AC-9: `.gitignore` already covers `.wavefoundry/**/*.lock`; `data-and-control-flow.md` and `domain-map.md` document the canonical paths, persistent-carrier rule, index exception, upgrade marker taxonomy, and read-only dashboard ownership. (important)
- [x] AC-10: The sibling `1sxxw` producer leases ship directly at `.wavefoundry/locks/producers/` and delegate mechanics to the shared engine. (required)
- [x] AC-11: The structural tests reject raw steady-state platform-lock duplication and old-path residue, leaving only the index F_GETLK policy helper and pre-extract migration probe as explicit exceptions. Canonical verification: 5,868 tests across 55 isolated files, OK; docs-lint clean; diff check clean. (required)

## Tasks

- [x] Implement and directly test the shared runtime-lock engine.
- [x] Move producer-lease dir constant to `.wavefoundry/locks/producers` (coordinated with `1sxxw`).
- [x] Move the adoption-ledger, dashboard-start, and dashboard-server lock paths under `.wavefoundry/locks/`.
- [x] Migrate dashboard/adoption/producer and the mechanically-equivalent index operations to
  the shared engine; retain thin resource-policy wrappers.
- [x] Make every lock creator lazily create its own parent through the shared engine; verify `.gitignore` coverage.
- [x] Implement the one-way upgrade stop/cutover/restart path with durable restart intent and no runtime fallback.
- [x] Keep the dashboard launch mutex as a persistent OS-lock carrier; remove only its transient-unlink machinery.
- [x] Document the lock-location convention and explicit index/upgrade-marker taxonomy.
- [x] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| shared-engine | framework | — | implement typed cross-platform mechanics; no domain stale/reap/ordering policy |
| relocate | framework | shared-engine | move producer, adoption, dashboard-start, and dashboard-server locks; migrate wrappers |
| index-wrapper | framework | shared-engine | retain path/F_GETLK/interruption contract; reuse only equivalent mechanics |
| upgrade-cutover | framework | relocate | stop dashboard; gate old locks; remove old paths; persist restart intent; restart after successful cleanup |
| simplify-start-lock | framework | relocate | keep launch mutex; remove post-success unlink only |
| document | framework | shared-engine, relocate, upgrade-cutover | gitignore + engine boundary + path convention + explicit taxonomy |
| verify | framework | shared-engine, relocate, index-wrapper, upgrade-cutover, simplify-start-lock | engine, absent-parent, concurrency, migration, residue, and policy-regression tests |


## Serialization Points

- `context_efficiency.py` (producer-lease path) overlaps `1sxxw`; coordinate to ship the final
  location once. Dashboard relocation and upgrade cutover are one serialization unit: do not
  land the new dashboard paths without the stop/migrate/restart upgrade behavior.

## Affected Architecture Docs

The relevant architecture reference records the canonical lock paths, shared-engine boundary,
resource-policy ownership, and upgrade cutover. Steady-state coordination behavior is
preserved; the dashboard start-lock file lifecycle and upgrade dashboard lifecycle change
explicitly as planned.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The consolidation itself, including the launch mutex |
| AC-2 | required | Preserve the established resource-scoped index-lock contract |
| AC-3 | required | One engine must own the duplicated cross-platform mechanics honestly |
| AC-4 | required | Lock creators cannot depend on setup having provisioned a directory |
| AC-5 | required | The abstraction must not absorb or alter resource policy |
| AC-6 | required | Existing projects need an atomic one-way upgrade, not runtime fallback |
| AC-7 | required | Preserve no-double-spawn semantics while simplifying file lifecycle |
| AC-8 | required | Preserve adoption and producer concurrency contracts |
| AC-9 | important | The discoverable convention needs an honest exhaustive taxonomy |
| AC-10 | required | Avoid ship-then-move/refactor churn on new code |
| AC-11 | required | No duplicated mechanism, stale path, or behavioral regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-19 | Change doc authored on operator direction: consolidate non-index dedicated lock files under `.wavefoundry/locks/`; keep the index build lock co-located; short `producers/` subfolder. NOT to be implemented until the concurrent `1sxxw`/memory work settles, and coordinated with `1sxxw` for the producer-lease path | Scattered locks: `.wavefoundry/review-evidence-adoptions.lock`, `.wavefoundry/dashboard-server.lock`, `.wavefoundry/logs/context-efficiency-producers/*.lock`; index lock at `.wavefoundry/index/index-build.lock` |
| 2026-07-19 | Pre-implementation review repaired the plan: added the omitted dashboard launch mutex; replaced unsafe wipe/recovery and inaccurate index-lifecycle wording; made parent creation the responsibility of every lock creator; defined a one-way upgrade that stops/migrates/restarts the dashboard with no runtime fallback; retained `dashboard-start.lock` as a persistent launch mutex while removing its cosmetic unlink lifecycle; classified `upgrade-in-progress.json` explicitly | Current start flow holds `dashboard-start.lock` across parent spawn/readiness until the child owns `dashboard-server.lock`; dashboard server lock is also the metadata store; upgrade currently detects but does not stop the dashboard; `.gitignore` already covers `.wavefoundry/**/*.lock` |
| 2026-07-19 | Operator expanded the refactor to one generic runtime-lock handler. Plan bounded the abstraction to shared mechanics—lazy parent creation, cross-platform acquire/release, blocking mode, byte range, held probe, handle lifecycle, typed errors, and in-place metadata—while keeping reaping, launch ordering, adoption re-entrancy, and index interruption semantics in thin resource wrappers | Duplicated mechanics verified in `dashboard_lib.dashboard_lock`, `review_evidence._adoption_write_lock`, `context_efficiency._try_lock_lease`/`_unlock_lease`, and `indexer._index_build_lock`; index uses record-lock/F_GETLK and therefore remains a policy-specialized wrapper |
| 2026-07-19 | Focused readiness amendment passed and implementation began | Code-grounded review verified the dashboard check → launch-mutex → recheck → spawn → lifetime-lock handoff, in-place metadata requirement, adoption/producer contention paths, and the index F_GETLK exception; `wave_prepare(mode="dry_run")` reports seven admitted changes with lint/garden and council verdict valid |
| 2026-07-19 | Implementation complete: added the bounded shared engine; moved producer, adoption, and dashboard carriers to their canonical paths; retained the index lock in place; made every creator self-provisioning; removed dashboard-start unlink; and added the pre-extract stop/check/delete plus cleanup restart migration | Focused suites: runtime lock 10, dashboard 175, packaging 95, setup 18, context efficiency 38, review evidence 79, upgrade 307, index-lock 18, persistent dashboard start 5; canonical `run_tests.py`: 5,868 tests across 55 files, OK; `wave_validate`: docs-lint clean |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-19 | Consolidate dedicated lock files under `.wavefoundry/locks/` | One discoverable home + convention for locks that are not lifecycle-coupled to a resource dir | Leave scattered (rejected — no convention); move ALL locks including the index (rejected — the index build lock must live/die with the index dir) |
| 2026-07-19 | Keep `.wavefoundry/index/index-build.lock` co-located | It is resource-scoped index coordination state with an established persistent metadata/status contract | Move it too (rejected — separates an established resource-scoped coordination contract) |
| 2026-07-19 | Short `producers/` subfolder for the many ephemeral producer leases | Keeps the top of `locks/` uncluttered; self-healing leases are fine anywhere | Flat in `locks/` (rejected — clutter); keep the long `context-efficiency-producers` name (rejected — operator asked for shorter) |
| 2026-07-19 | Every lock creator lazily creates its own parent | A lock helper must work on a fresh install and cannot depend on setup/upgrade ordering | Eager setup provisioning (rejected — unnecessary hidden precondition) |
| 2026-07-19 | Keep `dashboard-start.lock`, but make its file persistent | The parent launcher and child lifetime owner are different processes; the mutex closes the handoff window. Persistent OS-lock carriers are crash-safe and simpler than post-success unlink | Remove the launch gate (rejected — permits duplicate child spawns); inherited-fd/socket handoff (rejected — disproportionate and cross-platform fragile); retain transient unlink (rejected — cosmetic complexity once locks have a dedicated directory) |
| 2026-07-19 | Upgrade stops, cuts over, and conditionally restarts the dashboard; no old-path fallback | The running dashboard holds and rewrites the old lock inode. A canonical-only upgrade requires quiescence before removing it | Runtime fallback/dual paths (rejected by operator); migrate while dashboard runs (rejected — split-lock/split-metadata risk) |
| 2026-07-19 | Introduce one shared runtime-lock engine with thin policy wrappers | Parent creation, OS branching, byte selection, acquire/release, metadata, and cleanup are duplicated and should have one tested implementation; resource semantics are not interchangeable | Keep duplicated helpers (rejected — repeated platform bugs/behavior drift); universal lock-policy manager (rejected — would hide materially different stale/reap/interruption contracts) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A missed path reference leaves a lock in the old location | Path-asserting tests per lock; grep sweep for old paths |
| Churn against `1sxxw`'s in-flight producer-lease code | Coordinate with the concurrent agent; ship the producer-lease path once at the final location (AC-6) |
| `.wavefoundry/locks/` is absent on a fresh install | Every creator performs idempotent parent mkdir immediately before open; absent-parent tests |
| A running old dashboard keeps the old inode locked or recreates old metadata | Stop and verify release before cutover; restart only under upgraded code after successful cleanup |
| Old MCP writers serialize on the retired adoption lock | Upgrade requires lifecycle-writer quiescence/reload and blocks if the old adoption lock is held |
| Deleting lock files is mistaken for releasing locks | Document OS-lock state as authority and prohibit wholesale lock-directory cleanup |
| Generic handler grows into a policy-heavy abstraction or silently changes a specialized lock | Keep a narrow mechanical API; thin wrappers own policy; parity tests pin each existing contract; structural census allows explicit policy helpers |
| Generic metadata writing replaces an inode and orphans a held lock | In-place truncate/write only; identity-preservation test; no generic atomic-rename writer |
| `.wavefoundry/locks/` accidentally tracked in git | Verify the managed `.wavefoundry/**/*.lock` rule covers every canonical path |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
