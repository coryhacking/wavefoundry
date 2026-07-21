# A source pin that rejects one producer shape is not a pin

Owner: Engineering
Status: active
Last verified: 2026-07-21

Memory ID: `mem-repaired-defect-fallback-reason-census-still-incomplete`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-21
Updated: 2026-07-21
Source exploration cost: 104280
Source event: `finding:1seax:fallback-reason-census-still-incomplete`
Validation: promote
Validated by: agent
Action delta: When pinning a vocabulary contract in source, never pin one syntactic producer shape; assert zero quoted occurrences of every canonical value in the emitting module, iterate the contract tuple itself so tuple growth is auto-covered, and prove the pin with an executed mutation probe.
Validation rationale: The drafted summary only echoed the reverification verdict; the durable lesson is the pin-shape failure (assignment-only pin missed call arguments, comparisons, and dict values, letting two emitted values stay out of the tuple) and the indirection-proof zero-occurrence repair. Body rewritten in place before validation; supplements the canonical-constants memory.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
## Summary

Wave 1seax, second-round operator finding after the vocabulary-alias repair: the first pin only rejected direct `fallback_reason = "..."` assignments, so it missed every other producer shape — call arguments, comparisons, failure_reason dict values — and two emitted values (`model_unavailable`, `index_missing`) stayed out of the canonical tuple entirely. A pin scoped to one syntactic shape verifies the shape, not the contract. Repair pattern: enforce ZERO quoted occurrences of any canonical value in the emitting module, iterating the contract tuple itself (so a later-grown tuple is automatically covered), and demonstrate the pin by an executed mutation probe (plant a quoted literal, watch the pin fail, restore). Supplements [[mem-a-canonical-constants-module-is-not-single-source-until-emit]]: consuming aliases at the sites you found is necessary; the indirection-proof pin is what makes the census stay complete.

## Evidence

- `fallback-reason-census-still-incomplete`
- `ev-fallback-reason-census-still-incomplete-3`
- `1seax`

## Targets

- `tests/test_docs_constants_lint.py`
