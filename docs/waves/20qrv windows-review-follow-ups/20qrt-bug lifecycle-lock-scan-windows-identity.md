# Lifecycle lock link scan keys directories by a zero identity on Windows

Change ID: `20qrt-bug lifecycle-lock-scan-windows-identity`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20qrv windows-review-follow-ups`

## Rationale

`_refuse_lock_links` in `lifecycle_lock.py` walks the record roots to refuse symlinks, junctions and hard links that could alias the lifecycle mutation lock, and to refuse links that lead outside the repository. Its `visited` set is keyed by `st_dev, st_ino` taken from `DirEntry.stat(follow_symlinks=False)`. CPython documents that on Windows a `DirEntry` stat result always has `st_dev`, `st_ino` and `st_nlink` set to zero; only `os.stat` fills them. The scan tops and phase-2 link targets use `os.stat` and get real keys, but every real subdirectory discovered during the walk is keyed `(0, 0)`. After the first subdirectory is pushed, every other directory under every root matches `key in visited` and is skipped.

On Windows the scan therefore inspects one wave folder and nothing else. A junction or symlink to the lock placed in any other wave folder, a directory junction inside a record root that leads outside the repository, and the entry-count bound are all silently not enforced. The hold succeeds with no diagnostic. The only Windows test stubs the link predicate; none models the zero identity. The hazard the scan guards is partly POSIX-specific, but the containment refusals and the advertised junction detection are the contract the docstring and tests claim.

## Requirements

1. On Windows, recover real directory identity with fresh no-follow stat metadata, then reclassify the entry before traversing. If it became a link/name-surrogate, apply existing link policy; if it disappeared, apply existing disappearance handling; permission/I/O failures refuse rather than silently skip. Do not use a following os.stat call to turn a replaced link into an ordinary directory. POSIX keys remain unchanged.
2. Every directory source (scan tops, real DirEntry children, and admitted linked-directory targets) uses one consistent tagged visited-key rule. Use usable device/inode identity when available; never insert (0,0). Otherwise use a tagged normalized canonical path key, preserving containment, alias/cycle handling and separation from numeric keys. Unknown identity is not permission to bypass classification.
3. Preserve the existing two-phase budget contract: phase 1 walks legitimate real record directories; the entry limit applies to phase 2 subtrees reached through links. Do not add a new whole-repository cap. Test zero DirEntry metadata, zero fresh metadata, repeated/cyclic targets, replacement races and errors.
4. Native Windows and drvfs execution are unverified. Tests simulate metadata shapes; no assertion that every drvfs mount exposes useful inodes or link counts. Keep msvcrt locking unchanged.

## Scope

**Problem statement:** the scan's cycle guard collapses the Windows walk to one directory.

**In scope:**

- `push` and `drain` inside `_refuse_lock_links` in `.wavefoundry/framework/scripts/lifecycle_lock.py`
- Tests in `.wavefoundry/framework/scripts/tests/` with a `DirEntry` oracle

**Out of scope:**

- The link predicate itself (already tag-aware; change `20qrs` makes other sites match it)
- The `msvcrt` lock mechanism

## Acceptance Criteria

- [x] AC-1: Windows-shaped zero DirEntry identity with usable fresh no-follow metadata visits all real directories, refuses later-folder lock aliases and outside-leading links, and reclassifies a directory replaced by a link before traversal. Permission/I/O failures do not silently skip it.
- [x] AC-2: Under zero-identity oracles the existing phase-2 linked-subtree entry limit trips; a legitimate phase-1 tree is not newly capped. A zero fresh identity uses canonical-path keys for tops, real children and linked targets without collapsing siblings.
- [x] AC-3: Existing POSIX scan/cycle tests pass unchanged; repeated targets and cycles terminate under both numeric and fallback keys.
- [x] AC-4: Focused tests and authored docs pass with no attributable regression; native Windows/drvfs qualification remains explicitly pending.

## Tasks

- [x] Write the `DirEntry` zero-identity oracle and the failing AC-1 and AC-2 tests.
- [x] Key Windows directories by fresh no-follow metadata with reclassification and consistent tagged real-path fallback across every directory source.
- [x] Note the drvfs `st_nlink` caveat in the Windows support reference.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fix and tests | Implementer | Readiness | Single write owner |
| Delivery review | QA, security | Fix and tests | Security-faithfulness: the scan is a guard |

## Serialization Points

- `.wavefoundry/framework/scripts/lifecycle_lock.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/native-windows-support.md`

## Affected Architecture Docs

N/A. The guard's contract is unchanged; its Windows implementation becomes correct.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The guard does not run today |
| AC-2 | required | Bound is part of the contract |
| AC-3 | required | POSIX must not change |
| AC-4 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Readback: DirEntry zero identities collapse siblings; tops and linked targets use different identity sources. Use fresh Windows no-follow stat with reclassification and tagged inode/path visited keys at every source; preserve the phase-2-only budget and msvcrt mechanism. | MCP current-file reads; implement after 20qrs predicate. Runtime model identity unknown. Zero/fresh identity, replacement/error, repeated target/cycle and budget oracles plus mutants will verify; native Windows/drvfs and final batch gates pending. |
| 2026-10-15 | Planned from Windows source review; no native execution claimed | Current source |
| 2026-10-15 | QRV-RD4 preserves no-follow classification, all visited-key sources and the existing phase-2-only budget. | Bounded readiness repair; owning requirements and ACs |
| 2026-10-15 | Serialization note: `20qrs` edits the `_is_link_entry` predicate in the same file; implement after it, one implementer at a time on `lifecycle_lock.py`. The root-alias refusal in `20tpn` (wave `20tpo`) touches `_link_scan_tops` and `drain` as well and must land after this change. | Cross-wave plan review; no requirement or AC changed |

| 2026-10-15 | Completed fresh Windows no-follow stat and reclassification, tagged inode/canonical-path keys across every push source, and explicit Windows inspection refusals; preserved phase-2-only entry budget and POSIX ordinary-file d_type fast path. | New test_windows_lifecycle_scan: 9 tests green, covering zero cached/fresh identities, later lock/outside links, replacement, EACCES/EIO, disappearance, listing denial, repeated targets/cycles, phase-2 budget and uncapped phase 1. Initial 7-test fixture reproduced scan omissions before source repair. Existing lifecycle-lock-link suite 45 tests green; fresh final rerun after POSIX fast-path preservation recorded separately. |
| 2026-10-15 | Four named scan mutants detected; native support reference records canonical fallback and drvfs identity/link-count limits. AC-1–AC-3 and tasks complete; AC-4 remains open for batch docs/full-suite gates. | `zero-fresh-identity-collapse` → `test_zero_fresh_keys_keep_sibling_and_top_directories_distinct` (1 failure); `fresh-stat-follows-replacement` → `test_fresh_nofollow_reclassifies_replacement_before_traversal` (1 failure); `phase-one-global-cap` → `test_zero_identity_link_subtree_still_counts_and_real_tree_is_not_capped` (1 failure, 1 error); `posix-regular-file-stat-regression` → `test_posix_regular_entries_keep_the_stat_free_fast_path` (1 failure). Zero skips; mutations compiled in memory. No msvcrt mechanism change or native Windows/drvfs execution. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Fresh no-follow stat with reclassification and tagged real-path fallback for zero identities | Real identity where the filesystem has one; still a complete walk where it does not | (a) Key by normalized real path everywhere: loses the hard-link cycle detection POSIX relies on. (b) Key by `os.stat` everywhere: an extra stat per directory on POSIX for no gain. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Extra `os.stat` per directory slows the Windows hold | The walk is bounded by the entry limit; one stat per directory is within it |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
