# Upgrade and Render Edge Test Gaps

Change ID: `200v2-maint upgrade-and-render-edge-test-gaps`
Change Status: `implemented`
Owner: framework-operator
Status: implemented
Last verified: 2026-10-07
Wave: 200xy security-follow-ups

## Rationale

Waves `1zyb2`, `1zyb3` and `1zxnz` each closed with low-severity follow-ups in edge paths: an upgrade dry-run preview that reports an error for old targets, two untested failure branches in declared-skill orphan removal, a journal date placeholder that accepts non-ASCII digits, and a lock mechanism whose Linux behavior is documented but has never been exercised. None is user-visible in the common path, but each is a place where the code and its stated contract can drift unnoticed. This change fixes the two behavior gaps and adds the missing evidence.

Brief: small, test-led maintenance; consumers are upgrade operators (preview output) and maintainers (test evidence); success is that each item has a failing-before, passing-after test or a recorded platform run.

Code-grounded facts (verified against HEAD `404e4950` on 2026-10-07; no framework script differs from HEAD in the working tree):

- `upgrade_extensions.post_extract` runs a dry-run preview for targets older than 1.5.0 (`_from_version_predates(ctx.from_version, "1.5.0")`, then `getattr(ctx, "dry_run", False)`). `_preview_role_field_backfill` puts the TARGET's `.wavefoundry/framework/scripts` on `sys.path` and runs `from history_paths import is_history_path`. `history_paths.py` is new in wave `1zyb2`, so a pre-1.5.0 target's tree has no such module; the dry run extracts nothing, so the import fails and the preview section records `ERROR (preview): <traceback>`. The real (non-dry) path, `_backfill_role_field_on_agent_docs`, runs in `post_extract` after extraction, when the target's scripts are already the incoming files, so it is unaffected. The preview context is built in `upgrade_wavefoundry` with `zip_path` set and `dry_run=True`. `upgrade_extensions` runs from the pack: `_storage_identity_helper` documents that the extension loader gives archive modules a relative `__file__` and loads an incoming helper from the zip member when `__file__` is not absolute. So in production the preview always loads from the pack; a load by absolute path happens only when a test imports `upgrade_extensions` from the scripts directory. Two test files pin today's shape: `tests/test_history_paths.py` `test_upgrade_sites_import_inside_the_function_after_the_path_insert` requires both `_backfill_role_field_on_agent_docs` and `_preview_role_field_backfill` to insert a `sys.path` entry before a function-local `from history_paths import`, and `tests/test_history_paths.py` `test_preview` and `tests/test_upgrade_wavefoundry.py` (the role-backfill preview tests) call `_preview_role_field_backfill(root)` with one argument.
- Declared-skill orphan removal in `render_agent_surfaces.render_skills`: a failed `skill_file.unlink()` raises `RuntimeError(f"cannot remove the undeclared skill {rel}: {exc}")`, whose `{exc}` text carries the OSError's absolute file path; a failed `folder.rmdir()` prints a NOTICE naming `type(exc).__name__`. `tests/test_declared_extension_skills.py` `DeclaredSkillOrphanTests` has no test of the unlink failure, and `test_orphan_folder_gaining_an_entry_after_the_decision_survives` asserts the NOTICE text but not the exception class.
- Journal migration: `upgrade_extensions._JOURNAL_PLACEHOLDER_PATTERNS["date"]` is `\d{4}-\d{2}-\d{2}` and `migrate_journals` captures the built-in scaffold's date with `^Last verified: (\d{4}-\d{2}-\d{2})\s*$`. Python's `\d` in a `str` pattern matches every Unicode decimal digit, so a date written in non-ASCII digits satisfies both.
- OFD locks (wave `1zxnz`, change `1zx02`): its Progress Log records the mechanism exercised only on macOS 27.2 arm64, with Linux and WSL2 evidence pending. `tests/test_runtime_lock.py` `RecordLockMechanismTests` asserts `mechanism == "ofd"` wherever `_ofd_expected()` holds and skips elsewhere, so a Linux run would exercise it, but no Linux run has been recorded. The repository has no CI workflow (`.github/workflows` absent) and this workstation has no container runtime.

## Requirements

1. **Preview loads the incoming predicate.** `_preview_role_field_backfill` takes `is_history_path` from the incoming framework (the code that will run after extraction), never from the target's tree: when `upgrade_extensions` was loaded from an absolute path, from the `history_paths.py` beside it, loaded by file location; when it was loaded from the pack, from the pack member beside it, read from `ctx.zip_path` and executed into a private module that is not registered in `sys.modules`. The preview function gains a keyword parameter `zip_path` defaulting to `None` (the post-extract caller passes `ctx.zip_path`), so existing one-argument calls keep working and load the module beside `upgrade_extensions` by file location; the real backfill is unchanged. If the incoming module cannot be loaded, the section names the cause class in one line, with no traceback and no absolute path. The structural test in `tests/test_history_paths.py` is rewritten for the preview so it pins the incoming-module load (no `sys.path` insert and no `history_paths` import from the target tree in `_preview_role_field_backfill`), and keeps its current pin on `_backfill_role_field_on_agent_docs`.
2. **Orphan unlink failure.** A failed orphan `SKILL.md` unlink still raises `RuntimeError` and still stops `render_skills` at that orphan, before its skill writes and prompt creations, and its message names the repository-relative skill path and the exception class only (as the rmdir NOTICE does), never the OSError text.
3. **Tests for both orphan branches.** A test makes the orphan unlink fail and asserts the `RuntimeError`, its message (relative path, class, no absolute path) and that no skill write or prompt creation followed it; the rmdir NOTICE test also asserts the exception class name.
4. **ASCII dates.** Every date pattern in the journal migration (the `{{date}}` placeholder and the built-in scaffold's `Last verified:` capture) matches only ASCII digits.
5. **Linux OFD evidence.** A Linux-only test class (skipped off Linux) asserts, on Linux x86_64 or aarch64, that `_ofd_expected()` holds (so the OFD tests run rather than skip) and that a separate open file description's `F_OFD_GETLK` on the held byte reports the holder with `l_pid == -1` and `F_WRLCK`. The probe's input `struct flock` sets `l_pid = 0`, which `F_OFD_GETLK` requires (the kernel rejects a non-zero input `l_pid` with `EINVAL`). The class's assertions are proven off Linux by a mutation or simulated probe (a patched `fcntl` that returns a holder record of the wrong shape makes the assertion code fail), so the class is known to check what it claims before any Linux run. The existing OFD tests and this class are run on a Linux host and on WSL2 (distribution filesystem), and each run is recorded in the Progress Log with kernel, distribution, architecture, Python version, the focused command and its test, failure and skip counts.

## Scope

**Problem statement:** four edge paths lack a fix or evidence.

**In scope:**

- Requirements 1 to 5 and their tests.

**Out of scope:**

- Other preview sections, and the absolute paths in other `ERROR (preview)` tracebacks.
- The rmdir NOTICE wording, which is already path-free.
- Windows lock behavior (`msvcrt`, unchanged) and adding a CI workflow.

## Acceptance Criteria

- [x] AC-1: A dry-run preview against a fixture target whose scripts directory has no `history_paths.py`, run once with `upgrade_extensions` loaded from a pack (relative `__file__`, `zip_path` set; the production path) and once loaded by absolute path (a test-only load), produces the role-backfill section with its planned rows and no `ERROR (preview)` line; the target tree is byte-identical afterwards. Fails today with the import error.
- [x] AC-2: With the incoming module unloadable (pack member removed), the role-backfill section is one line naming the cause class, with no traceback text and no absolute path.
- [x] AC-3: A patched failing orphan unlink makes `render_skills` raise `RuntimeError` whose message holds the relative skill path and the exception class name and not the repository root, and no skill file is written and no prompt creation is materialized after the failure (snapshot of the skill folders and the creation targets). The rmdir NOTICE test asserts the class name. A mutant that drops the raise, or puts `{exc}` back, fails the new test.
- [x] AC-4: A journal equal to the built-in scaffold or to a declared template except that its date uses non-ASCII decimal digits is not deleted (it is kept, or relocated as any non-pristine journal is); the same journal with ASCII digits is still migrated as a pristine scaffold.
- [x] AC-5: The Linux-only class exists, is skipped on macOS and Windows, sets `l_pid = 0` on its probe input, and its assertions are proven by a mutation or simulated probe off Linux (a wrong-shape holder record fails them).
- [~] AC-6: The Progress Log holds one Linux run and one WSL2 run per Requirement 5, each with the Linux-only class passing and zero failures and zero OFD skips in `RecordLockMechanismTests`. *No Linux or WSL2 host was available during the wave (macOS workstation, no container runtime, no CI); per the operator decision the Linux-only class ships and the Linux and WSL2 runs stay a named follow-up.*
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `framework_edit_allowed`.
- [x] `upgrade_extensions.py`: incoming `history_paths` loader for the preview (AC-1, AC-2).
- [x] `upgrade_extensions.py`: ASCII-only date patterns (AC-4).
- [x] `render_agent_surfaces.py`: path-free orphan unlink message (AC-3).
- [x] Tests in `tests/test_upgrade_wavefoundry.py`, `tests/test_declared_extension_skills.py` and `tests/test_runtime_lock.py` (AC-1 to AC-5), each confirmed failing against the unfixed code in a scratch copy.
- [x] `tests/test_history_paths.py`: rewrite the preview half of the structural import test to pin the incoming-module load; keep the backfill pin and the one-argument `test_preview` call (AC-1).
- [x] Close `framework_edit_allowed`.
- [~] Run `python3 .wavefoundry/framework/scripts/run_tests.py --file test_runtime_lock.py` on a Linux host and on WSL2; record both runs (AC-6).
- [x] Run `wf_validate_docs`, then the full suite last (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 upgrade preview and dates | implementer | - | Requirements 1 and 4 |
| ws-2 orphan removal | implementer | - | Requirements 2 and 3 |
| ws-3 Linux evidence | implementer | - | Requirement 5; needs operator access to a Linux host and WSL2 |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_declared_extension_skills.py`, `.wavefoundry/framework/scripts/tests/test_runtime_lock.py`, `.wavefoundry/framework/scripts/tests/test_history_paths.py`
- Within the wave this change lands second, after `200v1`; `render_agent_surfaces.py` is also edited by `200xx`, which lands after it.

## Affected Architecture Docs

N/A: each edit stays inside one function's behavior (preview loading, a message, two regexes) or adds tests and evidence; no boundary, flow or verification topology changes.

## Platform Behavior

- **Preview loading:** pack reads and file-location loads are path-separator neutral (`Path` and POSIX member names), identical on Windows, macOS, Linux and WSL2.
- **Orphan unlink:** on Windows a locked `SKILL.md` is the common failure; the message carries the class (`PermissionError`) and the relative path on every platform.
- **Dates:** pure regex, identical everywhere.
- **Locks:** Linux (kernel 3.15 or later, x86_64 or aarch64) uses OFD and is verified by Requirement 5; macOS uses OFD (verified in wave `1zxnz`); WSL2 runs Linux semantics on the distribution filesystem and is verified by Requirement 5; a DrvFs mount and WSL1 are expected to fall back to `lockf` and are not verified here; Windows uses `msvcrt` and is unchanged, and the Linux-only class is skipped there.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The preview reports a false error for every pre-1.5.0 dry run. |
| AC-2 | important | Fallback output only. |
| AC-3 | required | Untested failure branch, and the message leaks an absolute path. |
| AC-4 | important | Narrow false match; deletion is guarded by full-template equality. |
| AC-5 | required | The class ships with assertions proven to bite, so a Linux run cannot pass vacuously; provable on any host. |
| AC-6 | important | Depends on host access; the Linux and WSL2 passes of the class live here. |
| AC-7 | required | Change-local health. |

## Progress Log

| Date | Update | Evidence |
| ---- | ---- | ---- |
| 2026-10-07 | Planned from the follow-ups of waves `1zyb2`, `1zyb3` and `1zxnz`; claims verified against the working tree. | Rationale facts. |
| 2026-10-07 | Revised after readiness review round 1 (four findings); facts re-verified against HEAD `404e4950`. | Rationale facts; Decision Log. |
| 2026-10-07 | Requirement 1: `upgrade_extensions._incoming_history_paths(zip_path=None)` loads the incoming `history_paths` (file location beside the module when loaded by absolute path; the pack member beside it from `zip_path` when loaded from the pack), into a private module never registered in `sys.modules`, with no `sys.path` change; any load failure raises `_IncomingModuleUnavailable(<cause class>)`, which `post_extract` reports as one `ERROR (preview)` line naming the class. `_preview_role_field_backfill(root, *, zip_path=None)`; the post-extract dry run passes `ctx.zip_path`; the real backfill is unchanged. Structural test rewritten: no `history_paths` import, `sys.path` insert or `sys.modules` subscript in the preview or its loader; backfill pin kept. | `RoleBackfillPreviewIncomingModuleTests` (3 tests: pack load, path load, unloadable member); `test_history_paths.py` 25 tests OK. |
| 2026-10-07 | Requirements 2 to 4: orphan unlink `RuntimeError` message is now the relative skill path plus `(<exception class>)`; the rmdir NOTICE test asserts `(OSError)`. Journal `{{date}}` placeholder and the scaffold `Last verified:` capture use `[0-9]` instead of `\d`. | `DeclaredSkillOrphanTests.test_failed_orphan_unlink_raises_path_free_before_any_write` (whole-tree snapshot unchanged, no new skill folder, no prompt creation); `JournalAsciiDateTests` (2 tests, Arabic-Indic digits kept, ASCII deleted). |
| 2026-10-07 | Requirement 5: `LinuxOfdEvidenceTests` (skipUnless Linux x86_64 or aarch64; asserts `_ofd_expected()` and that a separate open file description's `F_OFD_GETLK` with input `l_pid = 0` reports `F_WRLCK`, `l_pid == -1`, the held byte) and `LinuxOfdEvidenceProbeTests` (every host: simulated `fcntl` with Linux constants that rejects a non-zero input `l_pid` with EINVAL; an OFD-shaped record passes, four wrong-shape records fail the assertions; the skip predicate selects Linux x86_64 and aarch64 only). Skipped here (macOS 27.2 arm64). | `test_runtime_lock.py` 39 tests OK in scratch. |
| 2026-10-07 | Failing-before: with HEAD `upgrade_extensions.py` and `render_agent_surfaces.py` in the scratch copy, all 3 preview tests (each with an `ERROR (preview)` import traceback), both date tests, the unlink test (message carried the absolute path) and the structural test fail. Mutation probes (scratch, each restored): drop the unlink raise, put `{exc}` back, revert either date pattern to `\d`, path load via `import history_paths`, register the pack-loaded module in `sys.modules`, leak cause text and pack path in the loader error, probe input `l_pid` non-zero, drop the `l_pid == -1` assertion, drop the `l_type` assertion, skip predicate admitting non-Linux: 11 of 11 killed. | Scratch `sG2`; focused run of the four touched files: 773 tests OK. |
| 2026-10-07 | AC-6 deferred: no Linux or WSL2 host on this macOS workstation (no container runtime, no CI). The Linux and WSL2 runs of `run_tests.py --file test_runtime_lock.py` remain a named follow-up. Deferring AC-6 published a new review-policy receipt, superseding the current readiness approval. | `wf_mark_ac` diagnostic `review_policy_receipt_superseded`. |
| 2026-10-07 | Proposed CHANGELOG bullets for 1zyv1 (under `## [1.29.0]`): "Fixed: the upgrade dry-run migration preview no longer reports an error for targets older than 1.5.0; it evaluates history paths with the incoming framework's predicate." "Fixed: a failure to remove an undeclared skill file now reports the repository-relative path and the error class instead of the operating-system error text." "Fixed: journal migration date patterns accept ASCII digits only." "Added: a Linux-only test that checks record locks are open file description locks, with a host-independent probe of its assertions." | For the 1zyv1 CHANGELOG pass. |
| 2026-10-07 | Full scratch suite (`run_tests.py --no-cache`, scratch copy including the parallel 200v1 work in progress at copy time): 11620 tests across 167 files OK. Docs lint OK with HEAD lint code plus this change's files (the live tree's lint was mid-edit by 200v1 and could not run). The Linux and WSL2 run task stays open for the coordinator (follow-up). | Scratch `sG2` full log; scratch `sG2b` docs-lint ok. |
| 2026-10-07 | Delivery-review repair DEL-4: `LinuxOfdEvidenceProbeTests` gains a case that runs `assert_ofd_holder` against the real `fcntl` wherever `_ofd_expected()` holds (it ran on this macOS host); disabling `_ofd_lock_support` in a scratch copy fails it (killed, restored). `upgrade_extensions._incoming_history_paths` now notes that the module runs without `sys.modules` registration and must stay free of constructs that need it, pinned by `test_history_paths_runs_without_sys_modules_registration` (imports limited to `__future__` and `pathlib`; an unregistered load works). Gapfill: shell used alongside the MCP tools for test runs and edits. | `tests/test_runtime_lock.py`; `tests/test_history_paths.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-07 | Load `history_paths` from the incoming framework for the preview. | The preview must model the code that runs after extraction, which is the incoming module; this follows the old-code-window rule and the existing `_storage_identity_helper` pattern. | Inline fallback copy of the predicate: a second definition of what wave `1zyb2` made single. Skip the section for old targets: hides the preview for exactly the targets it exists for. |
| 2026-10-07 | Make the unlink message path-free while adding its test. | The test would otherwise pin a message that echoes an absolute path, unlike the sibling NOTICE. | Test the current message as is: pins the leak. |
| 2026-10-07 | Record Linux evidence through a focused local run plus a Linux-only test, not CI. | No CI workflow exists and adding one is outside a follow-up; the Linux-only test turns a silent skip into a failure. | Add a CI workflow: new release surface. Documentation-only claim: unverified. |
| 2026-10-07 | Default the preview's new `zip_path` parameter to `None` and rewrite the preview half of the `test_history_paths.py` structural test. | One-argument callers in two test files keep working, and the structural test then pins the new behavior (incoming-module load) instead of the target-path import it replaces. | Required parameter: edits every one-argument test call for no behavior gain. Leave the structural test: it fails on the fix. |
| 2026-10-07 | Split the Linux evidence: required AC-5 proves the class off Linux by mutation or simulated probe; the Linux and WSL2 passes fold into important AC-6. | A required AC that only a Linux host can meet would block close on host access, which the operator decided against. | Keep AC-5 required with the Linux pass: unmeetable on this workstation. |
| 2026-10-07 | Operator decision: Linux and WSL2 runs are recorded if a host is available; otherwise AC-6 is marked `[~]` with a note and stays a follow-up, and the Linux-only class still ships. | No Linux host or CI on this workstation. | Block close on a Linux run. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| No Linux host or WSL2 is available during the wave. | AC-6 is important, not required; if no host is available it is marked `[~]` with the reason and the evidence stays a named follow-up. |
| Executing a pack member in the preview widens what the dry run runs. | It is a member of the same pack whose `upgrade_extensions` is already executing; it is loaded into a private module and never registered. |
| Shared file with `200xx` in this wave (`render_agent_surfaces.py`). | This change lands before `200xx` (wave serialization order); its edit is one message line in `render_skills`. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
