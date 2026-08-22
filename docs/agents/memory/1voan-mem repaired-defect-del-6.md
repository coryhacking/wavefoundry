# Repaired defect DEL-6

Owner: Engineering
Status: rejected
Last verified: 2026-08-18

Memory ID: `1voan-mem repaired-defect-del-6`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-18
Updated: 2026-08-18
Source exploration cost: 3814599
Source event: `finding:1vj4e:DEL-6`
Validation: reject
Validated by: agent
Action delta: Lesson is durable but cannot be recorded here (this draft's targets are dangling, which blocks rewrite); capture it with a fresh memory_add against seed 178, docs/prompts/refresh-techdocs.prompt.md and docs/index.md: when repairing a class of defect across a document, enumerate the defect's surface forms rather than grep the one form you wrote (a prose 'lines 1899-1906' range and a bare '(28804)' in a table are the same stale locator in two shapes), re-run the resolution pass last after every other edit in the session including sibling repairs, and let a party other than the author of the miss build the guard, with exact-span rather than overlap semantics.
Validation rationale: Rejecting the drafted record, not the lesson. Its summary is DEL-6's disposition sentence with no reusable action, and both targets are dangling: extract.py and resolve.py were the reverifying lane's scratch scripts under scratchpad/review/arch-rv2/, parsed out of a brace-expanded prose path in ev-del-6-3, and neither exists anywhere in the repository (repo-wide find returns nothing); memory_supply deliberately does not screen refs for on-disk existence. memory_validate's missing-target guard reads the candidate's own target_refs rather than the rewrite targets, so a corrected record naming the real surfaces cannot be recorded through this path and the draft is unsalvageable in place. The underlying lesson was verified end to end and is durable: DEL-1's repair left 22 of 60 anchors stale on docs/index.md because the sweep matched only the prose form and never saw the 20 bare parenthesized numbers in the tool-family table, both ranges it did recompute were re-broken by exactly +33 by the sibling DEL-2 insertion later in the same session, and the coordinator's overlap-semantics checker would have passed two of the three cycle-2 repair sites. Current tree checked: seed 178 lines 54 and 61 and the rendered twin lines 53 and 60 carry the Step 2 symbol-form preference and the Step 3 re-resolve rule, and docs/index.md has zero bare parenthesized line numbers with the table citing server_impl.register_mcp_surface. Recommend a follow-up memory_add for the enumeration and guard-independence halves the seed does not carry.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
## Summary

Real defect fixed in wave 1vj4e: DEL-6 resolved. The lane's four low findings (a short exit-code anchor, the checker's overlap semantics, five deliberate sub-ranges, and a one-level caller-guard scan) were folded in afterwards as editorial repairs, with the suite re-run g…

## Evidence

- `DEL-6`
- `ev-del-6-3`
- `1vj4e`

## Targets

- `extract.py`
- `resolve.py`
