# Update Indexes Bin Wrapper

Change ID: `0rlgv-feat update-indexes-bin-wrapper`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

Operators need a direct local command for the normal post-edit index refresh flow. The framework already exposes the behavior through `upgrade_wavefoundry.py --update-index`, but there is no dedicated bin wrapper in `.wavefoundry/bin/` alongside the other standard launchers.

## Requirements

1. `render_platform_surfaces.py` must generate a `.wavefoundry/bin/update-indexes` launcher.
2. The launcher must resolve the repo root from its own location and invoke `upgrade_wavefoundry.py --update-index --yes`.
3. The launcher must be executable and idempotent across repeated renders.
4. The renderer must keep removing stale wrapper files only when they are truly obsolete, not as a side effect of this addition.

## Scope

**Problem statement:** The repository has a standard rendered bin launcher set, but index refresh still requires calling the longer framework script path directly.

**In scope:**

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/bin/update-indexes`

**Out of scope:**

- Any change to indexer behavior or index update semantics
- Any change to `upgrade_wavefoundry.py` phase logic
- Any docs/prompt surface changes beyond the generated launcher itself

## Acceptance Criteria

- [x] AC-1: `render_platform_surfaces.py` writes `.wavefoundry/bin/update-indexes` as an executable launcher.
- [x] AC-2: The launcher invokes `upgrade_wavefoundry.py --update-index --yes` from the repo root.
- [x] AC-3: Regression tests cover launcher generation and keep the wrapper in the standard bin set.
- [x] AC-4: `render_platform_surfaces.py` remains idempotent after the new launcher is added.

## Tasks

- [x] Update `render_platform_surfaces.py` bin launcher rendering
- [x] Add regression coverage in `test_render_platform_surfaces.py`
- [x] Render the checked-in `.wavefoundry/bin/update-indexes` wrapper
- [x] Verify the generated wrapper contents and executable bit

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| Renderer update | implementer | — | Add the launcher to the canonical generator |
| Regression coverage | implementer | renderer update | Confirm the launcher is emitted and stable |
| Rendered artifact refresh | implementer | renderer update | Regenerate `.wavefoundry/bin/update-indexes` |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`

## Affected Architecture Docs

N/A. This is a narrow framework-surface addition with no boundary, flow, or verification-architecture change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The launcher must be generated automatically |
| AC-2 | required | The command needs the right index-update semantics |
| AC-3 | required | Prevents future regressions in the launcher set |
| AC-4 | required | Keeps renders deterministic |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-26 | Change doc created and admitted to wave | `wave_new_feature` / `wave_add_change` |
| 2026-05-26 | Renderer, wrapper, and regression coverage implemented and verified | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_render_platform_surfaces.py'`; `python3 -B -m py_compile .wavefoundry/framework/scripts/render_platform_surfaces.py .wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`; `wave_validate` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-26 | Model the launcher as a feature change | It adds a new standard operator entrypoint | Treat as docs-only or generic maintenance |

## Risks

| Risk | Mitigation |
|---|---|
| Wrapper name drifts from the command it invokes | Keep the launcher content and test assertions tied to `upgrade_wavefoundry.py --update-index --yes` |
| Future render passes omit the new file | Add explicit regression coverage in `test_render_platform_surfaces.py` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
