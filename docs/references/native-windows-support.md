# Native Windows Support — Scoping & Decision Assessment

Owner: Engineering
Status: supported
Last verified: 2026-10-19

## SQLite conversion qualification (1xjmm)

Native Windows support currently requires an x64 Python environment for the pinned sqlite-vec 0.1.9 binary. Native ARM64 and 32-bit Python have no matching wheel or source distribution; they are unavailable through this pinned setup path, not merely untested. WSL2 uses the Linux dependency path (glibc 2.28 or newer for APSW); keep the checkout on its local Linux filesystem. A compatible wheel does not prove native execution: Windows package tests for this conversion remain pending.

The project index needs local WAL-capable storage. Since wave `1xny6` one database, `.wavefoundry/index/index.sqlite`, holds both the semantic layers and the code graph, so that requirement now covers graph work too and Windows file-sharing locks matter for a single file rather than several. If setup reports WAL/runtime failure, correct the filesystem or native environment and retry without deleting the index. On cutover access/sharing failure, release database handles or correct permissions and resume the ordinary upgrade; the migration receipt and recoverable data remain, and recovery is forward — re-run the standard upgrade rather than reverting to the previous runner. A checkout reached through a trusted resolved profile/junction is distinct from an unowned reparse point inside its index tree; cleanup continues to refuse the latter.

## Context

Downstream users are running the Claude Code CLI on **native Windows** (standard Windows Terminal with PowerShell/cmd, **not** WSL) and asking whether Wavefoundry supports that environment. This document records what an investigation of the current code found, the work completed across multiple waves, and known remaining limitations. Native Windows is now **supported** — the blocking gaps identified in this scoping artifact have been resolved.

All findings below are cited to `file:line` from a read of the actual sources.

## Headline

Native-Windows support is **more than the bin shell scripts, but less than a rewrite.** The codebase already carries substantial, partially-finished Windows awareness; the blocking gaps are concentrated in the agent entry points (MCP server + bin launchers) and in one architectural decision about how a single repo serves both macOS/Linux and Windows developers.

## What already works (the foundation)

Windows was considered — and handled correctly — in several places:

- Process termination branches to `taskkill /PID <pid> /T /F` on `os.name == "nt"` (`wf_server/server_impl.py`).
- Process liveness, zombie state, command lines, working directories and start times come from `psutil` through `process_info.py` in the MCP server and the indexer (wave `1zc7n`, ADR `1z9df-adr psutil-process-info`); `psutil`'s Windows code is tested on Windows CI upstream, so no `tasklist` or PowerShell query runs on the MCP status path. Code that runs before dependencies are installed keeps a standard-library path: `upgrade_lib._pid_is_running` (timed `tasklist`), `dashboard_lib`'s dashboard scan (PowerShell/CIM) and `sqlite_storage_migration` (a `SYNCHRONIZE`-only `OpenProcess` probe). Application control (AppLocker or WDAC) must allow `psutil`'s extension (`_psutil_windows.pyd`) in the tool environment, as it already must allow the `apsw` and `sqlite-vec` extensions; when it is blocked, builds still run under the OS locks and `index_health` reports `process_info_unavailable` with the `wf setup` remedy.
- File locking branches between `msvcrt.locking` (Windows) and `fcntl.flock` (POSIX) (`indexer.py:1906`, `dashboard_lib.py:171`).
- Most background spawns set `creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` on Windows (`wf_server/server_impl.py`, `setup_index.py:771`, dashboard spawn `wf_server/server_impl.py`).
- Path strings are normalized through `replace("\\", "/")` before posix-path operations (`chunker.py:375` `_normalize_path`; `dashboard_lib.py` multiple sites).
- Hook bodies are Python on every OS. Claude launch commands resolve the body from `CLAUDE_PROJECT_DIR` inside Python, avoiding shell-specific environment-variable syntax; hosts without a verified owner anchor retain an explicit repository-root contract.
- `DmlExecutionProvider` (DirectML) is auto-detected and selected when available — it is in `PROVIDER_PRIORITY` (`provider_policy.py:26`) so no manual `WAVEFOUNDRY_EMBED_PROVIDER=dml` override is needed.
- macOS-only shell-outs (`sysctl`, `.DS_Store` cleanup) are correctly guarded with `sys.platform != "darwin"` (`graph_indexer.py:7766`, `render_platform_surfaces.py:1382`).

The floor is not zero. The work is finishing and verifying, not starting from scratch.

## Console windows (native Windows)

On native Windows a Python process spawned without a no-window flag can flash a blank console. Wavefoundry suppresses the windows it controls and documents the one it does not:

- **Synchronous helper subprocesses** launched by the MCP server (docs-lint, docs-gardener, sync-surfaces, upgrade phases, sensors, and similar bounded calls) go through one shared helper that sets `stdin=subprocess.DEVNULL`, captures/redirects stdout/stderr, and adds `CREATE_NO_WINDOW` on Windows. This both eliminates their console flash and keeps them from inheriting the MCP server's JSON-RPC stdio (the cause of the `wf_validate_docs`/docs-lint-over-MCP timeout).
- **Detached background jobs** (the index refresh, the dashboard daemon) already run window-free: `DETACHED_PROCESS` does not allocate a console, so they show no window regardless. `CREATE_NO_WINDOW` is additionally applied where it composes safely; on already-detached paths it is defensive, not load-bearing. These spawns, and the background reindex the rendered hooks start, also use `close_fds=True` on every OS, passed explicitly or as Python's default (wave `2134v`): with `close_fds=False` a Windows child inherits every inheritable handle of its parent, including the MCP server's stdio pipes or a hook's pipes to its host, which surfaced as `MCP error -32000: Connection closed` after write tools.
- **The main MCP server window is host-controlled, not Wavefoundry-controlled.** The MCP host (Claude Code, Cursor, …) creates the `python3 server.py` process; nothing inside `server.py` can hide that window after the host has created it. If a blank window persists after child-process suppression, the visible process is the host-launched server, and the remedy is a host-side no-console launcher strategy (e.g. a `pythonw`-style launcher) — tracked as an evidence-gated follow-up, not something the framework can fix from inside the server.

## Gap inventory (by severity)

### Critical — a native-Windows user is blocked

| ID | Gap | Evidence | What breaks |
| --- | --- | --- | --- |
| ~~C-1~~ | ~~`.mcp.json` sets `command` to a bash MCP-server wrapper with no `.cmd` sibling~~ — **RESOLVED:** MCP configs use `python3`; Claude resolves the script from `CLAUDE_PROJECT_DIR`, Cursor pins workspace cwd, Junie uses its documented config-relative path, and hosts without a verified anchor retain an explicit repository-root contract. The bash wrapper was retired (1p7tz). | MCP configs; platform renderer | No action — no shell wrapper is required. |
| ~~C-2~~ | ~~All 9 `.wavefoundry/bin/` launchers are bash-only~~ — **RESOLVED (wave 1p7tz):** the nine POSIX-only wrappers were replaced by one cross-OS `wf` dispatcher (`wf_cli.py`) behind a `wf` (bash) + `wf.cmd` (Windows) shim pair; `wf docs-lint`, `wf docs-gardener`, `wf gate`, `wf setup`, `wf upgrade`, `wf update-indexes`, `wf dashboard`, `wf lifecycle-id` run on every OS. | `render_platform_surfaces.render_bin_launchers`; `wf_cli.py` | No action — operator CLI is cross-OS. |
| ~~C-3~~ | ~~Committed hook config reflects whichever OS last rendered it~~ — **RESOLVED:** committed commands are platform-independent; Claude performs owner-root resolution inside Python and Copilot carries its native `bash` and `powershell` fields. | platform renderer; host hook configs | Native-Windows runtime smoke remains an operator validation item. |

Native Windows MCP configs use `command: "python3"` with `args: [".wavefoundry/framework/scripts/server.py"]` for generated repo-local configs, or `args: ["<repo>/.wavefoundry/framework/scripts/server.py", "--root", "<repo>"]` for manual host entries. Do not configure MCP to run `.wavefoundry\venv\Scripts\python.exe` directly as a workaround; `server.py` owns shared tool-venv activation. Python 3.13 or newer is recommended, but 3.11 is the current minimum.

### Diagnose a new native-Windows workstation before MCP

This applies both to first installation and an already-seeded checkout on another machine. Committed host config and completed install-log rows do not prove the local interpreter works. From the repository root, before `wf.cmd`, setup or MCP attachment, run the read-only script that needs neither Python nor MCP:

```powershell
powershell -NoProfile -File ".\.wavefoundry\framework\scripts\diagnose_python.ps1"
```

On first installation, a successful supported `python3` check permits setup to provision the tool environment before the server dry-run; do not require MCP bootstrap before its dependencies exist. Existing provisioned checkouts need no forced setup or rebuild merely for command repair.

Record the failed stage and attempted command, the resolved path and interpreter identity when available, and the observed error, exit status or timeout. The script checks `python3` and, for diagnosis, an available `python` entry with finite version probes. A discovered `python.exe` does not satisfy MCP's `python3` contract. Distinguish a missing command, old interpreter, failed execution, timeout and a later `server.py --dry-run` failure. A Store-placeholder explanation is supported only when the observed path or error identifies it; a generic failed exit is not proof. Do not infer PATH, alias or enterprise-policy causation from executable presence alone. A cause without supporting evidence remains undetermined, with the next probe named.

If PowerShell execution policy blocks the script, do not bypass the policy. In PowerShell run `Get-Command python3,python -All -ErrorAction SilentlyContinue`, `where.exe python3`, `where.exe python`, `python3 --version`, and, when present, `python --version`; report their exact outcomes. Ask IT for the approved diagnostic route if those probes are also restricted.

For a compatible existing interpreter, prefer an already approved `python3` executable or alias and a permitted user-level PATH correction. Check command resolution again in a **new terminal and restarted agent host**; a session-local PowerShell alias or `.cmd` shim is insufficient for a host that directly spawns `python3`. Do not assume administrator rights, Microsoft Store access, Developer Mode, machine-wide PATH changes, or that a particular installer creates `python3`. A new user-local executable launcher remains unqualified and is not a supported repair in this release. Do not reseed, run a rebuild, delete index data, or edit committed MCP config to address this machine-local prerequisite.

If no permitted local repair exists, keep setup unready and send IT this handoff: “Wavefoundry requires a host-visible `python3` command resolving to Python 3.11 or newer. `python3` failed at [stage] with [exact output/status/timeout]; resolution was [path or absent]. The approved existing interpreter is [path/version, if found]. Please provide or authorize a `python3` entry visible to directly spawned processes for this standard user, without replacing the committed MCP launch command. I will restart the agent host and verify `python3 --version`, `python3 .wavefoundry/framework/scripts/server.py --dry-run`, and MCP startup.”

After any repair, use those verification commands from the repository root, reconnect/restart the agent host, then confirm MCP initialization and a representative generated hook in a path with spaces. A passing `python.exe` probe or terminal-only alias does not prove a fresh host can spawn `python3`. Native-Windows diagnostic branches, standard-user repair and fresh-host evidence remain unverified. For wave 1yp0y, the operator deferred this qualification to external testers after the next release on 2026-09-22; see docs/waves/1yp0y pre-release-install-reliability/post-release-windows-validation.md.

### Moderate — degrades behavior; MCP server itself survives

| ID | Gap | Evidence | What breaks |
| --- | --- | --- | --- |
| ~~M-1~~ | ~~`dashboard_cmdline_pids` returns `None` on `os.name == "nt"` — no scan~~ — **RESOLVED (wave 1p6eq):** native Windows now gets a PowerShell/CIM cmdline scan (`_windows_process_cmdlines`); the probe also isolates `stdin` and suppresses the console window (wave 1p88t). | `dashboard_lib.py` (`_windows_process_cmdlines`, `dashboard_cmdline_pids`) | No action — orphan reconciliation runs on Windows. |
| ~~M-2~~ | ~~One background reindex spawn sets `start_new_session=True` without the Windows `creationflags`~~ — **RESOLVED (wave 1p7pn/1p88t):** all detached reindex/dashboard spawns set `creationflags = DETACHED_PROCESS \| CREATE_NEW_PROCESS_GROUP \| CREATE_NO_WINDOW` on Windows and `stdin=DEVNULL`. | `wf_server/server_impl.py` (`_start_background_index_refresh` + sibling spawns) | No action — background reindex detaches correctly on Windows. |
| ~~M-3~~ | ~~Git hooks rendered as `#!/usr/bin/env python3`; native Windows git can't run shebang Python directly~~ — **REMOVED (wave 1p88t): the git hooks were dropped entirely.** They only spawned a background incremental reindex and were opt-in/inactive-by-default; the in-session staleness monitor (wave 1p5xu) already hash-detects and refreshes VCS-driven index staleness within ~20s of an agent session, and `indexer.py`'s incremental diff is global so any trigger catches up `git pull`/`merge`/`checkout` changes. `render_git_hooks`/`git_hook_source` were removed and `remove_git_hooks` cleans up prior renders. The git-bash/`python3` execution concern is therefore moot. | `render_platform_surfaces.remove_git_hooks` (cleanup) | No action — git operations were never blocked; freshness is covered by the staleness monitor + global incremental reindex. |

### Low / pre-existing (not Windows-specific regressions)

| ID | Gap | Evidence | Note |
| --- | --- | --- | --- |
| ~~L-1~~ | ~~No `.gitattributes` for line-ending control~~ — **RESOLVED (wave 1p9hm):** `.gitattributes` now pins `*.py`, launchers, and text assets to `eol=lf`, guarding against `core.autocrlf` shebang corruption on git-for-Windows. | `.gitattributes` | No action. |
| ~~L-2~~ | ~~Secrets scan is a no-op off macOS~~ — **CORRECTED (wave 1p6d5): not a bug.** The `if sys.platform != "darwin": return` at the cited lines is inside `_physical_perf_core_count()` (a perf-core-count helper that gracefully returns `None` off macOS so the scan uses a default core count). The **secrets scan itself runs on Linux, WSL2, and Windows** — it is not gated by platform. | `scan_secrets.py:40-45`, `run_secrets_scan.py:32-33` (the helper, verified) | No action — the original claim misread the perf helper as a scan gate. |
| ~~L-3~~ | ~~DirectML accepted but never auto-detected~~ — **RESOLVED:** `DmlExecutionProvider` is in `PROVIDER_PRIORITY` (`provider_policy.py:26`) and is auto-selected when available in the ONNX Runtime install. No manual `WAVEFOUNDRY_EMBED_PROVIDER=dml` override needed. | `provider_policy.py:26` | No action. |
| L-4 | `PurePosixPath` used on real filesystem path strings | `chunker.py:10` and call sites | Safe in practice — every call site routes through `_normalize_path` (backslash → forward slash) first. Theoretical fragility if a raw Windows path bypasses normalization, but no known path does. |

## Work buckets

### Bucket 1 — Portable entry points (the hard blocker)

The MCP launcher (C-1) and bin launchers (C-2) need a Windows-runnable form. The recommended approach is **not** `.cmd` twins of every bash script (two parallel script families to maintain), but to **bypass the shell wrapper**: point `.mcp.json` at `python3` running `server.py`, and have the entry scripts self-bootstrap into the tool venv (`~/.wavefoundry/venv/bin/python` on POSIX, `Scripts\python.exe` on Windows). One portable mechanism instead of two. This is the gate — until the server starts and `docs-lint`/`wave-gate` run, nothing else is reachable.

### Bucket 2 — The selected cross-OS distribution model

**Resolved by C-3.** Each host has one committed, deterministic configuration artifact. Portable
commands remain identical across operating systems; where a host schema requires an OS-specific
override, the POSIX and Windows fields coexist in that same artifact. A mixed macOS/Linux/Windows
team therefore does not re-render tracked configuration per checkout and does not maintain
OS-suffixed sibling files. Native-platform runtime smoke remains an evidence obligation, not a
different distribution model.

### Bucket 3 — Process / dashboard lifecycle parity

**Fully landed.** M-1 (Windows `dashboard_cmdline_pids` scan, via PowerShell/CIM) and M-2 (`creationflags` on the detached reindex spawns) are resolved; M-3 is moot — the git hooks were **dropped** (wave 1p88t), since the in-session staleness monitor + global incremental reindex already cover VCS-driven freshness. L-1 (`.gitattributes` line-ending control) was resolved in wave 1p9hm.

### Bucket 4 — Verification you can trust

None of the remaining `taskkill` / `tasklist` / `msvcrt` / `creationflags` branches have ever run on a real Windows host in CI — they are **unverified**. Credible Windows support requires a Windows smoke path (CI runner or, at minimum, a documented manual checklist exercising: MCP server start, `docs-lint`, a wave-gate open/close, a dashboard start/stop, an index build). The biggest hidden risk in this whole effort is shipping Windows branches that have never executed on Windows.

## Status summary

All critical (C), medium (M), and low (L) items identified in this scoping assessment are resolved or closed. Native Windows is supported. The one remaining theoretical concern is L-4 (`PurePosixPath` fragility), which is safe in practice given universal `_normalize_path` call coverage.

## References

- Investigation date: 2026-06-17 (against framework `1.7.0`).
- Renderer: `render_platform_surfaces.py` (`launcher_command`, `render_mcp_json`, `render_bin_launchers`, `remove_git_hooks` — git hooks dropped in wave 1p88t).
- Platform mapping: `docs/agents/platform-mapping.md`.

## Python runtime policy

Python 3.13 or newer is recommended. Python 3.11 and 3.12 are deprecated but remain allowed; the minimum is still 3.11. No removal release is scheduled. Dependencies must support the selected interpreter; this recommendation does not qualify every future Python release.

The notice appears once per `wf` invocation or direct MCP serving startup, on stderr. Inspect `setup_readiness.advisories` through index health when host logs are hidden. It does not request repair or change command success. Follow the [runtime transition procedure](../../.wavefoundry/framework/README.md#python-runtime-advisory-and-transition): select PATH `python3` for setup and the restarted host, stop shared-environment consumers or propagate an isolated environment override, and retain pending recovery ownership. Ordinary setup may replace an incompatible tool environment; the advisory never does.

## Review-plan prompt migration recovery

An upgrade can refuse the legacy Review Plan prompt when its exact legacy contract lines were customized, when both legacy and new prompt paths exist, or when the legacy entry is linked, not a regular file, unreadable or not UTF-8. The incoming pack checks this before checkpoint, framework, policy or operating-document mutation on runners carrying the `post_preflight` hook (the executed v1.15.4 hook ABI is supported). Early runtime locks, temporary verified staging and the diagnostic upgrade log are permitted. Old-runner dry runs do not invoke that hook; a missing incoming checker warns and continues, and edits between preflight and rendering can still fail during rendering.

Preserve project prose and aliases; locate the legacy prompt using the path reported in the refusal. Create `docs/prompts/review-plan.prompt.md` from the packaged `.wavefoundry/framework/install/lifecycle-prompts/review-plan.prompt.md` template, merge the project prose and aliases, remove the old prompt, and update `docs/prompts/index.md` and the prompt manifest. Retry the upgrade after that repair. A retry is safe, but avoids marking waves for re-Prepare only when the migrated policy is byte-identical, carrier reconciliation has no edits and the evaluator is current. Changed policy/carriers or a stale evaluator legitimately require re-Prepare. A preflight refusal leaves no new upgrade checkpoint; an older already-mutated run retains its failed checkpoint and must follow the existing recovery guidance.

## Retained index-guard continuation

Use the checkpoint's emitted continuation command after stopping its recorded hosts. Proven post-docs handoffs use `--update-index` with `--confirm-hosts-stopped`; unproven, pre-docs and storage/rebuild states keep the full upgrade command. Pack-backed continuations own one verified file at `.wavefoundry/cache/upgrade/index-guard-feature.zip`, independently of temporary staging and the external original. Do not replace that file with a matching archive: its root, token, target, file identity and hash must match the checkpoint. Links, name-surrogate or unclassified reparse metadata, nonregular files, multilinks and permission failures refuse. Valid non-surrogate tags pass link classification; the other guards still apply. Windows reparse/permission coverage is injected simulation, not native Windows qualification.

Paused or failed publication, validation or cleanup retains recovery authority. After fatal storage/dashboard obligations succeed, cleanup records terminal completion before deleting the owned archive. If archive or checkpoint deletion fails, retry `--cleanup`; the validated terminal checkpoint permits this retry even after the archive was deliberately removed, without loading it or running rendering/indexing again. Ordinary resume still requires the owned archive. Fresh-process lost-TMP tests demonstrate restart recovery with bounded fake index children, not a measured reboot. The final identity-check/unlink sequence is not atomic against concurrent replacement.


## Reparse classification and lifecycle scan qualification

The contained-file, lint, renderer, bytecode-cache, review-authority, record-path, retired-sidecar and lifecycle-lock boundaries use one classification rule: POSIX symlinks and Windows tags carrying the name-surrogate bit (`0x20000000`) are links, including unknown surrogate tags. A reparse attribute with missing, invalid or unusable tag metadata refuses at these boundaries. An explicit valid non-surrogate tag, such as the simulated OneDrive or dedup tag, passes link classification while regular-file, containment, identity and size guards still apply. This classifies metadata; it does not establish cloud-file hydration or qualify native OneDrive or dedup behavior.

The lifecycle scan refreshes Windows directory metadata with a no-follow stat and reclassifies it before traversal. Its visited keys use usable device/inode identity or a tagged normalized canonical path when identity is unavailable, across scan roots, real children and admitted linked targets. Real record trees remain outside the entry budget; only subtrees reached through directory links consume it. The Windows-shaped tests cover zero identities, replacement links, disappearance, access errors, repeated targets and cycles. The `msvcrt` lock mechanism is unchanged.

Native Windows and drvfs execution of these changes remain unverified. Link classification can only use metadata the host exposes: a mount that hides name-surrogate/link metadata cannot be promised equivalent detection. Useful inode and `st_nlink` values on drvfs are also unqualified; no blanket claim applies to every drvfs mount. Keep WSL2 checkouts on the Linux filesystem as documented above.

## Conditional path and permission diagnostics

A long path with WinError 3 can mean that the host lacks working long-path support. Wavefoundry reports that as unreadable with a conditional hint; it does not diagnose or change the registry. Ordinary missing parents and WinError 2 keep their absent result. Invalid-name errors suggest checking spelling and reserved names. UTF-8 BOM workflow configuration is accepted by the shared include-prefix reader; malformed configuration still yields no prefixes.

A known Windows READONLY target is refused before publication, separately from a file that stays in use. Preserve the original and adjust its permissions explicitly if appropriate. A named descriptor-chmod failure is tolerated only when the actual new file descriptor already has the intended final permissions; an umask mismatch preserves the original. Command shims `uv.cmd` and `uv.bat` are reported and never executed; use `uv.exe` or the existing pinned, hash-verified bootstrap.

Qualification here used synthetic Windows metadata/errors and real POSIX descriptor controls, not a native Windows or drvfs run. Before claiming native qualification, probe long versus short missing paths, a BOM config, READONLY versus sharing violations, a shim-only PATH, and descriptor modes on the intended filesystem. The earlier warm-up return-value claim was disproved and remains deferred pending an actual Windows reproduction; no warm-up or timing policy changed.

## Retained archive cleanup and native probes

Combined upgrade archives are retained under `.wavefoundry/upgrade-assets/embedded-*.zip`; phase cleanup removes them only after current ownership and hash checks. Native Windows uses the bounded path fallback when descriptor-relative deletion is unavailable. It rechecks ancestors and final identity but retains a residual same-user pathname race. Index-guard continuation packs use `.wavefoundry/cache/upgrade/index-guard-feature.zip` and require atomic no-clobber hard-link publication; unavailable capability produces controlled restart/refusal guidance.

A failed guard-pack read-back first attempts to remove only the invocation-owned file. If removal is refused but exclusive ownership remains provable, the normal checkpoint retains that proof and reports `index_guard_durable_pack_retained_validation_unavailable`; retry its continuation after resolving access. Retry still validates identity and hash before archive execution. An unavailable proof, remaining private hardlink, or combined rollback/checkpoint-write failure stops explicitly for manual recovery: preserve the checkpoint and original package, and never replace or adopt an occupied slot by filename. On Windows a handle-based `ReOpenFile` adapter preserves the held file identity while permitting private-name removal; adapter failure occurs before publication. The adapter's API/resource tests are simulated, not native sharing qualification.

Legacy temporary-pack proofs accept an equivalent canonical temporary parent, including macOS `/var` and `/private/var` spellings. Only the parent is normalized, after the original proof/path binding; final links, replacements, unrelated parents and unproven legacy absence remain refused.

Native Windows and WSL2 execution remain unverified. The operator qualification probes are:

- **Native archive cleanup:** complete a combined-pack upgrade on NTFS. Verify successful cleanup is silent and sharing or permission refusal reports retention.
- **Interrupted retain/resume:** interrupt after guard-pack publication, restart the host and verify exact retained-package resume without replacing an occupied destination.
- **Reboot continuity:** retain both archive types, reboot, resume and complete terminal cleanup. Device drift in historical proof must not weaken current identity or hash checks.


## Repository layout and surface directories

Lifecycle holds refuse directory links targeting the repository root or an ancestor of an active scan top before descending through them. For example, `docs/site -> ..` is unsupported: replace it with a real directory or point it at a bounded content subtree, then retry. Ordinary safe links keep their existing scan coverage and phase-2 entry budget. Cache directories remain scanned for aliases of runtime locks; a layout repair never grants permission to hide those aliases.

Surface rendering keeps its lexical no-link parent policy on every applicable platform. A linked `.claude`, `.codex` or other output parent refuses even when its target stays inside the repository, because the lexical chain must not redirect a surface write. Preserve existing settings, replace the linked parent with a real directory at the expected location and restore the intended contents there before retrying rendering. This policy is narrower than ordinary contained reads; no renderer containment relaxation is included.

A failed stale-bytecode-cache rename, including an injected `EXDEV`, leaves the process without project-cache reads or writes and reports once with a bounded escaped diagnostic. The old generation stays in place without a current-generation stamp; it is never removed in place as a fallback. Correct the filesystem/access problem and retry in a fresh process. Explicitly disabled and read-only modes remain silent and do not flush. These are injected-fault and local-symlink results; native overlayfs, reboot, Windows and timing qualification remain unverified.

Verified temporary packs carry a recorded temporary-parent proof so cleanup can use their original owned location after TMPDIR changes. Older path/identity-only proofs remain supported for present files under the current temp parent; unprovable legacy parents or absence retain/refuse with bounded basename-only recovery guidance. Cleanup revalidates parent/file identities without an additional archive hash pass. The normal staging validation and expected-hash check remain unchanged.
