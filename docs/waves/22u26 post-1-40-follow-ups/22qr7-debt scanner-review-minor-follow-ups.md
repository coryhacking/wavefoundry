# Scanner review minor follow-ups

Change ID: `22qr7-debt scanner-review-minor-follow-ups`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-07
Wave: 22u26 post-1-40-follow-ups

## Rationale

Wave 22qr6's delivery reviewers recorded three low-impact, non-blocking observations about the newly delivered scanner code. The operator chose to track them rather than fix them before closing:

1. **Test isolation.** `tests/test_scanner_input_limits.py` calls `load_server()`, which reloads the `wave_lint_lib` worker module. When `tests/test_scanner_worker_config.py` runs later in the same `unittest` process, it patches a stale module object: 1 failure and 2 errors. `run_tests.py` runs each file in its own process, so the canonical suite is green.
2. **Guidance undercount.** `scanner_skips.incomplete_guidance` counts fixed-limit files from the completion `incomplete` list, which is truncated to 50 rows. Beyond 50 such files, its "N of them" figure undercounts. Each row's remedy is still correct.
3. **Trailing-newline anchor.** In the non-upstream (Python `re`) path matcher, `$` also matches before a trailing newline. The suggested anchored entry for path `x` therefore also excludes a path named `x` followed by a newline. The upstream translator emits `\Z` and is exact. The security reviewer judged this not a defect.
4. **Unguarded test child.** `tests/test_memory_records.py` (`_child_dirty`) spawns `sys.executable -c ...` without `-B`. Under a bare `unittest` run that lacks `PYTHONDONTWRITEBYTECODE`, it writes 11 framework `.pyc` files beside the sources (reproduced on 2026-11-07). The canonical runner is unaffected, because its workers set the variable.
5. **Runner tests read the live tree's bytecode census.** In-process `run_tests.main` tests in `tests/test_run_tests_cache.py` (for example `CacheReadOnceTests`, `FocusedRunTests`, `ScheduleControlTests`) take the real `.wavefoundry/framework/` census, so any stray bytecode in the checkout flips their exit code to 1 (observed in wave 22r97's first full run).

## Product Intent

Maintainers can run the scanner tests in any runner without false failures, operators see accurate counts, and suggested allowlist entries match exactly one path on every matcher. Detection and completion policy are unchanged.

## Requirements

1. The two scanner test modules pass when run together in one `unittest` process.
2. The fixed-limit count in `incomplete_guidance` reflects every outstanding fixed-limit file, not only the truncated rows.
3. A suggested allowlist entry matches exactly its own path on both the Python and the upstream path matchers.
4. The three known unguarded test children (`_child_dirty`, the `test_indexer` `index_state_store` child and the `test_lifecycle_mutation_lock` `server_impl` child) never write framework bytecode, and runner unit tests do not depend on the live checkout's bytecode census. A census of every test child spawn is a separate follow-up (`22ubd-debt test-child-spawn-bytecode-census`).
5. An allowlist path entry written in RE2 syntax that Python `re` cannot compile (such as one ending in `\z`) is matched through the existing RE2 translation on the Python matcher, as rule patterns already are, instead of being skipped.

## Scope

**In scope:** the two scanner test modules' module handling, the guidance callers' row source, the suggested entry's end anchor and the Python path matcher's compile fallback, the `_child_dirty` spawn in `tests/test_memory_records.py`, and the bytecode census seen by in-process runner tests in `tests/test_run_tests_cache.py`.

**Out of scope:** scanner policy, worker protocol and limits.

## Acceptance Criteria

- [x] AC-1: `cd .wavefoundry/framework/scripts && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python3 -B -m unittest tests.test_scanner_input_limits tests.test_scanner_worker_config`, in that order, passes; on the current code it gives 1 failure and 2 errors.
- [x] AC-2: With 60 fixed-limit files outstanding, the close diagnostic and the `wf_scan_secrets` diagnostic each report exactly 60; on the current code each reports 50.
- [x] AC-3: The suggested entry for `x` ends in `\z`, excludes `x` and does not exclude `x` followed by a newline on both the Python matcher and the upstream matcher. The in-suite test forces the `re.error` fallback in `_path_matches_allowlist` so it exercises the translation on any interpreter, and one recorded run on `/opt/homebrew/bin/python3.11` covers the real older-Python path. Known-bad controls on the current code: the `$` entry excludes `x` followed by a newline, and on Python 3.11 or 3.13 a `\z` entry excludes nothing because `re.error` is swallowed. An existing `$`-anchored entry keeps its current behaviour.
- [x] AC-5: The `test_memory_records._child_dirty` child, the `index_state_store` child in `tests/test_indexer.py` and the `server_impl` child in `tests/test_lifecycle_mutation_lock.py` each run with `-B` or with `PYTHONDONTWRITEBYTECODE` set, asserted on the arguments each test passes to its spawn. In a scratch copy of the scripts tree, a bare `unittest` run of each of the three modules without `PYTHONDONTWRITEBYTECODE` leaves no `__pycache__`; on the current code the `_child_dirty` and `test_indexer` runs each write 11 `.pyc` files. No known-bad run writes into the live tree.
- [x] AC-6: The in-process `run_tests.main` tests in `tests/test_run_tests_cache.py` pass with a stray `.pyc` planted under a scratch copy's framework census root, or with the census patched to report one; on the current code their exit code flips to 1.
- [x] AC-4: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Make the worker-config tests resolve the worker module at test time, or isolate the reload.
- [x] Pass the untruncated outstanding rows to `incomplete_guidance` at the close and `wf_scan_secrets` call sites.
- [x] Emit `\z` in `allowlist_entry` and in the fallback text in `scanner_skips` that still spells `'$'`, update the `ENTRY` constant in `tests/test_scanner_work_limits.py`, and retry an uncompilable path pattern through `_re2_to_re` in `_path_matches_allowlist`.
- [x] Guard the `_child_dirty`, `test_indexer` and `test_lifecycle_mutation_lock` spawns, with argument assertions.
- [x] Isolate the runner tests from the live bytecode census.
- [x] Add regression tests with known-bad controls.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| scanner    | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/scanner_skips.py`, `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: confined to the scanner module and its tests, with no boundary change.

## Platform Behavior

Pure Python; identical on Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | important    | Prevents false failures under alternate runners. |
| AC-2 | nice-to-have | Cosmetic count accuracy. |
| AC-3 | nice-to-have | Edge case with no realistic filenames. |
| AC-4 | required     | Change-local verification. |
| AC-5 | important    | Framework bytecode is a defect wherever it appears. |
| AC-6 | important    | Prevents false runner-test failures. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Filed from wave 22qr6 delivery review notes at operator request. | 22qr6 code, QA and security delivery approvals (limitations) |
| 2026-11-07 | Scheduled at operator request. Added ACs 5 and 6 for items 4 and 5. Chose `\z`: RE2 reads it as end of text, Python 3.14 accepts it natively, and older Python reaches it through `_re2_to_re`, which `_path_matches_allowlist` does not call today, so a `\z` entry would be silently skipped there. | `wave_lint_lib/secrets_validators.py` `_path_matches_allowlist`, `_re2_to_re` |
| 2026-11-07 | Readiness: QA finding `22u26-qa-unguarded-children` (two more unguarded spawns, one reproduced at 11 `.pyc` in a scratch copy); Requirement 4 and AC-5 narrowed to the three known sites, the option the finding offered; a full census would cover 202 unguarded-looking spawn lines in 99 test files, so it is filed as `22ubd-debt`. QA and code-review wording suggestions applied to AC-1, AC-2 and AC-3. | readiness review, cycle 1 repair |
| 2026-11-07 | Correction: the cycle-1 `repair_start` for `22u26-qa-unguarded-children` says "extend AC-5 rather than narrow Requirement 4". The repair actually made narrowed Requirement 4 and AC-5 to the three known sites, as the row above records; the ledger is append-only, so this row corrects it. | QA round-2 reverification note |
| 2026-11-07 | Implemented. AC-1: `setUpModule` rebinds `worker` and `scanner` in `test_scanner_worker_config`; the exact combined command now passes (20 OK, was 1 failure and 2 errors). AC-2: both diagnostics count `incomplete_guidance` over `scanner_skip_notice` rows (existing functions only, so a reload with an older `scanner_skips` still loaded keeps working); `tests/test_scanner_guidance_count.py` 2 OK, and with the original handlers both report 50. AC-3: `allowlist_entry` and the fallback text use `\z`, `_path_matches_allowlist` retries through `_re2_to_re`, `ENTRY` and the entry-form test updated; `tests/test_allowlist_entry_anchor.py` 6 OK on 3.14.8 and on `/opt/homebrew/bin/python3.11` (3.11.17, where `\z` is a bad escape); known-bad: the original matcher fails 7 on 3.11 and the forced-fallback test fails 3 on 3.14, the original entry fails 10. A first probe mislabelled 3.11 runs as 3.14 because the 3.11 venv was first on `PATH`, which hid a vacuous `search` in the test's stand-in `re`; the stand-in was fixed and the runs repeated with explicit interpreters. AC-5: `-B` on the three spawns; `tests/test_child_spawn_bytecode_guard.py` 2 OK; scratch bare runs wrote 11, 11 and 1 `.pyc` before and 0 after. AC-6: the scaffold and telemetry main() tests census a scratch framework path; with a planted stray `.pyc` the original file fails 12, the fixed one passes. | implementation |
| 2026-11-07 | Full suite `run_tests.py --no-cache`: 12612 tests in 235 files OK, 12 expected skips, no framework bytecode (second run). The first run failed two files from this wave's own edits, both fixed before the second: `test_lifecycle_golden` (the 22r95 `conditional_fields` schema entry; golden regenerated through `check_golden` with both overwrite flags, diff exactly the three expected fixture paths, and the addition declared with its exact value in `test_only_declared_observability_additions_since_extraction_golden`) and `test_server_package` (22u24's new filesystem test read producers by path; now `framework_files.source_path`). | full suite |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-06 | Deferred from 22qr6. | Low impact; fixing would have required a fresh qualification and recheck before close. | Fix in 22qr6 |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Changing the anchor alters existing allowlist semantics | Apply only to newly suggested entries, and test both matchers. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
