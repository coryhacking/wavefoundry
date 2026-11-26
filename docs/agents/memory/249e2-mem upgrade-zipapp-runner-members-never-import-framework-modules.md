# Upgrade zipapp runner members never import framework modules unconditionally

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249e2-mem upgrade-zipapp-runner-members-never-import-framework-modules`
Kind: `decision`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 184122
Supersedes: `204bd-mem decision-the-upgrade-zipapp-runner-members-upgrade-bundle-py`

## Summary

When editing .wavefoundry/framework/scripts/upgrade_bundle.py or upgrade_bridge_bootstrap.py, set sys.dont_write_bytecode before any other import and never add an unconditional framework import (bytecode_cache or any other); guard optional imports. Why: decision of wave 200xy (readiness round 2); these files run as release upgrade zipapp members and as a standalone copied bridge where bytecode_cache is not importable, so an unguarded import breaks every release upgrade, which the delivery review confirmed by rebuilding and running the real bundle.

## Evidence

- `1zyv1-enh project-local-bytecode-cache`
- `200xy`

## Targets

- `.wavefoundry/framework/scripts/upgrade_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
- `.wavefoundry/framework/scripts/bytecode_cache.py`
