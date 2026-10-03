# Create A Wave Under A Parent Folder

Change ID: `1zlu3-enh create-wave-parent-folder`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-02
Wave: 1zlu1 lifecycle-features-for-distributions

## Rationale

A distribution can turn on the nested record layout (`record_paths.NESTED = True`, wave 1y043) so wave folders are grouped under subfolders of the waves root (for example by initiative or quarter). Discovery, lint and every lifecycle tool already find nested waves, but `wf_create_wave` can only create a wave as a direct child of the waves root: `create_wave` writes to `load_record_roots(root).waves / wave_id`. Operators who use grouping folders create the wave flat and then move it by hand, which is exactly the kind of out-of-band record move the lifecycle tools are meant to replace (a move after events or review evidence exist risks the orphan-ledger and duplicate-id checks).

The operator decided (2026-10-02): an optional `parent` argument on `wf_create_wave`, relative to the waves root (for example `auth-overhaul` or `q4/auth`), with the refusals listed below; the parent must already exist.

Brief: consumers are distributions and operators using the nested layout; success is that a wave can be created directly in its grouping folder, with no way to place it outside the waves root, inside another wave, beyond the discovery depth, or under a colliding id.

## Product Intent

Creating a grouped wave is one call. Flat-layout repositories (the shipped default) see no behaviour change: the argument is refused there with a clear reason. Spec: `docs/specs/mcp-tool-surface.md`.

## Requirements

1. **Argument.** `wf_create_wave(slug, mode="dry_run", parent=None)`. `parent` is optional; absent or `None` keeps today's behaviour exactly. When given it is a path relative to the waves root, `/`-separated (a `\` is folded to `/`, as `record_paths._canonical_parts` does for the layout constants).
2. **Refusals.** With `parent` given, the tool refuses with `invalid_arguments` (one diagnostic naming the reason; nothing written, no lifecycle prefix consumed) when:
   - `record_paths.NESTED` is false (the loaded roots' `nested` flag);
   - the value is empty or only whitespace or only separators;
   - the value is absolute on either platform (a leading `/` or `\`, a drive letter such as `C:`, a UNC prefix), checked with both `PurePosixPath` and `PureWindowsPath` rules;
   - any component is `..` or `.`-prefixed (a dot directory, which the nested walk never enters);
   - any existing component is a symlink (`record_paths._has_symlink_component` on the waves root and the parts) or the parent does not resolve inside the waves root (`record_paths._resolved_inside`);
   - any directory from the first component down to the parent itself holds the record file (`vocabulary_profile.RECORD_FILENAME`, through `record_paths._has_wave_md`), since a wave folder's subfolders are never walked;
   - the parent's depth plus one exceeds the loaded `max_depth` (`MAX_DEPTH`, default 4, range 1 to 8, counting the wave folder's own depth below the waves root, which matches `walk_wave_candidates`: a wave folder at depth d is discovered only when d is at most `max_depth`);
   - the parent does not exist or is not a directory (no parents are created).

   No archive-root refusal is needed: `record_paths.validate_record_layout` refuses any layout where `ARCHIVE_ROOT` and `WAVES_ROOT` are equal or nest (through `_root_overlap`), so a parent that `_resolved_inside` places under the waves root can never be inside the archive.

   **Order.** Parent validation runs in `create_wave` before `_lifecycle_module().build_id(..., commit=(mode_s == "create"))`, so a refused `parent` never consumes a lifecycle prefix in either mode.
3. **Placement.** On `create`, the wave folder is created as `waves / parent / wave_id` with a single non-recursive `mkdir` (the parent must exist; today's `mkdir(parents=True)` is not used on this path), then the record and `events.jsonl` are written exactly as today.
4. **Collision scan under the lock.** Inside the existing `project_state_publication_lock` block, before writing, the tool re-checks that the parent still resolves inside the waves root with no symlink component (`_resolved_inside`, `_has_symlink_component`), so a parent swapped between validation and the write is refused; after the `mkdir` it checks that the created wave folder resolves inside the parent. It also lists `record_paths.discover_wave_dirs` and `record_paths.discover_archive_dirs` and refuses with `ambiguous_wave_id` (the existing code from `record_paths.AMBIGUOUS_WAVE_ID_CODE`) when the new id's prefix (`record_paths.wave_id_of`) already names a wave folder at another path. The existing same-path adoption (an existing record at the exact target path is reported as `exists`) is unchanged.
5. **Response.** `data.parent` is present in `dry_run` and `create`: the POSIX path of the existing parent folder relative to the waves root, derived from the on-disk folder (its resolved path relative to the resolved waves root), not echoed from the argument, so case folding on case-insensitive filesystems and Windows' stripping of trailing dots and spaces report the folder actually used; `null` when no parent was given. `data.path` stays repo-relative. The background index refresh and the attached lint result behave as today.
6. **Listing.** `wf_list_waves` adds a derived `parent` field to each wave: the POSIX path of the wave folder's parent relative to the waves root, or `null` for a direct child. It is derived from the discovered folder, not stored in the record. `list_waves` and its other callers are unchanged.
7. **Docs and surfaces.** The `wf_create_wave` docstring (which today says "under docs/waves") names the waves root and the `parent` rules; `docs/specs/mcp-tool-surface.md` (the `wf_create_wave` signature and the `wf_list_waves` fields); the tool-surface golden and handler digests; a CHANGELOG `### Added` bullet.

## Scope

**Problem statement:** under the nested layout a wave cannot be created in its grouping folder.

**In scope:**

- `create_wave`, `wf_create_wave_response`, the `wf_create_wave` tool signature and docstring.
- The derived `parent` field in `wf_list_waves_response`.
- Tests for every refusal, nested placement at the depth limit, the flat-layout refusal, the collision scan, the list field, and Windows-shaped inputs.
- Golden fixtures, spec and CHANGELOG.

**Out of scope:**

- Creating missing parent folders.
- Moving or re-parenting an existing wave.
- A `parent` argument on any other tool (`wf_add_change`, `wf_new_*` write plans, not waves).
- Changing `MAX_DEPTH` or the nested walk.

## Acceptance Criteria

- [x] AC-1: With `NESTED` true and an existing `q4/auth` folder, `wf_create_wave(slug, mode="create", parent="q4/auth")` creates `<waves root>/q4/auth/<wave id>/wave.md` and `events.jsonl`, the new wave is found by `wf_current_wave`/`wf_list_waves` with `parent == "q4/auth"`, and docs-lint passes; `dry_run` reports the same `path` and `parent` and writes nothing.
- [x] AC-2: Each refusal in Requirement 2 is covered by a test that fails against an implementation missing that check (a flat layout, an empty value, `/abs`, `C:\x` and `\\server\share`, `a/../b`, `.hidden`, a symlinked component (skipped where the platform cannot create symlinks), a parent holding `wave.md` and a grandparent holding `wave.md`, a parent at depth `MAX_DEPTH`, a missing parent, a file as parent); in each case no folder is created and no lifecycle prefix is consumed, checked in `create` mode by asserting the next minted prefix is unchanged (validation runs before `build_id`).
- [x] AC-3: A wave created at depth exactly `MAX_DEPTH` is discovered; the same parent one level deeper is refused (the depth rule matches `walk_wave_candidates`, verified with patched `MAX_DEPTH` values 1 and 2).
- [x] AC-4: When a wave folder with the same id prefix already exists at another path (forced in a test by pinning the minted id), `create` refuses with `ambiguous_wave_id` and writes nothing; a parent replaced by a symlink after validation (forced by patching between validation and the lock, skipped where symlinks cannot be created) is refused inside the lock.
- [x] AC-4a: `data.parent` reports the on-disk folder: with an existing `Q4/Auth` folder and `parent="q4/auth"` on a case-insensitive filesystem, `data.parent == "Q4/Auth"` (skipped on case-sensitive filesystems).
- [x] AC-5: Without `parent`, `wf_create_wave` output and on-disk result are unchanged (existing tests pass unmodified), and `data.parent` is `null`.
- [x] AC-6: The docstring, spec, `docs/architecture/data-and-control-flow.md`, tool-surface golden, handler digests and CHANGELOG describe the argument and the list field.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write failing tests for AC-1 through AC-5 (nested layout via the record-layout test helpers).
- [x] Add parent validation (before `build_id`) and placement to `create_wave`; thread `parent` through `wf_create_wave_response` and the tool.
- [x] Add the containment re-check and collision scan inside the publication lock.
- [x] Add the derived `parent` field to `wf_list_waves_response`.
- [x] Update the docstring, spec, `docs/architecture/data-and-control-flow.md`, golden fixtures and CHANGELOG.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| wave-parent | implementer | none | server code and tests |
| wave-parent-docs | implementer | wave-parent | spec, golden, CHANGELOG |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/tests/test_record_layout_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden.json`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` (lifecycle mutation path: wave creation can target a nested parent). No boundary change: the record layout and discovery are unchanged.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The feature. |
| AC-2 | required | The refusals are the safety contract. |
| AC-3 | required | A wave created beyond the walk would be invisible. |
| AC-4 | required | Duplicate ids break every id lookup. |
| AC-4a | important | The response must name the folder actually used. |
| AC-5 | required | Flat-layout behaviour must not change. |
| AC-6 | important | Discoverability and golden accuracy. |
| AC-7 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-03 | Reverification repairs. N1: the omitted-parameter refusal is now structural. `_install_extension_tools` records each override's omitted omittable parameters in `_EXTENSION_OMITTED_PARAMETERS`, and `register_mcp_surface` appends an `omitted` pass (`_wrap_omitted_core_parameters`) after the full chain (cost, lock, guard, setup and, when declared, rewrite), so it is outermost. A call carrying an omitted parameter, at the top level or inside a legacy `kwargs` object, returns `_ensure_no_extra_args(name, {param: value})` (`unknown_arguments`) before the guard, the lifecycle lock, cost recording or the handler run. New case `parent_swallowing_override` installs a handler that swallows `**kwargs` and records calls (spy): `parent=` is refused with `rejected_arguments == ['parent']` and the handler is not called, a call without `parent` reaches it, and the guard is the last marker. `test_overrides_inherit_exactly_the_core_wrappers` now expects the `omitted` marker on the ACME override. Spec and CHANGELOG wording now say the server refuses the call before the handler, lock or cost recording. Nit 1: direct unit tests on `_override_compatibility_problem` (`OverrideOmittableParameterTests`): omitted `parent` accepted and reported, declared `parent: int` refused, an unlisted parameter (`mode`) still "dropped". Nit 2: at Prepare, an empty readiness roster with a non-empty delivery roster gives a `required_review_lanes_empty` message naming the delivery lanes ("No readiness review lanes are required ... delivery (Review and Close) requires: release-review"), pinned in `test_delivery_only_roster_is_not_reported_empty_at_review`. | Failing-first and single-fix mutations in a scratch copy: N1a (guard not applied), N1b (guard passes the call through) and N1c (guard innermost) killed by `test_swallowing_override_omitting_parent_is_refused_structurally`; R4 (nothing omittable) and R5 (omitted parameter still schema-checked) re-run and killed by `test_an_omitted_parent_is_accepted_and_reported` (earlier labels corrected: they had been killed through `setUpClass`); Nit 2 (generic message) killed by `test_delivery_only_roster_is_not_reported_empty_at_review`. Full suite 10,882 OK (34 skipped), `--profile second` 10,879 OK, `--profile declared` 10,882 OK, in a fresh scratch copy |
| 2026-10-03 | Delivery-review repairs. F1: after the `mkdir`, `create_wave` also requires the new folder to resolve inside the waves root and to have no symlink on `waves/<parent>/<wave id>`; on refusal it removes the folder only when this call created it and it is empty (`rmdir`), and refuses with `invalid_arguments`. New test `test_parent_swapped_for_an_outside_symlink_after_the_recheck_writes_nothing_outside` swaps the parent for an outside symlink inside `record_paths.wave_id_of` and asserts the refusal, an empty outside directory and no leftover folder. F3 (operator-reversible, option b): `_OVERRIDE_OMITTABLE_CORE_PARAMETERS = {"wf_create_wave": frozenset({"parent"})}` beside `_override_compatibility_problem`; an override that omits an omittable, non-required core parameter is neither "drops" nor "changes the schema", one that declares it must match exactly, and the `additionalProperties` check stays first; each module's provenance gains `omitted_core_parameters`, shown by `wf_server_info`. The ACME override fixture is restored to its pre-1zlu1 signature (installs; a call passing `parent=` gets `unknown_arguments`), a `parent: int` override is refused (`parent_changed_override`), and `_OVERRIDE_OMITTABLE_CORE_PARAMETERS` is classified in the reserved-name census as non-behaviour. Docs: spec Overrides paragraph and CHANGELOG; the threat model does not describe the compatibility check, so it is unchanged. | Failing-first and mutations: R1 (waves-root checks removed) and R2 (no `rmdir`) killed by the new F1 test; R4 (nothing omittable) and R5 (omitted parameter still schema-checked) killed through `setUpClass` of `ExtensionServingTests`, which holds `test_override_omitting_parent_installs_and_refuses_a_parent_argument`; R6 (declared omittable skips the schema check) killed by `test_each_case_refuses_with_its_cause_and_serves_nothing`; R7 (provenance not recorded) killed by `test_provenance_names_module_hash_tools_and_overrides`; full suite 10,878 OK (34 skipped), `--profile second` 10,875 OK, `--profile declared` 10,878 OK, in a fresh scratch copy |
| 2026-10-03 | Implemented. `_wave_parent_parts` validates `parent` before `build_id` (flat layout, empty, absolute under POSIX and Windows rules, `..` or dot component, symlink or outside the waves root, inside a wave folder, beyond `max_depth`, missing or not a folder); `create_wave` places the wave with one non-recursive `mkdir` and, under the publication lock, re-checks the parent, scans live and archived wave folders for the same id prefix (`ambiguous_wave_id` through `record_paths.AmbiguousWaveId`) and checks the new folder resolves inside the parent; `_wave_parent_on_disk` reports the on-disk spelling (`os.path.samefile` per component); `wf_list_waves` adds the derived `parent` through `_wave_listing_parent`. Deviations: the collision scan runs only when `parent` is given, so the flat path is unchanged; `data.parent` (null) is a new key on every `wf_create_wave` response; adding an optional core parameter makes a distribution override of `wf_create_wave` that lacks `parent` fail the extension compatibility check (`drops parameters ['parent']`), so the five `wf_create_wave` override fixtures in `tests/test_extension_tool_modules.py` gained `parent` and the record-layout census allowlist lost the old docstring entry. Goldens: tool-surface golden adds `parent` to `wf_create_wave`; handler digest for `wf_create_wave` updated. | `tests/test_record_layout_lifecycle.py` `CreateWaveParentTests` (15 tests); failing-first: 52 errors on the pre-change tree; mutations P1-P11 each killed by its named test; full suite and both profiles green in a scratch copy (counts in 1zlu2) |
| 2026-10-02 | Planned from the operator's decisions. Verified against the tree: `create_wave` mints the id with `build_id(..., commit=(mode == "create"))`, writes to `load_record_roots(root).waves / wave_id` and calls `wave_dir.mkdir(parents=True, exist_ok=True)` inside `project_state_publication_lock`; `walk_wave_candidates` skips symlinks and dot directories, stops at folders holding the record file, and discovers a folder at depth d only when d is at most `max_depth`; `record_paths` defines `NESTED = False`, `MAX_DEPTH = 4`, `MAX_DEPTH_RANGE = (1, 8)`, `_has_symlink_component`, `_resolved_inside`, `_has_wave_md`, `wave_id_of`, `ambiguous_wave_ids`, `discover_wave_dirs`, `discover_archive_dirs`. Premise narrowed: `lifecycle_id._existing_prefixes` already walks every nested candidate folder and the archive and probes past any prefix in use, so two creates with the same slug on the same day get different prefixes in the normal path (inferred from reading `next_available_prefix`; not executed). The Requirement 4 scan is therefore defense in depth against a mint that races the write (the id is minted before the lock is taken), not the primary guard. | Code reads, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Optional `parent` on `wf_create_wave`, relative to the waves root | Operator decision | A separate `wf_create_nested_wave` tool (rejected: duplicates the scaffold path); a full path argument (rejected: invites paths outside the root) |
| 2026-10-02 | The parent must already exist | Operator decision: grouping folders are deliberate, and a typo must not create a new group | Create missing parents (rejected) |
| 2026-10-02 | Refuse when `NESTED` is false | Operator decision: a flat-layout repository never walks below the root, so the wave would be invisible | Ignore `parent` on flat layouts (rejected: silent) |
| 2026-10-02 | Re-scan for the id under the publication lock before writing | Operator decision; the mint happens before the lock, so a concurrent mint is the remaining collision path | Rely on the prefix probe alone |
| 2026-10-02 | Also refuse a parent inside the archive root | Added at planning: the archive is read-only (wave 1z8ts), and a wave written there would be read with the archive vocabulary. Flagged for readiness review as a planner addition | Leave it to the existing write guards (not verified to cover this path) |
| 2026-10-02 | `parent` is `null` (not an empty string) for a direct child | Distinguishes "no parent" from a malformed value in consumers | Empty string |
| 2026-10-02 | Readiness amendments: the archive-root refusal and its AC-2 case are dropped (B2), superseding the planner addition above, because `record_paths.validate_record_layout` refuses an `ARCHIVE_ROOT` that equals or nests with `WAVES_ROOT` (through `_root_overlap`), so a parent that `_resolved_inside` keeps under the waves root can never be inside the archive; parent validation runs before `build_id(..., commit=True)` so a refusal consumes no lifecycle prefix (B5); `data.parent` is derived from the on-disk relative path (case folding, trailing dot and space on Windows and macOS) and containment is re-checked inside the lock, with AC-4 and AC-4a cases (minor); `docs/architecture/data-and-control-flow.md` added to tasks and ACs (N11) | Readiness review findings, 2026-10-02. Operator decisions above are unchanged | Keep the archive check as redundant defense (rejected: unreachable under a valid layout, and an unreachable branch cannot be tested to fail) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A parent path is validated on one platform's rules and escapes on another | Absolute checks use both POSIX and Windows rules; `..` and dot components refused; realpath containment; symlink components refused (tests skip symlink creation where Windows lacks the privilege, the realpath check still runs) |
| Case-insensitive filesystems (macOS default, Windows) let `Q4/Auth` match `q4/auth` | The existing folder is used as found; the response reports the on-disk folder's relative path (Requirement 5); depth and containment are case-independent. Behaviour is otherwise identical on Windows, macOS, Linux and WSL2 |
| A distribution aliases `wf_create_wave` through `EXTENSION_TOOL_PARAMETERS` and pins its parameters | A new optional parameter with a default does not change existing pins; the alias census test is rerun |
| Grouping folders that hold files but no record trip the `record_discovery_mismatch` advisory | Unchanged behaviour (documented known limit); creating a wave inside such a folder makes it hold a record below, not in it |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
