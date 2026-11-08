# Read index producer sources through the module loader

Change ID: `22u24-enh index-compatibility-zip-import`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-07
Wave: 22u26 post-1-40-follow-ups

## Rationale

Wave 22r99 made `review_policy` importable from a zip of the framework scripts, which covers the lifecycle and upgrade path Waveforge's zipped launcher uses. Our reply to Waveforge named the remaining import-time source readers. The one on a shared library path is `index_compatibility`: at import it reads nine producer modules (`indexer`, `chunker`, `graph_indexer`, `graph_store`, `sqlite_vector_store`, `index_state_store`, `model_bundle`, `marker_namespaces`, `operational_evidence`) with `Path.read_bytes()`, and `ensure_runtime_current` re-reads them on every check. From a zip, `__file__` lies inside the archive, so the import raises `NotADirectoryError`, and every module that imports `index_compatibility` fails to load.

The MCP server modules and the eval scripts also read source files, but the server runs from the tool venv with the index and models on disk, and the eval scripts are developer tools. Neither has a zipped use, so they stay out of scope.

## Product Intent

A distribution that zips the framework scripts can import `index_compatibility` and the producers that register with it, with the same source capture, hashes and staleness check as a normal install.

## Requirements

1. `index_compatibility` reads each producer's bytes through its own module loader (`__loader__.get_data`), at import and in `ensure_runtime_current`.
2. On a normal filesystem install the captured bytes, hashes, `SUPPORTED` literals and staleness behaviour are unchanged, including the resolved source directory.
3. Inside a zip the in-archive path is built with `os.path` string operations from `__file__` as imported, never resolved and never through `pathlib`, so a symlinked temporary directory and a `./`-relative `sys.path` entry both match the archive's own prefix (`str(Path('./m.zip') / 'x.py')` drops the `./` and `zipimporter.get_data` then raises OSError).
4. `ensure_runtime_current` reports an unreadable producer inside a replaced or damaged archive as `index_runtime_stale`, as it does for an unreadable file today.

## Scope

**Problem statement:** importing `index_compatibility` from a zip fails.

**In scope:**

- `.wavefoundry/framework/scripts/index_compatibility.py` and an extension of `tests/test_review_policy_zip_import.py`.

**Out of scope:**

- `server.py`, `wf_server/server_impl.py` and the eval scripts; making the indexer run from a zip end to end.

## Acceptance Criteria

- [x] AC-1: From a zip of the shippable scripts, `index_compatibility` and `operational_evidence` import, `ensure_runtime_current()` passes, and `index_compatibility._SOURCE_HASHES` and `SUPPORTED` equal the filesystem import's values, in three cases: an absolute archive path, the same archive reached through a symlinked directory, and a `./`-relative `sys.path` entry. On the current code the import raises `NotADirectoryError`.
- [x] AC-2: A non-regression guard (the current code also passes it): on the filesystem, each captured hash equals the SHA-256 of that producer's file, and a changed producer file still raises `index_runtime_stale` from `ensure_runtime_current`.
- [x] AC-3: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add a loader-based reader and use it at both read sites.
- [x] Keep the resolved directory when `__file__` is a real file; otherwise join with `os.path` from `__file__` as imported.
- [x] Treat `zipimport.ZipImportError` like OSError in `ensure_runtime_current`.
- [x] Extend the zip import test, with the old read form as its known-bad control.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| loader     | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/index_compatibility.py`, `.wavefoundry/framework/scripts/tests/test_review_policy_zip_import.py`

## Affected Architecture Docs

N/A: confined to one module's source capture; no boundary or flow change.

## Platform Behavior

`zipimporter` accepts either path separator, so Windows archive paths work as on POSIX. Filesystem reads are unchanged on Windows, macOS, Linux and WSL2.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | important | The zipped import is the change's purpose. |
| AC-2 | required  | The staleness guard must not weaken. |
| AC-3 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-07 | Planned at operator request. Survey of module-level source reads outside tests found only `index_compatibility._SOURCE_BYTES`. | `grep` over `.wavefoundry/framework/scripts` |
| 2026-11-07 | Readiness code and QA suggestions applied: `os.path` joining for in-archive paths with a `./`-relative case, explicit symlinked case, ZipImportError handling, AC-2 marked a non-regression guard. | readiness review |
| 2026-11-07 | Implemented. `index_compatibility._read_source` reads through `__loader__.get_data`; `_SOURCE_ROOT` stays a resolved `Path` on disk (so `test_navigation_walker_runtime`'s patch still works) and is `os.path.dirname(__file__)` as a string inside an archive; `ensure_runtime_current` also treats `ImportError` (covers `ZipImportError`) as unreadable. Tests: `ZippedIndexCompatibilityImportTests` (absolute, `./`-relative and symlinked archive entries) and `FilesystemSourceCaptureTests` in `tests/test_review_policy_zip_import.py`, 4 OK. Known-bad in a scratch copy: the original module fails 3, a `Path(dirname)` mutant fails the `./` case, an always-resolve mutant fails 3 (macOS `/var` to `/private/var`). | implementation |
| 2026-11-07 | Full suite `run_tests.py --no-cache`: 12612 tests in 235 files OK, 12 expected skips, no framework bytecode (second run). The first run failed two files from this wave's own edits, both fixed before the second: `test_lifecycle_golden` (the 22r95 `conditional_fields` schema entry; golden regenerated through `check_golden` with both overwrite flags, diff exactly the three expected fixture paths, and the addition declared with its exact value in `test_only_declared_observability_additions_since_extraction_golden`) and `test_server_package` (22u24's new filesystem test read producers by path; now `framework_files.source_path`). | full suite |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-07 | Fix `index_compatibility` only | The server and eval scripts have no zipped use | Convert every source reader |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A resolved path no longer matches the zip archive prefix (macOS `/var` to `/private/var`) | Resolve only when `__file__` is a real file; the test builds its zip under the system temporary directory |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
