# Derive planning prompt names from each key's role

Change ID: `23z8y-bug role-derived-planning-names`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-20
Wave: 23z45

## Rationale

A distribution that vendors the framework through a rename map (`change` to `wave`, `wave` to `set`) reported against v1.46.0 that it still has to pin all five planning prompt names. Wave 23td0 promised that a custom profile gets usable default names from its nouns. That holds only while the earlier default slugs keep upstream's words.

`vocabulary_profile._custom_planning_defaults` names each unregistered planning key by splitting its `EARLIER_DEFAULT_PROMPT_SLUGS` value and replacing the word `change` with the planning noun and the word `wave` with the container noun. The rename map rewrites those slug values to `plan-wave`, `implement-wave`, `close-wave`, `add-wave-to-set` and `remove-wave-from-set`. The word replacement then reads the item word as the container word. `validate()` runs at import with no manifest, so every key takes this path before any render can read a registration.

Reproduced by execution on 2026-11-20 against a scratch copy of the HEAD module (profile Set and Wave, container prompts renamed to `*-set`, earlier slug values rewritten by the map):

| Planning pins | Result at HEAD |
| --- | --- |
| none | import raises `VocabularyProfileInvalid`: slug `implement-set` is used by `implement-wave` and `implement-change`, and the same for `close-set` |
| `implement-change` and `close-change` only | import succeeds; `derive_prompt_names(manifest={})` gives `plan-set` ("Plan set"), `add-set-to-set` and `remove-set-from-set` |
| none, earlier slug values left as upstream ships them | import succeeds with `plan-wave-doc`, `implement-wave-doc`, `close-wave-doc`, `add-wave-doc-to-set`, `remove-wave-doc-from-set` |

Both reported symptoms match. The third row shows the defect lives only in the dependence on the earlier slug's words.

The exact shape of the reporter's vendored tree is `inferred` from the report: which literals their map rewrites and which it leaves alone was not available to inspect. The reproduction models the one shape that yields both reported symptoms.

## Product Intent

A distribution maintainer whose rename also changes the words in upstream's file names can import the framework and install into an empty repository with no planning-name pins. Before, the import fails or a fresh install offers "Plan set" for the planning prompt. After, each of the five planning prompts gets a name built from its role and the profile's nouns, the same names a distribution that keeps upstream's file names already gets. AC-1 and AC-6 together establish the outcome (names derive correctly, and a fresh install records the role-derived names and routes each shortcut to its own key's prompt path and to no container prompt); the bodies of the plan, implement, add and remove prompts are authored by seed 100, not by the renderer, and are outside this change. AC-2 shows existing distributions and the shipped profile see no change. Registered names, explicit overrides and the migration of earlier default files keep their current behaviour.

## Requirements

1. For a custom planning vocabulary, the default name of each planning key that has neither a manifest registration nor a recorded slug is derived from that key's role and the profile's nouns. The roles are: item alone (plan, implement, close) and item in container (add to, remove from). The planning noun is `planning_noun()` and the container noun is `tier_noun("container")`, as today.
2. The derivation reads no word of any slug: not the `EARLIER_DEFAULT_PROMPT_SLUGS` values, not `DEFAULT_PROMPT_NAMES` slugs. The set of keys it covers is the key set of `EARLIER_DEFAULT_PROMPT_SLUGS`; a key in that set without a declared role is a defect a test reports by name.
3. The declared role phrases contain no tier word. A source rewrite that maps the shipped item or container word to another word leaves every phrase unchanged. A test enforces this against the shipped tier names and the planning noun.
4. For every profile whose `EARLIER_DEFAULT_PROMPT_SLUGS` values are the shipped ones, the derived slug, shortcut and aliases of all five keys equal what HEAD derives. No registered name moves and no shipped-profile name changes.
5. `EARLIER_DEFAULT_PROMPT_SLUGS` keeps its one remaining job: naming the earlier doc whose manifest registration authorises a move (`applied_prompt_slugs` and the renderer). Registration precedence, explicit override precedence, collision and cycle validation stay as they are. A genuine collision between a role-derived name and a distribution's own override is still refused at import.
6. Behaviour is the same on Windows, macOS, Linux and WSL2: the change is string derivation in a stdlib-only module with no path, permission or process dependence.

## Scope

**Problem statement:** default planning names are derived from the words of the earlier slugs, so a distribution whose rename rewrites those words gets colliding or wrong names and must pin all five keys.

**In scope:**

- The unregistered-key branch of `_custom_planning_defaults` in `vocabulary_profile.py` and a role declaration beside the prompt-name tables.
- Tests: a renamed-vocabulary known-bad fixture, an equivalence check for unrenamed profiles, and the two guards in Requirements 2 and 3.
- One sentence in the vocabulary profile paragraph of `docs/architecture/layering-rules.md` and one Unreleased changelog entry.

**Out of scope:**

- A distribution-declared word mapping for earlier slugs (rejected, see Decision Log).
- Changing what the planning noun is, or shortening derived names such as `plan-wave-doc`. A distribution that wants `plan-wave` keeps an explicit override.
- The move authority in `applied_prompt_slugs` when a rename map rewrites earlier slug values. A renamed earlier value can name a doc the distribution uses for another key; the existing guard that skips an earlier slug applied to another key covers the pinned case, and the unpinned case is not part of this report. By operator decision it is a follow-up to raise with the reporter, planned only if confirmed or reproduced. Status: `unverified`, recorded in Risks.
- Seeds, rendered prompt surfaces, MCP tool identifiers and the other mapped prompts.

## Acceptance Criteria

- [x] AC-1: Known-bad renamed vocabulary. A fixture scripts tree with item Wave, container Set, the container prompts renamed to their Set names, the earlier slug values rewritten by a `change` to `wave`, `wave` to `set` map, and no planning-key override imports cleanly in a fresh interpreter. Its `derive_prompt_names(manifest={})` gives the five planning keys the role-correct names: item-only keys carry the planning noun and no container noun, and the two item-in-container keys carry the planning noun then the container noun. Every mapped prompt slug and shortcut is distinct. The same fixture against the HEAD derivation fails at import with `VocabularyProfileInvalid` naming `implement-set` and `close-set`, so a no-op cannot satisfy this criterion.
- [x] AC-2: Unrenamed profiles are unchanged. For the shipped profile, a custom item and container profile (Ticket and Batch) and the Set and Wave profile with shipped earlier slug values, the five derived names equal a literal table recorded from HEAD before the change. The existing fresh-install and registered-name render tests pass unmodified under the default profile and the `second` profile.
- [x] AC-3: The role declaration covers exactly the `EARLIER_DEFAULT_PROMPT_SLUGS` key set, and no declared phrase contains the shipped item name, the shipped container name or the shipped planning noun as a word. Each check fails when a key is dropped or a tier word is put into a phrase.
- [x] AC-4: In the AC-1 fixture, pinning only `implement-change` and `close-change` leaves the other three keys at their role-derived names, with no container noun in the plan key. At HEAD the same arrangement yields `plan-set`.
- [x] AC-5: The layering-rules paragraph states that fresh default names come from each key's role and the profile's nouns and do not depend on the earlier slugs, and the Unreleased changelog entry says a distribution that renames upstream's file words needs no planning-name pins. The documents this change edits validate.
- [x] AC-6: Fresh install on the renamed fixture, limited to what the vocabulary profile and the renderer own. The AC-1 scripts tree, with all five planning names unpinned, is driven against an empty target repository (no prompt-surface manifest and no planning prompt registered) in the sequence the existing `FreshProfiledInstallTests` uses: render, `ensure_manifest`, render, then one more render that writes nothing. Afterwards all of these hold:
  1. The manifest's `prompt_names` records the five role-derived slugs.
  2. Each of the five planning shortcuts routes to its own key's role-derived prompt path, and none routes to a container prompt path.
  3. The close key's prompt doc exists with a non-empty body. No body is asserted for the plan, implement, add and remove prompts, which the renderer does not write.
  4. The rendered `wf-` skills for the plan and close keys point at their own key's prompt doc.
  5. Known-bad: at HEAD the same fixture cannot reach the sequence, because the scripts tree fails at import; with the two colliding keys pinned, the plan shortcut is "Plan set" and routes with the container noun. This criterion closes the gap where AC-1 and AC-2 pass while the distribution installs a shortcut that reaches the wrong prompt.

## Tasks

- [x] Record the HEAD-derived names for the three unrenamed profiles as the AC-2 literal table before editing the module.
- [x] Add the role declaration and replace the word-replacement branch in `_custom_planning_defaults`; update the function docstring and the `EARLIER_DEFAULT_PROMPT_SLUGS` comment to state its single remaining job.
- [x] Add the renamed-vocabulary fixture and the AC-1, AC-3 and AC-4 tests; confirm AC-1 and AC-4 fail against the unmodified branch in a scratch tree, not the working tree.
- [x] Add the AC-6 fresh-install test: drive the renamed fixture against an empty target with the existing test driver (`build_fresh_target`, then the `render`, `ensure_manifest`, `render`, `render` and `route` actions in `test_vocabulary_prompt_names.py`) and check the recorded `prompt_names`, shortcut routing for the five planning keys, the close doc body, and the plan and close `wf-` skills.
- [x] Run `test_vocabulary_prompt_names.py`, `test_server_tools_lifecycle.py` and `test_profile_support.py` under the default profile and `--profile second`.
- [x] Update `docs/architecture/layering-rules.md` and add the Unreleased changelog entry.
- [x] Run the framework suite last and validate docs.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| derivation | implementer | Readiness | Module edit and role declaration |
| tests | implementer | derivation | Known-bad fixture built in a scratch scripts tree |
| docs | implementer | derivation | Layering rules sentence and changelog entry |
| verify | qa-reviewer | tests | Default and second profile runs, known-bad replay |

## Serialization Points

- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/tests/test_vocabulary_prompt_names.py`
- `docs/architecture/layering-rules.md`
- The root changelog gains one entry.

## Affected Architecture Docs

`docs/architecture/layering-rules.md` (vocabulary profile paragraph): one sentence on role-based derivation. No boundary, flow or verification seam changes; the other architecture docs need no update.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reported failure; proves intent with a known-bad |
| AC-2 | required | Existing distributions and the shipped profile must not see a name change |
| AC-3 | required | Keeps the derivation immune to the rewrite that caused the defect |
| AC-4 | important | The second reported symptom, a wrong name under partial pins |
| AC-5 | important | The documented contract matches the behaviour |
| AC-6 | required | Proves the installed names are recorded and the shortcuts and skills route to their own key's prompt path, which import-level checks cannot |

## Progress Log

2026-11-21: The full framework suite passed on the reviewed changes. It ran 13,123 tests across 251 files in 741 seconds with 12 skips.

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-20 | Reproduced both reported symptoms and prototyped the selected approach in a scratch copy of the HEAD module; no repository code edited. | Import failure naming `implement-set` and `close-set`; `plan-set` under two pins; prototype imports with `plan-wave-doc` and `add-wave-doc-to-set`, and matches HEAD for Ticket and Batch |
| 2026-11-20 | Operator decisions recorded: derived names keep the documented `plan-wave-doc` form; the `applied_prompt_slugs` move-authority question stays out of scope as a follow-up to raise with the reporter. | Decision Log rows dated 2026-11-20 |
| 2026-11-20 | Plan review finding accepted: added AC-6 and a task for a fresh-install render of the renamed fixture with shortcut, manifest and skill routing checks. The render path was confirmed to exist by reading the test module; the AC-6 render on the renamed fixture itself is `unverified` (not executed at plan time). | `build_fresh_target` and the driver `render` and `route` actions in `test_vocabulary_prompt_names.py`; `test_custom_unregistered_names_derive_from_nouns_and_explicit_override` uses the same route check |
| 2026-11-20 | Readiness repair pass 1. Finding `R1-23z8y-ac6-unsatisfiable`: AC-6 narrowed to render, `ensure_manifest`, render and a no-write render with renderer-owned assertions; the non-empty body requirement for the plan, implement, add and remove prompts is removed; Product Intent, the AC-6 task and its priority rationale follow. Note folded in: the root changelog added to Serialization Points. | `.wavefoundry/work/23z45/review/qa-reviewer.md` (qa-F1), `code-reviewer.md` (code-reviewer-F1), `architecture-reviewer.md` (architecture-reviewer-F1, N5); `LIFECYCLE_PROMPT_BASELINES` read at `render_agent_surfaces.py` line 331 |
| 2026-11-20 | Readback: (implementer) intended behaviour: under a custom planning vocabulary, each planning key with no registration and no recorded slug takes its name from a declared role phrase (item alone, or item in container) filled with `planning_noun()` and `tier_noun("container")`; no slug word is read. ACs 1 to 6 in scope. Boundary: only the unregistered branch of `_custom_planning_defaults`, a role table beside the prompt-name tables, tests, one layering-rules sentence and one changelog entry; registration, override precedence, validation and `applied_prompt_slugs` stay as they are. Files: `vocabulary_profile.py`, `test_vocabulary_prompt_names.py`, `docs/architecture/layering-rules.md`, `CHANGELOG.md`. Example (item Wave, container Set, earlier slug values rewritten by the map, no pins): before, import raises `VocabularyProfileInvalid` naming `implement-set` and `close-set`; after, import succeeds with `plan-wave-doc`, `implement-wave-doc`, `close-wave-doc`, `add-wave-doc-to-set`, `remove-wave-doc-from-set`. | HEAD table for the three unrenamed profiles recorded by execution before the first edit (shipped: the spec names; Ticket and Batch: `plan-ticket-doc` form; Set and Wave: `plan-wave-doc` form) |

| 2026-11-20 | Implemented. `PLANNING_PROMPT_ROLES` added beside the prompt-name tables; the unregistered branch of `_custom_planning_defaults` fills the key's role phrase with `planning_noun()` and `tier_noun("container")` and no longer reads the earlier slug. New tests: `RoleDerivedPlanningNameTests` (AC-1 to AC-4 and Requirement 2) and `FreshRenamedInstallTests` (AC-6, unpinned and two-pin installs). The plan, implement, add and remove docs are not asserted to exist (the renderer does not write them); the close doc body and the plan and close skills are. | Working tree: 7 new tests pass; `test_vocabulary_prompt_names` 60 ok, `test_server_tools_lifecycle` 712 ok (2 skipped), `test_profile_support` 82 ok under the default profile; `run_tests.py --profile second --file` on the same three files: 846 tests, 0 of 3 files failed. Logs in `.wavefoundry/work/23z45/23z8y/` |
| 2026-11-20 | Known-bad and landing evidence, run in a scratch copy of the scripts tree (not the working tree). HEAD module: 6 of the 7 new tests fail; AC-1 and the unpinned AC-6 install fail at import with `VocabularyProfileInvalid` naming `implement-set` and `close-set`; AC-4 gives `plan-set`; the two-pin install routes "Plan wave doc" nowhere; the AC-2 equivalence test passes at HEAD, as intended. Mutants on the fixed module: a dropped role key fails `test_the_role_table_covers_the_planning_keys_and_holds_no_tier_word` (and the derivation tests with `KeyError`); a tier word in a phrase (`add {item} to wave`) fails the same test plus AC-1, AC-2 and AC-6; an item-in-container role without its container fails AC-1, AC-2, AC-4 and AC-6. Control (current module) passes. | `.wavefoundry/work/23z45/23z8y/new-tests-known-bad-head.log`; mutant runs executed 2026-11-20 |
| 2026-11-20 | Platforms: the change is string formatting in a stdlib-only module, with no path, permission or process dependence, so Windows, macOS, Linux and WSL2 behave the same. Executed on macOS only; the other three are `inferred` from the code. Observation: a role table missing a key raises `KeyError` at import under a custom vocabulary rather than `VocabularyProfileInvalid`; the key-set test reports it by name first. The final task (framework suite last) is left to the coordinator; docs validate clean. | `wf_validate_docs` passed |
| 2026-11-20 | Full-suite repair: promoted the lifecycle prompt names paragraph to its own subsection. The prose-coordinate census on the changed architecture document returned five wrong source ranges before the edit and zero after it. The chunker and its acceptance test are unchanged. | Repository prose-coordinate census and direct replay on the same document |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-20 | Derive each unregistered planning name from a declared role phrase per key (item, or item in container) filled with the profile's nouns. | It removes the dependence on slug words, which is the cause. It needs nothing from the distribution and adds no new constant for one to maintain. | Declared word mapping for earlier slugs: the distribution must declare and keep it in step with its rename map, so it replaces five pins with another pin and a wrong mapping fails the same way. Skip import-time validation of derived names and validate only with a manifest: hides real collisions until render and still yields "Plan set" on a fresh install. |
| 2026-11-20 | Mechanism efficacy. Replay: the prototype run on the reproduction fixture imports with no pins and gives `plan-wave-doc`, `implement-wave-doc`, `close-wave-doc`, `add-wave-doc-to-set`, `remove-wave-doc-from-set`; under two pins the plan key is `plan-wave-doc`. Control: the derivation decides the names directly, it is not advice. Misses: a rewrite that changes the role phrases themselves, which AC-3 guards for the shipped tier words but cannot guard for an arbitrary map; a map that rewrites dictionary keys inconsistently between tables, which the key-set check reports. Existing mechanism: none gives this; pins are the workaround being removed. Measure after release: the reporter removes the five pins and imports. | Executed in a scratch copy, see Progress Log. | Not applicable |
| 2026-11-20 | Keep the derived names identical to HEAD for unrenamed profiles, including the planning noun form (`wave-doc`). | Changing derived names would move fresh-install names for every custom distribution and is not part of the report. Prototype output equals HEAD for the shipped earlier slugs under Set and Wave and under Ticket and Batch. | Shorter names from the bare item noun: collides with container prompts for a Set and Wave distribution (`implement-wave`) whenever the container prompts keep upstream's slugs. |
| 2026-11-20 | Operator decision: derived names stay in the documented `plan-wave-doc` form; a distribution that wants `plan-wave` uses an explicit override. | Keeps fresh-install names stable for every custom distribution and avoids the container collision. | Shorter bare-noun names. |
| 2026-11-20 | Operator decision: the `applied_prompt_slugs` move-authority risk stays out of scope. Raise it with the reporter as a follow-up and plan a change only if it is confirmed or reproduced. | Not part of this report and not executed (`unverified`). | Fold it into this change. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The reporter's vendored tree differs from the modelled fixture (`inferred`), so the fix passes here and still fails there. | The fix removes every read of slug words from derivation, so no rewrite of slug values can reach it; ask the reporter to confirm by removing the pins on the release candidate. |
| A rename map rewrites a word inside a role phrase. | Phrases use verbs, prepositions and role placeholders only; AC-3 fails on a tier word. |
| A renamed earlier slug value names a doc the distribution uses for another key, and an unpinned checkout treats its registration as move authority (`unverified`, not executed). | Out of scope here; the existing other-key guard in `applied_prompt_slugs` covers the case where that key is applied at the slug. By operator decision, raise it with the reporter as a follow-up and plan a change only if it is confirmed or reproduced. |
| A derived name changes for an existing custom distribution. | AC-2 pins the HEAD table for three profiles and reruns the existing render tests under two profiles. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
