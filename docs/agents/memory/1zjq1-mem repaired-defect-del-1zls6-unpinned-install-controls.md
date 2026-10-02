# Repaired defect DEL-1ZLS6-UNPINNED-INSTALL-CONTROLS

Owner: Engineering
Status: superseded
Last verified: 2026-10-02

Memory ID: `1zjq1-mem repaired-defect-del-1zls6-unpinned-install-controls`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-02
Updated: 2026-10-02
Source exploration cost: 73697
Source event: `finding:1zls6:DEL-1ZLS6-UNPINNED-INSTALL-CONTROLS`
Validation: rewrite
Validated by: agent
Action delta: When changing setup_index._install_deps, keep test_install_deps_invokes_pip_via_venv_python asserting --exclude-newer and the uv install env, and keep source guards scoped to the function they protect (AST), not the whole file.
Validation rationale: Delivery review found the setup install's age guard and uv TLS env unpinned, and a file-wide substring guard satisfied by the startup installer's identical line; the generated summary had no actionable content.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1zliu-mem setup-install-controls-need-function-scoped-pins`

## Summary

Real defect fixed in wave 1zls6: Repair verified.

## Evidence

- `DEL-1ZLS6-UNPINNED-INSTALL-CONTROLS`
- `ev-del-1zls6-unpinned-install-controls-3`
- `1zls6`

## Targets

- `tests/test_setup_index.py`
- `tests/test_server_tools.py`
