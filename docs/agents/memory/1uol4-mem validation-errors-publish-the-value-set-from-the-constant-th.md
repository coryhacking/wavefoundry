# Validation errors publish the value set from the constant they checked

Owner: Engineering
Status: active
Last verified: 2026-08-06

Memory ID: `1uol4-mem validation-errors-publish-the-value-set-from-the-constant-th`
Kind: `decision`
Confidence: 0.9
Created: 2026-08-06
Updated: 2026-08-06
Source exploration cost: 48070
Source event: `decision-log:1ul77-enh validation-errors-carry-their-allowed-values:125dbcf2bc3159a6`
Validation: promote
Validated by: agent
Action delta: A future validator change prints its allowed set from the constant it checked, and adds a mutation test that varies the constant rather than the fixture.
Validation rationale: The drafted candidate is a faithful restatement of one Decision Log row but is scoped to a single variable at one call site, so it would not change behavior on any future validator. The durable signal from this wave is the general rule plus the falsification method that keeps it honest, both proven here: the mutation replacing the derived list with a hand-written one was killed, and its output showed the hand-written version printing the GLOBAL vocabulary for terminal status `complete` whose reachable set is only `complete`. Rewriting to the generalizable form and naming the shipped helper so the next caller can find it. Verified against the current tree: `allowed_values_suffix` exists in `wave_lint_lib/constants.py` and is applied at the shape, transition, dependency, watchpoint, and memory sites in `wave_validators.py`.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

When a validator rejects a value drawn from a fixed set, the failure message must state that set, rendered at runtime from the same constant the check used, via `allowed_values_suffix` in `wave_lint_lib/constants.py`. Where validity is relative rather than global, as with status transitions and blocked dependencies, print the subset valid from the current value and name that value; the subset is usually already bound in scope at the check, so no recomputation is needed. Never hand-write the list: a hand-written set drifts silently and reads as authoritative while being wrong. Pin it with a mutation test that varies the CONSTANT and asserts the message follows, patching the importing module rather than the constants module, because `wave_validators` binds these names with `from .constants import (...)` at import time. Publishing a set is guidance, not a gate: adding one must not make any currently-clean document fail.

## Evidence

- `1ul77-enh validation-errors-carry-their-allowed-values`
- `1ul78`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
