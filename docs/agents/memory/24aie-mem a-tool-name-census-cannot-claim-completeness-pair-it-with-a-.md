# A tool-name census cannot claim completeness; pair it with a membership invariant and document what it cannot see

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24aie-mem a-tool-name-census-cannot-claim-completeness-pair-it-with-a-`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 60274
Supersedes: `1yyok-mem repaired-defect-del-census-coverage`

## Summary

When you write a census test over collections of MCP tool names, or prose that describes one, do not claim it 'keeps the list complete'. A census that matches only literals naming current tools misses collections that hold only unserved names, collections derived from classified ones (unions, comprehensions, attribute references) and sets local to a function. Pair it with a membership invariant (every reserved name is a served core tool, and retired names are not served), and widen it to references to classified collections. In the prose, state its exact predicate and name the residual gap with a surviving mutant. Verify every sentence about lint flow against wave_lint_lib/cli.py: the 1yyoj repair itself added a false ADR sentence about when the warning runs. A core-prefix regex census was measured and rejected (24 false positives) (DEL-CENSUS-COVERAGE, wave 1yyoj).

## Evidence

- `DEL-CENSUS-COVERAGE`
- `ev-del-census-coverage-3`
- `1yyoj`
- `test_extension_tool_modules.test_reserved_collections_hold_only_served_or_retired_names`

## Targets

- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
