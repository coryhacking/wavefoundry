"""Server core/infrastructure MCP tool tests (shard 1 of 3, wave 1tmtx).

Retains the original basename: hosts the framework-wide subprocess
isolation guard (scan seams live in server_tools_support) and the
reader-census test whose grep filter names this file. Shared fixtures
come from server_tools_support; sibling shards are
test_server_tools_retrieval.py and test_server_tools_lifecycle.py.
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import importlib.util
import inspect
import io
import json
import math
import os
import stat
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import server_tools_support
from server_tools_support import (  # noqa: F401 — shared server-test fixtures
    SCRIPTS_ROOT,
    SERVER_PATH,
    integrity_checks,
    load_server,
    load_thin_runner,
    _make_repo,
    _store_read_meta,
    _seed_store_state,
    _write_index_layer,
    _write_sqlite_index,
)


class McpSubprocessHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def test_helper_never_inherits_json_rpc_stdio(self):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

        with patch.object(subprocess, "run", side_effect=fake_run):
            result = self.srv._mcp_subprocess_run(["tool"], cwd=Path.cwd())

        self.assertEqual(result.returncode, 0)
        self.assertIs(captured["stdin"], subprocess.DEVNULL)
        self.assertIs(captured["stdout"], subprocess.PIPE)
        self.assertIs(captured["stderr"], subprocess.PIPE)
        self.assertTrue(captured["text"])

    def test_helper_applies_windows_no_window_flag(self):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch.object(self.srv.os, "name", "nt"), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(subprocess, "run", side_effect=fake_run):
            self.srv._mcp_subprocess_run(["tool"], cwd=".", capture_output=False)

        self.assertEqual(captured["creationflags"], 0x08000000)
        self.assertIs(captured["stdin"], subprocess.DEVNULL)
        self.assertIs(captured["stdout"], subprocess.DEVNULL)
        self.assertIs(captured["stderr"], subprocess.DEVNULL)

    def test_background_index_refresh_uses_windows_no_window_flag(self):
        src = inspect.getsource(self.srv._start_background_index_refresh)
        self.assertIn("subprocess.DETACHED_PROCESS", src)
        self.assertIn("subprocess.CREATE_NEW_PROCESS_GROUP", src)
        self.assertIn("_windows_no_window_flag()", src)
        self.assertIn("stdin=subprocess.DEVNULL", src)  # wave 1p88t: sibling-consistent stdin isolation

    # --- wave 1p88t: MCP-reachable probes that previously bypassed the helper are now isolated ---

    def test_pid_is_running_isolates_stdin_and_no_window_on_windows(self):
        # tasklist liveness is MCP-reachable (12+ call sites incl. dashboard/index status).
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch.object(self.srv.os, "name", "nt"), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(subprocess, "run", side_effect=fake_run):
            self.srv._pid_is_running(4321)

        self.assertIs(captured["stdin"], subprocess.DEVNULL)
        self.assertEqual(captured["creationflags"], 0x08000000)

    def test_git_audits_route_through_mcp_subprocess_helper(self):
        # _audit_commit_governance (git log) and _audit_harnessability (git grep) are MCP-reachable
        # via wf_audit; both must go through the shared helper, not a raw _sp/__import__ subprocess.
        for fn_name, expect_cmd in (
            ("_audit_commit_governance", ["git", "log"]),
            ("_audit_harnessability", ["git", "grep"]),
        ):
            with self.subTest(fn=fn_name):
                calls: list[list[str]] = []

                def fake_helper(cmd, **kwargs):
                    calls.append(list(cmd))
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

                with tempfile.TemporaryDirectory() as tmp:
                    with patch.object(self.srv, "_mcp_subprocess_run", side_effect=fake_helper):
                        getattr(self.srv, fn_name)(Path(tmp))
                self.assertTrue(calls, f"{fn_name} did not call _mcp_subprocess_run")
                self.assertEqual(calls[0][:2], expect_cmd, f"{fn_name} forwarded the wrong command")

    def test_no_raw_subprocess_lacks_stdin_isolation(self):
        # Breadth guard (wave 1p88t, broadened in 1p8gu): EVERY subprocess invocation in the
        # MCP-reachable modules — `server_impl` AND the in-process secrets-scan fallback
        # (`wave_lint_lib/secrets_validators`, reached by the `wf_scan_secrets` tool's except-branch)
        # — must isolate stdin. After 1p8gu the secrets git probes route through
        # `subprocess_util.isolated_run` (inherently isolated); server_impl keeps `_mcp_subprocess_run`
        # + inline `stdin=DEVNULL`/`input=`. Covers aliased `_sp.run` / `__import__("subprocess").run`
        # forms that evaded the first review.
        import re

        targets = [
            SCRIPTS_ROOT / "server_impl.py",
            SCRIPTS_ROOT / "wave_lint_lib" / "secrets_validators.py",
        ]
        # Count both RAW spawns and shared-helper routings so the scan stays non-vacuous after 1p8gu
        # moved most secrets spawns onto subprocess_util.isolated_run/isolated_popen.
        call_re = re.compile(
            r"(?:subprocess|_sp)\.(?:run|Popen)\(|__import__\((?:'|\")subprocess(?:'|\")\)\.(?:run|Popen)\("
        )
        helper_re = re.compile(r"subprocess_util\.isolated_(?:run|popen)\(")
        offenders = []
        matched = 0
        for path in targets:
            src_lines = path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(src_lines):
                if helper_re.search(line):
                    matched += 1
                    continue  # shared helper guarantees isolation by construction
                if not call_re.search(line):
                    continue
                matched += 1
                if "subprocess.run(cmd, **kwargs)" in line:
                    continue  # the shared helper's own delegation (sets stdin in its kwargs dict)
                window = "\n".join(src_lines[max(0, i - 20):i + 20])
                # Isolated when stdin is explicitly DEVNULL'd, or fed via input= (PIPE, not inherited).
                if ("stdin" in window and "DEVNULL" in window) or "input=" in window:
                    continue
                offenders.append(f"{path.name}:{i + 1}: {line.strip()}")
        # Non-vacuous: the scan must actually find the known spawn/routing sites across both modules.
        # If this drops near 0 the regex has rotted into a tautology.
        self.assertGreaterEqual(matched, 10, "subprocess-isolation scan matched too few sites — regex likely broken")
        self.assertEqual(
            offenders, [],
            "raw subprocess invocations in MCP-reachable modules must isolate stdin from the JSON-RPC "
            "stream (route through subprocess_util.isolated_run / _mcp_subprocess_run or pass "
            "stdin=subprocess.DEVNULL / input=):\n"
            + "\n".join(offenders),
        )


class FrameworkWideSubprocessIsolationGuard(unittest.TestCase):
    """Wave 1p8gu: the breadth guard now spans EVERY framework script (not just server_impl +
    secrets). The guarantee is call-path-independent: no framework-initiated subprocess may inherit a
    blocking stdin or flash a console window on native Windows — regardless of whether it was reached
    via the MCP server, the `wf` dispatcher, a direct `python <script>.py` run, or an agent invoking
    `wf <subcommand>`. The field defect (a 1.9.4 native-Windows upgrade) was a stack of flashing
    console windows + a hang on inherited stdin from the setup/upgrade/index/graph/secrets pipeline,
    which 1p88t's MCP-only scope had left uncovered.

    This guard FAILS when a new bare `subprocess.run` / `subprocess.Popen` (or aliased `_sp.*`) is
    added without isolation — that is its whole purpose.
    """

    # Dev-host-only tools, excluded from every distribution zip (build_pack.EXCLUDED_REL_PATHS): they
    # run on a developer's source-host terminal with a real console (interactive `gh release` / git
    # push / the test runner), never on a target machine — the documented must-inherit exception class.
    _DEV_HOST_EXEMPT_FILES = {"build_pack.py", "run_tests.py"}

    # Alias of the support module's set (wave 1tmtx delivery review): the scan
    # seams below read server_tools_support.SPAWN_ATTRS, so a divergent literal
    # here would silently not widen the scan. One shared object keeps any
    # future widening visible to the seams.
    _SPAWN_ATTRS = server_tools_support.SPAWN_ATTRS
    # Process-POOL / raw-process constructs that spawn console-subsystem workers on Windows.
    _POOL_NAMES = {"ProcessPoolExecutor", "Pool", "Process"}

    @staticmethod
    def _framework_script_paths() -> list[Path]:
        paths = sorted(SCRIPTS_ROOT.glob("*.py"))
        paths += sorted((SCRIPTS_ROOT / "wave_lint_lib").glob("*.py"))
        # subprocess_util IS the isolation helper; its own `subprocess.run(cmd, **kwargs)` delegation
        # sets the isolation kwargs and is the single allowlisted exception by construction.
        return [p for p in paths if p.name != "subprocess_util.py"]

    # Wave 1tmtx (1tm6d): the AST scan seams live in server_tools_support so
    # non-test consumers (test_render_platform_surfaces) import pure support
    # callables instead of executing this test module. staticmethod rebinding
    # keeps every existing self./cls. call site working unchanged.
    _subprocess_aliases = staticmethod(server_tools_support._subprocess_aliases)
    _spawn_calls = staticmethod(server_tools_support._spawn_calls)
    _call_kwarg_names = staticmethod(server_tools_support._call_kwarg_names)
    _call_has_devnull_or_input = staticmethod(server_tools_support._call_has_devnull_or_input)
    _call_has_no_window = staticmethod(server_tools_support._call_has_no_window)
    _is_isolated_helper_call = staticmethod(server_tools_support._is_isolated_helper_call)

    def test_every_framework_spawn_isolates_stdin_and_suppresses_window(self):
        """AST-scoped guard: every raw subprocess spawn (in ANY form — aliased, from-import,
        os.system/popen, asyncio) must isolate stdin AND suppress the Windows window via ITS OWN
        kwargs. Routing through subprocess_util.isolated_* counts as isolated."""
        import ast as _ast

        stdin_offenders: list[str] = []
        nowindow_offenders: list[str] = []
        matched = 0
        for path in self._framework_script_paths():
            if path.name in self._DEV_HOST_EXEMPT_FILES:
                continue
            src = path.read_text(encoding="utf-8")
            lines = src.splitlines()
            tree = _ast.parse(src)
            for node in self._spawn_calls(tree):
                if self._is_isolated_helper_call(node):
                    continue
                matched += 1
                line = lines[node.lineno - 1].strip()
                # os.system/os.popen always inherit stdio + (on Windows) flash a console — never allowed.
                func = node.func
                is_os_shell = (isinstance(func, _ast.Attribute) and getattr(func.value, "id", None) == "os"
                               and func.attr in ("system", "popen"))
                if is_os_shell or not self._call_has_devnull_or_input(node):
                    stdin_offenders.append(f"{path.name}:{node.lineno}: {line}")
                if is_os_shell or not self._call_has_no_window(node):
                    nowindow_offenders.append(f"{path.name}:{node.lineno}: {line}")

        # Non-vacuous: the AST walk must still find the handful of inline-isolated raw spawns that
        # legitimately remain (server_impl's _mcp_subprocess_run **kwargs delegation + 3 detached Popens
        # + the _pid_is_running tasklist; setup_index's foreground streaming Popen; venv_bootstrap's
        # import-fallback). Most spawns route through subprocess_util.isolated_* (skipped above). If this
        # collapses to ~0 the AST walk broke.
        self.assertGreaterEqual(
            matched, 5,
            "framework-wide spawn scan matched too few raw sites — the AST walk likely broke",
        )
        self.assertEqual(
            stdin_offenders, [],
            "framework subprocess spawns must isolate stdin via their own kwargs (route through "
            "subprocess_util.isolated_run/isolated_popen, or pass stdin=subprocess.DEVNULL / input=):\n"
            + "\n".join(stdin_offenders),
        )
        self.assertEqual(
            nowindow_offenders, [],
            "framework subprocess spawns must suppress the Windows console window via their own kwargs "
            "(route through subprocess_util.isolated_*, or OR CREATE_NO_WINDOW into creationflags):\n"
            + "\n".join(nowindow_offenders),
        )

    def test_every_process_pool_uses_windowfree_helper(self):
        """GUARD generalization (MP-1/MP-5): every ProcessPoolExecutor / multiprocessing pool / Pool /
        Process construction must have the window-free-pool helper (windowless_mp_context /
        configure_windowless_mp_context) adjacent in the SAME function, so spawn workers do not each
        flash a console window on Windows. AST-detected so a new pool can't slip in bare."""
        import ast as _ast

        offenders: list[str] = []
        matched = 0
        for path in self._framework_script_paths():
            if path.name in self._DEV_HOST_EXEMPT_FILES:
                continue
            src = path.read_text(encoding="utf-8")
            tree = _ast.parse(src)
            # Map each function def to its source span so we can check the helper is used within it.
            func_spans = []
            for fn in _ast.walk(tree):
                if isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    end = getattr(fn, "end_lineno", None) or fn.lineno
                    func_spans.append((fn.lineno, end, _ast.get_source_segment(src, fn) or ""))
            for node in _ast.walk(tree):
                if not isinstance(node, _ast.Call):
                    continue
                func = node.func
                name = None
                if isinstance(func, _ast.Name):
                    name = func.id
                elif isinstance(func, _ast.Attribute):
                    name = func.attr
                if name not in self._POOL_NAMES:
                    continue
                # multiprocessing.get_context is also a pool-prep call but is covered by the helper;
                # the construction nodes (PPE/Pool/Process) are the audit points.
                matched += 1
                # Find the enclosing function's source; require the window-free helper named in it.
                enclosing = ""
                for lo, hi, seg in func_spans:
                    if lo <= node.lineno <= hi and len(seg) > len(enclosing):
                        enclosing = seg
                if not enclosing:
                    enclosing = src  # module-level pool (none expected) — check whole file
                if ("windowless_mp_context" not in enclosing
                        and "configure_windowless_mp_context" not in enclosing):
                    offenders.append(f"{path.name}:{node.lineno}: {name}(...) without window-free pool helper")
        self.assertGreaterEqual(
            matched, 1,
            "process-pool scan matched no pool sites — the AST walk likely broke",
        )
        self.assertEqual(
            offenders, [],
            "every ProcessPoolExecutor / Pool / Process must construct its mp context via "
            "subprocess_util.windowless_mp_context (console-free workers on Windows):\n"
            + "\n".join(offenders),
        )

    def test_every_captured_text_spawn_decodes_utf8(self):
        """AC-3 framework-wide (review F2): every captured ``subprocess.run(..., text=True)`` (or
        capture_output=True) must specify ``encoding=`` on its OWN kwargs, OR route through
        subprocess_util.isolated_run (which folds in encoding='utf-8', errors='replace'). The earlier
        AC-3 scan covered ONLY upgrade_wavefoundry.py — this spans all framework scripts via AST."""
        import ast as _ast

        offenders: list[str] = []
        matched = 0
        for path in self._framework_script_paths():
            if path.name in self._DEV_HOST_EXEMPT_FILES:
                continue
            src = path.read_text(encoding="utf-8")
            lines = src.splitlines()
            tree = _ast.parse(src)
            for node in self._spawn_calls(tree):
                if self._is_isolated_helper_call(node):
                    continue  # isolated_run folds in encoding/errors
                kwargs = self._call_kwarg_names(node)
                if None in {kw.arg for kw in node.keywords}:
                    continue  # **kwargs splat (the _mcp_subprocess_run-style delegation sets encoding)
                captured_text = ("text" in kwargs or "universal_newlines" in kwargs
                                 or "capture_output" in kwargs)
                if not captured_text:
                    continue  # not a captured text spawn (e.g. detached Popen to a binary log file)
                matched += 1
                if "encoding" not in kwargs:
                    offenders.append(f"{path.name}:{node.lineno}: {lines[node.lineno-1].strip()}")
        self.assertGreaterEqual(
            matched, 1, "captured-text-spawn scan matched none — the AST walk likely broke",
        )
        self.assertEqual(
            offenders, [],
            "captured text spawns must decode UTF-8 (route through subprocess_util.isolated_run or pass "
            "encoding='utf-8', errors='replace'):\n" + "\n".join(offenders),
        )

    def test_cli_entrypoint_mains_configure_utf8_stdio(self):
        """F3 (review): every CLI entry-point module that prints non-ASCII must wire
        cli_stdio.configure_utf8_stdio() (at module top after venv activation, or inside main) so a
        direct ``python <script>.py`` run on a cp1252 console never raises."""
        entrypoints = [
            "upgrade_wavefoundry.py", "setup_wavefoundry.py", "setup_index.py", "wf_cli.py",
            "docs_gardener.py", "docs_lint.py", "run_secrets_scan.py", "gen_codebase_map.py",
            "dashboard_server.py", "render_platform_surfaces.py", "gpu_doctor.py", "indexer.py",
            "check_version.py", "prune_framework.py",
        ]
        offenders = []
        for fname in entrypoints:
            src = (SCRIPTS_ROOT / fname).read_text(encoding="utf-8")
            if "configure_utf8_stdio()" not in src:
                offenders.append(fname)
        self.assertEqual(
            offenders, [],
            "these CLI entry points must call cli_stdio.configure_utf8_stdio():\n" + "\n".join(offenders),
        )

    def test_pipeline_files_route_through_shared_helper(self):
        # AC-3: the specific upgrade/setup/index/graph/secrets pipeline files must reference the shared
        # isolation helper (named-file assertion — the spawns that broke the field upgrade).
        expected = {
            "upgrade_wavefoundry.py": "subprocess_util",
            "setup_index.py": "subprocess_util",
            "indexer.py": "subprocess_util",
            "graph_indexer.py": "subprocess_util",
            "gen_codebase_map.py": "cli_stdio",  # no spawns; CLI-encoding wiring instead
        }
        for fname, token in expected.items():
            src = (SCRIPTS_ROOT / fname).read_text(encoding="utf-8")
            self.assertIn(token, src, f"{fname} does not reference the shared {token} helper")
        # scan_secrets is a lib (run_secrets_scan is its CLI); both route through subprocess_util.
        for fname in ("scan_secrets.py", "run_secrets_scan.py"):
            src = (SCRIPTS_ROOT / fname).read_text(encoding="utf-8")
            self.assertIn("subprocess_util", src, f"{fname} does not route through subprocess_util")

    def test_single_shared_isolation_helper_no_duplicates(self):
        # AC-1: the four pre-existing per-module no-window helper bodies are gone — exactly ONE
        # definition of the consolidated helper remains (anti-drift). server_impl keeps a thin
        # `_windows_no_window_flag` ALIAS that DELEGATES to the shared helper (not a re-implementation),
        # so its presence is allowed only when it returns the delegation.
        import re

        dup_def_re = re.compile(r"^\s*def _no_window_creationflags\(", re.MULTILINE)
        offenders = []
        for path in self._framework_script_paths():
            src = path.read_text(encoding="utf-8")
            if dup_def_re.search(src):
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            "duplicate `_no_window_creationflags` definitions must be consolidated into "
            "subprocess_util.no_window_creationflags():\n" + "\n".join(offenders),
        )
        # The shared helper is the single source.
        helper_src = (SCRIPTS_ROOT / "subprocess_util.py").read_text(encoding="utf-8")
        self.assertIn("def no_window_creationflags(", helper_src)
        self.assertIn("def isolated_run(", helper_src)
        self.assertIn("def isolated_popen(", helper_src)
        # server_impl's retained alias must DELEGATE, not re-implement the getattr lookup.
        si_src = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        self.assertIn("subprocess_util.no_window_creationflags()", si_src)

    def test_guard_detects_planted_bare_and_aliased_spawns(self):
        # GUARD-2: drive the PRODUCTION scan methods (_spawn_calls / _call_has_devnull_or_input /
        # _call_has_no_window) over planted-defect source — NOT a re-implementation. Proves the guard
        # FAILS for a bare spawn, an ALIASED spawn (`import subprocess as sp`), a from-import spawn
        # (`from subprocess import run`), and os.system — the exact forms the old text scan missed.
        import ast as _ast
        plants = {
            "bare": "import subprocess\ndef f():\n    return subprocess.run(['git','status'], capture_output=True, text=True)\n",
            "aliased": "import subprocess as sp\ndef f():\n    return sp.run(['git','status'], capture_output=True, text=True)\n",
            "from_import": "from subprocess import run\ndef f():\n    return run(['git','status'], capture_output=True, text=True)\n",
            "os_system": "import os\ndef f():\n    return os.system('git status')\n",
        }
        for label, src in plants.items():
            with self.subTest(plant=label):
                tree = _ast.parse(src)
                calls = list(self._spawn_calls(tree))
                self.assertTrue(calls, f"{label}: _spawn_calls did not detect the planted spawn")
                node = calls[0]
                is_os = (isinstance(node.func, _ast.Attribute)
                         and getattr(node.func.value, "id", None) == "os"
                         and node.func.attr in ("system", "popen"))
                # Bare/aliased/from-import lack stdin+no-window; os.system always inherits/flashes.
                self.assertTrue(
                    is_os or not self._call_has_devnull_or_input(node),
                    f"{label}: guard wrongly considered the planted spawn stdin-isolated",
                )
                self.assertTrue(
                    is_os or not self._call_has_no_window(node),
                    f"{label}: guard wrongly considered the planted spawn window-suppressed",
                )

    def test_guard_detects_planted_process_pool(self):
        # GUARD-2 (pool): the pool guard must flag a ProcessPoolExecutor / Pool / Process built WITHOUT
        # the window-free helper. Drives the same name-detection the production pool scan uses.
        import ast as _ast
        for ctor in ("ProcessPoolExecutor", "Pool", "Process"):
            with self.subTest(ctor=ctor):
                src = f"def f():\n    p = {ctor}(max_workers=4)\n    return p\n"
                tree = _ast.parse(src)
                found = []
                for node in _ast.walk(tree):
                    if isinstance(node, _ast.Call):
                        fn = node.func
                        nm = fn.id if isinstance(fn, _ast.Name) else getattr(fn, "attr", None)
                        if nm in self._POOL_NAMES:
                            found.append(nm)
                self.assertIn(ctor, found, f"pool guard failed to detect a planted {ctor}")
                # And the enclosing source lacks the helper → would be flagged.
                self.assertNotIn("windowless_mp_context", src)

    def test_upgrade_has_no_detached_background_index_launcher(self):
        # Model-set v2 publishes one synchronous all-layer epoch and suppresses the redundant
        # Phase 4c detached pass. No dead background launcher or log handle may remain.
        src = (SCRIPTS_ROOT / "upgrade_wavefoundry.py").read_text(encoding="utf-8")
        self.assertEqual(
            src.count("subprocess_util.isolated_popen("), 0,
            "upgrade must not retain a detached semantic-index launcher",
        )
        self.assertNotIn("_bg_log_file", src)

    # ── Wave 1p8pe: framework python spawns must launch via the console-free pythonw.exe on Windows ──
    #
    # A console-subsystem ``python.exe`` still briefly flashes a console for long-running / detached /
    # rapid spawns even WITH ``CREATE_NO_WINDOW``; a windows-subsystem ``pythonw.exe`` cannot allocate a
    # console at all. So a framework python spawn whose output is redirected (DEVNULL / PIPE / log) must
    # resolve its interpreter through ``subprocess_util.windowless_pythonw()`` (directly, or via the
    # ``_preferred_python()`` resolver which prefers pythonw on Windows). Sites that genuinely NEED a
    # console (operator-visible installs, the operator-terminal CLI re-exec, the MCP JSON-RPC stdio
    # transport, dev-host tools) are DOCUMENTED KEEPS — listed below, keyed by file + a stable signature
    # of the kept spawn, with the reason it must inherit a real console.
    #
    # An interpreter-token expression counts as a "python spawn" when the spawned argv's first element
    # references one of these tokens.
    _PYTHON_INTERP_TOKENS = (
        "sys.executable", "_preferred_python", "_tool_venv_python", "tool_venv_python",
        "venv_python", "probe_interp", "python_exec", "windowless_pythonw",
    )
    # An interpreter is "windowless" (converted) when its expression — or its enclosing function —
    # routes the interpreter through pythonw: either the direct helper, or the _preferred_python()
    # resolver (which prefers pythonw on Windows; wave 1p8pe).
    _WINDOWLESS_MARKERS = ("windowless_pythonw", "_preferred_python")
    # Documented keeps: {filename: {signature-substring: reason}}. The signature must appear on the
    # spawn-call source line so a NEW python spawn (a different signature) is not silently grandfathered.
    _PYTHONW_KEEPS = {
        # Console-streaming installs — the operator must SEE pip / venv progress on a real console.
        "setup_index.py": {
            '"-m", "venv"': "venv creation — console-visible bootstrap, before any tool venv exists",
            '"-m", "pip", "install"': "pip install — operator must see the streaming install progress",
        },
        # Operator-terminal CLI re-exec — runs on a real console with the operator watching.
        "wf_cli.py": {
            "[sys.executable, str(target)": "wf dispatcher re-exec — operator-terminal CLI output",
        },
        # setup_wavefoundry runs its MCP smoke / phase scripts with operator console output.
        "setup_wavefoundry.py": {
            "[sys.executable, str(script_path), \"--repo-root\"": "setup phase script — operator-visible console output",
        },
        # Dev-host-only (also in _DEV_HOST_EXEMPT_FILES) — runs on a developer terminal.
        "build_pack.py": {
            "[sys.executable, str(script)]": "dev-host packaging — developer console",
            "sys.executable": "dev-host packaging — developer console",
        },
    }

    @classmethod
    def _all_spawn_and_isolated_calls(cls, tree):
        """Every spawn-shaped Call to audit for its interpreter token: the raw spawns from _spawn_calls
        PLUS the subprocess_util.isolated_run/isolated_popen wrapper calls (where most framework python
        spawns actually route — _spawn_calls intentionally excludes the wrapper for the stdin/no-window
        scan, but the interpreter token lives in the wrapper's argv too)."""
        import ast as _ast
        seen = set()
        for node in cls._spawn_calls(tree):
            seen.add(id(node))
            yield node
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Call) and cls._is_isolated_helper_call(node) and id(node) not in seen:
                yield node

    @classmethod
    def _spawn_argv_first_token(cls, node, src):
        """Return the source text of the spawn argv's first element (the interpreter), or None when the
        call's first positional arg is not a list literal we can introspect."""
        import ast as _ast
        if not node.args:
            return None
        a0 = node.args[0]
        if isinstance(a0, _ast.List) and a0.elts:
            return _ast.get_source_segment(src, a0.elts[0]) or ""
        # `cmd` variable form — resolve the most recent `cmd = [<first>, ...]` literal above the call.
        if isinstance(a0, _ast.Name):
            target = a0.id
            best = None
            for n in _ast.walk(_ast.parse(src)):
                if (isinstance(n, _ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], _ast.Name) and n.targets[0].id == target
                        and isinstance(n.value, _ast.List) and n.value.elts
                        and n.lineno <= node.lineno):
                    if best is None or n.lineno > best.lineno:
                        best = n
            if best is not None:
                return _ast.get_source_segment(src, best.value.elts[0]) or ""
        return None

    def test_every_framework_python_spawn_uses_windowless_pythonw_or_is_keep(self):
        """Wave 1p8pe guard: every framework python spawn (argv[0] is a python interpreter) must launch
        via the console-free pythonw.exe path on Windows — directly through windowless_pythonw() or via
        the _preferred_python() resolver — UNLESS its file+signature is a documented console keep."""
        import ast as _ast

        offenders: list[str] = []
        matched = 0
        for path in self._framework_script_paths():
            if path.name in self._DEV_HOST_EXEMPT_FILES:
                continue
            src = path.read_text(encoding="utf-8")
            lines = src.splitlines()
            tree = _ast.parse(src)
            # Map each function def to its source span (mirrors the pool guard) so the enclosing-function
            # `interp = windowless_pythonw() or ...` form counts as converted.
            func_spans = []
            for fn in _ast.walk(tree):
                if isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    end = getattr(fn, "end_lineno", None) or fn.lineno
                    func_spans.append((fn.lineno, end, _ast.get_source_segment(src, fn) or ""))
            for node in self._all_spawn_and_isolated_calls(tree):
                first = self._spawn_argv_first_token(node, src)
                if first is None:
                    continue
                if not any(tok in first for tok in self._PYTHON_INTERP_TOKENS):
                    continue  # not a python interpreter spawn (e.g. a git / nvidia-smi probe)
                matched += 1
                call_line = lines[node.lineno - 1]
                # Converted: the interpreter expr OR the enclosing function references the windowless path.
                if any(m in first for m in self._WINDOWLESS_MARKERS):
                    continue
                enclosing = ""
                for lo, hi, seg in func_spans:
                    if lo <= node.lineno <= hi and len(seg) > len(enclosing):
                        enclosing = seg
                if any(m in enclosing for m in self._WINDOWLESS_MARKERS):
                    continue
                # Documented keep? signature must be on the spawn-call source line.
                keeps = self._PYTHONW_KEEPS.get(path.name, {})
                if any(sig in call_line or sig in enclosing for sig in keeps):
                    continue
                offenders.append(f"{path.name}:{node.lineno}: {call_line.strip()}")
        self.assertGreaterEqual(
            matched, 5,
            "python-spawn scan matched too few sites — the AST walk likely broke",
        )
        self.assertEqual(
            offenders, [],
            "framework python spawns must launch via subprocess_util.windowless_pythonw() (directly or "
            "via _preferred_python()) so they never flash a console window on Windows — or be added to "
            "_PYTHONW_KEEPS with the reason a real console is required:\n" + "\n".join(offenders),
        )

    def test_pythonw_keeps_are_real_console_sites(self):
        """Non-vacuous: each documented pythonw KEEP signature must actually occur in its file (so the
        allowlist cannot rot into grandfathering spawns that no longer exist)."""
        for fname, keeps in self._PYTHONW_KEEPS.items():
            src = (SCRIPTS_ROOT / fname).read_text(encoding="utf-8")
            for sig in keeps:
                self.assertIn(
                    sig, src,
                    f"_PYTHONW_KEEPS[{fname!r}] signature {sig!r} no longer appears in the file — "
                    "remove the stale keep so the guard stays honest",
                )

    def test_converted_python_spawns_reference_windowless_pythonw(self):
        """Non-vacuous positive: the converted per-site spawns actually thread the windowless helper."""
        si = (SCRIPTS_ROOT / "setup_index.py").read_text(encoding="utf-8")
        self.assertEqual(
            si.count("subprocess_util.windowless_pythonw() or"), 3,
            "setup_index must convert its three spawn sites (background build, foreground indexer, "
            "import probe) via windowless_pythonw() with a venv-python fallback",
        )
        ds = (SCRIPTS_ROOT / "dashboard_server.py").read_text(encoding="utf-8")
        self.assertIn("subprocess_util.windowless_pythonw() or sys.executable", ds)
        for fname in ("server_impl.py", "upgrade_wavefoundry.py"):
            src = (SCRIPTS_ROOT / fname).read_text(encoding="utf-8")
            self.assertIn(
                "subprocess_util.windowless_pythonw()", src,
                f"{fname}._preferred_python must prefer the windowless pythonw on Windows",
            )

    def test_setup_index_resolver_and_venv_bootstrap_keeps_unchanged(self):
        """Wave 1p8pe AC-2: the :134 resolver + venv path-math + console pip install must be UNTOUCHED —
        _tool_venv_python() stays a plain venv_bootstrap delegation (no pythonw), and the pip-install
        spawn keeps its plain venv-python interpreter (console-streaming progress)."""
        import ast as _ast
        src = (SCRIPTS_ROOT / "setup_index.py").read_text(encoding="utf-8")
        tree = _ast.parse(src)
        resolver = None
        for fn in _ast.walk(tree):
            if isinstance(fn, _ast.FunctionDef) and fn.name == "_tool_venv_python":
                resolver = _ast.get_source_segment(src, fn) or ""
        self.assertIsNotNone(resolver, "setup_index._tool_venv_python not found")
        self.assertIn("venv_bootstrap.tool_venv_python()", resolver)
        self.assertNotIn("windowless_pythonw", resolver,
                         "the :134 resolver must NOT be pythonw-converted (it feeds venv path-math)")
        # The console pip install keeps the venv python (operator sees streaming install progress).
        self.assertIn('cmd = [str(venv_python), "-m", "pip", "install"]', src)
        # venv_bootstrap.tool_venv_python itself stays pythonw-free (shared by in-process callers).
        vb = (SCRIPTS_ROOT / "venv_bootstrap.py").read_text(encoding="utf-8")
        self.assertNotIn("windowless_pythonw", vb,
                         "venv_bootstrap must not import/use windowless_pythonw (stdlib-only)")

    def test_provider_policy_nvidia_probe_isolates_stdin_and_no_window_on_windows(self):
        # nvidia-smi probe is MCP-reachable via wf_gpu_doctor / provider selection in the server process.
        import provider_policy

        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, stdout="GPU 0", stderr="")

        with patch.object(provider_policy, "shutil") as shutil_mock, \
             patch.object(provider_policy.os, "name", "nt"), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(subprocess, "run", side_effect=fake_run):
            shutil_mock.which.return_value = "/usr/bin/nvidia-smi"
            provider_policy.nvidia_gpu_present()

        self.assertIs(captured["stdin"], subprocess.DEVNULL)
        self.assertEqual(captured["creationflags"], 0x08000000)

    def test_dashboard_powershell_scan_isolates_stdin_and_no_window_on_windows(self):
        # The PowerShell cmdline scan is MCP-reachable via server_impl's dashboard reconciliation.
        import dashboard_lib

        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch.object(dashboard_lib.os, "name", "nt"), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(subprocess, "run", side_effect=fake_run):
            dashboard_lib._windows_process_cmdlines()

        self.assertIs(captured["stdin"], subprocess.DEVNULL)
        self.assertEqual(captured["creationflags"], 0x08000000)


class FrameworkInProcessStdoutPurityGuard(unittest.TestCase):
    """Wave 1p9io: a companion to FrameworkWideSubprocessIsolationGuard for Python-level stdout.

    The prior stdio-hardening waves (1p8vc/1p88t) isolated native fd-1 writes (onnxruntime/DirectML)
    and MCP-helper *subprocess* stdout, but nothing guarded plain Python ``print()`` on the in-process
    call set reachable from MCP tool handlers. ``server.py`` repoints ``sys.stdout`` to the private fd
    the stdio JSON-RPC transport writes frames through, so any in-process ``print()`` to stdout corrupts
    the protocol frame — worst on the native-Windows host least tolerant of a bad first-call frame.

    There are exactly two in-process boundaries where indexer/graph code runs inside the server (every
    other index build is a subprocess, isolated by construction):

    1. ``graph_query._ensure_graph_builder_current`` → ``indexer.build_index(full=True)`` — the graph
       auto-rebuild on the first graph query after a builder-version bump. Protected by wrapping the
       call in ``cli_stdio.isolated_stdout_fd()`` + ``contextlib.redirect_stdout(sys.stderr)`` so ALL
       output during the rebuild (any of indexer's ~50 progress prints, a missing-grammar warning, a
       native fd-1 write) is neutralized at the boundary regardless of upstream print sites.
    2. ``indexer.walk_repo`` — called in-process from the navigation tools and index-health. It is NOT
       wrapped (called directly), so every ``print()`` in its body must route to ``file=sys.stderr``.

    These guards FAIL if the boundary wrapper is removed (1) or a bare-stdout ``print()`` is added to
    ``walk_repo`` (2) — their whole purpose.
    """

    def test_graph_query_in_process_build_index_is_stdout_isolated(self):
        """Every ``build_index(`` call in graph_query.py must sit inside a function that also references
        ``isolated_stdout_fd``/``redirect_stdout`` — the in-process graph auto-rebuild must never be able
        to write to the JSON-RPC stdout channel."""
        import ast as _ast

        src = (SCRIPTS_ROOT / "graph_query.py").read_text(encoding="utf-8")
        tree = _ast.parse(src)
        # Collect the line spans of `with` blocks whose CONTEXT-MANAGER EXPRESSIONS reference the
        # stdout-isolation helpers. We inspect the withitems' AST (via ast.dump) — NOT the raw source —
        # so a mere comment mentioning "isolated_stdout_fd" cannot satisfy the guard; only a real
        # `with cli_stdio.isolated_stdout_fd()/contextlib.redirect_stdout(...):` counts.
        guard_spans: list[tuple[int, int]] = []
        for node in _ast.walk(tree):
            if isinstance(node, _ast.With):
                items_dump = " ".join(_ast.dump(item) for item in node.items)
                if "isolated_stdout_fd" in items_dump or "redirect_stdout" in items_dump:
                    guard_spans.append((node.lineno, getattr(node, "end_lineno", None) or node.lineno))
        matched = 0
        offenders: list[str] = []
        for node in _ast.walk(tree):
            if not (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute)
                    and node.func.attr == "build_index"):
                continue
            matched += 1
            if not any(lo <= node.lineno <= hi for lo, hi in guard_spans):
                offenders.append(f"graph_query.py:{node.lineno}")
        self.assertGreaterEqual(
            matched, 1, "no in-process build_index( call found in graph_query.py — the AST walk broke",
        )
        self.assertGreaterEqual(
            len(guard_spans), 1,
            "no stdout-isolation `with` block found in graph_query.py — the AST walk broke or the "
            "wrapper was removed",
        )
        self.assertEqual(
            offenders, [],
            "in-process build_index calls must be lexically inside a `with cli_stdio.isolated_stdout_fd(), "
            "contextlib.redirect_stdout(sys.stderr):` block so the graph auto-rebuild cannot write to the "
            "MCP JSON-RPC stdout channel:\n" + "\n".join(offenders),
        )

    def test_indexer_walk_repo_prints_route_to_stderr(self):
        """``indexer.walk_repo`` runs in-process from the MCP server (navigation tools + index-health);
        every ``print()`` in its body must carry ``file=`` (routed to stderr) so it cannot corrupt the
        JSON-RPC stdout channel."""
        import ast as _ast

        src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        tree = _ast.parse(src)
        walk_fn = next(
            (fn for fn in _ast.walk(tree)
             if isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and fn.name == "walk_repo"),
            None,
        )
        self.assertIsNotNone(walk_fn, "walk_repo not found in indexer.py — the AST walk broke")
        prints = 0
        offenders: list[str] = []
        for node in _ast.walk(walk_fn):
            if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name) and node.func.id == "print":
                prints += 1
                if "file" not in {kw.arg for kw in node.keywords if kw.arg is not None}:
                    offenders.append(f"indexer.py:{node.lineno}")
        self.assertGreaterEqual(
            prints, 1, "walk_repo has no print() — the AST walk broke",
        )
        self.assertEqual(
            offenders, [],
            "walk_repo runs in-process from the MCP server; every print() must route to file=sys.stderr "
            "so it cannot corrupt the JSON-RPC stdout channel:\n" + "\n".join(offenders),
        )


# ---------------------------------------------------------------------------
# Root discovery
# ---------------------------------------------------------------------------

class RootDiscoveryTests(unittest.TestCase):
    """Wave 1p7pm: ``_discover_root`` resolves the served repo cwd-independently, anchored on the
    server script's OWN install location (``parents[3]`` of ``server_impl.py``). Priority:
    override → script-location → marker-validated host env vars → cwd-walkup → fallback. Because the
    REAL ``server_impl.__file__`` points at the live wavefoundry repo (which carries the marker), the
    env/cwd-branch tests patch ``repo_root.__file__`` (the shared discovery module, wave 1t3gt/1t1b3)
    to a markerless tree so those branches run."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self._real_file = self.srv.repo_root.__file__

    def tearDown(self):
        self.srv.repo_root.__file__ = self._real_file
        self.tmp.cleanup()

    def _markerless_script_file(self) -> str:
        """A fake ``server_impl.py`` path whose ``parents[3]`` is a markerless tree (no
        workflow-config.json) so the script-location branch is skipped and env/cwd can be tested."""
        bare = self.root / "bare-tree"
        scripts = bare / ".wavefoundry" / "framework" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        return str(scripts / "repo_root.py")

    def test_override_path_used(self):
        _make_repo(self.root)
        result = self.srv._discover_root(override=str(self.root))
        self.assertEqual(result, self.root.resolve())

    def test_script_location_wins_independent_of_cwd(self):
        # server_impl.py at <repo>/.wavefoundry/framework/scripts/ → parents[3] is the repo; the
        # marker there makes it authoritative regardless of cwd / env.
        repo = self.root / "served-repo"
        scripts = repo / ".wavefoundry" / "framework" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        _make_repo(repo)  # marker at <repo>/docs/workflow-config.json
        elsewhere = self.root / "some" / "other" / "cwd"
        elsewhere.mkdir(parents=True, exist_ok=True)
        self.srv.repo_root.__file__ = str(scripts / "repo_root.py")
        with patch("pathlib.Path.cwd", return_value=elsewhere), \
             patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(elsewhere), "PROJECT_ROOT": str(elsewhere)}, clear=False):
            result = self.srv._discover_root()
        self.assertEqual(result, repo.resolve())

    def test_claude_project_dir_used_only_when_marker_present(self):
        # script-location markerless → fall through to env vars; CLAUDE_PROJECT_DIR is honored ONLY
        # when it carries the marker (a stray var must not mis-root us).
        self.srv.repo_root.__file__ = self._markerless_script_file()
        # A markerless env-var target + a markerless cwd (fully isolated subtree) → the stray var is
        # ignored; the result is NOT the stray path.
        stray = self.root / "stray-no-marker"
        stray.mkdir(parents=True, exist_ok=True)
        isolated_cwd = self.root / "bare-tree" / "deep" / "cwd"  # under bare-tree (no marker anywhere up)
        isolated_cwd.mkdir(parents=True, exist_ok=True)
        with patch("pathlib.Path.cwd", return_value=isolated_cwd), \
             patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(stray)}, clear=False):
            os.environ.pop("PROJECT_ROOT", None)
            os.environ.pop("REPO_ROOT", None)
            self.assertNotEqual(self.srv._discover_root(), stray.resolve())
        # With the marker, CLAUDE_PROJECT_DIR wins.
        marked = self.root / "claude-target"
        _make_repo(marked)
        with patch("pathlib.Path.cwd", return_value=isolated_cwd), \
             patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(marked)}, clear=False):
            os.environ.pop("PROJECT_ROOT", None)
            os.environ.pop("REPO_ROOT", None)
            self.assertEqual(self.srv._discover_root(), marked.resolve())

    def test_env_var_project_root(self):
        self.srv.repo_root.__file__ = self._markerless_script_file()
        _make_repo(self.root)
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.root)}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            os.environ.pop("REPO_ROOT", None)
            result = self.srv._discover_root()
        self.assertEqual(result, self.root.resolve())

    def test_falls_back_to_cwd_when_no_config(self):
        self.srv.repo_root.__file__ = self._markerless_script_file()
        _make_repo(self.root)  # cwd carries the marker
        with patch("pathlib.Path.cwd", return_value=self.root), \
             patch.dict("os.environ", {}, clear=False):
            for k in ("CLAUDE_PROJECT_DIR", "PROJECT_ROOT", "REPO_ROOT"):
                os.environ.pop(k, None)
            result = self.srv._discover_root()
        self.assertEqual(result, self.root.resolve())


class GuidedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv

    def test_first_party_prefix_helper_flags_violations(self):
        viol = self.srv.first_party_tool_names_violating_prefix(["wf_help", "bad_name", "docs_search"])
        self.assertEqual(viol, ["bad_name"])

    def test_resolve_path_under_root_accepts_relative_inside_repo(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = _make_repo(Path(self.tmp.name))
        try:
            (root / "docs" / "foo.md").write_text("x", encoding="utf-8")
            path, err = self.srv.resolve_path_under_root(root, "docs/foo.md")
            self.assertIsNone(err)
            assert path is not None
            self.assertTrue(path.is_file())
        finally:
            self.tmp.cleanup()

    def test_resolve_path_under_root_rejects_parent_escape(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = _make_repo(Path(self.tmp.name))
        try:
            path, err = self.srv.resolve_path_under_root(root, "../../../etc/passwd")
            self.assertIsNone(path)
            assert err is not None
            self.assertEqual(err["code"], "path_outside_allowed_roots")
        finally:
            self.tmp.cleanup()

    def test_docs_search_rejects_invalid_kind(self):
        index = MagicMock()
        result = self.srv.docs_search_response(index, "anything", "not-a-valid-kind")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_arguments")
        index.search_docs.assert_not_called()

    def test_docs_search_normalizes_kind_case(self):
        index = MagicMock()
        index.search_docs.return_value = ([], False)
        self.srv.docs_search_response(index, "q", "Doc")
        index.search_docs.assert_called_with("q", kind="doc", top_n=7, tags=None)

    def test_wf_help_catalog_is_browseable(self):
        self.srv._cached_help_catalog_json.cache_clear()
        result = self.srv.wf_help_response()
        self.assertEqual(result["status"], "ok")
        self.assertIn("core_tools", result["data"])
        self.assertIn("workflows", result["data"])
        self.assertIn("wf_help", result["data"]["core_tools"])
        self.assertIn("wf_server_info", result["data"]["core_tools"])
        self.assertIn("wf_map", result["data"]["core_tools"])
        self.assertIn("server_identity", result["data"]["workflows"])

    def test_wf_server_info_returns_repo_identity(self):
        tmp = tempfile.TemporaryDirectory()
        runner = load_thin_runner()
        saved = (self.srv._runner_version, list(self.srv._runner_files))
        # Inject the real capture-at-launch state the thin runner records at build time
        # (wave 1u2b0): the launch identity hash plus the un-reloadable runner file set.
        self.srv.set_server_runner_version(
            runner.SERVER_RUNNER_VERSION, runner_files=runner.SERVER_RUNNER_FILES
        )
        try:
            root = _make_repo(Path(tmp.name) / "wave_foundry")
            result = self.srv.wf_server_info_response(root)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["data"]["repo_root"], str(root.resolve()))
            self.assertEqual(result["data"]["repo_name"], root.name)
            self.assertEqual(result["data"]["project_slug"], "wave-foundry")
            self.assertNotIn("codex_server_name", result["data"])
            self.assertIn("framework_version", result["data"])
            self.assertIn("server_runner_version", result["data"])
            self.assertIn("server_impl_version", result["data"])
            self.assertIn("impl_matches_disk", result["data"])
            self.assertEqual(result["data"]["server_runner_version"], runner.SERVER_RUNNER_VERSION)
            self.assertEqual(result["data"]["server_impl_version"], self.srv.SERVER_IMPL_VERSION)
            # Runner files unchanged on disk: the query-time hash matches launch, not stale.
            self.assertEqual(result["data"]["runner_disk_identity"], runner.SERVER_RUNNER_VERSION)
            self.assertIs(result["data"]["runner_stale"], False)
            self.assertEqual(result["next_tools"], ["wf_current_wave", "wf_help"])
        finally:
            self.srv.set_server_runner_version(saved[0], runner_files=saved[1])
            tmp.cleanup()

    def test_ensure_no_extra_args_returns_envelope(self):
        err = self.srv._ensure_no_extra_args("docs_search", {"extra": 1})
        assert err is not None
        self.assertEqual(err["status"], "error")
        self.assertEqual(err["diagnostics"][0]["code"], "unknown_arguments")

    def test_wf_help_unknown_goal_returns_catalog_and_diagnostic(self):
        result = self.srv.wf_help_response("not-a-real-goal")
        self.assertEqual(result["status"], "ok")
        self.assertIn("workflows", result["data"])
        self.assertEqual(result["diagnostics"][0]["code"], "unknown_goal")

    def test_docs_search_response_includes_result_id_and_trust_label(self):
        index = MagicMock()
        index.search_docs.return_value = ([{
            "id": "chunk-1",
            "path": ".wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md",
            "kind": "seed",
            "section": "Install",
            "lines": [1, 10],
            "text": "install seed body",
            "score": 0.99,
        }], False)

        result = self.srv.docs_search_response(index, "install", "seed")

        self.assertEqual(result["status"], "ok")
        entry = result["data"]["results"][0]
        self.assertEqual(entry["trust_label"], self.srv.TRUSTED_FRAMEWORK)
        self.assertTrue(entry["result_id"].startswith("doc:"))

    def test_docs_search_falls_back_when_semantic_model_unavailable_offline(self):
        # docs_health() is NOT called on the search hot path; fallback is exception-driven.
        index = MagicMock()
        index.search_docs.side_effect = self.srv.SemanticModelUnavailableOfflineError("offline model missing")
        index.search_docs_lexical.return_value = [{
            "id": "chunk-1",
            "path": "docs/plans/129nj.md",
            "kind": "doc",
            "section": "Rationale",
            "lines": [1, 5],
            "text": "agent catalog expansion",
            "score": 3.0,
        }]

        # 1seaq: model-unavailable with NO published epoch → live walk (the
        # FTS fallback requires a captured complete epoch).
        result = self.srv.docs_search_response(index, "agent catalog", "doc", epoch_state=None)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "live_fallback")
        self.assertEqual(result["data"]["fallback_reason"], "store_absent")
        index.search_docs_lexical.assert_called_once_with("agent catalog", kind="doc", top_n=7, tags=None)
        index.docs_health.assert_not_called()

    def test_docs_search_calls_semantic_search_directly_without_health_preflight(self):
        # docs_health() must not be called on the search hot path regardless of index state.
        index = MagicMock()
        index.search_docs.return_value = ([{
            "id": "chunk-1",
            "path": "docs/plans/129nj.md",
            "kind": "doc",
            "section": "Rationale",
            "lines": [1, 5],
            "text": "agent catalog expansion",
            "score": 0.95,
        }], False)

        result = self.srv.docs_search_response(index, "agent catalog", "doc")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "semantic")
        index.search_docs.assert_called_once_with("agent catalog", kind="doc", top_n=7, tags=None)
        index.docs_health.assert_not_called()

    def test_docs_search_live_walk_on_index_not_ready_without_store(self):
        # 1seaq state table: IndexNotReadyError with NO published epoch
        # (store absent) → the live-filesystem walk, honestly labeled.
        index = MagicMock()
        index.search_docs.side_effect = self.srv.IndexNotReadyError("index missing")
        index.search_docs_lexical.return_value = [{
            "id": "chunk-1",
            "path": "docs/plans/129nj.md",
            "kind": "doc",
            "section": "Rationale",
            "lines": [1, 5],
            "text": "agent catalog expansion",
            "score": 2.0,
        }]

        result = self.srv.docs_search_response(index, "agent catalog", "doc", epoch_state=None)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "live_fallback")
        self.assertEqual(result["data"]["fallback_reason"], "store_absent")
        index.search_docs_lexical.assert_called_once_with("agent catalog", kind="doc", top_n=7, tags=None)
        index.docs_health.assert_not_called()

    def test_docs_search_live_walk_on_building_epoch(self):
        # 1seaq state table: a stable building/interrupted epoch → live walk
        # with fallback_reason index_not_ready (no published FTS to serve).
        index = MagicMock()
        index.search_docs.side_effect = self.srv.IndexNotReadyError("mid-build")
        index.search_docs_lexical.return_value = []
        result = self.srv.docs_search_response(
            index, "agent catalog", "doc", epoch_state=("attempt-a", "building", 3)
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["search_mode"], "live_fallback")
        self.assertEqual(result["data"]["fallback_reason"], "index_not_ready")

    def test_code_search_response_handles_index_not_ready(self):
        index = MagicMock()
        index.search_code.side_effect = self.srv.IndexNotReadyError("missing code index")

        result = self.srv.code_search_response(index, "build index", "python")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")


class PromptCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wf_get_prompt_uses_prompt_cache(self):
        prompts = self.root / "docs" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (prompts / "cached-prompt.md").write_text("# Cached\n\nHello.\n", encoding="utf-8")
        cache = self.srv.McpRepoCache(self.root)
        with patch.object(self.srv, "get_prompt", wraps=self.srv.get_prompt) as gp:
            self.srv.wf_get_prompt_response(self.root, "cached-prompt", cache=cache)
            self.srv.wf_get_prompt_response(self.root, "cached-prompt", cache=cache)
        self.assertEqual(gp.call_count, 1)


class AutoLintAtMcpGatesTests(unittest.TestCase):
    """Wave 1p3dk / 1p3dq: every write-side wave MCP tool returns a `lint`
    field in its response describing the post-write docs-lint state. Agents
    no longer have to manually run `wf_validate_docs` between gate calls."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        lifecycle = self.srv._lifecycle_module()
        lifecycle._last_assigned_prefix = None

    def tearDown(self):
        self.tmp.cleanup()
        lifecycle = self.srv._lifecycle_module()
        lifecycle._last_assigned_prefix = None

    def test_helper_shape(self):
        """AC-1: `_run_post_write_lint` returns {clean, error_count,
        warning_count, first_errors} with `first_errors` capped at 5."""
        lint = self.srv._run_post_write_lint(self.root)
        self.assertIn("clean", lint)
        self.assertIn("error_count", lint)
        self.assertIn("warning_count", lint)
        self.assertIn("first_errors", lint)
        self.assertIsInstance(lint["first_errors"], list)
        self.assertLessEqual(len(lint["first_errors"]), 5,
            "first_errors must be capped at 5 per AC-5")

    def test_fresh_wave_is_lint_clean_at_creation(self):
        """Wave 1t3gt (1t3gu) AC-1: a freshly scaffolded wave.md passes docs-lint with
        zero errors at creation — no manual repair of generated structure."""
        result = self.srv.wf_create_wave_response(self.root, "scaffold-clean", mode="create")
        self.assertEqual(result["status"], "ok")
        lint = result["data"]["lint"]
        self.assertEqual(lint["error_count"], 0, lint["first_errors"])

    def test_fresh_wave_stays_lint_clean_after_first_admission(self):
        """Wave 1t3gt (1t3gu) AC-2: the scaffold stays lint-clean once a planned change
        is admitted (the non-terminal state every new wave passes through — this is
        where the Watchpoints placeholder marker check fires)."""
        created = self.srv.wf_create_wave_response(self.root, "scaffold-admit", mode="create")
        wave_id = created["data"]["wave_id"]
        change = self.srv._change_create_response(self.root, "enh", "scaffold-child", mode="create")
        change_id = change["data"]["change_id"]
        admitted = self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(admitted["status"], "ok")
        admitted_doc = self.root / admitted["data"]["target_path"]
        self.assertIn(f"Wave: {wave_id}", admitted_doc.read_text(encoding="utf-8"))
        lint = admitted["data"]["lint"]
        self.assertEqual(lint["error_count"], 0, lint["first_errors"])

    def test_scaffold_projection_sections_come_from_canonical_renderers(self):
        """Wave 1t3gt (1t3gu) AC-3: the scaffold renders projection-owned sections via
        the canonical renderers, with no hardcoded review-status markup inline."""
        import inspect
        src = inspect.getsource(self.srv.create_wave)
        self.assertIn("render_review_evidence_projection", src)
        self.assertIn("render_review_status_projection", src)
        self.assertNotIn("wave:review-status begin", src)

    def test_create_wave_apply_includes_lint(self):
        """AC-2: wf_create_wave(apply) response carries the lint state."""
        result = self.srv.wf_create_wave_response(
            self.root, "lint-test", mode="create",
        )
        self.assertIn("lint", result["data"], "apply response must include `lint`")
        lint = result["data"]["lint"]
        self.assertIn("clean", lint)

    def test_create_wave_dry_run_omits_lint(self):
        """AC-3: dry_run responses do NOT include the lint field — no writes
        occurred so the lint state is unchanged from pre-call."""
        result = self.srv.wf_create_wave_response(
            self.root, "dry-test", mode="dry_run",
        )
        self.assertNotIn("lint", result["data"],
            "dry_run response must NOT include `lint`")

    def test_change_create_apply_includes_lint(self):
        """AC-2 parallel: change-doc creation via `wf_new_*` includes lint."""
        result = self.srv._change_create_response(
            self.root, "enh", "lint-included", mode="create",
        )
        self.assertIn("lint", result["data"])

    def test_lint_failure_does_not_change_tool_status(self):
        """AC-4: lint state is decoupled from tool status. A tool can succeed
        structurally while the docs gate reports failures."""
        from unittest.mock import patch

        def fake_lint(_root):
            return {
                "clean": False, "error_count": 3, "warning_count": 1,
                "first_errors": ["seeded failure 1", "seeded failure 2", "seeded failure 3"],
            }

        with patch.object(self.srv, "_run_post_write_lint", side_effect=fake_lint):
            result = self.srv.wf_create_wave_response(
                self.root, "fake-fail", mode="create",
            )

        self.assertEqual(result["status"], "ok",
            "tool status must remain `ok` even when lint reports failures")
        self.assertFalse(result["data"]["lint"]["clean"])
        self.assertEqual(result["data"]["lint"]["error_count"], 3)

    def test_lint_error_count_caps_first_errors_at_5(self):
        """AC-5: first_errors is capped at 5 to keep response size bounded."""
        from unittest.mock import patch

        def fake_validate(_root):
            return {
                "passed": False,
                "errors": [f"error {i}" for i in range(20)],
                "warnings": [],
            }

        with patch.object(self.srv, "run_validate_changed", side_effect=fake_validate):
            lint = self.srv._run_post_write_lint(self.root)

        self.assertEqual(lint["error_count"], 20,
            "error_count must reflect TRUE total, not the capped list")
        self.assertEqual(len(lint["first_errors"]), 5,
            "first_errors must be capped at 5")

    def test_lint_helper_isolates_failures(self):
        """The integration must never break the tool — a lint exception is
        captured into `first_errors` with `clean: None`."""
        from unittest.mock import patch

        def bad_validate(_root):
            raise RuntimeError("simulated lint crash")

        with patch.object(self.srv, "run_validate_changed", side_effect=bad_validate):
            lint = self.srv._run_post_write_lint(self.root)

        self.assertIsNone(lint["clean"], "crash → clean is None")
        self.assertEqual(lint["error_count"], -1)
        self.assertTrue(any("RuntimeError" in e for e in lint["first_errors"]))

    def test_lint_skipped_on_error_envelope(self):
        """`_attach_lint_to_response` does not add lint to error responses —
        the tool didn't perform a write, so reporting post-write state is
        misleading."""
        envelope = self.srv._response("error", {"sentinel": True})
        result = self.srv._attach_lint_to_response(envelope, self.root, "create")
        self.assertNotIn("lint", result["data"])


class PostWriteLintIncrementalTests(unittest.TestCase):
    """Wave 1p9pe / 1p9p8: the ADVISORY post-write lint attachment runs the cheap
    incremental changed-set scan (`run_validate_changed`, hook timeout bound) while
    the six full-corpus `run_validate` lifecycle gates (wf_audit, wf_validate_docs,
    wf_audit_install, wf_prepare_wave, wf_review_wave, wf_close_wave) stay unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_docs_lint_config(self, **docs_lint) -> None:
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"docs_lint": docs_lint}), encoding="utf-8",
        )

    def _mock_run(self, returncode: int = 0, stdout: str = "docs-lint: ok\n", stderr: str = ""):
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    # --- AC-1: the post-write path is incremental, never the full corpus ---------------------------

    def test_post_write_lint_spawns_changed_scan_and_never_full(self):
        """AC-1: `_run_post_write_lint` spawns docs_lint with `--changed` and does NOT
        route through the full-corpus `run_validate` (patched to fail loudly if hit)."""
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=self._mock_run()) as run, \
             patch.object(self.srv, "run_validate",
                          side_effect=AssertionError("full-corpus run_validate must not run on the post-write path")):
            lint = self.srv._run_post_write_lint(self.root)
        self.assertTrue(lint["clean"])
        self.assertEqual(run.call_count, 1, "exactly one docs_lint spawn")
        cmd = run.call_args.args[0]
        self.assertIn("--changed", cmd, f"post-write argv must include --changed: {cmd}")
        self.assertIn("docs_lint.py", cmd[1])

    # --- AC-2: bounded by the hook knob, not the full-scan knob ------------------------------------

    def test_post_write_lint_bounded_by_hook_timeout_not_full_scan_knob(self):
        """AC-2: the incremental scan forwards `docs_lint.hook_timeout_seconds` as the
        subprocess timeout — even when the full-scan knob is set to a different value."""
        self._write_docs_lint_config(hook_timeout_seconds=77, full_scan_timeout_seconds=555)
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=self._mock_run()) as run:
            self.srv.run_validate_changed(self.root)
        self.assertEqual(run.call_args.kwargs.get("timeout"), 77.0)

    def test_post_write_lint_hook_timeout_defaults_to_120(self):
        """AC-2: absent config, the hook knob's 120s default applies (via
        indexer.docs_lint_hook_timeout_seconds), not the 300s full-scan default."""
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=self._mock_run()) as run:
            self.srv.run_validate_changed(self.root)
        self.assertEqual(run.call_args.kwargs.get("timeout"), 120.0)
        self.assertNotEqual(
            run.call_args.kwargs.get("timeout"), self.srv.DOCS_LINT_FULL_SCAN_TIMEOUT_DEFAULT,
        )

    # --- AC-3: every one of the six lifecycle gates stays full-corpus ------------------------------

    def test_all_six_lifecycle_gates_route_through_full_run_validate(self):
        """AC-3: each of the six gate functions calls full-corpus `run_validate(root)`
        and none uses the incremental helper — a partial rescope leak into ANY gate fails."""
        gate_funcs = [
            self.srv.wf_audit_response,
            self.srv.wf_validate_docs_response,
            self.srv.wf_audit_install_response,
            self.srv.wf_prepare_wave_response,
            self.srv.wf_review_wave_response,
            self.srv.wf_close_wave_response,
        ]
        for func in gate_funcs:
            src = inspect.getsource(func)
            self.assertRegex(
                src, r"\brun_validate\(root\)",
                f"{func.__name__} must call the full-corpus run_validate",
            )
            self.assertNotIn(
                "run_validate_changed(", src,
                f"{func.__name__} must NOT be rescoped to the incremental scan",
            )

    def test_post_write_helper_is_sole_incremental_caller(self):
        """AC-3: `_run_post_write_lint` is the ONLY `run_validate_changed` caller, and
        `run_validate_changed` is the only site spawning the `--changed` argv."""
        module_src = Path(self.srv.__file__).read_text(encoding="utf-8")
        calls = re.findall(r"(?<!def )run_validate_changed\(", module_src)
        self.assertEqual(
            len(calls), 1,
            "exactly one run_validate_changed call site (the post-write helper) is allowed",
        )
        self.assertIn(
            "run_validate_changed(",
            inspect.getsource(self.srv._run_post_write_lint),
            "the single incremental call site must be _run_post_write_lint",
        )
        self.assertEqual(
            module_src.count('"--changed"'), 1,
            "the --changed argv literal must appear only in run_validate_changed",
        )
        self.assertIn('"--changed"', inspect.getsource(self.srv.run_validate_changed))

    def test_wf_validate_docs_gate_uses_full_scan_behaviorally(self):
        """AC-3 (behavioral): the wf_validate_docs gate calls run_validate, and the
        incremental helper (patched to fail loudly) is never consulted for the gate."""
        passing = {"passed": True, "errors": [], "warnings": [], "output": ""}
        with patch.object(self.srv, "run_validate", return_value=passing) as full, \
             patch.object(self.srv, "run_validate_changed",
                          side_effect=AssertionError("gate must not use the incremental scan")):
            result = self.srv.wf_validate_docs_response(self.root)
        self.assertEqual(full.call_count, 1)
        self.assertEqual(result["status"], "ok")

    # --- AC-4: unchanged response shape + degradation contract -------------------------------------

    def test_post_write_lint_shape_on_clean_changed_set(self):
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=self._mock_run()):
            lint = self.srv._run_post_write_lint(self.root)
        self.assertEqual(
            lint,
            {
                "clean": True, "error_count": 0, "warning_count": 0, "first_errors": [],
                # Review-fix: the additive `mode` key — a spawn that printed the normal
                # summary line reports "incremental".
                "mode": "incremental",
            },
        )

    def test_post_write_lint_surfaces_changed_doc_error(self):
        mock = self._mock_run(returncode=1, stdout="",
                              stderr="ERROR: docs/plans/x.md: broken link\nWARNING: stale date\n")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=mock):
            lint = self.srv._run_post_write_lint(self.root)
        self.assertFalse(lint["clean"])
        self.assertEqual(lint["error_count"], 1)
        self.assertEqual(lint["warning_count"], 1)
        self.assertIn("ERROR: docs/plans/x.md: broken link", lint["first_errors"])

    def test_post_write_lint_timeout_degrades_legibly(self):
        """AC-4: a hung incremental scan degrades to the structured contract naming the
        hook config key — no raised exception, and the envelope shape is preserved."""
        self._write_docs_lint_config(hook_timeout_seconds=77)

        def _timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="docs_lint", timeout=77)

        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=_timeout):
            lint = self.srv._run_post_write_lint(self.root)
        self.assertFalse(lint["clean"])
        self.assertEqual(
            sorted(lint), ["clean", "error_count", "first_errors", "mode", "warning_count"],
        )
        self.assertTrue(
            any("docs_lint.hook_timeout_seconds" in e for e in lint["first_errors"]),
            f"timeout error must name the hook config key: {lint['first_errors']}",
        )
        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=_timeout):
            result = self.srv.run_validate_changed(self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(any("77" in e for e in result["errors"]),
                        f"timeout error must name the elapsed bound: {result['errors']}")

    def test_post_write_lint_empty_changed_set_on_non_git_root_reports_clean(self):
        """AC-4 (end-to-end, real spawn): on a non-git skeleton the changed set is empty,
        so the incremental scan is a clean no-op — even though this same skeleton FAILS
        the full-corpus scan (missing required files), proving corpus checks were skipped.
        Review-fix: the attached summary carries `mode: "skipped"` so the checked-nothing
        no-op is distinguishable from checked-and-clean."""
        lint = self.srv._run_post_write_lint(self.root)
        self.assertTrue(lint["clean"], lint)
        self.assertEqual(lint["error_count"], 0)
        self.assertEqual(lint["first_errors"], [])
        self.assertEqual(lint["mode"], "skipped", lint)
        result = self.srv.run_validate_changed(self.root)
        self.assertEqual(result["mode"], "skipped")
        self.assertIn("docs-lint: skipped (no git changed-set available)", result["output"])


@unittest.skipUnless(shutil.which("git"), "git not available")
class PostWriteLintIncrementalGitBehaviorTests(unittest.TestCase):
    """Wave 1p9pe / 1p9p8 (readiness anti-vacuity note): fixture-scale REAL-behavior
    evidence, no argv mocking — the incremental post-write scan demonstrably does not
    run the full corpus, surfaces a defect in a changed doc, and a changed config file
    still triggers the CLI's internal full-lint fallback (AC-5)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self._git("init", "-q")
        self._git("add", "-A")
        self._git("-c", "user.email=wave@test", "-c", "user.name=wave", "commit", "-qm", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True,
        )

    def test_incremental_skips_corpus_defects_the_full_scan_reports(self):
        """The same tree, both scans: full-corpus FAILS on corpus-wide defects (the
        skeleton misses required files) while the incremental scan with an EMPTY
        changed set passes clean — direct proof the post-write path does not run
        the full corpus."""
        full = self.srv.run_validate(self.root)
        self.assertFalse(full["passed"], "precondition: the skeleton must fail the full scan")
        self.assertTrue(any("missing required" in e for e in full["errors"]), full["errors"])
        inc = self.srv.run_validate_changed(self.root)
        self.assertTrue(inc["passed"], f"empty changed set must be a clean no-op: {inc['output']}")
        lint = self.srv._run_post_write_lint(self.root)
        self.assertTrue(lint["clean"], lint)

    def test_changed_doc_defect_surfaces_through_post_write_lint(self):
        """A defective doc in the working tree (untracked → in the changed set) is
        caught by the incremental per-file validators and lands in first_errors."""
        bad = self.root / "docs" / "plans" / "bad-link.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("# Bad\n\n[missing](./no-such-file.md)\n", encoding="utf-8")
        lint = self.srv._run_post_write_lint(self.root)
        self.assertFalse(lint["clean"], lint)
        self.assertGreater(lint["error_count"], 0)
        self.assertTrue(
            any("bad-link.md" in e for e in lint["first_errors"]),
            f"the changed doc's defect must surface: {lint['first_errors']}",
        )

    def test_changed_config_file_falls_back_to_full_lint(self):
        """AC-5: a changed config file (docs/workflow-config.json) makes the CLI fall
        back to the FULL lint inside the incremental invocation — the corpus-wide
        defects the empty-changed-set scan skipped are now reported again. Review-fix:
        the result carries `mode: "full-fallback"` (vs `"incremental"` beforehand)."""
        clean = self.srv.run_validate_changed(self.root)
        self.assertTrue(clean["passed"], "precondition: clean incremental scan before the config change")
        self.assertEqual(clean["mode"], "incremental", clean)
        cfg = self.root / "docs" / "workflow-config.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data["docs_lint"] = {"hook_timeout_seconds": 90}
        cfg.write_text(json.dumps(data), encoding="utf-8")
        result = self.srv.run_validate_changed(self.root)
        self.assertFalse(result["passed"], "config change must trigger the full-lint fallback")
        self.assertTrue(
            any("missing required" in e for e in result["errors"]),
            f"full-lint fallback must report corpus-wide defects: {result['errors']}",
        )
        self.assertEqual(result["mode"], "full-fallback", result["mode"])

    # --- Review-fix (1p9pe follow-up hardening): timeout-knob crossover ----------------------------

    def _write_docs_lint_config(self, **docs_lint) -> None:
        cfg = self.root / "docs" / "workflow-config.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data["docs_lint"] = docs_lint
        cfg.write_text(json.dumps(data), encoding="utf-8")

    def test_predicted_full_fallback_uses_full_scan_timeout_knob(self):
        """A trigger file (docs/workflow-config.json) in the git changed set means the
        `--changed` invocation will run the FULL corpus inside the CLI, so the subprocess
        must be bounded by `docs_lint.full_scan_timeout_seconds` — not the 120s hook knob
        the incremental path uses (the pre-fix crossover)."""
        self._write_docs_lint_config(hook_timeout_seconds=77, full_scan_timeout_seconds=555)
        # The config write above IS the changed trigger file (unstaged in the fixture repo).
        self.assertTrue(self.srv._predict_incremental_full_fallback(self.root))
        mock_result = MagicMock(returncode=0, stdout="docs-lint: ok\n", stderr="")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=mock_result) as run:
            result = self.srv.run_validate_changed(self.root)
        self.assertEqual(run.call_args.kwargs.get("timeout"), 555.0,
                         "predicted fallback must use the full-scan knob")
        self.assertEqual(result["mode"], "full-fallback")

    def test_predicted_full_fallback_timeout_message_names_full_scan_knob(self):
        self._write_docs_lint_config(hook_timeout_seconds=77, full_scan_timeout_seconds=555)

        def _timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="docs_lint", timeout=555)

        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=_timeout):
            result = self.srv.run_validate_changed(self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("docs_lint.full_scan_timeout_seconds" in e for e in result["errors"]),
            f"the fallback timeout must name the full-scan knob: {result['errors']}",
        )
        self.assertFalse(
            any("docs_lint.hook_timeout_seconds" in e for e in result["errors"]),
            "the fallback timeout must NOT point the operator at the hook knob",
        )

    def test_normal_changed_doc_uses_hook_timeout_knob(self):
        """With the config committed (clean) and only a doc changed, no fallback is
        predicted and the hook knob bounds the scan."""
        self._write_docs_lint_config(hook_timeout_seconds=77, full_scan_timeout_seconds=555)
        self._git("add", "-A")
        self._git("-c", "user.email=wave@test", "-c", "user.name=wave", "commit", "-qm", "config")
        doc = self.root / "docs" / "plans" / "note.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("# Note\n", encoding="utf-8")
        self.assertFalse(self.srv._predict_incremental_full_fallback(self.root))
        mock_result = MagicMock(returncode=0, stdout="docs-lint: ok\n", stderr="")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=mock_result) as run:
            result = self.srv.run_validate_changed(self.root)
        self.assertEqual(run.call_args.kwargs.get("timeout"), 77.0,
                         "the normal incremental path must keep the hook knob")
        self.assertEqual(result["mode"], "incremental")


class McpRepoCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_plans_returns_same_cached_list_when_fingerprint_unchanged(self):
        cache = self.srv.McpRepoCache(self.root)
        plans_dir = self.root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        (plans_dir / "1000-feat x.md").write_text(
            "# X\n\nChange ID: `1000-feat x`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        a = cache.list_plans_cached()
        b = cache.list_plans_cached()
        self.assertIs(a, b)

    def test_list_plans_cache_refreshes_when_plan_files_change(self):
        cache = self.srv.McpRepoCache(self.root)
        plans_dir = self.root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        (plans_dir / "1000-feat x.md").write_text(
            "# X\n\nChange ID: `1000-feat x`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        first = cache.list_plans_cached()
        (plans_dir / "1001-feat y.md").write_text(
            "# Y\n\nChange ID: `1001-feat y`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        second = cache.list_plans_cached()
        self.assertGreater(len(second), len(first))

    def test_invalidate_clears_plans_cache_identity(self):
        cache = self.srv.McpRepoCache(self.root)
        plans_dir = self.root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        (plans_dir / "1000-feat x.md").write_text(
            "# X\n\nChange ID: `1000-feat x`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        a = cache.list_plans_cached()
        cache.invalidate()
        b = cache.list_plans_cached()
        self.assertIsNot(a, b)
        self.assertEqual([p["id"] for p in a], [p["id"] for p in b])


# ---------------------------------------------------------------------------
# _audit_harnessability — type-coverage detection (wave 1p35d / 1p35p)
# ---------------------------------------------------------------------------

class HarnessabilityTypeCoverageJVMTests(unittest.TestCase):
    """Wave 1p35d (1p35p): JVM build files and source files signal type config
    so Spring Boot and other JVM-ecosystem projects no longer false-negative
    as 'no type config detected'. File-presence only — no compiler invocation."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _type_dim(self, root: Path) -> dict:
        return self.srv._audit_harnessability(root)["dimensions"]["type_coverage"]

    def test_pure_python_repo_reports_no_type_config(self):
        """Regression guard: empty fixture (no JVM, no TS, no Python type config)
        still reports `low` / 'No type configuration files detected'."""
        dim = self._type_dim(self.root)
        self.assertEqual(dim["score"], "low")
        self.assertIn("No type configuration", dim["evidence"])

    def test_maven_pom_xml_counts_as_type_config(self):
        (self.root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("pom.xml", dim["evidence"])

    def test_gradle_build_counts_as_type_config(self):
        (self.root / "build.gradle").write_text("plugins {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("build.gradle", dim["evidence"])

    def test_gradle_kts_counts_as_type_config(self):
        (self.root / "build.gradle.kts").write_text("plugins {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("build.gradle.kts", dim["evidence"])

    def test_java_source_falls_back_to_source_signal(self):
        """When no build file is present, a *.java file alone is enough."""
        src = self.root / "src" / "main" / "java" / "com" / "example"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.java").write_text("class App {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("*.java", dim["evidence"])

    def test_kotlin_source_signals_type_coverage(self):
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "Main.kt").write_text("fun main() {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("*.kt", dim["evidence"])

    def test_scala_source_signals_type_coverage(self):
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "Main.scala").write_text("object Main\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("*.scala", dim["evidence"])

    def test_mixed_jvm_repo_uses_build_file_signal(self):
        """When both a build file and source files are present, build-file
        signal wins (the source-fallback is bounded by `if not jvm_signals`)."""
        (self.root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
        src = self.root / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.java").write_text("class App {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertIn("pom.xml", dim["evidence"])
        # Source-pattern fallback shouldn't fire when a build file is present.
        self.assertNotIn("*.java", dim["evidence"])

    def test_jvm_plus_python_combination_scores_high(self):
        """Two type configs (mypy + JVM) → `high` score per the >=2 rule."""
        (self.root / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")
        (self.root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertEqual(dim["score"], "high")

    def test_groovy_source_signals_type_coverage(self):
        """Wave 1p35d (1p35p enterprise-hardening): Groovy is a JVM language;
        Spring Boot Groovy apps must signal type coverage."""
        src = self.root / "src" / "main" / "groovy"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.groovy").write_text("class App {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("*.groovy", dim["evidence"])

    def test_vendored_java_outside_canonical_root_does_not_signal(self):
        """Wave 1p35d (1p35p enterprise-hardening, C6-DC-2 fix): a vendored 3rd-
        party Java source in a non-canonical location (e.g., `vendor/`,
        `third_party/`, `target/`) must NOT trigger the JVM source-pattern
        fallback. Enterprise monorepos commonly vendor JAR sources; the previous
        unguarded `rglob` false-positived on every one of them."""
        for ignore_dir in ("vendor", "third_party", "node_modules", "target",
                           "build", ".git", ".idea"):
            d = self.root / ignore_dir / "legacy"
            d.mkdir(parents=True, exist_ok=True)
            (d / "VendoredClass.java").write_text("class VendoredClass {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        # No build file, no canonical-root source → no JVM signal at all.
        self.assertEqual(dim["score"], "low")
        self.assertNotIn("*.java", dim["evidence"])

    def test_java_in_unconventional_top_level_root_still_signals(self):
        """An unconventional layout where `src/Main.kt` (no `main/kotlin/`)
        is the only source must still trigger the fallback. The `src` entry
        in `_JVM_CANONICAL_SOURCE_ROOTS` is the catch-all for projects that
        don't follow the Maven/Gradle layout."""
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src" / "Main.kt").write_text("fun main() {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("*.kt", dim["evidence"])

    def test_java_at_repo_root_top_level_still_signals(self):
        """Tiny single-file JVM-flavored repo: `App.java` at repo root with no
        canonical src/ layout. The root-level iterdir-only entry in
        `_JVM_CANONICAL_SOURCE_ROOTS` covers this case."""
        (self.root / "App.java").write_text("class App {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("*.java", dim["evidence"])

    def test_java_at_arbitrary_subdir_does_not_signal(self):
        """Source files in a non-canonical, non-ignored directory (e.g.
        `examples/sample/`) must NOT trigger the fallback. Canonical-root-only
        scope means random Java files in arbitrary tree locations are not
        evidence of a JVM project."""
        odd = self.root / "examples" / "sample"
        odd.mkdir(parents=True, exist_ok=True)
        (odd / "Sample.java").write_text("class Sample {}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertEqual(dim["score"], "low")


# ---------------------------------------------------------------------------
# JVM source-walking helper — direct unit tests for _detect_jvm_source_evidence
# (wave 1p35d / 1p35p enterprise-hardening)
# ---------------------------------------------------------------------------

class JVMSourceEvidenceHelperTests(unittest.TestCase):
    """Direct tests for `_detect_jvm_source_evidence`. The helper is the
    bounded-walk implementation that supersedes the previous `next(root.rglob(...))`
    approach. Exercises walk bounds, ignore-dir handling, and budget enforcement."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_empty_when_no_sources(self):
        self.assertEqual(self.srv._detect_jvm_source_evidence(self.root), [])

    def test_canonical_root_recursive_walk_finds_nested_source(self):
        """Maven layout: `src/main/java/com/example/App.java` (3 levels deep)."""
        deep = self.root / "src" / "main" / "java" / "com" / "example"
        deep.mkdir(parents=True, exist_ok=True)
        (deep / "App.java").write_text("class App {}\n", encoding="utf-8")
        result = self.srv._detect_jvm_source_evidence(self.root)
        self.assertEqual(result, ["*.java"])

    def test_ignore_dirs_inside_canonical_root_are_skipped(self):
        """A `vendor/` dir nested inside `src/` must not be walked, even though
        `src/` is a canonical root."""
        vendored = self.root / "src" / "vendor" / "legacy"
        vendored.mkdir(parents=True, exist_ok=True)
        (vendored / "Vendored.java").write_text("class V {}\n", encoding="utf-8")
        result = self.srv._detect_jvm_source_evidence(self.root)
        # `src/vendor/...` is skipped; `src/` itself contains no source files.
        self.assertEqual(result, [])

    def test_file_budget_cap(self):
        """When the walk visits more than `_JVM_SOURCE_WALK_FILE_BUDGET` files
        without finding a match, it bails. Guards against pathological monorepo
        walks that would otherwise run for seconds."""
        budget = self.srv._JVM_SOURCE_WALK_FILE_BUDGET
        # Plant the source file at a depth that requires walking past the budget.
        canonical = self.root / "src"
        canonical.mkdir(parents=True, exist_ok=True)
        # Pre-populate with budget+10 non-matching files in the canonical root.
        for i in range(budget + 10):
            (canonical / f"junk-{i}.txt").write_text("noise", encoding="utf-8")
        # Now plant a real source. Depending on iteration order it may or may
        # not be found first, but the budget cap must hold the call to a
        # bounded number of filesystem reads regardless.
        (canonical / "real-source.java").write_text("class X {}\n", encoding="utf-8")
        result = self.srv._detect_jvm_source_evidence(self.root)
        # We accept either outcome (found or budget-exhausted) — the contract
        # is that the function returns in bounded time, not that it must find
        # this specific source.
        self.assertIn(result, ([], ["*.java"]))


# ---------------------------------------------------------------------------
# Monorepo workspace detection — _detect_monorepo_subprojects (wave 1p35d / 1p35p)
# ---------------------------------------------------------------------------

class MonorepoDetectionTests(unittest.TestCase):
    """Wave 1p35d (1p35p enterprise-deployment hardening): when the agent's
    CWD is a workspace parent containing multiple sub-projects, harnessability
    must aggregate signals across sub-projects rather than reporting "no type
    config" based on root-only checks. Covers Nx, Lerna, pnpm-workspaces,
    Rush, Bazel (WORKSPACE / WORKSPACE.bazel / MODULE.bazel), Pants, Buck,
    npm/yarn workspaces (`package.json` workspaces field), Cargo workspaces
    (`[workspace]` section), and Maven multi-module parent POMs."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_subproject(self, parent: str, name: str, type_config_file: str | None = None) -> Path:
        sub = self.root / parent / name
        sub.mkdir(parents=True, exist_ok=True)
        if type_config_file:
            (sub / type_config_file).write_text("{}\n", encoding="utf-8")
        return sub

    # -- Negative cases (no marker → no sub-project walk) --

    def test_no_marker_returns_empty(self):
        """Single-project repo (no workspace marker) → empty list. Preserves
        single-project behavior; sub-project walking is opt-in via the
        workspace-marker signal."""
        self._seed_subproject("services", "auth", "pom.xml")
        self.assertEqual(self.srv._detect_monorepo_subprojects(self.root), [])

    def test_package_json_without_workspaces_field_no_walk(self):
        """A plain `package.json` without `"workspaces"` does NOT signal monorepo."""
        (self.root / "package.json").write_text(
            '{"name": "single-project"}', encoding="utf-8"
        )
        self._seed_subproject("packages", "app", "package.json")
        self.assertEqual(self.srv._detect_monorepo_subprojects(self.root), [])

    def test_cargo_toml_without_workspace_section_no_walk(self):
        (self.root / "Cargo.toml").write_text(
            '[package]\nname = "single"\n', encoding="utf-8"
        )
        self._seed_subproject("crates", "core", "Cargo.toml")
        self.assertEqual(self.srv._detect_monorepo_subprojects(self.root), [])

    def test_pom_xml_without_modules_no_walk(self):
        """Single-module Maven (no `<modules>` and not packaging=pom) is not a monorepo."""
        (self.root / "pom.xml").write_text(
            "<project><artifactId>single</artifactId></project>\n", encoding="utf-8"
        )
        self._seed_subproject("modules", "core", "pom.xml")
        self.assertEqual(self.srv._detect_monorepo_subprojects(self.root), [])

    # -- Positive cases (marker present → walks sub-project parents) --

    def test_nx_workspace_walks_apps_and_libs(self):
        (self.root / "nx.json").write_text("{}\n", encoding="utf-8")
        self._seed_subproject("apps", "web", "tsconfig.json")
        self._seed_subproject("libs", "common", "tsconfig.json")
        result = self.srv._detect_monorepo_subprojects(self.root)
        names = sorted(p.name for p in result)
        self.assertEqual(names, ["common", "web"])

    def test_lerna_workspace_walks_packages(self):
        (self.root / "lerna.json").write_text("{}\n", encoding="utf-8")
        self._seed_subproject("packages", "ui")
        self._seed_subproject("packages", "core")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), 2)

    def test_pnpm_workspace_yaml(self):
        (self.root / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'packages/*'\n", encoding="utf-8"
        )
        self._seed_subproject("packages", "lib-a")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), 1)

    def test_bazel_workspace_marker(self):
        (self.root / "WORKSPACE").write_text("workspace(name = 'demo')\n", encoding="utf-8")
        self._seed_subproject("services", "auth", "BUILD")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), 1)

    def test_bazel_module_marker(self):
        """MODULE.bazel is the modern Bzlmod replacement for WORKSPACE."""
        (self.root / "MODULE.bazel").write_text("module(name='demo')\n", encoding="utf-8")
        self._seed_subproject("services", "auth")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), 1)

    def test_pants_marker(self):
        (self.root / "pants.toml").write_text("[GLOBAL]\n", encoding="utf-8")
        self._seed_subproject("subprojects", "a")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), 1)

    def test_npm_workspaces_field(self):
        (self.root / "package.json").write_text(
            '{"name": "mono", "workspaces": ["packages/*"]}', encoding="utf-8"
        )
        self._seed_subproject("packages", "a", "package.json")
        self._seed_subproject("packages", "b", "package.json")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), 2)

    def test_cargo_workspace_section(self):
        (self.root / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["crates/*"]\n', encoding="utf-8"
        )
        self._seed_subproject("crates", "core", "Cargo.toml")
        self._seed_subproject("crates", "cli", "Cargo.toml")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), 2)

    def test_maven_multimodule_parent(self):
        """Maven multi-module: `<packaging>pom</packaging>` + `<modules>` block
        at the parent POM. The classic enterprise Java monorepo shape."""
        (self.root / "pom.xml").write_text(
            "<project><packaging>pom</packaging>"
            "<modules><module>service-a</module><module>service-b</module></modules>"
            "</project>\n",
            encoding="utf-8",
        )
        self._seed_subproject("modules", "service-a", "pom.xml")
        self._seed_subproject("modules", "service-b", "pom.xml")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), 2)

    def test_subproject_budget_caps_walk(self):
        (self.root / "nx.json").write_text("{}\n", encoding="utf-8")
        budget = self.srv._MONOREPO_SUBPROJECT_BUDGET
        for i in range(budget + 10):
            self._seed_subproject("packages", f"p{i:03d}")
        result = self.srv._detect_monorepo_subprojects(self.root)
        self.assertEqual(len(result), budget)

    def test_ignore_dirs_inside_subproject_parent_skipped(self):
        """`packages/node_modules/some-dep` must not register as a sub-project."""
        (self.root / "lerna.json").write_text("{}\n", encoding="utf-8")
        self._seed_subproject("packages", "real-app", "package.json")
        # Vendored node_modules inside packages/ — should be skipped per ignore-dirs
        vendored = self.root / "packages" / "node_modules" / "vendored"
        vendored.mkdir(parents=True, exist_ok=True)
        result = self.srv._detect_monorepo_subprojects(self.root)
        names = sorted(p.name for p in result)
        self.assertEqual(names, ["real-app"])


# ---------------------------------------------------------------------------
# Harnessability type-coverage — monorepo aggregation (wave 1p35d / 1p35p)
# ---------------------------------------------------------------------------

class HarnessabilityMonorepoAggregationTests(unittest.TestCase):
    """The high-level harnessability check, when given a monorepo workspace
    root, must report sub-project type-coverage rather than the misleading
    'no type config detected' that root-only checks produce."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _type_dim(self, root: Path) -> dict:
        return self.srv._audit_harnessability(root)["dimensions"]["type_coverage"]

    def test_nx_monorepo_with_typed_subprojects_reports_coverage(self):
        """The bare repo at root has no type config; only sub-project tsconfigs
        exist. Without monorepo support this reports 'low'. With support it
        reports the sub-project signals."""
        (self.root / "nx.json").write_text("{}\n", encoding="utf-8")
        for sub in ("web", "admin"):
            d = self.root / "apps" / sub
            d.mkdir(parents=True, exist_ok=True)
            (d / "tsconfig.json").write_text("{}\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        self.assertIn("monorepo", dim["evidence"])
        self.assertIn("tsconfig.json", dim["evidence"])

    def test_maven_multimodule_aggregates_subproject_poms(self):
        """Enterprise Java monorepo: parent POM at root, child modules under
        `modules/`. Root-only check sees parent POM (already triggers JVM
        signal); sub-project walk should also enrich evidence with module-
        level POMs."""
        (self.root / "pom.xml").write_text(
            "<project><packaging>pom</packaging>"
            "<modules><module>auth</module><module>data</module></modules>"
            "</project>\n",
            encoding="utf-8",
        )
        for svc in ("auth", "data"):
            d = self.root / "modules" / svc
            d.mkdir(parents=True, exist_ok=True)
            (d / "pom.xml").write_text(
                "<project><artifactId>" + svc + "</artifactId></project>\n",
                encoding="utf-8",
            )
        dim = self._type_dim(self.root)
        self.assertEqual(dim["score"], "high")  # JVM root + monorepo evidence ≥2
        self.assertIn("monorepo", dim["evidence"])
        self.assertIn("auth/pom.xml", dim["evidence"])

    def test_mixed_language_monorepo(self):
        """Realistic enterprise monorepo: Nx workspace with TS apps,
        Python services, JVM libs."""
        (self.root / "nx.json").write_text("{}\n", encoding="utf-8")
        d_web = self.root / "apps" / "web"
        d_web.mkdir(parents=True, exist_ok=True)
        (d_web / "tsconfig.json").write_text("{}\n", encoding="utf-8")
        d_etl = self.root / "services" / "etl"
        d_etl.mkdir(parents=True, exist_ok=True)
        (d_etl / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")
        d_lib = self.root / "libs" / "common"
        d_lib.mkdir(parents=True, exist_ok=True)
        (d_lib / "pom.xml").write_text("<project/>\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        self.assertNotEqual(dim["score"], "low")
        # All three sub-project type configs should be in evidence
        for marker in ("tsconfig.json", "mypy.ini", "pom.xml"):
            self.assertIn(marker, dim["evidence"])

    def test_single_project_repo_unchanged_by_monorepo_logic(self):
        """Regression guard: a plain single-project repo (no workspace marker)
        must produce the same evidence string as before the monorepo patch."""
        (self.root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
        dim = self._type_dim(self.root)
        # No `monorepo` label in evidence — single-project path used the
        # root-only check, which DOES list pom.xml directly.
        self.assertNotIn("monorepo", dim["evidence"])
        self.assertIn("pom.xml", dim["evidence"])


# ---------------------------------------------------------------------------
# build_server — tool registration
# ---------------------------------------------------------------------------

class ServerStdioTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_server()
        cls.runner = load_thin_runner()

    def test_configure_stdio_uses_utf8_lf_and_write_through_for_outputs(self):
        class FakeStream:
            def __init__(self):
                self.calls = []

            def reconfigure(self, **kwargs):
                self.calls.append(kwargs)

        fake_stdin = FakeStream()
        fake_stdout = FakeStream()
        fake_stderr = FakeStream()

        with patch.object(self.runner.sys, "stdin", fake_stdin), \
             patch.object(self.runner.sys, "stdout", fake_stdout), \
             patch.object(self.runner.sys, "stderr", fake_stderr):
            self.runner._configure_stdio_for_mcp_transport()

        self.assertEqual(fake_stdin.calls, [{"encoding": "utf-8", "newline": "\n"}])
        self.assertEqual(
            fake_stdout.calls,
            [{"encoding": "utf-8", "newline": "\n", "write_through": True}],
        )
        self.assertEqual(
            fake_stderr.calls,
            [{"encoding": "utf-8", "newline": "\n", "write_through": True}],
        )

    def test_configure_stdio_is_best_effort(self):
        class RejectingStream:
            def reconfigure(self, **kwargs):
                raise ValueError("unsupported")

        with patch.object(self.runner.sys, "stdin", RejectingStream()), \
             patch.object(self.runner.sys, "stdout", RejectingStream()), \
             patch.object(self.runner.sys, "stderr", RejectingStream()):
            self.runner._configure_stdio_for_mcp_transport()

    def test_main_configures_stdio_before_building_server(self):
        events = []

        class FakeMcp:
            def run(self, *, transport):
                events.append(("run", transport))

        def fake_configure():
            events.append("configure")

        def fake_build(root):
            events.append("build")
            return FakeMcp()

        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(self.runner, "_configure_stdio_for_mcp_transport", side_effect=fake_configure), \
             patch.object(self.runner, "build_server", side_effect=fake_build):
            root = _make_repo(Path(tmp))
            result = self.runner.main(["--root", str(root)])

        self.assertEqual(result, 0)
        self.assertEqual(events, ["configure", "build", ("run", "stdio")])


class ServerToolRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_tools_registered(self):
        try:
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        # FastMCP exposes tool names on _tool_manager._tools (or legacy _tools)
        tool_names = self.srv._registered_mcp_tool_names(mcp)
        if not tool_names and hasattr(mcp, "list_tools"):
            import asyncio
            tools = asyncio.run(mcp.list_tools())
            tool_names = {t.name for t in tools}

        expected = {
            "wf_help",
            "wf_server_info",
            "wf_map",
            "wf_create_wave",
            "wf_add_change",
            "wf_remove_change",
            "wf_prepare_wave",
            "wf_pause_wave",
            "wf_review_wave",
            "wf_review_event",
            "wf_reopen_wave",
            "wf_close_wave",
            "index_build_status",
            "docs_search",
            "code_search",
            "seed_get",
            "wf_current_wave",
            "wf_list_waves",
            "wf_list_plans",
            "wf_get_change",
            "wf_get_prompt",
            "wf_open_gate",
            "wf_close_gate",
            "wf_gate_status",
            "wf_new_feature",
            "wf_new_bug",
            "wf_new_enhancement",
            "wf_new_refactor",
            "wf_new_change",
            "wf_new_documentation",
            "wf_new_tech_debt",
            "wf_new_task",
            "wf_new_maintenance",
            "wf_new_operations",
            "wf_validate_docs",
            "wf_garden_docs",
            "wf_sync_surfaces",
            "index_health",
            "index_build",
            "wf_audit",
            "wf_upgrade",
            "wf_upgrade_status",
            "wf_reload_mcp",
            "wf_start_dashboard",
            "wf_open_dashboard",
            "wf_stop_dashboard",
            "wf_restart_dashboard",
            "code_list_files",
            "code_read",
            "code_keyword",
            "code_definition",
            "code_references",
            "wf_get_handoff",
            "wf_set_handoff",
        }
        self.assertTrue(
            expected.issubset(tool_names),
            f"Missing tools: {expected - tool_names}",
        )
        self.assertNotIn("wave_setup_resume_after_memory", tool_names)
        self.assertNotIn("wf_resume_setup_after_memory", tool_names)

    def test_registered_tools_obey_prefix_contract(self):
        try:
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        names = self.srv._registered_mcp_tool_names(mcp)
        viol = self.srv.first_party_tool_names_violating_prefix(names)
        self.assertEqual(viol, [], f"Prefix violations: {viol}")

    def test_agents_available_tools_census_matches_registration(self):
        """The root guide labels this list exhaustive, so keep it executable."""
        try:
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        import re

        repo_root = Path(__file__).resolve().parents[4]
        agents = repo_root.joinpath("AGENTS.md").read_text(encoding="utf-8")
        match = re.search(
            r"\*\*Available tools:\*\*(.*?)(?=\n\n\*\*Graph index:)",
            agents,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "AGENTS.md Available tools block is missing")
        documented = set(re.findall(r"`([a-z][a-z0-9_]*)`", match.group(1)))
        registered = self.srv._registered_mcp_tool_names(mcp)
        self.assertEqual(
            documented,
            registered,
            "AGENTS.md Available tools must exactly match live registration",
        )


class RunnerIdentityTests(unittest.TestCase):
    """Wave 1u2b0 (1u2ay): capture-at-launch runner identity plus tri-state staleness.

    AC-1 test shape (named per the change doc's allowance): injection of the captured
    identity. The launch state the thin runner would record is injected via
    set_server_runner_version over temp COPIES of the real runner files, then the
    on-disk copies are mutated to simulate an upgrade or a development edit; no
    fresh-subprocess MCP probe is needed because the comparison seam is the injected
    (identity, runner_files) pair, which is exactly what server.py records at launch.
    """

    def setUp(self):
        self.srv = load_server()
        self.runner = load_thin_runner()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self._saved = (self.srv._runner_version, list(self.srv._runner_files))

    def tearDown(self):
        self.srv.set_server_runner_version(self._saved[0], runner_files=self._saved[1])
        self.tmp.cleanup()

    def _copied_runner_files(self) -> list[str]:
        copies: list[str] = []
        for src in self.runner.SERVER_RUNNER_FILES:
            dst = Path(self.tmp.name) / Path(src).name
            shutil.copyfile(src, dst)
            copies.append(str(dst))
        return copies

    def test_launch_identity_is_content_hash_not_frozen_literal(self):
        ident = self.runner.SERVER_RUNNER_VERSION
        self.assertRegex(ident, r"^[0-9a-f]{12}$")
        self.assertNotEqual(ident, "1")
        self.assertEqual(
            ident, self.srv.compute_runner_identity(self.runner.SERVER_RUNNER_FILES)
        )

    def test_runner_file_set_covers_server_and_venv_bootstrap(self):
        names = sorted(Path(f).name for f in self.runner.SERVER_RUNNER_FILES)
        self.assertEqual(names, ["server.py", "venv_bootstrap.py"])

    def test_identity_changes_when_either_runner_file_changes(self):
        copies = self._copied_runner_files()
        base = self.srv.compute_runner_identity(copies)
        for target_name in ("server.py", "venv_bootstrap.py"):
            target = Path(next(c for c in copies if c.endswith(target_name)))
            original = target.read_bytes()
            target.write_bytes(original + b"\n# mutated\n")
            self.assertNotEqual(
                self.srv.compute_runner_identity(copies), base, target_name
            )
            target.write_bytes(original)
        self.assertEqual(self.srv.compute_runner_identity(copies), base)

    def test_stale_runner_detected_after_disk_change(self):
        # AC-1: replacing server.py bytes on disk while the launched identity is
        # still serving flips runner_stale to True with a restart-naming indication.
        copies = self._copied_runner_files()
        launch = self.srv.compute_runner_identity(copies)
        self.srv.set_server_runner_version(launch, runner_files=copies)
        result = self.srv.wf_server_info_response(self.root)
        self.assertIs(result["data"]["runner_stale"], False)
        self.assertEqual(result["diagnostics"], [])

        server_copy = Path(next(c for c in copies if c.endswith("server.py")))
        server_copy.write_bytes(server_copy.read_bytes() + b"\n# replaced by upgrade\n")
        result = self.srv.wf_server_info_response(self.root)
        self.assertIs(result["data"]["runner_stale"], True)
        self.assertEqual(result["data"]["server_runner_version"], launch)
        self.assertNotEqual(result["data"]["runner_disk_identity"], launch)
        detail = result["data"]["runner_stale_detail"]
        self.assertIn("restart", detail)
        # Req 4: the indication reads sensibly for both the upgrade case and a
        # self-host development edit.
        self.assertIn("upgrade", detail)
        self.assertIn("development", detail)
        self.assertIn("runner_stale", [d["code"] for d in result["diagnostics"]])

    def test_venv_bootstrap_change_also_flags_stale(self):
        # AC-1 second file: the identity covers the whole un-reloadable runner set.
        copies = self._copied_runner_files()
        launch = self.srv.compute_runner_identity(copies)
        self.srv.set_server_runner_version(launch, runner_files=copies)
        vb_copy = Path(next(c for c in copies if c.endswith("venv_bootstrap.py")))
        vb_copy.write_bytes(vb_copy.read_bytes() + b"\n# changed\n")
        result = self.srv.wf_server_info_response(self.root)
        self.assertIs(result["data"]["runner_stale"], True)

    def test_fresh_launch_from_new_bytes_reports_current(self):
        # AC-2 second half: a fresh process launch from the new bytes recaptures the
        # identity at the new content, so it reports current with no stale indication.
        copies = self._copied_runner_files()
        server_copy = Path(next(c for c in copies if c.endswith("server.py")))
        server_copy.write_bytes(server_copy.read_bytes() + b"\n# new runner bytes\n")
        relaunched = self.srv.compute_runner_identity(copies)
        self.srv.set_server_runner_version(relaunched, runner_files=copies)
        result = self.srv.wf_server_info_response(self.root)
        self.assertIs(result["data"]["runner_stale"], False)
        self.assertNotIn("runner_stale_detail", result["data"])
        self.assertEqual(result["diagnostics"], [])

    def test_unreadable_disk_degrades_to_nulls_without_raising(self):
        # AC-3: a missing/unreadable runner file (torn mid-upgrade copy) yields
        # explicit nulls, never an exception.
        copies = self._copied_runner_files()
        launch = self.srv.compute_runner_identity(copies)
        torn = copies[:1] + [str(Path(self.tmp.name) / "deleted-mid-upgrade.py")]
        self.srv.set_server_runner_version(launch, runner_files=torn)
        result = self.srv.wf_server_info_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["server_runner_version"], launch)
        self.assertIsNone(result["data"]["runner_disk_identity"])
        self.assertIsNone(result["data"]["runner_stale"])
        self.assertNotIn("runner_stale_detail", result["data"])

    def test_standalone_impl_reports_null_identity(self):
        # AC-4: a server_impl context with no runner process reports explicit nulls.
        self.srv.set_server_runner_version("", runner_files=None)
        result = self.srv.wf_server_info_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertIsNone(result["data"]["server_runner_version"])
        self.assertIsNone(result["data"]["runner_disk_identity"])
        self.assertIsNone(result["data"]["runner_stale"])

    def test_retired_literal_alias_is_gone(self):
        # AC-4: no code path may silently serve the retired literal "1". server_impl
        # must not define the alias at all; server.py's module __getattr__ re-export
        # therefore finds only the runner's real hash attribute.
        self.assertNotIn("SERVER_RUNNER_VERSION", vars(self.srv))
        with self.assertRaises(AttributeError):
            getattr(self.srv, "SERVER_RUNNER_VERSION")
        self.assertRegex(
            getattr(self.runner, "SERVER_RUNNER_VERSION"), r"^[0-9a-f]{12}$"
        )

    def test_identity_pattern_is_derived_from_the_length_constant(self):
        # Wave 1u2b0 repair: a hardcoded repetition count would silently stop matching real
        # identities (disabling every staleness comparison) if the length constant changed.
        length = self.srv._RUNNER_IDENTITY_HEX_LEN
        produced = self.srv.compute_runner_identity(self.runner.SERVER_RUNNER_FILES)
        self.assertEqual(len(produced), length)
        self.assertTrue(self.srv._RUNNER_IDENTITY_RE.match(produced))
        self.assertEqual(
            self.srv._RUNNER_IDENTITY_RE.pattern,
            rf"^[0-9a-f]{{{length}}}$",
            "the identity pattern must be generated from _RUNNER_IDENTITY_HEX_LEN",
        )
        self.assertIsNone(self.srv._RUNNER_IDENTITY_RE.match("0" * (length + 1)))

    def test_import_survives_a_loader_without_a_venv_bootstrap_file(self):
        # Wave 1u2b0 repair: the runner set is built from `__file__` attributes one statement
        # before a deliberately defensive getattr. A loader that supplies no `__file__` must drop
        # that member (identity still computes over what remains), never raise at import.
        real_vb = sys.modules["venv_bootstrap"]
        stub = types.ModuleType("venv_bootstrap")
        stub.activate_tool_venv = real_vb.activate_tool_venv
        stub.tool_venv_python = real_vb.tool_venv_python
        self.assertFalse(hasattr(stub, "__file__"))
        sys.modules["venv_bootstrap"] = stub
        self.addCleanup(sys.modules.__setitem__, "venv_bootstrap", real_vb)
        self.addCleanup(sys.modules.pop, "server_runner_file_probe", None)

        spec = importlib.util.spec_from_file_location(
            "server_runner_file_probe", SERVER_PATH
        )
        probe = importlib.util.module_from_spec(spec)
        sys.modules["server_runner_file_probe"] = probe
        spec.loader.exec_module(probe)

        self.assertEqual(
            [Path(f).name for f in probe.SERVER_RUNNER_FILES], ["server.py"]
        )
        self.assertRegex(probe.SERVER_RUNNER_VERSION, r"^[0-9a-f]+$")

    def test_pre_hash_launch_identity_compares_null(self):
        # An old runner that still injects the frozen "1" cannot be meaningfully
        # compared against a disk hash; degrade to null rather than a false stale.
        copies = self._copied_runner_files()
        self.srv.set_server_runner_version("1", runner_files=copies)
        result = self.srv.wf_server_info_response(self.root)
        self.assertEqual(result["data"]["server_runner_version"], "1")
        self.assertIsNotNone(result["data"]["runner_disk_identity"])
        self.assertIsNone(result["data"]["runner_stale"])


class RunnerIdentitySetterCompatibilityTests(unittest.TestCase):
    """Wave 1u2b0 repair: a torn mid-upgrade tree (this runner + an OLDER server_impl whose
    ``set_server_runner_version`` takes only the version argument) must keep serving.

    Known bad this pins: the runner used to call the setter with the ``runner_files`` keyword at
    both call sites. Against a one-argument impl that raises TypeError, ``build_server`` never
    builds the MCP server, and ``perform_mcp_reload`` raised AFTER closing the old handler and
    BEFORE installing the new one, leaving a CLOSED handler in a live process.
    """

    def setUp(self):
        self.srv = load_server()
        self.runner = load_thin_runner()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        fw = self.root / ".wavefoundry" / "framework"
        fw.mkdir(parents=True, exist_ok=True)
        (fw / "VERSION").write_text("test-pack-version", encoding="utf-8")
        self._saved_identity = (self.srv._runner_version, list(self.srv._runner_files))
        self._real_setter = self.srv.set_server_runner_version
        self._saved_handler = self.runner._handler
        self._saved_root = self.runner._root
        self._saved_mcp = self.runner._mcp

    def tearDown(self):
        # A simulated older impl replaces the module attribute; put the real one back first so a
        # mid-test failure cannot leave a one-argument setter behind for other test classes.
        self.srv.set_server_runner_version = self._real_setter
        self.srv.set_server_runner_version(
            self._saved_identity[0], runner_files=self._saved_identity[1]
        )
        self.runner._handler = self._saved_handler
        self.runner._root = self._saved_root
        self.runner._mcp = self._saved_mcp
        self.tmp.cleanup()

    @staticmethod
    def _one_arg_setter(recorded: list[str]):
        """An older impl's setter: version only, no ``runner_files`` keyword."""

        def set_server_runner_version(v):  # noqa: ANN001; mirrors the older signature
            recorded.append(v)

        return set_server_runner_version

    @staticmethod
    def _raising_setter(exc: BaseException):
        """A setter that fails with something OTHER than TypeError.

        The single-argument fallback exists only for a signature mismatch; a validating
        impl (ValueError), one that persists the identity (OSError), or a partially
        initialised module (AttributeError) has no retry to offer. The never-raises
        guarantee must still hold, because ``perform_mcp_reload`` calls the helper AFTER
        closing the pre-reload handler.
        """

        def set_server_runner_version(v, runner_files=None):  # noqa: ANN001
            raise exc

        return set_server_runner_version

    def test_non_typeerror_setter_failure_degrades_instead_of_raising(self):
        # Known bad this pins: the first call used to catch only TypeError, so a setter
        # raising anything else escaped and falsified the documented never-raises contract.
        for exc in (
            ValueError("rejected identity"),
            OSError("identity store unwritable"),
            AttributeError("module partially initialised"),
        ):
            with self.subTest(exc=type(exc).__name__):
                with patch.object(
                    self.srv, "set_server_runner_version", self._raising_setter(exc)
                ):
                    warning = self.runner._record_runner_identity()
                self.assertIsNotNone(
                    warning, "a setter failure must be reported, not silent"
                )
                self.assertIn(type(exc).__name__, warning)
                self.assertIn("could not record the runner identity", warning)

    def test_reload_survives_a_non_typeerror_setter_and_keeps_handler_usable(self):
        # The failure shape that matters: the helper is called after the old handler is
        # closed, so an escaping exception leaves the CLOSED handler installed in a live
        # process. Assert the reload still completes and installs a usable handler.
        try:
            self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        closed_handler = self.runner._get_handler()

        real_reload = self.runner.importlib.reload
        real_setter = self.srv.set_server_runner_version
        raising = self._raising_setter(ValueError("rejected identity"))

        def reload_into_raising_impl(module):
            reloaded = real_reload(module)
            reloaded.set_server_runner_version = raising
            return reloaded

        with patch.object(self.runner.importlib, "reload", reload_into_raising_impl):
            result = self.runner.perform_mcp_reload()
        # Restore the real setter the simulated impl overwrote, then the launch identity.
        self.srv.set_server_runner_version = real_setter
        self.srv.set_server_runner_version(
            self._saved_identity[0], runner_files=self._saved_identity[1]
        )

        self.assertEqual(result["status"], "ok", result)
        self.assertTrue(result["data"]["ok"])
        self.assertIn(
            "runner_identity_unrecorded",
            [item["code"] for item in result["diagnostics"]],
            "the degraded identity recording must be surfaced as a diagnostic",
        )
        live_handler = self.runner._get_handler()
        self.assertIsNot(live_handler, closed_handler)
        self.assertEqual(live_handler.root, self.root.resolve())
        second = self.runner.perform_mcp_reload()
        self.assertEqual(second["status"], "ok", second)

    def test_one_arg_impl_setter_does_not_raise_and_reports_degradation(self):
        recorded: list[str] = []
        with patch.object(
            self.srv,
            "set_server_runner_version",
            self._one_arg_setter(recorded),
        ):
            warning = self.runner._record_runner_identity()
        self.assertEqual(recorded, [self.runner.SERVER_RUNNER_VERSION])
        self.assertIsNotNone(warning, "the degraded fallback must be reported, not silent")
        self.assertIn("runner_files", warning)

    def test_missing_impl_setter_degrades_instead_of_raising(self):
        with patch.object(self.srv, "set_server_runner_version", None):
            warning = self.runner._record_runner_identity()
        self.assertIsNotNone(warning)
        self.assertIn("unavailable", warning)

    def test_build_server_survives_one_arg_impl_setter(self):
        recorded: list[str] = []
        with patch.object(
            self.srv,
            "set_server_runner_version",
            self._one_arg_setter(recorded),
        ):
            try:
                mcp = self.runner.build_server(self.root)
            except ImportError:
                self.skipTest("mcp package not installed")
        self.assertIsNotNone(mcp)
        self.assertEqual(recorded, [self.runner.SERVER_RUNNER_VERSION])
        self.assertIsNotNone(self.runner._get_handler())

    def test_reload_survives_one_arg_impl_setter_and_keeps_handler_usable(self):
        try:
            self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        closed_handler = self.runner._get_handler()

        real_reload = self.runner.importlib.reload
        real_setter = self.srv.set_server_runner_version
        recorded: list[str] = []
        one_arg = self._one_arg_setter(recorded)

        def reload_into_older_impl(module):
            """Simulate the reload picking up an older impl file: the freshly reloaded module
            exposes only the single-argument setter."""
            reloaded = real_reload(module)
            reloaded.set_server_runner_version = one_arg
            return reloaded

        with patch.object(self.runner.importlib, "reload", reload_into_older_impl):
            result = self.runner.perform_mcp_reload()
        # Restore the real setter the simulated older impl overwrote, then the launch identity.
        self.srv.set_server_runner_version = real_setter
        self.srv.set_server_runner_version(
            self._saved_identity[0], runner_files=self._saved_identity[1]
        )

        self.assertEqual(result["status"], "ok", result)
        self.assertTrue(result["data"]["ok"])
        self.assertEqual(recorded, [self.runner.SERVER_RUNNER_VERSION])
        self.assertIn(
            "runner_identity_unrecorded",
            [item["code"] for item in result["diagnostics"]],
            "the degraded identity recording must be surfaced as a diagnostic",
        )
        # The live process must NOT be left holding the closed pre-reload handler.
        live_handler = self.runner._get_handler()
        self.assertIsNot(live_handler, closed_handler)
        self.assertEqual(live_handler.root, self.root.resolve())
        # And the installed handler is genuinely usable: a second reload closes and rebuilds it.
        second = self.runner.perform_mcp_reload()
        self.assertEqual(second["status"], "ok", second)


class WaveMcpReloadTests(unittest.TestCase):
    """12rb9: wf_reload_mcp and version fields."""

    def setUp(self):
        # Reload-sensitive: this class tests module-reload behavior; per-method isolation is required.
        self.srv = load_server()          # server_impl (impl namespace)
        self.runner = load_thin_runner()  # server.py thin runner (build_server, perform_mcp_reload, …)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        fw = self.root / ".wavefoundry" / "framework"
        fw.mkdir(parents=True, exist_ok=True)
        (fw / "VERSION").write_text("test-pack-version", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_wf_help_lists_wf_reload_mcp(self):
        self.srv._cached_help_catalog_json.cache_clear()
        result = self.srv.wf_help_response()
        self.assertIn("wf_reload_mcp", result["data"]["core_tools"])

    def test_wf_help_reload_mcp_goal(self):
        self.srv._cached_help_catalog_json.cache_clear()
        result = self.srv.wf_help_response("reload_mcp")
        self.assertEqual(result["data"]["goal"], "reload_mcp")
        self.assertEqual(result["data"]["recommended_chain"][0], "wf_reload_mcp")

    def test_perform_mcp_reload_returns_versions(self):
        try:
            self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        result = self.runner.perform_mcp_reload()
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["ok"])
        self.assertEqual(result["data"]["framework_version"], "test-pack-version")
        self.assertEqual(result["data"]["server_runner_version"], self.runner.SERVER_RUNNER_VERSION)
        self.assertTrue(result["data"]["server_impl_version"])
        # impl_matches_disk is false when test root VERSION differs from installed pack VERSION
        self.assertIs(result["data"]["impl_matches_disk"], False)
        # Wave 1u2b0 (AC-2): an in-process reload never changes the runner identity; with the
        # on-disk runner files untouched the disk hash matches launch and staleness is False.
        self.assertEqual(result["data"]["runner_disk_identity"], self.runner.SERVER_RUNNER_VERSION)
        self.assertIs(result["data"]["runner_stale"], False)
        self.assertNotIn(
            "runner_stale", [item["code"] for item in result.get("diagnostics", [])]
        )

    def test_reload_notification_state_domains_are_closed(self):
        self.assertEqual(
            self.runner._MCP_RELOAD_NOTIFICATION_DISPATCH_STATES,
            {
                "not_needed",
                "deferred",
                "scheduled",
                "no_running_loop",
                "completed",
                "failed",
            },
        )
        self.assertEqual(
            self.runner._MCP_RELOAD_DIRECT_PUBLIC_DISPATCH_STATES,
            {"not_needed", "completed", "failed"},
        )
        self.assertEqual(
            self.runner._MCP_RELOAD_UPGRADE_PUBLIC_DISPATCH_STATES,
            {"not_needed", "scheduled", "failed"},
        )
        with self.assertRaisesRegex(ValueError, "unsupported MCP reload"):
            self.runner.perform_mcp_reload(notify="unknown")

    def test_reload_helper_has_exactly_two_production_call_sites(self):
        observed: list[tuple[str, int]] = []
        for path in (SERVER_PATH, SCRIPTS_ROOT / "server_impl.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = (
                    func.id
                    if isinstance(func, ast.Name)
                    else func.attr
                    if isinstance(func, ast.Attribute)
                    else ""
                )
                if name == "perform_mcp_reload":
                    observed.append((path.name, node.lineno))
        self.assertEqual([name for name, _line in observed], ["server.py", "server_impl.py"])

    def test_reload_reports_launch_identity_not_a_recomputed_one(self):
        """Wave 1u2b0 (AC-2), falsifiable form: the reported identity is the one captured at
        LAUNCH, so an implementation that recomputed it during the reload fails here.

        The runner's launch constants are patched over temp COPIES of the real runner files, one
        copy is then mutated (an upgrade replacing the tree under a live process), and the reload
        must still report the pre-mutation launch value while flagging staleness. The weaker
        unchanged-disk assertion above passes for a recompute-at-reload implementation too.
        """
        try:
            self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        saved_identity = (self.srv._runner_version, list(self.srv._runner_files))
        self.addCleanup(
            self.srv.set_server_runner_version,
            saved_identity[0],
            runner_files=saved_identity[1],
        )

        copies: list[str] = []
        for src in self.runner.SERVER_RUNNER_FILES:
            dst = Path(self.tmp.name) / f"runner-copy-{Path(src).name}"
            shutil.copyfile(src, dst)
            copies.append(str(dst))
        launch_identity = self.srv.compute_runner_identity(copies)
        self.assertRegex(launch_identity, r"^[0-9a-f]+$")

        with patch.object(self.runner, "SERVER_RUNNER_FILES", tuple(copies)), patch.object(
            self.runner, "SERVER_RUNNER_VERSION", launch_identity
        ):
            mutated = Path(copies[0])
            mutated.write_bytes(mutated.read_bytes() + b"\n# replaced by upgrade\n")
            recomputed = self.srv.compute_runner_identity(copies)
            self.assertNotEqual(recomputed, launch_identity)
            result = self.runner.perform_mcp_reload()

        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(
            result["data"]["server_runner_version"],
            launch_identity,
            "a reload must never re-capture the runner identity from disk",
        )
        self.assertEqual(result["data"]["runner_disk_identity"], recomputed)
        self.assertIs(result["data"]["runner_stale"], True)
        # Wave 1u2b0 repair: runner_stale under status ok must carry its own diagnostic.
        stale_diagnostics = [
            item for item in result["diagnostics"] if item["code"] == "runner_stale"
        ]
        self.assertEqual(len(stale_diagnostics), 1, result["diagnostics"])
        self.assertIn("restart", stale_diagnostics[0]["message"])

    def test_perform_mcp_reload_re_registers_tools_and_reports_count(self):
        """1319bt (131d8): perform_mcp_reload re-registers the FastMCP tool
        surface so parameter / description changes land in-process. The
        response carries ``tools_reregistered`` ≥ 1 (the first-party tool
        count minus the wf_reload_mcp survivor)."""
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        pre_count = len(self.srv._registered_mcp_tool_names(mcp))
        self.assertGreater(pre_count, 1)
        result = self.runner.perform_mcp_reload()
        self.assertEqual(result["status"], "ok")
        self.assertIn("tools_reregistered", result["data"])
        self.assertGreaterEqual(result["data"]["tools_reregistered"], 1)
        # Tool surface should still contain the same first-party prefix set.
        post_count = len(self.srv._registered_mcp_tool_names(mcp))
        self.assertEqual(
            post_count, pre_count,
            f"Tool count drifted across reload: pre={pre_count} post={post_count}",
        )

    def test_perform_mcp_reload_preserves_wf_reload_mcp_tool(self):
        """The survivor list keeps wf_reload_mcp registered through the refresh
        — otherwise the tool that triggered the reload would unregister itself."""
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        self.assertIn("wf_reload_mcp", self.srv._registered_mcp_tool_names(mcp))
        self.runner.perform_mcp_reload()
        self.assertIn(
            "wf_reload_mcp", self.srv._registered_mcp_tool_names(mcp),
            "wf_reload_mcp was removed during refresh; the survivor list is broken",
        )

    def test_perform_mcp_reload_refreshes_tool_schemas_in_place(self):
        """1319bt (131d8): the FastMCP tool registry holds freshly introspected
        schemas after perform_mcp_reload. Verified by checking that
        ``wf_graph_report``'s schema includes the wave 131bt parameter
        ``collapse_package_to_directory`` after the reload sequence — even if
        the tool function signature changed, the registry would have picked
        up the change via the re-registration."""
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        import asyncio
        async def list_tools():
            return await mcp.list_tools()
        # Force a reload to exercise the refresh path.
        self.runner.perform_mcp_reload()
        tools = asyncio.run(list_tools())
        wgr = next((t for t in tools if t.name == "wf_graph_report"), None)
        self.assertIsNotNone(wgr, "wf_graph_report missing from tool list after reload")
        props = set((wgr.inputSchema or {}).get("properties", {}).keys())
        # The wave 131bt collapse_package_to_directory parameter should be in
        # the schema after the refresh — proving fresh introspection happened.
        self.assertIn(
            "collapse_package_to_directory",
            props,
            f"wf_graph_report schema is stale after reload — props were {sorted(props)}",
        )

    def test_perform_mcp_reload_reports_no_description_change_on_unchanged_reload(self):
        """131bu: when no tool description text changed between snapshots,
        ``description_changed_tools`` is empty and no protocol notification
        fires — `/mcp` reconnect alone covers any parameter schema deltas."""
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        # Two reloads in a row — server_impl module didn't change between them,
        # so no description should differ.
        self.runner.perform_mcp_reload()
        result = self.runner.perform_mcp_reload()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"].get("description_changed_tools"), [])
        self.assertEqual(result["data"].get("added_tools"), [])
        self.assertEqual(result["data"].get("removed_tools"), [])
        self.assertNotIn("tool_list_changed_notification_sent", result["data"])
        self.assertEqual(
            result["data"]["tool_list_changed_notification_dispatch"],
            "not_needed",
        )

    def test_perform_mcp_reload_defers_a_description_change_without_sending(self):
        """The defer helper returns only private handoff state for the async tool."""
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        # Establish a clean baseline.
        self.runner.perform_mcp_reload()
        # Force a description change by mutating a single tool's description
        # directly in the FastMCP registry, then trigger the reload.
        tools_reg = mcp._tool_manager._tools
        target_name = "wf_graph_report"
        original = tools_reg[target_name].description
        tools_reg[target_name].description = "STALE PLACEHOLDER DESCRIPTION"
        try:
            result = self.runner.perform_mcp_reload(notify="defer")
        finally:
            if tools_reg[target_name].description == "STALE PLACEHOLDER DESCRIPTION":
                tools_reg[target_name].description = original
        self.assertEqual(result["status"], "ok")
        self.assertIn(target_name, result["data"]["description_changed_tools"])
        self.assertNotIn("tool_list_changed_notification_sent", result["data"])
        self.assertIs(
            result["data"]["tool_list_changed_notification_required"], True
        )
        self.assertEqual(
            result["data"]["tool_list_changed_notification_dispatch"], "deferred"
        )
        diag_codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertFalse(
            any("tool_list_changed_notification" in str(c) for c in diag_codes)
        )

    def test_perform_mcp_reload_names_no_running_loop_without_attempting_send(self):
        """Off-loop schedule mode reports its defensive helper-only outcome."""
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        target_name = "memory_backfill"
        self.assertIn(target_name, self.srv._registered_mcp_tool_names(mcp))
        mcp.remove_tool(target_name)

        with patch.object(
            mcp,
            "get_context",
            side_effect=AssertionError("no-loop branch must not attempt a send"),
        ):
            result = self.runner.perform_mcp_reload()

        self.assertEqual(result["status"], "ok", result)
        self.assertIn(target_name, result["data"]["added_tools"])
        self.assertIn(target_name, self.srv._registered_mcp_tool_names(mcp))
        self.assertNotIn("tool_list_changed_notification_sent", result["data"])
        self.assertEqual(
            result["data"]["tool_list_changed_notification_dispatch"],
            "no_running_loop",
        )
        diag_codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn(
            "tool_list_changed_notification_no_running_loop",
            diag_codes,
        )

    def test_reload_tool_awaits_notification_before_returning_completed(self):
        """The async direct tool observes completion before its response exists."""
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        class Session:
            completed = False

            async def send_tool_list_changed(self):
                self.completed = True

        session = Session()
        context = types.SimpleNamespace(
            request_context=types.SimpleNamespace(session=session)
        )
        async def exercise():
            tool = mcp._tool_manager._tools["wf_reload_mcp"]
            with patch.object(mcp, "get_context", return_value=context), patch.object(
                self.runner,
                "_refresh_mcp_tool_surface",
                return_value=(1, [], ["memory_consolidate"], [], []),
            ):
                result = await tool.run({})
            self.assertTrue(session.completed)
            return result

        result = asyncio.run(exercise())
        self.assertTrue(session.completed)
        self.assertNotIn("tool_list_changed_notification_sent", result["data"])
        self.assertNotIn("tool_list_changed_notification_required", result["data"])
        self.assertEqual(
            result["data"]["tool_list_changed_notification_dispatch"], "completed"
        )
        self.assertIn(
            "tool_list_changed_notification_sent",
            [item["code"] for item in result["diagnostics"]],
        )

    def test_reload_tool_not_needed_never_resolves_a_session_or_leaks_handoff(self):
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        async def exercise():
            tool = mcp._tool_manager._tools["wf_reload_mcp"]
            with patch.object(
                mcp,
                "get_context",
                side_effect=AssertionError("no notification means no session lookup"),
            ), patch.object(
                self.runner,
                "_refresh_mcp_tool_surface",
                return_value=(1, [], [], [], []),
            ):
                return await tool.run({})

        result = asyncio.run(exercise())
        self.assertEqual(
            result["data"]["tool_list_changed_notification_dispatch"], "not_needed"
        )
        self.assertNotIn("tool_list_changed_notification_required", result["data"])
        self.assertNotIn("tool_list_changed_notification_sent", result["data"])

    def test_upgrade_helper_schedules_notification_on_active_event_loop(self):
        """The synchronous upgrade helper puts list_changed on a real MCP stream."""
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        async def exercise():
            import anyio
            from mcp import types as mcp_types
            from mcp.server.models import InitializationOptions
            from mcp.server.session import ServerSession

            inbound_send, inbound_receive = anyio.create_memory_object_stream(1)
            wire_send, wire_receive = anyio.create_memory_object_stream(1)
            session = ServerSession(
                inbound_receive,
                wire_send,
                InitializationOptions(
                    server_name="wavefoundry-test",
                    server_version="test",
                    capabilities=mcp_types.ServerCapabilities(),
                ),
            )
            context = types.SimpleNamespace(
                request_context=types.SimpleNamespace(session=session)
            )
            async with session:
                with patch.object(
                    mcp, "get_context", return_value=context
                ), patch.object(
                    self.runner,
                    "_refresh_mcp_tool_surface",
                    return_value=(1, [], ["memory_purge"], [], []),
                ):
                    result = self.runner.perform_mcp_reload()
                wire_message = await wire_receive.receive()
            await inbound_send.aclose()
            await inbound_receive.aclose()
            await wire_send.aclose()
            await wire_receive.aclose()
            return result, wire_message

        result, wire_message = asyncio.run(exercise())
        wire_payload = wire_message.message.model_dump(by_alias=True)
        self.assertEqual(
            wire_payload["method"], "notifications/tools/list_changed"
        )
        self.assertNotIn("tool_list_changed_notification_sent", result["data"])
        self.assertEqual(
            result["data"]["tool_list_changed_notification_dispatch"], "scheduled"
        )
        self.assertIn(
            "tool_list_changed_notification_scheduled",
            [item["code"] for item in result["diagnostics"]],
        )

    def test_upgrade_helper_reports_schedule_failure_without_claiming_delivery(self):
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        async def exercise():
            with patch.object(
                mcp, "get_context", side_effect=PermissionError("session unavailable")
            ), patch.object(
                self.runner,
                "_refresh_mcp_tool_surface",
                return_value=(1, [], ["memory_purge"], [], []),
            ):
                return self.runner.perform_mcp_reload()

        result = asyncio.run(exercise())
        self.assertEqual(
            result["data"]["tool_list_changed_notification_dispatch"], "failed"
        )
        self.assertNotIn("tool_list_changed_notification_sent", result["data"])
        failed = [
            item
            for item in result["diagnostics"]
            if item["code"] == "tool_list_changed_notification_failed"
        ]
        self.assertEqual(len(failed), 1)
        self.assertIn("PermissionError", failed[0]["message"])

    def test_reload_tool_reports_awaited_send_failure_without_private_state(self):
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        class Session:
            async def send_tool_list_changed(self):
                raise LookupError("notification transport unavailable")

        context = types.SimpleNamespace(
            request_context=types.SimpleNamespace(session=Session())
        )

        async def exercise():
            tool = mcp._tool_manager._tools["wf_reload_mcp"]
            with patch.object(mcp, "get_context", return_value=context), patch.object(
                self.runner,
                "_refresh_mcp_tool_surface",
                return_value=(1, [], ["memory_purge"], [], []),
            ):
                return await tool.run({})

        result = asyncio.run(exercise())
        self.assertEqual(
            result["data"]["tool_list_changed_notification_dispatch"], "failed"
        )
        self.assertNotIn("tool_list_changed_notification_sent", result["data"])
        self.assertNotIn("tool_list_changed_notification_required", result["data"])
        failed = [
            item
            for item in result["diagnostics"]
            if item["code"] == "tool_list_changed_notification_failed"
        ]
        self.assertEqual(len(failed), 1)
        self.assertIn("LookupError", failed[0]["message"])

    def test_cancellation_drops_awaited_send_but_not_scheduled_control(self):
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        class Session:
            def __init__(self):
                self.entered = asyncio.Event()
                self.release = asyncio.Event()
                self.delivered = False

            async def send_tool_list_changed(self):
                self.entered.set()
                await self.release.wait()
                self.delivered = True

        async def exercise():
            tool = mcp._tool_manager._tools["wf_reload_mcp"]
            awaited = Session()
            awaited_context = types.SimpleNamespace(
                request_context=types.SimpleNamespace(session=awaited)
            )
            with patch.object(
                mcp, "get_context", return_value=awaited_context
            ), patch.object(
                self.runner,
                "_refresh_mcp_tool_surface",
                return_value=(1, [], ["memory_purge"], [], []),
            ):
                direct = asyncio.create_task(tool.run({}))
                await awaited.entered.wait()
                direct.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await direct
            self.assertFalse(awaited.delivered)

            scheduled = Session()
            scheduled_context = types.SimpleNamespace(
                request_context=types.SimpleNamespace(session=scheduled)
            )

            async def schedule_then_wait():
                with patch.object(
                    mcp, "get_context", return_value=scheduled_context
                ), patch.object(
                    self.runner,
                    "_refresh_mcp_tool_surface",
                    return_value=(1, [], ["memory_purge"], [], []),
                ):
                    result = self.runner.perform_mcp_reload()
                self.assertEqual(
                    result["data"]["tool_list_changed_notification_dispatch"],
                    "scheduled",
                )
                await asyncio.Event().wait()

            caller = asyncio.create_task(schedule_then_wait())
            await scheduled.entered.wait()
            caller.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await caller
            scheduled.release.set()
            await asyncio.sleep(0)
            self.assertTrue(scheduled.delivered)

        asyncio.run(exercise())

    def test_reload_keeps_resource_callback_behavior_current(self):
        """Retained FastMCP resource wrappers resolve freshly reloaded globals.

        FastMCP has no public resource-removal API and retains the registered
        wrapper object on tool-only reload.  The wrapper must nevertheless
        execute the current projection implementation rather than a frozen
        pre-reload function body.
        """

        wave_result = self.srv.wf_create_wave_response(
            self.root, "reload-resource-current", mode="create"
        )
        wave_id = wave_result["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8").replace(
            "Status: planned", "Status: implementing"
        )
        text = re.sub(
            r"(?ms)<!-- wave:review-status begin -->.*?"
            r"<!-- wave:review-status end -->\n?",
            "",
            text,
        )
        wave_md.write_text(text, encoding="utf-8")
        try:
            mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        resource_before = mcp._resource_manager._resources[
            "wavefoundry://wave/current"
        ]

        result = self.runner.perform_mcp_reload()

        self.assertEqual(result["status"], "ok")
        resource_after = mcp._resource_manager._resources[
            "wavefoundry://wave/current"
        ]
        self.assertIs(resource_after, resource_before)
        import asyncio

        items = asyncio.run(mcp.read_resource("wavefoundry://wave/current"))
        rendered = "\n".join(
            str(getattr(item, "content", None) or getattr(item, "text", None) or "")
            for item in items
        )
        self.assertIn("<!-- wave:review-status begin -->", rendered)
        self.assertIn("projection is stale", rendered)


class ServerHandlerLazyInitTests(unittest.TestCase):
    """Wave 1p8kz: a STARTED server (root known) must never return `handler_not_ready`. `_get_handler`
    lazy-builds the handler when `_handler is None` and `_root` is set; it raises only for a genuinely
    uninitialized server (no root). Field defect: persistent `handler_not_ready` across an upgrade.

    Saves/restores the `_handler`/`_root` module globals so no state leaks to other reload-sensitive
    tests."""

    def setUp(self):
        load_server()  # ensures server.py (thin runner) is imported under sys.modules["server"]
        self.runner = load_thin_runner()
        # Snapshot the reload-sensitive globals so this test never leaks handler/root state.
        self._saved_handler = self.runner._handler
        self._saved_root = self.runner._root

    def tearDown(self):
        self.runner._handler = self._saved_handler
        self.runner._root = self._saved_root

    def test_get_handler_raises_only_when_uninitialized(self):
        # No handler AND no root → genuinely uninitialized → RuntimeError (the only error case).
        self.runner._handler = None
        self.runner._root = None
        with self.assertRaises(RuntimeError):
            self.runner._get_handler()

    def test_get_handler_lazy_builds_when_root_known(self):
        # No handler but root known → lazy-build via server_impl.build_handler, no raise.
        import server_impl
        sentinel = object()
        built = {}

        def fake_build(root):
            built["root"] = root
            return sentinel

        self.runner._handler = None
        self.runner._root = Path("/tmp/known-root")
        with patch.object(server_impl, "build_handler", side_effect=fake_build):
            handler = self.runner._get_handler()
        self.assertIs(handler, sentinel, "lazy-build must return the freshly built handler")
        self.assertEqual(built["root"], Path("/tmp/known-root"))
        # The lazy-built handler is cached on the module global.
        self.assertIs(self.runner._handler, sentinel)

    def test_get_handler_returns_existing_handler_without_rebuild(self):
        existing = object()
        self.runner._handler = existing
        self.runner._root = Path("/tmp/known-root")
        import server_impl
        with patch.object(server_impl, "build_handler",
                          side_effect=AssertionError("must not rebuild when a handler exists")):
            self.assertIs(self.runner._get_handler(), existing)

    def test_build_server_stashes_root_for_lazy_build(self):
        # AC-4: build_server records the root so a later _get_handler can lazy-build it. Use a real
        # build_server (skips if mcp absent), then drop the handler and confirm lazy-build uses the
        # stashed root rather than raising.
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            try:
                self.runner.build_server(root)
            except ImportError:
                self.skipTest("mcp package not installed")
            self.assertEqual(self.runner._root, root, "build_server must stash the root")
            # Drop the explicitly-set handler; _get_handler must rebuild from the stashed root.
            self.runner._handler = None
            handler = self.runner._get_handler()
            self.assertIsNotNone(handler)

    def test_perform_mcp_reload_no_handler_not_ready_on_started_server(self):
        # AC-4: after build_server (root stashed), dropping the handler and calling perform_mcp_reload
        # must NOT surface `handler_not_ready` — the reload's `old = _get_handler()` lazy-builds it.
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            fw = root / ".wavefoundry" / "framework"
            fw.mkdir(parents=True, exist_ok=True)
            (fw / "VERSION").write_text("test-pack-version", encoding="utf-8")
            try:
                self.runner.build_server(root)
            except ImportError:
                self.skipTest("mcp package not installed")
            self.runner._handler = None  # simulate the startup / post-reload window
            result = self.runner.perform_mcp_reload()
            diag_codes = [d.get("code") for d in result.get("diagnostics", [])]
            self.assertNotIn("handler_not_ready", diag_codes,
                             "a started server (root stashed) must never report handler_not_ready")
            self.assertEqual(result["status"], "ok")


class WavePlaceholderRepairTests(unittest.TestCase):
    """Admission fills in a `Wave:` field the tool already knows.

    Field report: a document carrying `Wave: <wave-id>` was hand-repaired by an
    operator. That form never came from our template, so this is not our
    placeholder leaking; it is that an unambiguous angle-bracket placeholder
    was not recognized as one. Recognition widens to bracketed forms only,
    never to "any unrecognized value", because an arbitrary unknown value can
    be operator-authored and must never be overwritten.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.wave_id = self.srv.wf_create_wave_response(
            self.root, "placeholder-wave", mode="create"
        )["data"]["wave_id"]

    def _admit_with_wave_line(self, wave_line: str, *, mode: str = "create") -> str:
        change_id = self.srv.new_change(self.root, "bug", "sample")["id"]
        plan = self.root / "docs" / "plans" / f"{change_id}.md"
        text = plan.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^Wave: .*$", wave_line, text, count=1)
        plan.write_text(text, encoding="utf-8")
        result = self.srv.wf_add_change_response(
            self.root, self.wave_id, change_id, mode=mode
        )
        self.assertEqual(result["status"], "dry_run" if mode == "dry_run" else "ok", result)
        target = (
            self.root / "docs" / "waves" / self.wave_id / f"{change_id}.md"
            if mode == "create" else plan
        )
        return next(
            l for l in target.read_text(encoding="utf-8").splitlines()
            if l.startswith("Wave:")
        )

    def test_angle_bracket_placeholders_are_repaired(self):
        for supplied in ("Wave: <wave-id>", "Wave: `<wave-id>`"):
            with self.subTest(supplied=supplied):
                self.setUp()
                self.assertEqual(
                    self._admit_with_wave_line(supplied), f"Wave: {self.wave_id}"
                )

    def test_the_scaffold_forms_still_repair(self):
        for supplied in ("Wave: [wave-id or TBD]", "Wave: TBD"):
            with self.subTest(supplied=supplied):
                self.setUp()
                self.assertEqual(
                    self._admit_with_wave_line(supplied), f"Wave: {self.wave_id}"
                )

    def test_an_operator_authored_value_is_never_overwritten(self):
        """The control. Widening to any unrecognized value would fail here."""
        self.assertEqual(
            self._admit_with_wave_line("Wave: my-own-tracking-note"),
            "Wave: my-own-tracking-note",
        )

    def test_dry_run_writes_nothing(self):
        self.assertEqual(
            self._admit_with_wave_line("Wave: <wave-id>", mode="dry_run"),
            "Wave: <wave-id>",
        )


class WaveAddChangeSectionPlacementTests(unittest.TestCase):
    """12as3: wf_add_change inserts blocks inside the ## Changes section."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _create_wave(self, slug: str) -> str:
        return self.srv.wf_create_wave_response(self.root, slug, mode="create")["data"]["wave_id"]

    def _create_change(self, kind: str, slug: str) -> str:
        return self.srv.new_change(self.root, kind, slug)["id"]

    def _changes_section_and_after(self, wave_md_text: str) -> tuple[str, str]:
        """Return (text inside ## Changes, text after it) split at next ## heading."""
        import re
        m = re.search(r"^## Changes[ \t]*\n", wave_md_text, re.MULTILINE)
        assert m is not None, "## Changes section missing"
        rest = wave_md_text[m.end():]
        next_m = re.search(r"^## ", rest, re.MULTILINE)
        if next_m:
            return rest[:next_m.start()], rest[next_m.start():]
        return rest, ""

    def test_wf_add_change_inserts_inside_changes_section(self):
        wave_id = self._create_wave("placement-test")
        change_id = self._create_change("feat", "first-change")
        result = self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        inside, after = self._changes_section_and_after(text)
        self.assertIn(f"Change ID: `{change_id}`", inside)
        self.assertNotIn(f"Change ID: `{change_id}`", after)

    def test_wf_add_change_preserves_order(self):
        wave_id = self._create_wave("order-test")
        first = self._create_change("feat", "alpha")
        second = self._create_change("feat", "bravo")
        third = self._create_change("feat", "charlie")
        for cid in (first, second, third):
            result = self.srv.wf_add_change_response(self.root, wave_id, cid, mode="create")
            self.assertEqual(result["status"], "ok", msg=f"admission failed for {cid}: {result}")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        inside, _ = self._changes_section_and_after(text)
        idx_first = inside.find(f"Change ID: `{first}`")
        idx_second = inside.find(f"Change ID: `{second}`")
        idx_third = inside.find(f"Change ID: `{third}`")
        self.assertGreaterEqual(idx_first, 0)
        self.assertGreater(idx_second, idx_first)
        self.assertGreater(idx_third, idx_second)

    def test_wf_add_change_legacy_layout_round_trips(self):
        """Wave.md with change blocks already placed before ## Dependencies (legacy)
        must not be rewritten; new admissions still land inside ## Changes.
        """
        wave_id = self._create_wave("legacy-layout")
        legacy_change_id = "99legacy-feat pre-existing-block"
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        # Simulate the legacy buggy layout: blocks before ## Dependencies.
        legacy_block = f"\nChange ID: `{legacy_change_id}`\nChange Status: `planned`\n\n"
        text = text.replace("## Dependencies", legacy_block + "## Dependencies", 1)
        wave_md.write_text(text, encoding="utf-8")
        # Also create a change doc the admit path can find (so the admit doesn't fail).
        new_change = self._create_change("feat", "freshly-admitted")
        result = self.srv.wf_add_change_response(self.root, wave_id, new_change, mode="create")
        self.assertEqual(result["status"], "ok", msg=f"admission failed: {result}")
        text_after = wave_md.read_text(encoding="utf-8")
        # Legacy block still present in its original position.
        self.assertIn(f"Change ID: `{legacy_change_id}`", text_after)
        # New block landed inside ## Changes.
        inside, _ = self._changes_section_and_after(text_after)
        self.assertIn(f"Change ID: `{new_change}`", inside)

    def test_wf_add_change_missing_changes_section_guard(self):
        """When ## Changes is missing (operator edit), create it above the next ## heading."""
        wave_id = self._create_wave("missing-section")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        # Remove the ## Changes heading to simulate operator-edited wave.
        text = text.replace("## Changes\n\n", "", 1)
        wave_md.write_text(text, encoding="utf-8")
        change_id = self._create_change("feat", "guard-test")
        result = self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(result["status"], "ok", msg=f"admission failed: {result}")
        text_after = wave_md.read_text(encoding="utf-8")
        self.assertIn("## Changes", text_after)
        inside, _ = self._changes_section_and_after(text_after)
        self.assertIn(f"Change ID: `{change_id}`", inside)


class WaveAddChangeBrokenLinksTests(unittest.TestCase):
    """AC-18: wf_add_change response data includes broken_links list."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _create_wave(self, slug: str) -> str:
        result = self.srv.wf_create_wave_response(self.root, slug, mode="create")
        return result["data"]["wave_id"]

    def _create_change(self, kind: str, slug: str) -> str:
        result = self.srv.new_change(self.root, kind, slug)
        return result["id"]

    def test_broken_links_empty_when_no_relative_wave_links(self):
        wave_id = self._create_wave("my-wave")
        change_id = self._create_change("feat", "clean-change")
        result = self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("broken_links", result["data"])
        self.assertEqual(result["data"]["broken_links"], [])

    def test_broken_links_detected_when_doc_has_waves_relative_link(self):
        wave_id = self._create_wave("my-wave")
        change_id = self._create_change("feat", "linked-change")
        # Inject a ../waves/ link into the change doc (simulates a doc written from docs/plans/)
        change_path = self.root / "docs" / "plans" / f"{change_id}.md"
        existing = change_path.read_text(encoding="utf-8")
        change_path.write_text(
            existing + "\n\nSee also [other wave](../waves/1234a other-wave/some-change.md).\n",
            encoding="utf-8",
        )
        result = self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("broken_links", result["data"])
        self.assertGreater(len(result["data"]["broken_links"]), 0)
        self.assertIn("../waves/", result["data"]["broken_links"][0])

    def test_broken_links_present_in_dry_run_response(self):
        wave_id = self._create_wave("my-wave")
        change_id = self._create_change("feat", "dry-check")
        result = self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="dry_run")
        self.assertIn("broken_links", result["data"])


class McpResourceRegistrationTests(unittest.TestCase):
    """AC-1/AC-2: MCP resource and resource-template registrations exist."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _get_mcp(self):
        try:
            return load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

    def _list_resources(self, mcp):
        import asyncio
        return asyncio.run(mcp.list_resources())

    def _list_templates(self, mcp):
        import asyncio
        return asyncio.run(mcp.list_resource_templates())

    def test_stable_resources_registered(self):
        mcp = self._get_mcp()
        resources = self._list_resources(mcp)
        uris = {str(r.uri) for r in resources}
        expected_uris = {
            "wavefoundry://overview",
            "wavefoundry://prompts",
            "wavefoundry://architecture/current-state",
            "wavefoundry://wave/current",
            "wavefoundry://session-handoff",
        }
        self.assertTrue(
            expected_uris.issubset(uris),
            f"Missing resources: {expected_uris - uris}",
        )

    def test_resource_templates_registered(self):
        mcp = self._get_mcp()
        templates = self._list_templates(mcp)
        uri_templates = {t.uriTemplate for t in templates}
        expected = {
            "wavefoundry://change/{change_id}",
            "wavefoundry://wave/{wave_id}",
            "wavefoundry://prompt/{slug}",
            "wavefoundry://seed/{slug}",
            "wavefoundry://architecture/{slug}",
            "wavefoundry://area/{area}",
        }
        self.assertTrue(
            expected.issubset(uri_templates),
            f"Missing templates: {expected - uri_templates}",
        )

    def test_existing_tools_still_register(self):
        mcp = self._get_mcp()
        tool_names = self.srv._registered_mcp_tool_names(mcp)
        self.assertIn("wf_validate_docs", tool_names)
        self.assertIn("wf_current_wave", tool_names)


class McpResourceReadTests(unittest.TestCase):
    """AC-3/AC-4: Resources return expected content or clear not-found messages."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _read_resource(self, uri: str):
        try:
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        import asyncio
        result = asyncio.run(mcp.read_resource(uri))
        # result is a list of ReadResourceContents items
        for item in result:
            content = getattr(item, "content", None) or getattr(item, "text", None) or ""
            if content:
                return str(content)
        return ""

    def test_overview_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://overview")
        # _make_repo doesn't create project-overview.md or README.md so not-found message expected
        # but README.md might exist at repo root — accept either content or not-found
        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)

    def test_prompt_index_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://prompts")
        self.assertIn("Not Found", text)

    def _write_area_graph(self):
        """Minimal graph+cluster so compute_areas yields one area at rep dir `svc`."""
        gd = self.root / ".wavefoundry" / "index" / "graph"
        gd.mkdir(parents=True, exist_ok=True)
        nodes = [
            {"id": "svc/a.py::run", "kind": "function", "label": "run", "layer": "project", "source_file": "svc/a.py"},
            {"id": "svc/b.py::go", "kind": "function", "label": "go", "layer": "project", "source_file": "svc/b.py"},
        ]
        (gd / "project-graph.json").write_text(json.dumps(
            {"schema_version": "1", "builder_version": "1", "layer": "project", "nodes": nodes, "edges": []}), encoding="utf-8")
        (gd / "project-graph-clusters.json").write_text(json.dumps(
            {"cluster_schema_version": "1", "cluster_builder_version": "10", "layer": "project",
             "communities": [{"community_id": "project:c0", "label": "svc", "seed_node_id": "svc/a.py::run",
                              "node_ids": [n["id"] for n in nodes], "node_count": 2, "boundary_node_count": 0}],
             "community_count": 1}), encoding="utf-8")

    def test_area_resource_returns_authored_agents_md(self):
        # 1p662: wavefoundry://area/{area_id} returns the on-disk AGENTS.md.
        self._write_area_graph()
        (self.root / "svc").mkdir(parents=True, exist_ok=True)
        (self.root / "svc" / "AGENTS.md").write_text("# svc\n\nLocal conventions for svc.\n", encoding="utf-8")
        text = self._read_resource("wavefoundry://area/svc")  # area_id == 'svc'
        self.assertIn("Local conventions for svc", text)

    def test_area_resource_not_found_when_unauthored_or_unknown(self):
        self._write_area_graph()  # area 'svc' exists but no AGENTS.md authored
        self.assertIn("Not Found", self._read_resource("wavefoundry://area/svc"))
        self.assertIn("Not Found", self._read_resource("wavefoundry://area/nonexistent"))

    def _write_deep_area_graph(self):
        """Graph whose area's representative path is a deep subdirectory, so the
        conventional AGENTS.md sits at an ANCESTOR (project root), not the rep path."""
        gd = self.root / ".wavefoundry" / "index" / "graph"
        gd.mkdir(parents=True, exist_ok=True)
        base = "libs/ui/src/components/buttons"
        nodes = [
            {"id": f"{base}/a.py::run", "kind": "function", "label": "run", "layer": "project", "source_file": f"{base}/a.py"},
            {"id": f"{base}/b.py::go", "kind": "function", "label": "go", "layer": "project", "source_file": f"{base}/b.py"},
        ]
        (gd / "project-graph.json").write_text(json.dumps(
            {"schema_version": "1", "builder_version": "1", "layer": "project", "nodes": nodes, "edges": []}), encoding="utf-8")
        (gd / "project-graph-clusters.json").write_text(json.dumps(
            {"cluster_schema_version": "1", "cluster_builder_version": "10", "layer": "project",
             "communities": [{"community_id": "project:c0", "label": "buttons", "seed_node_id": f"{base}/a.py::run",
                              "node_ids": [n["id"] for n in nodes], "node_count": 2, "boundary_node_count": 0}],
             "community_count": 1}), encoding="utf-8")

    def _load_gen_for_areas(self):
        import importlib.util as _ilu
        import sys as _sys
        scripts = Path(__file__).resolve().parent.parent
        spec = _ilu.spec_from_file_location("gen_codebase_map", scripts / "gen_codebase_map.py")
        mod = _ilu.module_from_spec(spec)
        _sys.modules[spec.name] = mod  # frozen-dataclass resolution needs this
        spec.loader.exec_module(mod)
        return mod

    def test_area_resource_walks_up_to_ancestor_agents_md(self):
        # 1p66d: AGENTS.md at the project root (an ancestor) is served for a deep area.
        self._write_deep_area_graph()
        (self.root / "libs" / "ui").mkdir(parents=True, exist_ok=True)
        (self.root / "libs" / "ui" / "AGENTS.md").write_text(
            "# ui\n\nUI project conventions live here.\n", encoding="utf-8"
        )
        gen = self._load_gen_for_areas()
        area = gen.compute_areas(self.root).areas[0]
        text = self._read_resource(f"wavefoundry://area/{area.area_id}")
        self.assertIn("UI project conventions live here", text)

    def test_architecture_current_state_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://architecture/current-state")
        self.assertIn("Not Found", text)

    def test_session_handoff_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://session-handoff")
        self.assertIn("Not Found", text)

    def test_current_wave_returns_no_active_wave_message(self):
        text = self._read_resource("wavefoundry://wave/current")
        # No active wave in test repo
        self.assertIn("No Active Wave", text)

    def test_current_wave_returns_wave_md_when_active(self):
        # Create a wave and mark it active
        wave_result = self.srv.wf_create_wave_response(self.root, "resource-test", mode="create")
        wave_id = wave_result["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        text = text.replace("Status: planned", "Status: active")
        wave_md.write_text(text, encoding="utf-8")
        result_text = self._read_resource("wavefoundry://wave/current")
        self.assertIn("Wave Record", result_text)

    def test_current_wave_resource_derives_stale_projection_and_fails_closed_on_bad_authority(self):
        wave_result = self.srv.wf_create_wave_response(
            self.root, "resource-event-state", mode="create"
        )
        wave_id = wave_result["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8").replace("Status: planned", "Status: active")
        text = text.replace("Machine review state — 0 findings", "Machine review state — 999 findings")
        wave_md.write_text(text, encoding="utf-8")

        stale = self._read_resource("wavefoundry://wave/current")
        self.assertIn("Machine review state — 0 findings", stale)
        self.assertIn("<!-- wave:review-status begin -->", stale)
        self.assertIn("projection is stale", stale)
        self.assertNotIn("999 records", stale)

        (wave_md.parent / "events.jsonl").write_bytes(b"{bad-json}\n")
        invalid = self._read_resource("wavefoundry://wave/current")
        self.assertIn("Wave Review Evidence Unavailable", invalid)
        self.assertIn("invalid JSON", invalid)
        self.assertNotIn("999 records", invalid)

    def test_current_wave_resource_derives_valid_authority_when_projection_is_missing(self):
        wave_result = self.srv.wf_create_wave_response(
            self.root, "resource-missing-projection", mode="create"
        )
        wave_id = wave_result["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8").replace("Status: planned", "Status: active")
        text = re.sub(
            r"(?ms)^## Finding Synthesis\n.*?(?=^## )",
            "",
            text,
            count=1,
        )
        wave_md.write_text(text, encoding="utf-8")

        derived = self._read_resource("wavefoundry://wave/current")

        self.assertNotIn("Wave Review Evidence Unavailable", derived)
        self.assertIn("Machine review state — 0 findings", derived)
        self.assertIn("<!-- wave:review-status begin -->", derived)
        self.assertIn("projection is missing", derived)

    def test_prompt_index_returns_content_when_exists(self):
        # Create a prompt index file
        prompts_dir = self.root / "docs" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "index.md").write_text("# Prompt Index\n\n- plan-feature\n", encoding="utf-8")
        text = self._read_resource("wavefoundry://prompts")
        self.assertIn("Prompt Index", text)


class McpResourceTemplateReadTests(unittest.TestCase):
    """AC-2/AC-4: Resource templates return content or clear not-found messages."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _read_resource(self, uri: str):
        try:
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        import asyncio
        result = asyncio.run(mcp.read_resource(uri))
        for item in result:
            content = getattr(item, "content", None) or getattr(item, "text", None) or ""
            if content:
                return str(content)
        return ""

    def test_change_template_returns_not_found_for_unknown_id(self):
        text = self._read_resource("wavefoundry://change/zzzzz-unknown")
        self.assertIn("Not Found", text)

    def test_change_template_returns_content_when_exists(self):
        result = self.srv.new_change(self.root, "feat", "resource-read-test")
        change_id = result["id"]
        text = self._read_resource(f"wavefoundry://change/{change_id}")
        self.assertIn("Change ID", text)

    def test_wave_template_returns_not_found_for_unknown_id(self):
        text = self._read_resource("wavefoundry://wave/zzzzz-unknown")
        self.assertIn("Not Found", text)

    def test_wave_template_returns_content_when_exists(self):
        wave_result = self.srv.wf_create_wave_response(self.root, "tpl-test", mode="create")
        wave_id = wave_result["data"]["wave_id"]
        text = self._read_resource(f"wavefoundry://wave/{wave_id}")
        self.assertIn("Wave Record", text)

    def test_architecture_template_returns_not_found_when_missing(self):
        text = self._read_resource("wavefoundry://architecture/nonexistent-doc")
        self.assertIn("Not Found", text)

    def test_architecture_template_returns_content_when_exists(self):
        arch_dir = self.root / "docs" / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)
        (arch_dir / "current-state.md").write_text("# Current State\n\nAll good.\n", encoding="utf-8")
        text = self._read_resource("wavefoundry://architecture/current-state")
        self.assertIn("Current State", text)

    def test_seed_template_returns_not_found_for_unknown_slug(self):
        text = self._read_resource("wavefoundry://seed/nonexistent-seed-xyz")
        self.assertIn("Not Found", text)


class WaveCurrentMigrationGrepTests(unittest.TestCase):
    """12as6 AC-20: no in-tree readers of the old data.wave envelope remain (outside historical)."""

    def test_no_stale_data_wave_readers_in_source_and_prompts(self):
        """Grep for old-style `data["wave"]` or `data.wave` response readers.

        Scope: framework scripts, prompt surfaces, seeds, AGENTS.md. Excludes
        historical wave records and journals under docs/waves/** and
        docs/agents/journals/**.
        """
        import re
        import subprocess
        # tests/ → scripts/ → framework/ → .wavefoundry/ → repo_root = 4 parents up
        repo_root = Path(__file__).resolve().parents[4]
        targets = [
            repo_root / ".wavefoundry" / "framework" / "scripts",
            repo_root / "docs" / "prompts",
            repo_root / ".wavefoundry" / "framework" / "seeds",
            repo_root / "AGENTS.md",
        ]
        existing_targets = [str(t) for t in targets if t.exists()]
        if not existing_targets:
            self.skipTest("No target paths to scan")
        # Pattern matches response-reader forms, not producer forms (key emission).
        # Examples to FAIL on: result["data"]["wave"]["status"], resp.data.wave.wave_id
        # Examples allowed: "wave": wave_data (producer in wf_audit), key strings like '"wave"'.
        pattern = r'(?:result|resp|response|data)\[(?:"wave"|\'wave\')\](?!s)'
        try:
            proc = subprocess.run(
                ["grep", "-rnE", "--include=*.py", "--include=*.md", pattern, *existing_targets],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            self.skipTest("grep not available")
        hits = [line for line in proc.stdout.strip().splitlines() if line]
        # Filter out this very test file (self-references to the pattern as a string literal
        # and the comment examples above would register as matches).
        hits = [line for line in hits if "test_server_tools.py" not in line]
        self.assertEqual(
            hits,
            [],
            f"Found stale `data[\"wave\"]` readers that should migrate to `data[\"waves\"][0]`:\n"
            + "\n".join(hits),
        )


# ---------------------------------------------------------------------------
# wf_open_dashboard tests (12qme-enh dashboard-open-browser)
# ---------------------------------------------------------------------------

def _make_mock_dashboard_lib(meta_path, *, browser_open_enabled: bool = True):
    """Return a MagicMock for dashboard_lib with dashboard_metadata_path returning meta_path."""
    mock_lib = MagicMock()
    mock_lib.dashboard_metadata_path.return_value = meta_path
    mock_lib.read_dashboard_metadata.return_value = {}
    mock_lib.dashboard_browser_open_enabled.return_value = browser_open_enabled
    return mock_lib


class WaveDashboardOpenTests(unittest.TestCase):
    """Tests for wf_open_dashboard_response (AC-2, AC-3, AC-4)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self._meta_path = self.root / ".wavefoundry" / "locks" / "dashboard-server.lock"
        self._prev_browser_suppress = os.environ.get("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER")
        os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "0"
        self._meta_path.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self._prev_browser_suppress is None:
            os.environ.pop("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER", None)
        else:
            os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = self._prev_browser_suppress
        self.tmp.cleanup()

    def _write_meta(self, pid: int, url: str) -> None:
        self._meta_path.write_text(
            json.dumps({"pid": pid, "url": url}), encoding="utf-8"
        )

    def _dashboard_lib_patch(self):
        """Return a sys.modules patch for dashboard_lib pointing meta_path at our tmp file."""
        import sys
        mock_lib = _make_mock_dashboard_lib(self._meta_path)
        return patch.dict(sys.modules, {"dashboard_lib": mock_lib})

    def test_open_when_running_calls_webbrowser_and_returns_opened(self):
        """AC-2: when dashboard running, webbrowser.open is called and opened=True returned."""
        self._write_meta(pid=12345, url="http://localhost:7890")
        import server_impl
        # Wave 1rswx: open now classifies the recorded PID with the zombie-safe cmdline-verified check,
        # so a genuinely-running dashboard must appear in the cmdline scan for this root.
        with self._dashboard_lib_patch(), \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[12345]), \
             patch.object(server_impl, "_pid_is_running", return_value=True), \
             patch("webbrowser.open") as mock_wb:
            result = self.srv.wf_open_dashboard_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("opened"))
        self.assertEqual(result["data"].get("url"), "http://localhost:7890")
        mock_wb.assert_called_once_with("http://localhost:7890")

    def test_open_when_not_running_delegates_to_start(self):
        """AC-3: when dashboard not running, delegates to wf_start_dashboard_response."""
        # No meta file written — dashboard not running path via empty mock lib.
        import sys
        import server_impl
        mock_lib = _make_mock_dashboard_lib(self._meta_path)  # meta_path doesn't exist
        with patch.dict(sys.modules, {"dashboard_lib": mock_lib}), \
             patch.object(
                 server_impl, "wf_start_dashboard_response",
                 return_value={"status": "ok", "data": {"started": True}},
             ) as mock_start:
            result = self.srv.wf_open_dashboard_response(self.root)
        mock_start.assert_called_once_with(self.root)
        self.assertEqual(result["data"]["started"], True)

    def test_start_already_running_includes_next_tools_dashboard_open(self):
        """AC-4: wf_start_dashboard when already running includes next_tools=['wf_open_dashboard']."""
        self._write_meta(pid=12345, url="http://localhost:7890")
        import sys
        mock_lib = _make_mock_dashboard_lib(self._meta_path)
        import server_impl
        with patch.dict(sys.modules, {"dashboard_lib": mock_lib}), \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[12345]), \
             patch.object(server_impl, "_pid_is_running", return_value=True):
            result = self.srv.wf_start_dashboard_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("already_running"))
        self.assertIn("wf_open_dashboard", result.get("next_tools", []))

    def test_start_lock_busy_returns_already_running_without_spawning(self):
        """Concurrent start attempts report an in-progress dashboard instead of spawning another."""
        import dashboard_lib
        import server_impl

        class BusyLock:
            def __enter__(self):
                raise dashboard_lib.DashboardLockBusy("busy")

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch.object(dashboard_lib, "dashboard_start_lock", return_value=BusyLock()), \
             patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0), \
             patch("subprocess.Popen") as popen:
            result = self.srv.wf_start_dashboard_response(self.root)

        popen.assert_not_called()
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("already_running"))
        self.assertTrue(result["data"].get("starting"))
        self.assertEqual(result["diagnostics"][0]["code"], "dashboard_start_in_progress")


class WaveDashboardPersistentStartLockTests(unittest.TestCase):
    """1sxxx: dashboard-start.lock persists; OS ownership is authoritative."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self._prev_browser_suppress = os.environ.get("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER")
        os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"
        import dashboard_lib
        self.lib = dashboard_lib
        self.start_lock_path = dashboard_lib.dashboard_lock_path(
            self.root, dashboard_lib.DASHBOARD_START_LOCK_NAME
        )
        self.server_lock_path = dashboard_lib.dashboard_lock_path(
            self.root, dashboard_lib.DASHBOARD_SERVER_LOCK_NAME
        )
        self.meta_path = self.root / ".wavefoundry" / "locks" / "dashboard-server.lock"

    def tearDown(self):
        if self._prev_browser_suppress is None:
            os.environ.pop("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER", None)
        else:
            os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = self._prev_browser_suppress
        self.tmp.cleanup()

    def _spawn_child(self, child_lock_holder, *, hold_lock: bool, write_meta: bool):
        """Return a Popen side-effect that simulates the spawned dashboard child.

        The fake child optionally acquires the lifetime lock (so the parent's
        flock-try sees it as busy=alive) and writes metadata with its own pid.
        """
        fake_pid = 99999

        def _side_effect(cmd, **kwargs):
            if hold_lock:
                lock_cm = self.lib.dashboard_server_lock(self.root)
                lock_cm.__enter__()
                child_lock_holder.append(lock_cm)
            if write_meta:
                self.lib.write_dashboard_metadata(
                    self.root,
                    {"pid": fake_pid, "url": "http://127.0.0.1:43127/dashboard.html"},
                )
            return MagicMock(pid=fake_pid)

        return _side_effect, fake_pid

    def test_successful_start_keeps_persistent_start_lock(self):
        # AC-7: both carriers persist after a confirmed start; only OS ownership
        # indicates contention.
        import server_impl
        holders: list = []
        side_effect, fake_pid = self._spawn_child(holders, hold_lock=True, write_meta=True)
        try:
            with patch("subprocess.Popen", side_effect=side_effect), \
                 patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[]), \
                 patch.object(server_impl, "_pid_is_running", return_value=True):
                result = self.srv.wf_start_dashboard_response(self.root)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["data"].get("started"))
            self.assertTrue(
                self.start_lock_path.exists(),
                "start.lock remains as a persistent OS-lock carrier",
            )
            self.assertTrue(
                self.server_lock_path.exists(),
                "dashboard-server.lock remains (held by the child)",
            )
        finally:
            for cm in holders:
                cm.__exit__(None, None, None)

    def test_failed_start_keeps_persistent_start_lock(self):
        # AC-7: a failed child leaves an unlocked, re-acquirable carrier.
        import server_impl
        holders: list = []
        side_effect, _ = self._spawn_child(holders, hold_lock=False, write_meta=False)
        with patch("subprocess.Popen", side_effect=side_effect), \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(server_impl, "_pid_is_running", return_value=False), \
             patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0):
            result = self.srv.wf_start_dashboard_response(self.root)
        # url never confirmed → url_not_ready diagnostic; start.lock left in place.
        self.assertEqual(result["status"], "ok")
        self.assertTrue(
            self.start_lock_path.exists(),
            "a failed/timed-out start must leave start.lock for the next attempt",
        )

    def test_meta_written_but_lock_not_held_does_not_unlink(self):
        # AC-2/AC-3: url confirmed but the child has not yet flocked the lifetime
        # lock → no unlink (avoid a double-spawn window).
        import server_impl
        holders: list = []
        side_effect, _ = self._spawn_child(holders, hold_lock=False, write_meta=True)
        with patch("subprocess.Popen", side_effect=side_effect), \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(server_impl, "_pid_is_running", return_value=True):
            result = self.srv.wf_start_dashboard_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("started"))
        self.assertTrue(
            self.start_lock_path.exists(),
            "without an observably held server lock the start.lock must remain",
        )

    def test_crash_leftover_start_lock_is_reacquirable(self):
        # AC-2: a leftover start.lock from a prior crash is harmless (flock, not
        # existence) and the next start re-acquires it.
        self.start_lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.start_lock_path.write_text("{}", encoding="utf-8")
        # Re-acquire succeeds despite the leftover file.
        with self.lib.dashboard_start_lock(self.root):
            pass
        self.assertTrue(self.start_lock_path.exists())

    def test_concurrent_start_loser_aborts_without_spawning(self):
        # AC-3: while start.lock is held by another starter, a second start is
        # gated (no double spawn) and reports the in-progress dashboard.
        import dashboard_lib
        import server_impl

        class BusyLock:
            def __enter__(self):
                raise dashboard_lib.DashboardLockBusy("busy")

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch.object(dashboard_lib, "dashboard_start_lock", return_value=BusyLock()), \
             patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0), \
             patch("subprocess.Popen") as popen:
            result = self.srv.wf_start_dashboard_response(self.root)
        popen.assert_not_called()
        self.assertTrue(result["data"].get("already_running"))
        self.assertTrue(result["data"].get("starting"))


class WaveDashboardBrowserSuppressTests(unittest.TestCase):
    """Dashboard browser must not open during the default test harness."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"

    def tearDown(self):
        self.tmp.cleanup()

    def test_start_spawns_without_open_flag_when_suppressed(self):
        import server_impl
        with patch("subprocess.Popen") as popen, \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(server_impl, "_pid_is_running", return_value=False):
            popen.return_value = MagicMock(pid=99999)
            self.srv.wf_start_dashboard_response(self.root)
        cmd = popen.call_args.args[0]
        self.assertNotIn("--open", cmd)

    def test_open_when_running_does_not_call_webbrowser_when_suppressed(self):
        meta_path = self.root / ".wavefoundry" / "locks" / "dashboard-server.lock"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(
            json.dumps({"pid": os.getpid(), "url": "http://127.0.0.1:9/dashboard.html"}),
            encoding="utf-8",
        )
        import server_impl
        # Wave 1rswx: the recorded PID must appear in the cmdline scan to be classified live (zombie-safe).
        with patch("webbrowser.open") as mock_wb, \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[os.getpid()]), \
             patch.object(server_impl, "_pid_is_running", return_value=True):
            result = server_impl.wf_open_dashboard_response(self.root)
        mock_wb.assert_not_called()
        self.assertFalse(result["data"].get("opened"))
        self.assertTrue(result["data"].get("browser_suppressed"))


class WaveDashboardPidRaceTests(unittest.TestCase):
    """Wave 1p8pf: the dashboard start lock/PID race. The readiness poll must NOT require
    `meta.pid == proc.pid` — a serving dashboard whose metadata was written under a DIFFERENT PID (the
    field race: poller PID 4920 vs metadata PID 4924) must be recognized, so the start does not
    false-report url_not_ready, spawn a duplicate, or climb ports."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        os.environ["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"
        self.meta_path = self.root / ".wavefoundry" / "locks" / "dashboard-server.lock"
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_meta(self, pid: int, url: str) -> None:
        self.meta_path.write_text(json.dumps({"pid": pid, "url": url}), encoding="utf-8")

    def test_metadata_pid_differs_from_proc_pid_no_false_url_not_ready(self):
        # AC-2/AC-3: the spawned child writes metadata under PID 4924, but the poller's Popen returns
        # PID 4920 (the field race). With the old `meta.pid == proc.pid` check this false-reported
        # url_not_ready; now a reachable URL (any live PID) is accepted. No duplicate is spawned beyond
        # the one start; no port climb.
        import server_impl

        POLLER_PID = 4920
        CHILD_PID = 4924
        URL = "http://127.0.0.1:43127/dashboard.html"

        def _popen_side_effect(cmd, **kwargs):
            # Simulate the spawned child writing metadata under ITS OWN (different) pid.
            self._write_meta(CHILD_PID, URL)
            return MagicMock(pid=POLLER_PID)

        with patch("subprocess.Popen", side_effect=_popen_side_effect) as popen, \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(server_impl, "_dashboard_url_reachable", return_value=True), \
             patch.object(server_impl, "_pid_is_running", return_value=False):
            result = self.srv.wf_start_dashboard_response(self.root)

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("started"))
        self.assertEqual(result["data"].get("url"), URL,
                         "the serving URL must be returned despite the PID mismatch")
        diags = result.get("diagnostics") or []
        codes = {d.get("code") for d in diags}
        self.assertNotIn("url_not_ready", codes,
                         "a serving dashboard must NOT report url_not_ready on a PID mismatch")
        # Exactly ONE spawn — no duplicate / port climb.
        self.assertEqual(popen.call_count, 1, "a serving dashboard must not be double-spawned")

    def test_reconcile_before_spawn_returns_serving_url_without_spawning(self):
        # AC-1: a dashboard is ALREADY serving under a drifted PID (recorded metadata PID not live, but a
        # live dashboard process exists for this root and the URL is reachable). The start must return
        # that URL WITHOUT spawning — no duplicate, no port climb (43127 stays 43127).
        import server_impl

        URL = "http://127.0.0.1:43127/dashboard.html"
        self._write_meta(pid=4924, url=URL)  # recorded PID is NOT live (running_meta returns None)

        with patch("subprocess.Popen") as popen, \
             patch.object(server_impl, "_pid_is_running", return_value=False), \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[4924]), \
             patch.object(server_impl, "_dashboard_url_reachable", return_value=True):
            result = self.srv.wf_start_dashboard_response(self.root)

        popen.assert_not_called()
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("already_running"))
        self.assertEqual(result["data"].get("url"), URL)

    def test_genuinely_failed_start_still_reports_url_not_ready(self):
        # AC-4 mitigation: relaxing the PID check must NOT mask a real failure. No metadata, nothing
        # reachable, no live PID → url_not_ready within the bounded deadline (no infinite hang).
        import server_impl

        with patch("subprocess.Popen") as popen, \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(server_impl, "_dashboard_url_reachable", return_value=False), \
             patch.object(server_impl, "_pid_is_running", return_value=False), \
             patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0):
            popen.return_value = MagicMock(pid=4920)
            result = self.srv.wf_start_dashboard_response(self.root)

        codes = {d.get("code") for d in (result.get("diagnostics") or [])}
        self.assertIn("url_not_ready", codes,
                      "a genuinely-failed start must still report url_not_ready")

    def test_url_reachable_helper_returns_true_on_http_error_status(self):
        # The reachability check must treat ANY HTTP response (incl. 4xx/5xx) as "serving" — only a
        # connection failure means not-reachable.
        import server_impl
        import urllib.request
        import urllib.error

        # HTTP 404 → serving.
        def _raise_http_error(*a, **k):
            raise urllib.error.HTTPError("http://x/", 404, "nf", {}, None)

        with patch.object(urllib.request, "urlopen", side_effect=_raise_http_error):
            self.assertTrue(server_impl._dashboard_url_reachable("http://127.0.0.1:1/x"))

        # Connection refused → not serving.
        with patch.object(urllib.request, "urlopen", side_effect=OSError("refused")):
            self.assertFalse(server_impl._dashboard_url_reachable("http://127.0.0.1:1/x"))

        # Empty URL → not serving (no call).
        self.assertFalse(server_impl._dashboard_url_reachable(""))


class PreferredPythonSubprocessTests(unittest.TestCase):
    """Regression coverage for explicit shared-venv subprocess routing."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_venv_python(self) -> Path:
        venv_root = self.root / ".venv-test"
        venv_python = venv_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        venv_python.parent.mkdir(parents=True, exist_ok=True)
        venv_python.write_text("", encoding="utf-8")
        return venv_python

    def test_run_validate_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0, stdout="docs-lint: ok\n", stderr="")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch("subprocess.run", return_value=mock_proc) as run_mock:
            self.srv.run_validate(self.root)
        called_cmd = run_mock.call_args.args[0]
        self.assertEqual(called_cmd[0], str(venv_python))

    def test_background_index_refresh_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        indexer = self.root / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
        indexer.parent.mkdir(parents=True, exist_ok=True)
        indexer.write_text("", encoding="utf-8")
        mock_proc = MagicMock(pid=12345)
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch("subprocess.Popen", return_value=mock_proc) as popen_mock, \
             patch.object(self.srv, "_background_refresh_active", return_value=False):
            started = self.srv._start_background_index_refresh(self.root, "project")
        self.assertTrue(started)
        called_cmd = popen_mock.call_args.args[0]
        self.assertEqual(called_cmd[0], str(venv_python))
        self.assertEqual(called_cmd[-2:], ["--content", "all"])

    def test_wf_start_dashboard_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        import server_impl
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch("subprocess.Popen", return_value=MagicMock(pid=99999)) as popen_mock, \
             patch.object(server_impl, "_dashboard_cmdline_pids", return_value=[]), \
             patch.object(server_impl, "_pid_is_running", return_value=False):
            self.srv.wf_start_dashboard_response(self.root)
        called_cmd = popen_mock.call_args.args[0]
        self.assertEqual(called_cmd[0], str(venv_python))

    def test_wf_upgrade_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0, stdout="Upgrade complete\n", stderr="")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch("subprocess.run", return_value=mock_proc) as run_mock:
            self.srv.wf_upgrade_response(self.root, phase="preflight_to_docs_gate")
        called_cmd = run_mock.call_args.args[0]
        self.assertEqual(called_cmd[0], str(venv_python))


# ---------------------------------------------------------------------------
# wf_upgrade_status + wf_upgrade + restart guard tests (12r08/12r0b)
# ---------------------------------------------------------------------------

class WaveUpgradeStatusTests(unittest.TestCase):
    """Tests for wf_upgrade_status_response (AC-5 / R5)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _lock_path(self):
        return self.root / ".wavefoundry" / "upgrade-in-progress.json"

    def _write_lock(self, pid=None, memory_run_id=""):
        p = self._lock_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "started_at": "2026-05-19T00:00:00+00:00",
            "from_version": "2026-05-10a",
            "to_version": "2026-05-19a",
            "pid": pid or os.getpid(),
            "memory_backfill_run_id": memory_run_id,
        }), encoding="utf-8")

    def test_no_lock_returns_not_in_progress(self):
        result = self.srv.wf_upgrade_status_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["in_progress"])
        self.assertIsNone(result["data"]["to_version"])

    def test_lock_present_returns_in_progress(self):
        self._write_lock()
        result = self.srv.wf_upgrade_status_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["in_progress"])
        self.assertEqual(result["data"]["from_version"], "2026-05-10a")
        self.assertEqual(result["data"]["to_version"], "2026-05-19a")

    def test_lock_exposes_exact_retired_model_cleanup_projection(self):
        self._write_lock()
        path = self._lock_path()
        lock = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "retired_model_cleanup_status": "failed",
            "retired_model_cleanup_removed": ["fastembed:default:retired-a"],
            "retired_model_cleanup_absent": ["clean-onnx:default:retired-b"],
            "retired_model_cleanup_unowned": ["fastembed:custom:retired-c"],
            "retired_model_cleanup_failed": ["coreml:default:retired-d|remove_failed"],
        }
        lock.update(expected)
        path.write_text(json.dumps(lock), encoding="utf-8")
        result = self.srv.wf_upgrade_status_response(self.root)
        self.assertEqual(
            {key: result["data"][key] for key in self.srv.RETIRED_MODEL_CLEANUP_KEYS},
            expected,
        )

    def test_lock_cleanup_projection_drops_paths_and_exception_text(self):
        self._write_lock()
        path = self._lock_path()
        lock = json.loads(path.read_text(encoding="utf-8"))
        lock.update({
            "retired_model_cleanup_status": "failed",
            "retired_model_cleanup_removed": ["/Users/operator/private/model"],
            "retired_model_cleanup_absent": ["coreml:default:retired-ok"],
            "retired_model_cleanup_unowned": ["PermissionError: errno 13"],
            "retired_model_cleanup_failed": [
                "coreml:default:retired-bad|/private/cache",
                "coreml:default:retired-failed|remove_failed",
            ],
        })
        path.write_text(json.dumps(lock), encoding="utf-8")
        result = self.srv.wf_upgrade_status_response(self.root)
        self.assertEqual(result["data"]["retired_model_cleanup_status"], "failed")
        self.assertEqual(result["data"]["retired_model_cleanup_removed"], [])
        self.assertEqual(
            result["data"]["retired_model_cleanup_absent"],
            ["coreml:default:retired-ok"],
        )
        self.assertEqual(result["data"]["retired_model_cleanup_unowned"], [])
        self.assertEqual(
            result["data"]["retired_model_cleanup_failed"],
            ["coreml:default:retired-failed|remove_failed"],
        )

    def test_lock_exposes_structured_memory_gate_and_exact_worklist(self):
        self._write_lock(memory_run_id="run-1")
        backfill = MagicMock()
        backfill.run_summary.return_value = {
            "run_id": "run-1",
            "state": "awaiting_validation",
            "candidates_pending": 2,
            "promoted": 1,
            "last_failure": "one source unreadable",
        }
        backfill.validation_worklist.return_value = {
            "validation_worklist": [{"memory_id": "1abc-memory"}],
            "validation_worklist_count": 2,
            "validation_worklist_remaining": 1,
        }
        with patch.object(self.srv, "_load_script", return_value=backfill):
            result = self.srv.wf_upgrade_status_response(self.root)
        gate = result["data"]["memory_backfill"]
        self.assertEqual(gate["run_id"], "run-1")
        self.assertEqual(gate["candidates_pending"], 2)
        self.assertEqual(gate["last_failure"], "one source unreadable")
        self.assertEqual(gate["validation_worklist"][0]["memory_id"], "1abc-memory")

    def test_publication_action_status_hides_legacy_failure_lease(self):
        self._write_lock(memory_run_id="run-publication")
        path = self._lock_path()
        lock = json.loads(path.read_text(encoding="utf-8"))
        action_required = {
            "kind": "historical_memory",
            "state": "awaiting_memory_publication",
            "resume_phase": "resume_after_memory",
            "run_id": "run-publication",
            "token": "publication-token",
        }
        lock.update({
            "current_phase": "awaiting_memory_publication",
            "failed_phase": "awaiting_memory_validation",
            "failed_at": None,
            "action_required": action_required,
        })
        path.write_text(json.dumps(lock), encoding="utf-8")
        backfill = MagicMock()
        backfill.run_summary.return_value = {
            "run_id": "run-publication", "state": "ready_for_index",
        }
        backfill.validation_worklist.return_value = {"validation_worklist": []}
        with patch.object(self.srv, "_load_script", return_value=backfill):
            result = self.srv.wf_upgrade_status_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["current_phase"], "awaiting_memory_publication")
        self.assertIsNone(result["data"]["failed_phase"])
        self.assertIsNone(result["data"]["failed_at"])
        self.assertEqual(result["data"]["action_required"], action_required)


class WaveDashboardRestartUpgradeGuardTests(unittest.TestCase):
    """Tests for wf_restart_dashboard upgrade guard (AC-4 / R7)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_lock(self):
        p = self.root / ".wavefoundry" / "upgrade-in-progress.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "started_at": "2026-05-19T00:00:00+00:00",
            "from_version": "old",
            "to_version": "new",
            "pid": os.getpid(),
        }), encoding="utf-8")

    def test_restart_proceeds_while_upgrade_in_progress(self):
        """AC-4 (revised): restart is not blocked during upgrade — dashboard comes up in upgrade_paused."""
        self._write_lock()
        import sys
        mock_lib = _make_mock_dashboard_lib(self.root / ".wavefoundry" / "locks" / "dashboard-server.lock")
        with patch.dict(sys.modules, {"dashboard_lib": mock_lib}), \
             patch.object(self.srv, "_pid_is_running", return_value=False), \
             patch.object(self.srv, "wf_start_dashboard_response",
                          return_value={"status": "ok", "data": {}}):
            result = self.srv.wf_restart_dashboard_response(self.root)
        self.assertNotEqual(result["status"], "error")
        self.assertNotIn("upgrade_in_progress", result.get("data", {}))

    def test_restart_allowed_when_no_lock(self):
        """Restart proceeds normally when no upgrade lock is present."""
        # No lock file — restart should attempt to stop/start (both will find nothing running).
        # Mock wf_start_dashboard_response to avoid spawning a real dashboard process.
        import sys
        mock_lib = _make_mock_dashboard_lib(self.root / ".wavefoundry" / "locks" / "dashboard-server.lock")
        with patch.dict(sys.modules, {"dashboard_lib": mock_lib}), \
             patch.object(self.srv, "_pid_is_running", return_value=False), \
             patch.object(self.srv, "wf_start_dashboard_response",
                          return_value={"status": "ok", "data": {}}):
            result = self.srv.wf_restart_dashboard_response(self.root)
        # Should not be blocked by upgrade guard.
        self.assertNotIn("upgrade_in_progress", result.get("data", {}))


class WaveUpgradeMcpToolTests(unittest.TestCase):
    """Tests for wf_upgrade_response (AC-2–AC-5 / 12r0b)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_storage_pause_carries_external_continuation_and_rejects_stale_action(self):
        migration = self.srv._load_script("sqlite_storage_migration")
        index = self.root / ".wavefoundry/index"
        (index / "docs.lance").mkdir(parents=True, exist_ok=True)
        context = types.SimpleNamespace(
            root=self.root, from_version="1.22.0+test", to_version="1.23.0+test",
            zip_path=None, dry_run=False, storage_migration_protocol=1,
        )
        invocation_tokens = []

        def pause_child(cmd, **kwargs):
            invocation_tokens.append(kwargs["env"][migration.INVOCATION_ENV])
            stream = io.StringIO()
            with patch.dict(os.environ, {**kwargs["env"], migration.CONFIRM_ENV: "0"}), \
                 contextlib.redirect_stdout(stream):
                with self.assertRaises(SystemExit) as paused:
                    migration.prepare_upgrade(context)
            return subprocess.CompletedProcess(cmd, paused.exception.code,
                                               stdout=stream.getvalue(), stderr="")

        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=pause_child):
            result = self.srv.wf_upgrade_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["state"], "restart_required")
        self.assertIsNone(result["data"]["failed_phase"])
        action = result["data"]["action_required"]
        self.assertEqual(action["invocation_token"], invocation_tokens[0])
        self.assertIn(str(self.root.resolve()), action["command_argv"])
        self.assertIn("--confirm-hosts-stopped", action["command_argv"])
        self.assertIn("non-MCP shell", result["next_step"])
        self.assertNotIn("wf_reload_mcp", result["next_tools"])
        self.assertTrue((index / migration.RECEIPT).exists())

        # Same durable receipt, different child invocation: a real exit 3 must
        # remain an error even if its output repeats the old pause message.
        stale = subprocess.CompletedProcess([], 3, stdout=json.dumps(action), stderr="real failure")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=stale):
            failed = self.srv.wf_upgrade_response(self.root)
        self.assertEqual(failed["status"], "error")
        self.assertIn("upgrade_failed", [d["code"] for d in failed["diagnostics"]])

    def test_unbound_storage_exit_and_dry_run_do_not_become_expected_pauses(self):
        proc = subprocess.CompletedProcess([], 3, stdout='{"code":"storage_restart_required"}', stderr="")
        for mode in ("apply", "dry_run"):
            with self.subTest(mode=mode), \
                 patch.object(self.srv, "_mcp_subprocess_run", return_value=proc):
                result = self.srv.wf_upgrade_response(self.root, mode=mode)
            self.assertEqual(result["status"], "error")
            self.assertNotIn("action_required", result["data"])

    def test_invalid_phase_returns_error(self):
        result = self.srv.wf_upgrade_response(self.root, phase="bad_phase")
        self.assertEqual(result["status"], "error")
        self.assertIn("valid_phases", result["data"])

    def test_success_returns_ok_with_output(self):
        """AC-2: successful subprocess exit → status ok with output and exit_code=0."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Upgrade complete\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="preflight_to_docs_gate")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["exit_code"], 0)
        self.assertIn("Upgrade complete", result["data"]["output"])

    def test_nonzero_exit_returns_error(self):
        """AC-5: non-zero exit code → status error with output in diagnostics."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "docs-lint failed"
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="preflight_to_docs_gate")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["exit_code"], 1)
        diag_codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("upgrade_failed", diag_codes)

    def test_bridge_refusal_is_promoted_to_typed_handoff(self):
        payload = {
            "status": "error",
            "code": "bridge_release_required",
            "why": "the live runner cannot replace itself",
            "package": "/tmp/wavefoundry-1.15.0.zip",
            "package_present": True,
            "command_argv": ["python3", "/tmp/wavefoundry-1.15.0.zip"],
        }
        mock_proc = MagicMock(
            returncode=3, stdout=json.dumps(payload) + "\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["diagnostics"][0]["code"], "bridge_release_required"
        )
        self.assertEqual(result["data"]["bridge_release_required"], payload)
        self.assertNotIn(
            "upgrade_failed", [item["code"] for item in result["diagnostics"]]
        )
        self.assertIn("restart every attached host", result["next_step"])

    def test_bridge_refusal_parses_complete_output_but_returns_bounded_display(self):
        payload = {
            "status": "error",
            "code": "bridge_release_required",
            "why": "the live runner cannot replace itself",
            "package": "/tmp/wavefoundry-1.15.0.zip",
            "package_present": True,
            "command_argv": ["python3", "/tmp/wavefoundry-1.15.0.zip"],
        }
        stdout = ("seed diff detail\n" * 30_000) + json.dumps(payload) + "\n"
        self.assertGreater(len(stdout), 300_000)
        mock_proc = MagicMock(returncode=3, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)
        self.assertEqual(result["data"]["bridge_release_required"], payload)
        self.assertTrue(result["data"]["output_truncated"])
        self.assertEqual(result["data"]["output_total_chars"], len(stdout))
        self.assertLess(len(result["data"]["output"]), 61_000)
        self.assertIn("see log_path", result["data"]["output"])

    def test_repo_sized_summary_keeps_complete_envelope_below_public_cap(self):
        findings = [
            {
                "file": f"docs/agents/carrier-{index:05d}.md",
                "line": index + 1,
                "retired_surface": "reviewer loop",
                "matched": "reviewer loop",
                "suggested": "Use Review wave and a typed repair cycle.",
            }
            for index in range(10_000)
        ]
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            "reconciliation": findings,
            "host_permission_flags": list(findings),
            "skipped_scan_locations": [],
            "retired_model_cleanup_status": "failed",
            "retired_model_cleanup_removed": ["fastembed:default:retired-a"],
            "retired_model_cleanup_absent": ["clean-onnx:default:retired-b"],
            "retired_model_cleanup_unowned": ["fastembed:custom:retired-c"],
            "retired_model_cleanup_failed": ["coreml:default:retired-d|remove_failed"],
        }
        stdout = (
            ("seed diff detail\n" * 30_000)
            + self.srv._upgrade_summary_sentinel()
            + json.dumps(summary)
            + "\n"
        )
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        envelope_chars = len(json.dumps(result, ensure_ascii=False))
        self.assertLessEqual(envelope_chars, self.srv.UPGRADE_RESPONSE_CAP_CHARS)
        self.assertTrue(result["data"]["output_truncated"])
        bounded = result["data"]["summary"]
        self.assertTrue(bounded["summary_truncated"])
        self.assertEqual(bounded["reconciliation_total"], 10_000)
        self.assertGreater(bounded["reconciliation_remaining"], 0)
        self.assertEqual(
            bounded["reconciliation_returned"]
            + bounded["reconciliation_remaining"],
            bounded["reconciliation_total"],
        )
        self.assertEqual(bounded["host_permission_flags_total"], 10_000)
        self.assertGreater(bounded["summary_total_chars"], 900_000)
        self.assertEqual(
            {key: bounded[key] for key in self.srv.RETIRED_MODEL_CLEANUP_KEYS},
            {
                "retired_model_cleanup_status": "failed",
                "retired_model_cleanup_removed": ["fastembed:default:retired-a"],
                "retired_model_cleanup_absent": ["clean-onnx:default:retired-b"],
                "retired_model_cleanup_unowned": ["fastembed:custom:retired-c"],
                "retired_model_cleanup_failed": ["coreml:default:retired-d|remove_failed"],
            },
        )
        self.assertEqual(
            result["data"]["log_path"],
            str(self.root / ".wavefoundry/logs/upgrade.log"),
        )

    def test_summary_cleanup_projection_drops_paths_and_exception_text(self):
        summary = {
            "retired_model_cleanup_status": "failed",
            "retired_model_cleanup_removed": ["/private/operator/model"],
            "retired_model_cleanup_absent": ["coreml:default:retired-ok"],
            "retired_model_cleanup_unowned": ["OSError: errno 13"],
            "retired_model_cleanup_failed": [
                "coreml:default:retired-bad|/private/cache",
                "coreml:default:retired-failed|remove_failed",
            ],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout=stdout, stderr=""),
        ):
            result = self.srv.wf_upgrade_response(self.root)
        bounded = result["data"]["summary"]
        self.assertEqual(bounded["retired_model_cleanup_removed"], [])
        self.assertEqual(
            bounded["retired_model_cleanup_absent"],
            ["coreml:default:retired-ok"],
        )
        self.assertEqual(bounded["retired_model_cleanup_unowned"], [])
        self.assertEqual(
            bounded["retired_model_cleanup_failed"],
            ["coreml:default:retired-failed|remove_failed"],
        )

    def test_write_tier_permissions_delta_survives_bounding_with_counts(self):
        """Wave 1u2b0 repair (F1): the operator's permissions consent point must survive the
        summary bounder on the WRITE tier, which is the render that most needs consent.

        Known bad this pins: as a single dict value the delta exceeded
        UPGRADE_SUMMARY_VALUE_CAP_CHARS and came back as ``None`` with a truncated flag. As two
        top-level LISTS plus a scalar count it routes through the collection bounder, which yields
        total / returned / remaining / truncated instead of dropping the value. The rules come from
        the canonical producer (``mcp_tool_roster.allow_rules``), not hand-written strings.
        """
        import mcp_tool_roster

        added = list(mcp_tool_roster.allow_rules(include_write=True))
        removed = [
            "mcp__wavefoundry__wave_close",
            "mcp__wavefoundry__wave_review",
            "mcp__wavefoundry__wave_implement",
        ]
        # NOTE the name: allow_rules(include_write=True) returns read UNION write, so this
        # count moves on a READ-tier add too (1vqqi: wf_techdocs_audit took it 89 -> 90).
        self.assertEqual(len(added), 90, "roster size changed; re-measure this test")

        # Non-vacuity control: the retired dict shape is still over the per-value cap, so this
        # test would fail against the pre-repair producer/consumer pair.
        legacy_value_chars = len(
            json.dumps(
                {
                    "file": ".claude/settings.json",
                    "added": added,
                    "removed": removed,
                    "changed": True,
                },
                ensure_ascii=False,
            )
        )
        self.assertGreater(legacy_value_chars, self.srv.UPGRADE_SUMMARY_VALUE_CAP_CHARS)
        legacy_bounded = self.srv._bounded_upgrade_summary(
            {
                "from_version": "1.14.0",
                "to_version": "1.15.0",
                "permissions_delta": {
                    "file": ".claude/settings.json",
                    "added": added,
                    "removed": removed,
                    "changed": True,
                },
            }
        )
        self.assertIsNone(legacy_bounded["permissions_delta"])
        self.assertTrue(legacy_bounded["permissions_delta_truncated"])

        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            "permissions_file": ".claude/settings.json",
            "permissions_added": added,
            "permissions_removed": removed,
            "permissions_changed": len(added) + len(removed),
            "reconciliation": [],
            "host_permission_flags": [],
            "renderer_provenance_flags": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        bounded = result["data"]["summary"]
        self.assertEqual(bounded["permissions_added"], added)
        self.assertEqual(bounded["permissions_added_total"], len(added))
        self.assertEqual(bounded["permissions_added_returned"], len(added))
        self.assertEqual(bounded["permissions_added_remaining"], 0)
        self.assertFalse(bounded["permissions_added_truncated"])
        self.assertEqual(bounded["permissions_removed"], removed)
        self.assertEqual(bounded["permissions_removed_total"], len(removed))
        self.assertFalse(bounded["permissions_removed_truncated"])
        self.assertEqual(bounded["permissions_changed"], len(added) + len(removed))
        self.assertEqual(bounded["permissions_file"], ".claude/settings.json")
        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )

    def test_unchanged_permissions_delta_reports_zero_not_absent(self):
        """A no-change render still names the consent field: empty lists plus a zero count, so
        the operator can tell "nothing changed" from "the field was dropped"."""
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            "permissions_added": [],
            "permissions_removed": [],
            "permissions_changed": 0,
            "reconciliation": [],
            "host_permission_flags": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)
        bounded = result["data"]["summary"]
        self.assertEqual(bounded["permissions_added"], [])
        self.assertEqual(bounded["permissions_added_total"], 0)
        self.assertFalse(bounded["permissions_added_truncated"])
        self.assertEqual(bounded["permissions_changed"], 0)

    def test_oversized_summary_scalar_and_nested_detail_cannot_bypass_cap(self):
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            "unexpected_detail": "x" * 180_000,
            "future_nested_detail": {
                "rows": [{"body": "y" * 10_000} for _ in range(20)]
            },
            "reconciliation": [],
            "host_permission_flags": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        bounded = result["data"]["summary"]
        self.assertIsNone(bounded["unexpected_detail"])
        self.assertTrue(bounded["unexpected_detail_truncated"])
        self.assertGreater(bounded["unexpected_detail_total_chars"], 180_000)
        self.assertIsNone(bounded["future_nested_detail"])
        self.assertTrue(bounded["future_nested_detail_truncated"])
        self.assertTrue(bounded["summary_truncated"])
        self.assertEqual(bounded["from_version"], "1.14.0")
        self.assertEqual(bounded["docs_gate"], "PASSED")

    def test_many_individually_small_unknown_summary_scalars_cannot_bypass_cap(self):
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            **{
                f"future_scalar_{index:03d}": "x" * 1_900
                for index in range(80)
            },
            "reconciliation": [],
            "host_permission_flags": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        bounded = result["data"]["summary"]
        self.assertTrue(bounded["summary_truncated"])
        self.assertGreater(bounded["summary_scalar_fields_truncated"], 0)
        self.assertLess(
            bounded["summary_scalar_fields_returned"],
            bounded["summary_scalar_fields_total"],
        )
        self.assertEqual(bounded["from_version"], "1.14.0")
        self.assertEqual(bounded["to_version"], "1.15.0")
        self.assertEqual(bounded["docs_gate"], "PASSED")

    def test_many_omitted_scalar_metadata_records_preserve_terminal_summary(self):
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            **{
                f"future_scalar_{index:03d}_{'k' * 96}": "x" * 1_900
                for index in range(320)
            },
            "reconciliation": [],
            "host_permission_flags": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        bounded = result["data"]["summary"]
        self.assertEqual(bounded["from_version"], "1.14.0")
        self.assertEqual(bounded["to_version"], "1.15.0")
        self.assertEqual(bounded["docs_gate"], "PASSED")
        self.assertGreater(bounded["summary_scalar_fields_omitted"], 0)
        self.assertGreater(
            bounded["summary_scalar_metadata_fields_omitted"],
            0,
        )
        self.assertLessEqual(
            bounded["summary_scalar_metadata_returned_chars"],
            bounded["summary_scalar_metadata_cap_chars"],
        )

    def test_oversized_unknown_summary_key_cannot_bypass_cap(self):
        oversized_key = "future_" + ("k" * 140_000)
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            oversized_key: "x",
            "reconciliation": [],
            "host_permission_flags": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        bounded = result["data"]["summary"]
        self.assertTrue(bounded["summary_truncated"])
        self.assertEqual(bounded["summary_oversized_key_fields_omitted"], 1)
        self.assertGreater(bounded["summary_oversized_key_chars_total"], 100_000)
        self.assertNotIn(oversized_key, bounded)
        self.assertEqual(bounded["from_version"], "1.14.0")
        self.assertEqual(bounded["docs_gate"], "PASSED")

    def test_oversized_unknown_collection_key_preserves_terminal_summary(self):
        oversized_key = "future_" + ("k" * 140_000)
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            oversized_key: [],
            "reconciliation": [],
            "host_permission_flags": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        bounded = result["data"]["summary"]
        self.assertEqual(bounded["from_version"], "1.14.0")
        self.assertEqual(bounded["to_version"], "1.15.0")
        self.assertEqual(bounded["docs_gate"], "PASSED")
        self.assertEqual(bounded["summary_oversized_key_fields_omitted"], 1)
        self.assertEqual(bounded["summary_collection_fields_omitted"], 1)
        self.assertNotIn(oversized_key, bounded)

    def test_many_empty_unknown_collections_preserve_terminal_summary(self):
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            **{
                f"future_collection_{index:03d}_{'k' * 96}": []
                for index in range(160)
            },
            "reconciliation": [],
            "host_permission_flags": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        bounded = result["data"]["summary"]
        self.assertEqual(bounded["from_version"], "1.14.0")
        self.assertEqual(bounded["to_version"], "1.15.0")
        self.assertEqual(bounded["docs_gate"], "PASSED")
        self.assertGreater(bounded["summary_collection_fields_omitted"], 0)
        self.assertLess(
            bounded["summary_collection_fields_returned"],
            bounded["summary_collection_fields_total"],
        )
        self.assertTrue(bounded["summary_truncated"])

    def test_unknown_exit_three_retains_generic_failure(self):
        mock_proc = MagicMock(returncode=3, stdout='{"code":"different"}\n', stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)
        self.assertEqual(result["diagnostics"][0]["code"], "upgrade_failed")

    def test_bridge_payload_prose_and_unknown_fields_cannot_bypass_cap(self):
        argv = ["python3", "/tmp/wavefoundry-1.15.0.zip", "--root", "/tmp/repo"]
        payload = {
            "status": "error",
            "code": "bridge_release_required",
            "why": "x" * 180_000,
            "package": "/tmp/wavefoundry-1.15.0.zip",
            "package_present": True,
            "command_argv": argv,
            "unexpected_detail": {"body": "y" * 180_000},
        }
        mock_proc = MagicMock(
            returncode=3, stdout=json.dumps(payload) + "\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        handoff = result["data"]["bridge_release_required"]
        self.assertEqual(handoff["command_argv"], argv)
        self.assertEqual(handoff["omitted_field_count"], 1)
        self.assertEqual(handoff["text_truncated_fields"], ["why"])
        self.assertNotIn("unexpected_detail", handoff)
        self.assertEqual(result["diagnostics"][0]["code"], "bridge_release_required")
        self.assertIn("restart every attached host", result["next_step"])

    def test_bridge_payload_aggregate_argv_cannot_bypass_cap(self):
        payload = {
            "status": "error",
            "code": "bridge_release_required",
            "why": "the live runner cannot replace itself",
            "package": "/tmp/wavefoundry-1.15.0.zip",
            "package_present": True,
            "command_argv": ["x" * 4_096 for _ in range(32)],
        }
        mock_proc = MagicMock(
            returncode=3, stdout=json.dumps(payload) + "\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        self.assertNotIn("bridge_release_required", result["data"])
        self.assertEqual(result["diagnostics"][0]["code"], "upgrade_failed")

    def test_bridge_payload_wrong_typed_protocol_detail_cannot_bypass_cap(self):
        payload = {
            "status": "error",
            "code": "bridge_release_required",
            "runner_protocol": {"future": "r" * 180_000},
            "minimum_runner_protocol": 2,
            "why": "the live runner cannot replace itself",
            "package": "/tmp/wavefoundry-1.15.0.zip",
            "package_present": True,
            "command_argv": ["python3", "/tmp/wavefoundry-1.15.0.zip"],
        }
        mock_proc = MagicMock(
            returncode=3, stdout=json.dumps(payload) + "\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        self.assertNotIn("bridge_release_required", result["data"])
        self.assertEqual(result["diagnostics"][0]["code"], "upgrade_failed")

    def test_bridge_payload_argv_uses_serialized_wire_budget(self):
        payload = {
            "status": "error",
            "code": "bridge_release_required",
            "runner_protocol": 1,
            "minimum_runner_protocol": 2,
            "why": "the live runner cannot replace itself",
            "package": "/tmp/wavefoundry-1.15.0.zip",
            "package_present": True,
            "command_argv": ["\u0001" * 4_000 for _ in range(6)],
        }
        self.assertEqual(
            sum(len(item) for item in payload["command_argv"]),
            self.srv.UPGRADE_BRIDGE_ARGV_CAP_CHARS,
        )
        self.assertGreater(
            len(json.dumps(payload["command_argv"], ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        mock_proc = MagicMock(
            returncode=3, stdout=json.dumps(payload) + "\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        self.assertNotIn("bridge_release_required", result["data"])
        self.assertEqual(result["diagnostics"][0]["code"], "upgrade_failed")

    def test_terminal_response_compaction_bounds_diagnostic_keys(self):
        result = self.srv._bounded_upgrade_response_envelope(
            {
                "status": "error",
                "data": {"phase": "preflight_to_docs_gate"},
                "diagnostics": [{"code": "c" * 180_000, "message": "small"}],
            }
        )
        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        self.assertEqual(
            len(result["diagnostics"][0]["code"]),
            self.srv.UPGRADE_SUMMARY_KEY_CAP_CHARS,
        )

    def test_terminal_response_compaction_bounds_retained_bridge_detail(self):
        argv = ["python3", "/tmp/wavefoundry-1.15.0.zip"]
        result = self.srv._bounded_upgrade_response_envelope(
            {
                "status": "error",
                "data": {
                    "phase": "preflight_to_docs_gate",
                    "log_path": "/tmp/upgrade.log",
                    "bridge_release_required": {
                        "status": "error",
                        "code": "bridge_release_required",
                        "package": "/tmp/wavefoundry-1.15.0.zip",
                        "package_present": True,
                        "command_argv": argv,
                        "future_detail": {"body": "x" * 180_000},
                    },
                },
                "diagnostics": [
                    {"code": "bridge_release_required", "message": "bridge required"}
                ],
            }
        )
        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        handoff = result["data"]["bridge_release_required"]
        self.assertEqual(handoff["command_argv"], argv)
        self.assertTrue(handoff["handoff_compacted"])
        self.assertNotIn("future_detail", handoff)

    def test_spawn_failure_diagnostic_cannot_bypass_cap(self):
        with patch("subprocess.run", side_effect=OSError("x" * 180_000)):
            result = self.srv.wf_upgrade_response(self.root)

        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False)),
            self.srv.UPGRADE_RESPONSE_CAP_CHARS,
        )
        diagnostic = result["diagnostics"][0]
        self.assertEqual(diagnostic["code"], "spawn_failed")
        self.assertTrue(diagnostic["message_truncated"])
        self.assertGreater(diagnostic["message_total_chars"], 100_000)
        self.assertLess(len(diagnostic["message"]), 3_000)

    def test_action_required_exit_exposes_structured_memory_gate(self):
        mock_proc = MagicMock(returncode=4, stdout="paused\n", stderr="")
        backfill = MagicMock()
        backfill.run_summary.return_value = {
            "run_id": "run-2",
            "state": "awaiting_validation",
            "candidates_pending": 1,
            "promoted": 3,
            "last_failure": "",
        }
        backfill.validation_worklist.return_value = {
            "validation_worklist": [{"memory_id": "1abd-memory"}],
            "validation_worklist_count": 1,
            "validation_worklist_remaining": 0,
        }
        lock = {
            "memory_backfill_run_id": "run-2",
            "action_required": {
                "kind": "historical_memory",
                "state": "awaiting_memory_validation",
                "resume_phase": "resume_after_memory",
                "run_id": "run-2",
                "token": "test-token",
            },
        }
        upgrade_lib = types.SimpleNamespace(read_upgrade_lock=lambda _root: lock)
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(self.srv, "_load_upgrade_lib", return_value=upgrade_lib), \
             patch.object(self.srv, "_load_script", return_value=backfill):
            result = self.srv.wf_upgrade_response(self.root)
        self.assertEqual(result["data"]["state"], "awaiting_memory_validation")
        gate = result["data"]["memory_backfill"]
        self.assertEqual(gate["run_id"], "run-2")
        self.assertEqual(gate["candidates_pending"], 1)
        self.assertEqual(gate["validation_worklist"][0]["memory_id"], "1abd-memory")

    def test_publication_ready_exit_exposes_post_reload_recovery_contract(self):
        mock_proc = MagicMock(returncode=4, stdout="publication checkpoint\n", stderr="")
        backfill = MagicMock()
        backfill.run_summary.return_value = {
            "run_id": "run-publication", "state": "ready_for_index",
            "candidates_pending": 0, "promoted": 2, "last_failure": "",
        }
        backfill.validation_worklist.return_value = {
            "validation_worklist": [], "validation_worklist_count": 0,
            "validation_worklist_remaining": 0,
        }
        action_required = {
            "kind": "historical_memory",
            "state": "awaiting_memory_publication",
            "resume_phase": "resume_after_memory",
            "run_id": "run-publication",
            "token": "publication-token",
        }
        lock = {
            "memory_backfill_run_id": "run-publication",
            "current_phase": "awaiting_memory_publication",
            "failed_phase": "awaiting_memory_validation",
            "action_required": action_required,
        }
        upgrade_lib = types.SimpleNamespace(read_upgrade_lock=lambda _root: lock)
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(self.srv, "_load_upgrade_lib", return_value=upgrade_lib), \
             patch.object(self.srv, "_load_script", return_value=backfill):
            result = self.srv.wf_upgrade_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["state"], "awaiting_memory_publication")
        self.assertEqual(result["data"]["failed_phase"], None)
        self.assertEqual(result["data"]["action_required"], action_required)
        self.assertEqual(
            result["next_tools"], ["wf_reload_mcp", "wf_upgrade_status", "wf_upgrade"]
        )
        self.assertIn("resume_after_memory", result["next_step"])
        self.assertIn("publish", result["next_step"])
        self.assertIn("publication checkpoint", result["data"]["output"])

    def test_action_required_exit_without_action_record_is_error(self):
        mock_proc = MagicMock(returncode=4, stdout="failed\n", stderr="")
        upgrade_lib = types.SimpleNamespace(
            read_upgrade_lock=lambda _root: {"memory_backfill_run_id": "run-2"}
        )
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(self.srv, "_load_upgrade_lib", return_value=upgrade_lib):
            result = self.srv.wf_upgrade_response(self.root)
        self.assertEqual(result["status"], "error")
        self.assertNotEqual(result.get("data", {}).get("state"), "awaiting_memory_validation")

    def test_update_index_phase_passes_flag(self):
        """AC-3a: update_index phase passes --update-index (incremental)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Index updated\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            self.srv.wf_upgrade_response(self.root, phase="update_index")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--update-index", called_cmd)
        self.assertNotIn("--rebuild-index", called_cmd)

    def test_rebuild_index_phase_passes_flag(self):
        """AC-3b: rebuild_index phase passes --rebuild-index (full rebuild)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Index rebuilt\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            self.srv.wf_upgrade_response(self.root, phase="rebuild_index")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--rebuild-index", called_cmd)
        self.assertNotIn("--update-index", called_cmd)

    def test_cleanup_phase_passes_flag(self):
        """AC-4: cleanup phase passes --cleanup flag."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Lock removed\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            self.srv.wf_upgrade_response(self.root, phase="cleanup")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--cleanup", called_cmd)

    def test_resume_after_gate_phase_passes_flag(self):
        """Wave 1p44r AC-7: resume_after_gate is a valid phase and maps to
        --resume-after-gate."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Docs gate PASSED on resume\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            result = self.srv.wf_upgrade_response(self.root, phase="resume_after_gate", mode="apply")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--resume-after-gate", called_cmd)
        self.assertNotEqual(result.get("status"), "error")
        self.assertIn("resume_after_memory", result["next_step"])
        self.assertNotIn("phase='update_index'", result["next_step"])

    def test_resume_after_gate_nonzero_exit_is_error(self):  # wave 1p44r AC-5 (delivery review)
        # A repeated docs-gate failure (exit 1) on resume must map to status=error
        # so the caller detects it (the exit-code mapping is phase-agnostic).
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Docs gate still failing"
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="resume_after_gate", mode="apply")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["exit_code"], 1)
        self.assertIn("upgrade_failed", [d["code"] for d in result.get("diagnostics", [])])
        self.assertIn("retry wf_upgrade(phase='resume_after_gate')", result["next_step"])
        self.assertNotIn("update_index", result["next_step"])
        self.assertNotIn("phase='cleanup'", result["next_step"])
        self.assertEqual(
            result["next_tools"], ["wf_upgrade_status", "wf_upgrade"]
        )

    def test_projection_backstop_failure_is_not_misreported_as_memory_action(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = (
            "Review-state migration requires operator action before index "
            "publication. Run --resume-after-gate."
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(
                self.root, phase="update_index", mode="apply"
            )
        self.assertEqual(result["status"], "error")
        self.assertNotEqual(result.get("data", {}).get("state"), "awaiting_memory_validation")
        self.assertIn("retry wf_upgrade(phase='resume_after_gate')", result["next_step"])
        self.assertNotIn("phase='cleanup'", result["next_step"])
        self.assertEqual(
            result["next_tools"], ["wf_upgrade_status", "wf_upgrade"]
        )

    def test_dry_run_mode_passes_flag_and_omits_yes(self):
        """mode='dry_run' passes --dry-run and must NOT pass --yes (read-only, no prompt)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Dry Run\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            result = self.srv.wf_upgrade_response(self.root, mode="dry_run")
        self.assertEqual(result["status"], "ok")
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--dry-run", called_cmd)
        self.assertNotIn("--yes", called_cmd)

    def test_dry_run_summary_exposes_cleanup_sentinel(self):
        summary = {
            "from_version": "1.15.9",
            "to_version": "1.16.0",
            "retired_model_cleanup_status": "dry_run",
            "retired_model_cleanup_removed": [],
            "retired_model_cleanup_absent": [],
            "retired_model_cleanup_unowned": [],
            "retired_model_cleanup_failed": [],
        }
        mock_proc = MagicMock(
            returncode=0,
            stdout=self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, mode="dry_run")
        self.assertEqual(
            {key: result["data"]["summary"][key] for key in self.srv.RETIRED_MODEL_CLEANUP_KEYS},
            {key: summary[key] for key in self.srv.RETIRED_MODEL_CLEANUP_KEYS},
        )

    def test_invalid_mode_returns_error(self):
        """Unknown mode returns error with valid_modes list."""
        result = self.srv.wf_upgrade_response(self.root, mode="bad_mode")
        self.assertEqual(result["status"], "error")
        self.assertIn("valid_modes", result["data"])

    def test_cleanup_apply_invokes_mcp_reload(self):
        """AC-3: wf_upgrade cleanup+apply triggers in-process MCP reload.

        When phase='cleanup' and mode='apply' succeed, wf_upgrade_response
        must call server.perform_mcp_reload() and include its result under
        data['mcp_reload'].
        """
        import server as _server_mod
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Lock removed\n"
        mock_proc.stderr = ""
        reload_payload = {
            "status": "ok",
            "data": {"ok": True, "framework_version": "v1",
                     "server_runner_version": "0a1b2c3d4e5f",
                     "runner_disk_identity": "0a1b2c3d4e5f", "runner_stale": False,
                     "server_impl_version": "v1", "impl_matches_disk": True,
                     "tool_list_changed_notification_dispatch": "scheduled"},
            "diagnostics": [{
                "code": "tool_list_changed_notification_scheduled",
                "message": "Check from a fresh turn, reconnect, then restart.",
            }],
        }
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(_server_mod, "perform_mcp_reload", return_value=reload_payload) as mock_reload:
            result = self.srv.wf_upgrade_response(self.root, phase="cleanup", mode="apply")
        self.assertEqual(result["status"], "ok")
        mock_reload.assert_called_once()
        self.assertIn("mcp_reload", result["data"])
        self.assertTrue(result["data"]["mcp_reload"]["ok"])
        self.assertIn(
            "tool_list_changed_notification_scheduled",
            [item["code"] for item in result.get("diagnostics", [])],
        )

    def test_cleanup_apply_preserves_real_reload_wire_and_escalation_response(self):
        """The upgrade caller exercises the unmocked scheduled reload contract."""
        import server as _server_mod

        mock_proc = MagicMock(returncode=0, stdout="Lock removed\n", stderr="")
        try:
            mcp = _server_mod.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        async def exercise():
            import anyio
            from mcp import types as mcp_types
            from mcp.server.models import InitializationOptions
            from mcp.server.session import ServerSession

            inbound_send, inbound_receive = anyio.create_memory_object_stream(1)
            wire_send, wire_receive = anyio.create_memory_object_stream(1)
            session = ServerSession(
                inbound_receive,
                wire_send,
                InitializationOptions(
                    server_name="wavefoundry-upgrade-test",
                    server_version="test",
                    capabilities=mcp_types.ServerCapabilities(),
                ),
            )
            context = types.SimpleNamespace(
                request_context=types.SimpleNamespace(session=session)
            )
            async with session:
                with patch(
                    "subprocess.run", return_value=mock_proc
                ), patch.object(
                    mcp, "get_context", return_value=context
                ), patch.object(
                    _server_mod,
                    "_refresh_mcp_tool_surface",
                    return_value=(1, [], ["memory_purge"], [], []),
                ):
                    result = self.srv.wf_upgrade_response(
                        self.root, phase="cleanup", mode="apply"
                    )
                wire_message = await wire_receive.receive()
            await inbound_send.aclose()
            await inbound_receive.aclose()
            await wire_send.aclose()
            await wire_receive.aclose()
            return result, wire_message

        result, wire_message = asyncio.run(exercise())
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(
            wire_message.message.model_dump(by_alias=True)["method"],
            "notifications/tools/list_changed",
        )
        reload_data = result["data"]["mcp_reload"]
        self.assertEqual(
            reload_data["tool_list_changed_notification_dispatch"], "scheduled"
        )
        self.assertNotIn("tool_list_changed_notification_sent", reload_data)
        scheduled = [
            item
            for item in result["diagnostics"]
            if item["code"] == "tool_list_changed_notification_scheduled"
        ]
        self.assertEqual(len(scheduled), 1)
        for rung in ("fresh", "reconnect", "restart"):
            self.assertIn(rung, scheduled[0]["message"].lower())

    # ── Wave 1to78 — cutover-scoped reload suppression (AC-3) ─────────────────

    def _cutover_summary_output(self, restart_required):
        return self._summary_output(
            review_sidecar_cleanup={
                "removed_sidecars": 2,
                "removed_stale_root_lock": 1,
                "restart_required": restart_required,
            }
        )

    def test_cutover_active_preflight_apply_performs_no_reload(self):
        """AC-3 executed control: a cutover-active preflight_to_docs_gate apply
        run performs NO in-process reload and instructs a full host restart."""
        import server as _server_mod
        mock_proc = MagicMock(
            returncode=0, stdout=self._cutover_summary_output(True), stderr=""
        )
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(_server_mod, "perform_mcp_reload") as mock_reload:
            result = self.srv.wf_upgrade_response(
                self.root, phase="preflight_to_docs_gate", mode="apply"
            )
        self.assertEqual(result["status"], "ok")
        mock_reload.assert_not_called()
        self.assertNotIn("mcp_reload", result["data"])
        self.assertNotIn("wf_reload_mcp", result["next_tools"])
        self.assertIn("fully restart", result["next_step"])
        self.assertIn(
            "mcp_reload_suppressed",
            [d["code"] for d in result.get("diagnostics", [])],
        )

    def test_cutover_active_cleanup_apply_performs_no_reload(self):
        """AC-3: the cleanup phase (the second automatic-reload site) is also
        suppressed on cutover-active runs; next_step drops the wf_reload_mcp
        suggestion for the full-restart instruction."""
        import server as _server_mod
        mock_proc = MagicMock(
            returncode=0, stdout=self._cutover_summary_output(True), stderr=""
        )
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(_server_mod, "perform_mcp_reload") as mock_reload:
            result = self.srv.wf_upgrade_response(
                self.root, phase="cleanup", mode="apply"
            )
        self.assertEqual(result["status"], "ok")
        mock_reload.assert_not_called()
        self.assertNotIn("mcp_reload", result["data"])
        self.assertNotIn("wf_reload_mcp", result["next_tools"])
        self.assertNotIn("Call wf_reload_mcp()", result["next_step"])
        self.assertIn("fully restart", result["next_step"])

    def test_non_cutover_preflight_apply_keeps_reload_flow(self):
        """AC-3: a non-cutover run (restart_required false in the summary)
        keeps the established reload behavior and guidance untouched."""
        import server as _server_mod
        mock_proc = MagicMock(
            returncode=0, stdout=self._cutover_summary_output(False), stderr=""
        )
        reload_payload = {
            "status": "ok",
            "data": {"ok": True, "framework_version": "v1",
                     "server_runner_version": "0a1b2c3d4e5f",
                     "runner_disk_identity": "0a1b2c3d4e5f", "runner_stale": False,
                     "server_impl_version": "v1", "impl_matches_disk": True},
        }
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(_server_mod, "perform_mcp_reload",
                          return_value=reload_payload) as mock_reload:
            result = self.srv.wf_upgrade_response(
                self.root, phase="preflight_to_docs_gate", mode="apply"
            )
        self.assertEqual(result["status"], "ok")
        mock_reload.assert_called_once()
        self.assertIn("mcp_reload", result["data"])
        self.assertIn("wf_reload_mcp", result["next_tools"])
        self.assertNotIn("fully restart", result["next_step"])

    def test_cutover_detection_falls_back_to_upgrade_lock_state(self):
        """AC-3: when the summary sentinel is absent, the retained upgrade
        lock's review_sidecar_cleanup counts still gate the reload."""
        import json as _json
        import server as _server_mod
        lock_path = self.root / ".wavefoundry" / "upgrade-in-progress.json"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(
            _json.dumps(
                {
                    "review_sidecar_cleanup": {
                        "removed_sidecars": 1,
                        "removed_stale_root_lock": 0,
                        "restart_required": True,
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        mock_proc = MagicMock(returncode=0, stdout="Upgrade complete\n", stderr="")
        with patch("subprocess.run", return_value=mock_proc), \
             patch.object(_server_mod, "perform_mcp_reload") as mock_reload:
            result = self.srv.wf_upgrade_response(
                self.root, phase="preflight_to_docs_gate", mode="apply"
            )
        self.assertEqual(result["status"], "ok")
        mock_reload.assert_not_called()
        self.assertNotIn("mcp_reload", result["data"])
        self.assertNotIn("wf_reload_mcp", result["next_tools"])

    # ── Wave 1p8eu — structured summary parse + next_step/next_tools ──────────

    def _summary_output(self, **overrides):
        import json as _json
        summary = {
            "from_version": "1.5.0", "to_version": "1.6.0", "zip_applied": None,
            "pruned_count": 3, "docs_gate": "PASSED",
            # 1u44n value domain: this is the SUCCESS value ("publication
            # observed successful"); the failed domain value starts with
            # "publication failed" and is exercised by
            # test_failed_publication_summary_carries_index_health_diagnostic.
            "index_update": "docs and code layers complete",
            "failed_phase": None, "is_major_or_minor": True,
            "reconciliation": [
                {"file": "docs/x.md", "line": 4, "retired_surface": "docs-lint",
                 "suggested": "wf docs-lint"},
            ],
        }
        summary.update(overrides)
        return "Upgrade complete\nFiles pruned:       3\nWAVE_UPGRADE_SUMMARY_JSON:" + _json.dumps(summary) + "\n"

    def test_summary_parsed_into_data(self):
        """AC-2: the sentinel summary is parsed into data['summary'] with all fields."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = self._summary_output()
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="update_index")
        self.assertEqual(result["status"], "ok")
        summary = result["data"]["summary"]
        for key in ("from_version", "to_version", "pruned_count", "docs_gate",
                    "index_update", "failed_phase", "is_major_or_minor", "reconciliation"):
            self.assertIn(key, summary)
        self.assertEqual(summary["pruned_count"], 3)
        self.assertEqual(summary["reconciliation"][0]["retired_surface"], "docs-lint")
        # Back-compat: output + exit_code unchanged/present.
        self.assertEqual(result["data"]["exit_code"], 0)
        self.assertIn("Upgrade complete", result["data"]["output"])

    def test_failed_publication_summary_carries_index_health_diagnostic(self):
        """1u44n (AC-4): a zero-exit run whose summary reports a failed
        publication carries a diagnostic naming index_health."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = self._summary_output(
            index_update=(
                "publication failed: semantic index epoch incomplete; run "
                "index_build, then confirm with index_health"
            ),
        )
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(
                self.root, phase="preflight_to_docs_gate"
            )
        self.assertEqual(result["status"], "ok")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("index_publication_failed", codes)
        diag = next(
            d for d in result["diagnostics"]
            if d["code"] == "index_publication_failed"
        )
        self.assertIn("index_health", diag["message"])
        self.assertIn("index_health", diag.get("recovery_tools", []))

    def test_standalone_index_failure_not_mislabelled_as_docs_gate(self):
        """1u44n (AC-4): the standalone index phases reuse exit 1; an observed
        publication failure is labelled as such and carries the diagnostic."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = (
            "Index publication FAILED: Docs index update exited 7; the "
            "semantic index epoch is incomplete. Recover with index_build, "
            "then confirm with index_health.\n"
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="update_index")
        self.assertEqual(result["status"], "error")
        upgrade_failed = next(
            d for d in result["diagnostics"] if d["code"] == "upgrade_failed"
        )
        self.assertIn("index publication failed", upgrade_failed["message"])
        self.assertNotIn("docs gate", upgrade_failed["message"])
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("index_publication_failed", codes)

    def test_successful_summary_carries_no_publication_diagnostic(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = self._summary_output()
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(
                self.root, phase="preflight_to_docs_gate"
            )
        self.assertEqual(result["status"], "ok")
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertNotIn("index_publication_failed", codes)

    def test_next_step_and_next_tools_present(self):
        """AC-2: a top-level next_step and a populated next_tools are added."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = self._summary_output()
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="update_index")
        self.assertIn("next_step", result)
        self.assertTrue(result["next_step"])
        self.assertIn("wf_upgrade_status", result["next_tools"])

    def test_missing_summary_falls_back_to_output(self):
        """AC-3: an absent sentinel → no data['summary'], output preserved, no exception."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Upgrade complete\nFiles pruned:       0\n"  # no sentinel line
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="update_index")
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("summary", result["data"])
        self.assertIn("Upgrade complete", result["data"]["output"])
        self.assertEqual(result["data"]["exit_code"], 0)

    def test_corrupt_summary_falls_back_to_output(self):
        """AC-3: a malformed sentinel JSON → no data['summary'], output preserved, no exception."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Upgrade complete\nWAVE_UPGRADE_SUMMARY_JSON:{not valid json,,}\n"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="update_index")
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("summary", result["data"])
        self.assertIn("Upgrade complete", result["data"]["output"])

    def test_parse_upgrade_summary_helper_fail_safe(self):
        """The parse helper returns None on absent/malformed input without raising."""
        self.assertIsNone(self.srv._parse_upgrade_summary(""))
        self.assertIsNone(self.srv._parse_upgrade_summary("no sentinel here"))
        self.assertIsNone(self.srv._parse_upgrade_summary("WAVE_UPGRADE_SUMMARY_JSON:[1,2,3]"))  # not a dict
        parsed = self.srv._parse_upgrade_summary('WAVE_UPGRADE_SUMMARY_JSON:{"pruned_count": 9}')
        self.assertEqual(parsed, {"pruned_count": 9})

    def test_parse_upgrade_summary_deeply_nested_no_exception(self):
        # F1: a pathological deeply-nested payload (RecursionError risk) must NOT escape — returns None.
        deep = "[" * 100000  # malformed + deeply nested → json.loads raises (RecursionError or ValueError)
        line = "WAVE_UPGRADE_SUMMARY_JSON:" + deep
        self.assertIsNone(self.srv._parse_upgrade_summary(line))

    def test_summary_sentinel_constant_is_imported_not_redefined(self):
        # TA-1: server_impl must use the single constant from upgrade_wavefoundry, never a redefinition.
        import upgrade_wavefoundry as _uw
        self.assertEqual(self.srv._upgrade_summary_sentinel(), _uw.WAVE_UPGRADE_SUMMARY_SENTINEL)
        self.assertFalse(
            hasattr(self.srv, "_WAVE_UPGRADE_SUMMARY_SENTINEL"),
            "server_impl must NOT redefine the sentinel constant (TA-1)",
        )

    def test_round_trip_emit_then_parse(self):
        # TA-1: capture _print_operator_summary's real stdout and feed it to _parse_upgrade_summary —
        # the exact emitted line must parse back to the same fields (structural emit↔parse contract).
        import contextlib
        import io as _io
        import upgrade_wavefoundry as _uw
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            _uw._print_operator_summary(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=5, ran_index_rebuild=True, failed_phase=None,
            )
        parsed = self.srv._parse_upgrade_summary(buf.getvalue())
        self.assertIsNotNone(parsed, "the emitted sentinel line must parse")
        self.assertEqual(parsed["from_version"], "1.5.0")
        self.assertEqual(parsed["to_version"], "1.6.0")
        self.assertEqual(parsed["pruned_count"], 5)
        self.assertEqual(parsed["docs_gate"], "PASSED")
        self.assertTrue(parsed["is_major_or_minor"])
        for key in ("index_update", "failed_phase", "reconciliation"):
            self.assertIn(key, parsed)

    def test_round_trip_delegated_child_transport(self):
        # Wave 1u44o: extend the emit↔parse round trip to the CHILD-TRANSPORT
        # contract: the parent's single emit site re-emits a delegated payload
        # byte-verbatim under its own sentinel, and the server parses it into
        # the same fields plus the schema token.
        import contextlib
        import io as _io
        import upgrade_wavefoundry as _uw
        payload = json.dumps({
            "summary_schema_version": _uw.SUMMARY_SCHEMA_VERSION,
            "from_version": "1.14.0", "to_version": "1.15.0",
            "pruned_count": 2, "docs_gate": "PASSED",
            "reconciliation": [],
        }, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scripts = root / ".wavefoundry" / "framework" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "upgrade_wavefoundry.py").write_text(
                f"print('WAVE_UPGRADE_SUMMARY_JSON:' + {payload!r})\n",
                encoding="utf-8",
            )
            buf = _io.StringIO()
            with patch.object(_uw, "_preferred_python", return_value=sys.executable), \
                    contextlib.redirect_stdout(buf):
                _uw._emit_primary_summary_via_delegate_or_fallback(
                    root=root, from_version="1.14.0", to_version="1.15.0",
                    zip_path=None, pruned_count=2, index_published=True,
                )
        parsed = self.srv._parse_upgrade_summary(buf.getvalue())
        self.assertIsNotNone(parsed, "the transported sentinel line must parse")
        self.assertEqual(parsed["summary_schema_version"], _uw.SUMMARY_SCHEMA_VERSION)
        self.assertEqual(parsed["from_version"], "1.14.0")
        self.assertEqual(parsed["pruned_count"], 2)
        self.assertNotIn("summary_source_degraded", parsed)

    def test_new_schema_probe_field_survives_into_response_summary(self):
        # Wave 1u44o AC-1 (parser-side end to end): a field the current server
        # cannot itself produce must survive _parse_upgrade_summary +
        # _bounded_upgrade_summary into wf_upgrade_response's data['summary'],
        # not merely appear in the sentinel line.
        stdout = self._summary_output(
            summary_schema_version=1,
            probe_from_future_schema="delegation-transport-proof",
        )
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="update_index")
        summary = result["data"]["summary"]
        self.assertEqual(
            summary["probe_from_future_schema"], "delegation-transport-proof"
        )
        self.assertEqual(summary["summary_schema_version"], 1)

    def test_degradation_marker_is_terminal_and_survives_budget_pressure(self):
        # Wave 1u44o AC-2: the marker is registered as a terminal key, so
        # bounding can never silently drop the very field that discloses
        # degradation; even when oversized unknown scalars exhaust the
        # unknown-scalar budget.
        self.assertIn(
            "summary_source_degraded", self.srv.UPGRADE_SUMMARY_TERMINAL_KEYS
        )
        summary = {
            "from_version": "1.14.0",
            "to_version": "1.15.0",
            "docs_gate": "PASSED",
            "failed_phase": None,
            "summary_source_degraded": "entry_point_absent",
            **{
                f"future_scalar_{index:03d}": "x" * 1_900
                for index in range(80)
            },
            "reconciliation": [],
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)
        bounded = result["data"]["summary"]
        self.assertTrue(bounded["summary_truncated"])
        self.assertEqual(
            bounded["summary_source_degraded"], "entry_point_absent",
            "bounding must never drop the degradation disclosure",
        )

    def test_degradation_marker_survives_without_terminal_registration(self):
        # Wave 1u44o AC-2 (stale-server corner): a server launched BEFORE this
        # change can outlive multiple upgrades without restart; its terminal-key
        # set lacks the marker, so the marker must be flat and small enough to
        # survive the unknown-scalar budget path of a normal-size summary.
        stale_terminal_keys = {
            key
            for key in self.srv.UPGRADE_SUMMARY_TERMINAL_KEYS
            if key != "summary_source_degraded"
        }
        stdout = self._summary_output(
            summary_source_degraded="exit_status_2",
        )
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch.object(
            self.srv, "UPGRADE_SUMMARY_TERMINAL_KEYS", stale_terminal_keys
        ), patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root)
        bounded = result["data"]["summary"]
        self.assertEqual(
            bounded["summary_source_degraded"], "exit_status_2",
            "the marker must survive the unknown-scalar budget path on a "
            "pre-1u44o server",
        )

    def test_schema_token_is_terminal_and_survives_cleanup_budget_pressure(self):
        # Wave 1uf68 requirement 6(d) / AC-4: the cleanup emit site now carries
        # summary_schema_version, so the bounder must never be able to make a
        # PRESENT token look absent. Unregistered, the token competes in the
        # unknown-scalar budget and a drop yields None, which reads as absent to
        # any consumer not also checking the truncation flag, reintroducing the
        # exact ambiguity this change removes. Budget pressure is load-bearing:
        # without it the token survives even unregistered and the test proves
        # nothing, which is why the same summary is also driven through a
        # terminal-key set with the token filtered out.
        self.assertIn(
            "summary_schema_version", self.srv.UPGRADE_SUMMARY_TERMINAL_KEYS
        )
        # A cleanup-shaped summary: token present, failed_phase null (success
        # branch), plus enough unknown scalars to exhaust the budget.
        #
        # Two fixture properties are load-bearing and were both established by
        # execution, not assumed:
        #  - Key ORDER mirrors the real emit site: `_print_operator_summary`
        #    assigns the token onto the finished builder dict, so on the wire the
        #    token is the LAST key and every unknown scalar is budgeted first.
        #  - The fillers are sized to the token's own entry cost (a 24-char key
        #    plus a 1-char value = 25 chars). A handful of OVERSIZED fillers does
        #    not exhaust the budget: `_bounded_upgrade_summary` decrements it only
        #    for ADMITTED fields, so oversized fillers leave hundreds of
        #    characters of slack and a 25-char entry still fits even unregistered.
        #    Same-size fillers drive the residual budget strictly below 25, which
        #    is the only state in which the terminal registration is what keeps
        #    the token on the wire.
        summary = {
            "from_version": "1.15.2",
            "to_version": "1.15.3",
            "docs_gate": "PASSED",
            "failed_phase": None,
            **{f"u{index:04d}": "x" * 16 for index in range(1_200)},
            "reconciliation": [],
            "summary_schema_version": 1,
        }
        stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"
        mock_proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="cleanup")
        bounded = result["data"]["summary"]
        self.assertTrue(
            bounded["summary_truncated"],
            "the fixture must actually exhaust the budget or it proves nothing",
        )
        self.assertEqual(
            bounded["summary_schema_version"], 1,
            "bounding must never drop the freshness token from a cleanup summary",
        )
        # Anti-vacuity control (the pre-registration behaviour this pins
        # against): with the token filtered out of the terminal-key set it loses
        # the guarantee and the bounder is free to drop it.
        stale_terminal_keys = {
            key
            for key in self.srv.UPGRADE_SUMMARY_TERMINAL_KEYS
            if key != "summary_schema_version"
        }
        with patch.object(
            self.srv, "UPGRADE_SUMMARY_TERMINAL_KEYS", stale_terminal_keys
        ), patch("subprocess.run", return_value=mock_proc):
            unregistered = self.srv.wf_upgrade_response(self.root, phase="cleanup")
        self.assertIsNone(
            unregistered["data"]["summary"].get("summary_schema_version"),
            "control: without the registration the token is droppable, which is "
            "what the registration exists to prevent",
        )

    def test_failure_response_carries_next_step_and_next_tools(self):
        # F2: the primary error path must route a retained typed-gate failure
        # back through resume_after_gate rather than publication or cleanup.
        mock_proc = MagicMock()
        mock_proc.returncode = 1  # docs gate failed
        mock_proc.stdout = ""
        mock_proc.stderr = (
            "Upgrade failed during phase 'docs_gate'. Resolve the typed "
            "review-state or docs findings, then run --resume-after-gate."
        )
        with patch("subprocess.run", return_value=mock_proc):
            result = self.srv.wf_upgrade_response(self.root, phase="preflight_to_docs_gate")
        self.assertEqual(result["status"], "error")
        self.assertIn("retry wf_upgrade(phase='resume_after_gate')", result["next_step"])
        self.assertNotIn("phase='update_index'", result["next_step"])
        self.assertNotIn("phase='cleanup'", result["next_step"])
        self.assertEqual(
            result["next_tools"], ["wf_upgrade_status", "wf_upgrade"]
        )
        self.assertIn(
            "review-state projection or docs gate failed",
            result["diagnostics"][0]["message"],
        )


class ImplHandlerCloseTests(unittest.TestCase):
    """AC-6: ImplHandler.close() nulls Lance handles before build_handler creates new ones."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_close_nulls_lance_handles(self):
        """AC-6: close() must set Lance table refs and reranker to None so no double-open occurs."""
        handler = self.srv.build_handler(self.root)
        # Force-populate internal table refs with sentinel values to confirm they are cleared.
        handler.index._docs_vector_layer = object()
        handler.index._code_vector_layer = object()
        handler.index._reranker = object()
        handler.index._loaded = True

        handler.close()

        self.assertIsNone(handler.index._docs_vector_layer, "_docs_vector_layer must be None after close()")
        self.assertIsNone(handler.index._code_vector_layer, "_code_vector_layer must be None after close()")
        self.assertIsNone(handler.index._reranker, "_reranker must be None after close()")
        self.assertFalse(handler.index._loaded, "_loaded must be False after close()")

    def test_reload_closes_old_handler_before_build(self):
        """AC-6: perform_mcp_reload() calls close() on the old handler before building a new one."""
        import server as _server_mod
        try:
            _server_mod.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

        closed = []
        original_close = _server_mod._get_handler().close

        def tracking_close():
            closed.append(True)
            original_close()

        _server_mod._get_handler().close = tracking_close
        result = _server_mod.perform_mcp_reload()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(closed), 1, "close() must be called exactly once during reload")


class WaveCodeFootprintTests(unittest.TestCase):
    """Exercise `_wave_code_footprint` itself.

    Every existing retrieval-posture test stubs `_FOOTPRINT_PROVIDER`, which
    short-circuits before this function runs, so the whole wave-bounding
    semantic shipped with no coverage at all. These tests deliberately leave the
    seam unset.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def _repo(self, declared: str, dirty: list[str]):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        wave_dir = root / "docs" / "waves" / "0aaaa sample"
        wave_dir.mkdir(parents=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            "# Wave Record\n\nStatus: implementing\n"
            "wave-id: `0aaaa sample`\n\n"
            "## Changes\n\nChange ID: `1200a-feat sample`\nChange Status: `active`\n",
            encoding="utf-8",
        )
        (wave_dir / "1200a-feat sample.md").write_text(
            "# Change\nChange ID: `1200a-feat sample`\n\n"
            f"## Serialization Points\n\n{declared}\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
        for rel in dirty:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x\n", encoding="utf-8")
        # Intent-to-add: git collapses a wholly untracked directory to a single
        # `?? src/` entry, which the porcelain parser correctly skips as a
        # directory. Recording intent makes each path appear individually, which
        # is what a real dirty working tree looks like.
        if dirty:
            subprocess.run(
                ["git", "-C", str(root), "add", "-N", *dirty], check=True
            )
        return root, wave_md

    def test_declared_targets_are_matched_regardless_of_path_case(self):
        """`git status` preserves case; the declared extractor lowercases.

        Comparing them directly dropped every PascalCase target, so a
        TypeScript, Java, or C# repository undercounted its own declared
        footprint while the advisory still claimed to describe it.
        """
        root, wave_md = self._repo(
            "- `src/GardenerMetadata.ts`\n- `src/beta.ts`",
            ["src/GardenerMetadata.ts", "src/beta.ts"],
        )
        self.assertEqual(self.srv._wave_code_footprint(root, wave_md), 2)

    def test_a_wave_declaring_nothing_stays_silent_instead_of_guessing(self):
        root, wave_md = self._repo("(none yet)", ["src/alpha.ts"])
        self.assertIsNone(self.srv._wave_code_footprint(root, wave_md))

    def test_unrelated_dirt_is_not_evidence_about_this_wave(self):
        root, wave_md = self._repo(
            "- `src/alpha.ts`", ["src/alpha.ts", "src/unrelated.ts", "other/thing.ts"]
        )
        self.assertEqual(self.srv._wave_code_footprint(root, wave_md), 1)

    def test_a_declared_directory_counts_the_files_beneath_it(self):
        """The directory arm of `in_wave_footprint` was unpinned.

        Declaring `src/` must bound the footprint to everything under it;
        without the prefix arm a directory declaration matches nothing and the
        advisory silently reports zero for a wave that declared its whole
        source tree.
        """

        root, wave_md = self._repo(
            "- `src/`",
            ["src/alpha.ts", "src/nested/beta.ts", "other/thing.ts"],
        )
        self.assertEqual(self.srv._wave_code_footprint(root, wave_md), 2)

    def test_a_renamed_declared_file_is_attributed_by_its_new_path(self):
        """Delivery finding: the rename parse shipped with zero coverage.

        Git writes `old -> new` in a rename entry and quotes each side
        INDEPENDENTLY when it contains a space, so unquoting before splitting
        on the arrow left a stray quote on the new path and the target never
        matched. Both deleting the split and inverting it to take the OLD path
        left the whole suite green, so the behavior was correct but unpinned.

        Declaring a path with a space is only possible through the explicit
        marker block, which is what makes this reachable at all.
        """

        root, wave_md = self._repo(
            "**Review targets (repo-relative paths):**\n\n"
            "- `src/spaced dir/new.py`\n- `src/plain/new.py`",
            ["src/spaced dir/old.py", "src/plain/old.py"],
        )
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.email=t@e", "-c", "user.name=t",
             "commit", "-qm", "base"],
            check=True,
        )
        for old, new in (
            ("src/spaced dir/old.py", "src/spaced dir/new.py"),
            ("src/plain/old.py", "src/plain/new.py"),
        ):
            subprocess.run(["git", "-C", str(root), "mv", old, new], check=True)
        porcelain = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        self.assertIn(' -> ', porcelain, "fixture must stage real renames")
        self.assertIn('"', porcelain, "git must quote the spaced rename")
        self.assertEqual(
            self.srv._wave_code_footprint(root, wave_md), 2,
            f"both renames must attribute to their NEW paths:\n{porcelain}",
        )

    def test_a_rename_away_from_a_declared_path_is_not_attributed(self):
        """The OLD path must not be what counts, or the split could invert.

        Declaring only the pre-rename path must score zero: the file that
        changed is the new one, and attributing the old path would let a
        `rsplit` silently become a `split` without any test noticing.
        """

        root, wave_md = self._repo(
            "- `src/plain/old.py`", ["src/plain/old.py"],
        )
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.email=t@e", "-c", "user.name=t",
             "commit", "-qm", "base"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "mv", "src/plain/old.py", "src/plain/new.py"],
            check=True,
        )
        self.assertEqual(self.srv._wave_code_footprint(root, wave_md), 0)


# Wave 1p41o: code_risk_score MCP wrapper-layer regression (AC-7) — assert the
# documented fields survive the tool boundary, not just the query-layer method.
_RISK_WRAP_FIXTURE = {
    "present": True,
    "layer": "project",
    "nodes": [
        {"id": "src/m.py", "label": "m", "kind": "module", "source_file": "src/m.py"},
        {"id": "src/m.py::hub", "label": "hub", "kind": "function", "source_file": "src/m.py"},
        {"id": "src/m.py::leaf", "label": "leaf", "kind": "function", "source_file": "src/m.py"},
        {"id": "src/c1.py::a", "label": "a", "kind": "function", "source_file": "src/c1.py"},
        {"id": "src/c2.py::b", "label": "b", "kind": "function", "source_file": "src/c2.py"},
    ],
    "edges": [
        {"source": "src/c1.py::a", "target": "src/m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "src/c2.py::b", "target": "src/m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
    ],
}


class CodeRiskScoreWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _call(self, scope, **kw):
        gqmod = self.srv._load_graph_query()
        idx = gqmod.GraphQueryIndex(dict(_RISK_WRAP_FIXTURE))
        # Wave 1p9q3 (1p9pz): tools construct via the cached accessor now —
        # patch get_query_index (the accessor seam), not from_root.
        with patch.object(
            gqmod, "get_query_index",
            lambda root, layer="project": idx,
        ):
            return self.srv.code_risk_score_response(self.root, scope, **kw)

    def test_wrapper_surfaces_documented_fields(self):
        resp = self._call("src/m.py", top=5)
        self.assertEqual(resp["status"], "ok")
        data = resp["data"]
        # Wave 1p5l4: confidence-weighted composite v2.
        self.assertEqual(data["score_formula"], "risk = weighted_affected_file_count * log1p(weighted_fan_in)")
        self.assertEqual(data["score_components"], [
            "weighted_affected_file_count", "weighted_fan_in", "fan_out",
            "affected_file_count", "fan_in", "extracted_edge_fraction",
            "transitive_extracted_fraction",
        ])
        self.assertIn("extracted_edge_weight", data)
        self.assertTrue(data["results"])
        top = data["results"][0]
        self.assertEqual(top["label"], "hub")
        for field in ("node_id", "label", "source_file", "kind",
                      "risk", "weighted_affected_file_count", "weighted_fan_in",
                      "affected_file_count", "fan_in", "fan_out",
                      "extracted_edge_fraction", "transitive_extracted_fraction", "hop"):
            self.assertIn(field, top, f"missing documented field {field!r} through the tool boundary")

    def test_wrapper_empty_scope_errors(self):
        resp = self.srv.code_risk_score_response(self.root, "")
        self.assertEqual(resp["status"], "error")

    def test_wrapper_over_cap_errors(self):
        resp = self._call("src/m.py", candidate_cap=1)
        self.assertEqual(resp["status"], "error")
        self.assertIn("scope_too_large", json.dumps(resp))


# Wave 1p4es: code_impact graph-mode ergonomics — edges bounded by max_results,
# edges_total surfaced, resolved no longer null (field report).
_IMPACT_EDGES_FIXTURE = {
    "present": True,
    "layer": "project",
    "nodes": [
        {"id": "m.py::hub", "label": "hub", "kind": "function", "source_file": "m.py"},
        {"id": "a.py::a", "label": "a", "kind": "function", "source_file": "a.py"},
        {"id": "b.py::b", "label": "b", "kind": "function", "source_file": "b.py"},
        {"id": "c.py::c", "label": "c", "kind": "function", "source_file": "c.py"},
    ],
    "edges": [
        {"source": "a.py::a", "target": "m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "b.py::b", "target": "m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
        {"source": "c.py::c", "target": "m.py::hub", "relation": "calls", "confidence": "RECEIVER_RESOLVED"},
    ],
}


class CodeImpactErgonomicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _call(self, **kw):
        gqmod = self.srv._load_graph_query()
        idx = gqmod.GraphQueryIndex(dict(_IMPACT_EDGES_FIXTURE))
        # Wave 1p9q3 (1p9pz): tools construct via the cached accessor now —
        # patch get_query_index (the accessor seam), not from_root.
        with patch.object(
            gqmod, "get_query_index",
            lambda root, layer="project": idx,
        ):
            return self.srv.code_impact_response(self.root, symbol="hub", **kw)

    def test_edges_bounded_by_max_results_and_total_surfaced(self):
        resp = self._call(max_results=2)
        self.assertEqual(resp["status"], "ok")
        d = resp["data"]
        # hub has 3 callers → 3 edges; max_results=2 caps the response edges.
        self.assertLessEqual(len(d["edges"]), 2, "edges must be bounded by max_results")
        self.assertGreaterEqual(d["edges_total"], 3, "edges_total must surface the real count")
        self.assertTrue(d["truncated"], "truncated must reflect edge truncation")

    def test_resolved_field_is_true_not_null(self):
        resp = self._call(max_results=50)
        d = resp["data"]
        self.assertEqual(d["resolved"], True, "graph-mode `resolved` must be True (was null)")
        self.assertEqual(d["node_id"], "m.py::hub")


class WindowsLivenessGuardTests(unittest.TestCase):
    """1p6d6: _pid_is_running uses tasklist on native Windows (the formerly-unguarded check called
    from 12+ sites incl. the dashboard 1p654 reconciliation); the POSIX path stays os.kill (byte-
    identical). _background_build_status routes through the guard instead of an inline os.kill."""

    def setUp(self):
        self.srv = load_server()

    def test_pid_non_positive_is_false(self):
        self.assertFalse(self.srv._pid_is_running(0))
        self.assertFalse(self.srv._pid_is_running(-5))

    def test_posix_uses_os_kill_unchanged(self):
        srv = self.srv
        with patch.object(srv.os, "name", "posix"):
            with patch.object(srv.os, "kill") as killed:
                self.assertTrue(srv._pid_is_running(4321))
                killed.assert_called_once_with(4321, 0)
            with patch.object(srv.os, "kill", side_effect=OSError()):
                self.assertFalse(srv._pid_is_running(4321))

    def test_windows_uses_tasklist(self):
        srv = self.srv
        with patch.object(srv.os, "name", "nt"):
            present = MagicMock(stdout='"python.exe","4321","Console","1","50,000 K"\r\n')
            with patch("subprocess.run", return_value=present) as run:
                self.assertTrue(srv._pid_is_running(4321))
                argv = run.call_args[0][0]
                self.assertEqual(argv[0], "tasklist")
                self.assertIn("PID eq 4321", argv)
            absent = MagicMock(stdout="INFO: No tasks are running which match the specified criteria.\r\n")
            with patch("subprocess.run", return_value=absent):
                self.assertFalse(srv._pid_is_running(4321))
            with patch("subprocess.run", side_effect=OSError()):
                self.assertFalse(srv._pid_is_running(4321))

    def test_background_build_status_routes_through_guard(self):
        srv = self.srv
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wavefoundry" / "index").mkdir(parents=True)
            (root / ".wavefoundry" / "index" / "background-build.pid").write_text("4321", encoding="utf-8")
            with patch.object(srv, "_pid_is_running", return_value=True):
                self.assertEqual(srv._background_build_status(root), "running")
            with patch.object(srv, "_pid_is_running", return_value=False):
                self.assertEqual(srv._background_build_status(root), "completed")
        # absent pid file -> "none"
        with tempfile.TemporaryDirectory() as tmp2:
            self.assertEqual(srv._background_build_status(Path(tmp2)), "none")


class GpuDoctorToolTests(unittest.TestCase):
    """1p6et: wf_gpu_doctor_response wraps the provider diagnostic in the read-only envelope."""

    def setUp(self):
        self.srv = load_server()

    def test_response_envelope_wraps_diagnostic_report(self):
        # wf_gpu_doctor_response now runs setup's bounded probe; mock select_embedding_providers so
        # the unit test doesn't load a model (probe-selection itself is covered in test_setup_wavefoundry).
        import provider_policy
        fake = provider_policy.ProviderDecision(
            selected_provider="CPUExecutionProvider",
            providers=("CPUExecutionProvider",),
            available_providers=("CPUExecutionProvider",),
            reason="test",
            remediation=None,
        )
        with tempfile.TemporaryDirectory() as tmp, \
             patch("provider_policy.select_embedding_providers", return_value=fake):
            resp = self.srv.wf_gpu_doctor_response(Path(tmp))
        self.assertEqual(resp["status"], "ok")
        data = resp["data"]
        for key in ("platform", "onnxruntime_version", "nvidia_gpu_present", "apple_silicon_present",
                    "available_onnx_providers", "selected_provider", "selection_reason", "cuda12_abi_gap"):
            self.assertIn(key, data)
        self.assertEqual(resp["usage"], "wf_gpu_doctor()")

    def test_probe_wrapped_in_fd_level_stdout_isolation(self):
        # 1p8vc AC-3: the cold ORT probe is wrapped in cli_stdio.isolated_stdout_fd (OS fd level),
        # in addition to the Python-level redirect_stdout — so native onnxruntime/DirectML writes to
        # fd 1 cannot corrupt the MCP JSON-RPC stdout channel and hang the first call.
        import re as _re
        src = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        start = src.index("def wf_gpu_doctor_response(")
        rest = src[start + 1:]
        m = _re.search(r"\n(?=def |class )", rest)
        body = rest[: m.start()] if m else rest
        self.assertIn("isolated_stdout_fd", body, "probe must be wrapped in the fd-level stdout isolation")
        self.assertIn("redirect_stdout", body, "Python-level redirect must remain (belt-and-suspenders)")


class BackgroundBuildReapRegistryTests(unittest.TestCase):
    """Wave 1p98u: the long-lived server reaps the background index builds it launches so they don't
    linger as zombies whose stale PID makes the index-build lock read as live."""

    def setUp(self):
        # Wave 1wpif cycle-3 (CODE-RV2-2): the last setUp-level bare import
        # in the tests tree. It resolved only because an earlier test in the
        # module had already put SCRIPTS_ROOT on sys.path, so this class
        # failed at import when run in isolation.
        self.srv = load_server()
        self._saved = set(self.srv._BACKGROUND_BUILD_PIDS)
        self.srv._BACKGROUND_BUILD_PIDS.clear()

    def tearDown(self):
        self.srv._BACKGROUND_BUILD_PIDS.clear()
        self.srv._BACKGROUND_BUILD_PIDS.update(self._saved)

    def test_register_is_posix_only_and_validates(self):
        with patch.object(self.srv.os, "name", "posix"):
            self.srv._register_background_build_pid(1234)
            self.assertIn(1234, self.srv._BACKGROUND_BUILD_PIDS)
            self.srv._register_background_build_pid(0)
            self.srv._register_background_build_pid(-9)
            self.assertNotIn(0, self.srv._BACKGROUND_BUILD_PIDS)
            self.assertNotIn(-9, self.srv._BACKGROUND_BUILD_PIDS)

    def test_register_noop_on_windows(self):
        with patch.object(self.srv.os, "name", "nt"):
            self.srv._register_background_build_pid(1234)
        self.assertNotIn(1234, self.srv._BACKGROUND_BUILD_PIDS)

    def test_reap_removes_finished_child(self):
        self.srv._BACKGROUND_BUILD_PIDS.add(1234)
        with patch.object(self.srv.os, "name", "posix"), \
             patch.object(self.srv.os, "waitpid", return_value=(1234, 0)) as wp:
            self.srv._reap_background_build_pids()
        wp.assert_called_once_with(1234, self.srv.os.WNOHANG)
        self.assertNotIn(1234, self.srv._BACKGROUND_BUILD_PIDS)

    def test_reap_keeps_still_running_child(self):
        self.srv._BACKGROUND_BUILD_PIDS.add(1234)
        with patch.object(self.srv.os, "name", "posix"), \
             patch.object(self.srv.os, "waitpid", return_value=(0, 0)):
            self.srv._reap_background_build_pids()
        self.assertIn(1234, self.srv._BACKGROUND_BUILD_PIDS)

    def test_reap_discards_non_child(self):
        self.srv._BACKGROUND_BUILD_PIDS.add(1234)
        with patch.object(self.srv.os, "name", "posix"), \
             patch.object(self.srv.os, "waitpid", side_effect=ChildProcessError):
            self.srv._reap_background_build_pids()
        self.assertNotIn(1234, self.srv._BACKGROUND_BUILD_PIDS)

    def test_reap_noop_on_windows(self):
        self.srv._BACKGROUND_BUILD_PIDS.add(1234)
        with patch.object(self.srv.os, "name", "nt"), \
             patch.object(self.srv.os, "waitpid") as wp:
            self.srv._reap_background_build_pids()
        wp.assert_not_called()
        self.assertIn(1234, self.srv._BACKGROUND_BUILD_PIDS)


class HarnessCoherencePackTextTests(unittest.TestCase):
    """Wave 1u8o2 (1u8o1): pack-owned migration text and the wf_cli module
    reference no longer flag as stale tool references; a genuinely stale name
    still flags, with pack-owned findings classified `pack_internal`.

    Fixture text is COPIED from the real seed lines (fixtures-from-canonical-
    producers); the live-tools collector reads the RUNNING server's scripts
    directory, not the fixture root, so retired names stay non-live here."""

    # Copied verbatim from seed-160 lines 182 and 459 (migration instruction +
    # verification checklist: the retired names MUST stay in this text). The
    # wf_cli line is copied and abridged from seed-080 line 28 (truncated
    # mid-sentence; the module-path form `wf_cli.py` is preserved intact).
    _SEED_MIGRATION_TEXT = (
        "# Upgrade Wavefoundry\n\n"
        " - `AGENTS.md` and `CLAUDE.md` gate-tool references — when either file "
        "references `wave_open_gate` or `wf_close_wave_gate`, update to "
        "`wf_open_gate`, `wf_close_gate`, and add `wf_gate_status` as the "
        "read-only gate inspection tool; reconcile against current `seed-050` "
        "wording. These surfaces are not regenerated automatically by "
        "`render_platform_surfaces.py` so they must be updated explicitly.\n"
        "- `AGENTS.md` and `CLAUDE.md` reference `wf_open_gate`, "
        "`wf_close_gate`, and `wf_gate_status` in any gate-usage guidance — "
        "not the retired `wave_open_gate` / `wf_close_wave_gate` names; "
        "reconcile when the old names are still present\n"
        "- The single cross-OS `wf` shim pair (`.wavefoundry/bin/wf` + "
        "`wf.cmd`) dispatches to `wf_cli.py`, which routes `wf docs-lint` to "
        "`.wavefoundry/framework/scripts/docs_lint.py`\n"
    )
    _MIRROR_TEXT = (
        "# Upgrade Wavefoundry (rendered mirror)\n\n"
        "- The `wf` shim pair dispatches to `wf_cli.py`, which routes "
        "subcommands to their backing scripts.\n"
    )

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.seeds = self.root / ".wavefoundry" / "framework" / "seeds"
        self.prompts = self.root / "docs" / "prompts"
        self.seeds.mkdir(parents=True)
        self.prompts.mkdir(parents=True)

    def test_downstream_shaped_fixture_reports_zero_pack_findings(self):
        # AC-1: the migration text (both retired gate names) plus module-path
        # wf_cli mentions, in the pack AND the rendered mirror, report zero
        # stale_tool_reference findings under the checker-side resolution.
        (self.seeds / "160-upgrade-wavefoundry.prompt.md").write_text(
            self._SEED_MIGRATION_TEXT, encoding="utf-8")
        (self.prompts / "upgrade-wavefoundry.prompt.md").write_text(
            self._MIRROR_TEXT, encoding="utf-8")
        result = self.srv._audit_harness_coherence(self.root)
        self.assertEqual(result["scanned_files"], 2)
        self.assertEqual(result["findings_count"], 0, result["findings"])
        self.assertEqual(result["pack_internal_count"], 0)
        self.assertEqual(result["project_findings_count"], 0)

    def test_positive_control_stale_name_still_flags_with_classification(self):
        # AC-4 positive control + the requirement 2 mechanism (b): a real
        # stale tool name in non-migration prose still flags on both sides,
        # pack-owned findings classified `pack_internal`, project-owned
        # findings `project`.
        (self.seeds / "999-example.prompt.md").write_text(
            "Run `wf_totally_retired_tool` before closing the wave.\n",
            encoding="utf-8")
        (self.prompts / "example.prompt.md").write_text(
            "Call `wave_frobnicate` to frobnicate the index.\n",
            encoding="utf-8")
        result = self.srv._audit_harness_coherence(self.root)
        self.assertEqual(result["findings_count"], 2, result["findings"])
        by_file = {f["file"]: f for f in result["findings"]}
        pack = by_file[".wavefoundry/framework/seeds/999-example.prompt.md"]
        self.assertEqual(pack["type"], "stale_tool_reference")
        self.assertEqual(pack["classification"], "pack_internal")
        project = by_file["docs/prompts/example.prompt.md"]
        self.assertEqual(project["classification"], "project")
        self.assertEqual(result["pack_internal_count"], 1)
        self.assertEqual(result["project_findings_count"], 1)

    def test_real_surfaces_keep_retired_names_and_scan_clean_of_them(self):
        # AC-3 + AC-4: the canonical seed still carries BOTH retired names at
        # the instruction lines (a checker fix that "fixed" the seed instead
        # trips this), the rendered mirror still carries the wf_cli mention it
        # renders (the retired gate names live only in the canonical seed's
        # migration sections, which the mirror does not render), and the real
        # scan reports no wf_cli or retired-gate-name findings anywhere.
        repo_root = Path(__file__).resolve().parents[4]
        seed = repo_root / ".wavefoundry" / "framework" / "seeds" / "160-upgrade-wavefoundry.prompt.md"
        mirror = repo_root / "docs" / "prompts" / "upgrade-wavefoundry.prompt.md"
        seed_text = seed.read_text(encoding="utf-8")
        self.assertIn("wave_open_gate", seed_text)
        self.assertIn("wf_close_wave_gate", seed_text)
        self.assertIn("wf_cli", mirror.read_text(encoding="utf-8"))
        result = self.srv._audit_harness_coherence(repo_root)
        details = [f["detail"] for f in result["findings"]]
        self.assertFalse(
            any("'wf_cli'" in d for d in details),
            "wf_cli must never flag (module reference, not a tool)")
        self.assertFalse(
            any("'wave_open_gate'" in d or "'wf_close_wave_gate'" in d for d in details),
            "retired gate names in migration text must never flag")


class TechdocsAuditToolTests(unittest.TestCase):
    """Wave 1vqqi: `wf_techdocs_audit`, the read-tier MCP entry of the publication audit.

    Read tier means: no lock, no publication-writer registration, findings as data
    rather than diagnostics, and advisory diagnostics for the states where the tool
    could not compute an answer.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = (Path(self.tmp.name) / "Example_Project").resolve()
        _make_repo(self.root)
        meta = "Owner: Engineering\nStatus: active\nLast verified: 2026-08-18\n"
        for rel, title in (
            ("docs/index.md", "Home"),
            ("docs/ARCHITECTURE.md", "Architecture"),
            ("docs/references/project-overview.md", "Project overview"),
            ("docs/prompts/index.md", "Commands"),
        ):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {title}\n\n{meta}\n", encoding="utf-8")
        (self.root / "catalog-info.yaml").write_text("kind: Component\n", encoding="utf-8")
        block = "\n".join(
            "  " + line for line in
            ["/*", "!/index.md", "!/ARCHITECTURE.md", "!/architecture/", "!/architecture/**",
             "!/references/", "!/references/**", "!/prompts/", "/prompts/*", "!/prompts/index.md"]
        )
        (self.root / "mkdocs.yml").write_text(
            "site_name: Example\ndocs_dir: docs\nnav:\n  - Home: index.md\n"
            "  - Project overview: references/project-overview.md\n"
            "  - Architecture: ARCHITECTURE.md\n  - Workflow: prompts/index.md\n"
            "exclude_docs: |\n" + block + "\n",
            encoding="utf-8",
        )

    def test_the_read_tier_payload_is_bounded_and_says_what_it_dropped(self):
        """DEL-4: an unbounded envelope overruns hosts and floods agent context.

        A published tree large enough to matter (the non-default docs_dir case
        Requirement 3 keeps the metadata and link codes for) produced 12001
        findings in a 1.8MB envelope with no truncation marker. Bounding without
        a marker would be worse than not bounding, so the totals and the omitted
        counts are asserted, not just the caps.
        """
        pages = self.srv.TECHDOCS_AUDIT_FINDING_CAP + 40
        refs = self.root / "docs" / "references"
        for index in range(pages):
            (refs / f"bulk{index}.md").write_text("# Bulk\n\n[gone](./nope.md)\n",
                                                  encoding="utf-8")

        response = self.srv.wf_techdocs_audit_response(self.root)
        data = response["data"]
        self.assertEqual(response["status"], "ok")
        self.assertTrue(data["truncated"])
        self.assertEqual(len(data["findings"]), self.srv.TECHDOCS_AUDIT_FINDING_CAP)
        self.assertGreater(data["findings_total"], self.srv.TECHDOCS_AUDIT_FINDING_CAP)
        self.assertEqual(
            data["findings_total"] - self.srv.TECHDOCS_AUDIT_FINDING_CAP,
            data["findings_omitted"])
        publication = data["publication"]
        self.assertEqual(len(publication["survivor_pages"]),
                         self.srv.TECHDOCS_AUDIT_SURVIVOR_CAP)
        self.assertEqual(publication["survivor_count"], pages + 4,
                         "the true total must survive truncation")
        self.assertIn("survivor_pages_omitted", publication,
                      "a capped survivor list must SAY that it was capped")
        self.assertEqual(
            publication["survivor_count"] - self.srv.TECHDOCS_AUDIT_SURVIVOR_CAP,
            publication["survivor_pages_omitted"],
            "a capped survivor list must SAY how many pages it dropped")
        finding_codes = {f["code"] for f in data["findings"]}
        diagnostic_codes = {d["code"] for d in response["diagnostics"]}
        self.assertEqual(finding_codes & diagnostic_codes, set(),
                         "findings stay data; truncation must not turn them into diagnostics")

    def test_a_small_report_carries_no_truncation_claim(self):
        """The control for the test above: caps must not fire on an ordinary tree."""
        response = self.srv.wf_techdocs_audit_response(self.root)
        data = response["data"]
        self.assertFalse(data["truncated"])
        self.assertNotIn("findings_omitted", data)
        self.assertNotIn("survivor_pages_omitted", data["publication"])
        self.assertEqual(data["findings_total"], len(data["findings"]))

    def test_the_survivor_cap_marks_its_own_truncation_when_it_fires_alone(self):
        """The survivor cap must mark itself without the finding cap firing too.

        In the test above both caps fire, so `truncated` and the omitted counts are
        satisfied by the finding half alone and the survivor marker rides along
        unpinned. This is the case the audit tool actually meets on a large clean
        tree: hundreds of published pages, no findings. Without the marker the
        envelope reports a 200-entry list, no omitted count and `truncated` False
        while the list really is capped, which is the silent truncation the bounding
        docstring calls worse than a large payload.
        """
        pages = self.srv.TECHDOCS_AUDIT_SURVIVOR_CAP + 7
        meta = "Owner: Engineering\nStatus: active\nLast verified: 2026-08-18\n"
        refs = self.root / "docs" / "references"
        for index in range(pages):
            (refs / f"clean{index}.md").write_text(f"# Clean {index}\n\n{meta}\n",
                                                   encoding="utf-8")

        response = self.srv.wf_techdocs_audit_response(self.root)
        data = response["data"]
        self.assertEqual(response["status"], "ok")
        publication = data["publication"]
        # Precondition: the finding cap must NOT fire, or it masks the survivor cap.
        self.assertLess(data["findings_total"], self.srv.TECHDOCS_AUDIT_FINDING_CAP)
        self.assertNotIn("findings_omitted", data)
        self.assertGreater(publication["survivor_count"],
                           self.srv.TECHDOCS_AUDIT_SURVIVOR_CAP)
        # The survivor half alone must carry the whole truncation claim.
        self.assertTrue(data["truncated"])
        self.assertEqual(len(publication["survivor_pages"]),
                         self.srv.TECHDOCS_AUDIT_SURVIVOR_CAP)
        self.assertEqual(publication["survivor_count"], pages + 4,
                         "the true total must survive truncation")
        self.assertIn("survivor_pages_omitted", publication,
                      "a capped survivor list must SAY that it was capped")
        self.assertEqual(
            publication["survivor_count"] - self.srv.TECHDOCS_AUDIT_SURVIVOR_CAP,
            publication["survivor_pages_omitted"],
            "a capped survivor list must SAY how many pages it dropped")

    def test_the_unsafe_survivor_cap_marks_its_own_truncation(self):
        """The cycle-3 refusal channel is tree-sized and obeys the MCP cap too."""
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        outside = Path(self.tmp.name) / "outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        refs = self.root / "docs" / "references"
        target_count = self.srv.TECHDOCS_AUDIT_SURVIVOR_CAP + 7
        try:
            for index in range(target_count):
                os.symlink(outside, refs / f"leak{index:04d}.md")
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")

        response = self.srv.wf_techdocs_audit_response(self.root)
        data = response["data"]
        publication = data["publication"]
        self.assertEqual(response["status"], "ok")
        self.assertTrue(data["truncated"])
        self.assertEqual(len(publication["unsafe_survivor_targets"]),
                         self.srv.TECHDOCS_AUDIT_SURVIVOR_CAP)
        self.assertEqual(publication["unsafe_survivor_targets_total"], target_count)
        self.assertEqual(publication["unsafe_survivor_targets_omitted"], 7)
        self.assertNotIn("findings_omitted", data,
                         "the unsafe-list cap must own the truncation claim")
        self.assertNotIn("survivor_pages_omitted", publication,
                         "the unsafe-list cap must own the truncation claim")

    def test_a_small_unsafe_survivor_list_keeps_its_total_without_truncation(self):
        if not hasattr(os, "symlink"):  # pragma: no cover
            self.skipTest("symlinks unavailable")
        outside = Path(self.tmp.name) / "outside-small.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        try:
            os.symlink(outside, self.root / "docs" / "references" / "leak.md")
        except OSError:  # pragma: no cover
            self.skipTest("symlink creation not permitted")

        data = self.srv.wf_techdocs_audit_response(self.root)["data"]
        publication = data["publication"]
        self.assertFalse(data["truncated"])
        self.assertEqual(publication["unsafe_survivor_targets"], ["references/leak.md"])
        self.assertEqual(publication["unsafe_survivor_targets_total"], 1)
        self.assertNotIn("unsafe_survivor_targets_omitted", publication)

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def _digest(self) -> dict:
        out = {}
        for path in sorted(self.root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                out[str(path.relative_to(self.root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return out

    def test_findings_are_data_never_blocking_diagnostics(self):
        (self.root / "docs" / "references" / "links.md").write_text(
            "# Links\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-08-18\n\n"
            "[gone](./missing.md)\n", encoding="utf-8")
        before = self._digest()
        resp = self.srv.wf_techdocs_audit_response(self.root)
        self.assertEqual(resp["status"], "ok")
        codes = [f["code"] for f in resp["data"]["findings"]]
        self.assertIn("techdocs_link_missing", codes)
        # The finding is NOT a diagnostic: this tool gates nothing.
        self.assertNotIn("techdocs_link_missing", [d["code"] for d in resp["diagnostics"]])
        self.assertEqual(self._digest(), before)

    def test_not_applicable_is_an_advisory_diagnostic_not_an_error(self):
        (self.root / "mkdocs.yml").unlink()
        resp = self.srv.wf_techdocs_audit_response(self.root)
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["summary"]["verdict"], "not_applicable")
        self.assertEqual([d["code"] for d in resp["diagnostics"]], ["techdocs_audit_not_applicable"])
        self.assertTrue(resp["diagnostics"][0].get("advisory"))
        self.assertEqual(resp["next_tools"], ["wf_techdocs_baseline"])

    def test_degraded_run_is_advisory_and_never_reports_clean(self):
        resp = self.srv.wf_techdocs_audit_response(self.root)
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["summary"]["verdict"], "degraded")
        self.assertIn("git_unavailable", resp["data"]["degraded"])
        diagnostic = [d for d in resp["diagnostics"] if d["code"] == "techdocs_audit_degraded"]
        self.assertEqual(len(diagnostic), 1)
        self.assertTrue(diagnostic[0].get("advisory"))

    def test_registered_read_tier_and_not_a_publication_writer(self):
        import mcp_tool_roster
        import publication_control

        self.assertEqual(mcp_tool_roster.TOOL_TIERS["wf_techdocs_audit"], mcp_tool_roster.TIER_READ)
        self.assertIn("mcp__wavefoundry__wf_techdocs_audit", mcp_tool_roster.allow_rules())
        # Asserted literally: publication_block_reason returns None for ANY unregistered
        # tool (it fails open), so absence is not enforced by the guard itself.
        self.assertNotIn(
            "wf_techdocs_audit",
            {writer.tool_name for writer in publication_control.PUBLICATION_WRITER_REGISTRY},
        )

    def test_the_registered_tool_is_read_only_and_shares_the_library(self):
        try:
            mcp = load_thin_runner().build_server(self.root)
        except Exception as exc:  # pragma: no cover
            self.skipTest(f"mcp package not installed: {exc}")
        tools = getattr(mcp, "_tool_manager", mcp)
        registry = getattr(tools, "_tools", None) or getattr(mcp, "_tools")
        tool = registry["wf_techdocs_audit"]
        self.assertTrue(tool.annotations.readOnlyHint)
        self.assertFalse(tool.annotations.destructiveHint)
        self.assertIn("hard ten-second worker deadline", tool.description)
        self.assertIn("nav_target_escapes_root", tool.description)
        # One patch is observed by both entries: the response function imports the
        # public bounded runner at call time rather than binding a private copy.
        import techdocs_audit_lib

        sentinel = techdocs_audit_lib.run_techdocs_audit
        with patch.object(techdocs_audit_lib, "run_techdocs_audit", side_effect=sentinel) as spy:
            self.srv.wf_techdocs_audit_response(self.root)
        spy.assert_called_once()

    def test_timeout_is_advisory_data_and_never_a_blocking_finding(self):
        """AC-10: MCP returns the bounded runner's timeout envelope as read-tier data."""
        import techdocs_audit_lib

        before = self._digest()
        timeout_report = techdocs_audit_lib._timeout_report(self.root)
        with patch.object(techdocs_audit_lib, "run_techdocs_audit",
                          return_value=timeout_report) as run:
            resp = self.srv.wf_techdocs_audit_response(self.root)

        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["degraded"], ["audit_timeout"])
        self.assertEqual(resp["data"]["summary"]["verdict"], "degraded")
        self.assertEqual([d["code"] for d in resp["diagnostics"]],
                         ["techdocs_audit_degraded"])
        self.assertTrue(resp["diagnostics"][0]["advisory"])
        run.assert_called_once_with(self.root, compare_to=None)
        self.assertEqual(self._digest(), before)

    def test_a_compare_to_that_looks_like_an_option_is_refused(self):
        resp = self.srv.wf_techdocs_audit_response(self.root, compare_to="--upload-pack=x")
        self.assertIn("compare_to_refused", resp["data"]["degraded"])


class TechdocsBaselineToolTests(unittest.TestCase):
    """Wave 1vj4e (1vj4d Requirement 10 / AC-8): `wf_techdocs_baseline`, the MCP entry of the
    Backstage/TechDocs baseline, wraps the same `render_agent_surfaces.render_techdocs_baseline`
    the CLI calls: read-first `dry_run` default, missing-only `run`, typed envelope, error codes,
    write tier, publication registry, and the upgrade-checkpoint guard."""

    TRIO = ("catalog-info.yaml", "mkdocs.yml", "docs/index.md")

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = (Path(self.tmp.name) / "Example_Project").resolve()
        _make_repo(self.root)
        (self.root / "docs" / "references").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "prompts").mkdir(parents=True, exist_ok=True)

    def _targets(self):
        for rel in ("docs/references/project-overview.md", "docs/ARCHITECTURE.md", "docs/prompts/index.md"):
            (self.root / rel).write_text("# t\n", encoding="utf-8")

    def _digest(self) -> dict:
        out = {}
        for path in sorted(self.root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                out[str(path.relative_to(self.root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return out

    def _call(self, mode=None, cache=None):
        with patch.object(self.srv, "_run_post_write_lint", return_value={"passed": True, "errors": [], "warnings": [], "output": "ok"}, create=True), \
             patch.object(self.srv, "_trigger_background_index_refresh_for_paths", return_value={}) as refresh:
            if mode is None:
                resp = self.srv.wf_techdocs_baseline_response(self.root, cache=cache)
            else:
                resp = self.srv.wf_techdocs_baseline_response(self.root, mode=mode, cache=cache)
        self._last_refresh = refresh
        return resp

    def test_dry_run_default_writes_nothing_and_reports_absent_paths(self):
        self._targets()
        before = self._digest()
        resp = self._call()
        self.assertEqual(resp["status"], "dry_run", resp)
        data = resp["data"]
        self.assertEqual(data["mode"], "dry_run")
        self.assertEqual(data["missing_targets"], [])
        self.assertEqual(data["absent_paths"], list(self.TRIO))
        self.assertEqual(data["written_paths"], [])
        self.assertEqual(data["preserved_paths"], [])
        self.assertIsNone(data["partial"])
        self.assertIsNone(data["refusal"])
        self.assertEqual([d["code"] for d in resp["diagnostics"]], ["dry_run"])
        self.assertIn("mode='run'", resp["diagnostics"][0]["message"])
        self.assertNotIn("lint", data)  # nothing written, nothing linted
        self.assertEqual(self._digest(), before)

    def test_run_writes_exactly_the_absent_members_then_rerun_is_silent(self):
        self._targets()
        before = self._digest()
        cache = MagicMock()
        resp = self._call(mode="run", cache=cache)
        self.assertEqual(resp["status"], "ok", resp)
        data = resp["data"]
        self.assertEqual(data["written_paths"], list(self.TRIO))
        self.assertEqual(data["absent_paths"], list(self.TRIO))
        self.assertEqual(data["generated_paths"], list(self.TRIO))
        self.assertEqual(data["preserved_paths"], [])
        self.assertIsNone(data["partial"])
        self.assertEqual(resp["diagnostics"], [])
        self.assertIn("lint", data)
        after = self._digest()
        self.assertEqual(sorted(set(after) - set(before)), sorted(self.TRIO))
        for rel in self.TRIO:
            self.assertEqual(before.get(rel), None)
        cache.invalidate.assert_called_once()
        self._last_refresh.assert_called_once_with(self.root, ["docs/index.md"])
        # Envelope shape: the CLI's six keys plus mode/absent_paths (and the attached lint).
        self.assertEqual(
            sorted(k for k in data if k != "lint"),
            ["absent_paths", "generated_paths", "missing_targets", "mode", "partial", "preserved_paths", "refusal", "written_paths"],
        )
        # A marker-preserving user edit survives the rerun (missing-only, not overwrite).
        marked = self.root / "mkdocs.yml"
        marked.write_text(marked.read_text(encoding="utf-8") + "extra_key: kept\n", encoding="utf-8")
        snapshot = {rel: (self.root / rel).read_bytes() for rel in self.TRIO}
        cache2 = MagicMock()
        rerun = self._call(mode="run", cache=cache2)
        self.assertEqual(rerun["status"], "ok")
        self.assertEqual(rerun["data"]["written_paths"], [])
        self.assertEqual(rerun["data"]["absent_paths"], [])
        self.assertEqual(rerun["data"]["preserved_paths"], list(self.TRIO))
        self.assertIsNone(rerun["data"]["partial"])
        self.assertEqual({rel: (self.root / rel).read_bytes() for rel in self.TRIO}, snapshot)
        cache2.invalidate.assert_not_called()

    def test_precondition_unmet_is_an_error_with_no_writes(self):
        before = self._digest()
        resp = self._call(mode="run")
        self.assertEqual(resp["status"], "error")
        self.assertEqual([d["code"] for d in resp["diagnostics"]], ["techdocs_precondition_unmet"])
        self.assertEqual(len(resp["data"]["missing_targets"]), 3)
        self.assertEqual(resp["data"]["written_paths"], [])
        for rel in self.TRIO:
            self.assertFalse((self.root / rel).exists(), rel)
        self.assertEqual(self._digest(), before)

    def test_non_regular_destination_is_refused_before_any_write(self):
        self._targets()
        (self.root / "docs" / "index.md").mkdir()
        before = self._digest()
        resp = self._call(mode="run")
        self.assertEqual(resp["status"], "error")
        self.assertEqual([d["code"] for d in resp["diagnostics"]], ["techdocs_destination_refused"])
        self.assertIn("not a regular file", resp["data"]["refusal"])
        self.assertFalse((self.root / "catalog-info.yaml").exists())
        self.assertFalse((self.root / "mkdocs.yml").exists())
        self.assertEqual(self._digest(), before)

    def test_write_failure_after_preflight_is_reported_and_invalidates_the_cache(self):
        self._targets()
        import render_agent_surfaces as ras
        real = ras._write_review_carrier_text
        calls = []

        def flaky(path, content, *, exclusive=False):
            calls.append(path.name)
            if path.name == "mkdocs.yml":
                raise RuntimeError(f"review carrier write refused for {path}: simulated EACCES")
            return real(path, content, exclusive=exclusive)

        cache = MagicMock()
        with patch.object(ras, "_write_review_carrier_text", side_effect=flaky):
            resp = self._call(mode="run", cache=cache)
        self.assertEqual(resp["status"], "error")
        self.assertEqual([d["code"] for d in resp["diagnostics"]], ["techdocs_write_failed"])
        self.assertIn("simulated EACCES", resp["data"]["refusal"])
        # catalog-info.yaml was written before the failure; the envelope reports the tree.
        self.assertTrue((self.root / "catalog-info.yaml").is_file())
        self.assertFalse((self.root / "mkdocs.yml").exists())
        # written_paths names what THIS run wrote before failing, and the member lists
        # report the tree as it is now even though a lone generated member is not a
        # mixed trio (partial stays None). Reporting [] here would contradict the tree.
        self.assertEqual(resp["data"]["written_paths"], ["catalog-info.yaml"])
        self.assertEqual(resp["data"]["generated_paths"], ["catalog-info.yaml"])
        self.assertEqual(resp["data"]["preserved_paths"], [])
        self.assertEqual(resp["data"]["absent_paths"], ["mkdocs.yml", "docs/index.md"])
        self.assertIsNone(resp["data"]["partial"])
        cache.invalidate.assert_called_once()

    def test_non_runtimeerror_failures_are_normalized_into_an_envelope(self):
        """The module normalizes OSError and UnicodeDecodeError into TechdocsWriteFailed.

        Neither is a RuntimeError (UnicodeDecodeError is a ValueError), so before the
        module wrapped them they escaped both entry points uncaught: the CLI printed a
        traceback with empty stdout under --json and the tool returned no envelope at all.
        """

        self._targets()
        import render_agent_surfaces as ras
        real = ras._write_review_carrier_text

        def flaky(path, content, *, exclusive=False):
            if path.name == "mkdocs.yml":
                raise PermissionError(13, "Permission denied", str(path))
            return real(path, content, exclusive=exclusive)

        cache = MagicMock()
        with patch.object(ras, "_write_review_carrier_text", side_effect=flaky):
            resp = self._call(mode="run", cache=cache)
        self.assertEqual(resp["status"], "error")
        self.assertEqual([d["code"] for d in resp["diagnostics"]], ["techdocs_write_failed"])
        self.assertIn("Permission denied", resp["data"]["refusal"])
        self.assertEqual(resp["data"]["written_paths"], ["catalog-info.yaml"])
        self.assertEqual(resp["data"]["generated_paths"], ["catalog-info.yaml"])
        cache.invalidate.assert_called_once()

    def test_a_non_utf8_template_is_an_envelope_not_a_traceback(self):
        """A target-local template in another encoding raises UnicodeDecodeError.

        It is a ValueError, so the (RuntimeError, OSError) clause did not hold it and it
        escaped the tool with a half-written tree and no cache invalidation.
        """

        self._targets()
        # _resolve_install_asset is target-first per file, so one operator-edited
        # template in the target tree is enough; the other two fall back to packaged.
        install = self.root / ".wavefoundry" / "framework" / "install"
        install.mkdir(parents=True, exist_ok=True)
        (install / "mkdocs.template.yml").write_bytes(b"site_name: \xff\xfe broken\n")

        cache = MagicMock()
        resp = self._call(mode="run", cache=cache)
        self.assertEqual(resp["status"], "error")
        self.assertEqual([d["code"] for d in resp["diagnostics"]], ["techdocs_write_failed"])
        self.assertEqual(resp["data"]["written_paths"], ["catalog-info.yaml"])
        self.assertTrue((self.root / "catalog-info.yaml").is_file())
        self.assertFalse((self.root / "mkdocs.yml").exists())
        cache.invalidate.assert_called_once()

    def test_mixed_trio_carries_the_partial_advisory_and_all_generated_does_not(self):
        self._targets()
        (self.root / "mkdocs.yml").write_text("site_name: Mine\n", encoding="utf-8")
        resp = self._call(mode="run")
        self.assertEqual(resp["status"], "ok")
        codes = [d["code"] for d in resp["diagnostics"]]
        self.assertEqual(codes, ["backstage_techdocs_partial"])
        self.assertTrue(resp["diagnostics"][0].get("advisory"))
        self.assertEqual(resp["diagnostics"][0]["message"], resp["data"]["partial"]["detail"])
        self.assertEqual(resp["data"]["partial"]["preserved_paths"], ["mkdocs.yml"])
        self.assertEqual(resp["data"]["written_paths"], ["catalog-info.yaml", "docs/index.md"])
        # dry_run on the (now mixed) tree carries it too, still writing nothing.
        dry = self._call(mode="dry_run")
        self.assertEqual([d["code"] for d in dry["diagnostics"]], ["backstage_techdocs_partial", "dry_run"])
        # Negative control: an all-generated tree carries no advisory.
        for rel in self.TRIO:
            (self.root / rel).unlink()
        clean = self._call(mode="run")
        self.assertEqual(clean["diagnostics"], [])

    def test_invalid_mode_is_rejected_without_writes(self):
        self._targets()
        before = self._digest()
        resp = self._call(mode="write")
        self.assertEqual(resp["status"], "error")
        self.assertEqual([d["code"] for d in resp["diagnostics"]], ["invalid_arguments"])
        self.assertEqual(self._digest(), before)

    def test_cli_and_mcp_share_the_module_function(self):
        import render_agent_surfaces as ras
        import techdocs_baseline as cli
        import io
        self._targets()
        seen = []
        real = ras.render_techdocs_baseline

        def spy(repo_root, *, dry_run=False):
            seen.append((repo_root, dry_run))
            return real(repo_root, dry_run=dry_run)

        with patch.object(ras, "render_techdocs_baseline", side_effect=spy):
            self._call(mode="dry_run")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc = cli.main(["--root", str(self.root), "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(seen, [(self.root, True), (self.root, False)])
        # No re-implementation in the tool body: it delegates and never opens the trio itself.
        src = inspect.getsource(self.srv.wf_techdocs_baseline_response)
        self.assertIn("render_techdocs_baseline(", src)
        for forbidden in ("os.open(", "TECHDOCS_BASELINES", "_write_review_carrier_text", "_load_script("):
            self.assertNotIn(forbidden, src)

    def test_registration_tier_registry_extractor_and_checkpoint_guard(self):
        import mcp_tool_roster as roster
        import publication_control
        self.assertEqual(roster.TOOL_TIERS["wf_techdocs_baseline"], roster.TIER_WRITE)
        writer = publication_control._BY_TOOL["wf_techdocs_baseline"]
        self.assertEqual((writer.producer, writer.contention_policy, writer.surface), ("techdocs_baseline", "fail_fast", "tool"))
        self.assertIn("wf_techdocs_baseline", publication_control.registered_publication_tool_names())
        # Cost accounting credits the written members on a real run only.
        extractor = self.srv._ARTIFACT_EXTRACTORS["wf_techdocs_baseline"]
        self._targets()
        run = self._call(mode="run")
        tokens, digest = extractor(self.root, run)
        self.assertEqual(len(tokens), 3)
        self.assertIsNone(digest)
        self.assertEqual(extractor(self.root, self._call(mode="dry_run")), ([], None))
        # Upgrade checkpoint: the guard wraps the tool by name and refuses every mode.
        calls = []

        def original(*args, **kwargs):
            calls.append((args, kwargs))
            return {"status": "ok"}

        tool = types.SimpleNamespace(fn=original)
        mcp = types.SimpleNamespace(_tool_manager=types.SimpleNamespace(_tools={"wf_techdocs_baseline": tool}))
        checkpoint = self.root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps({"current_phase": "surface_rendering"}), encoding="utf-8")
        self.srv._wrap_upgrade_publication_guard(mcp, lambda: types.SimpleNamespace(root=self.root))
        result = tool.fn(mode="run")
        self.assertEqual(result["status"], "error")
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["upgrade_in_progress"])
        self.assertEqual(calls, [])

    def test_registered_tool_is_mutating_and_locks_only_on_run(self):
        runner = load_thin_runner()
        try:
            mcp = runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        tool = mcp._tool_manager._tools["wf_techdocs_baseline"]
        self.assertIs(tool.annotations.readOnlyHint if hasattr(tool.annotations, "readOnlyHint") else tool.annotations["readOnlyHint"], False)
        schema = tool.parameters.get("properties", {})
        self.assertEqual(schema.get("mode", {}).get("default"), "dry_run")
        self._targets()
        with patch.object(self.srv, "project_state_publication_lock", wraps=self.srv.project_state_publication_lock) as lock, \
             patch.object(self.srv, "_run_post_write_lint", return_value={"passed": True, "errors": [], "warnings": [], "output": "ok"}, create=True), \
             patch.object(self.srv, "_trigger_background_index_refresh_for_paths", return_value={}):
            dry = tool.fn()
            self.assertEqual(dry["status"], "dry_run")
            lock.assert_not_called()
            run = tool.fn(mode="run")
            self.assertEqual(run["status"], "ok")
            lock.assert_called_once()
        self.assertEqual(run["data"]["written_paths"], list(self.TRIO))


class UpgradePublicationWrapperContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def _mcp(self, name, fn):
        tool = types.SimpleNamespace(fn=fn)
        manager = types.SimpleNamespace(_tools={name: tool})
        return types.SimpleNamespace(_tool_manager=manager), tool

    def _checkpoint(self, root: Path, phase: str = "surface_rendering") -> None:
        path = root / ".wavefoundry" / "upgrade-in-progress.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"current_phase": phase}), encoding="utf-8")

    def test_review_public_path_refuses_during_upgrade_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._checkpoint(root)
            calls = []
            def original(*args, **kwargs):
                calls.append((args, kwargs))
                return {"status": "ok"}
            mcp, tool = self._mcp("wf_review_wave", original)
            self.srv._wrap_upgrade_publication_guard(
                mcp, lambda: types.SimpleNamespace(root=root)
            )

            result = tool.fn(wave_id="1abc")

            self.assertEqual(result["status"], "error")
            self.assertEqual(
                [row["code"] for row in result["diagnostics"]],
                ["upgrade_in_progress"],
            )
            self.assertEqual(calls, [])

    def test_index_build_diagnostic_renders_the_composed_recovery_text(self):
        """1u44n (AC-2): the MCP index_build refusal strips only the
        `upgrade_in_progress: ` prefix, so the diagnostic renders the SAME
        enriched zero-pending recovery text as the composition site (the
        in-upgrade child raise renders the identical full string; asserted in
        test_review_policy)."""
        import publication_control

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / ".wavefoundry" / "upgrade-in-progress.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "current_phase": "awaiting_memory_validation",
                        "memory_backfill_pending": 0,
                    }
                ),
                encoding="utf-8",
            )
            reason = publication_control.publication_checkpoint_reason(
                root, "index_build"
            )
            mcp, tool = self._mcp(
                "index_build", lambda **_kwargs: {"status": "ok"}
            )
            self.srv._wrap_upgrade_publication_guard(
                mcp, lambda: types.SimpleNamespace(root=root)
            )
            result = tool.fn(content="docs")
            self.assertEqual(result["status"], "error")
            diag = result["diagnostics"][0]
            self.assertEqual(diag["code"], "upgrade_in_progress")
            self.assertEqual(
                diag["message"], reason.removeprefix("upgrade_in_progress: ")
            )
            self.assertIn("resume_after_memory", diag["message"])
            self.assertIn("index_health", diag["message"])

    def test_upgrade_guard_is_outermost_and_never_waits_on_lifecycle_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._checkpoint(root)
            calls = []
            def original(*args, **kwargs):
                calls.append((args, kwargs))
                return {"status": "ok"}
            mcp, tool = self._mcp("wf_prepare_wave", original)
            self.srv._wrap_lifecycle_mutation_lock(
                mcp, lambda: types.SimpleNamespace(root=root)
            )
            self.srv._wrap_upgrade_publication_guard(
                mcp, lambda: types.SimpleNamespace(root=root)
            )

            with patch.object(
                self.srv,
                "_lifecycle_mutation_lock",
                side_effect=AssertionError("upgrade guard must return before lock acquisition"),
            ):
                result = tool.fn(wave_id="1abc")

            self.assertEqual(result["status"], "error")
            self.assertEqual(result["diagnostics"][0]["code"], "upgrade_in_progress")
            self.assertEqual(calls, [])

    def test_read_only_tool_records_no_context_efficiency_cost_during_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._checkpoint(root)
            recorded = []

            class Telemetry:
                focus = types.SimpleNamespace(wave_id="", stage="general")

                def record_tool_cost(self, *args, **kwargs):
                    recorded.append((args, kwargs))

            mcp, tool = self._mcp(
                "wf_help", lambda **_kwargs: {"status": "ok", "data": {}}
            )
            handler = types.SimpleNamespace(root=root, telemetry=Telemetry())
            self.srv._wrap_first_party_tool_costs(mcp, lambda: handler)
            result = tool.fn()
            self.assertEqual(result["status"], "ok")
            self.assertEqual(recorded, [])

    def test_native_retrieval_recorder_is_quiet_during_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._checkpoint(root)

            class Telemetry:
                def record_retrieval(self, *_args, **_kwargs):
                    raise AssertionError("retrieval telemetry must be fenced")

            handler = types.SimpleNamespace(root=root, telemetry=Telemetry())
            response = {"status": "ok", "data": {"content": "result"}}
            result = self.srv._record_retrieval_context(
                handler, "code_read", response, indexed_epoch_stable=True
            )
            self.assertIs(result, response)
            self.assertNotIn("context_avoided", result["data"])

    def test_background_index_launcher_is_quiet_during_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._checkpoint(root)
            with patch.object(
                self.srv, "_reap_background_build_pids",
                side_effect=AssertionError("checkpoint must precede native work"),
            ), patch("subprocess.Popen") as popen:
                self.assertFalse(
                    self.srv._start_background_index_refresh(root, "project")
                )
            popen.assert_not_called()
            self.assertFalse((root / ".wavefoundry/index").exists())


if __name__ == "__main__":
    unittest.main()
