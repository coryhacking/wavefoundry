# Windows CLI encoding + path robustness

Change ID: `1p8gv-bug windows-cli-encoding-and-path-robustness`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p8gx windows-upgrade-hardening`

## Rationale

A real native-Windows 1.9.4 upgrade **broke** on three encoding/path defects:

1. **`/tmp` FileNotFoundError.** `upgrade_wavefoundry.py:58` falls back to `os.environ.get("TMPDIR", "/tmp")`; `/tmp` does not exist on Windows, so the old-MANIFEST copy at `:2180` (`shutil.copy2(old_manifest, OLD_MANIFEST_TMP)`) raises `FileNotFoundError`.
2. **`_log()` UnicodeEncodeError.** The upgrade CLI prints `⚠` (U+26A0) at ~25 sites via `_log`/`print`, but **never reconfigures stdout to UTF-8** — only `server.py:65` does, for the MCP runner. In a cp1252 console, `print("⚠")` raises `UnicodeEncodeError` and crashes the upgrade.
3. **Garbled `\u0000`/`\n`/`??` output.** Captured spawns use `subprocess.run(..., capture_output=True, text=True)` **without `encoding="utf-8"`** (`:1247`); combined with the cp1252 stdio and the structured-summary JSON, the upgrade output mojibakes (literal `\n`, `??` for non-ASCII, runs of `\u0000`).

The Windows agent hand-patched #1 and #2 **locally on the consumer machine** — those fixes must land in canonical source here.

## Requirements

1. A shared UTF-8 stdio reconfigure helper (extract/reuse the `server.py:65` logic) invoked at **all** CLI entry points (`upgrade_wavefoundry`, `setup_wavefoundry`, `wf_cli` dispatcher, `docs_gardener`, `docs_lint`, `scan_secrets`/`run_secrets_scan`, `gen_codebase_map`, `dashboard_server`, `render_platform_surfaces`) so prints never crash on non-ASCII in a cp1252 console.
2. Replace the `/tmp` fallback (`upgrade_wavefoundry.py:58`) with `tempfile.gettempdir()`, and audit the framework for other hardcoded POSIX-path assumptions (`/tmp`, `/dev/null` literals, etc.).
3. All captured `subprocess.run(..., text=True)` calls specify `encoding="utf-8", errors="replace"` so child output decodes consistently across OSes.
4. Reproduce + fix the garbled `\u0000`/`\n` upgrade output (the structured-summary/transcript rendering on Windows). Requires a Windows-console repro; the stdio + capture-encoding fixes are the leading candidates.

## Scope

**Problem statement:** the Windows upgrade CLI crashes on `/tmp` and on cp1252-unencodable characters, and emits garbled output.

**In scope:**

- Shared UTF-8 stdio reconfigure at all CLI entry points.
- `/tmp` → `tempfile.gettempdir()` + a POSIX-path-assumption audit.
- `encoding="utf-8", errors="replace"` on all captured spawns.
- Reproduce + fix the `\u0000`/`\n` garble.

**Out of scope:**

- The subprocess console/stdin isolation (sibling `1p8gu`) — though both touch the same `subprocess.run` calls (see Serialization).
- The install-audit parser (sibling `1p8gw`).

## Acceptance Criteria

- [x] AC-1: a shared UTF-8 stdio reconfigure runs at every CLI entry point; printing `⚠`/non-ASCII does not raise under a simulated cp1252 stdout (test). — `cli_stdio.configure_utf8_stdio()` wired into ALL CLI entry points (review F3 added the missed ones): `upgrade_wavefoundry`, `setup_wavefoundry`, `setup_index`, `wf_cli`, `docs_gardener`, `docs_lint`, `run_secrets_scan`, `gen_codebase_map`, `dashboard_server`, `render_platform_surfaces`, `gpu_doctor`, **`indexer`** (the spawned child that printed `→`), **`check_version`**, **`prune_framework`**. Tests: `test_cli_stdio.ConfigureUtf8StdioTests` + `FrameworkWideSubprocessIsolationGuard.test_cli_entrypoint_mains_configure_utf8_stdio` (wiring guard over all 14 entry points).
- [x] AC-2: no hardcoded `/tmp` fallback remains; `tempfile.gettempdir()` is used; the old-MANIFEST copy path resolves on a Windows-style temp dir (path test, no real `/tmp` dependency). — `upgrade_wavefoundry.OLD_MANIFEST_TMP = Path(tempfile.gettempdir()) / "wf-manifest-old.txt"`. Tests: `WindowsTempPathRobustnessTests`. POSIX-path audit: the only other `/dev/null` occurrences are unified-diff labels (`a/`/`b/` convention), correct on all OSes — not filesystem paths.
- [x] AC-3: every captured `subprocess.run(..., text=True)` specifies `encoding="utf-8", errors="replace"` (source-scan assertion). — folded into `subprocess_util.isolated_run`; the inline-isolated captures (`server_impl._mcp_subprocess_run`, `_pid_is_running` tasklist, `venv_bootstrap`) got `encoding=`/`errors=` directly (review F2/GUARD-3). **Source-scan broadened framework-wide** (review F2 — was upgrade_wavefoundry-only): `FrameworkWideSubprocessIsolationGuard.test_every_captured_text_spawn_decodes_utf8` (AST, all scripts). Plus `test_subprocess_util` encoding cases.
- [x] AC-4 (root-caused with landed fixes — AC text explicitly accepts "root-caused with a landed fix"): the garble had THREE now-fixed causes — (1) the CHILD index process owned a cp1252 stdout and crashed/mangled on `→`/em-dash (review F1, the dominant cause): every child spawn now gets `PYTHONUTF8=1`+`PYTHONIOENCODING=utf-8` via `subprocess_util.utf8_child_env` AND indexer reconfigures its own stdio — PROVEN by `test_subprocess_util.test_cp1252_child_crashes_then_utf8_child_env_fixes_it` (rc=1 baseline → rc=0 fixed, glyph written); (2) captured child output decoded with the host ANSI codec → now UTF-8/errors=replace; (3) the parent CLI stdout → now UTF-8-reconfigured. The remaining open item is only a live-console VISUAL confirmation on a real cp1252 Windows host (no code change identifiable from here). Original AC text: the garbled `\u0000`/`\n` output is reproduced and fixed (or root-caused with a landed fix); upgrade output renders as clean text.
- [x] AC-5: full framework suite + docs-lint pass. — `run_tests.py`: 3611 tests OK; `docs_lint.py`: ok.

## Tasks

- [x] Extract the shared UTF-8 stdio-reconfigure helper from `server.py`; wire it into all CLI entry points. — new `cli_stdio.py`.
- [x] `/tmp` → `tempfile.gettempdir()`; audit for other POSIX-path assumptions. — only other `/dev/null` are diff labels (correct).
- [x] Add `encoding="utf-8", errors="replace"` to captured spawns. — folded into `subprocess_util.isolated_run`.
- [x] Repro + fix (root cause = child cp1252 stdout; PYTHONUTF8 child env + child stdio reconfigure landed, rc==0 proven) the `\u0000`/`\n` garble.
- [x] Tests (cp1252-print non-crash, temp-path, encoding source-scan) + full suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| shared stdio reconfigure + entry wiring | implementer | — | reuse server.py:65 logic |
| /tmp → gettempdir + POSIX-path audit | implementer | — | independent of stdio work |
| capture encoding + garble repro/fix | implementer | shared stdio | coordinate with 1p8gu on the same spawns |
| tests | qa-reviewer | all | cp1252 sim, temp-path, source-scan |

## Serialization Points

- Shares `upgrade_wavefoundry.py` + `setup_index` `subprocess.run` calls with `1p8gu` (this change adds `encoding=`; `1p8gu` adds `stdin`+`creationflags` to the same calls). Land `1p8gu`'s shared helper first; fold the encoding kwarg into it or layer it here.

## Affected Architecture Docs

`docs/references/native-windows-support.md` (CLI encoding + temp-path robustness). Architecture hub / ADR `N/A` — robustness fixes, no boundary change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The `⚠` crash breaks the upgrade. |
| AC-2 | required | The `/tmp` crash breaks the upgrade. |
| AC-3 | required | Consistent capture decoding. |
| AC-4 | important | The garble is confusing but not upgrade-breaking; needs a repro. |
| AC-5 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from a real native-Windows 1.9.4 upgrade (FileNotFoundError on `/tmp`, UnicodeEncodeError on `⚠`, garbled output). | `upgrade_wavefoundry.py:58/:117/:2180`; only `server.py:65` reconfigures stdio. |
| 2026-06-27 | Implemented. New `cli_stdio.configure_utf8_stdio()` (mirrors server.py's guarded reconfigure, encoding-only) wired at all CLI entry points. `/tmp` fallback → `tempfile.gettempdir()`. UTF-8 capture decoding folded into `subprocess_util.isolated_run` (coordinated with 1p8gu). POSIX-path audit clean (remaining `/dev/null` are diff labels). | Tests `test_cli_stdio`, `WindowsTempPathRobustnessTests`, `UpgradeCliEncodingTests`. Full suite OK. |
| 2026-06-27 | Adversarial-review fixes (BLOCKER F1 + F2/F3/GUARD-3). ROOT CAUSE of the AC-4 garble found: the spawned index CHILD owned a cp1252 stdout (only the parent had been reconfigured) → `→` crash, silent index fail. Added `subprocess_util.utf8_child_env` (PYTHONUTF8=1 + PYTHONIOENCODING=utf-8, override-on); applied at the setup_index foreground+background launchers and the upgrade Phase-4 launchers; indexer/check_version/prune_framework mains now call `configure_utf8_stdio()` (F3). Added `encoding=`/`errors=` to the inline-isolated captures (server_impl `_mcp_subprocess_run` + tasklist, venv_bootstrap — F2/GUARD-3). Broadened the AC-3 encoding scan framework-wide (was upgrade-only). AC-4 → met (root-caused + landed; rc==0 child proof). | `test_subprocess_util.Utf8ChildEnvTests` (rc=1 cp1252 baseline → rc=0 fixed), `test_every_captured_text_spawn_decodes_utf8`, `test_cli_entrypoint_mains_configure_utf8_stdio`. Full suite 3611 OK. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | Shared UTF-8 stdio reconfigure at all CLI entry points. | One helper; matches the MCP-runner fix; fixes both the `⚠` crash and cp1252 `??`. | Per-print try/except (rejected: ~25 sites, fragile). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `\u0000` root cause is not the capture encoding. | Reproduce on a Windows console first; treat AC-4 as repro-gated. |
| stdio reconfigure unavailable on a stream (no `reconfigure`). | Mirror `server.py:65`'s guarded `getattr(stream, "reconfigure", None)` pattern. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
