# Rebrand-Stable Names in the Profile Shortcut Tests

Change ID: `21cw3-task rebrand-stable-profile-shortcut-test-names`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-21
Wave: 21cw4 windows-pack-setup-root-and-record-hardening

## Rationale

A downstream distribution builds by a source rebrand that rewrites upstream names in every file, tests included (their Y5). `ProfileShortcutLookupTests._swap_profile` (`.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py:514`) simulates a renamed profile with the literals `close-wave` / "Close wave" and `close-set` / "Close set". The rebrand rewrites those onto the distribution's real names, they collide, and four tests fail. The collision with a default phrase is deliberate: it proves a renamed phrase that equals another key's default resolves to the profile's own prompt.

## Product Intent

A source-rebranded distribution can run these tests unchanged, and the tests keep proving the collision case. Before: four tests fail after a rebrand. After: the colliding name is read from the default table at runtime and the second name is one no profile uses. Boundaries: test-only; no production code changes. AC-1 tests whether the intent was established.

## Requirements

1. The colliding slug, shortcut and alias in `_swap_profile`, and the literals the tests compare against, are derived at runtime from `DEFAULT_PROMPT_NAMES` rather than written as literals, so a text rebrand that rewrites the default table carries them along.
2. The second simulated rename uses names no shipped or known distribution profile uses (`close-unit` / "Close unit").
3. Every assertion keeps its current meaning, including the old-default-phrase negative check, in every test that uses `_swap_profile`.

## Scope

**Problem statement:** literal names in a test collide with a rebranded distribution's real names.

**In scope:**

- `ProfileShortcutLookupTests` fixtures and assertions.

**Out of scope:**

- Other tests that pin default names on purpose (`DefaultNamePinTests`).

## Acceptance Criteria

- [~] AC-1: In a scratch copy of the framework scripts where the reported rebrand is applied as a simultaneous text substitution to `vocabulary_profile.py` and the test module (`close-change` to `close-wave`, `close-wave` to `close-set`, "Close change" to "Close wave", "Close wave" to "Close set", "Prepare wave" to "Prepare set"), `test_renamed_profile_resolves_its_own_phrases`, `test_cache_follows_manifest_changes`, `test_missing_declared_file_falls_through_without_refusal` and `test_refused_declared_file_is_recorded_and_falls_through` pass; the same substitution over the current test module fails them. *Narrowed by evidence 2026-10-21 (coordinator): in the scratch rebrand (all framework .py files, including the prepare-wave slug) the two close-name tests fail before and pass after; the two Prepare-wave tests pass before and after because their failure depends on distribution rewrite rules we do not have. The change removes their literals (phrase and path now come from the profile); the distribution is asked for those tracebacks.*
- [x] AC-2: Under the shipped default table the class passes, and the collision case still exercises a phrase equal to another key's default shortcut.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Derive the colliding names from the default table and use `close-unit` for the second rename.
- [x] Run the class under the shipped table and in the scratch rebrand copy (AC-1), before and after.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes      |
| ---------- | ----------- | ---------- | ---------- |
| tests      | implementer | none       | test-only  |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`

## Affected Architecture Docs

N/A: test-only.

## Platform Behavior

Test-only text fixtures; identical on native Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority | Rationale                    |
| ---- | -------- | ---------------------------- |
| AC-1 | required | the reported failure         |
| AC-2 | required | collision coverage preserved |
| AC-3 | required | change-local verification    |


## Progress Log


| Date       | Update  | Evidence                                          |
| ---------- | ------- | ------------------------------------------------- |
| 2026-10-21 | Planned | distribution follow-up Y5, verified at `1c5ba851` |
| 2026-10-21 | Readiness amendments: tests named; AC-1 runs a text-substituted scratch copy, matching how the rebrand works. | readiness code-reviewer finding |
| 2026-10-21 | Implemented: `ProfileShortcutLookupTests._names()` derives the colliding slug, shortcut and `Finish <noun>` alias from `DEFAULT_PROMPT_NAMES["close-wave"]` and the old phrase from `DEFAULT_PROMPT_NAMES["close-change"]`; second rename is `close-unit` / "Close unit"; the two `Prepare wave` tests read the phrase and declared path from the profile; the collision test asserts the renamed shortcut equals another key's default. AC-1 scratch: the substitution applied to only the two named files does not import (other modules call `prompt_doc("close-change")` at import), so it was applied to every `.py` under a scratch copy of `.wavefoundry/framework/scripts`. | Scratch rebrand, before: `test_renamed_profile_resolves_its_own_phrases` and `test_cache_follows_manifest_changes` FAIL, the two `Prepare wave` tests already pass under this table (slug `prepare-wave` is not rewritten); after: class 8 ok. Shipped table: `test_server_tools_lifecycle.py` 654 ok, `--profile second` 653 ok |
| 2026-10-21 | Clarification of the AC-1 note: the implementer's first scratch rebrand did not rewrite the `prepare-wave` slug; the coordinator's rerun added it. Both runs gave the same result: the two close-name tests fail before and pass after, and the two Prepare-wave tests pass before and after. | delivery code-reviewer finding E4; scratch rebrand rerun |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-21 | Derive the collision from the default table | Survives a rebrand and keeps the collision case | Use two unused names (drops the collision coverage); leave it to the distribution's rewrite rules (their workaround) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Derived names make the test less readable | A comment states the collision being exercised |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
