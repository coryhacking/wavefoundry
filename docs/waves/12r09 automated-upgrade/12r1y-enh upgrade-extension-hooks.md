# Upgrade Extension Hooks

Change ID: `12r1y-enh upgrade-extension-hooks`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

The automated upgrade script runs a fixed set of mechanical phases. There is no way for the framework (new version) or a project to inject version-specific steps — e.g., migrating a config schema that changed between versions, running a custom surface generator added in the new pack, or asserting project-specific invariants before the docs gate. Without an extension point, these steps fall entirely on the agent's editing pass, which is undocumented and easy to miss.

The solution is a two-layer hook model unified under a single runner:
1. **Framework-side extension module** (`upgrade_extensions.py`) loaded directly from the zip before extraction — the new version ships its own migration hooks alongside the framework code, and they run as part of the same upgrade invocation with no MCP restart required.
2. **Project-level convention hooks** (`.wavefoundry/hooks/<hook-name>`) — executable scripts the project operator places at known paths. They are called by the same hook runner with the same context, so the extension model is the single mechanism for both layers.

Every hook receives an `UpgradeContext` carrying `root`, `from_version`, `to_version`, `zip_path`, and `yes` so it can self-select by version range and skip itself when not applicable.

## Requirements

### R1 — UpgradeContext

A new `UpgradeContext` class in `upgrade_wavefoundry.py` with attributes:
- `root: Path` — repository root
- `from_version: str | None` — installed revision before upgrade
- `to_version: str | None` — target version from zip or pack
- `zip_path: Path | None` — path to the zip being applied (None if upgrading from current tree)
- `yes: bool` — whether the upgrade is running non-interactively

### R2 — Extension module loader

`_load_extension_module(zip_path)` reads `upgrade_extensions.py` from inside the zip (checking both `.wavefoundry/framework/scripts/upgrade_extensions.py` and `framework/scripts/upgrade_extensions.py`) **before extraction**, compiles and executes it into a fresh `types.ModuleType`, and returns the module. Returns `None` if no zip is provided, the zip contains no extension module, or loading fails (logged as a warning, never fatal). When an extension module is loaded, a single log line confirms it.

### R3 — Hook runner

`_run_hook(name, ctx, ext_mod)` executes a named hook through both layers in order:

1. **Extension module**: calls `getattr(ext_mod, name, None)` and invokes it with `ctx` if callable. Exceptions abort the upgrade (exit 3). `SystemExit` propagates unchanged.
2. **Convention script**: checks `ctx.root / ".wavefoundry" / "hooks" / name.replace("_", "-")` — e.g. `pre-surface-rendering`. If it exists and is executable, runs it via `subprocess.run` with env vars `WF_FROM_VERSION`, `WF_TO_VERSION`, `WF_ROOT`, `WF_YES`. Non-zero exit aborts the upgrade (exit 3).

Both layers are always called for a given hook name (extension module first, then convention script) — they are additive, not exclusive.

### R4 — Hook call sites

The following hooks are called in `main()` around each phase. `pre_preflight` is omitted (context not yet available):

| Hook name | When called |
|---|---|
| `post_preflight` | after pre-flight checks pass, before zip extraction |
| `pre_extract` | immediately before zip extraction |
| `post_extract` | immediately after zip extraction (skipped if no zip) |
| `pre_surface_rendering` | before phase 1 |
| `post_surface_rendering` | after phase 1 |
| `pre_pruning` | before phase 2 |
| `post_pruning` | after phase 2 (and after old-manifest temp file cleanup) |
| `pre_docs_gate` | before phase 3 |
| `post_docs_gate` | after phase 3 |
| `pre_index_rebuild` | before phase 4 (in `--rebuild-index` path) |
| `post_index_rebuild` | after phase 4 |
| `pre_cleanup` | before phase 5 (in `--cleanup` path) |
| `post_cleanup` | after phase 5 |

For `--rebuild-index` and `--cleanup` standalone paths, the context is reconstructed from the lock file and `_find_zip(root)` so the extension module can still be loaded.

### R5 — Failure semantics

A hook aborting (non-zero exit or exception) logs a clear message identifying the hook name and source (extension module or convention script path), then exits with code 3. The upgrade lock is removed before exit if it was already written.

### R6 — No-extension-module path

When the zip has no `upgrade_extensions.py` (current packs, projects with no convention hooks), behavior is identical to today — `_run_hook` is a no-op for both layers. Zero performance impact.

## Scope

**Problem statement:** The upgrade script has no extension points — framework-version-specific migrations and project-specific steps cannot be injected into the upgrade flow.

**In scope:**

- `scripts/upgrade_wavefoundry.py` — `UpgradeContext`, `_load_extension_module`, `_run_hook`, hook call sites in `main()`
- `scripts/upgrade_extensions.py` — empty reference implementation shipped with the framework (documents the hook API via docstring and commented-out stubs)

**Out of scope:**

- Extension hooks for `check_version.py` (standalone, not part of upgrade flow)
- MCP-level hook invocation (everything runs inside the script, no MCP restart needed)
- Hook discovery beyond `.wavefoundry/hooks/` (no recursive search, no `workflow-config.json` hook list)
- Async or parallel hook execution

## Acceptance Criteria

- AC-1: `_load_extension_module` returns a live module when zip contains `upgrade_extensions.py`; returns `None` gracefully when the file is absent or the zip is None.
- AC-2: `_run_hook` calls the extension module function (if defined) then the convention script (if present), in that order, for every call site.
- AC-3: An extension module function that raises an exception aborts the upgrade with exit 3 and removes the lock.
- AC-4: A convention script that exits non-zero aborts the upgrade with exit 3 and removes the lock.
- AC-5: When neither layer defines a hook, `_run_hook` is a silent no-op.
- AC-6: Context attributes (`from_version`, `to_version`, `root`, `zip_path`, `yes`) are correctly populated in all three execution paths (full upgrade, `--rebuild-index`, `--cleanup`).
- AC-7: A reference `upgrade_extensions.py` with API documentation is shipped at `scripts/upgrade_extensions.py`.
- AC-8: All existing tests pass; new unit tests cover AC-1 through AC-6.

## Tasks

- Add `UpgradeContext` class to `upgrade_wavefoundry.py`
- Add `_load_extension_module(zip_path)` to `upgrade_wavefoundry.py`
- Add `_run_hook(name, ctx, ext_mod)` to `upgrade_wavefoundry.py`
- Wire hook call sites into `main()` for all three execution paths
- Ensure lock is removed on hook failure (extend existing `except SystemExit` handler)
- Write reference `scripts/upgrade_extensions.py`
- Add unit tests to `test_upgrade_wavefoundry.py`

## Agent Execution Graph

| Workstream  | Owner              | Depends On | Notes                                   |
| ----------- | ------------------ | ---------- | --------------------------------------- |
| impl        | framework-engineer | —          | UpgradeContext + loader + runner + wiring |
| reference   | framework-engineer | impl       | upgrade_extensions.py stub              |
| tests       | framework-engineer | impl       | unit tests for all new functions        |

## Serialization Points

- `upgrade_wavefoundry.py` only — single file, no shared framework state.

## Affected Architecture Docs

N/A — internal upgrade script extension; no MCP surface, schema, or boundary change.

## AC Priority

| AC   | Priority  | Rationale                                    |
| ---- | --------- | -------------------------------------------- |
| AC-1 | required  | Foundation — loader must work correctly      |
| AC-2 | required  | Core hook dispatch behavior                  |
| AC-3 | required  | Safety — bad extension must not silently pass |
| AC-4 | required  | Safety — bad convention hook must not silently pass |
| AC-5 | required  | Backward compatibility — no-op when unused   |
| AC-6 | required  | Context correctness across all paths         |
| AC-7 | important | Operators need API documentation to write hooks |
| AC-8 | required  | No regression                                |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | Implemented. `UpgradeContext`, `_load_extension_module`, `_run_hook` added to `upgrade_wavefoundry.py`; all 13 hook call sites wired in `main()` across the full upgrade, `--rebuild-index`, and `--cleanup` paths; reference `upgrade_extensions.py` written with full API documentation. 15 new unit tests added across `LoadExtensionModuleTests`, `RunHookTests`, and `UpgradeContextTests`. 1396 tests pass. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1396 OK |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | Load extension module from zip before extraction | Pre-extraction load means `pre_extract` hook works; avoids chicken-and-egg if extraction partially fails; zip read is non-destructive | Load from disk after extraction (misses pre_extract, couples to extraction success) |
| 2026-05-19 | `exec()` into `types.ModuleType` (not temp file + importlib) | No temp file I/O; no path manipulation; self-contained; works on all platforms | Write to temp file, use spec_from_file_location (more importlib-idiomatic but adds disk I/O and cleanup) |
| 2026-05-19 | Both layers always called (additive, not exclusive) | Framework hook and project hook address different concerns; either can be absent | First-match-wins (would silently suppress project hooks when extension module is present) |
| 2026-05-19 | Convention hook path uses dashes not underscores | Shell executables conventionally use dashes; consistent with bin launcher naming | Underscore names (less conventional for shell scripts) |
| 2026-05-19 | `pre_preflight` omitted | Context (from_version, to_version) not yet determined at that point | Pass partial context (confusing — version fields would be None unpredictably) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Extension module syntax error causes confusing failure | Compile error is caught, logged with file name and exception, and treated as a warning — upgrade proceeds without the extension module |
| Convention hook blocks on stdin in `--yes` mode | `WF_YES=1` env var tells hooks to run non-interactively; hooks are responsible for respecting it |
| Hook aborts after lock written but before lock is removed | `except SystemExit` handler in `main()` already removes the lock; hook failures exit via `sys.exit(3)` which is caught there |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.