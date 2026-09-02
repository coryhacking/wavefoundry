# Advisory-First Shipping for New Blocking Sensors

Change ID: `1wujs-enh advisory-first-blocking-sensors`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-01
Wave: 1wuju review-churn-and-evaluator-baseline

## Rationale

The AC-locality sensor shipped in `1wur7` as a blocking `docs-lint` error on
day one. Because it is a prose heuristic, every unpinned alternation member
was a potential hard stop on a compliant criterion, which is why five review
rounds concentrated on it, and a consuming repository that upgrades while
holding an activated carrier wave halts at the upgrade's docs gate. A sensor
with no field data should not be able to block anyone. The framework has a
warnings channel (`wave_lint_lib/cli.py` prints `WARNING:` lines and returns
0; `run_validate` collects them; `wf_validate_docs` emits `docs_lint_warning`),
used today by the file-size guard, the factor surface, and the design-system
validators, but no wave-document validator in `wave_validators.py` uses it,
only `wf_validate_docs` renders the warnings as diagnostics, and nothing
records a sensor's polarity or when it may flip.

## Requirements

1. `wave_lint_lib` SHALL carry a sensor polarity registry: sensor id, polarity (`advisory` or `blocking`), and the wave that introduced the sensor (the shipping release is unknown at authoring, so the wave id is the durable key). `check_wave_docs` SHALL gain a warnings sink, wired at all three `wave_lint_lib/cli.py` call sites (incremental changed docs, changed event-wave docs, full scan), so an advisory sensor's findings reach the existing `WARNING:` channel with the same message text and lint passes with them present. Every lifecycle caller of `run_validate` that renders `errors` as `docs_lint_error` (prepare, review, close, audit, and the others readiness RT-RDY-5 enumerated) SHALL also render `warnings` as `docs_lint_warning` diagnostics carrying `advisory: true`, the flag `docs/specs/mcp-tool-surface.md` defines as non-blocking, so an advisory finding is visible at every gate and blocks none.
2. The AC-locality sensor (`_check_ac_asserts_repository_state`) SHALL be the first registrant, registered `advisory` with `introduced_wave: 1wur7`; the flip to `blocking` is a separate, recorded change once field data exists. This reverses the `1wur7` REL-DEL-3 polarity decision on the question of WHEN, not whether (Decision Log row below, operator-approved); the one-line rewrite the diagnostic supplies is unchanged.
3. Seed `170-plan-feature` SHALL state the advisory-first rule for any new docs-lint sensor (ship advisory, flip in a recorded change with the field data that justified it) and its existing "mechanically enforced ... blocking error" paragraph SHALL be corrected to the registered polarity, with `docs/prompts/plan-feature.prompt.md` reconciled (its line-37 tail loses "blocking"); `docs/contributing/change-workflow.md` ("a blocking error") SHALL be corrected the same way. Seed `190-finalize-feature` SHALL carry one close-side sentence (advisory findings are review notes at close), and the gate contract itself (advisory findings never block Prepare, Review, or Close) SHALL be stated in `docs/specs/mcp-tool-surface.md` under the `wf_validate_docs` tool detail, which is where gate behaviour is documented (readiness DOCS-RDY-6).
4. `CHANGELOG.md` `## [Unreleased]` SHALL announce the polarity registry, the AC-locality sensor's advisory status, and the planned flip; its three sentences that state the sensor blocks ("`docs-lint` enforces it as a blocking error", the "Upgrading with an open wave" halt at `phase_docs_gate`, and the `resume_after_gate` instruction) SHALL be corrected so the upgrade docs gate no longer halts on that sensor.
5. The release checklist SHALL surface the registry: `docs/prompts/package-wavefoundry.prompt.md` gains a step that lists every registry entry still `advisory` with its introducing wave so the operator decides each flip at release time (readiness RT-RDY-8: a mitigation with no deliverable is not a mitigation).

## Scope

**Problem statement:** New heuristic sensors go blocking with no field data and no recorded flip, which turns every miss into rework and can halt a consumer's upgrade.

**In scope:**

- The polarity registry and the warnings routing in `docs_lint` and `wave_lint_lib`.
- Registering the AC-locality sensor as advisory.
- Seed `170` and `190` text, the reconciled prompt surfaces, `docs/contributing/change-workflow.md`, `docs/specs/mcp-tool-surface.md`, the package prompt, and the CHANGELOG paragraphs.
- The `docs_lint_warning` rendering at every lifecycle gate caller of `run_validate`, with `advisory: true`.

**Out of scope:**

- Changing any sensor's matching behaviour.
- Flipping the AC-locality sensor to blocking (a later change).
- Registering the pre-existing blocking validators (they have field data; they stay blocking by default).

## Acceptance Criteria

- [x] AC-1: A sensor registered `advisory` reports its findings as warnings and lint passes (`run_validate` returns `passed: true` with a non-empty `warnings`), the same sensor registered `blocking` fails lint, and a Prepare dry-run on a scratch wave carrying the finding returns a `docs_lint_warning` diagnostic with `advisory: true` and no blocking diagnostic; each outcome is pinned by a fixture that flips when only the registry entry flips.
- [x] AC-2: The AC-locality sensor is registered advisory, and a scratch wave carrying a repository-wide criterion flipped to `active` produces a warning naming the criterion and passes lint; the pin fails if the registration is removed.
- [x] AC-3: Seed `170` states the advisory-first rule and no longer calls the sensor blocking, seed `190` carries the close-side sentence, `docs/specs/mcp-tool-surface.md` states the gate contract, and `change-workflow.md` and the plan-feature prompt are corrected; the seed sentences are pinned by `assertIn` tests.
- [x] AC-5: The package prompt lists advisory registry entries with their introducing wave, pinned by an `assertIn` test.
- [x] AC-4: The tests this change adds pass, the documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the polarity registry to `wave_lint_lib` and the warnings routing at the sensor call site.
- [x] Register the AC-locality sensor advisory; adjust its existing fixture tests from error to warning.
- [x] Wire `docs_lint_warning` with `advisory: true` at every lifecycle gate caller of `run_validate`.
- [x] Seed `170` and `190` text with the gate opened and closed; reconcile the prompt surfaces, `change-workflow.md`, the tool-surface spec, and the package prompt.
- [x] CHANGELOG paragraphs, including the three upgrade-day sentences.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Registry and routing | implementer | — | Warnings channel already exists |
| Sensor registration | implementer | Registry and routing | Fixture polarity flips |
| Seeds and CHANGELOG | implementer | Sensor registration | Gate around seed edits |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`, `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`, `.wavefoundry/framework/seeds/190-finalize-feature.prompt.md`
- `docs/prompts/plan-feature.prompt.md`, `docs/prompts/close-wave.prompt.md`, `docs/prompts/package-wavefoundry.prompt.md`, `docs/contributing/change-workflow.md`, `docs/specs/mcp-tool-surface.md`
- The root `CHANGELOG.md` Unreleased section (a root-level file cannot be declared as a path; it is named here in prose).

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` (docs-lint sensor polarity)

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The registry is the mechanism; both polarities must be proven. |
| AC-2 | required | The first registrant is the reason the change exists. |
| AC-3 | required | The rule must reach planners in every target repository. |
| AC-4 | required | The replacement shape, applied to itself. |
| AC-5 | important | The flip is decided at release; the listing is what makes the decision visible. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-01 | AC on the change's own evidence, the replacement shape applied to itself: the tests this change adds pass, the documents it authors or edits validate (`wf_validate_docs` green), and the coordinator's full run on the implemented tree shows no failure elsewhere (8,026 tests across 69 files, all green, receipt `ok`). | `full_suite_1wuju2.log` in session scratch; `.wavefoundry/framework/test-cache.json` 8,026 ok. |
| 2026-09-01 | Implemented. `SENSOR_POLARITY_REGISTRY` in `wave_lint_lib/constants.py` (first entry `ac_asserts_repository_state`, advisory, introduced `1wur7`); `_route_sensor_findings` in `wave_validators.py` delivers a registered sensor's findings to the `warnings` sink `check_wave_docs` now accepts, with the message text kept and a suffix naming the sensor and its wave; all three `cli.py` call sites pass the sink; `_docs_lint_warning_diagnostics` in `server_impl.py` renders `warnings` as `docs_lint_warning` with `advisory: true` at `wf_audit`, `wf_validate_docs`, `wf_prepare_wave`, the review readiness phase, and the shared delivery evaluator that serves `wf_review_wave` and `wf_close_wave` (`wf_audit_install` is untouched: install audits carry no wave documents; withdrawn in delivery round 1, ARCH-DEL-2 row below: the install audit runs the full-corpus lint and now renders the warnings too). The advisory-site census guard `test_advisory_tags_appear_only_at_the_sanctioned_sites` gained the two new sites. Landing rule applied, six scratch mutants each fail a named test: routing advisory findings to failures, removing the registration, the full-scan CLI passing no sink, the helper dropping `advisory: true`, the prepare gate dropping the warnings render, the shared delivery gate dropping it. Five fixture tests flipped from exit 1 to exit 0 with the `WARNING:` line asserted; new `SensorPolarityRegistryTests` (registry flips outcome in-process; registration present; no-sink caller never fails) and gate pins in the lifecycle tests. Seed 170 rewritten (registered polarity, advisory-first rule), seed 190 guardrail, prompts, `change-workflow.md`, the tool-surface spec, the package prompt step, the CHANGELOG (three upgrade-day sentences corrected, new registry bullet), and a `testing-architecture.md` section; pinned by `AdvisoryFirstRulePinTests`. | `test_server_tools_lifecycle.py` 527 OK; `test_docs_lint.py` subset 12 OK, full file run recorded at the wave's suite run; scratch mutants under session scratch `mut9`; `wf_validate_docs` green. |
| 2026-09-01 | Delivery round 1. CODE-DEL-1 / ARCH-DEL-1: `wf_close_wave` keyed its early error return on list non-emptiness, so an advisory `docs_lint_warning` blocked the close; the predicate now ignores `advisory: true` entries and the success envelope carries them, pinned by `test_advisory_lint_warning_never_blocks_review_or_close` (closable legacy fixture: review `ok`, close `dry_run`, one advisory diagnostic each), which fails on the pre-repair predicate. ARCH-DEL-2: `wf_audit_install` renders the warnings on every envelope (the earlier "carry no wave documents" rationale was false: the install audit runs the full-corpus lint, `docs/waves` included); the spec and `testing-architecture.md` name it. Landing-rule pins added for the incremental changed-docs CLI sink (`test_incremental_changed_wave_record_routes_an_advisory_finding_to_warnings`; the AC sensors run from the wave-record branch, so the changed path is `wave.md`), the changed-event-wave sink (`test_incremental_changed_ledger_revalidates_the_owning_wave_through_the_sink`, a top-level copy of the fixture wave with an `events.jsonl`-only change), the readiness-phase render (`review_prepare` subtest), and the unregistered-sensor branch (`test_an_unregistered_sensor_stays_a_failure`). `SENSOR_POLARITIES` is now load-bearing: the router raises `ValueError` on an unknown polarity (`test_an_unknown_polarity_fails_loudly`). DOCS-DEL-1 / QA-DEL-1: the sensor docstring and the allowlist comment no longer call the polarity blocking; the sanctioned-site census message says nine sites. | targeted `test_server_tools_lifecycle.py` and `test_docs_lint.py` sets; `wf_validate_docs`. |
| 2026-09-01 | Landing rule, delivery round 1: seven scratch-copy mutants under session scratch `mut10`, each caught by its named test on an otherwise green base: the close predicate restored to list non-emptiness (`test_advisory_lint_warning_never_blocks_review_or_close`); the install-audit helper call replaced by an empty list (`test_advisory_lint_warning_is_rendered_non_blocking_at_the_install_audit`); the readiness-phase render deleted (`test_advisory_lint_warnings_reach_prepare_review_and_close_as_non_blocking`, `review_prepare`); the warnings sink dropped at the incremental changed-docs site (`test_incremental_changed_wave_record_routes_an_advisory_finding_to_warnings`) and at the changed-event-wave site (`test_incremental_changed_ledger_revalidates_the_owning_wave_through_the_sink`); unregistered sensors routed to warnings (`test_an_unregistered_sensor_stays_a_failure`); the polarity validation removed (`test_an_unknown_polarity_fails_loudly`). | `mut10_run.py` log: 13 of 13 caught. |
| 2026-09-01 | Delivery round 2. QA-DEL-2 (found by the qa lane's replacement-defect probe): a `docs_lint.py` crash (non-zero exit, no `ERROR:` line, which the new registry `ValueError` now produces on a misspelled polarity) reached every gate as passed-false-with-no-errors and the diagnostics-keyed gates let it through. `run_validate` and `run_validate_changed` now synthesize one `ERROR: docs-lint exited <rc> without a lint verdict; <last line>` entry (mirroring the timeout branch), and `wf_audit_install` routes entries carrying that prefix past its expected-absence classifier. Pins: `test_run_validate_synthesizes_an_error_when_lint_exits_without_a_verdict`, `test_run_validate_changed_synthesizes_the_same_error`, `test_a_lint_crash_without_a_verdict_blocks_every_gate` (validate, prepare, review both phases, close all `error` with a `docs_lint_error` naming the cause, derived from the real parser over the crashed subprocess shape), `test_a_verdict_gap_error_blocks_the_install_audit_even_when_it_quotes_an_absence_marker`. ARCH-RV2-1: the terminal install-audit envelope is pinned by a third subtest. | targeted lifecycle tests; scratch mutants in round 2. |
| 2026-09-01 | Landing rule, delivery round 2: five scratch-copy mutants under session scratch `mut11`, each caught: the `run_validate` synthesis removed (`test_run_validate_synthesizes_an_error_when_lint_exits_without_a_verdict`, and `test_a_lint_crash_without_a_verdict_blocks_every_gate` with five gate subtests); the `run_validate_changed` synthesis removed (`test_run_validate_changed_synthesizes_the_same_error`); the install-audit prefix bypass removed (`test_a_verdict_gap_error_blocks_the_install_audit_even_when_it_quotes_an_absence_marker`); the terminal install-audit envelope carry dropped (`test_advisory_lint_warning_is_rendered_non_blocking_at_the_install_audit`, terminal subtest). | `mut11_run.py` log: 12 of 12 caught. |
| 2026-09-01 | Delivery round 3. CODE-DEL-3 (found by the full suite, not by a targeted set): the synthesized verdict-gap cause quoted the crash line verbatim, and a `PermissionError` traceback carries the absolute repository path, breaking the `1uu9z` no-path-leak contract at prepare and close; `_strip_repository_root` now renders the repository root repo-relative in both its given and resolved spellings (macOS pairs `/var` with `/private/var`), pinned by `test_the_synthesized_cause_never_leaks_the_absolute_repository_path` (both spellings) and the pre-existing `test_no_read_failure_message_leaks_the_absolute_path` on the real subprocess; the sanitizer-removed mutant fails both. DOCS-FIN-1 (docs-contract final pass): the `checked_but_missing` install-audit envelope now carries the advisory warnings too, pinned by a fourth subtest of `test_advisory_lint_warning_is_rendered_non_blocking_at_the_install_audit` on a log with a checked row whose artifact is missing; the carry-dropped mutant fails it. DOCS-FIN-2: the spec's `wf_validate_docs` sentence now says the other gates previously passed the crash through. Review notes carried, not repaired (code lane, low, maybe later): the `1viyu` synthesized-failure branch in `wf_audit_install_response` is now reachable only under a patched lint result; the cause line is uncapped in length; the install-audit gap pin hand-builds the entry rather than deriving it from the parser. Process: `wf_prepare_wave(mode='ready')` gardens the changed docs' metadata dates, which moved the tree fingerprint under the final approval lanes (docs content otherwise unchanged); snapshot after the prepare call. | `full_suite_1wuju3.log` (one failure); targeted lifecycle set 44 OK; scratch `fix12` and `mut13`. |
| 2026-09-01 | Delivery round 3, code lane final pass (CODE-RV4-1): the incremental runner's root pass-through to the sanitizer was the one mechanism of the round-3 delta with no failing test when deleted; `test_the_synthesized_cause_never_leaks_the_absolute_repository_path` now loops over both runners and both root spellings, and the root-dropped mutant at the incremental site fails it on both spellings (scratch `mut14`). Carried, not repaired (low, maybe later): a filesystem-root or relative repository root would mangle the cause line (unreachable through `discover_root`, which resolves every root); `_docs_lint_verdict_gap_error`'s `root` parameter defaults to `None`; the sanitizer and `_read_error_detail` render the same `PermissionError` in two vocabularies, both path-free. | targeted `-k never_leaks` OK; full suite re-run. |
| 2026-09-01 | Drafted from the `1wur7` retrospective: a blocking prose sensor with no field data concentrated five review rounds and halts a consumer's upgrade docs gate. | `1wur7` REL-DEL-3 and REL-DEL-11 records; `1wuui` Progress Log. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-01 | OPERATOR-APPROVED reversal of `1wur7` REL-DEL-3 on timing: the AC-locality sensor is registered advisory. REL-DEL-3 kept blocking polarity and explicitly rejected "advisory for one release"; the new facts are zero field data at that decision, five review rounds in which every unpinned member was a hard stop on a compliant criterion, and the upgrade-day halt for consumers. The flip condition is recorded: field data from at least one release with no false-positive report, decided at the release checklist step Requirement 5 adds. Approved by the operator's instruction to prepare, review, and implement the presented plan, which named this reversal as the operator's decision; the operator may veto at readiness. | The rewrite and the diagnostic are unchanged; only polarity and timing move. | **Keep blocking (REL-DEL-3 as recorded):** every consumer with an activated carrier halts on upgrade day with no field data behind the rule. |
| 2026-09-01 | Advisory-first for NEW sensors only; existing blocking validators keep their polarity. | Existing validators have field data; retro-registering them is churn with no evidence. | **Register every validator:** larger and unmotivated. **No registry, edit the sensor to warn:** loses the recorded flip and the rule. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An advisory sensor is ignored and never flipped. | The registry records the introducing wave and Requirement 5 makes the release checklist list every advisory entry for a decision. |
| Reversing REL-DEL-3 reads as gate shaping. | The rewrite and the diagnostic are unchanged; only the polarity and its timing move, recorded as an operator decision. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
