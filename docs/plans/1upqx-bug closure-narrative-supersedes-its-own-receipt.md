# Closure Narrative Supersedes Its Own Receipt

Change ID: `1upqx-bug closure-narrative-supersedes-its-own-receipt`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-08
Wave: [wave-id or TBD]

## Withdrawn At Readiness

Admitted to wave `1ur6o` on 2026-08-07 and withdrawn on 2026-08-08 after both prepare-council seats independently disproved the premise below. **The Rationale that follows is preserved as written, including its false claims, so the disproof stays legible.** Do not implement as written. Corrections:

1. **The premise is false on this tree.** This plan asserts that writing `## Completion Notes` is a closure step "as a matter of course". Verified: the heading appears in **zero** seeds, zero install lifecycle prompts, zero `docs/prompts/`, zero specs, and zero scripts, and it is in neither `docs/plans/plan-template.md` nor seed 170's required-section list. `wf_close_wave` writes only to `wave.md`, which is not digested. **On a stock repository, closing a wave produces zero change-doc digest churn.** The downstream report describes a locally-invented section.
2. **The cited precedent argues against the change.** Wave `1uhcb`'s test for granting a digest exclusion is: observed churn source, mandated by some surface, and gaining an explicit narrate-not-amend rule. Completion Notes scores none of the three, and `1uhcb` rejected `## Session Handoff` on weaker grounds.
3. **The proposed fix would not fix the reported shape.** This plan mandates the Progress Log's body-only sentinel substitution, which keeps the heading. Because the section is **created** at close rather than appended to, the heading still enters the canonical body and the digest still moves. AC-1 pins appending, the one shape that cannot occur while no template carries the section.
4. **Undeclared carrier.** `seeds/180-implement-feature.prompt.md:71` states Progress Log "is **the one** the review-policy digest excludes", a singular-exclusivity claim this change would falsify. Neither that seed nor `review_policy_reconcile.py`, the seam `1uhcb` used to reach existing repositories, is declared here.
5. **A third consumer was missed.** `canonical_review_policy_body` has three production call sites, not two; `server_impl.py:7119` feeds `extract_full_council_triggers`, and `delivery_council_required` is receipt-semantic, so excluding a section can flip a required delivery council from true to false.
6. **The 36-document word-boundary figure does not reproduce.** Independent runs gave 51, 23, or 0 depending on variant, and a left-boundary-only form drops zero lanes. The decision to reject word-boundary matching survives on stronger grounds, since it removes zero genuine false positives here, but the number must not be reused.

**If revived**, the defensible shapes are: route closure narrative to `## Wave Summary` in `wave.md`, already non-digested and already generated at close; or generalize to a declared exclusion set with a stated admission test rather than granting a permanent exception to a heading the framework does not define. The open question underneath, why narrative prose scores review lanes at all, needs its own wave and its own measurement.

## Rationale

Field report from a downstream repository closing a wave on 1.15.4. Closing took **three receipt re-mints** (`0e8ffde4` to `c6601c80` to `7a1189a8`), because writing the closure narrative into a change document supersedes the receipt that the closure is recording approvals against. Closing a wave invalidates its own approvals.

`canonical_review_policy_body` (`gardener_metadata.py:233`) normalizes exactly four carriers and says so in its own docstring: leading workflow-status metadata, the gardener date, the `## Progress Log` body, and completion-tracking checkbox markers. "Every other section stays digested byte for byte." `## Completion Notes` is not among them, and it is a real change-document section on this tree (`12wsj framework-cleanup/1p0qw-doc…:210`, `1p0r6-maint…:137`).

**This is the same shape wave `1uhcb` already settled for the Progress Log.** That wave excluded the Progress Log because it is the mandated repair-tracking surface: a section that *narrates what happened* rather than stating a reviewable contract, whose every append lapsed an unrelated approval roster. Completion Notes is the closure-time member of that same family. The argument that justified the first exclusion justifies this one, and the argument that kept `## Session Handoff` digested does not apply, because Completion Notes is written by the closer, at close, as a matter of course.

**One correction to the field report.** The operator attributed part of the churn to the operator-signoff checkpoint in the wave record. `policy_input_digest` (`review_policy.py:819-840`) hashes change-document bytes plus configuration; `wave.md` is not digested. The one exception is the `Requested review lanes` line, which feeds `requested_lanes` into the payload. Two of their three receipts are consistent with two change-document edit rounds; the wave-record writes were not the cause.

**The same change fixes a second reported symptom, and this is the load-bearing observation.** The fallback corpus is built by passing each undeclared document through the same normalizer (verified: `select_required_review_lanes` calls `canonical_review_policy_body`). The operator separately reported that a Completion Notes phrase, "view-rendering test harness", recruited `qa-reviewer` through the bare-substring token at `review_policy.py:57`. Excluding the section from the canonical body removes it from lane scoring as well as from the digest. One exclusion, both symptoms.

**Exposure here is two documents, and that understates it.** Only 2 of 815 change documents currently carry the section, both in closed waves. The cost is not paid by documents that already have it; it is paid by every wave that closes from now on, because writing the section is a closure step.

## Requirements

1. The body of the one canonical `## Completion Notes` section must be digest-neutral, so recording a closure narrative does not supersede the receipt the closure is approving against.
2. The exclusion must follow the `## Progress Log` precedent exactly: same region scanner, same fence handling, same degrade-on-ambiguity contract, same sentinel-substitution shape.
3. The exclusion is **hash-only**. The section stays in the file, stays readable, and stays part of the closed record.
4. Because the fallback corpus shares the normalizer, the section must also stop contributing lane-recruiting prose. That consequence must be stated and pinned, not left to be discovered.
5. The boundary must not widen silently. Sections adjacent to Completion Notes, and Session Handoff in particular, stay digested, pinned by test.
6. The change must report its own transition cost, measured.

## Scope

**Problem statement:** Writing a wave's closure narrative supersedes the review-policy receipt, so a wave necessarily invalidates the approvals it is closing against, and the same prose also recruits review lanes through the fallback corpus.

**In scope:**

- Excluding the `## Completion Notes` body from `canonical_review_policy_body`.
- The consequent removal of that section from the undeclared-document fallback corpus.
- A boundary pin proving the exclusion is exactly one section wide.
- `REVIEW_POLICY_EVALUATOR_VERSION` bump and its one-time re-Prepare, disclosed.
- A census of affected documents.

**Out of scope:**

- **Tightening the legacy whole-document trigger tokens.** Evaluated in this wave and **declined on measurement**: word-boundary matching drops a required lane on 36 undeclared documents, because `regression` matches "regressions" as a substring but not as a bounded word. See the Decision Log.
- `## Session Handoff`, which stays digested; wave `1uhcb` recorded that decision and nothing here revisits it.
- The wave record. It is not digested, so no change is needed there.
- The declaration contract and the scaffold gate, which are the sibling change in this wave.

## Acceptance Criteria

- [ ] AC-1: Appending to `## Completion Notes` leaves the review-policy digest unchanged, reproduced as a red test first.
- [ ] AC-2: A real contract edit elsewhere in the same document still moves the digest. Without this a normalizer that blanked everything would satisfy AC-1.
- [ ] AC-3: The exclusion is exactly one section wide: an edit to `## Session Handoff` and an edit to the section immediately following Completion Notes both still move the digest.
- [ ] AC-4: The region scanner matches the Progress Log precedent on the cases that broke it before: a fenced `## Completion Notes` lookalike neither opens nor closes the region, and a CRLF document is handled identically to an LF one. The fixture must place a genuine Completion Notes section after the construct under test, so the test cannot pass merely because some guard exists.
- [ ] AC-5: Prose in `## Completion Notes` no longer recruits a fallback lane, pinned with the reported phrase "view-rendering test harness" against the `qa-reviewer` trigger, and a control proving the same phrase in `## Scope` still recruits.
- [ ] AC-6: Ambiguous input degrades byte-for-byte, matching the sibling contract: zero or multiple `## Completion Notes` headings return the input unchanged.
- [ ] AC-7: The evaluator bump converges in exactly one re-Prepare and is idempotent thereafter; closed waves stay byte-immutable, and both existing pins move rather than disappear.
- [ ] AC-8: The census reports how many documents change digest and how many sit in non-closed waves. Expected here: 2 documents, both in closed waves.
- [ ] AC-9: The full framework suite and docs-lint pass.

## Tasks

- [ ] Write the red test for digest stability under a Completion Notes append.
- [ ] Add the section exclusion, reusing the Progress Log region scanner.
- [ ] Add the AC-2 and AC-3 boundary controls, including the adjacent-section case.
- [ ] Add the fence and CRLF pins with a genuine target section after the construct.
- [ ] Add the fallback-corpus pin and its `## Scope` control.
- [ ] Run the census and record affected documents and their wave statuses.
- [ ] Bump the evaluator version, moving both existing pins.
- [ ] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                                       |
| ---------- | ----------- | ---------- | -------------------------------------------------------------- |
| red-test   | implementer | none       | Digest stability under append, before any exclusion             |
| exclusion  | implementer | red-test   | Reuses the Progress Log scanner rather than a parallel one      |
| boundary   | implementer | exclusion  | Exactly one section wide, both neighbours pinned                |
| fallback   | implementer | exclusion  | The second symptom, with its `## Scope` control                 |
| transition | implementer | exclusion  | Evaluator bump, convergence, census                             |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/gardener_metadata.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `docs/specs/mcp-tool-surface.md`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` states which carriers the admitted-change digest normalizes and names the shipped evaluator version. Both change here, so the line changes with the code. No boundary moves and no ownership changes.

## AC Priority


| AC   | Priority  | Rationale                                                                                 |
| ---- | --------- | -------------------------------------------------------------------------------------------- |
| AC-1 | required  | The reported defect.                                                                           |
| AC-2 | required  | Without it a normalizer that blanked everything would pass AC-1.                               |
| AC-3 | required  | An exclusion that widens silently is the failure mode `1uhcb` guarded against.                  |
| AC-4 | required  | The Progress Log exclusion shipped with a fence bug and a CRLF asymmetry; the same scanner carries the same risks. |
| AC-5 | required  | The second reported symptom, fixed by the same change and otherwise undiscovered.               |
| AC-6 | required  | Matches the sibling degrade contract; an unguarded scanner guesses on malformed input.          |
| AC-7 | required  | Digest semantics changing without a bump leaves receipts describing a stale rule.               |
| AC-8 | important | Transition cost must be measured; a downstream repository will differ.                          |
| AC-9 | required  | Standard gate.                                                                                  |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-07 | Field report reproduced structurally: `canonical_review_policy_body` normalizes four carriers and Completion Notes is not one, so the section is digested byte-for-byte | `gardener_metadata.py:233-254` |
| 2026-08-07 | Corrected the field report's attribution: `wave.md` is NOT digested (`policy_input_digest` hashes change-doc bytes plus config), so the operator-signoff checkpoint did not cause churn. Only the `Requested review lanes` line feeds the payload | `review_policy.py:819-840` |
| 2026-08-07 | Confirmed the fallback corpus is canonicalized, so this one exclusion also fixes the reported `test harness` lane recruitment | `select_required_review_lanes` source inspection |
| 2026-08-07 | Census: 2 of 815 change docs carry `## Completion Notes`, both in closed waves. Exposure is future closures, not the existing corpus | corpus scan |
| 2026-08-07 | Word-boundary token matching EVALUATED AND REJECTED: it drops a required lane on 36 undeclared documents. Sampled live `test harness` hits are legitimate AC-level mentions, not narrative, so the section exclusion is the correct instrument | `\b`-matching census |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-07 | Exclude the `## Completion Notes` body from the digest | It narrates what happened rather than stating a reviewable contract, and it is written at close as a matter of course, so digesting it makes every wave invalidate its own approvals. This is the argument `1uhcb` accepted for the Progress Log | Leave it digested and accept a re-mint per closure, which the field report shows costs three receipts and trains operators to treat approval lapses as noise |
| 2026-08-07 | Reject word-boundary matching for the legacy prose tokens | Measured: it drops a required lane on 36 undeclared documents, because `regression` matches "regressions" as a substring but not as a bounded word. Losing coverage to reduce false positives is the wrong direction, and the reported symptom is fixed by the section exclusion anyway | Word-boundary matching as originally proposed; a curated stop-list, which needs the same census and buys less |
| 2026-08-07 | Keep the exclusion hash-only | The section is part of the closed record and has readers; only its contribution to the digest and the fallback corpus is removed | Strip the section at close, which destroys the record it exists to keep |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The exclusion widens and hides a real contract edit | AC-3 pins both neighbours, including Session Handoff, which `1uhcb` deliberately left digested |
| The region scanner repeats the Progress Log's fence or CRLF bugs | AC-4 reuses the same scanner and pins both cases, with the fixture shape that exposed the original vacuity: a genuine target section after the construct under test |
| Removing the section from the fallback corpus drops a lane a document legitimately needed | AC-5's control proves the same phrase still recruits from `## Scope`; only closure narrative stops scoring, and prose describing finished work is not evidence about what needs review |
| The evaluator bump lapses approvals on in-flight waves | AC-7 pins one-time convergence and moves both existing pins; disclosed in the changelog |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
