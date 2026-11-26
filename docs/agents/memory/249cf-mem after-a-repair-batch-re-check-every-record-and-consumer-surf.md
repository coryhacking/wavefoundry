# After a repair batch, re-check every record and consumer surface against the shipped behavior

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249cf-mem after-a-repair-batch-re-check-every-record-and-consumer-surf`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 3090767
Supersedes: `1vpm4-mem behavioral-repairs-can-leave-their-records-and-consumers-fal`

## Summary

When a review repair batch passes its implementation tests, run the public behavior again and re-read every record and consumer surface the repair touched: wave and change records, docs/agents/session-handoff.md, public prompts and seeds, the tool-surface contract, and consumer prose about bounded responses. Each must still match what ships. Do not check the repair prose only against itself. In wave 1vqqi (DEL-10), the techdocs_audit.py repair passed its tests while the 1vmt2 change doc, the handoff, seed 178 and the tool-surface contract still described the old behavior.

## Evidence

- `DEL-10`
- `ev-del-10-3`
- `delivery-1vqqi-rv5-docs`
- `1vqqi techdocs-audit-and-review-branch`

## Targets

- `docs/waves/1vqqi techdocs-audit-and-review-branch/1vmt2-enh techdocs-audit-tool-and-review-only-branch.md`
- `docs/agents/session-handoff.md`
- `docs/architecture/contracts/mcp-tool-surface.md`
- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `.wavefoundry/framework/scripts/techdocs_audit.py`
