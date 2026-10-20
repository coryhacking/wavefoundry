# Make the remaining distribution-blocking tests portable

Change ID: `2134w-enh distribution-test-portability-round-2`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-19
Wave: `2136y distribution-test-portability-round-2`

## Rationale

Waveforge's note against `d91b2e80` lists tests that cannot pass on their tree because of lasting rules in their distribution; their close gate is our runner's green receipt, so each blocks every close. Verified against HEAD (2026-10-19): (X1) `test_render_agent_surfaces.ChangePromptSkillAndContractTests.test_close_change_states_the_implemented_wf_close_change_contract` checks the close-state list "(`ready`, `active`, `review` or `implemented`)" literally in the distribution-owned template and rendered prompt, although our rule lives in code (`wf_server.server_impl._close_change_closable_statuses`); (X2) `test_memory_records.MemoryProposeTests.test_registered_manual_pending_candidate_blocks_close_without_source_event` calls `wf_close_wave` by its public name, which a distribution may replace through `EXTENSION_REPLACEMENTS` while the core handler stays reachable under its `alias_for_core`; (X3) `test_indexer.OperationalEvidencePolicyTests.test_registered_review_read_and_typed_history_retain_evidence` enables the nested layout and creates a wave without a parent; (X4) `test_upgrade_wavefoundry.JournalTriggerPolicyTests.test_registry_base_profiles_positional_validator_and_activation_are_compatible` pins the value `legacy_cutover` on the active declaration, although the validator accepts `journals_present` too; (X6) about 67 `test_docs_lint` tests lint the static fixture `tests/fixtures/docs_lint/base`, which carries default prompt names, so under a renamed profile lint reports a pending prompt-name migration in every result. None fails on our tree, including under `run_tests.py --profile second` and `--profile declared`.

## Product Intent

A distribution that replaces lifecycle tools, requires a parent folder, narrows the close rule, declares a different journal trigger or renames prompts runs these tests green on its tree, while each test still guards the same core behaviour on ours. Boundaries: test-only; no framework behaviour or seam is added. AC-6 tests the intent.

## Requirements

1. X1: the close-state clause stays a literal check on seed 190; for the template and rendered close-change prompt, the test asserts that the set of backticked statuses on the closable-states line (the line carrying the `wf_close_change` closable clause) equals the set returned by `_close_change_closable_statuses()`, instead of the literal list.
2. X2: the test resolves the core `wf_close_wave` handler through `mcp_tool_extensions.replacement_targets()` (the `alias_for_core` name when the tool is replaced, the core name otherwise) and calls it with the arguments the core tool takes.
3. X3: the fixture wave is created with `parent="group"`, the live folder `setUp` already writes, so the test passes when a layout requires a parent and is unchanged otherwise.
4. X4: the test keeps its pin on the shipped test-support declaration and, for the active profile, asserts the trigger is one of the validator's accepted values (`upgrade_extensions._JOURNAL_TRIGGER_POLICIES`), equals the loaded declaration, and passes `journal_declaration_problems`.
5. X6: tests that lint the docs-lint fixture build it under the active profile first: when the profile renames prompts, a copy of the fixture gets its prompt files at the profile's names and a matching manifest `prompt_names` record (the existing migration or `prompt_vocabulary_support.prime_profile_render`), so lint sees a migrated tree. Under the default profile the fixture is used as today.
6. No assertion is removed or loosened without a stated reason in the Progress Log.

## Scope

**Problem statement:** Five tests or test groups fail on a renamed distribution's tree for reasons that are not defects there.

**In scope:**

- The five test sites above and test support code they share.
- One CHANGELOG bullet.

**Out of scope:**

- An expected-failure declaration (Waveforge X5): not needed once these tests are portable.
- `test_wf_cli`'s retired-name check and the shipped README (change `2134x`).
- Framework behaviour.

**Platform behaviour:** tests only; the same on Windows, macOS, Linux and WSL2.

## Acceptance Criteria

- [x] AC-1: X1: under the default profile the converted close-change test passes and fails when a status the code accepts is missing from the template or rendered prompt, or the seed's literal list is altered. Oracle: scratch mutants.
- [x] AC-2: X2: with a fixture extension that replaces `wf_close_wave` (as `test_extension_tool_modules` already models), the memory-gate test still reaches the core gate and passes; under the default profile it is unchanged. Oracle: the test and a scratch replacement.
- [x] AC-3: X3: the evidence-policy test passes, and still fails when the evidence policy under test is broken. Oracle: a scratch mutant.
- [x] AC-4: X4: the journal test passes for an active declaration of `journals_present` and fails for a value the validator rejects. Oracle: patched declarations.
- [x] AC-5: X6: in a scratch Set/Wave copy (the 2134q `setup_setwave.py` tree), `test_docs_lint.py` reports no prompt-name migration error; under the default profile it is unchanged. Oracle: the scratch run.
- [x] AC-6: In the scratch Set/Wave copy, every test named in requirements 1-5 passes, and `run_tests.py --profile second` and `--profile declared` pass for the changed files. This is the intent check.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] X1 close-state clause.
- [x] X2 core-handler resolution.
- [x] X3 parent for the fixture wave.
- [x] X4 trigger contract assertion.
- [x] X6 profile-aware lint fixture.
- [x] Run the scratch Set/Wave and both profile runs; record them.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| tests | implementer | none | five sites |
| qualification | qa-reviewer | tests | AC-6 |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: test-only.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required | Unblocks their close gate. |
| AC-2 | required | Same. |
| AC-3 | required | Same. |
| AC-4 | required | Same. |
| AC-5 | required | Largest group of failures. |
| AC-6 | required | The distribution outcome. |
| AC-7 | required | Standard verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned. | Waveforge note against `d91b2e80` (X1-X4, X6); readiness investigation reports for each site. |
| 2026-10-19 | Readiness red-team primer: no blocker. Repaired before any approval: X1 asserts set equality (not a superset), anchored on the line carrying the `wf_close_change` closable clause. Implementation notes: X2 must keep the `run_validate` patch target valid when a replacement wraps the core; AC-5 must check that migrating the three-prompt docs-lint fixture records `prompt_names` for all 11 keys (or lint still reports pending for absent ones); AC-3's mutant breaks the retention policy, not parent handling. | Red-team primer report; receipt `review-policy-bc31f918b84ed94d13c6` superseded. |
| 2026-10-19 | Implemented. X1 (`test_render_agent_surfaces`): the seed keeps the literal closable list; template and rendered prompt now assert set equality between the backticked statuses inside the `closable (...)` parenthetical (list item selected by `closable (`, hard-wrapped lines joined first) and `_close_change_closable_statuses()`. X2 (`test_memory_records`): `wf_close_wave` resolves through `mcp_tool_extensions.replacement_targets()` to its `alias_for_core` when replaced; the `run_validate` patch is unchanged. X3 (`test_indexer`): `parent="group"`. X4 (`test_upgrade_wavefoundry`): the `SHIPPED_DECLARATION` pin stays; the per-profile check that every run-mode profile declares `legacy_cutover` is replaced by membership in `_JOURNAL_TRIGGER_POLICIES` plus `journal_declaration_problems(...) == []`, and the active profile's trigger must also equal the loaded declaration. Reason for that narrowing: a distribution may legitimately declare `journals_present`, which the validator accepts. X6 (`tests/record_layout_support.py`): `localized_docs_lint_fixture` ends with `render_agent_surfaces.migrate_profile_prompt_names(dest)` (no-op under the default profile); `test_activated_wave_requires_sibling_change_docs` now looks for `vocabulary_profile.shortcut("prepare-wave")` instead of the literal phrase. CHANGELOG bullet under Fixed. Default-profile focused runs: test_render_agent_surfaces 171 OK, test_memory_records 234 OK, test_indexer 414 OK, test_upgrade_wavefoundry 736 OK, test_docs_lint 350 OK, test_install_resume_integration 2, test_profile_support 82, test_vocabulary_second_profile 11, test_record_document_read_rule 12, test_change_kinds 28, test_wf_cli 54, all OK. `--profile second` and `--profile declared` over those 11 files: 2094 tests OK each; test_docs_lint re-run under both after the last edit: OK. Known-bad probes (default scratch copy, all as expected): AC-1 killed by template or rendered prompt dropping `review`, template adding `planned`, seed 190 list altered, code closing an extra status; passes with the list hard-wrapped mid-parenthetical and with a reworded reordered list, which the pre-fix test fails. AC-2: with a fixture `fork_tools` replacing `wf_close_wave` (alias `fork_close_container`) the fixed test passes and the pre-fix test fails. AC-3: `is_operational_evidence_path` forced to False fails the test at the evidence-excluded search assertion. AC-4: patched active declaration `journals_present` passes, `on_upgrade` fails, pre-fix test fails for `journals_present`. Set/Wave scratch copies (2134q `setup_setwave.py`, full layout and `SETWAVE_NO_LAYOUT=1`): the X1-X4 tests pass; test_docs_lint drops from 67 failures to 5 with no prompt-name migration error. Remaining 5 are outside X6: four read this repository's own rendered prompts at default names (`AdvisoryFirstRulePinTests`, `CouncilSeedVerificationContractTests`, two `ReviewCycleChurnControlPinTests`), and `test_change_prompt_migration_keeps_lint_green_once_reported_link_is_fixed` exercises the legacy `plan-feature` to `plan-change` migration by default names. AC-6 left open for that one fixture test. | Scratch logs under `/private/tmp/claude-502/-Users-coryhacking-Developer-wavefoundry/64d2b992-b50d-423e-985d-22b0c59dd1ac/scratchpad/2134w` (`mutants.log`, `sw-*-run.log`, `sw-*-dl.log`, `profile-*.log`). |
| 2026-10-19 | AC-6 follow-up. `test_change_prompt_migration_keeps_lint_green_once_reported_link_is_fixed` now builds from the unmigrated fixture (`localized_docs_lint_fixture(..., migrate_prompts=False)`, new keyword defaulting to True; `copy_fixture` passes it through), matching its pre-rename premise; every `migrate_change_prompt_renames` assertion is kept. Before the final lint it runs `migrate_profile_prompt_names(root)` (no-op under the default profile) and fixes the reported link to `vocabulary_profile.prompt_doc("plan-change")`'s file name. Known-bad: pointing the link at `plan-change.prompt.md` in the Set/Wave copy fails with a broken-link error. test_docs_lint: default 350 OK, `--profile second` and `--profile declared` OK; other fixture users (test_profile_support 82, test_change_kinds 28, test_vocabulary_second_profile 11, test_record_document_read_rule 12, test_install_resume_integration 2) OK. Both Set/Wave copies: test_docs_lint 4 failures, none in requirements 1-5. The remaining four (`AdvisoryFirstRulePinTests.test_prompt_surfaces_and_contributing_docs_are_reconciled`, `CouncilSeedVerificationContractTests.test_ac_locality_rule_pinned_in_seed_170_and_reconciled_prompt`, `ReviewCycleChurnControlPinTests.test_review_entry_phase_receipt_trigger_and_reprepare_contract`, `ReviewCycleChurnControlPinTests.test_prompt_surfaces_and_role_docs_are_reconciled`) read this repository's own rendered prompts, not the docs-lint fixture; no requirement names them, so they are outside AC-6. | Scratch logs `sw-*-dl.log`, `dl-*.log` in the 2134w scratch folder. |
| 2026-10-19 | Gapfill: the implementer read and edited the eight test files with shell and file tools rather than the code_* MCP tools. The work was mechanical edits at known test sites and fixtures named in the plan, plus scratch-copy mutant runs, which are shell work. | Implementer report. |
| 2026-10-19 | Delivery repair CODE-DEL-1 (code-reviewer): `localized_docs_lint_fixture` migrated prompt names to the loaded profile even for callers passing an explicit `vocabulary`, so `test_vocabulary_second_profile` failed under a prompt-renaming profile (Set/Wave copy and `--profile prompt-names`). The migration now runs only when `vocabulary is None`. test_vocabulary_second_profile, test_docs_lint, test_profile_support, test_change_kinds and test_install_resume_integration: 473 OK on default; 0 of 5 files failed under `--profile prompt-names`, `second` and `declared`. | Logs under `/private/tmp/claude-502/-Users-coryhacking-Developer-wavefoundry/64d2b992-b50d-423e-985d-22b0c59dd1ac/scratchpad/2136y-repair`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Fix each test against the contract it guards; no expected-failure mechanism. | Waveforge prefers fixed tests; every named test has a portable form. | A distribution expected-failure list (X5): a new authority path for tests that can be fixed. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A converted assertion becomes vacuous. | Each AC names a mutant that must still fail. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
