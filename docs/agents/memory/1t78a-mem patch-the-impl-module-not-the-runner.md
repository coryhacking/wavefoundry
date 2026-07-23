# patch-the-impl-module-not-the-runner

Owner: Engineering
Status: active
Last verified: 2026-07-22

Memory ID: `1t78a-mem patch-the-impl-module-not-the-runner`
Kind: `environment_gotcha`
Confidence: 0.8
Created: 2026-07-22
Updated: 2026-07-22
## Summary

patch.object on the thin runner module (server.py) does not reach functions the impl module (server_impl.py) resolves internally; tests must patch the module that owns the lookup, and a function defined early in a module can reference later definitions via late binding without monkey-patching its own module.

## Evidence

- `12rbc`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/server_impl.py`

## Targets

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/server_impl.py`
