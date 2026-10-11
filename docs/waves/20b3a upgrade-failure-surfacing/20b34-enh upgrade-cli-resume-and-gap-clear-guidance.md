# Upgrade CLI Resume and Accounting-Gap Clear Guidance

Change ID: `20b34-enh upgrade-cli-resume-and-gap-clear-guidance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-10
Wave: 20b3a upgrade-failure-surfacing

## Rationale

Two field-report symptoms turned out to be missing guidance rather than missing capability.

**Mid-upgrade MCP deadlock.** After the 1.28 framework files were extracted, the Wavefoundry MCP server could not start (missing `apsw`, `sqlite-vec`, `psutil`), and `wf setup` refused with `storage_setup_foreign_upgrade`. The upgrade's historical-memory pause told the operator to "Reload MCP, run memory_backfill(...) and memory_validate, then call wf_upgrade(phase='resume_after_memory')", all of which need the MCP server. A CLI path exists and is tested: `--resume-after-memory` (`upgrade_wavefoundry.py:5363-5372`, handler `:5645`) with `--confirm-hosts-stopped` (`:5330`); tests at `tests/test_upgrade_wavefoundry.py:10666 ff.` and `tests/test_storage_upgrade_resume.py:613`. But the exact CLI resume command is surfaced only for the index-guard and storage restart pauses (`restart_command`, `sqlite_storage_migration.py:801-828`) and by `repair_ppol_memory_staging.py:265`, not for the plain memory pause. The same MCP-only wording appears at `upgrade_wavefoundry.py:6202-6205` and `:6638-6641`, `upgrade_extensions.py:2752, 2878, 2886`, `upgrade_bundle.py:188`, `publication_control.py:145, 153` and `wf_server/upgrade_handlers.py:1123, 1494, 1498`. The `storage_setup_foreign_upgrade` refusals (`setup_reconciliation.py:109` and `:126`, printed by `setup_wavefoundry.py:341-343`) do not name the resume command either. The operator found the way out only by experiment.

**Accounting-gap marker.** The field report said the framework has no command to clear `.wavefoundry/logs/context-efficiency.gap`. That claim is **refuted**: `wf clear-accounting-gap` (native Windows `.\.wavefoundry\bin\wf.cmd clear-accounting-gap`) exists (`context_efficiency.py:1025-1026`, `wf_cli.py:80` and `:132`, implementation `context_efficiency.py:3398-3496`), clears a zero-byte marker without trouble, is non-destructive, and `_gap_diagnostic` (`context_efficiency.py:1167-1182`) appends the exact command to `projection.detail.error`. The weak spot is the top-level error: `wf_server/server_impl.py:24485-24503` (`wf_upgrade`) and `server.py:927-944` (`wf_reload_mcp`) say only "Resolve the projection failure" (lines 24502 and 943), and the operator, who saw only the top-level text, concluded no command existed. There is no MCP tool for the clear; this change does not add one.

Brief: goal is that a blocked operator is told the exact next command at the point of the block. Audience: operators and agents mid-upgrade. Constraints: wording and structured-field changes only; no new command, no new MCP tool, no behavior change to resume or clear. Exclusions: changing the full-upgrade handoff command shape (change `20b36-bug index-guard-handoff-resume-not-full-upgrade`). Success: each named message contains the exact command with `--root` filled in for the repository.

## Requirements

1. The historical-memory pause, wherever emitted, names the CLI resume form alongside the MCP form: `upgrade_wavefoundry.py --root <repo> --resume-after-memory --yes --confirm-hosts-stopped`, run with the interpreter that `restart_command`-style helpers already select, and states that it requires the external-terminal, hosts-stopped condition and is run by the operator. The census of emission sites is: `upgrade_wavefoundry.py:6202-6205`, `:6211` (the "ready_for_index" message), `:6638-6641`, and the generic pause renderer `_report_action_required_pause` (`:5057-5066`); `upgrade_extensions.py:2752`, `:2878`, `:2886`, `:2921` (the "newly installed resume_after_memory runner" message) and the third `action_required` writer near `:2800`; `upgrade_bundle.py:188`; `publication_control.py:145`, `:153`; `wf_server/upgrade_handlers.py:1123`, `:1494`, `:1498`; and `memory_handlers.py:1191` (`usage = "wf_upgrade(phase='resume_after_memory')"`). Each site is in scope unless the implementer records an out-of-scope reason for it; sites found missing at implementation are added to this list, not skipped. The census also records, per site, the checkpoint state in which it fires, because the right wording and flag depend on it: `upgrade_wavefoundry.py:6211` is the "ready_for_index" message, so the flag there is `--resume-after-memory` for index publication and the text is NOT a memory-validation pause (AC-1 must not demand "awaiting validation" wording at that site); the `:6202-6205` and `:6638-6641` sites and `_report_action_required_pause` fire at the memory pause; `upgrade_extensions.py:2921` fires after a newly installed `resume_after_memory` runner; the other sites record their own state in the Progress Log during the re-enumeration task.
2. The `action_required` record at every writer (`upgrade_wavefoundry.py:6187-6193`, `:6618-6624` and `upgrade_extensions.py` near `:2800`) carries the CLI form as a structured `command_argv`, and the human text and `command_argv` come ONLY from one shared helper, never a hand-assembled string.
   - **Placement (decided).** The helper lives in `sqlite_storage_migration.py` next to `restart_command` (`:801-828`), because `setup_reconciliation.py` already hard-imports that module as `migration` (`setup_reconciliation.py:18`); a separate module would import `restart_command` anyway and add a module and a mixed-version surface for no gain. The helper is a thin wrapper over `restart_command` through an optional `resume_flag` argument whose default leaves `restart_command` output byte-identical (change `20b36` owns any other `restart_command` change, so this change's edit sits in a separate hunk from `20b36`'s).
   - It must not reuse `restart_command`'s `--pack` tail, because the resume form takes no `--pack`. `restart_command` already appends `--yes --confirm-hosts-stopped`, so the resume flag must precede them; the argv order is pinned as `... --root <repo> <resume-flag> --yes --confirm-hosts-stopped`.
   - Quoting is correct on both shells (`shlex.join` on POSIX, PowerShell single-quote doubling on `nt`, both already done by `restart_command`), including a repository path with spaces and an apostrophe. The same helper's quoting is reused for the `<root>` in Requirement 5.
   - The implementer confirms in the argparse block (near `upgrade_wavefoundry.py:5322`) that each of `--update-index`, `--cleanup`, `--resume-after-gate` and `--resume-after-memory` accepts `--yes` and `--confirm-hosts-stopped` (the field note says `--confirm-hosts-stopped` is a global flag), and that the `storage_setup_resume_required` guard near `:5449-5458` does not apply to the checkpoint-derived commands; any flag that fails either check is dropped from the allowlist in Requirement 3 and gets the generic wording.
3. The `storage_setup_foreign_upgrade` messages (`setup_reconciliation.py:109` and `:126`) fire for ANY recorded non-setup upgrade checkpoint, so they name the resume command derived from the recorded checkpoint (`failed_phase` and `current_phase` in the lock), never a hard-coded `--resume-after-memory`.
   - **Allowlist, never interpolated.** The flag is chosen by mapping the recorded checkpoint onto a fixed allowlist of four flags (`--resume-after-gate`, `--resume-after-memory`, `--update-index`, `--cleanup`). Lock-record contents are never interpolated into the command, so an edited lock cannot inject a flag. An unrecognized checkpoint gets the safe generic wording and no flag.
   - **Mixed-version guard.** `setup_reconciliation` is deliberately mixed-version tolerant (it uses `getattr` on `upgrade_lib`). Because the helper lives in `sqlite_storage_migration.py`, the import is already hard and the wording "tolerant import" does not apply; instead the call site is guarded: an older `sqlite_storage_migration` whose `restart_command` lacks `resume_flag` (a `TypeError`, or a failed `getattr` check for the helper) falls back to the pre-change generic wording, and the refusal keeps its code `storage_setup_foreign_upgrade` and its exit status. The refusal must never raise.
4. The printed resume command, in text and in `command_argv`, is marked operator-run: it must be run from an external terminal after every Wavefoundry host is stopped, and agents must not execute it (a structured argv invites automatic execution, so the marker is part of the structured record, not only the prose). The structured record carries that marker.
5. When `projection.detail.authority_status == "accounting_gap"`, the top-level `wf_upgrade` error (`server_impl.py:24502`) and `wf_reload_mcp` error (`server.py:943`) include the clear command for the platform: `./.wavefoundry/bin/wf clear-accounting-gap` on POSIX and `.\.wavefoundry\bin\wf.cmd clear-accounting-gap` on native Windows, introduced by "from the repository root `<root>`" (with `<root>` quoted by the same helper as the resume command, so a path with spaces or an apostrophe is safe) or given as the absolute dispatcher path, because the relative form depends on the current directory and could run another checkout's dispatcher. Other projection failures keep their current text.
6. The messages state that clearing the marker discards no waves, docs or memories, and that it marks unsealed, non-closed waves `accounting_gap`, so those waves stay marked and their totals stay flagged incomplete (events that failed and were not spooled are not backfilled).

## Scope

**Problem statement:** Existing, tested recovery commands are not named where the operator is blocked.

**In scope:**

- Message text and the structured `action_required.command_argv` at the pause sites in the Requirement 1 census and Requirements 2 to 3.
- Conditional clear-command text in the two top-level projection-failure errors.
- One shared helper for the CLI resume argv in `sqlite_storage_migration.py` (a thin wrapper over `restart_command` with an optional `resume_flag`; default `restart_command` output unchanged), plus the guarded call from `setup_reconciliation.py`.
- Tests asserting the commands appear, and a CHANGELOG Unreleased bullet.

**Out of scope:**

- An MCP tool for clearing the gap (the Requirement 4 text is the only guidance).
- Making the upgrade not block on a gap marker (a separate policy decision; the current block is deliberate and the clear command is the supported path).
- The re-poisoning cause on `flush` permission failures (change `20b38-bug context-efficiency-flush-permission-poisons-store`).
- The `--resume-after-memory` implementation itself.

**Platform behavior (required statement):**

- Windows (native): command text uses the `.cmd` dispatcher form and Windows path style for the clear command; the resume command uses the tool-venv interpreter that the index-guard handoff already selects (the field run hit Errno 9 with the Store Python and no redirection advice is added here; the Errno 9 fault is change `20b31-bug fsync-readonly-handle-windows-storage-migration`).
- macOS, Linux, WSL2: POSIX dispatcher form `./.wavefoundry/bin/wf`; WSL2 is treated as Linux.
- The Windows command forms (the `.cmd` dispatcher and PowerShell quoting) are verified by rendering with a patched platform value and are **inferred, not run on a real Windows host**.

**Old-code window:** These messages are produced by the INSTALLED `upgrade_wavefoundry.py`, `setup_reconciliation.py` and server code. An older install being upgraded will still print the old text; this change helps upgrades that begin from a version containing it, and the field blocked state (new files extracted, old messages already printed) is not retroactively fixed. Tests must not assume otherwise.

## Acceptance Criteria

- [x] AC-1: Every emission site in the Requirement 1 census includes the CLI resume form with the repository root, the checkpoint-appropriate resume flag (`--resume-after-memory` at the memory pause and at the `:6211` "ready_for_index" message), `--yes` and `--confirm-hosts-stopped` and the operator-run statement, verified by tests that capture each rendered message. The `:6211` "ready_for_index" site is not required to carry "awaiting validation" wording. Sites found missing at implementation are recorded, not silently skipped; an out-of-scope site carries a recorded reason, and each site's firing checkpoint is recorded in the Progress Log.
- [x] AC-2: Every `action_required` writer contains a `command_argv` whose elements equal the argv from the shared helper and carries the operator-run marker, verified by a test comparing the two; the human text is rendered from the same helper.
- [x] AC-3: The `storage_setup_foreign_upgrade` refusal names a resume command derived from the recorded checkpoint through the fixed four-flag allowlist, with one test per checkpoint (resume-after-gate, resume-after-memory, update-index, cleanup) built from a lock record with the matching `failed_phase` or `current_phase`; a test that an unrecognized checkpoint, and a lock record whose fields contain a flag-like string, get the generic wording and no flag; and a mixed-version test that stubs an older `restart_command` lacking `resume_flag` (or blocks the helper) and asserts the refusal still renders the pre-change generic wording, never raises, and keeps the code `storage_setup_foreign_upgrade` and the same exit status. Assertions in `tests/test_setup_reconciliation.py` and `tests/test_setup_wavefoundry.py` are updated accordingly, and the argv order `... --root <repo> <resume-flag> --yes --confirm-hosts-stopped` is asserted.
- [x] AC-4: With a gap marker present, the `wf_upgrade` and `wf_reload_mcp` top-level errors contain the platform-correct `clear-accounting-gap` command qualified by the repository root or an absolute dispatcher path and the statement that affected waves stay marked `accounting_gap` with totals flagged incomplete; with a non-gap projection failure they do not, each verified by a test (the Windows form verified by rendering with a patched platform value).
- [x] AC-5: The existing test pinning the pause wording (`tests/test_upgrade_wavefoundry.py:11943` asserts `resume_after_memory`) still passes, and no existing assertion on `index-guard` command shape (including `tests/test_index_upgrade_guard.py`) is altered by this change; `restart_command` output with no `resume_flag` is byte-identical to before.
- [x] AC-6: A repository path containing spaces and an apostrophe renders a correctly quoted command in both the POSIX and the Windows (PowerShell) form, verified by tests for the shared helper's text and `command_argv`.
- [x] AC-7: The `CHANGELOG.md` `[Unreleased]` section carries one bullet naming this change id, the new CLI resume and clear-command text, and the old-code window (the first upgrade carrying this change still prints the old text), with no build numbers; this is also re-checked at wave close.
- [x] AC-8: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Re-enumerate every emission site of the memory pause (Requirement 1 census) and the two refusals against HEAD and record any missed site.
- [x] Confirm in the argparse block (`upgrade_wavefoundry.py` near `:5322`) that `--update-index`, `--cleanup`, `--resume-after-gate` and `--resume-after-memory` accept `--yes` and `--confirm-hosts-stopped`, and that the `storage_setup_resume_required` guard near `:5449-5458` does not apply to them; drop any failing flag from the allowlist.
- [x] Add the shared CLI-resume argv helper in `sqlite_storage_migration.py` as a thin wrapper over `restart_command` with an optional `resume_flag` (flag before `--yes --confirm-hosts-stopped`, no `--pack`); do not change default `restart_command` output; keep the hunk separate from `20b36`'s.
- [x] Update the pause messages and every `action_required.command_argv` writer to use the helper and carry the operator-run marker.
- [x] Update `setup_reconciliation.py:109` and `:126` to derive the resume flag from the recorded checkpoint through the fixed allowlist, guarding the call (`TypeError` or failed `getattr`) so an older `restart_command` falls back to the generic wording.
- [x] Add the conditional, root-qualified clear-command text to `server_impl.py:24502` and `server.py:943`.
- [x] Add and update tests (AC-1 to AC-6); run the pre-existing upgrade, setup and context-efficiency suites that touch these strings.
- [x] Update `docs/specs/mcp-tool-surface.md` or the upgrade runbook if they quote the pause text; add the CHANGELOG Unreleased bullet (AC-7).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| resume-guidance | implementer | none | pause messages, command_argv, setup refusals |
| gap-clear-guidance | implementer | none | server_impl.py and server.py error text |
| tests-and-docs | implementer | resume-guidance, gap-clear-guidance | spec and CHANGELOG |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/setup_reconciliation.py`, `.wavefoundry/framework/scripts/sqlite_storage_migration.py`, `.wavefoundry/framework/scripts/server.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` is checked for any description of the memory-pause hand-off and updated only if it names MCP as the sole resume path. Other architecture docs: N/A, text and structured-field changes with no boundary, layering or data-flow change.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The memory pause is where the field operator got stuck. |
| AC-2 | important | Prevents MCP and CLI renderings drifting apart. |
| AC-3 | required | The refusal is the second dead end in the same flow. |
| AC-4 | required | The top-level text caused the wrong "no command exists" conclusion. |
| AC-5 | important | Guards against collateral changes to pinned wording and `restart_command`. |
| AC-6 | required | A wrongly quoted command fails for exactly the paths where operators are already stuck. |
| AC-7 | important | Release-note obligation and the old-code-window honesty statement. |
| AC-8 | required | Change-local test and docs validity. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-10 | Planned from field report; "no clear command" claim refuted at HEAD, resume messaging gap confirmed | file:line citations in Rationale |
| 2026-10-10 | SOURCE_FILES unchanged; helper lives in sqlite_storage_migration.py, an already-unlisted module. Readiness-digest effect: none from this change, because no module is added to `setup_readiness.py` SOURCE_FILES and `setup_reconciliation.py` already imports the module | Release-reviewer re-verification (round 2) |
| 2026-10-10 | Round-2 repair from the confirming readiness reviewers: helper placed in `sqlite_storage_migration.py` (the "tolerant import" wording dropped, replaced by a `TypeError`/`getattr` call-site guard with a test), argv order pinned, fixed four-flag allowlist, argparse and `storage_setup_resume_required` confirmation task, `:6211` recorded as the "ready_for_index" message, root quoted by the same helper, CHANGELOG AC added, Windows forms noted as simulated only. Product Intent: waived (guidance-text change with no product scope; no change doc of this kind carries the section and docs-lint does not enforce it). | reviewer findings recorded in the wave readiness round |
| 2026-10-10 | Readback: before, memory pauses and foreign-upgrade refusals expose MCP-only recovery and top-level gap failures omit the supported clear command. After, one checkpoint-allowlisted helper supplies operator-run CLI guidance and structured argv; default restart argv, memory authorization and all resume/clear behavior remain unchanged. | Parent activation; admitted Requirements 1–6, captured pre-edit restart baseline in owned temporary receipt. |
| 2026-10-10 | Thought: implement the helper beside restart_command, propagate concrete roots through the census, preserve generic unknown/mixed-version refusals, then prove each real renderer and negative gap case. | Live census in preflight; four global argparse flags and non-setup guard confirmed. |
| 2026-10-10 | Action / Observe: resume_guidance wraps restart_command with a four-literal checkpoint allowlist and operator-only markers. All three action writers use its argv; both runner memory pauses, ready-for-index, generic typed pause, old-protocol post-docs, pre-index validation/publication, post-index candidate refusal, bundle recovery, publication refusal, MCP next-step/pause and memory-handler usage carry its root-qualified prose. | New real message consumers plus existing 735-test upgrade module; all six captured pre-edit default restart dictionaries match byte-for-byte afterward. |
| 2026-10-10 | Checkpoint census: awaiting_memory_validation / awaiting_memory_publication / memory_resume_preflight choose resume-after-memory, including a failed index child under memory ownership; legacy post-docs failure or docs-gate failure chooses resume-after-gate; index_update/rebuild/publication failure chooses update-index; index_complete and cleanup/dashboard_restart/retired_model_cleanup choose cleanup. Unknown, flag-like and non-string fields have no command. Setup-owned checkpoints retain setup guidance. | Per-checkpoint real setup _inspect tests, POSIX and simulated PowerShell spaces/apostrophe argv/quoting, older-helper absence and restart TypeError generic fallback; four global argparse flags accept yes/hosts-stopped and checkpoint-derived commands are non-setup-owned. |
| 2026-10-10 | Refusal census: both setup _inspect foreign-upgrade refusals are updated. sqlite_storage_migration.restore_checkpoint foreign-setup-receipt conflict remains excluded: its setup-owned receipt cannot authorize a foreign upgrade continuation. Top-level registered wf_upgrade and wf_reload_mcp name clear-accounting-gap only for authority_status=accounting_gap and preserve other failures verbatim. | Real zero-byte gap marker at both registered tools, no live reload or child launch; safe clear guidance includes root qualification, retained accounting_gap/incomplete totals and unspooled-event caveat. |
| 2026-10-10 | Reflect: guidance changes no phase, publication or memory authorization. Architecture data/control flow names the publication transition without presenting MCP as the only resume path; no architecture edit needed. SOURCE_FILES roster is unchanged; tracked server.py/server_impl.py bytes still change their ordinary readiness digest. Old installed messages remain on the first consuming upgrade. | Two Unreleased bullets and MCP tool spec updated; native Windows command forms inferred from simulated rendering only; no memory curation or new command/tool. |
| 2026-10-10 | Qualification boundary: AC-1 through AC-7 are evidenced; AC-8 remains for coordinator canonical qualification/docs validation. A combined test exposed a stale lifecycle_lock test patch after prior module reload; it now binds the actual runtime lookup and keeps called/not-called assertions. | 36 expanded new tests passed in 2.935s; setup CLI module 50 passed in 2.084s; final corrected integration pending at this checkpoint. |
| 2026-10-10 | Final focused checkpoint: corrected integration passed 135 tests in 85.872s; upgrade module passed 735 tests with 2 skips in 178.524s; setup CLI module passed 50 tests in 2.084s; all 36 expanded new tests passed in 2.935s. Eight in-memory deletion/loosening mutants were killed at their actual lookup consumers. All owned test processes and fixture children are joined; diff whitespace check passed. | Source freeze; canonical full-suite and full docs validation remain coordinator-owned, with AC-13 (20b33) / AC-8 (20b34) intentionally still unchecked. |

| 2026-10-10 | Cycle-2 repair readback: successful MCP reload must refresh child_tee and sqlite_storage_migration before the current handler consumes them. Add both concrete purge entries, bind the two new tests to the current qualified handler module, and add a real reload-consumer regression in the existing failure-surfacing test. Update only the intentionally changed wf_upgrade handler digest, retaining captured_at, every other digest and all guard assertions. Four framework paths; existing module integration and guidance contracts are unchanged. | Executed pre-fix reload/census/digest counterexamples; typed repair_start precedes mutation; no new phase, trust or ownership protocol. |

| 2026-10-10 | Repair readback refinement: evict child_tee, but refresh sqlite_storage_migration through the existing in-place reload machinery, retaining its exception identity and module-owned candidate ContextVar. Literal eviction exposed eight indexing/setup dependencies and split retained exception identity; it is rejected. Preserve the existing ContextVar on module initialization and verify active binding/scope exit as well as both fresh handler consumers. This adds the already-owned migration module as a fifth repair path; no dependency purge, generic state map or ownership protocol is introduced. | Fresh architecture/code controls reproduce raw reload losing active context and raising ValueError; the guarded initializer preserves context, exception and runtime-lock identities while refreshing guidance. |

| 2026-10-10 | Existing reload test expectation refinement: adding the approved migration in-place entry requires the current two-name tuple assertion and a runtime_lock-only deletion mutant that retains migration. Update only these two structural expectations; keep all negative guard/census assertions and ensure the mutant actually changes the source. This is the sixth repair path, with no production scope expansion. | Real handler/active candidate-scope oracle passes; unchanged closure guard reports no missing dependencies. |
| 2026-10-10 | Readback/Thought: cycle-3 qualification repair, typed before mutation. Update only the obsolete runtime-lock deletion mutant, nine migration child mocks to the actual tee seam, and one exact internal-wait census classification. Preserve original mutation, child outcome/order/publication assertions and planted-call controls; all production bytes and admitted foreground flags remain unchanged. Before: canonical11 failures from stale test instrumentation; after: the same assertions reach current producers. Explicit helper timeout remains direct-child-only as before, not tree termination. | `20b3a-qualification-fixture-alignment`; `RuntimeLockReloadInPlaceTests`, `NativeMigrationTests`, `SchemaEightKindTests`, `ClassificationTests`; canonical12196/184/12, exit1; independent scratch11/0skips |
| 2026-10-10 | Observe: only the three test alignments landed;14 focused original failure/positive/planted-call controls pass in10.184s, zero skips. Removing the exact new wait classification fails `test_every_timed_call_is_routed_or_classified`; restored control passes. Runtime-lock deletion still raises `ImportError`/`reload_probe_marker`; all nine native child outcome/order/epoch/failure assertions remain unchanged and now reach the tee seam. Production bytes remain unchanged; framework edit gate closed for independent focused review and quiet qualification. | Named `RuntimeLockReloadInPlaceTests`, `NativeMigrationTests`, `SchemaEightKindTests`, `ClassificationTests`; cycle-3 typed repair before edits |


## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-10 | Divergent pre-plan: selected approach C below. | Smallest change that puts the exact command at each dead end. | A: add an MCP `wf_clear_accounting_gap` tool (rejected: expands the tool surface for an operator-only recovery, and the field case had a working CLI; also needs its own security and gate review). B: make upgrade ignore the gap marker (rejected: weakens a deliberate integrity guard; a policy decision outside a guidance change). C: name the existing CLI commands in messages and structured fields (selected). |
| 2026-10-10 | Build resume argv from one shared helper placed in `sqlite_storage_migration.py` beside `restart_command`. | Avoids hand-assembled strings drifting between the log text, `action_required` and the setup refusal; `setup_reconciliation` already hard-imports that module, so a separate module would add a module and a mixed-version surface for nothing. | Inline strings per site (rejected: the site count, at least ten, invites drift). A new stdlib module imported tolerantly (rejected: it would import `restart_command` anyway). |
| 2026-10-10 | Map the recorded checkpoint onto a fixed four-flag allowlist; never interpolate lock contents. | An edited lock record must not be able to inject a flag into a printed command. | Interpolate `failed_phase` into a flag (rejected: injection). |
| 2026-10-10 | Do not alter default `restart_command` output; add the helper as a thin wrapper with an optional `resume_flag`. | Tests pin its shape, change `20b36` owns any other change to it, and the resume form must not carry `--pack`. | Reuse by modifying it (rejected: couples to `20b36`). Mirror it in a second implementation (rejected: quoting drift). |
| 2026-10-10 | Derive the resume flag from the recorded checkpoint in the setup refusal. | The refusals fire for any recorded checkpoint, and a hard-coded `--resume-after-memory` is a wrong command after a mid-extract failure. | Hard-code the memory flag (rejected). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Site list is incomplete (some emissions found only by grep of the same phrase) | Census in Requirement 1 plus a re-enumeration task; AC-1 records missed sites. |
| Printing a `--confirm-hosts-stopped` command invites running it with hosts still up, or an agent running it from the structured `command_argv` | Operator-run marker in text and structured field; agents must not execute it (Requirements 1 and 4). |
| Wrong flag shown for the recorded checkpoint | Per-checkpoint derivation through a fixed allowlist and tests (AC-3). |
| Older `restart_command` in a mixed-version tree lacks `resume_flag` and the refusal raises | Call-site `TypeError`/`getattr` guard falling back to the generic wording; mixed-version test (AC-3). |
| A flag in the allowlist rejects `--yes` or `--confirm-hosts-stopped`, or hits the `storage_setup_resume_required` guard | Argparse and guard confirmation task; failing flags are dropped from the allowlist. |
| Relative clear command runs another checkout's dispatcher | Root-qualified or absolute path (Requirement 5, AC-4). |
| Overlap on `upgrade_wavefoundry.py` and `upgrade_extensions.py` with `20b33` and with wave `20b3b` | Lands after `20b33`; `20b3b` rebases on this change's helper; separate hunks (see wave Watchpoints). |
| Clear command text shown for a non-gap failure | Conditional on `authority_status == "accounting_gap"` (AC-4 negative case). |
| Old-code window: first upgrade carrying this still shows old text | Documented; not retroactively fixable. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
