# The Symbol-Anchor Citation Rule Never Reached Review-Evidence Authoring

Change ID: `1uu9y-doc citation-rule-reaches-review-evidence-authoring`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-09
Wave: 1uwpf receipt-and-citation-contract-followups

## Rationale

Wave `1usqm`'s change `1urlb` stated a rule: authored artifacts cite a **resolvable anchor** — a function, class, method, constant, test name, or distinguishing expression — rather than a bare `file:line`, because a symbol resolves with `code_definition` and `code_read` while a line anchor can only be re-checked. Its Requirement 1 named four artifact classes: change docs, wave records, **review evidence**, and agent answers.

Three of those four landed. **Review evidence did not**, and this was found during that wave's own readiness council rather than after it.

The rule shipped into `170-plan-feature.prompt.md` (change-doc authoring), `180-implement-feature.prompt.md` (implementation-time citations) and `211-guru.prompt.md` (Q&A answers). But a census across all seeds — run by the docs-contract seat and re-verified for this plan — places the review-evidence contract elsewhere: `209-agent-harness-core.prompt.md` is the **only** seed containing `artifact_or_test_id`, the evidence field a reviewer fills when recording a finding or an approval. None of the three edited seeds governs it.

`1urlb` recorded this honestly rather than papering over it, adding an explicit out-of-scope bullet, and shipped with one of its four artifact classes unaddressed.

**`237-council-review.prompt.md` is the second half.** Its Verify-code-grounded bullet reads:

> cited `file:line` sites and symbols must resolve, "X already does Y" claims must hold in the code, and "no other caller/site" censuses must be complete.

`1urlb` decided this needed no edit, on the reasonable ground that the sentence names symbols and is a *verification* instruction rather than an authoring one, so it does not contradict the new rule. That reasoning holds as far as it goes. But 237 is where a council seat is told what to do, its only citation sentence leads with `file:line`, and `1urlb`'s own Requirement 1 asks for the rule to be stated "where authors and reviewers will meet it". "Does not contradict" is weaker than that.

The cost is measurable rather than theoretical. Across wave `1usqm`'s six review rounds, lanes repeatedly cited by line into files under concurrent edit, and several citations went stale mid-review — including, pointedly, `1urlb`'s own Serialization Points block, whose `guru.md` line anchors drifted because `1urlb`'s edits moved them.

## Requirements

1. **The rule reaches review-evidence authoring.** `209-agent-harness-core.prompt.md`'s Executable Evidence Record guidance states that `artifact_or_test_id` and evidence prose cite a resolvable anchor, with the same carve-outs the other three seeds carry. State it at a named insertion point, not "somewhere in the evidence section".

2. **`237-council-review.prompt.md` states the rule for the findings a seat writes.** Its existing verification sentence is correct and stays — a reviewer checking a cited `file:line` must still resolve it, because plans legitimately contain line anchors under the carve-outs. What is added is the authoring direction: a finding a seat writes cites by symbol.

3. **The carve-outs travel with the rule, stated in each audience's own terms.** All five Requirement 2 cases from `1urlb` — module-level constant block, data file, generated artifact, prose in a hand-authored markdown document, deliberately historical — plus the obligation to name the case inline.

   **The historical case gets the audience's own referent, not seed 170's section names.** An earlier revision required both statements to name `## Progress Log` and `## Decision Log`; those are change-document sections, and neither audience writes one. A seed-209 evidence record lives in `events.jsonl`; a council seat authoring a finding under seed 237 writes neither. Seed 211 already set the precedent, folding them into "deliberately historical — which includes line numbers already written into a change document's `## Progress Log` or `## Decision Log` rows". So: for seed 209, that an appended evidence record is immutable and its anchors are never rewritten; for seed 237, seed 211's change-document framing.

4. **One canonical wording, not four paraphrases.** `1urlb` already established this and then had to defend it: a paraphrase is what produced its original AC-2 defect. Reuse the wording that shipped in seed 170 rather than re-deriving it.

5. **Consumer surfaces are named, not conditionally checked — and this plan already failed that once.** `1urlb` shipped believing the rendered wrappers needed no change, and two delivery lanes proved otherwise. An earlier revision of THIS plan then repeated the omission at two surfaces, both found at readiness:

   - **`docs/prompts/council-review.prompt.md`** carries seed 237's citation sentence **byte-identically** and is a registered renderer carrier in `REVIEW_POLICY_CARRIER_REGISTRY`. The plan said only "consumer surfaces of both, if any restate citation guidance" — a conditional where a named surface belonged.
   - **`_prepare_council_instructions`** in `server_impl.py` builds the runtime brief containing the same sentence, pinned exactly by `test_brief_code_grounded_sentence_is_pinned_exactly`. That is the text a seat actually reads at readiness — precisely the audience Requirement 2 targets — and a seeds-only census cannot see it.

   The runtime brief is **receipt-neutral**: `_prepare_policy_state` never reads `council_brief`, and `_bind_prepare_council_brief_to_receipt` only copies receipt into brief. Editing it lapses no readiness approval. The cost was never the fix; it was the scope.

   Seed 209's carrier `docs/contributing/review-and-evals.md` was checked and is clean — zero citation guidance, and its generated region points at seed 209 rather than restating it. It is named so the check is verifiable rather than assertable.

## Scope

**Problem statement:** The symbol-anchor rule names review evidence as an in-domain artifact class and then lands nowhere that governs it, so the reviewers who spend findings on citation drift are the one audience the rule never reached.

**In scope:**

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`: the evidence-record citation rule.
- `.wavefoundry/framework/seeds/237-council-review.prompt.md`: the authoring half, alongside the existing verification sentence.
- `docs/prompts/council-review.prompt.md`: seed 237's **rendered carrier**, which restates the Verify-code-grounded bullet verbatim and receives the same authoring addition.
- `.wavefoundry/framework/scripts/server_impl.py`: the **runtime** prepare-council brief in `_prepare_council_instructions`, which is the text a council seat actually receives at readiness.

**Out of scope:**

- Re-editing seeds 170, 180 or 211. They shipped in `1usqm` and were verified at five pinned sites plus a sixth found later; this change reuses their wording rather than revisiting it.
- Any mechanical gate. `1urlb` Requirement 5 declined a docs-lint rule because separating live claims from historical rows from legitimately line-anchored sites is a judgment call, and that reasoning is unchanged.
- Retrofitting existing review evidence. Recorded findings are history.

## Acceptance Criteria

- [x] AC-1: `209-agent-harness-core.prompt.md` states the resolvable-anchor rule as a new paragraph under `### Executable Evidence Record`, placed immediately **after** the paragraph beginning "The five `integrity_checks` booleans attest…" and **before** the paragraph beginning "Mandatory project orientation may disclose…". The point is named exactly rather than delegated: `artifact_or_test_id` occurs twice in that seed, once as a table row and once inside a dense paragraph, and neither can host prose "adjacent" — inserting between the field table and its explanation would separate them.
- [x] AC-2: `237-council-review.prompt.md` states the authoring direction for findings a seat writes. Its existing Verify-code-grounded sentence — "cited `file:line` sites and symbols must resolve…" — is **byte-unchanged**, verified by diff, because a reviewer must still resolve line anchors that plans carry legitimately.
- [x] AC-3: Both statements enumerate all five carve-outs and carry the name-the-case-inline obligation, with the deliberately-historical case stated in the audience's own terms per Requirement 3. Verified against the **canonical seed**, not the rendered artifact: `render_agent_surfaces.py` excludes `209-agent-harness-core.prompt.md` from full-body rendering and materializes a carrier stub pointing back at the seed, so reading the rendered file would not show the carve-outs at all.
- [x] AC-4: The rule text added to seeds 209 and 237 is lifted from seed 170's `### Citations in change docs anchor by symbol`, changing only the audience noun and the drift-mechanism sentence. A diff against seed 170 shows no other substantive change. **Divergence among seeds 170, 180 and 211 predates this change and is out of scope**, recorded rather than reconciled: seed 211 states a materially different rule ("lead with the symbol, and keep `path:start-end` as the locating aid" — requiring the range be kept), and seed 180 compresses the five-case table into prose. An earlier revision required no substantive divergence across all five seeds, which was unachievable without re-editing three seeds this change excludes.
- [x] AC-5: Every consumer surface is checked and the result recorded either way — `docs/prompts/council-review.prompt.md` (restates the sentence; updated), `_prepare_council_instructions` in `server_impl.py` (restates it in code; updated or explicitly exempted with a stated reason), `docs/contributing/review-and-evals.md` (checked clean), and `docs/specs/mcp-tool-surface.md` (restates the evidence field vocabulary; checked). A conditional "if any restate citation guidance" is what let two surfaces go unnamed.
- [x] AC-6: This change's own documents carry zero un-annotated line citations in live claims, counted with a detector that catches **both** the `file.md:NNN` and the prose `line NNN` forms. `1urlb`'s first count missed the second form and reported a false zero.
- [x] AC-7: The full framework suite and docs-lint pass.

## Tasks

- [x] Extract the canonical rule wording from seed 170 rather than re-deriving it.
- [x] Edit `209-agent-harness-core.prompt.md` under the `seed_edit_allowed` gate.
- [x] Edit `237-council-review.prompt.md` under the same gate, leaving its verification sentence byte-unchanged.
- [x] Check and update consumer surfaces; record the check either way.
- [x] Count live-claim line citations in this change's own documents, both notation forms.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| rule-text | implementer | — | Lift from seed 170; do not paraphrase |
| seed-edits | implementer | rule-text | Requires `seed_edit_allowed`; 237's verification sentence stays byte-identical |
| consumer-surfaces | implementer | seed-edits | `1urlb` shipped this wrong once; check rather than assume |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/237-council-review.prompt.md`
- `docs/prompts/council-review.prompt.md`
- `.wavefoundry/framework/scripts/server_impl.py`

## Affected Architecture Docs

`N/A` with rationale: this states authoring guidance in seed prompts. It moves no boundary, no data flow, and no test topology, and changes no evidence-record schema — only how the fields are filled.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The gap this change exists to close; without it review evidence stays the one unaddressed artifact class. |
| AC-2 | required | The negative half matters as much: deleting the verification sentence would tell reviewers to stop resolving line anchors that plans legitimately carry. |
| AC-3 | required | A partial restatement is how four statements of one rule drift apart. |
| AC-4 | important | Paraphrase is what produced `1urlb`'s original AC-2 defect. |
| AC-5 | required | `1urlb` shipped believing its wrappers were clean and two lanes proved otherwise. |
| AC-6 | important | Self-application, with the detector defect that produced a false zero last time explicitly named. |
| AC-7 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | AC-5's exemption for `_prepare_council_instructions` collapsed on inspection and the surface was updated instead. Three lanes converged on it. The exemption rested on two claims, both checked: the existing pin uses `assertIn` over a sentence ending "only against its own text", so appending after it preserves the pin; and `council_brief` appears in `_prepare_policy_state` exactly once, in the signature, never read. The brief is genuinely receipt-neutral, which made this a cheap fix rather than a legitimate exemption -- and it is the one surface a council seat actually receives at readiness | pin re-read; `policy_input_digest` signature takes no brief; dry-run prepare reports `receipt_append_required: False` |
| 2026-08-10 | AC-6 detector re-run after this session's edits and validated against six controls in BOTH polarities before trusting its zero. The earlier false zero came from a detector that matched nothing; a later attempt false-positived on "regenerated" containing "generated". Three positive controls fire, three negatives (carve-out named inline, symbol anchor, the "regenerated" case) do not | 0 un-annotated live-claim citations across all four wave documents |
| 2026-08-09 | DOCS-CONTRACT P1, and the sharpest finding of this round: THIS PLAN REPEATED THE DEFECT IT EXISTS TO FIX. It was written because `1urlb` shipped believing its consumer surfaces were clean, and it then said only "consumer surfaces of both, if any restate citation guidance" while two surfaces demonstrably restate the sentence — `docs/prompts/council-review.prompt.md`, a registered renderer carrier holding it byte-identically, and `_prepare_council_instructions` in `server_impl.py`, the runtime brief a seat actually receives at readiness and the exact audience Requirement 2 names. A conditional stood where two named surfaces belonged. Both now declared | seat verified both; I re-verified the carrier and located the runtime brief at the line-wrapped string in `_prepare_council_instructions` |
| 2026-08-09 | The runtime brief is receipt-neutral, which removes the obvious objection to editing it: `_prepare_policy_state` never reads `council_brief`, and `_bind_prepare_council_brief_to_receipt` only copies receipt into brief. Editing it lapses no readiness approval. The cost was never the fix, only the scope | docs-contract seat |
| 2026-08-09 | Three ACs were unachievable or wrong-method as written. AC-4 required no substantive divergence across all five seeds while Scope forbids re-editing three of them — and divergence already exists, since seed 211 states a materially different rule requiring the line range be KEPT. AC-3 said verify the RENDERED seed, but `render_agent_surfaces.py` excludes seed 209 from full-body rendering and emits a carrier stub, so the carve-outs would not appear there at all. AC-1 demanded "a named insertion point" without naming one, and `artifact_or_test_id` occurs twice in seed 209 with neither occurrence able to host adjacent prose | docs-contract seat, each verified against the seeds and the renderer |
| 2026-08-09 | Requirement 3 imported a change-document concept into audiences that have no such structure: it required both statements to name `## Progress Log` and `## Decision Log`, but a seed-209 evidence record lives in `events.jsonl` and a council finding has neither section. Restated in each audience's own terms, following the precedent seed 211 already set | docs-contract seat |
| 2026-08-09 | Split out of wave `1usqm`. `1urlb`'s readiness council found that its Requirement 1 named review evidence as an in-domain artifact class while none of its three edited seeds governs it; the change recorded an explicit out-of-scope bullet and shipped with that third unaddressed | `1usqm` docs-contract seat, 68-seed census |
| 2026-08-09 | Census re-verified for this plan rather than carried from the lane report: `209-agent-harness-core.prompt.md` is the ONLY seed containing `artifact_or_test_id`, and seed 237's citation sentence exists verbatim in its Verify-code-grounded bullet | direct read of both seeds |
| 2026-08-09 | Motivating cost recorded from the wave that produced it: across six review rounds in `1usqm`, citations drifted repeatedly under concurrent edit — including `1urlb`'s own `guru.md` line anchors, which its own edits moved. The rule demonstrated itself against its author | `1usqm` architecture lane |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-09 | Edit seed 237 after all, adding authoring direction beside the existing verification sentence | `1urlb` declined on non-contradiction grounds, which is true but weaker than its own Requirement 1 ("state the rule where authors and reviewers will meet it"). 237 is where a council seat is told what to do, and its only citation sentence leads with `file:line` | Leave 237 alone (rejected: it is the seat-facing surface and the rule's stated audience includes reviewers); rewrite the verification sentence (rejected: reviewers must still resolve legitimately line-anchored sites) |
| 2026-08-09 | Reuse seed 170's wording rather than writing per-audience text | `1urlb` established this and then had to defend it when a paraphrase produced its AC-2 defect. Four statements of one rule is already the drift surface; four independent wordings would be worse | Write each audience its own text (rejected: multiplies the drift surface for no benefit) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Seed 237's verification sentence is damaged while adding the authoring half | AC-2 requires it byte-unchanged, verified by diff |
| The four statements of the rule drift apart over time | AC-3 and AC-4 require full carve-outs and one canonical wording; the drift surface is acknowledged rather than denied |
| A consumer surface keeps the old rule | AC-5 requires the check and requires recording it either way; this failed once already in `1urlb` |
| The self-application count reports a false zero again | AC-6 names both notation forms explicitly, which is the defect that produced the false zero |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
