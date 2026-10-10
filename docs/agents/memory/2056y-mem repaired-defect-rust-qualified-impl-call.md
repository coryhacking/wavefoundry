# Repaired defect rust-qualified-impl-call

Owner: Engineering
Status: rejected
Last verified: 2026-10-08

Memory ID: `2056y-mem repaired-defect-rust-qualified-impl-call`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 681705
Source event: `finding:206og:rust-qualified-impl-call`
Validation: reject
Validated by: agent
Action delta: Use the canonical Rust qualified-call contract and named regression tests instead of a generic memory attached to a temporary probe.
Validation rationale: Generated target tmp/wf-206og-qualified-probe.py is not a repository file, preventing truthful rewrite validation. The normalized receiver-alias contract and ambiguity controls are documented and tested; this draft adds no reusable current target.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates

## Summary

Real defect fixed in wave 206og: Original issue remains classified real; explicit module identity and conservative ambiguity contract independently reverified.

## Evidence

- `rust-qualified-impl-call`
- `ev-rust-qualified-impl-call-4`
- `206og`

## Targets

- `tmp/wf-206og-qualified-probe.py`
