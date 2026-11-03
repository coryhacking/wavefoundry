# Plan initiatives and carry outcomes across waves

Change ID: `22brz-enh initiative-planning-and-continuation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-02
Wave: 22bs0 initiative-continuity

## Rationale

The operator asked to follow the revised Wavefoundry vision with an implementation wave. The selected direction connects **Vision → Horizon → Initiative → Wave → Change** so a small team can carry substantial outcomes through delivery. It applies to creation, improvement, modernization, replacement and takeover. Changes remain inside waves. Existing acceptance, review and agent handoff are foundations, not presumed missing capabilities.

The first opportunity is to assemble a useful continuation from existing records: the outcome, accepted increments, remaining obligations, dependencies and next consequential decision. A new maintained tracker or autonomous coordinator would be premature until the cheaper derived approach shows what information lacks a reliable home. This change delivers that bounded workflow and checks its behavior; it does not implement the entire six-horizon vision.

Source inspection found relevant ingredients in the current Plan change vision bridge, Pause wave handoff and seed 200 reconciliation guidance. They already describe outcome alignment, unresolved decisions, assumptions and next-wave dependencies. The operator reports successful cross-agent planning, implementation and handoff. Neither source presence nor that experience establishes that an initiative continuation already works end to end. Conversely, absent comparative evidence is not evidence that current planning fails.

## Product Intent

An operator or incoming contributor pursuing a substantial outcome can recover what the work is trying to achieve, what accepted work actually establishes, what remains blocked and which bounded advance or decision comes next, without manually stitching together several wave conversations. The continuation stays grounded in the project's own sources and preserves existing acceptance and authority boundaries. AC-2 and AC-3 test this meaning and continuation behavior; AC-1 and AC-5 establish delivery of the reusable capability. Reduced human coordination cost, commercial demand and sustained autonomous execution remain field claims outside this change's evidence.

This advances [Vision: Horizon 3](../../../VISION.md#horizon-3--initiatives-carried-through-useful-waves) through its thin planning/continuation increment, reusing Horizon 1 controls and only necessary Horizon 2 understanding. Target projects use their own visions and horizons. A project without an adopted vision can still organize an explicitly requested outcome; no vision or initiative is a prerequisite to ordinary waves.

## Requirements

1. **One optional, reusable workflow.** Deliver **Plan initiative**, backed by `docs/prompts/plan-initiative.prompt.md` and thin `wf-plan-initiative` skill. It can establish a bounded outcome or revisit an existing one and derive a continuation brief. It plans and explains; it does not itself create, admit, ready, open, close, implement or commit a wave/change. A separately explicit lifecycle request continues through that workflow's existing rules. Do not introduce a new lifecycle state, approval, database table, ID namespace or mandatory initiative file.

2. **Distinct purpose and ownership.** Explain vision, horizon, initiative, wave and change in the context needed for the request. One horizon may have several initiatives and an initiative several waves; admitted changes remain owned by waves. Features may describe capabilities without a required extra level. Preserve standalone fixes and maintenance. The installed project owns its direction; Wavefoundry's H3 describes the enabling capability, not the target project's goal. Do not force all work into a hierarchy or infer a commercial, takeover-only or autonomous destination.

3. **Use authoritative context proportionately.** Reuse the operator's chosen outcome, owner, constraints and existing sources before asking questions. Apply the current adopted-vision discovery/read boundary when relevant. Use target-scoped MCP and typed lifecycle evidence where available, validating consequential findings against their authoritative current sources; disclose unavailable or contradictory evidence. Begin with identified relevant waves, changes, decisions and handoff, following consequential dependency references rather than reading every historical wave. Attribute claims to their sources and revisions where available. A closed wave is not sufficient proof of achieved benefit: inspect relevant objective/intent outcomes, acceptance dispositions and outstanding work. Do not infer completion, adoption, authority or a dependency from mere naming, status or proximity.

4. **Produce a usable continuation, not a second ledger.** Default to one response containing a coherent outcome and boundaries, what the available evidence establishes, remaining obligations and dependencies, the next useful bounded wave/change proposal or decision, and the reasons and uncertainties. Adapt the shape to the work; do not impose a fixed questionnaire or lengthy form. Distinguish recorded facts, interpretations and proposals. Preserve an existing authoritative home for the outcome; if none exists, state the operator's supplied intent and its provenance without inventing a file or pretending the response is durable state. The operator may direct saving the brief to a named existing planning/handoff surface; preserve unrelated material and its ownership. The default invocation writes no project artifacts. Before later lifecycle work relies on the brief, recheck consequential mutable source state. The brief never becomes review or readiness authority.

5. **Guide decisions and adapt the path.** When a missing or changed fact materially redirects outcome, scope, priority or responsibility, explain a small set of concrete options, consequences and a recommendation; ask one focused question in dependency order. Reuse prior answers. Reflect how an actual answer changes the next priorities. Honor explicit draft-first, deferral and no-interview instructions; silence is not selection. Pause dependent recommendations when needed and continue independent investigation. A changed assumption should change the affected proposed sequence or expose a decision, preserving unaffected work and current authority. Missing evidence must not be converted into a fabricated dependency or a universal implementation blocker.

6. **Test the cheaper mechanism before adding maintained state.** Derive the first continuation from existing records. Record evidence of missing, ambiguous or expensive-to-reconstruct outcome/dependency information in delivery findings. Do not create persistent initiative fields or a tracker as a repair within this scope. Existing trackers may supply authoritative context if already available and authorized; no integration or remote access is implied. If derivation is insufficient, return a concrete follow-up option with ownership and cost rather than expanding implementation automatically.

7. **Connect existing guidance without making it heavier for unrelated work.** Envision may describe useful initiatives beneath horizons and point to Plan initiative for subsequent authorized planning; it must not automatically run it or turn every vision into an initiative backlog. Plan change, when given relevant initiative context, identifies how the requested change contributes and which consequential prerequisites apply, without choosing different work or making the new workflow mandatory. Preserve the adopted-vision bridge, standalone/no-fit paths and vision ownership. Do not change close, pause, readiness or review semantics. Acceptance improvements require their own demonstrated need and are excluded here.

Keep the workflow itself short: gather relevant context, explain the next useful step, and ask only for a consequential missing choice. No standing council, reader trial, review cycle or validation checklist is part of invoking Plan initiative. Use ordinary author source checks and the existing downstream wave checks.

8. **Deliver to new and existing targets.** Follow the existing prompt-seeding, upgrade reconciliation and skill-rendering architecture. New installs receive the backing prompt; upgrades create it missing-only and reconcile later canonical changes while preserving compatible local edits and surfacing conflicts. Rendering emits only a thin doc-gated pointer in each active supported skill host, using existing frontmatter practices without a new YAML dependency. Setup/rendering must not be described as prose reconciliation or initiative execution. Package the canonical source and tests through normal policy; do not include actual project visions, briefs or evaluation artifacts in the distribution. Apply the writing guide to all authored prose.

## Scope

**Problem statement:** useful cross-wave continuation is not established as a delivered workflow; the evidence supports testing a small derived planning surface before a persistent initiative mechanism.

**Intended canonical writes during implementation:**

- New `.wavefoundry/framework/seeds/171-plan-initiative.prompt.md` in the existing 170–199 lifecycle band (171 is unused in the inspected tree; recheck before editing).
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`, `100-project-prompt-surface-bootstrap.prompt.md` and `160-upgrade-wavefoundry.prompt.md`: discoverability, missing-only delivery and changed-seed reconciliation for the new surface and any changed existing surfaces.
- `.wavefoundry/framework/seeds/170-plan-change.prompt.md`, `179-envision-project.prompt.md` and, only for the handoff pointer, `seeds/envision/delivery.prompt.md`: conditional continuity guidance with existing authority boundaries intact.
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`: one registry entry and thin pointer body, following the existing doc-gated pattern.
- `.wavefoundry/framework/scripts/vocabulary_profile.py`: reserve the new fixed prompt, skill and phrase against distribution-name collisions; update its existing contract test and the framework text-ownership fixture for new source files. No naming-profile redesign.
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py` and new focused `test_initiative_planning_delivery.py`; relevant existing bootstrap/upgrade contract tests if their assertions govern the edited surfaces.
- Canonical catalog/map references in `.wavefoundry/framework/README.md` and `.wavefoundry/framework/seeds/008-framework-map.md` where needed for this new public workflow.

**Self-hosted delivery and documentation writes:**

- New `docs/prompts/plan-initiative.prompt.md`; matching portions of `docs/prompts/plan-change.prompt.md`, `envision-project.prompt.md`, `agents/envision/delivery.prompt.md`, `upgrade-wavefoundry.prompt.md` and `index.md`.
- `AGENTS.md` shortcut/skill catalog only; `docs/agents/platform-mapping.md` capability entry; `docs/architecture/data-and-control-flow.md` new advisory planning flow; `docs/contributing/review-and-evals.md` only if documenting the bounded evidence method requires it; `CHANGELOG.md`.
- Generated active-host skill surfaces and their existing manifest/catalog outputs through the normal renderer, not hand-authored parallel workflow bodies. Derive the output set from actual active host configuration and renderer output; do not invent inactive roots or broaden host permissions.
- This wave/change evidence and `docs/agents/session-handoff.md`.

**Read-only and protected:** actual `VISION.md`, `VISION-research.md`, `VISION-review.md`, `docs/visions/`, prior wave evidence and ledgers, unrelated working-tree changes, existing lifecycle/runtime/storage/gate implementation and the shared writing guide. Seeds 180, 190 and 200 and the Pause wave workflow supply context but are not changed. Preserve unrelated local customizations and generated marker ownership. The author owns only planned edits; evaluators/reviewers inspect and report, never silently repair production prose or record approvals outside the appropriate lifecycle.

**Out of scope:** a full initiative schema/store/ID/status machine, hierarchy migration, automatic wave creation or execution, scheduling, concurrency changes, code-graph/Tensorwell extraction, runtime or language migration, new acceptance controls, dashboard hierarchy UI, mandatory feature/story documents, external tracker integration, implementation of a target project's initiative, public release, version bump or package build.

## Acceptance Criteria

- [x] AC-1: The delivered Plan initiative entry yields the specified advisory planning/continuation behavior, keeps changes inside waves and keeps target direction distinct from Wavefoundry's roadmap. It requires neither an adopted vision nor an invented initiative for ordinary work and grants no lifecycle or implementation authority. A missing entry, a competing state authority or silently redirected request fails. Contract review and actual invocation evidence establish this; phrase presence alone does not.
- [x] AC-2: One representative multi-wave walkthrough using the delivered prompt recovers the supplied outcome, accepted evidence, unresolved obligations and a justified next increment or decision. It follows a consequential dependency reference and does not treat wave closure as proof of achieved benefit. Check the response against a short source-fact checklist prepared before prompt edits. Retain the input, response and verdict; no matched baseline or separate blind reader is required. This demonstrates the case, not improvement over current practice.
- [x] AC-3: Continue that same walkthrough with a changed assumption and an explicit choice or deferral. The response adjusts the affected path, preserves other obligations and starts no implementation. Use a short additional no-vision/unrelated-maintenance example to check that the hierarchy is optional. These focused checks reuse the same author and reviewer; they are not independent samples or evidence of general effectiveness.
- [x] AC-4: Envision and Plan change carry only the conditional bridge described in R7. Existing no-initiative/no-fit behavior remains usable, actual visions and unrelated records stay unchanged, and the installed local wording preserves authority and selection semantics. A brief treated as a readiness receipt, automatic vision write, forced extra planning invocation or new acceptance prerequisite fails. Verify positive and negative routes with focused invocation/contract evidence and before/after protected-artifact checks.
- [x] AC-5: A fresh target and a target upgrading with local customization receive a usable backing prompt and correctly gated thin skills. An existing customized prompt is preserved/reconciled by the canonical upgrade rule with an explicit conflict outcome where needed; a later changed seed 171 has a defined reconciliation route. Actual rendered/pack-collected artifacts preserve paths, links and standard frontmatter; missing-doc, repeated render and changed-seed-list cases discriminate against accidental unconditional generation or skipped delivery. This change's own tests and authored/edited documents pass validation, with no failure elsewhere attributable to it.

## Tasks

- [x] Prepare one small walkthrough and its source-fact checklist before prompt edits; preserve the working-tree baseline and protected files.
- [x] Author seed 171 and its self-hosted prompt; implement the minimal conditional Envision/Plan change bridge and document ownership.
- [x] Wire bootstrap, upgrade reconciliation, registry/catalog delivery and existing active-host rendering; add focused delivery controls.
- [x] Run cheap delivery/contract checks before the authoring/continuation batch.
- [x] Run the representative walkthrough, changed-assumption continuation and short optional-workflow check; retain concise evidence.
- [x] Reconcile findings within the declared batch boundary, run required delivery reviews and framework checks, and hand off the result and remaining field limits.

## Agent Execution Graph

The coordinator owns the tightly coupled prompt, delivery and documentation edits. One walkthrough author exercises the delivered prompt; the required QA lane checks its result against the prepared facts. Reuse that evidence for the required delivery review instead of adding an evaluation council or separate reader. Required lifecycle reviewers remain independent of implementation.

## Serialization Points

Prepare the small case and source checklist before prompt edits. Preserve the working-tree baseline. Render after canonical/local delivery is coherent. Keep the candidate stable during the walkthrough and review; record any repair and its focused verification. Final framework receipt follows the last framework edit.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/171-plan-initiative.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/170-plan-change.prompt.md`
- `.wavefoundry/framework/seeds/179-envision-project.prompt.md`
- `.wavefoundry/framework/seeds/envision/delivery.prompt.md`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/tests/test_vocabulary_prompt_names.py`
- `.wavefoundry/framework/scripts/tests/fixtures/framework-text-ownership.json`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_initiative_planning_delivery.py`
- `docs/prompts/`
- `docs/architecture/data-and-control-flow.md`
- `docs/agents/platform-mapping.md`

Root-level catalog/changelog edits are explicitly in Scope above. Request QA, architecture and docs-contract review alongside the lanes selected from these paths; this is an advisory workflow and delivery change, not a new execution security boundary.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: describe the advisory initiative-to-wave planning flow, current record owners, derived brief and conditional handoff; no new runtime, database or authority. `docs/agents/platform-mapping.md`: new doc-gated public skill. Keep actual product architecture and vision unchanged during implementation.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the new public workflow and its boundaries |
| AC-2 | required | Tests useful continuation rather than heading completeness |
| AC-3 | required | Tests adaptation, case breadth and evidence/authority preservation |
| AC-4 | required | Protects ordinary workflows and project ownership |
| AC-5 | required | Makes the improvement reach new and existing installations |

## Evaluation Scope and Stopping Rule

Keep validation proportional to this advisory prompt and one renderer entry. First run focused delivery tests for prompt creation/reconciliation, doc gating and rendering using existing fixtures and conventions. Then run one small multi-wave walkthrough, its changed-assumption continuation and a short no-vision/unrelated-work example. Prepare the source facts before prompt edits and let the required QA reviewer check the outputs; no matched baseline, blind-reader protocol, manufactured bad-output suite or additional review council is required.

Allow one focused repair and recheck of a failed walkthrough outcome. If a required outcome remains unproven, return the evidence and options to the operator rather than launch more trials. Existing required readiness/delivery lanes and the framework suite remain unchanged. Retain only the small case, consequential outputs, failures and final conclusions. No performance, human-comprehension or productivity improvement is claimed. Check live planning carry-through when it naturally occurs.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-02 | All required delivery lanes and targeted council approve; fresh receipt readiness approvals restored by focused bookkeeping-effect checks. Same actual delivery contexts supplied phase-specific ledger IDs, not additional independent samples. No material findings pending. Memory proposal created no candidates; plan choices duplicate canonical guidance or have no current source target. Seed/framework edit gates closed. | Typed approvals on review-policy-fe518e1fbb78e02a6045; operator signoff remains pending |
| 2026-11-02 | Delivery reviewers found no implementation defect. Corrected the old Session Handoff state; conditional digest rules rotated readiness to review-policy-fe518e1fbb78e02a6045. Prepare refreshed only Last verified dates in local Plan change/platform mapping; reversing those dates exactly recovers reviewed hashes. Focused approval effect check, no new trial or source repair. | Current receipt; delivery review; full docs validation green |
| 2026-11-02 | Canonical suite passes on unchanged source with host access: 12,300 tests / 216 files / 12 expected skips, 593.852 s. All six sandbox-failed modules pass; no source repair or qualification waiver. | Canonical test-cache receipt; `delivery-evidence.json` framework_suite |
| 2026-11-02 | First canonical run completed 12,300 tests across 216 files with 12 skips; six modules failed under sandbox restrictions: local socket binding/process inspection denied, uv bootstrap temporary write denied and pip cache access disabled. Exact traces inspected; no source repair. Canonical rerun with host access started on unchanged source. | `.wavefoundry/work/22bs0/framework-tests.log`; refused execution 183172efe0134099a009c8f58b7693c9; host rerun log |
| 2026-11-02 | Delivered the 631-word local prompt, minimal conditional bridges and thin skill; existing renderer wrote only the three active-host skill files. Full docs validation and diff whitespace check pass. | Seed 171/local prompt; `wf_sync_surfaces`; `wf_validate_docs` |
| 2026-11-02 | Focused delivery suite: 239 tests pass, zero skips. Initial component test wrongly expected tests in the runtime pack; corrected the test to assert their existing exclusion, without changing packaging. Actual collection/extraction, later changed-seed detection, doc gating, custom-byte preservation, repeated rendering and collision checks pass. | `delivery-evidence.json`; temporary log `.wavefoundry/work/22bs0/initiative-focused-tests.log` |
| 2026-11-02 | Landing controls: deleting each new fixed prompt/skill/shortcut reservation in process makes `test_initiative_names_reject_collisions_and_allow_adjacent_names` fail (1, 1, 2 assertions respectively); restoring them passes. No source mutation. | `delivery-evidence.json` name_reservation_controls |
| 2026-11-02 | One read-only author used the rendered skill and local prompt, followed the receiver dependency, separated closed waves from beneficiary acceptance and proposed access/confirmation before retirement. The explicit deferral redirected only the next increment to a dry-run report; unrelated typo work needed no initiative. Source checklist retained before edits; no repair needed. | `delivery-evidence.json` walkthrough inputs/outputs; independent QA review pending |
| 2026-11-02 | Agent-assisted reconciliation authored a missing prompt, applied only the six-byte canonical change to a customized prompt, and left conflicting mandatory-tracker policy untouched/incomplete. Newly current targets needed no further write. Protected fixture and actual vision files retain hashes. | `delivery-evidence.json` reconciliation/protected_artifacts; no full target installation or human benefit claim |
| 2026-11-02 | Readback: deliver a short optional read/recommend/hand-off prompt and thin skill. AC1–4 exercise source-grounded continuation; AC5 covers existing delivery mechanisms. Example: passing export-format tests must not authorize retirement before receiving-team acceptance. Scope is seeds/local prompts, registry and name reservations, catalogs and focused tests; actual visions, lifecycle semantics and persistent state remain untouched. Readiness passed on review-policy-52b5e7579356ccd5f608; wave activated and seed/framework gates opened. | Typed readiness approvals; `wf_implement_wave`; operator lightweight direction |
| 2026-11-02 | Prepared linked synthetic source records and a small fact checklist before candidate edits; preserved canonical/local working-tree and vision hashes. | `.wavefoundry/work/22bs0/walkthrough/`; `baseline-hashes.json` |
| 2026-11-02 | Simplified the workflow and validation on operator direction: short response-first flow, one walkthrough with focused variations, QA reuse and normal delivery tests; removed comparative trial and separate reader machinery before readiness. | Operator: keep workflow, process and validation lightweight |
| 2026-11-01 | Planned and admitted the first bounded initiative workflow to 22bs0 following the operator-directed vision revision. Source inspection and lifecycle inventory only; no framework edit or trial execution. | VISION revision 2026-11-01-C; current prompt/renderer reads; `wf_current_wave` empty and pending-plan inventory checked |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-02 | Use direct behavioral and delivery checks, not a comparative evaluation program. | The operator requested the simplest practical workflow and lightweight validation. The claim is a usable first entry, not proven superiority to current practice. | Matched author trials and blind-reader controls add cost beyond this first delivery claim. |
| 2026-11-01 | Select an optional derived Plan initiative brief using existing records. | Checks a representative continuation of a substantial outcome while preserving working acceptance and avoiding a second ledger. The expected benefit is a hypothesis, not a measured improvement. | Keep existing Plan change/handoff alone: lowest cost and remains usable, but offers no dedicated synthesis entry. Build a persisted initiative tracker/scheduler now: explicit state but commits to ownership and upkeep before showing the missing information. |
| 2026-11-01 | The mechanism advises; existing workflows retain authority. | Replaying the motivating case yields an outcome/dependency/decision brief for the next agent. It can support correct continuation but cannot enforce truth or make a person act. It may miss undocumented dependencies, overread stale summaries or be ignored when too costly; source checks, visible uncertainty and a focused walkthrough checks those risks. | A new gate could force use but would not prove the brief useful and would burden unrelated changes. |
| 2026-11-01 | Existing source evidence is limited to inspection; dynamic delivery and benefit remain to execute. | `execution_status: inferred` for current prompt/render behavior: Plan change line 21, Pause wave lines 23–29/53–57, seed 200 lines 94–120, renderer `Skill`/doc-gated registry were read. `execution_status: unverified` for improved continuation and new prompt install/reconciliation behavior. No test or agent trial was run for this plan. | Do not promote source presence, prior generic suite counts or operator success in other workflows into evidence for this new one. |
| 2026-11-01 | Keep actual vision files and old records protected. | The approved authoring outcome informs this plan; implementation must not rewrite direction or historical evidence to satisfy its tests. | Extending the vision during implementation would conflate product choice with delivery proof. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A new hierarchy adds recordkeeping rather than capacity | Short response-first brief, no routine review or tracker, persistent state excluded |
| Plausible synthesis invents alignment or hides failed benefit | Source-backed claims, conflicting/negative cases, closure-versus-intent distinction and explicit unknowns |
| New workflow silently takes over planning or authority | Optional explicit entry, preserved no-fit paths, no lifecycle mutation by the workflow and unchanged gates |
| Upgrades deliver the skill but miss its backing prose | Missing-only and changed-seed reconciliation tests plus actual renderer/package collection checks |
| Evaluation repeats the prompt's own checklist | Prepared source facts and required QA review of actual responses rather than heading counts |
| Scope grows into the full autonomous laboratory | One planning/continuation increment; report remaining needs as follow-up options |

## Session Handoff

Implementation and the focused walkthrough/delivery checks are complete. Full framework suite passes: 12,300 tests across 216 files, 12 expected skips. Required delivery review is finishing; no closure, commit or build is authorized. The current work is in open wave `22bs0 initiative-continuity`. See `docs/agents/session-handoff.md` for next actions and `delivery-evidence.json` for the bounded evidence and limits.
