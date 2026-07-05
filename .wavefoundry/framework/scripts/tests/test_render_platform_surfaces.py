from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parents[2]
SCRIPT_PATH = PROJECT_ROOT / "framework" / "scripts" / "render_platform_surfaces.py"


def _load_render_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("render_platform_surfaces_canonical", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RenderPlatformSurfacesScriptTests(unittest.TestCase):
    def test_renders_python_hook_entrypoints_and_configs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            (repo_root / ".wavefoundry" / "framework" / "scripts").mkdir(parents=True)
            (repo_root / ".claude").mkdir()
            (repo_root / ".claude" / "hooks").mkdir()
            (repo_root / ".cursor" / "rules").mkdir(parents=True)
            (repo_root / ".cursor" / "hooks").mkdir()
            (repo_root / ".github").mkdir()
            (repo_root / ".github" / "hooks").mkdir(parents=True)
            (repo_root / ".github" / "workflows").mkdir(parents=True)
            (repo_root / ".git" / "hooks").mkdir(parents=True)
            (repo_root / ".junie").mkdir()
            (repo_root / ".github" / "copilot-instructions.md").write_text("", encoding="utf-8")
            (repo_root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
            (repo_root / ".git" / "hooks" / "pre-push").write_text("#!/bin/sh\n", encoding="utf-8")
            (repo_root / ".junie" / "guidelines.md").write_text("", encoding="utf-8")
            (repo_root / ".claude" / "hooks" / "pre-edit.sh").write_text("# legacy\n", encoding="utf-8")
            (repo_root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("# legacy\n", encoding="utf-8")
            (repo_root / ".cursor" / "hooks" / "reformat.py").write_text("# legacy\n", encoding="utf-8")
            (repo_root / ".github" / "hooks" / "pre-tool-use.sh").write_text("# legacy\n", encoding="utf-8")

            # Wave 1p7pm: render `main` calls venv_bootstrap.ensure_python_resolves(), which is
            # SIDE-EFFECTING (creates ~/.local/bin/python3 + may append to the shell rc). This is a
            # real subprocess, so in-process patching can't reach it — set the documented opt-out env
            # var so the heal is a complete no-op and the test never mutates the operator's box.
            sub_env = {**os.environ, "WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}
            result = subprocess.run(
                ["python3", str(SCRIPT_PATH), "--repo-root", str(repo_root)],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=sub_env,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            # Wave 1p88t: hook commands follow the MCP command token (`python3`) and stay repo-relative.
            # Native-Windows Claude Code did not expand `$CLAUDE_PROJECT_DIR`, so the committed surface
            # must not depend on host-specific project-root env-var syntax.
            expected_claude_command = 'python3 ".claude/hooks/pre-edit.py"'
            expected_cursor_command = 'python3 ".cursor/hooks/after-file-edit.py"'
            expected_copilot_command = 'python3 ".github/hooks/pre-tool-use.py"'

            claude_settings = json.loads((repo_root / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(
                claude_settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"],
                expected_claude_command,
            )

            # Wave 1p5ti: session-end capture hook is rendered for Stop + SubagentStop.
            expected_stop_command = 'python3 ".claude/hooks/session-capture.py"'
            self.assertEqual(
                claude_settings["hooks"]["Stop"][0]["hooks"][0]["command"],
                expected_stop_command,
            )
            # Stop only — SubagentStop would fire on every subagent completion (noise).
            self.assertNotIn("SubagentStop", claude_settings["hooks"])

            cursor_hooks = json.loads((repo_root / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(
                cursor_hooks["hooks"]["afterFileEdit"][0]["command"],
                expected_cursor_command,
            )

            copilot_hooks = json.loads((repo_root / ".github" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(
                copilot_hooks["hooks"]["preToolUse"][0]["bash"],
                expected_copilot_command,
            )
            # Wave 1p7pm (1p7pb-adr): Junie MCP names the byte-identical `python` command on the
            # repo-relative server.py — never the bash .wavefoundry/bin/mcp-server wrapper.
            junie_mcp = json.loads((repo_root / ".junie" / "mcp" / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                junie_mcp["mcpServers"]["wavefoundry"]["command"],
                "python3",
            )
            self.assertEqual(
                junie_mcp["mcpServers"]["wavefoundry"]["args"],
                [".wavefoundry/framework/scripts/server.py"],
            )

            # Wave 1p7pm: only the `.py` body is rendered — the `.sh`/`.cmd` trampolines are retired.
            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit.py").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "pre-edit").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "pre-edit.cmd").exists())
            self.assertTrue((repo_root / ".claude" / "hooks" / "session-capture.py").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "session-capture").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "session-capture.cmd").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn.py").exists())
            self.assertFalse((repo_root / ".cursor" / "hooks" / "framework-plan-warn").exists())
            self.assertFalse((repo_root / ".wavefoundry" / "bin" / "register-codex-mcp").exists())
            self.assertFalse((repo_root / ".cursor" / "hooks" / "framework-plan-warn.cmd").exists())
            self.assertTrue((repo_root / ".github" / "hooks" / "post-tool-use.py").exists())
            self.assertFalse((repo_root / ".github" / "hooks" / "post-tool-use").exists())
            self.assertFalse((repo_root / ".github" / "hooks" / "post-tool-use.cmd").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "pre-edit.sh").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "pycache-cleanup.py").exists())
            self.assertFalse((repo_root / ".cursor" / "hooks" / "reformat.py").exists())
            self.assertFalse((repo_root / ".github" / "hooks" / "pre-tool-use.sh").exists())
            self.assertTrue((repo_root / ".github" / "workflows" / "ci.yml").exists())
            self.assertTrue((repo_root / ".git" / "hooks" / "pre-push").exists())
            self.assertIn(
                "def read_payload_text()",
                (repo_root / ".claude" / "hooks" / "pre-edit.py").read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".wavefoundry/guard-overrides.json",
                (repo_root / ".claude" / "hooks" / "pre-edit.py").read_text(encoding="utf-8"),
            )
            post_edit = (repo_root / ".claude" / "hooks" / "post-edit.py").read_text(encoding="utf-8")
            # 1p4ww: the reindex hook is a single bare project spawn (framework seeds/README
            # fold into the project docs index) — no separate framework-index reindex.
            self.assertIn("maybe_trigger_reindex", post_edit)
            self.assertNotIn("--index-dir", post_edit)
            self.assertNotIn("should_reindex_framework", post_edit)
            # Wave 1p7pm/1p802 (1p7pb-adr): the body ACTIVATES the tool venv in-process first-line via
            # the single `venv_bootstrap` resolver — no rendered `_venv_python_path` resolver remains, no
            # re-exec. Wave 1p8pe: inner spawns now resolve the interpreter via hook_python() (the
            # console-free pythonw.exe on Windows, else sys.executable; the re-spawned script
            # self-activates the venv).
            self.assertIn("activate_tool_venv()", post_edit)
            self.assertNotIn("reexec_into_tool_venv", post_edit)
            self.assertIn("import venv_bootstrap", post_edit)
            self.assertNotIn("_venv_python_path", post_edit)
            self.assertIn("python_exec = hook_python()", post_edit)
            self.assertIn("return sys.executable", post_edit)  # hook_python()'s POSIX/unavailable fallback
            # Wave 1p35d (1p35n, AC-9): the rendered hook helper source must no longer
            # contain the dead `maybe_cleanup_pycache` helper or its `shutil` dependency.
            # The previous third hook was never actually wired in any host's settings,
            # but the helper code shipped in every rendered hook regardless. Verify it's
            # gone across every rendered hook file, not just one.
            rendered_hooks = [
                repo_root / ".claude" / "hooks" / "pre-edit.py",
                repo_root / ".claude" / "hooks" / "post-edit.py",
                repo_root / ".claude" / "hooks" / "simulate-hooks.py",
                # Wave 1p7pm: session-capture is rendered via compose_script too — it MUST bootstrap.
                repo_root / ".claude" / "hooks" / "session-capture.py",
                repo_root / ".cursor" / "hooks" / "after-file-edit.py",
                repo_root / ".cursor" / "hooks" / "docs-lint.py",
                repo_root / ".cursor" / "hooks" / "framework-plan-warn.py",
                repo_root / ".cursor" / "hooks" / "seed-warn.py",
                repo_root / ".github" / "hooks" / "pre-tool-use.py",
                repo_root / ".github" / "hooks" / "post-tool-use.py",
            ]
            for path in rendered_hooks:
                if not path.exists():
                    continue
                body = path.read_text(encoding="utf-8")
                self.assertNotIn("maybe_cleanup_pycache", body, f"{path.name} still ships the retired pycache helper")
                self.assertNotIn("import shutil", body, f"{path.name} still imports shutil (only the pycache helper used it)")
                # Wave 1p7pm/1p802 (1p7pb-adr): EVERY rendered hook body must self-activate the tool
                # venv in-process first-line — no exceptions, and no leftover re-exec.
                self.assertIn(
                    "activate_tool_venv()", body,
                    f"{path.name} is missing the first-line venv activation",
                )
                self.assertNotIn("reexec_into_tool_venv", body, f"{path.name} still calls the removed re-exec")
                self.assertIn("import venv_bootstrap", body, f"{path.name} is missing the venv_bootstrap import")
            self.assertIn("[python_exec, str(indexer), \"--root\", str(REPO_ROOT)]", post_edit)
            cursor_after = (repo_root / ".cursor" / "hooks" / "after-file-edit.py").read_text(encoding="utf-8")
            self.assertNotIn("_venv_python_path", cursor_after)
            # Wave 1p8pe: cursor gate spawns resolve the interpreter via hook_python() (windowless pythonw
            # on Windows, else sys.executable).
            self.assertIn("python_exec = hook_python()", cursor_after)
            self.assertIn("[python_exec, str(gate)]", cursor_after)
            claude_sim = (repo_root / ".claude" / "hooks" / "simulate-hooks.py").read_text(encoding="utf-8")
            self.assertNotIn("_venv_python_path", claude_sim)
            # Wave 1p8pe: simulate-hooks has no shared helpers (include_helpers=False) — it keeps the
            # sys.executable default and resolves a windowless interpreter inline.
            self.assertIn("python_exec = sys.executable", claude_sim)
            self.assertIn("windowless_pythonw()", claude_sim)
            self.assertIn("[python_exec, str(target)]", claude_sim)
            upgrade_skill = (repo_root / ".claude" / "skills" / "upgrade-wave.md").read_text(encoding="utf-8")
            self.assertIn(".wavefoundry/guard-overrides.json", upgrade_skill)
            # Wave 1p88t: the skill's docs-gardener/docs-lint steps must give BOTH the POSIX `wf` and
            # the native-Windows `wf.cmd` forms (the bash `wf` shim does not run in cmd/PowerShell).
            self.assertIn("./.wavefoundry/bin/wf docs-lint", upgrade_skill)
            self.assertIn(".\\.wavefoundry\\bin\\wf.cmd docs-lint", upgrade_skill)
            self.assertIn("./.wavefoundry/bin/wf docs-gardener", upgrade_skill)
            self.assertIn(".\\.wavefoundry\\bin\\wf.cmd docs-gardener", upgrade_skill)
            aiignore_text = (repo_root / ".aiignore").read_text(encoding="utf-8")
            self.assertIn(".wavefoundry/index/", aiignore_text)
            self.assertIn(".wavefoundry/framework/index/", aiignore_text)
            self.assertIn(".wavefoundry/*.lock", aiignore_text)
            self.assertIn(".wavefoundry/framework/*.lock", aiignore_text)
            self.assertNotIn(".wavefoundry/framework/seeds/*.prompt.md", aiignore_text)

            # Wave 1p7tz: the nine bash wrappers are retired — render_bin_launchers writes ONLY the
            # cross-OS `wf` (bash) + `wf.cmd` (Windows) shim pair dispatching to wf_cli.py.
            bin_dir = repo_root / ".wavefoundry" / "bin"
            wf = bin_dir / "wf"
            wf_cmd = bin_dir / "wf.cmd"
            self.assertTrue(wf.exists(), ".wavefoundry/bin/wf should be created")
            self.assertTrue(wf_cmd.exists(), ".wavefoundry/bin/wf.cmd should be created")
            # The nine retired wrappers must NOT be present.
            for retired in ("docs-lint", "docs-gardener", "wave-gate", "update-indexes",
                            "lifecycle-id", "wave-dashboard", "upgrade-wavefoundry",
                            "setup-wavefoundry", "mcp-server"):
                self.assertFalse((bin_dir / retired).exists(),
                                 f".wavefoundry/bin/{retired} must be retired (wave 1p7tz)")
            self.assertFalse((bin_dir / "wave_dashboard").exists(), "stale wave_dashboard should be removed")
            self.assertFalse((bin_dir / "register-codex-mcp").exists(), "register-codex-mcp should be removed")
            if os.name != "nt":
                self.assertTrue(os.access(wf, os.X_OK), "wf should be executable")
            wf_src = wf.read_text(encoding="utf-8")
            self.assertIn(".wavefoundry/framework/scripts/wf_cli.py", wf_src)


class RenderBinLaunchersTests(unittest.TestCase):
    """Wave 1p7tz: render_bin_launchers now emits ONLY the cross-OS `wf` (bash) + `wf.cmd` (Windows)
    shim pair dispatching to `wf_cli.py`; the nine individual bash wrappers are retired (hard cutover)."""

    RETIRED_WRAPPERS = (
        "docs-lint", "docs-gardener", "wave-gate", "update-indexes", "lifecycle-id",
        "wave-dashboard", "upgrade-wavefoundry", "setup-wavefoundry", "mcp-server",
    )

    def _load_rps(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("rps", SCRIPT_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_renders_wf_shim_pair(self):
        # AC-2: `wf` (bash) + `wf.cmd` (Windows) are emitted and dispatch to wf_cli.py.
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_bin_launchers(root)
            wf = root / ".wavefoundry" / "bin" / "wf"
            wf_cmd = root / ".wavefoundry" / "bin" / "wf.cmd"
            self.assertTrue(wf.exists())
            self.assertTrue(wf_cmd.exists())
            wf_src = wf.read_text(encoding="utf-8")
            wf_cmd_src = wf_cmd.read_text(encoding="utf-8")
            wf_bytes = wf.read_bytes()
            wf_cmd_bytes = wf_cmd.read_bytes()
        # AC-3: the bash shim uses the standardized `python3` command.
        self.assertIn("#!/usr/bin/env bash", wf_src)
        self.assertIn(".wavefoundry/framework/scripts/wf_cli.py", wf_src)
        self.assertIn('exec python3 "$REPO_ROOT/.wavefoundry/framework/scripts/wf_cli.py" "$@"', wf_src)
        self.assertNotIn('PYTHON="python"', wf_src)
        self.assertNotIn("WAVEFOUNDRY_VENV", wf_src)
        # The cmd shim follows the standard command token.
        self.assertIn("@echo off", wf_cmd_src)
        self.assertIn("wf_cli.py", wf_cmd_src)
        self.assertIn("python3 ", wf_cmd_src)
        self.assertNotIn("python ", wf_cmd_src)
        # Wave 1p7tz (newline fix): the line terminators are written VERBATIM regardless of the
        # rendering host's os.linesep. `wf.cmd` is CRLF (cmd.exe) with NO doubled CR; the `wf` bash
        # shim is pure LF (no CR — a CRLF shebang breaks git-bash/WSL2).
        self.assertIn(b"\r\n", wf_cmd_bytes)
        self.assertNotIn(b"\r\r", wf_cmd_bytes)  # no doubled CR (the newline=None translation bug)
        self.assertNotIn(b"\r", wf_bytes)  # bash shim has zero CR
        # The cmd comment must be ASCII-safe on legacy Windows codepages (no em-dash).
        self.assertNotIn("—".encode("utf-8"), wf_cmd_bytes)

    def test_retired_wrappers_not_rendered(self):
        # AC-2: none of the nine individual bash wrappers is written; a re-render removes any present.
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / ".wavefoundry" / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            # Simulate a pre-cutover install: the old wrappers exist on disk.
            for name in self.RETIRED_WRAPPERS:
                (bin_dir / name).write_text("#!/usr/bin/env bash\nlegacy\n", encoding="utf-8")
            rps.render_bin_launchers(root)
            for name in self.RETIRED_WRAPPERS:
                self.assertFalse((bin_dir / name).exists(),
                                 f"retired wrapper {name} must be removed on re-render")
            # Only the wf shim pair remains (plus any unrelated files the test didn't create).
            self.assertTrue((bin_dir / "wf").exists())
            self.assertTrue((bin_dir / "wf.cmd").exists())

    def test_wf_executable(self):
        if os.name == "nt":
            self.skipTest("executable bit not applicable on Windows")
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_bin_launchers(root)
            self.assertTrue(os.access(root / ".wavefoundry" / "bin" / "wf", os.X_OK))

    def test_render_bin_launchers_is_idempotent(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_bin_launchers(root)
            first_wf = (root / ".wavefoundry" / "bin" / "wf").read_text(encoding="utf-8")
            rps.render_bin_launchers(root)
            second_wf = (root / ".wavefoundry" / "bin" / "wf").read_text(encoding="utf-8")
        self.assertEqual(first_wf, second_wf)

    def test_render_bin_launchers_removes_stale_windows_upgrade_wrapper(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = root / ".wavefoundry" / "bin" / "upgrade-wavefoundry.bat"
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_text("stale\n", encoding="utf-8")
            rps.render_bin_launchers(root)
            self.assertFalse(stale.exists())


class WriteTextNewlineFidelityTests(unittest.TestCase):
    """Wave 1p7tz (MAJOR review fix): `write_text` must write embedded line terminators VERBATIM,
    regardless of the rendering host's os.linesep. The default `Path.write_text` (newline=None)
    translates every `\\n` → os.linesep on write, which on native Windows doubles the CR in the
    CRLF-embedded `wf.cmd` (`\\r\\r\\n`) and gives CRLF shebangs to the LF bash/`.py` surfaces — both
    corrupt the re-render. `write_text` opens with newline="" to disable translation."""

    def _load_rps(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("rps", SCRIPT_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_crlf_string_written_verbatim(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cmd.txt"
            rps.write_text(path, "a\r\nb\r\n")
            self.assertEqual(path.read_bytes(), b"a\r\nb\r\n")  # no doubling, no translation

    def test_lf_string_written_verbatim(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bash.sh"
            rps.write_text(path, "a\nb\n")
            self.assertEqual(path.read_bytes(), b"a\nb\n")  # stays LF even if os.linesep is \r\n

    def test_write_text_survives_patched_linesep(self):
        # Even if os.linesep were "\r\n" (Windows), newline="" must keep the bytes exact.
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp, patch.object(rps.os, "linesep", "\r\n"):
            lf = Path(tmp) / "lf"
            crlf = Path(tmp) / "crlf"
            rps.write_text(lf, "x\ny\n")
            rps.write_text(crlf, "x\r\ny\r\n")
            self.assertEqual(lf.read_bytes(), b"x\ny\n")
            self.assertEqual(crlf.read_bytes(), b"x\r\ny\r\n")


class MergeMcpServerTests(unittest.TestCase):
    """Unit tests for _merge_mcp_server, render_cursor_mcp_json, render_mcp_json, render_junie_mcp_json."""

    def _load_rps(self):
        import importlib.util, sys
        spec = importlib.util.spec_from_file_location("rps", SCRIPT_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_render_cursor_mcp_json_creates_stanza(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_cursor_mcp_json(root)
            data = json.loads((root / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
        wf = data["mcpServers"]["wavefoundry"]
        self.assertEqual(wf["type"], "stdio")
        # Wave 1p7pm (1p7pb-adr): byte-identical `python` on the repo-relative server.py.
        self.assertEqual(wf["command"], "python3")
        self.assertEqual(wf["args"], [".wavefoundry/framework/scripts/server.py"])
        self.assertEqual(wf["cwd"], "${workspaceFolder}")

    def test_render_cursor_mcp_json_preserves_existing_servers(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_dir = root / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "mcp.json").write_text(
                json.dumps({"mcpServers": {"other-tool": {"command": "node", "args": ["other.js"]}}}),
                encoding="utf-8",
            )
            rps.render_cursor_mcp_json(root)
            data = json.loads((cursor_dir / "mcp.json").read_text(encoding="utf-8"))
        # Pre-existing entry preserved
        self.assertIn("other-tool", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["other-tool"]["command"], "node")
        # Wavefoundry entry written (wave 1p7pm: byte-identical `python` command)
        self.assertEqual(data["mcpServers"]["wavefoundry"]["command"], "python3")

    def test_render_mcp_json_uses_python_command(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_mcp_json(root)
            data = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
        wf = data["mcpServers"]["wavefoundry"]
        self.assertEqual(wf["command"], "python3")
        self.assertEqual(wf["args"], [".wavefoundry/framework/scripts/server.py"])

    def test_render_mcp_json_preserves_existing_servers(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".mcp.json").write_text(
                json.dumps({"mcpServers": {"my-other-server": {"command": "npx", "args": ["-y", "my-pkg"]}}}),
                encoding="utf-8",
            )
            rps.render_mcp_json(root)
            data = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
        self.assertIn("my-other-server", data["mcpServers"])
        self.assertIn("wavefoundry", data["mcpServers"])

    def test_render_junie_mcp_json_uses_python_command(self):
        # Wave 1p7pm (1p7pb-adr): Junie MCP names the byte-identical `python` command on the
        # repo-relative server.py — never the bash .wavefoundry/bin/mcp-server wrapper.
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_junie_mcp_json(root)
            data = json.loads((root / ".junie" / "mcp" / "mcp.json").read_text(encoding="utf-8"))
        wf = data["mcpServers"]["wavefoundry"]
        self.assertEqual(wf["command"], "python3")
        self.assertEqual(wf["args"], [".wavefoundry/framework/scripts/server.py"])

    def test_merge_mcp_server_is_idempotent(self):
        rps = self._load_rps()
        stanza = {"command": "python3", "args": ["server.py", "--root", "."]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".mcp.json"
            rps._merge_mcp_server(target, stanza)
            first = target.read_text(encoding="utf-8")
            rps._merge_mcp_server(target, stanza)
            second = target.read_text(encoding="utf-8")
        self.assertEqual(first, second)

    def test_render_antigravity_mcp_json_uses_python_command(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_antigravity_mcp_json(root)
            data = json.loads((root / ".agents" / "mcp_config.json").read_text(encoding="utf-8"))
        wf = data["mcpServers"]["wavefoundry"]
        self.assertEqual(wf["command"], "python3")
        self.assertEqual(wf["args"], [".wavefoundry/framework/scripts/server.py"])


class SessionCaptureHookTests(unittest.TestCase):
    """Wave 1p5ti: the generated session-end capture script is fast, fail-safe,
    always exits 0, captures open-wave/AC state, and never writes memory/commits."""

    def setUp(self) -> None:
        self.mod = _load_render_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.script = Path(self._tmp.name) / "session-capture.py"
        self.script.write_text(self.mod.claude_stop_source(), encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, cwd: Path):
        return subprocess.run(
            ["python3", str(self.script)],
            cwd=str(cwd), text=True, capture_output=True, input="{}", timeout=15,
        )

    def test_captures_active_wave_and_ac_progress(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            wave_dir = root / "docs" / "waves" / "1abc demo"
            wave_dir.mkdir(parents=True)
            (wave_dir / "wave.md").write_text(
                "# Wave Record\nStatus: active\nwave-id: `1abc demo`\n", encoding="utf-8"
            )
            (wave_dir / "1abc-enh thing.md").write_text(
                "- [x] AC-1: done\n- [ ] AC-2: todo\n", encoding="utf-8"
            )
            res = self._run(root)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            capture = root / ".wavefoundry" / "logs" / "last-session-capture.md"
            self.assertTrue(capture.exists())
            text = capture.read_text(encoding="utf-8")
            self.assertIn("1abc demo", text)
            self.assertIn("1/2", text)
            self.assertIn("memory candidate", text)

    def test_no_active_wave_is_clean_exit(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / "docs" / "waves").mkdir(parents=True)
            res = self._run(root)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("No active wave", (root / ".wavefoundry" / "logs" / "last-session-capture.md").read_text())

    def test_not_a_repo_is_fail_safe(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            # No docs/waves and no .wavefoundry: must still exit 0, never raise.
            res = self._run(Path(d).resolve())
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_never_writes_memory_or_commits(self) -> None:
        # The capture source must not write memory files or invoke git commit.
        src = self.mod.claude_stop_source()
        self.assertNotIn("git commit", src)
        self.assertNotIn("/memory/", src)


class ClaudeHookSimulateParityTests(unittest.TestCase):
    """Wave 1p607: the simulate-hooks HOOKS map and the hooks rendered into
    .claude/settings.json must derive from one shared source so they cannot drift.
    Every Claude hook rendered into settings must be dry-runnable via simulate-hooks.
    """

    def setUp(self) -> None:
        self.mod = _load_render_module()

    @staticmethod
    def _settings_hook_names(settings: dict) -> set[str]:
        """Script basenames referenced by every hook entry in .claude/settings.json.

        Wave 1p88t: the command is `python3 ".claude/hooks/session-capture.py"` ->
        "session-capture".
        """
        names: set[str] = set()
        for entries in settings.get("hooks", {}).values():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    command = hook["command"]
                    token = command.split()[-1].strip('"')  # drop the leading `python` + quotes
                    base = token.replace("\\", "/").rsplit("/", 1)[-1]
                    if base.endswith(".py"):
                        base = base[: -len(".py")]
                    names.add(base)
        return names

    def test_every_rendered_settings_hook_is_in_simulate_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self.mod.render_claude_settings(root)
            settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))

        rendered = self._settings_hook_names(settings)
        self.assertTrue(rendered, "expected at least one rendered Claude hook")

        simulate_src = self.mod.claude_simulate_hooks_source()
        for name in sorted(rendered):
            # The simulate HOOKS map keys each rendered hook by its script basename.
            self.assertIn(
                f'"{name}": REPO_ROOT / ".claude" / "hooks" / "{name}.py"',
                simulate_src,
                f"hook {name!r} is rendered into .claude/settings.json but is missing "
                f"from the simulate-hooks HOOKS map (drift)",
            )

    def test_session_capture_is_simulatable(self) -> None:
        simulate_src = self.mod.claude_simulate_hooks_source()
        self.assertIn(
            '"session-capture": REPO_ROOT / ".claude" / "hooks" / "session-capture.py"',
            simulate_src,
            "the Stop session-capture hook must be present in the simulate HOOKS map",
        )


if __name__ == "__main__":
    unittest.main()


class LauncherCommandTests(unittest.TestCase):
    """Wave 1p88t: `launcher_command` names `python3` on a repo-relative `.py` hook body.

    The command is byte-identical across render hosts and intentionally ignores project-root env vars.
    """

    def setUp(self):
        self.mod = _load_render_module()

    def test_launcher_command_nt_invokes_python_on_py_body(self):
        mod = self.mod
        with patch.object(mod.os, "name", "nt"):
            anchored = mod.launcher_command(".claude/hooks/session-capture", "CLAUDE_PROJECT_DIR")
            self.assertNotIn("\\", anchored)
            self.assertNotIn("cmd.exe", anchored)
            self.assertEqual(
                anchored,
                'python3 ".claude/hooks/session-capture.py"',
            )
            bare = mod.launcher_command(".cursor/hooks/after-file-edit")
            self.assertNotIn("\\", bare)
            self.assertEqual(bare, 'python3 ".cursor/hooks/after-file-edit.py"')

    def test_launcher_command_posix_invokes_python_on_py_body(self):
        mod = self.mod
        with patch.object(mod.os, "name", "posix"):
            self.assertEqual(
                mod.launcher_command(".claude/hooks/session-capture", "CLAUDE_PROJECT_DIR"),
                'python3 ".claude/hooks/session-capture.py"',
            )
            self.assertEqual(
                mod.launcher_command(".cursor/hooks/after-file-edit"),
                'python3 ".cursor/hooks/after-file-edit.py"',
            )

    def test_launcher_command_interpreter_and_path_byte_identical_across_os(self):
        """The interpreter and the `.py` path are byte-identical across render hosts."""
        mod = self.mod
        with patch.object(mod.os, "name", "posix"):
            posix = mod.launcher_command(".claude/hooks/pre-edit", "CLAUDE_PROJECT_DIR")
        with patch.object(mod.os, "name", "nt"):
            nt = mod.launcher_command(".claude/hooks/pre-edit", "CLAUDE_PROJECT_DIR")
        self.assertEqual(posix, 'python3 ".claude/hooks/pre-edit.py"')
        self.assertEqual(nt, posix)


class GpuDoctorLauncherTests(unittest.TestCase):
    """1p6et: there is NO dedicated GPU-doctor bin launcher — the diagnostic is reached via
    `wf setup --check-gpu` (wave 1p7tz; was `setup-wavefoundry --check-gpu`) and the `wave_gpu_doctor`
    MCP tool (regression guard against re-adding a launcher)."""

    def setUp(self):
        self.mod = _load_render_module()

    def test_no_dedicated_gpu_doctor_launcher_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.mod.render_bin_launchers(repo_root)
            bin_dir = repo_root / ".wavefoundry" / "bin"
            self.assertFalse((bin_dir / "wave-gpu-doctor").exists())
            self.assertFalse((bin_dir / "wave-doctor").exists())
            # The cross-OS `wf` dispatcher (which routes `wf setup --check-gpu`) is rendered.
            self.assertTrue((bin_dir / "wf").exists())


class NoPathedLauncherScanTests(unittest.TestCase):
    """Wave 1p7pm (1p7pb-adr) AC-3/AC-2: standing guard that NO committed MCP config names a pathed
    launcher (the bash `.wavefoundry/bin/mcp-server`) — they all name the byte-identical `python`
    command on the repo-relative server.py. The scan enumerates the ACTUAL on-disk config set,
    INCLUDING the separate-file configs that live outside `render_platform_surfaces.py`:
    `.codex/config.toml` (from `render_agent_surfaces.py`) and `.air/mcp.json` (hand-committed)."""

    EXPECTED_COMMAND = "python3"
    EXPECTED_ARGS = [".wavefoundry/framework/scripts/server.py"]

    def _render_all_json_mcp(self, repo_root: Path) -> None:
        mod = _load_render_module()
        mod.render_mcp_json(repo_root)
        mod.render_cursor_mcp_json(repo_root)
        mod.render_junie_mcp_json(repo_root)
        mod.render_antigravity_mcp_json(repo_root)

    def test_rendered_json_mcp_configs_name_python_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp).resolve()
            self._render_all_json_mcp(repo_root)
            on_disk = [
                repo_root / ".mcp.json",
                repo_root / ".cursor" / "mcp.json",
                repo_root / ".junie" / "mcp" / "mcp.json",
                repo_root / ".agents" / "mcp_config.json",
            ]
            for path in on_disk:
                self.assertTrue(path.exists(), f"{path} not rendered")
                wf = json.loads(path.read_text(encoding="utf-8"))["mcpServers"]["wavefoundry"]
                self.assertEqual(wf["command"], self.EXPECTED_COMMAND, f"{path.name}: wrong command")
                self.assertEqual(wf["args"], self.EXPECTED_ARGS, f"{path.name}: wrong args")
                raw = path.read_text(encoding="utf-8")
                self.assertNotIn("bin/mcp-server", raw, f"{path.name} references a pathed launcher")

    def test_committed_on_disk_configs_have_no_pathed_launcher(self):
        """Scan the REAL committed config set in this repo with STRICT structural equality (not a weak
        substring) — incl. `.codex/config.toml` + `.air/mcp.json`, the separate-file configs an in-temp
        render of `render_platform_surfaces` would miss. Every config's wavefoundry server stanza must
        have `command == 'python'` exactly and `args == ['.wavefoundry/framework/scripts/server.py']`."""
        import tomllib

        repo = PROJECT_ROOT.parent  # PROJECT_ROOT is `.wavefoundry`; its parent is the repo root
        json_configs = [
            repo / ".mcp.json",
            repo / ".cursor" / "mcp.json",
            repo / ".junie" / "mcp" / "mcp.json",
            repo / ".agents" / "mcp_config.json",
            repo / ".air" / "mcp.json",
        ]
        present_json = [c for c in json_configs if c.exists()]
        self.assertTrue(present_json, "expected at least one committed JSON MCP config to scan")
        for path in present_json:
            data = json.loads(path.read_text(encoding="utf-8"))
            wf = data["mcpServers"]["wavefoundry"]
            self.assertEqual(wf["command"], "python3", f"{path}: command must be exactly 'python3'")
            self.assertEqual(
                wf["args"], self.EXPECTED_ARGS,
                f"{path}: args must be exactly {self.EXPECTED_ARGS}",
            )

        codex = repo / ".codex" / "config.toml"
        if codex.exists():
            cfg = tomllib.loads(codex.read_text(encoding="utf-8"))
            wf = cfg["mcp_servers"]["wavefoundry"]
            self.assertEqual(wf["command"], "python3", ".codex/config.toml: command must be exactly 'python3'")
            self.assertEqual(
                wf["args"], self.EXPECTED_ARGS,
                f".codex/config.toml: args must be exactly {self.EXPECTED_ARGS}",
            )


class HookReindexDetachTests(unittest.TestCase):
    """Wave 1p7pn / 1p88t: the post-edit reindex spawn (`hook_helpers.maybe_trigger_reindex`) must
    detach per-OS — on Windows start_new_session is a no-op, so without creationflags the child stays
    in the host's process group and dies with the hook. (Git hooks were DROPPED in wave 1p88t — the
    in-session staleness monitor covers VCS-driven index refresh — so only the post-edit reindex
    spawn remains.)"""

    def setUp(self):
        self.mod = _load_render_module()

    def test_docs_lint_hook_is_bounded_and_advisory_on_timeout(self):
        # Wave 1p9bg: maybe_docs_lint must bound the docs-lint subprocess with a configurable timeout
        # and treat a TimeoutExpired as ADVISORY (not blocking) so it can never hang the post-edit hook.
        src = self.mod.hook_helpers()
        self.assertIn("docs_lint_hook_timeout_seconds", src, "docs-lint hook must read the configurable timeout")
        self.assertIn("timeout=timeout_s", src, "docs-lint spawn must pass the timeout through run_command")
        self.assertIn("subprocess.TimeoutExpired", src, "docs-lint hook must catch a timeout")
        # run_command must accept + forward a timeout to both the isolated and fallback spawn paths.
        self.assertIn("def run_command(argv: list[str], timeout=None)", src)
        self.assertIn("timeout=timeout", src)

    def test_post_edit_reindex_spawn_has_per_os_detach_branch(self):
        src = self.mod.hook_helpers()
        self.assertIn('os.name == "nt"', src, "hook_helpers: missing the per-OS detach branch")
        self.assertIn("subprocess.DETACHED_PROCESS", src, "hook_helpers: missing DETACHED_PROCESS")
        self.assertIn("subprocess.CREATE_NEW_PROCESS_GROUP", src, "hook_helpers: missing CREATE_NEW_PROCESS_GROUP")
        self.assertIn("CREATE_NO_WINDOW", src, "hook_helpers: missing Windows no-window flag")
        self.assertIn("start_new_session", src, "hook_helpers: missing POSIX start_new_session else-branch")
        self.assertIn('close_fds=os.name != "nt"', src, "hook_helpers: missing per-OS close_fds")

    def test_every_rendered_hook_body_spawn_is_isolated(self):
        # GUARD-4: re-parse EVERY rendered hook body that spawns a child and run the PRODUCTION
        # stdin/no-window AST scan over it — not just the one post-edit body. A new hook body added with
        # a bare spawn (the templates do not get subprocess_util on a transient/old tree, so each
        # carries a guarded inline fallback) must be caught.
        import ast as _ast
        import importlib.util as _ilu

        # Load the framework-wide guard's static scan methods to reuse the production logic.
        spec = _ilu.spec_from_file_location(
            "wavefoundry_test_server_tools", Path(__file__).resolve().parent / "test_server_tools.py"
        )
        tst = _ilu.module_from_spec(spec)
        spec.loader.exec_module(tst)
        Guard = tst.FrameworkWideSubprocessIsolationGuard

        # Every rendered body source function that may contain a child spawn.
        body_funcs = [
            "claude_pre_edit_source", "claude_post_edit_source", "claude_simulate_hooks_source",
            "cursor_after_file_edit_source", "claude_stop_source",
            "cursor_seed_warn_source", "cursor_framework_warn_source", "cursor_docs_lint_source",
            "windsurf_seed_protect_source", "windsurf_docs_lint_source",
        ]
        offenders: list[str] = []
        bodies_with_spawns = 0
        for fname in body_funcs:
            fn = getattr(self.mod, fname, None)
            if fn is None:
                continue
            body = fn()
            tree = _ast.parse(body)
            lines = body.splitlines()
            for node in Guard._spawn_calls(tree):
                if Guard._is_isolated_helper_call(node):
                    continue  # routed through _wf_subprocess_util.isolated_*
                bodies_with_spawns += 1
                if not Guard._call_has_devnull_or_input(node):
                    offenders.append(f"{fname}:{node.lineno}: missing stdin isolation: {lines[node.lineno-1].strip()}")
                if not Guard._call_has_no_window(node):
                    offenders.append(f"{fname}:{node.lineno}: missing no-window: {lines[node.lineno-1].strip()}")
        # Non-vacuous: several rendered bodies DO spawn (run_command, gate runners, reindex Popen).
        self.assertGreaterEqual(
            bodies_with_spawns, 2,
            "rendered-hook-body spawn scan found too few spawns — the body set or AST walk likely broke",
        )
        self.assertEqual(
            offenders, [],
            "rendered hook bodies must isolate every child spawn (stdin DEVNULL/input + no-window):\n"
            + "\n".join(offenders),
        )

    def test_hook_helpers_defines_windowless_hook_python(self):
        # Wave 1p8pe AC-4: hook_helpers() exposes hook_python() — the console-free interpreter resolver
        # that prefers the tool-venv pythonw.exe on Windows (via the guarded _wf_subprocess_util) and
        # falls back to sys.executable on POSIX / when subprocess_util is unavailable.
        src = self.mod.hook_helpers()
        self.assertIn("def hook_python()", src, "hook_helpers must define the windowless hook_python()")
        self.assertIn("windowless_pythonw()", src, "hook_python must call windowless_pythonw()")
        self.assertIn("return sys.executable", src, "hook_python must fall back to sys.executable")

    def test_converted_hook_bodies_launch_via_windowless_pythonw(self):
        # Wave 1p8pe AC-4: the four converted rendered hook bodies launch python via the windowless path
        # (hook_python() for the helper-bearing bodies; an inline guarded windowless resolution for
        # claude_simulate_hooks_source which carries no helpers) with a sys.executable fallback, while
        # preserving their existing input=/stdin/capture wiring.
        # docs-lint (run_command) + post-edit reindex Popen + cursor gate runners → hook_python().
        for fname in ("claude_post_edit_source", "cursor_after_file_edit_source"):
            body = getattr(self.mod, fname)()
            self.assertIn("hook_python()", body, f"{fname} must launch python via hook_python()")
        # The docs-lint launch lives in hook_helpers() (shared into post-edit/cursor bodies).
        # Wave 1p9bg: the call carries a bounded timeout (`, timeout=timeout_s`).
        # Wave 1p9c1: the post-edit call runs INCREMENTALLY (`--changed`); the full gate omits the flag.
        self.assertIn(
            'run_command([hook_python(), str(docs_lint), "--changed"], timeout=timeout_s)',
            self.mod.hook_helpers(),
        )
        # simulate-hooks body: no shared helpers (include_helpers=False) → inline guarded windowless.
        sim = self.mod.claude_simulate_hooks_source()
        self.assertIn("windowless_pythonw()", sim,
                      "claude_simulate_hooks_source must resolve a windowless interpreter inline")
        self.assertIn("python_exec = sys.executable", sim,
                      "claude_simulate_hooks_source must keep the sys.executable fallback")
        # Preserve the existing input= wiring (PIPE payload) in the converted bodies.
        self.assertIn("input=payload", sim, "simulate-hooks must preserve input=payload")
        self.assertIn("input=raw", self.mod.cursor_after_file_edit_source(),
                      "cursor after-file-edit must preserve input=raw")

    def test_every_rendered_mcp_command_stays_python3(self):
        # Wave 1p8pe AC-5: the MCP JSON-RPC stdio transport must NOT be pythonw-converted — every host's
        # rendered MCP server command must stay the byte-identical `python3` on server.py (a windows-
        # subsystem pythonw.exe with no console would break the stdio handshake the same way).
        renderers = {
            ".mcp.json": ("render_mcp_json", lambda r: r / ".mcp.json"),
            "cursor": ("render_cursor_mcp_json", lambda r: r / ".cursor" / "mcp.json"),
            "junie": ("render_junie_mcp_json", lambda r: r / ".junie" / "mcp" / "mcp.json"),
            "antigravity": ("render_antigravity_mcp_json", lambda r: r / ".agents" / "mcp_config.json"),
        }
        for host, (fn_name, path_of) in renderers.items():
            with self.subTest(host=host):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    getattr(self.mod, fn_name)(root)
                    data = json.loads(path_of(root).read_text(encoding="utf-8"))
                wf = data["mcpServers"]["wavefoundry"]
                self.assertEqual(wf["command"], "python3",
                                 f"{host} MCP command must stay python3 (never pythonw)")
                self.assertEqual(wf["args"], [".wavefoundry/framework/scripts/server.py"])

    def test_git_hooks_are_not_rendered(self):
        # Wave 1p88t: git hooks were dropped; the renderer must no longer expose git_hook_source /
        # render_git_hooks, and a render must leave no .wavefoundry/git-hooks/ behind.
        self.assertFalse(hasattr(self.mod, "git_hook_source"), "git_hook_source should be removed")
        self.assertFalse(hasattr(self.mod, "render_git_hooks"), "render_git_hooks should be removed")
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp).resolve()
            # Seed a stale hook to prove remove_git_hooks cleans it up on re-render.
            stale_dir = repo_root / ".wavefoundry" / "git-hooks"
            stale_dir.mkdir(parents=True)
            (stale_dir / "post-commit").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            self.mod.remove_git_hooks(repo_root)
            self.assertFalse(stale_dir.exists(), "remove_git_hooks should delete the git-hooks dir")


class GitAttributesTests(unittest.TestCase):
    """Wave 1p7pn (1p7pb-adr, L-1): a repo-root `.gitattributes` pins shebang-bearing files to LF so
    git-for-Windows `autocrlf` cannot corrupt the launcher/hook shebangs on checkout."""

    def test_committed_gitattributes_pins_shebang_files_to_lf(self):
        repo = PROJECT_ROOT.parent  # PROJECT_ROOT is `.wavefoundry`; its parent is the repo root
        ga = repo / ".gitattributes"
        self.assertTrue(ga.exists(), ".gitattributes must exist at the repo root")
        text = ga.read_text(encoding="utf-8")
        self.assertIn("* text=auto", text)
        self.assertIn("*.py text eol=lf", text)
        for prefix in (
            ".wavefoundry/bin/*",
            ".claude/hooks/*",
            ".cursor/hooks/*",
            ".github/hooks/*",
        ):
            self.assertIn(f"{prefix} text eol=lf", text, f"{prefix} not pinned to eol=lf")


class RenderGitignoreBlockTests(unittest.TestCase):
    """Wave 1p8vj: the runtime .gitignore block is written programmatically + idempotently, and
    self-heals on every render/upgrade, instead of relying on agent prose."""

    _CANONICAL = (
        ".wavefoundry/index/",
        ".wavefoundry/framework/index/",
        ".wavefoundry/logs/",
        ".wavefoundry/**/*.lock",
        ".wavefoundry/dashboard-server.json",
        ".wavefoundry/upgrade-in-progress.json",
        ".wavefoundry/guard-overrides.json",
        "/wavefoundry-*.zip",
    )

    def setUp(self):
        self.mod = _load_render_module()

    def test_creates_gitignore_with_block_when_missing(self):
        # AC-1 + AC-4: a fresh repo gets .gitignore with the full canonical runtime block.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            self.mod.render_gitignore_block(root)
            text = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(self.mod._GITIGNORE_BEGIN, text)
        self.assertIn(self.mod._GITIGNORE_END, text)
        for entry in self._CANONICAL:
            self.assertIn(entry, text, f"managed block must contain {entry}")

    def test_appends_block_and_is_idempotent(self):
        # AC-2: an existing .gitignore without the block gets it appended; a second run does not
        # duplicate the markers or entries.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / ".gitignore").write_text("node_modules/\n*.log\n", encoding="utf-8")
            self.mod.render_gitignore_block(root)
            once = (root / ".gitignore").read_text(encoding="utf-8")
            self.mod.render_gitignore_block(root)
            twice = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual(once, twice, "render must be idempotent")
        self.assertEqual(twice.count(self.mod._GITIGNORE_BEGIN), 1, "exactly one managed block")
        self.assertEqual(twice.count(".wavefoundry/index/"), 1, "no duplicate entries")

    def test_preserves_user_entries(self):
        # AC-3: operator-authored lines outside the managed region are kept verbatim.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / ".gitignore").write_text("node_modules/\n.env\n# my custom rule\nbuild/\n", encoding="utf-8")
            self.mod.render_gitignore_block(root)
            text = (root / ".gitignore").read_text(encoding="utf-8")
        for user_line in ("node_modules/", ".env", "# my custom rule", "build/"):
            self.assertIn(user_line, text, f"user entry {user_line!r} must be preserved")

    def test_folds_loose_managed_entries_without_duplicating(self):
        # A repo with the canonical entries as LOOSE lines (older hand-seeded block) must end up with
        # them ONLY inside the managed block — no duplicates — while user entries stay.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / ".gitignore").write_text(
                "node_modules/\n.wavefoundry/index/\n.wavefoundry/logs/\n", encoding="utf-8"
            )
            self.mod.render_gitignore_block(root)
            text = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual(text.count(".wavefoundry/index/"), 1)
        self.assertEqual(text.count(".wavefoundry/logs/"), 1)
        self.assertIn("node_modules/", text)

    def test_main_wires_gitignore_render(self):
        # AC-5: render_platform_surfaces.main() calls render_gitignore_block (runs on every
        # render / setup / upgrade) so the block is enforced and self-heals.
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        start = src.index("def main(")
        body = src[start:]
        self.assertIn("render_gitignore_block(repo_root)", body,
                      "main() must call render_gitignore_block so the block is enforced on every render")


class RenderGitattributesBlockTests(unittest.TestCase):
    """Wave 1p9hm: the LF line-ending policy for Wavefoundry-rendered files is propagated to target
    repos programmatically + idempotently, self-healing on every render/upgrade (previously the 1p7pn
    .gitattributes existed only in the self-host repo, so a git-for-Windows autocrlf checkout could
    rewrite the LF shebang in .wavefoundry/bin/* to CRLF and break the launcher)."""

    _PINS = (
        ".wavefoundry/bin/* text eol=lf",
        ".claude/hooks/* text eol=lf",
        ".wavefoundry/bin/*.cmd text eol=crlf",
    )

    def setUp(self):
        self.mod = _load_render_module()

    def test_creates_gitattributes_with_block_when_missing(self):
        # AC-1: a fresh repo gets .gitattributes with the managed line-ending block and the pins.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            self.mod.render_gitattributes_block(root)
            text = (root / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(self.mod._GITATTRIBUTES_BEGIN, text)
        self.assertIn(self.mod._GITATTRIBUTES_END, text)
        for pin in self._PINS:
            self.assertIn(pin, text, f"managed block must contain {pin!r}")
        # AC-scope: the narrow block must NOT overreach into the target's own sources.
        self.assertNotIn("* text=auto", text, "must not force a global text policy on a target repo")
        self.assertNotIn("*.py text eol=lf", text, "must not force all target Python to LF")

    def test_appends_block_and_is_idempotent(self):
        # AC-1: existing .gitattributes without the block gets it appended; a second run does not
        # duplicate the markers or entries.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / ".gitattributes").write_text("*.bin -text\n", encoding="utf-8")
            self.mod.render_gitattributes_block(root)
            once = (root / ".gitattributes").read_text(encoding="utf-8")
            self.mod.render_gitattributes_block(root)
            twice = (root / ".gitattributes").read_text(encoding="utf-8")
        self.assertEqual(once, twice, "render must be idempotent")
        self.assertEqual(twice.count(self.mod._GITATTRIBUTES_BEGIN), 1, "exactly one managed block")
        self.assertEqual(twice.count(".wavefoundry/bin/* text eol=lf"), 1, "no duplicate pins")

    def test_preserves_user_entries(self):
        # AC-1 (non-destructive): operator-authored attribute rules outside the block are kept verbatim.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / ".gitattributes").write_text(
                "*.bin -text\n*.md diff=markdown\n# custom\n", encoding="utf-8"
            )
            self.mod.render_gitattributes_block(root)
            text = (root / ".gitattributes").read_text(encoding="utf-8")
        for user_line in ("*.bin -text", "*.md diff=markdown", "# custom"):
            self.assertIn(user_line, text, f"user entry {user_line!r} must be preserved")

    def test_folds_loose_managed_pins_without_duplicating(self):
        # A repo that already has a pin as a LOOSE line ends up with it ONLY inside the managed block.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / ".gitattributes").write_text(
                "*.bin -text\n.wavefoundry/bin/* text eol=lf\n", encoding="utf-8"
            )
            self.mod.render_gitattributes_block(root)
            text = (root / ".gitattributes").read_text(encoding="utf-8")
        self.assertEqual(text.count(".wavefoundry/bin/* text eol=lf"), 1)
        self.assertIn("*.bin -text", text)

    def test_main_wires_gitattributes_render(self):
        # render_platform_surfaces.main() must call render_gitattributes_block so it self-heals.
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        body = src[src.index("def main("):]
        self.assertIn("render_gitattributes_block(repo_root)", body,
                      "main() must call render_gitattributes_block so the block is enforced on every render")


class HookStdinUtf8Tests(unittest.TestCase):
    """Wave 1p9j0 / change 1p9iv: rendered hooks must decode their host JSON payload from stdin as
    UTF-8 (HOOK_BOOTSTRAP calls cli_stdio.configure_utf8_stdio()), and the dev-simulation spawn must
    encode its input=payload as UTF-8 — so a native-Windows cp1252 console never mis-decodes / fails
    to encode a non-ASCII payload (a file path / message / diff excerpt carrying em-dash / box-drawing
    / accented characters)."""

    def setUp(self):
        self.mod = _load_render_module()

    def test_hook_bootstrap_calls_configure_utf8_stdio_guarded(self):
        # AC-2: HOOK_BOOTSTRAP calls configure_utf8_stdio() via a guarded import, AFTER the framework
        # scripts dir is on sys.path (so the import resolves), and the composed hook source carries it.
        bootstrap = self.mod.HOOK_BOOTSTRAP
        self.assertIn("import cli_stdio as _wf_cli_stdio", bootstrap)
        self.assertIn("_wf_cli_stdio.configure_utf8_stdio()", bootstrap)
        self.assertLess(
            bootstrap.index("_wf_sys.path.insert"),
            bootstrap.index("import cli_stdio"),
            "configure_utf8_stdio import must come after the sys.path insert",
        )
        # Best-effort: the import + call are wrapped in try/except so a hook rendered against an
        # old/transient tree lacking cli_stdio still runs.
        guarded = (
            "try:\n"
            "    import cli_stdio as _wf_cli_stdio\n"
            "\n"
            "    _wf_cli_stdio.configure_utf8_stdio()\n"
            "except Exception:\n"
            "    pass"
        )
        self.assertIn(guarded, bootstrap)
        composed = self.mod.compose_script("def main() -> int:\n    return 0\n")
        self.assertIn("_wf_cli_stdio.configure_utf8_stdio()", composed)

    def test_hook_bootstrap_tolerates_unimportable_cli_stdio(self):
        # AC-2 (best-effort): executing HOOK_BOOTSTRAP when cli_stdio (and venv_bootstrap) are
        # unimportable must NOT raise — the guarded try/except swallows the ImportError so the hook
        # still runs. Setting sys.modules[name] = None makes `import name` raise ImportError.
        import sys as _sys

        with tempfile.TemporaryDirectory() as tmp:
            ns = {"__file__": str(Path(tmp) / ".claude" / "hooks" / "hook.py")}
            with patch.dict(
                _sys.modules,
                {"cli_stdio": None, "venv_bootstrap": None, "subprocess_util": None},
            ):
                exec(compile(self.mod.HOOK_BOOTSTRAP, "<bootstrap>", "exec"), ns)  # must not raise

    def test_rendered_hook_body_decodes_utf8_stdin_payload(self):
        # AC-3: a composed hook body (real read_payload_text/load_payload/detect_file_path helpers)
        # decodes a non-ASCII UTF-8 stdin payload correctly. The child's std streams are forced to
        # cp1252 (simulating a native-Windows console) via PYTHONIOENCODING; without the bootstrap
        # stdin reconfigure the UTF-8 bytes would mis-decode. Platform-independent: cp1252 is always
        # available, so this runs identically on POSIX and never depends on the host being Windows.
        body = """
            def main() -> int:
                payload = load_payload(read_payload_text())
                sys.stdout.write("DECODED:" + detect_file_path(payload))
                sys.stdout.flush()
                return 0

            if __name__ == "__main__":
                raise SystemExit(main())
        """
        script = self.mod.compose_script(body)
        scripts_dir = SCRIPT_PATH.parent
        non_ascii = "docs/café/—résumé⚠.md"
        payload = json.dumps({"tool_input": {"file_path": non_ascii}})
        with tempfile.TemporaryDirectory() as tmp:
            hook = Path(tmp) / "hook.py"
            hook.write_text(script, encoding="utf-8")
            env = {
                **os.environ,
                "PYTHONIOENCODING": "cp1252:replace",
                "PYTHONPATH": str(scripts_dir),
                "WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1",
            }
            result = subprocess.run(
                ["python3", str(hook)],
                input=payload,
                text=True,
                encoding="utf-8",
                capture_output=True,
                env=env,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DECODED:" + non_ascii, result.stdout)

    def test_simulate_spawn_encodes_input_as_utf8(self):
        # AC-4: the claude_simulate_hooks_source() spawn encodes input=payload as UTF-8 (errors=replace)
        # so a non-ASCII payload never triggers a locale-codepage encode error on Windows. Exec the
        # generated simulate source with the bootstrap imports stubbed (deterministic, no real spawn)
        # and a patched subprocess.run that records the kwargs the spawn is invoked with.
        import sys as _sys
        import types as _types

        sim_src = self.mod.claude_simulate_hooks_source()
        recorded: dict[str, object] = {}

        def fake_run(args, **kwargs):
            recorded["args"] = args
            recorded["kwargs"] = kwargs

            class _R:
                returncode = 0

            return _R()

        stub_vb = _types.ModuleType("venv_bootstrap")
        stub_vb.activate_tool_venv = lambda: None
        stub_cs = _types.ModuleType("cli_stdio")
        stub_cs.configure_utf8_stdio = lambda: None
        stub_su = _types.ModuleType("subprocess_util")
        stub_su.windowless_pythonw = lambda: None

        payload = "payload-—⚠"
        with patch.dict(
            _sys.modules,
            {"venv_bootstrap": stub_vb, "cli_stdio": stub_cs, "subprocess_util": stub_su},
        ), patch.object(subprocess, "run", fake_run):
            with tempfile.TemporaryDirectory() as tmp:
                ns = {
                    "__name__": "wavefoundry_sim_under_test",
                    "__file__": str(Path(tmp) / ".claude" / "hooks" / "simulate-hooks.py"),
                }
                exec(compile(sim_src, "<simulate>", "exec"), ns)
                rc = ns["main"](["post-edit", payload])
        self.assertEqual(rc, 0)
        kwargs = recorded["kwargs"]
        self.assertEqual(kwargs.get("encoding"), "utf-8", "simulate spawn must pin encoding=utf-8")
        self.assertEqual(kwargs.get("errors"), "replace", "simulate spawn must use errors=replace")
        self.assertEqual(kwargs.get("input"), payload, "the payload must be passed through unchanged")


class CopilotRemovalDetectionGateTests(unittest.TestCase):
    """Wave 1p9pe (1p9p7-bug renderer-overwrite-safety): copilot-artifact
    removal must key off `detect_platforms(repo_root)` — whether the REPO has
    copilot surfaces — never off the invocation's explicit `--platform` set.
    Pre-fix, `render_platform_surfaces --platform claude` on a copilot repo
    deleted the committed `.github/hooks/*` (the wave-1p9j0 DF-2 clobber).
    """

    _HOOK_SENTINEL = '{"sentinel": "operator-committed copilot hooks"}\n'

    def _run_main(self, repo_root: Path, *platform_args: str) -> None:
        sub_env = {**os.environ, "WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}
        result = subprocess.run(
            ["python3", str(SCRIPT_PATH), "--repo-root", str(repo_root), *platform_args],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=sub_env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def _seed_copilot_hooks(self, repo_root: Path) -> Path:
        hooks_dir = repo_root / ".github" / "hooks"
        hooks_dir.mkdir(parents=True)
        hooks_json = hooks_dir / "hooks.json"
        hooks_json.write_text(self._HOOK_SENTINEL, encoding="utf-8")
        (hooks_dir / "pre-tool-use.py").write_text("# committed hook body\n", encoding="utf-8")
        return hooks_json

    def test_explicit_non_copilot_render_preserves_copilot_hooks(self) -> None:
        # AC-4: `--platform claude` on a repo WITH .github/copilot-instructions.md
        # must not delete .github/hooks/* — detection, not the invocation's
        # platform set, decides removal.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            (repo_root / ".github").mkdir()
            (repo_root / ".github" / "copilot-instructions.md").write_text("", encoding="utf-8")
            hooks_json = self._seed_copilot_hooks(repo_root)

            self._run_main(repo_root, "--platform", "claude")

            self.assertTrue(
                hooks_json.is_file(),
                ".github/hooks/hooks.json must survive an explicit non-copilot render on a copilot repo",
            )
            self.assertEqual(
                hooks_json.read_text(encoding="utf-8"), self._HOOK_SENTINEL,
                "the committed copilot hooks must be untouched (copilot was not in scope to re-render)",
            )
            self.assertTrue((repo_root / ".github" / "hooks" / "pre-tool-use.py").is_file())

    def test_no_copilot_repo_still_removes_stale_artifacts(self) -> None:
        # AC-5: on a repo with NO copilot surfaces, stale .github/hooks/*
        # copilot artifacts are still cleaned up — no regression.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            hooks_json = self._seed_copilot_hooks(repo_root)  # stale, no instructions file

            self._run_main(repo_root, "--platform", "claude")

            self.assertFalse(hooks_json.exists(), "stale copilot hooks.json must be removed")
            self.assertFalse((repo_root / ".github" / "hooks" / "pre-tool-use.py").exists())

    def test_copilot_in_scope_still_renders_artifacts(self) -> None:
        # AC-8: the removal-guard fix must not suppress legitimate copilot
        # rendering — both via auto-detect and via an explicit --platform copilot.
        with tempfile.TemporaryDirectory() as temp_dir:
            # Auto-detect: repo with copilot-instructions.md renders/refreshes hooks.
            repo_root = Path(temp_dir).resolve()
            (repo_root / ".github").mkdir()
            (repo_root / ".github" / "copilot-instructions.md").write_text("", encoding="utf-8")
            self._run_main(repo_root)
            hooks_json = repo_root / ".github" / "hooks" / "hooks.json"
            self.assertTrue(hooks_json.is_file(), "auto-detect on a copilot repo must render copilot hooks")
            rendered = json.loads(hooks_json.read_text(encoding="utf-8"))
            self.assertIn("preToolUse", rendered["hooks"])

        with tempfile.TemporaryDirectory() as temp_dir:
            # Explicit --platform copilot on a repo without the instructions file:
            # cleanup (detection says no copilot) runs BEFORE the render, so the
            # explicit render still leaves fresh artifacts in place.
            repo_root = Path(temp_dir).resolve()
            self._run_main(repo_root, "--platform", "copilot")
            hooks_json = repo_root / ".github" / "hooks" / "hooks.json"
            self.assertTrue(hooks_json.is_file(), "explicit --platform copilot must render copilot hooks")


if __name__ == "__main__":
    unittest.main()
