# Factor 12 — Admin Processes Review Agent

## What This Factor Covers

CLI tools, one-off operational commands, and management scripts run alongside the main process.

## Why This Factor Is Applicable to Wavefoundry

Wavefoundry's primary interface for maintainers and operators is a set of CLI admin scripts: `lifecycle_id.py`, `docs_lint.py`, `docs_gardener.py`, `build_pack.py`, `render_platform_surfaces.py`, `run_tests.py`. These are the admin process surface and must behave predictably and safely.

Evidence: `framework/scripts/` contents; AGENTS.md; `docs/contributing/build-and-verification.md`.

## Review Questions

When evaluating a wave touching framework scripts:

1. Does the script use `sys.exit(0)` on success and non-zero on failure with an actionable error message?
2. Does the script validate required arguments before doing any work?
3. Are destructive operations (file writes, VERSION stamp) safe to re-run (idempotent or with explicit overwrite confirmation)?
4. Is the script tested in `framework/scripts/tests/`? Are edge cases covered?
5. Does the help text (`--help`) accurately describe the script's behavior?
6. Is the script invocable from the repo root with `python3 .wavefoundry/framework/scripts/<script>.py`?
7. Are relative paths computed from `__file__` or an explicit project-root argument rather than `os.getcwd()`?

## Findings

Advisory for Wavefoundry. Record in wave `## Review checkpoints`.
