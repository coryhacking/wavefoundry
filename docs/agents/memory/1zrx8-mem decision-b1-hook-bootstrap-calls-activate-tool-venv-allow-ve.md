# Decision: B1: `HOOK_BOOTSTRAP` calls `activate_tool_venv(allow_versio…

Owner: Engineering
Status: superseded
Last verified: 2026-10-04

Memory ID: `1zrx8-mem decision-b1-hook-bootstrap-calls-activate-tool-venv-allow-ve`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 470529
Source event: `decision-log:1zrag-bug setup-repairs-python-upgrade-and-stuck-migration:bf95dd3990983a9a`
Validation: rewrite
Validated by: agent
Action delta: When a hook or setup path must survive a Python minor upgrade, activate with allow_version_mismatch=True and rely on the sticky deferral, never catch SystemExit around plain activation.
Validation rationale: Generated candidate targeted indexer.py, but the decision lives in render_platform_surfaces HOOK_BOOTSTRAP and venv_bootstrap's deferral; verified in the current tree and the 13 regenerated hooks.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1zrq6-mem hooks-and-setup-survive-a-python-minor-upgrade-through-the-v`

## Summary

Decision (wave 1zqe4): B1: `HOOK_BOOTSTRAP` calls `activate_tool_venv(allow_version_mismatch=True)` and then reads the deferral accessor. Under a deferral the in-process `indexer.py` loads keep running; when activation raised (no deferral) they are skipped; self-activating children are always skipped while degraded.. Rationale: The sticky deferral makes the later plain calls in `indexer.py` and `sqlite_runtime` return. Loading `indexer.py` on the system interpreter was executed and succeeds. A raised activation records no deferral, so a reload would raise again past `except Exception`..

## Evidence

- `1zrag-bug setup-repairs-python-upgrade-and-stuck-migration`
- `1zqe4`

## Targets

- `indexer.py`
