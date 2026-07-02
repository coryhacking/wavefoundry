# Stop on missing or too-old python3

Change ID: `1p9hh-bug python3-prereq-stop`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-02
Wave: `1p9hi python3-prereq-stop`

## Rationale

Wavefoundry's committed MCP and hook launch surfaces use `python3`. Setup currently prints an alternate absolute tool-venv MCP stanza around the same failure path, which can make a missing or too-old `python3` look recoverable by bypassing the declared launch contract. The prerequisite should be unambiguous: before install/setup proceeds, `python3 --version` must work from the command line and report Python 3.11 or newer.

## Requirements

1. `wf setup` must stop before surface rendering and MCP dry-run when `python3` is missing from PATH.
2. `wf setup` must stop before surface rendering and MCP dry-run when `python3` resolves to a Python version below 3.11.
3. The diagnostic must instruct the agent/operator to fix PATH or install Python so `python3 --version` succeeds and reports Python 3.11 or newer before proceeding.
4. Setup/docs/seeds must not suggest bypassing this prerequisite with a per-machine absolute tool-venv MCP command for this scenario.

## Scope

**Problem statement:** Missing or too-old `python3` should be a hard setup prerequisite failure with direct operator instructions, not a condition that suggests alternate MCP launch shapes.

**In scope:**

- Update setup prerequisite messaging and ordering so the stop condition is explicit.
- Update install guidance and framework seed text that describes the Python prerequisite.
- Add focused tests for missing and below-minimum `python3` diagnostics.

**Out of scope:**

- Supporting `python` as an equivalent committed launch command.
- Changing generated MCP surfaces away from `command: "python3"`.
- Changing the minimum supported Python version.

## Acceptance Criteria

- [x] AC-1: Missing `python3` during setup fails closed with an instruction to run `python3 --version` and get Python 3.11+ before proceeding.
- [x] AC-2: `python3` resolving below 3.11 during setup fails closed with the same prerequisite instruction.
- [x] AC-3: Setup no longer prints or recommends an absolute tool-venv MCP fallback as recovery for missing PATH `python3`.
- [x] AC-4: Install prompt and seed guidance state the prerequisite consistently.
- [x] AC-5: Focused regression tests and the framework test suite pass.

## Tasks

- [x] Update setup/venv prerequisite diagnostics.
- [x] Update install docs and seed guidance.
- [x] Add or adjust regression tests.
- [x] Run framework tests.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Setup prerequisite | implementer | - | Keep generated MCP command contract unchanged. |
| Docs and seeds | implementer | Setup prerequisite | Align operator-facing guidance. |
| Verification | implementer | Setup prerequisite, Docs and seeds | Focused tests plus full framework suite. |


## Serialization Points

- `venv_bootstrap.py` and `setup_wavefoundry.py` share the operator-facing failure contract.

## Affected Architecture Docs

N/A. This is a setup prerequisite and guidance correction within the existing MCP launch architecture; it does not change module boundaries or runtime topology.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Missing `python3` is the reported install failure class. |
| AC-2 | required | Too-old `python3` is equally invalid across all environments. |
| AC-3 | required | The fix is to stop and repair the prerequisite, not bypass it. |
| AC-4 | important | Agents/operators rely on the seed and prompt text during setup. |
| AC-5 | required | Behavior must be locked by tests. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-02 | Change scoped and admitted to wave `1p9hi`. | Operator request; change doc. |
| 2026-07-02 | Implemented prerequisite-stop behavior and guidance updates; focused tests pass. | `venv_bootstrap.py`, `setup_wavefoundry.py`, install prompt/seed diffs; `python3 -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_venv_bootstrap.py`; `python3 -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_setup_wavefoundry.py`. |
| 2026-07-02 | Full verification passed. | `python3 .wavefoundry/framework/scripts/run_tests.py` -> 4088 OK; `wave_validate` -> docs-lint ok. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-02 | Keep `python3` as the committed launch command and fail setup if it is unavailable or too old. | Existing generated surfaces and tests intentionally use byte-identical `python3`; the operator wants a prerequisite stop. | Accept `python` on Windows; rejected as out of scope for this fix. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| GUI hosts may not inherit shell PATH even when a terminal does. | Keep the prerequisite centered on command-line setup; host-specific GUI PATH repair remains an operator configuration task after `python3 --version` works in the setup environment. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
