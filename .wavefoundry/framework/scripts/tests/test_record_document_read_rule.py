"""Docs-lint reads every record document under the member-doc rule (wave 200xy, change 200v1).

A record document is any ``*.md`` entry lexically under the resolved waves or plans root. Every
docs-lint read of one goes through ``lifecycle_gate_support._read_member_doc_bytes``, every
docs-lint enumeration yields one only when ``lstat`` shows a regular file, and a refused entry is
reported once, by its own path and a cause class, never by anything read from its target. The
secrets scanner, which also runs outside docs-lint, surfaces the same refusal through its skip
channel.
"""
from __future__ import annotations

import builtins
import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import record_paths  # noqa: E402
import vocabulary_profile  # noqa: E402
from record_layout_support import localized_docs_lint_fixture  # noqa: E402

DOCS_LINT_SCRIPT = SCRIPTS_ROOT / "docs_lint.py"
SCAN_RULES = SCRIPTS_ROOT.parent / "scan-rules.toml"
FIXTURE_WAVE_DIR = "change-2026-03"
LINK_CAUSE = "(a link or special file)"
_TIMEOUT = 300


def _python() -> str:
    return os.environ.get("PYTHON", sys.executable)


def _can_symlink(base: Path) -> bool:
    probe = base / ".symlink-probe"
    try:
        probe.symlink_to(base)
    except (OSError, NotImplementedError):
        return False
    probe.unlink()
    return True


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false", *args],
        cwd=root, check=True, capture_output=True,
    )


class _RecordFixture(unittest.TestCase):
    """The docs-lint fixture with the shipped scan rules, beside an outside directory."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="wf-record-rule-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.root = self.base / "repo"
        localized_docs_lint_fixture(self.root)
        rules = self.root / ".wavefoundry" / "framework" / "scan-rules.toml"
        rules.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCAN_RULES, rules)
        roots = record_paths.load_record_roots(self.root)
        self.waves, self.plans = roots.waves, roots.plans
        self.plans.mkdir(parents=True, exist_ok=True)
        self.wave_dir = self.waves / FIXTURE_WAVE_DIR
        self.outside = self.base / "outside"
        self.outside.mkdir()
        self.inside_targets = self.root / "link-targets"
        self.inside_targets.mkdir()

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def target(self, inside: bool, name: str, sentinel: str) -> Path:
        folder = self.inside_targets if inside else self.outside
        path = folder / f"{name}.md"
        path.write_text(
            f"# {sentinel}\n\n{vocabulary_profile.BACKREF_LABEL}: `{sentinel}-wave`\n"
            f"Owner: {sentinel}\nStatus: {sentinel}\nLast verified: 2026-01-01\n",
            encoding="utf-8",
        )
        return path

    def link(self, entry: Path, target: Path) -> Path:
        entry.symlink_to(target)
        return entry

    def run_lint(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PROJECT_ROOT"] = str(self.root)
        env["PYTHONPATH"] = str(SCRIPTS_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [_python(), "-B", str(DOCS_LINT_SCRIPT), *args],
            cwd=self.root, env=env, text=True, capture_output=True, check=False, timeout=_TIMEOUT,
        )

    @staticmethod
    def errors(result: subprocess.CompletedProcess[str]) -> list[str]:
        return [line for line in result.stderr.splitlines() if line.startswith("ERROR: ")]

    def assert_reported_once(self, result: subprocess.CompletedProcess[str], entry: Path) -> None:
        rel = self.rel(entry)
        hits = [line for line in self.errors(result) if rel in line]
        self.assertEqual(len(hits), 1, result.stderr)
        self.assertEqual(
            hits[0],
            f"ERROR: {rel}: record document refused (a link or special file); it was not read. "
            "Replace it with the document itself.",
        )


class LinkedRecordDocumentTests(_RecordFixture):
    """AC-1: links under the waves and plans roots, to targets inside and outside the
    repository, and a wave folder whose record file is a link beside a non-empty ledger."""

    def test_each_link_is_reported_once_and_no_target_text_is_echoed(self) -> None:
        if not _can_symlink(self.base):
            self.skipTest("symbolic links are unavailable")
        sentinels = {}
        entries = []
        for where, folder in (("waves", self.wave_dir), ("plans", self.plans)):
            for inside in (True, False):
                name = f"linked-{where}-{'in' if inside else 'out'}"
                sentinel = f"SENTINEL{where.upper()}{'IN' if inside else 'OUT'}"
                target = self.target(inside, f"target-{name}", sentinel)
                sentinels[sentinel] = target
                entries.append(self.link(folder / f"{name}.md", target))
        linked_wave = self.waves / "200zz linked-record"
        linked_wave.mkdir()
        record_sentinel = "SENTINELRECORD"
        record_target = self.target(False, "record-target", record_sentinel)
        sentinels[record_sentinel] = record_target
        entries.append(self.link(linked_wave / vocabulary_profile.RECORD_FILENAME, record_target))
        (linked_wave / "events.jsonl").write_text("{}\n", encoding="utf-8")

        result = self.run_lint()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for entry in entries:
            with self.subTest(entry=self.rel(entry)):
                self.assert_reported_once(result, entry)
        output = result.stdout + result.stderr
        for sentinel, target in sentinels.items():
            self.assertNotIn(sentinel, output)
            self.assertNotIn(str(target), output)
            self.assertNotIn(target.name, output)
        self.assertNotIn(str(self.outside), output)
        self.assertNotIn("orphaned review ledger", output)


@unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX only")
class FifoRecordDocumentTests(_RecordFixture):
    """AC-2: a FIFO named ``*.md`` in a wave folder and in the plans root never blocks a run."""

    def test_fifos_are_reported_once_without_blocking(self) -> None:
        fifos = [self.wave_dir / "fifo-member.md", self.plans / "fifo-plan.md"]
        for fifo in fifos:
            os.mkfifo(fifo)
        try:
            result = self.run_lint()
        except subprocess.TimeoutExpired:  # pragma: no cover - the regression
            self.fail(f"docs-lint blocked on a FIFO for more than {_TIMEOUT} seconds")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for fifo in fifos:
            with self.subTest(entry=self.rel(fifo)):
                self.assert_reported_once(result, fifo)


class _OpenSpy:
    """Records every open of a record document (a ``*.md`` path under the waves or plans
    root) through ``Path.read_text``, ``Path.read_bytes``, ``Path.open``, ``builtins.open`` and
    ``os.open``, except calls whose caller frame is ``_read_member_doc_bytes``; and every
    path ``_read_member_doc_bytes`` is asked to read."""

    def __init__(self, waves: Path, plans: Path) -> None:
        self.roots = (waves, plans)
        self.opens: list[tuple[str, str]] = []
        self.member_reads: list[Path] = []

    def _is_record(self, value) -> bool:
        if isinstance(value, int):
            return False
        try:
            path = Path(os.fsdecode(os.fspath(value)))
        except TypeError:
            return False
        if path.suffix != ".md":
            return False
        path = Path(os.path.abspath(path))
        return any(path == root or root in path.parents for root in self.roots)

    @staticmethod
    def _from_member_reader() -> bool:
        caller = sys._getframe(2)
        return caller.f_code.co_name == "_read_member_doc_bytes"

    def _wrap(self, name: str, real, path_index: int = 0):
        spy = self

        def wrapper(*args, **kwargs):
            if len(args) > path_index and spy._is_record(args[path_index]) and not spy._from_member_reader():
                spy.opens.append((name, str(args[path_index])))
            return real(*args, **kwargs)

        return wrapper

    def patches(self):
        import lifecycle_gate_support as lgs

        real_member = lgs._read_member_doc_bytes
        spy = self

        def member(folder, path, *, root):
            spy.member_reads.append(Path(path))
            return real_member(folder, path, root=root)

        return (
            mock.patch.object(pathlib.Path, "read_text", self._wrap("Path.read_text", pathlib.Path.read_text)),
            mock.patch.object(pathlib.Path, "read_bytes", self._wrap("Path.read_bytes", pathlib.Path.read_bytes)),
            mock.patch.object(pathlib.Path, "open", self._wrap("Path.open", pathlib.Path.open)),
            mock.patch.object(builtins, "open", self._wrap("open", builtins.open)),
            mock.patch.object(os, "open", self._wrap("os.open", os.open)),
            # inert-by-design: a recording wrapper, not a mock; the test asserts on its member_reads list.
            mock.patch.object(lgs, "_read_member_doc_bytes", member),
        )


class ReadPathSpyTests(_RecordFixture):
    """AC-3: during a whole docs-lint run on a git fixture, every record document read goes
    through ``_read_member_doc_bytes`` and nothing else opens one, on every platform."""

    def test_every_record_read_goes_through_the_member_doc_rule(self) -> None:
        from wave_lint_lib import cli, helpers

        _git(self.root, "init", "-q")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "base")
        staged = self.plans / "staged-plan.md"
        staged.write_text("# Staged\n\nOwner: x\nStatus: planned\nLast verified: 2026-01-01\n", encoding="utf-8")
        _git(self.root, "add", self.rel(staged))
        untracked = self.wave_dir / "untracked-note.md"
        untracked.write_text("# Note\n\nOwner: x\nStatus: active\nLast verified: 2026-01-01\n", encoding="utf-8")

        record_docs = sorted(
            path for root in (self.waves, self.plans) for path in root.rglob("*.md")
            if path.is_file() and not path.is_symlink()
        )
        self.assertIn(staged, record_docs)
        self.assertIn(untracked, record_docs)

        spy = _OpenSpy(self.waves, self.plans)
        out, err = io.StringIO(), io.StringIO()
        helpers.read_text_cache_clear()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, {"PROJECT_ROOT": str(self.root)}))
            stack.enter_context(mock.patch.object(sys, "argv", ["docs_lint.py"]))
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            for patch in spy.patches():
                stack.enter_context(patch)
            cli.main()
        self.assertEqual(spy.opens, [], err.getvalue())
        read = {Path(os.path.abspath(path)) for path in spy.member_reads}
        missing = [self.rel(path) for path in record_docs if path not in read]
        self.assertEqual(missing, [], err.getvalue())


class ChangedModeTests(_RecordFixture):
    """AC-4: the incremental run (the post-edit hook path) reports a changed linked record
    document once, without its target."""

    def test_changed_run_reports_the_link_once(self) -> None:
        if not _can_symlink(self.base):
            self.skipTest("symbolic links are unavailable")
        _git(self.root, "init", "-q")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "base")
        regular = self.plans / "regular-plan.md"
        regular.write_text("# Regular\n\nOwner: x\nStatus: planned\nLast verified: 2026-01-01\n",
                           encoding="utf-8")
        sentinel = "SENTINELCHANGED"
        target = self.target(False, "changed-target", sentinel)
        entry = self.link(self.wave_dir / "changed-link.md", target)

        result = self.run_lint("--changed")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assert_reported_once(result, entry)
        output = result.stdout + result.stderr
        self.assertNotIn(sentinel, output)
        self.assertNotIn(str(target), output)
        self.assertNotIn(str(self.outside), output)
        self.assertNotIn(self.rel(entry), "\n".join(
            line for line in self.errors(result) if "record document refused" not in line))

    def test_a_repeated_in_process_changed_run_reports_no_stale_refusal(self) -> None:
        # The long-lived MCP server runs ``--changed`` in-process; a refusal from the
        # previous run must not outlive the link once it is replaced by the document.
        if not _can_symlink(self.base):
            self.skipTest("symbolic links are unavailable")
        from wave_lint_lib import cli, helpers

        _git(self.root, "init", "-q")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "base")
        entry = self.link(self.wave_dir / "repeat-link.md", self.target(True, "repeat-target", "REPEAT"))
        rel = self.rel(entry)

        def refused() -> list[str]:
            helpers.read_text_cache_clear()  # what each docs-lint main() does first
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                outcome = cli._run_incremental_checks(self.root)
            self.assertIsNotNone(outcome)
            return [line for line in outcome[0] if rel in line and "record document refused" in line]

        self.assertEqual(len(refused()), 1)
        entry.unlink()
        entry.write_text("# Repeat\n\nOwner: x\nStatus: planned\nLast verified: 2026-01-01\n", encoding="utf-8")
        self.assertEqual(refused(), [])


class EnumerationRuleTests(_RecordFixture):
    """Requirement 3: every docs-lint enumeration under a record root yields an entry only
    when ``lstat`` shows a regular file, and records the refusal without reading."""

    def test_enumerations_do_not_yield_links(self) -> None:
        if not _can_symlink(self.base):
            self.skipTest("symbolic links are unavailable")
        from wave_lint_lib import helpers, wave_validators

        target = self.target(True, "enum-target", "ENUMSENTINEL")
        member = self.link(self.wave_dir / "enum-link.md", target)
        plan = self.link(self.plans / "enum-plan.md", target)
        linked_wave = self.waves / "200zy enum-wave"
        linked_wave.mkdir()
        record = self.link(linked_wave / vocabulary_profile.RECORD_FILENAME, target)
        roots = record_paths.load_record_roots(self.root)
        helpers.read_text_cache_clear()
        with mock.patch.object(helpers, "read_record_text",
                               side_effect=AssertionError("enumeration must not read")):
            docs = list(helpers.iter_markdown_docs(self.root))
            folder_docs = wave_validators._wave_folder_docs(self.wave_dir, self.root)
            wave_dirs = wave_validators.lint_wave_dirs(self.root, roots)
        for entry in (member, plan, record):
            self.assertNotIn(entry, docs)
        self.assertNotIn(member, folder_docs)
        self.assertIn(self.wave_dir / vocabulary_profile.RECORD_FILENAME, folder_docs)
        self.assertNotIn(linked_wave, wave_dirs)
        self.assertIn(self.wave_dir, wave_dirs)
        self.assertEqual(
            helpers.record_refusals(),
            {self.rel(entry): "a link or special file" for entry in (member, plan, record)},
        )


class RecordReadCacheTests(_RecordFixture):
    """Requirement 2: the record reader's cache is keyed on the entry's own identity, so an
    entry swapped for a link never serves the cached content of its earlier file."""

    def test_a_swapped_link_is_refused_not_served_from_the_cache(self) -> None:
        if not _can_symlink(self.base):
            self.skipTest("symbolic links are unavailable")
        from wave_lint_lib import helpers

        helpers.read_text_cache_clear()
        doc = self.plans / "cached-plan.md"
        doc.write_text("# Cached\n\nCACHEDBODY\n", encoding="utf-8")
        self.assertIn("CACHEDBODY", helpers.read_record_text(self.root, doc))
        stat_before = os.stat(doc)
        # Same size and modification time as the original, so a following
        # ``stat`` key could not tell them apart.
        target = self.outside / "swap-target.md"
        target.write_text("# Swaped\n\nSWAPSENTIN\n", encoding="utf-8")
        self.assertEqual(target.stat().st_size, stat_before.st_size)
        os.utime(target, ns=(stat_before.st_atime_ns, stat_before.st_mtime_ns))
        doc.unlink()
        doc.symlink_to(target)
        self.assertIsNone(helpers.read_record_text(self.root, doc))
        self.assertEqual(helpers.record_refusals(), {self.rel(doc): "a link or special file"})
        helpers.read_text_cache_clear()
        self.assertEqual(helpers.record_refusals(), {})

    def test_read_time_refusals_carry_their_cause_class(self) -> None:
        import lifecycle_gate_support as lgs
        from wave_lint_lib import helpers

        helpers.read_text_cache_clear()
        large = self.plans / "large-plan.md"
        large.write_text("# Large\n" + "x" * 64 + "\n", encoding="utf-8")
        # inert-by-design: a lowered size cap value, not a callable; the refusal below is asserted.
        with mock.patch.object(lgs, "MEMBER_DOC_MAX_BYTES", 16):
            self.assertIsNone(helpers.read_record_text(self.root, large))
        expected = {self.rel(large): "over the size cap"}
        if _can_symlink(self.base):
            away = self.outside / "away-folder"
            away.mkdir()
            (away / "doc.md").write_text("# AWAYSENTINEL\n", encoding="utf-8")
            folder = self.plans / "linked-folder"
            folder.symlink_to(away, target_is_directory=True)
            self.assertIsNone(helpers.read_record_text(self.root, folder / "doc.md"))
            expected[self.rel(folder / "doc.md")] = "outside its folder or the repository"
        self.assertEqual(helpers.record_refusals(), expected)
        for line in helpers.record_refusal_failures():
            self.assertNotIn("AWAYSENTINEL", line)
            self.assertNotIn(str(self.outside), line)

    def test_a_document_changed_during_the_read_is_not_cached(self) -> None:
        # The entry's identity changes between the before and the after ``lstat``:
        # the text read is not cached, so restoring the original identity over new
        # content of the same size cannot serve the earlier text.
        import lifecycle_gate_support as lgs
        from wave_lint_lib import helpers

        helpers.read_text_cache_clear()
        doc = self.plans / "racing-plan.md"
        doc.write_text("# ONE\n", encoding="utf-8")
        first = os.lstat(doc)
        real_read = lgs._read_member_doc_bytes

        def read_then_change(folder, path, **kwargs):
            data = real_read(folder, path, **kwargs)
            with open(path, "r+b") as handle:  # in place: same inode, same size
                handle.write(b"# TWO\n")
            os.utime(path, ns=(first.st_atime_ns, first.st_mtime_ns + 5_000_000_000))
            return data

        # inert-by-design: a wrapper that delegates to the real reader and then changes the file; the test asserts on the returned text.
        with mock.patch.object(lgs, "_read_member_doc_bytes", read_then_change):
            self.assertEqual(helpers.read_record_text(self.root, doc), "# ONE\n")
        os.utime(doc, ns=(first.st_atime_ns, first.st_mtime_ns))
        self.assertEqual(os.lstat(doc).st_ino, first.st_ino)
        self.assertEqual(helpers.read_record_text(self.root, doc), "# TWO\n")

    def test_an_edited_document_is_read_again(self) -> None:
        from wave_lint_lib import helpers

        helpers.read_text_cache_clear()
        doc = self.plans / "edited-plan.md"
        doc.write_text("# One\n", encoding="utf-8")
        self.assertEqual(helpers.read_record_text(self.root, doc), "# One\n")
        doc.write_text("# Two, longer\r\n", encoding="utf-8")
        self.assertEqual(helpers.read_record_text(self.root, doc), "# Two, longer\n")


class SecretsScannerSkipTests(_RecordFixture):
    """AC-13: outside docs-lint, the secrets scanner surfaces a linked record document through
    its existing skip channel, never as a clean scan and never with target text."""

    def _scan(self, **kwargs) -> tuple[list[str], str]:
        from wave_lint_lib import secrets_validators as sv

        err = io.StringIO()
        with mock.patch.object(sv, "get_current_git_user_email", return_value="t@example.com"), \
                contextlib.redirect_stderr(err):
            failures = sv.check_hardcoded_secrets(self.root, max_workers=1, **kwargs)
        return failures, err.getvalue()

    def test_a_linked_record_document_is_skipped_visibly(self) -> None:
        if not _can_symlink(self.base):
            self.skipTest("symbolic links are unavailable")
        from wave_lint_lib import secrets_validators as sv

        sentinel = "SENTINELSECRETS"
        target = self.target(False, "secrets-target", sentinel)
        target.write_text(target.read_text(encoding="utf-8")
                          + 'aws_secret_access_key = "AKIAIOSFODNN7EXAMPLEKEY0123456789abcd"\n',
                          encoding="utf-8")
        entry = self.link(self.plans / "linked-secret.md", target)
        rel = self.rel(entry)
        expected_line = (f"secrets-scan: SKIPPED {rel} (record document refused: "
                         "a link or special file)")
        for label, kwargs in (("file set", {"scan_all": True}), ("explicit files", {"files": [entry]})):
            with self.subTest(path=label):
                failures, stderr = self._scan(**kwargs)
                self.assertIn(expected_line, stderr)
                rows = [row for row in sv._SCANNER_SKIPS if row["file"] == rel]
                self.assertEqual(rows, [{"file": rel, "reason": "record document refused",
                                         "detail": "a link or special file"}])
                self.assertIn(rel, sv.unpublished_scanner_skips())
                output = stderr + "\n".join(failures)
                self.assertNotIn(sentinel, output)
                self.assertNotIn(str(target), output)
                self.assertNotIn(str(self.outside), output)
                self.assertNotIn("AKIAIOSFODNN7", output)
                ledger = self.root / ".wavefoundry" / "index" / "scan" / "guard-skips.json"
                self.assertIn(rel, ledger.read_text(encoding="utf-8"))

    def test_the_size_guard_runs_before_the_record_read(self) -> None:
        from wave_lint_lib import secrets_validators as sv

        doc = self.plans / "large-plan.md"
        doc.write_text("# Large\n" + "x" * 64 + "\n", encoding="utf-8")
        import lifecycle_gate_support as lgs

        # inert-by-design: the size guard must refuse before any record read, so the stub never runs.
        with mock.patch.object(sv, "MAX_FILE_BYTES", 16), \
                mock.patch.object(lgs, "_read_member_doc_bytes",
                                  side_effect=AssertionError("read before the size guard")):
            _failures, stderr = self._scan(files=[doc])
        self.assertIn(f"secrets-scan: SKIPPED {self.rel(doc)} (file too large", stderr)


if __name__ == "__main__":
    unittest.main()
