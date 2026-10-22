# Compare Pack File Identities Taken by Different Stat Calls Without ctime

Change ID: `21alh-bug verified-pack-identity-mixes-fstat-and-lstat`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-21
Wave: 21cw4 windows-pack-setup-root-and-record-hardening

## Rationale

A downstream distribution upgrading 1.34.0 to 1.35.0 on native Windows 11 (NTFS, Python 3.12.10) was refused before any change with `upgrade_protocol_invalid: cannot freeze selected feature pack: verified private pack changed before validation` (exit 3). Verified at `1c5ba851`:

- `_stage_pack_for_consumption` (`.wavefoundry/framework/scripts/upgrade_wavefoundry.py:344`) records `copied_identity` from `os.fstat()` on the still-open write handle, then (`:350`, `:354`) compares it with `_pack_entry_identity(staged)`, which uses `lstat()` on the path after close.
- `_pack_entry_identity` (`:215`) includes `st_ctime_ns`. Their standalone repro of the same sequence differed in 9 of 10 runs, always only in `st_ctime`; device, inode, size and mtime matched.
- `_cleanup_verified_pack` (`:283`) compares a fresh `os.fstat()` of an opened handle with the path-derived identity in the same way, so fixing staging alone moves the refusal to cleanup.
- The index-guard durable pack helpers in `.wavefoundry/framework/scripts/upgrade_extensions.py` (`_guard_file_identity`) carry the same five fields and mix handle and path snapshots in `_read_guard_pack`, `validate_index_guard_durable_pack` and the publication re-check.

The code dates from `57f7cecc` (2026-10-15); a 1.34 upgrade passing the same step was chance. The operator worked around it with a local patch that drops ctime from the identity.

## Product Intent

Operators upgrading on native Windows get an upgrade that stages, validates and cleans up the verified pack without a false "changed" refusal, while a pack that is actually replaced, resized or rewritten between snapshots is still refused. Before: a deterministic-in-practice refusal on Windows with Python 3.12. After: the same upgrade proceeds; POSIX behaviour is unchanged. Boundaries: the proof shape recorded in the upgrade lock stays five fields, so locks written by 1.35.0 remain readable; no other ownership check is relaxed. AC-1 with AC-3 tests whether the intent was established.

## Requirements

1. The comparison set is derived by rule: every identity comparison in `upgrade_wavefoundry.py` and `upgrade_extensions.py` whose two sides come from different stat kinds, one from an open handle (`os.fstat`, or a helper returning the opened handle's stat) and one from a path (`lstat`, `os.stat` with or without `dir_fd`). A recorded proof takes the kind of the stat it was taken from: the staging proof `identity` is path-derived (`lstat`); the index-guard durable proof is handle-derived (`bind` receives an `os.fstat` result). As found at `1c5ba851` the set is: staging `copied_identity` (handle) against `_pack_entry_identity(staged)` (path), twice; cleanup's opened-handle check against the path-derived `current`; `_read_guard_pack`'s two `entry`/`path.lstat()` against `opened` checks; `validate_index_guard_durable_pack`'s handle-derived proof against `entry = path.lstat()`; and the publication re-check of `entry = target.lstat()` against `current = os.fstat(fd)`. The rule governs where this list is incomplete.
2. Each comparison in that set ignores ctime and otherwise compares exactly the fields it compares today; existing exclusions (for example the `[1:]` comparisons that skip device) stay. Same-kind comparisons are unchanged.
3. The recorded proof keeps its five-field shape, and readers of an existing proof keep accepting it.
4. A pack whose inode, size or mtime differs between the compared snapshots is still refused with the existing message.

## Scope

**Problem statement:** handle-derived and path-derived stat results disagree on ctime on Windows with Python 3.12, so the verified-pack checks refuse an unchanged file.

**In scope:**

- A shared helper (or equivalent) for the cross-kind comparison in both modules, applied to every comparison Requirement 1 derives.
- Tests that fail on the current code and pass after the fix.

**Out of scope:**

- The separate cleanup retention reported as "ownership proof is unproven" (`upgrade_wavefoundry.py:243`): it fires before any stat, so it has a different cause. We are asking the reporter for the full retained line; a later change if the evidence shows a defect.
- Changing the proof shape or dropping ctime from same-kind comparisons.
- Any change to what the upgrade copies, validates or deletes.

## Acceptance Criteria

- [x] AC-1: With a patched stat boundary where handle-derived stats differ from path-derived stats only in `st_ctime_ns` (the platform cannot be forced), staging returns the verified copy and cleanup removes it; on the current code the same fixture refuses both.
- [x] AC-2: With the handle snapshot differing in inode, size or mtime, staging is still refused with "verified private pack changed before validation" and cleanup still retains the file.
- [x] AC-3: For every comparison Requirement 1 lists, a test drives its public path under the same ctime-only patched boundary and passes; on the current code each of those tests fails. Cleanup's same-kind check (the path-derived stored proof against the path-derived `current`), which compares ctime today, still refuses when the later path stat alone carries a different ctime (injected on the path-stat side).
- [x] AC-4: A five-field proof recorded by the 1.35.0 code is accepted by the new cleanup and index-guard readers.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the cross-kind identity comparison and apply it to every comparison Requirement 1 derives in both modules.
- [x] Add the ctime-only, real-change, same-kind and old-proof fixtures for each listed comparison.
- [x] Open `## [Unreleased]` in `CHANGELOG.md` (the wave's first entry) and add this change's Fixed entry.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                  |
| ---------- | ----------- | ---------- | -------------------------------------- |
| fix        | implementer | none       | shared comparison in both modules      |
| tests      | implementer | fix        | stat-boundary injection per comparison |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: the fix is confined to identity comparison inside the upgrade runner's existing pack ownership checks; no boundary, flow or verification seam changes.

## Platform Behavior

Native Windows: the reported failure; handle and path stat results may differ in ctime, which the cross-kind comparisons now ignore. macOS, Linux and WSL2: ctime agrees between `fstat` and `lstat` for the same file, so outcomes are unchanged; the remaining four fields still bind the identity. The fix cannot protect the install that delivers it: the upgrade to the fixed release is staged by the installed runner, so a Windows operator keeps the local workaround until the fixed release is installed.

## AC Priority


| AC   | Priority  | Rationale                              |
| ---- | --------- | -------------------------------------- |
| AC-1 | required  | the reported refusal                   |
| AC-2 | required  | real changes still refused             |
| AC-3 | required  | every cross-kind comparison covered    |
| AC-4 | important | locks written by 1.35.0 stay readable  |
| AC-5 | required  | change-local verification              |


## Progress Log


| Date       | Update  | Evidence                                              |
| ---------- | ------- | ----------------------------------------------------- |
| 2026-10-21 | Planned | distribution 1.35.0 Windows upgrade report, verified at `1c5ba851` |
| 2026-10-21 | Readiness amendments: proof provenance and the as-found comparison list in Requirement 1; existing field exclusions kept (Requirement 2); AC-3 drives each comparison instead of a static census; Unreleased section task. | readiness code-reviewer and qa-reviewer findings |
| 2026-10-21 | Implemented: `_cross_kind_pack_identity_matches` (`upgrade_wavefoundry.py`) for both staging checks and cleanup's opened-handle check; `_guard_cross_kind_matches` and `_guard_durable_file_matches(cross_kind=True)` (`upgrade_extensions.py`) for both `_read_guard_pack` checks, validation's proof against `path.lstat()`, and the publication re-check. Same-kind checks and the `[1:]` device exclusion unchanged; proof stays five fields. Reviewed-comparison allowlist in `test_sqlite_storage_migration.py` updated to the new expressions. | new `tests/test_verified_pack_stat_kinds.py` 8 tests OK; against HEAD modules 5 fail (AC-1/AC-3 ctime-only tests); 9 single-comparison mutants (M1-M7 per Requirement 1 comparison, same-kind ctime drop, helper mtime drop) each killed. `python3 -B -m unittest` (run_tests lock held by a concurrent run): test_upgrade_wavefoundry 742 OK, test_index_upgrade_guard 45 OK, test_upgrade_rerun_reliability 19 OK, test_verified_pack_portability 15 OK, test_archive_ownership_portability 29 OK, test_upgrade_failure_surfacing 30 OK, test_sqlite_storage_migration 133 OK |
| 2026-10-21 | Gapfill: the wave's six changes were implemented by four parallel subagents whose code reads were mostly targeted shell reads (`sed`, `grep`) of files and symbols the readiness reviews had already located by line; the instrumented MCP retrieval telemetry therefore shows near-zero implement-stage calls. Delivery review is briefed MCP-first. | coordinator note; `wf_review_wave` retrieval_posture_gap advisory |
| 2026-10-21 | Delivery repair cycle 1: staging keeps the path-stat identity taken before `validate_feature_pack` and requires all five fields to match after it (finding S1); new tests drive the guard read with a shifted handle mtime, validation with shifted path inode, size and mtime, and the publication re-check with a shifted path inode (finding E1). Mutant M7 (guard cross-kind drops inode) is now killed by `test_real_path_change_refuses_the_publication_recheck`; on the read paths `contained_files` refuses inode and size changes before the guard comparison. | `test_verified_pack_stat_kinds` 11 OK; S1 revert and M7 each fail the new tests in scratch copies; upgrade, guard, portability and storage suites OK |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-21 | Ignore ctime only in comparisons that mix handle and path snapshots | Keeps proof shape, same-kind strength and existing field exclusions | Drop ctime from the identity everywhere (changes proof shape, weakens POSIX same-kind checks); take both snapshots by `lstat` after close (loses binding to the handle that wrote the copy) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A cross-kind comparison is missed | Requirement 1 states the rule and proof provenance; AC-3 drives each listed path |
| A rewrite that preserves size and mtime goes unnoticed | Inode and device still bind; the pack is hash-verified before use |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
