# uv Refusal Tests Expect the Platform's Setup Command

Change ID: `1zlu5-debt uv-refusal-tests-platform-command`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls7 waveforge-defect-fixes

## Rationale

Wave `1zls6` added `assert_uv_required_refusal` in `tests/test_setup_index.py`. Its `command` parameter defaults to the POSIX form `` `wf setup` ``, but `_uv_required_message()` correctly emits `` `.\.wavefoundry\bin\wf.cmd setup` `` when `os.name == "nt"`. Four tests call the helper without overriding the default (the no-uv refusal, both `_install_deps` callers, the end-to-end failed-bootstrap detector, and the bootstrap-timeout path), so they fail on Windows. Found in operator review after `1zls6` was committed; fixed here because `1zls7` is the open wave.

## Requirements

1. `assert_uv_required_refusal` derives its default expected command from the platform the same way `_uv_required_message` does (`os.name == "nt"` gives the `wf.cmd` form, otherwise `` `wf setup` ``), when the caller passes no `command`.
2. The two explicit message tests keep their explicit expectations: the Windows form test passes the `wf.cmd` command, and the POSIX form test passes `` `wf setup` `` with `windows=False`.
3. No change to `setup_index.py`.

## Scope

**Problem statement:** four refusal tests hardcode the POSIX command and fail on Windows.

**In scope:**

- `assert_uv_required_refusal` in `tests/test_setup_index.py`, and the POSIX message test's explicit expectation.

**Out of scope:**

- Any change to the refusal message or `setup_index.py`.

## Acceptance Criteria

- [x] AC-1: With `os.name` patched to `"nt"`, the four default-command callers' shape passes (the helper expects the `wf.cmd` form), and with `os.name` as `"posix"` it expects `` `wf setup` ``; a test pins both.
- [x] AC-2: The Windows and POSIX message tests keep explicit expectations and still pass.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Derive the helper's default command from the platform; pass the POSIX command explicitly in the POSIX message test.
- [x] Add a test that pins the default for both platforms.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| refusal-tests | implementer | none | tests/test_setup_index.py only |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

## Affected Architecture Docs

N/A: a test-only change confined to one test helper.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The four tests must pass on Windows. |
| AC-2 | required | The explicit platform message tests stay explicit. |
| AC-3 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Implemented. `assert_uv_required_refusal` now defaults to `platform_setup_command()` (the `os.name == "nt"` rule `_uv_required_message` uses); the POSIX message test passes `` `wf setup` `` explicitly. New `InstallIsolationTests.test_the_default_expected_command_follows_the_platform` patches `os.name` to `nt` and `posix`. Mutation (default hardcoded to `` `wf setup` ``) fails it on the `nt` case. | `test_setup_index` 194 OK run directly with unittest (the runner's repository-change guard trips while the wave's implementer edits the tree); mutation in a scratch copy |
| 2026-10-02 | Planned from operator review of wave `1zls6` (P2). | Default-command callers at `test_setup_index.py` lines 1915, 1929, 1966, 2087 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Fix in the open wave `1zls7` rather than reopening `1zls6` | `1zls6` is closed and committed and only one wave may be open | Reopen `1zls6` after `1zls7` |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The helper drifts from the message's platform rule | It uses the same `os.name == "nt"` test as `_uv_required_message`; AC-1 pins both platforms. Behaviour on macOS, Linux and WSL2 is unchanged |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
