# Repaired defect DEL-CENSUS-COVERAGE

Owner: Engineering
Status: active
Last verified: 2026-09-24

Memory ID: `1yyok-mem repaired-defect-del-census-coverage`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-24
Updated: 2026-09-24
Source exploration cost: 60274
Source event: `finding:1yyoj:DEL-CENSUS-COVERAGE`
Validation: promote
Validated by: agent
Action delta: When a test or doc claims a census is complete, state the census predicate exactly, pair it with a membership invariant over the classified sets, and prove the residual gap with a surviving mutant instead of claiming completeness.
Validation rationale: Red-team and docs-contract lanes independently disproved a completeness claim with scratch mutants; the repair and its limits were verified by four lanes and the council.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

A census test that only matches collections whose literals name CURRENT tools cannot claim to "keep the list complete": it misses collections holding only unserved names, collections derived from classified ones (unions, comprehensions, attribute references) and function-local sets. In wave 1yyoj the docs claimed completeness and a red-team mutant disproved it. The repair pairs the census with a membership invariant (every name in a reserved collection is a served core tool; retired names are not served), widens the census to references to classified collections, and documents the residual gap with a surviving mutant. A core-prefix regex census was measured and rejected (24 false positives). When writing docs for a census, state its exact predicate and name what it cannot see; verify every sentence about lint flow against cli.py (the repair itself added a false ADR sentence about when the warning runs).

## Evidence

- `DEL-CENSUS-COVERAGE`
- `ev-del-census-coverage-3`
- `1yyoj`

## Targets

- `tests/test_extension_tool_modules.py`
- `wave_lint_lib/cli.py`
- `server_impl.py`
