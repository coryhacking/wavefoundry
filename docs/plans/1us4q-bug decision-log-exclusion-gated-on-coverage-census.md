# Decision Log Churn: Phase Routing Plus A Guard For Trigger Text In Excluded Regions

Change ID: `1us4q-bug decision-log-exclusion-gated-on-coverage-census`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-10
Wave: TBD (withdrawn from `1uwpf`; not admitted)

> **Withdrawn from wave `1uwpf` on 2026-08-10 after six independent review lanes returned WITHHELD, and the implementation was reverted.** The census gate this document was originally deferred behind has now been run three times and reproduces. What failed is the INSTRUMENT, for the third time. Everything below the Rationale describes a design that six lanes falsified; it is retained because the falsifications are the most valuable thing this document owns. **Read `## Progress Log` before redesigning.** The next attempt must start from the findings, not from these Requirements.

**Corpus definition, used by every number in this document:** all `*.md` under `docs/plans/` and `docs/waves/*/`, excluding `wave.md`, **including** `docs/plans/plan-template.md`. That is **824** documents, of which **732** carry exactly one `## Decision Log`, 92 carry none, and 0 carry more than one. Counts elsewhere that report 731 or 733 differ only by whether the template is included; the definition is stated here because a review seat could not reproduce the earlier figure without it.

## Rationale

Appending a `## Decision Log` row to a change document moves `policy_input_digest` and lapses every recorded review approval, without any load-bearing claim changing. The framework **instructs** the edit: seed `180-implement-feature.prompt.md` tells participants to "leave enough state in wave artifacts (Progress Logs, Decision Logs, the session handoff) for another agent to continue safely". The Progress Log half of that sentence is excluded from the digest; the Decision Log half lapses the approvals the same wave just collected.

**The cost is per append event, not per row, and each event is expensive.** Carrying a Decision Log does not cause churn; appending to one after approval does. Measured over the corpus: 699 documents have a dated Decision Log, **634 of them (90.7%) have every row on a single date** — written at plan time, never appended to. Only **65 documents (9.3%)** ever gained a later-dated row, totalling **214 rows**. Each of those 214 appends supersedes the receipt and forces a re-Prepare plus a re-record of the entire readiness roster. The rate is rising:

| Month | Append-after-plan-time rows |
|---|---:|
| 2026-05 | 24 |
| 2026-06 | 41 |
| 2026-07 | 143 |
| 2026-08 (to the 10th) | 6 |

**The obvious fix — excluding the region — removes real review coverage.** Excluding a region does not only stop it being hashed. `select_required_review_lanes` builds its corpus for any document that declares no Serialization Points from `canonical_review_policy_body(...)`, and `extract_full_council_triggers` and `_select_prepare_council_rotating_seat` both consume canonical text at the receipt-producing site. Text inside an excluded region is inert on **three** channels. `docs/architecture/data-and-control-flow.md` states this as a design property: "Adding or changing an exclusion therefore moves lane selection, the delivery-Council decision, and the council seat, not just receipt identity."

Differential census, reproduced independently three times:

| Measure | `1urlc` council seat | Coordinator re-run | Red-team seat |
| --- | ---: | ---: | ---: |
| Documents losing a full-council trigger | 21 | **23** | **23** |
| Documents losing a required lane | 4 | **4** | **4** |
| Documents *gaining* a lane | — | 0 | **0** |

Lost trigger fields: `cross_platform_changed` (13), `failure_or_readiness_semantics_changed` (6), `release_or_upgrade_changed` (2), `contract_or_required_ac_semantics_changed` (2). Named casualties: `12mgm-enh dashboard-markdown-table-render.md` loses `architecture-reviewer`; `1p3ay-feat upgrade-migration-for-1-5-0-breaking-changes.md` loses `release-reviewer` because its Decision Log row is the one naming `upgrade_wavefoundry.py`.

**Redirecting narration to the Progress Log carries the same loss prospectively, and an earlier revision of this plan claimed it carried none.** That revision said "this costs zero review coverage". Both readiness seats falsified it by execution, and the coordinator reproduced it: the identical decision row yields `('release_or_upgrade_changed',)` and recruits `release-reviewer` when it sits in `## Decision Log`, and yields `()` and recruits nothing when it sits in `## Progress Log`. The Progress Log is already excluded, so instructing authors to write decisions there **is** an exclusion applied at authoring time.

**The loss is bounded and small, which is what makes the instrument viable.** Of the 214 append-after-plan-time rows, only **13 (6.1%)** are trigger-bearing. **201 (93.9%) are redirectable with no coverage effect at all.** So a carve-out that keeps boundary-crossing decisions in the Decision Log preserves the coverage while leaving 94% of the churn addressable.

**The hazard is already live, and this change closes it rather than opening it.** The Progress Log exclusion shipped in `1uhcb` already inerts trigger text. Measured today: **97 documents carry 156 trigger-bearing Progress Log rows** that are currently inert for council triggering. Every one of the 97 is in a **closed** wave; **zero live documents are affected**. That is the fact that makes an error-level guard implementable — it passes clean on the corpus as it stands while catching every future occurrence, and closed-wave history is never rewritten.

So this change does two things: it routes narration by phase with a boundary carve-out, and it adds the mechanical guard that makes the carve-out something other than author judgment.

**One consumer consequence, recorded rather than discovered.** `memory_propose` drafts candidate records from "the wave's `events.jsonl` heads + admitted change-doc Decision Logs". Redirecting implementation narration thins that input. Judged an improvement: plan-time decisions with weighed alternatives are the durable-shaped evidence memory wants. If supply measurably drops, extending `memory_propose` to read Progress Logs is a separate change.

## Requirements

1. **Seed 180 states where decision narration goes, by phase.** A decision that is part of the approved contract — alternatives weighed at plan time, the design chosen — is recorded in `## Decision Log`, and editing it after approval legitimately supersedes the receipt because it changes what was approved. A decision made *while implementing or reviewing* is recorded in `## Progress Log`. The rule is stated as a property of the phase rather than as a list of sections, matching the existing bullet's own stated reason for avoiding enumeration.

2. **The phase rule carries a boundary carve-out.** An implementation-time decision that crosses a trust, permission, release/upgrade, architecture or ownership, cross-component-protocol, failure/readiness, cross-platform, or public-contract boundary stays in the `## Decision Log` regardless of phase, because that text is load-bearing for lane selection, the delivery-Council decision, and seat selection. Without this the rule instructs authors to inert exactly the 6.1% of rows that matter most. The carve-out is stated in the audience's own terms, not as a list of trigger field names.

3. **A mechanical guard backs the carve-out.** `docs_lint` gains a check that fails when text inside a **digest-excluded region** of a live change document would register a full-Council trigger. It reuses the shipped detector rather than a second vocabulary, so the guard and the selection channel can never disagree. Scope is `docs/plans/` and change documents in **non-closed** waves; closed waves are historical and are never rewritten. Measured: this fails on **zero** documents today, so it ships as an error rather than a warning. The message names the document, the region, the offending text, and the fix — move it to the section that owns the contract.

4. **The rule reaches existing repositories through a mechanism that cannot silently no-op.** Seed 180 itself ships to installed repos because `.wavefoundry/framework/` is replaced wholesale at upgrade, so an agent reading the seed gets the rule. For the rendered surface, an exact-string reconciler pair is **not** acceptable on its own: `docs/prompts/review-wave.prompt.md` contains no Decision Log prose to key on, two byte-different baselines exist (the fresh-install template is hard-wrapped, the reconciler constant is not), and `plan_reconciliation` computes matches against the **original** text so a pair keyed on another pair's output silently misses on a single upgrade hop. Deliver through the renderer-owned `wavefoundry:review-policy` marker region, which `reconcile_review_policy_surfaces` rewrites wholesale on every upgrade with no keying and no drift sensitivity. If a reconciler pair is used anywhere in this change, it must satisfy the unwritten invariant every one of the 13 existing pairs satisfies — the replacement must not contain its own legacy anchor as a substring — or it compounds on each upgrade.

5. **The rendered implement surface is addressed or explicitly excluded.** This is an implementation-phase rule, and `docs/prompts/implement-feature.prompt.md` is reached by no update mechanism at all — it is absent from `LIFECYCLE_PROMPT_BASELINES`, `REVIEW_POLICY_CARRIER_REGISTRY`, and `LIFECYCLE_RECONCILER_CARRIERS`. `docs/prompts/implement-wave.prompt.md` is a carrier with registered pairs and a renderer block. State which rendered surface carries the implementer-facing half and why, rather than leaving the reader to infer that the review surface was chosen deliberately.

6. **No canonicalizer change, no evaluator bump, no digest change.** `canonical_review_policy_body` composes exactly the five section normalizations it composes today. `REVIEW_POLICY_EVALUATOR_VERSION` stays 7. No wave goes stale, no approval lapses, and there is no one-time re-Prepare. This is what distinguishes the shipped instrument from both rejected ones.

7. **The census is a deliverable, not a step.** It ships as a runnable script with a declared path and a positive control, because the next exclusion proposal should be cheap to judge and because this census has already produced one false zero. `.wavefoundry/framework/scripts/` is packaged by exclusion, so a governance-only tool must be added to `EXCLUDED_REL_PATHS` — as `build_scan_allowlist.py` already is — or it ships to every target repository that has no use for it.

8. **The rejected instruments stay recorded with the measurement that rejected each.** The whole-region exclusion, structured-rows-only, split-carrier, redirect-without-carve-out, and the `## AC Priority` candidate. This document exists because the first attempt measured after designing; discarding the measurements would reproduce that.

## Scope

**Problem statement:** A framework-mandated recordkeeping edit lapses review approvals 214 times across the corpus and rising, and both obvious fixes remove measurable review coverage.

**In scope:**

- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`: the phase-routing rule with its carve-out (Requirements 1-2) and the corrected state-leaving bullet.
- `.wavefoundry/framework/scripts/docs_lint.py`: the excluded-region trigger guard (Requirement 3).
- The renderer-owned `wavefoundry:review-policy` region source for `docs/prompts/review-wave.prompt.md` (Requirement 4), and this repository's rendered copy.
- A census script with a declared path, plus its `EXCLUDED_REL_PATHS` entry (Requirement 7).
- `.wavefoundry/framework/scripts/tests/`: tests for the guard and the census.

**Out of scope:**

- Any change to `canonical_review_policy_body`, the normalizer set, or `REVIEW_POLICY_EVALUATOR_VERSION`. Requirement 6 is the boundary.
- Excluding `## AC Priority`. It measured 0 trigger and 0 lane losses and remains the best future exclusion candidate, but it is a different section and belongs in its own change. `## Risks`, `## Affected Architecture Docs`, and `## Serialization Points` are **not** measured here and are named only to close the boundary; `## Serialization Points` is structurally ineligible in any case, because `select_required_review_lanes` branches on whether that section declares paths.
- Rewriting the 97 closed-wave documents carrying 156 inert Progress Log rows. Closed waves are historical; the guard does not apply to them.
- Extending `memory_propose` to read Progress Logs.

## Acceptance Criteria

- [ ] AC-1: The differential census ships as a runnable script at a declared path, with a **positive control that fires on both the trigger and lane channels**, and its full result is recorded in this document. An earlier run returned a false zero because `select_required_review_lanes` is keyword-only, every call raised `TypeError`, and a bare `except Exception: continue` swallowed all of them; a control that does not fire makes the numbers worthless. The script's corpus definition matches the one stated at the head of this document.
- [ ] AC-2: **The relocation attack is executed against the shipped instrument.** Take a decision row that registers a full-Council trigger in `## Decision Log`, place it in `## Progress Log` as the new rule would direct, and assert that the carve-out plus the Requirement 3 guard prevent it — the guard fails the document and names the row. The three historical attacks are kept as a regression baseline, but they are **not** this AC's obligation: they were attacks on the rejected exclusion, and re-running them against unchanged code asserts only that yesterday's behavior still holds.
- [ ] AC-3: Seed 180 states the phase-routing rule and its carve-out, verified against the **canonical seed** rather than a rendered carrier. The existing "An excluded section narrates; it must not amend" bullet is left byte-unchanged, verified by **comparing that bullet's own text against a literal pinned in the test** — not by a file-level `git diff`, because a sibling wave has an uncommitted edit immediately above it that would produce a false failure.
- [ ] AC-4: The state-leaving bullet routes by phase and no longer directs implementation-time state flatly into both sections.
- [ ] AC-5: The Requirement 3 guard fails a document with trigger-bearing text in an excluded region, naming document, region, and text; passes the same document once the text moves to a digested section; **passes the entire current corpus with zero failures**; and does not fire on closed waves. Red-first: the guard must fail on a constructed case before it exists.
- [ ] AC-6: The rule reaches an existing repository through the renderer-owned region, verified by running the reconciler **twice** against a byte-copy of a shipped baseline and asserting the file is byte-identical after the second pass. If any reconciler pair is added, a test asserts the no-self-containment invariant for every pair in `KNOWN_SECTION_REPLACEMENTS`, which all 13 existing pairs satisfy and which is currently unwritten.
- [ ] AC-7: `canonical_review_policy_body` composes exactly five section normalizations and `REVIEW_POLICY_EVALUATOR_VERSION` is 7, both asserted. A Decision Log append still moves the digest, asserted **with an inline docstring stating why that is correct**: a contract-bearing edit should supersede the receipt, and this change deliberately does not alter that. Without the docstring the assertion reads as pinning the reported symptom.
- [ ] AC-8: `docs/architecture/data-and-control-flow.md`'s five-region claim is confirmed unchanged and still correct, recorded rather than edited — every rejected instrument would have required that edit, and a reader comparing this change to them may expect it.
- [ ] AC-9: The census script is excluded from the packaged framework, or the change records why a target repository needs it. Verified against `EXCLUDED_REL_PATHS`.
- [ ] AC-10: Requirement 5 is answered in the document: the rendered surface carrying the implementer-facing half is named, with the reason.
- [ ] AC-11: The full framework suite and docs-lint pass.

## Tasks

- [ ] Write the census script at its declared path with a positive control; record its output here.
- [ ] Add the phase-routing rule and carve-out to seed 180 under the `seed_edit_allowed` gate; correct the state-leaving bullet in the same gated edit; close the gate immediately after.
- [ ] Implement the excluded-region trigger guard in `docs_lint.py`, red-first.
- [ ] Deliver the rendered half through the renderer-owned region; verify twice-run idempotence.
- [ ] Add the census script to `EXCLUDED_REL_PATHS`.
- [ ] Assert the no-change boundary (AC-7, AC-8).
- [ ] Run the full suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | — | AC-1; positive control mandatory |
| seed-180 | implementer | census | Requires `seed_edit_allowed`; ships to every target repo |
| lint-guard | implementer | census | AC-2/AC-5; red-first; new failure surface, needs its own tests |
| rendered-surface | implementer | seed-180 | AC-6; renderer region, twice-run idempotence |
| no-change-pins | implementer | seed-180 | AC-7/AC-8; keeps the rejected instruments out |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `.wavefoundry/framework/scripts/docs_lint.py`
- `.wavefoundry/framework/scripts/review_policy_reconcile.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/prompts/review-wave.prompt.md`

## Affected Architecture Docs

`N/A` with rationale, and the rationale is the point of AC-8. Every rejected instrument would have required editing `docs/architecture/data-and-control-flow.md`'s description of what the canonicalizer normalizes. The shipped instrument changes no normalizer, so that description stays correct and is deliberately **not** edited. AC-8 records the confirmation so a reader who expects the edit finds the reason it is absent.

The same document's sentence "Adding or changing an exclusion therefore moves lane selection, the delivery-Council decision, and the council seat, not just receipt identity" is **read and relied upon** by this change, and remains accurate.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The gate this change was deferred behind. The positive control is required because this census already produced one false zero. |
| AC-2 | required | The previous revision's AC-2 could not fail. This one tests the shipped instrument's own attack surface. |
| AC-3 | required | The rule is the deliverable; the pinned-literal method is required because a file diff would false-fail against a sibling wave's edit. |
| AC-4 | required | Names the exact sentence that causes the churn; leaving it ships the rule and the contradiction together. |
| AC-5 | required | The guard is what makes the carve-out mechanical rather than author judgment. |
| AC-6 | required | Without a no-op-proof mechanism the rule reaches fresh installs only. |
| AC-7 | required | The pin that stops a rejected instrument re-entering under this change's identity. |
| AC-8 | important | Prevents a well-meaning edit that would falsify a correct sentence. |
| AC-9 | important | A governance tool shipping to every target repo is scope leakage. |
| AC-10 | important | Requirement 5 would otherwise be an orphan. |
| AC-11 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | WITHDRAWN and the implementation REVERTED at operator direction. Six independent lanes (four delivery, two readiness) all returned WITHHELD and all converged primarily on this change; the three siblings were clean or near-clean. The guard shipped and was removed from the tree: `check_excluded_region_triggers`, its `cli.py` registration on both paths, `census_exclusion_coverage.py`, the `EXCLUDED_REL_PATHS` entry, the seed 180 phase rule and carve-out, the two `REVIEW_POLICY_SURFACE_BLOCKS` edits, and both test classes. `review_policy.py` and the rendered prompt regions verified byte-identical to HEAD afterwards | targeted reversion, no `git revert`/`checkout`; seed 180 retains only `1urlb`'s citation bullet |
| 2026-08-10 | THE INSTRUMENT IS INVERTED, found independently by four lanes and reproduced by the coordinator. `cross_platform_changed` matches the bare tokens `windows`/`macos`/`linux`, so "Reran the suite on Windows" is a BLOCKING docs-lint error whose prescribed remedy is to move the row into a digested section, which lapses every approval -- the exact churn this change exists to remove. 104-116 of the 157 corpus hits are that token alone. Meanwhile recall on the carve-out's own eight boundary categories is 0/8: "Bumped REVIEW_POLICY_EVALUATOR_VERSION, so every installed repo re-Prepares once" registers nothing | executed against the shipped producers by red-team, architecture, code, and the coordinator |
| 2026-08-10 | THE CENTRAL BARGAIN RESTS ON THE WRONG PROXY. The arithmetic is honest and reproduces (216 append rows, 13 trigger-bearing), but 6.1% measures how often a row contains one of ~24 literal substrings, NOT how often it crosses a boundary. Given 0/8 recall the two quantities are unrelated. Red-team sampled 25 of the 203 non-triggering rows and found four that cross a named carve-out boundary and register nothing -- including THIS DOCUMENT'S OWN row "Guard ships as an error rather than a warning", which changes a gate outcome. Any future revision must stop reporting 6.1% as the coverage loss | red-team 25-row sample |
| 2026-08-10 | THE CLOSED-WAVE EXEMPTION KEYS ON A MUTABLE FIELD. `wf_reopen_wave` writes `Status: active`, and `wf_prepare_wave(mode='create')` flips it too. Executed on byte-copies of `1p9j0` and `1p88t`: 0 failures while closed, 11-12 after reopen. Corpus-wide 60 of 207 closed waves arm on reopen, and because close runs a full corpus validate the wave then cannot be closed again -- with the only remedy being to rewrite archived Progress Log rows, which three separate rules forbid. The word "reopen" appears nowhere in this document | architecture and red-team, executed independently |
| 2026-08-10 | THE REGION DETECTOR WAS A SECOND IMPLEMENTATION, and Requirement 3's core claim ("the guard and the selection channel can never disagree") was true of the TRIGGER vocabulary and false of the REGION predicate. Five constructible divergences: fenced heading, fenced lookalike, fenced heading inside the body, multi-space heading form, and `## Session Handoff`. The decisive one: `normalize_session_handoff` excludes only when the body EXACTLY equals the template, and `extract_full_council_triggers(TEMPLATE_BODY)` returns `()` -- so every hit that region can produce is necessarily a false positive. The repair three lanes converged on: derive inertness from `canonical_review_policy_body` itself (present in raw text, absent from canonical), which is fence-aware and conditional for free | code, architecture, and readiness docs-contract, each executed |
| 2026-08-10 | THE TEST EVIDENCE WAS WEAKER THAN CLAIMED. QA designed 59 independent mutants: 32 killed, 27 SURVIVED (54%), all 27 confirmed against the full suite with 19 applied simultaneously. The coordinator's "12/12 killed" was true only of the 12 it chose. Decisively, `test_the_live_repository_corpus_passes` used `PROJECT_ROOT = SCRIPTS_ROOT.parents[3]`, which resolves to the repository's PARENT: it scanned zero documents and could never fail, and the same module already documents that exact trap. The guard also had zero end-to-end coverage -- unregistering it from both lint paths left the suite green | qa mutation sweep; coordinator reproduced the PROJECT_ROOT defect |
| 2026-08-10 | "Fails on zero documents today" was measured over the guard's real scope of 16 live documents, not the 824-document census corpus. At the historical base rate of 11.8%, P(zero across 16) is about 0.13. Observing zero was a coin flip, not evidence of quiet, and the decision to ship as an error rather than a warning rested on it | red-team |
| 2026-08-10 | Contract defects to fix before any re-attempt: `## Serialization Points` named `docs_lint.py` and `review_policy_reconcile.py` (both UNMODIFIED) while omitting the five files actually edited; Requirement 8 was an orphan; the census script's path and one scope determination were declared ONLY in `## Progress Log`, which is this change's own definition of a section that narrates but must not amend; and the corpus figure is 825/732/93 as of 2026-08-10, not 824/732/92 | readiness docs-contract and delivery docs-contract |
| 2026-08-10 | Implemented. The guard landed RED-FIRST: five tests written against `check_excluded_region_triggers` before it existed, all five erroring on ImportError, then green. Registered on both the incremental and full lint paths, and proven non-vacuous end-to-end by planting a violation in a live document and confirming `wf docs-lint` fails with the document, region, and trigger named | planted violation reproduced the failure; file restored byte-identical from a byte-copy |
| 2026-08-10 | Census shipped as `census_exclusion_coverage.py` with a mandatory positive control and reproduces 4 lane / 23 trigger losses, matching all three prior runs including field breakdown. The control is not decoration: re-applying the exact historical defect (positional call plus bare `except`) makes it report DID NOT FIRE on the lane channel and the script refuses to print numbers | mutation applied to a byte-copy and restored; refusal message observed |
| 2026-08-10 | AC-10 answered: the implementer-facing half lands in the `docs/prompts/implement-wave.prompt.md` renderer-owned region and the reviewer-facing half in `docs/prompts/review-wave.prompt.md`. Both are entries in `REVIEW_POLICY_SURFACE_BLOCKS`, rewritten wholesale by `reconcile_review_policy_surfaces` on every upgrade, so neither can silently no-op the way a keyed replacement pair can. `docs/prompts/implement-feature.prompt.md` was NOT used: it is reached by no update mechanism at all | both regions rendered; second pass wrote nothing |
| 2026-08-10 | A gap found while verifying AC-6 and recorded rather than fixed here: `docs-lint` passed with the `REVIEW_POLICY_SURFACE_BLOCKS` source edited and the rendered files still stale, so carrier parity is NOT enforced between block source and rendered region. The regions were reconciled explicitly. Worth its own change; out of scope here | rendered files lacked the new text while `docs-lint: ok` |
| 2026-08-10 | AC-7's pin verified non-vacuous by mutation: composing a sixth section normalization into `canonical_review_policy_body` is KILLED by the boundary test, so neither rejected exclusion can re-enter under this change's identity | mutant applied and restored byte-identical |
| 2026-08-10 | READINESS COUNCIL, both seats WITHHELD, converging independently on the same P1: the redirect instrument reproduces the measured coverage loss PROSPECTIVELY, and this plan claimed "costs zero review coverage". The coordinator reproduced it before relaying: the identical row yields `('release_or_upgrade_changed',)` and recruits `release-reviewer` in `## Decision Log`, and `()` with no lane in `## Progress Log`. The Progress Log is already excluded, so instructing authors to write there IS an exclusion applied at authoring time | both seats plus coordinator, executed against the shipped producers |
| 2026-08-10 | The P1 is answered by measurement rather than by abandoning the change: only 13 of the 214 append-after-plan-time rows (6.1%) are trigger-bearing, so 201 (93.9%) are redirectable with no coverage effect. A boundary carve-out (Requirement 2) protects the 6.1% and a mechanical guard (Requirement 3) makes the carve-out something other than author judgment | trigger detector run per-row over every later-dated Decision Log row, with a positive control |
| 2026-08-10 | The hazard is ALREADY LIVE and this change now closes it. 97 documents carry 156 trigger-bearing `## Progress Log` rows that are inert for council triggering today, from the exclusion `1uhcb` shipped. Every one is in a CLOSED wave and zero live documents are affected, which is what makes an error-level guard implementable rather than a warning | per-document scan bucketed by wave status |
| 2026-08-10 | The coordinator's earlier recommendation to NOT ship was withdrawn after the operator challenged the framing. "8.8% of rows" measured the wrong unit: churn cost is per append EVENT, each costing a re-Prepare plus a full readiness re-record, and the rate is rising (24 in May, 41 in June, 143 in July) | append events bucketed by month |
| 2026-08-10 | AC-2 of the previous revision was VACUOUS and both seats said so independently. Re-running the three historical attacks against an instrument that changes no code asserts only that unmodified code behaves as it did yesterday. The attacks are kept as a regression baseline; the relocation attack against the shipped instrument is the new obligation | red-team; docs-contract |
| 2026-08-10 | Requirement 3's carrier claim was wrong in two ways, both found by the docs-contract seat. `docs/prompts/review-wave.prompt.md` carries a renderer-owned `wavefoundry:review-policy` marker region rewritten wholesale on every upgrade — strictly better than a reconciler pair and never a silent no-op — and the file contains NO Decision Log prose to key a pair on, so the "shipped sentence" the plan referred to does not exist. Red-team independently found that a pair of the shape this plan described compounds on every upgrade (1 occurrence, then 2, then 3), violating an unwritten invariant all 13 existing pairs satisfy | docs-contract seat read `REVIEW_POLICY_SURFACE_BLOCKS`; red-team executed `reconcile_lifecycle_sections` three times against a byte-copy |
| 2026-08-10 | Corpus definition stated explicitly after a seat could not reproduce "733". The count is 732 of 824 including `docs/plans/plan-template.md`; excluding it gives 731. Neither figure was wrong, but the definition was unstated, which is what made an independently correct recount look like a discrepancy | recount under both definitions |
| 2026-08-10 | Orphans and false claims folded: Requirement 5 of the previous revision was unpinned; AC-1 and AC-2 pinned no Requirement; "each was measured" was false for three of four rejected candidates; `## Serialization Points` omitted seed 180, the primary deliverable; and the census script had no declared path while `.wavefoundry/framework/scripts/` packages by exclusion, so it would have shipped to every target repository | docs-contract coverage matrix; red-team packaging check |
| 2026-08-10 | "In the opposite direction" corrected. The split-carrier rejection is sound and STRONGER than the previous revision claimed: the same-carrier invariant is enforced at three sites, not one, and is documented as a design property in the architecture reference. The failure shape is the same direction, not the opposite | red-team |
| 2026-08-10 | A duplicate plan, `1ux18-change decision-log-excluded-from-review-policy-digest`, was written and admitted into this wave before this parked document was found, then removed and deleted. Its central requirement asserted the exclusion "alters which bytes are hashed and nothing else", which the census falsifies. The deferral note on this document existed to prevent exactly that and worked only after the fact | `wf_remove_change` executed; `1ux18` retired |
| 2026-08-08 | Split out of `1urlc` at operator direction after a council seat measured the proposed exclusion removing a full-council trigger from 21 documents and a required lane from 4, and demonstrated three author-reachable attacks including one that reinterprets an approved AC with no digest movement at all | red-team seat, 824-document differential |
| 2026-08-08 | Recorded rather than discarded, with the disproof attached, so the next attempt starts from the measurement instead of repeating the original reasoning | operator decision to split |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Ship phase routing WITH a boundary carve-out and a mechanical guard | The redirect alone reproduces the coverage loss prospectively, measured. The carve-out bounds it to the 6.1% of append rows that are trigger-bearing, and the guard makes the classification mechanical rather than author judgment. The guard also closes a live hazard the shipped Progress Log exclusion already created | Whole-region exclusion (rejected: 23 trigger and 4 lane losses); structured-rows-only (rejected: column-level normalization inside a markdown table is fragile and still inerts the row text on all three channels); split the canonical carriers (rejected: violates the same-carrier invariant enforced at three sites); redirect WITHOUT a carve-out (rejected: both readiness seats falsified its zero-coverage claim by execution); do nothing (rejected: 214 append events and rising, each costing a full readiness re-record) |
| 2026-08-10 | Guard ships as an error rather than a warning | It fails on zero live documents today, so an error costs nothing now and catches every future occurrence. A warning on a check that currently never fires is a check nobody will notice regressing | Warning (rejected: no signal); error including closed waves (rejected: 97 closed documents would fail, and closed-wave history is never rewritten) |
| 2026-08-10 | Reuse `extract_full_council_triggers` in the guard rather than a second vocabulary | A guard with its own word list can disagree with the selection channel it protects, and would drift from it silently | Hand-maintained keyword list (rejected: guaranteed drift) |
| 2026-08-10 | Deliver the rendered half through the renderer-owned region, not a reconciler pair | The pair has no anchor sentence to key on, two byte-different baselines, a compounding failure mode if it self-contains, and a single-hop miss because matches are computed against the original text. The renderer region is idempotent and cannot silently no-op | Exact-string reconciler pair (rejected on four independent grounds); whole-file rendering (rejected: `reconcile_lifecycle_prompt_baselines` is missing-only by design and overwriting project-authored prose is out of bounds) |
| 2026-08-10 | Accept the `memory_propose` consequence rather than pre-emptively extend it | Plan-time decisions with weighed alternatives are the durable-shaped evidence memory wants; implementation narration is the ephemeral half, so the signal improves | Extend `memory_propose` here (rejected: widens a seed-and-lint change into the memory subsystem on a predicted rather than observed regression) |
| 2026-08-08 | Defer rather than drop | The churn is real, framework-mandated, and the highest-frequency remaining case. What failed was the evidence order, not the goal | Ship with a stronger AC (rejected: the census belongs in front of the design); abandon (rejected: the underlying complaint stands) |
| 2026-08-08 | Require the census as reusable tooling rather than a probe | Six candidates were judged by prose and two of those judgments were wrong in opposite directions | One-off measurement (rejected: the same argument will recur) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Authors route a boundary-crossing decision into the Progress Log despite the carve-out | Requirement 3's guard fails the document and names the row; the carve-out does not depend on the author classifying correctly |
| The guard is a new failure surface and false-fails on ordinary prose | It reuses the shipped detector, so it can only fire where the selection channel would also have fired; AC-5 requires the whole current corpus pass with zero failures |
| The rule ships and authors keep writing implementation decisions into the Decision Log | Self-correcting in the direction of compliance: writing there still lapses approvals, so the cost is visible when incurred and the rule names the cheaper alternative |
| The renderer region is the wrong carrier and existing repos miss the rule | AC-6 verifies twice-run idempotence against a byte-copy of a shipped baseline rather than against the current file |
| A later change re-adds the exclusion, believing the census was never run | AC-1 records the full result and AC-7 pins the normalizer count and evaluator version, so re-adding it fails a test |
| The census tooling rots, or ships to every target repository | AC-1 requires a runnable script at a declared path; AC-9 requires the packaging decision be explicit |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
