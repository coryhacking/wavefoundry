# Setup's uv Lookup Can Pick A uv From The Repository

Change ID: `1zv84-bug setup-uv-lookup-trusts-repo`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv87 downstream-security-hardening

## Rationale

Downstream report (Waveforge S3, confirmed by reading at `fdd8de15`): `setup_index._uv_bin` falls back to `shutil.which("uv")`. The `wf` and `wf.cmd` launchers start in the repository root, and on Windows the current folder is searched for commands, while on POSIX an empty or `.` PATH entry resolves there too. A `uv` planted in the repository can therefore be run by setup, and a PATH `uv` takes precedence over the hash-verified bootstrap.

## Requirements

1. `_uv_bin` resolves a PATH `uv` with an explicit scan of `PATH` that skips empty, `.` and other relative entries and any entry inside the current folder or the target root, and never consults the current folder implicitly; `shutil.which` is not used at all (on Windows it inserts the current folder even with an explicit `path=`). On Windows only `uv.exe` is accepted (no `.cmd`/`.bat` shims, which carry batch argument-injection risk).
2. A candidate that resolves inside the target root is refused even when reached through an absolute PATH entry. `root` is threaded from the callers (`_bootstrap_uv`, `install_requirement_specs`, `_install_deps`); when a caller has no root, candidates under the current folder are refused (the launchers start in the repository root).
3. The venv `uv` keeps first place and the hash-verified bootstrap stays the fallback when no acceptable `uv` is found.
4. CHANGELOG gets a bullet under `## [1.29.0]` `### Security`.

## Scope

**Problem statement:** a repository-planted `uv` can be selected by setup.

**In scope:**

- `.wavefoundry/framework/scripts/setup_index.py` `_uv_bin` and a small PATH-scan helper; tests; CHANGELOG.

**Out of scope:**

- Preferring the bootstrap over a trusted PATH `uv` (behavior change for every operator; recorded as considered).

## Acceptance Criteria

- [x] AC-1: With a fake executable `uv` in the target root, the working directory set to the target root and `PATH` containing `.` and an empty entry, `_uv_bin` does not return the planted `uv` (returns the venv `uv`, an outside PATH `uv`, or None).
- [x] AC-2: An absolute PATH entry pointing inside the target root is skipped.
- [x] AC-3: A `uv` in an ordinary absolute PATH folder outside the root is still found; on Windows only `uv.exe` is accepted and a `uv.cmd` on PATH is ignored (tested through a patched `os.name` or on Windows).
- [x] AC-4: Restoring `shutil.which("uv")` fails the AC-1 test (scratch copy).
- [x] AC-5: CHANGELOG Security bullet; docs validate.

## Tasks

- [x] Replace the `shutil.which` fallback with a filtered PATH scan
- [x] Refuse candidates inside the target root
- [x] Tests for planted `uv`, relative and empty entries, absolute in-root entry, normal PATH and Windows names
- [x] Show the mutant fails in a scratch copy
- [x] CHANGELOG Security bullet

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| uv-lookup | implementer | — | setup_index only |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`

## Affected Architecture Docs

N/A: one lookup helper.

## Platform Behavior

Windows: the implicit current-folder search is the main exposure and is removed by scanning `PATH` explicitly; only the literal `uv.exe` is accepted (`PATHEXT` is not consulted, so no `.cmd`/`.bat` shim runs). POSIX (macOS, Linux, WSL2): empty and `.` entries are skipped.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the reported path |
| AC-2 | required | the absolute variant |
| AC-3 | required | no regression |
| AC-4 | required | pin catches a revert |
| AC-5 | required | release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Implemented: `_trusted_path_uv(root)` scans `PATH` explicitly (skips empty, `.`, quoted-empty and relative entries and entries inside the current folder or root; refuses candidates whose realpath lands there; `uv.exe` only on Windows); `_uv_bin(venv_python, root=None)`; root threaded through `_bootstrap_uv`, `install_requirement_specs`, `_install_deps`; one existing assertion updated (a relative PATH entry is now refused). Tests `UvLookupTrustTests` (7) | mutants (`shutil.which` restored, in-root refusal dropped) fail |
| 2026-10-05 | Readiness review folded in: no `shutil.which`, `uv.exe` only on Windows, root threaded from the three callers, cwd refused when no root | readiness F8 |
| 2026-10-05 | Planned from the Waveforge private report S3 | `_uv_bin` uses `shutil.which("uv")`; launchers `cd` to the repository root |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Keep a trusted PATH `uv` ahead of the bootstrap | operators rely on their installed uv; the exposure is the repository-controlled locations, which are now excluded | always prefer the bootstrap |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `_uv_bin` does not know the target root | pass the root from its callers, or derive it from the setup context; tests pin both |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
