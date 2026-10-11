# Review-Plan Prompt Migration Is Detected In Preflight, Not After Mutation

Change ID: `20b35-bug review-plan-prompt-migration-preflight`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: 20b3b upgrade-resilience

## Rationale

**Brief.** Goal: an upgrade that cannot migrate a project's customized `docs/prompts/interrogate-plan.prompt.md` must refuse before framework, operating-document, policy or checkpoint mutation. Consumer: an operator upgrading a repository whose legacy review-plan prompt is shortened or customized, including the real field path of an installed 1.15.4 runner upgrading to 1.28. Constraints: preflight in that window runs the OLD installed runner and OLD installed renderer (the old-code window), the check must be read-only, it must run with only the Python standard library available, and Windows, macOS, Linux and WSL2 behave identically. Success: the operator learns of the blocker, and how to resolve it, before the framework tree is extracted and before any wave is marked for re-Prepare, even when the installed runner predates this change.

**Precondition.** Do not Prepare or Implement this change until wave `20b3a upgrade-failure-surfacing` is implemented, fully delivery-reviewed and PAUSED under the operator-approved sequence. Re-derive every cited line anchor against the post-`20b3a` tree; line numbers in this document are advisory and symbols are the anchors. Re-Prepare these amended plans against that source before activation; all framework code edits require the root Stage Gate and applicable framework-edit authorization. Closure is not required or authorized.

Field report (upgrade 1.15.4 to 1.28.0, Windows): `migrate_review_plan_prompt` (`render_agent_surfaces.py:2627`, profile check from 2680, blocking `RuntimeError` at 2704-2711) refused a customized legacy prompt only in Phase 1 (`phase_surface_rendering`, `upgrade_wavefoundry.py:1931-1962`). By then Phase 0b had extracted the new framework files and Phase 0c (`review_policy_upgrade.py:136`) had marked 18 open waves for re-Prepare. The failure retained the upgrade lock with `failed_phase="surface_rendering"`. Verified at HEAD: `preflight_agent_surface_paths` (`render_agent_surfaces.py:4034-4048`) only checks path containment, and `upgrade_wavefoundry.py` has no reference to the migration, so neither `phase_preflight` (1629) nor `phase_dry_run` (1382) detects it. The error text says to resolve the fields manually and retry, but does not say a rerun is safe, and no recovery documentation exists.

The migration refuses in three groups, all invisible to preflight today: the pre-profile refusals at `render_agent_surfaces.py:2649-2679` (symlink, not a regular file, non-UTF-8), the both-prompts-exist message at 2641-2648, and the profile mismatch at 2680-2711. The check must cover all three, or "same blocking reason" cannot hold.

**Why the installed runner cannot carry the fix (verified at HEAD).** In the field case `phase_preflight` and `phase_dry_run` are the installed OLD runner; the pack cannot patch them, and they never import `render_agent_surfaces`. A `getattr`-tolerant call there degrades to "no detection" for exactly the field upgrade. A sanctioned incoming-pack seam already exists: `_load_extension_module` (`upgrade_wavefoundry.py:1179`) executes the pack's `upgrade_extensions.py` from the zip before extraction, and `_run_hook("post_preflight", ctx, ext_mod)` (6270) runs its `post_preflight(ctx)` (`upgrade_extensions.py:201`, which already stops protocol-1 runners) before the lock write (6311), before `plan_review_policy_upgrade` (6278), before extraction (6380) and before Phase 0c (6448). `_run_hook` turns a raised exception into `sys.exit(3)`. A release review diffed the v1.15.4 tag and found the same hook list and call (`post_preflight` at about 1157 and 4544 there), so the seam reaches a 1.15.4 runner.

**Why the hook cannot load the renderer (verified at HEAD).** `render_agent_surfaces.py` (lines 10-47) imports `contained_files`, `review_policy`, `review_policy_reconcile`, `history_paths`, `marker_namespaces`, `mcp_tool_extensions`, `record_paths` and `vocabulary_profile`. `_load_extension_module` executes a single source string into a bare module, so those siblings would resolve against the OLD installed scripts directory, where a 1.15.4 tree lacks `contained_files` and carries older versions of the rest. Loading the renderer from the zip is therefore not implementable, and the decision is closed: the hook runs a self-contained, standard-library-only checker.

Source-derived rerun condition: `review_policy_upgrade.plan_review_policy_upgrade` skips marking only when the migrated config is byte-identical, no carriers change, and the evaluator is current (`policy_unchanged and not stale_evaluator`). Policy/carrier edits or a stale evaluator can legitimately re-mark waves. Implementation must execute both conditions before recovery text claims a no-op rerun; this source trace is not execution evidence.

## Requirements

1. A new standard-library-only module, `review_plan_prompt_check.py`, holds the single shared logic: `REVIEW_PLAN_LEGACY_CONTRACT_PROFILES`, the old and new prompt constants (`REVIEW_PLAN_OLD_PROMPT`, `REVIEW_PLAN_NEW_PROMPT` or their current names in the renderer), and one classification function that takes the observed state of the old and new prompt paths (exists, symlink or reparse point, regular file, bytes) and returns pass or a blocking reason. `render_agent_surfaces.migrate_review_plan_prompt` imports and calls it, so the migration and the preflight check cannot diverge. The readers differ deliberately: the migration keeps its contained-path reader (`_contained_review_carrier_path`, `_read_move_source_identity`); the hook uses a plain `os.lstat`, `is_symlink`, `is_file` and UTF-8 read, which is read-only and accepts a weaker TOCTOU guarantee. The classification function is the only place the profiles and refusal reasons live.
2. The classification covers all three refusal groups: the pre-profile refusals (`render_agent_surfaces.py:2649-2679`: symlink, not a regular file, non-UTF-8), the both-prompts-exist case (2641-2648) and the profile mismatch (2680-2711). It treats these as PASS: old prompt absent with new prompt present; neither prompt present; only `review-plan.prompt.md` present (an idempotent retry after a partial Phase 1). On Windows the plain reader also refuses a reparse point (`st_file_attributes` with `FILE_ATTRIBUTE_REPARSE_POINT`, standard library only), because `is_symlink` does not report junctions.
3. Detection runs from the incoming pack: the pack's `upgrade_extensions.py` `post_preflight(ctx)` is restructured as `_check_protocol(ctx)` followed by `_check_review_plan_prompt(ctx)`. The new check runs after the protocol gate and before the existing early return (`upgrade_extensions.py` about 222-235, `if int(runner_protocol) >= minimum: return`), which would otherwise skip it on the happy path. The `bridge_release_required` refusal wins over the review-plan refusal when both apply.
4. The hook obtains the standard-library-only checker from the incoming pack using the existing `_incoming_framework_module` private zip loader; it must not import the renderer or resolve old installed siblings. If that loader cannot satisfy this contract after the predecessor rebase, the existing read-and-exec pattern is the fallback, not a second profile table. A missing or unloadable checker logs a warning and does not refuse (the admitted fail-open limit); a test pins that behavior. Roster membership does not make the checker a mandatory old-runner protocol-census module.
5. The hook refuses, by raising, before `write_upgrade_lock`, `plan_review_policy_upgrade`, extraction, Phase 0c or operating-document/wave writes. The checker itself performs no writes. Authorized runtime/lifecycle lock carriers, verified temporary pack staging and the predecessor's early diagnostic `upgrade.log` are permitted footprints and excluded from byte-invariance assertions. Do not move this check to `pre_extract`, which is after checkpoint publication. Before raising, emit a structured JSON error (`review_plan_prompt_migration_blocked`, offending path and recovery pointer) for old runners and wrappers.
6. Lock release. The predecessor now covers `_run_hook("post_preflight")` with the outer `main` `try/finally`: it releases the still-open lifecycle publication transaction and closes the log (`upgrade_wavefoundry.py:6767-6772`). Preserve and execute this existing release contract rather than adding a second local `__exit__` that could double-release. This protects the new runner and in-process callers; the old runner in the field window relies on process exit freeing the OS locks. `_run_hook` discards the hook's return value, so a dry-run-style return cannot refuse. The staged pack temporary copy precedes the hook; use its existing owned cleanup if exposed, otherwise record that specific leftover as a limit. Do not add another upgrade pass or cleanup service.
7. `phase_preflight` and `phase_dry_run` also call the shared check on the new-runner path, tolerating an installed tree that lacks `review_plan_prompt_check.py` (import guarded, as `phase_preflight` already guards `upgrade_lock_unreadable_cause` at about 1645). An absent module is not an error and is not the field-case guarantee.
8. The refusal message names the offending file, the unmatched contract labels or the structural reason, the supported manual recovery (write `docs/prompts/review-plan.prompt.md` from the packaged template, keep project aliases, remove the old prompt, update `docs/prompts/index.md` and the prompt manifest), and states whether a rerun is safe once the rerun-safety investigation has a result. The refusal is written to the upgrade log by the early log open of change `20b33-enh upgrade-failure-surfacing-log-and-child-output`. This is a hard dependency: when this change rebases on `20b3a`, the log open must precede the `post_preflight` hook.
9. Recovery is documented under a new heading in `docs/references/native-windows-support.md`, framed as the Windows field recovery, and platform-neutral text in `CHANGELOG.md`.
10. Behavior is the same on Windows, macOS, Linux and WSL2: the classification reads the prompt with the same newline handling the migration uses (`render_agent_surfaces.py:2672`, `line_content_and_ending`), so a CRLF checkout of a stock legacy prompt is classified as stock, not customized.

**Limits (stated, not hidden).**

- The hook runs only in a full upgrade with a pack (`ext_mod is not None`). The old runner's `--dry-run` runs only `post_extract(dry_run=True)` (about 1488-1532) and never `post_preflight`, so an old-runner dry run does not report this blocker. Do not treat `phase_dry_run` as precedent for a pre-extraction check.
- The seam reaches runners that already carry `post_preflight`. v1.15.4 was diffed and carries it (introduced by an earlier wave whose tag was not mapped); older runners get no early detection.
- Editing `docs/prompts/interrogate-plan.prompt.md` after the check passes and before Phase 1 is a TOCTOU window the plain reader does not close; Phase 1 still refuses, as today.

## Prompt-Surface Edits

This change writes no file under `docs/prompts/`. The operator-facing recovery instructs the operator to create `docs/prompts/review-plan.prompt.md` and edit `docs/prompts/index.md` and the prompt manifest; the change never writes them.

- Protected, read-only for every lane: the packaged template `.wavefoundry/framework/install/lifecycle-prompts/review-plan.prompt.md`, the seeds under `.wavefoundry/framework/seeds/`, and the operator's `docs/prompts/interrogate-plan.prompt.md` (the check reads it and never writes it).
- Write-owning (implementer only): `.wavefoundry/framework/scripts/review_plan_prompt_check.py` (new), `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/mcp_tool_extensions.py`, `.wavefoundry/framework/scripts/setup_readiness.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`, `docs/architecture/data-and-control-flow.md`, `docs/architecture/layering-rules.md`, `docs/references/native-windows-support.md`, `CHANGELOG.md`.
- Every reviewer lane is read-only; request security-reviewer for the incoming-code and path guards and docs-contract-reviewer for the behavior/recovery contract, in addition to code, QA, architecture, release and the full fixed-seat Council.

## Scope

**Problem statement:** A customized legacy review-plan prompt is discovered only after the upgrade has mutated the tree and marked waves, leaving a retained lock and a half-upgraded repository, and the installed runner in the field case cannot be patched to detect it.

**In scope:**

- The new standard-library-only check module and its single use by the migration.
- Detection from the incoming pack's `post_preflight` hook, plus the new-runner call in preflight and dry-run.
- The pre-profile refusals, the both-prompts-exist case and the profile mismatch.
- Lock release on the hook failure path in the new runner.
- A clear, actionable refusal message and the recovery documentation.
- Registering the new module wherever framework modules are listed.
- Tests, including a simulation of the old-runner window and the full-upgrade failure state.

**Out of scope:**

- Automatically migrating customized prompts (the operator owns project prose).
- Changing the set of recognized legacy profiles.
- Patching the already-installed runner.
- The interaction with CRLF checkouts beyond keeping the classification newline-stable (see the CRLF change in the windows-crlf-correctness wave).

## Acceptance Criteria

- [x] AC-1: A legacy runner/installed-tree fixture lacking the checker, with the incoming hook in its pack, refuses a customized legacy prompt at `post_preflight`. Framework and operating-document bytes are unchanged, no upgrade checkpoint or policy/wave mutation occurs, and the checker performs no writes. The fixture separately permits and checks only the authorized runtime locks, verified temporary staging and early diagnostic log footprint.
- [x] AC-2: A repository holding both `interrogate-plan.prompt.md` and `review-plan.prompt.md`, and one whose legacy prompt is a symlink (or a reparse point on Windows), not a regular file, or not UTF-8, is refused the same way with the same guarantees. The symlink case patches the symlink predicate or carries an explicit skip guard on hosts where creating a symlink needs privilege, the reparse-point case also runs on every platform through a patched `st_file_attributes` stat result, and the other refusal cases run on every platform.
- [x] AC-3: A repository with a stock legacy prompt (either recognized profile, LF or CRLF) passes the check and migrates exactly as before; old absent with new present, neither present, and only `review-plan.prompt.md` present all pass.
- [x] AC-4: A hook refusal leaves the lifecycle publication transaction released and the upgrade lock absent. Two tests: (a) a subprocess run of the upgrade asserts the refusal exit status, a structured JSON error on the output and a free lock afterwards; (b) an in-process call of `main` catches the `SystemExit`, then enters `lifecycle_lock.lifecycle_publication_transaction(root)` again and asserts `upgrade_lock_path` does not exist, exercising the new runner's explicit release.
- [x] AC-5: The refusal names the file, unmatched labels or structural reason and manual recovery steps. A rerun fixture with byte-identical migrated config, no carrier changes and a current evaluator does not re-mark waves; separate stale-evaluator and changed-carrier/policy fixtures assert the legitimate re-mark behavior. The recovery sentence states these conditions instead of promising every rerun is a no-op.
- [x] AC-6: A test drives `phase_surface_rendering` directly with preflight bypassed (simulating the old-runner window, where no early detection exists) and asserts the state it leaves behind: the `failed_phase="surface_rendering"` lock, the extracted tree and the marked waves. It is explicitly the old-runner simulation, not a requirement that the defect persist.
- [x] AC-7: With a new-runner preflight and the check module present, `phase_preflight` and `phase_dry_run` refuse the same cases; with the module absent from the installed tree they do not crash.
- [x] AC-8: The recovery heading exists in `docs/references/native-windows-support.md` and a platform-neutral `CHANGELOG.md` `[Unreleased]` bullet exists; the bullet states the old-code-window limit.
- [x] AC-9: The checker imports only the standard library, proven in a restricted-import subprocess, and the migration and incoming hook call the same classification function and profile table. Missing-checker warning, loader isolation and protocol-before-prompt precedence are tested without embedding a second table.
- [x] AC-10: `review_plan_prompt_check.py` is registered in the framework module roster and source-file list and ships in the pack and manifest (a test asserts the pack and manifest include it), and a bridge refusal still wins over the review-plan refusal when both apply. A test also runs the real old-runner pack validation over a pack that contains the new module (`layering-rules.md` line 23 records that installed 1.25 and 1.26 runners count flat modules during pack validation, so the new flat module must be safe to ship), using the same census that `test_server_package` applies to the mandatory modules.

## Tasks

- [x] Before message authoring, execute current-evaluator/no-change and stale-evaluator/carrier-policy-change rerun fixtures against `plan_review_policy_upgrade`; record the conditional result for AC-5.
- [x] Create `review_plan_prompt_check.py` and move the profile table, constants and classification into it; make `migrate_review_plan_prompt` call it.
- [x] Restructure `post_preflight` in `upgrade_extensions.py` as `_check_protocol` then `_check_review_plan_prompt`, ahead of the early return, loading the checker privately from the incoming zip per Requirement 4; print the structured JSON error before raising.
- [x] Preserve and test the existing outer transaction release around `_run_hook("post_preflight")`; confirm and record owned staged-copy cleanup, without a second transaction exit.
- [x] Wire the new-runner call into `phase_preflight` and `phase_dry_run` with a guarded import.
- [x] Rewrite the refusal message per Requirement 8.
- [x] Register the new module in the module roster (`mcp_tool_extensions.py`, about lines 225-240), the readiness source-file list (`setup_readiness.py` `SOURCE_FILES`, about lines 41-48) and confirm the pack and manifest include it; record the readiness source-digest effect.
- [x] Add tests for AC-1 to AC-10 beside `test_customized_old_only_is_non_successful_and_mutates_no_prompt` in `tests/test_upgrade_wavefoundry.py`, with the named old-runner fixture (legacy runner stub, installed tree without the check module, pack zip carrying the new hook).
- [x] Update `docs/architecture/data-and-control-flow.md` (upgrade section, about lines 429-445) with the `post_preflight` refusal and its position before the lock write, and `docs/architecture/layering-rules.md` with the `upgrade_extensions` to check-module dependency and the release of the transaction on the `sys.exit(3)` path.
- [x] Write the recovery paragraph under a new heading in `docs/references/native-windows-support.md` and the `CHANGELOG.md` bullet.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| rerun-safety verification | implementer | none | gating; feeds message and AC-5 |
| check module and migration refactor | implementer | none | independent of wave 20b3a |
| incoming-pack hook and lock release | implementer | check module | independent of wave 20b3a except the log-open dependency in Requirement 8 |
| new-runner wiring | implementer | check module | preflight and dry-run |
| module registration | implementer | check module | roster, source list, pack |
| tests and docs | implementer | hook, wiring, registration | includes the old-runner simulation |


## Serialization Points

- `.wavefoundry/framework/scripts/review_plan_prompt_check.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`, `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `docs/architecture/data-and-control-flow.md`, `docs/architecture/layering-rules.md`, `docs/references/native-windows-support.md`

`CHANGELOG.md` also changes (root-level file, so not a declared target). `upgrade_wavefoundry.py` and `upgrade_extensions.py` are also edited by the upgrade-failure-surfacing wave (`20b33`, `20b34`); that wave is implemented, delivery-reviewed and paused first and this change rebases on it. Within this wave, order this change before `20b36`, which edits `upgrade_extensions.py` at the index-guard call site.

## Affected Architecture Docs

Update (mandatory, not conditional): `docs/architecture/data-and-control-flow.md` (upgrade section, about lines 429-445) gains the `post_preflight` review-plan refusal and its position before the lock write, Phase 0c and extraction; `docs/architecture/layering-rules.md` gains a row for the `upgrade_extensions` to `review_plan_prompt_check` dependency (a standard-library-only module loaded from the pack; the row states that it is not an upgrade-mandatory module and is loaded only by the incoming extension) and states that the `sys.exit(3)` refusal path releases the lifecycle publication transaction (Requirement 6). The change adds no boundary beyond the existing extension-hook seam, but it adds a pre-extraction check that gates the lock write, which is an upgrade-phase-order fact the docs must record.

## AC Priority


| AC    | Priority  | Rationale |
| ----- | --------- | --------- |
| AC-1  | required  | The core defect on the field upgrade path. |
| AC-2  | required  | Same defect, the other refusal triggers. |
| AC-3  | required  | Must not regress stock migration or an idempotent retry. |
| AC-4  | required  | A refusal must leave nothing held or changed. |
| AC-5  | important | Message and rerun claim must be true. |
| AC-6  | important | Pins the late-failure state of an old runner. |
| AC-7  | important | New-runner path and old-code-window tolerance. |
| AC-8  | important | Operators recover from docs when the message is not enough. |
| AC-9  | required  | The hook must run without sibling imports, and the two copies must not drift. |
| AC-10 | important | A new module that is not registered or shipped breaks the pack. |


## Progress Log

Qualification repair verified — 2026-10-10: the combined integrated repair passes 80 focused tests in 13.954 seconds with no skips. For this change, both fixture paths now use configured roots and record names; the two censuses retain unchanged detection/assertion code with only existing stock-message owners moved; live recovery names the legacy prompt through the refusal. The scratch two-fixture relocated/renamed run passes, and all seven original/unlisted-literal and retired-reference controls assertion-fail then restore. No production preflight or census behavior was loosened. Full qualification and independent delivery review remain pending.

Readback, qualification repair — 2026-10-10: the complete canonical run identified five hard-coded test-layout literals, stock-message classifications still owned by the renderer after extraction to the checker, and a retired prompt filename in live recovery prose. Derive the two fixtures' roots/record names from the existing profile APIs; move only the exact existing message classifications in the record/vocabulary censuses; describe the legacy prompt by the refusal-reported path. Keep production behavior, every census assertion, the declaration component explanation and all skips unchanged. Scratch verification passes 35 tests and two relocated/renamed-record controls; seven named bad/unlisted controls fail and are restored. This is implementation qualification repair, not delivery approval.

Qualification fixture repair — 2026-10-10: the coordinator's full-suite run caught the unclassified declaration literal in `test_rerun_safety_real_planner_conditional_marks` (formerly line 3705). With the failed run stopped and the gate reopened for this hunk only, added one immediately adjacent `component-fixture` comment explaining that the empty evidence projection tests policy-migration planning and claims no readiness/delivery validity. Literals, code, assertions and the declaration census are unchanged. Before/after `ast.dump(..., include_attributes=False)` is identical (SHA256 `beb6547bf8bed7206fca6357655252b5c91674a94865fd7658271473c986485b`), and before bytes equal the original frozen fixture. The 13 declared-fixture tests plus the named policy-planner test pass (14 tests, 2.021 seconds, no skips); the original frozen fixture still fails the exact census test (1 test, 1.384 seconds) on that sole unclassified literal. Current test-file SHA256 is `5ffe2f8a8457d1a7302f5adf9d079a8107d32f335d8de959e3086876517fdfab`. Supplemental packet: `/private/tmp/wf20b3b-upgrade-fixture-supplement.json`. Full qualification remains coordinator-owned; this narrow correction does not weaken the census or alter earlier behavior evidence.

Implementation — shared stdlib checker/profiles now own all migration refusals; renderer keeps contained identity reads, incoming hook gates protocol first, installed preflight/dry-run tolerate a missing module. Current main and fresh subprocess refuse before checkpoint/policy writes; child lock acquisition after in-process refusal proves release, and the separate TMP proof permits owned staged cleanup. Actual v1.15.4 loader/hook functions and complete protocol validator are byte-identical historical fixtures, not a full old installed-process qualification. Pack collector/manifest producer and mandatory flat-import census include the new helper; readiness source identity changes intentionally. The direct old-window Phase-1 fixture retains the extracted VERSION, marked wave and failed_phase=surface_rendering through the actual finalizer.

Guard controls — removing incoming `_check_review_plan_prompt` makes `test_actual_v1_15_4_zip_loader_and_hook_refuse` fail (SystemExit missing); allowing linked legacy entries makes `test_checker_structural_refusals_and_stock_newline_profiles` fail (blocked=False). Both restored before green rerun. The earlier remove-link branch-only control errored on absent read bytes and is diagnostic only, superseded by the explicit fail-open mutant. Architecture checked/changed: layering rules and data/control flow; Windows recovery plus shared CHANGELOG describe bounded compatibility, old dry-run, missing-checker and TOCTOU limits. Native Windows execution, full canonical qualification and independent delivery lanes remain root-owned/pending.

Readback — 2026-10-10: customized legacy prompts currently fail after extraction/policy marking; the incoming protocol-first hook will refuse before checkpoint, framework and operating-doc mutation. AC-1–10 cover shared stdlib profiles/classifier, contained renderer reads, guarded new-runner preflight/dry-run, release, conditional recovery and package/legacy compatibility. Affected files: checker, renderer, upgrade runner/extensions, module/source rosters, focused tests and owned architecture/Windows recovery docs. No prompt, seed, template or unrelated state writes. Live MCP navigation confirmed callable; producer index is stale, so source facts use current reads.

Premise execution — current planner with temporary real wave/config and injected receipt/carrier observations: current evaluator plus byte-identical policy/no carriers plans zero waves; stale evaluator, changed carrier and changed policy each plan one wave. Rerun guidance therefore promises safety after manual repair but says re-Prepare is skipped only when those no-change/current conditions hold. No production source edits preceded this probe.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-10 | Planned from upgrade field feedback; claims verified read-only against HEAD. | file:line citations in Rationale |
| 2026-10-10 | Readiness repair: old-code-window question settled in favor of the incoming-pack extension seam; scope extended to the pre-profile refusals. | red-team and docs-contract readiness reviews |
| 2026-10-10 | Confirming-round repair: the hook is a self-contained standard-library-only checker (the renderer cannot be loaded from the zip); lock release made a required wrapper; dry-run-style return dropped; limits stated; module registration and architecture docs made mandatory. Product Intent: waived (bug fix, no product scope). | confirming readiness reviews of all six lanes |
| 2026-10-10 | Plan amended: predecessor reviewed/paused sequence; authorized early footprint excluded from invariance; current evaluator/carrier rerun condition and private stdlib loader fixed. No implementation claimed. | `plan_review_policy_upgrade`, `_incoming_framework_module`, root Stage Gate; operator direction |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-10 | Divergent pre-plan. Approach A: factor a read-only check in the installed renderer and call it from preflight with `getattr` tolerance. Approach B: load the incoming pack's renderer and run its check before extraction. Approach C: only improve the Phase 1 message and docs. Approach D: a self-contained standard-library-only checker module shared with the migration and run from the incoming `post_preflight` hook. SELECTED D, with A kept as the new-runner path only. | The field case is an installed 1.15.4 runner whose `phase_preflight` and renderer cannot be patched, so A alone degrades to no detection there. B is not implementable: the renderer imports eight sibling modules that resolve against the old installed tree. D runs pack code through the existing sanctioned seam before the lock, extraction and Phase 0c, needs no new trust boundary, and a single shared classification function keeps the hook and the migration equal. | A alone misses the field case; B cannot import the renderer's siblings; C does not fix the defect. Embedding the table in `upgrade_extensions.py` is the recorded fallback if the zip read-and-exec pattern cannot be reused for a second member, guarded by the AC-9 parity test. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The hook exit leaves the lifecycle publication transaction held in-process. | Requirement 6 wrapper and AC-4 (subprocess and in-process cases); the old runner relies on process exit. |
| The hook cannot import what it needs from the old installed tree. | Standard-library-only module, loaded by read-and-exec; AC-9. |
| The check and the migration drift apart. | One shared classification function; parity test if embedded (AC-9). |
| CRLF checkout makes a stock prompt look customized. | Same newline handling as the migration; test both endings (AC-3). |
| A rerun after the manual fix re-marks waves. | Gating prerequisite task; the message does not claim rerun safety until verified (AC-5). |
| The new module is missing from the module roster, source list or pack. | Task and AC-10. |
| An old-runner dry run does not report the blocker. | Stated in the Limits paragraph and the CHANGELOG bullet. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
