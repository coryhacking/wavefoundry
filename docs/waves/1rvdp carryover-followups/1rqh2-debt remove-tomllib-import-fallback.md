# Remove stale tomllib import fallbacks

Change ID: `1rqh2-debt remove-tomllib-import-fallback`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-04
Wave: TBD

## Rationale

`docs/architecture/decisions/12tm5-adr python-tool-environment.md` requires Python >= 3.11 specifically so that `tomllib` (stdlib since 3.11) is always available, and states new code "must not use `tomllib` import fallbacks." Two production call sites still carry a `tomllib` -> `tomli` -> `None` fallback chain that predates or was never reconciled with that ADR ruling. The fallback is dead weight: it can never take the `tomli`/`None` branch under the ADR's own minimum-version guarantee, and it invites new code to copy the same now-unnecessary pattern.

## Requirements

1. `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` imports `tomllib` directly (no `tomli`/`None` fallback), consistent with ADR `12tm5`.
2. `.wavefoundry/framework/scripts/render_agent_surfaces.py` imports `tomllib` directly (no `tomli`/`None` fallback) at its `.codex/config.toml` merge-validation call site.
3. Any now-dead fallback branches (`_require_tomllib()` guard, `tomli` import attempts, `None`-check paths) are removed rather than left unreachable.
4. Test files that mirror the same fallback pattern (`test_setup_index.py`, `test_render_agent_surfaces.py`, `test_render_platform_surfaces.py`, `test_secrets_validators.py`) are updated to import `tomllib` directly for consistency, unless a test is intentionally exercising Python-version compatibility (call out explicitly if so).

## Scope

**Problem statement:** Two production modules and several tests still use a `tomllib`/`tomli`/`None` import fallback chain that ADR `12tm5` says new code must not use, since Python >= 3.11 already guarantees `tomllib`.

**In scope:**

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` (lines ~12-46, plus later merged-ruleset call sites ~1374/1386)
- `.wavefoundry/framework/scripts/render_agent_surfaces.py` (lines ~338-343)
- Matching test-side fallback imports in `test_setup_index.py`, `test_render_agent_surfaces.py`, `test_render_platform_surfaces.py`, `test_secrets_validators.py`

**Out of scope:**

- Any change to the ADR itself or the Python minimum-version policy
- Any change to TOML file formats, schemas, or the secrets-scan ruleset content
- Broader search for other `tomllib`/`tomli` fallback patterns outside the files named above (do a repo-wide grep at implementation time and fold in any additional hits found, but this doc does not pre-enumerate them)

## Acceptance Criteria

- [ ] AC-1: `secrets_validators.py` imports `tomllib` directly; no `tomli` import attempt or `None`-fallback branch remains reachable.
- [ ] AC-2: `render_agent_surfaces.py` imports `tomllib` directly at its `.codex/config.toml` validation call site; no fallback branch remains.
- [ ] AC-3: Framework test suite (`python3 .wavefoundry/framework/scripts/run_tests.py`) passes after the change.
- [ ] AC-4: A repo-wide grep for `tomli` (backport package) and `tomllib.*None` fallback patterns turns up no remaining hits outside intentionally-excluded scope.

## Tasks

- [ ] Update `secrets_validators.py` to import `tomllib` directly; delete the `tomli`/`None` fallback and the now-dead `_require_tomllib()` guard paths.
- [ ] Update `render_agent_surfaces.py` to import `tomllib` directly; delete the fallback branch.
- [ ] Update the four affected test files to match.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and fix any fallout.
- [ ] Grep repo-wide for remaining `tomli`/`tomllib` fallback patterns and fold in any missed call sites.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| tomllib-cleanup | implementer | — | Single small, low-risk cleanup; no parallelization needed |

## Serialization Points

- None — single-file-cluster change with no shared-state coordination needed.

## Affected Architecture Docs

N/A — confined to two framework scripts' import statements and their tests; no module boundary, data/control flow, or integration contract changes. ADR `12tm5` already documents the policy this change brings the code into line with; no ADR edit needed.

## AC Priority

(Populated at Prepare wave.)

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
