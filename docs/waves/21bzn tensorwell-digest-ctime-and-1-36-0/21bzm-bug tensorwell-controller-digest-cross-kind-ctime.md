# Tensorwell Controller Digest Ignores ctime Across Stat Kinds

Change ID: `21bzm-bug tensorwell-controller-digest-cross-kind-ctime`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-21
Wave: 21bzn tensorwell-digest-ctime-and-1-36-0

## Rationale

After wave `21cw4` fixed a native-Windows refusal caused by comparing an open-handle stat with a path stat on `st_ctime_ns` (change `21alh`), a census of `.wavefoundry/framework/scripts/` found one more comparison of that kind: `_controller_digest` (`.wavefoundry/framework/scripts/tensorwell_client.py`) compares `identity(after)` (from `os.fstat`) with `identity(current)` (from `executable.stat(follow_symlinks=False)`) on device, inode, size, mtime and ctime. On Windows with Python 3.12 the two kinds can disagree on ctime alone, so the digest would refuse an unchanged controller as "changed controller". Today the function cannot run on native Windows (it uses `os.O_NOFOLLOW` unguarded), so the defect is latent; fixing it now keeps the 21alh rule consistent across the codebase.

## Product Intent

Operators whose Tensorwell controller becomes reachable on native Windows are not refused because handle and path stats disagree on ctime alone, while a controller that is actually replaced, resized or rewritten during hashing is still refused. Before: the cross-kind comparison includes ctime. After: it compares device, inode, size and mtime, as the 21alh rule does; the handle-to-handle comparison keeps ctime. Boundaries: no other behaviour of the client changes, and making the client Windows-capable is out of scope. AC-1 with AC-2 tests whether the intent was established.

## Requirements

1. In `_controller_digest`, the comparison between the handle stat after hashing and the path stat ignores ctime and compares device, inode, size and mtime.
2. The comparison between the two handle stats (before and after hashing) keeps all five fields.
3. A controller whose inode, size or mtime differs between the handle and path stats is still refused with "changed controller".

## Scope

**Problem statement:** one remaining cross-kind stat comparison includes ctime.

**In scope:**

- The comparison in `_controller_digest` and tests for it.

**Out of scope:**

- Making the Tensorwell client run on native Windows.
- The unverified device and inode behaviour of other cross-kind comparisons on ReFS, Dev Drive or SMB shares (a probe is planned separately).

## Acceptance Criteria

- [x] AC-1: With the path stat differing from the handle stat only in `st_ctime_ns` (patched at the stat boundary), `_controller_digest` returns the digest; on the current code the same fixture raises "changed controller".
- [x] AC-2: With the path stat differing in inode, size or mtime, it still raises "changed controller"; with the two handle stats differing in ctime alone, it still raises.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Compare the handle and path stats on device, inode, size and mtime in `_controller_digest`.
- [x] Add the AC-1 and AC-2 tests to `tests/test_tensorwell_client.py`.
- [x] CHANGELOG entry in the 1.36.0 section (Fixed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                   |
| ---------- | ----------- | ---------- | ----------------------- |
| fix        | implementer | none       | one comparison          |
| tests      | implementer | fix        | patched stat boundary   |


## Serialization Points

- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: one comparison inside one function; no boundary, flow or verification seam changes.

## Platform Behavior

macOS, Linux and WSL2: handle and path stats agree on ctime, so behaviour is unchanged. Native Windows: the client does not run there today; when it does, a ctime-only disagreement no longer refuses an unchanged controller.

## AC Priority


| AC   | Priority | Rationale                    |
| ---- | -------- | ---------------------------- |
| AC-1 | required | the cross-kind ctime case    |
| AC-2 | required | real changes still refused   |
| AC-3 | required | change-local verification    |


## Progress Log


| Date       | Update  | Evidence                                                   |
| ---------- | ------- | ---------------------------------------------------------- |
| 2026-10-21 | Planned | stat-kind census after wave 21cw4; operator asked to fix known problems |
| 2026-10-21 | Readiness: Risks row cites the `_cli` path re-check; AC-2's inode, size and mtime cases guard against over-dropping fields and pass on current code too. | readiness subagent aa3c0a8 |
| 2026-10-21 | Implemented: `_controller_digest` compares the handle stat after hashing with the path stat on `[:4]` (device, inode, size, mtime); the before/after handle comparison keeps five fields. Test `ClientTests.test_controller_digest_ignores_ctime_only_between_handle_and_path` patches `Path.stat` and `tc.os.fstat`. | `test_tensorwell_client` 53 OK; with the fix reverted in a scratch copy the new test raises "changed controller" (AC-1 known-bad); AC-2 cases are over-drop guards |
| 2026-10-21 | Full suite run 1: 12052 tests, one failure in `test_server_tools.WaveUpgradeStatusTests.test_legacy_memory_status_does_not_read_or_offer_worklists` (`_load_script('indexer')` called by index freshness checks); the file passed 3 of 3 isolated reruns and does not touch `tensorwell_client`, so it is an intermittent ordering flake, not attributable to this change. Suite rerun for the close receipt. | scratchpad 21bzn-full-suite.log; `run_tests.py --file test_server_tools.py` x3 OK |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-21 | Apply the 21alh rule to the one remaining cross-kind ctime comparison | Consistent rule; tiny change | Comment the function as POSIX-only (leaves the trap for a later Windows port) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A same-size rewrite that preserves mtime goes unnoticed across the two stat kinds | The handle-to-handle comparison still binds ctime across the hash; inode and device still bind the path; `_cli` re-checks the controller with the five-field path identity captured after qualification (`_controller_file_identity`), which keeps ctime |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
