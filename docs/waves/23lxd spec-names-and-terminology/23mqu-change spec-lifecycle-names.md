# Rename the lifecycle prompts, phrases and skills from "change" to "spec"

Change ID: `23mqu-change spec-lifecycle-names`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-16
Wave: 23lxd spec-names-and-terminology

## Rationale

Engineers in the enterprise where the downstream distribution runs call this workflow "spec-driven", and many arrive from spec-driven tools such as Spec Kit and OpenSpec. Wavefoundry never uses the term: on 2026-11-16 "spec-driven", "Spec Kit" and "OpenSpec" appeared only in `VISION.md` (a comparison) and seed 002 (legacy corpus import). The operator decided on 2026-11-16 to make "spec" the real name of the planning document, not an alias. This change renames what people type and open: the lifecycle prompts, their shortcut phrases and their skills, and it states the vocabulary once.

It is the first of two linked changes. `23myn-change spec-and-behavior-contract-terminology` rewords existing prose in the same wave. MCP tool names, record labels and identifiers keep "change" by design: a spec describes one change, and tools and records identify the change.

## Product Intent

People who plan work with Wavefoundry plan, add, implement and close a spec, under those names, and an engineer arriving from another spec-driven tool recognises the framework in its first screen. Before: the phrases, prompt files and skills say "change" and the term "spec-driven" is absent. After: **Plan spec** and its siblings are the primary phrases, `/wf` lists `wf-plan-spec` and `wf-close-spec`, and the introductions say what Wavefoundry is. The earlier phrases keep working. No record, ledger or closed wave is rewritten in any repository.

Vision alignment: this serves adoption of Horizon 1 (dependable delivery on the existing foundation). `VISION.md` says a structured workflow alone is not a differentiation claim, so the positioning names spec-driven as the method and keeps waves, review evidence and gates as what Wavefoundry adds. `VISION.md` is not edited.

AC-1, AC-3 and AC-7 together test whether the intent was established.

## Vocabulary (decided 2026-11-16)

| Term | Meaning | Was |
| --- | --- | --- |
| spec | The document that plans one change | change doc |
| change | The unit of work a spec describes; it has an id and a status, and a wave delivers changes | unchanged |
| wave | The reviewed bundle of changes | unchanged |
| behavior contract | A durable document under `docs/specs/` describing implemented, tested behaviour | spec |

`Change Status:` and the `## Changes` heading name the change and stay, and `Status:` is the state of the spec document. The path `docs/specs/` stays. The `Change ID:` label and the `change_id` key stay as they are, by design: they identify the change.

## Requirements

1. Every default lifecycle prompt whose shortcut contains the word "change" is renamed by substituting "spec" in its slug and its shortcut, and keeps its earlier shortcut as an alias. The derived set governs. On 2026-11-16 it is five: `plan-change` to `plan-spec` (**Plan spec**), `add-change-to-wave` to `add-spec-to-wave` (**Add spec to wave**), `remove-change-from-wave` to `remove-spec-from-wave` (**Remove spec from wave**), `implement-change` to `implement-spec` (**Implement spec**) and `close-change` to `close-spec` (**Close spec**).
2. Skills follow their prompts: `wf-plan-spec` and `wf-close-spec` on every skill host. `wf-close-spec` stays operator-owned and manual-only on the Claude host. A skill file at an earlier default name (`wf-plan-change`, `wf-close-change`) is removed on render, with its folder and any operator-policy file in it, unless a current registry skill or a declared extension skill uses that name. The earlier names are not added to the fixed retired-name lists, because a distribution may already use them.
3. An installed repository is migrated on render by the profile-aware prompt-name migration, not by a fixed pair. A key moves from its earlier default slug only when all of these hold: the manifest's `prompt_names` record has no entry for the key; the manifest's public prompt list registers the earlier default doc; and the earlier slug is not the applied slug of any other key. The same rule decides the applied name wherever the renderer or the server reads one: the Close entry repair in the manifest and the server's prompt-path lookup. The public prompt and the agent body under `docs/prompts/agents/` then move to the profile's name by exact byte copy and the manifest is updated to the new doc and shortcut. The existing whole-plan preflight applies: if any pair has both a source and a target that differ, or a source that is a link or outside the repository, nothing is written and one error names every conflicting pair. Content is never rewritten. Links to the old paths are reported, not rewritten. When the manifest is missing or unreadable and an earlier-named prompt exists, the render does not create the new-named baseline beside it and reports that the manifest must be repaired first. Seed 160 gains an upgrade instruction, beside its existing prompt-name reconciliation, telling the upgrading agent to edit the moved prompts' authored titles and `Shortcut:` lines, the project's prompt index and agent-guide rows, and every other mention that the link report or a search for an earlier phrase, path or skill name finds. The live sub-instructions of seed 160's earlier rename bullet that tell an agent which phrase to write are updated to the current names.
4. A distribution profile that renames any of these prompts keeps its own names: its recorded applied names are honoured, and nothing of its is moved or removed. This holds when the distribution gives another key one of the earlier default slugs (for example its container prompt at `implement-change`).
5. The earlier phrases stay valid. Each resolves to the renamed prompt, appears as the alias on the prompt's `Shortcut:` line, and is not reported as retired by the reconcile scan.
6. The two seeds named for these prompts are renamed with history: `170-plan-change.prompt.md` to `170-plan-spec.prompt.md` and `180-implement-change.prompt.md` to `180-implement-spec.prompt.md`. Seed numbers do not change. Every live reference to the old file names is updated. The install templates under `install/lifecycle-prompts/` keep their file names: the renderer looks each one up by its profile key, and the keys do not change.
7. The vocabulary above is stated once in shipped text (the core-concepts section of seed 001) and once in self-hosted text (`docs/references/project-overview.md`), and other surfaces point at it.
8. The introductions state that Wavefoundry is a spec-driven development framework, that a spec plans one change, and that a wave bundles changes, reviews them and closes them: root `README.md` opening, `docs/index.md`, `docs/references/project-overview.md`, the framework README (Framework Identity) and the workflow topic of the install operator summary in seed 012 step 2.15. Where an introduction mentions behavior contracts, the first mention is the full phrase with its meaning or a pointer to the vocabulary in Requirement 7.
9. Root `README.md` gains a short mapping table for readers arriving from Spec Kit and OpenSpec with three rows: the in-flight document (spec), the durable document (behavior contract), and the bundle (wave). Each external-tool cell is checked against that tool's current official documentation during implementation and the table states the check date. The cells are `unverified` at plan time.
10. `CHANGELOG.md` Unreleased records the renames, the automatic move, the link report and its repair, and the note for distributions in Requirement 4, including that a distribution slug equal to one of the new default slugs now fails validation at import.

## Scope

**Problem statement:** the names people type and open say "change" for a document the operator has decided is a spec.

**In scope:**

- The five prompt names, their phrases and aliases, the two skills, and the installed-repository migration.
- The three framework file renames and their references.
- The vocabulary statement, the positioning sentences and the mapping table.

**Out of scope:**

- Rewording existing prose: `23myn-change spec-and-behavior-contract-terminology`.
- MCP tool names and `wf_help` goals. They are named for the change and stay.
- Record labels and headings, the `change_id` key and parameter, change-kind tokens, diagnostic codes, configuration keys and code identifiers (including `change_doc_checklist.py`).
- `docs/contributing/change-workflow.md`: its name refers to the work, not the document.
- `VISION.md`.

**Platforms:** file moves use the renderer's existing byte-copy and unlink path. Behaviour is the same on Windows, macOS, Linux and WSL2; the conflict preflight treats a case-only name difference as it does today.

## Acceptance Criteria

AC-1, AC-3 and AC-7 together establish the intent.

- [x] AC-1: A render under the default profile into a tree that holds the five earlier prompts, their agent bodies and the two earlier skills leaves each prompt and agent body at its new path with identical bytes and no file at the old path, a manifest naming the new docs and shortcuts with each doc and shortcut appearing once, docs lint passing on the resulting tree, `wf-plan-spec` and `wf-close-spec` on each active skill host, and no earlier skill folder. The rendered Claude `wf-close-spec` carries `disable-model-invocation: true`. A second render changes nothing. The same holds for a tree that starts from the feature-named prompts: it ends at the spec names with a manifest naming them.
- [x] AC-2: A render into a tree where one prompt has differing files at both its old and new paths writes nothing, and its error names that pair.
- [x] AC-3: Under the default profile, each new phrase and each earlier phrase from Requirement 1 resolves through the server's shortcut resolution to the renamed prompt, and the `Shortcut:` line of each of the five prompts in this repository, and of each freshly materialized baseline, shows the new phrase with the earlier one as its alias. Seed 160 carries the upgrade instruction in Requirement 3.
- [x] AC-4: A test derives the renamed set from the default prompt table by the rule in Requirement 1 and asserts that no default shortcut still has "change" as its primary word, so a new prompt named for "change" fails.
- [x] AC-5: A render under the `prompt-names` fixture profile, which renames lifecycle prompts, produces that profile's names, validates, and moves or removes none of that profile's prompts or skills. A render under a profile that gives a non-change key an earlier default slug (the container prompt at `implement-change`) leaves that prompt and its skill in place with identical bytes.
- [x] AC-6: The two seeds in Requirement 6 exist under their new names with their history, and a census of the old file names over live text (the exclusions of `23myn-change spec-and-behavior-contract-terminology` Requirement 4) returns only the name-history exceptions listed in that change's Requirement 6.
- [x] AC-7: Each surface in Requirement 8 states the positioning, the two surfaces in Requirement 7 state the four terms, and no passage describes `docs/specs/` documents as in-flight work.
- [x] AC-8: Root `README.md` contains the mapping table with its check date, and the Progress Log cites the official page consulted for each tool.
- [x] AC-9: `MEMBER_HEADING`, `MEMBER_ID_LABEL`, `MEMBER_STATUS_LABEL` and `ITEM_NAME` keep their values, a document scaffolded after the change carries `Change ID:` and `Change Status:`, and an existing closed wave lints as before.
- [x] AC-10: `CHANGELOG.md` Unreleased carries the entry described in Requirement 10.
- [x] AC-11: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Prove the migration on a scratch copy first: old files present, new absent, default profile; then under the `prompt-names` fixture profile and under a profile that reuses an earlier default slug. Record what moved.
- [x] Open `framework_edit_allowed` and `seed_edit_allowed` before the first framework or seed edit; close both when done.
- [x] Rename the five default prompt names and add the earlier phrases as aliases in `vocabulary_profile.py`; update the default pin table and add the derived-rule test.
- [x] Teach the profile-aware prompt-name migration the earlier default slugs under the rule in Requirement 3, and the server's prompt-path lookup the same rule; remove earlier-default skill files unless a current skill uses the name; cover AC-1, AC-2 and AC-5.
- [x] Make the vocabulary edit, the migration edit and the render of this repository one step, then reload the MCP server before relying on lint or prompt lookup: the required prompt paths derive from the vocabulary, so this repository lints red between the edit and the render.
- [x] Add the seed 160 upgrade instruction from Requirement 3.
- [x] Update every consumer of the earlier names: the lint constants for required prompt files, the reconcile scan tables, the lifecycle baseline table, the operator-only skill set, and the prompt manifest in this repository.
- [x] Rename the two seeds with `git mv`; update every hit of the AC-6 census.
- [x] Run the migration in this repository through `wf render-surfaces`, then repair the reported links.
- [x] Write the vocabulary statement, the positioning sentences and the mapping table; verify the external cells and record the pages.
- [x] Add the `CHANGELOG.md` Unreleased entry.
- [x] Run `wf_validate_docs`, then the framework test suite last, including the declared second profile on the vocabulary, render and skill tests.

## Agent Execution Graph


| Workstream           | Owner       | Depends On | Notes |
| -------------------- | ----------- | ---------- | ----- |
| scratch-proof        | implementer | -          | Execute the migration before designing around it |
| names-and-migration  | implementer | scratch-proof | Profile table, migration, consumers, tests |
| file-renames         | implementer | names-and-migration | Seeds, template, references |
| positioning          | implementer | -          | Vocabulary, introductions, mapping table |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/seeds/`
- `.wavefoundry/framework/README.md`
- `docs/prompts/`
- `docs/references/project-overview.md`
- `docs/index.md`

Root-level files also edited: the readme, the agent guide and the changelog. This change lands before `23myn-change spec-and-behavior-contract-terminology`, which rewords the same seeds and guides.

## Affected Architecture Docs

`docs/architecture/layering-rules.md`, vocabulary profile paragraph: update the statement of what a default prompt name is, since the keys no longer equal the default slugs. `docs/architecture/data-and-control-flow.md`: update if it names the prompt paths. No boundary or flow moves.

## AC Priority


| AC    | Priority  | Rationale |
| ----- | --------- | --------- |
| AC-1  | required  | The rename and its migration are the change |
| AC-2  | required  | A partial move would leave an installed repository failing lint |
| AC-3  | required  | Both vocabularies must reach the prompt |
| AC-4  | important | Keeps the rule complete as prompts are added |
| AC-5  | required  | A distribution must not lose its names |
| AC-6  | important | File names are part of a real rename |
| AC-7  | required  | The positioning and the definitions are half of the intent |
| AC-8  | important | External claims must be checked before they ship |
| AC-9  | required  | Proves this change did not move the record format |
| AC-10 | important | Upgraders need the repair steps |
| AC-11 | required  | Change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-16 | Plan authored; supersedes two drafts from the same session that planned aliases only | Decision Log |
| 2026-11-16 | Readied. Implementation notes carried from the council, none of which changes a requirement: (N-1) lint's `check_prompt_name_migration` is a fourth reader of applied names, so apply the Requirement 3 rule there or accept the weaker "required prompt file missing" diagnostic for an upgraded, unrendered repository; (N-3) the task line on skill removal is narrower than Requirement 2 and AC-1, which govern (folder, operator-policy file, declared extension skills); `stale_skill_paths()` must read the raw `EXTENSION_SKILLS` keys, not `declared_skills()`, or it recurses; keep the `CHANGE_PROMPT_RENAMES` targets literal; include a real distribution profile in the scratch proof if one is reachable locally. | Council verdict in `events.jsonl`; `.wavefoundry/work/23lxd/readiness-lane-outcomes.md` |
| 2026-11-16 | Scratch proof of the migration through the render entry point, five cases: default profile on this repository's tree (five prompts and two agent bodies moved byte-identical, one manifest entry each, earlier skill folders removed, second render a no-op, docs lint ok); `prompt-names` profile already applied (nothing moved); slug-reuse profile already applied (the distribution's `implement-change` prompt and skill untouched); the same profile adopted in the same upgrade (chain ran without conflict); partial profile (its one renamed prompt untouched, the other four moved). No real distribution profile was reachable locally. | `.wavefoundry/work/23lxd/scratch-proof-migration.md` |
| 2026-11-16 | Mapping table checked against the official Spec Kit and OpenSpec pages fetched on 2026-11-16: Spec Kit README, docs index, `spec-driven.md`, the evolving-specs and persisting-specs how-to pages; OpenSpec README, homepage, glossary and worksets pages. Neither tool has an equivalent of a wave in the pages read, and Spec Kit mandates no durable document; the table says so. | `.wavefoundry/work/23lxd/mapping-table-evidence.md` |
| 2026-11-17 | Implemented. The applied-name rule lives in `vocabulary_profile.applied_prompt_slugs` and is used by the renderer's migration and Close entry repair, the server's prompt-path lookup and the lint migration check (council note N-1 applied). Tests added for AC-1 to AC-5, the missing-manifest clause, the declared-skill clause and the lint check; mutations of the rule (empty earlier-slug table, rule body disabled, third clause removed, declared-name exemption removed, stranded-key detection disabled) each failed the tests that cover them. One behaviour to note: an agent body at an earlier name whose public prompt is not registered in the manifest does not move. One code addition beyond the plan's list: the outgoing Guru subagent description is registered as previously shipped, without which installed repositories would keep "Plan change" in it. | Implementer reports; `tests/test_vocabulary_prompt_names.py` `DefaultSpecRenameMigrationTests`; `tests/test_server_tools_lifecycle.py` `SpecPromptPhraseLookupTests` |
| 2026-11-17 | Delivery review. A fifth reader of applied prompt names was found by the red-team seat and repaired: `lifecycle_baseline_drift` now resolves lifecycle baselines through `applied_prompt_slugs`, so a Close prompt still at its earlier name is reported instead of dropped; the repair's own regression (a manifest symlinked outside the repository) was found by the code-reviewer and repaired. Also from review: seed 160, its self-hosted copy and the changelog name the two earlier seed file names as search targets, because lint does not check inline-code mentions; the previously-shipped Guru description table covers a profile that kept the earlier plan shortcut; a test pins that a declared skill may take only an earlier default name. Not executed by anyone: an installing upgrade from a packaged archive under old code, and any real distribution profile. Final full suite: 12,865 tests, OK. Council delivery intent fit for this change: establishes. | Wave record Review Checkpoints; `events.jsonl`; `suite-real-6.log` |
| 2026-11-16 | Record defect, noted by the council-chair: the red-team primer's three blocking findings and the code-reviewer's CR-1 were repaired in the plan without being recorded as typed readiness findings. They cannot be recorded faithfully after the fact, because a repair start must precede the repair. They are traceable in the wave's Review Checkpoints, the primer file and the code-reviewer approval. | Same |
| 2026-11-17 | The follow-on changes this spec names, `23myo-change spec-tool-names` and `23myp-change spec-id-label-and-key` (wave `23lxe`), were implemented, reviewed and then backed out on operator decision, and their wave folder was deleted on operator instruction. Tools, parameters, labels and keys keep "change" by design: a spec describes one change, and tools and records identify the change. References to those two changes in this spec's body are history; the body is not edited after readiness. | `docs/agents/session-handoff.md`; `CHANGELOG.md` Unreleased |
| 2026-11-17 | Correction to the row above that says the body is not edited after readiness: the operator then accepted a re-prepare, and this spec's body was corrected (the pointers to the removed follow-on changes; in `23myn`, Requirements 10 and 11, AC-9 and AC-10). See the wave record's Review Checkpoints. | Wave record |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-16 | Operator: "spec" is the real name of the planning document; the durable documents are "behavior contracts"; records keep `Change Status:` and `## Changes` | Decided in session. Those two name the change, which a spec describes, so they stay accurate. The operator later decided that new specs carry `Spec ID:` and that `change_id` becomes `spec_id`; a second wave implemented that and was backed out on 2026-11-17 (see the row of that date), so the label and key stay. `Change Status:` cannot fold into `Status:`: both lines exist and differ in 1,010 of 1,846 documents. | (a) Aliases only: the operator wanted a real rename. (b) Rename every record label and heading with per-record reading of old records: two-vocabulary readers for `Change Status:` and `## Changes` with no gain in accuracy. (c) "Blueprints" for the durable documents: reads as a plan made before building, and the review lane is already `docs-contract-reviewer`. |
| 2026-11-16 | Rename all five prompts by rule, keeping the earlier phrases as aliases | A partial set gives a lifecycle that reads **Plan spec**, **Add change to wave**. Aliases keep every existing habit and document working. | Plan and close only: inconsistent at the second step. |
| 2026-11-16 | Change the default names and migrate installed repositories through the profile-aware prompt-name migration, with the manifest's registration of the earlier default doc as the authority to move | That migration already preflights the whole plan and handles chains, cycles, colliding applied names, per-key manifest recording and the link report, and it never touches a distribution's recorded names. It already uses manifest registration as rename authority for one earlier fixed prompt. `inferred`: read in `render_agent_surfaces.py`, not executed for these keys; the first task executes it. Efficacy: the migration controls the outcome; the case it must not get wrong is a distribution that reuses an earlier default slug, which Requirement 4 and AC-5 replay. | (a) New rows in the fixed-pair migration: the red-team primer showed it moves whatever file exists without reading the profile, so it would move a distribution's container prompt that reuses `implement-change`, and retiring the old names to prevent that would make such a profile fail at import. (b) Ship the renames as `PROMPT_NAME_OVERRIDES` entries: the shipped "defaults" would no longer be the shipped names. (c) Rename with no migration: installed repositories fail lint on the missing prompt files. |
| 2026-11-16 | One copy of the mapping table, in the root README | External claims go stale; one copy has one check date. | Repeat it in the docs site and framework README. |
| 2026-11-17 | Operator: "spec" is the name people read and "change" stays the name underneath. Tools, record labels, the `change_id` key and receipts keep "change". | A downstream distribution that renamed its tiers left `change_id` alone; the renames were breaking for distributions and made receipts unreadable by earlier versions; a spec and the change it describes are different things, so two names are accurate. A second wave (`23lxe`) that renamed the tools, label, parameter and receipt key was implemented, reviewed, backed out and its folder deleted. | Keep the second wave's renames. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The migration moves or removes a distribution's prompts or skills. `inferred`: no distribution profile was inspected. | Requirement 4, AC-5, and the scratch proof under the `prompt-names` profile and a slug-reuse profile. |
| A migrated installed prompt keeps its authored title and `Shortcut:` line, so an upgraded repository still shows "Plan change" in the file. | Content is never rewritten by the renderer; the seed 160 upgrade instruction tells the upgrading agent to edit them, and the earlier phrase remains a valid alias meanwhile. |
| An installed repository has edited copies at both old and new paths. | The preflight refuses and names the pair; nothing is written. |
| Links to the old prompt paths break in installed repositories. | They are reported on render; the changelog and the seed 160 instruction give the repair. |
| "Spec" in the introductions is read as `docs/specs/`. | The vocabulary statement and AC-7; the sibling change rewords the durable documents as behavior contracts. |
| The mapping table misstates another tool. | Requirement 9: verified against official documentation and dated. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
