# Withdraw the proposed separator-crossing-group cost ceiling

Change ID: `1vt2r-enh techdocs-crossing-group-cost-ceiling`
Change Status: `withdrawn`
Owner: Engineering
Status: planned
Last verified: 2026-08-21
Wave: 1vt2t techdocs-cost-ceiling-and-map-links

## Rationale

> **WITHDRAWN FROM WAVE `1vt2t` ON 2026-08-20. THE CENTRAL PREMISE BELOW IS FALSIFIED.**
> Do not implement this as written. A prepare-phase council failed it and the disqualifying
> measurement is recorded here so the next attempt starts from it rather than re-deriving it.
>
> **Crossing-group count does not predict cost.** Measured on the shipped module against
> `"/".join(["a"] * N)`:
>
> | pattern | crossing groups | @1201 | @2047 |
> | --- | --- | --- | --- |
> | `**/a/**` | 2 | 0.012s | 0.034s |
> | `**/drafts/**` | 2 | 0.019s | 0.054s |
> | `**/architecture/**` | 2 | 0.020s | 0.058s |
> | `**/a/**/*aX` | 2 | 5.97s | **29.6s** |
> | `**/a/**/b/**/c` | 3 | 2.81s | 13.7s |
>
> At the SAME count of 2 the cost spans three orders of magnitude, and count 3 is CHEAPER than
> count 2, so the metric is neither a threshold separator nor monotone. A ceiling of one refuses
> the ordinary floating `**/dir/**` form at 0.019s. What actually drives cost is whether the
> subject can FAIL to match and force full split exploration, not how many crossing fragments
> are emitted.
>
> **Three further blockers, independent of the above.**
> 1. Requirement 2 says to KEEP a "within-segment ambiguity budget" that does not exist: the tree
>    has one global `variable_groups` counter, checked once. And no count-based budget can satisfy
>    AC-1 and AC-2 together, because `*/*/*/*/*/*.md` (must ADMIT) and `/*?*?*?*?*?*?x.md` (must
>    REFUSE) both count 6. Requirement 2's "7 variable groups" figure is wrong; it is 6, and that
>    error was concealing the tie.
> 2. AC-1 refuses `**/a/**/*aX`, the subject of the bounded-runner timeout reproduction that
>    `layering-rules.md` cites as Verified evidence. Orphaning it makes that cell false. This is
>    the same defect class `1vqqj` AC-3b existed to prevent.
> 3. **The plan's own safety net could not see any of this.** AC-4 checks this repository's
>    dogfood, whose `exclude_docs` block is entirely ANCHORED (worst pattern 1 crossing group), so
>    it would have gone green while the metric was broken.
>
> **The one idea worth keeping**, from the red-team seat: charge a per-SEGMENT star count (reset
> at every literal `/` and every crossing fragment) alongside a crossing bound, because `[^/]*`
> cannot cross a separator so stars in different segments never compose. It validated against 14
> hand-picked cases. It was NOT validated against the pattern space, and it still refuses
> `**/dir/**`. **Any next attempt must begin with adversarial search over the pattern space**,
> which is what this plan's own Requirement 4 demands and what three attempts running have
> skipped. This module's cost figure has now been wrong six times, every time from generalizing a
> small sample.

`_MAX_VARIABLE_GROUPS` charges the backtracking budget on **source** variable-group count.
Measured, that number does not predict cost, so the ceiling refuses cheap patterns and admits
expensive ones. Wave `1vry5`'s readiness council produced the table (`excluded()` against
`"/".join(["a"] * 1201)`):

| pattern | source groups | post-collapse crossing groups | cost | today |
| --- | --- | --- | --- | --- |
| `*/*/*/*.md` | 4 | 0 | 0.0119s | **refused** |
| `*/*/*/*/*/*.md` | 6 | 0 | 0.0119s | **refused** |
| `**/**/**/*aX` | 4 | 1 | 0.0264s | **refused** |
| `**/**/*aX` | 3 | 1 | 0.0268s | admitted |
| `**/a/**/b/**/c` | 3 | 3 | 2.82s | admitted |
| `**/a/**/*aX` | 3 | 2 | **5.89s** | admitted |

Source-group count is uncorrelated with the cost column; crossing-group count tracks it. The
consequences are both directions of wrong: an entirely ordinary `*/*/*/*.md`, which `pathspec`
matches on a linear regex and `mkdocs.config.load_config` accepts, is refused so the run degrades
and the boundary is never computed; while `**/a/**/*aX` is admitted at 5.89s, and 27.1s at 2001
components, which is the shape that reaches the ten-second worker deadline.

**Why this is a separate change.** Wave `1vry5`'s `1vqqj` collapses adjacent floating prefixes.
That collapse was measured semantically neutral by a readiness-council PROTOTYPE (6000
patterns, 455 with changed emissions, 0 mismatches over 15000 comparisons). That is a
prototype measurement, not a delivered proof: `1vqqj` is `planned`, and its AC-2 states the
same corpus as a requirement still to be met. Calling it "proven" here would be the exact
defect class `1vqqj`'s repair cycle just closed, relocated into its follow-up and buys 212x on one shape, but it moves the worst admitted
cost by **zero**: inserting one literal character gives the non-adjacent `**/a/**/*aX`, which
costs the same before and after. `1vqqj` was deliberately kept narrow and says so. This change is
the one that would actually bound the family, and it needs the collapse to have landed first,
because the metric is defined on the POST-collapse emission.

**A recorded false start.** `1vqqj`'s Decision Log first named the deferred design as "charge for
a run of adjacent variable groups with no intervening literal separator". That metric rates
`**/a/**/*aX` at **zero** adjacent runs, since every `(?:.*/)?` is separated by the literal `a/`,
so it would admit the 5.89s shape it was supposed to catch. It is recorded here so it is not
re-proposed.

## Requirements

1. **Charge the budget on post-collapse separator-crossing groups.** A crossing group is an
   emitted fragment that can match a VARIABLE number of segments: `(?:.*/)?`, `/.*`, and the
   `.*` of a whole-segment `**`. A **literal `/` does NOT count**, and an earlier draft of this
   requirement wrongly included it, which contradicted every row of the table above and
   Requirement 3: counting literals gives `**/a/**/*aX` 4 rather than 2, `**/a/**/b/**/c` 6
   rather than 3, and this repository's `!/architecture/**` 2 rather than 1. Since the whole
   change turns on this metric predicting cost, a definition that scores a different quantity
   than the one measured would set the ceiling on the wrong thing. Count them AFTER `1vqqj`'s
   collapse, so `**/**/*aX` and `**/**/**/*aX` both count one. A ceiling of at most one crossing group admits every cheap row of the Rationale
   table and refuses exactly the two that cost seconds.

2. **Keep the within-segment ambiguity budget; the two are ADDITIVE, not alternatives.**
   `/*?*?*?*?*?*?x.md` has **zero** crossing groups and is still exponential in component length.
   **Measurement provenance, because the figures cannot come from the public path:** that
   pattern is REFUSED on the current tree (7 variable groups against a ceiling of 3), so
   `excluded()` never compiles it. The figures 0.0444s at 40 characters, 0.1592s at 50 and
   0.4308s at 60 were taken by compiling the translated regex DIRECTLY, bypassing the ceiling,
   and any re-measurement must do the same and say so. A crossing-group ceiling alone would
   admit this pattern, so both budgets must apply and a design that replaces one with the other
   is wrong.

3. **This repository's own block must stay admitted.** Its worst pattern (`!/architecture/**`) is
   one crossing group. A ceiling that degrades this repository's dogfood is a failed change, not a
   stricter one.

4. **Every bound is set by adversarial search and stated with its subject shape.** This module's
   cost figures have been falsified five times, every time by reading one point off a curve. No
   figure enters a comment, an acceptance criterion or a Risks row without naming the pattern AND
   the subject it was measured against.

## Scope

**Problem statement:** The backtracking ceiling is charged on a count that does not predict cost,
so it refuses cheap ordinary patterns and admits expensive ones.

**In scope:**

- The crossing-group metric, the ceiling, and its interaction with the existing within-segment
  budget in `_translate_pattern`.
- Re-measuring the worst admitted cost before and after, by adversarial search.
- The fidelity gap `1vqqj` deliberately defers: `*/*/*/*.md` and its family stop being refused.

**Out of scope:**

- The adjacent-prefix collapse itself, delivered by `1vqqj` in wave `1vry5`. This change depends
  on it and must not re-implement it.
- The ten-second worker deadline, which stays the enclosing aggregate guard regardless.

## Acceptance Criteria

- [~] AC-1: Every row of the Rationale table lands on the side the cost column implies:
  `*/*/*/*.md`, `*/*/*/*/*/*.md` and `**/**/**/*aX` become admitted; `**/a/**/b/**/c` and
  `**/a/**/*aX` become refused and appear in `publication.unsupported_patterns`. Each assertion
  names its current-tree polarity so the test fails before the change. **Status: intentionally not
  met — the retained measurements disprove this polarity split, so no implementation was
  authorized.**
- [~] AC-2: **Preservation check, not a gate, and labelled as such:** the within-segment budget
  still refuses `/*?*?*?*?*?*?x.md`, which has zero crossing groups. This is already true today,
  so it cannot fail before the change; it exists to catch a design that REPLACES one budget with
  the other rather than adding them. The gating half is AC-1, whose polarity flips are all
  falsifiable against the current tree. **Status: intentionally not met — the proposed additive
  two-budget design was invalidated before implementation, and the production budget remains
  unchanged.**
- [~] AC-3: **Worst admitted cost, before and after, by adversarial search**, over the same
  pattern family and subject shape, each figure naming its pattern and subject. Unlike `1vqqj`,
  this change is motivated by cost, so an unchanged worst is a FAILED change here. **Status:
  intentionally not met — there is no delivered implementation to benchmark; any replacement
  must define a new adversarial corpus and claim boundary in a new plan.**
- [~] AC-4: The boundary is otherwise unchanged: the `1vqqj` oracle differential still reports 0
  fail-open and 0 fail-closed, and this repository's dogfood still reports 62 survivors, 4 nav
  entries, 2 findings and an empty degraded list. **Status: intentionally not met — no production
  boundary was changed by this withdrawn proposal; the delivered `1vry5` evidence remains the
  applicable baseline.**
- [~] AC-5: Patterns that become ADMITTED are checked against the oracle for agreement, not merely
  for admission. Admitting a pattern and then computing a wrong boundary for it is worse than
  refusing it. **Status: intentionally not met — this design admitted no new patterns because it
  was withdrawn before implementation.**

## Tasks

- [~] Confirm `1vqqj` has landed; the metric is defined on the post-collapse emission. **Status:
  intentionally not met — the dependency landed, but this follow-up task was retired with the
  falsified design.**
- [~] Implement crossing-group counting in `_translate_pattern`, additive with the existing
  within-segment budget. **Status: intentionally not met — the proposed metric is neither
  monotone nor predictive, so implementing it would make the boundary worse.**
- [~] Re-measure the worst admitted cost before and after by adversarial search. **Status:
  intentionally not met — the readiness measurements above disqualified the design before a
  delivery benchmark was warranted.**
- [~] Re-run the oracle differential and the dogfood; verify newly admitted patterns AGREE with
  the oracle rather than merely being admitted. **Status: intentionally not met — no production
  mutation or newly admitted set exists to validate.**

## Agent Execution Graph


| Workstream | Role | Depends on | Notes |
| ---------- | ---- | ---------- | ----- |
| ws-1 crossing-group counter | implementer | — | Count post-collapse crossing fragments in `_translate_pattern`, ADDITIVE with the existing within-segment budget, never replacing it. |
| ws-2 ceiling + polarity | implementer | ws-1 | Apply the at-most-one-crossing-group ceiling; every row of the Rationale table must flip to the side its cost column implies. |
| ws-3 adversarial re-measurement | implementer | ws-2 | Worst admitted cost before and after, by search, each figure naming pattern AND subject. Unlike `1vqqj`, an unchanged worst FAILS here. |
| ws-4 oracle agreement | implementer | ws-2 | Newly ADMITTED patterns must agree with the oracle, not merely be admitted. Reuses the `tests/oracle/` harness `1vqqj` delivered. |


## Serialization Points

Declared review targets:

- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/test_techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py`

**Serialization against the sibling change:** disjoint files from `1vt2s`. The shared observable is
this repository's dogfood: AC-4 here requires 62 survivors and 4 nav entries UNCHANGED, while
`1vt2s` AC-1 requires the finding count to reach zero. Compatible, but read the dogfood after both
land rather than attributing it to whichever ran last.

## Affected Architecture Docs

N/A. The change replaces the quantity the existing backtracking budget is charged on, inside one
function of one module. It adds no dependency, moves no boundary, and changes no documented flow.
The `layering-rules.md` row for `wf techdocs-audit` describes the module as a stdlib-only
recognized-shape parser that degrades explicitly; that stays true, since this changes WHICH
patterns degrade, not the degrade mechanism. If the crossing-group metric turns out to need the
oracle at runtime rather than only in tests, that WOULD be a dependency change and this section
must be amended before that edit.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The polarity flips ARE the change. Every row names its current-tree side, so the criterion fails before the work and cannot be satisfied by a no-op, which is the defect its sibling `1vqqj` shipped in draft. |
| AC-2 | required | The two budgets must be additive. A crossing-group ceiling alone admits `/*?*?*?*?*?*?x.md`, which is exponential with zero crossing groups, so replacing rather than adding would trade one wrong ceiling for another. |
| AC-3 | required | This change is MOTIVATED by cost, unlike `1vqqj`. An unchanged worst admitted cost is therefore a failed change here, and the figure has been wrong five times when read off one point of a curve. |
| AC-4 | required | Admitting a pattern and then computing a wrong boundary for it is worse than refusing it, so agreement is checked rather than admission alone. The dogfood half guards against a stricter ceiling degrading this repository. |
| AC-5 | required | Same reason as AC-4's first clause, applied to the newly admitted set specifically: the fidelity gain is the point, and an unverified gain is not one. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-21 | Marked the change withdrawn and every AC/task intentionally not met; retained the readiness falsifier as the durable negative result. | Operator disposition after review; wave `1vt2t` withdrawal record; disqualifying measurement table above. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-21 | Withdraw rather than delete or implement `1vt2r`. | The crossing-group metric is neither monotone nor predictive, while the plan contains useful negative evidence that should not be lost. | Delete the plan (rejected: loses the falsifier); implement as written (rejected: central premise is false); replace immediately (rejected until real timeout evidence supports a new adversarially grounded design). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
