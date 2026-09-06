# Validator stub modules must mirror every name scan_secrets imports

Owner: Engineering
Status: active
Last verified: 2026-09-05

Memory ID: `1x6hh-mem validator-stub-modules-must-mirror-every-name-scan-secrets-i`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-09-05
Updated: 2026-09-05

## Summary

test_scan_secrets.py (_inject_mock_validators and the inline mock at the escalation test) and test_secret_scan_cache.py (test_update_secrets_scan_reports_skip_and_escalation) replace wave_lint_lib.secrets_validators with a bare types.ModuleType carrying only the names they knew about. When scan_secrets.update_secrets_scan gains a new import from that module (wave 1x5tr added unpublished_scanner_skips), every stub must gain the same attribute or the full suite fails with ImportError (unknown location) while the targeted suites stay green. Grep for ModuleType("wave_lint_lib.secrets_validators") and extend each stub in the same edit as the import.

## Evidence

- `1x5tr`
- `test_scan_secrets.TestUpdateSecretsScanEscalation`
- `test_secret_scan_cache.test_update_secrets_scan_reports_skip_and_escalation`
- `scratchpad 1x5tr_full_suite_r2.log ImportError: cannot import name unpublished_scanner_skips`

## Targets

- `.wavefoundry/framework/scripts/tests/test_scan_secrets.py`
- `.wavefoundry/framework/scripts/tests/test_secret_scan_cache.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
