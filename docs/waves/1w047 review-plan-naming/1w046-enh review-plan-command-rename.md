# Rename Plan Review to `wf-review-plan`

Change ID: `1w046-enh review-plan-command-rename`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-22
Wave: 1w047 review-plan-naming

## Rationale

The optional plan stress test is currently exposed as **Interrogate this plan** and `/wf-interrogate-plan`. That vocabulary is unnecessarily adversarial and obscures its relationship to the rest of the public review surface. Rename the workflow to the clearer **Review plan** / `/wf-review-plan` identity while keeping **Review wave** / `/wf-review-wave` distinct: plan review challenges a change document, or the current wave record when no change is named, before or after admission and before implementation; wave review runs the required lanes for an open wave and records typed evidence.

This is a complete public-surface migration, not a display-only alias. The canonical seed, self-hosted prompt, skill registry, rendered skills, install/upgrade guidance, manifests, catalogs, tests, and living references must converge on the new identity. Existing natural-language phrases remain accepted aliases for operator continuity, but the old skill name is retired so hosts do not expose two competing commands.

## Requirements

1. Make **Review plan** the primary shortcut phrase and `wf-review-plan` the only rendered skill for the optional plan stress test. Keep **Interrogate this plan** and **Stress-test this plan** as accepted natural-language aliases. Do not render or advertise a `wf-interrogate-plan` skill alias.
2. Preserve the current semantic contract and boundary with **Review wave** / `wf-review-wave`: plan review primarily examines one change document, falls back to the current wave record when no change is specified, may run before or after admission but before implementation, and returns the current Self-Answered Questions, Operator Questions or batch Question List, and Stop Condition outputs. It records no typed signoff and satisfies no prepare or delivery gate. Wave review continues to run the open wave's required lanes and record typed evidence.
3. Rename the canonical workflow seed from `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` to `.wavefoundry/framework/seeds/175-review-plan.prompt.md` and the self-hosted authored prompt from `docs/prompts/interrogate-plan.prompt.md` to `docs/prompts/review-plan.prompt.md`. Update titles, primary phrase, self-references, routing descriptions, and links while preserving the workflow's behavior and the two natural-language aliases.
4. Change the skill registry to render `wf-review-plan` from `docs/prompts/review-plan.prompt.md`. Add the three exact generated file paths `.codex/skills/wf-interrogate-plan/SKILL.md`, `.claude/skills/wf-interrogate-plan/SKILL.md`, and `.agents/skills/wf-interrogate-plan/SKILL.md` to `STALE_SKILL_PATHS`. The contained cleanup must unlink only that generated file and remove its parent directory only when empty, preserving any unrelated sibling content. Containment is against each declared host skill root, not merely the repository root: refuse a parent symlink into another in-repository directory, a parent symlink outside the repository, and a final `SKILL.md` symlink. Rendering must converge idempotently on the new skill in every active skill host.
5. Upgrade existing target repositories without overwriting project-authored prompt prose. Add `docs/prompts/review-plan.prompt.md` as the seventh missing-only lifecycle baseline owned by seed 175, with a packaged `.wavefoundry/framework/install/lifecycle-prompts/review-plan.prompt.md` template carrying lint-clean `Owner`, `Status`, and `Last verified: {{generated_at}}` metadata. Run the migration at the start of the freshly extracted `render_platform_surfaces.py` -> `render_agent_surfaces.py` subprocess, before both `render_skills` and lifecycle baseline materialization, so the installing upgrade uses the newly shipped logic and the first render points `wf-review-plan` at the migrated prompt. The migration must implement this explicit matrix:
   - old prompt exists and new prompt is absent, with all seven canonical contract lines in a recognized legacy form: move the project-owned file to `docs/prompts/review-plan.prompt.md` and replace only the exact lines in the closed table below; preserve every other byte, including project-authored extensions;
   - old prompt exists and new prompt is absent, but any of those seven contract lines is customized or unrecognized: preserve the old file, do not render the new skill or materialize the new baseline, and return an actionable blocking migration diagnostic;
   - new prompt exists and old prompt is absent: preserve the new file unchanged except for normal marker-owned or explicitly reconciled canonical regions already governed by upgrade policy;
   - both prompt paths exist: fail closed, preserve both files, skip baseline materialization for this prompt, and return an actionable blocking migration diagnostic rather than overwriting or deleting either;
   - neither prompt exists: let the normal missing-only lifecycle reconciliation materialize the new canonical prompt.
   A blocking migration diagnostic makes the upgrade result non-successful and requires operator resolution, but does not roll back unrelated already-extracted framework files.
   The only recognized legacy contract table is exact and case-sensitive:

   | Field | Accepted old line | Required new line |
   | ----- | ----------------- | ----------------- |
   | Heading | `# Interrogate This Plan` | `# Review Plan` |
   | Shortcut | ``Shortcut: **`Interrogate this plan`** \| Alias: **`Stress-test this plan`**`` | ``Shortcut: **`Review plan`** \| Aliases: **`Interrogate this plan`**, **`Stress-test this plan`**`` |
   | Purpose | `Optional stress-test of a consolidated change doc before wave admission. Walks every unresolved decision branch in Requirements, Acceptance Criteria, and Scope.` | `Optional stress-test of a consolidated change doc, or the current wave record when no change is specified, before or after admission and before implementation. Walks every unresolved decision branch in Requirements, Acceptance Criteria, and Scope.` |
   | Input fallback | `Given a change doc as context:` | `Given a change doc as context, or the current wave record when no change is specified:` |
   | When to use | `- Before admitting a complex or high-risk change` | `- Before or after admitting a complex or high-risk change, but before implementation` |
   | No-gate timing | `**Interrogate this plan** is an optional stress-testing tool, not a required lifecycle step. Use it before or after authoring a change doc but before wave admission.` | `**Review plan** is an optional stress-testing tool, not a required lifecycle step. Use it before or after plan admission, at the operator's discretion, before implementation begins.` |
   | Canonical source | ``See `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` for the full interrogation contract.`` | ``See `.wavefoundry/framework/seeds/175-review-plan.prompt.md` for the full plan-review contract.`` |

   A second closed legacy profile is admitted for the recovered pre-Shortcut public prompt shipped in `1.19.0+pko0`. It is recognized only when every accepted old logical line below occurs exactly once; any prefixed, suffixed, missing, duplicated, or mixed-profile line remains customized-old and fails closed. The trigger replacement expands one old bullet into two physical lines using the source line's existing newline style; all other replacements remain one-for-one and every unrelated byte is preserved.

   | Field | Accepted `pko0` old logical line | Required new logical line(s) |
   | ----- | -------------------------------- | ---------------------------- |
   | Heading | `# Interrogate This Plan Prompt` | `# Review Plan Prompt` |
   | Primary trigger | ``- `Interrogate this plan` `` | ``- `Review plan` `` followed by ``- `Interrogate this plan` `` |
   | Canonical source | ``Use `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` to:`` | ``Use `.wavefoundry/framework/seeds/175-review-plan.prompt.md` to:`` |
   | Input fallback | ``- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<change-id>.md`) or wave record (`docs/waves/<wave-id>/wave.md`).`` | ``- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<change-id>.md`) or, when no change is specified, the current wave record (`docs/waves/<wave-id>/wave.md`).`` |
   | Scope wording | `- Do not re-plan or derive new scope during interrogation; record emergent scope items as follow-on candidates rather than introducing them inline.` | `- Do not re-plan or derive new scope during plan review; record emergent scope items as follow-on candidates rather than introducing them inline.` |
   | No-gate identity | `- Do not treat this as a required lifecycle gate; it is entirely voluntary before or after plan admission.` | `- Do not treat **Review plan** as a required lifecycle gate; it is entirely voluntary before or after plan admission.` |
   | Bounded wording | `- Keep interrogation bounded to Requirements, Acceptance Criteria, and Scope — do not re-examine explicitly resolved Decision Log entries.` | `- Keep plan review bounded to Requirements, Acceptance Criteria, and Scope — do not re-examine explicitly resolved Decision Log entries.` |
   | Batch example | ``- In `--batch` mode (e.g. `Interrogate this plan --batch`): dump all unresolved questions as a numbered list rather than asking one at a time. Each item includes the recommended answer and source citation.`` | ``- In `--batch` mode (e.g. `Review plan --batch`): dump all unresolved questions as a numbered list rather than asking one at a time. Each item includes the recommended answer and source citation.`` |

6. Extend `.wavefoundry/framework/scripts/reconcile_scan.py` as the canonical reconciliation owner so living references to the retired skill name, old public prompt/seed paths, and the project-specific `docs/prompts/agents/interrogate-plan.prompt.md` path are reported and repairable. The project-specific agent path is report-only: instruct the operator to merge any unique guidance into `docs/prompts/review-plan.prompt.md` and remove the obsolete file; do not generically rename or rewrite it. Add exact positive controls there, negative controls for both supported phrase aliases, and exact-path exclusions for historical wave/change/changelog evidence and the retained `.wavefoundry/framework/scripts/benchmarks/model_swap_v2_result.json`; require that retained result file to be byte-identical before and after implementation. Upgrade output must print each finding's existing disposition key and explain that truthful historical narrative may be recorded once as `historical-record` in `docs/reconcile-dispositions.json`, while live instructions must be repaired. Do not implement a second classifier in `upgrade_wavefoundry.py`. Fresh installs and packages must contain only the new seed, prompt references, skill name, and manifest entry.
7. Update every living public carrier that owns the workflow vocabulary or routing boundary, including bootstrap/install/upgrade seeds, framework and project READMEs, `AGENTS.md`, prompt catalogs and manifest, platform mapping, project overview, contributor workflow guidance, and council/red-team/archetype/plan-feature routing text. Preserve the hash-bound `.wavefoundry/framework/scripts/benchmarks/model_swap_docs_queries.json` input and its retained `model_swap_v2_result.json` result byte-identically as one historical provenance pair. Add the new terminology and Review-plan-versus-Review-wave distinction to an ordinary live semantic-routing regression under the existing prompt-surface test tier instead of modifying the frozen benchmark pair. Preserve closed wave archives and earlier changelog entries as historical evidence.
8. Record the change under the current `1.19.0` changelog section unless release ownership moves it before implementation closes. Do not change MCP schemas, lifecycle state-machine behavior, review-policy semantics, or `wf-review-wave` behavior.
9. Keep disposition-key precision out of this repair. The existing key remains file + retired surface + matched text and therefore may cover repeated identical text in one file; plan any line-/context-sensitive key redesign as a separate change with its own compatibility and store-migration analysis.

## Scope

**Problem statement:** The public command family calls one optional review workflow an "interrogation," even though the product vocabulary and operator intent are better expressed as a plan review. A partial rename would leave split command discovery, stale generated skills, unsafe downstream prompt migration, or ambiguity with `wf-review-wave`.

**In scope:**

- Rename the canonical seed, self-hosted prompt, primary shortcut, and rendered skill.
- Preserve `Interrogate this plan` and `Stress-test this plan` as natural-language aliases only.
- Remove each generated `wf-interrogate-plan/SKILL.md` on render/upgrade and remove its directory only when empty.
- Add safe, project-prose-preserving prompt-path migration and conflict reporting.
- Update living catalogs, manifests, routing text, installation/upgrade carriers, and tests; add a live semantic-routing regression without modifying the frozen model-swap benchmark pair.
- Add exact semantic-boundary, convergence, containment, migration-matrix, fresh-install, packaging, and stale-reference tests.

**Out of scope:**

- Renaming or changing `wf-review-wave` or the Review wave workflow.
- Changing what plan review asks, its one-question-at-a-time interaction model, or its no-signoff authority.
- Adding a compatibility skill named `wf-interrogate-plan`.
- Rewriting closed wave archives, historical changelog entries, or retained benchmark results.
- Broadly overwriting project-authored lifecycle prompts during upgrade.
- Automatically rewriting or renaming project-specific `docs/prompts/agents/interrogate-plan.prompt.md` content.
- Redesigning reconciliation disposition keys or migrating existing disposition stores.
- Adding or changing an MCP tool, lifecycle schema, review lane, or policy gate.

## Acceptance Criteria

- [x] AC-1: All active public command catalogs and skill descriptions identify **Review plan** / `wf-review-plan` as the primary optional plan review, accept the two legacy natural-language aliases, preserve change-doc input plus current-wave fallback, pre/post-admission timing, the three canonical question/stop outputs, and no-signoff authority, and distinguish it explicitly from **Review wave** / `wf-review-wave`; no active carrier advertises `wf-interrogate-plan` as a skill.
- [x] AC-2: The canonical seed exists only at `.wavefoundry/framework/seeds/175-review-plan.prompt.md`, the self-hosted prompt exists only at `docs/prompts/review-plan.prompt.md`, both preserve the workflow contract and aliases, and fresh install/package manifests contain no retired seed or prompt path.
- [x] AC-3: Rendering each active skill host creates `wf-review-plan`, removes only the contained stale `wf-interrogate-plan/SKILL.md`, removes its parent only when empty, preserves unrelated skill content, and is byte-idempotent on a second render. Three explicit negative controls must prove no deletion through (a) a parent symlink into another in-repository directory outside the declared host skill root, (b) a parent symlink outside the repository, and (c) a final `SKILL.md` symlink.
- [x] AC-4: Installing-upgrade tests execute the fresh-code seam before both skill rendering and baseline materialization across all five prompt states (recognized old-only, customized old-only, new-only, both, neither), exercise both closed legacy profiles in Requirement 5, prove exact logical-line replacement plus byte identity for every unrelated byte and physical newline preservation, prove blocking/no-mutation behavior for embedded or mixed-profile customizations and both-path conflicts, and prove neither-state materialization from the new metadata-complete seventh baseline. Each recognized-old profile must prove the first render emits `wf-review-plan` against the migrated path with change-doc/current-wave fallback and pre/post-admission-before-implementation timing. The faithful Phase-1-complete tree fixture must exercise the real install template, renderer, and validator and finish lint-clean.
- [x] AC-5: `reconcile_scan` tests report living retired skill/path references including `docs/prompts/agents/interrogate-plan.prompt.md`, do not flag either supported phrase alias, exact declared historical evidence, `.wavefoundry/framework/scripts/benchmarks/model_swap_docs_queries.json`, or `.wavefoundry/framework/scripts/benchmarks/model_swap_v2_result.json`, and preserve the semantic distinction between plan review and wave review. Upgrade output exposes the scanner's stable disposition key and distinguishes live repair from a truthful `historical-record` disposition. Both frozen benchmark files are byte-identical before and after implementation, their existing hash/provenance test remains green, and a separate live prompt-surface regression exercises the new primary phrase, both phrase aliases, the retired-skill negative, and the Review-plan-versus-Review-wave routing boundary.
- [x] AC-6: Seed/bootstrap/install/upgrade carriers, `SKILL_REGISTRY`, prompt manifest/index, platform mapping, root and framework READMEs, `AGENTS.md`, project overview, contributor guidance, and council-related routing docs agree on the new identity; a repository-wide classified census finds no unexplained living retired skill/path reference, while a project-specific agents prompt is reported for manual merge/removal rather than auto-rewritten.
- [x] AC-7: Focused renderer, upgrade, install, packaging, prompt-surface, shipped-reference, and semantic-routing tests pass; the full framework suite passes without unintended skips; `wf_validate_docs` and `git diff --check` are clean; the `1.19.0` changelog entry accurately describes the hard skill cutover, phrase aliases, both closed migration profiles, and report-only legacy-agent guidance.

## Tasks

- [x] Rename seed 175 and the self-hosted authored prompt; update canonical title, primary shortcut, links, self-references, aliases, and the plan-review versus wave-review boundary.
- [x] Replace the skill-registry entry with `wf-review-plan`; add the three exact old host `SKILL.md` files to contained stale cleanup; preserve nonempty parents; and add in-repo parent, outside-repo parent, and final-file symlink refusal tests.
- [x] Extend the fresh-subprocess migration matrix with the exact recovered `pko0` public-prompt profile, newline/all-other-byte preservation, and embedded/mixed-profile refusal controls.
- [x] Report the project-specific agents prompt for manual merge/removal; expose stable disposition keys and historical-record guidance through the canonical reconciliation/upgrade path.
- [x] Update the canonical upgrade carrier and `1.19.0` changelog for the field repair while preserving both frozen model-swap files byte-identically.
- [x] Render/synchronize active host skill surfaces from the registry and verify only `wf-review-plan` remains.
- [x] Add the recovered-profile, manual-agent-carrier, disposition-guidance, and classified stale-census regressions.
- [x] Run focused and full verification, run `wf_validate_docs`, run `git diff --check`, and confirm the frozen benchmark pair remains byte-identical.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| canonical-contract | implementer | — | Rename seed/prompt and establish the exact public identity, aliases, and review boundary first. |
| skill-rendering | implementer | canonical-contract | Update registry, stale cleanup, rendered hosts, containment, and convergence tests. |
| upgrade-migration | implementer | canonical-contract | Add the seventh baseline; implement the seven-line, five-state project-owned prompt migration before skill and baseline rendering in the fresh renderer subprocess; update reconciliation in its canonical owner. |
| carrier-alignment | implementer | canonical-contract | Update living docs, manifests, seeds, live routing regression, and changelog; preserve the frozen benchmark input/result pair and other history. |
| integrated-verification | qa-reviewer | skill-rendering, upgrade-migration, carrier-alignment | Run focused/full suites, install/package checks, classified census, docs lint, and diff validation. |

Read-only delivery lanes: `code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `docs-contract-reviewer`, and `release-reviewer`. The implementer owns repository mutations. Reviewers inspect and record evidence only.

Protected surfaces:

- `.wavefoundry/framework/seeds/175-review-plan.prompt.md` is the canonical generic workflow source after the rename.
- `.wavefoundry/framework/install/lifecycle-prompts/review-plan.prompt.md` is the packaged missing-only baseline generated from seed 175; the renderer reads this install template and has no seed fallback.
- `docs/prompts/review-plan.prompt.md` is Wavefoundry's self-hosted authored twin; downstream copies are project-owned and must follow the explicit migration matrix.
- `.codex/skills/`, `.claude/skills/`, and `.agents/skills/` are renderer-owned only for registered/stale generated files; unrelated content and nonempty parent directories are protected.
- Closed waves and historical changelog entries are read-only evidence. `.wavefoundry/framework/scripts/benchmarks/model_swap_docs_queries.json` and `.wavefoundry/framework/scripts/benchmarks/model_swap_v2_result.json` are one frozen input/result provenance pair and both must remain byte-identical.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md`
- `.wavefoundry/framework/seeds/175-review-plan.prompt.md`
- `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `.wavefoundry/framework/seeds/177-red-team-review.prompt.md`
- `.wavefoundry/framework/seeds/236-archetype-council.prompt.md`
- `.wavefoundry/framework/seeds/237-council-review.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/review-plan.prompt.md`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_model_bundle.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`
- `.wavefoundry/framework/scripts/benchmarks/model_swap_docs_queries.json`
- `.wavefoundry/framework/scripts/benchmarks/model_swap_v2_result.json`
- `.codex/skills/wf-interrogate-plan/SKILL.md`
- `.codex/skills/wf-review-plan/SKILL.md`
- `.claude/skills/wf-interrogate-plan/SKILL.md`
- `.claude/skills/wf-review-plan/SKILL.md`
- `.agents/skills/wf-interrogate-plan/SKILL.md`
- `.agents/skills/wf-review-plan/SKILL.md`
- `.codex/skills/wf-council/SKILL.md`
- `.claude/skills/wf-council/SKILL.md`
- `.agents/skills/wf-council/SKILL.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/prompts/interrogate-plan.prompt.md`
- `docs/prompts/review-plan.prompt.md`
- `docs/prompts/index.md`
- `docs/prompts/prompt-surface-manifest.json`
- `docs/prompts/plan-feature.prompt.md`
- `docs/prompts/red-team-review.prompt.md`
- `docs/prompts/archetype-council.prompt.md`
- `docs/prompts/council-review.prompt.md`
- `docs/agents/platform-mapping.md`
- `docs/references/project-overview.md`
- `docs/contributing/feature-workflow.md`
- `AGENTS.md`
- `README.md`
- `.wavefoundry/framework/README.md`
- `CHANGELOG.md`

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — update only if it names the old prompt/skill identity in the operator-routing path.
- `docs/architecture/testing-architecture.md` — update only if the upgrade migration or classified living-reference census creates a new permanent verification tier; otherwise record N/A in the Progress Log because existing renderer/upgrade/package test tiers own the work.
- No ADR is expected: this is a public identity and migration change within existing prompt, renderer, upgrade, and review-authority boundaries.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Defines the public identity and prevents ambiguity with the required wave review. |
| AC-2 | required | Establishes one canonical seed/prompt location for installs and packages. |
| AC-3 | required | Prevents duplicate host commands and unsafe stale cleanup. |
| AC-4 | required | Protects downstream project-authored prompt prose during upgrade. |
| AC-5 | required | Makes drift detection useful without rewriting aliases or history. |
| AC-6 | required | Ensures every living carrier and packaged surface converges. |
| AC-7 | required | Supplies executable delivery evidence and release documentation. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-21 | Plan authored from the operator-approved terminology and migration decisions; no framework implementation started. | Decision Log; change remains `planned`; Stage Gate requires wave admission and readiness before source edits. |
| 2026-08-21 | Readiness cycle 1 repaired two blocking plan defects: preserved the current plan-review input/timing/output contract, corrected target ownership and paths, specified file-level stale cleanup, and defined the fresh-code five-state prompt migration and reconciliation owner. | `PREP-PLAN-SEMANTICS-001`; `PREP-IMPLEMENTATION-MAP-002`; independent code/docs/red-team evidence; framework source remains unmodified. |
| 2026-08-21 | Readiness cycle 1 QA follow-up made four proof boundaries exact: retained result path/byte identity, the fixed three-line migration table, three declared-root symlink polarities, and the wave-level pre/post-admission timing statement. | `PREP-QA-FALSIFIABILITY-003`; QA packet oracle; framework source remains unmodified. |
| 2026-08-21 | Readiness cycle 2 corrected benchmark provenance: both the frozen model-swap input and retained result are now protected byte-for-byte, and new terminology coverage moves to the live prompt-surface test tier. | `PREP-BENCHMARK-PROVENANCE-004`; `embed_bench.MODEL_SWAP_DOCS_SHA256`; `test_model_bundle.py`; framework source remains unmodified. |
| 2026-08-21 | Readiness cycle 2 expanded the recognized legacy migration from three identity lines to seven exact contract lines and moved it before both skill rendering and baseline materialization, preventing a renamed prompt from retaining pre-admission-only semantics. | `PREP-MIGRATED-PROMPT-SEMANTICS-005`; mechanical legacy-prompt transform; framework source remains unmodified. |
| 2026-08-21 | **Thought:** Begin implementation in dependency order: establish the canonical Review plan contract, then implement contained skill cleanup and fresh-upgrade migration, align living carriers, and finish with integrated verification. Builder allocation: one implementation owner for renderer/migration code, one for public carriers, and one independent verification owner; overlapping files remain single-owner. | `wf_implement_wave(1w047, mode=create)`; receipt `review-policy-85bb615055f4b184bb8d`; pre-implementation memory briefing. |
| 2026-08-22 | **Observe:** Implemented the complete identity cutover and safe downstream migration. The renderer now owns only `wf-review-plan`, removes the retired generated skill within each declared host root, migrates only the seven exact legacy prompt lines across the five declared states, and materializes the seventh metadata-complete lifecycle baseline. Reconciliation, packaging, fresh-install, upgrade, carrier, and routing tests cover the new behavior; both frozen benchmark artifacts remain byte-identical. | Focused integration matrix 893/893; final framework suite 7,482/7,482 across 64 files; frozen SHA-256 values `63359684…11e5` and `6906ac23…fb13`; `wf_validate_docs` clean; `git diff --check` clean. |
| 2026-08-22 | **Reflect:** The first full-suite run correctly rejected one living literal mention of the retired skill in the prompt index, even though the prose said it was not rendered. Rephrasing that sentence without the retired token made the classified living-reference boundary consistent; the focused 51-test CLI guard and the complete suite then passed. | `test_wf_cli.NoLiveReferenceToRetiredWrapperTests`; focused rerun 51/51; clean full-suite rerun 7,482/7,482. |
| 2026-08-22 | **Observe:** Delivery review found two required-AC gaps that the green suite missed: the legacy-prompt migrator matched canonical strings inside longer customized lines, and the renderer-owned `wf-council` skill still presented a legacy phrase as the sole plan-review route. | `QA-DEL-1`; `QA-DEL-2`; independent code, QA, and docs-contract public-path probes. |
| 2026-08-22 | **Reflect:** Cycle 3 replaced substring migration with exact logical-line recognition while preserving physical line endings, added a seven-field embedded-prefix/suffix rejection matrix, updated the canonical council registry/body to make **Review plan** primary with both aliases secondary, regenerated all three host skills, and extended the live routing regression to cover the council consumer. | Focused repair tests 25/25; adjacent renderer/upgrade/reconcile/package/CLI matrix 835/835; fresh independent reverification required before approvals. |
| 2026-08-22 | **Observe:** The next delivery pass found one containment gap and one public-doc layout residual: `render_skills` treated a symlinked declared skill root (or a same-root stale-skill parent symlink) as its containment anchor, and the new README boundary paragraph temporarily left the `/wf-techdocs` row outside the skills table. | `CODE-DEL-1`; disposable declared-root and sibling-parent sentinel probes; docs-contract changed-Markdown table census. |
| 2026-08-22 | **Reflect:** Cycle 3 now preflights every lexical component of active skill roots, stale cleanup paths, and generated skill targets before any mutation, with declared-root and same-root-parent regressions added to the existing outside-root/final-file matrix. The README paragraph was moved below the complete skills table without changing its contract text. | `SkillRegistryTests.test_retired_plan_skill_cleanup_is_contained_to_each_declared_host_root`; renderer suite 113/113; final framework suite 7,483/7,483 across 64 files; `wf_validate_docs` and `git diff --check` clean. |
| 2026-08-22 | **Observe:** Downstream `1.19.0+pko0` evidence exposed a second canonical public-prompt shape that predates the seven-line Shortcut contract, plus a project-specific agents prompt outside renderer ownership and historical handoff findings that need disposition guidance. A blind upgrade would extract the pack, then fail the fresh renderer phase; a manual pre-migration was required. | `FIELD-DOWNSTREAM-LEGACY-PROMPT-001`; recovered SHA-256 `882a2b09…bd2` and `650abb3c…6e7`; downstream `pko0 -> pkw3` upgrade report. |
| 2026-08-22 | **Reflect:** Cycle 4 admits the recovered Trigger-Phrases public prompt as a second exact profile, adds an exact current-wave fallback transform, preserves CRLF/LF through the one-to-two-line alias expansion, reports the project-specific agents prompt for manual merge/removal, and prints stable disposition keys with truthful-history guidance. The local upgrade carrier avoids repeating the retired path so the living-reference census remains useful. | Focused repair matrix 84/84; affected renderer/upgrade/reconcile/shipped/package matrix 805/805; final framework suite 7,488/7,488 across 64 files; `wf_validate_docs` and `git diff --check` clean; frozen hashes `63359684…11e5` and `6906ac23…fb13`. |
| 2026-08-22 | **Observe:** Fresh council, code, and QA review found that the cycle-4 scanner test covered the agents-layer path only as prose inside `guide.md`; an actual surviving file at that path produced no carrier-identity/manual-merge finding. | `PREP-AGENT-CARRIER-EXISTENCE-006`; exact recovered agents prompt SHA-256 `650abb3c…6e7`; actual-path `scan_repo` probe. |
| 2026-08-22 | **Reflect:** Cycle 4 now synthesizes a report-only finding from the exact legacy agents prompt's file identity before content scanning and adds a faithful actual-file regression whose body does not name its own path. No automatic merge/delete or disposition-key redesign was added. | `RetiredPlanReviewIdentityTests.test_legacy_agents_prompt_is_reported_by_file_identity`; warning-strict reconciliation suite 54/54; final framework suite 7,489/7,489 across 64 files; fresh independent reverification pending. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-21 | Use **Review plan** and `wf-review-plan` as the primary public identity. | It is direct, consistent with the command family, and names the artifact being reviewed. | Keep Interrogate terminology; rename only the skill while retaining the old phrase as primary. |
| 2026-08-21 | Keep **Interrogate this plan** and **Stress-test this plan** as natural-language aliases, but remove the `wf-interrogate-plan` skill. | Phrase aliases preserve conversational compatibility; a second skill would clutter host menus and make the canonical command ambiguous. | Hard-remove all aliases; render both skills indefinitely. |
| 2026-08-21 | Rename both seed 175 and the self-hosted prompt file. | A complete identity migration avoids permanent path-level split vocabulary. | Leave old filenames as internal implementation details. |
| 2026-08-21 | Use an explicit old-only/new-only/both/neither upgrade matrix and fail closed when both files exist. | Lifecycle prompts are project-owned after materialization; silent replacement or conflict deletion would lose authored prose. | Always overwrite from the seed; prefer one file automatically when both exist. |
| 2026-08-21 | Preserve historical archives/results and classify only living stale references. | Historical evidence should remain truthful to the version that produced it. | Repository-wide blind replacement. |
| 2026-08-21 | Keep `wf-review-wave` unchanged. | Plan review and wave review have different authority, timing, and outputs. | Merge the workflows behind one command. |
| 2026-08-21 | Preserve change-doc input, current-wave fallback, pre/post-admission use, question-list output, and stop-condition behavior. | The operator asked for a rename, not a semantic narrowing; seed 175 already defines these behaviors. | Limit Review plan to a single pre-admission change document. |
| 2026-08-21 | Run prompt-path migration in the freshly extracted renderer subprocess before adding the seventh missing-only baseline. | First-cycle upgrade runs old code in process; the subprocess is the earliest declared seam that executes the newly shipped migration logic before materialization. | Put migration only in the old in-process upgrader; defer migration to a second upgrade. |
| 2026-08-21 | Customized old-only and dual-file states preserve files and make the upgrade non-successful with an actionable diagnostic. | Silent merging or advisory-only continuation could create two competing project-owned prompts or destroy custom prose. | Guess a winner; overwrite; advisory-only success. |
| 2026-08-21 | Recognize exactly seven legacy contract lines and replace them with the fixed Requirement 5 table before rendering the new skill or missing-only baseline. | Identity-only replacement left the canonical legacy prompt's change-doc-only and pre-admission-only behavior behind; a closed literal table preserves current semantics while keeping customized-old classification and all-other-bytes preservation independently falsifiable. | Rename only three identity lines; fuzzy matching; an open-ended list of recognized forms. |
| 2026-08-21 | Preserve both model-swap benchmark files byte-identically and add a separate live routing regression. | The query is hash-bound and the retained result embeds it; changing only the input destroys historical provenance. | Rewrite the frozen query and keep a stale result; regenerate the historical comparison for a naming-only change. |
| 2026-08-22 | Admit the recovered pre-Shortcut public prompt as a second exact legacy profile, but keep the project-specific agents prompt report-only. | The public file has the current workflow semantics and a repeatable canonical shape; the agents file carries repository-specific source guidance that a generic renderer cannot merge safely. | Fuzzy migration; blindly rename both files; require every downstream operator to hand-migrate. |
| 2026-08-22 | Make existing historical-record dispositions actionable in upgrade output, but defer any disposition-key redesign. | The current store already supports truthful-history suppression; changing key identity would require compatibility and migration policy beyond this field repair. | Ignore false-positive history; redesign keys inside the release repair. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Operators confuse Review plan with Review wave. | Pin input fallback, authority, and output differences in both skill descriptions, catalogs, routing tests, and public docs without narrowing current timing. |
| Upgrade overwrites project-authored prompt extensions, rejects a known older canonical prompt, or renames a prompt while retaining stale behavior. | Transform only one of the two closed exact legacy profiles before skill and baseline rendering; preserve unrelated bytes and physical line endings; block customized, mixed-profile, and dual-file conflicts before either output is created. |
| Old and new skills coexist after render or upgrade. | Add all three host paths to contained stale cleanup and test first render plus idempotent convergence. |
| Stale cleanup or rendering follows a symlink at or below a declared lexical skill root. | Preflight every lexical component before any mutation and retain declared-root, same-root-parent, outside-root, and final-file symlink controls. |
| A blind stale-reference census flags supported aliases/history or misses a project-specific agents prompt. | Classify living skill/path references separately from phrase aliases and historical evidence; report the agents prompt for manual merge/removal; print stable disposition keys and truthful-history guidance while leaving key precision to a separate change. |
| The rename accidentally changes plan-review behavior or review authority. | Keep workflow content semantically unchanged and add boundary tests proving no typed wave signoff or gate satisfaction. |
| The release entry drifts from the actual cutover behavior. | Record the hard skill cutover, retained phrase aliases, and safe upgrade behavior under `1.19.0` during final reconciliation. |
| New terminology coverage corrupts the frozen model-swap comparison. | Protect both input and result with before/after hashes and put current routing assertions in the ordinary prompt-surface test tier. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
