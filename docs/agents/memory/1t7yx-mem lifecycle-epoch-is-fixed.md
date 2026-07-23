# lifecycle-epoch-is-fixed

Owner: Engineering
Status: active
Last verified: 2026-07-22

Memory ID: `1t7yx-mem lifecycle-epoch-is-fixed`
Kind: `decision`
Confidence: 0.85
Created: 2026-07-22
Updated: 2026-07-22
## Summary

Never re-anchor the lifecycle id epoch: docs/workflow-config.json pins epoch_utc 2022-04-28T00:00:00Z from init, and every minted wave/change/memory id (including backdated deterministic memory renames) derives from it; changing the epoch silently changes id prefixes and breaks id ordering and migration idempotence.

## Evidence

- `docs/workflow-config.json`
- `.wavefoundry/framework/scripts/lifecycle_id.py`
- `1t9w7-ref memory-lifecycle-naming`

## Targets

- `docs/workflow-config.json`
- `.wavefoundry/framework/scripts/lifecycle_id.py`
