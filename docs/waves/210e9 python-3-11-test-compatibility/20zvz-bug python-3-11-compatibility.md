# Framework tests run on Python 3.11

Change ID: `20zvz-bug python-3-11-compatibility`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: 210e9 python-3-11-test-compatibility

## Rationale

Python 3.11 is the supported minimum (`venv_bootstrap.MIN_PYTHON_VERSION`), and Waveforge reports framework test errors on 3.11. A full-suite run under Python 3.11.17, with the same pinned `mcp`, `apsw`, `lancedb` and tree-sitter packages as the shipped tool venv, fails in four test files. Every cause is in test code, and each comes from a Python 3.12 or 3.13 behaviour the tests assumed. Our own runs use Python 3.14, so none of this showed.

1. `tests/test_build_pack.py` does not compile on 3.11. `_assert_release_assets` opens a `TemporaryDirectory` plus a `with` of 20 items, which is 21 statically nested blocks. Python 3.11 refuses more than 20 per function ("too many statically nested blocks"), so the whole file fails to import. The 20th item, the qualification-gate stub, came in with wave 20wq7.
2. `tests/test_docs_lint.py` calls `Path.read_text(..., newline=...)` in two places (`ClosedInlineRecordLintTests._predicate` and `test_closed_inline_record_with_crlf_is_left_alone`). That keyword arrived in Python 3.13, so 17 tests raise `TypeError` on 3.11 and 3.12. Wave 20x1k added these.
3. `tests/test_python_parse_diagnostics.py` expects an invalid string escape to raise `SyntaxWarning`. Python 3.12 made it a `SyntaxWarning`; 3.11 raises `DeprecationWarning`, which is hidden by default. Four tests fail on 3.11. The tree-wide sweep `test_no_tracked_python_file_has_invalid_escape` uses the same filter, so on 3.11 it can never find an offender and passes vacuously.
4. `tests/test_server_tools_lifecycle.py::test_techdocs_baseline_precondition_fails_on_the_faithful_phase_one_tree` expects exactly one stderr line from `wf_cli.main`. On Python 3.11 and 3.12, `wf_cli` also prints the deprecated-runtime advisory, which makes two lines. The advisory is intended policy: 3.11 and 3.12 are deprecated but still supported, and the advisory goes to stderr only.

Two more failures in that run were environmental and are out of scope. `test_storage_upgrade_resume` needed `lancedb==0.33.0` and passes once it is installed. `test_mcp_tool_registry::test_reload_rebuilds_the_registry_from_fresh_code` clears the child environment, so its child found the 3.14 tool venv in the home directory; on a real 3.11 install that venv is 3.11. That second classification is inferred from the code (`venv_bootstrap.tool_venv_base` falls back to `~/.wavefoundry/venv` when the variable is absent), not observed on a 3.11 home venv.

## Requirements

1. `test_build_pack._assert_release_assets` registers the `sys.argv` patch through `self.enterContext` instead of the `with` statement, with a comment naming the 20-block limit. The function then has 20 nested blocks, and the file compiles on Python 3.11. Nothing else in the test changes. The patch is undone at test cleanup instead of at the end of the `with`, and nothing after the `with` reads `sys.argv`. `TestCase.enterContext` exists from Python 3.11, the minimum, and the file already uses it.
2. `test_docs_lint` reads the raw text with `read_bytes().decode("utf-8")` where it used `read_text(newline="")`, and with `read_text(encoding="utf-8")` where it used `newline=None`. The CRLF test still sees `\r\n`, and on 3.13 and later the decoded text is identical to what `newline=""` gave.
3. `test_python_parse_diagnostics` picks its expected category by version: `SyntaxWarning` on 3.12 and later, `DeprecationWarning` on 3.11. The `_syntax_warnings` helper filters on that category. The sweep `InvalidEscapeSweepTests.test_no_tracked_python_file_has_invalid_escape` has its own inline `SyntaxWarning` filter, which also changes to the selected category, so the sweep detects invalid escapes on 3.11 too. The subprocess test `test_real_graph_build_logs_fixture_path_not_unknown` asserts the selected category's name instead of the literal `SyntaxWarning`. On 3.11 only, because 3.11 hides `DeprecationWarning` by default, it runs its child with `-W always::DeprecationWarning`; on 3.12 and later the child command is unchanged. On 3.11 that test therefore proves the fixture path reaches the warning, not that a default-filter build log shows it, since such a log never shows it on 3.11. The `invalid escape sequence`, fixture-path and no-`<unknown>` assertions stay.
4. The techdocs test patches `wf_cli.runtime_advisory.python_runtime_advisory` to return `None`, which is how `test_setup_readiness` already isolates the advisory. The one-line assertion stays.
5. Test-only change. No product code changes. Behaviour is the same on Windows, macOS, Linux and WSL2: the edits touch in-process patches, a byte decode and a warning-category choice, with no platform-specific path or subprocess beyond the existing `sys.executable` child.

## Scope

**Problem statement:** four framework test files fail on Python 3.11, the supported minimum, and one 3.11 check passes vacuously.

**In scope:** Requirements 1 to 4 in the four named test files.

**Out of scope:**

- Product code: nothing in the 3.11 run failed outside tests.
- The two environmental failures named in the Rationale.
- A permanent 3.11 lane in the qualification profiles, or a static nested-block check. Both are possible follow-ups.

## Acceptance Criteria

- [x] AC-1: Under Python 3.11 with the shipped package pins, the four named files pass, and a whole-suite run has no failure except the two environmental ones named in the Rationale. Each skip in that run that the 1.32.0 release default report does not have is named with its reason in the Progress Log.
- [x] AC-2: In a git-initialised scratch copy with a `git add`ed fixture file holding an invalid escape, under Python 3.11 the old sweep filter passes and the new one fails, naming the fixture and an `invalid escape sequence` warning. This shows the sweep is no longer vacuous.
- [x] AC-3: Under the default Python 3.14 tool venv, the four files pass, and one whole-suite `--no-cache` run passes with a fresh green receipt.

## Tasks

- [x] Apply Requirements 1 to 4 to the four test files.
- [x] Run the four files under Python 3.11 and run the AC-2 sweep probe in a scratch copy.
- [x] Run the whole suite under Python 3.11, then once under 3.14 for the receipt.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| tests | implementer | none | Requirements 1 to 4 |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_build_pack.py`, `.wavefoundry/framework/scripts/tests/test_docs_lint.py`, `.wavefoundry/framework/scripts/tests/test_python_parse_diagnostics.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`

## Affected Architecture Docs

N/A: test-only repairs in four test files, with no boundary, flow or verification-architecture change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Python 3.11 is the supported minimum, and Waveforge runs it. |
| AC-2 | required | The sweep must actually check something on 3.11. |
| AC-3 | required | The receipt must be current before close. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned after two full-suite runs under Python 3.11.17. The first used unpinned packages, and most of its failures were environmental. The second used the shipped pins and left six failing files: these four, plus the two environmental ones. A scratch copy of the Requirement 1 fix compiles under 3.11. | scratchpad py311-run2.txt, py311fix |
| 2026-10-18 | Implemented under `framework_edit_allowed`. The four files pass under 3.11.17 and 3.14.8. AC-1: the whole suite under 3.11 with the shipped pins ran 11901 tests; the only failure is the environmental `test_mcp_tool_registry::test_reload_rebuilds_the_registry_from_fresh_code`, and `test_storage_upgrade_resume` passes with `lancedb==0.33.0`. Against the 1.32.0 release default report (12 skips) the 3.11 run has one extra skip: `test_server_tools_retrieval.MaybeRefreshIfStaleTests.test_completed_registered_child_is_reaped_before_refresh_decision`, reason "requires waitid with WNOWAIT to preserve child wait status". `os.waitid` reached macOS only in Python 3.13, and no product code calls it, so this is a capability skip. AC-2: in a git-initialised scratch copy with a `git add`ed `probe_bad.py` holding `"\d"`, under 3.11 the HEAD sweep passed and the new sweep failed with `probe_bad.py:1: invalid escape sequence '\d'`. AC-3: whole suite `--no-cache` under 3.14 ran 11901 tests, OK, with a fresh green receipt. Delivery: code and QA lanes approved after scratch mutants: inline filter reverted (sweep vacuous on 3.11), `-W` flag dropped, advisory patch dropped, argv patch back inside the `with` (3.11 SyntaxError), `filename=` dropped in chunker and graph indexer, and an extra precondition stderr line; each was caught. Gapfill: shell and scratch copies, because the checks needed a second interpreter and uncommitted files. | scratchpad py311-after.txt, py314-after.txt, ac2probe, del-code, del-qa; .wavefoundry/cache/qualification/py311-after.json |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-18 | Fix the tests and add no new mechanism. | Every failure is in test code, and smaller work wins. | A 3.11 qualification lane or a static nested-block check; possible follow-ups. |
| 2026-10-18 | Readiness review folded in: the sweep's inline filter named, `-W` only on 3.11, the skip comparison in AC-1, the AC-2 old-versus-new probe, the inferred registry classification, and the two 20-block functions in Risks. | Code, QA, red-team and architecture reviewers. | Forward `WAVEFOUNDRY_TOOL_VENV` into the registry reload child; not taken, since a real 3.11 install passes and smaller work wins. A parked tech-debt stub for the follow-up; not taken, the Risks row records the recipe. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A later test again uses a 3.12-or-later feature. | Not mitigated here. Reproduction recipe: run the whole suite under Python 3.11 with the shipped tool-venv pins and `WAVEFOUNDRY_TOOL_VENV` pointing at that venv. A permanent 3.11 lane, or a static check for 3.12-and-later APIs and nested blocks, is the follow-up. |
| `test_build_pack._assert_release_assets` and `test_release_main_rejects_extra_current_build_public_package` sit at 20 nested blocks after this change and at or near 20 respectively, so one more stub can break 3.11 again. | Named here for the next editor; the follow-up check above would catch it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
