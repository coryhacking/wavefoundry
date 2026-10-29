# Deliver Envision upgrades and product-led discovery

Change ID: `21vpo-enh envision-upgrade-and-discovery`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-28
Wave: 21tpp envision-product-vision

## Rationale

The improved Envision authoring contract must be discoverable through skill/catalog wording that leads with the product destination and path, and later revisions of seed179 must reach projects that already hold an Envision prompt. The previous combined plan 21ux4 mixed these delivery mechanisms with potentially iterative vision-quality evaluation. This change takes ownership of its former Requirements 11–12 and AC-6 with separate acceptance and review targets.

Seed179 has not shipped in any release: wave 21u1e was committed as aa8d3b8c after v1.38.0, and 21u1e plus this wave are expected to ship together. In that release every target takes seed100's missing-prompt authoring route, so no field target performs a 21u1e-to-21ux4 merge. The changed-seed179 rule protects subsequent revisions; this release's upgrade evidence is therefore one bounded probe of the rule, not a matrix for a transition no target will make.

Seed160 already has explicit merge-safe guidance for changed seed178. Its changed-seed carriers do not yet name seed179; seed100's Envision entry describes general reconciliation but leaves this upgrade trigger implicit. The current registry description and summary bullets emphasize review coordination. These are guidance/copy changes using existing delivery paths, not a new merge engine.

## Product Intent

Operators upgrading a target that already holds an Envision prompt receive later seed179 revisions without losing project-specific content, and agents discovering the skill understand that it establishes an ambitious product future and a practical, value-delivering path. AC-1 and AC-2 establish bounded upgrade/discovery outcomes; AC-3 confirms integration with the actual authoring candidate. This does not establish the quality of visions produced by that candidate, which belongs to companion 21ux4.

## Requirements

1. Add an explicit changed-seed179 reconciliation rule to seed160 and the self-hosted upgrade prompt, modeled on changed-seed178 guidance. Retain the read-only pre-apply seed diff; when seed179 changed, reconcile its changed canonical instructions into an existing Envision prompt after extraction during that installing run. Preserve project-only additions, metadata and unrelated content. If absent, author through the existing seed100 path. Do not run Envision or alter a project's vision during upgrade.
2. Support restructured canonical instructions, not just wording substitutions. Use the known prior canonical prompt and incoming seed to map changed/moved clauses, preserving local additions rather than replacing the entire project-owned file. Restructuring alone is not a conflict. If local wording conflicts with an incoming rule, a prior canonical span cannot be distinguished from local edits, or a safe placement cannot be determined, stop the affected merge and present the conflict to the operator. Do not guess, discard edits or claim successful reconciliation. A current reconciled prompt is stable on repetition.
3. Make the skill description, three summary bullets and Envision catalog entries lead with product destination, beneficiary value and the path through useful, enduring/adaptable capabilities. Preserve concise advisory-review, read-only and authority boundaries, with the backing prompt owning the full workflow. Update the registry and regenerate active-host skills through the public renderer. Preserve name, backing path, doc gate, active-host selection and invocation policy, including Claude model invocation. Use the existing `SkillRegistryTests` pattern for skill validation: direct string assertions on rendered header fields, copy and invocation policy, plus the shared single-line description and no-`": "` checks, extended in that same shared test with a no-`" #"` assertion (an unquoted value is silently truncated at a YAML comment). Keep the existing renderer and frontmatter format; do not add a YAML parser dependency or a separate general YAML validator for this change. Seed050 wording pinned by `test_seed_100_and_seed_050_register_the_shortcut` is either preserved or updated with that test in this change.
4. Reconcile catalog wording from the current seed050/100 guidance while preserving local additions, then rerender surfaces and run the docs gate after prompt reconciliation. Explain the difference between agent-executed prompt merging and executable rendering; neither setup alone nor rendering alone merges the project's prose. No generic merger or seed150 redesign.
5. Integrate the authoring companion's agreed artifact-flow contract in the architecture doc: detailed findings and actual review coverage live in the sibling/existing review location or response, with a short dated status link in the vision. Correct the current flow wording that credits seed100 with merge-safe reconciliation: seed160's agent-executed upgrade step merges a changed seed179 into an existing prompt, seed100 authors a missing prompt, and rendering only emits the skill. Correct the existing Unreleased changelog line that says the workflow is delivered to all targets through prompt reconciliation. Own the scoped architecture, catalog and changelog integration so the two changes have disjoint source write targets. Release wording must describe observed delivery separately from the authoring change's qualified outcomes.

## Scope

**In scope:** `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`; Envision entries in seeds050/100; `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/prompts/index.md`, AGENTS.md, `.wavefoundry/framework/README.md` and `docs/agents/platform-mapping.md`; wf-envision description/bullets in `.wavefoundry/framework/scripts/render_agent_surfaces.py` and affected expectations in `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`; generated `.agents/skills/wf-envision/SKILL.md`, `.claude/skills/wf-envision/SKILL.md`, `.codex/skills/wf-envision/SKILL.md`; scoped Envision paragraphs in `docs/architecture/data-and-control-flow.md`; CHANGELOG.md entries for the two coordinated changes.

**Read-only integration inputs:** seed179 and `docs/prompts/envision-project.prompt.md` owned by 21ux4, and the frozen 21u1e prompt. Do not edit these as part of delivery. Preserve personal skills, all real vision drafts, unrelated work and closed-wave evidence. No renderer algorithm, runtime/MCP service, permission, packaging or release changes.

**Wave boundary:** admit this and 21ux4 into the same future wave, with no blanket dependency preventing delivery implementation or review while authoring evaluation continues. Final candidate integration is a serialization point. A subsequent relevant candidate edit reopens only affected integration evidence; an unchanged mechanism does not need a repeated full review. The shared wave cannot close until both changes settle; this split does not authorize a separate release or bypass final qualification.

## Acceptance Criteria

- [x] AC-1: One bounded upgrade probe exercises the new rule through the real seed160 mechanism. Its inputs are the old/new seed179 pair (the 21u1e seed at aa8d3b8c and the frozen 21ux4 candidate) plus the 21u1e local prompt carrying one compatible project-only addition. A fresh agent that did not write the rule, given only the upgrade prompt and the fixture, performs the reconciliation. Expected result: the frozen 21ux4 candidate local prompt plus the preserved addition, differing only by documented wrapper/metadata differences; restructuring alone does not yield a conflict, and a repeat reconciliation produces no further change. One separate genuine-conflict variant (a local rule contradicting an incoming rule) stops the affected merge and reports it without overwriting the disputed content. The missing-prompt route is seed100's existing authoring path and needs no new trial. Report actual patches, the diff against the expected result and preservation evidence; citing the rule is insufficient. A full customization matrix is deferred until a released baseline exists.
- [x] AC-2: Public rendering produces the registered product-led skill description/bullets for each active supported host, preserves doc gating/inactive hosts and project-authored prompt/vision bytes, and is stable on repetition. Catalogs agree with the registered identity and authoring contract. Focused tests assert literal product-led phrases from Requirement 3 (not only equality with the registry value, which a stale registry would also pass), check the rendered header delimiters, expected name and description using the existing string-assertion pattern, retain the shared description checks, and positively assert that the Claude wf-envision skill carries no `disable-model-invocation`. They detect stale copy, missing emission or destructive replacement. These are focused rendering assertions, not a general YAML parsing test, and require no new parser dependency. This establishes surface delivery, not agent adoption or vision quality.
- [x] AC-3: The final integration identifies the exact incoming seed/local-prompt candidate, verifies their relevant artifact/discovery contract against delivery-owned docs and surfaces, and records passing change-owned tests/docs validation with no failure elsewhere attributable to this change. A relevant candidate change requires a targeted recheck. Architecture wording places detailed review evidence in the sibling/existing review location or response. Report macOS evidence and any untested native platforms honestly; do not repeat companion vision-quality trials as a delivery gate.

## Tasks

- [x] Admit and ready both plans; freeze the exact 21u1e baseline and define delivery fixtures and expected outcomes.
- [x] Add upgrade guidance, product-led registry/catalog wording and the architecture artifact-flow update; preserve unrelated content.
- [x] Update focused renderer expectations and regenerate active-host skills through the public path.
- [x] Run the bounded upgrade probe (clean restructure with one compatible addition, repeat, one genuine conflict) through a fresh agent against the frozen actual candidate; retain inputs, patches, identities and the diff against the expected result.
- [x] Complete scoped independent delivery review and final candidate integration, contribute accurate release wording and share the final canonical qualification boundary with 21ux4.

## Fixture Contract

The baseline is closed wave 21u1e as committed in aa8d3b8c: local `docs/prompts/envision-project.prompt.md` SHA-256 `1c3b54f34cc07980bff05a4ae208b863d540fb6b25d4f26c90747afc9202362a` (11,652 bytes, 1,526 whitespace-separated words) and seed `179-envision-project.prompt.md` SHA-256 `36a2875c7378caf2eba994f908047cf36c3f3909c73b7a25967f9e52aaf30c87` (11,597 bytes, 1,521 words). Retrieve them from that commit and verify the hashes; do not substitute a generic old prompt. The incoming artifact is the actual restructured seed179 from 21ux4, identified by its content hash; normalize only documented seed/local wrapper differences when assessing canonical parity.

The clean canonical case must converge on the expected result; defaulting a restructure to “conflict” fails AC-1. A conflict result is correct only for the genuine-conflict variant. The conflict variant is written before the reconciling agent starts and is not shown to it as a labelled trap. This is a bounded agent-reconciliation probe plus executable renderer checks, not an invented deterministic merge service, and one probe shows the rule can work, not that every host reliably follows it. Preserve unique inputs and patches so the old-to-new result remains reviewable.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Delivery implementation | implementer | wave readiness | Owns only listed delivery sources and local carriers |
| Delivery verification | independent reviewers | frozen delivery source | No repeated vision-quality evaluation |
| Candidate integration | coordinator and affected reviewer | frozen actual 21ux4 candidate | Read-only candidate; targeted integration evidence |

## Serialization Points

Separate write ownership from 21ux4. Delivery may finish its mechanism and focused review before authoring evaluation finishes. Before final qualification, confirm the actual candidate identity and perform affected integration checks. Serialize architecture/changelog edits through this owner; authoring supplies outcome evidence without editing those files. Freeze all nonignored files during canonical qualification.

When a predeclared verification batch ends with a required outcome unproven, or a repair fails its recheck, return evidence/options to the operator before expanding scope or starting another batch. No autonomous repair/retest loop is authorized by this plan.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/README.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/prompts/index.md`
- `docs/agents/platform-mapping.md`
- `docs/architecture/data-and-control-flow.md`
- `.agents/skills/wf-envision/SKILL.md`
- `.claude/skills/wf-envision/SKILL.md`
- `.codex/skills/wf-envision/SKILL.md`

Root AGENTS.md and CHANGELOG.md are also in scope. Request code, QA and docs-contract review for the relevant delivery behavior; readiness determines required lanes. The companion authoring files are read-only integration inputs, not duplicate write/review targets for this change.

## Affected Architecture Docs

Own the Envision source-to-prompt-to-skill and authoring/review-artifact paragraphs in `docs/architecture/data-and-control-flow.md`, incorporating the changed-seed route and companion R8's sibling-review-file contract. No runtime architecture changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Later seed179 revisions reach existing prompts safely; this release proves the rule with one bounded probe. |
| AC-2 | required | Skill/catalog discovery expresses the product purpose and renders correctly. |
| AC-3 | required | The actual authoring candidate is integrated without coupling delivery to its quality trials. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-28 | Implementation and required delivery review complete. All four specialist lanes and targeted Council approved; reader-protocol finding independently resolved with limitations retained. All required ACs/tasks complete, edit gates closed, source fingerprint and matching 12,291-test receipt unchanged. Full docs validation and diff whitespace check passed; unique evaluation proof retained, global handoff updated. Wave remains OPEN; no close/commit/push authorized or performed. | wave.md Review Checkpoints and typed events.jsonl; envision-evaluation.json; docs/agents/session-handoff.md. |
| 2026-10-28 | AC-3 final integration verified: incoming seed179 f0b8d82721689464f9957066d455e638dc0521f273212e0ce028291a2370190d and local prompt c57874fdc70af8cf5b685c1b3d33ae1daf4ad8799dc289fcf3b9cb1e5ef018dc remain unchanged; all 17 reviewed source blobs match. Independent code/architecture checks establish parity, product-led discovery and sibling-review flow. 18 focused tests and four controls pass; canonical 12,291-test host-permitted receipt is green, and current full Prepare dry-run docs/garden checks pass. No native Windows/Linux execution or universal upgrade-adherence claim. Final approvals remain tracked separately. | Source-review-fingerprint.json; delivery-review/code.json and architecture-docs.json; qualification-attempts.json; review-policy receipt46f4fbfacbb33d0b8445 unchanged. |
| 2026-10-28 | Fresh upgrade author followed the multi-seed changed report and actual upgrade prompt: compatible output exactly equals frozen candidate plus declared glossary addition; repeat made no changes. A different fresh context stopped the genuine authority conflict and left prompt/vision bytes unchanged. Separate code reviewer independently checked provenance, expected-byte equality, preservation and current hashes, and reran 18 focused tests plus four known-bad controls. | `.wavefoundry/work/21tpp/upgrade-probe/results.json`, both probe reports, and delivery-review/code.json; typed code-reviewer approval recorded. Bounded reconciliation, not full installer/catalog merge execution or universal compliance. |
| 2026-10-28 | Canonical source qualification passed 12,291 tests across 214 files, 12 existing skips, 554.420s with host permissions. Earlier restricted run retained: six failing files included blocked sockets/process inspection/bootstrap-cache writes and a vendored assertion; unchanged host run passed all. No failure waived or source changed to obtain green. | `.wavefoundry/work/21tpp/qualification-attempts.json`; green inputs_hash 209c121b1e2785206e6a31bacfaa1695ae01d5bbd2e4928ee7a0df0635ab8aed, ran_at 2026-10-29T00:04:38.475259+00:00. |
| 2026-10-28 | Delivery mechanism and discovery draft implemented across 15 owned paths. Existing SkillRegistryTests plus seed050/100 pin: 18 passed, zero skips. Known-bad controls detected stale copy, missing emission, destructive prompt replacement and comment-token description. Public render changed exactly three Envision skills; repeat changed nothing. Shared description census found no existing comment token. AC-1 and final AC-3 await actual frozen authoring candidate; release wording remains provisional. | `.wavefoundry/work/21tpp/tests/delivery-evidence.json` and delivery-controls.py/json; macOS ARM execution only. Full docs validation passed; coordinator reconciled status warnings. |
| 2026-10-28 | Readback: make Envision discovery lead with product destination, beneficiary value and useful enduring/adaptable capabilities; merge changed seed179 instructions during upgrade while preserving project additions and stopping genuine conflicts. Example: existing prompt plus a project-only rule becomes incoming canonical guidance plus that rule, without running Envision or changing VISION.md. Delivery owns only its listed carriers, registry/tests, catalogs, architecture/changelog and generated skills; AC-1 and AC-3 await the frozen candidate. Existing string assertions and public renderer verify delivery. Independent implementer delivery21tpp owns these files; current model selected for bounded code/copy work, actual runtime identity unknown. | Fresh wf_implement_wave create succeeded; baseline aa8d3b8c hashes verified; memory briefing inspected and edit gates opened. |
| 2026-10-28 | Split from 21ux4 before readiness at operator request. Recorded exact closed-wave prompt hash and explicit restructure/conflict expectations. No implementation or fixture execution claimed. | Current 21u1e prompt bytes; inspected seed160 changed-178 carrier and registry/preservation test in prior planning |
| 2026-10-28 | Readiness round 1 (receipt review-policy-6bf876336950f44cd443): red-team primer found AC-1 tested a transition no field target makes, since seed179 never shipped. On operator instruction, 21u1e was committed and pushed (aa8d3b8c) and these plan edits were made. Rescoped AC-1 to one bounded probe with the old/new seed pair, an expected result and a fresh reconciling agent; added YAML-safe copy, literal-phrase and invocation-policy assertions, the seed050 pinned wording, and the seed100/seed160 flow and changelog corrections from code, QA and architecture review. | Red-team primer; code, QA and architecture readiness reports; git tag v1.38.0 and commit aa8d3b8c |
| 2026-10-28 | Readiness round 2 (receipt review-policy-944232a6e53119d307b9) binding implementation decisions, recorded without changing ACs. (1) The AC-1 probe input includes a pre-apply seed-diff report naming several changed seeds, of which seed179 is one, so the probe also tests that the upgrading agent notices the rule. (2) The fixture declares where the project-only addition lands in the expected result so the diff is mechanical; the repeat run uses the same fresh agent, and the conflict variant uses a new fresh agent. (3) AC-2's YAML check uses a stdlib structural assertion that fails rather than skips: one-line description, no `": "` or `" #"` sequence, no leading YAML indicator character. Delivery reports test_ran_without_unintended_skip honestly. (4) Reword seed100's Envision entry so it no longer claims merge-safe reconciliation and points at seed160's changed-seed179 rule, keeping seed100 consistent with the corrected architecture doc. | Red-team round-2 primer challenge 4; code round-2 findings 1 and 2; QA round-2 advisories 4 and 5; architecture round-2 finding 1 (seed100 Envision entry) |
| 2026-10-28 | Docs-contract round-2 clarifications. The documented wrapper/metadata differences between seed179 and the local prompt are exactly the title line (`# 179 - Envision Project` versus `# Envision Project`) and the Owner/Status/Last verified block, with the date refreshed; the AC-1 diff normalizes only these. For AC-2, the round-2 stdlib structural check is the operative reading of "parse the generated frontmatter as YAML". | Docs-contract round-2 findings 1 and 2 |
| 2026-10-28 | Operator directed reuse of the existing skill-testing approach. Updated Requirement 3 and AC-2 to use existing string/header, copy and invocation-policy assertions without a new YAML parser or general validator. This supersedes the YAML-specific interpretation in the two round-2 Progress Log entries above; their other decisions remain unchanged. The prior readiness receipt predates this acceptance edit; refresh affected readiness before implementation. | Three existing SkillRegistryTests passed: registry namespace/description policy, host invocation gates, and Envision emission/preservation/repetition. |
| 2026-10-28 | Readiness round 3 clarification: under the operator-directed test approach, the round-2 leading-YAML-indicator check and its fail-rather-than-skip clause are intentionally not carried forward; product-led prose is not expected to start with an indicator character, and this is accepted as unchecked. The shared description test gains only the no-`" #"` assertion; the implementer confirms no existing registry description contains `" #"` before adding it. | QA round-3 advisories 1 and 2 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-28 | Separate delivery and authoring changes in one wave. | Different failure modes, targets and review evidence deserve separate ownership; final integration remains a narrow real dependency. | One change repeats unrelated review through authoring iterations. Separate waves offer separate closure but differ from requested grouping. |
| 2026-10-28 | Expect a clean 21u1e-to-restructured179 merge to succeed; reserve conflicts for genuine uncertainty or local incompatibility. | A rule that refuses every substantial revision would not deliver the improved workflow. The prior canonical bytes and actual candidate make the assertion falsifiable. | Unspecified older fixture may pass trivial substitutions while missing restructuring. Whole-file replacement discards project ownership. |
| 2026-10-28 | Treat this release as Envision's first ship; prove the changed-seed179 rule with one bounded probe. | Seed179 is absent from every release, so all targets author the prompt fresh in this release. The rule matters for later revisions; a fresh-agent probe with a defined expected result and one genuine conflict shows it works without a matrix for an unpopulated transition. | Full five-variant matrix: proves a path no target takes now. No probe: leaves the rule unexercised until a field upgrade fails. |
| 2026-10-28 | Reuse the changed-seed178 instruction pattern and existing renderer. | Agent guidance handles local prose while rendering handles registered surfaces. Test each boundary honestly; do not equate instructions with universal compliance. | A general merge engine or seed150 redesign adds scope without demonstrated need. |
| 2026-10-28 | Follow the existing skill renderer tests for Envision; no new YAML parser dependency or general YAML validator. | Operator direction; the existing tests exercise header/copy assertions, description restrictions, host invocation policy, doc gating, preservation and repeat rendering. Three representative tests passed unchanged. Literal product-led copy assertions still detect stale wording independently of registry equality. | Mandatory parser adds a dependency for a copy change; bespoke YAML restrictions expand validation beyond the established approach. Focused string assertions do not claim general YAML validity. |


## Risks

| Risk | Mitigation |
| --- | --- |
| Destructive merge or blanket conflict refusal | Exact old/new fixture, compatible additions and genuine conflict cases with explicit expected outcomes. |
| Candidate changes after verification | Record hash and recheck affected integration assertions before final qualification. |
| Scope split implies independent release | State shared-wave closure and final qualification boundaries explicitly. |
| Agent-guidance probe overstates upgrade guarantees | Retain actual observations and distinguish them from executable rendering and broader host behavior. |

## Session Handoff

Admitted with 21ux4 into wave 21tpp, not opened. The prior readiness receipt predates the operator-directed Requirement 3 / AC-2 revision to reuse existing skill tests; affected readiness must be refreshed before implementation. No seed, renderer or generated skill has changed.
