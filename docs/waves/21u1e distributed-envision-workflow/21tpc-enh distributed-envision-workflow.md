# Distribute the Envision workflow with independent vision reviews

Change ID: `21tpc-enh distributed-envision-workflow`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-28
Wave: `21u1e distributed-envision-workflow`

## Rationale

The operator's existing personal `wf-envision` skill is unavailable to other Wavefoundry users and does not coordinate the requested architecture, red-team and archetype council reviews. Promote its reusable vision/horizon authoring contract into the framework's normal prompt and skill distribution.

## Product Intent

Operators of any Wavefoundry target can invoke Envision project or wf-envision to obtain a source-grounded project vision with useful technical horizons and candid independent review. The result supports strategic investment decisions without starting implementation or asserting future capabilities are shipped. AC-1 and AC-3 together demonstrate availability and a representative authoring outcome; they do not establish universal agent reliability or realized product benefit.

## Requirements

1. Ship a generic canonical Envision project seed, author its project-local prompt through seed 100, expose the shortcut in the catalogs/manifest and render the thin-pointer wf-envision skill for each active supported skill host when the backing prompt exists. Preserve existing project-authored vision content and customized prompt conventions. Follow the existing doc-gated TechDocs installation/reconciliation pattern, including render after prompt authoring; no new setup service or MCP tool.
2. Default authoring output is the project's existing canonical vision, otherwise root VISION.md, titled Project: Vision and Technical Horizons. Reuse the brief and repository facts; ground the starting point, distinguish verified capabilities from proposals, and specify meaningful horizons with prerequisites, demonstrations, exit criteria, failure conditions, uncertainty and intermediate value. Include sequencing, evaluation, architecture evolution, hard questions and the next bounded investment. Do not impose a twelve-month schedule, unlimited resources, an agent product, or Wavefoundry-specific founding brief on unrelated projects. Do not introduce the retired aspirational term from the earlier discussion.
3. On new/substantial vision authoring, coordinate independent architecture review, standalone red-team challenge and council-chair-led Archetype Council using the installed canonical role/protocol documents. Review one identified draft, preserve seat isolation and honest execution reporting, reconcile material findings into the document and retain a compact review record with unresolved decisions. Reuse the existing protocols rather than cloning their schemas or changing their authority. Minor revisions use affected reviews proportionately; explicit operator review scope controls.
4. Reviews are artifact advice, never wave readiness/delivery signoffs. Envisioning creates no waves or implementation backlog and changes no approval, deployment, commit or publication authority. Read-only discussion/review requests write nothing. If independent workers or role documents are unavailable, provide the useful draft or advice, disclose missing reviews and label any self-check; never claim the missing reviews passed or install/reconfigure hosts. Do not run an unbounded review/repair loop.
5. Keep the author's personal skill, project-specific vision drafts, unrelated wave closure changes and current process/environment configuration untouched. This distribution change does not run Envision against Wavefoundry or Tensorwell.

## Scope

**In scope:** canonical seed `179-envision-project.prompt.md`; seed 100 prompt distribution and seed 050 entry guidance; SKILL_REGISTRY registration, fixed vocabulary collision protection, framework text ownership inventory and focused renderer/seed tests; self-hosted backing prompt, prompt catalog/manifest, AGENTS shortcut and skills reference, platform mapping, project overview, framework README and changelog. Update the architecture data/control-flow description for the advisory vision-authoring path. Generated active-host skill surfaces come from the renderer.

**Out of scope:** creating a new MCP endpoint, changing lifecycle review semantics, new native host integrations, packaging/release, user-global skill removal, writing any project's vision, rewriting closed wave records, broader skill/role refactoring.

## Acceptance Criteria

- [x] AC-1: A target with the Envision backing prompt receives the named thin-pointer skill in each active supported host; a target lacking the prompt does not receive a dangling skill; rerender is stable and unrelated project content is preserved. The shipped seed/catalog path instructs install and upgrade to author the prompt and render the skill, without requiring a personal skill or Wavefoundry identity.
- [x] AC-2: The shipped prompt carries the generic vision/horizon contract and delegates the three requested advisory review forms to their canonical protocols. A reviewer can follow the links and distinguish review completion, unavailable independent review, unresolved findings and lifecycle approval authority. Read-only and narrow-edit requests have explicit bounded handling.
- [x] AC-3: An independent forward evaluation against a small non-Wavefoundry fixture produces a coherent grounded vision and review outcome using the shipped instructions; a separate read-only/unavailable-review scenario preserves files and reports its limitation. Evaluate observable output and actual actions, not exact prose. Record limitations and do not extrapolate universal quality from these samples.
- [x] AC-4: Change-owned tests and docs validation pass, current catalogs agree with the rendered skill, and no failure elsewhere is attributable to this change. macOS execution is recorded; portable Python/text behavior is assessed without claiming native Windows or Linux execution.

## Tasks

- [x] Add canonical Envision seed and seed100/050 distribution guidance; author self-hosted prompt and references.
- [x] Register the gated skill and add focused delivery/preservation regression coverage; render active host skills.
- [x] Run independent forward evaluation and reconcile demonstrated workflow defects.
- [x] Complete focused and canonical verification, independent delivery review, and session handoff.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Prompt authoring and coordination | coordinator | readiness | Sole owner of canonical seed and self-hosted prose |
| Renderer and tests | implementer | readiness | Own registry and focused tests only; MCP-first discovery |
| Independent evaluation/review | reviewers | draft/implementation | Read-only source; isolated temporary fixture outputs allowed |

## Serialization Points

Coordinator integrates all source changes before canonical qualification. No overlapping file edits. Reviewers do not edit source, prompt surfaces or lifecycle records.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/tests/fixtures/framework-text-ownership.json`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/179-envision-project.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `docs/prompts/envision-project.prompt.md`
- `docs/prompts/index.md`
- `docs/prompts/prompt-surface-manifest.json`
- `docs/agents/platform-mapping.md`
- `docs/architecture/data-and-control-flow.md`

Root AGENTS.md and CHANGELOG.md are also in scope. Personal skills and untracked VISION.md/docs/visions are protected.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` with the source-to-prompt-to-skill authoring path and artifact-only review boundary; runtime architecture and MCP transport do not change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Distribution is the motivating user outcome. |
| AC-2 | required | Review forms and authority boundaries must remain usable and honest. |
| AC-3 | required | Text delivery alone cannot prove an agent can use the workflow. |
| AC-4 | required | Integration must preserve existing behavior and qualify changed surfaces. |

## Progress Log

Readback: before this change a generic target with an authored Envision prompt receives no Envision skill. After seed100 reconciliation and rendering it will receive the thin-pointer skill; invoking its prompt produces technical horizons with three honest advisory review forms. Implement AC-1 through AC-4 in the declared renderer/vocabulary, seed/catalog and test files; preserve personal skill and vision drafts.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-28 | Personal skill and authoring guide read; existing TechDocs distribution pattern located. No implementation edits before readiness. | personal wf-envision/SKILL.md and references/vision-guide.md; render_agent_surfaces Skill/render_skills; seed100 TechDocs contract |

| 2026-10-28 | Executed pre-change generic-target full-render probe: authored CRLF prompt preserved, 65 unrelated outputs rendered, no Envision skills on all three active hosts; rerun made zero changes. Renderer owner found fixed vocabulary census contract requiring all three new collision reservations. | Independent implementer discovery; render_agent_surfaces/render_skills; test_vocabulary_prompt_names fixed-set census |

| 2026-10-28 | Renderer registration and gate-removal controls each produce two assertion failures; focused renderer199, vocabulary36 and ownership9 tests passed. Fresh public CLI rendered exactly three Envision skills; quick_validate passed in existing Wavefoundry environment (system Python lacks PyYAML). | SkillRegistryTests.test_envision_appears_after_prompt_authoring_and_preserves_project_content; registration deletion and requires_doc=None in-memory controls; fixed name collisions rejected |
| 2026-10-28 | Read-only independent trial completed with explicit unavailable-review disclosure and author-only self-check. The source-grounded advice correctly identifies aggregation-only current behavior and proposes local-stock/handoff/disconnected-sharing horizons. All17 fixture files hash-identical; zero new files. | /root/envision_readonly_trial; pantry.py stock.csv returned beans6/rice15; fixture under .wavefoundry/work/21u1e/evaluation/read-only |
| 2026-10-28 | Whole ownership-inventory check reports33 pre-existing omissions; scoped inventory delta adds seed179 only, no removals; ownership9 tests pass. No unrelated inventory backfill. Readiness packet architecture-role path transcription was corrected in a later typed approval; the worker's actual probe used the correct role path. | ActorTokenCensusTests; current packet correction in events.jsonl |

| 2026-10-28 | Independent Pantry Map trial produced4 grounded horizons and actual architecture/red-team/five-axis council reviews. One bounded author repair fixed stock conservation, restored authority, fulfillment metric, steward succession and terminology; affected independent checks closed findings. Five axes ran; two pre-read declarations are worker-attested, timing not independently observable, and Sun Tzu null phrase was confirmed afterward. | Unique inputs, final output, exact diff, raw review evidence and limits retained in envision-evaluation.json; final vision SHA256 1a793e04e51ab98eee8735a8627d771e055c51adfee0d99fad68c41c938254a6 |
| 2026-10-28 | First full suite executed12291tests/214files/12skips in562.497s, failed6 files due sandbox restrictions on local sockets/process lookup/cache writes. A65-test failing socket file passes unchanged with host permissions; canonical host-permission rerun in progress. | canonical.log; preserved refused-018c6008757d4b14b682414d7a581c9a.json; canonical-host.log |

| 2026-10-28 | Host-permission canonical run passed all12291tests/214files/12skips in555.559s, but repository guard refused a receipt because coordinator added unique envision-evaluation.json during execution. Reconcile correctly refused added-file acceptance. No test failure waived; freeze all nonignored repository files and rerun. Independent delivery Council/four lanes found no defects; QA/code/Council approvals await qualified receipt and final docs. | refused-28f54c78453041c5be3ff45ae08d6785.json; delivery/review-payloads.json; canonical-host.log |

| 2026-10-28 | Final frozen-tree canonical run passed 12,291 tests across 214 files with 12 skips in 558.329s on macOS; green receipt recorded without exceptions. Full docs validation passed. Independent code, QA, architecture, docs-contract and delivery Council approvals recorded; no findings. All four ACs complete; no native Windows/Linux execution claim. | test-cache.json result ok, inputs_hash 9c19c7d213ae0b974614373817c2ecb83b8bcbb250fcd0c67ef92a5d47715fa6, ran_at 2026-10-28T21:23:29.624364+00:00; events.jsonl; retained envision-evaluation.json |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-28 | Use canonical prompt plus registry thin pointer and existing seed100 reconciliation. | Makes the capability available to any target through the normal install/upgrade contract; prompt remains project-visible and role protocols remain authoritative. This delivers guidance, not enforced agent compliance: independent forward evaluation probes usability and review honesty. After release, operators can inspect skill availability and authored vision review records. It can still fail if prompt reconciliation is skipped or the host ignores guidance; name those limits instead of claiming universal completion. | Copy the personal skill verbatim: duplicates workflow bodies and imports user-local references. New MCP envision orchestrator: adds runtime/state machinery without a demonstrated need. |
| 2026-10-28 | Include architecture, red-team and Archetype Council in substantial Envision authoring; retain their artifact-only authority. | Operator explicitly requested these complementary reviews. Default composition supports feasibility, challenge and orthogonal strategic/prose critique; limited revisions and unavailable-worker reporting keep the workflow proportional. | Pure opt-in reviews would leave the requested integration unused by default; treating their verdict as lifecycle approval would conflate vision with implementation authority. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Review ceremony overwhelms useful vision work | One initial pass, bounded reconciliation and affected-review verification; disclose remaining issues. |
| Source guidance is delivered but workers do not follow it | Independent scenario evaluation; distinguish text, observed behavior and generalized claims. |
| Existing global wf-envision shadows project skill | Preserve global user content; name the installed project skill/backing prompt in handoff and qualify host discovery separately. |
| Generic workflow inherits Wavefoundry-specific assumptions | Use a non-Wavefoundry fixture and omit the personal founding brief. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
