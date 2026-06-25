# Single cross-OS `wf` CLI dispatcher replacing the POSIX-only bin wrappers

Change ID: `1p7tz-enh wf-cli-dispatcher`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-06-25
Wave: `1p7pk native-windows-launchers`

## Rationale

After the `1p7pk` cutover, the nine `.wavefoundry/bin/*` wrappers are bash-only (`#!/usr/bin/env bash` → `exec python <script>.py`) operator-CLI convenience — **nothing in the runtime spawns them** anymore (the MCP configs and rendered hooks call `python <script>` directly; the only remaining references are docstrings, doc pointers, the `settings.local.json` permission allowlist, and log messages). On native Windows there is no bash, so they don't run at all.

Dual-rendering a `.cmd` per wrapper (18 files) would re-introduce exactly the per-OS launcher proliferation `1p7pm` just retired (the `.sh`/`.cmd` hook trampolines), for convenience-only scripts. Instead, consolidate the nine wrappers into **one cross-OS `wf` Python CLI dispatcher** (`wf <subcommand>`), exposed through a thin `wf` (bash) + `wf.cmd` (Windows) shim pair that self-bootstraps into the venv. Operators get identical short commands on every OS; the framework ships ~3 files instead of nine POSIX-only ones, consistent with the wave-`1p7pk` "single runtime execution surface" goal. (`wf` = wavefoundry.)

## Requirements

1. **`wf_cli.py` dispatcher** — an argparse CLI mapping each operator subcommand to its existing entry: `docs-lint`→`docs_lint`, `docs-gardener`→`docs_gardener`, `gate`→`wave_gate`, `dashboard`→`dashboard_server`, `update-indexes`→the incremental indexer refresh, `lifecycle-id`→`lifecycle_id`, `upgrade`→`upgrade_wavefoundry`, `setup`→`setup_wavefoundry`. Each subcommand forwards `argv` through to the target's own arg parsing. First-line `venv_bootstrap.reexec_into_tool_venv()` so it runs in the venv — **except** the `setup` path, which must stay on the system interpreter pre-symlink (the three-tier model from `1p7pb-adr`); the dispatcher must not block fresh bootstrap.
2. **`render_bin_launchers` emits the shim pair + the dispatcher**: `wf` (bash — resolve `REPO_ROOT` from `$BASH_SOURCE`, `cd`, `exec` the dispatcher with a **`python3`→`python` fallback** so `wf setup` works *pre*-symlink on a fresh box) and `wf.cmd` (Windows — `python "%REPO_ROOT%\…\wf_cli.py" %*`). The only per-OS difference is the shell wrapper itself (bash vs cmd), exactly like the hook env-var sigil — no per-OS *logic* duplication.
3. **Retire the nine individual bash wrappers** (`docs-lint`, `docs-gardener`, `wave-gate`, `update-indexes`, `lifecycle-id`, `wave-dashboard`, `upgrade-wavefoundry`, `setup-wavefoundry`, `mcp-server`). `mcp-server` is vestigial (no config names it post-cutover) — drop it. **Decision (operator-directed 2026-06-25): hard cutover** — DELETE the nine wrappers outright (no forwarders, no deprecation window); the rename to `wf <subcommand>` is called out in the changelog. The wrappers are local operator convenience, not an external contract.
4. **Update every live reference** to the new surface: `.cursor/rules/project-context.mdc`, `.github/PULL_REQUEST_TEMPLATE.md`, the upgrade-wave skill, `upgrade_wavefoundry.py`'s log line, `setup_index.py`/`setup_wavefoundry.py` handoff messages, `AGENTS.md`/`CLAUDE.md` CLI-fallback mentions, and the `settings.local.json` Bash allowlist (`wf *`). No live doc may point at a retired `bin/<wrapper>`.
5. **Cross-OS parity**: every former `bin/foo` capability is reachable as `wf foo`; `wf setup` bootstraps on a fresh box (system `python3`/`python`); `wf dashboard …` keeps the self-detach behavior; macOS/Linux operator capability is unchanged.

## Scope

**Problem statement:** The `bin/*` operator wrappers are bash-only and don't run on native Windows; the runtime no longer depends on them, so the fix is a cross-OS convenience CLI, not a launcher contract.

**In scope:**

- New `wf_cli.py` dispatcher + `render_bin_launchers` rendering `wf`/`wf.cmd` and retiring the nine wrappers.
- Updating all live references (docs, skill, allowlist, log/handoff messages) to `wf <subcommand>`.
- Tests: dispatch mapping, the shim render (bash python3→python fallback + cmd), retired-wrapper scan, no-live-reference-to-old-wrapper scan.

**Out of scope:**

- The MCP tool surface (the primary interface; `wf` is the *CLI fallback* for no-MCP terminals/CI/hooks).
- `1p7pk`'s committed `command: "python"` config/hook cutover (already shipped) — `wf` does not touch the MCP/hook spawn path.
- Re-homing any logic out of the existing scripts; `wf_cli.py` only dispatches to them.

**Depends on:** `1p7pl` (the shared `venv_bootstrap` the dispatcher self-boots through) — landed in `1p7pk`.

## Acceptance Criteria

- [x] AC-1: `wf_cli.py` dispatches every operator subcommand (`docs-lint`, `docs-gardener`, `gate`, `dashboard`, `update-indexes`, `lifecycle-id`, `upgrade`, `setup`) to the correct entry with argv pass-through; first-line venv bootstrap on all paths except `setup` (which stays pre-symlink-safe). Verified by tests. — `wf_cli.py`; `test_wf_cli.WfCliDispatchTests` (routing/argv/prefix + `setup`-no-reexec).
- [x] AC-2: `render_bin_launchers` emits `wf` (bash, `python3`→`python` fallback) + `wf.cmd` (Windows); the nine individual bash wrappers are no longer rendered (and removed on re-render). Verified by a render test. — `render_bin_launchers`; `test_render_platform_surfaces.RenderBinLaunchersTests.test_renders_wf_shim_pair`/`test_retired_wrappers_not_rendered`.
- [x] AC-3: the rendered `wf`/`wf.cmd` carry no per-OS *logic* difference beyond the shell wrapper; the bash shim's pre-symlink `python3`→`python` fallback is asserted. Verified by a test. — `test_renders_wf_shim_pair`.
- [x] AC-4: every live reference (docs, upgrade-wave skill, PR template, `settings.local.json` allowlist, log/handoff messages, `AGENTS.md`/`CLAUDE.md`, seeds) names `wf <subcommand>`; a scan asserts no live doc/config points at a retired `bin/<wrapper>` (historical wave records + `CHANGELOG.md` release history + test files excluded). Verified by a scan test. — `test_wf_cli.NoLiveReferenceToRetiredWrapperTests`.
- [x] AC-5: macOS/Linux operator capability is unchanged (every former `bin/foo` has a working `wf foo` — verified live: `wf docs-lint`, `wf gate status`); framework tests bytecode-free; `wave_validate`/`docs-lint` clean.
- [~] AC-6 (value gate — operator-run): `wf <cmd>` smoke on a real python.org-Windows host (`wf docs-lint`, `wf dashboard`, `wf gate`) and macOS post-symlink, incl. `wf setup` fresh-bootstrap. Deferred/downstream like other native-Windows gates. (Operator-run; cannot be exercised in CI — no real Windows host here.)

## Tasks

- [x] Write `wf_cli.py` (argparse dispatch → existing entries; first-line bootstrap except `setup`).
- [x] `render_bin_launchers`: emit `wf` + `wf.cmd`; remove the nine individual wrappers (**hard cutover** — operator-directed; no forwarders).
- [x] Update live references (docs, skill, PR template, allowlist, log/handoff messages, AGENTS.md/CLAUDE.md, seeds).
- [x] Tests: dispatch mapping; shim render (bash fallback + cmd); retired-wrapper + no-live-reference scans.
- [x] Changelog entry for the `bin/*` → `wf <subcommand>` rename.

## Agent Execution Graph


| Workstream  | Owner       | Depends On  | Notes                                              |
| ----------- | ----------- | ----------- | -------------------------------------------------- |
| dispatcher  | implementer | —           | `wf_cli.py` argv-passthrough dispatch              |
| renderer    | implementer | dispatcher  | `render_bin_launchers` → `wf`/`wf.cmd`; retire 9   |
| references  | implementer | renderer    | docs/skill/allowlist/messages → `wf <subcommand>`  |
| tests       | implementer | dispatcher  | dispatch + render + retired/no-reference scans     |


## Serialization Points

- Independent of `1p7pk`'s remaining close gate (AC-6). Best landed *after* `1p7pk` closes so the launcher surface settles first; can also be folded into `1p7pk` if the operator prefers (delays that wave's close + needs a test-pack rebuild).

## Affected Architecture Docs

- Touches the operator-CLI surface only; no boundary/flow change. Note the `bin/*` → `wf` consolidation in `docs/references/native-windows-support.md` at close. Confirm at Prepare.

## AC Priority

(Proposed; confirmed at Prepare.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The dispatcher is the deliverable. |
| AC-2 | required  | The cross-OS shim render is the cross-platform fix. |
| AC-3 | important | Locks "no per-OS logic" + the pre-symlink bootstrap path. |
| AC-4 | required  | A retired wrapper still referenced is a broken operator instruction. |
| AC-5 | required  | No macOS/Linux capability regression; test-locked. |
| AC-6 | important | Real-Windows value gate. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-24 | Drafted after `1p7pk` exposed the `bin/*` wrappers as the last POSIX-only launcher surface. Operator chose a single `wf` dispatcher over dual-rendering or POSIX-only sugar. Confirmed the wrappers are convenience-only (no runtime spawns them — grep across configs/hooks/scripts). | `1p7pk`; `.wavefoundry/bin/*` (9 bash wrappers); grep: configs/hooks call `python <script>` not the wrappers |
| 2026-06-25 | Implemented (admitted into OPEN wave 1p7pk; HARD CUTOVER per operator). `wf_cli.py` argparse dispatcher routes `docs-lint`/`docs-gardener`/`gate`/`dashboard`/`update-indexes`/`lifecycle-id`/`upgrade`/`setup` to the existing entries with argv pass-through (sets `sys.argv` for sys.argv-reading targets like docs_lint; passes `argv` for the rest; `dashboard`/`update-indexes` keep the retired wrappers' fixed prefix args). Re-execs into the venv for every subcommand except `setup` (pre-symlink-safe). `render_bin_launchers` now emits ONLY `wf` (bash, `python3`→`python` fallback) + `wf.cmd` (Windows); the nine wrappers are deleted (renderer stale-list + on-disk). `.gitattributes` pins `*.cmd` to CRLF. ~46 live references swept to `wf <subcommand>` (docs, seeds, AGENTS/CLAUDE, settings.local allowlist, PR template, cursor rule, renderer docstrings + log/handoff messages); C-1/C-2 marked RESOLVED in native-windows-support; CHANGELOG `[Unreleased]` bullet added. Live-verified `wf docs-lint`/`wf gate status`. Full parallel suite green; `docs-lint` clean. | `wf_cli.py`; `render_bin_launchers`; `.gitattributes`; `test_wf_cli.py` (dispatch + no-live-reference scan); `test_render_platform_surfaces.RenderBinLaunchersTests` |
| 2026-06-25 | Pre-close review found THREE DYNAMIC `Path / "bin" / "<wrapper>"` references the literal-string scan missed (it only matched the `.wavefoundry/bin/<name>` string, not path-join constructions): (1) `build_pack.check_docs_gate` — already fixed by reviewer to run the scripts under `sys.executable`; updated its `DocsGateTests` fixtures to create fake `docs_gardener.py`/`docs_lint.py` under `framework/scripts/`. (2) **REAL BREAKAGE** — the rendered hook helper `maybe_docs_lint` ran the deleted `bin/docs-lint` with no fallback (Cursor docs-edit hook would fail); fixed to `run_command([sys.executable, str(scripts/docs_lint.py)])` (`sys` is plainly imported in the helpers section), regenerated all hook surfaces — `.cursor/hooks/after-file-edit.py` now calls `docs_lint.py`. (3) `upgrade_wavefoundry.phase_docs_gate` — the always-false `bin/<name>` probe simplified to `[_preferred_python(), scripts/<module>.py]` (behavior identical). Strengthened the AC-4 scan with `test_no_dynamic_bin_wrapper_construction_in_scripts` (flags `"bin" / "<wrapper>"` path-joins; verified it catches the pre-fix pattern, ignores `_RETIRED_BIN_WRAPPERS`/`bin_dir / "wf"`). Exhaustive re-grep (`"bin"`/`bin_dir`) found no other retired-wrapper invocations. Full parallel suite green (3469); pack rebuilt at 1.9.0. | `render_platform_surfaces.maybe_docs_lint`; `upgrade_wavefoundry.phase_docs_gate`; `test_wf_cli.test_no_dynamic_bin_wrapper_construction_in_scripts`; `test_build_pack.DocsGateTests` |
| 2026-06-25 | Second pre-close review — MAJOR newline bug + minors. **MAJOR:** `render_platform_surfaces.write_text` used the default `newline=None`, which on a native-Windows re-render translates `\n`→`os.linesep`, doubling the CR in the CRLF-embedded `wf.cmd` (`\r\r\n`, breaks `%REPO_ROOT%`) and giving CRLF shebangs to the LF bash/`.py`/hook surfaces (break git-bash/WSL2). Fixed to open with `newline=""` so embedded terminators are written VERBATIM, byte-identical on every host. Verified post-render: `wf.cmd`=7 CRLF / 0 doubled-CR, `wf`+rendered hooks=0 CR. **Minors:** removed the non-ASCII em-dash from the `wf.cmd` REM comment (legacy-codepage safe); strengthened the dynamic-bin scan to also catch a variable bin-dir join (`<bin-var> / "<wrapper>"`, the demonstrated false-negative; `wf`/`_RETIRED_BIN_WRAPPERS` stay non-matching); added a one-line note that the POSIX OS-trust-store tier is empty on Windows (1p7s6 host-agent/certifi tiers cover it). Tests: `WriteTextNewlineFidelityTests` (CRLF/LF written verbatim, survives patched `os.linesep`) + CRLF/LF + no-em-dash assertions in `test_renders_wf_shim_pair`. Pack rebuilt at 1.9.0. | `render_platform_surfaces.write_text` (`newline=""`); `test_render_platform_surfaces.WriteTextNewlineFidelityTests` + `test_renders_wf_shim_pair`; `test_wf_cli.VAR_BINDIR_PATTERN` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-24 | Single cross-OS `wf` Python dispatcher + `wf`/`wf.cmd` shims | One self-bootstrapping CLI works identically on every OS; ~3 files vs 9 POSIX-only or 18 dual-rendered; matches the single-runtime-surface goal. | Dual-render `.cmd` per wrapper — rejected (re-introduces the per-OS proliferation 1p7pm retired). POSIX-only sugar + documented `python <script>.py` — viable but no short Windows command. |
| 2026-06-25 | **Hard cutover** — DELETE the nine bash wrappers, no `exec wf <subcommand>` forwarders, no deprecation window | Operator-directed: the wrappers are local convenience, not an external contract; a forwarder window adds 9 throwaway files + a deprecation print for no external consumer. The rename is documented in the changelog and every live reference is updated to `wf <subcommand>`. | One-release deprecation forwarders (the Req-3 default proposal) — rejected by operator direction. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Operator muscle-memory / scripts call the old `bin/<wrapper>` names | Update every live reference; call the rename out in the changelog; optionally a one-release deprecation-forwarder window (decided at Prepare). |
| `wf setup` re-introduces the pre-symlink circularity | The `wf` bash shim uses the same `python3`→`python` fallback as the retired `setup-wavefoundry` shim; `setup` subcommand does not force the venv re-exec. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
