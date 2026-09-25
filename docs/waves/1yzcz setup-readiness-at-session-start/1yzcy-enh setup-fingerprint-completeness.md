# Setup Fingerprint Completeness

Change ID: `1yzcy-enh setup-fingerprint-completeness`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-24
Wave: `1yzcz setup-readiness-at-session-start`

## Rationale

The advisory setup stamp `.wavefoundry/index/setup-state.json` (wave `1y3og`, shipped in 1.25.0, gitignored with the rest of `.wavefoundry/index/`) lets the readiness assessment report `setup_inputs_changed` after a pulled framework update. Three defects make that signal missing or wrong:

1. **Setup's own stamp never matches a fresh check (live in 1.25.0 and 1.26.0).** Ordinary setup calls `setup_index.main` in-process; on every core index path `report_embedding_provider_decision` sets `os.environ[SETUP_SELECTED_ENV]` (`WAVEFOUNDRY_EMBED_PROVIDER_SELECTED`, a process-scoped setup handoff), and `write_setup_stamp` later records `_environment_identity()`, whose variables come from `ENV_KEYS` and include that variable. Every fresh checker (terminal `wf setup --check`, MCP startup, the monitor) has it unset, so it reports `setup_inputs_changed` after every successful setup, and rerunning setup rewrites the same mismatch. Readiness lanes reproduced this on the `SetupReadinessTests` fixture (write with the variable set, assess with it unset: `action_required`, `['setup_inputs_changed']`). Existing tests miss it because they mock `write_setup_stamp` or write under a clean environment.
2. **The stamp compares launch-process details.** `_environment_identity` also compares the interpreter path, full version string, prefix, ABI flags, `PYTHONPATH` and `VIRTUAL_ENV`. A checker launched differently from setup (an agent host started from an activated shell, a GUI host with a different `PATH`) reports changed inputs although nothing setup produces changed. Interpreter compatibility is already judged live by `environment_incompatible` and `dependencies_missing`.
3. **Most installs have no stamp.** Only ordinary setup writes it (`setup_wavefoundry.py`, the `write_setup_stamp` call after reconciliation completes); `wf upgrade` never does. An upgrade-only install, and this repository (probe 2026-09-24), have none, so the "inputs changed" signal is silent there.

The stamp is advisory by design ("Stamp comparison can reveal an update, but cannot authorize readiness", in `assess_setup`); live checks decide readiness. That is what makes writing it from a live `ready` assessment safe. The session-start hook (change `1yzcx-enh session-start-setup-readiness-hook`) surfaces this signal to the agent, so it must be accurate first.

## Requirements

1. **Compared environment projection.** Stamp comparison projects both the stored and the current environment to: the resolved tool environment path, the Python `major.minor` version (parsed from the stored `python[1]` version string for stamps written before this change), and the operator-controlled variables `REQUESTED_PROVIDER_ENV` (`WAVEFOUNDRY_EMBED_PROVIDER`) and `WAVEFOUNDRY_DISABLE_RERANKER`. `SETUP_SELECTED_ENV`, the interpreter path, full version string, prefix, ABI flags, `PYTHONPATH` and `VIRTUAL_ENV` are still recorded for diagnosis but not compared. `ENV_KEYS`, the stamp payload shape and `SCHEMA_VERSION` are unchanged, so existing stamps stay valid and are judged by the projection. `assessment_signature` is unchanged.
2. **Provenance.** `write_setup_stamp(root, *, provenance="setup", identity=None, exclusive=False)` records a `provenance` field (`setup`, `upgrade` or `adopted`), ignored by comparison. When `identity` is given, the stamp records those source hashes and the write is refused (`ObservationError`) if a fresh `capture_loaded_identity()` differs, so a source change between assessment and write is never recorded as the baseline. When `exclusive` is true, the stamp is published create-only (link the fsynced temporary file to the final name; fail if it exists) and an existing stamp is never replaced. Setup's existing call is unchanged (`write_setup_stamp(repo_root)`). The docstring states the three writers.
3. **`use_stamp`.** `assess_setup` gains a keyword `use_stamp: bool = True`. With `False` it skips only the stamp comparison block; every live check runs unchanged.
4. **Upgrade refresh.** In `upgrade_wavefoundry.phase_cleanup`, on the success path after `upgrade_lib.remove_upgrade_lock(root)` and `_ensure_lifecycle_policy_backstop(root)` and before `_print_operator_summary`, when there is no failed phase and `index_update_failed` is false: capture the source identity, call `assess_setup(root, use_stamp=False)`, and when `ready` write the stamp with provenance `upgrade` and that identity, replacing an existing stamp unless the existing readable stamp's projected environment differs from the current one (an operator environment change the live checks cannot see is not hidden). The cleanup log gains one prose line (not a summary-sentinel key): baseline recorded; or not recorded with `wf setup` named for `action_required` and `wf setup --check` named for `indeterminate`. Any exception from this step is caught and logged as a warning; it never fails the upgrade. `phase_cleanup` runs only in the standalone `--cleanup` process on the new code, so the old-code window does not apply.
5. **MCP startup adoption.** In `server.main`, after the `--dry-run` early return and before stdio transport configuration, when the startup assessment is `ready` and no readable current-schema stamp exists (absent, unparseable, or a different `schema_version`), write the stamp with provenance `adopted`, `identity=_SETUP_LOADED_IDENTITY` and `exclusive=True`. It never replaces a readable current-schema stamp. `OSError` and `ValueError` (which covers `ObservationError` and JSON/TOML decode errors from a configuration read racing the write) are caught; at most one stderr line; startup is never affected. The module-level `__main__` assessment is not the adoption site.
6. **Read-only paths stay read-only.** `wf setup --check`, `assess_setup`, the background monitor and the session-start hook never write the stamp.
7. **Docs.** Update every statement that only ordinary setup writes the stamp or that the startup assessment writes nothing: `docs/architecture/domain-map.md` (assessor paragraph plus an Interaction Edges row naming the three writers), `docs/architecture/data-and-control-flow.md`, `docs/contributing/build-and-verification.md`, `docs/specs/mcp-tool-surface.md` ("Setup readiness notices"), and the `write_setup_stamp` docstring. Changelog: a Fixed bullet for defect 1 and an Added bullet for writers and projection, with an operator note that upgraded installs gain a baseline so `wf setup --check` can begin reporting `setup_inputs_changed` after a later pull.

## Scope

**Problem statement:** setup's own fingerprint never matches a fresh check, the comparison includes launch-process details, and most installs have no fingerprint, so the "framework inputs changed" signal is wrong where it exists and missing where it matters.

**In scope:**

- `setup_readiness.py`: projection, provenance, identity-guarded and create-only writes, `use_stamp`.
- Upgrade cleanup refresh; MCP startup adoption.
- Tests, docs and changelog listed above.

**Out of scope:**

- The session-start hook (change `1yzcx-enh session-start-setup-readiness-hook`).
- Any change to live readiness checks, reason codes, exit codes or `assessment_signature`.
- Writing the stamp from setup's selected-work paths, the check, the monitor or the hook.

## Acceptance Criteria

- [x] AC-1: Projection: identities differing only in `SETUP_SELECTED_ENV`, interpreter path, full version string, prefix, ABI flags, `PYTHONPATH` or `VIRTUAL_ENV` compare equal; a difference in tool environment path, Python `major.minor`, `WAVEFOUNDRY_EMBED_PROVIDER` or `WAVEFOUNDRY_DISABLE_RERANKER` compares unequal; a stamp in the pre-change format compares by the same rule.
- [x] AC-2: Real-order convergence: on a ready fixture, run the real `setup_index.report_embedding_provider_decision` (provider probe patched), then `write_setup_stamp`, then `assess_setup` in a fresh subprocess with a clean environment that still carries `WAVEFOUNDRY_TOOL_VENV` for the AC-6 fixture: the result is `ready`. With the pre-change comparison restored as a mutant, the same test reports `setup_inputs_changed`.
- [x] AC-3: `assess_setup(root, use_stamp=False)` on a fixture whose stamp reports changed inputs returns the live result without `setup_inputs_changed`; with the default it still reports it.
- [x] AC-4: Upgrade cleanup through the real `phase_cleanup` path (existing `--cleanup` harness) on a ready fixture writes a stamp with provenance `upgrade`, replacing an older stamp; it writes nothing when the assessment is not ready, when a phase failed, when `index_update_failed` is true, or when the prior readable stamp's projected environment differs; the log names `wf setup` or `wf setup --check` accordingly; an exception from the step does not fail cleanup; the stamp is written only after the upgrade lock is removed.
- [x] AC-5: MCP adoption through `server.main` with `build_server` and the transport stubbed: a ready fixture with no stamp gains one with provenance `adopted`; a readable current-schema stamp is never rewritten; a not-ready startup and `--dry-run` write nothing; a source change between assessment and write writes nothing; a create-only race with an existing stamp leaves the existing stamp intact.
- [x] AC-6: After adoption on a subprocess-ready fixture (the fixture's own scripts copy, real dist-info metadata for the whole `_dependencies` census including `GPU_ACCEL_IMPORTS` and extras such as `socksio`, a fake tool environment via `WAVEFOUNDRY_TOOL_VENV`, the `SetupReadinessTests` database, and a rendered `.mcp.json`), the fixture's own `wf setup --check` in a subprocess returns ready, and after a framework-source edit returns `setup_inputs_changed`.
- [x] AC-7: `wf setup --check` never writes the stamp (the file stays absent after a check on a ready fixture).
- [x] AC-8: The listed docs and changelog are updated; the documents this change authors or edits validate, and the change's suites and every test it adds pass.

## Tasks

- [x] Projection, provenance, identity guard, create-only publish and `use_stamp` in `setup_readiness.py`.
- [x] Upgrade cleanup refresh and log line.
- [x] MCP startup adoption in `server.main`.
- [x] The subprocess-ready fixture and tests for AC-1 to AC-7, with mutants recorded in wave evidence.
- [x] Docs and changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Stamp, upgrade and startup changes with tests | implementer | readiness | Lands before the hook change uses `setup_readiness.py` |
| Docs | implementer | code | |
| Verification | code, qa, security, architecture, release, docs-contract reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/domain-map.md`, `docs/architecture/data-and-control-flow.md`, `docs/contributing/build-and-verification.md`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/architecture/domain-map.md` (assessor paragraph; Interaction Edges row for the stamp writers) and `docs/architecture/data-and-control-flow.md`. The stamp stays advisory and is still not recovery or publication authority; `assess_setup` still owns no mutation (the writes are separate calls in upgrade cleanup and `server.main`). No ADR exists for the stamp and none is needed.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes false "inputs changed" reports |
| AC-2 | required | Proves the live 1.25/1.26 defect is fixed on the real setup order |
| AC-3 | required | Upgrade must judge readiness without its own stale stamp |
| AC-4 | required | Covers upgrade-only installs |
| AC-5 | required | Covers installs with no stamp; must never erase a signal |
| AC-6 | required | End-to-end proof the signal works after adoption |
| AC-7 | required | Keeps the check read-only (`1y3hc` contract) |
| AC-8 | required | Docs currently state the opposite |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-24 | Planned. Probe: this repository has no stamp; ambient `PYTHONPATH` or the venv interpreter changes the recorded environment. The probe did not run `setup_index.main`, so it missed defect 1 | Environment probe in session scratch |
| 2026-09-24 | Readiness round 1: all three lane groups blocked on the `SETUP_SELECTED_ENV` mismatch (reproduced by the code lane) and architecture on the upgrade write site; one bounded repair applied (projection drops the setup handoff variable, real-order AC, `phase_cleanup` site after lock removal, identity-guarded and create-only adoption in `server.main`, subprocess-ready fixture, docs census extended, 1y3hc supersession recorded) | readiness-review.md |
| 2026-09-24 | Implemented: `projected_environment`, `COMPARED_ENV_KEYS`, `read_setup_stamp`, `write_setup_stamp(provenance, identity, exclusive)`, `adopt_setup_stamp`, `assess_setup(use_stamp)` in `setup_readiness.py`; `_record_setup_baseline` in `upgrade_wavefoundry.phase_cleanup` after lock removal and the lifecycle backstop; `_adopt_setup_baseline` in `server.main` after the dry-run return, gated on a ready status. Deviation from Requirement 2/5 wording: adoption publishes create-only when the stamp is absent and replaces an unreadable or other-schema file (a create-only publish cannot replace it); a readable current-schema stamp is never replaced. New `tests/setup_ready_fixture.py` (subprocess-ready fixture) reused by the hook tests; tests in `test_setup_readiness.py`, `test_setup_stamp_writers.py`, `test_upgrade_wavefoundry.PhaseCleanupSetupBaselineTests`; 17 mutants in evidence/mutants.py all killed (a duplicate-call lock-order mutant was equivalent and was replaced by a move). Docs: domain-map (paragraph and edge row), data-and-control-flow, build-and-verification, mcp-tool-surface, CHANGELOG Fixed and Added. Gapfill: code reads by shell over anchors verified during readiness | evidence/mutants.py |
| 2026-09-24 | Delivery repair DEL-STAMP-WRITER-DOCS and non-blocking notes: docs state setup writes after reconciliation and adoption is create-only only when absent; `wf setup` guidance after config edits (RT-DEL-3) in mcp-tool-surface; cleanup logs the skipped baseline when the index update failed (QA-DEL-4); tests for adoption-before-transport ordering (QA-DEL-1), other-schema adoption (QA-DEL-2), upgrade identity guard (QA-DEL-3/RT-DEL-2); readiness tests independent of the runner's pinned provider environment; identity-comparison census updated for the two new comparisons; five mutants added to evidence. Requirement 2/5 `exclusive=True` wording stays superseded by the recorded adoption deviation | tests/test_setup_stamp_writers.py; tests/test_upgrade_wavefoundry.py |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-24 | Write the stamp from a live ready assessment at upgrade cleanup and adopt a missing one at MCP startup | The stamp is advisory and live checks gate readiness; covers upgrade-only and legacy installs with no operator step | Ask the operator to run `wf setup` once; let the check or hook write it (breaks the read-only contract) |
| 2026-09-24 | Compare only operator-controlled, setup-relevant environment fields | `SETUP_SELECTED_ENV` is a setup-internal handoff that makes every setup stamp mismatch; launch details differ between terminal and host without any setup-relevant change | Snapshot `ENV_KEYS` before setup mutates them (keeps comparing launch details) |
| 2026-09-24 | Supersede `1y3hc` Requirement 11 ("written only by successful ordinary setup") and the startup no-new-cache-file clause of its AC-8 | Adoption and upgrade refresh are new writers by design | Keep setup as the only writer (leaves most installs without a stamp) |

## Risks

| Risk | Mitigation |
| --- | --- |
| First pull after this ships is adopted as the baseline on a machine that never ran setup or upgrade, so that one update is not reported | Accepted and documented; live checks still gate readiness, and later pulls are reported |
| Upgrade cleanup often sees the post-upgrade reindex and records no baseline, so the next session reports `setup_inputs_changed` against the pre-upgrade stamp | Accepted: running `wf setup` clears it; the cleanup log says so |
| Upgrade refresh with `use_stamp=False` records an operator configuration change the live checks cannot see | Environment changes are guarded; configuration changes are accepted and documented |
| Concurrent adopters or a source change mid-startup | Create-only publish; identity guard |
| Filesystems without hard links (for example FAT) make the create-only publish raise `OSError`, so adoption never writes there | Accepted: caught as one stderr line; setup and upgrade still write the stamp |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
