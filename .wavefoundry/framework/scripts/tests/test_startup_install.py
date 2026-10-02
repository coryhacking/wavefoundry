"""Setup after an upgrade and a pull (wave 1zfd9, change 1zcm3).

MCP startup installs missing or version-incompatible declared dependencies
when they are the only thing blocking it: in the background when the server
runs without them, before starting otherwise, through uv only, with nothing on
stdout. The upgrade provisions dependencies as its own step and reports setup
readiness in its summary.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import queue
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import process_info  # noqa: E402
import runtime_lock  # noqa: E402
import setup_index  # noqa: E402
import setup_readiness  # noqa: E402
import setup_requirements  # noqa: E402
import venv_bootstrap  # noqa: E402
from server_tools_support import _make_repo, load_server  # noqa: E402

PSUTIL = setup_requirements.PSUTIL_REQUIREMENT


def _assessment(*codes: str, missing=(), blocked=True, status="action_required") -> dict:
    reasons = []
    for code in codes:
        item = {"code": code, "message": code}
        if code == "dependencies_missing":
            item["missing"] = list(missing)
        reasons.append(item)
    return {
        "schema_version": 1, "status": status, "startup_blocked": blocked, "reasons": reasons,
        "actions": [{"kind": "setup", "argv": ["wf", "setup", "--root", "/r"]}],
        "advisories": [], "limitations": [], "timings_ms": {},
    }


FAKE_UV = textwrap.dedent(
    """
    import os, sys, time
    # A stand-in for uv: writes to its OWN stdout and stderr, then records the
    # install in a marker file named by the environment.
    print("UV-STDOUT-MARK", flush=True)
    print("UV-STDERR-MARK", file=sys.stderr, flush=True)
    time.sleep(float(os.environ.get("FAKE_UV_SLEEP", "0")))
    marker = os.environ.get("FAKE_UV_MARKER")
    if marker:
        with open(marker, "a", encoding="utf-8") as handle:
            handle.write(" ".join(sys.argv[1:]) + "\\n")
    sys.exit(int(os.environ.get("FAKE_UV_EXIT", "0")))
    """
)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name).resolve()
        self.venv = self.dir / "venv"
        python = self.venv.joinpath(*(("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")))
        python.parent.mkdir(parents=True)
        python.write_text("", encoding="utf-8")
        self.fake_uv = self.dir / "fake_uv.py"
        self.fake_uv.write_text(FAKE_UV, encoding="utf-8")
        self.marker = self.dir / "installed.txt"
        env = patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(self.venv), "FAKE_UV_MARKER": str(self.marker)})
        env.start()
        self.addCleanup(env.stop)
        seam = patch.object(setup_index, "_STARTUP_UV_COMMAND", [sys.executable, str(self.fake_uv)])
        seam.start()
        self.addCleanup(seam.stop)


class TriggerTests(unittest.TestCase):
    def test_non_blocking_reasons_a_pull_produces_do_not_prevent_the_install(self):
        result = _assessment("setup_inputs_changed", "producer_changed", "dependencies_missing", missing=[PSUTIL])
        self.assertEqual(setup_readiness.startup_install_specs(result), [PSUTIL])

    def test_excluded_reasons_and_unblocked_results_install_nothing(self):
        for code in sorted(setup_readiness.STARTUP_INSTALL_EXCLUDED_REASONS):
            with self.subTest(code=code):
                result = _assessment(code, "dependencies_missing", missing=[PSUTIL])
                self.assertEqual(setup_readiness.startup_install_specs(result), [])
        self.assertEqual(
            setup_readiness.startup_install_specs(_assessment("dependencies_missing", missing=[PSUTIL], blocked=False)), []
        )

    def test_the_real_assessment_lists_the_missing_specs(self):
        with patch.object(setup_readiness, "_dependencies", return_value=[PSUTIL]):
            result = setup_readiness.assess_setup(SCRIPTS.parents[2], use_stamp=False)
        reason = [item for item in result["reasons"] if item["code"] == "dependencies_missing"]
        self.assertEqual(reason[0]["missing"], [PSUTIL])
        self.assertEqual(setup_readiness.missing_dependency_specs(result), [PSUTIL])


class InstallerTests(_Tmp):
    def test_installs_exactly_the_given_specs_through_uv_from_the_venv_base(self):
        calls = []
        real = setup_index._run_install_step

        def record(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return real(cmd, **kwargs)

        with patch.object(setup_index, "_run_install_step", side_effect=record):
            outcome = setup_index.install_requirement_specs([PSUTIL])
        self.assertEqual(outcome["status"], "installed", outcome)
        cmd, kwargs = calls[0]
        self.assertEqual(cmd[:2], [sys.executable, str(self.fake_uv)])
        self.assertEqual(cmd[2:4], ["pip", "install"])
        self.assertIn("--python", cmd)
        self.assertIn("--exclude-newer", cmd)
        self.assertEqual(cmd[-1], PSUTIL)
        self.assertEqual(kwargs["cwd"], str(self.venv))
        self.assertNotIn("pip", [Path(part).name for part in cmd[:2]])

    def test_no_uv_installs_nothing_and_never_falls_back_to_pip(self):
        with patch.object(setup_index, "_STARTUP_UV_COMMAND", None), \
                patch.object(setup_index, "_uv_bin", return_value=None), \
                patch.object(setup_index, "_bootstrap_uv") as bootstrap, \
                patch.object(setup_index, "_run_install_step") as run:
            outcome = setup_index.install_requirement_specs([PSUTIL])
        self.assertEqual(outcome["status"], "no_uv")
        self.assertIn("wf setup", outcome["message"])
        bootstrap.assert_not_called()
        run.assert_not_called()

    def test_failed_install_names_wf_setup_and_windows_names_what_to_stop(self):
        with patch.dict(os.environ, {"FAKE_UV_EXIT": "1"}):
            outcome = setup_index.install_requirement_specs([PSUTIL])
        self.assertEqual(outcome["status"], "failed")
        self.assertIn("wf setup", outcome["message"])

        class _Nt:
            name = "nt"

            def __getattr__(self, attr):
                return getattr(os, attr)

        failing = MagicMock(returncode=1)
        with patch.object(setup_index, "os", _Nt()), \
                patch.object(setup_index, "_run_install_step", return_value=failing):
            outcome = setup_index.install_requirement_specs([PSUTIL])
        self.assertIn("index builds and the dashboard", outcome["message"])

    def test_a_failed_uv_names_the_network_cause_and_wf_setup(self):
        # Wave 1zicq: an unreachable index makes uv exit 2 on its own; the message says why.
        with patch.dict(os.environ, {"FAKE_UV_EXIT": "2"}):
            outcome = setup_index.install_requirement_specs([PSUTIL])
        self.assertEqual(outcome["status"], "failed")
        self.assertIn("exit 2", outcome["message"])
        self.assertIn("network, proxy or TLS access to the package index", outcome["message"])
        self.assertIn("run `wf setup`", outcome["message"])

    def test_the_interpreter_path_is_absolute_for_a_relative_tool_venv(self):
        calls = []
        # A relative override from the venv's parent folder: same drive on Windows.
        with contextlib.chdir(self.venv.parent), \
                patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": self.venv.name}), \
                patch.object(setup_index, "_run_install_step", side_effect=lambda cmd, **kw: calls.append(cmd) or MagicMock(returncode=0)):
            setup_index.install_requirement_specs([PSUTIL])
        python = calls[0][calls[0].index("--python") + 1]
        self.assertTrue(os.path.isabs(python), python)

    def test_timeout_reports_network_guidance(self):
        timeout = subprocess.TimeoutExpired(["uv"], 1)
        with patch.object(setup_index, "_run_install_step", side_effect=timeout):
            outcome = setup_index.install_requirement_specs([PSUTIL])
        self.assertEqual(outcome["status"], "failed")
        self.assertIn("timed out", outcome["message"])

    def test_recheck_under_the_lock_skips_an_install_already_done(self):
        with patch.object(setup_index, "_run_install_step") as run:
            outcome = setup_index.install_requirement_specs([PSUTIL], recheck=lambda: [])
        self.assertEqual(outcome["status"], "already_installed")
        run.assert_not_called()

    def test_a_held_lock_makes_a_bounded_waiter_report_busy(self):
        holder = runtime_lock.RuntimeFileLock(setup_index.dependency_install_lock_path(), blocking=False)
        holder.acquire()
        self.addCleanup(holder.release)
        started = time.monotonic()
        outcome = setup_index.install_requirement_specs([PSUTIL], lock_wait_seconds=0.3)
        self.assertEqual(outcome["status"], "busy")
        self.assertLess(time.monotonic() - started, 10)

    def test_the_lock_sits_beside_the_venv_and_is_shared_with_wf_setup(self):
        path = setup_index.dependency_install_lock_path()
        self.assertEqual(path.parent, self.venv.parent)
        self.assertFalse(str(path).startswith(str(self.venv) + os.sep))
        with setup_index._held_install_lock() as lock:
            self.assertEqual(lock.path, path)
            outcome = setup_index.install_requirement_specs([PSUTIL], lock_wait_seconds=0.2)
        self.assertEqual(outcome["status"], "busy")


class LockOwnershipTests(_Tmp):
    """The shared install lock owns every mutation of the tool venv (operator review, 1zfd9)."""

    def test_a_lock_that_cannot_be_taken_fails_closed(self):
        class _Broken:
            def acquire(self):
                raise runtime_lock.RuntimeLockError(13, "lock path refused")

            def release(self):
                pass

        with patch.object(setup_index, "_dependency_install_lock", return_value=_Broken()), \
                patch.object(setup_index, "_venv_needs_bootstrap", return_value=True), \
                patch.object(setup_index, "_bootstrap_venv") as bootstrap, \
                patch.object(setup_index, "_install_deps") as install, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as raised:
                setup_index.ensure_deps()
            with self.assertRaises(SystemExit):
                setup_index.ensure_migration_deps(Path("/r"))
        self.assertEqual(raised.exception.code, 2)
        bootstrap.assert_not_called()
        install.assert_not_called()
        self.assertIn("nothing was installed", err.getvalue())

    def test_venv_bootstrap_runs_only_while_the_lock_is_held(self):
        seen = []

        def bootstrap(root=None, *, lock=None):
            probe = runtime_lock.RuntimeFileLock(setup_index.dependency_install_lock_path(), blocking=False)
            try:
                probe.acquire()
                probe.release()
                seen.append("free")
            except runtime_lock.RuntimeLockBusy:
                seen.append("held")
            return self.venv / "bin" / "python"

        with patch.object(setup_index, "_bootstrap_venv", side_effect=bootstrap), \
                patch.object(setup_index, "_venv_needs_bootstrap", return_value=True), \
                patch.object(setup_index, "_missing_in_venv", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()):
            setup_index.ensure_deps()
        self.assertEqual(seen, ["held"])

    def test_another_owner_blocks_bootstrap_until_it_releases(self):
        holder = runtime_lock.RuntimeFileLock(setup_index.dependency_install_lock_path(), blocking=False)
        holder.acquire()
        released = threading.Event()
        order = []

        def bootstrap(root=None, *, lock=None):
            order.append("bootstrap" if released.is_set() else "bootstrap-while-held")
            return self.venv / "bin" / "python"

        def run():
            with patch.object(setup_index, "_bootstrap_venv", side_effect=bootstrap), \
                    patch.object(setup_index, "_venv_needs_bootstrap", return_value=True), \
                    patch.object(setup_index, "_missing_in_venv", return_value=[]), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                setup_index.ensure_deps()

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        try:
            time.sleep(0.6)
            before_release = list(order)
        finally:
            released.set()
            holder.release()
            worker.join(timeout=30)
        self.assertEqual(before_release, [], "bootstrap ran while another owner held the lock")
        self.assertEqual(order, ["bootstrap"])

    def test_a_check_that_changes_nothing_takes_no_lock(self):
        # A no-op check must not fail on lock errors (DEL-LOCK-LINK-REFUSAL).
        with patch.object(setup_index, "_dependency_install_lock", side_effect=AssertionError("lock taken")), \
                patch.object(setup_index, "_venv_needs_bootstrap", return_value=False), \
                patch.object(setup_index, "_missing_in_venv", return_value=[]), \
                patch.object(setup_index, "_bootstrap_venv") as bootstrap, \
                contextlib.redirect_stdout(io.StringIO()):
            setup_index.ensure_deps()
            setup_index.ensure_migration_deps(Path("/r"))
        bootstrap.assert_not_called()

    def test_a_missing_package_found_without_the_lock_is_rechecked_under_it(self):
        answers = [["psutil>=6"], []]
        with patch.object(setup_index, "_venv_needs_bootstrap", return_value=False), \
                patch.object(setup_index, "_missing_in_venv", side_effect=lambda *a, **k: answers.pop(0)), \
                patch.object(setup_index, "_bootstrap_venv", return_value=self.venv / "bin" / "python") as bootstrap, \
                patch.object(setup_index, "_install_deps") as install, \
                contextlib.redirect_stdout(io.StringIO()):
            setup_index.ensure_deps()
        bootstrap.assert_called_once()
        install.assert_not_called()

    def test_venv_needs_bootstrap_reads_the_venv_state(self):
        with patch.object(venv_bootstrap, "_venv_python_version", return_value=sys.version_info[:2]):
            self.assertFalse(setup_index._venv_needs_bootstrap())
        with patch.object(venv_bootstrap, "_venv_python_version", return_value=(2, 7)):
            self.assertTrue(setup_index._venv_needs_bootstrap())
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(self.dir / "absent")}):
            self.assertTrue(setup_index._venv_needs_bootstrap())

    @unittest.skipIf(os.name == "nt", "symlink creation needs privileges on Windows")
    def test_a_linked_per_user_base_locks_at_its_resolved_path(self):
        real = self.dir / "elsewhere"
        real.mkdir()
        home = self.dir / "home"
        home.mkdir()
        (home / ".wavefoundry").symlink_to(real, target_is_directory=True)
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(home / ".wavefoundry" / "venv")}):
            path = setup_index.dependency_install_lock_path()
            self.assertEqual(path, real / ("venv" + setup_index.DEPENDENCY_INSTALL_LOCK_SUFFIX))
            with contextlib.redirect_stderr(io.StringIO()):
                with setup_index._held_install_lock() as lock:
                    self.assertEqual(lock.path, path)

    @unittest.skipIf(os.name == "nt", "symlink creation needs privileges on Windows")
    def test_every_spelling_of_a_linked_venv_directory_shares_one_lock(self):
        real = self.dir / "store" / "realvenv"
        real.mkdir(parents=True)
        link = self.dir / "venvlink"
        link.symlink_to(real, target_is_directory=True)
        paths = set()
        for spelling in (link, real):
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(spelling)}):
                paths.add(setup_index.dependency_install_lock_path())
        self.assertEqual(paths, {real.with_name("realvenv" + setup_index.DEPENDENCY_INSTALL_LOCK_SUFFIX)})

    def test_a_lock_path_that_cannot_be_resolved_fails_closed_without_a_traceback(self):
        # ntpath.realpath re-raises winerrors outside its allowlist (1zfd9 advisory).
        unresolvable = OSError(22, "The specified network name is no longer available")
        with patch.object(setup_index, "dependency_install_lock_path", side_effect=unresolvable), \
                patch.object(setup_index, "_run_install_step") as run:
            outcome = setup_index.install_requirement_specs([PSUTIL])
        self.assertEqual(outcome["status"], "failed")
        self.assertIn("lock unavailable", outcome["message"])
        self.assertIn("wf setup", outcome["message"])
        run.assert_not_called()
        with patch.object(setup_index, "dependency_install_lock_path", side_effect=unresolvable), \
                patch.object(setup_index, "_venv_needs_bootstrap", return_value=True), \
                patch.object(setup_index, "_bootstrap_venv") as bootstrap, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as raised:
                setup_index.ensure_deps()
        self.assertEqual(raised.exception.code, 2)
        bootstrap.assert_not_called()
        self.assertIn("nothing was installed", err.getvalue())

    @unittest.skipIf(os.name == "nt", "the carrier is inherited only on POSIX")
    def test_bootstrap_children_inherit_the_lock_carrier(self):
        lock = runtime_lock.RuntimeFileLock(setup_index.dependency_install_lock_path(), blocking=False)
        lock.acquire()
        self.addCleanup(lock.release)
        calls = []

        def record(cmd, **kwargs):
            calls.append(kwargs)
            return MagicMock(returncode=0)

        with patch.object(setup_index, "_run_install_step", side_effect=record), \
                patch.object(setup_index, "_uv_bin", return_value=None), \
                contextlib.redirect_stdout(io.StringIO()):
            setup_index._bootstrap_uv(self.venv / "bin" / "python", lock=lock)
            with patch.object(setup_index, "_tool_venv_python", return_value=self.dir / "new" / "bin" / "python"):
                setup_index._bootstrap_venv(lock=lock)
        self.assertEqual(len(calls), 2)
        for kwargs in calls:
            self.assertEqual(kwargs.get("pass_fds"), (lock.handle.fileno(),))


class UvConfigIsolationTests(_Tmp):
    def _cmd(self):
        calls = []
        with patch.object(setup_index, "_run_install_step", side_effect=lambda cmd, **kw: calls.append(cmd) or MagicMock(returncode=0)):
            setup_index.install_requirement_specs([PSUTIL])
        return calls[0]

    def test_a_falsy_uv_no_config_keeps_isolation_on(self):
        with patch.object(setup_index, "_operator_uv_config_files", return_value=[self.dir / "absent.toml"]), \
                patch.dict(os.environ, {"UV_CONFIG_FILE": "", "UV_NO_CONFIG": "0"}):
            self.assertEqual(setup_index._uv_config_args(), ["--no-config"])
        with patch.dict(os.environ, {"UV_CONFIG_FILE": "", "UV_NO_CONFIG": "1"}):
            self.assertEqual(setup_index._uv_config_args(), [])

    def test_no_operator_config_means_no_config_discovery(self):
        with patch.object(setup_index, "_operator_uv_config_files", return_value=[self.dir / "absent.toml"]), \
                patch.dict(os.environ, {"UV_CONFIG_FILE": "", "UV_NO_CONFIG": ""}):
            cmd = self._cmd()
        self.assertIn("--no-config", cmd)
        self.assertNotIn("--config-file", cmd)

    def test_the_operator_file_is_passed_explicitly(self):
        user = self.dir / "user-uv.toml"
        user.write_text("", encoding="utf-8")
        with patch.object(setup_index, "_operator_uv_config_files", return_value=[user]), \
                patch.dict(os.environ, {"UV_CONFIG_FILE": "", "UV_NO_CONFIG": ""}):
            cmd = self._cmd()
        self.assertEqual(cmd[cmd.index("--config-file") + 1], str(user))
        self.assertNotIn("--no-config", cmd)

    def test_an_operator_uv_config_file_variable_is_left_to_uv(self):
        with patch.dict(os.environ, {"UV_CONFIG_FILE": str(self.dir / "chosen.toml")}):
            cmd = self._cmd()
        self.assertNotIn("--no-config", cmd)
        self.assertNotIn("--config-file", cmd)

    def test_a_repository_uv_toml_above_the_venv_is_never_read_by_real_uv(self):
        import shutil

        uv = shutil.which("uv") or str(Path(sys.executable).parent / ("uv.exe" if os.name == "nt" else "uv"))
        if not Path(uv).is_file():
            self.skipTest("uv is not available")
        repo = self.dir / "checkout"
        (repo / "venv-inside").mkdir(parents=True)
        (repo / "uv.toml").write_text('[pip]\nindex-url = "http://127.0.0.1:9/repo-index"\n', encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if key not in ("UV_CONFIG_FILE", "UV_NO_CONFIG")}
        env["UV_OFFLINE"] = "1"
        with patch.object(setup_index, "_operator_uv_config_files", return_value=[]), \
                patch.dict(os.environ, {"UV_CONFIG_FILE": "", "UV_NO_CONFIG": ""}):
            args = setup_index._uv_config_args()
        # Offline: uv's verbose log names the configuration it found, without any index access.
        def found(extra):
            done = subprocess.run(
                [uv, "-v", "pip", "install", *extra, "--dry-run", "--python", sys.executable, "zzz-nonexistent-1zfd9"],
                cwd=repo / "venv-inside", capture_output=True, text=True, timeout=60, env=env,
            )
            return str(repo / "uv.toml") in done.stdout + done.stderr

        self.assertTrue(found([]), "control: uv discovers the repository uv.toml without isolation")
        self.assertFalse(found(args), "the startup install's arguments must keep it out")

    def test_a_relative_operator_uv_config_file_still_resolves_with_real_uv(self):
        # DEL-1ZICQ-RELATIVE-OPERATOR-CONFIG: installs run from the tool-venv base, so the
        # operator's relative UV_CONFIG_FILE must be resolved against the caller's folder first.
        import shutil

        uv = shutil.which("uv") or str(Path(sys.executable).parent / ("uv.exe" if os.name == "nt" else "uv"))
        if not Path(uv).is_file():
            self.skipTest("uv is not available")
        caller = self.dir / "caller"
        base = self.dir / "tool-venv-base"
        caller.mkdir()
        base.mkdir()
        (caller / "operator.toml").write_text("[pip]\n", encoding="utf-8")
        captured = []
        with contextlib.chdir(caller), \
                patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(base), "UV_CONFIG_FILE": "operator.toml", "UV_NO_CONFIG": ""}), \
                patch.object(setup_index, "_uv_bin", return_value=Path(uv)), \
                patch.object(setup_index, "_run_install_step", side_effect=lambda cmd, **kw: captured.append((cmd, kw)) or MagicMock(returncode=0)), \
                contextlib.redirect_stdout(io.StringIO()):
            setup_index._install_deps(["pip"], Path(sys.executable))
            cmd, kwargs = captured[0]
            env = dict(kwargs["env"] if kwargs.get("env") is not None else os.environ)
        self.assertEqual(kwargs["cwd"], str(base))
        self.assertEqual(env["UV_CONFIG_FILE"], str(caller / "operator.toml"))
        env["UV_OFFLINE"] = "1"
        done = subprocess.run(
            [cmd[0], "-v", *cmd[1:], "--dry-run"], cwd=kwargs["cwd"],
            capture_output=True, text=True, timeout=60, env=env,
        )
        self.assertNotIn("failed to open file", (done.stdout + done.stderr).lower())

    def test_pip_sees_the_same_cache_dir_from_the_venv_base_as_from_the_caller(self):
        # DEL-1ZICQ-TILDE-CACHE-PATH: pip expands "~" in PIP_CACHE_DIR, PIP_CERT and
        # PIP_CLIENT_CERT itself; the rebased value must mean what pip made of the original.
        caller = self.dir / "caller"
        base = self.dir / "tool-venv-base"
        caller.mkdir()
        base.mkdir()

        def pip_cache_dir(env, cwd):
            done = subprocess.run(
                [sys.executable, "-m", "pip", "cache", "dir"], cwd=cwd,
                capture_output=True, text=True, timeout=120, env=env,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            return os.path.realpath(done.stdout.strip())

        for value in ("~/.cache/wf-tilde-probe", "relative-cache"):
            with self.subTest(value=value):
                original = dict(os.environ, PIP_CACHE_DIR=value, PIP_DISABLE_PIP_VERSION_CHECK="1")
                with contextlib.chdir(caller):
                    rebased = setup_index._installer_env(original)
                self.assertEqual(pip_cache_dir(rebased, base), pip_cache_dir(original, caller))

    def test_home_relative_values_follow_each_consumer(self):
        home_relative = {
            # pip expands "~" for its path options: keep pip's expansion.
            "PIP_CACHE_DIR": os.path.expanduser("~/pip-cache"),
            "PIP_CERT": os.path.expanduser("~/ca.pem"),
            "PIP_CLIENT_CERT": os.path.expanduser("~/client.pem"),
            # uv, pip's PIP_CONFIG_FILE, OpenSSL and requests read "~" literally.
            "UV_CONFIG_FILE": str(self.dir / "~" / "uv.toml"),
            "UV_CACHE_DIR": str(self.dir / "~" / "uv-cache"),
            "PIP_CONFIG_FILE": str(self.dir / "~" / "pip.conf"),
            "SSL_CERT_FILE": str(self.dir / "~" / "bundle.pem"),
            "REQUESTS_CA_BUNDLE": str(self.dir / "~" / "bundle.pem"),
        }
        raw = {
            "PIP_CACHE_DIR": "~/pip-cache", "PIP_CERT": "~/ca.pem", "PIP_CLIENT_CERT": "~/client.pem",
            "UV_CONFIG_FILE": "~/uv.toml", "UV_CACHE_DIR": "~/uv-cache", "PIP_CONFIG_FILE": "~/pip.conf",
            "SSL_CERT_FILE": "~/bundle.pem", "REQUESTS_CA_BUNDLE": "~/bundle.pem",
        }
        self.assertEqual(set(raw), set(setup_index._INSTALLER_PATH_ENV_VARS))
        with contextlib.chdir(self.dir):
            env = setup_index._installer_env(dict(raw))
        for name, expected in home_relative.items():
            self.assertEqual(env[name], expected, name)

    def test_every_installer_child_resolves_relative_path_settings_first(self):
        relative = {"UV_CONFIG_FILE": "uv.toml", "PIP_CONFIG_FILE": "pip.conf", "PIP_CERT": "ca.pem"}
        with contextlib.chdir(self.dir), patch.dict(os.environ, relative):
            calls = []
            with patch.object(setup_index, "_run_install_step", side_effect=lambda cmd, **kw: calls.append(kw) or MagicMock(returncode=0)):
                setup_index.install_requirement_specs([PSUTIL])
            # Wave 1zls6: dependency installs run only through uv, so the setup install is given one.
            with patch.object(setup_index, "_uv_bin", return_value=Path(self.dir / "fake-uv")), \
                    patch.object(setup_index, "_bootstrap_uv") as bootstrap, \
                    patch.object(setup_index, "_run_install_step", side_effect=lambda cmd, **kw: calls.append(kw) or MagicMock(returncode=0)), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                setup_index._install_deps(["fastembed"], Path(sys.executable))
            bootstrap.assert_not_called()
            with patch.object(setup_index, "_uv_bin", return_value=None), \
                    patch.object(setup_index, "_run_install_step", side_effect=lambda cmd, **kw: calls.append(kw) or MagicMock(returncode=1)), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                setup_index._bootstrap_uv(Path(sys.executable))
        self.assertEqual(len(calls), 3)
        for kwargs in calls:
            for name, value in relative.items():
                self.assertEqual(kwargs["env"][name], str(self.dir / value), name)
        # Absolute values, empty values and the null device leave an inherited environment
        # inherited; "nul" (the Windows null device, relative-looking) exercises the guard everywhere.
        with patch.object(os, "devnull", "nul"), \
                patch.dict(os.environ, {"UV_CONFIG_FILE": str(self.dir / "abs.toml"), "PIP_CONFIG_FILE": "nul", "PIP_CERT": ""}):
            self.assertIsNone(setup_index._installer_env(None))
            explicit = {"PIP_CONFIG_FILE": "nul", "UV_CONFIG_FILE": "rel.toml"}
            resolved = setup_index._installer_env(explicit)
        self.assertEqual(resolved["PIP_CONFIG_FILE"], "nul")
        self.assertEqual(explicit["UV_CONFIG_FILE"], "rel.toml", "the input mapping is never mutated")

    def test_the_setup_install_keeps_a_repository_uv_toml_out_with_real_uv(self):
        # Wave 1zicq: the command and working directory `_install_deps` builds, run by a real uv.
        import shutil

        uv = shutil.which("uv") or str(Path(sys.executable).parent / ("uv.exe" if os.name == "nt" else "uv"))
        if not Path(uv).is_file():
            self.skipTest("uv is not available")
        repo = self.dir / "checkout"
        base = repo / "venv-inside"
        base.mkdir(parents=True)
        (repo / "uv.toml").write_text('[pip]\nindex-url = "http://127.0.0.1:9/repo-index"\n', encoding="utf-8")
        captured = []
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(base), "UV_CONFIG_FILE": "", "UV_NO_CONFIG": ""}), \
                patch.object(setup_index, "_operator_uv_config_files", return_value=[]), \
                patch.object(setup_index, "_uv_bin", return_value=Path(uv)), \
                patch.object(setup_index, "_run_install_step", side_effect=lambda cmd, **kw: captured.append((cmd, kw)) or MagicMock(returncode=0)), \
                contextlib.redirect_stdout(io.StringIO()):
            setup_index._install_deps(["zzz-nonexistent-1zicq"], Path(sys.executable))
        cmd, kwargs = captured[0]
        env = {key: value for key, value in os.environ.items() if key not in ("UV_CONFIG_FILE", "UV_NO_CONFIG")}
        env["UV_OFFLINE"] = "1"

        def found(argv):
            done = subprocess.run(
                [argv[0], "-v", *argv[1:], "--dry-run"], cwd=kwargs["cwd"],
                capture_output=True, text=True, timeout=60, env=env,
            )
            return str(repo / "uv.toml") in done.stdout + done.stderr

        control = [part for part in cmd if part not in ("--no-config",)]
        self.assertEqual(kwargs["cwd"], str(base))
        self.assertTrue(found(control), "control: without isolation uv discovers the repository uv.toml")
        self.assertFalse(found(cmd), "the setup install's command must keep it out")


class StdoutAndConcurrencyTests(_Tmp):
    HARNESS = textwrap.dedent(
        """
        import json, sys
        sys.path.insert(0, sys.argv[1])
        import setup_index
        setup_index._STARTUP_UV_COMMAND = [sys.executable, sys.argv[2]]
        marker = sys.argv[3]
        def recheck():
            try:
                with open(marker, encoding="utf-8") as handle:
                    return [] if handle.read().strip() else ["psutil>=6.1,<8"]
            except OSError:
                return ["psutil>=6.1,<8"]
        outcome = setup_index.install_requirement_specs(["psutil>=6.1,<8"], recheck=recheck)
        sys.stderr.write("OUTCOME " + json.dumps(outcome) + "\\n")
        """
    )

    def _harness(self):
        path = self.dir / "harness.py"
        path.write_text(self.HARNESS, encoding="utf-8")
        return [sys.executable, "-B", str(path), str(SCRIPTS), str(self.fake_uv), str(self.marker)]

    def _parse_outcome(self, stderr: str) -> dict:
        line = [row for row in stderr.splitlines() if row.startswith("OUTCOME ")][-1]
        return json.loads(line[len("OUTCOME "):])

    def test_installer_output_never_reaches_stdout(self):
        done = subprocess.run(self._harness(), capture_output=True, text=True, timeout=120, env=dict(os.environ))
        self.assertEqual(done.stdout, "", done.stderr)
        self.assertIn("UV-STDOUT-MARK", done.stderr)
        self.assertEqual(self._parse_outcome(done.stderr)["status"], "installed")

    def test_two_concurrent_installers_install_once(self):
        env = dict(os.environ, FAKE_UV_SLEEP="1.5")
        procs = [
            subprocess.Popen(self._harness(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            for _ in range(2)
        ]
        results = [proc.communicate(timeout=120) for proc in procs]
        statuses = sorted(self._parse_outcome(err)["status"] for _out, err in results)
        self.assertEqual(statuses, ["already_installed", "installed"], results)
        self.assertEqual(len(self.marker.read_text(encoding="utf-8").strip().splitlines()), 1)


class ProcessInfoGateTests(unittest.TestCase):
    """A version replacement is loaded only when nothing imported the old one."""

    HARNESS = textwrap.dedent(
        """
        import json, sys
        pkgs, scripts, gated = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
        sys.path.insert(0, pkgs)
        sys.path.insert(1, scripts)
        import process_info
        init = pkgs + "/psutil/__init__.py"
        if gated:
            process_info.set_startup_install_pending("MCP startup is installing psutil")
        during = process_info.available()
        imported_during = "psutil" in sys.modules
        with open(init, "w", encoding="utf-8") as handle:
            handle.write('__version__ = "7.0.0"\\n')
        process_info.set_startup_install_pending(None)
        after = process_info.available()
        print(json.dumps({"during": during, "imported_during": imported_during, "after": after}))
        """
    )

    def _run(self, gated: bool) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            pkgs = Path(tmp) / "pkgs"
            (pkgs / "psutil").mkdir(parents=True)
            (pkgs / "psutil" / "__init__.py").write_text('__version__ = "6.0.0"\n', encoding="utf-8")
            harness = Path(tmp) / "gate.py"
            harness.write_text(self.HARNESS, encoding="utf-8")
            done = subprocess.run(
                [sys.executable, "-B", "-S", str(harness), str(pkgs), str(SCRIPTS), "1" if gated else "0"],
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_the_gate_defers_the_import_so_the_new_version_loads(self):
        result = self._run(gated=True)
        self.assertEqual(result["during"][0], False)
        self.assertIn("installing", result["during"][1])
        self.assertFalse(result["imported_during"])
        self.assertEqual(result["after"], [True, "7.0.0"])

    def test_without_the_gate_the_old_module_stays_loaded(self):
        result = self._run(gated=False)
        self.assertTrue(result["imported_during"])
        self.assertEqual(result["after"][0], False)


class ServerStartTests(unittest.TestCase):
    """The deferrable set really is not imported when the server starts."""

    def test_no_deferrable_package_is_imported_at_server_start(self):
        probe = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(SCRIPTS)!r})
            import server  # noqa: F401 - runner and server_impl at module level
            import setup_requirements
            names = [setup_requirements.REQUIRED_IMPORTS[spec] for spec in setup_requirements.STARTUP_DEFERRABLE_IMPORTS]
            print(",".join(name for name in names if name in sys.modules))
            """
        )
        done = subprocess.run([sys.executable, "-B", "-c", probe], capture_output=True, text=True, timeout=180)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "")
        self.assertEqual(sorted(setup_requirements.STARTUP_DEFERRABLE_IMPORTS), [PSUTIL])


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_server()
        import server

        cls.server = server

    def setUp(self):
        self.addCleanup(process_info.set_startup_install_pending, None)
        self.addCleanup(setattr, self.server, "_BACKGROUND_INSTALL_SPECS", [])
        self.addCleanup(setattr, self.server, "_STARTUP_INSTALL", None)

    def test_dry_run_and_excluded_reasons_never_install(self):
        with patch.object(setup_index, "install_requirement_specs") as install:
            blocked = _assessment("dependencies_missing", missing=["numpy"])
            self.assertIs(self.server._startup_install_gate(Path("/r"), blocked, dry_run=True), blocked)
            stale = _assessment("loaded_code_stale", "dependencies_missing", missing=["numpy"])
            self.assertIs(self.server._startup_install_gate(Path("/r"), stale, dry_run=False), stale)
        install.assert_not_called()

    def test_deferrable_only_plans_a_background_install_and_gates_process_info(self):
        blocked = _assessment("setup_inputs_changed", "dependencies_missing", missing=[PSUTIL])
        with patch.object(setup_index, "install_requirement_specs") as install:
            result = self.server._startup_install_gate(Path("/r"), blocked, dry_run=False)
        install.assert_not_called()
        self.assertEqual(self.server._BACKGROUND_INSTALL_SPECS, [PSUTIL])
        self.assertIn("startup_install_running", [item["code"] for item in result["reasons"]])
        self.assertEqual(self.server._startup_install_snapshot()["mode"], "background")
        self.assertIn("installing", process_info._STARTUP_INSTALL_PENDING)

    def test_foreground_failure_reassesses_once_and_stays_blocked(self):
        blocked = _assessment("dependencies_missing", missing=["numpy"])
        failed = {"status": "failed", "packages": ["numpy"], "message": "uv install failed; run `wf setup`"}
        stderr = io.StringIO()
        with patch.object(setup_index, "install_requirement_specs", return_value=failed) as install, \
                patch.object(self.server.setup_readiness, "assess_setup", return_value=blocked) as assess, \
                contextlib.redirect_stderr(stderr):
            result = self.server._startup_install_gate(Path("/r"), blocked, dry_run=False)
        install.assert_called_once()
        self.assertEqual(assess.call_count, 1)
        self.assertTrue(result["startup_blocked"])
        self.assertIn("If startup is interrupted, run `wf setup`", stderr.getvalue())
        self.assertIn("run `wf setup`", stderr.getvalue())
        self.assertEqual(self.server._startup_install_snapshot()["status"], "failed")

    def test_a_reported_install_that_still_reassesses_blocked_is_final(self):
        blocked = _assessment("dependencies_missing", missing=["numpy"])
        installed = {"status": "installed", "packages": ["numpy"], "message": ""}
        with patch.object(setup_index, "install_requirement_specs", return_value=installed) as install, \
                patch.object(self.server.setup_readiness, "assess_setup", return_value=blocked) as assess, \
                contextlib.redirect_stderr(io.StringIO()):
            result = self.server._startup_install_gate(Path("/r"), blocked, dry_run=False)
        install.assert_called_once()
        self.assertEqual(assess.call_count, 1)
        self.assertTrue(result["startup_blocked"])
        self.assertEqual(self.server._BACKGROUND_INSTALL_SPECS, [])  # so the entry exits instead of starting


class McpStartupTests(unittest.TestCase):
    """End to end: the real runner installs, starts, and serves MCP requests."""

    # Runs server.py's real executable entry (runpy, run_name="__main__") after
    # patching only the assessor and the installer's view of the tool venv.
    HARNESS = textwrap.dedent(
        """
        import json, os, runpy, sys
        from pathlib import Path
        scripts, root, spec, tmp = sys.argv[1:5]
        sys.argv = [str(Path(scripts) / "server.py"), "--root", root]
        sys.path.insert(0, scripts)
        import setup_index, setup_readiness, venv_bootstrap
        venv = Path(tmp) / "venv"
        python = venv.joinpath(*(("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")))
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_text("", encoding="utf-8")
        class _InstallTarget:
            # Only the installer sees the fake venv; the server runs on the real one.
            def tool_venv_base(self):
                return venv
            def tool_venv_python(self):
                return python
            def __getattr__(self, name):
                return getattr(venv_bootstrap, name)
        setup_index.venv_bootstrap = _InstallTarget()
        setup_index._STARTUP_UV_COMMAND = [sys.executable, str(Path(tmp) / "fake_uv.py")]
        ready_marker = Path(os.environ["READY_MARKER"])
        calls = Path(tmp) / "assess-calls.jsonl"
        blocked = {
            "schema_version": 1, "status": "action_required", "startup_blocked": True,
            "reasons": [
                {"code": "setup_inputs_changed", "message": "changed"},
                {"code": "dependencies_missing", "message": "missing", "missing": [spec]},
            ],
            "actions": [{"kind": "setup", "argv": ["wf", "setup", "--root", root]}],
            "advisories": [], "limitations": [], "timings_ms": {},
        }
        ready = dict(blocked, status="ready", startup_blocked=False, reasons=[], actions=[])
        def assess(*args, **kwargs):
            with calls.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"server_impl_loaded": "server_impl" in sys.modules}) + "\\n")
            return dict(ready if ready_marker.exists() else blocked)
        setup_readiness.assess_setup = assess
        setup_readiness.adopt_setup_stamp = lambda *a, **k: None
        runpy.run_path(str(Path(scripts) / "server.py"), run_name="__main__")
        """
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name).resolve()
        self.root = _make_repo(self.dir / "repo")
        (self.dir / "fake_uv.py").write_text(FAKE_UV, encoding="utf-8")
        (self.dir / "harness.py").write_text(self.HARNESS, encoding="utf-8")
        self.marker = self.dir / "installed.txt"

    def _start(self, spec: str, sleep: str, *, exit_code: str = "0", ready_marker: "Path | None" = None):
        env = dict(
            os.environ, FAKE_UV_MARKER=str(self.marker), FAKE_UV_SLEEP=sleep, FAKE_UV_EXIT=exit_code,
            READY_MARKER=str(ready_marker or self.marker),
        )
        proc = subprocess.Popen(
            [sys.executable, "-B", str(self.dir / "harness.py"), str(SCRIPTS), str(self.root), spec, str(self.dir)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env,
        )
        self.addCleanup(self._stop, proc)
        lines: "queue.Queue[str]" = queue.Queue()
        threading.Thread(target=lambda: [lines.put(line) for line in proc.stdout], daemon=True).start()
        self.stdout_lines: list[str] = []
        return proc, lines

    def _stop(self, proc):
        if proc.poll() is None:
            try:
                proc.stdin.close()
            except OSError:
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    def _request(self, proc, lines, message_id, method, params=None):
        payload = {"jsonrpc": "2.0", "id": message_id, "method": method, "params": params or {}}
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                if proc.poll() is not None:
                    self.fail("server exited: " + proc.stderr.read())
                continue
            self.stdout_lines.append(line)
            message = json.loads(line)  # every stdout line is protocol JSON
            if message.get("id") == message_id:
                return message
        self.fail(f"no response to {method}")

    def _initialize(self, proc, lines):
        reply = self._request(proc, lines, 1, "initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"},
        })
        self.assertIn("serverInfo", reply["result"])
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

    def _server_info(self, proc, lines, message_id) -> dict:
        reply = self._request(proc, lines, message_id, "tools/call", {"name": "wf_server_info", "arguments": {}})
        result = reply["result"]
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured.get("result", structured)
        return json.loads(result["content"][0]["text"])

    def test_foreground_install_then_serves_requests_with_a_clean_stdout(self):
        proc, lines = self._start("numpy", "0")
        self._initialize(proc, lines)
        info = self._server_info(proc, lines, 2)
        self.assertEqual(info["data"]["startup_install"]["mode"], "foreground")
        self.assertEqual(info["data"]["startup_install"]["status"], "installed")
        self.assertTrue(self.marker.exists())
        self.assertNotIn("UV-STDOUT-MARK", "".join(self.stdout_lines))
        # The entry assessed, installed, then reassessed, all before server_impl was imported.
        calls = [json.loads(line) for line in (self.dir / "assess-calls.jsonl").read_text().splitlines()]
        self.assertGreaterEqual(len(calls), 3)
        self.assertEqual([call["server_impl_loaded"] for call in calls[:3]], [False, False, False])

    def test_background_install_serves_first_and_reports_progress(self):
        proc, lines = self._start(PSUTIL, "4")
        self._initialize(proc, lines)
        during = self._server_info(proc, lines, 2)
        self.assertIn(during["data"]["startup_install"]["status"], ("pending", "running"))
        self.assertEqual(during["data"]["process_info"]["available"], False)
        self.assertIn("installing", json.dumps(during["data"]["process_info"]))
        deadline = time.monotonic() + 60
        after = during
        message_id = 3
        while time.monotonic() < deadline:
            after = self._server_info(proc, lines, message_id)
            message_id += 1
            if after["data"]["startup_install"]["status"] == "installed":
                break
            time.sleep(0.5)
        self.assertEqual(after["data"]["startup_install"]["status"], "installed")
        self.assertEqual(after["data"]["process_info"]["available"], True)
        self.assertNotIn("UV-STDOUT-MARK", "".join(self.stdout_lines))

    def _notices(self, proc, lines, message_id) -> list[str]:
        reply = self._request(proc, lines, message_id, "tools/call", {"name": "wf_list_waves", "arguments": {}})
        result = reply["result"]
        structured = result.get("structuredContent")
        body = structured.get("result", structured) if isinstance(structured, dict) else json.loads(result["content"][0]["text"])
        return [item["message"] for item in body.get("diagnostics", []) if item.get("code") == "setup_not_ready"]

    def test_background_install_failure_reaches_the_agent_with_wf_setup(self):
        never_ready = self.dir / "never-ready.txt"
        proc, lines = self._start(PSUTIL, "1", exit_code="1", ready_marker=never_ready)
        self._initialize(proc, lines)
        first = self._notices(proc, lines, 2)
        self.assertTrue(first and "startup_install_running" in first[0], first)
        deadline = time.monotonic() + 60
        message_id = 3
        seen: list[str] = []

        def poll(message_id):
            info = self._server_info(proc, lines, message_id)
            seen.extend(item["message"] for item in info.get("diagnostics", []) if item.get("code") == "setup_not_ready")
            return info

        info = poll(message_id)
        while info["data"]["startup_install"]["status"] in ("pending", "running") and time.monotonic() < deadline:
            time.sleep(0.5)
            message_id += 1
            info = poll(message_id)
        self.assertEqual(info["data"]["startup_install"]["status"], "failed")
        self.assertIn("wf setup", info["data"]["startup_install"]["message"])
        # The notice is shown once per distinct result, on whichever call comes first
        # after the result is published; collect it from every response.
        notices = seen + self._notices(proc, lines, message_id + 1)
        failed = [text for text in notices if "startup_install_failed" in text]
        self.assertTrue(failed, notices)
        self.assertIn("wf setup", failed[0])
        self.assertFalse(never_ready.exists())


class StaleServerNoticeTests(unittest.TestCase):
    def test_the_stale_notice_says_the_restart_attempts_the_install(self):
        # A requirement added on disk is invisible to the loaded assessor: it
        # judges dependencies against the requirement dict it imported.
        on_disk = dict(setup_requirements.REQUIRED_IMPORTS, **{"zzz-new-package": "zzz_new_package"})
        with patch.object(setup_requirements, "REQUIRED_IMPORTS", on_disk):
            result = setup_readiness.assess_setup(SCRIPTS.parents[2], loaded_identity={"launch": "older"})
        codes = [item["code"] for item in result["reasons"]]
        self.assertIn("loaded_code_stale", codes)
        stale = [item for item in result["reasons"] if item["code"] == "loaded_code_stale"][0]
        self.assertIn("attempts to install any newly required dependencies", stale["message"])
        self.assertIn("wf setup", stale["message"])
        self.assertEqual(result["actions"][0]["kind"], "restart")
        self.assertNotIn("zzz-new-package", json.dumps(result))


class UpgradeDependencyStepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import upgrade_wavefoundry

        cls.up = upgrade_wavefoundry

    def test_metadata_present_skips_the_installer(self):
        with patch.object(setup_readiness, "_dependencies", return_value=[]), \
                patch.object(setup_index, "ensure_deps") as ensure, \
                patch("upgrade_lib.update_upgrade_lock") as update:
            self.assertTrue(self.up._provision_upgrade_dependencies(Path("/r")))
        ensure.assert_not_called()
        update.assert_called_once_with(Path("/r"), dependency_provisioning_failed=False)

    def test_failure_is_a_dependency_failure_naming_wf_setup(self):
        err = io.StringIO()
        with patch.object(setup_readiness, "_dependencies", return_value=[PSUTIL]), \
                patch.object(setup_index, "ensure_deps", side_effect=SystemExit(2)), \
                patch("upgrade_lib.update_upgrade_lock") as update, \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(self.up._provision_upgrade_dependencies(Path("/r")))
        update.assert_called_once_with(Path("/r"), dependency_provisioning_failed=True)
        combined = err.getvalue()
        self.assertIn("Dependency provisioning FAILED", combined)
        self.assertIn("wf setup", combined)

    def test_index_update_skips_its_children_when_provisioning_fails(self):
        with patch.object(self.up, "_enforce_index_guard_before_children"), \
                patch("sqlite_storage_migration.read_receipt", return_value=None), \
                patch.object(self.up, "_provision_upgrade_dependencies", return_value=False), \
                patch.object(self.up.subprocess_util, "isolated_run", side_effect=AssertionError("child ran")):
            self.assertFalse(self.up.phase_index_update(Path("/r")))
            self.assertFalse(self.up.phase_index_rebuild(Path("/r")))

    def test_a_pending_storage_migration_raises_instead_of_skipping(self):
        receipt = {"state": "converting", "strategy": "transfer"}
        with patch.object(self.up, "_enforce_index_guard_before_children"), \
                patch("sqlite_storage_migration.read_receipt", return_value=receipt), \
                patch.object(self.up, "_provision_upgrade_dependencies", return_value=False), \
                patch.object(self.up.subprocess_util, "isolated_run", side_effect=AssertionError("child ran")):
            with self.assertRaises(RuntimeError) as raised:
                self.up.phase_index_update(Path("/r"))
        self.assertIn("storage migration retains its receipt", str(raised.exception))

    # Wave 1zep5: provisioning inside the storage-migration branch.

    class _Reached(Exception):
        pass

    def _migration_branch(self, stack, *, deps_error=None, reader_error=None, receipt=None):
        import sqlite_storage_migration as migration

        stack.enter_context(patch.object(self.up, "_enforce_index_guard_before_children"))
        stack.enter_context(patch.object(migration, "read_receipt", return_value=receipt))
        stack.enter_context(patch.object(self.up, "_provision_upgrade_dependencies", return_value=True))
        stack.enter_context(patch.object(
            migration, "detect", return_value={"migration_required": True, "legacy": ["code.lance"]}))
        mocks = {
            "deps": stack.enter_context(patch.object(setup_index, "ensure_deps", side_effect=deps_error)),
            "reader": stack.enter_context(patch.object(setup_index, "ensure_migration_deps", side_effect=reader_error)),
            "convert": stack.enter_context(patch.object(
                migration, "migrate_legacy", side_effect=self._Reached("migrate_legacy"))),
            "publish": stack.enter_context(patch.object(migration, "begin_upgrade_publication")),
            "update": stack.enter_context(patch("upgrade_lib.update_upgrade_lock")),
            "err": io.StringIO(),
        }
        stack.enter_context(contextlib.redirect_stderr(mocks["err"]))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        return mocks

    def _assert_classified_failure(self, mocks, raised):
        self.assertIn("storage migration retains its receipt", str(raised.exception))
        mocks["update"].assert_called_with(Path("/r"), dependency_provisioning_failed=True)
        self.assertIn("Dependency provisioning FAILED", mocks["err"].getvalue())
        self.assertIn("wf setup", mocks["err"].getvalue())
        mocks["convert"].assert_not_called()
        mocks["publish"].assert_not_called()

    def test_a_failing_migration_reader_is_a_dependency_failure_without_a_receipt(self):
        # migration_required can be set with no receipt; the branch still raises.
        with contextlib.ExitStack() as stack:
            mocks = self._migration_branch(stack, reader_error=SystemExit(2), receipt=None)
            with self.assertRaises(RuntimeError) as raised:
                self.up.phase_index_update(Path("/r"))
        self._assert_classified_failure(mocks, raised)

    def test_a_failing_ensure_deps_in_the_migration_branch_is_classified_the_same(self):
        receipt = {"state": "converting", "strategy": "transfer"}
        with contextlib.ExitStack() as stack:
            mocks = self._migration_branch(stack, deps_error=OSError(13, "denied"), receipt=receipt)
            with self.assertRaises(RuntimeError) as raised:
                self.up.phase_index_update(Path("/r"))
        self._assert_classified_failure(mocks, raised)
        mocks["reader"].assert_not_called()

    def test_successful_migration_provisioning_proceeds_to_the_migration(self):
        with contextlib.ExitStack() as stack:
            mocks = self._migration_branch(stack)
            with self.assertRaises(self._Reached):
                self.up.phase_index_update(Path("/r"))
        mocks["deps"].assert_called_once_with(Path("/r"))
        mocks["reader"].assert_called_once_with(Path("/r"))
        mocks["update"].assert_called_with(Path("/r"), dependency_provisioning_failed=False)

    def test_an_unrelated_error_is_not_relabelled_a_dependency_failure(self):
        with contextlib.ExitStack() as stack:
            mocks = self._migration_branch(stack, reader_error=ValueError("bug"))
            with self.assertRaises(ValueError):
                self.up.phase_index_update(Path("/r"))
        self.assertNotIn("Dependency provisioning FAILED", mocks["err"].getvalue())
        mocks["convert"].assert_not_called()

    def test_the_delegated_summary_reads_the_lock_flag(self):
        lock = {"from_version": "1", "to_version": "2", "dependency_provisioning_failed": True}
        out = io.StringIO()
        with patch("upgrade_lib.read_upgrade_lock", return_value=lock), \
                patch.object(self.up, "_run_reconciliation_scan", return_value=([], [], [])), \
                patch.object(self.up, "_run_reconciliation_disposition_diagnostics", return_value=[]), \
                patch.object(self.up, "_run_renderer_warning_scan", return_value=[]), \
                contextlib.redirect_stdout(out):
            self.assertEqual(self.up._emit_delegated_summary(Path("/r")), 0)
        line = [row for row in out.getvalue().splitlines() if row.startswith(self.up.WAVE_UPGRADE_SUMMARY_SENTINEL)][0]
        summary = json.loads(line[len(self.up.WAVE_UPGRADE_SUMMARY_SENTINEL):])
        self.assertIs(summary["dependency_provisioning_failed"], True)
        self.assertEqual(summary["setup_status"], "not_assessed")

    def test_publication_outcome_is_not_a_failure_when_no_child_ran(self):
        with patch("upgrade_lib.read_upgrade_lock", return_value={"dependency_provisioning_failed": True}), \
                patch("upgrade_lib.update_upgrade_lock") as update:
            self.up._record_index_publication_outcome(Path("/r"), False)
        update.assert_called_once_with(Path("/r"), index_rebuilt_at=None, index_publication_failed=False)

    def _summary(self, **kwargs) -> dict:
        base = dict(from_version="1", to_version="2", zip_path=None, pruned_count=0,
                    ran_index_rebuild=False, failed_phase=None, reconciliation=[])
        base.update(kwargs)
        return self.up._build_upgrade_summary(**base)

    def test_summary_carries_flat_setup_fields_and_the_dependency_outcome(self):
        default = self._summary()
        self.assertEqual(
            (default["setup_status"], default["setup_reasons"], default["setup_command"]),
            ("not_assessed", [], None),
        )
        failed = self._summary(dependency_provisioning_failed=True, index_update_failed=True)
        self.assertTrue(failed["dependency_provisioning_failed"])
        self.assertTrue(failed["index_update"].startswith("not run: dependency provisioning failed"))
        needs = self._summary(setup_assessment=_assessment("dependencies_missing", missing=[PSUTIL]))
        self.assertEqual(needs["setup_status"], "action_required")
        self.assertEqual(needs["setup_reasons"], ["dependencies_missing"])
        self.assertEqual(needs["setup_command"], "wf setup --root /r")
        for key in ("setup_status", "setup_command", "dependency_provisioning_failed", "setup_reasons"):
            self.assertNotIsInstance(needs[key], dict)

    def test_setup_command_keeps_a_spaced_root_as_one_argument(self):
        argv = ["wf", "setup", "--root", "/Users/someone/My Repo"]
        result = dict(_assessment("dependencies_missing", missing=[PSUTIL]), actions=[{"kind": "setup", "argv": argv}])
        command = self._summary(setup_assessment=result)["setup_command"]
        self.assertEqual(command, setup_readiness.format_command(argv))
        if os.name != "nt":
            import shlex

            self.assertEqual(shlex.split(command), argv)


class UpgradeResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))

    def _cleanup_with(self, summary: dict) -> dict:
        import server as runner

        proc = MagicMock(returncode=0, stdout="Upgrade complete\nWAVE_UPGRADE_SUMMARY_JSON:" + json.dumps(summary) + "\n",
                         stderr="")
        with patch("subprocess.run", return_value=proc), \
                patch.object(runner, "_mcp", object()), \
                patch.object(runner, "perform_mcp_reload", return_value={"status": "ok", "data": {"ok": True}}):
            return self.srv.wf_upgrade_response(self.root, phase="cleanup", mode="apply")

    def test_setup_not_ready_leads_the_next_step_and_survives_bounding(self):
        result = self._cleanup_with({
            "setup_status": "action_required", "setup_reasons": ["dependencies_missing"],
            "setup_command": "wf setup --root /r", "dependency_provisioning_failed": False,
            "summary_schema_version": 1,
        })
        self.assertTrue(result["next_step"].startswith("Setup needs attention"))
        self.assertIn("`wf setup --root /r`", result["next_step"])
        self.assertLess(result["next_step"].index("wf setup"), result["next_step"].index("wf_reload_mcp"))
        self.assertIn("ask before running any command", result["next_step"])
        self.assertEqual(result["next_tools"][0], "index_health")
        summary = result["data"]["summary"]
        self.assertEqual(summary["setup_status"], "action_required")
        self.assertEqual(summary["setup_command"], "wf setup --root /r")

    def test_setup_fields_survive_an_oversized_summary(self):
        import wf_server.upgrade_handlers as upgrade_handlers

        # Thousands of tiny unregistered fields fill the aggregate budget to within a few
        # characters, so any non-terminal setup field would be dropped behind them.
        summary = {f"k{i:04d}": "x" for i in range(4000)}
        summary.update({
            "setup_status": "action_required", "setup_reasons": ["dependencies_missing"],
            "setup_command": "wf setup --root /r", "dependency_provisioning_failed": True,
        })
        bounded = upgrade_handlers._bounded_upgrade_summary(summary)
        self.assertEqual(bounded["setup_status"], "action_required")
        self.assertEqual(bounded["setup_command"], "wf setup --root /r")
        self.assertIs(bounded["dependency_provisioning_failed"], True)
        kept = [f"k{i:04d}" for i in range(4000) if bounded.get(f"k{i:04d}") == "x"]
        self.assertLess(len(kept), 4000, "the fixture must exceed the aggregate cap")

    def test_ready_setup_keeps_the_existing_next_step(self):
        result = self._cleanup_with({"setup_status": "ready", "setup_reasons": [], "setup_command": None})
        self.assertTrue(result["next_step"].startswith("Upgrade complete."))

    def test_dependency_failure_diagnostic(self):
        result = self._cleanup_with({"dependency_provisioning_failed": True, "setup_status": "not_assessed"})
        codes = [item["code"] for item in result.get("diagnostics", [])]
        self.assertIn("dependency_provisioning_failed", codes)
        self.assertNotIn("index_publication_failed", codes)


if __name__ == "__main__":
    unittest.main()
