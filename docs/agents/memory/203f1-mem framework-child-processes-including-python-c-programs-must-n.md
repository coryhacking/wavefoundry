# Framework child processes, including python -c programs, must not write in-tree bytecode

Owner: Engineering
Status: active
Last verified: 2026-10-07

Memory ID: `203f1-mem framework-child-processes-including-python-c-programs-must-n`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 184122
Source event: `decision-log:1zyv1-enh project-local-bytecode-cache:baa579fab010af8c`
Validation: promote
Validated by: agent
Action delta: Any new framework subprocess launch, including python -c programs, must set sys.dont_write_bytecode before importing a framework module (then bytecode_cache.configure() where importable) or pass -B; test_bytecode_cache's script and -c censuses fail otherwise.
Validation rationale: Wave 200xy widened the no-in-tree-bytecode rule to every process script, but delivery review DEL-1 found python -c children (CoreML probe, graph-builder probe) still writing __pycache__ beside sources because the census covered only scripts; the repair guarded them and added a -c census, independently reverified with guard-removal mutants.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

The bytecode cache contract (wave 200xy, change 1zyv1) is that no framework process writes __pycache__ beside framework sources. Entry scripts set the flag then call bytecode_cache.configure(); python -c children must do the same before their first framework import, or run with -B. Delivery finding DEL-1 showed a script-only census misses -c programs; test_bytecode_cache now censuses both.

## Evidence

- `200xy`
- `DEL-1`
- `1zyv1-enh project-local-bytecode-cache`

## Targets

- `.wavefoundry/framework/scripts/bytecode_cache.py`
- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_bytecode_cache.py`
