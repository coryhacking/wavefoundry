# Close requires explicit disposition for evidence-derived memory

Owner: Engineering
Status: active
Last verified: 2026-07-19

Memory ID: `mem-close-requires-explicit-disposition-for-evidence-derived-mem`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-19
Updated: 2026-07-19
Source event: `finding:1sxj7:memory-close-one-shot-silent`
Validation: promote
Validated by: agent
Action delta: Before closing a wave, require every evidence-derived memory source to have a candidate and an explicit validation disposition; zero-memory is valid only after drafting finds no material source.
Validation rationale: The independent public close probe reproduced the missing-candidate and pending-candidate gates, then showed an explicit rejection clears the diagnostic. This is a durable lifecycle invariant, while the original generated summary was too generic.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Before closing a wave, run memory proposal and give every drafted candidate an explicit promote, retain, reject, or rewrite disposition. Treat zero-memory as valid only when drafting itself finds no material source; never interpret a failed or skipped proposal pass as an empty successful result.

## Evidence

- `1sxj7`
- `memory-close-one-shot-silent`
- `ev-memory-close-one-shot-silent-4`
- `MemoryAgentValidationTests.test_close_diagnostics_require_candidate_and_verdict_but_allow_zero_memory`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
