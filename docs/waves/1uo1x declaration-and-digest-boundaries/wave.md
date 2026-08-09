# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-07
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uo1x declaration-and-digest-boundaries`
Title: Declaration And Digest Boundaries

## Objective

Fix two silent boundary defects in the review-policy machinery. First, one sentence of prose inside `## Serialization Points` currently flips an entire wave into declared-target mode and can empty its required-lane roster; adoption becomes per-document with a two-tier declaration form whose floor accepts only pure-path bullets, so prose in any shape can never again remove review coverage. Second, the status normalizer can rewrite a body `Status:` line it promises to leave alone, making a real contract edit digest-invisible; the frontmatter scan becomes a fixed known-key allowlist with an explicitly stated ambiguity guard.

## Changes

Change ID: `1uo1w-bug prose-flips-declared-mode-and-drops-lanes`
Change Status: `implemented`

Change ID: `1umsf-bug status-normalization-captures-body-prose`
Change Status: `implemented`

## Participants

- Coordinator: session agent (Claude Code)
- Write-owning roles: implementer (red-test, adoption, spaces, carriers, transition workstreams for 1uo1w; red-test, boundary, guard, census workstreams for 1umsf)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-07

## Wave Summary

Wave `1uo1x` (Declaration And Digest Boundaries) delivered two changes: Prose Flips Declared Mode And Drops Lanes and Status Normalization Captures Body Prose. Notable adjustments during implementation: Prose Flips Declared Mode And Drops Lanes: Pure-path floor measured: 817 change docs, 138 declared, 40 keep, 98 revert, zero lane losses corpus-wide, 92 reverting docs gain lanes. Live exposure three docs: this wave's two plans keep; `1rolq` reverts with gains. Phantom mechanism confirmed: the unbackticked spaced-path bullet extracts nothing because `docs/waves/1uo1x` fails the predicate and the all-tokens rule rejects the bullet. The embedded template's placeholder bullet is also rejected as prose under the floor, closing a pre-existing hazard; Prose Flips Declared Mode And Drops Lanes: Council P2s folded: `_wave_code_footprint` acknowledged as the second consumer of the extractor, with the porcelain double-quoting case added to AC-5; the Risks row citing a nonexistent "allowed-values affordance" rewritten to the floor's real mitigation; Prose Flips Declared Mode And Drops Lanes: IMPLEMENTED. All five red tests written first and confirmed failing on current code (prose bullet AND plain line emptying the roster, mixed wave collapsing, phantom `declaration-and-digest-boundaries/wave.md`, wrapped bullet declaring only its continuation-line target, scaffold placeholder declaring `src/app/handler.py`). Wave-level suppression deleted; two-tier extraction added.

**Changes delivered:**

- **Prose Flips Declared Mode And Drops Lanes** (`1uo1w-bug prose-flips-declared-mode-and-drops-lanes`) — 12 ACs completed. Key decisions: Adoption is per document, not per wave; Floor is pure-path bullets, all tokens accepted or the bullet is prose
- **Status Normalization Captures Body Prose** (`1umsf-bug status-normalization-captures-body-prose`) — 7 ACs completed. Key decisions: Replace the heading-bounded design with a fixed known-key allowlist; Tolerate blockquotes inside the carrier
## Watchpoints

- Blocking: adoption is per DOCUMENT, never per wave. Wave-level suppression is the original defect; an independent probe showed a mixed wave collapsing `[code, qa, docs-contract]` to `[docs-contract]` under the first proposed design. AC-3's mixed-wave fixture is the only detector; a corpus census passes under a correct and an incorrect design alike.
- Blocking: a shredded path fragment (`declaration-and-digest-boundaries/wave.md` from a space-containing path) must never become a declared target. The phantom is worse than the silent drop because it suppresses the fallback and yields zero lanes.
- Watchpoint: the 1umsf guard admits match counts one AND two; the literal sibling `len(matches) != 1` contract would stop normalizing 794 documents (current-scan bucket over 1457 docs) and lapse approvals on every status advance. AC-5 pins the wrong implementation as a failing test.
- Watchpoint: prose bullets must NOT confer adoption. The council's probe emptied a roster with `- Shared with the wave that also touches the docs/ folder` under the scanned-bullet floor; the pure-path rule (every token accepted or the bullet is prose) is the fix, measured at zero lane losses corpus-wide with 92 of 98 reverting docs gaining lanes.
- Watchpoint: `REVIEW_POLICY_EVALUATOR_VERSION` bumps (5 to 6) once for the whole wave, carrying both 1uo1w's lane-semantics change and 1umsf's digest boundary change; one-time re-Prepare for non-closed waves, disclosed in the changelog. Closed waves stay byte-immutable.
- Watchpoint: 1uo1w edits seeds (040, 160, 170) and the shipped lifecycle prompt; the `seed_edit_allowed` gate must be opened before and closed immediately after those edits. Seed 160:199 carries the "Adoption is per WAVE" sentence this wave deletes.
- Follow-ups filed separately: unique-basename resolution (zero day-one recall behind the marker), and a systematic audit of every path-parsing site for space handling.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-07: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the first council round FAILED readiness by disproving both headline designs with evidence the plans had recorded as reassurance: red-team showed heading-bounding was structurally vacuous because a `## ` heading already closes the current scan, so zero post-heading captures is a property of the code, and executed a probe in which the plan's own repro still captured under heading-bounding while a prose bullet emptied a roster under the scanned-bullet floor, whose 134-of-138 preservation census was counting an empty-roster misclassification as a keep; docs-contract independently found a fourth guarantee carrier the exact-phrase grep had missed, seed 160:199, which ships the "Adoption is per WAVE" sentence this wave deletes, with stale siblings at :198 and :481. Both plans were rewritten to the seats' proposed alternatives (fixed known-key allowlist boundary; pure-path-bullet floor), and a fresh second-round verification seat reproduced every census figure exactly (1457-doc captured-set diff of exactly one document, 1p7dg widening; 138 declared, 40 keep, 98 revert, zero lane losses, 92 gains; live exposure three documents, all safe), failed both directed falsification attempts against the floor, and confirmed all four prior P1 repairs. Its two P2s were folded as AC tightenings: the porcelain-match pin moved to a spaced target outside `_FOOTPRINT_EXCLUDE_PREFIXES` because `docs/` is footprint-excluded and the originally named artifact class would have measured zero under correct and incorrect handling alike, and AC-8 gained a freshly-scaffolded-doc-declares-nothing pin with a stated tier-2 block boundary so documenting the marker cannot re-open the placeholder hazard; strongest-alternative: the seats' own alternative designs were adopted as the shipped designs rather than rejected, and the final round's remaining alternative was the AC tightening described above, also adopted. Two rounds, coordinator-run with independent sandboxed seats, proportionate to a wave whose first two revisions were each falsified by independent review)

- **Delivery review [initial_delivery] — 2026-08-07: PASS after repair** (lanes run as independent sandboxed reviewers against copies of the shipped tree, each free to mutate its own copy; the real tree was never written to by a lane. **docs-contract: WITHHELD then repaired** — found the reported defect SURVIVING inside the new tier-2 block, where span extraction took every backticked token and ignored the words around it, so the wave's own worst-case sentence still took a document from two required lanes to zero in the block the docs present as the stricter opt-in; also found the seed examples taught a declaration form the parser rejects. **code: APPROVE** with three P2s, all repaired: `_serialization_points_body` was fence-blind so a fenced EXAMPLE of a whole Serialization Points section substituted for the real one and dropped a lane (a shape this change made MORE likely, because the scaffold it ships now teaches fenced examples in that section); `index in block` contradicted the union invariant the module documents; and the rename-parse fix had zero coverage, with both deletion and inversion leaving the suite green. **qa: WITHHELD** on a P1 whose repair had already landed between its snapshot and its report, verified by re-running its exact mutations against the live tree rather than by argument, plus six genuinely unpinned branches, all now covered. **qa reverification: APPROVE** — nine mutations killed across all seven prior findings, both censuses reproduced exactly, 18/18 behavior cases correct, and one new P2 found and fixed in session: a tier-2 span carrying a path plus a trailing note declared a phantom that suppressed the fallback and zeroed the wave footprint. The reverifier also isolated a census confound, showing that 42 apparent lane losses in a naive HEAD comparison belong to closed wave 1umst's fallback-corpus canonicalization and not to this change. Twenty-two mutations killed in total across coordinator and lane harnesses; final measurement 815 change docs, 139 declared before, 38 after, 101 revert, 95 gain, ZERO lane losses)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 29 | 6,217 |
| implement | 39 | 1,111,892 |
| review | 66 | 836,812 |
| **Total** | **134** | **1,954,921** |

<!-- wave:context-efficiency-state {"generation":142,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":39,"content_source_credit":1174247,"derived_artifact_credit":2009,"direct_net":1111892,"estimated_tokens_saved":1111892,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4066,"response_debit":61729,"source_credit_count":51,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":29,"content_source_credit":35323,"derived_artifact_credit":1466,"direct_net":6217,"estimated_tokens_saved":6217,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5476,"response_debit":30546,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5450},"review":{"calls":66,"content_source_credit":987926,"derived_artifact_credit":1022,"direct_net":836812,"estimated_tokens_saved":836812,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5179,"response_debit":148303,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":134,"content_source_credit":2197496,"derived_artifact_credit":4497,"direct_net":1954921,"estimated_tokens_saved":1954921,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14721,"response_debit":240578,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8227},"wave_id":"1uo1x declaration-and-digest-boundaries"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 12 | 0 | 7 | 3,893,990 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":3893990,"surfaced_events":12} -->
<!-- wave:exploration-avoided end -->
