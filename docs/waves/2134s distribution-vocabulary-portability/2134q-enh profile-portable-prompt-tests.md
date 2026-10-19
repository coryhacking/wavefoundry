# Make lifecycle prompt tests hold on any declared vocabulary

Change ID: `2134q-enh profile-portable-prompt-tests`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-19
Wave: `2134s distribution-vocabulary-portability`

## Rationale

Waveforge renames our tiers (our wave is their Set, our change is their wave) and edits the lifecycle prompt template bodies in their own copies. Our suite then fails on their tree: tests pin our default prompt paths (`docs/prompts/close-change.prompt.md`), our default shortcut phrases ("Close change"), and our template wording in a repository's rendered prompts (for example `ChangePromptSkillAndContractTests.test_close_change_states_the_implemented_wf_close_change_contract` requires "admitted to that wave" and "only wave close"). A read-only census (2026-10-19) found about 143 test lines using literal mapped prompt paths, 85 using literal shortcut phrases, and 17 lines in 7 files reading template files directly.

The operator's decision (2026-10-19): Waveforge may edit template bodies themselves; we do not render template prose or seeds through the profile. What they need is tests that guard their surfaces without our wording.

## Product Intent

A distribution that declares its own prompt names and edits its lifecycle prompt bodies runs our suite green on its tree, and the tests still catch a missing or broken contract on its surfaces. Boundaries: Wavefoundry's own coverage does not weaken, seed tests stay literal (seeds remain canonical shared source), and no test is skipped merely because a profile is renamed. AC-2 tests the intent.

## Requirements

1. The set to change is derived by this rule: a test assertion in `.wavefoundry/framework/scripts/tests/` whose expected value is a default prompt path or slug, a default shortcut or alias phrase, or literal prose from a lifecycle prompt template, and which is checked against the active profile's rendered or derived surfaces. Implementation records the census (files and counts) in the Progress Log. Tests that patch a profile and assert that profile's own declared names, and tests of the default name table itself, are outside the rule.
2. Path and phrase assertions in the set derive their expected values through `vocabulary_profile` (`prompt_doc`, `agent_prompt_doc`, `prompt_slug`, `skill_name`, `shortcut`, `shortcut_aliases`, `shortcut_line`).
3. Wording assertions in the set check clause presence, not whole-template containment (on this repository the rendered prompts are authored, and five of the six templated keys differ from their template). Each contract clause a test names is asserted in the template and in the rendered prompt either as noun-free text (for example "cannot be reopened", `dry_run`) or with its tier nouns built through the `2134r` helpers, compared case-insensitively. Prompt keys with no shipped template (plan-change, add-change, remove-change, implement-change, pause-wave) are outside this requirement; their path and phrase assertions still follow requirement 2.
4. Assertions on seed text keep their literal phrases.
5. No assertion is removed or loosened without a stated reason in the Progress Log; a test whose protection cannot be expressed portably is listed there with its reason.

## Scope

**Problem statement:** Tests pin default vocabulary and template wording, so they fail on renamed distributions.

**In scope:** test files under `.wavefoundry/framework/scripts/tests/` covered by requirement 1, a renamed-profile qualification check (AC-2), and one CHANGELOG bullet.

**Out of scope:** rendering template prose or seeds through the profile, migrating already-rendered prompt text, skill descriptions (change `2134r`, whose tier-noun helpers this change uses), and prompt lookup (change `2134p`).

**Platform behaviour:** tests only; they run the same on Windows, macOS, Linux and WSL2. Expected paths come from the profile helpers, which return forward-slash repository-relative strings the tests already compare.

## Acceptance Criteria

- [x] AC-1: Under the default profile, the changed tests pass and each still fails on a known-bad variant of the surface it guards (for example a template or rendered prompt missing a named contract clause, or a prompt file at the wrong path). Oracle: scratch-copy mutants recorded in the Progress Log.
- [x] AC-2: In a scratch copy configured as a Set/Wave distribution (renamed `PROMPT_NAME_OVERRIDES` and tier names, migrated prompt files, and template and rendered prompt bodies edited to the distribution's own wording, carrying the contract clauses in its own nouns), the test files changed by this change pass. Oracle: the qualification run, its setup script and its result recorded in the Progress Log.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Run the requirement 1 census and record it.
- [x] Convert path and phrase assertions to the profile helpers.
- [x] Convert wording assertions to template comparisons.
- [x] Build the Set/Wave scratch qualification and run it (AC-2).
- [x] Run the AC-1 mutants.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | none | requirement 1 |
| conversion | implementer | census | test files |
| qualification | qa-reviewer | conversion | AC-2 scratch distribution |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: one sentence that lifecycle prompt tests derive names through the vocabulary profile and compare wording against the shipped templates, if the doc describes distribution test portability (wave 1zv88 / 200ex); otherwise N/A.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Portability must not cost coverage. |
| AC-2 | required  | The distribution outcome. |
| AC-3 | required  | Standard change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned from the Waveforge request (ask C) and the operator's decision that distributions edit their own template bodies. | Census estimate: about 143 literal prompt-path lines, 85 literal shortcut lines, 17 template reads in 7 files. |
| 2026-10-19 | Readiness red-team primer, blocker: requirement 3's template containment fails under the default profile here (rendered prompts are authored; five of six templated keys differ), and literal tier nouns in clauses fail under Set/Wave. Repaired before any approval: requirement 3 is clause presence with noun-free text or `2134r` helper-built nouns; keys without templates are outside it; `2134r` is now a dependency. Note for AC-2: the framework-owned templates in `install/lifecycle-prompts/` are what a distribution edits in its own tree. | Red-team primer report; receipt `review-policy-7c7c28e99e841ca1cae2` superseded. |
| 2026-10-19 | Implemented (implementer subagent; coordinator reviewed). Census: candidate grep found mapped prompt paths in 21 test files, shortcut phrases in 8, template reads in 12; the authoritative census was the Set/Wave scratch run of 25 candidate files (about 110 failures), of which 13 files hold Requirement 1 assertions, all converted: test_render_agent_surfaces (+151/-85), test_setup_wavefoundry (+16/-14), test_reconcile_scan (+16/-12), test_review_policy (+15/-10), test_declared_extension_skills (+13/-6), test_compact_review_artifacts (+12/-2), test_memory_records (+11/-4), test_render_platform_surfaces (+10/-2), test_install_resume_integration (+6/-2), test_upgrade_wavefoundry (+5/-1), test_readiness_convergence (+2/-2), test_server_context_efficiency (+2/-2), test_server_tools_lifecycle (one test); new support module `tests/prompt_vocabulary_support.py`. Wording clauses use `{wave}`/`{change}`/`{doc[key]}`/`{shortcut[key]}` placeholders: seeds compared exactly with shipped nouns, templates and rendered prompts case-insensitively with `tier_noun` nouns. Narrowed under renamed profiles only, with inline reasons (Requirement 5): seed-to-template body byte equality in `BriefingLoopCarrierTests`, and containment of the implement-wave Completion section in this repository's rendered prompt; both still apply under shipped names and the clause checks run on every profile. Left literal: seed text, template asset file names, the untiered review-plan prompt, `DefaultNamePinTests`, `ProfileConsumerTests`, and no-record manifest fixtures. Outside Requirement 1 and not changed: test_docs_lint (about 60 failures on the Set/Wave tree, because the static `DOCS_LINT_FIXTURE` carries shipped prompt names and lint asks for migration) and test_wf_cli (a census of this repository's own live docs); a distribution suite run still sees those, recorded as a follow-up. AC-1: 13 scratch mutants (missing template or rendered clause, prompt at the wrong path) killed on both the default and the Set/Wave tree, unmutated controls pass (`scratchpad/2134q/mutants.py`). AC-2: `scratchpad/2134q/setup_setwave.py` (Set/Wave tier names, all 11 prompt overrides, migrated prompts, reworded templates and rendered prompts, marker regions untouched, a re-render writes nothing): the 13 changed files ran 2387 tests OK, 8 skips (4 shared with the default run, 4 existing `default_profile_only`). Existing gap noted, not changed: `LifecyclePromptTextTests._text` skips rather than fails when the file is missing. | Repository: `run_tests.py --file` over the 13 files, 2388 tests OK (4 skipped). |
| 2026-10-19 | Delivery repair. The coordinator ran the wave's 14 test files under `run_tests.py --profile second` (tier names Set/Wave, shipped templates and prompt names): 17 failures in test_render_agent_surfaces, because clauses were built only with profile nouns while that profile keeps the shipped wording; at HEAD those tests passed under `second`, so the wave would have broken the repository's own second-profile run. Repaired: `prompt_vocabulary_support.has_clause` accepts a non-seed clause in the profile's nouns and names or in the shipped ones (case-insensitive; seeds stay exact); the clause-deletion and fresh-review known-bad controls mutate whichever form the file carries; `test_self_hosted_review_plan_skills_match_registry_bytes` is `@default_profile_only` (it compares this repository's own rendered skill files). Accepted limitation (QA): on a reworded tree, a clause written in the shipped nouns where the distribution means the other tier (for example "admitted to that wave" in its item-close prompt) passes; a missing clause still fails in both vocabularies, and HEAD had no coverage on renamed trees. | `--profile second` over the 14 files: 0 of 14 failed; fresh Set/Wave rebuild (`scratchpad/2134q/setwave3`): 2394 tests OK; QA re-ran the 13 mutants on both trees, all killed (`2134s-del-qa-reviewer-2`). |
| 2026-10-19 | Whole framework suite (last, both waves 2134o and 2134s in the tree): `Ran 11945 tests across 201 files in 722.422s OK` (12 skipped); green receipt. | `python3 .wavefoundry/framework/scripts/run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Derive names through the profile and compare wording against the shipped template. | Holds on any vocabulary and keeps guarding distribution surfaces. | Skip wording tests on non-default profiles: drops coverage for distributions (rejected by wave 200ex's principle). Render template prose through the profile: not needed for portability; operator declined. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A template comparison becomes vacuous (the rendered prompt is the template, so the test proves nothing). | AC-1 requires each converted test to fail on a known-bad surface; the test still names the contract sentences it requires in the template. |
| The census misses a pinning test. | AC-2 runs the changed files on a renamed profile; any remaining failure in them is in scope. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
