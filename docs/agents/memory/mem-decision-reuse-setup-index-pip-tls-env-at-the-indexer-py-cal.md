# Decision: Reuse `setup_index._pip_tls_env()` at the `indexer.py` call…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-reuse-setup-index-pip-tls-env-at-the-indexer-py-cal`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p93u-bug lancedb-autoinstall-bare-pip-tls:ac1d86e2172714b8`
Validation: reject
Validated by: agent
Action delta: None; apply the consolidated model-download and TLS-path census guidance and inspect the current shared helper.
Validation rationale: The specific helper reuse is embodied in current code and overlaps the broader active TLS-path memory.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p93v): Reuse `setup_index._pip_tls_env()` at the `indexer.py` call site rather than writing a new helper or duplicating CA-merge logic.. Rationale: Identical problem shape to the three already-fixed `setup_index.py` call sites; `_pip_tls_env()` is already proven correct and tested (wave 1p8tf)..

## Evidence

- `1p93u-bug lancedb-autoinstall-bare-pip-tls`
- `1p93v`

## Targets

- `indexer.py`
- `setup_index.py`
