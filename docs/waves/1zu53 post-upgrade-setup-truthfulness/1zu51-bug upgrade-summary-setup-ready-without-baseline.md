# Upgrade Summary Reports Setup Ready When No Setup Baseline Was Recorded

Change ID: `1zu51-bug upgrade-summary-setup-ready-without-baseline`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-04
Wave: 1zu53 post-upgrade-setup-truthfulness

## Rationale

Field report (1.29.0+puha upgrade, macOS, Python 3.13 to 3.14): the cleanup summary printed `Setup: ready` and `setup_status: "ready"`, while `index_health` reported `action_required (setup_inputs_changed)` and the cleanup log said "Setup baseline not recorded: the environment differs from the one setup last recorded; run `wf setup`". The same contradiction was reported for the ptit build and never planned.

Cause, in `upgrade_wavefoundry._record_setup_baseline`: the summary's setup fields come from a live assessment that ignores the setup stamp (`assess_setup(root, use_stamp=False)`). When that assessment is ready but the stamp is NOT written (the prior stamp's environment differs, or `stamp=False` after a failed index update or dependency step), the function still returns the live `ready` result. Every later readiness check compares against the old stamp and reports `setup_inputs_changed`, so the summary contradicts the state the upgrade leaves behind.

## Requirements

1. When `_record_setup_baseline` returns without writing the stamp on a path where the live assessment was `ready` (the environment-differs path and the `stamp=False` path), it returns the stamp-aware assessment (`setup_readiness.assess_setup(root)`, `use_stamp` default), so the summary's `setup_status`, `setup_reasons` and `setup_command` match what `index_health` reports after cleanup. That assessment goes through the same bounded transient retry as the live one (one shared helper), so a reindex still writing does not leave a needless `indeterminate`.
2. When the stamp IS written, the returned assessment is unchanged (the live result, `ready`).
3. A non-ready live assessment is returned as today (it already names its own command), and the exception path still returns `None` (`not_assessed`). Known residual, kept on purpose: when `write_setup_stamp` itself raises (for example framework sources changed during the assessment) and an outdated stamp remains, the summary reads `not_assessed` while `index_health` reports `setup_inputs_changed`; that is not a false `ready`, and the log names `wf setup --check`.
4. Nothing else changes: the stamp-writing decision, the retry loop, the log lines and the `wf_upgrade` next-step logic stay as they are. With `setup_status` now `action_required`, the existing 1zfd9 logic puts `setup_command` ahead of `wf_reload_mcp`.
5. Seed 160, the rendered upgrade prompt and the MCP tool-surface spec say that when no setup baseline is recorded the summary reports the stamp-aware assessment; CHANGELOG gets a bullet under `## [1.29.0]` `### Fixed` (1.29.0 is unreleased).

## Scope

**Problem statement:** the upgrade summary says setup is ready when the upgrade deliberately left an outdated stamp that makes every later check say otherwise.

**In scope:**

- `_record_setup_baseline` return value on its no-stamp paths; tests; seed 160 and its rendered prompt; spec; CHANGELOG.

**Out of scope:**

- Whether the environment-differs path should write the stamp (kept: an environment change the live checks cannot see stays visible).
- Other setup feedback from the same field report (`.gitattributes` drift, `--check` transient, first-install closing text), triaged separately.

## Acceptance Criteria

- [x] AC-1: With a prior stamp from a different environment and a ready live assessment, the cleanup summary reports `setup_status` `action_required`, `setup_reasons` containing `setup_inputs_changed`, and a `setup_command` naming `wf setup`; the stamp is unchanged.
- [x] AC-2: With `stamp=False` (failed index update) and a prior stamp that no longer matches, the summary reports `action_required` with `setup_inputs_changed`; without a prior stamp it still reports `ready` (existing 1zfd9 tests stay green).
- [x] AC-3: When the stamp is written, the summary reports `ready` (existing tests stay green).
- [x] AC-4: Reverting to returning the live result on the no-stamp paths fails the AC-1 and AC-2 tests (shown in a scratch copy).
- [x] AC-5: Seed 160, `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/specs/mcp-tool-surface.md` and CHANGELOG describe the behavior; docs validate.

## Tasks

- [x] Return the stamp-aware assessment on the no-stamp ready paths
- [x] Add the AC-1 and AC-2 tests to `test_upgrade_wavefoundry.py`
- [x] Show the revert mutant fails in a scratch copy
- [x] Update seed 160, the rendered prompt, the spec and CHANGELOG

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                |
| ---------- | ----------- | ---------- | ------------------------------------ |
| summary    | implementer | —          | one function, tests, docs            |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: the summary's fields and producers are unchanged; only which assessment fills them on two paths. The spec carries the field contract.

## Platform Behavior

Windows, macOS, Linux and WSL2 behave the same: the assessment and stamp logic are platform-neutral. Transition: the summary fields come from the new-code `--cleanup` subprocess, so they are correct on the upgrade that installs the fix; the `next_step` reordering is computed by the running server, so on the MCP path it appears only after a reload or restart onto the new code (as the spec already states).

## AC Priority


| AC   | Priority | Rationale                                       |
| ---- | -------- | ----------------------------------------------- |
| AC-1 | required | the field-reported contradiction                |
| AC-2 | required | same contradiction on the failed-index path     |
| AC-3 | required | no regression on the normal path               |
| AC-4 | required | the pins must catch a revert                    |
| AC-5 | required | the documented contract must match              |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-04 | Delivery finding DEL-1 (the stamp-aware call's retry was unpinned) repaired: `test_stamp_aware_summary_assessment_is_retried_while_transient` covers both no-stamp paths (environment differs, `stamp=False`); reverified independently | mutants M3, M3a, M3b killed |
| 2026-10-04 | Implemented: `_record_setup_baseline` routes every assessment through one nested `assess(**kwargs)` that keeps the 1z1vs transient retry; the `stamp=False` and environment-differs paths return `assess()` (stamp-aware). New tests `test_kept_stamp_makes_the_summary_report_what_later_checks_report` and `test_unstamped_index_failure_reports_an_outdated_stamp`; the two retry tests' sleep spy now matches `co_qualname` (the loop moved into the nested helper). Seed 160 (gate opened and closed), rendered prompt, spec, CHANGELOG 1.29.0 Fixed | `test_upgrade_wavefoundry` 589 OK; scratch mutants M1 (environment-differs returns live) and M2 (`stamp=False` returns live) killed against a green baseline |
| 2026-10-04 | Readiness review folded in: retry the stamp-aware assessment like the live one; residual write-failure case recorded in Requirement 3; transition note and CHANGELOG section named | readiness reviewer F1-F3 |
| 2026-10-04 | Planned from the 1.29.0+puha field report | `_record_setup_baseline` returns the live result on the environment-differs and `stamp=False` paths; `setup_readiness.assess_setup` stamp comparison yields `setup_inputs_changed` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-04 | Report the stamp-aware assessment instead of inventing a `setup_baseline_not_recorded` reason | it is exactly what `index_health` reports afterwards, so the summary and later checks cannot disagree, and its command already names `wf setup --root` | a new synthetic reason code (a second vocabulary for the same state) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The extra assessment is slow or transient | it runs only on no-stamp paths, through the same bounded transient retry; a persistent `indeterminate` still names `wf setup --root`, which is honest |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
