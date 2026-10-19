# Explicit intent from planning through delivery

Change ID: `2124m-enh explicit-intent-through-lifecycle`
Change Status: `implemented`
Owner: Engineering
Status: implementing
Last verified: 2026-10-18
Wave: 2124l explicit-intent-through-lifecycle

## Rationale

Wavefoundry operators and agents need to keep work focused on the outcome that justified it, even when the implementation changes. Today motivation, scope and tasks are recorded more consistently than that outcome. Seed 170 requires Product Intent and distinguishes it from Rationale, but the shipped and project-local plan templates and the local Plan Change instructions omit it. Wave objectives can consequently become lists of mechanisms, and completing the list can be mistaken for achieving the goal.

This change serves framework source projects, installed consumers and renamed downstream distributions through the same canonical sources and existing installation/upgrade paths. It makes intent explicit in existing records and carries it into existing readback, review and close work. It adds no approval round, hard gate, sidecar, reporting service or routine upgrade scan. One sentence is sufficient for a straightforward change. Native host features, such as Claude settings or skills, are not required to receive this contract.

## Product Intent

Operators and agents can identify who benefits, the observable improvement sought and the boundaries that must remain, then use that intent to select, implement and evaluate the smallest suitable change. A mechanically complete task list does not substitute for an evidenced outcome. Review and closure state what was established and what remains uncertain without adding routine process overhead.

Before: an agent can complete the prescribed mechanisms while losing the reason for the work. After: new plans expose the intended beneficiary and outcome; the existing readback and reviews use that outcome to evaluate the chosen mechanism, and closure preserves an evidence-backed assessment including uncertainty. The same contract reaches this framework source project and installed or renamed consumers. This wave can prove the contract's delivery and truthful preservation through public paths; improved agent adherence remains an intended benefit unless separately observed. Existing authorization, compatibility and qualification boundaries remain.

## Requirements

1. **One concise intent contract in existing records.** Use the existing `## Product Intent` heading consistently in new change scaffolds and planning guidance for every change kind, including framework, maintenance and documentation work. It states the beneficiary, desired before/after outcome and material boundaries; it describes an outcome rather than prescribing a mechanism. Rationale explains why now, Requirements specify behavior, Scope bounds the work, Tasks describe implementation and ACs describe evidence. Do not duplicate those sections in intent or impose a field-filling interview. Use the existing wave Objective for the shared outcome; do not add another wave-level intent section.
2. **Planning producers agree.** Align seed 170, the shipped install template, the project-local template consumed by `wf_new_*`, and the Plan Change/Create Wave guidance. The wave objective scaffold prompts for an outcome shared by admitted changes. At least one AC, or a clearly identified combination of existing ACs, addresses whether each change's intent was established. Keep implementation checks where useful. For guidance changes, separate proof that instructions were delivered from evidence of improved agent behavior; never claim the latter from renderer tests alone.
3. **Existing execution and review steps use intent.** The existing implementation readback briefly relates the chosen work to intent. Existing plan/readiness and delivery reviews ask whether meeting the requirements and ACs would achieve the intent, and whether added complexity, runtime cost or operator burden undermines it. Add this to existing review work, not a new lane or independent gate. A better mechanism may replace the planned mechanism only under existing scope, requirement-amendment, re-Prepare and operator-authorization rules; intent is not permission to broaden scope or silently change the contract.
4. **Closure retains an honest outcome assessment.** Existing Review Checkpoints hold a concise, explicitly authored `Intent outcome:` paragraph stating achieved, partial or not established, evidence references and material limitations. It may cover multiple changes together when their outcome is shared. Existing close guidance asks for this assessment. The existing close-summary composer carries that authored assessment into Wave Summary when present, preserving its qualification and references rather than inferring achievement from checked ACs or titles. It must not fabricate evidence or an approval. The composer reads wave.md's exact `## Review Checkpoints` H2 (the heading the prepare-council reader already uses), takes the last list item or paragraph whose text, after an optional `- ` and an optional `YYYY-MM-DD: ` prefix, starts with `Intent outcome:`, tolerates CRLF line endings, and carries that text verbatim as its own paragraph after the delivered sentence. For older records without an assessment, including those using a lowercase `## Review checkpoints` heading, the output is byte-identical to the current close behavior; absence introduces no new blocking gate or schema requirement. The composer's signature is unchanged.
5. **Delivery to consumers uses existing paths.** Update canonical seeds, shipped lifecycle templates and the applicable current self-hosted carriers. Initial installation and the existing agent-assisted upgrade reconciliation convey the same intent contract. Project-local plan templates must be reconciled as well as the shipped fallback, because `new_change` prefers the local template. Missing-only rendering must not be described as updating existing project-authored prose. Preserve project additions, metadata, renderer-owned regions and distribution-declared layout/vocabulary. Ambiguous or conflicting project edits use the existing operator-resolution behavior. Add no broad history scan, source qualification in consumers, model download, extra index pass or new evidence generation during upgrade.
6. **Prospective compatibility and proportionate records.** New plans use the contract; an existing plan being materially revised gets a concise intent clarification in its ordinary edit. Do not bulk-edit planned/readied/active records, rotate other waves' receipts, or rewrite closed waves, admitted historical plans or ledgers to retrofit it. Existing Product Intent records remain valid; legacy records without it remain readable and closable under their existing gates. Reuse the current record paths, ordinary paragraph text and existing evidence locations; do not introduce another artifact type, machine-scored intent field, ledger event or reviewer roster.
7. **Bounded verification.** Exercise real creation, existing-target rendering/reconciliation and close-summary paths in disposable fixtures, including a renamed/declarative-layout control. Keep tests about delivery, compatibility and truthful summary behavior; do not add a model-evaluation system or claim that string assertions prove agent adherence. Run affected tests while implementing, then one canonical source suite on settled wave inputs; existing receipt reuse and ordinary bookkeeping rules remain.

## Scope

**Problem statement:** the framework's intent concept is inconsistently scaffolded and carried through execution and closure, allowing implementation completion to replace outcome assessment.

**In scope, intended file edits:**

- Canonical planning/execution/close seeds: `.wavefoundry/framework/seeds/170-plan-change.prompt.md` (including retargeting its wave-level `## Product intent` clause, about line 231, to the wave Objective), `180-implement-change.prompt.md`, `190-close-wave.prompt.md` (including retargeting its product-owner "wave Product intent" reference, about line 33, to the Objective); existing wave/bootstrap and prompt/upgrade guidance in seeds 110, 100 and 160 where they carry these contracts. Seed 160 extends its existing reconciliation row lists rather than adding a table or phase.
- The review clause has two owners only: seed 209's shared review guidance (readiness and delivery lanes) and seed 175 (plan review). Seed 221 and `docs/agents/code-reviewer.md` are not edited; they already route through seed 209.
- `.wavefoundry/framework/install/plan-template.md` and existing lifecycle templates for create-wave, implement-wave, review-plan, prepare-wave, review-wave and close-wave where they carry the changed clauses.
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`: the wave objective scaffold and existing `_generate_wf_close_wave_summary` only; paired handler-digest fixture if the changed public handler identity requires it. Existing declaration, publication and authorization behavior is protected.
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`: add `Product Intent` to `PLAN_TEMPLATE_REQUIRED_HEADINGS`, so `FreshPlanTemplateTests` fails when the shipped template loses it. No other renderer change; `review_policy.py` is not edited. Do not change review-policy canonicalizers, lane selection or receipt semantics.
- Self-hosted `docs/plans/plan-template.md`, corresponding public planning/implementation/review/close/upgrade prompts, and `docs/contributing/change-workflow.md` / `review-and-evals.md` as their existing contracts require. Preserve unrelated project text. No root AGENTS expansion is required.
- Existing tests for scaffolds, rendering, lifecycle summaries, carrier reconciliation and distribution compatibility, principally `test_render_agent_surfaces.py`, `test_server_tools_lifecycle.py` and `test_docs_lint.py`. Add focused cases to the owning files and use shared profile/layout fixtures.
- This admitted change, wave.md and authoritative ledger for ordinary workflow evidence.

**Out of scope:**

- Implementing or altering waves 2136j, 2136r or 2136s; broad agent-guide cleanup; a small-change lane or new review policy.
- New lifecycle states, hard gates, required lanes, identity rules, semantic quality scoring, routine evidence folders or new upgrade phases.
- Changes to external distribution repositories, terminology, private feedback or host-global settings. Downstream adoption is supported by the shared pack and fixtures, not claimed as an executed downstream deployment.
- Bulk historical backfill, closed-record edits, unrelated cleanup, packaging, release, commit or push under this planning request.

## Acceptance Criteria

- [x] AC-1: Public change creation using the reconciled project-local template and using the shipped fallback both produce the concise Product Intent scaffold; wave creation prompts for a shared outcome. Fixtures preserve the declared record vocabulary/layout and show that legacy documents need no bulk conversion.
- [x] AC-2: Planning, existing readback and existing review guidance consistently distinguish why, intended outcome, behavior, implementation and proof. A documented example changes mechanism while preserving intent, and another shows why all implementation checks can pass without establishing the claimed benefit. No new reviewer, approval stage or hard gate is introduced.
- [x] AC-3: The actual close-summary path retains an explicitly authored partial/not-established outcome, evidence reference and limitation without converting it into success. An older record with no assessment retains its current close behavior. No approval or benefit is inferred from an AC count.
- [x] AC-4: A fresh-target fixture materializes the intent contract from canonical assets. Existing-target delivery is the seed 160 agent-assisted checklist entry plus this repository's hand-reconciled `docs/plans/plan-template.md`; a fixture with a reconciled custom local template shows `new_change` produces Product Intent while custom prose is preserved and a repeat render converges. No mechanical rewrite of an existing operator template is added. A renamed/layout-declared fixture passes without introducing a live-checkout dependency. No extra upgrade scan, test/profile run, model work or evidence sidecar is required.
- [x] AC-5: The self-hosted templates and applicable prompts agree with canonical sources, and untouched historical/closed records and ledgers remain unchanged. The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Confirm the bounded producer/consumer map and existing ownership paths; record the implementation readback against Product Intent before editing.
- [x] Align canonical planning, execution, review and close clauses, install assets and upgrade reconciliation instructions under the relevant edit gates.
- [x] Update the existing objective scaffold and close-summary composition, preserving legacy behavior and publication/authorization boundaries.
- [x] Reconcile the affected self-hosted carriers and local plan template, preserving unrelated prose and other waves.
- [x] Add the focused creation/render/reconciliation/summary and declared-profile controls; demonstrate that removal of the changed contract or preservation behavior fails the relevant check.
- [x] Complete existing independent delivery review, final docs validation and one canonical source qualification on settled inputs; consolidate outcomes and limits in the existing records.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| intent contract and carriers | implementer | none | One write owner for the named seeds, templates and shared lifecycle source |
| verification | same implementer; independent existing reviewers | settled affected inputs | Focused checks during implementation; one final canonical suite; required independent review stays |

## Serialization Points

- `.wavefoundry/framework/seeds/170-plan-change.prompt.md`, `.wavefoundry/framework/seeds/180-implement-change.prompt.md`, `.wavefoundry/framework/seeds/190-close-wave.prompt.md`, `.wavefoundry/framework/seeds/110-wave-memory-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/175-review-plan.prompt.md`, `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/install/plan-template.md`, `.wavefoundry/framework/install/lifecycle-prompts/`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`, `.wavefoundry/framework/scripts/tests/test_docs_lint.py`, `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/plans/plan-template.md`, `docs/prompts/`, `docs/contributing/change-workflow.md`, `docs/contributing/review-and-evals.md`

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md`: clarify how existing creation/close human-view output carries intent without acquiring approval authority. `docs/contributing/change-workflow.md` and `review-and-evals.md` carry the outcome-versus-mechanism review convention. No new runtime boundary or storage schema.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Intent must reach real new records rather than remain a seed-only instruction. |
| AC-2 | required | Implementers and reviewers must use intent to assess the outcome. |
| AC-3 | required | Closure must retain an honest outcome assessment and support legacy records. |
| AC-4 | required | Installed and renamed consumers must receive the shared contract safely. |
| AC-5 | required | Self-hosting, preservation and change-local qualification. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-18 | Implemented the bounded intent contract in seeds 100/110/160/170/175/180/190/209, shipped plan and six lifecycle templates, and the corresponding current self-hosted planning/readback/review/close/upgrade/contribution carriers. Seed 160 extends existing agent-assisted mapping/checklist rows; the local plan template is hand-reconciled. Only Product Intent was added to the renderer's required-heading tuple; missing-only rendering and project additions remain intact. The released MCP spec paragraphs now describe creation and human-view summary behavior. The objective remains a single angle-bracket placeholder, retaining the existing unpopulated advisory. | Named source diff; seed 170 and change-workflow examples distinguish a bounded lookup from a cache, and delivered instructions from unobserved adherence. No historical/closed records or ledgers were edited by this implementer. |
| 2026-10-18 | Focused verification: 13 selected tests passed in 5.990s, covering public creation responses for every mintable kind, an existing custom local template under declared roots, Objective/advisory preservation, actual close publication, qualified partial/not-established assessments, exact-heading/CRLF/legacy behavior, real fresh rendering and shipped-template lint. Six selected cases also passed in 6.090s in a disposable copied framework with the shared second profile applied: set.md and docs/delivery/sets, with no live self-hosted documentation dependency. Five final carrier/handler-digest tests passed in 0.662s. | Named tests in NewChangeTests, WaveCreateScaffoldAlignmentTests, WaveCloseSummaryGenerationTests, BriefingLoopCarrierTests, ScaffoldBaselineTests, FreshPlanTemplateTests and HandlerDigestTests; temporary reproducer /private/tmp/2124l-renamed-fixture.py. Handler digest fixture unchanged. |
| 2026-10-18 | Guard/preservation controls: eight in-memory mutants failed their intended assertions with no errors/skips: remove fallback Product Intent heading; remove required-heading tuple member; ignore custom local template; omit authored outcome; select the first assessment; accept lowercase legacy heading; strip authored trailing spaces; lose CRLF heading support. Baseline cases passed before mutation. Existing carrier tests additionally reject deletion/reversal of the new brief, readback, intent comparison and upgrade-merge clauses. | test_public_creation_fallback_delivers_intent_for_every_new_kind; test_shipped_template_has_required_headings_and_declares_nothing; test_reconciled_custom_template_creates_intent_under_declared_layout; test_public_close_preserves_last_authored_intent_and_qualification; test_intent_composer_preserves_crlf_wrapping_and_legacy_output; BriefingLoopCarrierTests; temporary in-memory reproducer /private/tmp/2124l-intent-mutants.py. |
| 2026-10-18 | Initial canonical focused run: docs-lint 350 passed; renderer 170 exposed a new-clause placement parity error; lifecycle 644 exposed a new fixture's retained record_paths module copy. Both test-local defects were corrected and their named cases passed. Other existing lifecycle cases passed with two existing skips. That diagnostic run also correctly rejected concurrent material edits during the separate 2136s detour and this implementation, so it establishes no settled-tree qualification or receipt. Full MCP docs validation then passed; the temporary status-drift advisory was reconciled. Canonical settled-source suite and independent delivery review remain coordinator-owned and pending. | run_tests.py --file test_render_agent_surfaces.py --file test_server_tools_lifecycle.py --file test_docs_lint.py; corrected targeted selection above; wf_validate_docs; git diff --check clean. No whole-file retry or full/profile qualification was run by this implementer. |
| 2026-10-18 | Readback: make beneficiary, outcome and boundaries explicit in new plans, then use intent in existing readback/review work. Preserve the last authored Intent outcome assessment in close output without inferring benefit from implementation checks. For example, a partial outcome with an evidence link and unobserved agent-adherence limitation remains partial after close. Scope is the named seeds/templates/self-hosted carriers, two server seams and focused tests; existing operator templates remain missing-only under rendering. The frozen MCP spec edit is deferred to the coordinator. MCP live-file reads/keyword tools are callable; pre-implementation memory briefing rechecked the renderer's missing-only and contained-write boundaries. Both framework and seed gates are open. | Current plan; MCP gate status and memory_brief; server composer and renderer heading reads. |
| 2026-10-18 | Planned on operator instruction as one enhancement in a new wave. No source edits or implementation authorization consumed. | Operator request; existing seed/template and lifecycle-source reads. |
| 2026-10-18 | Verified seed 170:79-85 already requires Product Intent; shipped/local templates and current public creation omit it. Public `wf_new_enhancement` created this document without the section before authoring. `new_change` prefers the project-local template; lifecycle baseline rendering alone is missing-only. | Actual creation of 2124m; `server_impl.new_change`; `render_agent_surfaces.LIFECYCLE_PROMPT_BASELINES` and `SCAFFOLD_BASELINE_TEMPLATES`. |
| 2026-10-18 | Close composer currently reads titles, ACs, Progress Log and Decision Log and replaces Wave Summary; explicit intent assessment must be carried through that writer rather than placed where it will be discarded. Existing seed160 reconciliation distinguishes authored carriers from renderer regions. | `server_impl._generate_wf_close_wave_summary`; seed160 Changed briefing-loop/project-owned review carriers. |
| 2026-10-18 | Gapfill: indexed discovery is unavailable with index_runtime_stale; current-file MCP reads and exact keyword tools supplied the planning evidence. Temporary source inspection used no target repository, model operation or external private material. | Current MCP diagnostics and live-file source reads. |
| 2026-10-18 | Readiness repair (one bounded pass, coordinator session) after five fresh readiness lanes (red-team, code, qa, architecture, docs-contract). AC-4's existing-target half had no executable path, since every renderer path is missing-only; it now names the seed 160 checklist plus this repository's reconciled template, with no new rewriter. Seed 170's wave-level Product intent clause and seed 190's product-owner reference are retargeted to Objective. Requirement 4 now defines the `Intent outcome:` parse. The review clause has two owners (209, 175); seed 221, `docs/agents/code-reviewer.md`, `review_policy.py`, `test_shipped_reference_docs.py` and `test_upgrade_wavefoundry.py` leave scope, which also removes collisions with 2136r and 2136s. `PLAN_TEMPLATE_REQUIRED_HEADINGS` gains the heading so the shipped-template check can fail. Implementation notes: the Objective placeholder must stay one `<...>` span so `_wave_objective_unpopulated` still fires; the composer reads wave text it already receives; editing seeds rotates no receipt (`policy_input_snapshot` digests change docs and config only). | 2124l readiness lanes, coordinator session |
| 2026-10-18 | Focused readiness verification: red-team, code, qa, architecture and docs-contract lanes re-approved the repaired plan; the duplicated AC-4 clause they flagged was removed before readiness was recorded. Implementation note: `test_review_policy.py` holds a CRLF fixture of the Objective scaffold text; code review found it self-contained rather than compared to `create_wave`, so check it when the placeholder changes. | 2124l focused readiness round |
| 2026-10-18 | Final canonical qualification: `/Users/coryhacking/.wavefoundry/venv/bin/python .wavefoundry/framework/scripts/run_tests.py --no-cache` passed 11,911 tests across 200 files in 764.084 seconds, with 12 reported skips. Green receipt matches current framework inputs `de1645bfd5b392a8a9bb5b71d98df4fc5ddd8e05f5e0b46a597447420aa722cd`. Full `wf_validate_docs` passed with zero errors/warnings and `git diff --check` is clean. The earlier sandboxed attempt was interrupted after a localhost-bind refusal; it is not qualification evidence, and no tests or thresholds were changed to bypass it. This one completed run qualifies all four settled waves; no duplicate full profiles were added. Implementation, required delivery review, AC-5 and the final task are complete; operator closure remains pending. | `.wavefoundry/framework/test-cache.json`; existing named regression tests; wave Review Checkpoints; /private/tmp/wf-four-wave-final-suite.log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-18 | Reuse Product Intent in change documents and Objective in wave records. | Already defined by the canonical seed; makes the concept visible without a competing heading or duplicate record. Applies to framework and maintenance as well as product features. | Leave intent implicit in Rationale: keeps the observed drift. Add a parallel Intent document/schema: adds duplication and migration overhead. |
| 2026-10-18 | Carry intent through existing readback, reviewers and human-view closure output. | Keeps implementation choices answerable to the intended outcome while preserving current authority and stage gates. | Add an intent approval lane or blocking validator: creates overhead and cannot mechanically prove the semantic benefit. |
| 2026-10-18 | Preserve explicit outcome assessment; never infer it from task completion. | Delivery of guidance and achievement of the intended benefit are different claims. | Synthesize success from checked ACs: falsely promotes implementation proof into outcome proof. |
| 2026-10-18 | Adopt prospectively through existing install/upgrade reconciliation. | Reaches consumers and renamed distributions without rewriting historical evidence or adding upgrade work. | Bulk backfill all records: churns receipts and history without improving the already-completed outcomes. |
| 2026-10-18 | Existing-target template delivery stays agent-assisted through seed 160; no mechanical section inserter. | Every renderer path is missing-only, and a new rewriter is the mechanism the plan rules out. | Mirror `repair_declaring_scaffold` for plan templates: new upgrade mechanism and new write targets. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Another mandatory section becomes bureaucracy. | One sentence is sufficient; reuse existing headings and work, no new gate or artifact. |
| Tests prove text transport but are described as agent improvement. | Guidance explicitly separates intended benefit from observed delivery; closure retains uncertainty. |
| New summary output fabricates success or drops a qualification. | Actual partial/not-established controls and unchanged legacy fallback; no inference from checkbox count. |
| Existing projects keep an old local template or project-owned prompt. | Reconcile both sources through the existing ownership-aware upgrade path and test the existing-target shape. |
| Concurrent guidance waves share seeds, renderers and tests. | Single writer; serialize with 2136r/2136s; do not edit their plans or implementation from this wave. |

## Session Handoff

Planned and admitted only. Next: Prepare wave and independent readiness review when requested, then implement after successful readiness. Existing OPEN work remains undisturbed.
