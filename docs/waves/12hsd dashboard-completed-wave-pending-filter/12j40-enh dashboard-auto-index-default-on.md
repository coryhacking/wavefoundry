# Dashboard: Enable Auto-Index By Default

Change ID: `12j40-enh dashboard-auto-index-default-on`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The dashboard’s index updater is now stable enough that requiring an explicit `dashboard.auto_index: true` opt-in adds unnecessary friction. Operators who start the dashboard generally expect the semantic index to stay current while they work. Making auto-indexing the default brings the shipped behavior in line with that expectation while still allowing repositories to opt out explicitly with `dashboard.auto_index: false`.

## Requirements

1. `read_dashboard_config()` must treat a missing `dashboard.auto_index` setting as `true`.
2. Repositories that explicitly set `dashboard.auto_index: false` must continue to disable background index updates.
3. Current operator-facing docs that show the default dashboard config must reflect the new default.
4. Dashboard verification must cover the new default and the explicit opt-out behavior.

## Scope

**Problem statement:** the dashboard currently requires an explicit opt-in for auto-indexing even though the feature is now part of the expected local dashboard workflow.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_lib.py`
  - Change the default `auto_index` config fallback from `false` to `true`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add/adjust tests for the new default and explicit `false` opt-out
- `docs/references/dashboard-install-upgrade.md`
  - Update sample config and upgrade notes to reflect the new default
- `docs/references/dashboard-adapter-model.md`
  - Add `auto_index` and `auto_index_delay_seconds` to the current config surface reference

**Out of scope:**

- Changing debounce timing defaults
- Changing index trigger semantics beyond the default enablement

## Acceptance Criteria

- AC-1: Missing `dashboard.auto_index` is interpreted as enabled.
- AC-2: Explicit `dashboard.auto_index: false` still disables background index building.
- AC-3: Current operator docs no longer describe the default as opt-in/false.
- AC-4: Dashboard verification passes.

## Tasks

- Flip the config default for `auto_index`
- Add a regression for default-on behavior
- Make the “disabled” test path explicit
- Update current operator docs to match the new default
- Run dashboard verification and docs lint

## Affected Architecture Docs

N/A — default config behavior change only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core requested behavior change |
| AC-2 | required | Preserves explicit operator control |
| AC-3 | important | Prevents docs/config drift |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created to make dashboard auto-indexing default-on while preserving explicit opt-out. | Operator request; `dashboard_lib.py` |
| 2026-05-11 | Flipped the missing-value fallback for `dashboard.auto_index` to `true`, made the disabled dashboard-server test path explicit with `auto_index: false`, and updated current dashboard install/adapter docs to describe the new default and opt-out semantics. | `dashboard_lib.py`; `test_dashboard_server.py`; `docs/references/dashboard-install-upgrade.md`; `docs/references/dashboard-adapter-model.md`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Preserve explicit `false` opt-out while changing only the missing-value fallback | Keeps compatibility for repos that intentionally disabled background indexing | Remove the config flag entirely (rejected: removes operator control) |

## Risks

| Risk | Mitigation |
|------|------------|
| Some repos may see unexpected background indexing after upgrade | Preserve explicit `dashboard.auto_index: false` and document the opt-out clearly |
| Tests may silently rely on the old missing-value behavior | Add explicit coverage for both default-on and explicit-off cases |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
