"""Tests for upgrade_wavefoundry.py — _compute_seed_diffs (12r1b) and extension hooks (12r1y)."""
from __future__ import annotations

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
        self.root.mkdir(parents=True)
        self.user_home.mkdir(parents=True)
        self.home_dir.mkdir(parents=True)
        self.dist_dir.mkdir(parents=True)

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
        ), unittest.mock.patch.object(self.mod, "_DIST_DIR", self.dist_dir):
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
        # Isolate from real ~/.wavefoundry/dist/ so tests are not polluted by
        # actual release zips present on the developer's machine.
        self._dist_patch = patch.object(self.mod, "_DIST_DIR", Path(self.tmp.name) / "dist")
        self._dist_patch.start()

    def tearDown(self):
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


class PreferredPythonTests(unittest.TestCase):
    """Regression coverage for explicit shared-venv subprocess routing."""

    def setUp(self):
        self.mod = load_upgrade_module()
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

    Closes the Solaris failure mode where 1.5.0's CHUNKER_VERSION bump didn't
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
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        (self.root / ".wavefoundry" / "framework" / "scripts").mkdir(parents=True)
        (self.root / ".wavefoundry" / "framework" / "index" / "graph").mkdir(parents=True)

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
        (self.root / ".wavefoundry" / "framework" / "index" / "graph" / "framework-graph-state.json").write_text(
            json.dumps(content), encoding="utf-8",
        )

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


if __name__ == "__main__":
    unittest.main()
