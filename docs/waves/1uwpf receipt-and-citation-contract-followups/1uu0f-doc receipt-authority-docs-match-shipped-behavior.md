# Receipt-Authority Documentation No Longer Matches Shipped Behavior

Change ID: `1uu0f-doc receipt-authority-docs-match-shipped-behavior`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-09
Wave: 1uwpf receipt-and-citation-contract-followups

## Rationale

Two documents assert things about review-policy receipt authority that the code no longer does. Both were found by delivery-review lanes during wave `1usqm` and deliberately deferred rather than folded, because repairing them was outside that wave's declared scope.

**Seed `007-review-system-overview.md` states a closure rule the shipped predicate only approximates.** Its `transition_policy` bullet says closure "does not retroactively require a missing readiness signoff for a wave that never re-entered `Prepare wave`". Wave `1usqm` changed `_required_wave_council_signoffs` to key its close carve-out on `current_policy_receipt(authority.records) is None and not authority.ledger_errors` — a far better encoding than the approval-absence check it replaced, which produced an inversion where refusing a stale approval *weakened* the close gate. But it is not exact, because **`wf_mark_ac(state='~')` is a second receipt writer**. The architecture lane executed the counterexample on a declared wave that had never been prepared:

```
close roster BEFORE mark_ac: ['wave-council-delivery']
mark_ac status: ok
close roster AFTER  mark_ac: ['wave-council-readiness', 'wave-council-delivery']
```

One AC deferral mints from an empty ledger and re-arms the readiness key on a wave that never entered Prepare. `1usqm` withdrew its claim that receipt presence encodes the rule "faithfully" and recorded the discrepancy; this change reconciles the documented rule to what the code actually implements, so the seed stops describing a behavior no predicate provides.

**`docs/architecture/data-and-control-flow.md` carries three drifts**, all verified against the current tree:

| Claim | Reality |
|---|---|
| "Prepare is the sole writer of the generated review roster and the append-only…" | `_mark_change_item_response`'s `refresh_receipt` path publishes roster and receipt through the same publisher prepare uses |
| "Evaluator version 2 makes that boundary…" | `REVIEW_POLICY_EVALUATOR_VERSION` is `7` |
| "Exactly 18 retrieval/navigation tools attach `context_avoided`" and enumerates 18 | `_CONTEXT_RETRIEVAL_TOOLS` has **20** members; `code_hover` and `code_risk_score` are in the frozenset and absent from the enumeration |

**A fourth claim was asserted as a drift and is NOT one — withdrawn before implementation.** An earlier revision of this plan listed "normalizes five narrow regions to stable sentinels" as drifted, on the ground that `canonical_review_policy_body` composes six normalizer calls. Both readiness seats independently falsified it. The document reads "**first stabilizes carriers** … **then normalizes five narrow regions**", and the function's own docstring reads "Carrier stabilization … followed by **five narrow section normalizations**". `normalize_carriers` is the carrier step, described separately in the preceding clause; the remaining five match one-for-one. Implementing the withdrawn claim would have converted a correct sentence into a wrong one and contradicted the function's docstring. It is recorded rather than deleted because it is the exact failure mode this plan exists to correct, committed by the plan itself.

The sole-writer drift is the one that matters most, and its status changed during `1usqm`. It was cosmetic when recorded; it is now **contract-relevant**, because that second writer is precisely why the new close predicate mis-encodes seed 007. A reader reasoning about the close gate from this document reaches the wrong conclusion.

## Requirements

1. **Seed 007's closure bullet states the rule the code implements — all three conjuncts.** `_required_wave_council_signoffs` gates the close carve-out on **three** conditions, and an earlier revision of this requirement named only two, which would have installed a second not-quite-right rule:

   ```python
   if prepare_signoff_recorded:
       return required
   never_prepared_under_policy = (
       current_policy_receipt(authority.records) is None
       and not authority.ledger_errors
   )
   ```

   The carve-out therefore applies only to a wave that has **never recorded a readiness approval**, has **no published review-policy receipt**, and whose **ledger is readable**. The bullet names `wf_mark_ac(state='~')` as a second way a wave becomes governed, with the caveat that it publishes only when the wave uses external review evidence and `wave_review` config is present — so the second-writer path does not reach legacy prose waves.

   The replacement sentence is supplied rather than described, because the property this requirement previously supplied was itself incomplete:

   > Closure does not retroactively require a readiness signoff for a wave that has never recorded one, carries no published review-policy receipt, and whose event ledger is readable. A wave becomes governed by publishing a receipt — normally at `Prepare wave`, but also through `wf_mark_ac(state='~')` on a wave that uses external review evidence with `wave_review` configured, which publishes a receipt from an empty ledger.

2. **The architecture doc's three drifts are repaired.** The sole-writer sentence names both writers; the evaluator-version claim matches the constant; the "Exactly 18" tool count matches `_CONTEXT_RETRIEVAL_TOOLS` and its enumeration lists every member. Each is stated so it does not go stale on the next change — prefer naming the constant or the frozenset over restating a value or a count where the sentence allows, because two of these three drifted precisely by hardcoding a number.

3. **No behavior changes.** This is documentation reconciliation only. The close predicate, the canonicalizer and the evaluator version all stay exactly as `1usqm` shipped them. If reconciling the wording surfaces a case where the code is wrong rather than the doc, that is a finding for a separate change, recorded here and not fixed.

4. **The seed edit is a framework change with target-repo reach.** Seed 007 ships to every target repository, so the edit goes through the `seed_edit_allowed` gate and the change discloses that installed repositories see the corrected rule only after their next upgrade.

## Scope

**Problem statement:** Two documents describe receipt authority as it was before wave `1usqm`, and one of those descriptions is now load-bearing for reasoning about a gate that behaves differently.

**In scope:**

- `.wavefoundry/framework/seeds/007-review-system-overview.md`, the `transition_policy` closure bullet.
- `docs/architecture/data-and-control-flow.md`, the three drifted claims.

**Out of scope:**

- Changing the close predicate, the canonicalizer, or the evaluator version. `1usqm` shipped those and the delivery lanes verified them.
- Making `wf_mark_ac` stop writing receipts. Its write is correct; `1usqm` Requirement 6 froze the publication path deliberately and that boundary stands.
- The framework scripts this change reads to verify what the documents should say. It edits none of them; they are deliberately absent from `## Serialization Points`, and naming them there — even to say they are undeclared — makes the legacy whole-section scan recruit a lane the strict extractor does not, which breaks the corpus no-lane-lost invariant.
- Drifts the AC-5 census finds **outside** `data-and-control-flow.md` and seed 007. Those are surfaced as findings with their disposition recorded, not repaired here. Note this boundary is drawn after the census rather than before it — drawing it first is what hid the "Exactly 18" drift.

## Acceptance Criteria

- [x] AC-1: Seed 007's closure bullet describes the shipped carve-out (no published receipt, readable ledger) rather than "never re-entered `Prepare wave`", and names `wf_mark_ac(state='~')` as a second path to becoming governed.
- [x] AC-2: The sole-writer sentence in `docs/architecture/data-and-control-flow.md` names both writers. Verified by reading, and by confirming no other sentence in that document still asserts a single writer.
- [x] AC-3: The `context_avoided` tool claim matches `_CONTEXT_RETRIEVAL_TOOLS` — both the count and the enumeration, which currently omits `code_hover` and `code_risk_score`. Stated so a future addition to the frozenset does not silently re-drift it.
- [x] AC-4: The evaluator-version claim matches `REVIEW_POLICY_EVALUATOR_VERSION`. Stated so a future bump does not silently re-drift it — name the constant, or state the boundary without pinning a number.
- [x] AC-5: A census over **`data-and-control-flow.md` itself** enumerates every falsifiable claim it makes — counts, constants, "exactly N", and uniqueness assertions — and checks each against the code. The scope line is drawn AFTER that census, not before. An earlier revision censused only *other* documents, declared everything outside three named claims out of scope, and thereby missed the "Exactly 18" drift sitting in the same document. The census also covers other documents for the sole-writer and evaluator-version claims. If it finds a claim outside the declared targets, that is recorded in `## Progress Log` with its disposition — repaired here if within the declared targets, surfaced as a finding if not.
- [x] AC-7: No change **attributable to `1uu0f`** modifies any file under `.wavefoundry/framework/scripts/`. Verified by reading the script diff and attributing every hunk to a sibling change, **not** by a bare `git status`: `1uu9z` edits `server_impl.py` and `test_server_tools.py`; `1uu9y` AC-5 edits `_prepare_council_instructions` in the same file; and `render_agent_surfaces.py` carries one hunk from `1urlb` in the already-closed, still-uncommitted wave `1usqm` — the Claude subagent template's citation instruction. So file-level presence cannot attribute, and an earlier revision of this AC was unverifiable as written. The third file was omitted from this enumeration until a readiness seat named it; the substantive claim was unaffected, but an incomplete attribution list is the same defect class this wave exists to repair. This pins Requirement 3's no-behavior-change boundary, which was otherwise unpinned.
- [x] AC-8: The change discloses that installed repositories see the corrected seed 007 rule only at their next upgrade, and the seed edit is made under the `seed_edit_allowed` gate. This pins Requirement 4, which was otherwise pinned by a Task alone.
- [x] AC-6: The full framework suite and docs-lint pass. No test changes are expected; if any test asserts the old wording, that is a finding to surface rather than a fixture to edit.

## Tasks

- [x] Run the AC-5 census before editing, so the edit set is known rather than assumed.
- [x] Edit seed 007's closure bullet under the `seed_edit_allowed` gate; close the gate immediately after.
- [x] Repair the three claims in `docs/architecture/data-and-control-flow.md`.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | — | AC-5; establishes the real edit set |
| seed-007 | implementer | census | Requires `seed_edit_allowed`; ships to every target repo |
| architecture-doc | implementer | census | Three named claims only |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/007-review-system-overview.md`
- `docs/architecture/data-and-control-flow.md`


## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` is edited directly by this change — it is the subject, not a downstream consequence. No other architecture document is affected, which AC-5 verifies rather than assumes.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The documented rule and the shipped predicate describe different sets; a reader reasoning about closure from the seed is misled. |
| AC-2 | required | The sole-writer claim is now load-bearing for reasoning about the close gate, not cosmetic. |
| AC-3 | important | A real drift of the same shape the earlier revision missed while flagging a correct sentence. |
| AC-4 | important | Same. Worth fixing so the doc stops accumulating known-false statements. |
| AC-5 | required | Censusing only other documents is what let a drift in THIS document go unnamed while a correct sentence was flagged as drifted. |
| AC-7 | required | Requirement 3's boundary is the one thing separating a documentation change from a behavior change. |
| AC-8 | important | Framework-source edit with target-repo reach; the disclosure is the operator-facing half. |
| AC-6 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | AC-5 census executed over `data-and-control-flow.md` and recorded. It found ONE further drift of exactly the shape the plan exists to correct, in the declared target and therefore repaired here: "Five lifecycle tools record request/response debits" against `_LIFECYCLE_CONTEXT_STAGES`, which has SEVEN members -- the five milestones plus `wf_mark_ac` and `wf_mark_task`. The five-item list in the same sentence is the prompt-CREDIT milestone set, which is why the number looked right. Now names the constant rather than a count, per Requirement 2 | constant read directly: 7 members; "six lifecycle prompt baselines" checked in the same pass and is CORRECT |
| 2026-08-10 | The State Ownership row for `events.jsonl` carried the same sole-writer premise as the prose and was repaired with it: its Written By set listed only `wf_create_wave` and `wf_review_event`, omitting both receipt writers. Verified precisely rather than assumed -- `_mark_change_item_response` publishes only when `state == '~'` AND the section is Acceptance Criteria AND the wave uses external review evidence AND `wave_review` is configured, so `wf_mark_task` is receipt-neutral and the row now says so | read the `refresh_receipt` condition directly |
| 2026-08-10 | Sole-writer premise found in THREE documents outside the declared targets. Per the Scope boundary these are recorded as findings, NOT repaired here: `docs/architecture/decisions/1tsbu-adr review-policy-and-upgrade-protocol.md` ("Prepare alone derives the ordered specialist roster and appends a parent-bound `review_policy_receipt`"), `docs/specs/mcp-tool-surface.md` ("Prepare alone may append a parent-bound `review_policy_receipt`"), and `docs/contributing/review-and-evals.md` ("Prepare is the sole policy authority"). The ADR is the load-bearing one. `docs/waves/1tuoc .../1tsbu-enh` carries it too and is a closed-wave archive, so it stays as history | repo-wide grep, each hit read in context |
| 2026-08-10 | AC-2's "no other sentence in that document" conjunct verified rather than assumed. Two other `sole`-bearing sentences exist in the document; both assert `events.jsonl` is the sole machine AUTHORITY for review evidence, which is a different and correct claim, not a second sole-WRITER assertion | grep for sole/alone/only-writer intersected with prepare/receipt/roster |
| 2026-08-10 | AC-7 was unverifiable as written and is restated. It required `git status` to show no file under `.wavefoundry/framework/scripts/` modified, but `1uu9z` edits `server_impl.py` and `test_server_tools.py` and `1uu9y` AC-5 edits the same file, all in this wave -- file-level presence cannot attribute. Now verified by attributing every script hunk to a sibling change, and confirmed by content: zero changed lines touching `REVIEW_POLICY_EVALUATOR_VERSION`, `canonical_review_policy_body`, `_CONTEXT_RETRIEVAL_TOOLS`, or `_LIFECYCLE_CONTEXT_STAGES` | per-symbol diff census over the script tree |
| 2026-08-09 | READINESS COUNCIL, both seats independently FALSIFIED a claim this plan asserted as verified fact. "Five narrow regions" is NOT a drift: the document reads "first stabilizes carriers ... then normalizes five narrow regions", and `canonical_review_policy_body`'s own docstring reads "Carrier stabilization ... followed by five narrow section normalizations". `normalize_carriers` is the carrier step, excluded by the doc's own clause; the remaining five match one-for-one. Implementing AC-3 as written would have converted a CORRECT sentence into a wrong one and contradicted the function's docstring. Withdrawn, and recorded rather than deleted because this plan committed the exact failure it exists to correct | both seats, function docstring read directly |
| 2026-08-09 | RED-TEAM P1: a REAL fourth drift of the same shape was sitting unnamed in the same document while the plan flagged a correct one. `data-and-control-flow.md` says "Exactly 18 retrieval/navigation tools attach `context_avoided`" and enumerates 18; `_CONTEXT_RETRIEVAL_TOOLS` has 20, with `code_hover` and `code_risk_score` absent from the enumeration. The plan had drawn its scope line BEFORE censusing the document, which is what hid it. AC-5 now censuses this document first and the scope line is drawn after | re-derived by parsing the frozenset: 20 vs 18 |
| 2026-08-09 | DOCS-CONTRACT P2: Requirement 1's replacement rule was itself an incomplete encoding of the shipped predicate. `_required_wave_council_signoffs` gates on THREE conditions and the requirement named two, omitting the `prepare_signoff_recorded` early return — so a wave carrying a readiness approval but no receipt would have wrongly qualified. Writing it as stated would have installed a second not-quite-right rule in seed 007, which is the failure this change exists to end. All three conjuncts now stated, and the exact replacement sentence supplied rather than described | docs-contract seat read the predicate |
| 2026-08-09 | Two orphan Requirements pinned: Requirement 3's no-behavior-change boundary (AC-7, `git status` over `.wavefoundry/framework/scripts/`) and Requirement 4's gate-plus-upgrade-latency disclosure (AC-8). For a framework-source edit with target-repo reach, the disclosure was the one thing worth pinning and had only a Task behind it | docs-contract coverage trace |
| 2026-08-09 | Split out of wave `1usqm` at operator direction. Both drifts were found by delivery-review lanes there and deliberately deferred: `1upba` declared the architecture doc for READING and recorded its drifts without repairing them, and the seed 007 discrepancy surfaced only when the architecture lane executed the `wf_mark_ac` counterexample against the new close predicate | `1usqm` architecture lane |
| 2026-08-09 | Every claim in this plan verified against the tree before it was written, rather than carried from the lane reports: seed 007's bullet, the three architecture-doc claims, and the normalizer set. Two corrections resulted — the doc says "five narrow regions" while `canonical_review_policy_body` now composes SIX normalizers, and the earlier note recorded the understatement without the number | direct read of both documents and `gardener_metadata.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-09 | Withdraw the "five narrow regions" drift rather than soften it | Both seats falsified it independently against the function's own docstring. A plan whose subject is documents asserting things the code does not do cannot itself assert a drift the code does not have; withdrawing outright is the only disposition consistent with its own thesis | Reword AC-3 to "verify the count either way" (rejected: launders a false claim into a verification task and leaves the wrong number reachable) |
| 2026-08-09 | Reconcile the documentation to the code, not the code to the documentation | The shipped predicate is a genuine improvement over what it replaced and was verified by four delivery lanes; the gap is that seed 007 describes a rule no predicate provides. Tightening the predicate to match the prose would mean re-opening a close-gate behavior that took a full wave to get right | Change the predicate to exclude `wf_mark_ac`-minted receipts (rejected: re-opens verified behavior for a wording problem, and would grant the carve-out to waves that carry a published roster and a receipt minted from current policy — treating a governed wave as ungoverned, which is fail-OPEN. An earlier revision stated this as "stranding" such waves, which is inverted: treating those receipts as absent makes the carve-out fire and close EASIER, not harder. It would also require receipt provenance, a field that does not exist) |
| 2026-08-09 | Keep this separate from `1uugh advisory-diagnostic-severity` | `1uugh` is scoped to diagnostic classification and its Requirement 8 forbids widening. Admitting documentation reconciliation would move its canonical text, supersede its receipt, and re-open a readiness cycle that took four review rounds to settle | Fold into `1uugh` (rejected on scope and on readiness cost) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The reconciled seed text ships a rule that is itself wrong | Requirement 3 says that if reconciling surfaces a code defect rather than a doc defect, it is recorded as a finding rather than repaired here |
| A third instance of the same drift class is found later | AC-5 requires the census before editing rather than after |
| The evaluator-version claim re-drifts on the next bump | AC-4 requires the sentence be written so a bump does not silently falsify it |
| Target repositories keep the old rule | Requirement 4 discloses that installed repos see the correction only at their next upgrade |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
