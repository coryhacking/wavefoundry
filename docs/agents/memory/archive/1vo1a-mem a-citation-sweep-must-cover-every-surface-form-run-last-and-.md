# A citation sweep must cover every surface form, run last, and be guarded by someone other than its author

Owner: Engineering
Status: archived
Last verified: 2026-08-18

Memory ID: `1vo1a-mem a-citation-sweep-must-cover-every-surface-form-run-last-and-`
Superseded by: `24bza-mem a-citation-sweep-must-enumerate-every-locator-form-and-use-a`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-08-18
Updated: 2026-11-25
Archived: 2026-11-25
Archive reason: Superseded by 24bza-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1vo1a-mem a-citation-sweep-must-cover-every-surface-form-run-last-and-.md`

## Summary

When repairing or validating `path:line` citations on a published page, do three things the 1vj4e delivery review had to learn twice. First, enumerate EVERY locator surface form before sweeping: a substring sweep of the prose `lines N-M` form left 20 bare parenthesized numbers in a markdown table untouched, and they were all stale. Second, re-resolve after every other edit in the session is complete, including edits made by a sibling repair to the same file: two ranges recomputed correctly mid-session were re-broken by exactly +33 when another repair inserted a function above them. Third, do not let the party who made the miss supply the only guard: the checker written after the fact judged ranges by overlap, and re-run against the pre-repair page it would have passed two of the three sites it was credited with catching. Only exact-span resolution (the cited start must fall inside the symbol's real AST span) detects this class. Seed 178 now carries the timing and coverage halves of this rule; the enumeration and guard-independence halves live only here.

## Evidence

- `1vj4e backstage-techdocs-baseline`
- `DEL-1`
- `DEL-6`
- `ev-del-6`
- `ev-del-6-2`
- `ev-del-6-3`
- `docs/waves/1vj4e backstage-techdocs-baseline/events.jsonl`

## Targets

- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `docs/prompts/refresh-techdocs.prompt.md`
- `docs/index.md`
