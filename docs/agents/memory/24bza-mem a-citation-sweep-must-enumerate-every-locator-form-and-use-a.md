# A citation sweep must enumerate every locator form and use an independent exact-span check

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bza-mem a-citation-sweep-must-enumerate-every-locator-form-and-use-a`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1vo1a-mem a-citation-sweep-must-cover-every-surface-form-run-last-and-`

## Summary

When you sweep or validate path:line citations on a published TechDocs page, first list every locator form the page uses (prose 'lines N-M', path:start-end, bare parenthesized numbers in markdown tables) and sweep each one. In the 1vj4e delivery review (DEL-6), a sweep of the prose form left 20 stale bare numbers in a table untouched. Judge ranges by exact-span resolution: the cited start line must fall inside the symbol's real AST span. Do not let the author of the miss write the only guard. The 1vj4e checker written after the fact judged ranges by overlap, and on the pre-repair page it would have passed two of the three sites it was credited with catching. Seed 178 (.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md, Step 3) already covers re-resolving last and preferring symbol citations.

## Evidence

- `1vj4e backstage-techdocs-baseline`
- `DEL-1`
- `DEL-6`
- `ev-del-6`
- `ev-del-6-2`
- `ev-del-6-3`

## Targets

- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `docs/prompts/refresh-techdocs.prompt.md`
- `docs/index.md`
