# Memory CLI Root Defaults to CWD, Not Repo Root

Change ID: `1t1b3-bug memory-cli-root-default-cwd-not-repo`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

`memory_backfill.py` and `memory_cli.py` (`main()`, `--root` argument) both default the
repository root to `Path(".").resolve()` — the process's current working directory — rather
than anchoring on the actual repo root. This was observed directly: invoking either script
(or `wf memory-backfill`) without an explicit `--root` while cwd was
`.wavefoundry/framework/scripts/` silently created a stray
`.wavefoundry/framework/scripts/.wavefoundry/index/memory-state.sqlite`, nested one level too
deep to be caught by the repo-root `.gitignore` entry for `.wavefoundry/index/`. It required
manual discovery and cleanup.

The MCP path is unaffected — `wave_memory_backfill_response` in `server_impl.py` calls
`_load_script("memory_backfill")` in-process with the MCP server's own resolved root — but any
direct/manual invocation of these two CLI entry points is exposed. `server_impl.py` already has
a more robust `_discover_root()` that anchors on the script's own install location
(`Path(__file__).resolve().parents[3]`, since `server_impl.py` always lives at
`<root>/.wavefoundry/framework/scripts/`) before falling back to env vars and cwd-walking, and
its docstring explicitly flags that sibling copies (`indexer`, `lifecycle_id`,
`render_platform_surfaces`, `docs_gardener`) still anchor on cwd only and should eventually
unify onto that logic. `memory_backfill.py`/`memory_cli.py` are new instances of that same known
class of issue, and `run_secrets_scan.py` shows a simpler alternative already used elsewhere in
this script directory: making `--root` `required=True` instead of defaulting at all.

## Requirements

1. `memory_backfill.py`'s `main()` and `memory_cli.py`'s `main()` must resolve a default root
   anchored on the script's own install location (both files live at the same
   `<root>/.wavefoundry/framework/scripts/` depth as `server_impl.py`, so the same
   `parents[3]` anchor applies), not on `Path(".")` / cwd.
2. An explicit `--root <path>` argument must continue to take priority over the default,
   unchanged.
3. The fix must not change behavior for any existing caller that already passes `--root`
   explicitly — this covers the MCP server path and any test/script that already sets it.
4. Root-discovery logic must be shared (extracted or reused), not duplicated as a third
   divergent copy — reuse or factor out the pattern already implemented in
   `server_impl.py:_discover_root`.

## Scope

**Problem statement:** `memory_backfill.py` and `memory_cli.py` silently create
`.wavefoundry/index/` state wherever the process happens to be invoked from, instead of always
at the true repository root, because their `--root` CLI flag defaults to the literal cwd
instead of an anchored discovery.

**In scope:**

- `memory_backfill.py` `main()` `--root` default
- `memory_cli.py` `main()` `--root` default
- Shared root-discovery helper (extracted from or delegating to `server_impl.py`'s
  `_discover_root` pattern) covering both files
- Regression test(s) proving the default resolves to the repo root when invoked from a
  subdirectory (e.g. from inside `.wavefoundry/framework/scripts/`)

**Out of scope:**

- The other already-flagged sibling copies of this same cwd-anchored discovery pattern
  (`indexer.py`, `lifecycle_id.py`, `render_platform_surfaces.py`, `docs_gardener.py`) —
  `server_impl.py`'s own docstring already flags these as a known, separate "future task
  should unify" item. Bundling them here would expand scope well beyond the incident that
  triggered this bug report.
- Any change to the MCP-path call sites (`wave_memory_backfill_response`, `_load_script`),
  which already pass an explicit resolved root and are unaffected by this bug.

## Acceptance Criteria

- [x] AC-1: Running `memory_backfill.py` / `memory_cli.py` (or `wf memory-backfill`) with no
      `--root`, from a subdirectory of the repo such as
      `.wavefoundry/framework/scripts/`, resolves the default root to the actual repository
      root, not cwd.
- [x] AC-2: Passing an explicit `--root <path>` still takes priority and is unchanged.
- [x] AC-3: A regression test exercises the subdirectory-invocation case (fails against the
      pre-fix default, passes after).
- [x] AC-4: Existing `memory_backfill`/`memory_cli` test suites and the full framework test
      suite (`python3 .wavefoundry/framework/scripts/run_tests.py`) pass.

## Tasks

- [x] Confirm the exact discovery pattern to reuse from `server_impl.py:_discover_root` (script
      `parents[3]` anchor, then env vars, then cwd-walk, marker = `docs/workflow-config.json`)
- [x] Add or extract a shared script-location-anchored root-discovery helper usable by both
      `memory_backfill.py` and `memory_cli.py`
- [x] Wire both scripts' `main()` `--root` default to the new helper, preserving
      explicit-override priority
- [x] Add regression test(s) covering subdirectory invocation for both entry points
- [x] Run the full framework test suite

## Agent Execution Graph


| Workstream       | Owner       | Depends On | Notes |
| ---------------- | ----------- | ---------- | ----- |
| root-default-fix | Engineering | —          | Single small workstream, no parallelism needed |


## Serialization Points

- None — both files are independent CLI entry points with no shared mutable state beyond the
  new helper itself, which is additive.

## Affected Architecture Docs

N/A — confined to the `--root` default-resolution behavior of two existing CLI entry scripts,
reusing an already-documented pattern from `server_impl.py`. No new component, boundary, or
data-flow change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The defect itself — default root must anchor to the repo, not cwd; this is the observed stray-artifact failure |
| AC-2 | required  | Explicit `--root` priority is the contract every existing caller (MCP path, tests) relies on; regressing it breaks the unaffected path |
| AC-3 | important | Regression protection for the fixed behavior; the fix is verifiable manually, but the test prevents silent recurrence in either script |
| AC-4 | required  | Suite-green is the delivery gate for all framework script changes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
