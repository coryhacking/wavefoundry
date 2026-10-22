# Setup Refuses a Root Without the Framework Copy

Change ID: `21ayw-bug setup-refuses-root-without-framework`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-21
Wave: 21cw4 windows-pack-setup-root-and-record-hardening

## Rationale

A privately reported issue, verified at `1c5ba851`: `wf setup --root <dir>` on a folder without `.wavefoundry/framework/` keeps going after `_provision_lifecycle_policy_if_absent` (`.wavefoundry/framework/scripts/setup_wavefoundry.py:166`) prints "skipping provisioning" and returns 0. Step 1 (`:365`) then runs the platform render with `--include-permissions` against that folder. Pointed at a home folder by mistake, the render merges the MCP allow rules, the managed-allow marker and the hook events into the user's global host settings. No supported flow runs setup on a root without the framework: the install guide's Step 1 runs setup on the installed checkout, and the provisioning docstring states the pack is always extracted first.

## Product Intent

An operator who points setup at the wrong folder gets an immediate refusal naming `--root`, and the folder is left exactly as it was. Before: setup renders host settings, hooks and permissions into any folder, including a home folder. After: setup proceeds only in a root that holds the framework copy. Boundaries: `wf setup --check` and `--check-gpu` stay read-only and unaffected; a correct root behaves as today. AC-1 with AC-2 tests whether the intent was established.

## Requirements

1. After the `--check`, `--help` and `--check-gpu` branches, setup resolves the root and exits non-zero, before the Python and tool-environment checks, setup reconciliation, provisioning, rendering or any other step, when `<root>/.wavefoundry/framework` is not a directory.
2. The refusal message names `--root`, says the folder is not a Wavefoundry repository root, and prints no absolute path beyond the root the operator supplied.
3. `--check`, `--check-gpu` and `--help` keep their current behaviour.
4. A root whose framework entry is a regular file or missing is refused the same way. A framework entry that is a link to a directory is accepted, as today (developer checkouts may link it).

## Scope

**Problem statement:** setup writes host settings and permissions into a folder that is not a Wavefoundry repository.

**In scope:**

- The root check in `setup_wavefoundry.main` and its message.
- The provisioning anchor guard stays as a second line of defence.
- Tests for an empty folder, a home-like folder with existing host settings, and a valid root.
- Existing setup tests whose fixture roots lack the framework directory (`tests/test_setup_wavefoundry.py`, `tests/test_setup_reconciliation.py`, and any setup-readiness integration test that calls setup's `main`) gain one.

**Out of scope:**

- The render CLI run directly (`render_platform_surfaces.py --repo-root`), which is a framework-internal entry with its own discovery.
- Any change to what setup writes in a valid root.

## Acceptance Criteria

- [x] AC-1: Setup against an empty temporary folder exits non-zero, names `--root` in its message, leaves the folder empty (no entries created), and never reaches the Python check or setup reconciliation (both patched and asserted uncalled).
- [x] AC-2: Setup against a folder laid out like a home folder, with an existing `.claude/settings.json` and `.codex/config.toml`, exits non-zero and leaves both files byte-identical and creates no other entry; on the current code the same fixture is modified.
- [x] AC-3: A root whose `.wavefoundry/framework` is a regular file is refused; `--check` against a folder without the framework still reports readiness without writing.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the root check in `main` after the `--check`, `--help` and `--check-gpu` branches, before the Python checks and `setup_reconciliation.session`.
- [x] Give existing setup test fixtures a framework directory where they call `main` on a bare root.
- [x] Add the empty-folder, home-like folder, file-not-directory and `--check` tests, with a scratch HOME so no real host settings are reachable.
- [x] CHANGELOG Unreleased entry (Fixed), worded without exploit detail, noting that setup now exits non-zero on such a root.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                             |
| ---------- | ----------- | ---------- | --------------------------------- |
| guard      | implementer | none       | root check before any setup write |
| tests      | implementer | guard      | scratch HOME fixtures             |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: an early refusal in one entry point; no boundary, flow or verification seam changes.

## Platform Behavior

The check is a directory test on a path, identical on native Windows, macOS, Linux and WSL2. On Windows a home folder is `%USERPROFILE%`; the fixture uses a temporary folder on every platform, so no test touches a real profile.

## AC Priority


| AC   | Priority | Rationale                         |
| ---- | -------- | --------------------------------- |
| AC-1 | required | refusal before any write          |
| AC-2 | required | the reported home-folder case     |
| AC-3 | required | non-directory and check unchanged |
| AC-4 | required | change-local verification         |


## Progress Log


| Date       | Update  | Evidence                                          |
| ---------- | ------- | ------------------------------------------------- |
| 2026-10-21 | Planned | private report, verified at `1c5ba851`            |
| 2026-10-21 | Readiness amendments: check moved ahead of the Python and environment steps; linked framework directory stays accepted (Requirement 4 narrowed); existing fixture updates named. | readiness qa-reviewer, code-reviewer and security-reviewer findings |
| 2026-10-21 | Implemented: `_root_has_framework` in `setup_wavefoundry.py`, called in `main` after `--check`/`--help` and before the Python check for every non `--check-gpu` run; refusal names `--root` and only the supplied root. New `SetupRootWithoutFrameworkTests` (empty folder, home-like folder, file entry, linked directory, `--check`) with a scratch HOME; `SetupWavefoundryTests` sandbox and four fixtures gain `.wavefoundry/framework/`. | known-bad: on the HEAD code 3 refusal tests fail (setup runs on to dependency provisioning) and the link test errors; the HEAD Step 1 render changed both home-like files (checksums differ). Focused `test_setup_wavefoundry.py` 55 ok, `test_setup_reconciliation.py` 47 ok, `test_setup_readiness.py` 52 ok, `test_setup_readiness_integration.py` 20 ok |
| 2026-10-21 | Delivery repair cycle 1: the full suite found `test_memory_backfill` calling setup's `main` on a root without `.wavefoundry/framework/`; that fixture now creates it, like the other setup fixtures. | full suite 12036 tests, 1 failing file before; `test_memory_backfill` 52 OK after; old fixture fails 4 and errors 1 in a scratch copy |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-21 | Refuse in `main` before reconciliation | Nothing is written before the check | Make the provisioning guard fatal (runs after reconciliation reads the root); guard only the permissions render (other surfaces still land in the wrong folder) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A test or flow runs setup on a frameworkless temporary root | Scope names the affected test files; no supported flow does (install runs setup on the installed checkout) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
