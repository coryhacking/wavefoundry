# Setup readiness: ignore a source-only stamp mismatch

Change ID: `212b9-bug setup-readiness-source-only-stamp-mismatch`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-19
Wave: 212yk setup-readiness-source-only-stamp

## Rationale

`setup_readiness.assess_setup` reports `setup_inputs_changed` (status `action_required`, action `wf setup`) whenever the advisory stamp `.wavefoundry/index/setup-state.json` differs from the current hashes of the 31 framework scripts in `SOURCE_FILES`. In this framework source repository those scripts change in almost every wave (`wf_server/server_impl.py`, `render_agent_surfaces.py`, `render_platform_surfaces.py`), so every tool response carries a `setup_not_ready` diagnostic and the agent stops to ask the operator to run setup. On 2026-10-19 the operator ran `wf setup` after waves 2136r, 2136s and 2124l: every live check had already passed, no dependency was installed, the index was already current and no rendered file changed. Setup's only effect was rewriting the stamp. The operator reported that running setup when nothing is needed is the recurring cost.

In a target repository the framework scripts change only through an upgrade or a pull of an upgrade, and both also change `.wavefoundry/framework/VERSION`, which the stamp's configuration identity already compares.

## Product Intent

Operators and agents working in a checkout whose framework scripts were edited, with the framework `VERSION`, the setup configuration, the launch surfaces and the setup-relevant environment unchanged and every live check passing, no longer see `setup_not_ready` or a request to run `wf setup`. A `VERSION` change, a configuration or surface change, an environment change, or any failing live check still requests setup exactly as before. AC-1 and AC-2 together test the intent.

## Requirements

1. In `assess_setup`, when the stamp is readable and current-schema, its configuration identity (which includes the framework `VERSION` hash) and projected environment equal the current ones, and only the `sources` map differs, the comparison adds no `setup_inputs_changed` reason and no setup action. It appends one line to `limitations` stating that framework sources differ from the setup stamp at the same framework version and that live checks decided readiness.
2. When the configuration identity or the projected environment differs, `setup_inputs_changed` is reported exactly as today, whether or not sources also differ.
3. Every live check is unchanged, and no stamp writer, writer condition or read-only guarantee changes (`wf setup --check`, the monitor and the session-start hook still never write the stamp).
4. Platform behaviour: the comparison is dictionary equality over hashes already computed, so behaviour is identical on Windows, macOS, Linux and WSL2; no path, process or filesystem behaviour changes.

## Scope

**Problem statement:** a source-only stamp mismatch requests a setup run that has nothing to do.

**In scope:**

- The stamp comparison block in `setup_readiness.assess_setup`.
- Tests in `test_setup_readiness.py`, `test_setup_stamp_writers.py` and `test_upgrade_wavefoundry.py` whose fixtures assert `setup_inputs_changed` from a source-only change; each keeps its purpose by also changing `VERSION` or the configuration where the scenario models a pull or upgrade.
- `test_sqlite_storage_migration.test_direct_identity_equalities_are_only_reviewed_boundaries` pins the three stamp comparison expressions in `assess_setup`; they stay verbatim, or that census is updated in the same edit.
- The stamp prose in `docs/contributing/build-and-verification.md`, `docs/architecture/domain-map.md` and `docs/specs/mcp-tool-surface.md` where it states what the stamp compares; one CHANGELOG Fixed bullet.

**Out of scope:**

- New live checks (model bundle materialization, `.wavefoundry/bin/` launcher bytes). See Decision Log.
- Refreshing the stamp from MCP startup or any read-only path.
- New MCP tools: the assessment is already exposed through `index_health().setup_readiness` and the `setup_not_ready` diagnostic on every tool.
- The startup install (wave `1zfd9`) reason exclusions.

## Acceptance Criteria

- [x] AC-1: In the in-process `SetupReadinessTests` fixture, a stamp written by `write_setup_stamp` whose `sources` map is then rewritten for one entry yields `status == "ready"`, no `setup_inputs_changed` reason, no actions, and the new limitation line. In the fresh-process fixture (`test_setup_stamp_writers.test_adopted_baseline_reports_a_later_framework_change`), a real on-disk edit to a `SOURCE_FILES` script with `VERSION` unchanged yields the same result. With the source-only rule removed as a mutant, both tests report `setup_inputs_changed`.
- [x] AC-2: In the in-process fixture, the rewritten `sources` entry combined with a `.wavefoundry/framework/VERSION` change, a setup-relevant `docs/workflow-config.json` change, or a projected environment change each still yields `action_required` with `setup_inputs_changed`; a `VERSION` change alone does too.
- [x] AC-3: The existing tests that model a pulled framework update or an outdated upgrade stamp still assert `setup_inputs_changed`, with their fixtures changing `VERSION` or configuration alongside sources (the fresh-process pulled-update test gains a `VERSION` variant that still reports it); the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Split the stamp comparison in `assess_setup` into the source-only case and the existing case.
- [x] Add the in-process AC-1 and AC-2 tests to `test_setup_readiness.py` (rewrite the stamp's `sources`, never the on-disk scripts, since `assess_setup` refuses a target whose scripts differ from the executing assessor); flip `test_setup_stamp_writers.test_adopted_baseline_reports_a_later_framework_change` to expect `ready` with the limitation line and add its `VERSION` variant; adjust the source-only fixtures in `test_upgrade_wavefoundry.py`.
- [x] Run the AC-1 mutant in a scratch copy and record the result in the Progress Log.
- [x] Update the three docs and add the CHANGELOG Fixed bullet.
- [x] Run the touched suites, then the whole suite last.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| comparison-and-tests | implementer | — | `setup_readiness.py` and the three test files |
| docs | implementer | comparison-and-tests | Three docs and CHANGELOG |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`, `.wavefoundry/framework/scripts/tests/test_setup_stamp_writers.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `docs/contributing/build-and-verification.md`, `docs/architecture/domain-map.md`, `docs/specs/mcp-tool-surface.md`
- CHANGELOG.md (root-level file, not a declared target)

## Affected Architecture Docs

`docs/architecture/domain-map.md`: the assessor paragraph states what the stamp compares; add that a source-only difference at an unchanged framework version is reported as a limitation, not a setup request. No boundary, flow or ownership change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The operator-reported false positive |
| AC-2 | required | Must not hide a real pull, upgrade, config or environment change |
| AC-3 | required | Keeps the existing pull and upgrade signals tested |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Delivery review: code, QA, architecture and docs-contract approved delivery, each with independent scratch-copy known-bad probes (QA six mutants, all killed); council delivery recorded (red-team, security-reviewer, no blocker). Red-team ran `setup_wavefoundry.py --check --json` against this repository's real stamp with the on-disk code: `ready`, no reasons or actions, `SOURCE_ONLY_STAMP_LIMITATION` in limitations. Follow-ups, not in scope: N-1 (security) an error computing the live configuration identity (oversized or unreadable `VERSION` or launcher file, malformed `docs/workflow-config.json`) is caught by the stamp block's handler and reported as the stamp-unreadable limitation; pre-existing when sources matched, now also reachable when they differ; computing `_configuration_identity` outside that handler would fix it. Red-team wording note: the renderer gap covers launcher bytes only for an edit that was not re-rendered, since rendered launcher bytes are compared through the configuration identity. Whole suite last: `python3 .wavefoundry/framework/scripts/run_tests.py` ran 11914 tests across 200 files, OK (12 skipped), green receipt written. Only operator signoff remains | Ledger approvals; session scratchpad suite-212yk.txt |
| 2026-10-19 | Implemented. `setup_readiness.assess_setup`: the stamp block now reports `setup_inputs_changed` only for a configuration or projected-environment difference; a sources-only difference appends `SOURCE_ONLY_STAMP_LIMITATION`. The three comparison expressions are unchanged, so the identity-equality census passes untouched. Tests: `test_setup_readiness` `test_source_only_stamp_difference_is_a_limitation_not_a_setup_request` (AC-1 in-process) and `test_source_difference_with_another_input_change_still_requests_setup` (AC-2, VERSION, workflow config and environment, each with and without a source difference); `test_setup_stamp_writers` `test_adopted_baseline_treats_a_source_only_edit_as_a_limitation` (AC-1 fresh-process, real on-disk edit; it carries the AC-1 behaviour under a new name, while `test_adopted_baseline_reports_a_later_framework_change` keeps its name as the VERSION variant); `test_upgrade_wavefoundry.test_unstamped_index_failure_reports_an_outdated_stamp` now also changes the stamp's VERSION hash. Focused run: test_setup_readiness, test_setup_stamp_writers, test_sqlite_storage_migration, test_upgrade_wavefoundry, test_startup_install: 992 tests OK. Mutant (scratch copy, source-only branch restored to `setup_inputs_changed`): both AC-1 tests FAIL, the other 9 stamp-writer tests pass. Docs: domain-map (sentence corrected to name all three comparison inputs), data-and-control-flow (one sentence), build-and-verification (stamp paragraph), CHANGELOG Fixed bullet; `docs/specs/mcp-tool-surface.md` unchanged (docs-contract: its 'a pull also produces' sentence stays true). Gapfill: shell edits and reads for the bounded block and test edits named by the readiness lanes | Focused run output; scratch mutant run |
| 2026-10-19 | Readiness complete: code, QA, architecture and docs-contract approved on receipt `review-policy-7958418157275ac5091b`; security seat no blocker. Security S-1 (non-blocking, recorded here instead of re-readying): the claim that every distribution path changes `VERSION` has one exception, the protocol-bridge interim state (`upgrade_bridge_bootstrap.install` restores the old `VERSION` into the incoming tree; a kill before the feature child writes its upgrade lock leaves new scripts, old `VERSION`, no lock, only `framework/BRIDGE-ROLLBACK.json`). After this change that state reads `ready` with the limitation line; before it, readiness named `wf setup`, which is not the remedy either (rerun the upgrade or roll back). Accepted risk; a live `BRIDGE-ROLLBACK.json` check is deferred as new mechanism. Implementation notes: keep the three comparison expressions verbatim for the identity-equality census; add the limitation only for a readable current-schema stamp; write `VERSION` into fixtures before the stamp, then change it; assert the exact limitation string; `test_upgrade_wavefoundry.test_unstamped_index_failure_reports_an_outdated_stamp` is the upgrade test this change breaks; docs state that the stamp compares sources, the configuration identity (including `VERSION`) and the projected environment, fix the existing domain-map sentence, and add one sentence to `docs/architecture/data-and-control-flow.md` | Ledger approvals; security seat report |
| 2026-10-19 | Readiness red-team RT-1 (blocking): the in-process fixture refuses differing on-disk scripts before the stamp block, so AC-1 could not pass there. Repaired by narrowing AC-1/AC-2 to a rewritten stamp `sources` entry in-process and keeping the real on-disk edit in the fresh-process fixture; also added the identity-equality census test to Scope and widened the accepted renderer gap | Red-team primer, this wave |
| 2026-10-19 | Planned after the operator ran `wf setup` on a ready checkout: `wf setup --check` reported `setup_inputs_changed` only; setup installed nothing, the index build embedded 0 files and `--check` then reported `ready` | Session transcript |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Treat a source-only stamp difference at an unchanged framework `VERSION` as a limitation note, not a setup request | One comparison change; every real distribution path (upgrade, pulled upgrade, release) changes `VERSION`, which the configuration identity already compares, so the target-repo signal is kept | (a) Let MCP startup (`adopt_setup_stamp`) also replace a readable stamp whose only difference is `sources` after a ready assessment, so the stamp self-heals: the reported signal is the same either way, but this widens the diff into `server.main` and the wave `1yzcz` adoption tests and reverses that wave's AC-5 rule that adoption never replaces a readable stamp; the read-side rule is smaller, and its limitation line appears only in the full readiness result (`index_health`, `wf setup --check --json`), not in tool diagnostics. (b) Detect the self-hosting source repository and skip source comparison there: adds a detection mechanism and leaves the same false positive for anyone editing a vendored framework. (c) Split `SOURCE_FILES` into provisioning and runtime subsets: more surface to maintain and each new script needs a classification |
| 2026-10-19 | Accept the gap that a source-only edit to `model_bundle.py` (a `MODEL_SET_VERSION` bump) or to `render_platform_surfaces.py` is no longer flagged when `VERSION` is unchanged. For the renderer this covers every output no live check reads: `.wavefoundry/bin/` launcher bytes, `.claude/settings.json`, the rendered host hooks (`.claude/hooks/`, `.cursor/hooks/`, `.github/hooks/`) and `.wavefoundry/git-hooks/` | Those edits happen in this repository inside a wave that re-renders surfaces, and a model-set change ships with a release that changes `VERSION`; adding live checks for them is new mechanism | Add live model-bundle and launcher-byte checks (deferred until field evidence shows a miss) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A target repository edits or hot-patches framework scripts without a `VERSION` change and needs setup | Live checks still catch dependency, environment, surface entry, configuration and index problems; the limitation line names the source difference |
| An existing test silently loses its pull or upgrade signal | AC-3 requires those fixtures to still assert `setup_inputs_changed` with a `VERSION` or configuration change |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
