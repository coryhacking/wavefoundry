# Setup install controls need function-scoped pins

Owner: Engineering
Status: active
Last verified: 2026-10-02

Memory ID: `1zliu-mem setup-install-controls-need-function-scoped-pins`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-10-02
Updated: 2026-10-02
Source exploration cost: 73697
Source event: `finding:1zls6:DEL-1ZLS6-UNPINNED-INSTALL-CONTROLS`
Validation: promote
Validated by: agent
Action delta: When changing setup_index._install_deps, keep test_install_deps_invokes_pip_via_venv_python asserting --exclude-newer and the uv install env, and keep source guards scoped to the function they protect (AST), not the whole file.
Validation rationale: Delivery review found the setup install's age guard and uv TLS env unpinned, and a file-wide substring guard satisfied by the startup installer's identical line; the generated summary had no actionable content.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1zls6: dropping --exclude-newer or swapping the uv TLS env in setup_index._install_deps passed every test, and a subprocess-isolation guard asserted a substring anywhere in setup_index.py that install_requirement_specs also carries. test_install_deps_invokes_pip_via_venv_python now pins both arguments and the guard extracts _install_deps via AST. Source guards must be scoped to the function they protect.

## Evidence

- `DEL-1ZLS6-UNPINNED-INSTALL-CONTROLS`
- `1zls6`

## Targets

- `setup_index.py`
- `tests/test_setup_index.py`
- `tests/test_server_tools.py`
