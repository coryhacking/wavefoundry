# Census the bytecode guard on test child spawns

Change ID: `22ubd-debt test-child-spawn-bytecode-census`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-07
Wave: TBD

## Rationale

Wave 22u26's readiness QA review (finding `22u26-qa-unguarded-children`) found that tests spawn `sys.executable` children that import framework modules with neither `-B` nor `PYTHONDONTWRITEBYTECODE`. Under a bare `unittest` run, such a child writes `.pyc` files beside the framework sources; the canonical `run_tests.py` is unaffected because its workers set the variable. 22u26 guards the three known sites. A first count found 202 `sys.executable` lines without `-B` on the same line across 99 test files; many are guarded by an environment helper or import nothing from the framework, so the real number of unguarded sites is unknown.

## Product Intent

A maintainer can run any framework test module under a bare `unittest` without leaving framework bytecode, and a newly added unguarded child spawn fails a test.

## Requirements

1. Every test child spawn that can import framework modules runs with `-B` or `PYTHONDONTWRITEBYTECODE`.
2. A census test fails on a new unguarded spawn and states the spawn forms it cannot see statically.

## Scope

**In scope:** `.wavefoundry/framework/scripts/tests/` spawn sites and a census test.

**Out of scope:** framework source spawns, which the existing bytecode census in `run_tests.py` covers.

## Acceptance Criteria

- [ ] AC-1: The census reports no unguarded spawn on the repaired tree and reports a planted unguarded spawn in a scratch source.
- [ ] AC-2: A bare `unittest` run of the full test directory in a scratch copy, without `PYTHONDONTWRITEBYTECODE`, leaves no framework `__pycache__`.
- [ ] AC-3: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Classify the spawn sites.
- [ ] Guard the unguarded ones.
- [ ] Add the census test with its planted known-bad.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| tests      | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: test-only.

## Platform Behavior

Test-only Python; identical on Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | important | Keeps new spawns guarded. |
| AC-2 | important | The observable outcome. |
| AC-3 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-07 | Filed from wave 22u26 readiness (QA finding `22u26-qa-unguarded-children`), split from 22qr7's Requirement 4. | `grep -c sys.executable` over tests/ |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-07 | Split from 22qr7 | The census's size is unknown and larger than 22qr7's other items | Census in 22qr7 |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A static census misses runtime-built spawns | AC-2 checks the outcome directly |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
