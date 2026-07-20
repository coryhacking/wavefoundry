# Preserve content-addressed secret-scan candidate semantics

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-preserve-content-addressed-secret-scan-candidate-semantics`
Kind: `successful_pattern`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1rsha-enh incremental-secret-scan-cache:c8a6b38bde212073`
Validation: promote
Validated by: agent
Action delta: Preserve the distinct candidate semantics and full-scan bypass whenever secret-scan caching or file selection changes.
Validation rationale: Current source and tests still implement this non-obvious split, and losing it would silently reduce precision across branch switches or explicit full scans.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When changing secret scanning, keep the standalone scanner candidate set at all tracked files with content-addressed skips, keep the indexer path limited to its precise changed set, and make explicit full scans or rules changes bypass and repopulate the cache.

## Evidence

- `1rsha-enh incremental-secret-scan-cache`
- `1rsh9`
- `.wavefoundry/framework/scripts/run_secrets_scan.py:142`
- `.wavefoundry/framework/scripts/tests/test_secret_scan_cache.py`

## Targets

- `.wavefoundry/framework/scripts/run_secrets_scan.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/indexer.py`
