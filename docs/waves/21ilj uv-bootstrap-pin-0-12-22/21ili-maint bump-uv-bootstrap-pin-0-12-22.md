# Bump the uv Bootstrap Pin to 0.12.22

Change ID: `21ili-maint bump-uv-bootstrap-pin-0-12-22`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-24
Wave: 21ilj uv-bootstrap-pin-0-12-22

## Rationale

The package checklist (step 3) reviews the uv that `wf setup` installs when neither the tool environment nor `PATH` has one. The pin is `uv==0.12.17`. On 2026-10-24 the newest uv public for at least the 21-day package-age window is 0.12.22 (uploaded 2026-10-02); 0.12.23 (2026-10-03) and later are inside the window. 0.12.22 publishes 18 wheels, including Windows (win32, win_amd64, win_arm64), macOS (x86_64, arm64) and Linux (manylinux and musllinux), the same set as 0.12.17.

## Product Intent

A fresh `wf setup` on a machine without uv installs uv 0.12.22, verified against the 18 PyPI hashes; an existing uv of any version is still used as-is.

## Requirements

1. `UV_BOOTSTRAP_REQUIREMENT` becomes `uv==0.12.22`.
2. `UV_BOOTSTRAP_WHEEL_SHA256` is replaced in the same edit with every `bdist_wheel` filename and `digests.sha256` from `https://pypi.org/pypi/uv/0.12.22/json` (18 entries, none yanked).
3. No other behaviour changes: an existing uv is never replaced, and the install still uses `--require-hashes`.

## Scope

**Problem statement:** the bootstrap pin trails the newest eligible uv.

**In scope:**

- The two constants in `setup_index.py` and a CHANGELOG bullet.

**Out of scope:**

- uv 0.13.x (inside the package-age window).
- Any change to how uv is discovered or installed.

## Acceptance Criteria

- [x] AC-1: `setup_index.UV_BOOTSTRAP_REQUIREMENT == "uv==0.12.22"` and `UV_BOOTSTRAP_WHEEL_SHA256` holds exactly the 18 filename and hash pairs PyPI lists for 0.12.22, compared by a script against the PyPI JSON; Windows, macOS and Linux wheels are present.
- [x] AC-2: the existing uv pin tests in `tests/test_setup_index.py` pass, and the full framework suite passes.

## Tasks

- [x] Replace the two constants from the PyPI JSON.
- [x] Compare the table with PyPI by script.
- [x] Run `test_setup_index.py`, then the full suite.
- [x] Add a CHANGELOG bullet under 1.37.0.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| pin-bump   | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`

## Platform Behavior

Unchanged on Windows, macOS, Linux and WSL2: 0.12.22 publishes the same 18-tag wheel set as 0.12.17 (Windows win32, win_amd64 and win_arm64; macOS x86_64 and arm64; Linux and WSL2 through manylinux and musllinux), and the install path is unchanged.

## Affected Architecture Docs

N/A: two constants in one module; no boundary, flow or verification change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The pin and hashes are the whole change |
| AC-2 | required | The existing pin tests guard the table's shape |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-24 | Planned | Operator: "we can bump the uv version now". PyPI release list read 2026-10-24; 0.12.22 is the newest release older than 21 days |
| 2026-10-24 | Implemented. Cutoff rechecked at 15:10Z on 2026-10-24: 0.12.22 (2026-10-02T00:16Z) is past the 21-day window, 0.12.23 (2026-10-03T17:31Z) is not. Both constants replaced from the PyPI 0.12.22 JSON. AC-1: a fresh fetch compared with the parsed table: 18 of 18 filename and hash pairs match, with win32, win_amd64, win_arm64 and both macOS wheels. Real bootstrap in a scratch venv on macOS arm64 with the generated requirements line (`--require-hashes --only-binary :all: --no-deps`) installed `uv 0.12.22`; the same line with zeroed hashes was refused (`THESE PACKAGES DO NOT MATCH THE HASHES`). AC-2: `test_setup_index.py` 204 OK. Gapfill: the table was rewritten by a script from the PyPI JSON, a bulk-mechanical edit where MCP retrieval adds nothing. | implementation |
| 2026-10-24 | Delivery complete. code-reviewer and delivery Wave Council approved with no findings, each after an independent PyPI fetch and comparison; code-reviewer also repeated the real scratch-venv install. Full suite (`run_tests.py --no-cache`): 12113 tests OK. | delivery review |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-24 | Pin 0.12.22 | Newest release past the 21-day package-age window, same wheel set as the current pin | 0.13.x (inside the window); keep 0.12.17 (operator asked to bump) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A copied hash is wrong, so a fresh bootstrap refuses to install | AC-1 compares the table with the PyPI JSON by script |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
