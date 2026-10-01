# Profile Assets Name the Expected Profile, and the Second Profile Matches Set and Wave

Change ID: `1zima-debt profile-assets-name-the-expected-profile`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zimb expected-test-profile

## Rationale

Wave 1zim5 added profile assets under `tests/fixtures/profiles/` and two guards that check the loaded constants: `record_layout_support.declared_profile_match` (vocabulary and layout, used by `test_profile_support.test_loaded_constants_are_shipped_or_a_declared_profile`) and `declaration_support.declaration_profile_match` (tool declarations, used by `test_extension_tool_modules.test_declaration_module_ships_empty`). Both accept the shipped defaults or any committed asset. So a canonical tree accidentally left with `second.json`'s or `declared.json`'s exact values passes its default run; docs-lint would catch the vocabulary case indirectly, nothing catches the declaration case (the 1zim5 delivery review's strongest challenge). A distribution such as Waveforge, which changes its constants permanently, has no way to say which profile its tree is meant to be, so the guard cannot tell its intended profile from drift.

Separately, `second.json` uses Set/Member. Waveforge renamed its tiers to Set (container) and Wave (item), so the second profile should exercise that case, including the live item label Wave sharing its name with the archive profile's container label Wave.

## Requirements

1. **Second profile is Set/Wave.** `second.json` sets `ITEM_NAME` `Wave`, `ITEM_NAME_PLURAL` `Waves`, `MEMBER_HEADING` `## Waves`, `MEMBER_ID_LABEL` `Wave ID`, `MEMBER_STATUS_LABEL` `Wave Status`; the container values (`Set`, `Sets`, `set.md`, `set-id`, `# Set Record`, `## Set Summary`, back-reference `Set`), the layout and the default-vocabulary archive profile at `docs/waves` are unchanged. Its description says it mirrors a distribution that renamed its tiers to Set and Wave.
2. **One source for the second profile's names.** Tests that pin `second.json`'s values take them from `load_profile("second")`: `test_profile_support` (BuilderLintTests, LocalizationHelperTests), `test_vocabulary_second_profile`, `test_archive_root` and `test_archive_memory_backfill` (whose private Set/Member vocabulary is replaced by the asset's), so there is one Set/Wave profile in the suite. `test_vocabulary_writers` (its own `patch.multiple` vocabulary, allowlisted in the literal census) and the `test_vocabulary_profile` refusal cases stay unchanged.
3. **An asset can be marked active.** A profile asset may carry `"active": true` (a boolean; any other type is an error). The framework's own assets (`second.json`, `declared.json`) are never marked active, and a test pins that they carry no `active` key. A distribution marks its own asset (for example `waveforge.json`), committed beside the framework's. `WAVEFOUNDRY_TEST_PROFILE` is read in exactly one place, a resolver in `record_layout_support`, which `declaration_support` imports.
4. **The expected profile is a layering.** The base is the single asset marked active, else the shipped defaults; then, when `WAVEFOUNDRY_TEST_PROFILE` names a profile (set by `run_tests.py --profile NAME` in the copy's runner environment), that asset's modules are overlaid on the base, matching how `apply_profile` edits the copied tree. More than one active asset, or a `WAVEFOUNDRY_TEST_PROFILE` value with no asset, is an error that fails the guards; it never falls back to any match. The failure names every layer and its source.
5. **Exact guards.** `declared_profile_match` and `declaration_profile_match` (or their replacements) compare the loaded constants with the shipped defaults overlaid with the base, then the run-mode profile, and nothing else. On a mismatch the failure names each layer, its source (`WAVEFOUNDRY_TEST_PROFILE`, the active asset, or the shipped defaults) and each differing constant. `test_declaration_module_ships_empty` checks the expected declaration the same way. The comparison takes the expected profile as an argument; resolution is a separate function taking `environ` and `profiles_dir` (defaulting to `os.environ` and `PROFILES_DIR`). Unit tests pass both explicitly, so they hold under every run mode: `test_declared_profile_match` and `test_a_declaration_leaves_the_marker_and_the_match_alone` (test_profile_support) and `test_declaration_profile_match` (test_declaration_support) are rewritten that way, and `test_loaded_constants_are_shipped_or_a_declared_profile` is renamed `test_loaded_constants_are_the_expected_profile`.
6. **The run says which profile it applied.** The profile run's report already names the profile (`_print_profile_report`); it also states the source of the expected profile (run mode, active asset or shipped).
7. **Docs.** `docs/architecture/testing-architecture.md` describes the active marker, the layering and how a distribution adds its asset, replacing the any-asset wording in its profile section, the Set/Member description of the second profile and its `Member ID:` example with Set/Wave; the `test_vocabulary_second_profile` module docstring follows the asset; the 1zim5 `### Changed` entry in `## [Unreleased]` gains one sentence on the active marker for distributions.
8. **Platforms.** Windows, macOS, Linux and WSL2 behave the same: an environment variable and a JSON field.
9. **Transition.** Test infrastructure only; the default run of this repository is unchanged (no asset is active here).
10. **Receipt runs refuse a stray profile.** A full run that can write the receipt (no `--file` or `--profile`) refuses with exit 2, naming `WAVEFOUNDRY_TEST_PROFILE`, when that variable is set.

## Scope

**Problem statement:** the profile guards accept any committed asset, so they cannot catch a tree left on the wrong profile, and a distribution cannot declare its intended profile; the second profile does not mirror the Set/Wave rename distributions use.

**In scope:**

- `tests/fixtures/profiles/second.json`; `tests/record_layout_support.py`, `tests/declaration_support.py`, `run_tests.py` (environment and report); the tests named above; testing-architecture; one CHANGELOG sentence.

**Out of scope:**

- Waveforge's own asset (it lives in the Waveforge repository).
- Changing what `default_profile_only` compares against (it stays the frozen shipped defaults).

## Acceptance Criteria

- [x] AC-1: `second.json` holds the Set/Wave values in Requirement 1; the whole suite passes under `run_tests.py --profile second` with every skip beyond the default run's from `default_profile_only`, and under `--profile declared`.
- [x] AC-2: the tests that pin `second.json`'s values read them from `load_profile("second")`: `test_profile_support` (BuilderLintTests, LocalizationHelperTests), `test_vocabulary_second_profile`, `test_archive_root` and `test_archive_memory_backfill`; no literal Member, Members, Member ID or Member Status remains in them; `test_vocabulary_writers` and the `test_vocabulary_profile` refusal cases are unchanged; the literal census has no stale entry.
- [x] AC-3: the guards fail, naming each layer and the differing constants, when (a) a scratch canonical tree has `second.json`'s vocabulary with no marker and no run-mode name, (b) it has `declared.json`'s declaration likewise, (c) a scratch tree has an asset marked active and constants that differ from it, (d) two assets are marked active, (e) the run-mode name has no asset; they pass for the shipped tree, for each run mode, and for a scratch tree whose active asset matches its constants; (f) a receipt-writing full run refuses with exit 2, naming `WAVEFOUNDRY_TEST_PROFILE`, when it is set; (g) an active asset combined with a run-mode profile passes when the copy equals the layering and fails otherwise. The scratch-tree cases use the injected resolver, or `copy_scripts_tree` also copies `declaration_support.py`.
- [x] AC-4: the profile run's report states the source of the expected profile (run mode, active asset or shipped) beside the profile name it already prints.
- [x] AC-5: the testing-architecture doc and the CHANGELOG sentence describe the marker and precedence.
- [x] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Update `second.json` to Set/Wave.
- [x] Derive second-profile names from the asset in the tests that pin them, including the archive tests' private vocabulary.
- [x] Add the `active` field to asset validation and the expected-profile resolution.
- [x] Make both guards exact against the expected profile, with a naming failure message.
- [x] Set `WAVEFOUNDRY_TEST_PROFILE` in the copy's runner environment and name the profile in the report.
- [x] Refuse a receipt-writing full run while `WAVEFOUNDRY_TEST_PROFILE` is set; pin that the framework assets carry no `active` key.
- [x] Tests for AC-3 and AC-4; whole-suite runs under both profiles.
- [x] Docs and CHANGELOG sentence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Expected-profile guards | implementer | readiness | support modules and run mode |
| Second profile to Set/Wave | implementer | guards | asset and dependent tests |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/record_layout_support.py`, `.wavefoundry/framework/scripts/tests/declaration_support.py`, `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/tests/fixtures/profiles/second.json`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` (profile section).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The second profile must mirror the Set/Wave rename and still pass |
| AC-2 | required | One source for the profile's names |
| AC-3 | required | The guards must catch a tree on the wrong profile |
| AC-4 | required | The run must say what it checked |
| AC-5 | required | Distributions need the convention documented |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Delivery review approved all lanes; its maybe_later items fixed: the two-active and asset-load errors name the run-mode layer; testing-architecture names the `--schedule-control` exemption (Requirement 10's wording lists `--file` and `--profile`; the code's third exemption never writes the receipt); `test_the_refusal_comes_before_any_hashing` pins the ordering. Reverified with mutants. Full suite 10354 OK | `scratchpad/full-r2.txt` |
| 2026-10-01 | Implemented. Deviation: `test_run_tests_cache` and `test_run_tests_repo_guard` (not named in the plan) unset `WAVEFOUNDRY_TEST_PROFILE` in a `setUpModule` and restore it after, because the Requirement 10 refusal made 36 of their cases fail under `--profile`. Guard names `declared_profile_match`/`declaration_profile_match` replaced by `expected_profile_mismatch`/`declaration_profile_mismatch`; `copy_scripts_tree` also copies `declaration_support.py`. Full suite 10353 OK; `--profile second` 149/149 files (extra skips all `default-profile-only`); `--profile declared` 149/149 files (no extra skips); scratch mutation of the no-marker second vocabulary fails the guard | `scratchpad/full.txt`, `profile-second.txt`, `profile-declared.txt` |
| 2026-10-01 | Planned from the 1zim5 delivery review's strongest challenge and the operator's direction (Set/Wave second profile; the active marker inside the asset rather than a separate file). Verified: `declared_profile_match` returns "shipped" or the first asset whose overlay matches; `_profile_errors` accepts only a `modules` object today; `_child_runner_env` builds the copy's runner environment; second-profile names appear as literals in `test_profile_support`, `test_vocabulary_second_profile`, `test_vocabulary_writers`, and as private Set/Member tuples in `test_archive_root` and `test_archive_memory_backfill` | `tests/record_layout_support.py`, `tests/declaration_support.py`, `run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Mark the active asset with a field inside it | A distribution adds one file, and the asset and its activation cannot drift apart | A separate `ACTIVE` file naming the asset |
| 2026-10-01 | Run mode names its profile through the copy's runner environment | No extra write into the temporary repository, and nothing that can be committed by accident | A marker file written into the copy |
| 2026-10-01 | The expected profile layers the run-mode profile over the active asset (readiness finding) | `apply_profile` overlays the copied tree, which in a distribution already carries its active profile; replacing the base would fail every run mode there | Reset the copy to shipped before applying, which would stop run mode from testing the distribution's own profile |
| 2026-10-01 | Remaining Set/Wave labels derived from the item name (`## Waves`, `Wave ID`, `Wave Status`) | Mirrors how the default derives its labels from Change | Copy Waveforge's exact labels (to confirm with Waveforge if they differ) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Live item label Wave equals the archive container label Wave and confuses a reader | That is the realistic case this profile exists to exercise; the whole-suite run under it is the check |
| A stray `WAVEFOUNDRY_TEST_PROFILE` in a developer's shell selects a profile the tree does not have, or lets a drifted tree pass and write a green receipt | A receipt-writing full run refuses with exit 2 while it is set; otherwise the guards fail and name `WAVEFOUNDRY_TEST_PROFILE` as the source |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
