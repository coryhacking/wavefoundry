# Implement Wave Tool Gaps

Change ID: `1ypy4-bug implement-wave-tool-gaps`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-21
Wave: `1ypy6 implement-prompt-efficiency`

## Rationale

Three defects in the tools behind **Implement wave** and the review ledger were identified by the independent prompt review (2026-09-21) and confirmed by the readiness lanes as tooling gaps that prose has been papering over. All three are GENERIC and reach every target with the next framework upgrade.

1. `wf_implement_wave_response` derives each change's `depends_on` and the `serialization_points` list with `re.findall(r"Depends On:\s*`([^`]+)`", ct)` over the CHANGE DOC text. That line form is real: `DEPENDS_ON_LINE_PATTERN` in `wave_lint_lib/constants.py` and the lint checks in `wave_validators.py` already validate a `Depends On:` line with backticked ids inside each change's block of the WAVE RECORD's `## Changes` section (wave `1293d` uses it), but the plan template never emits it in a change doc, so on every wave in this repository the tool finds nothing and returns no serialization point. The tool reads the wrong document. Readiness rejected the first draft's plan to add parsers for the execution-graph table (its `Depends On` column names workstreams by construction) and for `## Dependencies` prose (no grammar); the fix is to read what lint already validates.
2. The ledger validator catches a reverification that shares its own finding's `repair_start` context while declaring `fresh_context=true` (`_reverification_independence_defect` in `review_evidence.py`, applied at the append boundary inside `build_compact_review_event` and at close inside `repair_independence_violations`), and nothing else. A context that recorded implementation work for one finding can approve a lane or reverify a different finding as fresh. Readiness established what the ledger CAN decide: a context that authored any `repair_start` row is not fresh for anything later. It also established what it cannot: the wave `1ymzk` shape (one reviewer context filing findings, then reverifying them, then approving) is the same shape wave `1y0h2` and `1yj14` closed with under the readiness rule "re-run only blocking lanes on their own findings", and one context recording several lanes' approvals in one council round is the shipped protocol. Those are declared-honesty cases under seed 209, so this change makes them visible, not refused.
3. `wf_implement_wave` on a successful create returns `next_tools=["wf_current_wave", "wf_review_wave"]`; the typed checkbox tools are not offered at the moment they apply, and eight prose statements of the real-time rule did not prevent end-of-wave bookkeeping.

## Requirements

1. Dependency source. `wf_implement_wave_response` derives `ordered_changes` order from the wave record's `## Changes` block order (admission order, which `wf_add_change` preserves; this is what `_extract_change_ids_from_wave_text` already returns) and each change's `depends_on` from the lint-validated `Depends On:` line inside that change's block in the wave record, resolving backticked tokens against admitted ids by exact id only, because lint resolves that line by exact id and rejects a prefix as an unknown change id. The existing change-doc backtick form stays accepted as a secondary source and keeps its prefix tolerance. `wf_add_change` writes no `Depends On:` line, so fixtures author it after admission, as this wave's own record does. No execution-graph table or `## Dependencies` prose is parsed. `serialization_points` keeps its current shape (a list of admitted change ids that something depends on). A dependency naming an id outside the wave is reported by attaching `_diagnostic(..., advisory=True)` to the SUCCESS envelope (the gate branch returns `error` whenever `diagnostics` is non-empty, so the advisory must not join that list). The `## Dependencies` scaffold bullet written by `wf_create_wave` gains one sentence telling authors to declare intra-wave order with the `Depends On:` line in the change's block; the matching seed 110 sentence (the seed that owns the wave-record dependency grammar) is owned by the sibling `1yobp`.
2. Retained-context audit. `review_evidence.py` gains a check applied wherever `_reverification_independence_defect` is applied, and additionally to the approval branch: a reverification or approval declaring `fresh_context=true` whose `context_id` equals the `context_id` of ANY earlier `repair_start` row in the same wave (any finding, any cycle) is a defect with the new code `review_context_retained`, added to `INDEPENDENCE_DIAGNOSTIC_CODES` so the write path surfaces it as a refusal in `create` and a diagnostic in `dry_run` (it lives inside `build_compact_review_event`; `_identified_review_event_bundle` in `server_impl.py` decides replay before the builder runs, so identical retries replay untouched). A `repair_start` run row carries no context of its own; the context is read from its evidence row the way `_resolving_repair_start_context` already does. The defect is also surfaced by `repair_independence_violations` at close (consumed through both call sites: the `lifecycle_gates.py` facade and `wf_close_wave_response`), and as a new advisory surface in `wf_review_wave(phase='delivery')`, following the non-blocking pattern `retrieval_posture_gap` already uses there. A scan of the eight most recent ledgers finds no row the predicate would have flagged, so its only known-bad at delivery is the fixture it ships with; it is a decidable contradiction guard, not a detector of the declared shapes. Rows declaring `fresh_context=false` are not flagged. Batch approvals from one context, a lane reverifying its own finding, and currency re-approvals after a receipt rotation stay legal. The refusal names the earlier `repair_start` record id. Supersession: the ledger is append-only, so a flagged row must not block close forever once a valid replacement exists. The close audit and the delivery advisory apply the predicate only to rows that are currently authoritative: the terminal reverification of each finding chain (the currency `repair_independence_violations` already uses) and the current approval per signoff key and phase (the currency `signoff_current` already uses); a flagged row that a later valid fresh-context row has superseded is reported as history in `context_summary`, not as a blocker. The append-boundary refusal is unaffected (it judges the row being written). The seed 209 sentence enumerating enforced codes is owned by `1yobp`.
3. Visibility for the declared cases. The ledger `list` view (`_review_evidence_list_response`) gains `context_summary`: one row per `context_id` with row count, distinct actors, first and last `claim_kind` or `run_kind`, and whether the context authored a finding, a `repair_start`, a reverification or an approval. This is where the `1ymzk` shape (finding, then reverification, then approval from one context) becomes visible without a trust assumption; the change doc states that it is not refused.
4. Next tools. The successful `create` branch of `wf_implement_wave_response` returns `next_tools=["wf_mark_ac", "wf_mark_task", "wf_review_wave", "wf_current_wave"]` with a usage hint stating the mark tools need the FULL change id as listed in `ordered_changes[].change_id` (no prefix resolution).
5. Existing ledgers. Sealed and closed archives are never retroactively invalidated (the `1tmb2` rule). Wave `1ymzk` is closed (`4a8b8951`); a census over the live ledgers at implementation time records which, if any, carry a row the new predicate flags, and the inventory states it.
6. Tests. Dependency fixtures are produced through `wf_create_wave` and `wf_add_change` scaffolds from real change docs in this repository (never hand-shaped), with known-bads: a Notes-column backtick span is not a dependency, a workstream name is not a dependency, an out-of-wave id yields the advisory, the legacy change-doc form still parses with its prefix tolerance, and a prefix in the wave-record line is NOT a dependency (it yields the advisory, because the authoritative record uses exact ids and lint rejects a prefix there). A ledger fixture written through the canonical `wf_review_event` writer: `repair_start` for finding A in context B, then an approval and a reverification of finding C from context B with `fresh_context=true`, flagged by the new code and not by the old validator (to plant the known-bad chain for the close audit after the guard lands, use the string-name patch pattern already used in `test_review_evidence.py` for `_reverification_independence_defect`); the reverification row with `fresh_context=false` is not flagged (a specialist approval cannot declare `fresh_context=false`, since the builder already rejects that upstream, so there is no approval twin). A `context_summary` assertion on a two-row-one-context fixture. Supersession regressions: a flagged approval followed by a valid fresh-context approval for the same key and phase no longer blocks close and the flagged row shows as history; a flagged terminal reverification replaced by a later valid one clears the chain; event ordering (the replacement recorded before the flagged row does not count as superseding it); and a receipt rotation with readiness approvals re-recorded against the new receipt keeps the audit's verdict unchanged. A `next_tools` assertion on the create branch. The golden tool-surface fixture is unchanged (no signature change). `fixtures/lifecycle-gate-golden.json` does not capture the implement envelope but does capture the delivery-review and close envelopes this change touches, so nothing unconditional (an empty advisory list, an always-present key) is added to those envelopes; the advisory and the audit result appear only when they fire.

## Scope

**Problem statement:** the implement tool reads dependencies from the wrong document, the ledger validator cannot see a context that did implementation work approving elsewhere, and the tool does not offer the mark tools when they apply.

**In scope:** `wf_implement_wave_response`, the `## Dependencies` scaffold sentence, `review_evidence.py` independence audit and its surfaces in `wf_review_event`, `wf_review_wave` and both close call sites, the list-view `context_summary`, tests, CHANGELOG bullet, the review-history architecture sentence.

**Out of scope:** any change to the review-policy digest, receipt rotation, the readiness rule or the approval schema; parsers for the execution-graph table or `## Dependencies` prose; seeds (sibling enhancement); prompt text (sibling documentation change); a heuristic for suffixed or reused context ids beyond the `repair_start` predicate.

## Acceptance Criteria

- [x] AC-1: `wf_implement_wave` derives `ordered_changes` from admission order and `depends_on` from the wave record's `Depends On:` lines by exact id (the authoritative form), keeps the legacy change-doc form with its prefix tolerance as the only compatibility path, and attaches an advisory for out-of-wave or prefix tokens in the wave record on the success envelope; the fixture known-bads all fail on a reverted parser.
- [x] AC-2: A `fresh_context=true` reverification or approval whose context authored any earlier `repair_start` is refused on `create` with `review_context_retained`, flagged on `dry_run`, and reported by the close audit through both call sites and by `wf_review_wave(phase='delivery')` only while it is the currently authoritative row for its chain or signoff; a superseding valid row clears it and the supersession, ordering and receipt-rotation regressions pass; the `fresh_context=false` reverification twin is not flagged; batch approvals and own-finding reverification pass; sealed archives are untouched.
- [x] AC-3: `context_summary` in the list view reports per-context rows, actors and first and last kinds, asserted on a two-row-one-context fixture.
- [x] AC-4: The successful create branch offers `wf_mark_ac` and `wf_mark_task` with the full-id usage hint.
- [x] AC-5: Framework suite green, golden tool-surface fixture unchanged, lifecycle envelope golden unchanged because nothing unconditional joins the delivery-review or close envelopes, docs gate clean.

## Tasks

- [x] Inventory: the parse site and its consumers, every caller of `_reverification_independence_defect`, both close call sites, the replay decision point, the live-ledger census for the new predicate.
- [x] Implement the wave-record dependency source, the scaffold sentence and the advisory; fixtures through the canonical scaffolds.
- [x] Implement `review_context_retained` at the append boundary, the close audit and the delivery advisory; add `context_summary`.
- [x] Update `next_tools`; add the assertions.
- [x] CHANGELOG bullet; architecture sentences; framework suite; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| tool-inventory | implementer | — | Committed before edits. |
| tool-fixes | implementer | tool-inventory | One owner for `server_impl.py` and `review_evidence.py`. |
| independent-review | required reviewers | tool-fixes | Fresh contexts; the two ledger fixtures are the known-bads. |

## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_gates.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_golden.py`
- `.wavefoundry/framework/scripts/tests/test_record_layout_lifecycle.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` ("Review history and current state"): one sentence that the independence audit also refuses a fresh-declared reverification or approval from any context that authored a `repair_start`, and that batch and own-finding shapes stay declared. `docs/architecture/testing-architecture.md` (review-protocol propagation row): one clause naming the retained-context fixture family. `cross-cutting-concerns.md` has no review-evidence section and is not edited.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The prompt instruction has no backing tool today. |
| AC-2 | required | The one decidable independence contradiction the ledger does not check. |
| AC-3 | important | Visibility for the declared cases; no gate depends on it. |
| AC-4 | important | Salience; the typed path offered at the moment it applies. |
| AC-5 | required | Change-local correctness. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Planned from the independent Implement wave prompt review; the regex, the validator and the `next_tools` list verified against `server_impl.py` and `review_evidence.py`. | Coordinator reads. |
| 2026-09-21 | Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): the first-draft predicate ("any earlier row") would have refused the second lane approval of every council round and every currency refresh, and would have failed this wave's own close; narrowed to any earlier `repair_start` context, with the finding-then-approve shape made visible instead. The table and prose parsers were dropped for the lint-validated wave-record line the tool never read. Added: advisory on the success envelope, replay placement, both close call sites, the lifecycle envelope golden, the `context_summary` schema, the full-id usage hint, the correct architecture doc. | Readiness review in this wave directory. |
| 2026-09-22 | Operator contract review (independent architecture and security reviews in the operator's session): the wave-record dependency line is exact-id everywhere the plan mentions it, with prefix tolerance confined to the legacy change-doc form; the retained-context audit judges only currently authoritative rows at close so a superseded flagged row cannot block an append-only ledger, with replacement, ordering and receipt-rotation regressions named. | Operator review message; `repair_independence_violations` terminal-chain currency; `signoff_current`. |

| 2026-09-22 | Readback: dependency parsing reads exact wave-record ids and only anchored legacy declarations; retained repair contexts cannot claim fresh review; current authority can supersede invalid historical rows; list visibility and mark-tool hints are additive. Before: this wave returns prose as dependencies; after: its two declared edges resolve exactly. Affected: server_impl.py, review_evidence.py and named tests. Thought: inventory producer/consumer seams and capture the required stable before receipt before source edits. | Current prepare/activation passed; fresh focused review approved. |

| 2026-09-22 | Observe / Reflect: full-suite advisory census detected the two admitted sites missing from its strict expected set (QA-DEL-1). Recorded repair start, added only those exact triples; independent QA reverified and killed both tuple-removal and extra-site controls. Keep exact site censuses in the changed-contract inventory. | delivery-review.md; typed cycle1; WaveCouncilPolicyTests.test_advisory_tags_appear_only_at_the_sanctioned_sites. |

| 2026-09-22 | Delivery complete: all required lanes approved, 9,522-test full suite green/current, docs lint clean, retrieval after receipt passes against before with no violations or invalidation. Wave remains open pending operator close. | delivery-review.md; events.jsonl; before/after retrieval receipts. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Predicate: any earlier `repair_start` context. | Decidable from the ledger; keeps the shipped multi-lane and own-finding shapes legal; extends the existing chain-anchored rule from "own repair_start" to "any". | Any earlier row (first draft): refuses the protocol. Finding-authoring contexts: not decidable without a trust assumption; made visible instead. |
| 2026-09-21 | Read the wave record's validated `Depends On:` line; drop the table and prose parsers. | Lint already validates that line; the table names workstreams; prose has no grammar. | Three parsers (first draft). |
| 2026-09-21 | Refuse on create, flag on dry run, new advisory in delivery review. | Create and dry-run match how the existing independence defect is surfaced; the delivery advisory is a new surface so the contradiction is visible before close. | Advisory only. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A live open ledger carries a flagged row and its close fails. | The inventory census names it before the change lands; sealed archives are exempt. |
| A prefix appears in a legacy change-doc `Depends On:` line and matches two admitted ids. | Exact id wins; an ambiguous prefix yields the advisory, not a dependency; the wave-record line is exact-id only. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
