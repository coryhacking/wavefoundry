# Route implementation narration without weakening review authority

Change ID: `1us4q-bug decision-log-exclusion-gated-on-coverage-census`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-11
Wave: `20bw2 review-decision-log-churn`

## Rationale

Brief: reduce needless review-approval churn from routine implementation observations, while preserving all material plan amendments and independent review authority. This revises the parked 1us4q approach after the operator requested a wave; the August failed/reverted implementation and contradictory historical evidence below remain unchanged. Their numbers describe that historical corpus, not the current repository.

Current code still hashes Decision Log text, while canonical Progress Log narration is excluded. A four-case probe of actual `policy_input_digest`, `select_required_review_lanes` and `extract_full_council_triggers` confirms a routine Windows test observation changes the digest and council trigger in Decision Log, leaves both unchanged in Progress Log, and a material requirement amendment still moves the digest and recruits its council triggers. Existing seed 180 already says an excluded section narrates rather than amends, but its participant state-leaving bullet still directs implementation records into both logs indiscriminately. Correct that contradictory instruction and carry clear examples through existing managed implementation/review regions. Do not revive the falsified whole-region exclusion or keyword-based blocking guard.

## Requirements

1. Distinguish plan decisions from implementation narration. Keep weighed plan choices and material decisions in Decision Log. Put test observations, repair progress, evidence locations and continuation notes in the canonical Progress Log or existing session handoff. Remove the seed-180 participant instruction that directs implementation narration indiscriminately into both logs.
2. A change to scope, requirements, acceptance, task meaning, priority, review targets or authority must update its existing owning digested section before or with the narration. The Progress Log may link or summarize that edit; it must never substitute for it. Material changes continue through existing re-Prepare and affected readiness approval rules. A new material design choice may still need Decision Log, and that legitimate receipt rotation remains intentional.
3. Publish concise routing guidance and paired ordinary-observation/material-amendment examples through the existing `REVIEW_POLICY_SURFACE_BLOCKS` implementation and review entries. Render local carriers with the existing reconciler/renderer; twice-run reconciliation in scratch must preserve authored prose outside managed regions and stop changing bytes after the first pass. No new whole-file overwrite, template, sidecar or upgrade pass.
4. Preserve `canonical_review_policy_body`, its existing section/carrier normalizations, policy snapshot hashing, lane selection, council trigger/seat selection and evaluator version. Their implementations and policy semantics are read-only in this wave; editing managed prose in review_policy.py is not permission to edit its evaluator functions. Do not exclude Decision Log or add a substring guard, lint sensor, blanket error, census utility or persistent evidence file.
5. Verification shall distinguish observations in the two log locations, material edits to digested sections, and unsupported/ambiguous Progress Log headings. Use declared and undeclared review-target fixtures, ordinary platform test narration and material authority changes. Assertions must test the actual producer channels, not treat lexical trigger recall as a semantic completeness guarantee. Historical archived records remain byte-identical, including after scratch reopen; no backfill or rewrite of old log rows.
6. Update the architecture explanation and developer guidance to state the routing rule, intentional material receipt rotation and honest limitation: guidance and existing review enforce authoring discipline; this wave does not automatically discover semantic amendments hidden only in narration. Consumer upgrades receive existing managed-region refresh only, with no source suites, corpus census or historical maintenance.

## Scope

**Problem statement:** contradictory authoring guidance sends ordinary implementation observations into a digested decision carrier and needlessly rotates readiness receipts.

**In scope:** seed 180 participant guidance; the implementation/review managed policy prose in review_policy.py; existing renderer-driven local implementation/review surfaces; targeted routing, policy and carrier regression tests; architecture and contributing guidance.

**Out of scope:** changing review-policy canonicalization or evaluator semantics; automatic natural-language amendment detection; a new lint/close/readiness gate; automatic approval transfer; historical corpus rewrite; memory-input expansion; native host hooks; any implementation before independent readiness.

**Protected surfaces and ownership:** implementer owns named seed/prose/tests after readiness and the applicable gates open. Code, QA, architecture, security and docs-contract reviewers are read-only. Existing policy algorithms, historical waves/events and unrelated generated surfaces stay unchanged.

## Acceptance Criteria

- [x] AC-1: Canonical seed and managed implementation/review guidance distinguish routine narration from weighed/material decisions and name owning-section amendment plus re-Prepare obligations, with paired examples that do not weaken the existing narrate-not-amend rule.
- [x] AC-2: Actual policy fixture outcomes show routine Progress Log observations preserve receipt inputs/selected lanes/council decisions, Decision Log edits remain digested, and material owning-section changes rotate inputs and retain affected review/council recruitment. Both declared and legacy undeclared targets are exercised, including ambiguous headings; assertions can distinguish a broken producer or misleading routing claim.
- [x] AC-3: Real carrier reconciliation updates an existing shipped scratch baseline, preserves customization outside managed regions, validates the resulting carriers and is byte-idempotent on the second run under the existing profile-aware keys.
- [x] AC-4: No canonicalizer/evaluator algorithm or version, new gate, source qualification during upgrade, historical record or memory-input contract changes; targeted source/differential checks establish the protected boundaries and scratch reopen does not require history edits.
- [x] AC-5: This change's own tests and every test it adds pass; authored/edited documents validate; current architecture/developer guidance reports the narrower benefit and semantic-detection limitation accurately.

## Tasks

- [x] Update seed and existing managed prose, then regenerate only directly affected carriers.
- [x] Add focused producer/routing and real carrier/idempotence coverage with meaningful negative controls.
- [x] Verify protected algorithms, historical bytes and profile-compatible carrier behavior.
- [x] Update architecture/contributing explanations and consolidate delivery evidence in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| plan/source diagnosis | coordinator | — | Current producer probe; failed history retained |
| guidance and carriers | implementer | readiness | Named source/prose only; source/seed gates |
| regressions and docs | implementer | guidance | Targeted controls; no blanket corpus instrumentation |
| independent review | required lanes and council-chair | draft | Fresh contexts; readiness only now |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`
- `docs/prompts/implement-wave.prompt.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/contributing/change-workflow.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: retain the shared canonical-carrier contract and explain narration routing without claiming a new exclusion. `docs/contributing/change-workflow.md`: paired examples and meaningful amendment/re-Prepare rule. No hub restructuring.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Corrects contradictory instructions at source and existing-target carriers. |
| AC-2 | required | Separates harmless narration from intentional contract/authority rotation. |
| AC-3 | required | Existing targets must receive guidance without customization loss or repeated work. |
| AC-4 | required | The previous guard and exclusion demonstrably weakened or broke review. |
| AC-5 | required | Own verification and honest contracts are the delivery obligation. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-11 | Readback: route ordinary implementation observations to canonical Progress Log/existing handoff; keep weighed/material choices in Decision Log and amend owning digested sections before or with narration, with existing re-Prepare rules. Example: reran tests on Windows stays narration; changed release/approval authority updates Requirements and intentionally rotates readiness. AC-1–5; seed180, managed implementation/review prose, two prompts, focused tests and two explanatory docs only. MCP-first reads and pre-implementation memory briefing consumed. | Activated/readied 20bw2; evaluator/canonicalizer/version/history remain protected. |
| 2026-10-10 | Replanned at operator request. Current actual four-case producer probe: base/progress digest b9d81548 equal, routine Decision Log f34fc06a differs and adds cross_platform_changed, owning material requirement 520217a4 differs and adds release/failure triggers. Declared code-review roster stays intact. No source/seed edit, future behavior or full semantic recall claimed. | Temporary /private/tmp/wf-next-waves-pack/churn-baseline.json; exact actual helpers named in Rationale; reviewers will independently replay. |
| 2026-10-10 | Divergent pre-plan and optional Review plan: selected phase-aware authoring with owning-section rule and existing managed refresh. Whole-log exclusion loses coverage; keyword guard false-fails narration and misses semantics; new structured decision subsystem adds unjustified migration/retention overhead. All current requirement/scope branches self-answered from current policy and August disproof. Stop condition: independent readiness, then no implementation until explicitly requested. | Seed180 narrate-not-amend and participant bullet; gardener_metadata.canonical_review_policy_body; review_policy source. |


| 2026-10-11 | Observe: seed180 participant state-leaving instruction now routes routine narration to canonical Progress Log/existing handoff and material choices to Decision Log, requiring owning-section amendment and existing re-Prepare rules. Existing managed implementation/review regions carry paired examples and semantic-detection limitation. Only the two directly affected prompts regenerated; second production renderer pass returned no writes. | AC-1/3; REVIEW_POLICY_SURFACE_BLOCKS; reconcile_review_policy_surfaces; ImplementationNarrationGuidanceTests. |
| 2026-10-11 | Observe: actual digest, lane and Council producers distinguish ordinary platform narration in Progress/Decision logs, material authority/target amendments, unsupported/duplicate headings and hidden-only material narration. Focused policy suite 115/115 and shipped-reference suite 28/28 pass; four new producer/carrier tests also pass after apply_profile(second) in a copied tree. Five faithful controls fail by assertion: remove progress exclusion, add whole Decision Log exclusion using existing normalizer, empty Council producer, omit release lane, no-op carrier renderer. The original contradictory participant instruction and prior managed blocks fail new source/carrier expectations before repair. | AC-2/3/5; ImplementationNarrationRoutingTests (platform observation, material amendment, ambiguous headings, shipped carrier refresh); temporary /private/tmp/wf-20bw2-controls.py. |
| 2026-10-11 | Observe: protected review_policy module AST matches pre-edit except REVIEW_POLICY_SURFACE_BLOCKS; gardener_metadata bytes and evaluator version unchanged. Preserved August history in this document remains byte-identical to HEAD. Production scratch reconciliation retains historical member bytes; root independently invoked actual wf_reopen_wave_response on a closed scratch legacy wave, transitioned it active and preserved its historical member byte-identically (SHA256 b341fad7c5e5b1650382170e9e68d9b1567a382f6995e5087be37fb9fe7b5c22); requested refresh touched wave.md only. | AC-4; policy_input_snapshot/select_required_review_lanes/extract_full_council_triggers unchanged; root actual-handler scratch control; no live history/index mutation. |
| 2026-10-11 | Delivery handoff: source frozen after focused checks; full wf_validate_docs passed with no errors/warnings. Architecture/developer explanations state intentional material receipt rotation, existing managed consumer refresh and no automatic semantic-amendment detection. Full canonical qualification and independent required lanes remain coordinator-owned; no approval, closure, commit, push or release claimed. Temporary captures/baselines stay outside repo. | AC-5; docs/architecture/data-and-control-flow.md; docs/contributing/change-workflow.md; reviewed files named in Serialization Points. |

| 2026-10-11 | Final boundary validation: own authored/edited documents have no lint errors. Earlier full wf_validate_docs passed; repeated full validation after final bookkeeping is blocked only by concurrently created unrelated 20d90/20d91/20d92 wave.md Watchpoints lacking required watchpoint/block/follow-up language. AC-5 remains change-local; no unrelated file was edited. Coordinator notified of exact external remedy. | Full wf_validate_docs structured errors contain only those three external wave records; no attributable failure. |

### Preserved failed-attempt history

The following August entries are historical observations and contradictions; their claims are not current requirements or measurements.

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
| 2026-08-10 | AC-10 answered: the implementer-facing half lands in the `docs/prompts/implement-wave.prompt.md` renderer-owned region and the reviewer-facing half in `docs/prompts/review-wave.prompt.md`. Both are entries in `REVIEW_POLICY_SURFACE_BLOCKS`, rewritten wholesale by `reconcile_review_policy_surfaces` on every upgrade, so neither can silently no-op the way a keyed replacement pair can. `docs/prompts/implement-change.prompt.md` was NOT used: it is reached by no update mechanism at all | both regions rendered; second pass wrote nothing |
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

The August choices below were rejected by their subsequent failed review and reversion. They remain historical; the final current choice follows the table.

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Ship phase routing WITH a boundary carve-out and a mechanical guard | The redirect alone reproduces the coverage loss prospectively, measured. The carve-out bounds it to the 6.1% of append rows that are trigger-bearing, and the guard makes the classification mechanical rather than author judgment. The guard also closes a live hazard the shipped Progress Log exclusion already created | Whole-region exclusion (rejected: 23 trigger and 4 lane losses); structured-rows-only (rejected: column-level normalization inside a markdown table is fragile and still inerts the row text on all three channels); split the canonical carriers (rejected: violates the same-carrier invariant enforced at three sites); redirect WITHOUT a carve-out (rejected: both readiness seats falsified its zero-coverage claim by execution); do nothing (rejected: 214 append events and rising, each costing a full readiness re-record) |
| 2026-08-10 | Guard ships as an error rather than a warning | It fails on zero live documents today, so an error costs nothing now and catches every future occurrence. A warning on a check that currently never fires is a check nobody will notice regressing | Warning (rejected: no signal); error including closed waves (rejected: 97 closed documents would fail, and closed-wave history is never rewritten) |
| 2026-08-10 | Reuse `extract_full_council_triggers` in the guard rather than a second vocabulary | A guard with its own word list can disagree with the selection channel it protects, and would drift from it silently | Hand-maintained keyword list (rejected: guaranteed drift) |
| 2026-08-10 | Deliver the rendered half through the renderer-owned region, not a reconciler pair | The pair has no anchor sentence to key on, two byte-different baselines, a compounding failure mode if it self-contains, and a single-hop miss because matches are computed against the original text. The renderer region is idempotent and cannot silently no-op | Exact-string reconciler pair (rejected on four independent grounds); whole-file rendering (rejected: `reconcile_lifecycle_prompt_baselines` is missing-only by design and overwriting project-authored prose is out of bounds) |
| 2026-08-10 | Accept the `memory_propose` consequence rather than pre-emptively extend it | Plan-time decisions with weighed alternatives are the durable-shaped evidence memory wants; implementation narration is the ephemeral half, so the signal improves | Extend `memory_propose` here (rejected: widens a seed-and-lint change into the memory subsystem on a predicted rather than observed regression) |
| 2026-08-08 | Defer rather than drop | The churn is real, framework-mandated, and the highest-frequency remaining case. What failed was the evidence order, not the goal | Ship with a stronger AC (rejected: the census belongs in front of the design); abandon (rejected: the underlying complaint stands) |
| 2026-08-08 | Require the census as reusable tooling rather than a probe | Six candidates were judged by prose and two of those judgments were wrong in opposite directions | One-off measurement (rejected: the same argument will recur) |

Current selection (2026-10-10): phase-aware authoring plus existing managed guidance, because it removes the contradictory instruction without hiding reviewable text or imposing a new false-positive gate. Rejected alternatives: whole Decision Log exclusion (proven coverage loss), keyword guard (false positives and semantic misses), new decision record format (migration/retention overhead).

## Risks

| Risk | Mitigation |
| --- | --- |
| Authors hide an amendment in narration | Preserve owning-section rule, independent review and explicit no-automatic-semantic-detection limit. |
| Guidance is shipped only to fresh installs | Existing managed implementation/review blocks and real twice-run scratch carrier checks. |
| Old rejected requirements are mistaken for current intent | Historical entries explicitly labelled; current numbered requirements and five ACs govern. |
| A test merely repeats the producer implementation | Use distinct material/observation outcomes and faithful known-bad controls at delivery. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
