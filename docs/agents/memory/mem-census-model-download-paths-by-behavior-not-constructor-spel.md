# Census model-download paths by behavior, not constructor spelling

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-census-model-download-paths-by-behavior-not-constructor-spel`
Kind: `successful_pattern`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1p92t-bug ca-bundle-non-setup-launchers:6686f5a0c6ae98d2`
Validation: promote
Validated by: agent
Action delta: Census model-download behavior through call graphs and aliases, then verify TLS configuration and diagnostics at every path.
Validation rationale: The three correction rounds prove literal constructor searches are insufficient, while current code still has several distinct download entry paths.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When changing model-download or TLS handling, census construction paths by behavior and call graph rather than only literal constructor tokens, apply the CA environment at every raw download path, and keep certificate diagnostics visible through graceful-degradation catches.

## Evidence

- `1p92t-bug ca-bundle-non-setup-launchers`
- `1p939`
- `.wavefoundry/framework/scripts/accel_embedder.py:104`
- `.wavefoundry/framework/scripts/server_impl.py:489`
- `.wavefoundry/framework/scripts/indexer.py:3270`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py:14030`

## Targets

- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/indexer.py`
