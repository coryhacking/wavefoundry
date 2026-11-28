# Clear Python and factor-review guidance on first install

Spec ID: `24fw1-enh first-install-python-and-factor-guidance`
Spec Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-11-27
Wave: 24i2t first-install-guidance

## Rationale

Waveforge reported two rough edges from a first install of a v1.54.0-based build on a workstation with Python 3.12 first on `PATH` and 3.14 also installed.

1. **Python version.** The Python runtime advisory (`runtime_advisory.py`) recommends 3.13 or newer and fires only on 3.11 and 3.12. As of November 2026, 3.13 is security-only: python.org publishes source-only security releases for it (3.13.18 has no installers), as it already does for 3.11 and 3.12. A person who installed one of those versions from python.org on Windows or macOS stops receiving security fixes at the last installer. The current text does not say this, and it does not mention 3.14. Setup also does not say when the interpreter running setup differs from the `python3` on `PATH` that the MCP host and `.wavefoundry/bin/wf` launch. The operator ran setup with 3.14 named explicitly while `python3` was 3.12. Setup then builds the tool environment for 3.14. The agent host and every `wf` subcommand other than setup launch `python3` (3.12) and refuse that environment: `venv_bootstrap.activate_tool_venv` prints "the tool venv was built for Python 3.14 ... run wf setup" and exits 2 (executed by the readiness red-team with a fake environment). Only setup recreates it (`setup_index._bootstrap_venv`). The field sequence is `inferred`: the operator's exact message is not yet captured.
2. **Factor-review warning.** On a fresh install, `docs/workflow-config.json` starts with an empty `factor_review_policy.applicable_factors` (`install/workflow-config.defaults.json`). Install row 2.3 (seed-030) writes `docs/repo-profile.json` with factors marked `applicable`. Row 2.5 (seed-050 task 5) then fills `applicable_factors` from the profile. `wf_audit_install` runs after every row, so every audit between rows 2.3 and 2.5 reports the mismatch that row 2.5 is about to fix. The warning was reproduced on a fixture made of the shipped defaults plus a profile with five applicable factors (executed, `check_factor_surface`). Its text uses framework vocabulary ("lane", "assessment", "applicable") and tells an installing user to run `Upgrade Wavefoundry`. The downstream agent turned it into a three-option decision with a default it chose itself.

## Product Intent

A person installing Wavefoundry for the first time learns which Python to use, and why, without reading the framework docs. Setup tells them when the interpreter running it is not the one their agent host will launch. During install they are not shown a factor-review warning that the next install step resolves. When the factor warning does apply (an installed project with factors marked relevant and none switched on), they can act on it, or ignore it, from the message alone.

Boundaries: no change to the Python floor (3.11), no change to what blocks setup, no automatic `PATH` or Python changes, no interactive prompt in setup, and no change to which factor lanes run.

AC-1 and AC-2 show the Python outcome, AC-4 the install-audit outcome, and AC-5 the wording outcome. Agent behaviour downstream (no invented decision) is observable only after release, in the next Waveforge first-install report.

## Requirements

1. The Python runtime advisory fires when the executing interpreter is 3.11, 3.12 or 3.13, and not on 3.14 or later. It recommends Python 3.14. It states that the executing version is supported, receives security fixes only, and blocks nothing. It states that python.org publishes no installers for security-only versions, so a version installed from python.org stops receiving security fixes, while package-manager builds may continue. The machine code `python_runtime_deprecated` and the advisory's field names stay unchanged. `recommended_minimum` becomes `"3.14"`.
2. When setup's strict Python check passes and the version that the `python3` on this `PATH` reports differs (major.minor) from the interpreter running setup, setup prints one stderr notice. The notice names both versions and both executables. It says the agent host and `wf` launch `python3`, so they will refuse the tool environment this run builds, and that the remedy is to rerun setup with that `python3` (for example `.wavefoundry/bin/wf setup`) or make the intended interpreter `python3`. Setup's result and exit code do not change.
3. The unresolved-interpreter failure text in `venv_bootstrap.py` recommends Python 3.14 instead of 3.13+.
4. The policy prose that states the Python recommendation is updated to Requirement 1's policy wherever it is stated: the framework README Python runtime section, seed-011 and seed-160, and the self-hosted docs that repeat it. Policy prose calls 3.11 to 3.13 supported and security-only, not deprecated. The census rule is every file that `git grep` finds for "3.13 or newer", "3.13+", "3.11/3.12" or "3.11 and 3.12" outside `docs/waves/` and `CHANGELOG.md`, keeping occurrences that are not about the recommendation.
5. The consolidated empty-lane factor warning fires whenever `applicable_factors` is empty and at least one factor is marked applicable (today it needs two, and a single factor falls through to the per-factor wording). While the install log has a pending row whose source is `seed-050`, `wf_audit_install` reports that warning under `pending_lint.warnings`, with its own note naming that row as the step that sets the default. The warning is reported neither as a `docs_lint_warning` diagnostic nor in `data.warnings` in that response. Once no such row is pending, the warning surfaces exactly as now. Other docs-lint warnings are unaffected, and `wf_validate_docs` output is unchanged by this requirement.
6. The consolidated empty-lane factor warning is reworded in plain terms. It names the relevant factor numbers, says this is fine to start with and blocks nothing, and gives two options with their consequence: switch some on (add their numbers to `applicable_factors`, after which the agent generates their reviewer docs and those reviewers join wave reviews), or keep none (mark those factors `partial` in `docs/repo-profile.json` to stop the notice). It keeps the leading `docs/workflow-config.json: ` path prefix. It drops the words "lane" and "assessment" and the `Upgrade Wavefoundry` instruction.

## Scope

**Problem statement:** first-install guidance about Python versions and factor reviews is out of date, silent where it matters, or noise.

**In scope:**

- `runtime_advisory.py` policy and text; the setup interpreter-mismatch notice; the `venv_bootstrap.py` failure text.
- Policy prose census per Requirement 4.
- `wf_audit_install` pending treatment of the consolidated factor warning; its wording in `wave_validators.py`.
- Tests for each of the above; a CHANGELOG entry.

**Out of scope:**

- Listing every interpreter installed (declined: MCP launches only `python3`).
- Stopping setup to make the person choose an interpreter (declined: 3.11 to 3.13 are supported and setup runs without a person present under agent hosts).
- Printing per-OS commands to change `PATH` (declined: wrong on managed machines; existing guidance points to the approved package manager or IT).
- Suppressing the factor warning for projects that deliberately keep zero lanes (declined: once this lands a fresh install no longer raises it, and the message says how to silence it).
- Recommending or qualifying Python 3.15, and raising the 3.11 floor.
- The per-factor drift warnings for projects with some lanes active.

## Acceptance Criteria

- [x] AC-1: The runtime advisory returns an advisory for 3.11, 3.12 and 3.13 and none for 3.14 and later, with `recommended_minimum` `"3.14"` and a message naming the python.org installer limit. Oracle: unit test over versions; fails against today's code, which returns none for 3.13 and recommends 3.13.
- [x] AC-2: With `PATH` `python3` reporting a different major.minor from the running interpreter, setup's strict check prints one notice naming both versions and the rerun-setup remedy, and returns `"ok"`; with matching versions it prints nothing extra. Oracle: unit test with a patched probe; fails today, since the ok path prints nothing.
- [x] AC-3: The failure text recommends 3.14, and the Requirement 4 census finds no remaining recommendation of 3.13 or deprecation wording for 3.11 to 3.13 outside `docs/waves/` and `CHANGELOG.md`. Oracle: test assertion on the failure text plus the census command recorded in the Progress Log.
- [x] AC-4: On a fixture install log with row 2.3 checked and the seed-050 row pending, plus the reproduced config and profile (with one and with several applicable factors), `wf_audit_install` carries the factor warning under `pending_lint.warnings` naming the seed-050 row, with no `docs_lint_warning` diagnostic and no `data.warnings` entry for it. With that row checked, the warning appears as a diagnostic. Oracle: handler test; fails today, since the warning is a diagnostic in both states.
- [x] AC-5: The reworded warning on the reproduced fixture names the factor numbers, contains neither "lane" nor "assessment" nor "Upgrade Wavefoundry", and states both options with their consequence. Oracle: docs-lint test.
- [x] AC-6: The change's own suites and every test it adds pass, including the second profile for each touched test file; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Update `runtime_advisory.py` (range, recommended version, message, guidance) and its tests.
- [x] Add the interpreter-mismatch notice to `ensure_python_resolves` (strict ok path) and test it; update the failure text.
- [x] Update the policy prose per the Requirement 4 census (seed edits under `seed_edit_allowed`).
- [x] Carry the consolidated factor warning as pending in `wf_audit_install` while a seed-050 row is pending; test it.
- [x] Reword the consolidated warning in `wave_validators.py`; update `test_docs_lint.py`.
- [x] Add a CHANGELOG entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| python-guidance | implementer | — | Requirements 1 to 4 |
| factor-warning | implementer | — | Requirements 5 and 6 |

## Serialization Points

- `.wavefoundry/framework/scripts/runtime_advisory.py`, `.wavefoundry/framework/scripts/venv_bootstrap.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/seeds/011-install-wavefoundry-phase-1.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/README.md`

## Affected Architecture Docs

`docs/architecture/contracts/mcp-tool-surface.md` states the advisory's version range and is updated under Requirement 4. No boundary, flow or layering change; other architecture docs N/A.

## Platform behaviour

All requirements behave the same on Windows, macOS, Linux and WSL2. The version probe already runs `python3` through raw spawn on each platform. The python.org installer limit matters most on Windows and macOS, where python.org installers are common; Linux distributions and Homebrew keep shipping patched builds. Native-Windows execution of the mismatch notice is unverified unless run on a Windows host.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core policy change |
| AC-2 | required | Closes the setup-vs-host mismatch seen in the field |
| AC-3 | required | Stale recommendation would contradict the advisory |
| AC-4 | required | Removes the self-inflicted install warning |
| AC-5 | required | Makes the remaining warning actionable |
| AC-6 | required | Change-local verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-27 | Spec planned from Waveforge first-install feedback | Fixture reproduction of the factor warning via `check_factor_surface` |
| 2026-11-27 | Readiness red-team primer: F1 (blocking, mismatch notice stated a false consequence) and F2 to F6 repaired in Rationale, Requirements 1, 2, 4, 5 and AC-2 to AC-4 before any lane approval | `.wavefoundry/work/24i2t/readiness-red-team.md` |
| 2026-11-27 | Lane approvals (code, QA, docs-contract) carry binding implementation notes. N1 (C2, code 7): the Requirement 6 option 1 text tells the person to ask the agent to generate the reviewer docs and says docs lint reports an error until they exist; it never says they appear on their own; AC-5's test asserts those clauses. N2 (C1, QA 1): the census adds a "deprecat" grep; prose stops calling 3.11 to 3.13 deprecated and says once why the machine code keeps its name. N3 (C3, C4): update the `wf_audit_install` contract in `docs/architecture/contracts/mcp-tool-surface.md` for `pending_lint.warnings` and its exemption, and the `pending_lint` description in seed 012; rendered `docs/prompts/*` follow their seeds. N4 (QA 4): the mismatch notice says the host refuses the tool environment built by `python3`'s mismatch, without claiming this run builds one, so it stays true under `wf setup --check`. N5 (code 1, 3, 5, 6; QA 2, 3, 5): shared constant prefix in `wave_lint_lib/constants.py` matched after stripping `WARNING: `; seed-050 row found in all rows, not phase-filtered; advisory range `(3, 11) <= v < (3, 14)`; notice only on the strict ok path, stderr, major.minor; AC-4 adds a blocking-lint-error case; invert the single-factor test and update the retired-lane test | `.wavefoundry/work/24i2t/readiness-code.md`, `readiness-qa.md`, `readiness-docs-contract.md` |
| 2026-11-27 | Implemented. Advisory range `(3, 11) <= v < (3, 14)`, recommends 3.14 (`runtime_advisory.python_runtime_advisory`). Setup mismatch notice `venv_bootstrap._report_interpreter_mismatch`, strict ok path only. Factor warning reworded behind `FACTOR_REVIEWS_OFF_WARNING_PREFIX`, threshold dropped to one factor; N1 wording says a switched-on factor becomes a reviewer agent that wave reviews can call on (review lane selection does not read `applicable_factors`, so "reviews every wave" would overclaim). `wf_audit_install_response` carries it under `pending_lint.warnings` while a `seed-050` row is pending in any phase. Census (four phrases plus "deprecat"): README, seeds 011, 160, 012, contract, project-overview, native-windows-support (lines 68 and 144; line 68 was missed by the readiness census), build-and-verification, install-log-format (both copies), and the two self-hosted prompts edited to match their seeds (this repo is never upgraded); remaining hit is a negative assertion in `test_venv_bootstrap.py`. Gapfill: censuses and multi-file prose replacements used `git grep` and scripted exact-string edits because they are bulk-mechanical; code reading used MCP and Read | `run_tests.py --no-cache`: 13653 tests, 261 files OK (receipt written); `--profile second` on the 5 touched test files: 0 failed; `wf_validate_docs`: ok |
| 2026-11-27 | Delivery red-team primer: no blocking findings, 15 of 15 mutants killed. Non-blocking RT-DEL-1 to RT-DEL-4 repaired before the delivery lanes ran: the switch-on option now says to mark factors left off `partial` (otherwise the per-factor wording returns); the mismatch remedy names `.\\.wavefoundry\\bin\\wf.cmd setup` on native Windows; `test_ok_when_python3_already_ge_311` patches `sys.version_info` so the notice no longer leaks to the runner; the `wf_audit_install` tool docstring names `pending_lint.warnings` (adds `wf_server/server_impl.py` to the delivery paths) | `.wavefoundry/work/24i2t/delivery-red-team.md`; focused runs of 5 files (1902 tests) OK; second profile on 2 touched test files OK |
| 2026-11-27 | The docstring repair changed the `wf_audit_install` handler digest; refreshed only that entry in `tests/fixtures/register-surface-handler-digests.json` (caught by the full suite in `test_mcp_tool_registry.py`) | `run_tests.py --no-cache`: 13654 tests, 261 files OK, receipt written; delivery fingerprint `8bc95b8c2e293372` over the 27 paths in `.wavefoundry/work/24i2t/delivery-paths.txt` |
| 2026-11-27 | CODE-DEL-1 (non-blocking test gap, mutant B survived): the checked-row case now asserts `warnings_note` is empty | `run_tests.py --no-cache`: 13654 tests OK (`full-suite-4.log`) |
| 2026-11-27 | Operator decision after a field report (a Waveforge 3.1 user on Python 3.12 upgraded one project to 3.2, and the shared tool environment rebuild forced every project to upgrade): "I'm thining that we do option 1." The advisory guidance and README transition step 2 now say every project on the machine shares one tool environment unless `WAVEFOUNDRY_TOOL_VENV` is set, that setup under a different Python rebuilds it for all of them with this project's release, and to upgrade the other projects first or isolate this one. Wording within Requirement 1's guidance; no new mechanism. Keying the environment by Python version or release stays out of scope (workstation-install design on hold) | `test_runtime_advisory.py` asserts the new sentences; focused and second-profile runs OK |
| 2026-11-27 | Full suite caught `test_venv_bootstrap.SingleResolverScanTests.test_tool_venv_env_read_in_exactly_one_place`: the guidance string named the override variable, which only `venv_bootstrap` may mention. The advisory guidance now says "isolate this project" and points to the framework README transition section, which names the variable | `full-suite-5.log` (1 failure, fixed); focused `test_runtime_advisory.py` + `test_venv_bootstrap.py` OK |
| 2026-11-27 | Code delta recheck re-approved; CODE-DEL-1's first assertion targeted the wrong case (mutant B still survived). Added the right case: a pending seed-050 row with no factor warning carries an empty `warnings` list and an empty `warnings_note` | `ev-approval-code-reviewer-3`; focused `test_server_tools_lifecycle.py` 743 tests OK |
| 2026-11-27 | Close preparation: the `.wavefoundry/work/24i2t/` review reports, delivery paths, process review, final suite log and second-profile log are archived in `evidence/review-notes.tar.gz` | `evidence/review-notes.tar.gz` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-27 | Recommend 3.14 and advise on 3.11 to 3.13 | Operator: "Ok, let's plan, prepare, review and implement these changes" after the 3.14 recommendation. 3.13 joined the security-only set in Oct 2026. Planner default: the advisory covers 3.13 because the same installer limit applies | Recommend 3.15 (rejected: six weeks old, dependency wheels unverified) |
| 2026-11-27 | Factor fix: audit carries the warning as pending while the seed-050 row is pending | Efficacy: replaying the field case, every audit between rows 2.3 and 2.5 now reports it as pending, and row 2.5 fixes the cause. Deterministic, reuses the audit's existing pending mechanism, no writes. Misses: an install that skips seed-050's default still warns after 2.5, which is correct. Measure: next Waveforge first-install report | Have seed-030 write `applicable_factors` too (rejected: still agent-followed prose, which is what failed); have the audit write the default (rejected: an audit must not mutate) |
| 2026-11-27 | Mismatch notice on stderr only; no `setup_readiness` reason | Planner default: the host's own refusal already names `wf setup`; a readiness reason is extra surface for the same fact | Report the mismatch through `setup_readiness` (rejected for now: larger change, same remedy) |
| 2026-11-27 | Mismatch notice instead of a block | Planner default: setup under an explicit newer interpreter is legitimate; the notice tells the person what the host will launch | Refuse setup on mismatch (rejected: adds a gate the operator declined in 1.2) |

## Risks

| Risk | Mitigation |
| --- | --- |
| 3.13 users see a new advisory after upgrade | The message says the version is supported and blocks nothing |
| The pending match keys on message text | Match on a constant prefix shared by the validator and the handler |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
