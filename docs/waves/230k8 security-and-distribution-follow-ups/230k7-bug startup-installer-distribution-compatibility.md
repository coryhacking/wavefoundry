# Guard startup installs and preserve distribution fixture boundaries

Change ID: `230k7-bug startup-installer-distribution-compatibility`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-10
Wave: 230k8 security-and-distribution-follow-ups

## Rationale

Waveforge reports startup dependency installation can use a uv below the existing advisory floor without a version check. Source inspection finds server._startup_install_gate_unguarded and _run_background_install call setup_index.install_requirement_specs, whose _uv_bin selection is separate from setup's uv_tls_step. Source also confirms unconditional container fixture arguments, retired wave_new_<kind> CLI wording and literal wave nouns in Plan arc skill copy. Execution status: unverified; reproduce installer behavior with controlled executables and no package network activity before claiming the defect is demonstrated.

## Product Intent

Operators receive a visible, actionable refusal before automatic dependency installation uses an affected or unverifiable uv. Distributions can test core declarations without fork-only arguments and render their own container vocabulary. AC-1 through AC-4 establish those outcomes. This supports [the adopted vision](../../../VISION.md), Horizon 1's dependable delivery on the existing foundation; it does not redirect the roadmap or add an acceptance program.

## Requirements

1. Before foreground or background MCP startup installs dependencies, validate the version of the actual selected uv executable against setup_index.UV_TLS_ADVISORY_FIXED_IN. Reuse the existing bounded version probe and floor rather than duplicate a version constant. Refuse startup installation when that selected version is below the floor or cannot be established; do not silently choose a different installer or downgrade transport security.
2. Recheck the selected executable at the install boundary so an earlier check of another path does not authorize installation. Preserve dependency rechecks and install-lock ownership. An eligible current uv follows the existing install flow; a startup needing no install does not fail because an unused uv is old.
3. Expose refused startup-install status and the reason through wf_server_info when the server can start, and stderr/startup assessment when it cannot. Give a selected-root launcher remedy using the existing operator-owned --upgrade-uv path; distinguish tool-environment from PATH ownership. Do not automatically upgrade uv, download packages to test the guard or change ordinary setup advisory policy.
4. Container test helpers must apply distribution fixture arguments only for the applicable active declaration. A fixture using declaration_support.apply_base_declaration must call core tools without fork-only arguments; a distribution declaration must still receive its configured arguments. Keep collision checks and existing fixture extension seams.
5. Change lifecycle_id CLI guidance from retired wave_new_<kind> to wf_new_<kind>. Render Plan arc container nouns through the vocabulary profile in description and body, including references to authoritative container evidence. Preserve public skill identity, prompt routing and no-implementation-authority semantics.
6. Update downstream-facing release notes and startup/tool-environment documentation for the guard and its limits. Security surface census and served-close fixture changes belong to companion plan 230k6, not this plan.

## Scope

In scope: server.py startup install paths, setup_index.py uv selection/probe/install helpers, process_info or server info propagation where needed, tests/server_tools_support.py and container fixture/declaration tests, lifecycle_id.py, render_agent_surfaces.py, generated Plan arc skill surfaces on active hosts, relevant tests, docs and CHANGELOG.md.

Out of scope: new uv pin, automatic uv upgrades, dependency policy redesign, real network installs during regression tests, downstream repository edits, renamed skill commands, general renderer changes and unrelated writing-guide work. Inspect the current advisory floor in source; do not substitute the pinned version for the minimum permitted version.

## Acceptance Criteria

- [x] AC-1: Controlled foreground and background startup tests reject below-floor, unreadable, failed and timed-out uv probes before any dependency installation occurs; a floor-satisfying selected uv proceeds and a no-install startup is unaffected. The existing unguarded path must fail these controls.
- [x] AC-2: The refusal reaches served wf_server_info for a startable server and startup stderr/assessment for a blocked server, with correct selected-root remediation and no automatic uv upgrade. Tests prove the checked executable is the executable selected for installation, including PATH fallback.
- [x] AC-3: Container fixture tests under the base declaration do not inject distribution-only arguments; declared distribution controls do inject them and preserve argument-collision refusal. Exercise the RetainedUpgradePreviewTests path that motivated the report.
- [x] AC-4: Rendered Plan arc skills use configured container nouns under default and renamed profiles while retaining routing and authority limits. The lifecycle ID CLI names current wf_new_<kind> tools; a literal old-name control fails.
- [x] AC-5: Changed source, generated skill copies and documentation agree; this change’s tests pass, its docs validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Reproduce startup selection and base-declaration fixture failures with bounded offline controls.
- [x] Implement the selected-uv install guard and truthful startup status propagation.
- [x] Repair fixture declaration handling, CLI guidance and Plan arc vocabulary; regenerate only affected surfaces.
- [x] Update release/support guidance, run scoped checks under default and downstream profiles, and obtain required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Reproduce and implement | Implementer | Readiness | Source edits only after admission and Prepare. |
| Verify delivery | Required reviewers | Implementation | Independently check served behavior and negative controls. |

## Serialization Points

One implementer owns shared source edits. Coordinate CHANGELOG.md with concurrent work. Do not modify unrelated writing-guide work.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/process_info.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/scripts/lifecycle_id.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.codex/skills/wf-plan-arc/`
- `.claude/skills/wf-plan-arc/`
- `.agents/skills/wf-plan-arc/`
- `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md for startup refusal/status flow and docs/architecture/testing-architecture.md for active-declaration fixture routing. Update docs/contributing/build-and-verification.md and applicable startup support guidance.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped repair and compatibility contract. |
| AC-2 | required | Establishes the scoped repair and compatibility contract. |
| AC-3 | required | Establishes the scoped repair and compatibility contract. |
| AC-4 | required | Establishes the scoped repair and compatibility contract. |
| AC-5 | required | Establishes the scoped repair and compatibility contract. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-10 | Authored from Waveforge v1.41.0 follow-up and current source inspection; not admitted or readied. | Report targets tag efc286b6 / commit d7ab7aad. Execution status: unverified; reproduce before implementation. Indexed retrieval refused index_runtime_stale, so targeted source reads supplied grounding. |
| 2026-11-10 | Readback: `setup_index.install_requirement_specs` will probe the exact uv command it is about to run, after the under-lock dependency recheck and before the install, and return a refusal when that uv is below `UV_TLS_ADVISORY_FIXED_IN` or its version cannot be read (today: it installs with any uv). A startup that needs no install never probes. Foreground and background startup report the refusal with the `--upgrade-uv` remedy through stderr, the startup assessment and `wf_server_info` (AC-1, AC-2). Container fixture arguments apply only when the active declaration serves a distribution handler for that tool, so a base-declaration fixture calls core tools without them (AC-3). The lifecycle-id CLI names `wf_new_<kind>` and the Plan arc skill renders container nouns through the vocabulary profile (AC-4). Scope boundary: no new uv pin, no automatic upgrade, no network in tests, ordinary `wf setup` advisory unchanged. Expected files: `setup_index.py`, `server.py`, `tests/server_tools_support.py`, `tests/declaration_support.py`, `lifecycle_id.py`, `render_agent_surfaces.py`, the three `wf-plan-arc` skill copies, tests, docs and `CHANGELOG.md`. This serves Product Intent by refusing visibly before an affected or unverifiable uv installs anything. | Source read: both startup routes call `install_requirement_specs`; `_uv_version` probes `_UV_PROBE_COMMAND` while the install runs `_STARTUP_UV_COMMAND` or `_uv_bin`. |
| 2026-11-10 | Reproduced before the fix. Installer: `install_requirement_specs` ran `uv pip install` with no version check; after the guard was added, the unchanged fake uv (which answers every argument the same way) was refused in five existing installer tests, showing those paths had never probed. Fixture: `RetainedUpgradePreviewProfileTests` asserted that the base-declaration preview fixtures receive the profile's `extra` argument, which only its spy removed before the core tool saw it. CLI: the stderr reminder named `wave_new_<kind>`. Skill: the Plan arc registry entry held the literal nouns `waves` and `wave`. | `test_startup_install.py`, `test_container_fixture_profile.py` and `test_lifecycle_id.py` before and after each edit; no package network activity, every uv is a local script. |
| 2026-11-10 | Implemented. `_uv_command_version` is the one bounded probe; the installer probes its own `uv_command` after the under-lock recheck and returns `uv_refused` with a `uv_refusal` detail; `server.py` adds `startup_install_uv_refused`, recommends `--upgrade-uv` for the selected root and keeps the detail in the `startup_install` record on both routes. `declaration_support.distribution_handler_served` routes fixture arguments by the active declaration. `lifecycle_id.py` names `wf_new_<kind>`. The Plan arc entry uses `_vp_wave()`; under the default profile the rendered text is byte-identical, so the three skill copies did not change. | `run_tests.py --file test_startup_install.py --file test_tree_kill_routing.py --file test_trusted_executable_lookup.py --file test_setup_uv_advisory.py --file test_setup_index.py`: 338 tests OK. `--file test_container_fixture_profile.py`: 15 OK. `--file test_vocabulary_tier_nouns.py --file test_lifecycle_id.py --file test_arc_records.py --file test_initiative_planning_delivery.py`: 104 OK. Registry text compared with `.claude`, `.codex` and `.agents` `wf-plan-arc/SKILL.md`: equal. |
| 2026-11-10 | Landing rule, in a scratch copy of the tree, baseline green, mutant killed. Guard disabled, and unreadable version accepted: `SelectedUvGuardTests.test_an_affected_or_unverifiable_uv_is_refused_before_any_install`. Probe of another command: `test_the_probed_command_is_the_command_that_installs` and `test_a_uv_at_or_above_the_floor_installs_as_before`. Probe moved before the recheck: `test_a_startup_that_needs_no_install_never_probes_an_old_uv`. Foreground and background refusal reasons removed: `GateTests.test_a_foreground_refusal_reaches_stderr_the_assessment_and_the_snapshot` and `test_a_background_refusal_is_published_with_the_reassessment`. Fixture routing disabled, and a pinned distribution declaration ignored: `ActiveDeclarationRoutingTests`. Retired CLI name restored: `test_cli_reminder_on_stderr_stdout_is_bare_id`. Literal Plan arc noun restored: `SkillProseTests.test_plan_arc_keeps_its_identity_routing_and_authority_limits`. | 10 of 10 mutants killed. |
| 2026-11-10 | Platform behaviour: the probe and refusal use the existing `_run_install_step` and path helpers, so they behave the same on Windows, macOS, Linux and WSL2; `uv.exe` under `Scripts` is the tool-environment uv on Windows. Verified on macOS only. Limits: the check reads the version the uv reports and does not verify the binary; a uv replaced between the probe and the install is not detected. | `test_the_path_fallback_uv_is_the_one_probed_and_its_remedy_names_path` covers both ownership cases with a patched selection; no native Windows run. |
| 2026-11-10 | Gapfill: same retrieval note as change 230k6; the stale loaded MCP server made host file reads the practical instrument for edit ranges after MCP orientation. | Context-efficiency ledger, implement stage. |
| 2026-11-10 | Delivery review. Code, QA, architecture, security and docs-contract lanes approved in fresh, independent contexts; the security lane's own uv probes pass on this tree and fail on a copy of HEAD. No finding against this change. Accepted notes: the four refusal cases run at the shared installer and two per startup route through real subprocesses, since both routes call the one installer; the PATH fallback test patches the uv selection. | Ledger approvals for all five lanes. Full suite: 12,709 tests across 238 files, 12 skips, OK. `run_tests.py --profile second` and `--profile declared` over the ten changed test files: 1,232 and 1,235 tests OK. `wf_validate_docs`: ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-10 | Guard automatic installation using the existing version probe and fix fixture/profile owners | A blocking check prevents the affected install; status gives an operator a remedy. Controlled startup and declaration tests measure the outcome; field integration remains separate | Startup advisory alone permits the affected install; automatic uv upgrade changes an operator-owned environment; disabling all startup installs loses useful supported behavior |

## Risks

| Risk | Mitigation |
| --- | --- |
| Version probe blocks healthy server startup | Probe only when automatic installation is needed and keep the existing finite timeout. |
| Fork fixture logic leaks into base declaration | Test both active declaration states in the same process and restore state between tests. |
| Guard observes a different installer than the one used | Bind the probe to the selected execution path at installation time; test selection changes. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
