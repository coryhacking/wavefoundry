# A Docs Link To A Runtime Lock Can Release The Lock

Change ID: `1zv8b-bug docs-link-releases-runtime-lock`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv8c waveforge-seams-and-lock-links

## Rationale

Residual of wave 1zv87 (1zuq7): the code-reading tools now refuse framework lock files, but a committed markdown file under `docs/` (or another record root) that is a symlink or hard link to `.wavefoundry/lifecycle-mutation.lock` is still read by the docs and lifecycle tools. The in-process readers (wave and change discovery, record and memory readers, some `wave_lint_lib` validators; docs lint itself runs in a subprocess) run while the server holds the lifecycle lock, and on macOS and Linux closing any descriptor of a file releases that process's POSIX record lock on it. A lifecycle operation could then lose its lock mid-run, letting another process change wave records at the same time. Guarding each of the forty readers would be fragile; the lock holder can refuse instead.

## Requirements

1. In `lifecycle_lock.lifecycle_mutation_lock`, after a successful acquire and `register_process_hold`, inside the existing `try` (so `finally` releases the lock) and outside `process_hold_guard()`, the hold is refused when:
   - the held handle's `os.fstat(...).st_nlink` is not 1 (a hard link exists anywhere on the volume, for example a `cp -al` backup), or
   - the link scan (Requirement 2) finds a symlink whose resolved target is a runtime lock file (`.wavefoundry/**/*.lock`, compared case-folded as in wave 1zv87).
   The refusal is a new `LifecycleLockLinkRefused(LifecycleLockUnavailable)`, so every existing catch of `(LifecycleLockBusy, LifecycleLockUnavailable)` (`upgrade_wavefoundry.py`, `setup_reconciliation.py`, `server_impl._lifecycle_mutation_lock`) still handles it. `LifecycleMutationBusy.from_lock_refusal` gains a distinct kind so the server reports `lifecycle_lock_link_refused`. The message is path-free apart from the repository-relative link, and gives the remedy (remove the link; for a hard link, remove it and recreate the lock file when no one holds it).
2. The scan covers the record roots from `record_paths.unvalidated_record_roots` (including the archive root; never `load_record_roots`, which would turn a layout error into a lock refusal) plus any other markdown location the census (Requirement 4) finds read in-process under the lock. It uses `os.scandir` and `DirEntry.is_symlink()`, resolving only symlinks (`os.path.realpath`, no open). Directory symlinks are followed, because flat-layout wave discovery (`record_paths._list_subdirs(guarded=False)`) opens wave folders through them: a directory symlink whose target is inside the repository is scanned too, with a visited set of resolved directories so a cycle ends; a directory symlink inside a record root whose target is outside the repository is refused with the same error (its contents cannot be bounded). On this repository the scan adds at most 50 ms per acquisition (measured and recorded).
3. The upgrade bridge's `_StrictLock(LIFECYCLE_LOCK, style="record")` takes the lifecycle lock outside the canonical acquisition; the census records whether markdown is read in-process while it is held and applies the same check there, or records why not.
4. A census in the Progress Log classifies every runtime lock the server, the CLI or the upgrade bridge holds in-process by style: record-style (`lockf`) locks, which a close of another descriptor releases (the lifecycle lock, `index-build.lock`, the bridge `_StrictLock`), and flock-style locks, which it does not. For each record-style lock held while markdown is read it names the readers and the check that covers them (`index-build.lock` is already covered by `indexer._walk_target_is_runtime_lock` from wave 1zv87).
5. The case-folded runtime-lock path test moves to one helper in `runtime_lock.py` (which stays stdlib-only: it is imported before the tool environment is activated), used by the acquisition scan, `server_impl._is_runtime_lock_path(root, path)` (resolved paths) and `indexer._walk_target_is_runtime_lock(path, root, entry_stat, lock_cache)` (resolves for itself); both call shapes are kept and the existing parity test stays green. The one allowed copy is the standalone, stdlib-only upgrade bridge (`upgrade_bridge_bootstrap.py`, which cannot import framework modules): if Requirement 3 applies the check there, it is a copy pinned to the shared helper by a parity test.
6. `docs/architecture/layering-rules.md` records the `lifecycle_lock` -> `record_paths` edge and `current-state.md` the acquisition check. `docs/architecture/threat-model.md` gains a row for the runtime-lock reader threat (waves 1zv87 and 1zv8c). CHANGELOG gets one Security bullet under `## [1.29.0]` without reproduction steps.

## Scope

**Problem statement:** a markdown link to a lock file lets an in-process docs read release the lifecycle lock.

**In scope:**

- The acquisition check, the refusal type and its mapping, the shared predicate, the census, threat model, tests, CHANGELOG.

**Out of scope:**

- Per-reader guards in the markdown walkers.
- Changing the lock style (the upgrade bridge and older runners take `lockf`).

## Acceptance Criteria

- [x] AC-1: With a committed markdown symlink to the lifecycle lock in a record root (and, separately, reached through an in-repository directory symlink under `docs/waves/`), a lifecycle tool refuses with `lifecycle_lock_link_refused` naming the link, writes nothing, and leaves the lock released (a child process can then acquire it); `wf setup` and the upgrade lock sites report the refusal without a traceback.
- [x] AC-2: With a hard link to the lock file, the same refusal happens; a fresh lock file (link count 1) is accepted.
- [x] AC-3: Ordinary file and directory symlinks inside the repository that lead to no lock are accepted, a directory-symlink cycle ends, a record-root directory symlink to a target outside the repository is refused, and the scan's measured cost on this repository is recorded and within 50 ms.
- [x] AC-4: The census is recorded, the shared predicate replaces both copies with the parity test green, the threat-model row, the `layering-rules.md` edge, the `current-state.md` sentence and the CHANGELOG bullet exist; the change's own tests pass and no failure elsewhere is attributable to this change.

## Tasks

- [x] Acquisition check, `LifecycleLockLinkRefused` and the `from_lock_refusal` kind
- [x] Link scan with directory-symlink following
- [x] Bridge `_StrictLock` decision
- [x] Shared lock-path predicate
- [x] In-process lock census by style
- [x] Tests (including setup and upgrade reporting) and timing measurement
- [x] Threat model and CHANGELOG

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| lock-link-guard | implementer | — | |


## Serialization Points

- `.wavefoundry/framework/scripts/lifecycle_lock.py`, `.wavefoundry/framework/scripts/runtime_lock.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`, `.wavefoundry/framework/scripts/setup_reconciliation.py`, `.wavefoundry/framework/scripts/record_paths.py`, `.wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py`, `docs/architecture/threat-model.md`, `docs/architecture/layering-rules.md`, `docs/architecture/current-state.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` has no entry for the runtime-lock reader threat yet; add one covering waves 1zv87 and 1zv8c. `docs/architecture/layering-rules.md`: record the new edge `lifecycle_lock` -> `record_paths` (and through it `vocabulary_profile`), which puts the record layout inside the lock primitive, and restate that `runtime_lock` stays stdlib-only. `docs/architecture/current-state.md`: one sentence that lifecycle-lock acquisition now also checks for links to the lock (the lock protocol between holders, its file, offset and style, is unchanged).

## Platform Behavior

macOS, Linux and WSL2 use POSIX record locks, where the release-on-close behaviour applies; the refusal prevents it. On Windows the lock is held per handle and a second handle's close does not release it, but the check runs on every platform so a repository behaves the same everywhere; Windows reports `st_nlink` for NTFS hard links, and symlink detection uses the same `scandir` path.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the reported residual |
| AC-2 | required | hard links bypass a path check |
| AC-3 | required | no false refusals; bounded cost |
| AC-4 | required | census, shared predicate, release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Delivery repairs DEL-1 to DEL-8 (two rounds, independently reverified): identity-based lock judgment for checkout spellings, scan of all of `.wavefoundry/` except a project-local venv, two-phase walk so only link-reached entries count toward the bound, junction detection by reparse tag, spec, current-state, threat-model and CHANGELOG aligned. Gapfill: implementers and reviewers worked in scratch copies with shell reads, AST probes and audit-hook censuses, because the index reflects the repository tree rather than the scratch trees under test and the work was mostly executed probes (child lockf, mutation, timing); retrieval tools were not the right instrument for that | final reverification rev8c3: 420 tests across 12 files; repo receipt 11277 OK |
| 2026-10-05 | Implemented: `runtime_lock.is_runtime_lock_path` (shared, stdlib-only); `lifecycle_lock.LifecycleLockLinkRefused(LifecycleLockUnavailable)` with `link_rel` and cause `hard_link`/`lock_link`/`outside_link`/`link_scan_limit`; `_refuse_lock_links` after acquire and `register_process_hold`, inside the release-protected `try`; server `from_lock_refusal` kind `link_refused` and `lifecycle_lock_link_refused` response (server reaches the predicate through `lifecycle_lock` so a reload never purges `runtime_lock`); link-specific wording at the setup and upgrade catch sites; `indexer._walk_target_is_runtime_lock` on the shared predicate. 1zv87 backstop fixtures now create their links after taking the hold | scratch impl8b: 561 OK across 11 files; `test_lifecycle_lock_links.py` 25 tests |
| 2026-10-05 | Scan scope and bound: record roots from `unvalidated_record_roots` plus the archive root (recursive; an out-of-repository directory link is refused), `docs/` (recursive; an out-of-repository directory link is skipped), and the repository root's own entries (not recursive). Only link entries are resolved; in-repository directory links are followed with a visited set; a followed link never enters `.git` or `.wavefoundry/index`; `_LINK_SCAN_ENTRY_LIMIT = 50_000` listed entries refuses with `link_scan_limit` (this repository lists 3,170). Measured cost on this repository, macOS warm: scan median 17.2-17.3 ms (min 16.1, max 19.4); full acquire, scan and release median 17.7 ms, max 23.3 ms; within the 50 ms budget | 3 rounds of 20 runs |
| 2026-10-05 | Census by lock style: record-style (released by another descriptor's close) are the lifecycle lock (covered by this check), `index-build.lock` (covered by `indexer._walk_target_is_runtime_lock`, wave 1zv87), the `review_evidence` transient probe (acquire then release, nothing read) and the bridge `_StrictLock` (reads no markdown: operator selection, archives, `VERSION`, `UPGRADE-PROTOCOL.json`; no check or copy needed, Requirement 3 decision). `test-run.lock` is flock on POSIX (record only on Windows, where a close does not release). Publication, dashboard, dependency-install, scanner-skips, index-source-guard, context-efficiency, codebase-map and legacy upgrade root locks are flock | implementer census |
| 2026-10-05 | Mutation probes killed (15): check removed, link count removed, directory links not followed, visited set removed, out-of-repository record-root link allowed, entry bound removed, `.git`/index skip removed, archive not scanned, root entries not scanned, predicate not case-folded, setup branch removed, upgrade branch removed, server kind not mapped, server not on the shared predicate. Docs: threat-model row, `layering-rules.md` edge, `current-state.md` paragraph and the CHANGELOG Security bullet added | scratch impl8b-mut |
| 2026-10-05 | Architecture review folded in: the `lifecycle_lock` -> `record_paths` edge recorded in `layering-rules.md` (A1); `runtime_lock` stays stdlib-only (A2); the bridge copy is the one allowed exception, pinned by parity (A3); `current-state.md` notes the content check at acquisition (A5) | architecture review |
| 2026-10-05 | Readiness review folded in: refusal subclasses `LifecycleLockUnavailable` with its own kind so upgrade, setup and the server handle it (B2); directory symlinks followed with a visited set, out-of-repository ones in record roots refused (B3); census by lock style including the bridge `_StrictLock` (N9); `fstat` on the held handle inside the release-protected region (N10); `unvalidated_record_roots` (N11); scope corrected, lint runs in a subprocess (N13); predicate keeps both call shapes (N14); threat-model row is new (D1). Measured scandir of `docs/`: 3,137 entries, 13-17 ms warm on macOS | readiness review |
| 2026-10-05 | Planned from the wave 1zv87 residual | `lifecycle_lock.lifecycle_mutation_lock` read |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Check at lock acquisition, not in each markdown reader | one choke point covers about forty walk sites, the server and the CLI | per-reader guards |
| 2026-10-05 | Detect hard links by the lock file's own link count | constant cost; no tree-wide `stat` | hashing every docs file's identity |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The scan slows every lifecycle operation | scandir without stat; measured budget in AC-3 |
| An existing repository links a record folder outside the repository | refused with a clear remedy; such a link already escapes the containment other tools enforce |
| A link created after the check | committed-content threat; same window as wave 1zv87's readers |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
