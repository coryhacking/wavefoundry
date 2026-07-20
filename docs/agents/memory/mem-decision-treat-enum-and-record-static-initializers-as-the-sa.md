# Decision: Treat enum and record static initializers as the same Java-…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-treat-enum-and-record-static-initializers-as-the-sa`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1sbfl-bug java-chunker-static-initializer-bodies:c265ef8445f42fd3`
Validation: rewrite
Validated by: agent
Action delta: Before changing Java initializer chunking, run the bounded generated differential suite and the named lexical edge regressions against tree-sitter and the spec-derived expected owner.
Validation rationale: The wave required repeated repairs for correlated fallback-lexer assumptions; the current target and named regressions preserve the independent reference and exact-identity boundaries.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-differential-guard-for-java-initializer-chunking`
## Summary

Decision (wave 1shv4): Treat enum and record static initializers as the same Java-container coverage contract, while excluding record instance initializers as illegal Java.. Rationale: The regex recognizer already names enum/record declarations and record static initializers are legal; allowing generic record line windows or class-only fixtures would contradict the promised first-class identity. **Corrected at readiness (2026-07-15):** the tree-sitter path does NOT have distinct enum/record body handling — it bundles `class_body`/`interface_body`/`enum_body` in one branch (`chunker.py:4157`) and does not recognize records at all, so `record_declaration` recognition + a `record_body` traversal are net-new work, not an existing branch to hook..

## Evidence

- `1sbfl-bug java-chunker-static-initializer-bodies`
- `1shv4`

## Targets

- `chunker.py`
