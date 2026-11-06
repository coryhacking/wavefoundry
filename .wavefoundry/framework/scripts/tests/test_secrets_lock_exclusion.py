"""Wave 1zimc (1zimg Requirement 9, AC-11): the secrets scanner never opens a
Wavefoundry lock file.

The lifecycle lock is a process-owned record lock on POSIX, so an in-process
scan that opened and closed ``.wavefoundry/lifecycle-mutation.lock`` would
release the server's own hold. The scanner's file selection skips every file
under ``.wavefoundry/locks/`` and every ``*.lock`` file elsewhere under
``.wavefoundry/`` at every branch, and an explicit ``files=`` list is filtered
the same way. ``*.lock`` files outside ``.wavefoundry/`` are still scanned.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent
FRAMEWORK_ROOT = SCRIPTS_ROOT.parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib import secrets_validators as sv  # noqa: E402
from wave_lint_lib.constants import SCAN_FINDINGS_PATH, SCAN_RULES_FRAMEWORK_PATH  # noqa: E402

# A credential the shipped ``generic-api-key`` rule matches; split so this
# source file carries no matching literal.
_API_KEY_LINE = 'api_key = "' + "Zq8mT3vXk9Lp2Wr7" + "Ny4Bc6Hd1Fs5Gj0A" + '"\n'

_LIFECYCLE_REL = ".wavefoundry/lifecycle-mutation.lock"
_EXCLUDED_RELS = (
    _LIFECYCLE_REL,
    ".wavefoundry/locks/notes.txt",
    ".wavefoundry/locks/producers/abc.lock",
    ".wavefoundry/index/index-build.lock",
)

_TRY_LIFECYCLE = (
    "import sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from pathlib import Path\n"
    "import lifecycle_lock\n"
    "try:\n"
    "    with lifecycle_lock.lifecycle_mutation_lock(Path(sys.argv[2])):\n"
    "        print('acquired', flush=True)\n"
    "except lifecycle_lock.LifecycleLockBusy:\n"
    "    print('busy', flush=True)\n"
)


def _other_process_lifecycle(root: Path) -> str:
    """One acquire attempt from a fresh interpreter (never a fork)."""
    out = subprocess.run(
        [sys.executable, "-B", "-c", _TRY_LIFECYCLE, str(SCRIPTS_ROOT), str(root)],
        capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
    )
    return out.stdout.strip() or f"<no answer: rc={out.returncode} {out.stderr[-2000:]}>"


def _git(root: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
         "-c", "commit.gpgsign=false", *args],
        cwd=root, capture_output=True, text=True, check=True,
    )
    return out.stdout


def _plant(root: Path) -> None:
    """A repository with the shipped ruleset, lock files and a Cargo.lock."""
    (root / "docs").mkdir(parents=True, exist_ok=True)
    rules = root / SCAN_RULES_FRAMEWORK_PATH
    rules.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FRAMEWORK_ROOT / "scan-rules.toml", rules)
    for rel in _EXCLUDED_RELS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_API_KEY_LINE, encoding="utf-8")
    (root / "Cargo.lock").write_text('[[package]]\nname = "x"\n' + _API_KEY_LINE, encoding="utf-8")
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")


def _excluded(rel: str) -> bool:
    """The test's own statement of the Requirement 9 rule (an independent oracle)."""
    norm = rel.replace("\\", "/").lower()
    return norm.startswith(".wavefoundry/") and (
        norm.startswith(".wavefoundry/locks/") or norm.endswith(".lock")
    )


def _rels(root: Path, paths) -> set[str]:
    return {Path(p).relative_to(root).as_posix() for p in paths}


class _ScanSpy:
    """Record every path the scan hands to its per-file scanner or opens."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.scanned: list[str] = []
        self.opened: list[str] = []
        self._real_scan = sv._scan_with_outcome
        self._real_open = pathlib.Path.open

    def _scan(self, fp, rel, *args, **kwargs):
        self.scanned.append(rel)
        return self._real_scan(fp, rel, *args, **kwargs)

    def _open(self, path_self, *args, **kwargs):
        self.opened.append(os.path.realpath(os.fspath(path_self)))
        return self._real_open(path_self, *args, **kwargs)

    def patches(self):
        spy = self

        def path_open(path_self, *args, **kwargs):
            return spy._open(path_self, *args, **kwargs)

        return (
            patch.object(sv, "_scan_with_outcome", self._scan),
            patch.object(pathlib.Path, "open", path_open),
        )

    def touched_excluded(self) -> list[str]:
        hits = [rel for rel in self.scanned if _excluded(rel)]
        excluded = {os.path.realpath(self.root / rel) for rel in _EXCLUDED_RELS}
        return hits + [path for path in self.opened if path in excluded]


def _scan(root: Path, **kwargs) -> list[str]:
    with patch.object(sv, "get_current_git_user_email", return_value="t@example.com"):
        return sv.check_hardcoded_secrets(root, max_workers=1, **kwargs)


class LockExclusionPredicateTests(unittest.TestCase):
    def test_predicate_covers_locks_folder_and_lock_suffix_case_insensitively(self):
        excluded = (
            ".wavefoundry/locks/notes.txt",
            ".wavefoundry/locks/producers/abc.lock",
            ".wavefoundry/lifecycle-mutation.lock",
            ".wavefoundry/index/index-build.lock",
            ".wavefoundry/framework/test-run.lock",
            ".WaveFoundry/locks/x",
            ".wavefoundry/index/X.LOCK",
            ".wavefoundry\\locks\\win.txt",
        )
        kept = (
            "Cargo.lock",
            "sub/Gemfile.lock",
            "docs/notes.lock.md",
            ".wavefoundry/framework/scan-rules.toml",
            ".wavefoundry/locksmith/readme.txt",
            "x/.wavefoundry/locks/nested.txt",
        )
        for rel in excluded:
            self.assertTrue(sv.is_wavefoundry_lock_path(rel), rel)
        for rel in kept:
            self.assertFalse(sv.is_wavefoundry_lock_path(rel), rel)


class OutsideGitWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        _plant(self.root)
        self.assertFalse(sv._is_inside_git(self.root), "fixture must be outside any git worktree")

    def test_selection_outside_git_skips_lock_files(self):
        selected = _rels(self.root, sv._get_all_files(self.root))
        self.assertIn("Cargo.lock", selected)
        self.assertEqual(sorted(r for r in selected if _excluded(r)), [])

    @unittest.skipIf(
        os.name == "nt",
        "msvcrt locks belong to the handle, so a second handle never drops the hold on Windows",
    )
    def test_in_process_scan_keeps_the_lifecycle_hold(self):
        import lifecycle_lock

        spy = _ScanSpy(self.root)
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            first, second = spy.patches()
            with first, second:
                failures = _scan(self.root, scan_all=True)
            after = _other_process_lifecycle(self.root)
        self.assertEqual(after, "busy", "the in-process scan released this process's lifecycle hold")
        self.assertEqual(spy.touched_excluded(), [])
        self.assertTrue(any(f.startswith("Cargo.lock:") for f in failures), failures)

    def test_root_cargo_lock_is_still_scanned_and_reported(self):
        failures = _scan(self.root, scan_all=True)
        self.assertTrue(
            any(f.startswith("Cargo.lock:") and "generic-api-key" in f for f in failures), failures
        )
        self.assertFalse(any(f.startswith(".wavefoundry") for f in failures), failures)

    def test_explicit_files_never_open_excluded_paths(self):
        lock_index = self.root / ".wavefoundry/index/X.LOCK"
        lock_index.write_text(_API_KEY_LINE, encoding="utf-8")
        files = [self.root / rel for rel in _EXCLUDED_RELS] + [
            lock_index,
            self.root / ".WaveFoundry/locks/x",
            self.root / "Cargo.lock",
        ]
        spy = _ScanSpy(self.root)
        first, second = spy.patches()
        with first, second:
            failures = _scan(self.root, files=files)
        self.assertEqual(spy.scanned, ["Cargo.lock"])
        self.assertEqual(spy.touched_excluded(), [])
        self.assertTrue(any(f.startswith("Cargo.lock:") for f in failures), failures)

    def test_existing_findings_for_excluded_paths_are_swept(self):
        stale = {
            "id": "1aaaa-sec",
            "file": ".wavefoundry/locks/notes.txt",
            "line": 1,
            "rule": "generic-api-key",
            "status": "false-positive",
            "match_sha256": "0" * 64,
            "confirmations": [],
        }
        kept = dict(stale, id="1aaab-sec", file="app.py")
        # A non-lock file under .wavefoundry/ keeps its finding: the sweep
        # removes only what is_wavefoundry_lock_path matches.
        (self.root / ".wavefoundry").mkdir(exist_ok=True)
        (self.root / ".wavefoundry/notalock.txt").write_text("x\n", encoding="utf-8")
        kept_wf = dict(stale, id="1aaac-sec", file=".wavefoundry/notalock.txt")
        findings = self.root / SCAN_FINDINGS_PATH
        findings.write_text(json.dumps([stale, kept, kept_wf], indent=2) + "\n", encoding="utf-8")
        _scan(self.root, scan_all=True)
        files = [entry.get("file") for entry in json.loads(findings.read_text(encoding="utf-8"))]
        self.assertNotIn(".wavefoundry/locks/notes.txt", files)
        self.assertIn("app.py", files)
        self.assertIn(".wavefoundry/notalock.txt", files)


class InsideGitWorktreeTests(unittest.TestCase):
    """A worktree whose ignore file lacks the managed lock lines."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        _git(self.root, "init", "-q")
        _plant(self.root)
        tracked = self.root / ".wavefoundry/locks/committed.txt"
        tracked.write_text("one\n", encoding="utf-8")
        _git(self.root, "add", "app.py", "Cargo.lock", ".wavefoundry/locks/committed.txt")
        _git(self.root, "commit", "-q", "-m", "init")
        tracked.write_text("two\n", encoding="utf-8")  # a tracked, changed lock-folder file
        (self.root / "app.py").write_text("x = 2\n", encoding="utf-8")
        self.assertTrue(sv._is_inside_git(self.root))

    def _assert_no_lock_paths(self, paths, *, expect: str) -> None:
        selected = _rels(self.root, paths)
        self.assertIn(expect, selected)
        self.assertEqual(sorted(r for r in selected if _excluded(r)), [])

    def test_ls_files_branch_skips_lock_files(self):
        self._assert_no_lock_paths(sv._get_all_files(self.root), expect="Cargo.lock")

    def test_changed_files_skip_lock_files(self):
        self._assert_no_lock_paths(sv._get_changed_files(self.root), expect="app.py")

    def test_rglob_fallback_inside_git_skips_lock_files(self):
        real_run = sv.subprocess_util.isolated_run

        def ls_files_fails(cmd, *args, **kwargs):
            if list(cmd) == ["git", "ls-files"]:
                return subprocess.CompletedProcess(cmd, 1, "", "injected")
            return real_run(cmd, *args, **kwargs)

        with patch.object(sv.subprocess_util, "isolated_run", ls_files_fails):
            selected = sv._get_all_files(self.root)
        self._assert_no_lock_paths(selected, expect="Cargo.lock")


class RuntimeDirectoryExclusionTests(unittest.TestCase):
    """Exact runtime descendants, including a distribution-declared namespace."""

    ROOTS = (".wavefoundry", ".waveforge")
    DIRS = ("cache", "index", "logs", "dist", "work", "locks")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.excluded = {
            f"{prefix}{name}/{directory}/probe.txt"
            for prefix in ("", "child/", "a/b/")
            for name in self.ROOTS for directory in self.DIRS
        }
        self.kept = {
            "app.txt", "child/.wavefoundry/framework/probe.txt",
            "child/.wavefoundry/bin/probe.txt", "child/.waveforge/framework/probe.txt",
            "child/.waveforge/bin/probe.txt", "child/.wavefoundry-extra/work/probe.txt",
            "child/.waveforge/project/cache/probe.txt", "child/.waveforge/workbench/probe.txt",
            "child/.wavefoundry/cache-tools/probe.txt",
        }
        for rel in self.excluded | self.kept:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("RUNTIME_PROBE_1234\n")
        rules = self.root / SCAN_RULES_FRAMEWORK_PATH
        rules.parent.mkdir(parents=True, exist_ok=True)
        rules.write_text("[[rules]]\nid='runtime-probe'\nregex='RUNTIME_PROBE_[0-9]{4}'\n")
        (self.root / "docs").mkdir()
        (self.root / SCAN_FINDINGS_PATH).write_text("[]")
        self.names = patch.object(sv._scanner_constants, "SCAN_RUNTIME_ROOT_NAMES", self.ROOTS)
        self.names.start()
        self.addCleanup(self.names.stop)

    def test_declaration_and_exact_directory_components(self):
        for rel in self.excluded:
            self.assertTrue(sv.is_scanner_excluded_path(rel), rel)
            self.assertTrue(sv.is_scanner_excluded_path(rel.replace("/", "\\")), rel)
        for rel in self.kept | {"child/.wavefoundry/cache", "child/.waveforge/work"}:
            self.assertFalse(sv.is_scanner_excluded_path(rel), rel)
        with patch.object(sv._scanner_constants, "SCAN_RUNTIME_ROOT_NAMES", (".wavefoundry",)):
            self.assertFalse(sv.is_scanner_excluded_path("child/.waveforge/work/probe.txt"))
            self.assertTrue(sv.is_scanner_excluded_path("child/.wavefoundry/work/probe.txt"))

    def test_non_git_selection_preserves_source_and_near_misses(self):
        self.assertFalse(sv._is_inside_git(self.root))
        selected = _rels(self.root, sv._get_all_files(self.root))
        self.assertFalse(selected & self.excluded)
        self.assertTrue(self.kept <= selected)

    def test_git_full_changed_and_failed_listing_use_the_same_policy(self):
        _git(self.root, "init", "-q")
        _git(self.root, "add", "-f", ".")
        _git(self.root, "commit", "-qm", "fixture")
        for rel in self.excluded | self.kept:
            (self.root / rel).write_text("RUNTIME_PROBE_5678\n")
        for select in (sv._get_all_files, sv._get_changed_files):
            selected = _rels(self.root, select(self.root))
            self.assertFalse(selected & self.excluded)
            self.assertTrue(self.kept <= selected)
        run = sv.subprocess_util.isolated_run
        def failed_listing(command, *args, **kwargs):
            if command == ["git", "ls-files"]:
                return subprocess.CompletedProcess(command, 1, "", "fixture")
            return run(command, *args, **kwargs)
        with patch.object(sv.subprocess_util, "isolated_run", failed_listing):
            selected = _rels(self.root, sv._get_all_files(self.root))
        self.assertFalse(selected & self.excluded)
        self.assertTrue(self.kept <= selected)

    def test_explicit_scan_and_incremental_cache_never_read_runtime_content(self):
        import scan_secrets
        scan_dir = self.root / ".wavefoundry/index/scan"
        scan_secrets._save_scan_state(scan_dir, {
            "scanner_version": scan_secrets.SCANNER_VERSION,
            "rules_hash": scan_secrets._compute_rules_hash(self.root),
        })
        original = Path.open
        forbidden = {self.root / rel for rel in self.excluded}
        def guarded_open(path, *args, **kwargs):
            self.assertNotIn(path, forbidden, "runtime content was opened")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", guarded_open), patch.object(scan_secrets, "_auto_max_workers", return_value=1):
            failures = _scan(self.root, files=[self.root / rel for rel in self.excluded | self.kept])
            result = scan_secrets.update_secrets_scan(
                root=self.root, scan_dir=scan_dir, changed=self.excluded | self.kept,
                removed=set(), full=False,
            )
        self.assertTrue(any(line.startswith("app.txt:") for line in failures), failures)
        self.assertEqual(result["files_scanned"], len(self.kept))
        findings = json.loads((self.root / SCAN_FINDINGS_PATH).read_text())
        self.assertEqual({entry["file"] for entry in findings}, self.kept)

    def test_history_sweeps_only_excluded_runtime_paths(self):
        rows = [{"id": f"fixture-{n}", "file": rel, "line": 1, "rule_id": "runtime-probe",
                 "status": "false-positive", "match_sha256": "0" * 64, "confirmations": []}
                for n, rel in enumerate(sorted(self.excluded | self.kept))]
        path = self.root / SCAN_FINDINGS_PATH
        path.write_text(json.dumps(rows))
        _scan(self.root, files=[])
        self.assertEqual({entry["file"] for entry in json.loads(path.read_text())}, self.kept)

    def test_invalid_declaration_refuses_empty_selection_and_no_work_update(self):
        import scan_secrets
        scan_dir = self.root / ".wavefoundry/index/scan"
        scan_secrets._save_scan_state(scan_dir, {
            "scanner_version": scan_secrets.SCANNER_VERSION,
            "rules_hash": scan_secrets._compute_rules_hash(self.root),
        })
        invalid = ((), ".wavefoundry", (".",), ("..",), ("cache",), (".wf/*",),
                   (".wf/cache",), (".wf\\cache",), (1,))
        for names in invalid:
            with self.subTest(names=names), patch.object(sv._scanner_constants, "SCAN_RUNTIME_ROOT_NAMES", names):
                with self.assertRaisesRegex(ValueError, "SCAN_RUNTIME_ROOT_NAMES"):
                    sv._get_all_files(self.root)
                with self.assertRaisesRegex(ValueError, "SCAN_RUNTIME_ROOT_NAMES"):
                    sv._get_changed_files(self.root)
                self.assertTrue(any("invalid runtime directory declaration" in line for line in _scan(self.root, files=[])))
                with self.assertRaisesRegex(ValueError, "SCAN_RUNTIME_ROOT_NAMES"):
                    scan_secrets.update_secrets_scan(
                        root=self.root, scan_dir=scan_dir,
                        changed=set(), removed=set(), full=False,
                    )


if __name__ == "__main__":
    unittest.main()
