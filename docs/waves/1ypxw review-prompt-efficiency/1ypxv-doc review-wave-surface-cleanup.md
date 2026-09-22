# Review Wave Surface Cleanup

Change ID: `1ypxv-doc review-wave-surface-cleanup`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-22
Wave: `1ypxw review-prompt-efficiency`

## Rationale

Wavefoundry's rendered `docs/prompts/review-wave.prompt.md` (2,555 tokens, utf8 bytes divided by 4, owned regions 26 percent) and its agent body (1,492 tokens) carry one hard correctness error and several passages that restate what the tools return. The error: step 3 says to run the delivery council "when `wave_review.enabled` is true" and "Required Before Close" says "when Wave Council is enabled", but `DELIVERY_MODES` in `review_policy.py` is `disabled`, `targeted` or `universal`, the receipt's `delivery_council_required` decides, Wavefoundry runs `targeted`, and the last three closed waves closed with no delivery council row; the agent body and seed 100 already state it correctly. Neither surface names `wf_review_wave` or says Review wave is the delivery phase. The agent body says "no re-Prepare unless the plan or scope became invalid", but any digested-section edit rotates the receipt. Steps 4 and 5 (AC scope gap, AC priority reconciliation) produced no artifact in three waves and nothing cites `## Review checkpoints`; the memory-capture section repeats the memory-review prompt; five cells in the agent body's lane table point at the section they sit in.

The packaged template `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md` (774 tokens) lacks every clause of seed 100's review-wave rule and the Truth Hierarchy section seed 160 backfills on upgrade, so a fresh install's review prompt omits gates its own next upgrade demands; seed 100 item 14 says the packaged templates are the only fresh-install source. It also has no exit-criteria line, no place for project-specific review instructions outside owned markers, and no phase or provenance sentence. No test pins its content today.

Three LOCAL items arrive from the sibling seed change: the rendered role docs `code-reviewer.md`, `qa-reviewer.md` and `architecture-reviewer.md` carry the mutation-table paragraph that seed 209 now owns, pinned by a wave `1wuju` test; `architecture-reviewer.md` keeps the tree-sitter coupling section (naming the current owners of `_TS_SYMBOL_LANG_MAP`, `server_impl.py` and `codenav_handlers.py`, instead of `server.py`) and `code-reviewer.md` gains the `accel_embedder` recorded case (it lives only in seed 221 today), since the sibling removes both from the generic seeds. The claim this change makes is modest: fewer duplicated paragraphs and a correct gate sentence lower entry cost; total read cost once pointers are followed is not claimed.

## Requirements

1. Public surface (LOCAL, outside the two owned regions `wave:executable-review-evidence` and `wavefoundry:review-policy`): step 3 and "Required Before Close" say delivery council runs when the current receipt lists `wave-council-delivery` under `required_council_signoffs`; the Purpose gains one sentence that Review wave is the delivery phase started with `wf_review_wave(wave_id, phase='implementation')`; step 6 says findings and approvals are recorded through `wf_review_event` and `## Review checkpoints` keeps only the narrative summary; steps 4 and 5 are conditional on the change doc carrying an `## AC Priority` table; "Required Before Close" gains the line that Review wave does not close the wave, mark completion or commit; the memory-capture section collapses to two lines pointing at `docs/prompts/memory-review.prompt.md` and keeps the literal `memory_add(status='candidate'` that `test_memory_records.py` pins; the seed 170 `[~]` pointer collapses into the sentence that carries it. The three step-2 literals `test_docs_lint.py` pins (the seed 209 packet-fields sentence, "Frozen tree per round", the `frozen_boundary` and `policy_input_digest` clause) stay verbatim. No `RETIRED_LIFECYCLE_TOKENS` string is introduced (in particular not "reviewer loop" or "fix and re-run reviewer"); the obligation anchors for the `lifecycle:review-wave.prompt.md` carrier row are satisfied by the owned policy block and stay.
2. Agent body (LOCAL): the five self-referential "inline, see Wavefoundry Review Specifics" cells are dropped; "Level 2: no re-Prepare unless" becomes "re-Prepare when `wf_review_wave` reports `review_policy_reprepare_required`", worded without the retired "fix and re-run reviewer" shape.
3. Packaged template (GENERIC, new installs; existing targets through seed 160's authored pass, which already backfills the Truth Hierarchy): after Purpose, the phase and provenance sentences (Review wave is the delivery phase; approvals come from contexts started for delivery review; retained contexts return findings and evidence but record no approval; without the typed tool, return judgment facts to the coordinator and never hand-edit the ledger); the seed 100 review-wave clauses (council when the current receipt requires it, AC scope gap and AC priority reconciliation with `qa-reviewer` attestation, `[~]` verification, `code-reviewer` not optional) with the briefing packet given as a pointer to seed 209's Briefing Packet plus at most the three names the public surface already pins (`tree_fingerprint`, `time_budget`, `sweep_rule`), consistent with seed 100 item 13's rule against copying seed 209's checklist; the Truth Hierarchy section; an exit-criteria line (Review wave ends when every required lane and any receipt-required council approval is current in `wf_review_wave`; it does not close, mark completion or commit); and an empty `## Project review specifics` heading outside owned markers. The existing `## Host-neutral orchestration` pointer stays (its carrier test mutation-tests it). Nothing names a Wavefoundry artifact or assumes Python. A new content pin beside `test_public_fresh_render_delivers_every_lifecycle_phase` asserts the phase and provenance sentences and the exit line, so a template mutant fails.
4. Role docs (LOCAL): `code-reviewer.md`, `qa-reviewer.md` and `architecture-reviewer.md` replace their mutation-table paragraph with the pointer sentence to seed 209's Landing rule that keeps the pinned clause "; report at the budget and list what was not run (seed 209, wave `1wuju`)" verbatim; the other two literals `test_prompt_surfaces_and_role_docs_are_reconciled` pins ("a mutation table for every mechanism" in architecture and qa, "Report it in a mutation table" in code) are updated in that test to the pointer wording, recording the `1wuju` amendment; `architecture-reviewer.md` keeps the tree-sitter coupling section with the current owners named; `code-reviewer.md` gains the `accel_embedder` recorded case from seed 221; all outside owned regions.
5. Tests named and updated in the same change: `test_docs_lint.py` `ReviewCycleChurnControlPinTests.test_prompt_surfaces_and_role_docs_are_reconciled` (public-surface literals kept; role-doc literals updated); `test_memory_records.py` (the `memory_add(status='candidate'` pin kept); the lifecycle-prompt class in `test_render_agent_surfaces.py` that covers review-wave (`test_public_fresh_render_delivers_every_lifecycle_phase`, `test_prompt_contract_and_known_bad_controls`) plus the new template pin; `test_events_only_residue_census.py` (no retired token introduced; its Level 2 strings are in-test fixtures, not tree reads). After the edits, `wf render-surfaces` leaves the owned regions and the hand-edited prose unchanged; the docs gate is clean; the prompt-surface manifest is unchanged.
6. Inventory: every sentence on the public surface and agent body classified as keep, cut, move-to-pointer or reword, with its seed owner and pinning test; the sizes before and after, measured, not pinned.

## Scope

**Problem statement:** the local review surfaces carry a wrong gate sentence and restated protocol; the packaged template omits the rule it exists to satisfy; three role docs duplicate a seed paragraph.

**In scope:** `docs/prompts/review-wave.prompt.md` and `docs/prompts/agents/review-wave.prompt.md` outside owned markers; the packaged review-wave template and its new pin; the three role docs outside owned regions; the named tests; CHANGELOG bullet.

**Out of scope:** seeds (sibling enhancement); the owned executable-review-evidence block and the tools (sibling bug change); any other lifecycle prompt.

## Acceptance Criteria

- [x] AC-1: The public surface names `wf_review_wave(phase='implementation')` and `wf_review_event`, ties delivery council to the current receipt, makes steps 4 and 5 conditional on the AC Priority table, states that Review wave does not close or commit, keeps the three pinned step-2 literals and the `memory_add(status='candidate'` literal; the wrong gate sentence is gone from both sites; new `test_docs_lint` pins cover the receipt-tied council sentence and the phase sentence.
- [x] AC-2: The agent body carries no self-referential cells and the re-Prepare sentence names `review_policy_reprepare_required`, pinned.
- [x] AC-3: The packaged template carries the phase and provenance sentences, the seed 100 clauses with the packet as a pointer, the Truth Hierarchy, the exit line and the project-specifics heading, names no Wavefoundry artifact, reads correctly without MCP, and the new content pin fails on a template mutant.
- [x] AC-4: The three role docs carry the pointer sentence with the budget clause; the updated role-doc pins pass; the tree-sitter section stays in `architecture-reviewer.md` with the current owners named and the `accel_embedder` case is present in `code-reviewer.md`.
- [x] AC-5: Owned regions unchanged after re-render; docs gate clean; manifest unchanged; the named tests pass with only the listed edits; before and after sizes recorded.

## Tasks

- [x] Inventory: sentence classification, pinning tests, sizes.
- [x] Rewrite the public surface and the agent body; add the new pins.
- [x] Bring the packaged template up to the seed 100 rule; add its content pin.
- [x] Edit the three role docs; update the role-doc pins.
- [x] Re-render; docs gate; CHANGELOG bullet; required delivery review (docs-contract lane reads every diff).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| surface-inventory | technical-writer | seed-edits (sibling change) | Written against the final seed text. |
| surface-rewrite | technical-writer | surface-inventory | Local surfaces, template, role docs. |
| independent-review | required reviewers | surface-rewrite | Docs-contract lane required. |

## Serialization Points

- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/agents/review-wave.prompt.md`
- `docs/agents/code-reviewer.md`
- `docs/agents/qa-reviewer.md`
- `docs/agents/architecture-reviewer.md`
- `.wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`

## Affected Architecture Docs

N/A: prompt and role-doc prose only.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The gate sentence is wrong today. |
| AC-2 | important | Salience and correctness of the re-Prepare rule. |
| AC-3 | important | Reaches new installs; upgrade path already exists. |
| AC-4 | important | Duplication removal; content preserved locally. |
| AC-5 | required | Owned regions and pinned carriers must survive a hand edit. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-22 | Readback / Thought: with six seed edits complete and the seed gate closed, reconcile the public and agent review prompts, generic install template and three local reviewer roles. Preserve owned blocks, public packet/frozen-tree literals, memory candidate literal and manifest. Add real-render template content and known-bad controls; independent delivery and full suite remain pending. | Seed/surface inventory; 7 seed/orchestration tests passed. |
| 2026-09-22 | Observe: source implementation frozen after 258 focused passes, 11 wording rechecks and three killed real-render template mutants. Final surface sync reported no writes; authored marker bytes and manifest preserved. Naming/duplication census and measured entry sizes recorded. Full suite and independent delivery remain pending. | `seed-surface-inventory.md` Executed verification and census; `test_fresh_review_template_contract_and_known_bad_controls`. |
| 2026-09-22 | Planned from the Review wave and implementation-review prompt reviews. | Coordinator reads. |
| 2026-09-22 | Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): the memory-capture collapse would have broken the `memory_add(status='candidate'` pin; the role-doc mutation-table cut is pinned by the `1wuju` reconciliation test, now named with its literals split into kept and updated; the template packet clause becomes a pointer per seed 100 item 13; the template gains its first content pin; the three step-2 literals and the retired-token strings to avoid are named. | Readiness review in this wave directory. |

| 2026-09-22 | Observe: implementation and delivery review complete; all ACs/tasks checked, C-1/C-2 terminal, four current delivery lane approvals, green current 9,533-test receipt and stable passing before/after retrieval comparison. Both edit gates closed. Wave remains open for operator closure; no commit performed. | `delivery-review.md` and typed review ledger. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-22 | Keep the Wavefoundry-specific reviewer passages in the role docs, not the seeds. | The sibling change de-localizes the seeds; the content is still true for this repository. | Delete them; loses a real coupling note. |
| 2026-09-22 | Template grows to carry the seed 100 rule, with the packet as a pointer. | A fresh install otherwise omits gates its next upgrade demands; item 13 forbids copying seed 209's checklist. | Keep the template short; the install is then wrong for one release. |
| 2026-09-22 | Role-doc pointer keeps the budget clause; the other `1wuju` literals move to the pointer wording in the test. | The budget clause is a real obligation with no other local home; the mutation-table wording is seed 209's. | Keep the whole paragraph; duplication stays. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A cut sentence was load-bearing for a host without seed access. | Every cut is classified against its seed owner and pinning test in the inventory. |
| The template's new clauses drift from seed 100. | Seed 100 item 14 (sibling change) names the template as the carrier; the new content pin and the docs-contract lane compare them at delivery. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
