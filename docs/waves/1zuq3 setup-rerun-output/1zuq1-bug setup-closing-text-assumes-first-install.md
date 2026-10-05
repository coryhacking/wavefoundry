# Setup's Closing Message Gives First-Install Instructions On Every Run

Change ID: `1zuq1-bug setup-closing-text-assumes-first-install`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-04
Wave: 1zuq3 setup-rerun-output

## Rationale

Field report (1.29.0+puha, a long-installed target with no `.wavefoundry/install-log.md`): a routine `wf setup` rerun ended by telling the operator to "mark Phase 1 complete in .wavefoundry/install-log.md and proceed to Phase 2 by calling wf_audit_install()". The final print in `setup_wavefoundry.main` is unconditional, so every full-core success gives first-install instructions, which on an installed repository point at a log that does not exist and an audit that does not apply.

## Requirements

1. `setup_wavefoundry.main` chooses the closing message with one helper, `_install_in_progress(repo_root)`: true only when `install_log_lib.read_install_log` returns text and either the log is unparseable (`install_log_lib.is_unparseable`) or a Phase 1 row is still pending (`filter_phase(parse_log(text), 1)` has a `is_pending` row). A read error (`OSError`) counts as in progress, so the install wording, which names the log, is the conservative choice.
2. When an install is in progress, the closing message is unchanged.
3. Otherwise the closing message keeps the existing restart guidance verbatim (fully quit and reopen the agent, or start a fresh conversation after the host's MCP restart; do not resume an old session) and then says to confirm with `index_health()` or `wf setup --check`; it does not mention the install log, Phase 1, Phase 2 or `wf_audit_install()`. The existing pin `test_setup_wavefoundry.test_success_message_requires_fresh_agent_session` (no install log, so the rerun text) keeps passing.
4. The partial-run and pending-memory closing messages are unchanged.
5. CHANGELOG gets a bullet under `## [1.29.0]` `### Fixed`.

## Scope

**Problem statement:** setup's success message assumes a first install.

**In scope:**

- `setup_wavefoundry.main` closing print and the new helper; tests; CHANGELOG.

**Out of scope:**

- Install-log content, seed 011 row 1.3 text, `wf_audit_install`.

## Acceptance Criteria

- [x] AC-1: With no install log, a full setup run's closing output names `index_health()` and contains none of `install-log`, `Phase 2`, `wf_audit_install`.
- [x] AC-2: With an install log whose Phase 1 has a pending row, the closing output is the first-install text (names the install log and `wf_audit_install()`).
- [x] AC-3: With an install log whose Phase 1 rows are all done (a later phase pending or none), the rerun text is used.
- [x] AC-4: An unparseable or unreadable install log gives the first-install text.
- [x] AC-5: Forcing the helper to always return True, or always False, fails the tests (scratch copy).
- [x] AC-6: CHANGELOG describes the fix; docs validate.

## Tasks

- [x] Add `_install_in_progress` and branch the closing print
- [x] Add tests for no log, Phase 1 pending, Phase 1 done, unparseable or unreadable log
- [x] Show the mutants fail in a scratch copy
- [x] CHANGELOG bullet

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                     |
| ---------- | ----------- | ---------- | ------------------------- |
| closing    | implementer | —          | setup_wavefoundry, tests  |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_setup_wavefoundry.py`

## Affected Architecture Docs

N/A: operator-facing text selection inside one entry point.

## Platform Behavior

Identical on Windows, macOS, Linux and WSL2: a file read and a string choice. `read_install_log` already reads UTF-8 with replacement, so a Windows-encoded log reads as unparseable and keeps the install wording.

## AC Priority


| AC   | Priority | Rationale                                   |
| ---- | -------- | ------------------------------------------- |
| AC-1 | required | the field-reported defect                    |
| AC-2 | required | first installs keep their instructions       |
| AC-3 | required | a finished install is a rerun                |
| AC-4 | required | conservative on a log it cannot read         |
| AC-5 | required | the pins must catch a revert                 |
| AC-6 | required | release notes                                |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-04 | Implemented: `_install_in_progress` (read error, unparseable log or a pending Phase 1 row means in progress; no log means not) chooses between the install text and the rerun text, which shares the restart guidance and ends with `index_health()` or `wf setup --check`. Tests: no log, Phase 1 pending, Phase 1 done, UTF-16 log and a read error | `test_setup_wavefoundry` OK; scratch mutants C1-C4 killed against a green baseline |
| 2026-10-04 | Readiness review folded in: rerun text keeps the restart wording so the existing fresh-session pin holds; edge cases recorded in Risks | readiness reviewer findings 1-2 |
| 2026-10-04 | Planned from the 1.29.0+puha field report | `setup_wavefoundry.main` final print is unconditional; `install_log_lib.read_install_log`, `parse_log`, `filter_phase`, `is_unparseable` exist |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-04 | First install means a live install log with Phase 1 pending | the install log is the install's own state; a repository without one has no install in progress | infer from seeded docs or an index (indirect, and true after any install) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A first install whose agent has not yet created the log gets the rerun text | the install prompt creates the log before running setup (seed 011); the rerun text still says to restart and confirm |
| A finished install whose row 1.3 was left `[ ]` keeps the first-install text; an empty log gets the rerun text | both are the conservative or harmless side; accepted |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
