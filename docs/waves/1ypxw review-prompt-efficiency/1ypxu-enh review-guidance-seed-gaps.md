# Review Guidance Seed Gaps

Change ID: `1ypxu-enh review-guidance-seed-gaps`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-22
Wave: `1ypxw review-prompt-efficiency`

## Rationale

The two independent reviews of the **Review wave** prompt and of the implementation review step (2026-09-21) found that the delivery-review contract is complete and every name in it resolves, but that it is stated three to four times across seeds 180, 209, 215 and each reviewer seed, that two generic seeds carry Wavefoundry-specific content, and that four generic behaviors the histories paid for are missing one sentence each. Every item here is GENERIC and reaches existing targets by a seed re-render on upgrade plus seed 160's authored reconciliation of project-owned carriers; nothing here belongs in the packaged template or Wavefoundry's own surfaces (sibling documentation change). This change depends on wave `1ypy6` closing first, because that wave edits seeds 180, 209 and 100 and two of its edits sit in the same paragraphs as edits here (seed 209's Typed authoring paragraph and its Code-Grounded Verification paragraph); every sentence here is named so the inventory can re-verify it against the landed text.

The gaps. Seed 209 does not say that delivery approvals are finding-scoped rather than receipt-scoped, so lanes re-record them on every rotation. Its Code-Grounded Verification names three top-risk claim shapes and omits attribution of a measured delta, the shape the last handler wave misread (`1ypy6` adds the substrate sentence after the pinned census sentence; this change adds the claim-shape clause to the earlier sentence that lists the three). Seed 239's evidence-integrity gate has no controlled-comparison condition. Seed 100's review-wave rule says nothing about which phase Review wave is or about context provenance for delivery approvals, and item 14 does not say the packaged template is the fresh-install carrier of that rule.

The duplication. The mutation-table paragraph appears byte-identically (apart from capitalization) in seeds 221, 239 and 214 and again in the rendered role docs, while seed 209's Landing rule for guards already defines it as the prose projection of `known_bad_detection_method: focused-mutation`; the paragraph's sweep-rule and time-budget sentence already sits in seed 209's packet row. Seed 180 describes the evidence packet a lane needs in two bullets ("Accept integrated evidence", "Hand off through existing artifacts") with a vocabulary different from seed 209's briefing packet, so lanes rebuilt their own hash manifests even though the packet already requires `tree_fingerprint`. Seed 180 calls a per-change delivery checkpoint inside a multi-change wave "exceptional" at three sites and says routine lanes run "later through Review wave" once literally and three times in paraphrase, while every recent multi-change wave ran a per-change checkpoint by plan. Seed 209's Typed authoring paragraph enumerates the judgment, evidence and integrity fields that `review_action_input_schema` returns on every call. The first draft also proposed removing seed 180's reference to `docs/contributing/agent-team-workflow.md` as dangling; readiness showed the framework treats that file as an expected target carrier (ten other seeds name it, 005, 007, 020, 050, 100, 150, 160, 170, 190 and 200, and seed 160 backfills it when absent), so that item is withdrawn.

The boundary. Seed 214 opens "You are running architecture-reviewer on Wavefoundry" and carries a tree-sitter coupling section naming `_TS_SYMBOL_LANG_MAP` and `server.py` (the symbol now lives in `server_impl.py` and is read from `codenav_handlers.py`); seed 221's false-positive guard cites the `accel_embedder` docstring case. Both are Wavefoundry content in generic seeds; Wavefoundry keeps them in its rendered role docs (sibling change) and the seeds get stack-neutral wording. Seed 212 opens the same way and is recorded in the census as out of scope.

## Requirements

1. Seed 209. Derived and lifecycle invariants: the existing bullet "Approval freshness is finding/lane scoped" is extended (insert, do not edit) with the sentence that delivery approvals are finding-scoped, not receipt-scoped; publishing a new review-policy receipt lapses readiness approvals only; a delivery approval stays current until a later synthesis names its lane in `approval_recheck_lanes` or a blocking head remains open for it; do not re-record a delivery approval because the receipt moved. Code-Grounded Verification: the sentence listing the three top-risk claim shapes gains attribution of a measured delta as a fourth, referring to the substrate sentence by content ("a before/after pair whose substrates differ"), with no wave id. Typed authoring and human view: exactly these sentences are removed because `review_action_input_schema` returns them on every call and the contract tests compare the registries, not the prose: the enumeration of the ten judgment facts, the six repair and proportionality facts, the finding and approval evidence field lists, and the five `integrity_checks` booleans; every other sentence is kept, including the writing-hand sentence wave `1ypy6` adds, the registry-ownership sentence, the `wf_review_event`-over-hand-serialized-JSONL sentence, the one-phase-correct `wf_review_wave` call, the `review_actions` bounded-projection sentence, `event: list` for forensics, the one-phase-never-satisfies-the-other rule, and what the tool derives.
2. Seed 239's evidence-integrity gate gains a condition: a before/after measurement attributes its delta to the change only when the two runs are shown to differ in nothing else, with a one-line pointer to seed 209's substrate sentence; otherwise the delta is recorded as unattributed.
3. Seeds 221, 239 and 214 replace their mutation-table paragraph with one pointer sentence to seed 209's Landing rule for guards that keeps the report-at-the-budget clause verbatim ("report at the budget and list what was not run"); the paragraphs have no non-duplicated clause (the sweep-rule and time-budget sentence is already seed 209's packet row). `test_lane_seeds_require_the_mutation_table` in `test_docs_lint.py`, a wave `1wuju` landing pin on four literals in each seed, is rewritten to the pointer wording in the same change, and the Decision Log records the `1wuju` amendment; the rendered role-doc half of that pin is owned by the sibling `1ypxv`.
4. Seed 180: the two evidence bullets are replaced by a pointer to seed 209's briefing packet, which gains the optional fields `changed_paths`, `commands_and_results`, `test_receipt` and `unresolved_findings` (the packet already requires `tree_fingerprint`; lanes reuse it); the one literal and three paraphrased "later through Review wave" statements collapse to one; the three "exceptional" sites are reworded so a per-change delivery checkpoint inside a multi-change wave is ordinary sequencing, and the approval a lane records at such a checkpoint IS that lane's wave-level delivery approval, subject to later `approval_recheck_lanes`; the authority model (one delivery approval per lane per wave, per `claim_id: approval:<signoff-key>`) is unchanged. Task 6 is not edited.
5. Seed 100's review-wave rule gains two sentences: Review wave is the delivery phase and readiness review already ran at Prepare; every required-lane approval comes from a reviewer context started for delivery review, and a context retained from readiness, an inventory or checkpoint pass, or a repair may return findings and evidence but records no approval. Item 14 states that the packaged review-wave template is the fresh-install carrier of the review-wave rule, so the template (sibling change) must satisfy it.
6. Seeds 214 and 221 lose their Wavefoundry-specific passages in favor of stack-neutral wording that keeps each rule. Seed 214: the opening names the role without the project, and the coupling section becomes the rule that a query-time coupling recorded in the project's domain map as an inbound dependency (symbol expansion depending on a parser or grammar stack) is re-verified whenever code changes the set of supported grammars or the lazy-load path, with a medium finding when the map is not updated. Seed 221: the recorded case keeps its three facts (a docstring declared a degradation branch unreachable; the branch was the live offline path exercised by existing tests; a sweep that trusted the docstring approved removing working code) without the module name. The sibling change keeps the specific content in Wavefoundry's role docs, naming the current owners of `_TS_SYMBOL_LANG_MAP`.
7. Propagation is explicit: the inventory carries a table with one row per changed sentence (seed anchor, every destination, mechanism: read from the seed; renderer constant edited, named; seed 160's authored reconciliation at upgrade, whose carrier clause triggers on seeds 180, 209, 214, 221 and 239 and whose repo-local prompt reconciliation triggers on seed 100; Wavefoundry's own surfaces via the sibling change), and a destination with no mechanism is recorded as not propagated. Every seed edit is made with `seed_edit_allowed` open and closed immediately after; `wf render-surfaces` runs once and its diff is limited to renderer-owned regions.
8. Pinned tests respected and updated in the same change: `test_lane_seeds_require_the_mutation_table` (rewritten); the seed byte pins in `test_upgrade_wavefoundry.py` and `test_setup_wavefoundry.py` (pass as long as the same seed ships); `test_docs_lint.py` seed-text pins adjacent to the edits (the packet `tree_fingerprint` row, the projection rule, the census sentence: insert beside, never edit); no seed 160 edit, so its pinned blocks are untouched; the inventory re-checks every seed 209 anchor against the text `1ypy6` lands.

## Scope

**Problem statement:** the delivery-review contract is correct but repeated and locally contaminated, and four generic behaviors the histories paid for lack one sentence each.

**In scope:** seeds 209, 239, 221, 214, 180 and 100 as itemized; the propagation table; the rewritten seed pin; regenerated renderer-owned regions; CHANGELOG bullet.

**Out of scope:** seed 180 and 209 sentences owned by wave `1ypy6`; seed 180 task 6 and the `agent-team-workflow.md` reference (an expected carrier, not dangling); seed 212's opening (recorded, out of scope); the packaged review-wave template and every Wavefoundry surface (sibling documentation change); the tools (sibling bug change); any change to the readiness rule or the delivery-round rule (delivery stays an open repair loop by design).

## Acceptance Criteria

- [x] AC-1: Seed 209 carries the extended freshness bullet, the fourth claim shape and the Typed authoring paragraph with exactly the four enumerations removed and every other sentence kept; seed 239 carries the controlled-comparison condition; all generic and naming no Wavefoundry artifact or wave id.
- [x] AC-2: Seeds 221, 239 and 214 carry the pointer sentence with the budget clause; a grep census records one owner (seed 209) for the mutation-table paragraph; the rewritten seed pin passes.
- [x] AC-3: Seed 180 carries the packet pointer, one Review-wave statement and the ordinary-sequencing wording; seed 209's packet carries the four new optional fields; task 6 is unchanged.
- [x] AC-4: Seed 100 carries the phase and provenance sentences and the item 14 statement.
- [x] AC-5: Seeds 214 and 221 name no Wavefoundry module, symbol or file; a grep census over the seeds for `Wavefoundry`, `_TS_SYMBOL_LANG_MAP`, `accel_embedder` and `server.py` records every remaining hit with its reason, with the pre-existing tool-posture "Wavefoundry MCP" lines, the "(wave 1wuju)" parentheticals and seed 212's opening recorded as remaining, not new.
- [x] AC-6: The propagation table exists with a mechanism or a not-propagated note per row; the framework suite and docs gate pass; the gate is closed at the end of the change.

## Tasks

- [x] Inventory: anchors re-verified against the `1ypy6` landed text, pinned tests, the propagation table, the three-seed paragraph comparison.
- [x] Open the seed gate; make the seed edits; close the gate.
- [x] Rewrite the seed pin; run `wf render-surfaces` once; run the censuses.
- [x] CHANGELOG bullet; framework suite; required delivery review (docs-contract lane greps every new sentence for Wavefoundry artifacts).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| seed-inventory | implementer | tool-fixes (sibling change) | After `1ypy6` closes; anchors re-verified against its seed edits. |
| seed-edits | implementer | seed-inventory | Gate open only for the edit window. |
| independent-review | required reviewers | seed-edits | Docs-contract lane reads every regenerated diff. |

## Serialization Points

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/239-qa-reviewer.prompt.md`
- `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md`
- `.wavefoundry/framework/seeds/214-architecture-reviewer.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`

## Affected Architecture Docs

N/A: seed prose changes; no module boundary, flow or verification architecture changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The missing behaviors and the one shared paragraph. |
| AC-2 | important | Duplication removal; behavior unchanged. |
| AC-3 | important | Packet vocabulary unified. |
| AC-4 | required | Phase and provenance are the two sentences a reviewer needs first. |
| AC-5 | required | Generic seeds must not carry one target's content. |
| AC-6 | required | Propagation honesty and gate hygiene. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-22 | Readback / Thought: after the tooling dependency passed focused checks, implement only six seeds and their pins; preserve writing-hand/substrate sentences, integration obligations, task 6, packet/census anchors and registry authority. Seed gate open only for this edit window. Test contract presence and producer propagation, not reviewer adherence. | Seed/surface inventory; coordinator release. |
| 2026-09-22 | Observe: six seed edits complete; seed gate closed before surface work. Rewritten seed pointer pin, seed-209 historical anchors and real-render host-neutral orchestration controls pass (7 tests). No claim of reviewer adherence. | `test_docs_lint.ReviewCycleChurnControlPinTests` two seed methods; `test_render_agent_surfaces.HostNeutralOrchestrationCarrierTests`. |
| 2026-09-22 | Observe: source implementation frozen after 258 focused passes, 11 wording rechecks and three killed real-render template mutants. Final surface sync reported no writes; authored marker bytes and manifest preserved. Naming/duplication census and measured entry sizes recorded. Full suite and independent delivery remain pending. | `seed-surface-inventory.md` Executed verification and census; `test_fresh_review_template_contract_and_known_bad_controls`. |
| 2026-09-22 | Planned from the Review wave and implementation-review prompt reviews; dependency on `1ypy6` declared. | Coordinator reads. |
| 2026-09-22 | Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): the Typed authoring shrink would have deleted the writing-hand sentence `1ypy6` adds, so the removed sentences are enumerated and everything else kept; the mutation-table cut is pinned by a `1wuju` seed test now named and rewritten; `tree_fingerprint` is already a required packet field; the `agent-team-workflow.md` reference is an expected carrier in seven seeds and the item is withdrawn; "exceptional" has three sites and the Review-wave statement one literal plus three paraphrases; seed 212's opening and the tool-posture lines are recorded in the census predicate; the de-localization rules are stated. | Readiness review in this wave directory. |

| 2026-09-22 | Repair C-2: canonical full suite found the old exactly-five QA condition pin. Updated it for the admitted conditional sixth rule, preserving the original five rules and adding a conditionality assertion. Companion renderer census removes only the now-stale allowlist entry; its historical SITES row remains with a retirement note. Eight affected tests pass; fresh QA reverification and full-suite rerun pending. | `evidence/delivery-qa-c2.md`; AC-1. |

| 2026-09-22 | Observe: implementation and delivery review complete; all ACs/tasks checked, C-1/C-2 terminal, four current delivery lane approvals, green current 9,533-test receipt and stable passing before/after retrieval comparison. Both edit gates closed. Wave remains open for operator closure; no commit performed. | `delivery-review.md` and typed review ledger. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-22 | Depend on `1ypy6` rather than merge into it. | Two waves editing seeds 180 and 209 concurrently would collide in two paragraphs; `1ypy6` is readied and its sentences are fixed. | Fold into `1ypy6`; operator chose to keep that wave at three changes. |
| 2026-09-22 | No delivery-round bound. | Delivery's open repair loop surfaced a BOM defect and two stale censuses after first approvals. | Mirror the readiness bound; rejected. |
| 2026-09-22 | Mutation table has one owner, seed 209; the `1wuju` seed pin is rewritten, not deleted. | Three byte-identical copies drift independently; the pin still proves the pointer and the budget clause are present. | Keep copies; rejected. |
| 2026-09-22 | Withdraw the `agent-team-workflow.md` removal. | Ten other seeds and seed 160's backfill treat the file as an expected carrier; the "never provisioned" predicate was half true. | Remove from every seed; out of scope and unproven. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A seed 209 anchor moves when `1ypy6` lands. | The inventory re-verifies every anchor after `1ypy6` closes; the change opens only then. |
| A de-localized passage loses its rule. | Requirement 6 names the rule each passage must keep; the docs-contract lane checks it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
