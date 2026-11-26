# Patch the impl module, not the runner

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249ga-mem patch-the-impl-module-not-the-runner`
Kind: `environment_gotcha`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `1t78a-mem patch-the-impl-module-not-the-runner`
Checked at: 2026-11-26T06:32:42Z
Check note: server.py remains a runner shim. When testing implementation calls, patch the module that actually owns the binding. Reviewed .wavefoundry/framework/scripts/wf_server/server_impl.py:21337.
Check flags: none

## Summary

When a test needs to replace a function that wf_server/server_impl.py calls internally, patch it on the server_impl module (for example patch.object(srv, name) where srv is server_impl), not on the thin runner .wavefoundry/framework/scripts/server.py. server.py only re-exports server_impl names through a module __getattr__, so patch.object(server, name) creates an attribute server_impl never looks up and the test silently exercises the real function. Late binding lets a function defined early in server_impl reach later definitions without patching its own module.

## Evidence

- `12rbc`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`

## Targets

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
