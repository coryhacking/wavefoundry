# Stale Helper Reference Advisory

Change ID: `1zojt-enh stale-helper-reference-advisory`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-03
Wave: 1zoju session-follow-ups

## Rationale

Follow-up N7 from wave `1zls8` (change `1zltx`, documented only): a declared helper module (`mcp_tool_extensions.EXTENSION_HELPER_MODULES`) is evicted and re-executed on every install, but a module that imported it and is not itself declared is never evicted. After `wf_reload_mcp` that importer still holds the OLD helper module object (or the old functions and classes it imported from it), so an extension calling through it runs stale code with no signal. `docs/specs/mcp-tool-surface.md` (**Helper modules**) states the rule ("an undeclared importer is never evicted, so after a reload it keeps the stale helper it imported"), and nothing reports when it happens.

Mechanism verified in `server_impl`: `_install_extension_tools` calls `_evict_extension_modules`, which pops only modules whose own namespace holds `__wf_extension__ = True`; `_install_declared_extension_tools` then loads each helper through `_load_extension_module`, which creates a NEW module object. Any undeclared module already in `sys.modules` keeps its bindings.

Detection is exact and cheap if the server keeps the OLD helper module objects it evicts until the post-install scan has run. A global is then stale in either of two cases: it IS an evicted old helper module, or the old helper's namespace binds some name to that very object while the new helper's namespace binds the same name to a different object. The scan uses only `vars()` on modules and identity comparisons. It reads no metadata from the scanned objects. A global bound to an object that the old helper exported under a name the new helper still binds, but to a different object, is stale in the common case. One residual false positive remains: an alias of a shared third-party object. If the old helper had `x = os.path` and the new helper rebinds `x`, an importer's `from h import x` still holds the current `os.path` and is flagged anyway. The advisory accepts this (Risks).

A probe on 2026-10-03 confirmed this. An importer did `import helper_h`, `from helper_h import f, C, inst`, and also bound a nested class, a factory-made closure and its own instance of `C`; the helper was then evicted and re-imported. The scan flagged exactly `helper_h`, `f`, `C` and `inst`, and none of the nested class, the closure or the importer's own instance. Exporting `inst` and rebinding it in the new helper makes it genuinely stale, so flagging it is correct. References held inside containers, closures, default arguments or instances are not seen, which the advisory states.

Partial overlap: the framework-script census test (`FRAMEWORK_SCRIPT_MODULE_NAMES` pinned to the scripts directory less the declared modules) already fails a fork's undeclared FLAT script in a repository that runs the framework tests. It does not see subpackages under `scripts/`, and a packaged distribution does not run those tests, so the runtime advisory still covers a real gap.

## Requirements

1. After a successful extension install (startup and every `wf_reload_mcp`), the server scans `sys.modules`. It skips every entry whose value is not a `types.ModuleType` (`issubclass(type(value), types.ModuleType)`, which rejects lazy proxies). For each remaining module it reads `vars(module).get("__file__")`, skips non-strings, string-prefix filters the value against the scripts directory, and only then calls `Path.resolve()` to confirm that the file lies inside the framework scripts directory (any depth, so subpackages count). It also skips modules marked `__wf_extension__`, and records each module-level global matching the Requirement 2 test. Each entry names the scanned module, the global, and the old module it came from.
2. `_evict_extension_modules` keeps a reference to each module object it evicts (every marked module, helpers and extension modules alike, since the declaration that named them may already have been replaced) in a retained list. Each eviction REPLACES the list, never extends it. The list is held until the post-install scan finishes and is then cleared, in a `finally` around the scan. It is also cleared in `register_mcp_surface`'s `except BaseException` block, next to the `_EXTENSION_*` clears, so an install that raises after eviction keeps no old module alive. For each scanned module, a module-level global `g` is a stale reference when either:
   - (a) `g is` one of the retained old module objects; or
   - (b) for a retained old module `old` whose name is in `sys.modules` now (the new module `new`), `vars(old)` binds some name `n` to `g` (identity), and `n in vars(new) and vars(new)[n] is not g`. A name the new module no longer binds is not flagged; for example, the old helper re-exported `os.path` and the new one does not. When the new module is absent from `sys.modules` (for example a helper dropped from the declaration), comparison (b) is skipped for it; (a) still applies.

   The scan uses only `vars()` on modules and identity comparisons, and reads no attribute of the objects it compares, so no code runs and nothing is inferred from metadata. A helper-exported object the new helper rebinds is reported, including an instance exported by name. A closure, a nested class, or an instance the importer builds itself is never bound by name in the old helper's namespace and so is never reported.
3. The result is stored in the extension provenance as `stale_helper_references`, a sorted list of `{"module", "global", "helper"}` entries, empty when none and always present (also in `_empty_extension_provenance`). `wf_server_info` reports it under `extensions.stale_helper_references` and, when non-empty, adds one advisory diagnostic `extension_helper_stale_reference` naming the modules and telling the operator to declare the importer as a helper or restart the host.
4. The scan never fails an install. An exception while scanning one module is caught for that module only: the module is skipped and noted in one advisory diagnostic naming only the exception class, and the scan continues with the next module.
5. When nothing was evicted (the first install, or no marked module existed), the retained list is empty and the scan does nothing; the stock `wf_server_info` output gains only the empty list.
6. The **Helper modules** paragraph in `docs/specs/mcp-tool-surface.md` names the advisory and its limit (module-level bindings only).
7. Platform behaviour: module paths are compared after `Path.resolve()`, and on Windows after `os.path.normcase` as well, so a case or separator difference between `__file__` and the scripts directory does not hide a module; on macOS a case-insensitive volume keeps the case Python imported with, which matches the declared exact-name rule. Identity comparisons are platform-neutral. Identical on Windows, macOS, Linux and WSL2.

## Scope

**Problem statement:** a stale helper reference after reload is silent.

**In scope:**

- The scan, provenance key and advisory in `wf_server/server_impl.py`.
- `_extension_provenance_for_response`, which rebuilds the `wf_server_info` `extensions` object from a fixed key list, so `stale_helper_references` must be added there as well as to `_empty_extension_provenance`.
- Tests in `tests/test_extension_tool_modules.py`, including any exact pin of the whole `extensions` object, which must gain the new key. (`test_provenance_lists_parameter_mappings` pins only `["parameters"]` and is unaffected.)
- The spec paragraph and a CHANGELOG bullet.

**Out of scope:**

- Evicting or re-importing undeclared modules (the spec's rule stays: declare the importer).
- References held in containers, closures, default arguments or the importer's own instances (only module-level bindings are scanned).

## Acceptance Criteria

- [x] AC-1: A fixture distribution declares helper `h` and extension `e`; `e` imports an undeclared flat module `u`, which does `import h` and `from h import f, C`. After a second install (the reload path), `wf_server_info` reports `stale_helper_references` with entries for the stale module reference `u.h`, the stale function `u.f` and the stale class `u.C`, plus the advisory. After the first install, with no evicted modules, it reports none. After the scan the retained old modules are released (no retained list remains, asserted with a weak reference to the old `h` that is cleared after `gc.collect()` once `u` drops its references).
- [x] AC-2: The same fixture with `u` declared as a helper reports none after reload (`u` is re-executed).
- [x] AC-3: A module under a subpackage of the scripts directory holding a stale reference is reported.
- [x] AC-4: None of the following produces an entry, and none raises an exception or runs attribute code: (1) a module whose module-level `__getattr__` answers every name; (2) a `sys.modules` entry that is not a `ModuleType`; (3) a module holding `holder = [h]`; (4) a function made by a factory closure in `h` and bound in `u`; (5) a nested class of `h` bound in `u`; (6) an instance of a helper class that `u` builds itself. Conversely, an instance that `h` exports by name and the new `h` rebinds, bound in `u` by `from h import inst`, IS reported, because it is stale.
- [x] AC-5: With nothing evicted, the scan reads nothing (a patched `sys.modules` iteration is not entered) and `extensions.stale_helper_references` is `[]`; existing exact provenance pins pass after gaining the key.
- [x] AC-6: An exception raised while scanning one module leaves the install successful, adds the class-only advisory, and still reports a stale reference in another module. Separately, a reload whose install raises after eviction (a forced extension tool-name prefix violation) leaves the retained list empty, and a weak reference to the old `h` clears after `gc.collect()`. A name the old `h` bound and the new `h` dropped is not reported.
- [x] AC-7: The change's own test files and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write AC-1 against the reload path and confirm no report exists on the current tree.
- [x] Retain evicted module objects in `_evict_extension_modules`, implement the scan (Requirements 1, 2, 4, 5) at the end of the install, and release the retained objects afterwards.
- [x] Add the provenance key to `_empty_extension_provenance` and `_extension_provenance_for_response`, and the `wf_server_info` advisory (Requirement 3); update any exact pin of the whole `extensions` object.
- [x] Add the AC-2 to AC-6 tests.
- [x] Update the spec paragraph and CHANGELOG; run the full suite in a scratch copy and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| scan | implementer | none | AC-1, AC-3, AC-4, AC-6 |
| report | implementer | scan | AC-2, AC-5 |
| docs | implementer | report | spec and CHANGELOG |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`
- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

N/A: a read-only scan reported through the existing `wf_server_info` provenance; the extension trust boundary and load order are unchanged.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The signal itself |
| AC-2 | required | The documented remedy clears it |
| AC-3 | important | Subpackages are the gap the census test misses |
| AC-4 | required | Guards the known false-positive shapes, and no code runs while scanning |
| AC-5 | required | Stock output stays stable |
| AC-6 | required | An advisory must never break install |
| AC-7 | required | Suite and lint gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-03 | Delivery repair F2 and F6: rule (b) skips old bindings whose value's exact type is in `_STALE_SCAN_SHARED_TYPES` (`NoneType`, `bool`, `int`, `float`, `complex`, `str`, `bytes`, `tuple`, `frozenset`, `range`, `ellipsis`, `NotImplementedType`) or whose name is a dunder; the whole scan body after the empty-list check runs inside `try/except Exception`, which returns no entries and records the class name in the skipped advisory (release stays in the install's `finally`); Decision Log N7, Risks, spec and CHANGELOG say exactly what is excluded | Tests: the stale fixture's new helper now gains a docstring and bumps an int constant, `u` also binds `LIMIT` and the old `__spec__`, and the exact reload list still holds only the five positives (`u.acme_h`, `u.f`, `u.C`, `u.inst`, `acme_pkg.sub.f`); `StaleHelperScanUnitTests.test_a_scan_wide_failure_is_reported_by_class_and_yields_nothing`. Failing-first on the pre-repair tree: the reload list held dozens of framework globals (`__doc__`, `_SETUP_STARTUP_ROOT`, ...) and the scan-wide failure raised. Mutations R5 (compare cached immutables) and R7 (no scan-wide guard) killed; R6 (compare dunders) survived until `u` bound the old `__spec__`, then killed. Full suite `--no-cache` in a fresh scratch copy, plus `--profile second` and `--profile declared`: 10,930 tests across 157 files OK (34 skipped); second 10,927 OK; declared 10,930 OK. The first repaired run failed only `test_label_reader_census` (its allowlist entry for the old `wf_current_wave` message became stale and was removed) |
| 2026-10-03 | Implemented: `_evict_extension_modules` replaces `_EXTENSION_RETAINED_MODULES` with what it evicts (and now tests module type by `type()`, so a proxy's `__class__` is never read); `_scan_stale_helper_references` runs at the end of every install with the release in a `finally`, and `register_mcp_surface`'s failure block also clears it; `stale_helper_references` added to both provenance builders; `wf_server_info` adds the advisories `extension_helper_stale_reference` and `extension_helper_stale_scan_skipped` (class names only); spec paragraph and CHANGELOG updated. The scan's string prefilter also accepts the unresolved spelling of a `sys.path` entry that resolves to the scripts directory (a macOS temporary directory is a symlink), before `Path.resolve()` decides | Tests: `test_extension_tool_modules.StaleHelperReferenceTests` (AC-1, AC-3, AC-4, AC-6 incl. the prefix-violation and install-raises cases), `StaleHelperDeclaredImporterTests` (AC-2), `StaleHelperScanUnitTests` and the stock pin (AC-5). Failing-first on HEAD: every new test failed (no `stale_helper_references` key). Mutations M17 to M27 all killed (M23 after ordering the failing module before the importer in `sys.modules`). full suite `run_tests.py --no-cache` in a scratch copy: 10,925 tests, 157 files, OK; `--profile second` and `--profile declared` OK (second 10,922 tests, declared 10,925; the final run, after every code change; 34 tests skipped in the full run). Gapfill: retrieval used grep and sed over the scripts tree instead of the MCP code tools, because the edits needed exact multi-line anchors in a 25,000-line module and the attached MCP server runs the pre-change code |
| 2026-10-03 | Planned from `1zls8` follow-up N7 | Identity probe flagged module, function and class bindings and missed a list-held reference |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-03 | Recheck N6: each eviction replaces the retained list, which is cleared in a `finally` around the scan and in `register_mcp_surface`'s `except BaseException` block | A failed install must not keep old modules alive, and extending the list across reloads would grow it | Clear only after a successful scan (rejected: leaks the old modules on a failed install) |
| 2026-10-03 | Recheck N7, amended by delivery repair F2: (b) requires the new module to still bind the name (`n in vars(new)`), and skips every old binding whose name is a dunder (`__doc__`, `__file__`, `__spec__` and the rest of the import machinery) or whose value's exact type is `NoneType`, `bool`, `int`, `float`, `complex`, `str`, `bytes`, `tuple`, `frozenset`, `range`, `ellipsis` or `NotImplementedType` | A dropped name is not a stale binding. Values of those types are cached and shared across modules (None, small ints, interned strings), so before F2 a helper gaining a docstring or bumping an int constant flagged 12 to 40 unrelated framework globals. Rule (a) and every other type are unchanged. An alias of a shared mutable object that the new helper rebinds (old `x = os.path`, new `x` rebound) is still flagged although the importer's object is current; it is rare, and the only consequence is an advisory suggesting a restart | Also compare against `sys.modules` for non-helper objects (rejected: back to reading metadata); exclude by value equality (rejected: reads the objects) |
| 2026-10-03 | Recheck N1: retain the evicted old module objects until the scan finishes, and flag a global that is an old module or that the old namespace binds under a name the new namespace rebinds; this replaces the F6 metadata-read design | `__module__`, `__name__` and `__qualname__` are descriptors on `types.FunctionType` and `type`, so reading them from `vars(value)` or a class `__dict__` never finds them; F6 would have skipped every function and class, and AC-1 could not pass. Identity against the old namespace needs no metadata and has no false positives by construction | The F6 metadata read (rejected: never works); `getattr` metadata (rejected: runs descriptor code and admits false positives) |
| 2026-10-03 | Readiness amendments F6 and F7 (Requirement 2 part superseded by the N1 row above): narrow Requirement 2 to modules and top-level plain functions and classes, read metadata through `vars`, filter `sys.modules` by type and `__file__` before resolving, catch per module; drop the "by construction" claim; name `_extension_provenance_for_response` in Scope | Review showed factory closures, nested classes and instances can carry a helper's `__module__` without being stale, and that the response builder uses a fixed key list | Keep the plain identity test (rejected: false positives); catch once per scan (rejected: one bad module would hide every report) |
| 2026-10-03 | Recommend implementing a narrow advisory | Detection by identity against the retained old namespace is exact for module-level bindings; the cost is one pass over the scripts-directory modules per install; it covers subpackages and packaged distributions the census test cannot see | Docs only (rejected: already documented, and the failure stays silent); drop it (acceptable if the wave needs trimming: the census test covers a fork's flat scripts in its own source repository) |
| 2026-10-03 | Report, never evict | Evicting an undeclared module would re-execute code the server did not load or hash, crossing the extension trust boundary | Evict importers too (rejected) |
| 2026-10-03 | Read `vars(module)` only | Matches the strict marker test; lazy `__getattr__` modules and properties never run code during the scan | `getattr`/`dir` (rejected: can execute module code) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A rebound alias of a shared third-party object (old helper `x = os.path`, new helper rebinds `x`) is flagged though current | Accepted (Decision Log N7); the advisory only suggests declaring the importer or restarting |
| A stale importer binding of an excluded immutable (`from h import LIMIT`, an int, string, tuple or other excluded type) is not reported after the helper rebinds it | Accepted (Decision Log N7, repair F2): such values are indistinguishable by identity from the same cached object anywhere else; the spec states that only non-immutable module-level bindings are checked |
| Operators read an empty list as proof of freshness | The spec and the advisory text state the module-level-only limit |
| The scan slows reload | It runs only when something was evicted and reads only modules under the scripts directory |
| A provenance key change breaks exact pins | Pins are updated in this change (AC-5) |
| Platform behaviour | Resolved and normcased path comparison; identical on Windows, macOS, Linux and WSL2 (Requirement 7) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
