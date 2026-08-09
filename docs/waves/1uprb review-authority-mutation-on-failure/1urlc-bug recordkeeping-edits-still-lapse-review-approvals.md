# Recordkeeping Edits Still Lapse Review Approvals

Change ID: `1urlc-bug recordkeeping-edits-still-lapse-review-approvals`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-08
Wave: 1uprb review-authority-mutation-on-failure

## Rationale

Wave `1ugk9` excluded the Progress Log from the review-policy digest so narration would stop lapsing approvals. It fixed one member of a family. Measured against the real producers, these edits still churn the digest and lapse every recorded approval with no load-bearing claim changed:

| Recordkeeping edit | Churns | Fixed here |
| --- | --- | --- |
| Edit `## Session Handoff` (boilerplate body) | Yes | **Yes** |
| Add or remove the trailing newline at EOF | Yes | **Yes** |
| Convert the file to CRLF | Yes | **Yes** |
| Prepend a BOM | Yes | **Yes** |
| Add one trailing space on a line | Yes | **Yes** |
| Reorder `## Changes` in `wave.md` | Yes | **Yes** |
| Append a `## Decision Log` row | Yes | **No — deferred, see below** |
| Rename a change doc with identical content | Yes | **No** — `change_id` is a genuine identity change and correctly digested |

**The Decision Log is deliberately NOT excluded here.** An earlier revision of this change excluded it. Council measurement across 824 change documents showed that exclusion would remove a full-council trigger from **21** documents and a required review lane from **4**, making it the second-most damaging of the six candidates considered while a candidate this plan *declined* measured 0 and 0. Three executed attacks confirmed it is author-reachable: a row containing "the trust boundary moves" flips `delivery_council_required` from true to false, and a row reading "Read AC-5 as satisfied by a spot check rather than a full count" moves no digest at all — falsifying the earlier revision's claim that reinterpreting an AC "still churns". The exclusion is deferred to `1us4q`, gated on a differential coverage census rather than a prose argument. This change ships only what measured harmless.

**The largest churn source is an exclusion edit, not a section.** With `evaluator_version` pinned at 6 so a version bump cannot explain it, identical document bytes hash differently under the committed and working-tree canonicalizers, across **100%** of the corpus. Attribution: the entire delta is explained by one new normalizer, `normalize_review_tracking_status`, whose uncommitted work spans **two** sibling waves in this tree: `1umst` added it and `1uo1x` repaired its frontmatter boundary. The hashing function changed *because* the exclusion set changed. So this is not an unfixable structural property, as an earlier revision claimed; it is the one-time cost every exclusion edit pays, including this one. That is what Requirement 6 makes explicit and disclosable rather than surprising.

**Two independent lapse paths.** An approval binds to `policy_receipt_id`, derived from `receipt_semantic_fields`. Moving `required_lanes` or `delivery_council_required` lapses an approval without the digest moving at all. Any fix addressing only digest inputs leaves the second path open, which is why the acceptance criteria measure policy **output**, not just the digest.

## Requirements

1. **Exclude `## Session Handoff` only when its body is the template boilerplate, matched AFTER whitespace normalization.** Ordering is load-bearing: if the body match runs first, a CRLF checkout, a BOM or a single trailing space makes the boilerplate fail to match, the region is digested, and the churn returns for the Windows population Requirement 2 exists to protect. Measured 0 trigger losses and 0 lane losses across 824 documents, but the categorical "nothing can be hidden there" is false: **39 of 732** sections (5.3%) carry substantive text, some of it admission preconditions such as "This change is planning-only until it is admitted, prepared…". Deleting that after a council approved on the basis of it must not be invisible. Normalize the section to a sentinel **only when its stripped body is EXACTLY equal to the template pointer sentence**; digest it byte for byte otherwise. Exact equality is required, not `startswith` or `in`: 5 documents begin with the template sentence and then continue with substantive text (`1p3ha`, `1p3hd`, `1p3hf`, `1p3ho`, `1tr85`), and a prefix match would swallow all five while still passing a negative test that uses a wholly-different body. The implementation must also state where the template sentence comes from — hardcoded, or read from `docs/plans/plan-template.md` at runtime — because hardcoding silently disables the exclusion if the framework template changes, and reading it introduces a new coupling. Note there are **two** producers of that sentence — `docs/plans/plan-template.md` and the `wf_new_*` template literal in `server_impl.py` — byte-identical today. Whichever source is chosen, the two must be kept in step, because a drift between them silently narrows the exclusion. This fixes the measured churn without blinding review to the 5% that use the section substantively. One residual interaction, consistent with both rules and currently unpopulated: a boilerplate body whose line ends in **two or more** trailing spaces is preserved by Requirement 2, therefore fails Requirement 1's exact match, and stays digested. Zero corpus documents are in that state; recorded so it is not read later as a defect.

2. **Normalize line endings, BOM, the trailing newline, and single trailing spaces.** CRLF conversion, a BOM, an EOF newline, and a lone trailing space carry no markdown meaning, and any of them lapses every approval in a wave with zero human intent. **Calibrated, because an earlier revision over-claimed the present tense:** measured today, the corpus contains **zero** CRLF documents and **zero** BOMs; 12 documents lack an EOF newline and 7 more carry trailing whitespace of some length. (An earlier revision quoted "13 of 825", which was the superseded lone-space rule's population and understates the shipped rule.) The argument is prospective — a Windows checkout or an editor that strips whitespace on save would hit every document — and that is the honest form of it. **ALL trailing whitespace outside a fence is normalized, including a markdown hard line break**, and trailing whitespace INSIDE a fence is preserved.

   Two earlier revisions got this wrong in opposite directions. The first declined all interior whitespace because "two trailing spaces are a hard line break", which was broader than its reason supported and left the headline harm unfixed. The second normalized a lone space and preserved runs of two or more, which was still wrong: the digest exists to detect changes to the approved CLAIM contract, and a hard break changes layout rather than words. The split was also unpredictable, since an author can see neither form, and it fixed the smaller population — measured on this corpus, 2 lines carry a lone trailing space and 24 carry a run of two or more, so the rule normalized 2 lines and left 24 churning.

   The fence carve-out is the real exception: inside a fence the whitespace can be the subject rather than the formatting, and a change document demonstrating one-space versus two-space behaviour would otherwise become indistinguishable from itself. This very document is such a case.

3. **Make legacy lane matching whitespace-independent, as the precondition for Requirement 2.** `_legacy_token_match` matches non-extension tokens with a bare `corpus.find(token)`, and four whole-document lane triggers carry a literal trailing space (`-feat `, `-enh `, `-refactor `, `-bug `). Today that makes lane selection depend on invisible whitespace in both directions: a line ending `-bug ` recruits `qa-reviewer` while a line ending `-bug` does not. Normalizing trailing spaces without fixing this would silently drop the first case.

   Match on a **word boundary** against the token with its trailing space stripped, so the trigger fires on the token itself rather than on adjacent whitespace. **This widens matching**: a document ending a line with a bare token will newly recruit a lane it does not get today. That is the correct direction — the trigger is the token, not the space — but it is a lane-selection semantics change and is treated as one: operator-directed, measured by census, and reviewed on its own terms rather than folded in as an implementation detail.

4. **Sort the `changes` payload by `change_id` before hashing.** Reordering `## Changes` in `wave.md` moves the digest today because `change_ids` are collected in document order and hashed unsorted. Order carries no meaning and nothing can be hidden in a sort. This is a canonicalization defect, not an exclusion, and needs none of the exclusion risk analysis.

5. **Decline the remaining candidates and record the measurement.** Each churns; each was measured on both policy-output channels before deciding:
   - `## Risks` — 5 trigger losses, 8 lane losses. Also the table where a plan states what it chooses to accept; excluding it would let a risk row and its mitigation be deleted invisibly.
   - `## Affected Architecture Docs` — 22 trigger losses and **185** lane losses, by far the worst candidate.
   - `## AC Priority` rationale column — measured 0 and 0, and declined only on structural fragility: a column-level exclusion inside a markdown table is brittle in a way section-level rules are not. Recorded as the strongest remaining candidate for `1us4q`, which should reconsider it with a section-level mechanism.
   - `## Serialization Points` prose — 0 trigger losses but **14** lane losses, because an undeclared document scores its lanes from the whole canonical body.

6. **Repair the seed guidance this change falsifies.** Seed `180-implement-feature.prompt.md`'s stop-condition bullet states that a repair confined to `## Progress Log` needs no re-Prepare "because **that section is the one** the review-policy digest excludes". Adding any exclusion makes that false in both directions: an implementer skips a needed re-Prepare or runs an unneeded one. Reword it to reference the exclusion set indirectly so the next exclusion does not re-break it.

7. **Extend the must-not-amend discipline generically, not by enumeration.** The same seed carries "The Progress Log narrates; it must not amend… an amendment announced only in a Progress Log row would never be reviewed." That discipline is what makes an exclusion safe, and it is written for one section. State it as a property of the class — every region the digest excludes narrates and must not amend — so it does not need re-editing each time the exclusion set grows. Enumerating regions here would reproduce exactly the drift Requirement 5 exists to remove, one bullet earlier in the same seed.

8. **State the exclusion-edit disclosure rule in both places that own it**, and state its mechanism inline. The rule has two halves with two different owners: the **author-time** half (disclose the one-time re-digest in your change doc) belongs in seed `170-plan-feature.prompt.md`; the **prepare-time** half belongs in `REVIEW_POLICY_SURFACE_BLOCKS` in `review_policy.py`, immediately after its existing "requires a re-Prepare whenever policy inputs change before implementation" sentence. No single seed owns both. Note that `docs/prompts/prepare-wave.prompt.md` is renderer-owned inside its `wavefoundry:review-policy` marker region and must **not** be hand-edited; the text is generated from that block. An edit to `canonical_review_policy_body` or its normalizers re-digests every change document in the repository once, lapsing every readiness approval in every open wave. An earlier revision anchored this to "exactly as an `evaluator_version` bump does"; `evaluator_version` appears in **zero** seeds, so that pointer resolves to nothing for a reader. Describe the mechanism and the disclosure directly.

9. **Do not widen the heading-match fragility, and fail loudly through the existing channel.** The Progress Log exclusion requires its heading to match exactly once outside a fence; `## progress log`, `### Progress Log`, `## Progress Log (delivery)` and a duplicate each disable it silently, at which point every narration row churns. Census: zero of the corpus carries a variant today, so this is latent, not live. Every existing normalizer degrades by `return text`, silently, so an implementer copying that pattern reproduces the hazard.

   The failure must therefore be **loud but not fatal**: reported through `_prepare_policy_state`'s existing `(None, errors)` return, which `_wave_review_policy_diagnostics` already surfaces. An earlier revision of this requirement said "raises"; that was an over-correction. The three call sites of `canonical_review_policy_body` carry no handler, so a raise converts an author typo into an unhandled traceback out of lane selection, digest computation and prepare, and introduces a degradation path `1upba`'s Requirement 2 taxonomy does not model.

## Scope

**Problem statement:** Approvals are lapsed by edits that change no claim — whitespace an editor inserts on save, a sort order nobody chose, and a boilerplate section nobody reads — and the largest churn source, an exclusion edit itself, is undisclosed.

**In scope:**

- `canonical_review_policy_body` and its normalizers: conditional Session Handoff, line endings, BOM, EOF newline, single trailing spaces.
- The `changes` payload ordering in the digest computation.
- Seed repairs for Requirements 5, 6 and 7.
- `docs/architecture/data-and-control-flow.md`, whose normalizer description this change falsifies further.

**Out of scope:**

- The `## Decision Log` exclusion. Deferred to `1us4q` on measurement, not omitted.
- `## Risks`, `## Affected Architecture Docs`, `## Serialization Points` prose (Requirement 4).
- `## AC Priority` rationale column, deferred to `1us4q` as its strongest candidate.
- Trailing runs of two or more spaces (Requirement 2).
- Change-doc renames: `change_id` is a real identity change.
- The `required_lanes` lapse path under an extractor edit. Real and measured, but a different mechanism deserving its own change.

## Acceptance Criteria

- [x] AC-1: Editing a **boilerplate** `## Session Handoff` does not move `policy_input_digest`, reproduced red-first. Editing a **substantive** one still moves it, asserted as the negative half, so the exclusion cannot be widened to the whole section.
- [x] AC-1b: The boilerplate match is **exact**, pinned with a body that BEGINS with the template sentence and then continues with substantive text. A `startswith` or `in` implementation swallows five real corpus documents and passes a negative test built from a wholly-different body, so the prefix case must be its own fixture.
- [x] AC-1a: The boilerplate match survives **whitespace normalization order**. A boilerplate Session Handoff still excludes under CRLF, with a BOM, and with one trailing space. Requirement 1's body match must run **after** Requirement 2's normalization, or a Windows checkout defeats the match and the churn returns for exactly the population Requirement 2 protects. This failure mode cannot fail loudly, because a body that differs from the template is indistinguishable from an author who wrote something substantive, so AC-7's heading-scoped loudness does not reach it and only this assertion does.
- [x] AC-2: A CRLF conversion, a BOM, an EOF-newline change, and trailing whitespace of **any** length outside a fence each leave the digest unmoved. Negative half: trailing whitespace **inside a fence** still moves it, because there it is content rather than formatting.
- [x] AC-3: Reordering `## Changes` in `wave.md` leaves the digest unmoved, while admitting or removing a change still moves it.
- [x] AC-4: The declined sections still churn, asserted positively for `## Risks`, an `## AC Priority` rationale cell, `## Affected Architecture Docs`, and `## Serialization Points` prose. This is the guard against over-applying the pattern.
- [x] AC-5: **Differential policy-output census across the whole corpus**, measured against a TRUE baseline (old canonicalizer AND old token matcher). Council seats are measured at WAVE scope, not per document, because `_select_prepare_council_rotating_seat` consumes a whole wave's joined canonical texts.

  **Result: exactly ONE difference across 824 change documents, enumerated and justified here as this AC requires.** `docs/waves/1t3gt mcp-tool-hygiene/1t3gs-ref mcp-tool-prefix-rename.md` **gains** `qa-reviewer`. Cause: a line wraps mid-citation and ends with a bare `` `1t1b3-bug ``, which the old literal `corpus.find("-bug ")` missed and the new boundary match finds. Zero documents lose a lane; zero council triggers move; zero rotating seats move. The gain is the AC-3a widening working as intended, in the safe direction.

  **Reconciled with AC-3a, which the earlier revision left in tension:** AC-3a deliberately widens matching, so a differential of exactly zero would have meant AC-3a did not ship. AC-5's gate is therefore "no unjustified difference and NO LOSSES", not "no difference".

  **An earlier revision of this AC was marked complete on a census that reported zero, and that census was wrong**: it applied the NEW token matcher to both sides, so the widening was invisible to the very gate meant to authorize it. Any difference is enumerated and justified by name, or the change does not ship. This is the gate the deferred Decision Log exclusion failed, and it measures policy output rather than the digest, so it also covers the second lapse path.
- [x] AC-3a: **Legacy lane matching is whitespace-independent**, and its one corpus-visible effect is enumerated under AC-5 rather than left to a census that reports zero. A line ending with a bare `-bug` and a line ending with `-bug ` both recruit the same lane, asserted in both directions. The widening is asserted positively rather than tolerated: the bare-token case must newly match, since that is the semantics change this requirement makes deliberately.
- [x] AC-5a: **Rule-level pin for space-terminated lane triggers, which the corpus snapshot cannot see.** `_legacy_token_match` is a plain `corpus.find(token)` and four whole-document triggers end in a space (`-feat `, `-enh `, `-refactor `, `-bug `), so a single trailing space is load-bearing for them. Executed: an undeclared document with `-bug ` at end of line scores `['qa-reviewer']` today and `[]` after single-space normalization. Zero current documents hit this, so AC-5's differential reports zero and will keep reporting zero while the hazard is permanent for every document written after this ships. Either run the whitespace normalization **after** lane scoring, or pin that a space-terminated legacy token at end of line keeps its lane. A snapshot census is not sufficient evidence for a rule change.
- [x] AC-6: **The exclusion is total, never partial** (anti-leak, not anti-hiding). A declaration bullet, a `**Review targets (repo-relative paths):**` marker block, and full-council trigger words placed in an excluded region do not partially survive canonicalization. Named precisely: an earlier revision called this AC "the exclusions cannot hide a claim", but its assertion was that policy output is unchanged, which is the statement that the exclusion works — it passes exactly when hiding occurs. AC-5 is the anti-hiding gate; this one is anti-leak.
- [x] AC-7: The new exclusion fails **loudly** on genuine ambiguity only, **through the diagnostic channel that already exists** rather than by raising. Surfaced by `_review_policy_receipt_diagnostics` and by `wf_prepare_wave`'s own error return, NOT by `_wave_review_policy_diagnostics`, which only fires on an invalid `wave_review` config and never calls `_prepare_policy_state`. "Genuine ambiguity" is two or more exact headings, or a variant heading in a document carrying no exact one. **Zero matches is the NORMAL absent case and must never be loud**: 89 of 825 change documents carry no `## Session Handoff` section at all, so an implementer who copies the existing `if len(matches) != 1: return text` predicate and turns it into a failure breaks 89 documents immediately. The predicate conflates absent with duplicated and must be split. `_prepare_policy_state` returns `(None, errors)` and `_wave_review_policy_diagnostics` surfaces those at review and close, so the failure reaches the operator as a named cause and composes with `1upba`'s degradation taxonomy. A bare `raise` is explicitly rejected: `canonical_review_policy_body` is a pure helper on the digest hot path whose three call sites — `select_required_review_lanes`, `policy_input_digest`, and `_prepare_policy_state` — have **no enclosing handler**, so raising would turn ordinary author input like `## Session Handoff (notes)` into an unhandled traceback out of prepare. Silent `return text` is still forbidden, which is what this AC pins.

  **Stated plainly, because it converts a silent degrade into a hard stop:** an ambiguous heading now returns `(None, errors)` from `_prepare_policy_state`, which blocks receipt publication at prepare and refuses a `wf_mark_ac` deferral. Zero corpus documents are in that state today, so the exposure is latent, and the message names the file and the fix. "Loud but not fatal" means no traceback, not no refusal.
- [x] AC-8: Requirement 6's stop-condition bullet and Requirement 7's must-not-amend rule are repaired in seed 180; Requirement 8's author-time half is added to seed 170 and its prepare-time half to `REVIEW_POLICY_SURFACE_BLOCKS` in `review_policy.py`. Verified by reading the rendered text of each, not by re-deriving a corpus measurement. The rendered `docs/prompts/prepare-wave.prompt.md` must show the new sentence inside its marker region **and** must not have been hand-edited.
- [x] AC-9: `docs/architecture/data-and-control-flow.md` is corrected. It currently states that admitted-change hashing "normalizes **only one** canonical top-level `Last verified`… all other bytes remain significant", which is false three ways today and would be false four ways after this change.
- [x] AC-11: **`REVIEW_POLICY_EVALUATOR_VERSION` bumps 6 to 7**, so the permanent `events.jsonl` history can tell a plan edit apart from this canonicalization change. Operator-directed, on the precedent this repository set at 2 to 3 for the Progress Log exclusion. The re-digest happens either way, so the bump only decides whether the ledger can EXPLAIN it. Pinned by the transition-boundary tripwire in `test_review_policy`, whose docstring records what each bump carried, and by the convergence test in `test_server_tools`, which now tracks the constant rather than a literal because convergence is about old to current to stable rather than about which number is current.
- [x] AC-10: The full framework suite and docs-lint pass.

## Tasks

- [x] Write the red tests for boilerplate Session Handoff and the four whitespace classes before changing the canonicalizer.
- [x] Pin the declined sections (AC-4) and the substantive-Session-Handoff negative (AC-1) before implementing, so over-application fails immediately.
- [x] Implement the conditional Session Handoff exclusion with loud failure on a variant heading.
- [x] Implement line-ending, BOM, EOF-newline and trailing-whitespace normalization, fence-aware so in-fence whitespace is preserved.
- [x] Fix `_legacy_token_match` to boundary-match the stripped token, BEFORE adding trailing-space normalization.
- [x] Sort the `changes` payload by `change_id` before hashing.
- [x] Run the differential policy-output census (AC-5) and enumerate any difference.
- [x] Repair seed 180's stop-condition and must-not-amend bullets, and add the disclosure rule to the plan-discipline seed, under the `seed_edit_allowed` gate.
- [x] Correct `data-and-control-flow.md`'s normalizer description.
- [x] Bump `REVIEW_POLICY_EVALUATOR_VERSION` and update the transition-boundary tripwire consciously, as its docstring requires.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-tests | implementer | — | Includes AC-4 declined pins and the AC-1 negative |
| handoff-exclusion | implementer | red-tests | Conditional on boilerplate body; loud failure |
| token-match | implementer | red-tests | Boundary match; precondition for `whitespace` |
| whitespace | implementer | token-match | All trailing whitespace outside a fence; in-fence preserved |
| changes-sort | implementer | red-tests | Canonicalization defect, independent |
| census | implementer | handoff-exclusion, whitespace, changes-sort | AC-5 differential; gates the change |
| seed-and-docs | implementer | — | Requirements 5-7 and the architecture doc |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/gardener_metadata.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/prompt-surface-manifest.json`

Citations anchor by symbol where a containing symbol exists, per the sibling change `1urlb`.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` is **edited** by this change, not merely checked, and is declared above. AC-9 covers it.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The section this change actually excludes, with the negative half that keeps the 5% substantive cases reviewable. |
| AC-1a | required | Ordering is silent when wrong: a body that differs from the template is indistinguishable from a substantive one, so AC-7's heading-scoped loudness cannot reach it. |
| AC-1b | required | A prefix match swallows five real corpus documents and still passes a wholly-different negative fixture. |
| AC-3a | required | A lane-selection semantics change, operator-directed. Asserting the widening positively is what stops it shipping as an unnoticed side effect of a whitespace rule. |
| AC-5a | required | The corpus snapshot reports zero and will keep reporting zero while the hazard is permanent for every future document. A rule change needs a rule-level pin. |
| AC-2 | required | Affects every document with zero human intent, and the fence carve-out is the one case where trailing whitespace is the subject rather than the formatting. |
| AC-3 | required | Pure bookkeeping with no content change; a canonicalization defect rather than a policy choice. |
| AC-4 | required | The guard against over-applying the pattern to load-bearing sections. |
| AC-5 | required | The gate the deferred Decision Log exclusion failed. It measures policy output, so it is the only AC covering the non-digest lapse path. |
| AC-6 | required | A partial exclusion would leave a half-canonicalized body, which is a correctness failure distinct from hiding. |
| AC-7 | required | Every existing normalizer degrades silently; without a loud-failure pin this exclusion joins them and the churn returns undiagnosably. |
| AC-8 | required | This change falsifies shipped seed guidance; leaving it false misroutes every implementer who reads it. |
| AC-9 | important | The architecture doc is already wrong three ways and this change makes it four. |
| AC-10 | required | Standard gate. |
| AC-11 | required | Without it every receipt this ships is indistinguishable in the permanent ledger from an ordinary plan edit, which is the property the 2-to-3 bump existed to preserve. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-08 | Code lane found the evaluator version left at 6 against this repository's own recorded precedent: the 1.15.4 entry bumped 2 to 3 for the Progress Log exclusion alone, stating the reason as letting the permanent ledger tell a plan edit apart from a canonicalization change. This change is strictly larger. OPERATOR directed the bump to 7. The re-digest was always going to happen, so the bump does not add cost; it decides whether the history can attribute the cost | shipped CHANGELOG 1.15.4 entry |
| 2026-08-08 | The bump tripped a deliberate tripwire, which is the design working: `test_evaluator_version_six_is_the_shipped_transition_boundary` exists to force a conscious update per bump. Renamed and its docstring extended with what v7 carries, rather than just changing the number. The paired convergence test in `test_server_tools` was pinning the literal 6; it now tracks the constant, since convergence is about old to current to stable and not about which number is current, so it needs no edit on the next bump | suite 7011 OK |
| 2026-08-08 | Remaining P1 from the code lane folded: AC-7's variant-heading half was specified but never implemented, so `## Progress Log (delivery)`, `### Progress Log`, `## progress log` and `## Session Handoff (notes)` each disabled their exclusion in silence. The detector now reports a variant heading when no exact one exists, and stays silent when a document legitimately has neither. Measured: 0 of 1032 documents would be blocked by the widened detector | executed corpus scan |
| 2026-08-08 | Three more vacuous tests of the coordinator's repaired after mutation testing named them. `test_a_legacy_token_inside_a_word_still_does_not_match` used "debugger", which does not contain "-bug" at all, so it held under substring search, boundary search, and with the lookahead deleted; it now uses `-bugfix` and `-enhanced`. AC-1's positive half compared a pure function against itself on identical input and passed under `return body`; it now asserts the sentinel actually appears. AC-4 named four sections while the fixture contained one of them; the other three are now real fixtures | qa lane mutants M17, M9; V2, V3, V4 |
| 2026-08-08 | DELIVERY review: three of five lanes WITHHELD, and the sharpest finding is a test the coordinator wrote that is VACUOUS. `test_an_excluded_region_is_never_partially_canonicalized` looped over three payloads and never used the loop variable, making three byte-identical assertions on a plain document. It was also self-contradictory: inserting a payload into a boilerplate handoff makes it non-boilerplate, so its sentinel assertion could never hold. Rewritten against `## Progress Log`, the only excluded region whose body can carry a payload and still be excluded | docs-contract lane, AST check |
| 2026-08-08 | AC-5's census claim of ZERO differences was FALSE, and the error was in the gate that authorizes this change: the coordinator's census applied the NEW token matcher to both sides, so the AC-3a widening was invisible to it. Re-run against a true baseline: exactly ONE difference across 824 documents, `1t3gs-ref mcp-tool-prefix-rename.md` gaining `qa-reviewer` from a line that wraps mid-citation ending in a bare `-bug`. Zero losses, zero trigger moves, zero seat moves. Now enumerated and justified in AC-5, and AC-5's gate restated as no-unjustified-difference-and-no-losses, since a differential of zero would have meant AC-3a never shipped | security lane; independently reproduced |
| 2026-08-08 | AC-8's seed-170 half never landed. Requirement 8 splits the disclosure because no single seed owns both plan and prepare discipline, and the coordinator put both halves in seed 180, where a plan author never reads the author-time one. The rule is now in seed 170 as its own section | docs-contract lane; grep of seed 170 returned zero hits |
| 2026-08-08 | The architecture doc was corrected against a SUPERSEDED revision: it described the lone-space rule the operator had already overturned, so AC-9 swapped one false statement for another and told a reader a hard break still supersedes the receipt. Now matches the shipped rule, and gained the two things it omitted: the fence carve-out, and the fact that these normalizers moved beyond receipt hashing into lane selection, the delivery-Council decision and seat rotation | architecture lane |
| 2026-08-08 | OPERATOR challenged the hard-line-break carve-out during implementation and was right. The rationale did not hold: the digest detects changes to the approved claim contract, and a hard break changes layout rather than words. Measured, the rule was also backwards — it normalized the 2 lines in this corpus carrying a lone trailing space and left the 24 carrying a run of two or more to churn. Now normalizes all trailing whitespace OUTSIDE a fence, and preserves it inside, since in a fence the whitespace can be the subject; this document is itself such a case | 2 lines vs 24 lines measured across 824 documents |
| 2026-08-08 | Implementation surfaced a fork the plan had left open and the OPERATOR decided it: `_legacy_token_match` matches four lane triggers with a literal trailing space, so lane selection currently depends on invisible whitespace in both directions. Rather than carve the tokens out of the whitespace rule (which would duplicate the token list across modules, the exact drift hazard this wave fights) or defer, the root fix was chosen: boundary-match the stripped token. Recorded as a lane-selection SEMANTICS change with its own requirement, AC and workstream, not folded in as an implementation detail, because it widens matching | operator decision; `review_policy.py` `_legacy_token_match` |
| 2026-08-08 | Operator reported that review is still invalidated by documentation recordkeeping. Measured rather than assumed: fifteen edit classes driven independently through the real producers, with the Progress Log as a control. The control held; seven other recordkeeping classes churn | scratch-copy probes |
| 2026-08-08 | **Decision Log exclusion REMOVED from this change** after council measured it on the policy-output channel the earlier revision never checked: 21 documents lose a full-council trigger and 4 lose a required lane, making it the second-most damaging of six candidates, while the declined `## AC Priority` rationale measured 0 and 0. Three executed attacks confirmed author reachability, including a row reinterpreting an AC that moves no digest at all — falsifying this plan's own earlier dismissal. Deferred to `1us4q` gated on a differential census | red-team seat, 824-document differential |
| 2026-08-08 | Session Handoff NARROWED to boilerplate-only after a census refuted the plan's categorical: **39 of 732** sections (5.3%) carry substantive text including admission preconditions. The earlier revision gave the section with the weaker risk analysis the wider exclusion, and the seed quote it leaned on ("the session handoff") names `docs/agents/session-handoff.md`, a different artifact entirely | docs-contract seat census |
| 2026-08-08 | Whitespace decline NARROWED in the other direction: the earlier revision declined all interior whitespace because "two trailing spaces are a hard line break", but the measured harm is a SINGLE trailing space, which carries no markdown meaning. The decline was broader than its reason supported and left this plan's own headline harm unfixed | both seats |
| 2026-08-08 | The "structurally unfixable" framing of the 100% re-digest is CORRECTED, not merely softened: the entire 824-document delta is explained by one new normalizer added by sibling wave `1umst` in this tree. The hashing function changed because the exclusion set changed, so this is the one-time cost every exclusion edit pays, including this one | attribution run |
| 2026-08-08 | AC-6 was a TAUTOLOGY and is renamed. Its assertion was that policy output is unchanged, which is the statement that the exclusion works, so it passed exactly when hiding occurred. Correct for the Progress Log, where anti-leak was the property wanted; wrong for any exclusion whose region can carry a claim. Anti-hiding is now AC-5's differential census | red-team seat |
| 2026-08-08 | Census figures corrected: Session Handoff 732 and Decision Log 725, not 733 and 726; numerator and denominator had come from different snapshots. The corpus is also relabelled, since roughly 800 of the 824 markdown documents carry a `Change ID` header | independent recount, both seats |
| 2026-08-08 | Three seed and doc defects folded that the earlier revision would have shipped: seed 180's stop condition asserts the Progress Log is "the one" excluded section, which this change falsifies; its must-not-amend discipline is written for one section while the exclusion set grows; and the `evaluator_version` analogy resolves to nothing, since that identifier appears in zero seeds | docs-contract P1-1, P1-2; both seats on the analogy |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-08 | Defer the Decision Log exclusion to `1us4q` | Measured 21 trigger losses and 4 lane losses on real corpus documents, with three executed author attacks. The value is real but it needs a differential census as its gate, not a prose risk argument | Ship it here with a stronger AC (rejected: the operator chose to split, and the measurement belongs in front of the exclusion rather than behind it); drop it permanently (rejected: the churn it causes is real and framework-mandated) |
| 2026-08-08 | Exclude Session Handoff conditionally rather than wholesale | 5.3% of sections carry substantive text, some load-bearing for admission. A boilerplate-only sentinel fixes 100% of the measured churn while leaving every substantive use reviewable | Whole-section exclusion (rejected on the census); no exclusion (rejected: it is the cleanest measured win in the set) |
| 2026-08-08 | Normalize single trailing spaces, preserve runs of two or more | One trailing space has no markdown meaning; two is a hard line break. Declining both left the headline harm unfixed | Decline all interior whitespace (rejected: broader than its reason); normalize all (rejected: changes rendering) |
| 2026-08-08 | Treat the `changes` ordering as a canonicalization defect | Order carries no meaning and nothing can be hidden in a sort, so it needs no exclusion-region risk analysis | Frame it as another exclusion (rejected: invites unnecessary scrutiny for a one-line sort) |
| 2026-08-08 | State the disclosure mechanism inline rather than by analogy | `evaluator_version` appears in zero seeds, so the analogy resolves to nothing for the reader it is written for | Cite the protocol-2 migration prose (rejected: it describes policy migrations, not exclusion edits) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An exclusion removes review coverage | AC-5 requires a whole-corpus differential on `required_lanes`, `delivery_council_required` and council seats, with every difference enumerated by name. This is what the deferred Decision Log exclusion failed |
| The pattern is over-applied to load-bearing sections | AC-4 pins that all four declined sections continue to churn |
| The Session Handoff exclusion is widened to the whole section | AC-1's negative half requires a substantive body to keep churning |
| A new exclusion silently stops excluding | AC-7 requires loud failure, explicitly against the `return text` pattern every existing normalizer uses |
| This change re-digests the corpus once | Disclosed rather than hidden: Requirement 7 puts the rule in a seed, and the cost is the same one every exclusion edit pays. It should land and settle before `1upba`'s refusal goes live, since after that each canonicalizer edit needs its own re-Prepare |
| `1upba` and this change share `server_impl.py` and `review_policy.py` | Sequencing is stated in `wave.md`; the canonicalizer work lands and settles before the refusal becomes active |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
