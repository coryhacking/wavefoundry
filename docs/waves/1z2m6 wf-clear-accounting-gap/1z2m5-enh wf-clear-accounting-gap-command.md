# Add `wf clear-accounting-gap`

Change ID: `1z2m5-enh wf-clear-accounting-gap-command`
Change Status: `review`
Owner: Engineering
Status: active
Last verified: 2026-09-26
Wave: 1z2m6 wf-clear-accounting-gap

## Rationale

Wave `1z2m4` added a supported way out of the Context Efficiency accounting gap, but the command is a raw script path: `python3 -B .wavefoundry/framework/scripts/context_efficiency.py --root <repo> --clear-gap`. Every other operator action runs through the `wf` dispatcher. The operator asked for a `wf` command, named after the state people see in `## Context Efficiency` (`accounting_gap`) rather than its cause: a database lock is one cause among several, and it has already released by the time anyone clears the gap.

## Requirements

1. `wf clear-accounting-gap` (native Windows: `.\.wavefoundry\bin\wf.cmd clear-accounting-gap`) runs the existing `clear_accounting_gap` through the `wf_cli` dispatcher and prints its JSON result. It appears in `wf --help`.
2. With no `--root`, the command targets the repository that contains the framework it runs from (the directory three levels above `context_efficiency.py`), not the current directory, so it works from any subfolder. `--root` still overrides it.
3. The `accounting_gap` diagnostic (`_gap_diagnostic`, via `CLEAR_GAP_COMMAND`) names `./.wavefoundry/bin/wf clear-accounting-gap`, noting `wf.cmd` on Windows.
4. On Windows, the clear retries a sharing violation (`PermissionError`, WinError 32) when renaming the gap file, for up to 2 seconds (`SHARING_RETRY_BUDGET_SECONDS`), because another process reading the gap reason or an antivirus scan can hold it open. The budget is short because the clear holds the store's write lock; elsewhere `PermissionError` is not retried. A lasting violation leaves the gap in place.
5. `docs/specs/mcp-tool-surface.md`, `docs/architecture/data-and-control-flow.md` step 9 and the `CHANGELOG.md` `[Unreleased]` Context Efficiency bullet name the `wf` command instead of the script path.

## Scope

**Problem statement:** the only documented way to clear the gap is a long script path with an explicit root.

**In scope:**

- the dispatcher entry and help text, the default root, the diagnostic text, docs and changelog.

**Out of scope:**

- any change to what the clear does (wave `1z2m4`), an MCP tool for it, and a bare `wf clear` alias (ambiguous with index, cache and gate state).

## Acceptance Criteria

- [x] AC-1: `wf_cli._SUBCOMMANDS["clear-accounting-gap"]` routes to `context_efficiency`, it is listed in `wf --help`, and running `wf clear-accounting-gap` in a repository with a gap clears it and prints the JSON result.
- [x] AC-2: run with no `--root` from a subdirectory, the command clears the gap of the repository that contains the framework, not the current directory.
- [x] AC-3: the `accounting_gap` health diagnostic names `wf clear-accounting-gap`.
- [x] AC-4: The change's own tests pass and the documents this change edits validate.
- [x] AC-5: a transient `PermissionError` on the rename is retried and the clear succeeds; a lasting one raises and leaves the gap in place; off Windows it is not retried.

## Tasks

- [x] Add the dispatcher entry and help text.
- [x] Default the root to the containing repository; update `CLEAR_GAP_COMMAND`.
- [x] Tests for AC-1 to AC-3; docs and changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Command | implementer | readiness | Single write owner |
| Review | combined reviewer | Command | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_cli.py`, `.wavefoundry/framework/scripts/context_efficiency.py`, `.wavefoundry/framework/scripts/tests/test_wf_cli.py`, `.wavefoundry/framework/scripts/tests/test_context_efficiency.py`, `docs/specs/mcp-tool-surface.md`, `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` step 9 names the clear command.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The requested command |
| AC-2 | required | A cwd-dependent root would clear nothing, or the wrong repository |
| AC-3 | required | The diagnostic is where operators learn the command |
| AC-4 | required | Verification |
| AC-5 | required | A Windows reader must not make the operator's clear fail |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-26 | Operator asked for a Windows review; added `_replace_with_retry` for the clear's gap-file renames (2-second budget, Windows only). Three tests; a mutant that drops the retry fails one | `GapRecoveryTests` |
| 2026-09-26 | Delivery review approved (no blocking findings); its nit fixed: the diagnostic gives the POSIX and Windows commands as separate code spans (`CLEAR_GAP_COMMAND_WINDOWS`), pinned by a test. Full suite green: 9701 tests across 128 files | `run_tests.py --no-cache` |
| 2026-09-26 | Implemented: `_SUBCOMMANDS['clear-accounting-gap']` with prefix `--clear-gap` (readiness N1) and a help line; `context_efficiency._default_root()` (patchable seam, readiness N3) replaces the cwd default; `CLEAR_GAP_COMMAND` names the `wf` forms; the diagnostic test asserts the new text (N2); the AC-2 test calls `main` from a temp subfolder, not through the shim (N4). Mutants (cwd default root, missing prefix) each fail a test | `test_wf_cli.ClearAccountingGapSubcommandTests`; `test_context_efficiency.GapRecoveryTests` |
| 2026-09-26 | Planned at the operator's request after wave `1z2m4`; the name follows the `accounting_gap` state, not the lock that may have caused it | Operator decision |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-26 | Name it `wf clear-accounting-gap` (operator) | Matches the `accounting_gap` status in `## Context Efficiency`; a lock is only one cause and is gone by clear time | `wf clear` (ambiguous); `wf clear-gap` (does not say which gap) |
| 2026-09-26 | Supersede the `1z2m4` decision to keep the clear off the `wf` dispatcher | The dispatcher is the operator CLI surface and adding an entry is a one-line map change | Keep the script path |

## Risks

| Risk | Mitigation |
| --- | --- |
| The default root resolves wrongly in a packaged install | The framework layout is `<repo>/.wavefoundry/framework/scripts/` in both the source and packaged trees; AC-2 tests it from a subdirectory |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
