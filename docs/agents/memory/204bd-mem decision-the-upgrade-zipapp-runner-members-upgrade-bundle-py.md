# Decision: The upgrade zipapp runner members (`upgrade_bundle.py`, `up…

Owner: Engineering
Status: active
Last verified: 2026-10-07

Memory ID: `204bd-mem decision-the-upgrade-zipapp-runner-members-upgrade-bundle-py`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 184122
Source event: `decision-log:1zyv1-enh project-local-bytecode-cache:050ade07df6137a2`
Validation: promote
Validated by: agent
Action delta: Never add an unconditional framework import (bytecode_cache or any other) to the upgrade zipapp members upgrade_bundle.py or upgrade_bridge_bootstrap.py; set sys.dont_write_bytecode first and guard optional imports.
Validation rationale: Readiness round 2 found the unconditional import would break every release upgrade, because those members run from the zip root and as a standalone bridge file; the delivery review rebuilt and ran the real bundle and confirmed it fails if it gains an unguarded import.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Decision (wave 200xy): The upgrade zipapp runner members (`upgrade_bundle.py`, `upgrade_bridge_bootstrap.py`) set the flag before imports and do not import `bytecode_cache` unconditionally (readiness round 2).. Rationale: They run as zip-root members and as a standalone bridge file where `bytecode_cache` is not importable; an unconditional import breaks every release upgrade..

## Evidence

- `1zyv1-enh project-local-bytecode-cache`
- `200xy`

## Targets

- `upgrade_bundle.py`
- `upgrade_bridge_bootstrap.py`
- `bytecode_cache.py`
