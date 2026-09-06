# Secrets scan cache has two producers; cache-record rules must be mirrored in both

Owner: Engineering
Status: active
Last verified: 2026-09-05

Memory ID: `1x5tw-mem secrets-scan-cache-has-two-producers-cache-record-rules-must`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1286966
Source event: `finding:1x5tr:RED-DEL-9`
Validation: promote
Validated by: agent
Action delta: Any rule about what the secrets scan cache may record must be applied at BOTH cache producers, scan_secrets.update_secrets_scan (indexer path) and run_secrets_scan.main (the wf_scan_secrets subprocess and CLI), and pinned by a test through each entry point; a repair landed at one producer alone reproduced the original defect on the other.
Validation rationale: RED-DEL-9: the cycle-2 repair filtered unpublished guard outcomes out of the cache only in update_secrets_scan; the red-team seat reproduced the cycle-0 defect through run_secrets_scan.py (F5 probe), and the cycle-3 mirror plus RunSecretsScanGuardHistoryTests closed it. RED-DEL-10 showed the parked set must cover every evaluated path of a failed run, not only the skipped ones, or a failed clear pins a stale ledger row through the cache. Both producers verified on the current tree.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

The secret-scan cache (index_state_store secret_scan_record) is written by two producers: scan_secrets.update_secrets_scan on the indexer path and run_secrets_scan.main behind wf_scan_secrets and the CLI. A rule about what may be cached (wave 1x5tr: outcomes the guard-skip ledger never received stay uncached, via secrets_validators.unpublished_scanner_skips) must be applied at both sites and pinned with a test through each entry point; the cycle-2 repair at one site alone reproduced the defect on the other (RED-DEL-9). On a publication failure park every path the run evaluated, not only the guard-skipped ones, or a failed clear pins a stale ledger row through a cache hit (RED-DEL-10).

## Evidence

- `RED-DEL-9`
- `RED-DEL-10`
- `ev-red-del-9-3`
- `ev-red-del-10-3`
- `RunSecretsScanGuardHistoryTests.test_failed_publication_keeps_the_run_out_of_the_cache_on_the_scan_tool_path`
- `GuardCoverageIntegrationTests.test_failed_publication_of_a_clear_does_not_pin_the_stale_row`
- `1x5tr`

## Targets

- `.wavefoundry/framework/scripts/run_secrets_scan.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
