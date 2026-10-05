"""Wave 1zrak (1zu4y): discovery, docs-lint inputs and removal validation fail closed.

From Python 3.14, ``Path.exists``, ``is_file``, ``is_dir`` and ``is_symlink``
return ``False`` on any ``OSError``, so an uninspectable waves or archive root
read as "no waves", an uninspectable docs-lint input as absent, and an
uninspectable requested source file as deleted. On every supported Python an
unlistable root, or a wave or nested grouping folder discovery could not
inspect, was silently left out. Each site now decides state under one errno
rule and refuses:

* discovery raises ``record_paths.RecordRootUnreadable`` (a
  ``RecordLayoutInvalid``) as ``record_root_unreadable`` or
  ``record_folder_unreadable``, path-free;
* docs-lint reports ``record_root_unreadable`` / ``record_folder_unreadable``
  and ``docs_lint_input_unreadable`` as blocking failures;
* the requested-files removal validation raises ``SourceChanged``.

Pins follow the 1zraj pattern: a mode-0 pin (skips on native Windows, where
``chmod 0`` does not deny traversal or listing, and under root, which ignores
mode 0) and a platform-independent pin that patches ``os.stat``/``os.lstat``
or the ``record_paths._scandir`` listing seam to fail for ONE target path and
delegate every other call. Symlink pins skip only when ``os.symlink`` is
refused for lack of privilege.
"""
from __future__ import annotations

import contextlib
import errno
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS = TESTS_DIR.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import commit_provenance  # noqa: E402
import context_efficiency  # noqa: E402
import indexer  # noqa: E402
import lifecycle_id  # noqa: E402
import lifecycle_lock  # noqa: E402
import memory_backfill  # noqa: E402
import memory_supply  # noqa: E402
import record_paths  # noqa: E402
import review_policy_upgrade  # noqa: E402
import vocabulary_profile  # noqa: E402
from record_layout_support import apply_layout  # noqa: E402
from wave_lint_lib import cli as lint_cli  # noqa: E402
from wave_lint_lib import docs_constants_validators as dcv  # noqa: E402
from wave_lint_lib import wave_validators  # noqa: E402

FIXTURE_V1_28 = TESTS_DIR / "fixtures" / "upgrade_old_runner" / "record_paths_v1_28_0.py.txt"
DOCS_LINT_SCRIPT = SCRIPTS / "docs_lint.py"
LIFECYCLE_ID_SCRIPT = SCRIPTS / "lifecycle_id.py"
ROOT_CODE = "record_root_unreadable"
FOLDER_CODE = "record_folder_unreadable"
EACCES_CAUSE = "PermissionError EACCES"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _skip_unless_mode_zero_denies(test: unittest.TestCase) -> None:
    if os.name == "nt":
        test.skipTest("chmod 0 does not deny traversal or listing on Windows; the patched pin covers it")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        test.skipTest("root ignores mode 0")


def _mode_zero(test: unittest.TestCase, path: Path) -> None:
    """chmod ``path`` to 0 for the rest of the test (restored on cleanup)."""
    os.chmod(path, 0)
    test.addCleanup(os.chmod, path, 0o755)


def _symlink_or_skip(test: unittest.TestCase, link: Path, target: Path) -> None:
    try:
        os.symlink(target, link)
    except OSError as exc:
        test.skipTest(f"symlinks unavailable without privilege: {exc}")


@contextlib.contextmanager
def _denied(primitive: str, *paths: Path):
    """Patch ``os.<primitive>`` to raise ``PermissionError`` for ``paths`` only.

    Both spellings are computed before the patch (``realpath`` itself calls
    ``os.lstat``); every other path reaches the real primitive. A patched
    ``os.stat`` denies only the link-following form (Python 3.13's
    ``Path.lstat`` calls ``os.stat(..., follow_symlinks=False)``)."""

    real = getattr(os, primitive)
    denied = {os.path.abspath(p) for p in paths} | {os.path.realpath(p) for p in paths}

    def fake(path, *args, **kwargs):
        following = kwargs.get("follow_symlinks", True) or primitive == "lstat"
        if (following and not isinstance(path, int)
                and os.path.abspath(os.fspath(path)) in denied):
            raise PermissionError(errno.EACCES, "Permission denied", os.fspath(path))
        return real(path, *args, **kwargs)

    with patch.object(os, primitive, fake):
        yield


@contextlib.contextmanager
def _untraversable(*paths: Path):
    """Both ``os.stat`` and ``os.lstat`` fail for ``paths``, as they do for a
    path under an untraversable parent."""
    with _denied("stat", *paths), _denied("lstat", *paths):
        yield


def _loaded_record_paths() -> list:
    """Every loaded ``record_paths`` module object: loading the server evicts
    and re-imports it, so modules imported earlier may hold another copy."""
    found = [mod for name, mod in list(sys.modules.items())
             if mod is not None and (name == "record_paths" or name.endswith(".record_paths"))]
    found += [record_paths, lifecycle_id.record_paths]
    return list({id(mod): mod for mod in found}.values())


@contextlib.contextmanager
def _unlistable(*paths: Path):
    """``record_paths._scandir`` raises ``PermissionError`` for ``paths`` only."""
    denied = {os.path.abspath(p) for p in paths}

    def make(real):
        def fake(path):
            if os.path.abspath(os.fspath(path)) in denied:
                raise PermissionError(errno.EACCES, "Permission denied", os.fspath(path))
            return real(path)
        return fake

    with contextlib.ExitStack() as stack:
        for mod in _loaded_record_paths():
            stack.enter_context(patch.object(mod, "_scandir", make(mod._scandir)))
        yield


def _root_line(rel: str, cause: str = EACCES_CAUSE) -> str:
    return (f"{ROOT_CODE}: {rel}: cannot be inspected ({cause}); "
            f"restore read and search access to {rel}, then retry")


def _folder_line(rel: str, root_rel: str, cause: str = EACCES_CAUSE) -> str:
    return (f"{FOLDER_CODE}: {rel}: cannot be inspected ({cause}); "
            f"restore read and search access to {rel}, or move it out of {root_rel} "
            "if it is not a wave folder, then retry")


class _TempRoot(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.roots = record_paths.load_record_roots(self.root)
        self.waves = self.roots.waves
        self.waves.mkdir(parents=True)

    def _wave(self, rel: str, record: "str | None" = None) -> Path:
        folder = self.waves.joinpath(*rel.split("/"))
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (record or vocabulary_profile.RECORD_FILENAME)).write_text(
            "# Wave\n\nStatus: planned\n", encoding="utf-8")
        return folder

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _flat(self):
        apply_layout(self, modules=(record_paths,), nested=False)
        self.roots = record_paths.load_record_roots(self.root)

    def _nested(self, max_depth=None):
        layout = {"nested": True}
        if max_depth is not None:
            layout["max_depth"] = max_depth
        apply_layout(self, modules=(record_paths,), **layout)
        self.roots = record_paths.load_record_roots(self.root)

    def _archive(self, rel: str = "records/archive") -> Path:
        apply_layout(self, modules=(record_paths,), archive_root=rel)
        self.roots = record_paths.load_record_roots(self.root)
        archive = self.root.joinpath(*rel.split("/"))
        archive.mkdir(parents=True, exist_ok=True)
        self.roots = record_paths.load_record_roots(self.root)
        return archive

    def assertRefuses(self, call, code: str, line):  # noqa: N802
        """``call`` raises the discovery refusal with ``code`` and the exact
        diagnostic ``line`` (or one of ``line`` when a tuple). Matched by class
        name and MRO, since loading the server re-imports ``record_paths``."""
        try:
            call()
        except Exception as raised:  # noqa: BLE001 - classified below
            exc = raised
        else:
            self.fail("no refusal was raised")
        names = [cls.__name__ for cls in type(exc).__mro__]
        self.assertEqual(names[0], "RecordRootUnreadable", repr(exc))
        self.assertIn("RecordLayoutInvalid", names)
        self.assertEqual(exc.code, code)
        lines = line if isinstance(line, tuple) else (line,)
        self.assertIn(str(exc), lines)
        self.assertEqual(exc.diagnostics, [str(exc)])
        self.assertIsNotNone(lifecycle_lock.path_free_text(str(exc), self.root), str(exc))
        self.assertNotIn("Permission denied", str(exc))
        return exc


# ---------------------------------------------------------------------------
# AC-1, AC-2: the root refusal
# ---------------------------------------------------------------------------

class RecordRootRefusalTests(_TempRoot):

    def test_absent_root_still_reads_as_no_waves(self):
        self.waves.rmdir()
        self.assertEqual(record_paths.walk_wave_candidates(self.root), [])
        self.assertEqual(record_paths.discover_wave_dirs(self.root), [])
        self._archive()
        self.roots.archive.rmdir()
        self.assertEqual(record_paths.discover_archive_dirs(self.root), [])
        self.assertFalse(record_paths.record_root_is_dir(self.roots.archive, "records/archive"))

    def test_root_that_is_a_file_reads_as_not_a_directory(self):
        self.waves.rmdir()
        self.waves.write_text("x", encoding="utf-8")
        self.assertFalse(record_paths.record_root_is_dir(self.waves, self.roots.waves_rel))

    def test_uninspectable_root_refuses_on_every_platform(self):
        self._wave("1aaaa one")
        line = _root_line(self.roots.waves_rel)
        with _untraversable(self.waves):
            for call in (lambda: record_paths.walk_wave_candidates(self.root),
                         lambda: record_paths.discover_wave_dirs(self.root),
                         lambda: record_paths.walk_wave_candidates(self.root, base=self.waves)):
                self.assertRefuses(call, ROOT_CODE, line)

    def test_uninspectable_archive_root_refuses_on_every_platform(self):
        archive = self._archive()
        with _untraversable(archive):
            self.assertRefuses(lambda: record_paths.discover_archive_dirs(self.root), ROOT_CODE,
                               _root_line("records/archive"))

    def test_unlistable_root_refuses_on_every_platform(self):
        self._wave("1aaaa one")
        with _unlistable(self.waves):
            self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), ROOT_CODE,
                               _root_line(self.roots.waves_rel))

    def test_root_under_an_untraversable_parent_refuses(self):
        _skip_unless_mode_zero_denies(self)
        self._wave("1aaaa one")
        _mode_zero(self, self.waves.parent)
        self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), ROOT_CODE,
                           _root_line(self.roots.waves_rel))

    def test_mode_zero_root_refuses_in_both_layouts(self):
        _skip_unless_mode_zero_denies(self)
        self._wave("1aaaa one")
        _mode_zero(self, self.waves)
        for layout in (self._flat, self._nested):
            layout()
            with self.subTest(layout=layout.__name__):
                self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), ROOT_CODE,
                                   _root_line(self.roots.waves_rel))

    def test_refusal_is_a_layout_error_with_path_free_text(self):
        rel = self.roots.waves_rel
        folder_rel = f"{rel}/x"
        exc = record_paths.RecordRootUnreadable(ROOT_CODE, rel, EACCES_CAUSE)
        self.assertIsInstance(exc, record_paths.RecordLayoutInvalid)
        self.assertNotIsInstance(exc, (OSError, ValueError))
        self.assertEqual(str(exc), _root_line(rel))
        self.assertEqual(exc.diagnostic, _root_line(rel))
        folder = record_paths.RecordRootUnreadable(FOLDER_CODE, folder_rel, EACCES_CAUSE, root_rel=rel)
        self.assertEqual(str(folder), _folder_line(folder_rel, rel))
        self.assertIn("RecordRootUnreadable", record_paths.__all__)


# ---------------------------------------------------------------------------
# AC-14: below-root refusal; AC-15: trees discovery legitimately ignores
# ---------------------------------------------------------------------------

class BelowRootRefusalTests(_TempRoot):

    def test_flat_mode_zero_wave_folder_refuses(self):
        _skip_unless_mode_zero_denies(self)
        self._flat()
        self._wave("1aaaa one")
        bad = self._wave("1bbbb two")
        _mode_zero(self, bad)
        self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), FOLDER_CODE,
                           _folder_line(self._rel(bad), self.roots.waves_rel))

    def test_flat_record_probe_denied_refuses_on_every_platform(self):
        self._flat()
        bad = self._wave("1bbbb two")
        with _denied("stat", bad / vocabulary_profile.RECORD_FILENAME):
            self.assertRefuses(lambda: record_paths.walk_wave_candidates(self.root), FOLDER_CODE,
                               _folder_line(self._rel(bad), self.roots.waves_rel))

    def test_flat_entry_lstat_failure_refuses_naming_the_root(self):
        # The flat walk's entries sit directly under the root, so an entry's
        # failed lstat means the root itself cannot be searched.
        self._flat()
        bad = self._wave("1bbbb two")
        with _denied("lstat", bad):
            self.assertRefuses(lambda: record_paths.walk_wave_candidates(self.root), ROOT_CODE,
                               _root_line(self.roots.waves_rel))

    def test_nested_mode_zero_grouping_folder_refuses(self):
        _skip_unless_mode_zero_denies(self)
        self._nested()
        self._wave("1aaaa one")
        group = self.waves / "team"
        self._wave("team/1bbbb two")
        _mode_zero(self, group)
        self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), FOLDER_CODE,
                           _folder_line(self._rel(group), self.roots.waves_rel))

    def test_nested_unlistable_grouping_folder_refuses_on_every_platform(self):
        self._nested()
        group = self.waves / "team"
        self._wave("team/1bbbb two")
        with _unlistable(group):
            self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), FOLDER_CODE,
                               _folder_line(self._rel(group), self.roots.waves_rel))

    def test_nested_record_probe_denied_refuses_on_every_platform(self):
        self._nested()
        wave = self._wave("team/1bbbb two")
        with _denied("stat", wave / vocabulary_profile.RECORD_FILENAME):
            self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), FOLDER_CODE,
                               _folder_line(self._rel(wave), self.roots.waves_rel))

    def test_nested_entry_lstat_failure_refuses_naming_the_parent(self):
        self._nested()
        wave = self._wave("team/1bbbb two")
        with _denied("lstat", wave):
            self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), FOLDER_CODE,
                               _folder_line(self._rel(self.waves / "team"), self.roots.waves_rel))

    def test_folder_at_max_depth_is_probed_and_refuses(self):
        _skip_unless_mode_zero_denies(self)
        self._nested(max_depth=2)
        deepest = self.waves / "g1" / "g2"
        deepest.mkdir(parents=True)
        _mode_zero(self, deepest)
        self.assertRefuses(lambda: record_paths.discover_wave_dirs(self.root), FOLDER_CODE,
                           _folder_line(self._rel(deepest), self.roots.waves_rel))

    def test_archive_folder_refuses_in_both_layouts(self):
        archive = self._archive()
        record = vocabulary_profile.archive_profile().RECORD_FILENAME
        wave = archive / "team" / "1cccc old"
        wave.mkdir(parents=True)
        (wave / record).write_text("# Wave\n", encoding="utf-8")
        flat_wave = archive / "1dddd flat"
        flat_wave.mkdir()
        (flat_wave / record).write_text("# Wave\n", encoding="utf-8")
        with self.subTest(layout="flat"), _denied("stat", flat_wave / record):
            self.assertRefuses(lambda: record_paths.discover_archive_dirs(self.root), FOLDER_CODE,
                               _folder_line("records/archive/1dddd flat", "records/archive"))
        apply_layout(self, modules=(record_paths,), nested=True)
        with self.subTest(layout="nested"), _unlistable(archive / "team"):
            self.assertRefuses(lambda: record_paths.discover_archive_dirs(self.root), FOLDER_CODE,
                               _folder_line("records/archive/team", "records/archive"))


class LegitimateTreeTests(_TempRoot):
    """AC-15: no refusal for what discovery never uses."""

    def _assert_found(self, expected):
        self.assertEqual(record_paths.discover_wave_dirs(self.root), expected)

    def test_mode_zero_dot_folder_never_refuses(self):
        _skip_unless_mode_zero_denies(self)
        a = self._wave("1aaaa one")
        dot = self.waves / ".cache"
        dot.mkdir()
        _mode_zero(self, dot)
        for layout in (self._flat, self._nested):
            layout()
            with self.subTest(layout=layout.__name__):
                self._assert_found([a])
        self._flat()
        self.assertIn(dot, record_paths.walk_wave_candidates(self.root))

    def test_denied_dot_entry_never_refuses_on_every_platform(self):
        self._flat()
        a = self._wave("1aaaa one")
        dot = self.waves / ".cache"
        dot.mkdir()
        with _untraversable(dot / vocabulary_profile.RECORD_FILENAME), _denied("lstat", dot):
            self._assert_found([a])

    def test_flat_symlink_to_an_unstatable_target_never_refuses(self):
        _skip_unless_mode_zero_denies(self)
        self._flat()
        a = self._wave("1aaaa one")
        locked = self.root / "locked"
        (locked / "target").mkdir(parents=True)
        _symlink_or_skip(self, self.waves / "1zzzz linked", locked / "target")
        _mode_zero(self, locked)
        self._assert_found([a])

    def test_flat_symlink_to_a_mode_zero_directory_never_refuses(self):
        _skip_unless_mode_zero_denies(self)
        self._flat()
        a = self._wave("1aaaa one")
        target = self.root / "outside"
        target.mkdir()
        link = self.waves / "1zzzz linked"
        _symlink_or_skip(self, link, target)
        _mode_zero(self, target)
        self._assert_found([a])
        self.assertIn(link, record_paths.walk_wave_candidates(self.root))

    def test_flat_symlink_with_a_denied_target_probe_never_refuses_on_every_platform(self):
        self._flat()
        a = self._wave("1aaaa one")
        target = self.root / "outside"
        target.mkdir()
        link = self.waves / "1zzzz linked"
        _symlink_or_skip(self, link, target)
        with _denied("stat", link / vocabulary_profile.RECORD_FILENAME):
            self._assert_found([a])

    def test_folder_beyond_max_depth_never_refuses(self):
        _skip_unless_mode_zero_denies(self)
        self._nested(max_depth=2)
        a = self._wave("1aaaa one")
        too_deep = self.waves / "g1" / "g2" / "g3"  # depth MAX_DEPTH + 1
        too_deep.mkdir(parents=True)
        _mode_zero(self, too_deep)
        self._assert_found([a])

    def test_uninspectable_subfolder_inside_a_wave_folder_never_refuses(self):
        _skip_unless_mode_zero_denies(self)
        a = self._wave("1aaaa one")
        evidence = a / "evidence"
        evidence.mkdir()
        _mode_zero(self, evidence)
        for layout in (self._flat, self._nested):
            layout()
            with self.subTest(layout=layout.__name__):
                self._assert_found([a])

    def test_files_never_refuse(self):
        _skip_unless_mode_zero_denies(self)
        a = self._wave("1aaaa one")
        loose = self.waves / "notes.md"
        loose.write_text("x", encoding="utf-8")
        _mode_zero(self, loose)
        for layout in (self._flat, self._nested):
            layout()
            with self.subTest(layout=layout.__name__):
                self._assert_found([a])


class DiscoveryMismatchAdvisoryTests(_TempRoot):
    """AC-18: the advisory stays advisory once the probe can refuse."""

    def test_refusing_probe_returns_none(self):
        self._flat()
        bad = self.waves / "1bbbb two"
        bad.mkdir()
        (bad / "notes.md").write_text("x", encoding="utf-8")
        with _denied("stat", bad / vocabulary_profile.RECORD_FILENAME):
            self.assertIsNone(record_paths.record_discovery_mismatch(self.root))
        self.assertIsNotNone(record_paths.record_discovery_mismatch(self.root))


# ---------------------------------------------------------------------------
# AC-6: reload safety against the frozen v1.28.0 record_paths
# ---------------------------------------------------------------------------

class ReloadIdentityTests(unittest.TestCase):

    def test_old_bound_and_module_handlers_catch_after_a_v1_28_reload(self):
        import upgrade_extensions

        real = sys.modules["record_paths"]
        self.addCleanup(sys.modules.__setitem__, "record_paths", real)
        old = types.ModuleType("record_paths")
        old.__file__ = str(SCRIPTS / "record_paths.py")
        sys.modules["record_paths"] = old
        exec(compile(FIXTURE_V1_28.read_text(encoding="utf-8"), old.__file__, "exec"), old.__dict__)
        self.assertFalse(hasattr(old, "RecordRootUnreadable"))
        held = old.RecordLayoutInvalid  # what ``from record_paths import RecordLayoutInvalid`` captured

        upgrade_extensions._reload_in_place(old)

        self.assertTrue(hasattr(old, "RecordRootUnreadable"))
        self.assertIs(old.RecordLayoutInvalid, held)
        self.assertTrue(issubclass(old.RecordRootUnreadable, held))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            waves = old.load_record_roots(root).waves
            waves.mkdir(parents=True)
            denied = os.path.abspath(waves)
            real_scandir = old._scandir

            def fake(path):
                if os.path.abspath(os.fspath(path)) == denied:
                    raise PermissionError(errno.EACCES, "Permission denied", os.fspath(path))
                return real_scandir(path)

            old._scandir = fake
            for label, handler in (("old-bound", held), ("module attribute", old.RecordLayoutInvalid)):
                with self.subTest(handler=label):
                    try:
                        old.discover_wave_dirs(root)
                    except handler as exc:
                        self.assertEqual(exc.code, ROOT_CODE)
                    else:
                        self.fail("discovery did not refuse")
            self.assertIsNone(old.record_discovery_mismatch(root))

    def test_a_fresh_import_bases_the_refusal_on_the_fresh_class(self):
        name = "record_paths_fresh_1zu4y"
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / "record_paths.py")
        fresh = importlib.util.module_from_spec(spec)
        sys.modules[name] = fresh  # ``dataclass`` resolves the defining module
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(fresh)
        self.assertIsNone(fresh._PRIOR_RECORD_LAYOUT_INVALID)
        self.assertEqual(fresh.RecordRootUnreadable.__bases__, (fresh.RecordLayoutInvalid,))


# ---------------------------------------------------------------------------
# AC-4: the caller-side root gates; AC-5: the OSError/ValueError boundaries
# ---------------------------------------------------------------------------

class CallerGateTests(_TempRoot):

    def setUp(self):
        super().setUp()
        self._wave("1aaaa one")
        context_efficiency._reset_open_wave_cache()
        self.addCleanup(context_efficiency._reset_open_wave_cache)

    def _gates(self):
        return (
            ("lifecycle_id._existing_prefixes", lambda: lifecycle_id._existing_prefixes(self.root)),
            ("memory_supply.resolve_wave_dir", lambda: memory_supply.resolve_wave_dir(self.root, "1aaaa")),
            ("context_efficiency._non_closed_wave_ids", lambda: context_efficiency._non_closed_wave_ids(self.root)),
            ("commit_provenance.resolve_via_evidence",
             lambda: commit_provenance.resolve_via_evidence(self.root, "abc1234")),
            ("wave_validators.check_wave_roots", lambda: wave_validators.check_wave_roots(self.root)),
            ("wave_validators.check_orphan_wave_ledgers",
             lambda: wave_validators.check_orphan_wave_ledgers(self.root)),
            ("docs_constants_validators.check_wave_scaffolding_integrity",
             lambda: dcv.check_wave_scaffolding_integrity(self.root)),
        )

    def _assert_gate_refuses(self, name, call, lines):
        if name == "wave_validators.check_wave_roots" and sys.version_info < (3, 14):
            # Out of scope (change doc): the required-path ``exists()`` loop
            # ahead of this gate raises the raw ``PermissionError`` before
            # Python 3.14 and reports the path missing from 3.14. The
            # caller-name pin below proves the gate itself uses the helper.
            with self.assertRaises(PermissionError):
                call()
            return
        self.assertRefuses(call, ROOT_CODE, lines)

    def test_each_gate_refuses_an_uninspectable_root_on_every_platform(self):
        with patch.object(commit_provenance, "canonical_commit", lambda _root, sha: sha), \
                _untraversable(self.waves):
            for name, call in self._gates():
                with self.subTest(gate=name):
                    self._assert_gate_refuses(name, call, _root_line(self.roots.waves_rel))

    def test_each_gate_refuses_a_mode_zero_parent(self):
        _skip_unless_mode_zero_denies(self)
        _mode_zero(self, self.waves.parent)
        # The id mint checks the plans root first; under the shipped layout it
        # shares the untraversable parent, so either root may be named.
        lines = (_root_line(self.roots.waves_rel), _root_line(self.roots.plans_rel))
        with patch.object(commit_provenance, "canonical_commit", lambda _root, sha: sha):
            for name, call in self._gates():
                with self.subTest(gate=name):
                    self._assert_gate_refuses(name, call, lines)

    def test_every_gate_decides_the_root_through_the_shared_helper(self):
        """AC-4: each of the 10 gates calls ``record_root_is_dir`` itself (the
        caller's code name is recorded), not only the discovery it guards."""
        import server_tools_support

        srv = server_tools_support.load_server()
        self._archive()
        callers = []

        def make(real):
            def spy(path, rel):
                callers.append((sys._getframe(1).f_code.co_name, rel))
                return real(path, rel)
            return spy

        fake_git = types.SimpleNamespace(returncode=0, stdout="abc1234 1aaaa-enh something\n", stderr="")
        with contextlib.ExitStack() as stack:
            for mod in _loaded_record_paths():
                stack.enter_context(patch.object(mod, "record_root_is_dir", make(mod.record_root_is_dir)))
            stack.enter_context(patch.object(commit_provenance, "canonical_commit", lambda _root, sha: sha))
            stack.enter_context(patch.object(srv, "_mcp_subprocess_run", lambda *a, **k: fake_git))
            for _name, call in self._gates():
                call()
            context_efficiency.resolve_open_wave(self.root)
            srv._audit_commit_governance(self.root)
        waves_rel = self.roots.waves_rel
        expected = {
            ("_existing_prefixes", waves_rel), ("_existing_prefixes", "records/archive"),
            ("resolve_wave_dir", waves_rel), ("resolve_open_wave", waves_rel),
            ("_non_closed_wave_ids", waves_rel), ("resolve_via_evidence", waves_rel),
            ("_audit_commit_governance", waves_rel), ("check_wave_roots", waves_rel),
            ("check_orphan_wave_ledgers", waves_rel), ("check_wave_scaffolding_integrity", waves_rel),
        }
        self.assertEqual(len(expected), 10)
        self.assertLessEqual(expected, set(callers), sorted(set(callers)))

    def test_archive_gate_of_the_id_mint_refuses(self):
        archive = self._archive()
        with _untraversable(archive):
            self.assertRefuses(lambda: lifecycle_id._existing_prefixes(self.root), ROOT_CODE,
                               _root_line("records/archive"))

    def test_observational_gates_use_the_helper_and_stay_observational(self):
        callers = []
        real = record_paths.record_root_is_dir

        def spy(path, rel):
            callers.append(sys._getframe(1).f_code.co_name)
            return real(path, rel)

        with patch.object(record_paths, "record_root_is_dir", spy, create=True), _untraversable(self.waves):
            self.assertIsNone(context_efficiency.resolve_open_wave(self.root))
        self.assertIn("resolve_open_wave", callers)

    def test_audit_commit_governance_gate_refuses(self):
        import server_tools_support

        srv = server_tools_support.load_server()
        fake = types.SimpleNamespace(returncode=0, stdout="abc1234 1aaaa-enh something\n", stderr="")
        with patch.object(srv, "_mcp_subprocess_run", lambda *a, **k: fake), _untraversable(self.waves):
            self.assertRefuses(lambda: srv._audit_commit_governance(self.root), ROOT_CODE,
                               _root_line(self.roots.waves_rel))

    def test_memory_backfill_reports_inventory_failed_path_free(self):
        bad = self._wave("1bbbb two")
        with _denied("stat", bad / vocabulary_profile.RECORD_FILENAME):
            with self.assertRaises(OSError) as caught:
                memory_backfill.inventory_closed_waves(self.root, with_shadowed=True)
        message = str(caught.exception)
        self.assertIn(_folder_line(self._rel(bad), self.roots.waves_rel), message)
        self.assertIsNotNone(lifecycle_lock.path_free_text(message, self.root), message)

    def test_memory_backfill_response_reports_inventory_failed_for_a_mode_zero_root(self):
        _skip_unless_mode_zero_denies(self)
        import server_tools_support

        srv = server_tools_support.load_server()
        _mode_zero(self, self.waves)
        result = srv.memory_backfill_response(self.root, mode="dry_run")
        self.assertEqual(result["status"], "error", result)
        diagnostic = result["diagnostics"][0]
        self.assertEqual(diagnostic["code"], "historical_memory_inventory_failed", result)
        self.assertIn(_root_line(self.roots.waves_rel), diagnostic["message"])
        self.assertIsNotNone(lifecycle_lock.path_free_text(diagnostic["message"], self.root))

    def test_review_policy_preflight_refuses_with_a_path_free_value_error(self):
        bad = self._wave("1bbbb two")
        with _denied("stat", bad / vocabulary_profile.RECORD_FILENAME):
            with self.assertRaises(ValueError) as caught:
                review_policy_upgrade.plan_review_policy_upgrade(self.root)
        message = str(caught.exception)
        self.assertIn(_folder_line(self._rel(bad), self.roots.waves_rel), message)
        self.assertIsNotNone(lifecycle_lock.path_free_text(message, self.root), message)

    def test_review_policy_preflight_refuses_a_mode_zero_root(self):
        _skip_unless_mode_zero_denies(self)
        _mode_zero(self, self.waves)
        with self.assertRaisesRegex(ValueError, ROOT_CODE):
            review_policy_upgrade.plan_review_policy_upgrade(self.root)


# ---------------------------------------------------------------------------
# AC-16: the id mint never mints blind
# ---------------------------------------------------------------------------

class IdMintTests(_TempRoot):

    def setUp(self):
        super().setUp()
        self._flat()
        self.a = self._wave("1aaaa one")

    def test_mode_zero_candidate_wave_folder_refuses(self):
        _skip_unless_mode_zero_denies(self)
        bad = self._wave("1bbbb two")
        _mode_zero(self, bad)
        self.assertRefuses(lambda: lifecycle_id._existing_prefixes(self.root), FOLDER_CODE,
                           _folder_line(self._rel(bad), self.roots.waves_rel))

    def test_unlistable_candidate_wave_folder_refuses_on_every_platform(self):
        bad = self._wave("1bbbb two")
        with _unlistable(bad):
            self.assertRefuses(lambda: lifecycle_id._existing_prefixes(self.root), FOLDER_CODE,
                               _folder_line(self._rel(bad), self.roots.waves_rel))
            self.assertRefuses(lambda: lifecycle_id.scan_max_prefix_value(self.root), FOLDER_CODE,
                               _folder_line(self._rel(bad), self.roots.waves_rel))

    def test_unlistable_plans_root_and_decisions_directory_refuse(self):
        self.roots.plans.mkdir(parents=True)
        with _unlistable(self.roots.plans):
            self.assertRefuses(lambda: lifecycle_id._existing_prefixes(self.root), ROOT_CODE,
                               _root_line(self.roots.plans_rel))
        decisions = self.root / "docs" / "architecture" / "decisions"
        decisions.mkdir(parents=True)
        with _unlistable(decisions):
            self.assertRefuses(lambda: lifecycle_id._existing_prefixes(self.root), ROOT_CODE,
                               _root_line("docs/architecture/decisions"))

    def test_untraversable_plans_root_refuses_the_mint_on_every_platform(self):
        self.roots.plans.mkdir(parents=True)
        with _untraversable(self.roots.plans):
            self.assertRefuses(lambda: lifecycle_id._existing_prefixes(self.root), ROOT_CODE,
                               _root_line(self.roots.plans_rel))

    def test_untraversable_decisions_directory_refuses_the_mint_on_every_platform(self):
        decisions = self.root / "docs" / "architecture" / "decisions"
        decisions.mkdir(parents=True)
        with _untraversable(decisions):
            self.assertRefuses(lambda: lifecycle_id._existing_prefixes(self.root), ROOT_CODE,
                               _root_line("docs/architecture/decisions"))

    def test_mode_zero_dot_folder_and_symlinked_mode_zero_folder_do_not_refuse(self):
        _skip_unless_mode_zero_denies(self)
        (self.a / "1aaab-enh change.md").write_text("x", encoding="utf-8")
        dot = self.waves / ".hidden"
        dot.mkdir()
        _mode_zero(self, dot)
        target = self.root / "outside"
        target.mkdir()
        _symlink_or_skip(self, self.waves / "1zzzz linked", target)
        _mode_zero(self, target)
        prefixes = lifecycle_id._existing_prefixes(self.root)
        self.assertIn("1aaaa", prefixes)
        self.assertIn("1aaab", prefixes)
        self.assertIn("1zzzz", prefixes)

    def test_cli_exits_two_with_the_path_free_diagnostic(self):
        _skip_unless_mode_zero_denies(self)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
            encoding="utf-8")
        bad = self._wave("1bbbb two")
        _mode_zero(self, bad)
        env = dict(os.environ, PROJECT_ROOT=str(self.root))
        result = subprocess.run(
            [sys.executable, "-B", str(LIFECYCLE_ID_SCRIPT), "--kind", "enh", "--slug", "x"],
            cwd=str(self.root), env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(f"lifecycle_id: error: {_folder_line(self._rel(bad), self.roots.waves_rel)}",
                      result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")


# ---------------------------------------------------------------------------
# AC-3: every decorated lifecycle tool that reaches discovery refuses
# ---------------------------------------------------------------------------

class LifecycleToolRefusalTests(unittest.TestCase):

    def setUp(self):
        import server_tools_support

        self.srv = server_tools_support.load_server()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = server_tools_support._make_repo(Path(tmp.name).resolve())
        self.roots = self.srv.record_paths.load_record_roots(self.root)
        self.wave = self.roots.waves / "1abcd demo"
        self.wave.mkdir(parents=True)
        (self.wave / vocabulary_profile.RECORD_FILENAME).write_text(
            "# Wave\n\nStatus: planned\n", encoding="utf-8")

    def _decorated_calls(self):
        srv, root = self.srv, self.root
        return (
            ("wf_current_wave", lambda: srv.wf_current_wave_response(root)),
            ("wf_list_waves", lambda: srv.wf_list_waves_response(root)),
            # The wave-bulk mode resolves the wave through discovery.
            ("wf_get_change", lambda: srv.wf_get_change_response(root, wave_id="1abcd")),
            ("wf_mark_item", lambda: srv._mark_change_item_response(
                root, "1abcd", "1abce", "AC-1", "x", target_section="Acceptance Criteria", mode="create")),
            ("wf_mark_item", lambda: srv._mark_change_item_response(
                root, "1abcd", "1abce", "Task one", "x", target_section="Tasks", mode="create")),
            ("wf_add_change", lambda: srv.wf_add_change_response(root, "1abcd", "1abce", mode="create")),
            ("wf_remove_change", lambda: srv.wf_remove_change_response(root, "1abcd", "1abce", mode="create")),
            ("wf_review_event", lambda: srv.wf_review_event_response(
                root, "1abcd", "approval", "qa", "ctx-1", mode="create", signoff_key="qa")),
            ("wf_pause_wave", lambda: srv.wf_pause_wave_response(root, "1abcd", mode="create")),
            ("wf_review_wave", lambda: srv.wf_review_wave_response(root, "1abcd")),
            ("wf_close_wave", lambda: srv.wf_close_wave_response(root, "1abcd", mode="create")),
            ("wf_close_change", lambda: srv.wf_close_change_response(root, "1abcd", "1abce", mode="create")),
            ("wf_prepare_wave", lambda: srv.wf_prepare_wave_response(root, "1abcd", mode="dry_run")),
            ("wf_implement_wave", lambda: srv.wf_implement_wave_response(root, "1abcd", mode="create")),
            ("wf_reopen_wave", lambda: srv.wf_reopen_wave_response(root, "1abcd")),
            ("wf_create_wave", lambda: srv.wf_create_wave_response(root, "refused-wave", mode="create")),
            ("wf_new_change", lambda: srv._change_create_response(root, "enh", "refused-change", mode="create")),
            ("wf_audit", lambda: srv.wf_audit_response(root)),
        )

    def _snapshot(self):
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))

    def _assert_every_tool_refuses(self, code: str, line: str) -> None:
        for tool, call in self._decorated_calls():
            before = self._snapshot()
            with self.subTest(tool=tool):
                result = call()
                self.assertEqual(result["status"], "error", result)
                diagnostic = result["diagnostics"][0]
                self.assertEqual(diagnostic["code"], code, result)
                self.assertEqual(result["data"]["tool"], tool)
                self.assertIn(line, diagnostic["message"])
                self.assertNotIn("record_paths.py", diagnostic["message"])
                self.assertIsNotNone(lifecycle_lock.path_free_text(json.dumps(result), self.root), result)
                if tool in {"wf_create_wave", "wf_new_change"}:
                    self.assertEqual(self._snapshot(), before, f"{tool} must write nothing")
        plans = self.srv.wf_list_plans_response(self.root)
        self.assertEqual(plans["status"], "ok", plans)

    def test_uninspectable_waves_root_refuses_every_tool_on_every_platform(self):
        with _untraversable(self.roots.waves):
            self._assert_every_tool_refuses(ROOT_CODE, _root_line(self.roots.waves_rel))

    def test_uninspectable_wave_folder_refuses_every_tool_on_every_platform(self):
        with _denied("stat", self.wave / vocabulary_profile.RECORD_FILENAME):
            self._assert_every_tool_refuses(
                FOLDER_CODE, _folder_line(f"{self.roots.waves_rel}/1abcd demo", self.roots.waves_rel))

    def test_mode_zero_waves_root_refuses_every_tool(self):
        _skip_unless_mode_zero_denies(self)
        _mode_zero(self, self.roots.waves)
        self._assert_every_tool_refuses(ROOT_CODE, _root_line(self.roots.waves_rel))

    # Single-change lookup (``_resolve_change_doc_matches``): its ``rglob``
    # skipped what it could not list, so a change held in an uninspectable wave
    # folder read as ``change_not_found`` (delivery review DEL-U1).

    def _hidden_change(self):
        change = self.wave / "1bbbb-bug hidden.md"
        change.write_text("# Hidden\n\nChange ID: `1bbbb-bug hidden`\n", encoding="utf-8")
        return _folder_line(f"{self.roots.waves_rel}/1abcd demo", self.roots.waves_rel)

    def _assert_lookup_refuses(self, code, line):
        result = self.srv.wf_get_change_response(self.root, "1bbbb")
        self.assertEqual(result["status"], "error", result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        self.assertIn(line, result["diagnostics"][0]["message"])
        self.assertIsNotNone(lifecycle_lock.path_free_text(json.dumps(result), self.root), result)

    def test_single_change_lookup_refuses_a_mode_zero_wave_folder(self):
        _skip_unless_mode_zero_denies(self)
        line = self._hidden_change()
        _mode_zero(self, self.wave)
        self._assert_lookup_refuses(FOLDER_CODE, line)

    def test_single_change_lookup_refuses_an_unlistable_wave_folder_on_every_platform(self):
        line = self._hidden_change()
        with _unlistable(self.wave):
            self._assert_lookup_refuses(FOLDER_CODE, line)

    def test_single_change_lookup_refuses_an_unlistable_plans_root_on_every_platform(self):
        self.roots.plans.mkdir(parents=True)
        with _unlistable(self.roots.plans):
            self._assert_lookup_refuses(ROOT_CODE, _root_line(self.roots.plans_rel))

    def test_single_change_lookup_refuses_an_unlistable_archived_folder_on_every_platform(self):
        rel = "records/archive"
        apply_layout(self, modules=(self.srv.record_paths, record_paths), archive_root=rel)
        record = vocabulary_profile.archive_profile().RECORD_FILENAME
        archived = self.root / "records" / "archive" / "1cccc old"
        archived.mkdir(parents=True)
        (archived / record).write_text("# Wave\n", encoding="utf-8")
        with _unlistable(archived):
            self._assert_lookup_refuses(FOLDER_CODE, _folder_line(f"{rel}/1cccc old", rel))

    def test_single_change_lookup_refuses_an_untraversable_plans_root_on_every_platform(self):
        self.roots.plans.mkdir(parents=True)
        with _untraversable(self.roots.plans):
            self._assert_lookup_refuses(ROOT_CODE, _root_line(self.roots.plans_rel))

    def _non_wave_candidate(self) -> Path:
        notes = self.roots.waves / "notes"
        notes.mkdir()
        (notes / "1bbbb-bug hidden.md").write_text(
            "# Hidden\n\nChange ID: `1bbbb-bug hidden`\n", encoding="utf-8")
        return notes

    def test_single_change_lookup_refuses_a_searchable_but_unlistable_candidate_folder(self):
        # 0o311: search without read. The record probe sees no record (so
        # discovery keeps the folder as a candidate) but nothing can list it;
        # the id mint refuses it, and so does the lookup.
        _skip_unless_mode_zero_denies(self)
        notes = self._non_wave_candidate()
        os.chmod(notes, 0o311)
        self.addCleanup(os.chmod, notes, 0o755)
        line = _folder_line(f"{self.roots.waves_rel}/notes", self.roots.waves_rel)
        self._assert_lookup_refuses(FOLDER_CODE, line)
        with self.assertRaises(Exception) as minted:
            lifecycle_id._existing_prefixes(self.root)
        self.assertEqual(str(minted.exception), line)

    def test_single_change_lookup_refuses_an_unlistable_candidate_folder_on_every_platform(self):
        notes = self._non_wave_candidate()
        line = _folder_line(f"{self.roots.waves_rel}/notes", self.roots.waves_rel)
        with _unlistable(notes):
            self._assert_lookup_refuses(FOLDER_CODE, line)
            with self.assertRaises(Exception) as minted:
                lifecycle_id._existing_prefixes(self.root)
        self.assertEqual(str(minted.exception), line)

    def test_single_change_lookup_finds_a_change_in_a_readable_candidate_folder(self):
        self._non_wave_candidate()
        result = self.srv.wf_get_change_response(self.root, "1bbbb")
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["data"]["change"]["change_id"], "1bbbb-bug hidden", result)

    # Wave and change resources answer a refusal with a markdown page.

    def _resources(self):
        from declaration_support import RecordingFastMCP

        recorder = RecordingFastMCP()
        handler = types.SimpleNamespace(root=self.root, cache=None)
        self.srv.register_mcp_surface(recorder, lambda: handler)
        return recorder.resource_functions

    def test_wave_and_change_resources_return_an_unavailable_page(self):
        resources = self._resources()
        calls = (
            ("resource_current_wave", ()), ("resource_waves", ()),
            ("resource_wave", ("1abcd",)), ("resource_change", ("1bbbb",)),
        )
        line = _root_line(self.roots.waves_rel)
        with _untraversable(self.roots.waves):
            for name, args in calls:
                with self.subTest(resource=name):
                    self.assertEqual(resources[name](*args), f"# Unavailable\n\n{line}\n")

    def test_change_resource_template_serves_the_unavailable_page_end_to_end(self):
        import asyncio
        import server_tools_support

        line = self._hidden_change()
        try:
            mcp = server_tools_support.load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        with _unlistable(self.wave):
            contents = asyncio.run(mcp.read_resource("wavefoundry://change/1bbbb"))
        text = "".join(str(getattr(item, "content", "") or "") for item in contents)
        self.assertEqual(text, f"# Unavailable\n\n{line}\n")

    def test_single_change_lookup_still_finds_a_readable_change(self):
        self._hidden_change()
        result = self.srv.wf_get_change_response(self.root, "1bbbb")
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["data"]["change"]["change_id"], "1bbbb-bug hidden", result)

    def test_mode_zero_wave_folder_refuses_every_tool(self):
        _skip_unless_mode_zero_denies(self)
        _mode_zero(self, self.wave)
        self._assert_every_tool_refuses(
            FOLDER_CODE, _folder_line(f"{self.roots.waves_rel}/1abcd demo", self.roots.waves_rel))


# ---------------------------------------------------------------------------
# AC-17: the dashboard says why instead of dropping the connection
# ---------------------------------------------------------------------------

class DashboardDocumentTests(_TempRoot):

    def _get_doc(self, **params):
        from urllib.parse import urlencode

        import dashboard_server

        class Handler(dashboard_server.DashboardHandler):
            def __init__(self, store, path):
                self.server = types.SimpleNamespace(snapshot_store=store, bound_host="127.0.0.1")
                self.path = path
                self.sent = None

            def send_error(self, code, message=None, explain=None):
                self.sent = (code, message, explain)

        store = types.SimpleNamespace(_root=self.root, _record_roots=self.roots)
        handler = Handler(store, "/api/doc?" + urlencode(params))
        handler._handle_doc()
        return handler

    def test_uninspectable_root_answers_503_with_the_path_free_diagnostic(self):
        self._wave("1aaaa one")
        with _untraversable(self.waves):
            handler = self._get_doc(type="wave", id="1aaaa")
        self.assertEqual(handler.sent, (503, ROOT_CODE, _root_line(self.roots.waves_rel)))

    def test_uninspectable_wave_folder_answers_503(self):
        self._flat()
        wave = self._wave("1aaaa one")
        with _denied("stat", wave / vocabulary_profile.RECORD_FILENAME):
            handler = self._get_doc(type="wave", id="1aaaa")
        self.assertEqual(handler.sent, (503, FOLDER_CODE, _folder_line(self._rel(wave), self.roots.waves_rel)))


# ---------------------------------------------------------------------------
# AC-7: docs-lint fails closed on an uninspectable record root or folder
# ---------------------------------------------------------------------------

class DocsLintRecordRefusalTests(_TempRoot):

    def setUp(self):
        super().setUp()
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def _lint(self, *args):
        env = dict(os.environ, PROJECT_ROOT=str(self.root))
        env["PYTHONPATH"] = str(SCRIPTS) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run([sys.executable, "-B", str(DOCS_LINT_SCRIPT), *args], cwd=str(self.root),
                              env=env, capture_output=True, text=True, check=False)

    def _assert_refused_once(self, result, line):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stderr.count(line), 1, result.stderr)
        self.assertIn(f"ERROR: {line}\n", result.stderr)
        self.assertNotIn(f"ERROR: ERROR: {line}", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_mode_zero_waves_root_fails_full_and_incremental_lint(self):
        _skip_unless_mode_zero_denies(self)
        self._wave("1aaaa one")
        _mode_zero(self, self.waves)
        line = _root_line(self.roots.waves_rel)
        for args in ((), ("--changed",)):
            with self.subTest(args=args):
                self._assert_refused_once(self._lint(*args), line)

    def test_mode_zero_wave_folder_fails_lint(self):
        _skip_unless_mode_zero_denies(self)
        bad = self._wave("1aaaa one")
        _mode_zero(self, bad)
        line = _folder_line(self._rel(bad), self.roots.waves_rel)
        for args in ((), ("--changed",)):
            with self.subTest(args=args):
                self._assert_refused_once(self._lint(*args), line)

    def _run_in_process(self, *args):
        stderr = io.StringIO()
        with patch.dict(os.environ, {"PROJECT_ROOT": str(self.root)}), \
                patch.object(sys, "argv", ["docs_lint.py", *args]), \
                contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = lint_cli.main()
        return code, stderr.getvalue()

    def test_uninspectable_root_and_folder_fail_lint_on_every_platform(self):
        # The folder case uses the listing seam on a nested grouping folder: a
        # patched stat of a record FILE in a listable folder is not a shape
        # the file system produces, and the corpus walk would meet it first.
        self._nested()
        self._wave("team/1aaaa one")
        group = self.waves / "team"
        cases = (
            ("root", lambda: _untraversable(self.waves), _root_line(self.roots.waves_rel)),
            ("folder", lambda: _unlistable(group), _folder_line(self._rel(group), self.roots.waves_rel)),
        )
        for label, denial, line in cases:
            for args in ((), ("--changed",)):
                with self.subTest(case=label, args=args), denial():
                    code, err = self._run_in_process(*args)
                    self.assertEqual(code, 1, err)
                    self.assertEqual(err.count(line), 1, err)
                    self.assertIn(f"ERROR: {line}\n", err)

    def test_refusal_raised_mid_run_is_reported_not_a_traceback(self):
        line = _root_line(self.roots.waves_rel)

        def explode(*_args, **_kwargs):
            raise lint_cli.record_paths.RecordRootUnreadable(ROOT_CODE, self.roots.waves_rel, EACCES_CAUSE)

        with patch.object(lint_cli, "check_wave_roots", explode):
            code, err = self._run_in_process()
        self.assertEqual(code, 1, err)
        self.assertEqual(err.count(line), 1, err)

    def test_refusal_raised_mid_run_on_the_incremental_path_is_reported(self):
        line = _root_line(self.roots.waves_rel)

        def explode(*_args, **_kwargs):
            raise lint_cli.record_paths.RecordRootUnreadable(ROOT_CODE, self.roots.waves_rel, EACCES_CAUSE)

        with patch.object(lint_cli, "_run_incremental_checks", explode):
            code, err = self._run_in_process("--changed")
        self.assertEqual(code, 1, err)
        self.assertEqual(err.count(line), 1, err)
        self.assertIn(f"ERROR: {line}\n", err)
        self.assertNotIn("Traceback", err)


# ---------------------------------------------------------------------------
# AC-8: docs-lint presence probes
# ---------------------------------------------------------------------------

class DocsLintInputProbeTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.docs = self.root / "docs"
        self.docs.mkdir()
        self.config = self.docs / "workflow-config.json"

    def _enable(self):
        self.config.write_text(json.dumps({"docs_lint": {"framework_internal_constants": True}}),
                               encoding="utf-8")

    @staticmethod
    def _unreadable(rel: str) -> str:
        return (f"docs_lint_input_unreadable: {rel}: cannot be inspected ({EACCES_CAUSE}); "
                f"restore read access to {rel}, then re-run docs-lint")

    def _assert_reported(self, failures, rel):
        self.assertIn(self._unreadable(rel), failures)
        emitted = io.StringIO()
        with contextlib.redirect_stderr(emitted):
            lint_cli._emit([f for f in failures if f.startswith("docs_lint_input_unreadable")], [], [],
                           self.root, None, incremental=True)
        self.assertEqual(emitted.getvalue(), f"ERROR: {self._unreadable(rel)}\n")
        self.assertIsNotNone(lifecycle_lock.path_free_text(emitted.getvalue(), self.root))

    # workflow-config.json

    def test_workflow_config_absent_passes(self):
        self.assertEqual(dcv._framework_internal_constants_enabled(self.root), (False, []))

    def test_workflow_config_uninspectable_on_every_platform(self):
        self._enable()
        with _denied("lstat", self.config):
            enabled, failures = dcv._framework_internal_constants_enabled(self.root)
        self.assertFalse(enabled)
        self._assert_reported(failures, "docs/workflow-config.json")

    def test_workflow_config_under_a_mode_zero_parent(self):
        _skip_unless_mode_zero_denies(self)
        self._enable()
        _mode_zero(self, self.docs)
        self._assert_reported(dcv._framework_internal_constants_enabled(self.root)[1], "docs/workflow-config.json")

    def test_workflow_config_itself_unreadable(self):
        _skip_unless_mode_zero_denies(self)
        self._enable()
        _mode_zero(self, self.config)
        self._assert_reported(dcv._framework_internal_constants_enabled(self.root)[1], "docs/workflow-config.json")

    # the claims doc

    def _claims_doc(self) -> Path:
        self._enable()
        doc = self.docs / "specs" / "mcp-tool-surface.md"
        doc.parent.mkdir()
        doc.write_text("# Surface\n", encoding="utf-8")
        return doc

    def test_claims_doc_absent_passes(self):
        self._enable()
        failures = dcv.check_docs_constants(self.root)
        self.assertFalse([f for f in failures if "docs_lint_input_unreadable" in f], failures)

    def test_claims_doc_uninspectable_on_every_platform(self):
        doc = self._claims_doc()
        with _denied("stat", doc):
            failures = dcv.check_docs_constants(self.root)
        self._assert_reported(failures, "docs/specs/mcp-tool-surface.md")

    def test_claims_doc_under_a_mode_zero_parent(self):
        _skip_unless_mode_zero_denies(self)
        doc = self._claims_doc()
        _mode_zero(self, doc.parent)
        self._assert_reported(dcv.check_docs_constants(self.root), "docs/specs/mcp-tool-surface.md")

    def test_claims_doc_itself_unreadable(self):
        _skip_unless_mode_zero_denies(self)
        doc = self._claims_doc()
        _mode_zero(self, doc)
        self._assert_reported(dcv.check_docs_constants(self.root), "docs/specs/mcp-tool-surface.md")

    # legacy memory pointer residue

    def _memory_root(self) -> Path:
        memory = self.root.joinpath(*wave_validators.MEMORY_RECORD_DIR.split("/"))
        memory.mkdir(parents=True)
        return memory

    def test_pointer_residue_absent_passes(self):
        self._memory_root()
        failures = wave_validators.check_memory_docs(self.root)
        self.assertFalse([f for f in failures if "pointers" in f], failures)

    def test_pointer_residue_uninspectable_on_every_platform(self):
        pointers = self._memory_root() / "pointers"
        with _denied("lstat", pointers):
            failures = wave_validators.check_memory_docs(self.root)
        self._assert_reported(failures, f"{wave_validators.MEMORY_RECORD_DIR}/pointers")

    def test_pointer_residue_under_a_mode_zero_parent(self):
        _skip_unless_mode_zero_denies(self)
        memory = self._memory_root()
        (memory / "pointers").mkdir()
        _mode_zero(self, memory)
        self._assert_reported(wave_validators.check_memory_docs(self.root),
                              f"{wave_validators.MEMORY_RECORD_DIR}/pointers")


# ---------------------------------------------------------------------------
# AC-9: requested-files removal validation
# ---------------------------------------------------------------------------

class RequestedRemovalTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        self.source = self.root / "notes" / "guide.md"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("# Guide\n", encoding="utf-8")

    def _validate(self):
        indexer._validate_prepared_removals(
            self.root, self.index_dir, {"notes/guide.md"}, {"docs": {"notes/guide.md"}},
            requested_files=[Path("notes/guide.md")], respect_ignore=True, include_prefixes=(),
            project_include_prefixes=(), include_tests=False, include_generated=False,
        )

    def test_genuinely_absent_requested_file_is_removed(self):
        self.source.unlink()
        self._validate()  # no SourceChanged

    def test_denied_requested_file_refuses_the_removal_on_every_platform(self):
        with _denied("stat", self.source), self.assertRaisesRegex(indexer.SourceChanged, "became unreadable"):
            self._validate()

    def test_requested_file_under_a_mode_zero_parent_refuses_the_removal(self):
        _skip_unless_mode_zero_denies(self)
        _mode_zero(self, self.source.parent)
        with self.assertRaisesRegex(indexer.SourceChanged, "notes/guide.md"):
            self._validate()


if __name__ == "__main__":
    unittest.main()
