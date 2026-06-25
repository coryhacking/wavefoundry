# Shared venv bootstrap: one stdlib re-exec helper for every entry point

Change ID: `1p7pl-ref shared-venv-bootstrap`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-06-24
Wave: `1p7pk native-windows-launchers`

## Rationale

Venv-resolution logic is duplicated across many sites — `server_impl._preferred_python`, `upgrade_wavefoundry._preferred_python`, `build_pack._reexec_with_venv_if_needed`, `indexer` (lancedb), `setup_index._tool_venv_python`/`_reexec_with_venv_if_needed`, `run_tests._test_runner_python`, and the rendered hook-body `_venv_python_path` — and `server.py` has **no** self-bootstrap (it trusts the bash launcher `.wavefoundry/bin/mcp-server` to invoke it under the venv python). This change is the core of `1p7pb-adr` **goal B (a single runtime execution surface):** consolidate every resolver into ONE stdlib-only helper, adopt it first-line in every entry point, and lock it with a **standing scan test** that fails if any other file re-derives the venv path. It is also the load-bearing prerequisite for the cross-OS config cutover (`1p7pm`) — configs can only name a bare interpreter once every entry self-bootstraps. On macOS/Linux there is **no** user-visible behavior change (the venv is still used), so it lands first and keeps CI green before any config flip.

## Requirements

1. A stdlib-only helper `reexec_into_tool_venv()` that: discovers the tool venv python (`Scripts\python.exe` on Windows, `bin/python` on POSIX, honoring `WAVEFOUNDRY_TOOL_VENV`); if the current interpreter is not that venv python **and** it exists, re-execs into it; otherwise continues on the current interpreter. Fast no-op when already running the venv python (the common case once setup created the venv).
2. The re-exec uses `os.execv` on **POSIX only**; on Windows it uses `subprocess.run([venv_python, __file__, *argv])` inheriting stdin/stdout/stderr, then `sys.exit(rc)` (the Windows CRT emulates `execv` as spawn-child-then-exit-parent, orphaning the host's stdio pipe → an MCP host sees an immediate server crash).
3. Imports nothing beyond stdlib (`os`/`sys`/`subprocess`/`pathlib`); writes any diagnostics to **stderr only** (a stdout byte before `mcp.run()` corrupts the JSON-RPC handshake); runs as the genuine first statement of each entry point, before any heavy import.
4. On a missing venv the helper **no-ops** — it continues on the current (system) interpreter and must **never** block `setup_index.ensure_deps()` from creating/populating the venv. This is the fresh-bootstrap path: `python3 .wavefoundry/framework/scripts/setup_wavefoundry.py` on a box with no venv and no `python` symlink must run end-to-end (the first-line bootstrap is a no-op → setup_index creates the venv → deps installed → the `python` symlink/PATH logic runs). It does not hard-fail here; interpreter availability is enforced at the config layer in `1p7pm`.
5. Adopt it first-line in every first-party entry point — `server.py`, `setup_index.py`, `setup_wavefoundry.py`, `upgrade_wavefoundry.py`, `indexer.py`, `dashboard_server.py`, `docs_lint.py`, **`docs_gardener.py`**, `wave_gate.py`, `lifecycle_id.py`, **`run_tests.py`** — and route every scattered resolver (`server_impl._preferred_python`, `upgrade_wavefoundry._preferred_python`, `build_pack._reexec_with_venv_if_needed`, `indexer` lancedb, `setup_index._reexec_with_venv_if_needed`, `run_tests._test_runner_python`) onto the one helper. The three `.claude/hooks/*.py` inner spawners (`post-edit.py`, `pre-edit.py`, `simulate-hooks.py`) drop their `_venv_python_path` copies and instead spawn via **`sys.executable`** (the already-bootstrapped venv python), letting the target's own first-line bootstrap confirm the venv. (`setup_wavefoundry.py` has no resolver to replace, so the first-line call is easy to overlook — the scan test must assert it explicitly.)
6. **Inner-spawn rule (the third tier):** every inner/child spawn *after* a process has bootstrapped uses **`sys.executable`**, never a re-resolved interpreter name (`python3`/`python`). After bootstrap `sys.executable` *is* the venv python — an absolute path that keeps children in the same venv on every OS, and avoids reintroducing the `python3`-absent-on-Windows / `python`-absent-on-macOS token split. (Tier 1 = setup runs on system `python3`/`python` pre-venv; tier 2 = committed configs name `python` post-symlink — both in `1p7pm`; tier 3 = inner spawns use `sys.executable`.)
7. **Single-resolver invariant (goal B):** a standing scan test fails if any file *other than* the shared helper contains a `Scripts`-vs-`bin` / `WAVEFOUNDRY_TOOL_VENV` venv-resolution branch. The one allowlisted exception is `setup`'s pre-venv system-interpreter bootstrap (it legitimately runs before the venv exists); every other exception needs a recorded rationale.

## Scope

**Problem statement:** Venv resolution is duplicated and `server.py` cannot self-bootstrap, so the configs cannot go interpreter-direct (the ADR) until every entry point self-resolves the venv.

**In scope:**

- The shared `reexec_into_tool_venv()` helper.
- First-line adoption in all first-party entry scripts (incl. `docs_gardener.py`, `run_tests.py`); consolidation of every Python-internal resolver onto it; routing the three `.claude/hooks/*.py` inner spawners off their `_venv_python_path` copies.
- The single-resolver scan-test invariant (goal B's success gate) + helper unit tests + the adoption scan.

**Out of scope:**

- Flipping the rendered configs / bin shims / `render_agent_surfaces` Codex / `.air` interpreter-direct (that is `1p7pm`) — though the *config* `command` form is `1p7pm`'s, the **rendered hook-body** resolver removal is shared: `1p7pl` routes the inner spawners, `1p7pm` stops the renderer emitting `_venv_python_path`.
- Git-hook bodies + `.gitattributes` + dashboard daemonization (`1p7pn`).
- The real-Windows smoke verification (the value gate, carried in `1p7pm` AC-6).
- The `python`-symlink verify/heal (`ensure_python_resolves`) is **added to this module (`venv_bootstrap`) by `1p7pm`**, which owns the symlink behavior + the setup/render/upgrade call sites. `1p7pl` creates `venv_bootstrap` with the re-exec + `tool_venv_*` accessors; `venv_bootstrap` is the single home for all python/venv resolution + healing.

**Depends on:** none — lands first; `1p7pb-adr` is the design.

## Acceptance Criteria

- [x] AC-1: `reexec_into_tool_venv()` exists and is stdlib-only; given a non-venv interpreter + an existing tool venv it re-execs into the venv python (`os.execv` on POSIX, `subprocess`-relay + `sys.exit` on Windows); given the venv python already, it is a no-op fast-return. Unit-tested for both OS paths + both no-op cases (`test_venv_bootstrap.py`). *(Windows branch tested via the pure `_venv_python_relpath` helper + mocked re-exec — a concrete `WindowsPath` can't be instantiated on POSIX; real nt behavior is AC-6.)*
- [x] AC-2: a test asserts the helper imports only stdlib (`StdlibOnlyTests`) and emits **zero stdout bytes** (`test_emits_no_stdout`).
- [x] AC-3: a test asserts the Windows re-exec path uses `subprocess` and **never** `os.execv`, preserving the child exit code (`test_windows_reexecs_via_subprocess_never_execv`).
- [x] AC-4: every first-party entry script that launches directly (`server.py`, `setup_wavefoundry`, `setup_index`, `indexer`, `dashboard_server`, `docs_lint`, `docs_gardener`, `wave_gate`, `lifecycle_id`, `run_tests`) calls `reexec_into_tool_venv()` first-line; every Python-internal venv resolver (`setup_index`, `server_impl`, `upgrade_wavefoundry`, `indexer` lancedb, `build_pack`, `run_tests`) is consolidated onto `venv_bootstrap` via the delegation pattern (inner spawns get the venv Python through the single resolver = `sys.executable` post-bootstrap); macOS/Linux runtime unchanged (full suite green, modulo a pre-existing unrelated secrets flake). **A standing `ReexecAdoptionScanTests` (`test_venv_bootstrap.py`) asserts all 10 entries call the bootstrap** (a 1p7pk pre-close review found `run_tests.py` imported `venv_bootstrap` but never invoked the re-exec — now fixed + scan-locked). *(The rendered `.claude/hooks/*.py` inner spawners are emitted by `render_platform_surfaces` → retired by `1p7pm`/`1p7pn`.)*
- [x] AC-5: **fresh-bootstrap path locked** — `FreshBootstrapTests`: with no venv (`WAVEFOUNDRY_TOOL_VENV` → empty dir), the bootstrap no-ops (no re-exec, no raise) and the venv path stays resolvable so setup can build it — no setup circularity. *(Full `python3 setup_wavefoundry.py` end-to-end build is `1p7pm` AC-6 operator smoke.)*
- [x] AC-6: **single-resolver invariant** — `SingleResolverScanTests`: a standing scan asserts `WAVEFOUNDRY_TOOL_VENV` is read only in `venv_bootstrap`. `render_platform_surfaces` (the rendered bin/hook templates) is the one **allowlisted-with-rationale** exception, retired by `1p7pm`/`1p7pn` — **the allowlist must be empty at wave close.**
- [x] AC-7: tests run bytecode-free (`-B`); full framework suite green after `1p7pm`/`1p7pn` (3438 OK, only the pre-existing unrelated secrets flake); `wave_validate` clean. The single-resolver scan now passes with an **empty** allowlist — goal B complete.

## Tasks

- [x] Open `framework_edit_allowed`; close after.
- [x] Write `reexec_into_tool_venv()` (stdlib-only; POSIX `execv` / Windows `subprocess`-relay; stderr-only; no-op-when-venv) → `venv_bootstrap.py`; adopted first-line in `server.py`; `test_venv_bootstrap.py` green (12 tests).
- [x] Adopt first-line in all first-party entry scripts (incl. `docs_gardener.py`, `run_tests.py`, `setup_wavefoundry.py`); route every scattered resolver onto it; switch the three `.claude/hooks/*.py` inner spawners (and any post-bootstrap child spawn) to `sys.executable`. *(1p7pk pre-close review found `run_tests.py` had imported `venv_bootstrap` but not called the re-exec — fixed + locked by `ReexecAdoptionScanTests`.)*
- [x] Write the fresh-bootstrap test (no venv + no `python` symlink + `python3 setup_wavefoundry.py` ⇒ venv created, deps, symlink/PATH runs; bootstrap no-ops, never blocks `ensure_deps`). — `FreshBootstrapTests`.
- [x] Write the single-resolver scan test (fails on any non-helper `Scripts`-vs-`bin`/`WAVEFOUNDRY_TOOL_VENV` branch; `setup` pre-venv bootstrap allowlisted). — `SingleResolverScanTests` (TOOL_VENV read + the strengthened venv-python-layout `Scripts/python.exe` branch scan).
- [x] Tests (both-OS re-exec via mock; no-`os.execv`-on-Windows; stdlib-only + stderr-only; first-line adoption scan incl. `setup_wavefoundry.py`) bytecode-free. — `ReexecAdoptionScanTests` covers all 10 entries.

## Agent Execution Graph


| Workstream  | Owner       | Depends On | Notes                                        |
| ----------- | ----------- | ---------- | -------------------------------------------- |
| helper      | implementer | —          | the stdlib bootstrap                         |
| adoption    | implementer | helper     | first-line in every entry; consolidate resolvers |
| tests       | implementer | helper     | both-OS mock, no-execv-on-nt, stderr-only, scan |


## Serialization Points

- Lands before `1p7pm` (the config cutover) — the configs cannot reference a bare interpreter until every entry self-bootstraps.

## Affected Architecture Docs

- Implements `docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md`. No boundary/flow change (additive helper + consolidation); no other architecture doc update needed.

## AC Priority

(Proposed; confirmed at Prepare.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The helper is the deliverable + the prerequisite for `1p7pm`. |
| AC-2 | required  | A stdout byte corrupts the MCP JSON-RPC handshake. |
| AC-3 | required  | `os.execv` on Windows orphans the host stdio pipe (the ADR's hard constraint). |
| AC-4 | required  | First-line adoption + full resolver consolidation + `sys.executable` inner spawns is the whole point; no macOS/Linux regression. |
| AC-5 | required  | Locks the fresh-bootstrap path — guards the setup circularity (P0) the prepare review caught. |
| AC-6 | required  | The single-resolver scan test IS goal B's success gate — without it "single surface" is unverified. |
| AC-7 | required  | Test-locked, bytecode-free. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-24 | Planned from `1p7pb-adr` as the no-OS-risk core that lands first. | `1p7pb-adr`; scattered resolvers at `build_pack.py:811`/`indexer.py:1108`/`server_impl.py:79`/`upgrade_wavefoundry.py:77`; `server.py` has no re-exec |
| 2026-06-24 | Helper + `server.py` adoption landed; AC-1/2/3 green. Remaining: adopt in the other entry scripts, consolidate the scattered resolvers, `sys.executable` inner spawns, fresh-bootstrap + single-resolver scan tests. | `venv_bootstrap.py`; `server.py` first-line; `test_venv_bootstrap.py` 12 tests OK (bytecode-free) |
| 2026-06-24 | `setup_index` consolidated via the delegation pattern (`_tool_venv_python`/`_reexec_with_venv_if_needed` → thin delegators to `venv_bootstrap`; zero behavior change). `test_setup_index` green (57). Pattern proven for the remaining resolvers. | `setup_index.py`; `test_setup_index.py` 57 OK |
| 2026-06-24 | Consolidation complete (AC-4): `server_impl`/`upgrade_wavefoundry`/`indexer`/`build_pack`/`run_tests` resolvers delegated; first-line bootstrap in the direct-launch entries. AC-5 (fresh-bootstrap) + AC-6 (single-resolver scan) tests added — 14 bootstrap tests green; scan confirms only `venv_bootstrap` reads `WAVEFOUNDRY_TOOL_VENV` (`render_platform_surfaces` allowlisted → cleared by `1p7pm`/`1p7pn`). Full suite green bar the pre-existing secrets flake. | 12 modules; `test_venv_bootstrap.py` 14 OK; `test_setup_index.py` 57 OK; `test_build_pack.py` retargeted |
| 2026-06-24 | Pre-close review fix: AC-4 was claimed `[x]` but `run_tests.py` imported `venv_bootstrap` without calling `reexec_into_tool_venv()` — added the first-line call (now all 10 direct-launch entries bootstrap). Added the promised **`ReexecAdoptionScanTests`** (asserts every entry self-bootstraps) and strengthened `SingleResolverScanTests` to also flag a `Scripts/python.exe`-vs-`bin/python` venv-PYTHON layout branch outside `venv_bootstrap` (Req-7 wording), keyed on the `python.exe` literal so the codebase-map `"Scripts"` labels + setup_index's `uv.exe` branch don't false-positive. | `run_tests.py` first-line; `test_venv_bootstrap.ReexecAdoptionScanTests` + `test_no_venv_python_layout_branch_outside_bootstrap` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-24 | Land the bootstrap first, configs unchanged | Keeps macOS/Linux runtime identical + CI green before the cross-OS cutover; de-risks the wave. | Flip configs in the same change — rejected: couples a behavior-neutral refactor to the risky cutover. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A heavy import slips ABOVE the bootstrap call in an entry point → it fails on system python before re-exec | The adoption-scan test asserts the bootstrap call precedes any non-stdlib import. |
| `os.execv` used on the Windows path → orphaned host stdio pipe | AC-3 test asserts the Windows path uses `subprocess`, not `os.execv`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
