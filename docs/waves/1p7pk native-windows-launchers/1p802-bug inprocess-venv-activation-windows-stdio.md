# In-process venv activation replaces the re-exec (fixes native-Windows MCP broken pipe)

Change ID: `1p802-bug inprocess-venv-activation-windows-stdio`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-06-26
Wave: `1p7pk native-windows-launchers`

## Rationale

1.9.0 field report: the MCP server **can't come up reliably on native Windows** — "broken pipe when it receives the tool list on startup," intermittently. Root cause is structural: an MCP host spawns **one** process (`python server.py`) and owns its stdio + lifecycle. On macOS/Linux `venv_bootstrap.reexec_into_tool_venv()` uses **`os.execv`** — an in-place image replacement (**same PID, one process**), invisible to the host. Windows has no in-place exec, so the bootstrap uses `subprocess.run(venv_python, …)` — a **separate child** (different PID). The host then owns/tracks the **parent** while JSON-RPC actually flows through the **child**, two processes hold the same stdout pipe, and on reconnect the host kills the parent it tracks → the child orphans holding the pipe → broken pipe / unreliable startup.

The committed byte-identical `command: "python"` is **not** the problem — the re-exec *mechanism* is. Keep the config; change how `python` reaches the venv: instead of re-execing into the venv interpreter, **activate the venv in the already-running process** (prepend its `site-packages` via `site.addsitedir`) and run the server in that single host-spawned process. No child, no `os.execv`/`subprocess` — one process on every OS, byte-identical `command: "python"` preserved, and the `os.execv`-vs-`subprocess` per-OS split disappears.

## Requirements

1. **Replace `reexec_into_tool_venv()` with `activate_tool_venv()`** in `venv_bootstrap` (stdlib-only). It:
   - **No-ops** when the venv does not exist (fresh bootstrap — runs on the system interpreter, never blocks `setup_index.ensure_deps` from creating it) or when already running inside the venv (`sys.prefix` == venv, e.g. a child spawned via `sys.executable` that is the venv Python).
   - **Version guard (the drift mitigation):** read the venv's Python version (`pyvenv.cfg` `version`/`version_info`); if its `(major, minor)` differs from the running interpreter's, the venv's compiled deps (onnxruntime/lancedb/fastembed) won't load — emit a clear stderr message ("the tool venv was built for Python X.Y; you're on Z.W — run `wf setup` to rebuild it") and `sys.exit` non-zero. Do **not** activate ABI-incompatible packages or fall back to the (Windows-broken) re-exec.
   - **Activate:** `import site; site.addsitedir(<venv site-packages>)` so `.pth` files are processed and the venv packages are importable — `<venv>/Lib/site-packages` on nt, `<venv>/lib/pythonX.Y/site-packages` on posix. Prepend so the venv wins over any bare system site-packages.
   - Stderr-only diagnostics (a stdout byte corrupts the MCP JSON-RPC handshake).
2. **Update every first-line caller** (`server.py`, `setup_index`, `indexer`, `dashboard_server`, `docs_lint`, `docs_gardener`, `wave_gate`, `lifecycle_id`, `setup_wavefoundry`, `run_tests`, `wf_cli`, and **every rendered hook body** + git hooks via `render_platform_surfaces`) from `reexec_into_tool_venv()` to `activate_tool_venv()`. Remove the `os.execv`/`subprocess`/`os.name=='nt'` re-exec entirely.
3. **Tier-3 inner spawns unchanged in shape, correct in effect.** After in-process activation `sys.executable` stays the *system* interpreter (activation does not change which interpreter runs), so `subprocess.Popen([sys.executable, <script>.py, …])` spawns the system interpreter — but each spawned framework script self-activates first-line, so it gets the venv packages. (Previously the re-exec made `sys.executable` the venv Python; both reach the venv.) Confirm the detached reindex / dashboard child spawns still resolve the venv via the spawned script's own `activate_tool_venv`.
4. **Guards updated:** the single-resolver scan + the bootstrap-adoption scan reference `activate_tool_venv`; `__all__`/`venv_bootstrap` docstring updated; the three-tier model note in `1p7pb-adr` reworded (tier 2 = `command: "python"` activates the venv in-process, no re-exec).

## Scope

**Problem statement:** The Windows re-exec (`subprocess.run` child) breaks the single-process stdio an MCP host requires, so the server is unreliable on native Windows.

**In scope:**

- `venv_bootstrap.py`: `activate_tool_venv` (+ `_venv_site_packages`, `_venv_python_version`, version guard); remove the re-exec.
- All first-line callers + rendered hook/git-hook bodies (`render_platform_surfaces`) → `activate_tool_venv`.
- Tests: activation adds the site-packages / processes `.pth`; the no-op cases (absent venv, already-in-venv); the version-guard mismatch path (clear error + non-zero, no activation); stdlib-only; a child spawned via `sys.executable` self-activates.
- The single-resolver + adoption scans.

**Out of scope:**

- The committed `command: "python"` configs (unchanged — byte-identical preserved).
- The TLS / wf / upgrade-guidance changes.
- Rebuilding the venv (that's `wf setup`'s job; the version guard points at it).

**Depends on:** `1p7pl` (the bootstrap this rewrites).

## Acceptance Criteria

- [x] AC-1: `activate_tool_venv()` activates the tool venv in-process via `site.addsitedir` (no `os.execv`, no `subprocess`, no child); no-ops on absent-venv and already-in-venv; stdlib-only. Verified by tests (site-packages prepended to `sys.path` after; both no-op cases). — `test_venv_bootstrap.ActivateTests`.
- [x] AC-2: the version guard emits a clear "run `wf setup`" message + non-zero exit when the venv's Python `(major, minor)` differs from the running interpreter, and does **not** import the incompatible packages. Verified by a test with a mismatched `pyvenv.cfg`. — `test_version_guard_mismatch_exits_and_does_not_activate` (+ `_match_activates`).
- [x] AC-3: every first-line entry point + rendered hook/git-hook body calls `activate_tool_venv()`; no `reexec_into_tool_venv`/`os.execv`/`subprocess`-re-exec remains in `venv_bootstrap` or the rendered bodies. Verified by the adoption scan + grep tests. — `ActivateAdoptionScanTests` (+ `test_no_reexec_into_tool_venv_call_in_any_entry`, `test_no_reexec_or_execv_in_module`); render-test `assertNotIn("reexec_into_tool_venv", body)`.
- [x] AC-4: macOS/Linux behavior unchanged in effect — the MCP server, hooks, `wf`, and inner reindex/dashboard spawns all run with the venv packages; full parallel suite green (3490 OK); `docs-lint` clean. **De-risk confirmed:** `python3 server.py --dry-run` under the SYSTEM interpreter prints `--dry-run: OK` — `server_impl` + `mcp`/`fastembed`/`onnxruntime`/`lancedb` import cleanly in-process via `site.addsitedir`.
- [~] AC-5 (value gate — operator-run on a real Windows host): **Deferred by operator close/package request on 2026-06-26.** The native python.org-Windows MCP attach/reconnect smoke (tool list arrives, no broken pipe) plus in-process heavy-dep import/index/query remain downstream validation. Local de-risk passed (`server.py --dry-run`, system-interpreter heavy-dep import test, full framework suite); no real Windows host evidence is available in this session.

## Tasks

- [x] Write `activate_tool_venv` (+ `_venv_site_packages`/`_venv_python_version` helpers + the version guard) in `venv_bootstrap`; remove the re-exec (`reexec_into_tool_venv`/`os.execv`/`subprocess`-relay gone).
- [x] Repoint all first-line callers + rendered hook/git-hook bodies (`HOOK_BOOTSTRAP`) to `activate_tool_venv`.
- [x] Update the adoption scan + the `1p7pb-adr` three-tier/tier-2 note (in-process activation, no re-exec).
- [x] Tests (activation, no-op cases, version-guard mismatch+match, stdlib-only incl. `site`, no-reexec/execv grep) bytecode-free.
- [x] Regenerate surfaces; rebuild the package for the Windows validation.

## Agent Execution Graph


| Workstream  | Owner       | Depends On | Notes                                              |
| ----------- | ----------- | ---------- | -------------------------------------------------- |
| bootstrap   | implementer | —          | `activate_tool_venv` + version guard; remove re-exec |
| callers     | implementer | bootstrap  | repoint entries + rendered hook/git-hook bodies    |
| tests       | implementer | bootstrap  | activation/no-op/version-guard/adoption scans      |


## Serialization Points

- After `1p7pl`. The native-Windows MCP reliability is the AC-5 operator gate (replaces the deferred 1.9.0 AC-6 for the launcher path).

## Affected Architecture Docs

- `docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md` — the re-exec → in-process-activation mechanism change (tier 2). Note in `docs/references/native-windows-support.md` at close.

## AC Priority

(Proposed; confirmed at Prepare.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The activation mechanism is the fix. |
| AC-2 | required  | The drift guard prevents a cryptic ABI crash after a Python upgrade (the robustness the re-exec had for free). |
| AC-3 | required  | No stray re-exec path can reintroduce the double-process. |
| AC-4 | required  | No macOS/Linux regression; test-locked. |
| AC-5 | required  | The real-Windows reliability gate — the whole point. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-25 | Drafted from the 1.9.0 native-Windows field report ("broken pipe receiving the tool list"). Root cause: the Windows re-exec is a `subprocess.run` child (different PID) vs `os.execv`'s in-place replacement on Unix — the host owns the parent while the server is the child. Fix keeps byte-identical `command: "python"`, changes the mechanism to in-process `site.addsitedir` activation. | field report; `venv_bootstrap.reexec_into_tool_venv` (os.execv posix / subprocess nt); `server.py:22` first-line bootstrap |
| 2026-06-25 | Implemented (admitted into OPEN wave 1p7pk; late-admitted Windows-MCP fix). `venv_bootstrap.reexec_into_tool_venv` REPLACED by `activate_tool_venv` — no-op when venv absent / already inside; **version guard** reads `pyvenv.cfg` and on a `(major,minor)` mismatch prints "run `wf setup`" + `sys.exit(2)` without activating; else `site.addsitedir(<venv>/Lib\|lib/pythonX.Y/site-packages)` with the new entries prepended. `os.execv`/`subprocess`-relay/`os.name=='nt'` re-exec branch DELETED; `__all__`/docstring/three-tier note updated. All 11 first-line entries + `HOOK_BOOTSTRAP`/`git_hook_source` repointed; surfaces regenerated (rendered hooks call `activate_tool_venv`). Tier-3 spawns unchanged (`[sys.executable, <script>.py]` — the re-spawned script self-activates). **CRITICAL de-risk PASSED:** `python3 server.py --dry-run` under the SYSTEM interpreter (sys.prefix = system framework, not venv) → `--dry-run: OK`; `fastembed`/`onnxruntime`/`lancedb` import from the venv site-packages in-process. Full parallel suite green (3490 OK); docs-lint clean; machine not mutated. Pack rebuilt at 1.9.1 for the AC-5 Windows gate. | `venv_bootstrap.activate_tool_venv`/`_venv_site_packages`/`_venv_python_version`; `render_platform_surfaces.HOOK_BOOTSTRAP`/`git_hook_source`; `test_venv_bootstrap.ActivateTests`/`ActivateAdoptionScanTests`; `1p7pb-adr` tier-2 amendment |
| 2026-06-25 | Pre-close review (PASS WITH NOTES) fixes. (1) Stale "re-exec'd / sys.executable IS the venv Python" comments in `render_platform_surfaces.py` (×5, incl. the one emitted VERBATIM into every git-hook body) reworded to the in-process-activation reality (sys.executable is the SYSTEM interpreter; the re-spawned script self-activates) — re-rendered; confirmed the on-disk `.wavefoundry/git-hooks/*` no longer say "re-exec'd". (2) Version-guard edges made conscious + documented: **fail-open** on absent/malformed `pyvenv.cfg` (comment + Risk row + `_venv_python_version` docstring + tests) and the **ABI-variant gap** (same-minor `3.13t`/debug shares `version =`) accepted as a residual (comment at the guard + Risk row; no abiflags machinery). (3) Test gaps closed: missing-site-packages-dir → `SystemExit(2)`; AC-1 strengthened to a REAL importable module + a real `.pth` processed; `test_emits_no_stdout` extended to the activate path; fail-open absent/malformed tests; and an **automated de-risk** (`ActivateInProcessDeRiskTests`) that runs the SYSTEM base interpreter (from `pyvenv.cfg executable=`, distinctness verified by a probed `sys.prefix` ≠ venv) and imports a venv-only heavy dep (`mcp`) in-process under `activate_tool_venv` — exit 0 (self-skips when no distinct system python). Full parallel suite green; docs-lint clean; pack rebuilt at 1.9.1. | `render_platform_surfaces` comment rewords; `venv_bootstrap` guard comments; `test_venv_bootstrap.ActivateTests` (+ `ActivateInProcessDeRiskTests`) |
| 2026-06-26 | **P1 review fix:** the Python-version drift guard no longer dead-ends its own remediation. `setup_wavefoundry.py` calls `activate_tool_venv(allow_version_mismatch=True)`, which no-ops without activating incompatible packages, so `wf setup` can continue into repair. `setup_index._bootstrap_venv` now detects a `pyvenv.cfg` major/minor mismatch and recreates the stale tool venv before dependency checks. Regression tests cover the setup-only bypass and stale-venv recreation; full framework suite passed (`3497` tests). | `venv_bootstrap.activate_tool_venv(allow_version_mismatch=True)`; `setup_wavefoundry.py`; `setup_index._bootstrap_venv`; `test_venv_bootstrap.test_version_guard_mismatch_can_noop_for_setup_repair`; `test_setup_index.test_bootstrap_venv_recreates_python_version_mismatch` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-25 | In-process `site.addsitedir` activation, not a re-exec | Single process on every OS keeps the MCP host's one-process stdio model intact AND preserves the byte-identical `command: "python"` (operator priority). | Windows-specific venv-direct command — rejected (sacrifices byte-identical, the wave's goal). Keep the re-exec, fix Windows handle/orphan management — rejected (still a structurally-awkward double-process). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Python-version drift (system Python upgraded, venv not rebuilt) → venv compiled deps fail to load | The version guard detects the mismatch and emits "run `wf setup`" + exits, instead of a cryptic ABI crash. The re-exec was robust to this for free; this is the accepted trade for single-process + byte-identical. |
| Heavy native deps (onnxruntime/lancedb/fastembed) may not import cleanly in-process on Windows | AC-5 validates exactly this on a real Windows host (incl. `server.py --dry-run` + a real index build) BEFORE the 1.9.1 release; native libs load package-relative so it should hold, but it is the open risk. |
| Partial isolation (system `site-packages` also on `sys.path`) | venv site-packages prepended so it wins; bare python.org system Python carries no conflicting heavy packages. |
| Absent / malformed `pyvenv.cfg` → version unverifiable | **Deliberate fail-open:** `_venv_python_version` returns None and activation PROCEEDS — don't block a valid, working venv over an unreadable version line. A genuinely ABI-broken venv still fails loud at the first compiled-dep import. Documented at the guard; tested (`test_fail_open_when_pyvenv_cfg_absent` / `_malformed`). |
| Same-minor ABI variant shares the `version =` line (free-threaded `3.13t`, debug build) → version guard doesn't catch it | **Accepted residual.** The guard compares `(major, minor)` only; recording `abiflags` machinery isn't worth it for this edge (it requires `python` to resolve to a different variant than built the venv — rare). The variant's import would fail loudly. Documented at the guard + `_venv_python_version` docstring. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
