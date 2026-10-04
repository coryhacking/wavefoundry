# Hooks and setup survive a Python minor upgrade through the venv activation deferral

Owner: Engineering
Status: active
Last verified: 2026-10-04

Memory ID: `1zrq6-mem hooks-and-setup-survive-a-python-minor-upgrade-through-the-v`
Kind: `decision`
Confidence: 0.9
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 470529
Source event: `decision-log:1zrag-bug setup-repairs-python-upgrade-and-stuck-migration:bf95dd3990983a9a`
Validation: promote
Validated by: agent
Action delta: When a hook or setup path must survive a Python minor upgrade, activate with allow_version_mismatch=True and rely on the sticky deferral, never catch SystemExit around plain activation.
Validation rationale: Generated candidate targeted indexer.py, but the decision lives in render_platform_surfaces HOOK_BOOTSTRAP and venv_bootstrap's deferral; verified in the current tree and the 13 regenerated hooks.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Decision (wave 1zqe4, 1zrag): 12 framework modules call venv_bootstrap.activate_tool_venv() at import, which exits 2 on a venv built for another Python minor. setup_wavefoundry.main and the rendered HOOK_BOOTSTRAP call activate_tool_venv(allow_version_mismatch=True), which records a process-local deferral (read via activation_deferred(), cleared via reset_activation_deferral() in tests) so later plain calls, such as indexer.py and sqlite_runtime at import, return instead of exiting. Hooks degrade (one stderr notice, exit 0, skip self-activating children) while gate hooks keep their stdlib verdict. The deferral never reaches the MCP server process. Regenerate hooks with wf_sync_surfaces, never by hand.

## Evidence

- `1zrag-bug setup-repairs-python-upgrade-and-stuck-migration`
- `1zqe4`

## Targets

- `.wavefoundry/framework/scripts/venv_bootstrap.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/setup_reconciliation.py`
