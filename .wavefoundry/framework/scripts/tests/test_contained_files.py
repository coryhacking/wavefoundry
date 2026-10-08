"""The contained read and write primitive (wave 200ey, change 1zyv2).

``contained_files`` owns one rule for reading and writing a file that must stay
inside a root: a link leaving the root or a special file is refused rather than
followed or opened, reads are capped, the mode is set on the descriptor, and a
refusal names no path. These tests cover the primitive itself, the directory
walk helper, a swap injected between the checks and the descriptor work, the
Windows branch (simulated on POSIX), the copied Windows link predicate, the
member-doc reader's delegation, and the census that keeps both surface
renderers on the primitive.
"""
from __future__ import annotations

import ast
import errno
import os
import shutil
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import contained_files as cf  # noqa: E402
from framework_files import framework_source_files, source_path  # noqa: E402

POSIX = os.name != "nt"
OUTSIDE_TEXT = b"outside-content\n"


def _run_with_timeout(case: unittest.TestCase, fn, timeout: float = 10.0):
    """Run ``fn`` in a daemon thread; fail when it is still running after
    ``timeout`` seconds (a blocked open). Returns ``(result, exception)``."""
    box: dict = {}

    def target() -> None:
        try:
            box["result"] = fn()
        except BaseException as exc:  # noqa: BLE001 - reported to the test
            box["error"] = exc

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout)
    case.assertFalse(worker.is_alive(), "the call blocked")
    return box.get("result"), box.get("error")


class _Roots(unittest.TestCase):
    def setUp(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="wf-contained-")).resolve()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        self.base = base
        self.root = base / "repo"
        self.root.mkdir()
        self.outside = base / "outside"
        self.outside.mkdir()
        self.secret = self.outside / "secret.txt"
        self.secret.write_bytes(OUTSIDE_TEXT)
        if POSIX:
            os.chmod(self.secret, 0o600)

    def assert_outside_untouched(self) -> None:
        self.assertEqual(self.secret.read_bytes(), OUTSIDE_TEXT)
        if POSIX:
            self.assertEqual(stat.S_IMODE(os.stat(self.secret).st_mode), 0o600)
        self.assertEqual(sorted(p.name for p in self.outside.iterdir()), ["secret.txt"])

    def assert_path_free(self, exc: BaseException) -> None:
        text = f"{exc} {exc!r}"
        self.assertNotIn(str(self.base), text)
        self.assertNotIn(os.path.realpath(self.base), text)
        self.assertNotIn(OUTSIDE_TEXT.decode().strip(), text)
        self.assertIsNone(getattr(exc, "filename", None))

    def refused(self, fn, cause: str | None = None) -> cf.ContainedFileRefused:
        with self.assertRaises(cf.ContainedFileRefused) as caught:
            fn()
        if cause is not None:
            self.assertEqual(caught.exception.cause, cause)
        self.assertEqual(caught.exception.errno, errno.EPERM)
        self.assert_path_free(caught.exception)
        return caught.exception


class ConstantsAndOwnershipTests(unittest.TestCase):
    def test_default_cap_equals_the_member_document_cap(self) -> None:
        import lifecycle_gate_support as lgs

        self.assertEqual(cf.DEFAULT_MAX_BYTES, 8 * 1024 * 1024)
        self.assertEqual(cf.DEFAULT_MAX_BYTES, lgs.MEMBER_DOC_MAX_BYTES)

    def test_runtime_lock_identities_has_one_owner(self) -> None:
        import lifecycle_gate_support as lgs

        # By the module lgs bound, not this test's import: a server load in the
        # same process purges and re-imports both.
        self.assertEqual(lgs.runtime_lock_identities.__module__, "contained_files")
        self.assertIs(lgs.runtime_lock_identities, lgs.contained_files.runtime_lock_identities)

    def test_the_module_is_a_registered_stdlib_only_leaf(self) -> None:
        import mcp_tool_extensions

        self.assertIn("contained_files", mcp_tool_extensions.FRAMEWORK_SCRIPT_MODULE_NAMES)
        tree = ast.parse(source_path("contained_files").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        framework = {p.stem for p in framework_source_files()}
        self.assertFalse(imported & framework, imported & framework)
        self.assertLessEqual(imported, set(sys.stdlib_module_names) | {"__future__"})


class WindowsPredicateParityTests(unittest.TestCase):
    """The copied name-surrogate predicate agrees with ``runtime_lock``'s."""

    def test_the_copy_agrees_over_the_reparse_tags(self) -> None:
        import runtime_lock

        cases = [
            (stat.S_IFREG | 0o644, 0),
            (stat.S_IFLNK | 0o777, 0),
            (stat.S_IFREG | 0o644, 0xA000000C),  # symlink
            (stat.S_IFDIR | 0o755, 0xA0000003),  # junction / mount point
            (stat.S_IFREG | 0o644, 0x9000001A),  # cloud files placeholder
            (stat.S_IFREG | 0o644, 0x80000013),  # deduplication
            (stat.S_IFDIR | 0o755, 0),
        ]
        for mode, tag in cases:
            fake = SimpleNamespace(st_mode=mode, st_reparse_tag=tag)
            with self.subTest(mode=oct(mode), tag=hex(tag)), \
                    mock.patch.object(os, "lstat", return_value=fake):
                self.assertEqual(cf._is_windows_link("x"), runtime_lock._is_windows_link("x"))
        with mock.patch.object(os, "lstat", side_effect=FileNotFoundError):
            self.assertEqual(cf._is_windows_link("x"), runtime_lock._is_windows_link("x"))

    def test_the_copy_is_the_same_code(self) -> None:
        import inspect

        import runtime_lock

        def body(fn) -> str:
            node = ast.parse(inspect.getsource(fn)).body[0]
            node.body = [n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
            return ast.unparse(node)

        self.assertEqual(body(cf._is_windows_link), body(runtime_lock._is_windows_link))


class ReadRuleTests(_Roots):
    def test_an_ordinary_file_reads_in_full_at_the_cap_and_is_refused_above_it(self) -> None:
        path = self.root / "docs" / "a.md"
        path.parent.mkdir()
        path.write_bytes(b"x" * 64)
        self.assertEqual(cf.read_contained_bytes(self.root, path, max_bytes=64), b"x" * 64)
        self.refused(lambda: cf.read_contained_bytes(self.root, path, max_bytes=63), cf.CAUSE_SIZE)
        data, opened = cf.read_contained(self.root, "docs/a.md", max_bytes=64)
        self.assertEqual(data, b"x" * 64)
        self.assertEqual((opened.st_dev, opened.st_ino), (os.stat(path).st_dev, os.stat(path).st_ino))

    def test_a_parent_component_is_refused_lexically(self) -> None:
        (self.root / "a.md").write_bytes(b"a")
        self.refused(
            lambda: cf.read_contained_bytes(self.root, self.root / "docs" / ".." / "a.md", max_bytes=9),
            cf.CAUSE_NOT_UNDER_ROOT,
        )
        self.refused(lambda: cf.read_contained_bytes(self.root, self.secret, max_bytes=99), cf.CAUSE_NOT_UNDER_ROOT)

    def test_a_missing_file_raises_a_path_free_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError) as caught:
            cf.read_contained_bytes(self.root, self.root / "missing.md", max_bytes=9)
        self.assert_path_free(caught.exception)

    @unittest.skipUnless(POSIX, "symlink and FIFO fixtures")
    def test_links_leaving_the_root_are_refused_and_links_inside_it_are_followed(self) -> None:
        os.symlink(self.secret, self.root / "final.md")
        os.symlink(self.outside, self.root / "linkdir")
        self.refused(lambda: cf.read_contained_bytes(self.root, self.root / "final.md", max_bytes=99), cf.CAUSE_OUTSIDE)
        self.refused(
            lambda: cf.read_contained_bytes(self.root, self.root / "linkdir" / "secret.txt", max_bytes=99),
            cf.CAUSE_OUTSIDE,
        )
        real = self.root / "real"
        real.mkdir()
        (real / "doc.md").write_bytes(b"inside\n")
        os.symlink("real", self.root / "alias")
        os.symlink("doc.md", real / "pointer.md")
        self.assertEqual(cf.read_contained_bytes(self.root, self.root / "alias" / "doc.md", max_bytes=99), b"inside\n")
        self.assertEqual(cf.read_contained_bytes(self.root, real / "pointer.md", max_bytes=99), b"inside\n")
        os.symlink("nowhere.md", self.root / "dangling.md")
        self.refused(lambda: cf.read_contained_bytes(self.root, self.root / "dangling.md", max_bytes=9), cf.CAUSE_NOT_REGULAR)
        self.assert_outside_untouched()

    @unittest.skipUnless(POSIX, "FIFO fixture")
    def test_a_fifo_is_refused_without_blocking(self) -> None:
        fifo = self.root / "pipe.md"
        os.mkfifo(fifo)
        _result, error = _run_with_timeout(self, lambda: cf.read_contained_bytes(self.root, fifo, max_bytes=9))
        self.assertIsInstance(error, cf.ContainedFileRefused)
        self.assertEqual(error.cause, cf.CAUSE_NOT_REGULAR)

    def test_a_runtime_lock_is_refused_by_name_and_as_a_hard_link(self) -> None:
        lock = self.root / ".wavefoundry" / "lifecycle-mutation.lock"
        lock.parent.mkdir()
        lock.write_bytes(b"lock")
        self.refused(lambda: cf.read_contained_bytes(self.root, lock, max_bytes=9), cf.CAUSE_RUNTIME_LOCK)
        try:
            os.link(lock, self.root / "hard.md")
        except OSError:
            self.skipTest("hard links unsupported here")
        self.refused(
            lambda: cf.read_contained_bytes(self.root, self.root / "hard.md", max_bytes=9), cf.CAUSE_RUNTIME_LOCK
        )
        self.assertEqual(lock.read_bytes(), b"lock")


class WriteRuleTests(_Roots):
    def test_a_new_file_is_created_with_its_parents_and_reported_changed(self) -> None:
        target = self.root / "a" / "b" / "c.txt"
        self.assertTrue(cf.write_contained_bytes(self.root, target, b"one\n"))
        self.assertEqual(target.read_bytes(), b"one\n")
        self.assertEqual([p.name for p in target.parent.iterdir()], ["c.txt"])

    def test_unchanged_bytes_write_nothing_and_a_mode_is_kept_or_set(self) -> None:
        target = self.root / "hook.py"
        self.assertTrue(cf.write_contained_bytes(self.root, target, b"#!x\n", executable=True))
        if POSIX:
            self.assertTrue(os.stat(target).st_mode & 0o111)
        before = os.stat(target)
        self.assertFalse(cf.write_contained_bytes(self.root, target, b"#!x\n", executable=True))
        after = os.stat(target)
        self.assertEqual((after.st_ino, after.st_mtime_ns), (before.st_ino, before.st_mtime_ns))
        if POSIX:
            os.chmod(target, 0o640)
            self.assertFalse(cf.write_contained_bytes(self.root, target, b"#!x\n", executable=True))
            self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o751)
            os.chmod(target, 0o640)
            self.assertTrue(cf.write_contained_bytes(self.root, target, b"changed\n"))
            self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o640)
            self.assertTrue(cf.write_contained_bytes(self.root, self.root / "m.txt", b"m", mode=0o600))
            self.assertEqual(stat.S_IMODE(os.stat(self.root / "m.txt").st_mode), 0o600)

    @unittest.skipUnless(POSIX, "symlink fixtures")
    def test_a_link_leaving_the_root_is_refused_and_one_inside_it_writes_its_target(self) -> None:
        os.symlink(self.secret, self.root / "final.txt")
        os.symlink(self.outside, self.root / "linkdir")
        self.refused(lambda: cf.write_contained_bytes(self.root, self.root / "final.txt", b"x"), cf.CAUSE_OUTSIDE)
        self.refused(
            lambda: cf.write_contained_bytes(self.root, self.root / "linkdir" / "new.txt", b"x"), cf.CAUSE_OUTSIDE
        )
        self.refused(
            lambda: cf.write_contained_bytes(self.root, self.root / "linkdir" / "deep" / "new.txt", b"x"),
            cf.CAUSE_OUTSIDE,
        )
        self.assert_outside_untouched()
        (self.root / "real.txt").write_bytes(b"old\n")
        os.symlink("real.txt", self.root / "alias.txt")
        self.assertTrue(cf.write_contained_bytes(self.root, self.root / "alias.txt", b"new\n"))
        self.assertTrue((self.root / "alias.txt").is_symlink())
        self.assertEqual((self.root / "real.txt").read_bytes(), b"new\n")

    @unittest.skipUnless(POSIX, "FIFO fixture")
    def test_a_special_file_target_is_refused(self) -> None:
        os.mkfifo(self.root / "pipe")
        _result, error = _run_with_timeout(
            self, lambda: cf.write_contained_bytes(self.root, self.root / "pipe", b"x")
        )
        self.assertIsInstance(error, cf.ContainedFileRefused)
        self.assertEqual(error.cause, cf.CAUSE_NOT_REGULAR)


@unittest.skipUnless(POSIX, "descriptor walk and symlink swaps need POSIX")
class SwapInjectionTests(_Roots):
    """AC-5: a final component swapped for a link between the checks and the
    descriptor work is refused (read) or replaced as an entry (write)."""

    def test_a_read_refuses_a_final_component_swapped_after_the_checks(self) -> None:
        target = self.root / "doc.md"
        target.write_bytes(b"inside\n")

        def swap(stage: str) -> None:
            if stage == "open":
                target.unlink()
                os.symlink(self.secret, target)

        with mock.patch.object(cf, "_checkpoint", side_effect=swap):
            self.refused(lambda: cf.read_contained_bytes(self.root, target, max_bytes=99), cf.CAUSE_CHANGED)
        self.assert_outside_untouched()

    def test_a_read_refuses_a_directory_component_swapped_after_the_checks(self) -> None:
        folder = self.root / "docs"
        folder.mkdir()
        (folder / "doc.md").write_bytes(b"inside\n")
        shutil.copy(self.secret, self.outside / "doc.md")

        def swap(stage: str) -> None:
            if stage == "open":
                folder.rename(self.root / "docs-moved")
                os.symlink(self.outside, folder)

        with mock.patch.object(cf, "_checkpoint", side_effect=swap):
            self.refused(lambda: cf.read_contained_bytes(self.root, folder / "doc.md", max_bytes=99))
        (self.outside / "doc.md").unlink()
        self.assert_outside_untouched()

    def test_a_write_replaces_a_swapped_link_entry_and_leaves_its_target(self) -> None:
        target = self.root / "out.txt"
        target.write_bytes(b"old\n")

        def swap(stage: str) -> None:
            if stage == "publish":
                target.unlink()
                os.symlink(self.secret, target)

        with mock.patch.object(cf, "_checkpoint", side_effect=swap):
            self.assertTrue(cf.write_contained_bytes(self.root, target, b"new\n"))
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_bytes(), b"new\n")
        self.assert_outside_untouched()


@unittest.skipIf(POSIX, "the POSIX twin is SwapInjectionTests")
class SwapInjectionWindowsTests(unittest.TestCase):
    def test_documented_window(self) -> None:
        self.skipTest(
            "Windows has no O_NOFOLLOW or dir_fd: a directory component swapped for a junction "
            "between the checks and the open or replace is the documented residual window"
        )


class OpenContainedDirTests(_Roots):
    """AC-14: the walk helper on both branches."""

    @unittest.skipUnless(POSIX, "descriptor branch")
    def test_an_ordinary_directory_yields_a_usable_descriptor(self) -> None:
        (self.root / "a" / "b").mkdir(parents=True)
        (self.root / "a" / "b" / "f.txt").write_bytes(b"f")
        fd = cf.open_contained_dir(self.root, "a/b")
        try:
            self.assertIsInstance(fd, int)
            self.assertTrue(stat.S_ISREG(os.stat("f.txt", dir_fd=fd).st_mode))
        finally:
            os.close(fd)
        fd = cf.open_contained_dir(self.root, ())
        os.close(fd)

    @unittest.skipUnless(POSIX, "descriptor branch")
    def test_a_component_swapped_for_a_link_before_the_walk_reaches_it_is_refused(self) -> None:
        (self.root / "a" / "b").mkdir(parents=True)
        os.rename(self.root / "a" / "b", self.root / "a" / "b-moved")
        os.symlink(self.root / "a" / "b-moved", self.root / "a" / "b")  # inside, still a link
        self.refused(lambda: cf.open_contained_dir(self.root, "a/b"), cf.CAUSE_LINK_COMPONENT)
        (self.root / "file").write_bytes(b"x")
        self.refused(lambda: cf.open_contained_dir(self.root, "file"), cf.CAUSE_NOT_DIRECTORY)
        with self.assertRaises(FileNotFoundError):
            cf.open_contained_dir(self.root, "absent")

    def test_unsafe_components_are_refused(self) -> None:
        for rel in ("..", "a/../b", ("a", ".."), ("a/b",)):
            with self.subTest(rel=rel):
                self.refused(lambda rel=rel: cf.open_contained_dir(self.root, rel), cf.CAUSE_NOT_UNDER_ROOT)

    def test_the_windows_branch_returns_none_after_the_component_checks(self) -> None:
        (self.root / "a" / "b").mkdir(parents=True)
        with mock.patch.object(cf, "_dir_fd_supported", return_value=False):
            self.assertIsNone(cf.open_contained_dir(self.root, "a/b"))
            self.assertIsNone(cf.open_contained_dir(self.root, "a/missing/deeper"))
            (self.root / "file").write_bytes(b"x")
            self.refused(lambda: cf.open_contained_dir(self.root, "file"), cf.CAUSE_NOT_DIRECTORY)
            with mock.patch.object(cf, "_is_windows_link", side_effect=lambda p: p.endswith("b")):
                self.refused(lambda: cf.open_contained_dir(self.root, "a/b"), cf.CAUSE_LINK_COMPONENT)
            if POSIX:
                os.symlink(self.outside, self.root / "out")
                self.refused(lambda: cf.open_contained_dir(self.root, "out"), cf.CAUSE_LINK_COMPONENT)


class WindowsBranchTests(_Roots):
    """The path branch (no dir_fd), simulated on POSIX, and the bounded
    ``os.replace`` retry after a sharing violation (AC-16)."""

    def setUp(self) -> None:
        super().setUp()
        patcher = mock.patch.object(cf, "_dir_fd_supported", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reads_and_writes_work_by_path(self) -> None:
        target = self.root / "d" / "x.txt"
        self.assertTrue(cf.write_contained_bytes(self.root, target, b"one\n"))
        self.assertEqual(cf.read_contained_bytes(self.root, target, max_bytes=9), b"one\n")
        self.assertFalse(cf.write_contained_bytes(self.root, target, b"one\n"))
        self.assertTrue(cf.write_contained_bytes(self.root, target, b"two\n"))
        self.assertEqual(target.read_bytes(), b"two\n")
        self.assertEqual([p.name for p in target.parent.iterdir()], ["x.txt"])

    def test_a_swapped_file_identity_is_refused(self) -> None:
        target = self.root / "doc.md"
        target.write_bytes(b"inside\n")

        def swap(stage: str) -> None:
            if stage == "open":
                target.unlink()
                target.write_bytes(b"replaced\n")

        with mock.patch.object(cf, "_checkpoint", side_effect=swap):
            self.refused(lambda: cf.read_contained_bytes(self.root, target, max_bytes=99), cf.CAUSE_CHANGED)

    @unittest.skipUnless(POSIX, "symlink fixture")
    def test_a_link_leaving_the_root_is_refused(self) -> None:
        os.symlink(self.secret, self.root / "final.txt")
        self.refused(lambda: cf.write_contained_bytes(self.root, self.root / "final.txt", b"x"), cf.CAUSE_OUTSIDE)
        self.refused(lambda: cf.read_contained_bytes(self.root, self.root / "final.txt", max_bytes=99), cf.CAUSE_OUTSIDE)
        self.assert_outside_untouched()

    def test_a_replace_that_keeps_failing_is_refused_after_bounded_retries(self) -> None:
        target = self.root / "x.txt"
        sleeps: list[float] = []
        with mock.patch.object(cf, "_windows", return_value=True), \
                mock.patch.object(cf.os, "replace", side_effect=PermissionError(13, "sharing violation")) as replace, \
                mock.patch.object(cf.time, "sleep", side_effect=sleeps.append):
            error = self.refused(lambda: cf.write_contained_bytes(self.root, target, b"x"), cf.CAUSE_IN_USE)
        self.assertEqual(replace.call_count, len(cf._REPLACE_RETRY_DELAYS) + 1)
        self.assertLessEqual(sum(sleeps), 0.5 + 1e-9)
        self.assertGreater(len(sleeps), 1)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.iterdir()), [], "the temporary file is removed")
        self.assertNotIn("sharing", str(error))

    def test_a_replace_that_succeeds_on_a_retry_publishes(self) -> None:
        target = self.root / "x.txt"
        real_replace = os.replace
        calls = {"n": 0}

        def flaky(src, dst, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] < 3:
                raise PermissionError(13, "sharing violation")
            return real_replace(src, dst, *args, **kwargs)

        with mock.patch.object(cf, "_windows", return_value=True), \
                mock.patch.object(cf.os, "replace", side_effect=flaky), \
                mock.patch.object(cf.time, "sleep"):
            self.assertTrue(cf.write_contained_bytes(self.root, target, b"published\n"))
        self.assertEqual(target.read_bytes(), b"published\n")
        self.assertEqual(calls["n"], 3)

    def test_off_windows_a_permission_error_is_not_retried(self) -> None:
        with mock.patch.object(cf, "_windows", return_value=False), \
                mock.patch.object(cf.os, "replace", side_effect=PermissionError(13, "denied")) as replace:
            with self.assertRaises(PermissionError) as caught:
                cf.write_contained_bytes(self.root, self.root / "x.txt", b"x")
        self.assertEqual(replace.call_count, 1)
        self.assertIsNone(caught.exception.filename)


class MemberDocDelegationTests(_Roots):
    """AC-9: the member-doc reader delegates, keeps its own rule and cause text."""

    # Every cause string ``wave_lint_lib.helpers._refusal_cause`` maps, with its class.
    PINNED = {
        "not a regular file": "link",
        "changed while being opened": "link",
        "resolves to a framework runtime lock": "link",
        "exceeds the member document size cap": "size",
        "not in its expected folder": "outside",
        "could not be resolved": "outside",
        "resolves outside its folder": "outside",
        "resolves outside the repository": "outside",
    }

    def _classes(self) -> dict:
        from wave_lint_lib import helpers

        return {
            helpers.RECORD_CAUSE_LINK: "link",
            helpers.RECORD_CAUSE_SIZE: "size",
            helpers.RECORD_CAUSE_OUTSIDE: "outside",
        }

    def test_every_cause_string_maps_to_its_pinned_class(self) -> None:
        from lifecycle_gate_support import MemberDocRefused
        from wave_lint_lib import helpers

        classes = self._classes()
        for cause, expected in self.PINNED.items():
            with self.subTest(cause=cause):
                self.assertEqual(classes[helpers._refusal_cause(MemberDocRefused(cause))], expected)

    def test_every_cause_the_reader_can_raise_is_pinned(self) -> None:
        import lifecycle_gate_support as lgs

        source = source_path("lifecycle_gate_support").read_text(encoding="utf-8")
        tree = ast.parse(source)
        reader = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_read_member_doc_bytes")
        literal = {
            node.args[0].value
            for node in ast.walk(reader)
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "MemberDocRefused"
            and node.args and isinstance(node.args[0], ast.Constant)
        }
        primitive = {
            lgs._MEMBER_DOC_CAUSES.get(value, value)
            for name, value in vars(cf).items()
            if name.startswith("CAUSE_")
            # write-only and walk-only causes cannot reach a read refusal unmapped
            and name not in {"CAUSE_IN_USE", "CAUSE_NO_TEMPORARY"}
        }
        self.assertLessEqual(literal | primitive, set(self.PINNED), (literal | primitive) - set(self.PINNED))

    def test_a_member_doc_read_goes_through_the_primitive(self) -> None:
        import lifecycle_gate_support as lgs

        folder = self.root / "docs" / "plans"
        folder.mkdir(parents=True)
        doc = folder / "1aaaa-bug x.md"
        doc.write_bytes(b"# Doc\n")
        primitive = lgs.contained_files  # the module lgs bound (a server load may re-import it)
        with mock.patch.object(primitive, "read_contained", wraps=primitive.read_contained) as spy:
            self.assertEqual(lgs._read_member_doc_bytes(folder, doc, root=self.root), b"# Doc\n")
        self.assertEqual(spy.call_count, 1)
        # inert-by-design: a value patch (a smaller cap), not a mock; the refusal below is the assertion.
        with mock.patch.object(lgs, "MEMBER_DOC_MAX_BYTES", 3):
            with self.assertRaises(lgs.MemberDocRefused) as caught:
                lgs._read_member_doc_bytes(folder, doc, root=self.root)
        self.assertEqual(caught.exception.strerror, "exceeds the member document size cap")


class RendererCensusTests(unittest.TestCase):
    """AC-15: both surface renderers read and write repository files only
    through ``contained_files`` (directly or through their helpers)."""

    FORBIDDEN_ATTRS = {"read_text", "read_bytes", "write_text", "write_bytes", "open", "chmod", "touch"}
    # Function -> why a direct open there is not a repository read or write
    # through a path (Requirement 8's listed exclusions).
    EXCLUSIONS = {
        "render_platform_surfaces.py": {
            "main": "the --manifest output is a caller-owned temporary file outside the repository",
        },
        "render_agent_surfaces.py": {
            "_exclusive_open": "the exclusive no-follow create, relative to an open_contained_dir descriptor",
        },
    }

    @classmethod
    def census(cls, source: str, module: str) -> list[str]:
        tree = ast.parse(source)
        parents: dict = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        def owner(node) -> str:
            cursor = parents.get(node)
            while cursor is not None and not isinstance(cursor, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cursor = parents.get(cursor)
            return cursor.name if cursor is not None else "<module>"

        problems: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            hit = None
            if isinstance(func, ast.Attribute) and func.attr in cls.FORBIDDEN_ATTRS:
                hit = ast.unparse(func)
            elif isinstance(func, ast.Name) and func.id == "open":
                hit = "open"
            if hit is None:
                continue
            where = owner(node)
            if where in cls.EXCLUSIONS.get(module, {}):
                continue
            problems.append(f"{module}:{node.lineno}: {where}: {hit}(...)")
        return problems

    def test_neither_renderer_reads_or_writes_a_repository_file_directly(self) -> None:
        for module in ("render_platform_surfaces.py", "render_agent_surfaces.py"):
            with self.subTest(module=module):
                source = source_path(module.removesuffix(".py")).read_text(encoding="utf-8")
                self.assertEqual(self.census(source, module), [])

    def test_the_census_reports_a_new_direct_read_or_write(self) -> None:
        for snippet in (
            "def f(p):\n    return p.read_text()\n",
            "def f(p):\n    p.write_text('x')\n",
            "def f(p):\n    return open(p).read()\n",
            "def f(p):\n    p.chmod(0o755)\n",
            "def f(p):\n    with p.open('rb') as h:\n        return h.read()\n",
        ):
            with self.subTest(snippet=snippet):
                self.assertEqual(len(self.census(snippet, "render_agent_surfaces.py")), 1)
        excluded = "def _exclusive_open(p):\n    return os.open(p, 0)\n"
        self.assertEqual(self.census(excluded, "render_agent_surfaces.py"), [])

    def test_the_writers_route_through_the_primitive(self) -> None:
        sources = {
            module: ast.parse(source_path(module.removesuffix(".py")).read_text(encoding="utf-8"))
            for module in ("render_platform_surfaces.py", "render_agent_surfaces.py")
        }

        def text(module: str, name: str) -> str:
            node = next(n for n in ast.walk(sources[module]) if isinstance(n, ast.FunctionDef) and n.name == name)
            return ast.unparse(node)

        self.assertIn("contained_files.write_contained_bytes(", text("render_platform_surfaces.py", "write_text"))
        self.assertIn("contained_files.read_contained_bytes(", text("render_platform_surfaces.py", "read_repo_text"))
        self.assertIn("contained_files.write_contained_bytes(", text("render_agent_surfaces.py", "_write_repo_bytes"))
        self.assertIn("contained_files.read_contained_bytes(", text("render_agent_surfaces.py", "_read_repo_bytes"))
        self.assertIn("contained_files.read_contained_bytes(", text("render_agent_surfaces.py", "_framework_read_text"))
        self.assertIn("contained_files.open_contained_dir(", text("render_agent_surfaces.py", "_exclusive_parent"))


if __name__ == "__main__":
    unittest.main()
