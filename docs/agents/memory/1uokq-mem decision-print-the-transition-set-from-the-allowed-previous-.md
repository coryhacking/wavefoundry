# Decision: Print the transition set from the `allowed_previous` variab…

Owner: Engineering
Status: superseded
Last verified: 2026-08-06

Memory ID: `1uokq-mem decision-print-the-transition-set-from-the-allowed-previous-`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-06
Updated: 2026-08-06
Source exploration cost: 48070
Source event: `decision-log:1ul77-enh validation-errors-carry-their-allowed-values:125dbcf2bc3159a6`
Validation: rewrite
Validated by: agent
Action delta: A future validator change prints its allowed set from the constant it checked, and adds a mutation test that varies the constant rather than the fixture.
Validation rationale: The drafted candidate is a faithful restatement of one Decision Log row but is scoped to a single variable at one call site, so it would not change behavior on any future validator. The durable signal from this wave is the general rule plus the falsification method that keeps it honest, both proven here: the mutation replacing the derived list with a hand-written one was killed, and its output showed the hand-written version printing the GLOBAL vocabulary for terminal status `complete` whose reachable set is only `complete`. Rewriting to the generalizable form and naming the shipped helper so the next caller can find it. Verified against the current tree: `allowed_values_suffix` exists in `wave_lint_lib/constants.py` and is applied at the shape, transition, dependency, watchpoint, and memory sites in `wave_validators.py`.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1uol4-mem validation-errors-publish-the-value-set-from-the-constant-th`
## Summary

Decision (wave 1ul78): Print the transition set from the `allowed_previous` variable already in scope. Rationale: At `wave_validators.py:1207` the reachable set is computed immediately before the failure, so the fix is local and cannot drift from the check.

## Evidence

- `1ul77-enh validation-errors-carry-their-allowed-values`
- `1ul78`

## Targets

- `wave_validators.py`
