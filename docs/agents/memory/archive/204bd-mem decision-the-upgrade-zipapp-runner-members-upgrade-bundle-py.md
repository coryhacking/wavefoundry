# Decision: The upgrade zipapp runner members (`upgrade_bundle.py`, `up…

Owner: Engineering
Status: archived
Last verified: 2026-10-07

Memory ID: `204bd-mem decision-the-upgrade-zipapp-runner-members-upgrade-bundle-py`
Superseded by: `249e2-mem upgrade-zipapp-runner-members-never-import-framework-modules`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-11-25
Source exploration cost: 184122
Source event: `decision-log:1zyv1-enh project-local-bytecode-cache:050ade07df6137a2`
Validation: promote
Validated by: agent
Action delta: Never add an unconditional framework import (bytecode_cache or any other) to the upgrade zipapp members upgrade_bundle.py or upgrade_bridge_bootstrap.py; set sys.dont_write_bytecode first and guard optional imports.
Validation rationale: Readiness round 2 found the unconditional import would break every release upgrade, because those members run from the zip root and as a standalone bridge file; the delivery review rebuilt and ran the real bundle and confirmed it fails if it gains an unguarded import.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Archived: 2026-11-25
Archive reason: Superseded by 249e2-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/204bd-mem decision-the-upgrade-zipapp-runner-members-upgrade-bundle-py.md`

## Summary

Decision (wave 200xy): The upgrade zipapp runner members (`upgrade_bundle.py`, `upgrade_bridge_bootstrap.py`) set the flag before imports and do not import `bytecode_cache` unconditionally (readiness round 2).. Rationale: They run as zip-root members and as a standalone bridge file where `bytecode_cache` is not importable; an unconditional import breaks every release upgrade..

## Evidence

- `1zyv1-enh project-local-bytecode-cache`
- `200xy`

## Targets

- `upgrade_bundle.py`
- `upgrade_bridge_bootstrap.py`
- `bytecode_cache.py`
