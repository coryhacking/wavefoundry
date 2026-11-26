# Secrets-validator stub modules must mirror every name scan_secrets imports

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24a0q-mem secrets-validator-stub-modules-must-mirror-every-name-scan-s`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `1x6hh-mem validator-stub-modules-must-mirror-every-name-scan-secrets-i`
Checked at: 2026-11-26T06:32:43Z
Check note: The scanner tests still construct stub validator modules. Adding imports to the production path changes the stub contract. Reviewed .wavefoundry/framework/scripts/tests/test_scan_secrets.py:325.
Check flags: none

## Summary

When you add a name to the import from wave_lint_lib.secrets_validators in scan_secrets.update_secrets_scan, add the same attribute in the same edit to every stub that replaces that module. Find them by grepping for ModuleType("wave_lint_lib.secrets_validators"): _inject_mock_validators and the inline mock in test_scan_secrets.py, and test_update_secrets_scan_reports_skip_and_escalation in test_secret_scan_cache.py. These stubs are bare types.ModuleType objects that carry only the names they were written for. A missing attribute fails the full suite with 'ImportError: cannot import name' (unknown location) while the targeted suites stay green. Wave 1x5tr hit this when it added unpublished_scanner_skips.

## Evidence

- `1x5tr`
- `test_scan_secrets.TestUpdateSecretsScanEscalation`
- `test_secret_scan_cache.test_update_secrets_scan_reports_skip_and_escalation`

## Targets

- `.wavefoundry/framework/scripts/tests/test_scan_secrets.py`
- `.wavefoundry/framework/scripts/tests/test_secret_scan_cache.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
