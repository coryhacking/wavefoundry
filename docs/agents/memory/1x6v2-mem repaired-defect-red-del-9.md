# Repaired defect RED-DEL-9

Owner: Engineering
Status: superseded
Last verified: 2026-09-05

Memory ID: `1x6v2-mem repaired-defect-red-del-9`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1286966
Source event: `finding:1x5tr:RED-DEL-9`
Validation: rewrite
Validated by: agent
Action delta: Any rule about what the secrets scan cache may record must be applied at BOTH cache producers, scan_secrets.update_secrets_scan (indexer path) and run_secrets_scan.main (the wf_scan_secrets subprocess and CLI), and pinned by a test through each entry point; a repair landed at one producer alone reproduced the original defect on the other.
Validation rationale: RED-DEL-9: the cycle-2 repair filtered unpublished guard outcomes out of the cache only in update_secrets_scan; the red-team seat reproduced the cycle-0 defect through run_secrets_scan.py (F5 probe), and the cycle-3 mirror plus RunSecretsScanGuardHistoryTests closed it. RED-DEL-10 showed the parked set must cover every evaluated path of a failed run, not only the skipped ones, or a failed clear pins a stale ledger row through the cache. Both producers verified on the current tree.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1x5tw-mem secrets-scan-cache-has-two-producers-cache-record-rules-must`
## Summary

Real defect fixed in wave 1x5tr: The second producer now applies the same rule; the change doc and tool-surface text name both producers.

## Evidence

- `RED-DEL-9`
- `ev-red-del-9-3`
- `1x5tr`

## Targets

- `run_secrets_scan.py`
