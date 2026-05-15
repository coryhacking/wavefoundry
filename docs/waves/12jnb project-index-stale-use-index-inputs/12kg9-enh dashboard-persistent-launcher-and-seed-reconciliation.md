# Dashboard Persistent Launcher and Seed Reconciliation

Change ID: `12kg9-enh dashboard-persistent-launcher-and-seed-reconciliation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard shortcut is currently rendered as a one-shot browser opener, which means the repo does not automatically seed the persistent launcher contract operators now expect. This change makes the persistent-process launcher part of the framework source so future installs and upgrades generate the shortcut automatically and the public prompt surface points at the launcher rather than the low-level script path.

## Requirements

1. The framework renderer should generate `.wavefoundry/bin/wave_dashboard` as an executable launcher.
2. The launcher should run `dashboard_server.py` through `nohup`, write logs to `.wavefoundry/logs/dashboard.log`, and keep the browser-opening `--open` behavior baked in.
3. The launcher should resolve `REPO_ROOT` from its own location and pass through caller-supplied arguments after the fixed flags.
4. The public `Start dashboard` prompt should use the launcher as the operator-facing command and retain the low-level no-browser fallback for direct script invocation.
5. Seed prompts that govern install/upgrade should require the launcher in the generated bin wrapper set so future render passes keep it present.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/seeds/152-start-dashboard.prompt.md`
- `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/bin/wave_dashboard`
- `docs/prompts/start-dashboard.prompt.md`

**Out of scope:**

- Changing dashboard server behavior
- Changing wave semantics or dashboard data sources
- Introducing new dashboard state files

## Acceptance Criteria

- `render_platform_surfaces.py` writes `.wavefoundry/bin/wave_dashboard` with the persistent-process contract.
- `Start dashboard` in the public prompt surface uses `.wavefoundry/bin/wave_dashboard` by default, and the low-level fallback remains documented.
- Install and upgrade seed prompts explicitly require the dashboard bin launcher in generated wrappers and reconciliation checks.
- The launcher is executable and preserves the browser-open-by-default behavior with log output and a stable startup message.

## Tasks

- Update dashboard launcher rendering in the framework renderer
- Update the dashboard seed and rendered prompt docs
- Add regression coverage for launcher generation
- Refresh the checked-in launcher to match the rendered contract

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The launcher must be generated automatically in future renders |
| AC-2 | required | Operators need a stable command that survives shell exit |
| AC-3 | required | Seed prompts must keep future installs and upgrades in sync |
| AC-4 | required | The prompt surface must still expose the low-level fallback |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Launcher writes logs to an unexpected location | Resolve the log path from `REPO_ROOT` and create the directory explicitly |
| `nohup` changes browser-open timing | Keep `--open` on the server invocation and preserve the startup message |
| Future renders drift from the checked-in launcher | Add regression coverage around `render_bin_launchers` output |
