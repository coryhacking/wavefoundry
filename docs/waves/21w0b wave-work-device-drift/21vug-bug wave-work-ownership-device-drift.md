# Wave Work Ownership Survives Device Drift

Change ID: `21vug-bug wave-work-ownership-device-drift`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-27
Wave: 21w0b wave-work-device-drift

## Rationale

Wave `21s7b` closed on 2026-10-27 but its `.wavefoundry/work/21s7b/` area survived, with close reporting `work_ownership_unproven; work preserved`. The area was created at 20:28 on 2026-10-26, the Mac rebooted at 02:02 on 2026-10-27, and macOS renumbered the volume. The recorded directory identity in `.owner.json` was `[16777229, 948521431]` and the live one `[16777232, 948521431]`: same inode, different device.

`wave_work._read_owner` requires `owner["directory"] == _identity(directory)`, where `_identity` is `[st_dev, st_ino]`. That is a persisted cross-run identity gated on `st_dev`, the defect wave `1yja8` fixed elsewhere by adding `storage_identity.compare_identity` (path plus available inode, device drift reported but not refused). The work-area code arrived later (wave `21luh`) and repeats the old comparison.

Verified by execution on a scratch repository with the current code: after `ensure_work`, rewriting only the recorded device makes `describe_work` return `available: false` and `cleanup_work` return `outcome: preserved`, both with `work_ownership_unproven`. `storage_identity.compare_identity` on the real 21s7b values returns `matches: true, basis: path+inode, device_drift: true`.

`_read_owner` has six call sites in four functions (census of `wave_work.py`, executed by grep): `describe_work`, `ensure_work` (adopt and reopen), `cleanup_work` (twice) and `_snapshot_directory` (twice). So after any reboot that renumbers the device, an open wave's area reads as unavailable, a reopen cannot adopt it, close preserves it, and focused re-review snapshots fall back to full review.

**Census of other sites (2026-10-27, executed by grep over every non-test framework file for `st_dev`, `samestat`, `samefile` and stored `"device"` fields, then reading each site):** two shipped sites compare a device number stored on disk against a live one. One is `wave_work._read_owner`. The other is the retired-graph deletion in `sqlite_storage_migration` (`_graph_identity`, compared in `_plan_captured_graph` and `_apply_retired_graph_directory`), which keeps exact device and inode on purpose: the persisted-identity guard allow-lists it with the comment that retired graph deletion deliberately requires exact device/inode and file metadata ownership. After a renumbering it retains the old graph files, which is the safe failure; it is out of scope here (see Decision Log). The other persisted sites from `1yja8` already use `storage_identity` (`sqlite_storage_migration` storage receipts, `setup_readiness`, `upgrade_extensions`, `publication_control`, `retrieval_eval`). The red-team readiness seat found the retired-graph site; the first census missed it. The verified-pack cleanup in `upgrade_wavefoundry` and the retained bundle proof in `embedded_model_bundle` compare stored identities without the device. Every other site compares two stats taken within one operation, an in-memory cache, or a per-process monitor signature. `repair_ppol_memory_staging` also compares stored device numbers, but it is a source-repository one-off repair pinned to an old build and excluded from every package by `build_pack.EXCLUDED_REL_PATHS`, so it is left as is. Non-Python framework files hold no such comparison outside frozen old-runner test fixtures.

The defect got through because the persisted-identity guard in `test_sqlite_storage_migration.py` scans only five named modules, and `wave_work` is not one of them.

## Product Intent

Operators and agents keep the use of a wave's work area across a reboot or remount that renumbers the device: an open wave still reports its area as available, focused re-review snapshots still load, and close still removes the area it owns. A different directory (different inode) or an unreadable ownership record is still refused and preserved. AC-1 together with AC-2 tests the intent; AC-3 guards the boundary.

## Requirements

1. The persisted directory identity in the ownership record is compared with `storage_identity.compare_identity`, so a device difference alone does not refuse ownership. Ownership is accepted only when the recorded value is a list of exactly two non-negative, non-bool integers, both the recorded and the live inode are greater than zero, and the comparison returns `matches: true` with `basis: "path+inode"`. The shape check runs before any indexing, so a malformed value refuses with `work_ownership_unproven` instead of raising. `compare_identity` alone would accept a zero inode on path alone, and `wave_work` supplies no path to that comparison.
2. Every `_read_owner` caller gets the same rule because the comparison lives in `_read_owner`; callers are not changed individually.
3. Within-operation checks stay strict on device and inode: `_same`, `_entry`, the `_parent` identity lists compared by `_anchor`, and the mount-crossing `st_dev` check in `_empty_directory` all compare stats taken during one operation, where the device cannot drift, and keep catching identity substitution.
4. The ownership record format is unchanged and nothing rewrites it to the new device (no restamping), matching the `1yja8` decision. Existing records stay valid.
5. The existing persisted-identity guard in `test_sqlite_storage_migration.py` also scans `wave_work`, with its within-operation comparisons listed as allowed, so a strict persisted comparison added there again fails the guard.

## Scope

**Problem statement:** a persisted `[st_dev, st_ino]` equality check makes every work area created before a device renumbering permanently unowned.

**In scope:**

- `.wavefoundry/framework/scripts/wave_work.py` `_read_owner` directory comparison.
- Tests in `.wavefoundry/framework/scripts/tests/test_wave_work_lifecycle.py` and `.wavefoundry/framework/scripts/tests/test_wave_work.py` (snapshot and malformed-record cases; the existing `[0, 0]` refusal in `test_wrong_repository_wave_or_directory_identity_is_preserved` stays unchanged), and adding `wave_work` to the persisted-identity guard in `test_sqlite_storage_migration.py`.
- `repair_ppol_memory_staging` stays out of scope: unshipped one-off repair for an old build.
- One sentence in `docs/architecture/threat-model.md` stating that the persisted directory identity tolerates device renumbering while within-operation checks stay strict.

**Out of scope:**

- Native Windows: `_parent` refuses with `safe_work_io_unsupported` before any ownership read because `dir_fd` is unavailable, so behavior there is unchanged.
- Changing `storage_identity`, the deliberately strict retired-graph deletion in `sqlite_storage_migration`, other persisted-identity sites, or the ownership record schema.
- Cleaning up areas already left behind; the 21s7b area was removed by hand on 2026-10-27.

**Platforms:** macOS (APFS renumbering after reboot, the motivating case), Linux and WSL2 filesystems whose device number changes across remount while directory inodes stay stable (btrfs subvolumes, NFS, the WSL2 ext4 VHD after `wsl --shutdown`) get the fix. overlayfs keeps stable directory inodes only with `xino` or `index`; otherwise an inode change still refuses. tmpfs is emptied on reboot, so the area is absent rather than drifted. Native Windows is unchanged as stated above. No Linux, WSL2 or Windows runner exists here, so the cross-platform claim rests on the simulated drift in AC-1 and AC-2, not on execution on those systems.

## Acceptance Criteria

Name at least one AC, or a clearly identified combination, that tests whether the intent was established. Keep implementation checks where useful; delivery of guidance alone does not prove improved agent behavior.

- [x] AC-1: With the ownership record's device changed and its inode kept, a registered whole-wave close removes the owned area (`work_cleanup.outcome == "removed"`) and, before that, the open wave reports the area available with its original generation. Fails if the device is still compared.
- [x] AC-2: Under the same simulated drift, a reopen adopts the retained area and rotates its generation, and a focused re-review snapshot written before the drift still loads. Fails if any `_read_owner` caller still refuses on device alone.
- [x] AC-3: Each of these recorded `directory` values is refused with `work_ownership_unproven` and the area preserved, on both the read path and close, with no exception escaping: a different inode, a recorded inode of 0, `[0, 0]`, a one- or three-element list, a non-list, and a bool element.
- [x] AC-4: The persisted-identity guard covers `wave_work`: restoring the strict `owner["directory"] == _identity(directory)` comparison makes the guard fail.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Compare the recorded directory identity in `_read_owner` with `storage_identity.compare_identity`.
- [x] Add drift, adoption, snapshot and refusal tests through the registered lifecycle tools and `wave_work` entry points.
- [x] Add `wave_work` to the persisted-identity guard with its within-operation comparisons allowed.
- [x] Add the threat-model sentence.
- [x] Run focused and canonical verification.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Ownership comparison and tests | implementer | readiness | One function plus tests |
| Independent review | code-reviewer, qa-reviewer | implementation | Fresh contexts |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_work.py`
- `.wavefoundry/framework/scripts/tests/test_wave_work_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_wave_work.py`
- `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py`
- `docs/architecture/threat-model.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md`: the work-area paragraph gains one sentence on device renumbering. No other architecture doc describes the ownership comparison.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The motivating failure: close leaves the area behind |
| AC-2 | required | Open-wave availability, reopen and snapshots share the defect |
| AC-3 | required | The fix must not weaken substitution refusal |
| AC-4 | required | Keeps the regression from returning unnoticed |
| AC-5 | required | Change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-27 | Observe: fresh independent code/QA/architecture/security and full-depth Council delivery approved; empty finding set, unanimous/max severity none, intent established in controlled macOS execution. Corrected registered old-comparator injection detected an availability assertion failure; initial injection displaced by load_server is excluded. All source hashes unchanged. No scope gap, intentional deferral or implementation blocker remains. | Typed delivery events, maintained test symbols and unique probe recipe in wave Review Checkpoints. Canonical 12,288 tests / 214 files / 12 skips / 547.670s remains current. |
| 2026-10-27 | Observe: canonical python3 .wavefoundry/framework/scripts/run_tests.py passed 12,288 tests / 214 files, exit 0; fresh green receipt inputs_hash b5ec21c5124b52f65164e966b812519d73e7616198174f12f2644c51800bc6bf. All ACs/tasks now verified complete; delivery approvals pending. Thought: fresh independent council chair coordinates isolated primer, required code/QA/architecture/security lanes, reality and rotating alternative seat on unchanged five-file fingerprint. | .wavefoundry/framework/test-cache.json; .wavefoundry/work/21w0b/canonical.log; /root/drift_delivery fresh context. |
| 2026-10-27 | Observe: implementation integrated in the five admitted files. Focused test_wave_work (38), test_wave_work_lifecycle (13), test_sqlite_storage_migration (133) passed: 184 tests / 35.191s / one existing native-Windows-only skip, zero failures/errors. Docs validation and diff check passed. All four isolated source controls detected by assertion failure, no errors/skips: restore strict persisted equality (three tests, including syntax guard); ignore different inode (one test); permit path-only zero-inode fallback (two tests, three subtest failures); restamp owner during read (two tests). Shared source unchanged by controls. | Tool venv unittest suites; maintained named tests test_device_drift_keeps_adoption_available_without_restamping, test_snapshot_written_before_device_drift_still_loads_without_restamping, test_invalid_directory_records_refuse_reads_and_cleanup_without_mutation, test_zero_live_inode_is_never_path_only_ownership, and test_direct_identity_equalities_are_only_reviewed_boundaries. Disposable details .wavefoundry/work/21w0b/implementation-mutants.json. |
| 2026-10-27 | Frozen Git blobs: wave_work.py cb393845500ffc81f6224b9c3350734e5c9c98e7; test_wave_work.py 4b9490980af7708b707cce1b6bd742784111f1fa; test_wave_work_lifecycle.py 75a415788033ef8606a6e64b3c18b890e4129aba; test_sqlite_storage_migration.py 64f88f59c2856a164a12bfbd517982511b724835; threat-model.md 320b92022b4479c72757d8ae0fd3a328cb47f0c0. Thought: run canonical qualification once on this frozen input before fresh independent delivery review. Framework edit gate closed. | No platform execution beyond macOS; simulated device drift, no physical reboot/remount claimed. |
| 2026-10-27 | Observe: failing-before regressions established against unchanged production: work tests 38 with two expected assertion failures (drift adoption/snapshot), registered lifecycle tests 13 with two expected assertion failures (availability/close and retained reopen), no errors. Fifteen malformed cases remain refused. Extended syntax guard fails at the old persisted equality. Thought: apply the bounded ownership comparison, then verify positive behavior and deliberate weakened/strict mutants. | Implementer reported baseline and regression runs using the tool venv; exact final commands/results follow after integration. |
| 2026-10-27 | Readback: device-only drift previously made owned work unavailable and prevented cleanup; after this change, a well-formed record with matching nonzero inode remains usable through describe, reopen, snapshot and registered close. AC-1/2 prove continuity; AC-3 keeps invalid identities refused; AC-4 extends the regression guard; AC-5 covers qualification. Only the five listed review targets change; no record restamping or within-operation relaxation. | Current _read_owner and compare_identity read through MCP; code_impact confirms all ownership consumers share the seam. |
| 2026-10-27 | Plan review self-answered: retain the existing format and shared helper, require exact integer-list shape and path+inode basis, and keep descriptor-relative race checks strict. No unresolved operator questions; stop condition met. Existing typed readiness on receipt d394fa3c93191afcd614 remains current; Prepare ready and Implement succeeded. | Current source reads, guided readiness actions empty, successful lifecycle gates. |
| 2026-10-27 | Thought: delegate the narrow coupled implementation and regression tests to one implementer, then coordinator integration and canonical qualification, then fresh independent delivery council and required specialist lanes. Requested gpt-6.1-sol/high for filesystem identity and test judgment; actual runtime identity unverified. Shared work .wavefoundry/work/21w0b; coordinator alone records lifecycle evidence. | Operator authorized review and implementation; no closure or commit inferred. |
| 2026-10-27 | Round-2 readiness notes, not plan edits (they would lapse the approvals): the older Decision Log row's "all five callers" means the six call sites in four functions stated in Rationale; "self-attests" in the drift-tolerance row overstates it, since a copied record carries the same generation. The binding against substitution is path continuity plus a nonzero inode match; generation-at-close protects cleanup. | Architecture and security round-2 reports |
| 2026-10-27 | Readiness repair. QA blocked: `compare_identity` accepts a zero inode on path alone, which would turn the existing `[0, 0]` refusal into acceptance; code, architecture and security raised the same point. Requirement 1 now requires an exact two-integer shape, nonzero inodes and `basis: path+inode`; AC-3 lists the malformed cases. Red-team found the deliberately strict retired-graph site the first census missed; recorded with a Decision Log row and kept out of scope. Also: call-site count, Requirement 3 coverage, `test_wave_work.py` in scope, platform list corrected, generation named as the main inode-reuse mitigation. | Readiness lane and red-team reports, 2026-10-27 |
| 2026-10-27 | Planned. Defect reproduced on a scratch repository: device-only drift makes describe and cleanup refuse; the shared helper accepts the real 21s7b values. | Scratch run of `ensure_work`, `describe_work`, `cleanup_work`, `compare_identity` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-27 | Work-area ownership tolerates device drift while retired-graph deletion stays strict | The work-area owner record lives inside the pinned directory it describes and carries a random generation that must equal the one captured before close, so it self-attests. Retired graph files are bound only by external metadata (size, mtime, ctime) with no such token, and failing there retains files safely. | Make both drift-tolerant: reverses a reviewed decision without that site's own review; left for a separate decision. |
| 2026-10-27 | Use `storage_identity.compare_identity` for the recorded directory identity inside `_read_owner` | Replaying 21s7b through it returns a match, so close would have removed the area; it reuses the reviewed `1yja8` rule, and one site covers all five callers. Path continuity is already enforced by the pinned no-follow walk from the repository root and the recorded repository and wave fields. It controls the outcome directly. It could wrongly accept a different directory that reuses the same inode on a replacement volume, which `1yja8` explicitly accepted. Measure by the AC-1 and AC-2 drift tests and by no further `work_ownership_unproven` leftovers after reboots. | Drop the directory identity from the record: also accepts a substituted directory carrying a copied owner file. Restamp the device on mismatch: writes during read paths that promise no writes, and the operator rejected restamping in `1yja8`. Relax `_identity` everywhere: weakens within-operation substitution checks that cannot drift. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Accepting a different directory with a reused inode on a replacement volume | The strongest guard is the 128-bit generation, which cleanup re-checks against the generation captured before close; with the repository and wave fields, acceptance effectively requires a copy of the original owner record, which needs the operator's own write access. Same accepted ambiguity as `1yja8` otherwise |
| `compare_identity` accepts a zero inode on path alone | Requirement 1 refuses a zero inode on either side and requires `basis: "path+inode"`; AC-3 covers it |
| Within-run checks loosened by accident | Requirement 3; existing interleaving and substitution tests stay unchanged and must pass |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
