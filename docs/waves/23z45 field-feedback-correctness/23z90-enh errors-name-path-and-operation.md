# Name the path and the operation in two failure messages

Change ID: `23z90-enh errors-name-path-and-operation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-20
Wave: 23z45

## Rationale

Field feedback against v1.46.0 (item 6 in `.wavefoundry/work/23z45/field-feedback-v1.46.0.md`) reports two failure messages that leave the operator unable to act:

1. `wf_prepare_wave` (mode `ready`) reported a `PermissionError` for the context-efficiency record without the path or the operation.
2. `wf_techdocs_audit` reported a missing baseline without saying which baseline it looked for.

Both were reproduced in this session against the current tree (VERSION 1.46.0+q4tt).

**Context-efficiency projection.** Lifecycle tools attach `data.context_efficiency_persistence` from `_flush_context_efficiency`, which calls `_project_context_efficiency_wave` in `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`. That function's broad handler (line 278 to 284) returns `"error": _cause_label(exc)`, which is the exception class and errno name only. A probe built on the `test_index_source_guard.py` fixture, with `-B` against a temporary root, injected three failures and observed (executed):

| Injected failure | Observed row |
| --- | --- |
| `PermissionError(EACCES, ..., <absolute wave.md>)` at `server_impl._atomic_replace_text` | `{'persistence': 'failed', 'projection': 'pending', 'error': 'PermissionError EACCES', 'wave_id': '1aaaa probe'}` |
| `PermissionError(EACCES, ...)` with no filename at `context_efficiency.mark_checkpoint_published` | same, `'error': 'PermissionError EACCES'` |
| `PermissionError('denied')` at `context_efficiency.read_wave_snapshot` | same, `'error': 'PermissionError'` |

The row drops the filename the exception carried and records neither which step failed nor which file it was working on. The same function's unreadable-record row (line 169 to 178) uses `_read_error_detail`, which yields `"<Class>: <strerror>"`, also without the path or the step (read from the code, not executed). Expected: the row names the step and its repository-relative target, so the operator knows whether the wave record or the context-efficiency store refused access. Field feedback item 4 (change `23z47-bug windows-fchmod-guard`) reports native-Windows `PermissionError` failures on record writes; the item 6 failure may share that cause (inferred, not reproduced on Windows).

**TechDocs audit.** No `no_baseline_commit` token exists in `.wavefoundry/framework/` (census by `grep -rn "no_baseline\|baseline_commit"`, which found only an unrelated test name). The audience check in `.wavefoundry/framework/scripts/techdocs_audit_lib.py` (`_baseline_text`, line 1178 to 1214) emits `baseline_untracked` or `baseline_missing`; the field report most likely paraphrased one of those (inferred). The report's `data.audience` entries already carry `baseline_ref` and the per-document `degrade`, but the human-readable surfaces print bare tokens. Executed against a scratch git repository with an uncommitted `docs/ARCHITECTURE.md` and `docs/references/project-overview.md`:

1. MCP `wf_techdocs_audit_response` (`wf_server/techdocs_handlers.py` line 98 to 106): `the audit could not compute part of its answer: exclude_docs_absent, baseline_untracked. A degraded run never reports a clean verdict.`
2. CLI `techdocs_audit.py` (lines 91 to 92 and 120 to 121): `techdocs-audit: NOTE degraded: baseline_untracked`.
3. After committing both files, `--compare-to nosuchref` printed `NOTE degraded: baseline_missing`: a nonexistent ref reads as a missing file, and nothing names the ref.

Expected: the message names the ref the audit compared against and each document that had no baseline there.

**Flush errors with absolute paths.** Two more producers write into the same `context_efficiency_persistence` row and render `f"{type(exc).__name__}: {exc}"`: `_flush_context_efficiency`'s outer handler (`wf_server/context_efficiency_handlers.py` line 396) and `ProcessTelemetry.flush`'s `FlushResult.error` (`context_efficiency.py` lines 2429 and 2434), which has four consumers in `wf_server/context_efficiency_handlers.py`: the lifecycle row at lines 353 and 361, and the `wf_upgrade` and `wf_reload_mcp` barrier rows in `project_pending_context_efficiency` at lines 415 and 422 (census by `grep` for `flushed.error`, rechecked 2026-11-20). A probe injected `PermissionError(EACCES, "Permission denied", <absolute store path>)` at `_open_write_store_once` during a general-bucket transfer (executed). The deferred branch returned `PermissionError: [Errno 13] Permission denied: '<absolute path>'`, and with `FLUSH_RETRYABLE_EXCEPTIONS` emptied the poisoned branch returned the same text. Both contain the absolute root. The line-396 handler has the same rendering (read from the code, not executed). Expected: the same repository-relative form as the projection rows, with no absolute path.

## Product Intent

An operator or agent who sees a context-efficiency persistence failure or a degraded TechDocs audit can tell, from the message alone, which file and which step (or which git ref) were involved, and act without reading framework source. Machine contracts stay as they are: the `degraded` token list, the diagnostic codes, and the existing row keys keep their values; the change adds information and never adds an absolute path. AC-1, AC-2, AC-3, AC-5 and AC-9 together test the intent for the context-efficiency row; AC-6 and AC-7 test it for the audit.

## Requirements

1. Every failed row that `_project_context_efficiency_wave` returns with `"persistence": "failed"` must carry an `operation` key naming the step that raised and a `target` key holding the repository-relative POSIX path of that step's file. The set of steps is derived by this rule: each call inside the function's publication-lock block that reads or writes a file. Steps that operate on the wave record target that record's path; steps that operate on the context-efficiency store target `context_efficiency.STORE_RELATIVE_PATH`. A step with no single file target carries `operation` and omits `target`. The step tracker always has a value: it is set before every call in the block, a pure step between file steps (one that touches no file) carries its own `operation` and no `target`, and a failure raised before the first step, while entering the lock block, carries an `operation` naming lock acquisition and no `target`. The typed lock branches that return their own rows today are unchanged. The implementer names each step while reading the block; the derived set governs over any list in this spec.
2. In those failed rows, `error` must be rendered by `lifecycle_lock.path_free_exception_text(exc, root)`, so an `OSError` whose filename lies under the root reads `<Class> <ERRNO> on <repo-relative path>`.
3. Both unreadable-record rows must carry `operation` and `target` for the wave record read, under the same rules: the `current is None` branch in `_project_context_efficiency_wave`, and the `initial_markdown is None` branch in `_flush_context_efficiency`, which returns first on the lifecycle path `wf_prepare_wave` uses. Rows that carry no exception, such as `wave_not_found`, are not widened.
4. No field added or changed by Requirements 1 to 3 may contain an absolute path, in POSIX, Windows-drive or backslash form, including when the exception's filename lies outside the root.
5. The `wf_techdocs_audit` degraded diagnostic and both CLI `NOTE degraded:` emissions must describe each token that appears in an `audience` entry's `degrade` field (`working_tree_missing`, `git_unavailable`, `baseline_untracked`, `baseline_missing`) with the entry's `baseline_ref` and the repository-relative paths of the documents that carry it. One helper in `techdocs_audit_lib.py` must produce this text for both entries, so the MCP and CLI wording cannot drift. Other tokens keep their current rendering. The helper reads the ref only from entries that carry a `degrade` field, so a ref the audit refused (`compare_to_refused`, whose entries carry no `degrade`) is never rendered. It renders every ref it does name in quoted, ASCII-escaped form (the form `json.dumps` produces) truncated to a fixed length held in one constant, so no raw control or non-ASCII character from a caller-supplied ref reaches a message. The quoting and truncation are new behaviour for review.
6. `data.degraded`, the `degraded` field of the CLI `--json` envelope, the diagnostic codes `techdocs_audit_degraded` and `techdocs_audit_not_applicable`, and the existing keys and values of the context-efficiency row other than `error` must stay unchanged.
7. `_flush_context_efficiency`'s outer handler and both `FlushResult.error` assignments in `ProcessTelemetry.flush` must render `error` with `lifecycle_lock.path_free_exception_text(exc, root)` instead of `f"{type(exc).__name__}: {exc}"`. The lifecycle rows they produce must carry `operation` and, when the failing step has a single file target, `target` under the rules of Requirement 1; the outer handler's row omits `target` when no single file can be named for the failing step. For `FlushResult`, the implementer adds the fields that `_flush_context_efficiency` copies into the row at lines 353 and 361. Requirement 4 applies to these rows. Because `error` is rendered where `FlushResult` is produced, the two barrier rows in `project_pending_context_efficiency` (`detail` and `pending_general_transfer`, returned by `wf_upgrade` and `wf_reload_mcp`) receive the path-free `error` too; they keep their documented key set and do not copy `operation` or `target` (see Out of scope). `context_efficiency.py` imports `path_free_exception_text` inside the two `except` branches, not at module level, so importing `context_efficiency` still loads neither `lifecycle_lock` nor `review_evidence`. This import edge is new and is review surface.
8. Paths in every message use repository-relative POSIX form on native Windows, macOS, Linux and WSL2. `path_free_exception_text` already normalises through `as_posix()`; the audit paths are fixed POSIX constants (`STARTUP_ORDER_DOCS`).

## Scope

**Problem statement:** two failure messages omit the file, step or git ref the operator needs to act on them.

**In scope:**

- The `_flush_context_efficiency` outer handler and the `FlushResult.error` producers in `.wavefoundry/framework/scripts/context_efficiency.py` (Requirement 7).
- The failed rows of `_project_context_efficiency_wave` in `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`.
- The degraded rendering in `.wavefoundry/framework/scripts/wf_server/techdocs_handlers.py` and `.wavefoundry/framework/scripts/techdocs_audit.py`, through one new helper in `.wavefoundry/framework/scripts/techdocs_audit_lib.py`.
- One sentence in `docs/specs/mcp-tool-surface.md`, in the paragraph that begins "General-row transfer has a separate result contract", stating the failed-row keys and the path-free `error` form.
- Tests for both, and one changelog entry.

**Out of scope:**

- Other `f"{type(exc).__name__}: {exc}"` renderings, including `wf_context_efficiency_eval_response` (`context_efficiency_handlers.py` line 767).
- Surfacing the persistence failure as a diagnostic rather than as data.
- Reclassifying a nonexistent `--compare-to` ref as anything other than `baseline_missing`; naming the ref makes the case diagnosable.
- `compare_to_refused`: the refused ref may hold control characters, so it is not echoed.
- The MCP not-applicable response. Without `mkdocs.yml` the audit returns `not_applicable` before the audience check runs, so no audience degrade token exists and `wf_techdocs_audit` emits no degraded message. That branch is unchanged and gains no diagnostic.
- `operation` and `target` on the `wf_upgrade` and `wf_reload_mcp` barrier rows (`detail` and `pending_general_transfer`). The report names the lifecycle row, and the contract documents `pending_general_transfer` as `{persistence, projection, wave_id, error}`; these rows change only by receiving the path-free `error`.
- Any other error message in the codebase.

## Acceptance Criteria

- [x] AC-1: A unit test injects `PermissionError(errno.EACCES, "Permission denied", <absolute wave record path>)` at the wave-record write inside `_project_context_efficiency_wave` and asserts the row has `operation` naming that write, `target` equal to the repository-relative POSIX wave record path, and `error` equal to `PermissionError EACCES on <that path>`. With the fix absent the row is `'error': 'PermissionError EACCES'` with neither key, so the test fails.
- [x] AC-2: A unit test injects a `PermissionError` with no filename at a context-efficiency store step (for example `mark_checkpoint_published`) and asserts `operation` names that step and `target` equals `.wavefoundry/logs/context-efficiency.sqlite`. With the fix absent neither key exists.
- [x] AC-3: Both unreadable-record rows name the read and the record.
  1. A unit test makes the wave record unreadable for the `current is None` branch of `_project_context_efficiency_wave` and asserts the row carries `operation` for the record read and `target` equal to the record's repository-relative path.
  2. A test drives `_flush_context_efficiency` (the path `wf_prepare_wave` uses) with an unreadable wave record, so the `initial_markdown is None` branch returns, and asserts the same `operation` and `target` on the returned row.
  3. With the fix absent each row has `error` and neither key, so both cases fail.
- [x] AC-4: For every row produced in AC-1 to AC-3, plus a case whose exception filename lies outside the root, the serialized row contains no form of the root path (raw, resolved, backslash) and no absolute path, checked with the existing path-free assertion pattern in `tests/test_lifecycle_mutation_lock.py` or `tests/test_server_context_efficiency.py`.
- [x] AC-5: A test drives `_flush_context_efficiency` (the path `wf_prepare_wave` uses) with the AC-1 failure and asserts the returned projection, which becomes `data.context_efficiency_persistence`, carries the same `operation` and `target`.
- [x] AC-6: A test runs `wf_techdocs_audit_response` against a git repository with `mkdocs.yml` present where both `STARTUP_ORDER_DOCS` files are uncommitted and asserts the `techdocs_audit_degraded` message names `HEAD`, `docs/ARCHITECTURE.md` and `docs/references/project-overview.md` beside `baseline_untracked`, while `data.degraded` still equals the bare token list. With the fix absent the message is the observed bare-token text, so the test fails.
- [x] AC-7: A test runs the `techdocs_audit.py` CLI, in both text and `--json` modes, against a git repository with `mkdocs.yml` present and both `STARTUP_ORDER_DOCS` files committed, with `--compare-to` set to a ref that does not exist. It asserts each `NOTE degraded: baseline_missing` stderr line names that ref in the quoted form and the affected paths, and that the MCP message for the same run carries the same description (one helper).
  1. Negative: with a `--compare-to` value that `_ref_refused` rejects (for example one holding an escape character), neither the CLI stderr nor the MCP message contains the ref's text.
  2. A helper-level case with an accepted ref that holds a non-ASCII control character and one longer than the length constant asserts the message contains only the escaped, truncated form and never the raw ref.
- [x] AC-8: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-9: A unit test injects `PermissionError(errno.EACCES, "Permission denied", <absolute store path>)` at `_open_write_store_once` during a general-bucket transfer, once retryable (deferred) and once not retryable (poisoned or failed), and asserts `FlushResult.error` and the `_flush_context_efficiency` row contain no absolute path and name `.wavefoundry/logs/context-efficiency.sqlite`, with an `operation` key. A second case makes `_flush_context_efficiency`'s outer handler catch an `OSError` with an absolute filename and asserts the row has an `operation` key and no absolute path. With the fix absent the error is `PermissionError: [Errno 13] Permission denied: '<absolute path>'`, so the test fails.
- [x] AC-10: `docs/specs/mcp-tool-surface.md` states, in the general-row transfer paragraph, that a failed `context_efficiency_persistence` row carries `operation`, carries `target` when the step has a single file, and renders `error` without an absolute path. Fails at HEAD, where the paragraph names no failed-row key.

## Tasks

- [x] In `_project_context_efficiency_wave`, track the current step and its target, and render failed rows per Requirements 1 to 3 with `path_free_exception_text`.
- [x] Add AC-1 to AC-5 tests in `tests/test_server_context_efficiency.py`, and update any test pinning the old `error` text or the failed-row key set. One known pin: `test_unavailable_and_failed_projection_rows_are_path_free` in `tests/test_index_source_guard.py` asserts `'PermissionError EACCES'` for an exception whose filename is the wave record; under Requirement 2 it becomes `PermissionError EACCES on <record path>`.
- [x] Render `FlushResult.error` (lines 2429 and 2434) and the `_flush_context_efficiency` outer handler (line 396) per Requirement 7; add the AC-9 tests in `tests/test_context_efficiency.py` and `tests/test_server_context_efficiency.py`.
- [x] Add the degrade-description helper to `techdocs_audit_lib.py`; use it in `techdocs_handlers.py` and both CLI emission sites in `techdocs_audit.py`.
- [x] Add AC-6 and AC-7 tests in `tests/test_techdocs_audit_lib.py` (and `tests/test_server_tools.py` if the MCP fixture lives there).
- [x] Add the failed-row sentence to `docs/specs/mcp-tool-surface.md` (AC-10).
- [x] Add one changelog entry under Unreleased.
- [x] Run the focused suites, then `python3 .wavefoundry/framework/scripts/run_tests.py`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ce-row | implementer | none | Requirements 1 to 4 and 7, AC-1 to AC-5, AC-9 and AC-10 |
| techdocs-message | implementer | none | Requirements 5 and 6, AC-6 and AC-7 |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/techdocs_handlers.py`
- `.wavefoundry/framework/scripts/techdocs_audit.py`
- `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_context_efficiency.py`
- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_index_source_guard.py`
- `docs/specs/mcp-tool-surface.md`
- The root changelog gains one entry.

## Affected Architecture Docs

N/A for the architecture docs. The change is not confined to single modules, and two surfaces move. First, the failed row of `data.context_efficiency_persistence` is a documented MCP response field; its contract in `docs/specs/mcp-tool-surface.md` is updated by this change (AC-10). Second, Requirement 7 adds an import edge from `context_efficiency.py` to `lifecycle_lock`, kept function-local so module import loads nothing new; the readiness review executed the import probe and found no cycle. `docs/architecture/layering-rules.md` records `lifecycle_lock`'s own imports, not its importers, so it needs no edit.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported failure: a write-step `PermissionError` without path or step. |
| AC-2 | required | Store steps raise exceptions with no filename, so `target` is the only path the operator gets. |
| AC-3 | required | Product Intent rests on it: an unreadable wave record is the failure `wf_prepare_wave` reaches first. |
| AC-4 | required | The change must not trade a missing path for an absolute-path leak. |
| AC-5 | required | Product Intent rests on it: proves the information reaches the `wf_prepare_wave` response the operator saw. |
| AC-6 | required | The reported audit failure: a missing baseline without the ref. |
| AC-7 | important | CLI parity, the nonexistent-ref case, and the refused or unsafe ref never echoed raw. |
| AC-8 | required | Standard change-local verification. |
| AC-9 | required | Operator decision: the flush producers must stop recording absolute paths in the row. |
| AC-10 | important | The documented response contract names the new failed-row keys. |


## Progress Log

2026-11-21: The full framework suite passed on the reviewed changes. It ran 13,123 tests across 251 files in 741 seconds with 12 skips.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-20 | Planned; both failures reproduced on the current tree. | CE probe on the `test_index_source_guard.py` fixture (rows in Rationale); `wf_techdocs_audit_response` and `techdocs_audit.py` run against a scratch git repository. |
| 2026-11-20 | Operator decisions applied: flush error producers brought into scope (Requirement 7, AC-9); TechDocs fix confirmed for both baseline tokens; reporter to be asked which token they saw. | Flush probe: deferred and poisoned `FlushResult.error` both contained the absolute root (executed). Line numbers 396, 2429 and 2434 rechecked against the tree. |
| 2026-11-20 | Readiness repair pass 1. `R1-23z90-unreadable-row-uncovered`: Requirement 3 and AC-3 extended to the `initial_markdown is None` row in `_flush_context_efficiency`. `R1-23z90-ac5-priority`: AC-5 ranked required; AC-3 ranked required for the same reason. `R1-23z90-techdocs-fixture-scope`: AC-6 and AC-7 fixtures state `mkdocs.yml`, and the MCP not-applicable branch is out of scope. Notes folded in: `test_index_source_guard.py` pin and file added; the four `FlushResult.error` consumers stated, with the two barrier rows receiving the path-free `error` only; contract sentence in `docs/specs/mcp-tool-surface.md` added (AC-10) and the single-module claim corrected; function-local import stated; refused and unsafe refs never echoed raw (Requirement 5, AC-7); step tracker defined before the first step; ACs put in numeric order. | Lane files under `.wavefoundry/work/23z45/review/`; `grep` for `flushed.error` (lines 353, 361, 415, 422); `initial_markdown is None` at line 318; `test_index_source_guard.py` line 170; contract paragraph at `docs/specs/mcp-tool-surface.md` line 1171 |
| 2026-11-20 | Readback: failed `context_efficiency_persistence` rows gain `operation` and, for a single-file step, `target` (repository-relative POSIX), with `error` rendered by `path_free_exception_text`; both unreadable-record rows gain the same keys; `FlushResult` gains `operation` and `target` and renders `error` path-free in both `except` branches through a function-local import; the outer flush handler does the same. The audit's degraded message and both CLI `NOTE degraded:` lines describe each audience degrade token with the quoted, escaped, truncated baseline ref and the affected paths through one helper in `techdocs_audit_lib.py`; `data.degraded`, the codes and the other row keys stay unchanged. ACs AC-1 to AC-10. Boundary: no other error rendering, the barrier rows receive only the path-free `error`, `compare_to_refused` is never echoed. Example: before `{'persistence': 'failed', 'projection': 'pending', 'error': 'PermissionError EACCES', 'wave_id': W}`; after the same row with `'operation': 'write_wave_record', 'target': 'docs/waves/W/wave.md', 'error': 'PermissionError EACCES on docs/waves/W/wave.md'`. | Files: the Serialization Points list. Retrieval: `code_read` and `memory_brief` through MCP. Gapfill: shell `grep` and `sed` used for test modules and line-ranged reads, because test modules are outside the code index and the review notes are work files. |
| 2026-11-20 | Implemented the context-efficiency rows. Steps derived from the lock block of `_project_context_efficiency_wave`: `acquire_publication_lock` (no target), `read_wave_record` (record), `parse_wave_record` (pure), `reconcile_checkpoint_authority`, `read_wave_snapshot` (store), `render_checkpoint_block` (pure), `render_exploration_block` (loads a script and reads several files, no target), `write_wave_record` (record), `mark_checkpoint_published`, `compact_published_wave` (store), `clear_focus_state` (no target). `_flush_context_efficiency` tracks `locate_wave_record`, `read_wave_record`, `parse_wave_record`, `reconcile_checkpoint_authority`, `derive_wave_stage`, `flush_telemetry`, `read_spool`, `project_checkpoint`. `FlushResult` gained `operation` (`transfer_general_rows` or `flush_telemetry`) and `target` (the store); the deferred and failed lifecycle rows copy them, the two barrier rows do not. Observation: per Requirement 2 a non-`OSError` now renders class plus path-free message (`ValueError: step failed`) where the broad handler rendered the class only, as security note N3 recorded. | `wf_server/context_efficiency_handlers.py`, `context_efficiency.py`; `FailedRowStepAndTargetTests` (9 tests) in `tests/test_server_context_efficiency.py`; `test_flush_error_is_path_free_and_names_the_store` and `test_importing_context_efficiency_loads_no_lifecycle_lock` in `tests/test_context_efficiency.py`; pin updated in `tests/test_index_source_guard.py` |
| 2026-11-20 | Implemented the audit message. `describe_degrade` and `DEGRADE_REF_DISPLAY_MAX` (80) in `techdocs_audit_lib.py`; the MCP diagnostic and both CLI notes call it. Form: `baseline_missing (baseline ref "nosuchref": docs/ARCHITECTURE.md, docs/references/project-overview.md)`. A truncated ref ends with `...` outside the closing quote and the cut falls between whole escapes. | `TechdocsAuditDegradeDescriptionTests` (5 tests) in `tests/test_techdocs_audit_lib.py`; the MCP handler is driven from that file, so `tests/test_server_tools.py` is unchanged |
| 2026-11-20 | Known-bad and landing evidence, run in a scratch copy of the scripts tree. With the five source files at HEAD: the audit class 4 failures and 2 errors (the refused-ref negative passes, as expected), `FailedRowStepAndTargetTests` 16 failures and 5 errors, the flush test 2 failures, the `test_index_source_guard.py` pin 1 failure. Mutants, each failing a named test: module-level import of `path_free_exception_text` fails `test_importing_context_efficiency_loads_no_lifecycle_lock`; helper reading entries without `degrade` fails `test_only_entries_with_a_degrade_field_are_described`; truncation removed, and raw ref unescaped, each fail `test_an_accepted_ref_is_rendered_escaped_and_truncated`; one step assignment deleted fails `test_every_step_in_the_lock_block_names_itself`; outer handler back to raw text fails `test_the_outer_flush_handler_names_its_step_without_an_absolute_path`. | Focused suites on the fixed tree: `test_techdocs_audit_lib` 91, `test_server_context_efficiency` 145, `test_context_efficiency` 108, `test_index_source_guard` 9, `test_lifecycle_mutation_lock` 69, `test_server_tools.TechdocsAuditToolTests` 12, `test_handler_modules` 13, all OK; logs under `.wavefoundry/work/23z45/23z90/` |
| 2026-11-20 | Platforms: `target` and the path in `error` are built with `as_posix()` or from fixed POSIX constants, so native Windows, macOS, Linux and WSL2 all render forward slashes; the path-free assertions cover raw, resolved and backslash root forms. Executed on macOS only; no native Windows, Linux or WSL2 run. The unreadable-record tests use undecodable bytes, not a mode change, so they hold on Windows. Full suite not run by this implementer (coordinator runs it last), so AC-8 and the last task stay open. Seen outside this change: `test_profile_literal_census` fails on a record-filename literal in `test_security_unsettled_disposition.py` lines 1078 to 1079. | `docs/specs/mcp-tool-surface.md` sentence (AC-10); one Unreleased changelog bullet under Changed |
| 2026-11-20 | Full-suite repair: the new record-target formatter now uses the existing contained-path helper. The audit test imports the handler by its package module path. Both failing repository census tests and the nine failed-row behavior cases passed together after the repair. | Path-containment census, retired-module census, and FailedRowStepAndTargetTests, 11 tests passed |
| 2026-11-20 | Delivery repair for D1-23z90-producer-lease-target, D1-23z90-unreadable-errno and D1-23z90-conditional-target-note. Two regression tests failed before repair. A contended producer lease now identifies its lock file before the transfer opens SQLite. Both wave readers report the errno and repository-relative record. The MCP reference and changelog describe when a row carries an operation and target. | 147 server telemetry tests, 108 ledger tests and 63 source, containment and server-package tests passed. On macOS, denying read access to the record produced EACCES in both rows and restoring access allowed publication. Denying file creation in the producer-lock directory produced EACCES with the relative lock target and zero transfer-store opens. Restoring write permission allowed a durable retry. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-20 | Selected: add `operation` and `target` keys to the failed context-efficiency rows and render `error` with the existing `path_free_exception_text`; describe audience degrade tokens with ref and paths through one shared helper, leaving the token list unchanged. | Replaying the field case: the AC-1 row would read `operation` write step, `target` the wave record, `error` `PermissionError EACCES on <record>`, which answers both missing facts. The keys are data the operator reads; nothing gates on them, so the change only informs. It reuses the path-free renderer and the `baseline_ref` the audit already records. Risk of misleading output: `target` names the step's intended file, while an `os.replace` failure may carry the temporary file in `error`; both appear, so neither is hidden. Success after release: the next field report of either failure names a file. | (a) Fold step and path into the `error` string only: smallest diff, but consumers would have to parse prose to get the file; rejected. (b) Wrap every exception in a new typed error class carrying path and operation through `context_efficiency.py`: covers more sites, but it is a new mechanism across a large module for two messages; rejected as oversized. (c) For TechDocs, encode ref and path in new degrade tokens: breaks the `degraded` machine contract and the exit-code logic that compares tokens; rejected. |
| 2026-11-20 | Operator decision: bring `_flush_context_efficiency`'s outer handler and `FlushResult.error` into scope; they must use the same `operation`, `target` and `path_free_exception_text` form. | They write into the same `context_efficiency_persistence` row, and the probe showed they record the absolute root there. | Keep them as a follow-up (the original plan); superseded by this decision. |
| 2026-11-20 | Operator decision: the TechDocs fix names the baseline ref and affected paths for both `baseline_untracked` and `baseline_missing`; the coordinator will ask the reporter which token they saw. | `no_baseline_commit` does not exist in the tree, and covering both tokens fixes either one. | none |
| 2026-11-20 | `no_baseline_commit` treated as the field report's paraphrase of `baseline_untracked` or `baseline_missing`. | The token does not exist in the tree (census above); these are the only baseline-absence tokens. | Ask the reporter for the literal text; not needed, because the fix covers both tokens. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A test pins the old failed-row `error` text or compares the whole row dictionary. | Run the focused suites first; update pinned expectations as part of the change. |
| `path_free_exception_text` keeps a non-`OSError` message only when it is path-free, so some rows still name only the class in `error`. | `operation` and `target` carry the step and file regardless of the exception's text. |
| The audit's sanctioned-advisory-site gate resolves diagnostic codes by AST. | The codes stay literals at their call sites; only the message argument changes. |
| A caller-supplied `--compare-to` ref appears in message text. | A refused ref is never echoed: the helper reads only entries with a `degrade` field. `_ref_refused` does not bound length or reject every control character, so the helper renders each ref quoted, ASCII-escaped and truncated (Requirement 5, AC-7). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
