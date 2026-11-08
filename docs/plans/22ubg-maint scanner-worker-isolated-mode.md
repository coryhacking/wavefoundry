# Start the Scanner Worker in Isolated Mode

Change ID: `22ubg-maint scanner-worker-isolated-mode`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-08
Wave: TBD

## Rationale

Waveforge's review of v1.40.0, item 2. `wave_lint_lib/betterleaks_worker._Client` starts the worker as `[sys.executable, "-B", <worker>, "--worker"]` through `subprocess_util.isolated_popen`, which passes the parent environment. Without `-I`, these can supply modules to the worker before `_serve` installs its offline audit hook:

- `PYTHONPATH`;
- the user site directory;
- the script directory.

The worker reads untrusted file content, so this is defence in depth.

The worker already puts its own `scripts/` directory on `sys.path` in its preamble. It imports `bytecode_cache`, `subprocess_util` and `wave_lint_lib.betterleaks_engine` from there and nothing else outside the standard library and the tool environment.

## Product Intent

The secret-scanner worker starts in Python's isolated mode, so environment variables, the user site directory and the current directory can no longer inject modules into it. Scan results are unchanged.

## Requirements

1. The default command becomes `[sys.executable, "-I", "-B", <worker>, "--worker"]`.
2. The worker still finds its own modules through the explicit `scripts/` insertion it already makes. The tool environment's own site-packages stay available, because `-I` drops only the user site.
3. Nothing the worker relies on comes from `PYTHON*` variables, which `-I` ignores. The implementer confirms this for `PYTHONUTF8`, `PYTHONIOENCODING` and `PYTHONPYCACHEPREFIX`: the worker uses binary stdio and `-B`.

## Scope

**In scope:** the command in `betterleaks_worker.py`, a test, and a CHANGELOG bullet.

**Out of scope:** other framework child processes. A census of those is a separate question.

## Platform Behavior

`-I` behaves the same on Windows, macOS, Linux and WSL2 (CPython 3.11 and newer). The Windows launch flags from `isolated_popen` are unchanged. The scanner test modules run on all three in CI profiles.

## Acceptance Criteria

- [ ] AC-1: The worker's default command has `-I` and `-B` before the script path. On the current code it has no `-I`.
- [ ] AC-2: With `PYTHONPATH` naming a directory that holds a planted `json.py` (or another module the worker imports), the worker's scans complete and the planted module is never imported. A marker file the module would write is absent. On the current code the marker is written.
- [ ] AC-3: The existing scanner suites (`test_scanner_*`, `test_betterleaks_*`) pass on Python 3.11 and 3.14.

## Tasks

- [ ] Add `-I` to the default command.
- [ ] Test for AC-2.
- [ ] CHANGELOG `[Unreleased]` bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| worker | implementer | none | one-line change and test |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/betterleaks_worker.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: one child-process flag.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The change |
| AC-2 | required | Proves the isolation is real |
| AC-3 | required | No scan regression |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-08 | Planned from Waveforge item 2. | operator answer |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-08 | `-I` on the command line | Smallest change; the worker already adds its own path | Scrub the environment in the parent |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A distribution relies on `PYTHONPATH` to reach worker modules | The worker adds `scripts/` itself; noted in the CHANGELOG |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
