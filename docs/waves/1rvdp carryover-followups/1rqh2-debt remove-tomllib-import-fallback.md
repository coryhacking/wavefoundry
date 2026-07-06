# Remove stale tomllib import fallbacks

Change ID: `1rqh2-debt remove-tomllib-import-fallback`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-07-06
Wave: TBD

## Rationale

`docs/architecture/decisions/12tm5-adr python-tool-environment.md` requires Python >= 3.11 specifically so that `tomllib` (stdlib since 3.11) is always available, and states new code "must not use `tomllib` import fallbacks." Two production call sites still carry a `tomllib` -> `tomli` -> `None` fallback chain that predates or was never reconciled with that ADR ruling. The fallback is dead weight: it can never take the `tomli`/`None` branch under the ADR's own minimum-version guarantee, and it invites new code to copy the same now-unnecessary pattern.

## Requirements

1. `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` imports `tomllib` directly (no `tomli`/`None` fallback), consistent with ADR `12tm5`.
2. `.wavefoundry/framework/scripts/render_agent_surfaces.py` imports `tomllib` directly (no `tomli`/`None` fallback) at its `.codex/config.toml` merge-validation call site.
3. Any now-dead fallback branches are removed rather than left unreachable — not just the import lines, but the **downstream code the `None` sentinel gated**: the `_require_tomllib()` guard and its fatal-diagnostic branch in `secrets_validators.py`, the `if tomllib is not None:` guards in `render_agent_surfaces.py` (the `else` of which was unreachable), and the `if tomllib is None: skipTest(...)` degrade-paths in the affected test. Under the ADR's ≥3.11 guarantee `tomllib` is never `None`, so these become always-true/always-false guards that should collapse, not linger as dead code.
4. Among the four originally-scoped test files, only `test_secrets_validators.py` actually carries the fallback chain (`import tomllib` → `import tomli` → `tomllib = None` at lines ~49-54, plus two inline repeats at ~1852/1869 and `if tomllib is None: skipTest` guards throughout). The other three (`test_setup_index.py`, `test_render_agent_surfaces.py`, `test_render_platform_surfaces.py`) **already import `tomllib` directly** and need no change — verified 2026-07-06. Update `test_secrets_validators.py` to import `tomllib` directly and drop the dead skip-guards; leave the other three untouched.

## Scope

**Problem statement:** Two production modules and several tests still use a `tomllib`/`tomli`/`None` import fallback chain that ADR `12tm5` says new code must not use, since Python >= 3.11 already guarantees `tomllib`.

**In scope:**

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` (fallback import ~12-18, `_require_tomllib()` guard ~38-41, merged-ruleset call sites ~1374/1386)
- `.wavefoundry/framework/scripts/render_agent_surfaces.py` (fallback import ~315-317, `if tomllib is not None:` guards ~333/424)
- The one test file that actually mirrors the fallback: `test_secrets_validators.py` (~49-54, inline repeats ~1852/1869, `if tomllib is None` skip-guards). The other three originally-listed test files already import `tomllib` directly — not in scope.

**Out of scope:**

- Any change to the ADR itself or the Python minimum-version policy
- Any change to TOML file formats, schemas, or the secrets-scan ruleset content
- Broader search for other `tomllib`/`tomli` fallback patterns outside the files named above (do a repo-wide grep at implementation time and fold in any additional hits found, but this doc does not pre-enumerate them)

## Acceptance Criteria

- [x] AC-1: `secrets_validators.py` imports `tomllib` directly; no `tomli` import attempt or `None`-fallback branch remains reachable. (Import collapsed to `import tomllib`; `_require_tomllib()` + its fatal-diagnostic branch deleted; both merged-ruleset call sites de-guarded.)
- [x] AC-2: `render_agent_surfaces.py` imports `tomllib` directly at its `.codex/config.toml` validation call site; no fallback branch remains. (Import collapsed; both `if tomllib is not None:` guards flattened.)
- [x] AC-3: Framework test suite (`python3 .wavefoundry/framework/scripts/run_tests.py`) passes after the change. (Full suite green 2026-07-06: 4665 tests across 43 files.)
- [x] AC-4: A repo-wide grep for `tomli` (backport package) and `tomllib.*None` fallback patterns turns up no remaining hits outside intentionally-excluded scope. (Repo-wide `*.py` sweep 2026-07-06: zero hits.)

## Tasks

- [x] Update `secrets_validators.py` to import `tomllib` directly; delete the `tomli`/`None` fallback, the `_require_tomllib()` guard, and its downstream fatal-diagnostic branch (now dead under ≥3.11).
- [x] Update `render_agent_surfaces.py` to import `tomllib` directly; delete the fallback branch and collapse the always-true `if tomllib is not None:` guards at ~333/424.
- [x] Update the one affected test file (`test_secrets_validators.py`): direct import + drop the dead `if tomllib is None` skip-guards (5 setUp/helper guards + 2 inline per-test fallbacks). Leave the three already-direct test files untouched.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and fix any fallout. (Full suite green: 4665 tests.)
- [x] Grep repo-wide for remaining `tomli`/`tomllib` fallback patterns and fold in any missed call sites. (None found.)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| tomllib-cleanup | implementer | — | Single small, low-risk cleanup; no parallelization needed |

## Serialization Points

- None — single-file-cluster change with no shared-state coordination needed.

## Affected Architecture Docs

N/A — confined to two framework scripts' import statements and their tests; no module boundary, data/control flow, or integration contract changes. ADR `12tm5` already documents the policy this change brings the code into line with; no ADR edit needed.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core fix target named in the rationale |
| AC-2 | required | Core fix target named in the rationale |
| AC-3 | required | Regression safety net |
| AC-4 | important | Catches any additional stale fallback the two named files don't cover |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-04 | Change doc drafted from a Guru investigation into `tomllib` usage | This doc |
| 2026-07-06 | Implemented: `secrets_validators.py` + `render_agent_surfaces.py` direct imports, `_require_tomllib()` + all `is None`/`is not None` guards removed; `test_secrets_validators.py` direct import + 7 dead guards dropped; repo-wide sweep clean. | Affected modules green (145+34+53+155 tests); `py_compile` clean; grep zero hits. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-04 | Track as a tech-debt change rather than fixing inline immediately | Operator asked to "write it up... so we don't forget", not to implement now | Fix inline in the originating conversation (rejected — operator wants it tracked, not applied yet) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Repo-wide grep at implementation time surfaces more fallback sites than expected, growing scope | AC-4 and the final task explicitly budget for a repo-wide sweep; fold genuine hits into this same change rather than opening a new one |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
