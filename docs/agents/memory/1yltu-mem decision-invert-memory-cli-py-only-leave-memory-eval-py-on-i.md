# Decision: Invert `memory_cli.py` only; leave `memory_eval.py` on its…

Owner: Engineering
Status: rejected
Last verified: 2026-09-22

Memory ID: `1yltu-mem decision-invert-memory-cli-py-only-leave-memory-eval-py-on-i`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-21
Updated: 2026-09-21
Source exploration cost: 394325
Source event: `decision-log:1ymzj-ref memory-handler-module:a67970ce217abf25`
Validation: reject
Validated by: agent
Action delta: No additional memory action: consult the canonical handler boundary and explicit follow-up decision before changing evaluator dependencies.
Validation rationale: Verified Decision Log and current memory_cli imports/calls; memory_eval still uses srv._memory_mod, srv._memory_ranked and srv._load_script. docs/architecture/domain-map.md explicitly records direct CLI ownership and retained evaluator handle. This is a delivered boundary and scoped deferral already documented canonically, not a new reusable lesson. High confidence; no contradiction with current source.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1ymzk): Invert `memory_cli.py` only; leave `memory_eval.py` on its single `server_impl` handle.. Rationale: Two of its five attributes do not move and one is test-patched on `server_impl`; splitting the handle threads two parameters through four helpers for no behavior gain..

## Evidence

- `1ymzj-ref memory-handler-module`
- `1ymzk`

## Targets

- `memory_cli.py`
- `memory_eval.py`
