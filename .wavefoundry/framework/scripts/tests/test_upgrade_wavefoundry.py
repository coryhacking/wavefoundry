"""Tests for upgrade_wavefoundry.py — _compute_seed_diffs (12r1b) and extension hooks (12r1y)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
UPGRADE_PATH = SCRIPTS_ROOT / "upgrade_wavefoundry.py"


def load_upgrade_module():
    spec = importlib.util.spec_from_file_location("upgrade_wavefoundry", UPGRADE_PATH)
    mod = importlib.util.module_from_spec(spec)
    # upgrade_wavefoundry imports upgrade_lib and check_version at call time;
    # those imports are deferred inside functions so loading the module is safe.
    sys.modules["upgrade_wavefoundry"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_zip(entries: dict[str, str], prefix: str = ".wavefoundry/framework/seeds/") -> bytes:
    """Build an in-memory zip with seeds at *prefix*."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(prefix + name, content)
    return buf.getvalue()


class ComputeSeedDiffsTests(unittest.TestCase):
    """Unit tests for _compute_seed_diffs (AC-1 through AC-6)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.seeds_dir = self.root / ".wavefoundry" / "framework" / "seeds"
        self.seeds_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_disk_seed(self, name: str, content: str) -> None:
        (self.seeds_dir / name).write_text(content, encoding="utf-8")

    def _make_zip_file(self, entries: dict[str, str], prefix: str = ".wavefoundry/framework/seeds/") -> Path:
        zip_path = self.root / "wavefoundry-test.zip"
        zip_path.write_bytes(_make_zip(entries, prefix=prefix))
        return zip_path

    # ── AC-3: unchanged seeds are omitted ─────────────────────────────────────

    def test_unchanged_seed_not_in_results(self):
        content = "# Seed\n\nNo change here.\n"
        self._write_disk_seed("seed-001.md", content)
        zip_path = self._make_zip_file({"seed-001.md": content})

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(results, [])

    # ── AC-2: modified seed appears with unified diff ─────────────────────────

    def test_modified_seed_returns_diff(self):
        self._write_disk_seed("seed-010.md", "# Old\n\nOriginal content.\n")
        zip_path = self._make_zip_file({"seed-010.md": "# New\n\nUpdated content.\n"})

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(len(results), 1)
        filename, status, diff = results[0]
        self.assertEqual(filename, "seed-010.md")
        self.assertEqual(status, "modified")
        self.assertIn("--- a/seed-010.md", diff)
        self.assertIn("+++ b/seed-010.md", diff)
        self.assertIn("-Original content.", diff)
        self.assertIn("+Updated content.", diff)

    # ── AC-4: added seed is labeled correctly ─────────────────────────────────

    def test_added_seed_status_is_added(self):
        # Not present on disk — only in zip
        zip_path = self._make_zip_file({"seed-new.md": "# Brand new seed\n"})

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(len(results), 1)
        filename, status, diff = results[0]
        self.assertEqual(filename, "seed-new.md")
        self.assertEqual(status, "added")
        self.assertIn("/dev/null", diff)
        self.assertIn("+++ b/seed-new.md", diff)

    # ── AC-4: removed seed is labeled correctly ───────────────────────────────

    def test_removed_seed_status_is_removed(self):
        # Present on disk — absent in zip
        self._write_disk_seed("seed-old.md", "# Old seed to be removed\n")
        zip_path = self._make_zip_file({})  # empty zip

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(len(results), 1)
        filename, status, diff = results[0]
        self.assertEqual(filename, "seed-old.md")
        self.assertEqual(status, "removed")
        self.assertIn("--- a/seed-old.md", diff)
        self.assertIn("/dev/null", diff)

    # ── AC-6: bad zip does not crash ──────────────────────────────────────────

    def test_bad_zip_returns_empty_list(self):
        bad_zip = self.root / "bad.zip"
        bad_zip.write_bytes(b"not a zip file")

        results = self.mod._compute_seed_diffs(self.root, bad_zip)
        self.assertEqual(results, [])

    # ── Alt zip prefix (framework/seeds/) ────────────────────────────────────

    def test_alt_zip_prefix_is_recognised(self):
        self._write_disk_seed("seed-010.md", "# Old\n")
        zip_path = self._make_zip_file(
            {"seed-010.md": "# New\n"}, prefix="framework/seeds/"
        )

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "seed-010.md")
        self.assertEqual(results[0][1], "modified")

    # ── Multiple seeds — mixed statuses ──────────────────────────────────────

    def test_multiple_seeds_mixed_statuses(self):
        self._write_disk_seed("seed-001.md", "unchanged\n")
        self._write_disk_seed("seed-002.md", "old content\n")
        self._write_disk_seed("seed-003.md", "to be removed\n")
        zip_path = self._make_zip_file({
            "seed-001.md": "unchanged\n",       # no change
            "seed-002.md": "new content\n",     # modified
            "seed-004.md": "brand new\n",       # added
            # seed-003.md absent → removed
        })

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        statuses = {name: status for name, status, _ in results}
        self.assertNotIn("seed-001.md", statuses)
        self.assertEqual(statuses.get("seed-002.md"), "modified")
        self.assertEqual(statuses.get("seed-003.md"), "removed")
        self.assertEqual(statuses.get("seed-004.md"), "added")
        self.assertEqual(len(results), 3)


# ---------------------------------------------------------------------------
# Extension hook tests (12r1y)
# ---------------------------------------------------------------------------

def _make_zip_with_extension(source: str, prefix: str = ".wavefoundry/framework/scripts/") -> bytes:
    """Build an in-memory zip containing upgrade_extensions.py."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(prefix + "upgrade_extensions.py", source)
    return buf.getvalue()


class LoadExtensionModuleTests(unittest.TestCase):
    """Tests for _load_extension_module (AC-1)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _zip_with(self, source: str, prefix: str = ".wavefoundry/framework/scripts/") -> Path:
        p = self.root / "wf-test.zip"
        p.write_bytes(_make_zip_with_extension(source, prefix=prefix))
        return p

    def test_returns_none_when_no_zip(self):
        self.assertIsNone(self.mod._load_extension_module(None))

    def test_returns_none_when_zip_has_no_extension_module(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("some-other-file.txt", "hello")
        p = self.root / "empty.zip"
        p.write_bytes(buf.getvalue())
        self.assertIsNone(self.mod._load_extension_module(p))

    def test_loads_module_from_primary_prefix(self):
        zip_path = self._zip_with("MY_MARKER = 'loaded'\n")
        ext = self.mod._load_extension_module(zip_path)
        self.assertIsNotNone(ext)
        self.assertEqual(ext.MY_MARKER, "loaded")

    def test_loads_module_from_alt_prefix(self):
        zip_path = self._zip_with("MY_MARKER = 'alt'\n", prefix="framework/scripts/")
        ext = self.mod._load_extension_module(zip_path)
        self.assertIsNotNone(ext)
        self.assertEqual(ext.MY_MARKER, "alt")

    def test_returns_none_on_syntax_error(self):
        zip_path = self._zip_with("def broken(:\n    pass\n")
        result = self.mod._load_extension_module(zip_path)
        self.assertIsNone(result)

    def test_returns_none_on_bad_zip(self):
        p = self.root / "bad.zip"
        p.write_bytes(b"not a zip")
        self.assertIsNone(self.mod._load_extension_module(p))


class RunHookTests(unittest.TestCase):
    """Tests for _run_hook (AC-2 through AC-5)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ctx = self.mod.UpgradeContext(
            root=self.root,
            from_version="2026-05-10a",
            to_version="2026-05-19a",
            zip_path=None,
            yes=True,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _make_ext(self, source: str):
        import types as _types
        m = _types.ModuleType("upgrade_extensions")
        exec(compile(source, "<test>", "exec"), m.__dict__)
        return m

    def _make_convention_hook(self, name: str, exit_code: int = 0) -> Path:
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        script = hooks_dir / name
        script.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
        script.chmod(0o755)
        return script

    # AC-5: no-op when neither layer defines the hook
    def test_noop_when_no_hooks_defined(self):
        ext = self._make_ext("")  # empty module
        self.mod._run_hook("pre_surface_rendering", self.ctx, ext)  # must not raise

    def test_noop_when_ext_mod_is_none(self):
        self.mod._run_hook("pre_surface_rendering", self.ctx, None)

    # AC-2: extension module hook called
    def test_extension_module_hook_is_called(self):
        called = []
        ext = self._make_ext(
            "def pre_surface_rendering(ctx): called.append(ctx.from_version)"
        )
        ext.__dict__["called"] = called
        ext.pre_surface_rendering = lambda ctx: called.append(ctx.from_version)
        self.mod._run_hook("pre_surface_rendering", self.ctx, ext)
        self.assertEqual(called, ["2026-05-10a"])

    # AC-2: convention script hook called
    def test_convention_script_hook_is_called(self):
        sentinel = self.root / "hook-ran"
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        script = hooks_dir / "pre-pruning"
        script.write_text(
            f"#!/bin/sh\ntouch {sentinel}\n", encoding="utf-8"
        )
        script.chmod(0o755)
        self.mod._run_hook("pre_pruning", self.ctx, None)
        self.assertTrue(sentinel.exists())

    # AC-2: both layers called in order
    def test_both_layers_called_in_order(self):
        order = []
        sentinel = self.root / "convention-ran"
        # Extension module appends "ext"
        ext = self._make_ext("")
        ext.post_extract = lambda ctx: order.append("ext")
        # Convention script appends "conv" via a file
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        script = hooks_dir / "post-extract"
        script.write_text(
            f"#!/bin/sh\ntouch {sentinel}\n", encoding="utf-8"
        )
        script.chmod(0o755)
        self.mod._run_hook("post_extract", self.ctx, ext)
        self.assertEqual(order, ["ext"])       # ext ran
        self.assertTrue(sentinel.exists())      # convention ran

    # AC-3: extension module exception aborts (sys.exit(3))
    def test_extension_hook_exception_exits_3(self):
        ext = self._make_ext("")
        ext.pre_docs_gate = lambda ctx: (_ for _ in ()).throw(RuntimeError("boom"))
        with self.assertRaises(SystemExit) as cm:
            self.mod._run_hook("pre_docs_gate", self.ctx, ext)
        self.assertEqual(cm.exception.code, 3)

    # AC-4: convention script non-zero exit aborts (sys.exit(3))
    def test_convention_hook_nonzero_exits_3(self):
        self._make_convention_hook("post-docs-gate", exit_code=1)
        with self.assertRaises(SystemExit) as cm:
            self.mod._run_hook("post_docs_gate", self.ctx, None)
        self.assertEqual(cm.exception.code, 3)

    # Wave 1p9hm (L-4c): on Windows a bare extensionless convention hook cannot be spawned by path.
    # It must be SKIPPED (logged) — not spawned — so the OSError that previously escaped the
    # TimeoutExpired-only except never crashes the upgrade. Exercised on POSIX by patching os.name.
    def test_convention_hook_windows_skips_extensionless_without_spawn(self):
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "pre-pruning").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")  # extensionless
        with patch.object(self.mod.os, "name", "nt"):
            with patch.object(self.mod.subprocess_util, "isolated_run") as run:
                self.mod._run_hook("pre_pruning", self.ctx, None)  # must NOT raise
        run.assert_not_called()  # extensionless hook is skipped on Windows, never spawned by path

    # Wave 1p9hm (L-4c): on Windows a `<name>.py` convention hook is dispatched via the interpreter.
    def test_convention_hook_windows_dispatches_py_via_interpreter(self):
        from types import SimpleNamespace
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "pre-pruning.py").write_text("import sys; sys.exit(0)\n", encoding="utf-8")
        with patch.object(self.mod.os, "name", "nt"):
            with patch.object(self.mod, "_preferred_python", return_value="PY"):
                with patch.object(self.mod.subprocess_util, "isolated_run",
                                  return_value=SimpleNamespace(returncode=0)) as run:
                    self.mod._run_hook("pre_pruning", self.ctx, None)
        run.assert_called_once()
        cmd = run.call_args[0][0]
        self.assertEqual(cmd, ["PY", str(hooks_dir / "pre-pruning.py")])

    # Wave 1p9hm (L-4c): a `<name>.cmd` convention hook must be launched via `cmd /c` — NOT by bare
    # path — because subprocess.run(shell=False) + Windows CreateProcess cannot execute a batch file
    # by path (WinError 193). Guards against reintroducing that crash class.
    def test_convention_hook_windows_dispatches_cmd_via_cmd_shell(self):
        from types import SimpleNamespace
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "pre-pruning.cmd").write_text("@echo off\r\nexit /b 0\r\n", encoding="utf-8")
        with patch.object(self.mod.os, "name", "nt"):
            with patch.object(self.mod.subprocess_util, "isolated_run",
                              return_value=SimpleNamespace(returncode=0)) as run:
                self.mod._run_hook("pre_pruning", self.ctx, None)
        run.assert_called_once()
        cmd = run.call_args[0][0]
        self.assertEqual(cmd, ["cmd", "/c", str(hooks_dir / "pre-pruning.cmd")])


class UpgradeContextTests(unittest.TestCase):
    """Tests for UpgradeContext attribute population (AC-6)."""

    def setUp(self):
        self.mod = load_upgrade_module()

    def test_attributes_set_correctly(self):
        root = Path("/tmp/fake-root")
        ctx = self.mod.UpgradeContext(
            root=root,
            from_version="2026-05-10a",
            to_version="2026-05-19a",
            zip_path=Path("/tmp/wf.zip"),
            yes=True,
        )
        self.assertEqual(ctx.root, root)
        self.assertEqual(ctx.from_version, "2026-05-10a")
        self.assertEqual(ctx.to_version, "2026-05-19a")
        self.assertEqual(ctx.zip_path, Path("/tmp/wf.zip"))
        self.assertTrue(ctx.yes)

    def test_none_versions_allowed(self):
        ctx = self.mod.UpgradeContext(Path("."), None, None, None, False)
        self.assertIsNone(ctx.from_version)
        self.assertIsNone(ctx.to_version)
        self.assertIsNone(ctx.zip_path)
        self.assertFalse(ctx.yes)


# ---------------------------------------------------------------------------
# _print_change_plan — seed_diffs=None must show "n/a" (AC-5 regression guard)
# ---------------------------------------------------------------------------

class PrintChangePlanSeedDiffsTests(unittest.TestCase):
    """Regression tests for AC-5: no-zip path shows n/a, not none."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _capture_plan(self, seed_diffs):
        lines = []
        orig_log = self.mod._log
        self.mod._log = lambda msg: lines.append(msg)
        try:
            self.mod._print_change_plan(
                root=self.root,
                from_version="2026-05-10a",
                to_version="2026-05-19a",
                zip_path=None,
                dash_running=False,
                prompt_files=[],
                seed_diffs=seed_diffs,
            )
        finally:
            self.mod._log = orig_log
        return "\n".join(lines)

    def test_no_zip_shows_na(self):
        """seed_diffs=None (no zip) must emit 'n/a', not 'none'."""
        output = self._capture_plan(seed_diffs=None)
        self.assertIn("n/a", output)
        self.assertNotIn("Seeds changed:      none", output)

    def test_empty_diffs_shows_none(self):
        """seed_diffs=[] (zip present, nothing changed) must emit 'none'."""
        output = self._capture_plan(seed_diffs=[])
        self.assertIn("Seeds changed:      none", output)
        self.assertNotIn("n/a", output)


# ---------------------------------------------------------------------------
# _read_extension_source
# ---------------------------------------------------------------------------

class ReadExtensionSourceTests(unittest.TestCase):
    """Tests for _read_extension_source (dry-run helper)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _zip_with(self, source: str, prefix: str = ".wavefoundry/framework/scripts/") -> Path:
        import io as _io
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(prefix + "upgrade_extensions.py", source)
        p = self.root / "test.zip"
        p.write_bytes(buf.getvalue())
        return p

    def test_returns_none_when_no_zip(self):
        self.assertIsNone(self.mod._read_extension_source(None))

    def test_returns_source_from_primary_prefix(self):
        zip_path = self._zip_with("MY_MARKER = 'hello'\n")
        result = self.mod._read_extension_source(zip_path)
        self.assertIsNotNone(result)
        candidate, source = result
        self.assertIn("upgrade_extensions.py", candidate)
        self.assertIn("MY_MARKER", source)

    def test_returns_source_from_alt_prefix(self):
        zip_path = self._zip_with("MY_MARKER = 'alt'\n", prefix="framework/scripts/")
        result = self.mod._read_extension_source(zip_path)
        self.assertIsNotNone(result)
        _, source = result
        self.assertIn("MY_MARKER", source)

    def test_returns_none_when_not_in_zip(self):
        import io as _io
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("other.txt", "hi")
        p = self.root / "no-ext.zip"
        p.write_bytes(buf.getvalue())
        self.assertIsNone(self.mod._read_extension_source(p))

    def test_returns_none_on_bad_zip(self):
        p = self.root / "bad.zip"
        p.write_bytes(b"not a zip")
        self.assertIsNone(self.mod._read_extension_source(p))

    def test_does_not_execute_source(self):
        """_read_extension_source must not exec the code — side-effects must not run."""
        sentinel = self.root / "should-not-exist"
        # Write code that would create a file if executed
        source = f"open({str(sentinel)!r}, 'w').close()\n"
        zip_path = self._zip_with(source)
        self.mod._read_extension_source(zip_path)
        self.assertFalse(sentinel.exists(), "Extension source was exec'd during dry-run read")


# ---------------------------------------------------------------------------
# phase_dry_run
# ---------------------------------------------------------------------------

class FindLatestReleaseZipTests(unittest.TestCase):
    """Tests for _find_latest_release_zip() multi-location semver discovery."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.user_home = Path(self.tmp.name) / "home"
        self.home_dir = Path(self.tmp.name) / "home-wavefoundry"
        self.dist_dir = self.home_dir / "dist"
        self.downloads_dir = Path(self.tmp.name) / "downloads"
        self.root.mkdir(parents=True)
        self.user_home.mkdir(parents=True)
        self.home_dir.mkdir(parents=True)
        self.dist_dir.mkdir(parents=True)
        self.downloads_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_zip(self, directory: Path, name: str) -> Path:
        p = directory / name
        p.write_bytes(b"fake")
        return p

    def _run(self) -> Path | None:
        with unittest.mock.patch.object(
            self.mod, "_HOME_DIR", self.user_home
        ), unittest.mock.patch.object(
            self.mod, "_HOME_WAVEFOUNDRY_DIR", self.home_dir
        ), unittest.mock.patch.object(
            self.mod, "_DIST_DIR", self.dist_dir
        ), unittest.mock.patch.object(
            self.mod, "_DOWNLOADS_DIR", self.downloads_dir
        ):
            return self.mod._find_latest_release_zip(self.root)

    def test_returns_none_when_dir_absent(self):
        import shutil
        shutil.rmtree(self.root)
        shutil.rmtree(self.user_home)
        shutil.rmtree(self.home_dir)
        with unittest.mock.patch.object(
            self.mod, "_HOME_DIR", self.user_home
        ), unittest.mock.patch.object(
            self.mod, "_HOME_WAVEFOUNDRY_DIR", self.home_dir
        ), unittest.mock.patch.object(
            self.mod, "_DIST_DIR", self.dist_dir
        ), unittest.mock.patch.object(self.mod, "_DOWNLOADS_DIR", self.downloads_dir):
            result = self.mod._find_latest_release_zip(self.root)
        self.assertIsNone(result)

    def test_returns_none_when_dir_empty(self):
        result = self._run()
        self.assertIsNone(result)

    def test_finds_zip_in_user_home(self):
        self._write_zip(self.user_home, "wavefoundry-1.2.0.2abc.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.2.0.2abc.zip")

    def test_finds_zip_in_downloads(self):
        # 1p5dk: browser-downloaded packs commonly land in ~/Downloads — discovery must see them.
        self._write_zip(self.downloads_dir, "wavefoundry-1.2.0.2abc.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.2.0.2abc.zip")

    def test_downloads_competes_on_semver(self):
        # A higher-semver pack in Downloads wins over a lower one in dist (all paths pooled).
        self._write_zip(self.dist_dir, "wavefoundry-1.0.0.2abc.zip")
        self._write_zip(self.downloads_dir, "wavefoundry-1.6.0.p5ec.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.6.0.p5ec.zip")

    def test_returns_highest_semver_zip(self):
        self._write_zip(self.root, "wavefoundry-0.8.0.2abc.zip")
        self._write_zip(self.home_dir, "wavefoundry-1.0.0.2tm5.zip")
        self._write_zip(self.dist_dir, "wavefoundry-0.8.1.2def.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.0.0.2tm5.zip")

    def test_skips_non_matching_filenames(self):
        self._write_zip(self.dist_dir, "wavefoundry-1.0.0.2abc.zip")
        (self.home_dir / "unrelated.zip").write_bytes(b"x")
        (self.root / "wavefoundry-2026-05-20i.zip").write_bytes(b"x")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.0.0.2abc.zip")

    def test_multi_digit_minor_beats_single_digit(self):
        """1.10.0 must rank above 1.9.0 — not lexicographic comparison."""
        self._write_zip(self.home_dir, "wavefoundry-1.9.0.2abc.zip")
        self._write_zip(self.dist_dir, "wavefoundry-1.10.0.2xyz.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.10.0.2xyz.zip")

    def test_same_version_returns_lexicographically_greatest_build(self):
        """When MAJOR.MINOR.PATCH is tied, pick greatest build prefix (most recent build)."""
        self._write_zip(self.root, "wavefoundry-1.0.0.2abc.zip")
        self._write_zip(self.dist_dir, "wavefoundry-1.0.0.2zzz.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.0.0.2zzz.zip")

    def test_prefers_root_over_home_only_when_root_has_higher_version(self):
        self._write_zip(self.root, "wavefoundry-1.1.0.2zzz.zip")
        self._write_zip(self.home_dir, "wavefoundry-1.0.0.2abc.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.1.0.2zzz.zip")


import unittest.mock  # ensure mock is imported for FindLatestReleaseZipTests


class DryRunTests(unittest.TestCase):
    """Tests for phase_dry_run (--dry-run / -n)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        # Save and restore the module-level _log_file global so dry-run's
        # _log() calls don't bleed into any log file opened by another test
        # class, and vice-versa.
        self._saved_log_file = self.mod._log_file
        self.mod._close_log()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Minimal repo structure
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        # Isolate from real ~/.wavefoundry/dist/ AND ~/Downloads/ so tests are not polluted by
        # actual release zips present on the developer's machine (1p5dk added ~/Downloads to the
        # search paths — a very common landing spot for real packs).
        self._dist_patch = patch.object(self.mod, "_DIST_DIR", Path(self.tmp.name) / "dist")
        self._dist_patch.start()
        self._downloads_patch = patch.object(self.mod, "_DOWNLOADS_DIR", Path(self.tmp.name) / "downloads")
        self._downloads_patch.start()

    def tearDown(self):
        self._downloads_patch.stop()
        self._dist_patch.stop()
        self.mod._close_log()
        self.mod._log_file = self._saved_log_file  # restore (normally None)
        self.tmp.cleanup()

    def _run_dry(self) -> str:
        lines = []
        orig_log = self.mod._log
        self.mod._log = lambda msg: lines.append(msg)
        try:
            self.mod.phase_dry_run(self.root)
        finally:
            self.mod._log = orig_log
        return "\n".join(lines)

    def test_returns_zero(self):
        result = self.mod.phase_dry_run(self.root)
        self.assertEqual(result, 0)

    def test_no_disk_writes(self):
        """Dry-run must not create the upgrade lock or any other files."""
        ul = _load_upgrade_lib()
        self.mod.phase_dry_run(self.root)
        self.assertIsNone(ul.read_upgrade_lock(self.root))

    def test_output_contains_dry_run_header(self):
        output = self._run_dry()
        self.assertIn("Dry Run", output)
        self.assertIn("no changes will be made", output)

    def test_output_contains_hook_inventory_section(self):
        output = self._run_dry()
        self.assertIn("Hook Inventory", output)

    def test_no_extension_module_when_no_zip(self):
        output = self._run_dry()
        self.assertIn("n/a (no zip)", output)

    def test_extension_module_source_surfaced(self):
        """When zip has upgrade_extensions.py, its source appears in dry-run output."""
        import io as _io
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                ".wavefoundry/framework/scripts/upgrade_extensions.py",
                "# MARKER_IN_SOURCE\n",
            )
        zip_path = self.root / "wavefoundry-1.0.0.2abc.zip"
        zip_path.write_bytes(buf.getvalue())
        output = self._run_dry()
        self.assertIn("MARKER_IN_SOURCE", output)

    def test_convention_hook_source_surfaced(self):
        """Convention hook scripts found on disk appear in dry-run output."""
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook = hooks_dir / "post-extract"
        hook.write_text("#!/bin/sh\n# HOOK_MARKER\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)
        output = self._run_dry()
        self.assertIn("HOOK_MARKER", output)

    def test_no_convention_hooks_message(self):
        output = self._run_dry()
        self.assertIn("none", output.lower())


# ---------------------------------------------------------------------------
# update_upgrade_lock (upgrade_lib)
# ---------------------------------------------------------------------------

def _load_upgrade_lib():
    import importlib.util as _ilu
    import sys as _sys
    scripts_root = Path(__file__).resolve().parents[1]
    spec = _ilu.spec_from_file_location("upgrade_lib", scripts_root / "upgrade_lib.py")
    mod = _ilu.module_from_spec(spec)
    _sys.modules["upgrade_lib"] = mod
    spec.loader.exec_module(mod)
    return mod


class UpdateUpgradeLockTests(unittest.TestCase):
    """Tests for upgrade_lib.update_upgrade_lock and zip_path in write_upgrade_lock."""

    def setUp(self):
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_update_returns_false_when_no_lock(self):
        result = self.lib.update_upgrade_lock(self.root, pruned_count=5)
        self.assertFalse(result)

    def test_update_merges_fields(self):
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        result = self.lib.update_upgrade_lock(self.root, pruned_count=7)
        self.assertTrue(result)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertEqual(lock["pruned_count"], 7)
        # Existing fields preserved
        self.assertEqual(lock["from_version"], "2026-05-10a")

    def test_write_lock_records_zip_path(self):
        fake_zip = Path("/tmp/wavefoundry-2026-05-19a.zip")
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a", zip_path=fake_zip)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertEqual(lock["zip_path"], str(fake_zip))

    def test_write_lock_zip_path_none(self):
        self.lib.write_upgrade_lock(self.root, None, "2026-05-19a", zip_path=None)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["zip_path"])

    def test_pruned_count_initially_none(self):
        self.lib.write_upgrade_lock(self.root, None, "2026-05-19a")
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["pruned_count"])

    def test_index_rebuilt_at_recorded(self):
        """--rebuild-index records index_rebuilt_at; --cleanup reads it as ran_index_rebuild=True."""
        self.lib.write_upgrade_lock(self.root, None, "2026-05-19a")
        self.lib.update_upgrade_lock(self.root, index_rebuilt_at="2026-05-19T14:00:00+00:00")
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertTrue(bool(lock.get("index_rebuilt_at")))


class FailureMarkerLockTests(unittest.TestCase):
    """Wave 1p44o — failed_phase/failed_at persistence in the upgrade lock."""

    def setUp(self):
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_failure_markers_seeded_none(self):
        """write_upgrade_lock seeds failed_phase/failed_at None for schema clarity."""
        self.lib.write_upgrade_lock(self.root, None, "2026-05-19a")
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["failed_phase"])
        self.assertIsNone(lock["failed_at"])

    def test_failure_markers_persist_via_update(self):
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        self.lib.update_upgrade_lock(
            self.root, failed_phase="docs_gate", failed_at="2026-06-08T00:00:00+00:00"
        )
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertEqual(lock["failed_phase"], "docs_gate")
        self.assertEqual(lock["failed_at"], "2026-06-08T00:00:00+00:00")
        # Pre-existing fields preserved.
        self.assertEqual(lock["from_version"], "2026-05-10a")

    def test_old_lock_without_markers_still_parses(self):
        """read_upgrade_lock tolerates older locks lacking the new fields."""
        lock_path = self.lib.upgrade_lock_path(self.root)
        lock_path.write_text(
            json.dumps({"from_version": "a", "to_version": "b", "pid": 123}),
            encoding="utf-8",
        )
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock.get("failed_phase"))


class FinalizeFailedUpgradeTests(unittest.TestCase):
    """Wave 1p44o — the except SystemExit handler's data-safety decision.

    Post-mutation failure RETAINS the lock with a marker; pre-mutation failure
    removes it. Tested via the extracted ``_finalize_failed_upgrade`` helper.
    """

    def setUp(self):
        self.mod = load_upgrade_module()
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        # A lock exists (it is written at upgrade start, before the try body).
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")

    def tearDown(self):
        self.tmp.cleanup()

    def test_post_mutation_retains_lock_with_marker(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.mod._finalize_failed_upgrade(
                self.root, tree_mutated=True, current_phase="docs_gate"
            )
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNotNone(lock, "lock must be RETAINED on a post-mutation failure")
        self.assertEqual(lock["failed_phase"], "docs_gate")
        self.assertTrue(lock["failed_at"], "failed_at timestamp must be stamped")

    def test_pre_mutation_removes_lock(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.mod._finalize_failed_upgrade(
                self.root, tree_mutated=False, current_phase="extract"
            )
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock, "lock must be removed on a pre-mutation failure")


class OperatorSummaryGateLineTests(unittest.TestCase):
    """Wave 1p44o — Docs gate summary line derives from lock state (AC-5)."""

    def setUp(self):
        self.mod = load_upgrade_module()

    def _capture_summary(self, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version="2026-05-10a",
                to_version="2026-05-19a",
                zip_path=None,
                pruned_count=3,
                ran_index_rebuild=True,
                **kwargs,
            )
        return buf.getvalue()

    def test_gate_line_passed_when_no_failure(self):
        self.assertEqual(self.mod._docs_gate_summary_line(None), "PASSED")

    def test_gate_line_failed_when_docs_gate_failed(self):
        self.assertEqual(self.mod._docs_gate_summary_line("docs_gate"), "FAILED")

    def test_gate_line_not_run_for_earlier_phase(self):
        line = self.mod._docs_gate_summary_line("surface_rendering")
        self.assertIn("NOT RUN", line)
        self.assertIn("surface_rendering", line)

    def test_summary_passed_state(self):
        out = self._capture_summary(failed_phase=None)
        self.assertIn("Upgrade complete", out)
        self.assertIn("Docs gate:", out)
        self.assertIn("PASSED", out)
        self.assertNotIn("FAILED", out)

    def test_summary_failed_state_not_hardcoded(self):
        out = self._capture_summary(failed_phase="docs_gate")
        self.assertIn("Docs gate:", out)
        self.assertIn("FAILED", out)
        # The header must not falsely claim success on a failed upgrade.
        self.assertNotIn("Upgrade complete", out)
        self.assertIn("Upgrade INCOMPLETE", out)

    def test_summary_default_failed_phase_is_passed(self):
        """Back-compat: omitting failed_phase renders PASSED (success cleanup)."""
        out = self._capture_summary()
        self.assertIn("PASSED", out)

    def test_next_steps_defers_to_seed_160(self):  # wave 1p454
        out = self._capture_summary()
        self.assertIn("See seed-160 for the full editing-pass sequence", out)  # AC-1
        self.assertIn("seed-160 step 0 / Reconcile journals", out)             # AC-2
        self.assertNotIn("step 0e", out)                                        # AC-2
        self.assertIn("docs/scan-findings.json", out)                           # AC-3
        self.assertIn("seed-213", out)                                          # AC-3
        # secrets-resolution ordered BEFORE the docs-gate re-run (AC-3)
        self.assertLess(out.index("scan-findings.json"), out.index("Docs gate re-run"))
        # does NOT enumerate seed-160 step-8 backfills verbatim (AC-4)
        self.assertNotIn("lifecycle_id_policy", out)
        self.assertNotIn(".gitignore runtime contract", out)


class PhaseCleanupLockStateTests(unittest.TestCase):
    """Wave 1p44o — phase_cleanup warns on absent lock (AC-4); reflects failed state."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _capture_cleanup(self, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod.phase_cleanup(
                root=self.root,
                from_version=None,
                to_version=None,
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=False,
                **kwargs,
            )
        return buf.getvalue()

    def test_absent_lock_warns_no_phantom_summary(self):
        out = self._capture_cleanup(failed_phase=None, lock_present=False)
        self.assertIn("No upgrade lock found", out)
        # No all-defaults "Upgrade complete" summary masquerading as a real upgrade.
        self.assertNotIn("Upgrade complete", out)
        self.assertNotIn("Version:", out)

    def test_present_lock_prints_summary(self):
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        out = self._capture_cleanup(failed_phase=None, lock_present=True)
        self.assertIn("Upgrade complete", out)
        self.assertIn("Docs gate:", out)
        self.assertIn("PASSED", out)

    def test_failed_lock_marks_incomplete(self):
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        self.lib.update_upgrade_lock(self.root, failed_phase="docs_gate")
        out = self._capture_cleanup(failed_phase="docs_gate", lock_present=True)
        self.assertIn("Upgrade INCOMPLETE", out)
        self.assertIn("FAILED", out)
        self.assertIn("failure marker", out)

    def test_successful_cleanup_regenerates_codebase_map(self):
        # Wave 1p601: a clean upgrade regenerates the codebase map once, after the
        # index phase (so a fresh install has it — a "not generated" field report).
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        with patch.object(self.mod, "_regenerate_codebase_map_on_upgrade") as regen:
            self._capture_cleanup(failed_phase=None, lock_present=True)
        regen.assert_called_once_with(self.root)

    def test_failed_cleanup_does_not_regenerate_codebase_map(self):
        # A half-replaced tree (failed phase) must NOT regenerate the map.
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        self.lib.update_upgrade_lock(self.root, failed_phase="docs_gate")
        with patch.object(self.mod, "_regenerate_codebase_map_on_upgrade") as regen:
            self._capture_cleanup(failed_phase="docs_gate", lock_present=True)
        regen.assert_not_called()

    def test_regenerate_codebase_map_on_upgrade_is_fail_safe(self):
        # Fail-safe contract: a generator error must never propagate out of the
        # upgrade. Force the generator to be unavailable and assert no raise.
        with patch.object(self.mod, "SCRIPTS_DIR", self.root / "no-such-dir"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.mod._regenerate_codebase_map_on_upgrade(self.root)  # must not raise


class ReadInstalledRevisionDelegationTests(unittest.TestCase):
    """Wave 1p44p — upgrade_wavefoundry._read_installed_revision routes through the
    single canonical resolver in check_version (no MANIFEST json.loads)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_delegates_to_manifest_revision(self):
        p = self.root / "docs" / "prompts" / "prompt-surface-manifest.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"framework_revision": "1.6.0+xyz"}), encoding="utf-8")
        self.assertEqual(self.mod._read_installed_revision(self.root), "1.6.0+xyz")

    def test_returns_none_when_unresolvable(self):
        self.assertIsNone(self.mod._read_installed_revision(self.root))


class MaterializeSecretsPolicyTests(unittest.TestCase):
    """Wave 1p44z — pre-gate secrets-policy materialization (committer count →
    threshold; create only when absent; never overwrite operator values)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _init_git(self, emails):
        import subprocess as _sp
        _sp.run(["git", "init", "-q"], cwd=self.root, check=True)
        for i, email in enumerate(emails):
            (self.root / f"c{i}.txt").write_text(str(i), encoding="utf-8")
            _sp.run(["git", "add", "."], cwd=self.root, check=True)
            _sp.run(
                ["git", "-c", f"user.email={email}", "-c", f"user.name=A{i}",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", f"c{i}"],
                cwd=self.root, check=True,
            )

    def _policy(self) -> Path:
        return self.root / "docs" / "scan-rules.toml"

    def test_threshold_mapping(self):  # AC-3
        m = self.mod._committer_threshold
        self.assertEqual([m(0), m(1)], [1, 1])
        self.assertEqual([m(2), m(6)], [2, 2])
        self.assertEqual([m(7), m(99)], [3, 3])

    def test_single_committer_threshold_one(self):  # AC-2 / AC-3
        self._init_git(["solo@example.com"])
        msg = self.mod.materialize_secrets_policy(self.root)
        self.assertTrue(self._policy().exists())
        self.assertIn("false_positive_confirmations_required = 1", self._policy().read_text())
        self.assertIn("committer", msg)  # observable status (AC-6 surfaces this in the upgrade log)

    def test_small_team_threshold_two(self):  # AC-3
        self._init_git(["a@x.com", "b@x.com", "c@x.com"])
        self.mod.materialize_secrets_policy(self.root)
        self.assertIn("false_positive_confirmations_required = 2", self._policy().read_text())

    def test_existing_file_not_overwritten(self):  # AC-3 / AC-5
        self._policy().parent.mkdir(parents=True)
        self._policy().write_text(
            "[policy]\nfalse_positive_confirmations_required = 5\n", encoding="utf-8"
        )
        msg = self.mod.materialize_secrets_policy(self.root)
        self.assertIn("already present", msg)
        self.assertIn("= 5", self._policy().read_text())  # operator value preserved

    def test_no_git_repo_defaults_to_one(self):  # AC-2 (fresh / no history)
        msg = self.mod.materialize_secrets_policy(self.root)
        self.assertTrue(self._policy().exists())
        self.assertIn("false_positive_confirmations_required = 1", self._policy().read_text())
        self.assertEqual(self.mod._count_committers(self.root), 0)

    def test_materialize_emits_confirmation_valid_days(self):  # 1p457 follow-up
        # The expiry window must be written into the project file (not left as an
        # invisible implicit default), with the operator-facing tunability hint.
        self.mod.materialize_secrets_policy(self.root)
        text = self._policy().read_text()
        self.assertIn("confirmation_valid_days = 365", text)
        self.assertIn("set 0 to disable", text)


class StampManifestRevisionTests(unittest.TestCase):
    """Wave 1p44p follow-up — `_stamp_manifest_revision` writes framework/VERSION into
    `docs/prompts/prompt-surface-manifest.json` `framework_revision` after upgrade so
    the installed-revision marker tracks the pack instead of freezing at the
    pre-upgrade value (never creates the manifest; never clobbers other keys)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _set_version(self, v):
        p = self.root / ".wavefoundry" / "framework" / "VERSION"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(v + "\n", encoding="utf-8")

    def _manifest(self) -> Path:
        return self.root / "docs" / "prompts" / "prompt-surface-manifest.json"

    def _write_manifest(self, data):
        self._manifest().parent.mkdir(parents=True, exist_ok=True)
        self._manifest().write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_stamps_stale_revision(self):
        self._set_version("1.6.0+p49k")
        self._write_manifest({"framework_revision": "1.5.1+p3qj", "other": 1})
        self.assertTrue(self.mod._stamp_manifest_revision(self.root))
        self.assertEqual(
            json.loads(self._manifest().read_text())["framework_revision"], "1.6.0+p49k")

    def test_preserves_other_keys(self):
        self._set_version("1.6.0+p49k")
        self._write_manifest({"framework_revision": "1.5.1+p3qj", "surfaces": ["a", "b"], "n": 3})
        self.mod._stamp_manifest_revision(self.root)
        data = json.loads(self._manifest().read_text())
        self.assertEqual(data["surfaces"], ["a", "b"])
        self.assertEqual(data["n"], 3)

    def test_noop_when_already_current(self):
        self._set_version("1.6.0+p49k")
        self._write_manifest({"framework_revision": "1.6.0+p49k"})
        self.assertFalse(self.mod._stamp_manifest_revision(self.root))

    def test_noop_when_manifest_absent(self):
        self._set_version("1.6.0+p49k")
        self.assertFalse(self.mod._stamp_manifest_revision(self.root))
        self.assertFalse(self._manifest().exists())  # never created

    def test_noop_when_version_absent(self):
        self._write_manifest({"framework_revision": "1.5.1+p3qj"})
        self.assertFalse(self.mod._stamp_manifest_revision(self.root))
        self.assertEqual(
            json.loads(self._manifest().read_text())["framework_revision"], "1.5.1+p3qj")

    def test_noop_when_manifest_unparseable(self):
        self._set_version("1.6.0+p49k")
        self._manifest().parent.mkdir(parents=True, exist_ok=True)
        self._manifest().write_text("{ not json", encoding="utf-8")
        self.assertFalse(self.mod._stamp_manifest_revision(self.root))


class ResumeAfterGateTests(unittest.TestCase):
    """Wave 1p44r — resume_after_gate re-runs only the docs gate against the
    retained-lock tree; extract is idempotent when the tree is already at target."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _resume(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return self.mod.main(["--resume-after-gate", "--root", str(self.root)])

    def _failed_gate_lock(self):
        self.lib.write_upgrade_lock(self.root, "1.5.0", "1.6.0")
        self.lib.update_upgrade_lock(self.root, failed_phase="docs_gate", failed_at="t")

    # AC-2 / AC-6b — extract idempotence decision.
    def test_tree_already_at_target(self):
        (self.root / "framework").mkdir()
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        (self.root / ".wavefoundry" / "framework" / "VERSION").write_text("1.6.0\n", encoding="utf-8")
        self.assertTrue(self.mod._tree_already_at(self.root, "1.6.0"))
        self.assertFalse(self.mod._tree_already_at(self.root, "1.7.0"))
        self.assertFalse(self.mod._tree_already_at(self.root, "unknown"))
        self.assertFalse(self.mod._tree_already_at(self.root, None))

    def test_tree_already_at_no_version_file(self):
        self.assertFalse(self.mod._tree_already_at(self.root, "1.6.0"))

    # AC-6a / AC-5 — resume runs the gate (no re-extract) and exits 0 on pass.
    def test_resume_runs_gate_and_clears_marker_on_pass(self):
        self._failed_gate_lock()
        called = []
        with patch.object(self.mod, "phase_docs_gate", lambda r: called.append(r)):
            rc = self._resume()
        self.assertEqual(rc, 0)
        self.assertEqual(len(called), 1)  # only the gate ran
        self.assertIsNone(self.lib.read_upgrade_lock(self.root).get("failed_phase"))

    # AC-5 — non-zero exit on repeated gate failure; marker retained.
    def test_resume_nonzero_on_repeated_failure(self):
        self._failed_gate_lock()
        def _fail(_root):
            raise SystemExit(1)
        with patch.object(self.mod, "phase_docs_gate", _fail):
            with self.assertRaises(SystemExit) as cm:
                self._resume()
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(self.lib.read_upgrade_lock(self.root).get("failed_phase"), "docs_gate")

    # AC-3 — refuse to resume when the prior failure was NOT the docs gate.
    def test_resume_refuses_non_gate_failure(self):
        self.lib.write_upgrade_lock(self.root, "1.5.0", "1.6.0")
        self.lib.update_upgrade_lock(self.root, failed_phase="extract", failed_at="t")
        called = []
        with patch.object(self.mod, "phase_docs_gate", lambda r: called.append(r)):
            rc = self._resume()
        self.assertEqual(rc, 1)
        self.assertEqual(called, [])  # gate must NOT run

    def test_resume_refuses_when_no_lock(self):
        self.assertEqual(self._resume(), 1)


class PhasePruningCountTests(unittest.TestCase):
    """Wave 1p44q — phase_pruning reads the pruned count from prune_framework.py's
    stderr summary, not the old (always-zero) stdout substring heuristic."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _prune(self, stderr, stdout="", returncode=0):
        from types import SimpleNamespace
        fake = SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)
        with patch.object(self.mod.subprocess, "run", return_value=fake), \
             contextlib.redirect_stdout(io.StringIO()):
            return self.mod.phase_pruning(self.root)

    def test_deleted_count_parsed(self):
        self.assertEqual(self._prune("prune: deleted 7 item(s)\n"), 7)

    def test_dry_run_would_delete_count_parsed(self):
        self.assertEqual(self._prune("prune: would delete 3 item(s)\n"), 3)

    def test_nothing_to_remove_is_zero(self):
        self.assertEqual(self._prune("prune: nothing to remove\n"), 0)

    def test_old_stdout_heuristic_no_longer_used(self):
        # Per-file stdout lines say "deleted:", never "removed"/"pruned"; the count
        # must come from the stderr summary, so absent-stderr → 0 (not a stdout scan).
        self.assertEqual(self._prune("", stdout="deleted: a\ndeleted: b\n"), 0)

    def test_nonzero_exit_returns_zero(self):
        self.assertEqual(self._prune("prune: deleted 5 item(s)\n", returncode=1), 0)


class PreferredPythonTests(unittest.TestCase):
    """Regression coverage for explicit shared-venv subprocess routing."""

    def setUp(self):
        self.mod = load_upgrade_module()
        # Wave 1p7pm: phase_surface_rendering calls venv_bootstrap.ensure_python_resolves(), which is
        # SIDE-EFFECTING (creates ~/.local/bin/python3 + may append to the shell rc). Patch it to a
        # no-op so driving phase_surface_rendering here never mutates the operator's box. (The real
        # heal is exercised, safely isolated into a tempdir, only in test_venv_bootstrap.py.)
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import venv_bootstrap
        heal = patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok")
        self.ensure_python_resolves_mock = heal.start()
        self.addCleanup(heal.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_venv_python(self) -> Path:
        venv_root = self.root / ".venv-test"
        venv_python = venv_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        venv_python.parent.mkdir(parents=True, exist_ok=True)
        venv_python.write_text("", encoding="utf-8")
        return venv_python

    def test_phase_surface_rendering_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0)
        script = self.root / "render_platform_surfaces.py"
        script.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock:
            self.mod.phase_surface_rendering(self.root)
        self.assertEqual(run_mock.call_args.args[0][0], str(venv_python))

    def test_phase_index_update_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0)
        setup_script = self.root / "setup_index.py"
        setup_script.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock, \
             patch("subprocess.Popen") as popen_mock:
            self.mod.phase_index_update(self.root)
        self.assertEqual(run_mock.call_args.args[0][0], str(venv_python))
        self.assertEqual(popen_mock.call_args.args[0][0], str(venv_python))

    def test_phase_index_update_runs_graph_only_update(self):
        # Wave 1p7dh: the upgrade index phase updates the GRAPH too (symmetric
        # with semantic) so a GRAPH_BUILDER_VERSION bump materializes during the
        # upgrade. `--graph-only` WITHOUT `--full` → update-or-escalate, not a
        # forced rebuild.
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0)
        setup_script = self.root / "setup_index.py"
        setup_script.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock, \
             patch("subprocess.Popen"):
            self.mod.phase_index_update(self.root)
        graph_calls = [c for c in run_mock.call_args_list if "--graph-only" in c.args[0]]
        self.assertEqual(len(graph_calls), 1, f"expected one --graph-only update call: {run_mock.call_args_list}")
        self.assertNotIn("--full", graph_calls[0].args[0], "update path must be update-or-escalate, not forced --full")

    def test_phase_index_rebuild_runs_graph_only_full(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0)
        setup_script = self.root / "setup_index.py"
        setup_script.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock, \
             patch("subprocess.Popen"):
            self.mod.phase_index_rebuild(self.root)
        graph_calls = [c for c in run_mock.call_args_list if "--graph-only" in c.args[0]]
        self.assertEqual(len(graph_calls), 1, f"expected one --graph-only rebuild call: {run_mock.call_args_list}")
        self.assertIn("--full", graph_calls[0].args[0], "rebuild path runs a full graph rebuild")


# ---------------------------------------------------------------------------
# Upgrade log file (12r21)
# ---------------------------------------------------------------------------

class UpgradeLogTests(unittest.TestCase):
    """Tests for _open_log / _close_log / _log tee behaviour."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.mod._close_log()   # defensive: ensure clean global state entering this test
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.mod._close_log()   # release handle so tmp dir can be deleted
        self.tmp.cleanup()

    def _log_path(self) -> Path:
        return self.root / ".wavefoundry" / "logs" / "upgrade.log"

    def test_log_file_created_on_open(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._close_log()
        self.assertTrue(self._log_path().exists())

    def test_log_contains_message(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._log("hello from test")
        self.mod._close_log()
        content = self._log_path().read_text(encoding="utf-8")
        self.assertIn("hello from test", content)

    def test_log_contains_timestamp(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._log("timestamped line")
        self.mod._close_log()
        content = self._log_path().read_text(encoding="utf-8")
        # Timestamps are absolute UTC date-time stamps.
        import re
        self.assertRegex(content, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00 timestamped line")

    def test_err_also_written_to_log(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._err("something went wrong")
        self.mod._close_log()
        content = self._log_path().read_text(encoding="utf-8")
        self.assertIn("ERROR: something went wrong", content)

    def test_append_mode_preserves_prior_content(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._log("phase 0 line")
        self.mod._close_log()

        self.mod._open_log(self.root, mode="a")
        self.mod._log("phase 4 line")
        self.mod._close_log()

        content = self._log_path().read_text(encoding="utf-8")
        self.assertIn("phase 0 line", content)
        self.assertIn("phase 4 line", content)

    def test_write_mode_truncates_prior_log(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._log("old content")
        self.mod._close_log()

        self.mod._open_log(self.root, mode="w")
        self.mod._log("new content")
        self.mod._close_log()

        content = self._log_path().read_text(encoding="utf-8")
        self.assertNotIn("old content", content)
        self.assertIn("new content", content)

    def test_no_log_written_when_not_open(self):
        """_log() is a no-op for the file when log is closed."""
        self.mod._log("should not appear in file")
        self.assertFalse(self._log_path().exists())

    def test_upgrade_log_path_helper(self):
        expected = self.root / ".wavefoundry" / "logs" / "upgrade.log"
        self.assertEqual(self.mod.upgrade_log_path(self.root), expected)


# ---------------------------------------------------------------------------
# 1.4.x → 1.5.0 migration helpers (wave 1p35d / 1p3ay)
# ---------------------------------------------------------------------------

def _load_upgrade_extensions():
    """Load the canonical upgrade_extensions.py (not from a zip)."""
    import importlib.util
    scripts_root = Path(__file__).resolve().parents[1]
    path = scripts_root / "upgrade_extensions.py"
    spec = importlib.util.spec_from_file_location("upgrade_extensions_canonical", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FromVersionPredatesTests(unittest.TestCase):
    """AC-2, AC-3: version-gate correctness for 1.4.x → 1.5.0 migration."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()

    def test_pre_1_5_0_semver_strings_return_true(self):
        for v in ("1.0.0", "1.3.32", "1.4.0", "1.4.1", "1.4.1+p347", "0.9.0"):
            self.assertTrue(
                self.ext._from_version_predates(v, "1.5.0"),
                f"{v} should be older than 1.5.0",
            )

    def test_at_or_after_1_5_0_returns_false(self):
        for v in ("1.5.0", "1.5.0+x", "1.5.1", "1.6.0", "2.0.0", "10.0.0"):
            self.assertFalse(
                self.ext._from_version_predates(v, "1.5.0"),
                f"{v} should be at or after 1.5.0",
            )

    def test_unknown_or_unparseable_returns_true_safe_default(self):
        """Idempotent migrations are safe to re-run; treating unknown as 'old'
        means we never silently skip migration on a state that needs it."""
        for v in (None, "", "2026-05-19a", "garbage", "v1.5.0"):
            self.assertTrue(
                self.ext._from_version_predates(v, "1.5.0"),
                f"{v!r} should be treated as predating (safe default)",
            )


class RoleBackfillMigrationTests(unittest.TestCase):
    """AC-4 through AC-6: Role: backfill on docs/agents/*.md."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "specialists").mkdir(parents=True)
        (self.root / "docs" / "agents" / "personas").mkdir(parents=True)
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel: str, body: str) -> Path:
        path = self.root / rel
        path.write_text(body, encoding="utf-8")
        return path

    def test_inserts_role_when_missing_after_status_line(self):
        path = self._write(
            "docs/agents/code-reviewer.md",
            "# Code Reviewer\n\n"
            "Owner: Engineering\n"
            "Status: active\n"
            "Category: review\n"
            "Last verified: 2026-05-01\n\n"
            "## Operating Identity\n\nReviews code.\n",
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, ["docs/agents/code-reviewer.md"])
        text = path.read_text(encoding="utf-8")
        self.assertIn("Role: code-reviewer", text)
        # Inserted right after Status:
        self.assertRegex(text, r"Status: active\nRole: code-reviewer\nCategory: review")

    def test_falls_back_to_owner_anchor_when_no_status_line(self):
        path = self._write(
            "docs/agents/specialists/my-spec.md",
            "# My Spec\n\n"
            "Owner: Engineering\n"
            "Category: specialist\n"
            "Last verified: 2026-05-01\n\n"
            "## Identity\n\nFoo.\n",
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, ["docs/agents/specialists/my-spec.md"])
        text = path.read_text(encoding="utf-8")
        self.assertRegex(text, r"Owner: Engineering\nRole: my-spec\nCategory: specialist")

    def test_already_present_role_not_modified(self):
        body = (
            "# Existing\n\n"
            "Owner: Engineering\n"
            "Status: active\n"
            "Role: existing\n"
            "Category: review\n\n"
            "## Identity\n\nFoo.\n"
        )
        path = self._write("docs/agents/existing.md", body)
        original = path.read_text(encoding="utf-8")
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, [])
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_exempt_filenames_skipped(self):
        for exempt in ("README.md", "session-handoff.md", "platform-mapping.md"):
            self._write(
                f"docs/agents/{exempt}",
                "# X\n\nOwner: Engineering\nStatus: active\n\n## Body\n",
            )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, [])

    def test_journals_directory_skipped(self):
        path = self._write(
            "docs/agents/journals/wave-coordinator.md",
            "# Journal\n\nOwner: Engineering\nStatus: active\n\n## Captures\n",
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, [])
        # Verify the journal file was not modified
        self.assertNotIn("Role:", path.read_text(encoding="utf-8"))

    def test_F6_recursive_walk_finds_nested_layout(self):
        """Wave 1p3b9 (1p3b7 F6): the migration walks docs/agents/ recursively
        so enterprise nested layouts (e.g., `docs/agents/teams/<team>/<role>.md`)
        are covered. Previously the migration walked three fixed subdirs and
        missed deeper nesting."""
        nested = self.root / "docs" / "agents" / "teams" / "auth-team"
        nested.mkdir(parents=True)
        (nested / "code-reviewer.md").write_text(
            "Owner: Engineering\nStatus: active\nCategory: review\n", encoding="utf-8"
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, ["docs/agents/teams/auth-team/code-reviewer.md"])
        # File was rewritten with Role: line
        text = (nested / "code-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("Role: code-reviewer", text)

    def test_F6_journals_skipped_at_any_depth(self):
        """Wave 1p3b9 (1p3b7 F6): the `journals` skip applies at any depth in
        the agents tree. A team's journal doc deep in the tree must NOT get
        a Role: insertion."""
        deep_journal = self.root / "docs" / "agents" / "teams" / "auth" / "journals" / "note.md"
        deep_journal.parent.mkdir(parents=True)
        original = "Owner: x\nStatus: active\n## Captures\n"
        deep_journal.write_text(original, encoding="utf-8")
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, [])
        # File unchanged
        self.assertEqual(deep_journal.read_text(encoding="utf-8"), original)

    def test_walks_specialists_and_personas_subdirs(self):
        self._write(
            "docs/agents/specialists/red-team.md",
            "Owner: Engineering\nStatus: active\nCategory: specialist\n",
        )
        self._write(
            "docs/agents/personas/admin.md",
            "Owner: Engineering\nStatus: active\nCategory: persona\n",
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(sorted(modified), [
            "docs/agents/personas/admin.md",
            "docs/agents/specialists/red-team.md",
        ])

    def test_idempotent_second_run_is_noop(self):
        """AC-13: re-running performs zero modifications once Role: is set."""
        self._write(
            "docs/agents/code-reviewer.md",
            "Owner: Engineering\nStatus: active\nCategory: review\n",
        )
        first = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(len(first), 1)
        second = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(second, [])

    def test_missing_agents_dir_safe(self):
        # Fresh tmp without docs/agents/
        with tempfile.TemporaryDirectory() as t:
            bare_root = Path(t).resolve()
            self.assertEqual(self.ext._backfill_role_field_on_agent_docs(bare_root), [])


class PycacheLauncherCleanupTests(unittest.TestCase):
    """AC-7: deletes .claude/hooks/pycache-cleanup* launcher files."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".claude" / "hooks").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_deletes_all_three_launcher_variants(self):
        for name in ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd"):
            (self.root / ".claude" / "hooks" / name).write_text("legacy\n", encoding="utf-8")
        deleted = self.ext._delete_pycache_hook_launchers(self.root)
        self.assertEqual(sorted(deleted), [
            ".claude/hooks/pycache-cleanup",
            ".claude/hooks/pycache-cleanup.cmd",
            ".claude/hooks/pycache-cleanup.py",
        ])
        for name in ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd"):
            self.assertFalse((self.root / ".claude" / "hooks" / name).exists())

    def test_deletes_only_existing(self):
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        deleted = self.ext._delete_pycache_hook_launchers(self.root)
        self.assertEqual(deleted, [".claude/hooks/pycache-cleanup.py"])

    def test_idempotent_when_no_launchers_present(self):
        self.assertEqual(self.ext._delete_pycache_hook_launchers(self.root), [])
        # Second call still a no-op
        self.assertEqual(self.ext._delete_pycache_hook_launchers(self.root), [])

    def test_does_not_touch_other_launcher_files(self):
        for name in ("pre-edit.py", "post-edit", "simulate-hooks.cmd"):
            (self.root / ".claude" / "hooks" / name).write_text("framework\n", encoding="utf-8")
        self.ext._delete_pycache_hook_launchers(self.root)
        for name in ("pre-edit.py", "post-edit", "simulate-hooks.cmd"):
            self.assertTrue((self.root / ".claude" / "hooks" / name).exists())

    def test_missing_claude_dir_safe(self):
        with tempfile.TemporaryDirectory() as t:
            bare_root = Path(t).resolve()
            self.assertEqual(self.ext._delete_pycache_hook_launchers(bare_root), [])


class SettingsJsonPycacheRowStripTests(unittest.TestCase):
    """AC-8, AC-9: removes the retired PostToolUse Bash pycache row,
    preserves operator-added customs."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.settings_path = self.root / ".claude" / "settings.json"
        self.settings_path.parent.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, data) -> None:
        self.settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read(self):
        return json.loads(self.settings_path.read_text(encoding="utf-8"))

    def test_strips_legacy_pycache_row(self):
        self._write({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit|Write",
                     "hooks": [{"type": "command", "command": ".claude/hooks/pre-edit"}]},
                ],
                "PostToolUse": [
                    {"matcher": "Bash",
                     "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup",
                                "statusMessage": "Cleaning __pycache__..."}]},
                    {"matcher": "Edit|Write",
                     "hooks": [{"type": "command", "command": ".claude/hooks/post-edit"}]},
                ],
            },
        })
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        # Wave 1p3b9 (1p3b7 F4): function now returns list of paths modified.
        self.assertEqual(result, [".claude/settings.json"])
        data = self._read()
        post = data["hooks"]["PostToolUse"]
        self.assertEqual(len(post), 1)
        self.assertEqual(post[0]["matcher"], "Edit|Write")
        # PreToolUse preserved
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 1)

    def test_strips_cmd_variant(self):
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command",
                            "command": "cmd.exe /c .claude\\hooks\\pycache-cleanup.cmd"}]},
            ]},
        })
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(result, [".claude/settings.json"])
        self.assertEqual(self._read()["hooks"]["PostToolUse"], [])

    def test_preserves_operator_custom_bash_hook(self):
        """An operator-added Bash hook with a DIFFERENT command must be preserved."""
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": "/operator/custom/audit-log"}]},
            ]},
        })
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(result, [".claude/settings.json"])
        post = self._read()["hooks"]["PostToolUse"]
        self.assertEqual(len(post), 1)
        self.assertIn("audit-log", post[0]["hooks"][0]["command"])

    def test_noop_when_no_pycache_row(self):
        """AC-9: when no pycache row present, no file rewrite, return empty list."""
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Edit|Write",
                 "hooks": [{"type": "command", "command": ".claude/hooks/post-edit"}]},
            ]},
        })
        before = self.settings_path.read_text(encoding="utf-8")
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(result, [])
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), before)

    def test_missing_settings_file_returns_empty_list(self):
        # setUp creates the parent dir but never writes settings.json
        self.assertFalse(self.settings_path.exists())
        self.assertEqual(self.ext._strip_pycache_row_from_claude_settings(self.root), [])

    def test_malformed_settings_returns_empty_list(self):
        self.settings_path.write_text("{not valid json", encoding="utf-8")
        self.assertEqual(self.ext._strip_pycache_row_from_claude_settings(self.root), [])

    def test_idempotent_second_run_is_noop(self):
        """AC-13: after first strip, second call returns empty list and doesn't rewrite."""
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
            ]},
        })
        first = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(first, [".claude/settings.json"])
        second = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(second, [])

    def test_F4_strips_from_settings_local_json_too(self):
        """Wave 1p3b9 (1p3b7 F4): personal-override settings.local.json gets
        stripped alongside the committed settings.json. Enterprise consumers
        with shared local-overrides don't leave the orphan row behind."""
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
            ]},
        })
        local_path = self.root / ".claude" / "settings.local.json"
        local_path.write_text(
            json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command",
                            "command": ".claude/hooks/pycache-cleanup"}]},
            ]}}, indent=2),
            encoding="utf-8",
        )
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(sorted(result), [
            ".claude/settings.json",
            ".claude/settings.local.json",
        ])
        # Both files have the row removed
        for rel in (".claude/settings.json", ".claude/settings.local.json"):
            data = json.loads((self.root / rel).read_text(encoding="utf-8"))
            self.assertEqual(data["hooks"]["PostToolUse"], [])

    def test_F4_settings_local_only(self):
        """Only settings.local.json has the row; settings.json absent.
        Strip operates on whichever file exists and has the row."""
        local_path = self.root / ".claude" / "settings.local.json"
        local_path.write_text(
            json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command",
                            "command": ".claude/hooks/pycache-cleanup"}]},
            ]}}, indent=2),
            encoding="utf-8",
        )
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(result, [".claude/settings.local.json"])


class ConvergenceMigrationTests(unittest.TestCase):
    """Wave 1p3iv (1p3j7): convergence half — `post_extract` always runs the
    legacy-config-key rewrite (no version gate), driven by the canonical-names
    manifest. Tests cover the rewrite helpers in isolation; integration with
    `post_extract` is verified by `PostExtractHookOrchestrationTests`."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "docs").mkdir()
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        # Plant a minimal canonical-names manifest in the test repo so the
        # rewrite helpers can resolve aliases against it.
        manifest = {
            "schema_version": 1,
            "role_renames": {},
            "config_key_renames": {
                "wave_council_policy": {
                    "canonical": "wave_review", "removed_in": "2.0.0",
                },
                "wave_execution": {
                    "canonical": "wave_implement", "removed_in": "2.0.0",
                },
            },
        }
        (self.root / ".wavefoundry/framework/canonical-names.json").write_text(
            json.dumps(manifest), encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, data):
        (self.root / "docs/workflow-config.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )

    def _read_config(self):
        return json.loads((self.root / "docs/workflow-config.json").read_text(encoding="utf-8"))

    def test_rewrite_renames_legacy_to_canonical(self):
        """Legacy-only key → renamed in-place; performed tuple carries
        action='rename' and dropped_value=None."""
        self._write_config({"wave_council_policy": {"enabled": True}, "other": 1})
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(
            performed,
            [("wave_council_policy", "wave_review", "rename", None)],
        )
        result = self._read_config()
        self.assertIn("wave_review", result)
        self.assertNotIn("wave_council_policy", result)
        self.assertEqual(result["wave_review"], {"enabled": True})
        # Other keys preserved
        self.assertEqual(result["other"], 1)

    def test_rewrite_drops_legacy_when_canonical_already_present(self):
        """Both legacy AND canonical → canonical wins (operator-explicit),
        legacy entry is dropped; the dropped value is captured in the
        returned tuple so operators can recover it from the log."""
        self._write_config({
            "wave_review": {"enabled": True, "explicit": True},
            "wave_council_policy": {"enabled": False},
        })
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        # Action discriminator distinguishes drop from rename, and the dropped
        # value is captured for log fidelity (1p3iv post-review fix).
        self.assertEqual(
            performed,
            [(
                "wave_council_policy",
                "wave_review",
                "drop",
                {"enabled": False},
            )],
        )
        result = self._read_config()
        self.assertNotIn("wave_council_policy", result)
        self.assertEqual(result["wave_review"], {"enabled": True, "explicit": True})

    def test_rewrite_is_noop_when_canonical_only(self):
        """No legacy keys present → no work; performed list is empty."""
        self._write_config({"wave_review": {"enabled": True}})
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(performed, [])
        # File untouched (still contains canonical only)
        self.assertEqual(self._read_config(), {"wave_review": {"enabled": True}})

    def test_rewrite_handles_multiple_legacy_keys_in_one_pass(self):
        """Both legacy spellings present → both renamed in one call."""
        self._write_config({
            "wave_council_policy": {"a": 1},
            "wave_execution": {"b": 2},
        })
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        legacies = {item[0] for item in performed}
        self.assertEqual(legacies, {"wave_council_policy", "wave_execution"})
        actions = {item[2] for item in performed}
        self.assertEqual(actions, {"rename"})
        result = self._read_config()
        self.assertIn("wave_review", result)
        self.assertIn("wave_implement", result)

    def test_rewrite_is_idempotent(self):
        """Running the rewrite twice yields no work on the second invocation."""
        self._write_config({"wave_council_policy": {"enabled": True}})
        first = self.ext._rewrite_legacy_config_keys(self.root)
        second = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(
            first,
            [("wave_council_policy", "wave_review", "rename", None)],
        )
        self.assertEqual(second, [])

    def test_rewrite_captures_dropped_value_for_complex_legacy_state(self):
        """When the legacy entry holds a non-trivial dict, the dropped value
        is captured in full so the log line can render it as JSON."""
        legacy_value = {
            "enabled": False,
            "policy": {"required_for_all_waves": True},
            "fixed_seats": ["red-team"],
        }
        self._write_config({
            "wave_review": {"enabled": True},
            "wave_council_policy": legacy_value,
        })
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(len(performed), 1)
        _legacy, _canonical, action, dropped_value = performed[0]
        self.assertEqual(action, "drop")
        self.assertEqual(dropped_value, legacy_value)

    # --- Report file writers (1p3iv post-review fix #2) ---

    def test_real_run_writes_convergence_log_file(self):
        """Real-run with renames performed → writes
        upgrade-convergence-migration.log with a record per performed item."""
        self._write_config({"wave_council_policy": {"enabled": True}})

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.dry_run = False
        ctx.from_version = "1.5.0+abcd"
        ctx.to_version = "1.5.0+efgh"
        ctx.zip_path = None
        ctx.yes = True

        self.ext._run_convergence_migration(ctx)

        log_path = self.root / ".wavefoundry/logs/upgrade-convergence-migration.log"
        self.assertTrue(log_path.exists())
        body = log_path.read_text(encoding="utf-8")
        self.assertIn("REAL RUN", body)
        self.assertIn("renamed `wave_council_policy` → `wave_review`", body)

    def test_real_run_log_records_dropped_value_for_drop_case(self):
        """Real-run with a drop → log records the dropped value as JSON so
        operators can recover from the file alone."""
        self._write_config({
            "wave_review": {"enabled": True},
            "wave_council_policy": {"enabled": False, "marker": "operator-set"},
        })

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.dry_run = False
        ctx.from_version = "1.5.0+abcd"
        ctx.to_version = "1.5.0+efgh"
        ctx.zip_path = None
        ctx.yes = True

        self.ext._run_convergence_migration(ctx)

        log_path = self.root / ".wavefoundry/logs/upgrade-convergence-migration.log"
        body = log_path.read_text(encoding="utf-8")
        self.assertIn("dropped legacy `wave_council_policy`", body)
        # The dropped value (a JSON dict) appears in the log so the operator
        # can recover it without consulting git history.
        self.assertIn('"marker": "operator-set"', body)

    def test_dry_run_writes_convergence_preview_log_file(self):
        """Dry-run with planned actions → writes
        upgrade-convergence-migration.preview.log (parity with the 1.4 → 1.5
        migration preview report shape)."""
        self._write_config({"wave_council_policy": {"enabled": True}})

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.dry_run = True
        ctx.from_version = "1.5.0+abcd"
        ctx.to_version = "1.5.0+efgh"
        ctx.zip_path = None
        ctx.yes = True

        self.ext._run_convergence_migration(ctx)

        preview_path = self.root / ".wavefoundry/logs/upgrade-convergence-migration.preview.log"
        self.assertTrue(preview_path.exists())
        body = preview_path.read_text(encoding="utf-8")
        self.assertIn("PREVIEW", body)
        self.assertIn("would rename `wave_council_policy` → `wave_review`", body)
        # File on disk is untouched
        self.assertEqual(
            self._read_config(),
            {"wave_council_policy": {"enabled": True}},
        )

    def test_no_log_files_when_no_renames_apply(self):
        """No legacy keys → no log files written (silent no-op)."""
        self._write_config({"wave_review": {"enabled": True}})

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.dry_run = False
        ctx.from_version = "1.5.0+abcd"
        ctx.to_version = "1.5.0+efgh"
        ctx.zip_path = None
        ctx.yes = True

        self.ext._run_convergence_migration(ctx)

        self.assertFalse((self.root / ".wavefoundry/logs/upgrade-convergence-migration.log").exists())
        self.assertFalse((self.root / ".wavefoundry/logs/upgrade-convergence-migration.preview.log").exists())

    def test_rewrite_is_noop_when_workflow_config_missing(self):
        """No workflow-config.json → no error, empty result."""
        self.assertEqual(self.ext._rewrite_legacy_config_keys(self.root), [])

    def test_rewrite_is_noop_when_workflow_config_malformed(self):
        """Malformed JSON → no error, empty result (degraded mode)."""
        (self.root / "docs/workflow-config.json").write_text("{not valid", encoding="utf-8")
        self.assertEqual(self.ext._rewrite_legacy_config_keys(self.root), [])

    def test_preview_plans_renames_without_touching_disk(self):
        """Preview returns the planned-action strings; file is unchanged."""
        self._write_config({"wave_council_policy": {"enabled": True}})
        before = (self.root / "docs/workflow-config.json").read_text(encoding="utf-8")
        planned = self.ext._preview_legacy_config_key_rewrite(self.root)
        after = (self.root / "docs/workflow-config.json").read_text(encoding="utf-8")
        self.assertEqual(after, before)
        self.assertEqual(len(planned), 1)
        self.assertIn("wave_council_policy", planned[0])
        self.assertIn("wave_review", planned[0])

    def test_preview_distinguishes_rename_vs_drop_when_both_present(self):
        """When both legacy and canonical exist, preview wording reflects the
        drop-legacy outcome (not a rename)."""
        self._write_config({
            "wave_review": {"explicit": True},
            "wave_council_policy": {"legacy": True},
        })
        planned = self.ext._preview_legacy_config_key_rewrite(self.root)
        self.assertEqual(len(planned), 1)
        self.assertIn("drop legacy", planned[0])


class PostExtractHookOrchestrationTests(unittest.TestCase):
    """AC-1, AC-10, AC-11, AC-12, AC-14: post_extract integration."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def _ctx(self, from_version: str | None = "1.4.1+p347"):
        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.from_version = from_version
        ctx.to_version = "1.5.0"
        ctx.zip_path = None
        ctx.yes = True
        return ctx

    def _report_path(self) -> Path:
        return self.root / ".wavefoundry" / "logs" / "upgrade-migration-1.5.0.log"

    def test_version_gate_skips_when_from_at_cutoff(self):
        """AC-14: from_version = 1.5.0 → zero work, no report."""
        # Plant a state that WOULD be migrated if the gate ran
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        self.ext.post_extract(self._ctx(from_version="1.5.0"))
        # Launcher still present; report not written
        self.assertTrue((self.root / ".claude" / "hooks" / "pycache-cleanup.py").exists())
        self.assertFalse(self._report_path().exists())

    def test_version_gate_fires_when_pre_cutoff(self):
        """AC-1: from_version = 1.4.1 → migrations run."""
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        self.ext.post_extract(self._ctx(from_version="1.4.1"))
        self.assertFalse((self.root / ".claude" / "hooks" / "pycache-cleanup.py").exists())
        self.assertTrue(self._report_path().exists())

    def test_no_report_written_when_no_work_done(self):
        """AC-11: pre-1.5.0 from_version but already-clean state → no report."""
        # No agent docs, no claude/hooks, no settings.json
        self.ext.post_extract(self._ctx(from_version="1.4.1"))
        self.assertFalse(self._report_path().exists())

    def test_report_lists_all_three_migration_sections(self):
        """AC-10: report names each migration and what fired."""
        # Plant work for migrations 1, 2, 3
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "code-reviewer.md").write_text(
            "Owner: Engineering\nStatus: active\nCategory: review\n", encoding="utf-8"
        )
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        (self.root / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
            ]}}, indent=2),
            encoding="utf-8",
        )
        self.ext.post_extract(self._ctx())
        report = self._report_path().read_text(encoding="utf-8")
        self.assertIn("Role: backfill", report)
        self.assertIn("Pycache launcher cleanup", report)
        self.assertIn("settings.json pycache row removal", report)
        self.assertIn("code-reviewer.md", report)

    def test_idempotent_full_pipeline(self):
        """AC-13: a second full post_extract on an already-migrated repo
        writes no report (no work performed)."""
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "code-reviewer.md").write_text(
            "Owner: Engineering\nStatus: active\nCategory: review\n", encoding="utf-8"
        )
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        self.ext.post_extract(self._ctx())
        report_after_first = self._report_path().read_text(encoding="utf-8")
        self._report_path().unlink()  # remove first report so we can detect second-run state
        # Second run — same from_version, but state already migrated
        self.ext.post_extract(self._ctx())
        self.assertFalse(self._report_path().exists())
        # Sanity: the first report DID list the migration
        self.assertIn("code-reviewer.md", report_after_first)

    def test_exception_in_one_migration_isolated(self):
        """AC-12: a migration helper raising must not abort other migrations
        and must be recorded in the report."""
        from unittest.mock import patch
        # Plant launcher cleanup work
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("x", encoding="utf-8")
        # Patch Role: backfill to raise
        with patch.object(
            self.ext, "_backfill_role_field_on_agent_docs",
            side_effect=RuntimeError("synthetic failure"),
        ):
            self.ext.post_extract(self._ctx())
        # Pycache launcher migration still ran
        self.assertFalse((self.root / ".claude" / "hooks" / "pycache-cleanup.py").exists())
        # Report captures both: ERROR for backfill, success for cleanup
        report = self._report_path().read_text(encoding="utf-8")
        self.assertIn("ERROR", report)
        self.assertIn("synthetic failure", report)
        self.assertIn("pycache-cleanup.py", report)


# ---------------------------------------------------------------------------
# Wave 1p3b9 (1p3b6): migration preview helpers + post_extract dry-run branch
# ---------------------------------------------------------------------------


class RoleBackfillPreviewTests(unittest.TestCase):
    """AC-2: `_preview_role_field_backfill` reports planned actions without
    mutating files."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "specialists").mkdir(parents=True)
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_empty_when_no_agent_docs(self):
        self.assertEqual(self.ext._preview_role_field_backfill(self.root), [])

    def test_reports_planned_role_insertion_without_mutating(self):
        path = self.root / "docs" / "agents" / "code-reviewer.md"
        original = (
            "# Code Reviewer\n\n"
            "Owner: Engineering\n"
            "Status: active\n"
            "Category: review\n\n## Identity\n\nReviews.\n"
        )
        path.write_text(original, encoding="utf-8")
        planned = self.ext._preview_role_field_backfill(self.root)
        self.assertEqual(len(planned), 1)
        self.assertIn("code-reviewer.md", planned[0])
        self.assertIn("Role: code-reviewer", planned[0])
        # File content unchanged
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_already_present_role_not_planned(self):
        path = self.root / "docs" / "agents" / "existing.md"
        path.write_text(
            "Owner: Engineering\nStatus: active\nRole: existing\nCategory: review\n",
            encoding="utf-8",
        )
        self.assertEqual(self.ext._preview_role_field_backfill(self.root), [])

    def test_journals_subdir_not_walked(self):
        path = self.root / "docs" / "agents" / "journals" / "wave-coordinator.md"
        path.write_text("Owner: x\nStatus: active\n", encoding="utf-8")
        self.assertEqual(self.ext._preview_role_field_backfill(self.root), [])


class PycacheLauncherDeletionPreviewTests(unittest.TestCase):
    """AC-3: `_preview_pycache_launcher_deletion` reports planned deletes
    without removing files."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".claude" / "hooks").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_empty_when_no_launchers(self):
        self.assertEqual(self.ext._preview_pycache_launcher_deletion(self.root), [])

    def test_reports_planned_deletes_without_mutating(self):
        for name in ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd"):
            (self.root / ".claude" / "hooks" / name).write_text("legacy\n", encoding="utf-8")
        planned = self.ext._preview_pycache_launcher_deletion(self.root)
        self.assertEqual(len(planned), 3)
        for name in ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd"):
            self.assertTrue((self.root / ".claude" / "hooks" / name).exists())


class SettingsPycacheStripPreviewTests(unittest.TestCase):
    """AC-4: `_preview_settings_pycache_strip` describes the row that would
    be stripped without rewriting the JSON."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.settings_path = self.root / ".claude" / "settings.json"
        self.settings_path.parent.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_none_when_no_settings_file(self):
        self.assertIsNone(self.ext._preview_settings_pycache_strip(self.root))

    def test_returns_none_when_no_pycache_row(self):
        self.settings_path.write_text(
            json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Edit|Write",
                 "hooks": [{"type": "command", "command": ".claude/hooks/post-edit"}]},
            ]}}, indent=2),
            encoding="utf-8",
        )
        original = self.settings_path.read_text(encoding="utf-8")
        self.assertIsNone(self.ext._preview_settings_pycache_strip(self.root))
        # File unchanged
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), original)

    def test_describes_planned_strip_without_mutating(self):
        body = {"hooks": {"PostToolUse": [
            {"matcher": "Bash",
             "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
        ]}}
        self.settings_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
        original = self.settings_path.read_text(encoding="utf-8")
        result = self.ext._preview_settings_pycache_strip(self.root)
        self.assertIsNotNone(result)
        self.assertEqual(result["matcher"], "Bash")
        self.assertIn("pycache-cleanup", result["command"])
        self.assertEqual(result["file"], ".claude/settings.json")
        # File unchanged
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), original)


class PostExtractDryRunBranchTests(unittest.TestCase):
    """AC-1, AC-5, AC-6, AC-8, AC-9: post_extract's dry-run branch produces
    a preview-log to a distinct filename and performs zero mutations."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def _ctx(self, from_version="1.4.1+p347", dry_run=False):
        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.from_version = from_version
        ctx.to_version = "1.5.0"
        ctx.zip_path = None
        ctx.yes = True
        ctx.dry_run = dry_run
        return ctx

    def _preview_log(self) -> Path:
        return self.root / ".wavefoundry" / "logs" / "upgrade-migration-1.5.0.preview.log"

    def _real_log(self) -> Path:
        return self.root / ".wavefoundry" / "logs" / "upgrade-migration-1.5.0.log"

    def test_dry_run_uses_distinct_filename_from_real_run(self):
        """AC-6: preview log filename must differ from real-run log so a
        subsequent real run doesn't shadow the preview."""
        self.assertNotEqual(self._preview_log().name, self._real_log().name)

    def test_dry_run_writes_preview_log_when_actions_planned(self):
        """AC-5, AC-9: with planned actions present, dry-run writes the
        preview log AND does not write the real-run log."""
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "code-reviewer.md").write_text(
            "Owner: x\nStatus: active\nCategory: review\n", encoding="utf-8",
        )
        self.ext.post_extract(self._ctx(dry_run=True))
        self.assertTrue(self._preview_log().exists())
        self.assertFalse(self._real_log().exists())
        text = self._preview_log().read_text(encoding="utf-8")
        self.assertIn("PREVIEW", text)
        self.assertIn("code-reviewer", text)

    def test_dry_run_zero_mutations(self):
        """AC-8: dry-run never touches the consumer files."""
        (self.root / "docs" / "agents").mkdir(parents=True)
        agent_path = self.root / "docs" / "agents" / "code-reviewer.md"
        agent_path.write_text(
            "Owner: x\nStatus: active\nCategory: review\n", encoding="utf-8",
        )
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        launcher_path = self.root / ".claude" / "hooks" / "pycache-cleanup.py"
        launcher_path.write_text("legacy\n", encoding="utf-8")
        agent_before = agent_path.read_text(encoding="utf-8")
        launcher_before = launcher_path.read_text(encoding="utf-8")
        self.ext.post_extract(self._ctx(dry_run=True))
        # No mutations to either file
        self.assertEqual(agent_path.read_text(encoding="utf-8"), agent_before)
        self.assertEqual(launcher_path.read_text(encoding="utf-8"), launcher_before)

    def test_dry_run_with_no_planned_actions_writes_no_preview_log(self):
        """When the consumer state has nothing to migrate, no preview log
        is written (parallels the real-run behavior)."""
        self.ext.post_extract(self._ctx(dry_run=True))
        self.assertFalse(self._preview_log().exists())

    def test_dry_run_respects_version_gate(self):
        """Same version-gate behavior as the real run: if from_version is
        already at the cutoff, neither preview nor real-run path fires."""
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "code-reviewer.md").write_text(
            "Owner: x\nStatus: active\nCategory: review\n", encoding="utf-8",
        )
        self.ext.post_extract(self._ctx(from_version="1.5.0", dry_run=True))
        self.assertFalse(self._preview_log().exists())


class ChunkerVersionBumpDetectionTests(unittest.TestCase):
    """Wave 1p3dk / 1p3ho: chunker-version-aware upgrade routing.

    Closes the field failure mode where 1.5.0's CHUNKER_VERSION bump didn't
    trigger a project-index rebuild because `indexer.build_index`'s internal
    auto-escalate was silent (no operator-visible decision log) and the
    upgrade reported success without verifying the rebuild ran."""

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Stand up the directory structure used by the helpers
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        (self.root / ".wavefoundry" / "framework" / "scripts").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_meta(self, content: dict) -> None:
        (self.root / ".wavefoundry" / "index" / "meta.json").write_text(
            json.dumps(content), encoding="utf-8",
        )

    def _write_chunker(self, version: str) -> None:
        (self.root / ".wavefoundry" / "framework" / "scripts" / "chunker.py").write_text(
            f'# stub chunker\nCHUNKER_VERSION = "{version}"\nMAX_DOC_CHUNK_CHARS = 2000\n',
            encoding="utf-8",
        )

    def test_snapshot_reads_per_layer_dict(self) -> None:
        """AC-2: pre-extract snapshot reads `chunker_versions` per-layer dict."""
        self._write_meta({"chunker_versions": {"docs": "22", "code": "22"}})
        snap = self.mod._snapshot_pre_extract_chunker_versions(self.root)
        self.assertEqual(snap, {"docs": "22", "code": "22"})

    def test_snapshot_falls_back_to_legacy_scalar(self) -> None:
        """AC-13: legacy `chunker_version` scalar key is mapped to per-layer dict."""
        self._write_meta({"chunker_version": "21"})
        snap = self.mod._snapshot_pre_extract_chunker_versions(self.root)
        self.assertEqual(snap, {"docs": "21", "code": "21"})

    def test_snapshot_empty_when_meta_absent(self) -> None:
        """Fresh install with no prior meta.json → empty snapshot, no bump detection."""
        snap = self.mod._snapshot_pre_extract_chunker_versions(self.root)
        self.assertEqual(snap, {})

    def test_read_chunker_version_from_pack(self) -> None:
        """AC-3: post-extract version read via regex (no Python import)."""
        self._write_chunker("23")
        self.assertEqual(self.mod._read_chunker_version_from_pack(self.root), "23")

    def test_read_chunker_version_empty_when_chunker_missing(self) -> None:
        """Defensive: missing chunker.py → empty string → no bump detection."""
        self.assertEqual(self.mod._read_chunker_version_from_pack(self.root), "")

    def test_detect_bump_when_versions_differ(self) -> None:
        """AC-4: bump detected when old != new and both are non-empty."""
        bumped, transition = self.mod._detect_chunker_version_bump(
            {"docs": "22", "code": "22"}, "23",
        )
        self.assertTrue(bumped)
        self.assertEqual(transition, ("22", "23"))

    def test_no_bump_when_versions_match(self) -> None:
        """AC-12: bump NOT detected when old == new (regression guard for the
        unchanged path — incremental update path stays default when no bump)."""
        bumped, transition = self.mod._detect_chunker_version_bump(
            {"docs": "23", "code": "23"}, "23",
        )
        self.assertFalse(bumped)
        self.assertIsNone(transition)

    def test_no_bump_on_fresh_install(self) -> None:
        """AC-9: empty pre-extract dict → no bump (no comparison baseline)."""
        bumped, transition = self.mod._detect_chunker_version_bump({}, "23")
        self.assertFalse(bumped)
        self.assertIsNone(transition)

    def test_no_bump_when_new_version_unreadable(self) -> None:
        """Defensive: empty new version (chunker.py couldn't be read) → no bump."""
        bumped, transition = self.mod._detect_chunker_version_bump(
            {"docs": "22", "code": "22"}, "",
        )
        self.assertFalse(bumped)
        self.assertIsNone(transition)

    def test_legacy_scalar_bump_detected(self) -> None:
        """AC-13: legacy `chunker_version` scalar correctly triggers bump detection
        when the new version differs."""
        self._write_meta({"chunker_version": "20"})
        snap = self.mod._snapshot_pre_extract_chunker_versions(self.root)
        bumped, transition = self.mod._detect_chunker_version_bump(snap, "23")
        self.assertTrue(bumped)
        self.assertEqual(transition, ("20", "23"))

    def test_verify_succeeds_when_meta_matches_new_version(self) -> None:
        """AC-7: post-rebuild verification confirms the new chunker version is
        recorded in the index meta.json."""
        self._write_chunker("23")
        self._write_meta({"chunker_versions": {"docs": "23", "code": "23"}})
        self.assertTrue(self.mod._verify_chunker_rebuild_succeeded(self.root))

    def test_verify_fails_when_meta_still_stale(self) -> None:
        """AC-8: post-rebuild verification detects stale meta.json — the
        rebuild failed silently and the upgrade must surface this as a
        fail-loud actionable error."""
        self._write_chunker("23")
        self._write_meta({"chunker_versions": {"docs": "22", "code": "22"}})
        self.assertFalse(self.mod._verify_chunker_rebuild_succeeded(self.root))

    def test_verify_conservative_when_no_meta(self) -> None:
        """When meta.json doesn't exist post-rebuild, verification returns True
        (don't block the upgrade on a verification-tooling failure)."""
        self._write_chunker("23")
        # No meta.json at all
        self.assertTrue(self.mod._verify_chunker_rebuild_succeeded(self.root))


class MultiVersionTransitionDetectionTests(unittest.TestCase):
    """Wave 1p3dk / 1p3ho v2: detect chunker + walker + graph_builder
    transitions and log them. The indexer's auto-escalate handles the
    rebuild; the upgrade flow just surfaces the transitions for operator
    visibility."""

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry" / "index" / "graph").mkdir(parents=True)
        (self.root / ".wavefoundry" / "framework" / "scripts").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_pack(self, chunker: str, walker: str, graph_builder: str) -> None:
        """Plant version constants in the extracted-pack location."""
        scripts = self.root / ".wavefoundry" / "framework" / "scripts"
        (scripts / "chunker.py").write_text(
            f'CHUNKER_VERSION = "{chunker}"\n', encoding="utf-8",
        )
        (scripts / "indexer.py").write_text(
            f'WALKER_VERSION = "{walker}"\n', encoding="utf-8",
        )
        (scripts / "graph_indexer.py").write_text(
            f'GRAPH_BUILDER_VERSION = "{graph_builder}"\n', encoding="utf-8",
        )

    def _write_meta(self, content: dict) -> None:
        (self.root / ".wavefoundry" / "index" / "meta.json").write_text(
            json.dumps(content), encoding="utf-8",
        )

    def _write_graph_state(self, content: dict) -> None:
        # Wave 1rvfx: the installed graph state lives in the REAL project graph dir — the legacy JSON
        # fallback path (pre-1p9q2 repos / the reader's fallback branch). The sqlite primary path is
        # exercised by _write_graph_state_sqlite + test_snapshot_reads_sqlite_graph_state.
        (self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.json").write_text(
            json.dumps(content), encoding="utf-8",
        )

    def _write_graph_state_sqlite(self, builder_version: str) -> None:
        # Wave 1rvfx: write the PRIMARY project graph state — the SQLite store's meta table — matching
        # the production shape read by _read_installed_graph_builder_version.
        import sqlite3
        store = self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.sqlite"
        conn = sqlite3.connect(str(store))
        try:
            conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO meta (key, value) VALUES ('builder_version', ?)", (builder_version,))
            conn.commit()
        finally:
            conn.close()

    def test_read_walker_version(self) -> None:
        self._write_pack("24", "6", "23")
        self.assertEqual(self.mod._read_walker_version_from_pack(self.root), "6")

    def test_read_graph_builder_version(self) -> None:
        self._write_pack("24", "6", "24")
        self.assertEqual(self.mod._read_graph_builder_version_from_pack(self.root), "24")

    def test_snapshot_collects_all_version_constants(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "22", "code": "22"},
            "walker_version": "4",
        })
        self._write_graph_state({"builder_version": "22"})
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        self.assertEqual(snap["chunker_docs"], "22")
        self.assertEqual(snap["chunker_code"], "22")
        self.assertEqual(snap["walker"], "4")
        self.assertEqual(snap["graph_builder"], "22")

    def test_snapshot_reads_sqlite_graph_state(self) -> None:
        # Wave 1rvfx AC-1: the PRIMARY read path — the installed project graph SQLite store's meta table.
        self._write_graph_state_sqlite("42")
        self._write_pack("24", "5", "43")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        self.assertEqual(snap["graph_builder"], "42")
        transitions = self.mod._detect_version_transitions(snap, self.root)
        self.assertTrue(any("GRAPH_BUILDER_VERSION" in name for name, _, _ in transitions))

    def test_snapshot_sqlite_takes_precedence_over_legacy_json(self) -> None:
        # Wave 1rvfx: when both exist, the SQLite store wins (mirrors read_state_builder_version).
        self._write_graph_state_sqlite("42")
        self._write_graph_state({"builder_version": "40"})  # legacy JSON present but superseded
        self.assertEqual(self.mod._read_installed_graph_builder_version(self.root), "42")

    def test_snapshot_graph_builder_absent_is_fail_safe(self) -> None:
        # Wave 1rvfx AC-3: no installed project graph state → no graph_builder key, no GRAPH_BUILDER_VERSION
        # transition, and NO exception (the upgrade must proceed).
        self._write_pack("24", "5", "43")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        self.assertNotIn("graph_builder", snap)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        self.assertFalse(any("GRAPH_BUILDER_VERSION" in name for name, _, _ in transitions))

    def test_snapshot_graph_builder_corrupt_store_is_fail_safe(self) -> None:
        # Wave 1rvfx AC-3: a corrupt/unreadable SQLite store yields no entry and never raises.
        store = self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.sqlite"
        store.write_text("this is not a sqlite database", encoding="utf-8")
        self.assertEqual(self.mod._read_installed_graph_builder_version(self.root), "")

    def test_detect_chunker_transition(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "22", "code": "22"},
            "walker_version": "5",
        })
        self._write_graph_state({"builder_version": "23"})
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        # Two chunker transitions (docs + code), no walker, no graph
        names = [name for name, _, _ in transitions]
        self.assertTrue(any("CHUNKER_VERSION (docs index)" in n for n in names))
        self.assertTrue(any("CHUNKER_VERSION (code index)" in n for n in names))
        self.assertFalse(any("WALKER" in n for n in names))
        self.assertFalse(any("GRAPH" in n for n in names))

    def test_detect_walker_transition(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "24", "code": "24"},
            "walker_version": "4",
        })
        self._write_graph_state({"builder_version": "23"})
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        names = [name for name, _, _ in transitions]
        self.assertTrue(any("WALKER_VERSION" in n for n in names))
        for name, old, new in transitions:
            if "WALKER" in name:
                self.assertEqual((old, new), ("4", "5"))

    def test_detect_graph_builder_transition(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "24", "code": "24"},
            "walker_version": "5",
        })
        self._write_graph_state({"builder_version": "22"})
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        names = [name for name, _, _ in transitions]
        self.assertTrue(any("GRAPH_BUILDER_VERSION" in n for n in names))

    def test_no_transitions_when_everything_matches(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "24", "code": "24"},
            "walker_version": "5",
        })
        self._write_graph_state({"builder_version": "23"})
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        self.assertEqual(transitions, [])

    def test_no_transitions_on_fresh_install(self) -> None:
        """No pre-existing meta or graph state → no transitions detected."""
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        self.assertEqual(transitions, [])


class RemoveRootBootstrapFileTests(unittest.TestCase):
    """Wave 1rxyi: the upgrade removes the re-dropped root install-wavefoundry.md (fail-safe).

    The zip ships that single-use bootstrap file at the zip root by design, so every extract re-drops it
    at the project root and prune (MANIFEST-scoped to .wavefoundry/framework/) never removes it."""

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_removes_present_bootstrap_file(self) -> None:
        # AC-1: a present root install-wavefoundry.md is deleted.
        f = self.root / "install-wavefoundry.md"
        f.write_text("bootstrap instructions", encoding="utf-8")
        self.mod._remove_root_bootstrap_file(self.root)
        self.assertFalse(f.exists(), "the root bootstrap file must be removed")

    def test_absent_is_noop(self) -> None:
        # AC-2: no file present → no-op, no exception.
        self.mod._remove_root_bootstrap_file(self.root)  # must not raise
        self.assertFalse((self.root / "install-wavefoundry.md").exists())

    def test_unlink_error_is_swallowed(self) -> None:
        # AC-2: a failed unlink is logged and swallowed — the upgrade must never abort over cleanup.
        f = self.root / "install-wavefoundry.md"
        f.write_text("x", encoding="utf-8")
        with patch.object(self.mod.Path, "unlink", side_effect=OSError("boom")):
            self.mod._remove_root_bootstrap_file(self.root)  # must not raise

    def test_only_touches_the_reserved_bootstrap_name(self) -> None:
        # A same-directory unrelated file is never touched — only the framework-reserved name is removed.
        other = self.root / "README.md"
        other.write_text("project readme", encoding="utf-8")
        (self.root / "install-wavefoundry.md").write_text("bootstrap", encoding="utf-8")
        self.mod._remove_root_bootstrap_file(self.root)
        self.assertTrue(other.exists(), "unrelated root files must be left untouched")
        self.assertFalse((self.root / "install-wavefoundry.md").exists())

    def test_extract_phase_wires_the_cleanup_after_extractall(self) -> None:
        # F1 (delivery review): lock the wiring — the upgrade extract phase must CALL
        # `_remove_root_bootstrap_file(root)` AFTER `zf.extractall`, so a refactor that drops the call is
        # caught. The helper is otherwise only unit-tested and the full apply path has no test harness
        # (main() is only reachable in the suite via --resume-after-gate / --materialize-lifecycle-policy,
        # neither of which reaches the extract block).
        import inspect
        src = inspect.getsource(self.mod)
        self.assertIn("_remove_root_bootstrap_file(root)", src, "the cleanup call must be wired in")
        extract_pos = src.index("zf.extractall")
        call_pos = src.index("_remove_root_bootstrap_file(root)")  # the call (def line reads `(root: Path)`)
        self.assertGreater(
            call_pos, extract_pos,
            "the bootstrap cleanup must run AFTER zf.extractall in the extract phase",
        )


class UpgradeContextChunkerFieldsTests(unittest.TestCase):
    """AC-1: UpgradeContext gains the three chunker-version transition fields."""

    def setUp(self) -> None:
        self.mod = load_upgrade_module()

    def test_default_chunker_fields_preserve_existing_behavior(self) -> None:
        ctx = self.mod.UpgradeContext(
            root=Path("/tmp/fake"),
            from_version=None, to_version=None,
            zip_path=None, yes=False,
        )
        self.assertEqual(ctx.pre_extract_chunker_versions, {})
        self.assertFalse(ctx.chunker_version_bumped)
        self.assertIsNone(ctx.chunker_version_transition)


class BackgroundCodeIncompleteWarningTests(unittest.TestCase):
    """H1 (Phase 4b reliability): cleanup warns when the background code re-embed left the code layer
    behind the docs layer (the silent-failure case the JS/TS team hit on p4g3/p4su)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _meta(self, docs, code):
        (self.root / ".wavefoundry" / "index" / "meta.json").write_text(
            json.dumps({"chunker_versions": {"docs": docs, "code": code}}), encoding="utf-8")

    def _run_capturing(self):
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lambda *a: lines.append(" ".join(str(x) for x in a))):
            self.mod._warn_if_background_code_incomplete(self.root)
        return lines

    def test_warns_on_chunker_mismatch(self):
        self._meta("29", "28")
        self.assertTrue(any("BEHIND" in ln for ln in self._run_capturing()))

    def test_silent_when_versions_match(self):
        self._meta("29", "29")
        self.assertFalse(any("BEHIND" in ln for ln in self._run_capturing()))

    def test_silent_when_meta_absent(self):
        self.assertEqual(self._run_capturing(), [])  # no meta.json → no warning, no crash


class UpgradeFloorAndMigrationSurfacingTests(unittest.TestCase):
    """1p5do: upgrade floor (warn, not abort), migration-log ERROR surfacing, and the
    empty-version-baseline rebuild signal."""

    def setUp(self):
        self.mod = load_upgrade_module()
        # _below_upgrade_floor does a call-time `from check_version import ...` (a sibling script);
        # ensure the scripts dir is importable when this test runs standalone.
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _capture(self, fn, *args):
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lambda *a: lines.append(" ".join(str(x) for x in a))):
            fn(*args)
        return lines

    # AC-1 — floor is a warn at 1.4.0, never fires for >= 1.4.0, fires for below + unparseable.
    def test_below_floor_predicate(self):
        self.assertEqual(self.mod.SUPPORTED_UPGRADE_FLOOR, "1.4.0")
        for below in ("1.3.0", "0.9.0", "not-a-version", ""):
            self.assertTrue(self.mod._below_upgrade_floor(below), below)
        for ok in ("1.4.0", "1.5.1", "1.6.0", "1.5.0+p4uw"):
            self.assertFalse(self.mod._below_upgrade_floor(ok), ok)

    # AC-3 — empty snapshot + index present → rebuild signal; otherwise silent.
    def test_no_version_baseline_warns_when_index_exists(self):
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        lines = self._capture(self.mod._warn_if_no_version_baseline, {}, self.root)
        self.assertTrue(any("No framework version baseline" in ln for ln in lines))

    def test_no_version_baseline_silent_when_baseline_present(self):
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        self.assertEqual(self._capture(self.mod._warn_if_no_version_baseline, {"graph_builder": "30"}, self.root), [])

    def test_no_version_baseline_silent_when_no_index(self):
        self.assertEqual(self._capture(self.mod._warn_if_no_version_baseline, {}, self.root), [])

    # AC-2 — migration-log ERROR surfacing (real logs only, not .preview).
    def _logs_dir(self):
        d = self.root / ".wavefoundry" / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_migration_errors_surface(self):
        (self._logs_dir() / "upgrade-migration-1.5.0.log").write_text("ok\nERROR: Role backfill failed\n", encoding="utf-8")
        self.assertTrue(any("ERROR entries" in ln for ln in self._capture(self.mod._warn_if_migration_errors, self.root)))

    def test_migration_clean_log_silent(self):
        (self._logs_dir() / "upgrade-convergence-migration.log").write_text("renamed wave_execution -> wave_implement\n", encoding="utf-8")
        self.assertEqual(self._capture(self.mod._warn_if_migration_errors, self.root), [])

    def test_migration_preview_log_ignored(self):
        (self._logs_dir() / "upgrade-migration-1.5.0.preview.log").write_text("ERROR: would fail\n", encoding="utf-8")
        self.assertEqual(self._capture(self.mod._warn_if_migration_errors, self.root), [])

    # 1p5ik — remove the deprecated framework/index/ that manifest-prune can't.
    def test_removes_deprecated_framework_index(self):
        fidx = self.root / ".wavefoundry" / "framework" / "index"
        (fidx / "docs.lance").mkdir(parents=True)
        (fidx / "meta.json").write_text("{}", encoding="utf-8")
        with patch.object(self.mod, "_log", side_effect=lambda *a: None):
            removed = self.mod._remove_deprecated_framework_index(self.root)
        self.assertTrue(removed)
        self.assertFalse(fidx.exists(), "stale framework/index/ must be removed")

    def test_remove_framework_index_absent_is_noop(self):
        with patch.object(self.mod, "_log", side_effect=lambda *a: None):
            removed = self.mod._remove_deprecated_framework_index(self.root)
        self.assertFalse(removed)  # absent → False, no error


class ConvergenceParseWarningTests(unittest.TestCase):
    """1p5do (AC-4): a malformed workflow-config.json makes the convergence migration WARN rather
    than no-op silently, so a later docs-gate failure is connectable to the un-migrated config."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("upgrade_extensions", SCRIPTS_ROOT / "upgrade_extensions.py")
        self.ext = importlib.util.module_from_spec(spec)
        sys.modules["upgrade_extensions"] = self.ext
        spec.loader.exec_module(self.ext)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_malformed_config_warns_and_noops(self):
        (self.root / "docs" / "workflow-config.json").write_text("{ this is not valid json", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(result, [])
        self.assertIn("WARNING", err.getvalue())
        self.assertIn("could not read/parse", err.getvalue())

    def test_valid_config_no_warning(self):
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps({"wave_implement": "x"}), encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.ext._rewrite_legacy_config_keys(self.root)
        self.assertNotIn("WARNING", err.getvalue())


class ConfigReviewRecommendationTests(unittest.TestCase):
    """Wave 1p5tk: the config-review recommendation is surfaced on every major/minor
    upgrade (stateless), silent on patch/downgrade/same, and fully fail-safe."""

    def setUp(self):
        # `_is_major_or_minor_upgrade` does `from check_version import _to_version`
        # at call time; make sure the scripts dir is importable.
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def test_minor_bump_recommends(self):
        lines = self.mod._config_review_recommendation_lines("1.5.0", "1.6.0")
        self.assertTrue(lines)
        self.assertTrue(any("framework-config-review.prompt.md" in ln for ln in lines))

    def test_major_bump_recommends(self):
        lines = self.mod._config_review_recommendation_lines("1.6.0", "2.0.0")
        self.assertTrue(lines)

    def test_build_suffix_stripped_minor_recommends(self):
        lines = self.mod._config_review_recommendation_lines("1.5.0+abc", "1.6.0+def")
        self.assertTrue(lines)

    def test_patch_bump_silent(self):
        self.assertEqual(self.mod._config_review_recommendation_lines("1.6.0", "1.6.1"), [])

    def test_same_version_silent(self):
        self.assertEqual(self.mod._config_review_recommendation_lines("1.6.0", "1.6.0"), [])

    def test_downgrade_silent(self):
        self.assertEqual(self.mod._config_review_recommendation_lines("1.6.0", "1.5.0"), [])

    def test_unparseable_is_silent_not_fatal(self):
        self.assertEqual(self.mod._config_review_recommendation_lines("garbage", "1.6.0"), [])

    def test_missing_version_silent(self):
        self.assertEqual(self.mod._config_review_recommendation_lines(None, "1.6.0"), [])
        self.assertEqual(self.mod._config_review_recommendation_lines("1.6.0", None), [])

    def test_is_major_or_minor_classification(self):
        self.assertTrue(self.mod._is_major_or_minor_upgrade("1.5.0", "1.6.0"))
        self.assertTrue(self.mod._is_major_or_minor_upgrade("1.6.0", "2.0.0"))
        self.assertFalse(self.mod._is_major_or_minor_upgrade("1.6.0", "1.6.1"))
        self.assertFalse(self.mod._is_major_or_minor_upgrade("1.6.0", "1.6.0"))


class ReconciliationRecommendationTests(unittest.TestCase):
    """Wave 1p7ww / 1p8et / 1p8kz: the reconciliation scan line runs on EVERY upgrade — operator
    direction (a patch or a same-version build-successor can change/retire a surface during testing).
    Unlike its sibling ``_config_review_recommendation_lines`` (still major/minor-gated), it is NOT
    gated on version delta; it returns [] only on an internal failure. Report-only; fail-safe."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def test_minor_bump_recommends(self):
        # Wave 1p8et: the recommend-only prose was replaced by the actionable scan; the heading is
        # now "Reconciliation scan". With no findings supplied it still emits the heading + a
        # "no stale references" line so the operator sees the scan ran.
        lines = self.mod._reconciliation_recommendation_lines("1.5.0", "1.6.0")
        self.assertTrue(lines)
        self.assertTrue(any("Reconciliation scan" in ln for ln in lines))
        # Names the concrete 1.9.0 bin/* -> wf retirement example.
        self.assertTrue(any("`wf`" in ln or "bin/" in ln for ln in lines))

    def test_findings_render_actionable_file_line_suggested(self):
        # Wave 1p8et: when findings are supplied, the actionable file:line → suggested list is emitted.
        # The printed reference is the finding's `matched` text (INV-recline), not a synthesized form.
        findings = [
            {"file": "docs/x.md", "line": 7, "retired_surface": "docs-lint",
             "matched": ".wavefoundry/bin/docs-lint", "suggested": "wf docs-lint"},
        ]
        lines = self.mod._reconciliation_recommendation_lines("1.5.0", "1.6.0", findings)
        joined = "\n".join(lines)
        self.assertIn("docs/x.md:7", joined)
        self.assertIn(".wavefoundry/bin/docs-lint", joined)
        self.assertIn("wf docs-lint", joined)

    def test_findings_print_matched_text_for_py_join(self):
        # INV-recline: a .py-join finding prints its actual matched text, not `.wavefoundry/bin/<name>`.
        findings = [
            {"file": "s.py", "line": 3, "retired_surface": "wave-gate",
             "matched": 'bin_dir / "wave-gate"', "suggested": "wf gate"},
        ]
        lines = self.mod._reconciliation_recommendation_lines("1.5.0", "1.6.0", findings)
        joined = "\n".join(lines)
        self.assertIn('bin_dir / "wave-gate"', joined)
        self.assertNotIn(".wavefoundry/bin/wave-gate", joined)
        self.assertIn("wf gate", joined)

    def test_major_bump_recommends(self):
        self.assertTrue(self.mod._reconciliation_recommendation_lines("1.6.0", "2.0.0"))

    def test_build_suffix_stripped_minor_recommends(self):
        self.assertTrue(self.mod._reconciliation_recommendation_lines("1.5.0+abc", "1.6.0+def"))

    def test_patch_bump_runs(self):
        # 1p8kz: a patch bump now RUNS the scan (gate removed) — emits the heading.
        lines = self.mod._reconciliation_recommendation_lines("1.6.0", "1.6.1")
        self.assertTrue(any("Reconciliation scan" in ln for ln in lines))

    def test_same_version_build_successor_runs(self):
        # 1p8kz: a same-version build-successor (a rebuilt pack during testing) also runs the scan.
        lines = self.mod._reconciliation_recommendation_lines("1.6.0", "1.6.0")
        self.assertTrue(any("Reconciliation scan" in ln for ln in lines))

    def test_downgrade_runs(self):
        # 1p8kz: report-only scan runs on any upgrade run, including a version rollback during testing.
        lines = self.mod._reconciliation_recommendation_lines("1.6.0", "1.5.0")
        self.assertTrue(any("Reconciliation scan" in ln for ln in lines))

    def test_findings_supplied_render_regardless_of_version_delta(self):
        # 1p8kz: with findings supplied, the actionable list renders on a PATCH bump too (no gate).
        findings = [{"file": "d.md", "line": 2, "retired_surface": "wave-gate",
                     "matched": ".wavefoundry/bin/wave-gate", "suggested": "wf gate"}]
        lines = self.mod._reconciliation_recommendation_lines("1.6.0", "1.6.1", findings)
        joined = "\n".join(lines)
        self.assertIn("d.md:2", joined)
        self.assertIn("wf gate", joined)

    def _capture_summary(self, from_version, to_version):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version=from_version,
                to_version=to_version,
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                failed_phase=None,
            )
        return buf.getvalue()

    def test_reconciliation_line_wired_into_operator_summary_on_minor_bump(self):
        # Wave 1p7ww review: the GATE was tested but the WIRING into _print_operator_summary was not.
        # Wave 1p8et: heading is now "Reconciliation scan".
        out = self._capture_summary("1.5.0", "1.6.0")
        self.assertIn("Reconciliation scan", out)
        # Sibling config-review line is also present on the same gate.
        self.assertIn("Config review recommended", out)

    def test_reconciliation_line_present_in_summary_on_patch_bump(self):
        # 1p8kz: the reconciliation scan line now appears on a PATCH bump (gate removed). The sibling
        # Config-review line stays major/minor-gated, so it is correctly ABSENT on a patch bump.
        out = self._capture_summary("1.6.0", "1.6.1")
        self.assertIn("Reconciliation scan", out)
        self.assertNotIn("Config review recommended", out)

    def test_reconciliation_line_absent_in_summary_on_failed_phase(self):
        # Recommendations are suppressed when the upgrade failed mid-phase.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=False, failed_phase="docs_gate",
            )
        self.assertNotIn("Reconciliation scan", buf.getvalue())


class ReconciliationScanIntegrationTests(unittest.TestCase):
    """Wave 1p8et: _print_operator_summary RUNS the shipped scan on a major/minor bump when a real
    root is supplied, and surfaces the actionable file:line → suggested list (report-only)."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def _summary_over_root(self, root, from_v="1.5.0", to_v="1.6.0", failed_phase=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version=from_v, to_version=to_v, zip_path=None,
                pruned_count=0, ran_index_rebuild=True,
                failed_phase=failed_phase, root=Path(root),
            )
        return buf.getvalue()

    def test_scan_surfaces_actionable_finding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs").mkdir()
            (root / "docs" / "runbook.md").write_text(
                "Run `.wavefoundry/bin/docs-lint` to lint.\n", encoding="utf-8"
            )
            out = self._summary_over_root(root)
            self.assertIn("docs/runbook.md:1", out)
            self.assertIn(".wavefoundry/bin/docs-lint", out)
            self.assertIn("wf docs-lint", out)

    def test_scan_runs_on_patch_bump(self):
        # 1p8kz (operator direction): the scan runs on a PATCH bump too and surfaces the actionable
        # finding (a patch can change/retire a surface during testing).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "x.md").write_text("`.wavefoundry/bin/docs-lint`\n", encoding="utf-8")
            out = self._summary_over_root(root, from_v="1.6.0", to_v="1.6.1")
            self.assertIn("Reconciliation scan", out)
            self.assertIn("x.md:1", out)
            self.assertIn("wf docs-lint", out)

    def test_scan_skipped_when_root_none(self):
        # Back-compat: no root → no scan, no exception, summary still renders.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=True,
            )
        out = buf.getvalue()
        self.assertIn("Reconciliation scan", out)
        self.assertIn("No stale retired-surface references found", out)

    def test_run_reconciliation_scan_is_fail_safe(self):
        # A bad root must not raise — returns ([], []) (1p8o5: two channels).
        self.assertEqual(self.mod._run_reconciliation_scan(None), ([], []))


class UpgradeSummarySentinelTests(unittest.TestCase):
    """Wave 1p8eu: the operator summary is built ONCE as a dict and emitted both as prose and a
    machine-readable WAVE_UPGRADE_SUMMARY_JSON: sentinel line, rendered from the one dict."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def _capture(self, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(**kwargs)
        return buf.getvalue()

    def _parse_sentinel(self, out):
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        for line in out.splitlines():
            if line.startswith(sentinel):
                return json.loads(line[len(sentinel):])
        return None

    def test_sentinel_line_present_with_all_fields(self):
        out = self._capture(
            from_version="1.5.0", to_version="1.6.0", zip_path=None,
            pruned_count=4, ran_index_rebuild=True, failed_phase=None,
        )
        summary = self._parse_sentinel(out)
        self.assertIsNotNone(summary)
        for key in ("from_version", "to_version", "pruned_count", "docs_gate",
                    "index_update", "failed_phase", "is_major_or_minor", "reconciliation",
                    "host_permission_flags"):
            self.assertIn(key, summary)
        self.assertEqual(summary["from_version"], "1.5.0")
        self.assertEqual(summary["to_version"], "1.6.0")
        self.assertEqual(summary["pruned_count"], 4)
        self.assertEqual(summary["docs_gate"], "PASSED")
        self.assertTrue(summary["is_major_or_minor"])
        self.assertEqual(summary["reconciliation"], [])
        self.assertEqual(summary["host_permission_flags"], [])  # 1p8o5: additive, empty by default

    def test_sentinel_host_permission_flags_separate_from_reconciliation(self):
        # 1p8o5 #2 / AC-2: a stale ref in a host permission/allow-rule file lands in the SEPARATE
        # `host_permission_flags` summary field, NOT in `reconciliation`; an editable doc lands in
        # `reconciliation`. The summary exposes both channels distinctly.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / ".claude" / "settings.local.json").write_text(
                '{"allow": ["Bash(.wavefoundry/bin/docs-lint)"]}\n', encoding="utf-8"
            )
            (root / "docs").mkdir()
            (root / "docs" / "runbook.md").write_text(
                "Run `.wavefoundry/bin/wave-gate`.\n", encoding="utf-8"
            )
            out = self._capture(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=True, failed_phase=None, root=root,
            )
            summary = self._parse_sentinel(out)
            recon_files = {f["file"] for f in summary["reconciliation"]}
            host_files = {f["file"] for f in summary["host_permission_flags"]}
            self.assertNotIn(".claude/settings.local.json", recon_files)
            self.assertIn(".claude/settings.local.json", host_files)
            self.assertIn("docs/runbook.md", recon_files)
            self.assertNotIn("docs/runbook.md", host_files)
            # The prose carries the separate operator-flag section.
            self.assertIn("Host permission/allow-rule files (flag for the OPERATOR", out)

    def test_sentinel_reconciliation_carries_findings(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text("`.wavefoundry/bin/wave-gate`\n", encoding="utf-8")
            out = self._capture(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=True, failed_phase=None, root=root,
            )
            summary = self._parse_sentinel(out)
            self.assertEqual(len(summary["reconciliation"]), 1)
            ref = summary["reconciliation"][0]
            self.assertEqual(ref["retired_surface"], "wave-gate")
            self.assertEqual(ref["matched"], ".wavefoundry/bin/wave-gate")
            self.assertEqual(ref["suggested"], "wf gate")

    def test_sentinel_failed_phase_reflected(self):
        out = self._capture(
            from_version="1.5.0", to_version="1.6.0", zip_path=None,
            pruned_count=0, ran_index_rebuild=False, failed_phase="docs_gate",
        )
        summary = self._parse_sentinel(out)
        self.assertEqual(summary["failed_phase"], "docs_gate")
        self.assertEqual(summary["docs_gate"], "FAILED")

    def test_prose_and_sentinel_agree_on_pruned_count(self):
        out = self._capture(
            from_version="1.5.0", to_version="1.6.0", zip_path=None,
            pruned_count=7, ran_index_rebuild=True, failed_phase=None,
        )
        summary = self._parse_sentinel(out)
        self.assertIn("Files pruned:       7", out)
        self.assertEqual(summary["pruned_count"], 7)


class PrimaryPhaseSummaryTests(unittest.TestCase):
    """Wave 1p8kz: the structured summary sentinel must surface at the END of the PRIMARY upgrade phase
    (phases 0–4, the default ``wave_upgrade()`` call) — not only on ``--cleanup`` — so an agent reading
    the primary upgrade response gets ``data.summary`` WITH the 1p8et reconciliation findings. The
    field gap (1.9.5 native-Windows): no summary on the primary call, persistent manual reconcile."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def _emit_primary(self, root, from_v, to_v, pruned_count=0):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._emit_primary_phase_summary(
                from_version=from_v, to_version=to_v, zip_path=None,
                pruned_count=pruned_count, root=Path(root) if root is not None else None,
            )
        return buf.getvalue()

    def _parse_sentinel(self, out):
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        return [json.loads(line[len(sentinel):]) for line in out.splitlines() if line.startswith(sentinel)]

    def test_emits_exactly_one_sentinel_line(self):
        out = self._emit_primary(None, "1.8.0", "1.9.0")
        summaries = self._parse_sentinel(out)
        self.assertEqual(len(summaries), 1, "primary phase must emit exactly one summary sentinel")

    def test_reconciliation_populated_on_minor_bump(self):
        # AC-1: a MINOR bump (1.8.0 → 1.9.0) runs the reconciliation scan; with a real root that has a
        # retired-surface reference, the sentinel's `reconciliation` carries the finding.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text("`.wavefoundry/bin/wave-gate`\n", encoding="utf-8")
            out = self._emit_primary(root, "1.8.0", "1.9.0")
            summary = self._parse_sentinel(out)[0]
            self.assertTrue(summary["is_major_or_minor"])
            self.assertEqual(len(summary["reconciliation"]), 1)
            self.assertEqual(summary["reconciliation"][0]["retired_surface"], "wave-gate")

    def test_reconciliation_populated_via_monkeypatched_scan_on_minor_bump(self):
        # AC-1 (monkeypatched form, per the task): a minor bump with _run_reconciliation_scan stubbed
        # to return a finding must surface that finding in the primary-phase sentinel.
        finding = [{"file": "x.md", "line": 1, "retired_surface": "docs-lint",
                    "matched": ".wavefoundry/bin/docs-lint", "suggested": "wf docs-lint"}]
        # 1p8o5: _run_reconciliation_scan now returns (reconciliation, host_permission_flags).
        with patch.object(self.mod, "_run_reconciliation_scan", return_value=(finding, [])):
            out = self._emit_primary("ignored-root-uses-stub", "1.8.0", "1.9.0")
        summary = self._parse_sentinel(out)[0]
        self.assertEqual(summary["reconciliation"], finding)

    def test_reconciliation_populated_on_patch_bump(self):
        # AC-6 (operator direction): the scan runs on EVERY upgrade — a PATCH bump (1.9.4 → 1.9.5) with
        # a retired-surface reference present DOES populate `reconciliation` (a patch can change/retire a
        # surface during testing). `is_major_or_minor` stays False (informational only — no longer gates).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text("`.wavefoundry/bin/wave-gate`\n", encoding="utf-8")
            out = self._emit_primary(root, "1.9.4", "1.9.5")
            summary = self._parse_sentinel(out)[0]
            self.assertFalse(summary["is_major_or_minor"])  # informational, not a gate
            self.assertEqual(len(summary["reconciliation"]), 1)
            self.assertEqual(summary["reconciliation"][0]["retired_surface"], "wave-gate")

    def test_scan_runs_on_patch_bump(self):
        # AC-6: a patch bump DOES invoke the scan (the major/minor gate was removed). Proven via a stub:
        # its return value now flows into the patch-bump sentinel.
        finding = [{"file": "x.md", "line": 1, "retired_surface": "docs-lint",
                    "matched": ".wavefoundry/bin/docs-lint", "suggested": "wf docs-lint"}]
        # 1p8o5: stub returns the (reconciliation, host_permission_flags) tuple.
        with patch.object(self.mod, "_run_reconciliation_scan", return_value=(finding, [])) as scan:
            out = self._emit_primary("some-root", "1.9.4", "1.9.5")
        summary = self._parse_sentinel(out)[0]
        scan.assert_called_once()
        self.assertEqual(summary["reconciliation"], finding)

    def test_reconciliation_populated_on_same_version_build_successor(self):
        # AC-6: a same-version build-successor (1.9.5 → 1.9.5 — a rebuilt pack at the same semver during
        # testing) ALSO runs the scan and populates reconciliation when stale refs exist.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text("`.wavefoundry/bin/wave-gate`\n", encoding="utf-8")
            out = self._emit_primary(root, "1.9.5", "1.9.5")
            summary = self._parse_sentinel(out)[0]
            self.assertFalse(summary["is_major_or_minor"])
            self.assertEqual(len(summary["reconciliation"]), 1)
            self.assertEqual(summary["reconciliation"][0]["retired_surface"], "wave-gate")

    def test_index_update_reflects_running_on_primary_phase(self):
        # Req-1: index_update reflects that phase 4 ran by the time the primary summary emits.
        out = self._emit_primary(None, "1.8.0", "1.9.0")
        summary = self._parse_sentinel(out)[0]
        self.assertIn("running in background", summary["index_update"])

    def test_primary_and_prose_render_from_same_builder(self):
        # AC-2: the primary-phase sentinel and the cleanup-phase prose sentinel are produced from the
        # one _build_upgrade_summary — assert identical sentinel JSON keys for the same inputs.
        primary_out = self._emit_primary(None, "1.8.0", "1.9.0", pruned_count=3)
        primary = self._parse_sentinel(primary_out)[0]
        prose_buf = io.StringIO()
        with contextlib.redirect_stdout(prose_buf):
            self.mod._print_operator_summary(
                from_version="1.8.0", to_version="1.9.0", zip_path=None,
                pruned_count=3, ran_index_rebuild=True, failed_phase=None, root=None,
            )
        prose_lines = [
            l for l in prose_buf.getvalue().splitlines()
            if l.startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
        ]
        prose = json.loads(prose_lines[0][len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):])
        self.assertEqual(set(primary.keys()), set(prose.keys()),
                         "primary + cleanup summaries must share one _build_upgrade_summary shape")
        # Same load-bearing values for the same inputs (one source, no drift).
        for k in ("from_version", "to_version", "pruned_count", "docs_gate", "is_major_or_minor"):
            self.assertEqual(primary[k], prose[k], f"key {k} drifted between the two emissions")

    def test_main_default_path_calls_emit_primary_phase_summary(self):
        # AC-1 (call-site, lighter harness per the task): the emit runs at the END of main()'s default
        # phases-0–4 path, BEFORE the "Phases 0–4 complete" log. Assert the call site via AST so a
        # refactor that drops it (re-stranding the summary to cleanup-only) fails — without driving a
        # real upgrade. The behavioral coverage above proves _emit_primary_phase_summary itself.
        import ast as _ast
        tree = _ast.parse(UPGRADE_PATH.read_text(encoding="utf-8"))
        main_fn = next(
            (n for n in _ast.walk(tree)
             if isinstance(n, _ast.FunctionDef) and n.name == "main"), None
        )
        self.assertIsNotNone(main_fn, "upgrade_wavefoundry.main not found")
        calls = [
            n for n in _ast.walk(main_fn)
            if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)
            and n.func.id == "_emit_primary_phase_summary"
        ]
        self.assertEqual(
            len(calls), 1,
            "main() must call _emit_primary_phase_summary exactly once on the default phase path",
        )
        # And it must come BEFORE the "Phases 0–4 complete" log (the end of the default path).
        emit_line = calls[0].lineno
        complete_log_lines = [
            n.lineno for n in _ast.walk(main_fn)
            if isinstance(n, _ast.Call) and "Phases 0" in _ast.dump(n)
        ]
        if complete_log_lines:
            self.assertLess(emit_line, min(complete_log_lines),
                            "the primary-phase summary must emit before the 'Phases 0–4 complete' log")


class DetectDashboardLivenessTests(unittest.TestCase):
    """Wave 1p654 review follow-up: upgrade dashboard detection cmdline-verifies the
    recorded PID (a bare os.kill accepts a zombie / recycled PID)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import dashboard_lib
        self.dashboard_lib = dashboard_lib
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_lock(self, pid):
        (self.root / ".wavefoundry" / "dashboard-server.lock").write_text(
            json.dumps({"pid": pid, "url": "http://127.0.0.1:43127/dashboard.html"}),
            encoding="utf-8",
        )

    def test_recycled_pid_rejected_by_cmdline_scan(self):
        self._write_lock(999999)
        with patch.object(self.dashboard_lib, "dashboard_cmdline_pids", return_value=[]):
            self.assertEqual(self.mod._detect_dashboard(self.root), (False, None, None))

    def test_matched_live_pid_detected(self):
        self._write_lock(os.getpid())
        with patch.object(self.dashboard_lib, "dashboard_cmdline_pids", return_value=[os.getpid()]):
            running, pid, url = self.mod._detect_dashboard(self.root)
        self.assertTrue(running)
        self.assertEqual(pid, os.getpid())

    def test_scan_unavailable_falls_back_to_pid_liveness_helper(self):
        # Wave 1p9hi: when the cmdline scan is unavailable (Windows / ps-error → None), _detect_dashboard
        # must fall back to the cross-OS upgrade_lib._pid_is_running helper, NOT a bare os.kill(pid, 0)
        # (which on Windows is GenerateConsoleCtrlEvent/TerminateProcess, not a liveness probe). Assert
        # BOTH the live and dead branches by patching the helper — this exercises the fallback contract
        # without depending on POSIX signal-0 semantics (the old test only ever ran the POSIX path).
        import upgrade_lib
        self._write_lock(4242)
        with patch.object(self.dashboard_lib, "dashboard_cmdline_pids", return_value=None):
            with patch.object(upgrade_lib, "_pid_is_running", return_value=True) as live_probe:
                running, pid, url = self.mod._detect_dashboard(self.root)
            self.assertTrue(running)
            self.assertEqual(pid, 4242)
            live_probe.assert_called_once_with(4242)
            with patch.object(upgrade_lib, "_pid_is_running", return_value=False) as dead_probe:
                running_dead, pid_dead, url_dead = self.mod._detect_dashboard(self.root)
            self.assertEqual((running_dead, pid_dead, url_dead), (False, None, None))
            dead_probe.assert_called_once_with(4242)


class WindowsTempPathRobustnessTests(unittest.TestCase):
    """Wave 1p8gv: the `/tmp` fallback raised FileNotFoundError copying the pre-upgrade MANIFEST on
    native Windows. The temp dir must come from tempfile.gettempdir() (cross-OS), not a hardcoded
    POSIX path."""

    def test_old_manifest_tmp_uses_gettempdir_not_slash_tmp(self):
        mod = load_upgrade_module()
        self.assertEqual(
            mod.OLD_MANIFEST_TMP.parent, Path(tempfile.gettempdir()),
            "OLD_MANIFEST_TMP must live under tempfile.gettempdir(), not a hardcoded /tmp",
        )
        self.assertEqual(mod.OLD_MANIFEST_TMP.name, "wf-manifest-old.txt")

    def test_no_hardcoded_tmp_or_tmpdir_fallback_in_source(self):
        src = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertNotIn('os.environ.get("TMPDIR", "/tmp")', src)
        self.assertIn("tempfile.gettempdir()", src)

    def test_old_manifest_copy_resolves_on_windows_style_temp(self):
        # Simulate a Windows-style temp dir (no real /tmp dependency): the MANIFEST copy target must
        # resolve under it and be writable (mirrors shutil.copy2(old_manifest, OLD_MANIFEST_TMP)).
        with tempfile.TemporaryDirectory() as win_temp:
            with patch.object(tempfile, "gettempdir", return_value=win_temp):
                target = Path(tempfile.gettempdir()) / "wf-manifest-old.txt"
            target.write_text("MANIFEST line\n", encoding="utf-8")
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "MANIFEST line\n")


class UpgradeCliEncodingTests(unittest.TestCase):
    """Wave 1p8gv: the upgrade CLI reconfigures stdio to UTF-8 (so `⚠` prints never raise on a cp1252
    console) and captures child output as UTF-8 (so it decodes cleanly across OSes)."""

    def test_module_reconfigures_stdio_at_import(self):
        src = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertIn("import cli_stdio", src)
        self.assertIn("cli_stdio.configure_utf8_stdio()", src)

    def test_captured_prune_spawn_routes_through_isolated_run(self):
        src = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "subprocess_util.isolated_run(cmd, cwd=str(root), capture_output=True, text=True, check=False)",
            src,
        )

    def test_no_bare_capture_output_text_subprocess_run_in_upgrade(self):
        # AC-3 source-scan: no captured `subprocess.run(..., text=True)` may remain bare — all route
        # through subprocess_util.isolated_run (which folds in encoding="utf-8", errors="replace").
        import re
        src_lines = UPGRADE_PATH.read_text(encoding="utf-8").splitlines()
        offenders = []
        for i, line in enumerate(src_lines):
            if re.search(r"\bsubprocess\.run\(", line):
                window = "\n".join(src_lines[i:i + 6])
                if "text=True" in window or "capture_output=True" in window:
                    offenders.append(f"{i + 1}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "captured subprocess.run(..., text=True) must route through subprocess_util.isolated_run "
            "(UTF-8 capture encoding):\n" + "\n".join(offenders),
        )


class SandboxResilientPackDiscoveryTests(unittest.TestCase):
    """1p8xl: a permission/sandbox error on one pack-search location (e.g. macOS-TCC ~/Downloads) must
    not abort discovery — it is logged, skipped, recorded, and surfaced in the upgrade summary."""

    class _Sandboxed:
        """A search-dir stand-in that EXISTS but raises PermissionError on iterdir (macOS TCC)."""

        def __init__(self, label: str) -> None:
            self._label = label

        def expanduser(self):
            return self

        def is_dir(self) -> bool:
            return True

        def iterdir(self):
            raise PermissionError("Operation not permitted")

        def __str__(self) -> str:
            return self._label

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.mod._PACK_SCAN_SKIPPED.clear()

    def test_scan_dir_entries_skips_and_records_on_permission_error(self):
        # AC-1 mechanism + AC-2 record: an unreadable location returns None (skip) and is recorded.
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.mod._scan_dir_entries(self._Sandboxed("/Users/x/Downloads"))
        self.assertIsNone(result)
        self.assertIn("/Users/x/Downloads", self.mod._PACK_SCAN_SKIPPED)

    def test_scan_dir_entries_lists_readable_dir(self):
        # AC-3: a readable location returns its listing and records no skip.
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("x", encoding="utf-8")
            result = self.mod._scan_dir_entries(Path(d))
        self.assertIsNotNone(result)
        self.assertEqual(self.mod._PACK_SCAN_SKIPPED, [])

    def test_find_latest_release_zip_resilient_to_unreadable_location(self):
        # AC-1 end-to-end: one location raises PermissionError, discovery still returns the pack from
        # the readable locations and does not raise.
        with tempfile.TemporaryDirectory() as good:
            good_p = Path(good)
            (good_p / "wavefoundry-1.2.3.abcd.zip").write_text("x", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), \
                 patch.object(self.mod, "_HOME_DIR", good_p), \
                 patch.object(self.mod, "_HOME_WAVEFOUNDRY_DIR", good_p), \
                 patch.object(self.mod, "_DIST_DIR", good_p), \
                 patch.object(self.mod, "_DOWNLOADS_DIR", self._Sandboxed("/fake/Downloads")):
                result = self.mod._find_latest_release_zip(good_p)
        self.assertIsNotNone(result, "must return the pack from the readable location")
        self.assertEqual(result.name, "wavefoundry-1.2.3.abcd.zip")
        self.assertIn("/fake/Downloads", self.mod._PACK_SCAN_SKIPPED)

    def test_print_all_release_zips_resilient_to_unreadable_location(self):
        # AC-4: the --list-zips path is equally resilient — a sandboxed location is skipped, not fatal.
        with tempfile.TemporaryDirectory() as good:
            good_p = Path(good)
            (good_p / "wavefoundry-1.2.3.abcd.zip").write_text("x", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), \
                 patch.object(self.mod, "_HOME_DIR", good_p), \
                 patch.object(self.mod, "_HOME_WAVEFOUNDRY_DIR", good_p), \
                 patch.object(self.mod, "_DIST_DIR", good_p), \
                 patch.object(self.mod, "_DOWNLOADS_DIR", self._Sandboxed("/fake/Downloads")):
                self.mod._print_all_release_zips(good_p)  # must not raise
        self.assertIn("wavefoundry-1.2.3.abcd.zip", buf.getvalue())

    def test_summary_surfaces_skipped_scan_locations(self):
        # AC-2 surfacing: the recorded skips appear in the upgrade summary dict.
        self.mod._PACK_SCAN_SKIPPED.extend(["/fake/Downloads"])
        summary = self.mod._build_upgrade_summary(
            from_version="1.9.7+a", to_version="1.9.8+b", zip_path=None,
            pruned_count=0, ran_index_rebuild=True, failed_phase=None, reconciliation=[],
        )
        self.assertEqual(summary["skipped_scan_locations"], ["/fake/Downloads"])

    def test_summary_skipped_empty_when_all_readable(self):
        # AC-3: no skips → empty field (no behavior change when everything reads).
        self.mod._PACK_SCAN_SKIPPED.clear()
        summary = self.mod._build_upgrade_summary(
            from_version="1.9.7+a", to_version="1.9.8+b", zip_path=None,
            pruned_count=0, ran_index_rebuild=True, failed_phase=None, reconciliation=[],
        )
        self.assertEqual(summary["skipped_scan_locations"], [])


class MaterializeLifecyclePolicyTests(unittest.TestCase):
    """Wave 1p9q0 AC-7 — idempotent, atomic, key-preserving v2 provisioning."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_upgrade_module()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "proj"
        (self.root / "docs").mkdir(parents=True)
        self.cfg = self.root / "docs" / "workflow-config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_cfg(self, data):
        self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _policy(self):
        return json.loads(self.cfg.read_text(encoding="utf-8"))["lifecycle_id_policy"]

    def test_v1_repo_migrates_to_v2_with_scanned_offset(self):
        (self.root / "docs" / "waves" / "1p9pk example-wave").mkdir(parents=True)
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z",
                                                 "hour_offset": 0}})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertIn("provisioned scheme v2", msg)
        pol = self._policy()
        self.assertEqual(pol["scheme_version"], "v2")
        self.assertEqual(pol["offset"], int("1p9pk", 36) + 288 * 366)
        self.assertNotIn("project_seed", pol)  # migrated, not fresh
        # Rollout-date epoch, never the stale 1999/2020 values.
        self.assertNotIn(pol["epoch_utc"][:4], ("1999", "2020"))

    def test_fresh_repo_gets_scattered_band_and_project_seed(self):
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        pol = self._policy()
        self.assertEqual(pol["scheme_version"], "v2")
        self.assertGreaterEqual(pol["offset"], 36 ** 3)
        self.assertLess(pol["offset"], 619_520)
        self.assertIn("proj", pol["project_seed"])

    def test_second_run_is_a_noop(self):
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        before = self.cfg.read_text(encoding="utf-8")
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertIn("left unchanged", msg)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)

    def test_idempotence_keyed_on_scheme_version_not_epoch(self):
        """A partial prior write (epoch present, scheme_version absent) is
        re-attempted — all-or-nothing."""
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "2026-06-01T00:00:00Z"}})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertIn("provisioned scheme v2", msg)
        self.assertEqual(self._policy()["scheme_version"], "v2")

    def test_unrelated_top_level_keys_preserved_value_and_order_equal(self):
        # Value- and key-order-preserving via whole-document re-serialization
        # (indent 2). NOT byte-equal for arbitrary input formatting — the AC-7
        # contract wording was reconciled to this by the delivery code lane.
        extra = {"wave_implement": {"waves_required_for_non_trivial_work": True},
                 "custom_operator_key": {"nested": [1, 2, 3]},
                 "lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z",
                                         "custom_inner": "kept"}}
        self._write_cfg(extra)
        self.mod.materialize_lifecycle_policy(self.root)
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["wave_implement"], extra["wave_implement"])
        self.assertEqual(data["custom_operator_key"], extra["custom_operator_key"])
        # Unknown keys INSIDE the policy block are preserved too.
        self.assertEqual(data["lifecycle_id_policy"]["custom_inner"], "kept")
        # Top-level key ORDER is preserved (json round-trip is insertion-ordered).
        self.assertEqual(list(data.keys()), list(extra.keys()))

    def test_crash_mid_write_leaves_original_valid_and_reattempts(self):
        """AC-7 crash-window clause at the mechanism level: a failure inside the
        atomic write must leave the original config byte-identical + parseable,
        strand no temp file, raise loudly, and succeed on the next run."""
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z"}})
        before = self.cfg.read_text(encoding="utf-8")
        with patch.object(self.mod.os, "replace", side_effect=OSError("simulated crash")):
            with self.assertRaises(RuntimeError):
                self.mod.materialize_lifecycle_policy(self.root)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)
        json.loads(before)  # still valid JSON
        leftovers = [p.name for p in (self.root / "docs").iterdir()
                     if p.name != "workflow-config.json"]
        self.assertEqual(leftovers, [])
        # Re-attempt (no crash) provisions normally — idempotence key still absent.
        self.mod.materialize_lifecycle_policy(self.root)
        self.assertEqual(self._policy()["scheme_version"], "v2")

    def test_low_horizon_warning_names_the_scanned_max(self):
        """A scanned max that leaves under ~5 years of 5-char space triggers the
        loud backstop naming the max prefix token (word-like false matches on
        6-char tokens are already excluded by the 5-char-only scan)."""
        # decode("w0000") = 53,747,712 → offset 54,063,936 > 36^5 − 1826×4096.
        (self.root / "docs" / "waves" / "w0000 anomalous").mkdir(parents=True)
        self._write_cfg({})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertIn("WARNING", msg)
        self.assertIn("w0000", msg)

    def test_below_threshold_scanned_max_stays_silent(self):
        """Just under the 5-year threshold from the other side: a large-but-legal
        scanned max that still leaves 5+ years emits no warning."""
        # decode("j0000") = 31,912,704 → offset 32,228,928 ≪ threshold 52,986,880.
        (self.root / "docs" / "waves" / "j0000 large-legit").mkdir(parents=True)
        self._write_cfg({})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertNotIn("WARNING", msg)

    def test_normal_migration_emits_no_horizon_warning(self):
        (self.root / "docs" / "waves" / "1p9pk example-wave").mkdir(parents=True)
        self._write_cfg({})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertNotIn("WARNING", msg)

    def test_word_like_six_char_filename_does_not_poison_migration(self):
        """Delivery red-team F2: `review-notes.md` decodes above 36^5 as a
        6-char token; the migration scan must ignore it (v1 history is 5-char
        by construction) and take the fresh path here."""
        (self.root / "docs" / "plans").mkdir(parents=True)
        (self.root / "docs" / "plans" / "review-notes.md").write_text("x", encoding="utf-8")
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        pol = self._policy()
        self.assertLess(pol["offset"], 619_520)  # fresh band, not 1.6B
        self.assertIn("project_seed", pol)

    def test_stale_v1_descriptor_keys_removed(self):
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z",
                                                 "time_unit": "5-minute-bucket",
                                                 "buckets_per_day": 288}})
        self.mod.materialize_lifecycle_policy(self.root)
        pol = self._policy()
        self.assertNotIn("time_unit", pol)
        self.assertNotIn("buckets_per_day", pol)

    def test_unparseable_config_fails_loudly_with_no_write(self):
        self.cfg.write_text("{corrupt json", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.mod.materialize_lifecycle_policy(self.root)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{corrupt json")

    def test_missing_config_file_is_created(self):
        self.assertFalse(self.cfg.exists())
        self.mod.materialize_lifecycle_policy(self.root)
        self.assertEqual(self._policy()["scheme_version"], "v2")

    def test_no_temp_file_left_behind(self):
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        leftovers = [p.name for p in (self.root / "docs").iterdir()
                     if p.name != "workflow-config.json"]
        self.assertEqual(leftovers, [])

    def test_written_config_is_valid_json_and_loader_accepts_it(self):
        """End-to-end: the written policy round-trips through the strict loader
        and the first mint decodes above the scanned pre-migration max."""
        (self.root / "docs" / "waves" / "1p9pk example-wave").mkdir(parents=True)
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z"}})
        self.mod.materialize_lifecycle_policy(self.root)
        spec = importlib.util.spec_from_file_location(
            "lifecycle_id_mig_test", SCRIPTS_ROOT / "lifecycle_id.py")
        lid = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lid)
        policy = lid.load_lifecycle_policy(self.root)
        prefix = lid.build_prefix(policy=policy, kind="bug", slug="post-migration")
        self.assertGreater(lid.decode_base36(prefix), int("1p9pk", 36))

    def test_cli_flag_runs_only_provisioning_and_exits_zero(self):
        self._write_cfg({})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = self.mod.main(["--materialize-lifecycle-policy", "--root", str(self.root)])
        self.assertEqual(rc, 0)
        self.assertIn("provisioned scheme v2", stdout.getvalue())
        self.assertEqual(self._policy()["scheme_version"], "v2")

    def test_cli_flag_propagates_corrupt_config_as_error(self):
        self.cfg.write_text("{corrupt", encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            rc = self.mod.main(["--materialize-lifecycle-policy", "--root", str(self.root)])
        self.assertEqual(rc, 1)
        self.assertIn("refusing to overwrite", stderr.getvalue())

    def test_cleanup_backstop_heals_unprovisioned_repo(self):
        """End-of-upgrade reconciliation check (operator directive): an
        un-provisioned repo at cleanup time is healed via the idempotent
        materialization."""
        self._write_cfg({})
        logged: list[str] = []
        with patch.object(self.mod, "_log", side_effect=logged.append):
            self.mod._ensure_lifecycle_policy_backstop(self.root)
        self.assertEqual(self._policy()["scheme_version"], "v2")
        self.assertTrue(any("backstop healed" in line for line in logged), logged)

    def test_cleanup_backstop_noop_when_already_v2(self):
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        before = self.cfg.read_text(encoding="utf-8")
        logged: list[str] = []
        with patch.object(self.mod, "_log", side_effect=logged.append):
            self.mod._ensure_lifecycle_policy_backstop(self.root)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)
        self.assertTrue(any("scheme v2 present" in line for line in logged), logged)

    def test_cleanup_backstop_never_raises_on_corrupt_config(self):
        """Fail-safe: a backstop error degrades to a loud recovery pointer —
        it must never fail cleanup."""
        self.cfg.write_text("{corrupt", encoding="utf-8")
        logged: list[str] = []
        with patch.object(self.mod, "_log", side_effect=logged.append):
            self.mod._ensure_lifecycle_policy_backstop(self.root)  # no raise
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{corrupt")
        self.assertTrue(any("--materialize-lifecycle-policy" in line for line in logged), logged)

    def test_update_index_phase_wires_the_lifecycle_backstop(self):
        # Wave 1ryce: the --update-index phase must invoke _ensure_lifecycle_policy_backstop (from the
        # freshly extracted NEW code) so a from-<1.10.1 MCP upgrade — whose preflight ran old code with no
        # Phase 2c and whose old server never reached the cleanup backstop — self-provisions scheme v2.
        # The full --update-index path spawns a real index build (no unit harness), so lock the wiring by
        # source: the backstop call must appear AFTER phase_index_update in the --update-index handler.
        import inspect
        src = inspect.getsource(self.mod)
        # `phase_index_update(root)` (closing paren) matches call sites, not the `(root: Path)` def; the
        # first call is the --update-index handler.
        piu = src.index("phase_index_update(root)")
        backstop_after = src.index("_ensure_lifecycle_policy_backstop(root)", piu)
        self.assertGreater(
            backstop_after, piu,
            "the --update-index phase must call _ensure_lifecycle_policy_backstop after phase_index_update",
        )


if __name__ == "__main__":
    unittest.main()
