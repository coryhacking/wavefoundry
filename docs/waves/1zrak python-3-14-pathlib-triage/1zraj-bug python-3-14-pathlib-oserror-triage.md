# Triage Framework Guards That Rely On Pathlib Predicates Raising, Which Python 3.14 Stopped Doing

Change ID: `1zraj-bug python-3-14-pathlib-oserror-triage`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-10-04
Wave: 1zrak python-3-14-pathlib-triage

## Rationale

Python 3.14 reimplemented `pathlib.Path.exists`, `Path.is_symlink`, `Path.is_file` and `Path.is_dir` on top of `os.path`, and they now return `False` on any `OSError`. Python 3.11 through 3.13 raised every error other than not-found. Probe (mode-0 parent directory, macOS): the four predicates raise `PermissionError` (errno 13) on 3.11.17 and 3.13.16 and return `False` on 3.14.8, while `os.lstat`, `os.path.realpath(strict=True)` and `Path.resolve(strict=True)` raise on all three.

Code that wraps one of those predicates in a `try` and treats an `OSError` as "cannot determine, refuse" silently changes meaning on 3.14: the handler becomes unreachable for that call and an undetermined path reads as absent or not-a-symlink. Change `1zrai-bug python-3-14-suite-compatibility` found and fixes one such guard, `review_evidence._review_authority_path_error`, where the authority guard passed an undetermined path. The same shape may exist in other security, authority and containment guards, where failing open matters most. 3.14 is inside the supported range (3.11 through 3.14), so any such site is a product defect on a supported interpreter.

## Requirements

1. Every call site in the starting census is classified as one of: defect (the code relies on the predicate raising to refuse or to report), benign (the handler exists for other calls, or `False` is the correct reading of an undetermined path), or needs-decision.
2. Security, authority and containment guards are triaged first, and every defect among them is fixed in this change.
3. A fix determines path state with `os.lstat` (or `os.stat` where following links is intended) under one errno rule, the pattern of `review_evidence._authority_member_lstat` (wave `1zqe4`): `FileNotFoundError` (ENOENT; Windows WinError 2 and 3) and `NotADirectoryError` (ENOTDIR) mean absent, and every other `OSError` propagates to the guard's refusal branch, including ELOOP, EACCES, EBADF and Windows WinError 21, 123 and 1921. `path_containment.contained_path` keeps its stricter handling: in its symlink-component walk only `FileNotFoundError` reads as absent, and every other `OSError` maps to `None`.
4. Defects outside the guard set are fixed here when the fix is local, or recorded as named follow-ups with the operator's agreement.
5. Behaviour is the same on Windows, macOS, Linux and WSL2 and on Python 3.11 through 3.14: every guard defect refuses an undetermined path under the errno rule in Requirement 3. This is deliberately stricter than 3.11 to 3.13, whose predicates read ENOENT, ENOTDIR, EBADF and ELOOP and Windows WinError 21, 123 and 1921 as absent; ELOOP, EBADF and those winerrors now refuse.
6. `upgrade_wavefoundry._retired_sidecar_path_error` refuses an undetermined path and its refusal message carries no absolute path.

## Scope

**Problem statement:** framework code written for 3.11 through 3.13 may rely on `pathlib` predicates raising `OSError`; on 3.14 they return `False`, and guards that should refuse an undetermined path may pass it instead.

**Starting census.** Predicate: a call to `.exists()`, `.is_symlink()`, `.is_file()` or `.is_dir()` with no arguments, not on `os.path`, inside the body of a `try` whose handlers catch `OSError`, `PermissionError`, `Exception` or `BaseException`, in a non-test `.py` file under `.wavefoundry/framework/scripts/` (AST scan at commit `56cd3e4c`, 2026-10-04). Result: 131 unique call sites in 35 files. A count by call-and-try pair, where a call nested in two qualifying `try` blocks counts twice, gives 136. AC-1 uses the unique call-site count.

- Per file (unique call sites): `setup_readiness.py` (18), `wf_server/server_impl.py` (16), `model_bundle.py` (9), `record_paths.py` (9), `upgrade_wavefoundry.py` (9), `context_efficiency.py` (7), `setup_index.py` (6), `wf_server/memory_handlers.py` (6), `accel_embedder.py` (4), `render_agent_surfaces.py` (4), `graph_indexer.py` (3), `indexer.py` (3), `memory_backfill.py` (3), `memory_supply.py` (3), `upgrade_extensions.py` (3), `wf_server/index_handlers.py` (3), `gen_codebase_map.py` (2), `render_platform_surfaces.py` (2), `techdocs_audit_lib.py` (2), `upgrade_bridge_bootstrap.py` (2), `wave_lint_lib/secrets_validators.py` (2), `wf_server/context_efficiency_handlers.py` (2), and one each in `index_paths.py`, `index_state_store.py`, `memory_records.py`, `prune_framework.py`, `review_policy_upgrade.py`, `run_secrets_scan.py`, `scan_secrets.py`, `setup_reconciliation.py`, `setup_wavefoundry.py`, `sqlite_storage_migration.py`, `subprocess_util.py`, `wave_lint_lib/wave_validators.py` and `wf_server/codenav_handlers.py`. `review_evidence.py` is 0: `1zqe4` moved its authority guard to `os.lstat`.
- Guard-named subset (predicate: the census restricted to functions whose name matches `safe|symlink|authority|contain|escape|guard|refuse|reject|resolv|trust|scope|allowed|root`): 10 calls in 6 functions. `context_efficiency.contained_stat_signature` (1), `context_efficiency._contained_prompt` (1), `context_efficiency.resolve_open_wave` (1), `memory_backfill._contained_source_file` (3), `memory_supply._contained_source_file` (3) and `setup_index._merged_trust_bundle` (1).
- Spot-check of the six (read at `56cd3e4c`): all benign. `contained_stat_signature`, `_contained_prompt` and both `_contained_source_file` run a strict `resolve(strict=True)` first, which raises on an undetermined path, and a `False` predicate result returns the fail-closed value; `resolve_open_wave` returns `None` (no attribution) when `is_dir()` reads `False`, the same as its failure path; `_merged_trust_bundle`'s handler covers `read_text` and `mkdir`, not a guard predicate.
- Known AC-2 defect: `upgrade_wavefoundry._retired_sidecar_path_error` (not guard-named). Probe with a mode-0 `docs/`: on 3.14.8 `waves_dir.is_symlink()` and `waves_dir.exists()` read `False` and it returns `None`, so the caller skips cleanup silently; on 3.13 it refused with "retired sidecar path is not safely resolvable". Its refusal message also interpolates `{exc}`, which carries an absolute path, against the path-free rule. Both are fixed in this change.
- AC-2 candidate to classify: `server_impl._archive_root_real`, which calls `roots.archive.is_dir()` and `is_symlink()` outside any `try`.
- Census limits. Membership is not evidence of a defect: most handlers exist for other calls in the same block. The predicate misses guards whose names do not match the pattern and predicates called outside a `try` (where 3.13 propagated the error to a caller's handler). `os.path.exists`, `os.path.isfile`, `os.path.isdir` and `os.path.islink` are excluded throughout: they never raised on any supported interpreter, so their behaviour is unchanged. Triage re-derives the guard set by the method below, not by the name filter.

**Guard re-derivation method (AC-2), sink-first and bounded:**

1. Find refusal sinks: non-test functions under `.wavefoundry/framework/scripts/` with an `OSError`, `Exception` or `BaseException` handler that returns or raises a refusal or error value (a message string, an error envelope, a refusal exception or a fail-closed sentinel).
2. Read each sink and its depth-1 callees (`code_callhierarchy`, outgoing) for `exists`, `is_symlink`, `is_file` and `is_dir` calls whose error reached that handler on 3.13.
3. Check every caller of `path_containment.contained_path` and `contained_resolved_path` (7 non-test files at `56cd3e4c`: `context_efficiency.py`, `memory_backfill.py`, `memory_records.py`, `memory_supply.py`, `render_agent_surfaces.py`, `review_policy.py`, `wf_server/server_impl.py`) and every `is_symlink()` call anywhere in non-test framework code.
4. Record the sink predicate, the number of sinks, callees and `is_symlink()` calls examined, and each guard found with its classification.

**In scope:**

- Classify all 131 census sites, guard set first.
- Re-derive the guard set by the sink-first method, including predicates outside a local `try` whose error reached a caller's refusal handler on 3.13.
- Fix every guard defect, with a pin per fix that goes red on 3.14 against the unfixed code and a platform-independent `os.lstat` pin.
- Fix `upgrade_wavefoundry._retired_sidecar_path_error`, including a path-free refusal message.
- Fix local non-guard defects; record the rest as named follow-ups.

**Out of scope:**

- `review_evidence._review_authority_path_error`, fixed by `1zrai-bug python-3-14-suite-compatibility`.
- Test files under `.wavefoundry/framework/scripts/tests/`, except pins this change adds.
- A blanket rewrite of benign sites for style.

## Triage

**Census re-run at implementation time** (tree at `56cd3e4c`, 2026-10-04, same predicate and AST scan as Scope): 131 unique call sites in 35 files; 136 call-and-try pairs. After the fixes below the same scan finds 116 unique sites in 32 files (121 pairs). Line numbers in this section are at `56cd3e4c`.

**Defects (15 sites, all fixed in this change).** Each fix determines path state with `os.lstat` (link-level checks) or `os.stat` (where the replaced predicate followed links) under the Requirement 3 errno rule.

| Site | Function | Kind | Reason |
| --- | --- | --- | --- |
| `upgrade_wavefoundry.py:2105`, `:2107`, `:2112`, `:2114` | `_retired_sidecar_path_error` | guard | 3.14 read an uninspectable `docs/waves` or sidecar as absent and returned `None`, so the cleanup skipped silently or deleted a sidecar the guard never proved; the refusal interpolated `{exc}` with an absolute path. |
| `upgrade_wavefoundry.py:2244` | `phase_review_evidence_sidecar_cleanup` | guard | `candidate.exists()` after the guard; now the same `os.lstat` rule, and every exception-derived `SystemExit` in the phase is path-free and names the member, cause and recovery (AC-9). |
| `index_paths.py:82` | `_present` | guard | Its docstring relies on `is_file()` raising to fail closed; 3.14 read an undecidable probe as absent, the one state that authorizes creating a database over an existing file. |
| `review_policy_upgrade.py:65` | `plan_review_policy_upgrade` | guard | Preflight refused ("cannot preflight workflow config") only when `exists()` raised; 3.14 planned over an uninspectable config as `{}`. `apply_review_policy_upgrade:149` (outside the `try`) is fixed the same way. |
| `setup_wavefoundry.py:220` | `_provision_workflow_defaults_if_absent` | guard | Refused only when `is_file()` raised; 3.14 replaced an uninspectable (for example symlinked) config with the defaults alone. |
| `upgrade_wavefoundry.py:441` | `_scan_dir_entries` | report | Records an inaccessible pack-search location only when `is_dir()` raised; 3.14 skipped it silently. |
| `indexer.py:1673` | `_remove_legacy_meta_json` | report | The LOUD warning fired only when `is_file()` raised; 3.14 skipped silently. |
| `setup_index.py:1923` | `_model_cache_corruption_reason` | report | "snapshot onnx directory unreadable" fired only when `is_dir()` raised; 3.14 passed an unreadable snapshot as healthy. |
| `upgrade_extensions.py:1452` | `repair_declaring_scaffold` | report | "could not be repaired" fired only when `is_file()` raised; 3.14 skipped an uninspectable template silently. |
| `wf_server/memory_handlers.py:2173`, `:2177`, `:2183` | `memory_consolidate_response` | report | The rollback reported `rollback_completed: true` while a member it could not inspect remained; 3.13 reported it incomplete. |

**Needs-decision (resolved 2026-10-04: the operator chose to fix all three in this wave as `1zu4y-bug python-3-14-discovery-lint-removal-fail-open` rather than defer them).** None is in the census; all came from the sink-first re-derivation below.

| Site | Function | Reason | Proposed follow-up |
| --- | --- | --- | --- |
| `record_paths.py:486`, `:515` | `walk_wave_candidates`, `discover_archive_dirs` | Outside any `try`: an uninspectable waves or archive root reads as "no waves" on 3.14, where 3.13 raised to the callers' handlers. Not local: every lifecycle tool, lint and the memory backfill share this discovery path, so the fix needs a refuse-or-report decision across callers. | Follow-up change: discovery roots under the errno rule, with a decided refuse-or-report contract for an uninspectable root. |
| `wave_lint_lib/docs_constants_validators.py:122`, `wave_lint_lib/wave_validators.py:1997` | `_framework_internal_constants_enabled`, `check_memory_docs` | Docs-lint presence probes: an uninspectable `docs/workflow-config.json` silently disables the internal-constants check, and uninspectable legacy pointer residue passes. Needs a decision on whether an uninspectable input is a lint ERROR. | Follow-up change: docs-lint presence probes under the errno rule, reporting an uninspectable input as an ERROR. |
| `indexer.py:4083` | `_validate_prepared_removals` | The requested-file filter drops an uninspectable requested file, which may then read as removed. Needs a decision on whether it is removed or unreadable (cf. the `unreadable_files` set from wave 1zime). | Follow-up change: classify an uninspectable requested file as unreadable, not removed. |

**Benign census sites, grouped by reason (116 sites).**

| Group | Reason | Sites | Per file |
| --- | --- | ---: | --- |
| B1 | No behaviour change: the handler yields the same result as a `False` reading (or the code already caught `OSError` into that value). | 50 | `wf_server/server_impl.py` 15, `record_paths.py` 9, `model_bundle.py` 3, `render_agent_surfaces.py` 3, `wf_server/index_handlers.py` 3, `context_efficiency.py` 2, `gen_codebase_map.py` 2, `graph_indexer.py` 2, `render_platform_surfaces.py` 2, `techdocs_audit_lib.py` 2, `prune_framework.py` 1, `run_secrets_scan.py` 1, `scan_secrets.py` 1, `subprocess_util.py` 1, `wave_lint_lib/wave_validators.py` 1, `wf_server/codenav_handlers.py` 1, `wf_server/memory_handlers.py` 1 |
| B2 | A strict check on the same path (`resolve(strict=True)`, `os.lstat`, or an lstat-based `_safe`) raises into the same refusal. Includes the six guard-named spot-check functions except `resolve_open_wave` and `_merged_trust_bundle`. | 12 | `memory_backfill.py` 3, `memory_supply.py` 3, `context_efficiency.py` 2, `upgrade_wavefoundry.py` 2, `sqlite_storage_migration.py` 1, `wf_server/context_efficiency_handlers.py` 1 |
| B3 | The guarded operation itself (read, write, unlink, `mkdir`, `scandir`, rename) targets the same path and fails into the same handler. | 20 | `accel_embedder.py` 4, `model_bundle.py` 6, `setup_index.py` 3, `wf_server/memory_handlers.py` 2, `context_efficiency.py` 1, `indexer.py` 1, `memory_records.py` 1, `upgrade_bridge_bootstrap.py` 1, `wf_server/context_efficiency_handlers.py` 1 |
| B4 | Optional or advisory: `False` skips a best-effort, heuristic or advisory step, and no refusal or report depends on it. Includes `server_impl._prepare_council_verdict_locations` (`:9965`): on 3.14 an uninspectable wave change doc falls through to the plan-path candidate, and the result only locates advisory verdict lines. | 6 | `graph_indexer.py` 1, `index_state_store.py` 1, `render_agent_surfaces.py` 1, `setup_reconciliation.py` 1, `upgrade_extensions.py` 1, `wf_server/server_impl.py` 1 |
| B5 | Path or its parent already proven reachable by the same code: `setup_readiness.assessment_signature` stats the probed paths first and turns any error but not-found into an indeterminate result (`index.sqlite-shm` and the `.claude`, `.codex`, `.cursor` and `.junie` directories are not in the signature, but their parent is: the `-wal` sibling and the repository root); the framework tree the upgrade runs from or just extracted; the context-efficiency store open in the same directory as its gap sentinel; an `rglob` entry inside a directory just stat'd. | 23 | `setup_readiness.py` 18, `context_efficiency.py` 2, `setup_index.py` 1, `upgrade_extensions.py` 1, `upgrade_wavefoundry.py` 1 |
| B6 | `False` still fails closed: it refuses, reports a corruption reason, or fails a downstream identity check. | 5 | `wave_lint_lib/secrets_validators.py` 2, `indexer.py` 1, `setup_index.py` 1, `upgrade_bridge_bootstrap.py` 1 |

Totals: 15 defects + 0 needs-decision census sites + 50 + 12 + 20 + 6 + 23 + 5 benign = 131 unique call sites.

**Guard-named spot-check confirmed:** `contained_stat_signature`, `_contained_prompt` and both `_contained_source_file` are B2 (strict `resolve` first); `resolve_open_wave` is B1 (`None` either way); `_merged_trust_bundle` is B3 (the write fails into the same handler).

**Sink-first re-derivation (AC-2).** Sink predicate: a non-test function under `.wavefoundry/framework/scripts/` with a `try` whose handler catches `OSError`, `PermissionError`, `Exception` or `BaseException` and whose handler body returns or raises. Depth-1 callees: calls in that `try` body to a function defined in the same module, or `<module>.<function>` on a sibling script, resolved by AST (a `code_callhierarchy` call per sink was impractical at this count; see the `Gapfill:` row). Totals at `56cd3e4c`: 786 sink `try` blocks, 392 distinct depth-1 callees examined, 51 callees holding 95 predicate calls outside any qualifying `try`. Containment-helper callers: 12 call sites in the 7 files named in Scope; none feeds a pathlib predicate into the containment decision (they resolve and then call the helper). `is_symlink()` sweep: 47 calls in 31 functions in non-test framework code.

Guards found and their classification:

| Guard | Source | Classification |
| --- | --- | --- |
| `upgrade_wavefoundry._retired_sidecar_path_error` | census, known | defect, fixed |
| `server_impl._archive_root_real` | Scope candidate (`is_dir()`, `is_symlink()` outside a `try`) | benign: a `False` reading returns `None`, the fail-closed value (the archive is not read), and `resolve(strict=True)` backs it |
| `index_paths._present` | census | defect, fixed |
| `upgrade_lib.read_upgrade_lock` | sink-first (`exists()` at `:63`, outside a `try`) | defect, fixed: an undetermined lock reads as present (`{}`). `upgrade_lib.upgrade_lock_unreadable_cause` tells it from a corrupt lock, so it is never stale and never rewritten, and setup, the storage-migration setup check and upgrade preflight refuse with a path-free message naming `.wavefoundry/upgrade-in-progress.json`, the errno cause and the recovery (restore access, or remove it if no upgrade is running) instead of "foreign upgrade" or "already in progress"; the dashboard stays paused and `wf_upgrade_status` adds a `lock_unreadable` field |
| `memory_backfill._canonical_waves_dir` | sink-first (`exists()`/`is_symlink()` at `:143`) | defect, fixed: an undetermined root raises under its `OSError` contract instead of reading as "no waves" |
| `memory_records.resolve_purge_memory_source` | `is_symlink()` sweep (`:846`) | defect, fixed: a body it cannot inspect no longer hides from "refusing to guess" |
| `review_policy_upgrade.apply_review_policy_upgrade` | sink-first (`:149`) | defect, fixed with the preflight |
| `upgrade_wavefoundry.materialize_lifecycle_policy` | sink-first (`:4801`) | defect, fixed: refuses (path-free) instead of overwriting an uninspectable config |
| `setup_readiness.assess_setup` | census (18 sites) | benign B5 |
| `memory_supply._contained_dirs`, `sqlite_storage_migration.read_receipt`, `upgrade_bridge_bootstrap._safe_wavefoundry_dir` and `_retain_feature_archive` | sink-first, `is_symlink()` sweep | benign: strict `resolve`, lstat-based `_safe`, or a `False` reading that refuses |
| `record_paths.walk_wave_candidates`, `discover_archive_dirs` | sink-first | needs-decision (above) |
| `memory_backfill._connect`, `memory_records._purge_disposition_path`, `rebuild_archive_manifest`, `migrate_legacy_memory_pointers`, `render_agent_surfaces._skill_path_has_symlink_component`, `migrate_review_plan_prompt`, `review_policy.contained_relative_path`, `upgrade_wavefoundry._old_manifest_snapshot`, `upgrade_extensions._preserve_original_manifest`, `accel_embedder._prune_superseded_coreml_entries`, `sqlite_storage_migration.detect` | `is_symlink()` sweep | benign: the following read, write or rename on the same path fails, nothing is deleted on a `False` reading, or authority comes from `index_paths._present` (fixed) |

The remaining sink-first callees are benign by the same groups: the running or just-extracted framework tree (upgrade phases, hooks, `_preferred_python`, `setup_reconciliation.framework_fingerprint`, `_get_index_state_store`), a `False` reading that fails closed (`context_efficiency._try_lock_lease` reads indeterminate, `_generate_wf_close_wave_summary`, `setup_index._uv_config_args` keeps `--no-config`), or a follow-up operation that fails on the same path (`sqlite_runtime.connect`, `setup_index._mkdir_private`, `model_bundle._normalize_refs_in_place`, the context-efficiency gap functions, `register_mcp_surface`, `gen_codebase_map`, `graph_call_census`, `repair_ppol_memory_staging`).

**Platform behaviour per fix.** Every fix uses `os.lstat` or `os.stat` and the same errno rule, so behaviour is identical on Windows, macOS, Linux and WSL2 and on Python 3.11 through 3.14: `FileNotFoundError` (ENOENT; Windows WinError 2 and 3) and `NotADirectoryError` read as absent; EACCES, ELOOP, EBADF and Windows WinError 21, 123 and 1921 refuse or report. On macOS, Linux and WSL2 the mode-0 pins exercise a real untraversable parent and skip under root. On Windows `chmod 0` does not deny traversal, so the mode-0 pins skip on `nt` and each fix's patched-stat pin covers it; symlink-dependent pins (the symlinked-config fixtures) also skip when `os.symlink` raises `OSError` for lack of privilege. Per fix: the sidecar cleanup, purge-body and historical-memory checks use `os.lstat` (they must see a link itself); `index_paths._present`, `read_upgrade_lock`, the three config readers, `_scan_dir_entries`, `_remove_legacy_meta_json`, `_model_cache_corruption_reason`, `repair_declaring_scaffold` and the consolidation rollback use `os.stat` (the replaced predicate followed links), and their platform-independent pins patch `os.stat` (the link-following form only).

**Pin independence (disclosed at delivery review).** For `memory_backfill._canonical_waves_dir` and the sidecar guard's `docs/waves` and candidate checks, the patched-`os.lstat` pins also pass against a revert of the fix, because the guard's own `resolve(strict=True)` lstats the same path and raises into the same refusal. Only the mode-0 pins kill those reverts, and they skip on Windows. So on Windows a reverted guard still refuses an access-denied path through `resolve(strict=True)`, but no Windows-run pin would catch the revert itself.

## Acceptance Criteria

- [x] AC-1: A grouped triage table in this change doc lists every defect and needs-decision site individually (file:line, function, reason) and groups benign sites by reason with per-file counts, and the group totals add up to the census total of unique call sites.
- [x] AC-2: The guard set is re-derived by the sink-first method in Scope, the predicates and totals examined are recorded, and every guard found (including `upgrade_wavefoundry._retired_sidecar_path_error` and `server_impl._archive_root_real`) is listed with its classification.
- [x] AC-3: Every guard defect refuses an undetermined path under the stated errno rule on Python 3.11 through 3.14.
- [x] AC-4: Every fixed defect has a pin that fails on Python 3.14 against the unfixed code, plus one platform-independent pin that patches `os.lstat` to raise `PermissionError` and runs on Windows.
- [x] AC-5: Every pin and the touched modules' test files pass on Python 3.14 and on Python 3.13.
- [x] AC-6: Every non-guard defect is fixed here, or recorded as a named follow-up (change id or plan) that the operator agreed to, with the agreement noted in the Decision Log.
- [x] AC-7: The change doc states Windows, macOS, Linux and WSL2 behaviour for each fix; every symlink-dependent pin has a no-privilege skip branch; every mode-0 pin skips on `nt` and when `hasattr(os, "geteuid") and os.geteuid() == 0`.
- [x] AC-8: The change's own test files and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-9: `upgrade_wavefoundry._retired_sidecar_path_error` refuses an undetermined `docs/waves` or candidate path on Python 3.11 through 3.14, pinned through `phase_review_evidence_sidecar_cleanup` from the `_new_code_upgrade_backstop` caller; every `SystemExit` that phase raises from an exception (the path error, `cannot remove retired sidecar`, and the `RecordLayoutInvalid` refusal) is path-free and names the member, the cause and the recovery (restore access to the waves root, then re-run the upgrade).

## Tasks

- [x] Re-run the census against the tree at implementation time and record the unique call-site and pair counts.
- [x] Re-derive the guard set by the sink-first method (sinks, depth-1 callees, `contained_path` / `contained_resolved_path` callers, every `is_symlink()` call) and record the predicates and totals.
- [x] Classify `_archive_root_real` and every other guard found; confirm the spot-check of the six guard-named functions.
- [x] Fix the guard defects with `os.lstat` (or `os.stat`) under the Requirement 3 errno rule, citing `review_evidence._authority_member_lstat` as the reference: `FileNotFoundError` and `NotADirectoryError` mean absent; ELOOP, EACCES, EBADF, WinError 21, 123, 1921 and every other `OSError` refuse.
- [x] Fix `_retired_sidecar_path_error`: errno-rule state checks and a path-free refusal message.
- [x] Add a pin per fix (mode-0 parent, skipped on `nt` and under root) and a platform-independent `os.lstat` `PermissionError` pin per fix.
- [x] Build the grouped triage table: defects and needs-decision sites individually, benign sites grouped by reason with per-file counts summing to the census total.
- [x] Fix local non-guard defects; record the rest as operator-agreed follow-ups in the Decision Log.
- [x] Run the touched test files on 3.14 and 3.13 in a scratch copy.
- [x] Add a CHANGELOG Unreleased bullet.
- [x] Validate docs.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| guard-triage | implementer | none | Guard set first, including re-derivation. |
| guard-fixes | implementer | guard-triage | Fix plus pin per defect. |
| remaining-triage | implementer | guard-triage | Classify the other sites. |
| verification | qa | guard-fixes, remaining-triage | 3.14 and 3.13, scratch copy. |


## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py`, `.wavefoundry/framework/scripts/memory_backfill.py`, `.wavefoundry/framework/scripts/memory_supply.py`, `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`

## Affected Architecture Docs

N/A at plan time. Fixes are expected to stay inside individual functions; if triage finds a shared containment helper that should own the check, `docs/architecture/cross-cutting-concerns.md` is updated in this change.

## Platform Behaviour

- **macOS, Linux and WSL2:** the 3.14 predicate change is platform-independent; `os.lstat` and `os.stat` raise `PermissionError` on an untraversable parent on all three, so a stat-based fix refuses where 3.14 predicates read absent. Mode-0 pins skip under root (`os.geteuid() == 0`), which ignores mode 0.
- **Windows:** the 3.14 predicate change applies; `os.lstat` raises `PermissionError` on access denial. `os.chmod(path, 0)` does not deny directory traversal, so mode-0 pins skip on `nt` with a stated reason; the patched-`os.lstat` pin covers each fix there. Symlink-dependent pins skip only when `os.symlink` raises `OSError` for lack of privilege. WinError 123 (invalid name, surfacing as `OSError` with errno EINVAL) now refuses where 3.13's predicates read absent; WinError 21 and 1921 likewise refuse.
- **Python 3.11 through 3.13:** pathlib predicates read ENOENT, ENOTDIR, EBADF and ELOOP and WinError 21, 123 and 1921 as absent and raised everything else. Under the errno rule, EACCES and other errors refuse as before, while ELOOP, EBADF and those winerrors become refusals by design; ENOENT and ENOTDIR stay absent.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The census is only useful once every site is classified, and grouped totals make the table auditable. |
| AC-2 | required | The name filter is known to miss guards; the sink-first method bounds the search. |
| AC-3 | required | Guards must not fail open on a supported interpreter. |
| AC-4 | required | Without a pin the fix can silently regress, and mode-0 pins do not run on Windows. |
| AC-5 | required | Fixes must hold across the supported range. |
| AC-6 | important | Non-guard defects matter less but must not be lost. |
| AC-7 | important | Windows is enterprise-critical; symlink pins need a no-privilege branch and mode-0 pins are meaningless under root. |
| AC-8 | required | Standard change-scoped verification. |
| AC-9 | required | A confirmed fail-open and path leak in upgrade cleanup on a supported interpreter. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-04 | Reverification follow-ups. N1: pins for the storage-migration setup branch (`restore_checkpoint` refuses an uninspectable setup lock path-free) and for `wf_upgrade_status`'s `lock_unreadable` field. N2: `sqlite_storage_migration.restore_checkpoint` and `setup_reconciliation._inspect` reach `upgrade_lock_unreadable_cause` through `getattr`, so an older cached `upgrade_lib` keeps the older refusal instead of raising `AttributeError`. N3: a non-UTF-8 `docs/workflow-config.json` gets the path-free lifecycle-policy refusal (byte offset plus recovery) instead of escaping as `UnicodeDecodeError`. | New pins: `test_restore_checkpoint_refuses_an_uninspectable_setup_lock_path_free` and `test_older_cached_upgrade_lib_keeps_the_older_refusal` (`test_setup_reconciliation.py`), `test_uninspectable_lock_is_named_path_free` (`test_server_tools.py`), `test_non_utf8_config_refusal_is_path_free` (`test_pathlib_predicate_guards.py`). Failing-first in scratch copies on 3.14 and 3.13: each N1 and N3 pin goes red with its branch deleted; the mixed-version pin errors with `AttributeError` with the `getattr` removed at either site alone. Focused runs OK: 3.14 in the repo; 3.13 in a scratch snapshot of the current scripts, because the other implementer's concurrent edits tripped the repository-change guard (the snapshot includes their in-progress 1zu4y edits). `test_server_package` 31, `test_pathlib_predicate_guards` 36, `test_setup_reconciliation` 47, `test_sqlite_storage_migration` 124, `test_upgrade_wavefoundry` 587, `test_server_tools` 386. |
| 2026-10-04 | Closed the flagged DEL-R1 gap: `phase_dry_run`'s advisory now logs the path-free `upgrade_lock_unreadable_message` for an uninspectable lock instead of "Upgrade already in progress" (`getattr` fallback for an older cached `upgrade_lib`). | Pins `test_unreadable_lock_is_named_by_the_dry_run` (mode-0 lock file) and `test_denied_lock_stat_is_named_by_the_dry_run_on_every_platform` (patched `os.stat`) are red on 3.14 and 3.13 against a scratch copy with the new branch reverted. Focused runs OK on 3.14.8 and 3.13.16: `test_upgrade_wavefoundry` 587, `test_pathlib_predicate_guards` 35, `test_server_package` 31. |
| 2026-10-04 | Scratch-copy and focused verification for the test-run task: the coordinator ran the full suite in a scratch copy on 3.14 (11,035 tests OK), and the touched test files ran focused on 3.14.8 and 3.13.16 after the delivery repairs. Two focused runs tripped the repository-change guard because another session added `docs/plans/1zu4y-bug python-3-14-discovery-lint-removal-fail-open.md`; they were rerun on a quiet tree. | 3.14 and 3.13 focused, all OK: `test_pathlib_predicate_guards` 33, `test_upgrade_wavefoundry` 587, `test_setup_reconciliation` 45, `test_sqlite_storage_migration` 124, `test_storage_upgrade_resume` 14, `test_index_upgrade_guard` 25, `test_dashboard_server` 228, `test_setup_wavefoundry` 46, `test_handler_modules` 13, `test_server_tools` 385, `test_server_package` 31. |
| 2026-10-04 | Delivery repairs (coordinator-approved, non-blocking): DEL-R1 `upgrade_lib.read_upgrade_lock` docstring corrected (`{}` is falsy) and new `upgrade_lock_unreadable_cause` / `upgrade_lock_unreadable_message`; an uninspectable lock is never stale (`is_lock_stale`) or rewritten (`update_upgrade_lock`); `setup_reconciliation._inspect`, the storage-migration setup check and `phase_preflight` refuse with the path-free message instead of "foreign upgrade" or "already in progress"; the dashboard stays paused; `wf_upgrade_status` adds `lock_unreadable`. DEL-R2: `materialize_lifecycle_policy`'s parse, read and non-object refusals are path-free and name the recovery. AC-9 recovery wording, Triage B5 reason and B1-to-B4 move, and the pin-independence disclosure updated; CHANGELOG bullet extended (EBADF, quarantine-and-retry, DEL-R1/R2). | Pins: 7 new tests in `test_pathlib_predicate_guards.py` (setup refusal mode-0 file and patched `os.stat`; never stale or rewritten, mode-0 and patched; preflight refusal; unparseable and non-object lifecycle config) plus a corrupt-lock control. Failing-first: all 7 red against HEAD `56cd3e4c` on 3.14 and 3.13, and red against a pre-round mutant (`upgrade_lock_unreadable_cause` returning `None`, old lifecycle messages) on 3.14 and 3.13, in scratch worktrees. |
| 2026-10-04 | Verification: every touched module's test file and the new pins pass on Python 3.14.8 and 3.13.16 (focused runs, `test_server_package.py` included). Existing tests updated honestly: `test_index_state_store` (import-light set now includes stdlib `os` and `stat`; the fail-closed probe test patched `Path.is_file` to raise, which simulated pre-3.14 behaviour and hid the defect, and now patches `os.stat`); the pack-discovery `_Sandboxed` stand-in gains `__fspath__` naming a real directory, since `_scan_dir_entries` now stats it. | `run_tests.py --file` on 3.14 and 3.13: `test_pathlib_predicate_guards` 25, `test_upgrade_wavefoundry` 587, `test_lifecycle_mutation_lock` 64, `test_memory_records` 230, `test_memory_backfill` 47, `test_archive_memory_backfill` 9, `test_review_policy` 105, `test_setup_wavefoundry` 46, `test_setup_index` 194, `test_indexer` 396, `test_index_state_store` 100, `test_setup_reconciliation` 45, `test_sqlite_storage_migration` 124, `test_index_upgrade_guard` 25, `test_storage_upgrade_resume` 14, `test_record_layout_census` 5, `test_path_containment` 23, `test_server_package` 31, all OK. Bare 3.11.17: 21 of 25 new pins pass; 4 need tool-venv dependencies (`apsw`) to import. |
| 2026-10-04 | Failing-first evidence. Against HEAD `56cd3e4c` in a scratch worktree with the new tests copied in: on 3.14.8 every mode-0 pin fails (the sidecar backstop passes and reaches the memory gate, rc 4; `_present` reads absent; the lock reads `None`; the waves root reads "no waves"; the purge proceeds to the visible body; the lifecycle policy and workflow defaults replace a symlinked config; the scan, meta.json, scaffold and model-cache reports stay silent; the consolidation rollback reports `rollback_completed: true`). Every patched-stat pin also fails on 3.14 except `_canonical_waves_dir`'s, which the errno-rule mutant (`except OSError: return None`) turns red on 3.14 and 3.13, as it does all four sidecar guard pins. On 3.13.16 the unfixed guards refuse but leak absolute paths or raise raw `PermissionError`. | Scratch worktree at `56cd3e4c`; mutants applied only there. |
| 2026-10-04 | Fixed 15 census defects and 5 re-derived guards (Triage section): `_retired_sidecar_path_error` and the sidecar phase (path-free `SystemExit` messages naming member, cause and recovery), `index_paths._present`, `upgrade_lib.read_upgrade_lock`, `memory_backfill._canonical_waves_dir`, `memory_records.resolve_purge_memory_source`, `review_policy_upgrade` plan and apply, `materialize_lifecycle_policy`, `_provision_workflow_defaults_if_absent`, `_scan_dir_entries`, `_remove_legacy_meta_json`, `_model_cache_corruption_reason`, `repair_declaring_scaffold`, `memory_consolidate_response` rollback. Three needs-decision follow-ups proposed (AC-6, awaiting operator agreement). | Pins: `tests/test_pathlib_predicate_guards.py` (new), AC-9 pins in `test_upgrade_wavefoundry.py` (`HistoricalMemoryUpgradeGateTests`, `ReviewEvidenceSidecarCleanupTests`, `ScaffoldRepairIsClassATests`), rollback pins in `test_lifecycle_mutation_lock.py`. |
| 2026-10-04 | Census re-run and triage. Gapfill: the census, sink-first enumeration (786 sink `try` blocks, 392 callees) and the `is_symlink()` sweep ran as AST scans in a scratch copy, because a per-sink `code_callhierarchy` call is impractical at that count and the census predicate (call inside a `try` body with given handler types) is not expressible as a code-tool query; site reads used shell `sed` for batch context around dozens of line numbers at once. MCP `code_read`, `code_references` and `code_keyword` were used for single-symbol reads. | Census at `56cd3e4c`: 131 unique / 136 pairs; after fixes 116 / 121. |
| 2026-10-04 | Repaired after readiness review (F1 to F7, F9): one errno rule after `_authority_member_lstat`; AC-3 and Requirement 5 restated (stricter than 3.13 by design); census refreshed; AC-1 grouped table; sink-first AC-2 method; AC-6 follow-up recording; root skip and patched-`os.lstat` pins; AC-9 and `upgrade_wavefoundry.py` added. | Census re-run at `56cd3e4c`: 131 unique call sites in 35 files (136 call-and-try pairs), guard-named 10 calls in 6 functions; `_retired_sidecar_path_error` probe returns `None` on 3.14.8 and refuses on 3.13; pathlib `_IGNORED_ERRNOS` / `_IGNORED_WINERRORS` read on 3.11.17 and 3.13.16; `contained_path` walk read at `path_containment.py:17`. |
| 2026-10-04 | Planned as a split from `1zrai-bug python-3-14-suite-compatibility` by coordinator decision. | Starting census above; predicate probes on 3.11.17, 3.13.16 and 3.14.8. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-04 | Operator agreement on the three needs-decision sites: fix them in this release as `1zu4y-bug python-3-14-discovery-lint-removal-fail-open`, admitted to wave 1zrak, instead of deferring them. | The operator directed "fix them instead of leaving for a follow up"; the named change satisfies AC-6 and closes with this wave. | Defer as unadmitted follow-up plans (rejected by the operator). |
| 2026-10-04 | Coordinator-approved delivery repairs (non-blocking review items): an uninspectable upgrade lock gets its own path-free refusal and is never treated as stale or rewritten (DEL-R1); `materialize_lifecycle_policy`'s parse and type refusals become path-free (DEL-R2); AC-9's recovery reads "then re-run the upgrade"; the Triage B5 reason and the `_prepare_council_verdict_locations` group are corrected; the reverts that only mode-0 pins kill are disclosed. | `--resume-after-gate` refuses `review_sidecar_cleanup`, so "resume" was not a recovery; reading an unreadable lock as a foreign or stale upgrade misled setup and could clear or overwrite it. | Leave as non-blocking follow-ups (rejected by the coordinator: same change, small). |
| 2026-10-04 | One errno rule for every fix: `FileNotFoundError` and `NotADirectoryError` mean absent, every other `OSError` refuses; `review_evidence._authority_member_lstat` is the reference. | Matches the `1zqe4` authority guard, so the framework has one reading of an undetermined path. | Mirror pathlib's 3.13 ignore list (rejected: reads ELOOP and EBADF as absent, which fails open on a loop). |
| 2026-10-04 | Fixes refuse ELOOP, EBADF and WinError 21, 123 and 1921 although 3.11 to 3.13 read them as absent. | An undetermined path in a guard must refuse; "as on 3.13" was not a coherent target. | Restore exact 3.13 classification (rejected: keeps those fail-opens). |
| 2026-10-04 | `path_containment.contained_path` keeps its stricter walk, where only `FileNotFoundError` is absent. | It already refuses more than the rule requires; loosening it is out of scope. | Align it to the rule (rejected: no defect to fix). |
| 2026-10-04 | AC-1 counts unique call sites; benign sites are grouped by reason, defects and needs-decision sites listed individually. | Pair counts double-count nested `try` blocks; grouping keeps 131 rows auditable. | One row per site (rejected: noise); pair count (rejected: inflated). |
| 2026-10-04 | AC-2 uses a sink-first method bounded to refusal sinks, depth-1 callees, containment-helper callers and every `is_symlink()` call; `os.path` predicates excluded. | A bounded, repeatable method replaces "re-derive by reading"; `os.path` predicates never raised, so they are unchanged. | Read all 674 out-of-`try` predicate calls (rejected: unbounded effort for little yield). |
| 2026-10-04 | Widen AC-9 per the release-reviewer recheck: pin the refusal through the new-code backstop caller (`_new_code_upgrade_backstop`), which is what runs the fixed check on the first upgrade to the fixed version since the installed runner's own cleanup call cannot fix itself; make every exception-derived `SystemExit` in `phase_review_evidence_sidecar_cleanup` path-free and actionable. | The neighbouring `cannot remove retired sidecar` and `RecordLayoutInvalid` messages interpolate `{exc}` with absolute paths; a refusal must keep a retained upgrade lock recoverable. | Record the neighbouring leaks as a follow-up (rejected: same phase, same fix). |
| 2026-10-04 | Fix `upgrade_wavefoundry._retired_sidecar_path_error` here, including a path-free refusal message (AC-9). | Confirmed fail-open on 3.14 with a mode-0 `docs/`, plus an absolute-path leak through `{exc}`. | Separate follow-up (rejected: confirmed defect in scope's own class). |
| 2026-10-04 | Each fix gets a patched-`os.lstat` `PermissionError` pin, and mode-0 pins skip under root. | Mode-0 pins skip on Windows and are meaningless under root, so each fix needs a pin that runs everywhere. | Rely on mode-0 pins only (rejected: no Windows coverage). |
| 2026-10-04 | Non-guard defects not fixed here are recorded as named follow-ups (change id or plan) with the operator's agreement noted in this log. | Makes AC-6 auditable. | Unnamed follow-ups (rejected: they get lost). |
| 2026-10-04 | Triage as its own change, guards first. | The census is large and mostly benign; the guard subset is where failing open matters. | Fold into `1zrai` (rejected by the coordinator). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The name-filtered guard set misses real guards. | AC-2 requires the sink-first re-derivation with recorded totals. |
| The stricter errno rule refuses paths 3.13 read as absent (ELOOP, EBADF, WinError 21, 123, 1921). | Intended; each fix's pin and the Platform Behaviour section state it. |
| A predicate outside a local `try` relied on a caller's handler on 3.13. | Included in the re-derivation task. |
| No Windows CI. | Explicit skip reasons; verify on a Windows host when one is available. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
