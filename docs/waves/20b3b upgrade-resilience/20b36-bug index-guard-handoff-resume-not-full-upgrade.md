# Index-Guard Handoff Resumes The Upgrade Instead Of Re-Running It

Change ID: `20b36-bug index-guard-handoff-resume-not-full-upgrade`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: 20b3b upgrade-resilience

## Rationale

**Brief.** Goal: when the index guard stops an upgrade and hands the operator a terminal command, that command must continue the recorded upgrade, not start a new full one. Consumer: an operator running the exact recorded command from an external terminal with all hosts stopped. Constraints: old-code window (the command is built by the code that is running), `--confirm-hosts-stopped` stays, Windows, macOS, Linux and WSL2 produce the same argv shape, and a resume command that the resume entry then refuses is worse than the full form, so the full form is the default whenever the recorded state is not provably accepted. Success: the handoff command resumes at index publication without re-taking a fresh lock, re-running preflight, re-rendering surfaces or truncating `upgrade.log`.

**Precondition.** Do not Prepare or Implement this change until wave `20b3a upgrade-failure-surfacing` is implemented, fully delivery-reviewed and PAUSED under the operator-approved sequence. Re-derive every cited line anchor against the post-`20b3a` tree; line numbers in this document are advisory and symbols are the anchors. Re-Prepare these amended plans against that source before activation; all framework code edits require the root Stage Gate and applicable framework-edit authorization. Closure is not required or authorized. This change consumes the CLI resume command helper that `20b34-enh upgrade-cli-resume-and-gap-clear-guidance` introduces; it makes no additional API change to `restart_command` beyond the actual `20b34` contract, which must be read after that change is implemented.

Field report: after the memory step, `index_guard_restart_required` produced a command that was the full upgrade (`--pack ... --confirm-hosts-stopped`). On Windows its Phase 1 re-rendered 21 managed docs and the docs gate then rejected them, so the full command could never pass the gate; the operator had to convert files and resume by hand without `--pack`.

**Verified at HEAD.**

- `enforce_index_guard_handoff` (`upgrade_extensions.py:797-877`) builds the command at line 851 with `migration.restart_command(root, record.get("pack_path"), rebuild)`; `restart_command` (`sqlite_storage_migration.py:801-828`) with the default `entry_path="upgrade"` emits `[python, upgrade_wavefoundry.py, --root R, --pack <pack_path>, --yes, --confirm-hosts-stopped, (--rebuild-storage)]` and never `--update-index`, `--resume-after-memory` or `--resume-after-gate`. `rebuild` there is `ctx.rebuild_storage or migration.rebuild_requested(storage_receipt)` (about line 848); resume contexts always have `ctx.rebuild_storage` false, so only the receipt term matters in a resume run.
- That is the full-upgrade path (`upgrade_wavefoundry.py:6225-6342`): it takes the lifecycle lock, runs preflight, stages the pack, rewrites the lock (6311) and reopens the log with `mode="w"` (6332), truncating the previous log.
- The full path DOES re-render after `_tree_already_at`. Only Phase 0b extraction is skipped (6380-6392). Phase 0c (6448), Phase 1 `phase_surface_rendering` (1931, a `render_platform_surfaces` subprocess), pruning and the docs gate (6513) run unconditionally. Task 1 re-confirms this and records it in the Progress Log.
- `restart_command` has a second caller, `sqlite_storage_migration.py:900` (the storage-receipt handoff, `_pause_for_restart`), which needs the full form with `--pack`. Change `20b34` relies on `restart_command` output staying unchanged.
- The guard can fire from many points: `upgrade_wavefoundry.py` 2701, 2714, 2782, 2832, 2866, 2898, 2937, 2956, 2975 (through `_enforce_index_guard_before_children`) and `upgrade_extensions.py` 990, 2852, 3833. There is no single "index publication" resume point, and the sites are not at one phase: `upgrade_extensions.py:3833` sits in `_post_extract`, after extraction but before surface rendering and the docs gate.
- The resume entries refuse by recorded state. `--resume-after-memory` (`upgrade_wavefoundry.py` about 5645-5690) requires `_memory_gate(lock)` to be non-None (which depends on `memory_backfill_run_id`) and `current_phase` in {`awaiting_memory_validation`, `awaiting_memory_publication`, `memory_resume_preflight`, `index_complete`} (about 5659-5672); anything else exits 1 with "resume is refused". `--update-index` (about 5810-5870) refuses unless the memory gate is `indexed`, and resolves its archive through `_zip_from_lock`. `--resume-after-gate` is at about 6048. They already append to the log (`_open_log(root, mode="a")` at 5646 and 5869); only the full path truncates.
- `--rebuild-storage` is rejected in combination with any resume flag (`upgrade_wavefoundry.py:5499-5503`: "use the retained continuation command with its original --pack").
- `_validate_index_guard_handoff` (`upgrade_extensions.py` about 726-740) checks the package sha against `pack_sha256` and fails with `index_guard_package_changed`. Resume forms omit `--pack` and resolve the archive from the lock `zip_path`, which may be the staged private copy (`_stage_pack_for_consumption`, about 6251).
- `tests/test_index_upgrade_guard.py:171-185` (`test_same_schema_old_host_requires_new_coordinator_and_confirmation`) pins the full-upgrade argv with `assertIn(str(self.package), result['command_argv'])`; `tests/test_server_tools.py:5472` and `:5509` assert only `--confirm-hosts-stopped`.

## Requirements

1. Before code, re-confirm the full path after `_tree_already_at`, every actual guard site and its persisted lock state. Build a fixture table of site, runner/module provenance, persisted `current_phase`, memory run/gate state, unrecovered docs/review gates and selected argv. Consume the actual implemented `20b34` helper; its API is still a dependency, not an assumed interface.
2. Command selection remains at `upgrade_extensions.enforce_index_guard_handoff`, using the incoming code in the old-code window. Use the `20b34` helper when available; stale installed modules or incompatible helper signatures fall back to the existing full form without raising. Do not add another `restart_command` argument or alter its default/storage-receipt caller output. If the actual helper returns display text only, construct the same resume argv from the default argv by removing the pack/rebuild options and inserting the selected flag.
3. Resume requires positively proven post-docs state, no unrecovered review/docs gate and no rebuild, pending storage receipt or `restart_action`. When already inside an accepted update-index or memory-resume entry, preserve that entry's flag if these conditions still hold; otherwise use this conservative table, verified against the actual entries before implementation:

   | Recorded state at the guard | Command form |
   | --- | --- |
   | Valid memory run/gate and persisted phase accepted by `--resume-after-memory`: `awaiting_memory_validation`, `awaiting_memory_publication`, `memory_resume_preflight`, `index_complete` | `--resume-after-memory --yes --confirm-hosts-stopped` |
   | Positively proven post-docs checkpoint, memory absent or `indexed`, and the actual `--update-index` entry accepts it | `--update-index --yes --confirm-hosts-stopped` |
   | Pre-docs `_post_extract`/`preflight`, unknown or unreadable state, unproven phase, rebuild, pending storage receipt or `restart_action` | existing full form with `--pack` |

   The second row must use an explicit phase whitelist derived from actual persisted checkpoints; the handler's broad gate predicate alone is insufficient. A legacy memory checkpoint with phase absent/`preflight`, a run id and no `runner_protocol` can enter the first row only when it is provably the entry's legacy post-docs checkpoint, not a pre-render guard. The full run sets local `current_phase = index_update` but retains persisted `awaiting_memory_validation`; these are different states. Explicitly test a synthetic persisted `index_update` and keep the full default unless post-docs provenance is proven. No `--resume-after-gate` row is added.
4. Rebuild and storage-receipt/restart handoffs retain the full form. Resume argv never contains `--pack` or `--rebuild-storage`, and a guard reached inside a proven `--update-index` or `--resume-after-memory` run regenerates that accepted form without skipping a phase. Existing log append behavior, interpreter selection and console mapping stay unchanged.
5. Operator-selected archive authority: before a pack-backed resumable handoff emits an action, retain the consumed byte-identical archive in one fixed ignored repository-owned slot, `.wavefoundry/cache/upgrade/index-guard-feature.zip`. Current-tree, pre-docs/full-form, rebuild and pending-receipt handoffs do not retain a pack. Temporary staging and the external original are not continuation authorities; do not assume either survives a reboot.
6. `upgrade_extensions` owns retention beside its existing handoff validation, using existing private incoming-module loading and contained-file helpers. Bind one versioned durable-pack proof under `index_guard_handoff`: fixed relative path, SHA256, target, handoff token, resolved root identity and opened regular-file identity. Atomically update the proof, `lock.zip_path`, guard `pack_path` and action through `update_upgrade_lock` while the existing lifecycle/publication transaction is held. Preserve the separate original staged path and `verified_pack_identity` for TMP cleanup; never forge a TMP proof for a cache file.
7. Reject any linked/reparse path component, final link, multiply-linked file, FIFO/device/directory, permission-denied/unresolved path or unrelated occupied slot before reading or changing it. A same-hash file is not owned merely because its bytes match. Reuse only when the existing checkpoint proves the exact path/root/token/target/identity/hash binding. Use exclusive contained staging and publication with target revalidation; do not overwrite/delete foreign contents or emit an unproven resume action on failure. An interrupted publish-before-binding leaves an explicitly diagnosed occupied slot, not guessed ownership.
8. In a fresh process, validate the durable binding's containment, regular-file identity and hash before extension loading or token validation. `_zip_from_lock` must prefer that proven locator and never substitute root archive discovery when a durable binding is present. Changed bytes/identity or malformed/escaped binding refuse. The sole absent-archive exception is cleanup-only finalization of the validated terminal checkpoint in Requirement 10, inspected before archive resolution; it never authorizes ordinary resume or extension loading. Merely adding `--pack` to a resume command is not a solution: the resume resolver does not consume it.
9. Failed/paused index publication, memory validation, host quiescence, storage cleanup or dashboard restart keep the owned archive and checkpoint. Phases 0-4 returning success are not terminal completion while the lock remains. Repeated handoffs reuse the one owned slot; no retry copies, history or broad cache service/sweep.
10. Successful terminal `phase_cleanup` removes only the exact owned durable file after all fatal cleanup guards and storage/dashboard obligations succeed, and before checkpoint removal. Persist a versioned terminal cleanup checkpoint before archive deletion, bound to the existing root/token/target/path/ownership proof and completed fatal obligations. A fresh `--cleanup` inspects that state before resolving or loading the archive: it may finalize only the exact owned file and checkpoint, without rendering/reindexing or loading the deliberately removed archive. If the file still exists, revalidate its full identity/hash binding before deletion; if it is absent, only the valid terminal state permits checkpoint finalization. Missing/malformed terminal state, replaced/foreign files and ordinary resume remain fail-closed. Clean the original staged copy only with its separate TMP proof; leave the external original and unowned files untouched. Archive or checkpoint deletion failure reports nonzero and retains recoverable terminal state; interruption before or after archive deletion has the same cleanup-only retry contract. Reuse existing cleanup states where possible; a late TMP-only `finally` cannot supply this guarantee.
11. Incoming retention works for the supported old-runner fixture; newly extracted code handles continuation and terminal cleanup. Keep old full-form commands and storage restart output accepted. Test actual old-runner cleanup/hook behavior before claiming compatibility; no speculative adapter or unsupported-host cleanup promise.
12. Argv and guards have the same contract on Windows, macOS, Linux and WSL2. Injected Windows reparse/permission fixtures are labeled simulations; a fresh-process lost-TMP test is restart evidence, not a measured reboot qualification.

## Scope

**Problem statement:** The recorded handoff command re-runs the whole upgrade, re-taking the lock, re-running preflight and re-rendering surfaces (which on Windows CRLF checkouts fails the docs gate) and truncating the log.

**In scope:**

- Command selection for the index-guard handoff at the single decision point, from recorded lock state.
- Consuming the `20b34` helper; no change to `restart_command`.
- Updating pinned argv tests only when their actual fixture selects a resume row; preflight/default fixtures keep the full form.
- One contained ignored durable recovery slot, checkpoint proof/resolver validation, terminal cleanup and its retry, with tests of actual callers.
- Recording the verified full-path/persisted-phase trace and honest restart evidence.

**Out of scope:**

- CRLF correctness of the renderer or docs gate (separate change in the windows-crlf-correctness wave).
- Changing the resume flags themselves, or the storage-receipt handoff at `sqlite_storage_migration.py:900`.
- Adding anything to `restart_command` (owned by `20b34`).
- Index build behavior.

## Acceptance Criteria

- [x] AC-1: Every proven resume row emits its accepted resume flag and `--confirm-hosts-stopped`, without `--pack` or `--rebuild-storage`; pack-backed rows resolve the checkpoint-owned durable copy.
- [x] AC-2: Pre-render `_post_extract`/`preflight`, unknown/unreadable/unproven phases, rebuild, pending receipts and restart actions emit the full form. A synthetic tree-not-at-target or persisted `index_update` fixture is labeled and cannot silently skip docs/rendering.
- [x] AC-3: Actual `main` execution of retained resume argv calls neither `write_upgrade_lock` nor `phase_preflight`, appends the log, does not extract/render, and continues index publication.
- [x] AC-4: Enumerate every real guard site and distinguish local `index_update` from persisted `awaiting_memory_validation`; cover the explicit update whitelist and valid legacy memory acceptance. Every selected flag is accepted by its entry; pre-docs and unmapped states remain full form.
- [x] AC-5: The actual post-`20b34` `restart_command` API and default argv are unchanged by this change, including the storage-receipt caller and predecessor tests.
- [x] AC-6: Record the row of each existing pinned fixture. `test_same_schema_old_host_requires_new_coordinator_and_confirmation` keeps the full form when its checkpoint remains preflight; server-tool confirmation assertions remain valid.
- [x] AC-7: Record the confirmed post-`_tree_already_at` full-path and persisted-phase trace in the Progress Log.
- [x] AC-8: A resumable pack handoff records one identical owned durable copy. Delete TMP staging, put the original outside discovery, and execute the retained command in a fresh subprocess: continuation succeeds without full preflight/render/extract. Label this restart simulation, not reboot qualification.
- [x] AC-9: Guards reached inside accepted update-index and memory-resume runs regenerate the same flag without looping or skipping phases.
- [x] AC-10: A stale module lacking the actual `20b34` helper/argument returns the full form without raising; test a text-only argv adapter only if the actual helper contract requires one.
- [x] AC-11: Wrong bytes, replaced identity, malformed root/path/token/target binding and linked/reparse/FIFO/directory/permission-denied or foreign occupied targets refuse before unsafe read/publication and leave foreign bytes untouched. An unowned matching-hash file is refused; FIFO tests cannot block.
- [x] AC-12: Repeated pauses and failed index/storage/dashboard paths keep the proof and reuse exactly one owned copy, with no per-retry archives.
- [x] AC-13: Actual successful terminal cleanup deletes only the exact owned durable and separately proven TMP files, removes the checkpoint and leaves the external original unchanged. Inject archive deletion denial and successful archive deletion followed by checkpoint-removal denial; each reports nonzero and retains recoverable terminal state. Execute fresh-process cleanup retries and interruption fixtures before/after archive deletion: finalization completes without archive loading, rerendering or reindexing. Absent/malformed terminal state and ordinary resume with missing archives still refuse; a replaced/unowned target is never deleted.
- [x] AC-14: A supported old-runner/incoming-hook fixture produces the retained binding and valid continuation; default full/storage handoffs remain accepted. Claims of old cleanup compatibility are bounded by executed fixtures.

## Tasks

- [x] Re-trace actual guard sites, persisted checkpoints and post-`_tree_already_at` behavior after `20b3a`; record the explicit safe whitelist and provenance table before code.
- [x] Read the implemented `20b34` helper and consume its actual contract at the single selection point, retaining stale/rebuild/receipt fallbacks.
- [x] Implement one-slot contained retention and atomic ownership binding in `upgrade_extensions`; validate it before loading in the resume resolver, preserving the separate TMP proof.
- [x] Integrate checkpoint-owned terminal deletion and cleanup-only retry with existing `phase_cleanup` states, including archive-success/checkpoint-failure and interrupted transitions; retain failed/paused authority and test old-runner seams without adding a general cache service.
- [x] Add actual-main/fresh-subprocess continuation, structural/identity/hash refusal, bounded reuse and cleanup-retry tests in `test_index_upgrade_guard.py` and `test_upgrade_wavefoundry.py`; re-verify pinned server/default-storage argv tests (AC-1 through AC-14).
- [x] Update `docs/architecture/data-and-control-flow.md` with phase/provenance selection and retained-pack authority/lifetime; add a `CHANGELOG.md` bullet. Record checked/changed architecture evidence.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| trace and actual helper contract | implementer | reviewed/paused `20b3a` | safe phase/provenance table |
| call-site selection | implementer | trace; change `20b34` helper | one decision point; hard dependency on `20b34` |
| retention, resolver and cleanup | implementer | selection | one owned slot; retain failed/paused proof |
| tests | implementer | selection and retention | actual-main and fresh-process evidence |
| architecture doc and CHANGELOG | implementer | selection | data-and-control-flow.md |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_index_upgrade_guard.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `docs/architecture/data-and-control-flow.md`

`CHANGELOG.md` also changes (root-level file, so not a declared target). `sqlite_storage_migration.py` is read-only here; `upgrade_wavefoundry.py` has bounded resolver and terminal-cleanup ownership in this change. The upgrade-failure-surfacing wave (`20b33`, `20b34`) edits the same upgrade files and is implemented, delivery-reviewed and paused first; within this wave, `20b35` also edits `upgrade_extensions.py` and lands before this change, in a separate hunk.

## Affected Architecture Docs

Update (mandatory): `docs/architecture/data-and-control-flow.md` describes the resume phases (`resume_after_gate`, `resume_after_memory`, about lines 441-445); it describes safe phase/provenance selection, the single contained checkpoint-owned recovery pack, fresh-process validation, failed/paused retention and terminal cleanup; unproven states retain the full form. The implementer records "checked, changed" in the Progress Log. No new boundary.

## AC Priority


| AC    | Priority  | Rationale |
| ----- | --------- | --------- |
| AC-1  | required  | The core defect. |
| AC-2  | required  | Must not break the safe default, rebuild or a pending receipt. |
| AC-3  | required  | Proves the behavior, not just the argv. |
| AC-4  | required  | A guard site with no mapping, or a flag its entry refuses, reintroduces the defect. |
| AC-5  | required  | Second caller and `20b34` depend on unchanged output. |
| AC-6  | required  | The pinned test must follow the contract. |
| AC-7  | important | Resolves an inferred claim. |
| AC-8  | required  | Resume forms omit `--pack`; the archive must still match. |
| AC-9  | important | A guard inside a resume run must not loop or skip a phase. |
| AC-10 | required  | A stale module must degrade to the full form, not crash. |
| AC-11 | required | Recovery authority must not trust or overwrite foreign paths. |
| AC-12 | required | Retention is bounded and survives pauses. |
| AC-13 | required | Completion must remove owned files without losing cleanup authority. |
| AC-14 | required | Incoming-hook compatibility is an executed contract. |


## Progress Log

Final tracking — 2026-10-10: all fourteen ACs and six tasks marked complete with typed `wf_mark_ac`/`wf_mark_task(mode='create')`; Change Status is implemented. The two existing pinned `test_server_tools.WaveUpgradeMcpToolTests` storage/index-guard confirmation tests passed unchanged (2 tests, 0.424 seconds, no skips). Source is frozen, all control mutants restored, and the coordinator owns full docs validation, whole-suite qualification and independent delivery review. The implementation briefing packet is `/private/tmp/wf20b3b-upgrade-implementation.json`; the evidence above remains durable here rather than depending on that temporary packet.

Implementation evidence — 2026-10-10: the selector consumes the unchanged `20b34` API and the positive phase table below. One retained archive is exclusively published and bound atomically through the existing checkpoint; a foreign matching-hash slot, raced publication, links/reparse/FIFO/directory/multilink/denied paths, root/token/target/path mismatch, replacement identity and changed bytes refuse. `_zip_from_lock` prefers only this proven locator; `main` validates it before memory backstops or extension loading, and the loader executes frozen validated bytes. Verified TMP ownership stays separate. Actual cleanup proves fatal/storage/dashboard completion and writes terminal state before deletion; deletion denial is nonzero with retry authority. Early terminal `--cleanup` finalizes before archive resolution, including modeled interruption before/after unlink; ordinary missing archives and malformed terminal proofs refuse. External originals remain untouched. Current-tree continuation creates no archive.

Qualification — final focused command uses `env -u PYTHONPYCACHEPREFIX PYTHONDONTWRITEBYTECODE=1 WAVEFOUNDRY_DISABLE_BYTECODE_CACHE=1 PYTHONPATH=.wavefoundry/framework/scripts/tests:.wavefoundry/framework/scripts /Users/coryhacking/.wavefoundry/venv/bin/python3 -B -m unittest` with `test_index_upgrade_guard`, `test_upgrade_wavefoundry.ReviewPlanPreflightTests`, `test_upgrade_wavefoundry.ReviewPlanInstallingUpgradeTests`, `test_render_agent_surfaces.ReviewPlanPromptMigrationTests`, `test_server_package.OldRunnerCompatibilityTests`, `test_upgrade_wavefoundry.FailureMarkerLockTests`, `test_upgrade_wavefoundry.PhaseCleanupLockStateTests`, `test_upgrade_wavefoundry.PhaseCleanupSetupBaselineTests`, `test_upgrade_wavefoundry.ResumeAfterGateTests`, `test_upgrade_wavefoundry.Phase4PublisherGrantTests`, `test_upgrade_recovery_guidance`, `test_upgrade_failure_surfacing`, and `test_sqlite_storage_migration.ReceiptTests`: 191 tests, 18.851 seconds, green with one existing native-runtime skip. Earlier batches were 69 tests/9.113 seconds and 56 cleanup tests/6.782 seconds; a 64-test recovery/storage batch exposed only the exact identity-boundary census, repaired by adding nine actual reviewed expressions without changing existing entries/assertions or migration implementation.

Guard controls — each source mutation was restored before continuing. Named tests failed when loosening the update whitelist, pre-docs memory exclusion, token binding, both proof identity comparisons, archive hash binding, exclusive publication, terminal fatal-obligation proof, ordinary archive absence, early terminal resolver ordering, or frozen-byte loading. The publication mutant replaced the raced foreign slot; its named test failed because `FileExistsError` was not raised. The loader mutant executed the injected foreign marker and failed its explicit assertion. An extra unlisted `entry.st_ino == entry.st_ino` comparison failed the existing identity census, demonstrating the nine-entry extension is not a whole-function exemption. First diagnostic controls for publication/loader raised downstream errors and were superseded by these assertion failures. No mutants remain.

Compatibility and limits — the imported actual v1.15.4 loader, hook and failure-finalizer fixture produces a retained binding and preserves the host pause; current freshly copied source executes the exact recorded continuation argv after TMP deletion and moving the external original beyond discovery. This is a restart simulation with fake expensive child publication/backfill boundaries; actual `main`, guards, resolver and ownership checks execute. It establishes neither a physical reboot/index-build measurement nor universal old installed-process/old cleanup compatibility. Continuation appends the log, omits lock recreation/preflight/extraction/rendering, and observes child publication; completion in this fixture ends at publication with the checkpoint retained, while separate actual `phase_cleanup` and fresh terminal retries prove final deletion. Windows reparse/permission cases are injected simulations. Descriptor containment does not make the final identity-check/unlink sequence atomic.

Pinned rows and architecture — `test_same_schema_old_host_requires_new_coordinator_and_confirmation` remains a preflight full-form row; legacy server-tool storage/index-guard fixtures have no proven post-docs target/gate and retain their default confirmation/full contracts. Existing receipt/recovery tests retain storage/default argv semantics. `docs/architecture/data-and-control-flow.md` checked, changed by the coordinator with the explicit whitelist, root/token/path authority, one-slot lifetime and terminal retry; `CHANGELOG.md` carries the scoped behavior bullet. Owned layering and native-Windows recovery docs describe the same boundaries and qualification limits. Nine exact census additions are two descriptor-read identity checks, two root identity binding checks, identity shape, named/opened proof identity, retained-byte hash, and separately proven TMP identity.

Readback — 2026-10-10: a host guard currently emits full --pack and reruns surface rendering even when `_tree_already_at` skips extraction; after repair a proven post-docs memory/update checkpoint emits its accepted resume flag and retains one owned byte-identical ignored archive. AC-1–14 cover conservative phase/tree/provenance/API selection, one-slot identity/hash/root/token/target ownership, validation before loading, failed/paused retention and terminal cleanup retries. Files: upgrade extensions/runner and focused guard/upgrade tests; shared data/control-flow and CHANGELOG are coordinator-owned. No storage helper/API/index behavior, prompt or seed edits.

Trace before code — actual guards: `_post_extract` (pre-docs; full fallback), `pre_index_update`, `pre_index_rebuild`, `_enforce_index_guard_before_children` (including parent-owned publication). Full `_tree_already_at` skips only extraction; Phase1 rendering continues. Full Phase4 local current_phase=index_update retains persisted current_phase=awaiting_memory_validation written after docs_gate_complete. Memory entry accepts awaiting_memory_validation/awaiting_memory_publication/memory_resume_preflight/index_complete; its legacy absent/preflight phase requires a real run/gate and no runner_protocol, and the actual post-extract site must explicitly prevent interpreting it as post-docs. Update whitelist is docs_gate_complete/index_complete with memory absent or indexed; synthetic persisted index_update, unknown/preflight, tree mismatch, rebuild, pending receipt/restart action and stale helper fall back full. Actual `restart_command(root, pack_path, rebuild_storage, *, entry_path, setup_args, resume_flag)` returns argv, command, shell and stays unchanged.

Readiness repair — 2026-10-10: one bounded plan repair resolves `20b36-retained-pack-terminal-cleanup-retry`. Requirements 8/10 and AC-13 now distinguish strict ordinary resume from terminal cleanup finalization after deliberate archive removal. The current-function TMP probe reached `phase_cleanup`, injected the planned archive unlink, and observed actual checkpoint denial returning false; it does not claim future implementation. Existing one-slot ownership, fatal obligations, default storage/restart API and external archive lifetime remain unchanged. Fresh focused verification follows publication of the repaired Prepare receipt.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-10 | Planned from upgrade field feedback; command shape and log truncation verified read-only. | file:line citations in Rationale |
| 2026-10-10 | Readiness repair: the full path is verified to re-render after `_tree_already_at`; mapping table, rebuild fallback and single decision point added. | red-team and docs-contract readiness reviews |
| 2026-10-10 | Confirming-round repair: mapping rewritten over real lock fields and the entries' accept sets; unreachable `--resume-after-gate` row deleted; `restart_command` no longer changed here (consumes the `20b34` helper); `zip_path` durability, pending-receipt rule and guard-inside-resume added. Product Intent: waived (bug fix, no product scope). | confirming readiness reviews of all six lanes |
| 2026-10-10 | Plan amended with conservative persisted-phase selection and operator-approved one-slot pack retention, validation and cleanup. Actual `20b34` API remains a post-predecessor verification dependency. | `enforce_index_guard_handoff`, `_zip_from_lock`, `_stage_pack_for_consumption`, `phase_cleanup`; operator direction |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-10 | Divergent pre-plan. Approach A: select a resume flag from recorded state at the guard's call site. Approach B: keep the full form but make the full path skip rendering and the docs gate when the tree is already at target. Approach C: only document the manual resume. Selected A, deciding at `upgrade_extensions.py:851` by consuming the `20b34` resume helper. | A fixes the handoff at the source and reuses tested resume flags; the call site is incoming code in the old-code window; adding nothing to `restart_command` protects `sqlite_storage_migration.py:900` and avoids a duplicate parameter with `20b34`. | B changes the semantics of the full upgrade for every caller; C is the status quo; changing `restart_command` here would collide with `20b34` and break its second caller. |
| 2026-10-10 | Delete the `--resume-after-gate` row. | No guard site fires before the docs gate has passed, and the one earlier site (`upgrade_extensions.py:3833`) maps to the full form, so the row is unreachable; keeping it would invite a dead command. | Keep it for synthetic coverage only (rejected: untestable through a real site). |
| 2026-10-10 | Operator selected one durable contained verified pack retained until terminal completion; full fallback remains for unproven phases. | Preserves resumability without assuming TMP or external-original survival. | Full fallback for every staged pack was rejected; no general archive cache. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Old-code window: an older runner emits the full form. | Requirement 9; the full form stays valid. |
| Wrong flag chosen for a checkpoint produces a command the resume entry refuses (worse than the full form). | Predicates copied from the entries' accept sets; the default row is the full form; AC-4 asserts acceptance per site. |
| `restart_command` or the `20b34` helper is a stale pre-upgrade module. | The call site falls back to the full form (Requirement 2, AC-10). |
| `--rebuild-storage` combined with a resume flag is rejected. | Requirement 4 keeps the full form when rebuild or a pending receipt applies. |
| TMP staging disappears or the durable recovery archive is replaced. | Retain one owned contained archive and validate identity/hash before loading (Requirements 5-8; AC-8 and AC-11). A refusal preserves recovery authority. |
| The cited line anchors shift once `20b3a` lands. | Precondition: re-derive anchors against the post-`20b3a` tree. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
