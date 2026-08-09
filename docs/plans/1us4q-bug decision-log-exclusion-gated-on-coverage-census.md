# Decision Log Exclusion, Gated On A Coverage Census

Change ID: `1us4q-bug decision-log-exclusion-gated-on-coverage-census`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-08
Wave: TBD (deferred; not admitted)

> **Deferred deliberately.** This change was originally part of `1urlc` in wave `1uprb` and was removed from it when council measurement showed the exclusion removes real review coverage. It is parked here with that measurement so the work is not lost and is not repeated from scratch. Do not admit it into a wave until the census in AC-1 has been run and its result argued.

## Rationale

Appending a `## Decision Log` row to a change document moves `policy_input_digest` and lapses every recorded review approval, without any load-bearing claim changing. The framework **instructs** the edit: seed `180-implement-feature.prompt.md` tells participants to "leave enough state in wave artifacts (Progress Logs, Decision Logs, the session handoff) for another agent to continue safely", and `memory_propose` drafts from Decision Logs. The Progress Log half of that sentence is excluded; the Decision Log half lapses the approvals the same wave just collected. `## Decision Log` is present in roughly 725 of the corpus's change documents, so the churn is broad.

**Why it was pulled out of `1urlc`.** The earlier plan analyzed one hiding vector (an acceptance criterion reinterpreted without editing the AC) and judged the risk bounded. A council seat measured the exclusion on the two policy-output channels the plan never checked, across 824 change documents:

| Candidate | Documents losing a full-council trigger | Documents losing a required lane |
| --- | ---: | ---: |
| Session Handoff (shipped in `1urlc`) | 0 | 0 |
| **Decision Log (this change)** | **21** | **4** |
| `## Risks` (declined) | 5 | 8 |
| `## AC Priority` rationale (declined) | 0 | 0 |
| `## Affected Architecture Docs` (declined) | 22 | 185 |
| `## Serialization Points` prose (declined) | 0 | 14 |

The mechanism: `extract_full_council_triggers` consumes the **canonical** change text, and for a document that declares no Serialization Points targets, `select_required_review_lanes` builds its whole-document corpus from the canonical body too. Text inside an excluded region becomes inert on both channels. Lost trigger fields were `cross_platform_changed` (13), `failure_or_readiness_semantics_changed` (4), `release_or_upgrade_changed` (2) and `contract_or_required_ac_semantics_changed` (2). Named casualties include `1p3ay-feat upgrade-migration-for-1-5-0-breaking-changes.md`, which loses `release-reviewer` because its Decision Log row is the one naming `upgrade_wavefoundry.py`.

Three executed author attacks, against a clean declared base:

```
ATTACK 1  row: "...the trust boundary moves but only for local renders"
   TODAY : triggers=['trust_boundary_changed']     delivery_council_required=True
   AFTER : triggers=[]                             delivery_council_required=False

ATTACK 2  row: "Ship the new seed text inside the release artifact..."
   TODAY : triggers=['release_or_upgrade_changed'] delivery_council_required=True
   AFTER : triggers=[]                             delivery_council_required=False

ATTACK 3  row: "Read AC-5 as satisfied by a spot check rather than a full count"
   TODAY : digest moves = True
   AFTER : digest moves = False
```

Attack 3 falsifies the original dismissal directly: no AC text changed and no `[~]` marker changed, so nothing else churned either.

**The value is still real.** This is a framework-mandated edit that lapses approvals, and it is the single highest-frequency such edit remaining after `1urlc`. The question is not whether to fix it but whether an exclusion is the right instrument, and that must be answered by measurement placed **in front of** the change rather than behind it.

## Requirements

1. **A differential coverage census gates the change.** Before any exclusion ships, compute `required_lanes`, `delivery_council_required` and the selected council seats for every change document in the corpus, with and without the exclusion. Every difference is enumerated by document and by field. If the differences cannot each be justified by name, the exclusion does not ship in that form.

2. **Consider instruments other than a whole-region exclusion**, because the census makes plain that region exclusion trades review coverage for churn reduction. At least these:
   - **Structured rows only.** Exclude the `| Date | Decision | Reason | Alternatives |` table rows and nothing else, so prose added under the heading still digests.
   - **Sentinel the narration, keep the trigger surface.** Canonicalize Decision Log rows for the digest but continue to feed the raw text to `extract_full_council_triggers` and the whole-document lane fallback. This removes the churn without removing coverage, and is the only candidate that does not trade one for the other.
   - **Do nothing, and fix the instruction instead.** Seed 180 could direct implementation-time decision narration to the Progress Log, which is already excluded and already carries the must-not-amend discipline, leaving the Decision Log for plan-time decisions that legitimately are part of the approved contract.

3. **Reconsider `## AC Priority` rationale in the same pass.** It measured 0 trigger losses and 0 lane losses, better than the candidate that was accepted elsewhere, and was declined only because a column-level exclusion inside a markdown table is structurally fragile. A section-level mechanism may make it both safe and cheap, in which case it is a better first exclusion than this one.

4. **Whatever ships carries the must-not-amend discipline.** Any newly excluded region must be named in seed 180's "narrates; must not amend" rule in the same change, so the discipline and the exclusion set never drift apart.

## Scope

**Problem statement:** A framework-mandated recordkeeping edit lapses review approvals, and the obvious fix removes measurable review coverage from real documents.

**In scope:**

- The differential census and its tooling, which is reusable for any future exclusion proposal.
- Whichever instrument the census supports.
- Seed 180 discipline text for the region that ships, if any.

**Out of scope:**

- Anything already delivered by `1urlc`.
- The `serialization_point_paths` extractor lapse path.

## Acceptance Criteria

- [ ] AC-1: The differential census runs across the whole corpus and its full result is recorded in this document before any exclusion is implemented. Chosen instrument shows **zero** unjustified differences in `required_lanes`, `delivery_council_required` and council seats.
- [ ] AC-2: The three author attacks recorded in the Rationale are re-run against the chosen instrument and each is either prevented or explicitly accepted with a reason.
- [ ] AC-3: If the shipped instrument is an exclusion, appending a Decision Log row no longer moves `policy_input_digest`, reproduced red-first.
- [ ] AC-4: The must-not-amend discipline in seed 180 names the newly excluded region.
- [ ] AC-5: The full framework suite and docs-lint pass.

## Tasks

- [ ] Build the differential census as reusable tooling, not a one-off probe.
- [ ] Run it for each candidate instrument in Requirement 2, plus `## AC Priority` per Requirement 3.
- [ ] Record every result here, including the ones that argue against shipping.
- [ ] Implement whichever instrument the census supports, or record that none does.
- [ ] Update seed 180's discipline text if a region is excluded.
- [ ] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census-tooling | implementer | — | Reusable; gates everything else |
| instrument-eval | implementer | census-tooling | One run per candidate in Requirement 2 |
| implement | implementer | instrument-eval | Only if the census supports an instrument |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/gardener_metadata.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`

## Affected Architecture Docs

`N/A` pending the census. If an exclusion ships, `docs/architecture/data-and-control-flow.md`'s normalizer description needs the same update `1urlc` makes for its own region.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The gate. This change exists because the measurement was taken after the design rather than before it. |
| AC-2 | required | The three attacks are the concrete disproof of the original risk argument; any instrument must answer them. |
| AC-3 | important | Only meaningful if the census supports an exclusion at all. |
| AC-4 | required | An excluded region without the discipline is how an amendment becomes invisible. |
| AC-5 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-08 | Split out of `1urlc` at operator direction after a council seat measured the proposed exclusion removing a full-council trigger from 21 documents and a required lane from 4, and demonstrated three author-reachable attacks including one that reinterprets an approved AC with no digest movement at all | red-team seat, 824-document differential |
| 2026-08-08 | Recorded rather than discarded, with the disproof attached, so the next attempt starts from the measurement instead of repeating the original reasoning. The census tooling is the deliverable that makes any future exclusion proposal cheap to judge | operator decision to split |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-08 | Defer rather than drop | The churn is real, framework-mandated, and the highest-frequency remaining case. What failed was the evidence order, not the goal | Ship with a stronger AC (rejected: the census belongs in front of the design); abandon (rejected: the underlying complaint stands) |
| 2026-08-08 | Require the census as reusable tooling rather than a probe | Six candidates were judged by prose and two of those judgments were wrong in opposite directions. A cheap differential makes the next exclusion argument evidence-led by default | One-off measurement (rejected: the same argument will recur) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The census is run and its result argued away | AC-1 requires zero **unjustified** differences and enumeration by name, so a difference must be defended individually rather than in aggregate |
| The exclusion ships and quietly removes coverage | AC-2 re-runs the three recorded attacks against whatever instrument is chosen |
| Deferral becomes abandonment | The churn is framework-mandated by seed 180, so the complaint recurs on its own; this document holds the measurement so the next attempt is cheap |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
