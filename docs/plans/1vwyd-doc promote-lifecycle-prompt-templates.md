# Promote lifecycle prompt templates to canonical documents

> **WITHDRAWN 2026-08-21 by prepare-council BLOCK (wave `1vwyc`). Do not revive this plan as written.**
>
> Both council seats falsified its central premise independently. The premise was that the shipped
> lifecycle templates are `{{generated_at}}` skeletons and target copies hold the real content.
>
> **1. The direction is inverted.** The templates are the maintained side: six commits since
> 2026-07-17, carrying 23 to 41 lines each that this repository's copies lack, including the
> automatic-lane-derivation contract that seed-160 mandates and which `git log -S` proves
> `docs/prompts/prepare-wave.prompt.md` has never held. `{{generated_at}}` is not a skeleton marker
> at all: wave `1viyu` added it on 2026-08-17 so freshly materialized carriers pass `check_metadata`.
> This plan read a four-day-old deliberate fix as evidence of neglect.
>
> **2. The magnitude was an artifact of the measuring method.** "Rendering would delete about half"
> came from comparing raw template files against rendered repo copies, which double-counts the fenced
> regions the renderer re-inserts in the same pass (`_upsert_review_policy_region` appends when
> markers are absent). A real render into a scratch tree, non-blank lines, fresh against this repo:
>
> | doc | fresh render | repo copy | ratio | this plan claimed |
> | --- | ---: | ---: | ---: | ---: |
> | review-wave | 85 | 87 | 0.98 | 0.45 |
> | create-wave | 76 | 82 | 0.93 | 0.40 |
> | prepare-wave | 60 | 65 | 0.92 | 0.58 |
> | implement-wave | 35 | 42 | 0.83 | 0.60 |
> | close-wave | 39 | 57 | 0.68 | 0.53 |
> | memory-review | 82 | 82 | 1.00 | 1.00 |
>
> The `memory-review` control reproduces under both methods, which is what validates the corrected
> one. Content loss is real but concentrated in `close-wave`, and is nowhere near half.
>
> **3. AC-2 and AC-5 were satisfiable-but-wrong.** AC-2's phrase-matching traceability drops
> reworded content (the seed-190 line 19 operator-consent rule appears in zero seeds as "assumed
> consent") and renderer-sourced content (invisible from the template side, which carries zero
> marker lines), and its "or a recorded authoring decision" branch made it unfalsifiable. AC-5
> guarded target-to-template loss only, so it passes on a promoted `close-wave` shipping without the
> operator-consent gate, because the baseline lacks it too.
>
> **4. The leak census was incomplete.** The `run_tests.py` instruction is in two of six documents
> (`close-wave` line 42 and `implement-wave` line 48), not one.
>
> **If this work is revived**, both seats agreed its first deliverable must be a published three-way
> instruction inventory per document (target-only, template-only, contradictory) rather than authored
> prose. Four contradictions are already known from one target: change-doc location during planning,
> whether an empty memory capture blocks close, the re-prepare threshold, and close dry-run ordering.
> Until those have named winners, "promote the templates" is not a reviewable documentation task.
> Three shipped tests constrain these files and must be named as targets:
> `test_render_agent_surfaces.MemoryReviewPromptTests.test_prompt_contract_and_known_bad_controls`,
> `test_events_only_residue_census.test_no_live_surface_retains_preimplementation_review_gate`, and
> `test_build_pack.test_lifecycle_prompt_baselines_ship_in_framework_tree`.


Change ID: `1vwyd-doc promote-lifecycle-prompt-templates`
Change Status: `withdrawn`
Owner: Engineering
Status: planned
Last verified: 2026-08-21
Wave: 1vwyc prompt-surface-correctness

## Rationale

The framework has no canonical source for its own lifecycle workflow content.

The six prompts under `.wavefoundry/framework/install/lifecycle-prompts/` ship as
`{{generated_at}}` starter skeletons. The copies that actually govern behavior in each target are
the accumulated current workflow, built up by upgrade-time agent reconciles across many releases.
The framework ships the skeleton; the workflow exists only as per-target sediment.

Measured in this repository, non-stamp lines, template against repo copy:

| Prompt | Template | This repo | Solaris | Diff lines here |
| --- | --- | --- | --- | --- |
| `review-wave` | 49 | 109 | 97 | 136 |
| `prepare-wave` | 52 | 90 | 69 | 120 |
| `create-wave` | 40 | 99 | 85 | 109 |
| `close-wave` | 39 | 74 | 49 | 89 |
| `implement-wave` | 36 | 60 | 60 | 70 |
| `memory-review` | 94 | 94 | 97 | 0 |

`memory-review` is the control: materialized recently, nothing has accreted onto it, and it matches
its template exactly. The other five diverge, and they diverge by different amounts in different
repositories, which is the direct evidence that no two targets are running the same lifecycle
instructions.

The accreted content is framework content, not local invention. Distinctive phrases in it resolve
back into the seed corpus: `AC scope gap` appears in 3 seeds, `Salience` in 22, `readiness
evaluation` in 9. The reconciling agent was reading seeds and synthesizing prompt docs. That
synthesis was never captured anywhere shippable.

Three consequences, all live today:

1. **Targets diverge from each other and from the framework's intent**, silently, and the drift
   grows with every release.
2. **`1vvs3` cannot cover the six documents that matter most.** Rendering from a skeleton means
   truncating about half of five documents, so the six lifecycle prompts were excluded and the
   render-from-source change now reaches only the 12 secondary docs.
3. **A new target gets the skeleton**, not the workflow, and only accumulates the real instructions
   if and when a later upgrade's reconcile step happens to fire.

This change authors the canonical documents so that the framework ships what it actually means.

## Requirements

1. Produce canonical current content for all six lifecycle prompts, shipped at
   `.wavefoundry/framework/install/lifecycle-prompts/`, replacing the skeletons.
2. Establish the authority for that content explicitly. This repository's copies are the most
   accreted baseline available, but they are one target's sediment and are not authoritative by
   virtue of being longest. Every load-bearing instruction in a promoted template must be traceable
   to a seed, a policy carrier obligation, or a deliberate authoring decision recorded here.
3. Remove content that is specific to this repository and must not ship to targets. A confirmed
   example: `docs/prompts/close-wave.prompt.md` instructs the reader to run
   `python3 .wavefoundry/framework/scripts/run_tests.py`, which is this framework's own suite and
   is wrong in any target repository.
4. Keep genuinely framework-internal references that targets also hold. Paths such as
   `.wavefoundry/framework/seeds/020-run-contract.prompt.md` exist in every installed target and are
   correct; the rule is target-validity, not the absence of `.wavefoundry/` strings.
5. Provide parameterization points where a target must supply its own commands or paths, rather than
   hardcoding this repository's answers or forcing each target to hand-edit after materialization.
6. Preserve the review-policy marker-fenced regions. Five of the six carry fences whose content is
   renderer-owned and blind-replaced; promotion must not freeze rendered content into the template.
7. Do not regress coverage. A promoted template must not drop an instruction that any measured
   target copy currently carries, unless dropping it is a recorded decision.

## Scope

**Problem statement:** the framework's lifecycle workflow content exists only as accumulated
per-target sediment, so the shipped templates are skeletons, targets diverge from each other, and no
change can render these documents from source.

**In scope:**

- Authoring canonical content for the six lifecycle prompts.
- The authority and traceability method that justifies each promoted instruction.
- Scrubbing repository-specific content, and the target-validity rule that distinguishes it from
  legitimate framework-internal references.
- Parameterization points for target-supplied commands and paths.
- A coverage comparison against the measured target copies.

**Out of scope:**

- The rendering mechanism itself. That is `1vvs3`, which consumes these templates once they exist.
- Bringing the six documents into `1vvs3`'s render set. That is a scope decision for `1vvs3` after
  this lands, not an automatic consequence.
- The 12 seed-sourced prompt docs, which already have canonical sources.
- Changing lifecycle workflow behavior. This captures what the workflow already is; a deliberate
  behavior change belongs in its own change with its own review.

**Ordering within the wave:** `1vwyb` first (seed citations must resolve before any content that
cites them is promoted), then `1vwyd`, then `1vvs3`.

## Acceptance Criteria

- [ ] AC-1: All six shipped templates are canonical current documents. No `{{generated_at}}`-only
      skeleton remains, with the placeholder itself retained where metadata stamping needs it.
- [ ] AC-2: Every load-bearing instruction in each promoted template traces to a seed, a policy
      carrier obligation, or a recorded authoring decision. Traceability is recorded per document,
      not asserted in aggregate.
- [ ] AC-3: No promoted template instructs a target to run this repository's own tooling. Proven by
      the `run_tests.py` case being absent and by a review of every command the templates contain.
- [ ] AC-4: Legitimate framework-internal references that targets also hold are retained, proven by
      resolving each referenced path against a target repository rather than against this one.
- [ ] AC-5: Coverage does not regress: for each of the six, no instruction present in a measured
      target copy is missing from the promoted template without a recorded decision.
- [ ] AC-6: Marker-fenced regions remain renderer-owned. A render after promotion does not fight the
      template, verified by rendering twice and diffing.
- [ ] AC-7: A fresh materialization into a scratch repository produces a document that is complete
      enough to follow, tested by walking one lifecycle step from the materialized text alone.
- [ ] AC-8: Parameterization points are declared, and a target that supplies nothing still gets a
      usable document rather than an unresolved placeholder.

## Tasks

- [ ] Assemble the per-document baseline: this repo's copy, the measured target copies, and the
      seed and policy-carrier content each instruction traces to.
- [ ] Author the six canonical templates from that baseline (gate: `seed_edit_allowed` if any seed
      text moves; the templates themselves live under `install/`, not `seeds/`).
- [ ] Record traceability per document per AC-2.
- [ ] Scrub repository-specific content per AC-3 and apply the target-validity rule from AC-4.
- [ ] Declare parameterization points and their no-input behavior.
- [ ] Run the coverage comparison for AC-5 and record every deliberate drop.
- [ ] Verify fence behavior by rendering twice and diffing.
- [ ] Materialize into a scratch repository and walk one lifecycle step from the text alone.

## Agent Execution Graph


| Workstream         | Owner             | Depends On      | Notes |
| ------------------ | ----------------- | --------------- | ----- |
| baseline-assembly  | implementer       | (`1vwyb` landed) | Gathers this repo's copies, target copies, and seed provenance per instruction. |
| authoring          | technical-writer  | baseline-assembly | The content work; six documents. |
| scrub-and-params   | implementer       | authoring       | Target-validity rule plus parameterization declaration. |
| traceability       | docs-contract     | authoring       | Owns AC-2; verifies per document, not in aggregate. |
| verification       | qa                | scrub-and-params | Coverage comparison, double-render fence check, scratch materialization walk. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/install/lifecycle-prompts/`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `docs/prompts/close-wave.prompt.md`
- `docs/prompts/create-wave.prompt.md`
- `docs/prompts/implement-wave.prompt.md`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/memory-review.prompt.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/data-and-control-flow.md` describe the
prompt surface and where its content originates. Both need the correction that lifecycle prompt
content becomes framework-canonical rather than per-target accumulated, because that is a change in
where authority for the workflow lives, not an implementation detail.

## AC Priority


| AC   | Priority       | Rationale |
| ---- | -------------- | --------- |
| AC-1 | required       | The deliverable. Without it nothing downstream changes. |
| AC-2 | required       | Length is not authority. Untraceable content promoted to canonical would ship one repository's habits to every target as if they were framework intent. |
| AC-3 | required       | A confirmed leak exists today; promoting it verbatim would tell every target to run this framework's test suite. |
| AC-4 | important      | Over-scrubbing is the opposite failure and would strip correct references that targets rely on. |
| AC-5 | required       | Promotion that silently drops instructions is the same truncation failure `1vvs3` AC-9 exists to prevent, arriving one layer earlier. |
| AC-6 | required       | Freezing rendered content into a template creates a fight between two writers of the same bytes. |
| AC-7 | important      | The only AC that tests whether the result is usable rather than merely complete. |
| AC-8 | important      | Determines whether a target that supplies nothing gets a working document or a broken one. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-21 | Planned after two target measurements showed the shipped templates are skeletons. | Non-stamp line counts, template against this repo: review-wave 49/109, prepare-wave 52/90, create-wave 40/99, close-wave 39/74, implement-wave 36/60; memory-review control 94/94, diff 0. |
| 2026-08-21 | Leak risk confirmed before authoring begins. | `docs/prompts/close-wave.prompt.md` line 42 instructs `python3 .wavefoundry/framework/scripts/run_tests.py`, which is this framework's own suite. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------- | ------------ |
| 2026-08-21 | Promote rather than exclude the six from rendering permanently. | These are the documents that most need to stay current. Leaving them unsourced means the render-from-source change reaches only secondary docs while the lifecycle workflow keeps diverging per target. | Permanent exclusion (rejected: concedes the main problem); render from skeletons (rejected: measured to delete about half of five documents). |
| 2026-08-21 | This repo's copies are the baseline, not the authority. | They are the most accreted available and every phrase sampled traces to a seed, but they are still one target's sediment and carry at least one confirmed repo-specific leak. | Treat longest as authoritative (rejected: length is accumulation, not correctness); reconstruct purely from seeds (rejected: the synthesis is real work the seeds do not contain in assembled form). |
| 2026-08-21 | Capture current behavior; do not change the workflow here. | Mixing a behavior change into a content-promotion change would make both unreviewable, and reviewers could not tell intent from sediment. | Improve the workflow while authoring (rejected: hides behavior changes inside a documentation change). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Promoting one repository's sediment ships its habits to every target as framework intent. | AC-2 requires per-document traceability to a seed, a policy obligation, or a recorded decision. Anything untraceable is a decision someone has to make explicitly. |
| Scrubbing removes correct framework-internal references along with the repo-specific ones. | AC-4 makes the test target-validity, resolved against a target repository, rather than pattern-matching `.wavefoundry/` strings. |
| Promotion silently drops instructions some target relies on. | AC-5 compares against measured target copies and requires a recorded decision for every drop. |
| Marker-fenced regions get frozen into templates, so renderer and template fight over the same bytes. | AC-6 verifies by rendering twice and diffing. |
| The content work is judged by length rather than by whether the result is followable. | AC-7 requires walking one lifecycle step from the materialized text alone. |
| Six documents is a large authoring surface and the wave already holds two changes. | Ordering is explicit (`1vwyb`, then this, then `1vvs3`), and this change is content-only with no code dependency, so it can proceed in parallel with `1vvs3` design work once `1vwyb` lands. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
