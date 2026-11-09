#!/usr/bin/env python3
"""``wf setup`` advises upgrading an affected uv and upgrades only when asked (wave 22upa, change 22ube).

Every uv before 0.13.4 trusts a compromised TLS root (GHSA-hq85-5cpj-mr62). These tests drive
the real ``setup_wavefoundry.main`` with the real ``setup_index`` uv step. Only the index runs,
the probed uv (a fake script that prints a chosen version) and the pip install are replaced.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
import test_setup_wavefoundry as base

AFFECTED = "0.12.22"


class _Harness(unittest.TestCase):
    def setUp(self):
        base.SetupWavefoundryTests.setUp(self)
        self.mod = base.load_setup_wavefoundry(real_uv_step=True)
        self.index = self.mod._load_setup_index()
        self.events: list[str] = []
        self.forwarded: list[list[str]] = []
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.venv_uv = self.tmp / "venv" / "bin" / "uv"
        self.path_uv = self.tmp / "path" / "uv"
        self.installs = 0
        self.install_locks: list = []

    def _fake_uv(self, body: str) -> list[str]:
        script = self.tmp / "fake_uv.py"
        script.write_text(textwrap.dedent(body), encoding="utf-8")
        return [sys.executable, "-I", "-B", str(script)]

    def _reports(self, version: str) -> list[str]:
        return self._fake_uv(f"print('uv {version} (abc 2026-01-01)')\n")

    def _index_main(self, argv=None):
        self.forwarded.append(list(argv or []))
        self.events.append("deps" if "--deps-only" in (argv or []) else "index")
        return 0

    def _run(self, argv, *, probe, uv_path, install_result=True, versions=None):
        index = self.index
        state = {"versions": list(versions or [])}

        def install(venv_python, root=None, *, lock=None):
            self.installs += 1
            self.install_locks.append(lock)
            self.events.append("upgrade")
            if not install_result:
                index._uv_bootstrap_failed()
                return None
            return self.venv_uv

        def version_of(path):
            if state["versions"]:
                return state["versions"].pop(0)
            return real_version(path)

        real_version = index._uv_version
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(self.mod, "_load_setup_index", return_value=index))
            stack.enter_context(patch.object(self.mod, "_run_render_platform_surfaces", return_value=0))
            stack.enter_context(patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0))
            stack.enter_context(patch.object(index, "main", side_effect=self._index_main))
            stack.enter_context(patch.object(index, "_UV_PROBE_COMMAND", probe))
            stack.enter_context(patch.object(index, "_uv_bin", return_value=uv_path))
            stack.enter_context(patch.object(index, "_venv_uv_path", return_value=self.venv_uv))
            stack.enter_context(patch.object(index, "_held_install_lock",
                                             side_effect=lambda root=None: contextlib.nullcontext("lock")))
            stack.enter_context(patch.object(index, "_bootstrap_venv", return_value=self.tmp / "venv" / "bin" / "python"))
            stack.enter_context(patch.object(index, "_install_pinned_uv", side_effect=install))
            if versions is not None:
                stack.enter_context(patch.object(index, "_uv_version", side_effect=version_of))
            stack.enter_context(contextlib.redirect_stdout(stdout))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            rc = self.mod.main(list(argv))
        return rc, stdout.getvalue(), stderr.getvalue()


class AdvisoryTests(_Harness):
    """AC-1, AC-2, AC-3, AC-5."""

    def test_an_affected_uv_gets_one_advisory_as_the_last_output(self):
        rc, _out, err = self._run([], probe=self._reports(AFFECTED), uv_path=self.venv_uv)
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.events, ["deps", "index"])
        self.assertEqual(err.count("ADVISORY:"), 1, err)
        advisory = err[err.index("ADVISORY:"):]
        self.assertEqual(err.rstrip().splitlines()[-1], advisory.rstrip().splitlines()[-1])
        for text in (str(self.venv_uv), AFFECTED, "GHSA-hq85-5cpj-mr62", "--upgrade-uv"):
            self.assertIn(text, advisory)
        self.assertEqual(self.installs, 0)

    def test_fixed_versions_get_no_advisory(self):
        for version in ("0.13.4", "0.13.5", "1.0.0"):
            with self.subTest(version=version):
                self.events.clear()
                rc, _out, err = self._run([], probe=self._reports(version), uv_path=self.venv_uv)
                self.assertEqual(rc, 0, err)
                self.assertNotIn("ADVISORY:", err)
        self.assertEqual(self.installs, 0)

    def test_the_remedy_depends_on_where_the_uv_lives(self):
        _rc, _out, venv_err = self._run([], probe=self._reports(AFFECTED), uv_path=self.venv_uv)
        self.assertIn("--upgrade-uv", venv_err)
        self.assertNotIn("uv self update", venv_err)
        _rc, _out, path_err = self._run([], probe=self._reports(AFFECTED), uv_path=self.path_uv)
        self.assertIn(str(self.path_uv), path_err)
        self.assertIn("uv self update", path_err)
        self.assertIn("--upgrade-uv", path_err)
        self.assertEqual(self.installs, 0)

    def test_windows_remedy_and_tool_uv_location(self):
        index = self.index
        # Only the remedy text is rendered under a patched os.name: pathlib refuses
        # WindowsPath on POSIX, so the tool-uv location is checked for this platform.
        with patch.object(index.os, "name", "nt"):
            text = index.uv_tls_advisory("C:/tool/Scripts/uv.exe", (0, 12, 22), in_tool_venv=True,
                                         root=self.tmp)
        self.assertIn("wf.cmd", text)
        self.assertIn("--upgrade-uv", text)
        location = index._venv_uv_path(self.tmp / "venv" / "bin" / "python")
        expected = ("Scripts", "uv.exe") if os.name == "nt" else ("bin", "uv")
        self.assertEqual((location.parent.name, location.name), expected)

    def test_an_unreadable_version_produces_no_advisory(self):
        cases = {
            "nonzero exit": self._fake_uv("import sys; print('uv 0.12.22'); sys.exit(3)\n"),
            "unparseable": self._fake_uv("print('not a version')\n"),
            "timeout": self._fake_uv("import time; time.sleep(30)\n"),
            "launch failure": [str(self.tmp / "missing-uv-binary")],
        }
        for name, probe in cases.items():
            with self.subTest(case=name), patch.object(self.index, "UV_VERSION_PROBE_TIMEOUT_SECONDS", 1.0):
                self.events.clear()
                rc, _out, err = self._run([], probe=probe, uv_path=self.venv_uv)
                self.assertEqual(rc, 0, err)
                self.assertNotIn("ADVISORY:", err)
                self.assertEqual(self.events, ["deps", "index"])
        self.assertEqual(self.installs, 0)

    def test_no_uv_leaves_the_bootstrap_path_alone(self):
        rc, _out, err = self._run([], probe=self._reports(AFFECTED), uv_path=None)
        self.assertEqual(rc, 0, err)
        self.assertNotIn("ADVISORY:", err)
        self.assertEqual(self.installs, 0)


class UpgradeTests(_Harness):
    """AC-4."""

    def test_upgrade_replaces_an_affected_tool_uv_before_any_dependency_install(self):
        self.venv_uv.parent.mkdir(parents=True)
        self.venv_uv.write_text("", encoding="utf-8")
        rc, out, err = self._run(["--upgrade-uv"], probe=self._reports("0.13.5"), uv_path=self.venv_uv,
                                 versions=[(0, 12, 22), (0, 13, 5), (0, 13, 5)])
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.installs, 1)
        # The install runs under the held install lock (the harness lock is "lock").
        self.assertEqual(self.install_locks, ["lock"])
        self.assertEqual(self.events, ["upgrade", "deps", "index"])
        self.assertIn("Upgrading uv to the pinned uv==0.13.5 (GHSA-hq85-5cpj-mr62)", out)
        self.assertIn("is now 0.13.5", out)
        self.assertNotIn("uv not found", out + err)
        self.assertNotIn("ADVISORY:", err)
        for argv in self.forwarded:
            self.assertNotIn("--upgrade-uv", argv)

    def test_upgrade_with_a_satisfying_uv_installs_nothing(self):
        self.venv_uv.parent.mkdir(parents=True)
        self.venv_uv.write_text("", encoding="utf-8")
        rc, out, err = self._run(["--upgrade-uv"], probe=self._reports("0.13.5"), uv_path=self.venv_uv,
                                 versions=[(0, 13, 5), (0, 13, 5)])
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.installs, 0)
        self.assertIn("already satisfies", out)
        self.assertEqual(self.events, ["deps", "index"])

    def test_a_failed_upgrade_exits_2_before_any_dependency_install(self):
        self.venv_uv.parent.mkdir(parents=True)
        self.venv_uv.write_text("", encoding="utf-8")
        rc, _out, err = self._run(["--upgrade-uv"], probe=self._reports(AFFECTED), uv_path=self.venv_uv,
                                  install_result=False, versions=[(0, 12, 22)])
        self.assertEqual(rc, 2)
        self.assertEqual(self.events, ["upgrade"])
        self.assertIn("No unverified uv was installed", err)
        self.assertIn("no dependencies were installed", err)

    def test_help_names_the_flag(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(self.mod.main(["--help"]), 0)
        self.assertIn("--upgrade-uv", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
