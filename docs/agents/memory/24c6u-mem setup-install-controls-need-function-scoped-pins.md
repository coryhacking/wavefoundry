# Setup install controls need function-scoped pins

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24c6u-mem setup-install-controls-need-function-scoped-pins`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 73697
Supersedes: `1zliu-mem setup-install-controls-need-function-scoped-pins`

## Summary

When changing setup_index._install_deps in .wavefoundry/framework/scripts/setup_index.py, keep tests/test_setup_index.py SetupIndexTests.test_install_deps_invokes_pip_via_venv_python asserting --exclude-newer and the uv install env, and scope any source guard to the function it protects by AST, not a substring anywhere in the file. Why: wave 1zls6 found dropping --exclude-newer or swapping the uv TLS env passed every test, and a file-wide substring guard was satisfied by the identical line in install_requirement_specs (DEL-1ZLS6-UNPINNED-INSTALL-CONTROLS); tests/test_server_tools.py FrameworkWideSubprocessIsolationGuard now extracts _install_deps via AST.

## Evidence

- `DEL-1ZLS6-UNPINNED-INSTALL-CONTROLS`
- `1zls6`
- `test_setup_index.SetupIndexTests.test_install_deps_invokes_pip_via_venv_python`

## Targets

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
