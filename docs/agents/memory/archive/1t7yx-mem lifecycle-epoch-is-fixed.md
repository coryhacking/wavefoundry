# lifecycle-epoch-is-fixed

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1t7yx-mem lifecycle-epoch-is-fixed`
Kind: `decision`
Confidence: 0.85
Created: 2026-07-22
Updated: 2026-11-25
Checked at: 2026-11-25T16:09:19Z
Check note: Item 7 review: target gone or duplicate. The record's fact is wrong (docs/workflow-config.json:5 now pins epoch_utc 2026-07-03T00:00:00Z under scheme v2, not 2022-04-28) and its action is carried canonically: the workflow-config notes field (:8), seed 011 (.wavefoundry/framework/seeds/011-install-wavefoundry-phase-1.prompt.md:103) and seed 160 (160-upgrade-wavefoundry.prompt.md:655, :832) say nev.
Check flags: target_churn
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, gone or carried by The record's fact is wrong (docs/workflow-config.json:5 now pins epoch_utc 2026-07-03T00:00:00Z under scheme v2, not 2022-04-28) and its action is carried canonically: the workflow-config notes field (:8), seed 011 (.wavefoundry/framework/seeds.
Archive path: `docs/agents/memory/archive/1t7yx-mem lifecycle-epoch-is-fixed.md`

## Summary

Never re-anchor the lifecycle id epoch: docs/workflow-config.json pins epoch_utc 2022-04-28T00:00:00Z from init, and every minted wave/change/memory id (including backdated deterministic memory renames) derives from it; changing the epoch silently changes id prefixes and breaks id ordering and migration idempotence.

## Evidence

- `docs/workflow-config.json`
- `.wavefoundry/framework/scripts/lifecycle_id.py`
- `1t9w7-ref memory-lifecycle-naming`

## Targets

- `docs/workflow-config.json`
- `.wavefoundry/framework/scripts/lifecycle_id.py`
