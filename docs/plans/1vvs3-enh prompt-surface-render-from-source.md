# Render prompt docs from source, with opt-out

> **REMOVED from wave `1vwyc` 2026-08-21 by prepare-council BLOCK. The thesis survives; the numbers
> and several ACs do not. Re-measure before re-admitting.**
>
> Both seats agreed the core change is still worth doing. These defects must be fixed first.
>
> **1. The 18-to-12 narrowing rests on a falsified measurement.** It was justified by "rendering the
> six lifecycle prompts would delete about half of each". A real render pass produces 0.68 to 1.00 of
> current size (see the withdrawal banner on `1vwyd-doc promote-lifecycle-prompt-templates.md` for
> the table). Re-decide the scope against corrected figures. Note the correction cuts both ways:
> rendering the six would have GIVEN this repo's `prepare-wave` the lane-derivation contract it has
> never held.
>
> **2. Scope self-contradiction.** Scope says 12 docs; Tasks said "the 18 in-scope docs". An
> implementer following the task list renders the six the narrowing exists to protect.
>
> **3. AC-9's length guard is the wrong instrument.** Divergence is bidirectional, so a render can be
> the same length or longer while deleting content. Replace with content-set subtraction: refuse when
> a removed instruction-bearing line is not attributable to a shipped source. AC-9's proof fixture
> also drew on the six documents this change does not render.
>
> **4. Census scope is understated.** `docs/prompts/` holds 41 files, not 27. AC-4's arithmetic
> ("the three numbers sum to the count of files present under `docs/prompts/`") is unsatisfiable as
> written. `docs/prompts/agents/review-wave.prompt.md` is a live registry carrier with a
> renderer-owned fence and is a ninth fenced doc the census missed.
>
> **5. Two in-scope docs carry fence collisions and were never named.** Of the 12, only
> `upgrade-wavefoundry.prompt.md` (1 region, `lifecycle_reconciler`-owned, written by
> `review_policy_reconcile`) and `council-review.prompt.md` (2 regions) actually collide with
> whole-file rendering. Requirement 6 framed the question over all 8 fenced docs and named neither.
>
> **6. Two factual errors.** `render_agent_surfaces.render_lifecycle_prompt_baselines` does not
> exist; the function is `reconcile_lifecycle_prompt_baselines`. And "no code path writes a whole
> file under `docs/prompts/`" is false; the true claim is that nothing OVERWRITES an existing file.
>
> **7. Disclosure is incomplete in the surfaces operators read.** `docs/architecture/domain-map.md`
> states the ownership rule normatively ("a materialized baseline is project-owned from that moment
> on and is never rewritten") and is named by neither plan. Worse, `upgrade_merge_notes` has no
> writer and no reconcile path (`_FRAMEWORK_OWNED_MANIFEST_KEYS` is `("generated_artifacts",)`), so
> every installed target keeps the opposite promise permanently unless that is fixed or explicitly
> accepted. Changing it is not free: `reconcile_scan` excludes the manifest from scanning because of
> that key.


Change ID: `1vvs3-enh prompt-surface-render-from-source`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-21
Wave: 1vwyc prompt-surface-correctness

## Rationale

A seed change to a prompt doc never reaches a repository that has already materialized that doc,
and nothing reports the divergence.

Field evidence, measured 2026-08-21 in the Solaris target repository. A pre-release test pack
(build pkjs) removed the external TechDocs renderer instructions from `178-refresh-techdocs.prompt.md`. Solaris had
materialized `docs/prompts/refresh-techdocs.prompt.md` during the first 1.18.0 test-pack upgrade
(build pkff) the previous day (APFS birth time 2026-08-20 16:30:13) and it carried the old
instructions. The pkjs pack landed
at 06:07:18 and the file was hand-edited at 06:09:24, about two minutes later. The upgrade did not
propagate the change; an operator noticed it and repaired it by reading.

This change was originally cut as provenance stamping plus source digests plus upgrade-time drift
detection, on the assumption that the ownership contract had to be preserved. That assumption was
tested and did not survive.

The contract is stated in the manifest (`upgrade_merge_notes`: "Preserve repo-grown adaptations in
`docs/prompts/` during upgrade; do not overwrite project-specific guidance"), and the materializer
honors it: `render_agent_surfaces.render_lifecycle_prompt_baselines` skips on
`if path.is_file(): continue`, and no code path writes a whole file under `docs/prompts/`.

But the contract protects nothing in practice. Solaris, after about four months of active
downstream use, reports **zero** workflow, content, or behavioral customizations to any
pack-materialized prompt doc. Every local edit it could find decomposes into three non-adaptation
classes: repairing inbound references after the framework renamed `.md` to `.prompt.md`; repointing
role-doc paths after the framework itself moved them; and authoring one doc the upgrade recommended
but never materialized. All three are repairs of framework drift, not project customization.

So the expensive design solves the wrong problem. Detecting divergence and asking an operator to
reconcile by hand is strictly worse than not diverging. The cheap design wins: render prompt docs
from their sources like any other surface, and give the rare deliberately-adapted file an explicit
opt-out.

**A second and third measurement broke the design as first re-cut.** Two independent target
repositories were asked the same question. Both confirm zero deliberate prose adaptations, so the
ownership flip itself is sound. Both also found regressions the opt-out marker cannot prevent, and
all of them share one property: **they arose through the sanctioned upgrade path, not through
deliberate local editing.** An opt-out marker only protects a file somebody chose to adapt. It
protects none of these.

1. **Lifecycle prompt templates are skeletons, not documents.** The six prompts under
   `install/lifecycle-prompts/` ship as `{{generated_at}}` starter files, while the copies in every
   target are the accumulated current workflow, built up by upgrade-time agent reconciles across
   many releases. Measured in this repository: `review-wave` 49 template lines against 109 in the
   repo copy, `prepare-wave` 52 against 90, `create-wave` 40 against 99, `close-wave` 39 against 74,
   `implement-wave` 36 against 60. `memory-review` is the control at 94 against 94 with a zero diff,
   because it was materialized recently and nothing has accreted onto it yet. The extra content is
   framework content, not local invention: distinctive phrases in it resolve back into the seed
   corpus (`AC scope gap` in 3 seeds, `Salience` in 22, `readiness evaluation` in 9).
   **Rendering these six from their templates would delete roughly half of each.**
2. **Path bindings drift without anyone adapting anything.** A target that consolidated role docs to
   `docs/agents/specialists/` has correct prompt docs and a stale seed. Re-rendering writes a link to
   a file that does not exist and fails docs-lint. Nobody adapted that file, so nobody would have set
   a marker on it. This is why `1vwyb` is a hard prerequisite.
3. **The commonest real adaptation is parameterization, and the marker is a blunt instrument for
   it.** The one repository with genuine adaptations has exactly two, and both are the same species:
   injecting repo-specific commands and paths into a generically worded framework instruction. One is
   a load-bearing verification gate naming that repo's real toolchain, added because its unit tests do
   not type-check and green tests were masking type errors. Marking that file opt-out freezes the
   whole document, so the operator stops receiving closure-contract changes they actively want. The
   marker forces a choice between a correct local gate and current framework content.

One correction to the original premise, from Solaris: upgrades **have** rewritten prompt docs
repeatedly, through agent-driven reconcile steps following seeds 150 and 160, not through renderer
code. Both findings hold and together they reframe the problem. A propagation path already exists;
it is agentic, unreliable, and it did not fire here. This change makes it deterministic.

## Requirements

1. Render each prompt doc that has a **canonical current source** from that source, on install and
   on upgrade, replacing the create-if-missing behavior for the docs in scope. A skeleton template is
   not a canonical source, and a doc whose only source is a skeleton is excluded rather than truncated.
2. Honor an explicit opt-out marker in a prompt doc. A doc carrying it is never rewritten, and its
   opted-out status is reported so the divergence is visible rather than silent.
3. Treat a prompt doc that exists but is not attributable to a shipped source as an implicit
   opt-out. Never overwrite a file the framework did not put there.
4. Report every doc the renderer does not manage, so the unmanaged remainder is a stated number
   rather than an inference.
5. Resolve local role-doc and reference paths correctly, or leave them untouched. Re-rendering must
   not reintroduce a path that a target already had to repair.
6. Decide and record whether the existing marker-fenced regions inside 8 prompt docs are retired,
   subsumed by whole-file rendering, or retained as a deliberate second mechanism. Do not ship a
   third hybrid state by leaving the question unanswered.
7. Provide a parameterization path for repo-specific verification commands and product paths, so the
   commonest real adaptation does not require opting a whole document out of updates. A target should
   be able to supply its own commands and paths and still receive framework content changes to the
   same file.
8. Never truncate. If a rendered result is materially shorter than what it replaces, treat that as a
   failure and refuse, rather than writing it and reporting success.
9. Disclose the transition: state which docs the first rendering upgrade will overwrite, and that a
   target which hand-adapted a doc without the opt-out marker will lose that adaptation.

## Scope

**Problem statement:** prompt docs are materialized once and never updated, so every seed change
lands only in fresh installs and the installed base drifts further from the shipped workflow on
each release.

**In scope:**

- Whole-file rendering for the **12** prompt docs whose canonical source is a seed and which
  seed-100 materializes.
- A parameterization mechanism for repo-supplied verification commands and product paths.
- A truncation guard that refuses a materially shorter render.
- The opt-out marker, its detection, and its reporting.
- Attribution of an existing file to a shipped source, so unattributable files are left alone.
- Reference-path resolution sufficient to satisfy requirement 5.
- The marker-fence decision in requirement 6.
- Seed-160 disclosure of the new rendering behavior and what it overwrites.

**Out of scope:**

- **The 6 lifecycle prompts** (`create-wave`, `implement-wave`, `prepare-wave`, `review-wave`,
  `close-wave`, `memory-review`). Their shipped templates are skeletons, so they have no canonical
  current source to render from. Promoting those templates to full current documents is the
  prerequisite that would bring them in scope, and it is substantial work: the content exists today
  only as per-target sediment accreted through upgrade reconciles, which is why no two targets hold
  the same copy. **That prerequisite is `1vwyd-doc promote-lifecycle-prompt-templates`, admitted to
  this same wave and ordered before this change.** Whether the six then join this change's render set
  is a scope decision to make after `1vwyd` lands, not an automatic consequence.
- The 6 docs with no shippable source (`add-change-to-wave`, `agent-routing-concurrency`,
  `codebase-cleanup-review`, `package-wavefoundry`, `pause-wave`, `remove-change-from-wave`).
  Authoring sources for them is a separate change; this one reports them as unmanaged.
- The 3 docs that have a seed but no materializer (`archetype-council`, `framework-config-review`,
  `red-team-review`). Wiring them into materialization is a separate decision, and Solaris shows
  targets hand-author them today, so rendering over that work needs its own review.
- Correcting the stale role-doc citations in seeds. That is `1vwyb`, which must land first.
- Any equivalent change for `docs/agents/`, `.claude/`, or other host surfaces.

**Depends on:** `1vwyb-bug seed-role-doc-paths-stale`, then `1vwyd-doc promote-lifecycle-prompt-templates`. Three seed-cited role-doc paths do not
resolve today. Rendering from those seeds before `1vwyb` lands would push broken paths into every
target, including two repositories that already repaired them by hand.

## Acceptance Criteria

- [ ] AC-1: A prompt doc whose source changed is updated to match on the next upgrade, proven end to
      end by the `refresh-techdocs` case: a repo holding the earlier 1.18.0 test pack's content (build
      pkff) receives the current content (build pkjs).
- [ ] AC-2: A doc carrying the opt-out marker is byte-identical before and after an upgrade, and is
      named in the run's report as opted out.
- [ ] AC-3: A prompt doc not attributable to a shipped source is never modified, proven with a
      locally authored file at a name the framework later starts shipping.
- [ ] AC-4: The run reports counts for managed, opted-out, and unmanaged docs, and the three numbers
      sum to the count of files present under `docs/prompts/`.
- [ ] AC-5: Rendering into a repository whose role-doc references were previously repaired does not
      reintroduce an unresolvable path. Verified against the `specialists/` layout.
- [ ] AC-6: The marker-fence decision is recorded in the Decision Log with its rationale, and the
      shipped behavior matches it. No prompt doc ends up both whole-file rendered and fence-patched
      unless that combination is the recorded decision.
- [ ] AC-7: Seed-160 names the docs the first rendering upgrade overwrites and states the adaptation
      loss risk for targets that adapted without the marker.
- [ ] AC-8: A dry run reports exactly what it would overwrite, and changes nothing on disk.
- [ ] AC-9: A render that would produce a materially shorter document than the one it replaces is
      refused and reported, not written. Proven with a skeleton template against an accreted copy,
      the exact shape that would have truncated five lifecycle prompts.
- [ ] AC-10: A target supplying its own verification commands and product paths receives framework
      content updates to the same document. Proven with the real case: a repo-specific typecheck gate
      survives a render that also changes surrounding framework prose.

## Tasks

- [ ] Land `1vwyb` first; confirm all seed-cited role-doc paths resolve before rendering anything.
- [ ] Define the opt-out marker and its placement convention; document it in the rendered doc itself
      so an operator adapting a file can see how to keep the adaptation.
- [ ] Implement source attribution, covering the seed convention and `LIFECYCLE_PROMPT_BASELINES`.
- [ ] Replace create-if-missing with render-if-managed-and-not-opted-out for the 18 in-scope docs.
- [ ] Implement the dry-run report and the managed/opted-out/unmanaged counts.
- [ ] Resolve the marker-fence question and apply the decision.
- [ ] Update seed-160 with the behavior change and the transition disclosure (gate: `seed_edit_allowed`).
- [ ] Tests for each AC, including the end-to-end `refresh-techdocs` replay.

## Agent Execution Graph


| Workstream         | Owner       | Depends On         | Notes |
| ------------------ | ----------- | ------------------ | ----- |
| source-attribution | implementer | (`1vwyb` landed)   | Two source families plus an explicit unattributable result. |
| opt-out-marker     | implementer | source-attribution | Marker plus implicit opt-out for unattributable files. |
| render-swap        | implementer | opt-out-marker     | The behavior change; dry run ships with it, not after. |
| fence-decision     | architect   | :                  | Can run in parallel; blocks AC-6 only. |
| seed-disclosure    | implementer | render-swap        | Requires the `seed_edit_allowed` gate; close immediately after. |
| verification       | qa          | render-swap        | Owns the `refresh-techdocs` end-to-end replay. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `docs/prompts/prompt-surface-manifest.json`
- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/data-and-control-flow.md` both describe
the prompt surface and its ownership; each needs the ownership flip recorded, because
project-owned-forever becomes framework-rendered-unless-opted-out. That is a genuine ownership
boundary move, not an implementation detail, and it is the kind of change that warrants an
architecture lane by judgment even though the paths alone would not recruit one.

## AC Priority


| AC   | Priority       | Rationale |
| ---- | -------------- | --------- |
| AC-1 | required       | The entire point. Without the end-to-end replay this is an untested claim. |
| AC-2 | required       | The opt-out is the only protection a deliberately adapted file has once rendering is on. |
| AC-3 | required       | Overwriting a file the framework never shipped would destroy work it has no claim to; Solaris has exactly such a file. |
| AC-4 | important      | Makes the unmanaged remainder visible so partial coverage is not mistaken for full coverage. |
| AC-5 | required       | Two repositories already repaired these paths. Re-breaking them would make the upgrade actively harmful. |
| AC-6 | required       | Leaving fences and whole-file rendering both live without a recorded decision is the third hybrid state this is meant to avoid. |
| AC-7 | required       | Undisclosed, the first rendering upgrade silently overwrites files; that is the one irreversible failure mode here. |
| AC-8 | important      | A dry run is how an operator can trust the first rendering run before it happens. |
| AC-9 | required       | Truncation is the failure mode that two repositories independently demonstrated, and it is silent. Refusing beats writing and reporting success. |
| AC-10 | required      | Without it the marker forces a choice between a correct local verification gate and current framework content, and a target will rationally choose the gate and stop receiving updates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-21 | Planned as provenance plus digest plus drift detection. | Census: 27 docs, 0 whole-file writers, 8 fenced, 21 with a shippable source. |
| 2026-08-21 | Re-cut around render-from-source after measuring the ownership contract's real value. | Solaris reports zero genuine adaptations in about 4 months; every local edit was framework-drift repair. Census refined to 18 managed, 3 sourced-but-unmaterialized, 6 sourceless. |
| 2026-08-21 | Scope narrowed from 18 to 12 docs after two target measurements. | Lifecycle templates measured as skeletons in this repo: review-wave 49 vs 109 lines, prepare-wave 52 vs 90, create-wave 40 vs 99, close-wave 39 vs 74, implement-wave 36 vs 60; memory-review control 94 vs 94, diff 0. Rendering would have deleted about half of each. |
| 2026-08-21 | Motivating evidence confirmed by file birth time. | `refresh-techdocs.prompt.md` born 2026-08-20 during the first 1.18.0 test-pack upgrade (pkff), hand-edited 2026-08-21 06:09:24, about 2 minutes after the pkjs pack landed at 06:07:18. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------- | ------------ |
| 2026-08-21 | Render from source with opt-out, rather than detect drift and report it. | The preserve-adaptations contract protects nothing measurable: zero genuine adaptations downstream in about 4 months. Reporting divergence and asking for a hand reconcile is strictly worse than not diverging. | Provenance plus digest plus drift detection (the original cut, rejected: builds machinery to describe a problem it could instead prevent); three-way merge (rejected: no merge base for unmanaged docs, cost far above the problem). |
| 2026-08-21 | Unattributable files are an implicit opt-out. | Solaris hand-authored `framework-config-review.prompt.md` because the upgrade recommended it and never materialized it. A renderer that later ships that name must not overwrite it. | Overwrite by name (rejected: destroys work the framework has no claim to); require an explicit marker on such files (rejected: the operator cannot mark a file against a future the framework has not shipped yet). |
| 2026-08-21 | Depend on `1vwyb` rather than absorbing it. | Three seed-cited role-doc paths do not resolve. Rendering first would push broken paths into every target, including two that already repaired them. Keeping them separate makes the ordering explicit and reviewable. | Fold the seed fix in (rejected: couples a one-line correction to an ownership change); render anyway and fix after (rejected: knowingly ships a regression). |
| 2026-08-21 | Exclude the 6 lifecycle prompts rather than render them from templates. | Their templates are `{{generated_at}}` skeletons; the real content is per-target sediment accreted through sanctioned upgrade reconciles. There is no canonical current source to render from, so rendering means truncating. | Render anyway (rejected: measured to delete about half of five documents); promote the templates to canonical documents inside this change (rejected: substantial work of a different kind, and it would hide a content-authoring effort inside an infrastructure change). |
| 2026-08-21 | Add parameterization rather than relying on the opt-out marker for repo-specific commands and paths. | The only genuine adaptations found across two repositories were both this species, and both are load-bearing. The marker freezes an entire document, so using it here trades a correct local gate against current framework content. | Marker only (rejected: forces that trade); ignore the case (rejected: it is the one real adaptation class observed). |
| 2026-08-21 | The 3 sourced-but-unmaterialized docs stay out of scope. | Targets hand-author them today because nothing materializes them. Rendering over that work is a distinct decision needing its own review, not a side effect of this change. | Include them (rejected: would overwrite locally authored content under cover of an infrastructure change). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The first rendering upgrade silently overwrites a doc a target adapted without the marker. This is the one irreversible failure mode. | AC-7 requires the disclosure and AC-8 requires a dry run, so the overwrite set is visible before it happens. Solaris measured zero such adaptations, which bounds but does not eliminate the exposure. |
| Rendering reintroduces reference paths a target already repaired. | Hard dependency on `1vwyb`, plus AC-5 verifying against the `specialists/` layout. |
| Marker fences and whole-file rendering coexist as overlapping mechanisms. | AC-6 forces an explicit recorded decision rather than letting both persist by default. |
| Ownership flips from project to framework, which is a real reduction in target autonomy. | The opt-out marker preserves autonomy for anyone who wants it, and the measured zero adaptations say almost nobody does. Recorded in the architecture docs so the flip is visible, not implicit. |
| The zero-adaptation finding rests on two repositories, one of which answered through two sessions that contradicted each other on working-tree state. | Treated as directional, not universal. AC-9 and AC-10 mean a target that differs is protected by mechanism rather than by the sample being right. |
| The commit-count proxy used to gather this evidence reads falsely clean where upgrade output is committed as one blob or left uncommitted. One repo returned count 1 for every tracked prompt doc while holding 819 uncommitted changed lines. | Any future sampling must read `git status` alongside `git log`, and must classify diffs rather than counting commits. Recorded so the next measurement does not repeat the error. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
