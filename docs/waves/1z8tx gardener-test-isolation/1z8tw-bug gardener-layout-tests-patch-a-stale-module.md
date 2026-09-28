# Layout Tests Depend on Test Order

Change ID: `1z8tw-bug gardener-layout-tests-patch-a-stale-module`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-28
Wave: 1z8tx gardener-test-isolation

## Rationale

Two in-process tests in `RecordLayoutGardenerTests` fail when a test that calls `server_tools_support.load_server()` runs earlier in the same interpreter: `test_default_manifest_payload_names_the_relocated_waves_root` and `test_invalid_layout_fails_closed_before_any_stamp`. Loading the server puts a fresh `record_paths` module in `sys.modules` (the module-level eviction loop in `wf_server/server_impl.py` drops `record_paths` so the server re-imports it). The gardener test module loaded `docs_gardener` at import time, so the gardener keeps the older copy. `record_layout_support.patch_layout` patches the copies it finds in `sys.modules` plus the `modules` it is given, so it never reaches the gardener's copy, and the relocated or invalid layout is not seen.

A downstream fork reported it after `test_archive_root` (wave `1z8ts`), but it is older: `test_declared_wave_fixtures` followed by `test_docs_gardener` fails the same two tests, and the exposure dates from `8545c4f9`, when these tests began patching in-process. `run_tests.py` runs each test file in its own process, which is why the framework suite never showed it; a single-process `unittest` run does. Nothing is left patched after the earlier tests finish.

The readiness review ran every layout-patching test file after both prefixes and found one more order-dependent test with a different cause: `ColdSiteRelocatedRootTests.test_server_infer_tags_derives_the_prefix_from_the_root` in `tests/test_record_layout_cold_sites.py` fails after `test_archive_root`. `_tag_utils` captures `_DEFAULT_WAVES_PREFIX` from `record_paths.WAVES_ROOT` at import. The server's copy (cached in `server_impl._script_cache`, which `load_server()` does not reset because it re-executes only `server.py`) and the public module are each captured by whichever test first imports them, under whatever layout that test has patched. The test's last assertion compared the two copies, so it passed only when both happened to be captured under the same layout: alone both are captured under this class's relocated layout; after `test_archive_root` the public module holds the shipped prefix and the server copy the relocated one. After `test_record_layout_nested` it passed by coincidence, because that module leaves both copies captured under the same relocated root. In production the layout is not patched at run time, so the import-time capture is correct there.

## Requirements

1. The two gardener tests patch the `record_paths` copy that `docs_gardener` reads, by passing it through `patch_layout(modules=...)`, the pattern `test_doc_drift` already uses for `index_state_store`.
2. `test_server_infer_tags_derives_the_prefix_from_the_root` compares the server's no-root `_infer_tags` with the server's OWN `_tag_utils` copy (`srv._load_script("_tag_utils")`) rather than the public module, so the result does not depend on when either copy was first imported.
3. No production code changes.

## Scope

**Problem statement:** three layout tests are order-dependent in a single interpreter.

**In scope:**

- `RecordLayoutGardenerTests` in `tests/test_docs_gardener.py`.
- `ColdSiteRelocatedRootTests.test_server_infer_tags_derives_the_prefix_from_the_root` in `tests/test_record_layout_cold_sites.py`.

**Out of scope:**

- Changing `load_server` or `patch_layout` to track every module copy.
- Other test files: every file that uses `patch_layout`, `apply_layout` or `load_server()` was run before both fixed modules in one interpreter, and all pass with this change.
- Removing the import-time leaks in `test_record_layout_nested` and elsewhere: the repaired assertion no longer depends on them.
- Making `_tag_utils` read the waves root at call time (a production change; the import-time capture is correct outside tests).

## Acceptance Criteria

- [x] AC-1: from `.wavefoundry/framework/scripts` with `PYTHONPATH=tests ~/.wavefoundry/venv/bin/python -B -m unittest` and the module names as separate arguments, these pass, and each failed before the change: `tests.test_archive_root tests.test_docs_gardener`, `tests.test_declared_wave_fixtures tests.test_docs_gardener`, `tests.test_archive_root tests.test_record_layout_cold_sites`. Each module also passes alone, and `tests.test_record_layout_nested tests.test_record_layout_cold_sites` (which passed before) still passes.
- [x] AC-2: the fixed tests still discriminate, both alone and after `test_archive_root`: a scratch mutant of `docs_gardener` that hard-codes `docs/waves` in `default_manifest_payload` and skips layout validation in `markdown_scan_roots` fails both gardener tests, and a scratch mutant of `server_impl._infer_tags` that ignores `root` fails the cold-site test.
- [x] AC-3: the change's own suites pass, and the documents this change edits validate.

## Tasks

- [x] Pass `modules=(dg.record_paths,)` in both gardener tests.
- [x] Compare the server's no-root `_infer_tags` with the server's own `_tag_utils` copy in the cold-site test.
- [x] Verify the three orderings and the mutants; CHANGELOG is not needed (test-only).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fix | implementer | readiness | Three edits in two test files |
| Review | combined reviewer | Fix | QA |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_docs_gardener.py`, `.wavefoundry/framework/scripts/tests/test_record_layout_cold_sites.py`

## Affected Architecture Docs

`N/A`: test-only.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reported defect |
| AC-2 | required | The fix must not weaken the tests |
| AC-3 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Reverification: finding resolved; all orderings pass including nested; 36-file census shows no fixed-module failure. Adopted the red-team alternative: the test also asserts the no-root tag directly from the server copy's captured `_DEFAULT_WAVES_PREFIX` (a path under it is a wave, `elsewhere/waves/` is not), so the final check is no longer a same-function comparison only. New mutant MD (no-root path hard-codes `docs/waves/`) fails it alone, after archive and after nested. Remaining structural hazard (two `_tag_utils` copies capture layout at import; `test_record_layout_nested` leaves them captured) is out of scope here | reviewer reverification; scratch mutants MT, M7, MD |
| 2026-09-28 | Delivery review finding `cold-site-preload-breaks-nested-ordering` (blocking): the preload and guard broke `test_record_layout_nested` then `test_record_layout_cold_sites` (OK at HEAD, 4 `setUp` failures after), and the comment's premise that `load_server()` empties `_script_cache` was false. Repaired: preload and guard removed; the final assertion compares with the server's own `_tag_utils` copy. All cold-site orderings pass (alone; after archive, declared, nested; archive then nested then cold-site); mutants MT and M7 (no-root path uses a fixed bogus prefix) fail the test | single-process `unittest` runs; scratch mutants |
| 2026-09-28 | Implemented. `RecordLayoutGardenerTests`: both in-process tests pass `modules=(dg.record_paths,)`. `ColdSiteRelocatedRootTests.setUp`: loads the server's `_tag_utils` and the public module before `apply_layout` and asserts both carry the shipped prefix (R1). AC-1: all six runs pass (each module alone; each after `test_archive_root` and after `test_declared_wave_fixtures`). AC-2 in a scratch copy of the framework: the gardener mutant (hard-coded `docs/waves` payload plus `unvalidated_record_roots` in `markdown_scan_roots`) fails both gardener tests alone and after `test_archive_root`; `_infer_tags` with `root = None` fails the cold-site test alone and after `test_archive_root`. Gapfill: this wave's reads and censuses used shell `grep`/`sed` rather than the MCP code tools, because the questions were runtime module-identity and test-order behaviour answered by executed probes, and the targets were a handful of known test files; the probes and mutants are executed shell work | six single-process `unittest` runs; scratch mutants MG and MT |
| 2026-09-28 | Readiness review: diagnosis and fix confirmed in a scratch copy; F1 found a third order-dependent test (`test_server_infer_tags_derives_the_prefix_from_the_root`, import-time capture in `_tag_utils`), admitted here; F2 and F3 tightened the AC commands and mutants; F4 names the `server_impl` eviction loop | readiness review; per-file ordering census |
| 2026-09-28 | Planned from a downstream report. Reproduced with two orderings; traced the swap to `load_server()` in the first `_ArchiveCase.setUp`, with nothing left patched afterwards | single-process `unittest` runs; `sys.modules` identity probe |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Compare with the server's own `_tag_utils` copy instead of preloading | The assertion's point is that the no-root path delegates to `_tag_utils`'s default; comparing against the same module object makes it independent of import timing. The first approach (preload both copies in `setUp`, plus the readiness R1 guard) rested on the false premise that `load_server()` empties `_script_cache`, and turned the passing `nested` then `cold_sites` ordering into four `setUp` failures | Preload with a guard (superseded, see Progress Log); read the waves root at call time in `_tag_utils` (production change); evict and re-import both copies in `setUp` (other tests hold references to the old functions) |
| 2026-09-28 | Patch the gardener's own copy in the two tests | Matches the existing `test_doc_drift` pattern and patches exactly what the code under test reads | Make `load_server` keep shared modules (wider blast radius across the suite); have `patch_layout` scan every loaded module for `record_paths` attributes (does not see the unregistered spec-loaded gardener module) |

## Risks

| Risk | Mitigation |
| --- | --- |
| The gardener reads the layout through another module copy too | AC-1 runs the failing orderings and AC-2 proves the tests still discriminate |
| The same-module comparison is weaker than comparing two independent copies | Scratch mutants that make the no-root path ignore the default (`root = None` everywhere, or a fixed bogus prefix without a root) still fail the test |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
