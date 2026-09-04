# The secrets ruleset is RE2-shaped but runs on a backtracking engine; judge any rewrite differentially

Owner: Engineering
Status: active
Last verified: 2026-09-04

Memory ID: `1x3m2-mem the-secrets-ruleset-is-re2-shaped-but-runs-on-a-backtracking`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-09-04
Updated: 2026-09-04

## Summary

`scan-rules.toml` is Gitleaks schema written for Go's RE2, which guarantees linear time; the scanner runs it on Python's `re`, which backtracks. A pattern that is safe upstream can be super-linear here. Wave `1x4ol` found eleven rules opening with two nested bounded lazy spans over one class (`[\w.-]{0,50}?(?i:[\w.-]{0,50}?`), ~2,600 split points per start position, and one 1.15 MB identifier-dense evidence artifact cost 173.6 s of a 198.5 s full scan; 120 more rules carry a single-span `(?i)[\w.-]{0,50}?` head the collapse does not reach. The fix lives in the load-time shim (`secrets_validators.collapse_redundant_prefix`), never in the ruleset data, so an upstream refresh cannot lose it. Two operating rules follow: (1) an engine rewrite is judged by IDENTICAL match sets, spans and captured groups against a baseline frozen BEFORE the edit (seeded random corpus, hand-authored positives validated on the unmodified engine, and every real-repository match), and a mutant that narrows the language must fail that differential; (2) measure the growth curve honestly -- the collapse removes a constant factor, not the exponent (both forms grow ~x3.1 per doubling), so do not assert a flatter curve. After a ruleset refresh, re-run `test_secrets_prefix_collapse.py` and read the scan summary's `secrets scan cost` lines, which name the most expensive rule per file.

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
