# Decision: Narrow the `publication_control.py` non-goal to the guard P…

Owner: Engineering
Status: active
Last verified: 2026-08-01

Memory ID: `1u494-mem decision-narrow-the-publication-control-py-non-goal-to-the-g`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-01
Updated: 2026-08-01
Source exploration cost: 539855
Source event: `decision-log:1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success:5e15b32bea60aede`
Validation: promote
Validated by: agent
Action delta: When changing index-publication refusal text, edit only the message tail composed in publication_control (now _checkpoint_recovery_tail); the predicate at :100-110 is the seed-160:511 documented invariant and stays byte-identical, and both refusal surfaces (MCP diagnostic strip, child raise) read the one composed string.
Validation rationale: Accurate and durable: the single-composition-point rule prevented surface divergence in the delivered fix (byte-parity asserted by tests on both surfaces), and the predicate byte-identity was diff-verified at delivery review. The target file contains both the predicate and the composition point. Future refusal-wording changes need exactly this record.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
## Summary

Decision (wave 1u44n): Narrow the `publication_control.py` non-goal to the guard PREDICATE only. Rationale: The predicate (`:100-110`) is the documented seed-160:511 invariant and stays byte-identical; the message tail (`:111-114`) is the single composition point both refusal surfaces read, so enriching it there is the only way the MCP diagnostic and the child raise cannot diverge.

## Evidence

- `1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`
- `1u44n`

## Targets

- `publication_control.py`
