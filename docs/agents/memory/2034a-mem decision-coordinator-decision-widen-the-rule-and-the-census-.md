# Decision: Coordinator decision: widen the rule and the census predica…

Owner: Engineering
Status: superseded
Last verified: 2026-10-07

Memory ID: `2034a-mem decision-coordinator-decision-widen-the-rule-and-the-census-`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 184122
Source event: `decision-log:1zyv1-enh project-local-bytecode-cache:baa579fab010af8c`
Validation: rewrite
Validated by: agent
Action delta: Any new framework subprocess launch, including python -c programs, must set sys.dont_write_bytecode before importing a framework module (then bytecode_cache.configure() where importable) or pass -B; test_bytecode_cache's script and -c censuses fail otherwise.
Validation rationale: Wave 200xy widened the no-in-tree-bytecode rule to every process script, but delivery review DEL-1 found python -c children (CoreML probe, graph-builder probe) still writing __pycache__ beside sources because the census covered only scripts; the repair guarded them and added a -c census, independently reverified with guard-removal mutants.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `203f1-mem framework-child-processes-including-python-c-programs-must-n`

## Summary

Decision (wave 200xy): Coordinator decision: widen the rule and the census predicate to every script run as a process.. Rationale: The operator wants no in-tree bytecode anywhere; 28 process scripts (among them `dashboard_server.py`, spawned without `-B`) set no flag today and would write beside their sources..

## Evidence

- `1zyv1-enh project-local-bytecode-cache`
- `200xy`

## Targets

- `dashboard_server.py`
