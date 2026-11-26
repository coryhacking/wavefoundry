# The RE2-shaped secrets ruleset runs on Python's backtracking re

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249pi-mem the-re2-shaped-secrets-ruleset-runs-on-python-s-backtracking`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1x3m2-mem the-secrets-ruleset-is-re2-shaped-but-runs-on-a-backtracking`

## Summary

When you refresh .wavefoundry/framework/scan-rules.toml or change how secrets_validators compiles its patterns, remember that the Gitleaks rules are written for Go's linear-time RE2 but run on Python's backtracking re. A pattern that is safe upstream can be super-linear here. In wave 1x4ol, eleven rules opening with nested lazy spans ([\w.-]{0,50}?(?i:[\w.-]{0,50}?) cost 173.6 s of a 198.5 s scan on one 1.15 MB artifact. Keep the fix in the load-time shim secrets_validators.collapse_redundant_prefix, never in the ruleset data, so an upstream refresh cannot lose it. Judge any engine rewrite by identical match sets, spans and groups against a baseline frozen before the edit (tests/fixtures/secrets_prefix_collapse_baseline.json). A mutant that narrows the language must fail that comparison. The collapse removes a constant factor, not the exponent, so do not claim a flatter growth curve. After a refresh, re-run test_secrets_prefix_collapse.py and read the 'secrets scan cost' lines.

## Evidence

- `1x4ol`
- `1x4ok-enh secrets-scan-cost-bounds`
- `secrets_validators.collapse_redundant_prefix`
- `test_secrets_prefix_collapse.CollapsePreservesTheLanguageTests`
- `test_secrets_prefix_collapse.CollapseRemovesTheSuperLinearCostTests`
- `.wavefoundry/framework/scripts/tests/fixtures/secrets_prefix_collapse_baseline.json`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
- `.wavefoundry/framework/scan-rules.toml`
- `.wavefoundry/framework/scripts/scan_secrets.py`
