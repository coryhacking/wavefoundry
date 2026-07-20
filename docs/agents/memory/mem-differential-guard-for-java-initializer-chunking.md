# Differential guard for Java initializer chunking

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-differential-guard-for-java-initializer-chunking`
Kind: `successful_pattern`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1sbfl-bug java-chunker-static-initializer-bodies:c265ef8445f42fd3`
Validation: promote
Validated by: agent
Action delta: Before changing Java initializer chunking, run the bounded generated differential suite and the named lexical edge regressions against tree-sitter and the spec-derived expected owner.
Validation rationale: The wave required repeated repairs for correlated fallback-lexer assumptions; the current target and named regressions preserve the independent reference and exact-identity boundaries.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When editing Java initializer chunking, verify fallback and tree-sitter output against an independently expected owner and line span, including comments as separators, class literals, long and Unicode identifiers, nesting, and escaped text-block delimiters.

## Evidence

- `1shv4`
- `1sbfl-bug java-chunker-static-initializer-bodies`
- `test_generated_java_owner_and_init_identity_parity`
- `test_fallback_escaped_text_block_delimiter_does_not_truncate`

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
