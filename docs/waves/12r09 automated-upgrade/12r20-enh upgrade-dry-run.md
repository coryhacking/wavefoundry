# Upgrade Dry-Run Mode

Change ID: `12r20-enh upgrade-dry-run`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

Before executing an upgrade the agent has no structured way to review what will happen or inspect the hook scripts that will run. Without this, the agent must either trust the zip blindly or manually inspect the scripts directory. For extension hooks loaded from the zip and convention hooks on disk, there is no safe pre-run review step.

`--dry-run` (-n) computes the full upgrade plan — same version detection, seed diffs, and change plan as the real run — and additionally surfaces the extension module source and every convention hook script found on disk, all via stdout captured by `wave_upgrade_response`. No lock file is written, no zip is extracted, no phases execute. The agent can review the output and then decide whether to proceed with the real upgrade.

This satisfies two goals:

1. **Pre-run safety check**: the agent can read the extension module source and convention hook scripts before any disk mutation occurs, and abort if they contain unexpected operations.
2. **Operator confirmation step**: the structured change plan (versions, seed diffs, dashboard state) gives the operator full visibility into what the upgrade will do before confirming.

## Requirements

### R1 — `--dry-run` / `-n` flag

`upgrade-wavefoundry --dry-run [--root <path>]` invokes `phase_dry_run(root)` and exits 0. The `--yes` flag has no effect in dry-run (there is no confirmation prompt to skip — the whole point is to review before confirming).

### R2 — Change plan output

Dry-run prints the full `_print_change_plan` output (identical to the real phase 0 plan): pack version, installed revision, zip to apply, surfaces, prune mode, docs gate, dashboard state, prompt files, and seed diffs. This gives the agent a complete picture of the mechanical changes before they execute.

### R3 — Hook inventory

After the change plan, dry-run emits a `── Hook Inventory ──` section:

1. **Extension module**: if a zip is present, read `upgrade_extensions.py` from inside it (without executing) and print the full source. If the zip has no extension module, print `none`. If no zip, print `n/a`.
2. **Convention hooks**: scan `.wavefoundry/hooks/<name>` for every hook name in `HOOK_NAMES`. For each that exists, print its path and full source. If none found, print a short message.

### R4 — No disk writes

Dry-run must not:
- Write or modify the upgrade lock file
- Extract any zip contents
- Run any phase subprocess (render, prune, docs gate, etc.)
- Execute the extension module source

Reading the zip (for seed diffs and extension source) and reading hook scripts from disk is permitted.

### R5 — `_read_extension_source`

A new `_read_extension_source(zip_path)` helper reads `upgrade_extensions.py` from the zip (checking both prefixes) and returns `(zip_entry_path, source_code)` as a tuple, or `None` if not found. It never executes the source — it only reads it. Used exclusively by dry-run.

### R6 — `HOOK_NAMES` constant

A module-level `HOOK_NAMES` list in `upgrade_wavefoundry.py` enumerates all 13 hook names in call order. Used by dry-run to enumerate convention hook paths to check. Also documents the complete hook surface for readers of the source.

### R7 — `_ensure_scripts_on_path`

Phase functions that deferred-import `upgrade_lib` or `check_version` are now directly callable from tests (not only via `main()`). A small `_ensure_scripts_on_path()` guard ensures SCRIPTS_DIR is on sys.path before deferred imports, without requiring `main()` to have run first.

## Scope

**In scope:**

- `scripts/upgrade_wavefoundry.py` — `phase_dry_run`, `_read_extension_source`, `HOOK_NAMES`, `_ensure_scripts_on_path`, `--dry-run`/`-n` CLI flag
- `scripts/server.py` — `mode: str = "apply"` parameter added to `wave_upgrade_response`; `mode="dry_run"` follows the existing MCP convention (same as `wave_prepare`, `wave_close`, etc.); `"dry_run"` removed from `phase` values; `--yes` omitted when `mode="dry_run"`
- `tests/test_upgrade_wavefoundry.py` — `DryRunTests` (8 tests), `ReadExtensionSourceTests` (6 tests)
- `tests/test_server_tools.py` — `test_dry_run_phase_passes_flag_and_omits_yes`

**Out of scope:**

- Dry-run for standalone `--rebuild-index` or `--cleanup` (no hook inventory needed; those paths have no preflight)
- Writing dry-run output to a file (stdout is already captured by `wave_upgrade_response`)
- Interactive confirmation from dry-run output (agent acts on the captured output; the real confirmation prompt is in the real run)
- Output size cap: `subprocess.run(capture_output=True)` buffers all output via `communicate()` with no size limit; for typical framework seed diffs (tens of KB) this is unproblematic. Very large diffs are bounded by available memory, not any code-level cap.

## Acceptance Criteria

- AC-1: `upgrade-wavefoundry --dry-run` exits 0 and writes no files (no lock, no extracted zip, no temp files).
- AC-2: Dry-run output includes the complete change plan (same as real phase 0 plan output).
- AC-3: When the zip contains `upgrade_extensions.py`, its full source appears in the dry-run output.
- AC-4: `_read_extension_source` does not execute the source — no side-effects from the extension module code.
- AC-5: Convention hook scripts found at `.wavefoundry/hooks/<name>` appear with their full content in the dry-run output.
- AC-6: When no zip is present, dry-run shows `Extension module: n/a (no zip)`.
- AC-7: When no convention hooks are found, dry-run says so explicitly.
- AC-8: All existing tests pass; `DryRunTests` and `ReadExtensionSourceTests` cover AC-1 through AC-7.

## Tasks

- Add `_read_extension_source(zip_path)` to `upgrade_wavefoundry.py`
- Add `HOOK_NAMES` constant
- Add `_ensure_scripts_on_path()` helper
- Add `phase_dry_run(root)` function
- Wire `--dry-run` / `-n` into `main()`'s argparse and dispatch
- Add `"dry_run"` as a valid phase in `wave_upgrade_response` in `server.py`; omit `--yes` for dry-run
- Write `DryRunTests` (8 tests) and `ReadExtensionSourceTests` (6 tests)
- Write `test_dry_run_phase_passes_flag_and_omits_yes` in `test_server_tools.py`

## Agent Execution Graph

| Workstream  | Owner              | Depends On | Notes                                    |
| ----------- | ------------------ | ---------- | ---------------------------------------- |
| helpers     | framework-engineer | —          | `_read_extension_source`, `HOOK_NAMES`, `_ensure_scripts_on_path` |
| dry-run     | framework-engineer | helpers    | `phase_dry_run`, CLI wiring              |
| tests       | framework-engineer | dry-run    | DryRunTests + ReadExtensionSourceTests   |

## Serialization Points

- All changes in `upgrade_wavefoundry.py` — single file, no shared state.

## Affected Architecture Docs

N/A — new flag on an existing CLI tool; no MCP surface, schema, or boundary change. The `wave_upgrade_response` already captures stdout so `--dry-run` output flows through MCP automatically without any server changes.

## AC Priority

| AC   | Priority  | Rationale                                              |
| ---- | --------- | ------------------------------------------------------ |
| AC-1 | required  | Dry-run must be strictly non-destructive               |
| AC-2 | required  | Agent needs the full plan to make a go/no-go decision  |
| AC-3 | required  | Primary safety benefit — review hook code before exec  |
| AC-4 | required  | Safety guarantee — reading must not trigger side-effects |
| AC-5 | required  | Convention hooks are equally important to review       |
| AC-6 | required  | Clean output for the no-zip path                       |
| AC-7 | required  | Explicit "none found" prevents ambiguity               |
| AC-8 | required  | No regression                                          |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-19 | Implemented. `phase_dry_run`, `_read_extension_source`, `HOOK_NAMES`, `_ensure_scripts_on_path` added to `upgrade_wavefoundry.py`; `--dry-run` / `-n` wired in `main()`. `"dry_run"` phase added to `wave_upgrade_response` in `server.py` (omits `--yes`). 15 new tests across `DryRunTests`, `ReadExtensionSourceTests`, and `WaveUpgradeMcpToolTests`. 1418 tests pass. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1418 OK |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | `_read_extension_source` returns raw source (no exec) | Core safety property: dry-run must not run hook code | Exec into sandbox module (still runs code, violates AC-4) |
| 2026-05-19 | Dry-run always exits 0 | It is informational — the agent decides whether to proceed; a missing zip or missing hook is not an error in dry-run context | Exit non-zero on downgrade detection (would confuse MCP callers that just want the plan) |
| 2026-05-19 | Dry-run advisory lock check (warns, doesn't abort) | Agent should see the plan even if an upgrade is already in progress (useful for diagnosis) | Abort with error on existing lock (prevents viewing plan during recovery) |
| 2026-05-19 | `--yes` ignored in dry-run | No prompt in dry-run, so the flag is meaningless | Error on --yes --dry-run (pedantic, adds no value) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Large extension module source makes stdout unwieldy | Extension modules are small Python files (typically <200 lines); acceptable for MCP response |
| Convention hook with sensitive content surfaced in dry-run output | Hooks are operator-controlled files; operator is aware of their content; dry-run runs with the same user credentials as the real upgrade |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
