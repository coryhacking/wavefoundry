# Delete the upgrade memory compatibility layer and aliases

Change ID: `20vin-debt delete-upgrade-memory-compat-layer`
Change Status: `planned`
Owner: framework maintainer
Status: planned
Last verified: 2026-10-16
Wave: TBD

## Rationale

Wave `20t73 upgrade-memory-gate-removal` (change `20smo-enh`) removed the historical-memory gate from upgrade and setup but kept a compatibility layer in `memory_backfill.py` so that any supported older runner, which executes the installing upgrade, passes through its memory step. It also kept `--resume-after-memory` and the `resume_after_memory` MCP phase as deprecated aliases of `update_index`, and an exit-code-4 tolerance in `upgrade_handlers.py`. That layer exists only for runners that still call the retired gate names. Once no supported runner can call them, the layer, the aliases and the tolerance are dead code that obscures the on-demand memory model.

**Precondition (from 20smo-enh Requirement 4 window boundary):** this change is implementable only when runner protocol 2 has been removed from `upgrade_protocol.SUPPORTED_RUNNER_PROTOCOLS` (protocol 1 leaves no later than protocol 2), or when the installing upgrade provably hands off to the newly extracted runner before its memory step. Elapsed releases alone never satisfy the precondition.

## Requirements

1. **Precondition check first.** Before any edit, confirm from source that `upgrade_protocol.SUPPORTED_RUNNER_PROTOCOLS` no longer lists protocol 2, or that the installing upgrade hands off to the extracted runner before its memory step, and record the evidence in the Progress Log. If neither holds, the change stays parked.
2. **Delete the compatibility layer.** Remove from `memory_backfill.py` the lifecycle entry-path handling (`setup` and `upgrade` runs), `_lifecycle_runs`, `_lifecycle_sync`, `_LIFECYCLE_UNAVAILABLE`, `_advisory_failure`, the advisory wrappers around `sync_inventory`, `run_summary`, `validation_worklist` and `ensure_run`, and the no-op names `reconcile_index_publication`, `complete_index_publication`, `mark_indexed`, `index_publication_scope` and `run_state`, plus the constants `ACTION_REQUIRED_EXIT` and `MAX_CANDIDATES_PER_CALL` when no remaining caller reads them. `memory_cli.py` drops the deprecated `--entry-path` option and `memory_backfill` drops the `entry_path` parameter.
3. **Delete the aliases and tolerance.** Remove `--resume-after-memory` from `upgrade_wavefoundry.py`, the `resume_after_memory` phase mapping from `upgrade_handlers.py` and the `wf_upgrade` docstring, the exit-code-4 tolerance keyed on `legacy_memory_pause`, and the emitter in `repair_ppol_memory_staging.py`. Run an emitter census for the flag and phase across scripts, seeds, prompts and docs before deleting, and retarget every hit.
4. **Legacy recovery predicate.** Decide whether `sqlite_storage_migration.legacy_memory_pause` and `_clear_legacy_memory_checkpoint` can also go: they recover retained locks written by old runners, so they stay unless the same supported-runner boundary proves no such lock can still exist on a supported starting version.
5. **Hooks and fixtures.** Remove `_observe_parent_index_outcome` from `upgrade_extensions.py` when no supported parent runner owns `phase_index_update`; retire the archived-runner fixture and the tests that exercise the compatibility layer; refresh the handler-digest fixture for `wf_upgrade` and `memory_backfill`.
6. **Surfaces.** Delete every `Legacy recovery:` sentence that describes the aliases, update the `wf_upgrade` docstring and prompts, and add one `### Changed` CHANGELOG bullet stating the aliases and tolerance are removed and naming the supported-runner boundary that allowed it.
7. **Platform behaviour.** Deletion only; no new file, lock, path or process primitive. Behaviour is identical on Windows, macOS, Linux and WSL2, including native Windows `wf.cmd upgrade` and `wf.cmd setup`.

## Scope

**Problem statement:** a report-only compatibility layer, two deprecated aliases and an exit-code tolerance remain in the upgrade and memory code solely so that older runners pass through the retired historical-memory gate; they should be deleted once the supported-runner boundary makes them unreachable.

**In scope:**

- `memory_backfill.py`, `memory_cli.py`, `upgrade_wavefoundry.py`, `upgrade_extensions.py`, `upgrade_handlers.py`, `server_impl.py` (docstring), `repair_ppol_memory_staging.py`, `sqlite_storage_migration.py` (predicate decision), the tests and fixtures that exercise the layer, seeds and prompts carrying `Legacy recovery:` sentences, the CHANGELOG.

**Out of scope:**

- The on-demand `memory_backfill` and `memory_validate` tool contracts and the historical-memory report line, which stay.
- Any change to `SUPPORTED_RUNNER_PROTOCOLS` itself; that decision belongs to the release that drops protocol 2.

## Acceptance Criteria

- [ ] AC-1: Progress Log records source evidence that the precondition holds before the first code edit.
- [ ] AC-2: `memory_backfill.py` exposes no lifecycle entry-path handling, advisory wrappers or no-op publication names, and the suite passes with the archived-runner fixture retired.
- [ ] AC-3: `--resume-after-memory` and `resume_after_memory` are refused as unknown flag and phase, and an emitter census over scripts, seeds, prompts and docs finds no remaining emitter.
- [ ] AC-4: No `Legacy recovery:` sentence describing the aliases survives in seeds, prompts or docs, and the CHANGELOG bullet is present.
- [ ] AC-5: Behaviour is stated and unchanged for Windows, macOS, Linux and WSL2.

## Tasks

- [ ] Verify the precondition from `upgrade_protocol.py` and the installing-upgrade handoff and record it.
- [ ] Run the emitter census for the flag, phase and compatibility names.
- [ ] Delete the compatibility layer, aliases and tolerance; retire fixtures and tests.
- [ ] Reconcile seeds and prompts under `seed_edit_allowed`; refresh the handler-digest fixture; add the CHANGELOG bullet.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Precondition and census | Implementer | Wave readiness | No deletion before the precondition is recorded |
| Deletion and surfaces | Same implementer | Precondition and census | Seed gate around seed edits |


## Serialization Points

- `.wavefoundry/framework/scripts/memory_backfill.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/sqlite_storage_migration.py`, `.wavefoundry/framework/scripts/repair_ppol_memory_staging.py`, `.wavefoundry/framework/scripts/memory_cli.py`
- `.wavefoundry/framework/scripts/tests/`, `.wavefoundry/framework/seeds/`, `docs/prompts/`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` (the `Legacy recovery:` sentence in the upgrade flow) and `docs/architecture/testing-architecture.md` (archived-runner fixture retirement). No ADR; the decision was taken in 20smo-enh.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The window boundary is the whole point of the change |
| AC-2 | required | Core deletion |
| AC-3 | required | Saved operator commands must fail loudly, not silently misbehave |
| AC-4 | important | Surface hygiene |
| AC-5 | required | Cross-platform statement is mandatory for every change |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-16 | Minted at the close of wave 20t73 as its follow-on tech-debt change; parked until the Requirement 4 window boundary of 20smo-enh is reached. Not admitted to any wave. | `docs/waves/20t73 upgrade-memory-gate-removal/20smo-enh remove-upgrade-historical-memory-gate.md` Requirement 4 and Decision Log |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-16 | Tie implementation to runner protocol 2 leaving the supported set or a proven runner handoff, never to elapsed releases | A project may skip releases and upgrade directly, so only the supported-runner boundary proves no old runner executes | Delete after one release (rejected in 20t73) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A saved operator command or kit still emits the old flag after deletion | Emitter census before deletion; the flag is refused as unknown with the parser's ordinary error |
| A retained legacy memory lock still exists on a supported starting version | Requirement 4 keeps the recovery predicate unless the boundary proves otherwise |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
