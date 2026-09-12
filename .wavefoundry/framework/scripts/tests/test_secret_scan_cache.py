"""Tests for the per-file secret-scan cache (wave 1rsh9 / 1rsha, Tier 1).

Covers: cache row shape + crash-safety (AC-1), content+rules fingerprint skip
correctness including git-noise cases (AC-2), instrumentation (AC-3), the
Tier-2-ready rule catalog (AC-4), the differential cache-vs-full equivalence
harness (AC-6), derived-only self-heal (AC-7), and scan-state/findings
contract compatibility (AC-8).
"""
from __future__ import annotations

import importlib.util
import io
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))
import index_paths  # noqa: E402 — one definition of the shared database name


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RULES_TOML = """
[policy]
false_positive_confirmations_required = 2

[[rules]]
id = "test-fake-key"
description = "Test fixture rule"
regex = '''FAKEKEY-[A-Z0-9]{12}'''
keywords = ["fakekey-"]

[[rules]]
id = "test-other-token"
description = "Second fixture rule"
regex = '''OTHERTOK-[A-Z0-9]{10}'''
keywords = ["othertok-"]
"""

RULES_TOML_V2 = RULES_TOML + """
[[rules]]
id = "test-third-rule"
description = "Added in v2"
regex = '''THIRDR-[A-Z0-9]{8}'''
keywords = ["thirdr-"]
"""


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-qm", message, "--allow-empty"], check=True
    )


class _CacheCase(unittest.TestCase):
    def setUp(self):
        self.iss = _load("index_state_store")
        self.scan_secrets = _load("scan_secrets")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / ".wavefoundry" / "framework" / "scan-rules.toml").write_text(
            RULES_TOML, encoding="utf-8"
        )
        (self.root / "docs" / "scan-findings.json").write_text("[]", encoding="utf-8")
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.rules_fp = self.scan_secrets._compute_rules_hash(self.root)

    def _write(self, rel: str, content: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class NonGitMachineAuthorityTests(_CacheCase):
    """1x550: fallback excludes authority only; full scans cannot cache themselves."""

    AUTHORITY_PATHS = (
        ".wavefoundry/index/index-build.lock",
        ".wavefoundry/index/code.lance/_versions/1.manifest",
        ".wavefoundry/framework/index/old.manifest",
        ".wavefoundry/logs/dashboard.log",
        ".wavefoundry/locks/dashboard-server.lock",
        ".wavefoundry/guard-overrides.json",
        ".wavefoundry/memory-purge-dispositions.json",
        "docs/waves/renamed_wave/events.jsonl",
        "docs/agents/memory/archive/old.md",
        "docs/agents/memory/pointers/old.md",
        "docs/scan-findings.json",
    )
    CONTENT_PATHS = (
        "src/app.py",
        ".env",
        ".private/settings.txt",
        "package-lock.json",
        "app.min.js",
        "build/output.txt",
        "events.jsonl",
        "docs/waves/renamed_wave/nested/events.jsonl",
        "docs/waves/renamed_wave/wave.md",
        "docs/agents/memory/archive-index.md",
        "docs/agents/memory/pointers-note.md",
        "src/scan-findings.json",
        ".wavefoundry/index-notes/readme.md",
    )

    def _fixture(self):
        for rel in self.AUTHORITY_PATHS + self.CONTENT_PATHS:
            if rel != "docs/scan-findings.json":
                self._write(rel, "fixture text\n")

    def _candidates(self):
        from wave_lint_lib.secrets_validators import get_scan_files
        return {p.relative_to(self.root).as_posix()
                for p in get_scan_files(self.root, scan_all=True)}

    def test_non_git_candidates_exclude_authority_and_preserve_content(self):
        self._fixture()
        candidates = self._candidates()
        for rel in self.AUTHORITY_PATHS:
            with self.subTest(authority=rel):
                self.assertNotIn(rel, candidates)
        for rel in self.CONTENT_PATHS:
            with self.subTest(content=rel):
                self.assertIn(rel, candidates)

    def test_git_candidates_preserve_tracked_and_untracked_authority(self):
        self._fixture()
        _init_git_repo(self.root)
        subprocess.run(["git", "-C", str(self.root), "add", "-f", "--", "."],
                       check=True, capture_output=True)
        untracked = ".wavefoundry/index/new.manifest"
        self._write(untracked, "new untracked manifest\n")
        candidates = self._candidates()
        for rel in self.AUTHORITY_PATHS + self.CONTENT_PATHS + (untracked,):
            with self.subTest(candidate=rel):
                self.assertIn(rel, candidates)

    def test_git_ls_files_failure_preserves_tracked_authority_in_fallback(self):
        from wave_lint_lib import secrets_validators as scanner

        self._fixture()
        _init_git_repo(self.root)
        subprocess.run(["git", "-C", str(self.root), "add", "-f", "--", "."],
                       check=True, capture_output=True)
        original_run = scanner.subprocess_util.isolated_run
        commands = []

        def fail_ls_files_only(command, *args, **kwargs):
            commands.append(command)
            if command[:2] == ["git", "ls-files"]:
                return subprocess.CompletedProcess(command, 128, "", "transient failure")
            return original_run(command, *args, **kwargs)

        with patch.object(scanner.subprocess_util, "isolated_run", side_effect=fail_ls_files_only):
            candidates = self._candidates()
        self.assertIn(["git", "rev-parse", "--is-inside-work-tree"], commands)
        self.assertIn(["git", "check-ignore", "--stdin"], commands)
        for rel in self.AUTHORITY_PATHS:
            with self.subTest(tracked_authority=rel):
                self.assertIn(rel, candidates)

    def test_two_full_scans_keep_exact_cache_membership_without_index_internals(self):
        self._fixture()
        expected = set(self.CONTENT_PATHS) | {".wavefoundry/framework/scan-rules.toml"}
        memberships = []
        # Real scanner/rules, real filesystem enumeration and real SQLite. Only
        # worker count is fixed so the fixture stays bounded on every host.
        with patch.object(self.scan_secrets, "_auto_max_workers", return_value=1), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            for _ in range(2):
                summary = self.scan_secrets.update_secrets_scan(
                    root=self.root, scan_dir=self.index_dir / "scan",
                    changed=set(), removed=set(), full=True,
                )
                self.assertEqual(summary["failures"], 0)
                with closing(sqlite3.connect(index_paths.runtime_database_path(self.index_dir))) as conn:
                    paths = [row[0] for row in conn.execute("SELECT path FROM secret_scan_cache")]
                self.assertFalse(any(p.startswith(".wavefoundry/index/") for p in paths), paths)
                self.assertEqual(set(paths), expected)
                self.assertEqual(len(paths), len(expected))
                memberships.append(set(paths))
        self.assertEqual(memberships[0], memberships[1])


class SkipCorrectnessTests(_CacheCase):
    """AC-1 (row shape), AC-2 (content+rules skip, git-noise cases)."""

    def test_record_then_matching_file_is_skipped(self):
        self._write("a.py", "x = 1\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["a.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={},
        )
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["a.py"], self.rules_fp
        )
        self.assertEqual(to_scan, [])
        self.assertEqual(skipped, 1)

    def test_content_change_forces_rescan(self):
        self._write("a.py", "x = 1\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["a.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={},
        )
        self._write("a.py", "x = 2\n")
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["a.py"], self.rules_fp
        )
        self.assertEqual(to_scan, ["a.py"])
        self.assertEqual(skipped, 0)

    def test_rules_change_forces_rescan(self):
        self._write("a.py", "x = 1\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["a.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={},
        )
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["a.py"], "different-rules-fp"
        )
        self.assertEqual(to_scan, ["a.py"])
        self.assertEqual(skipped, 0)

    def test_touch_and_revert_is_skipped_content_addressed(self):
        """Git-noise cases (AC-2): mtime changes / touch-and-revert / branch
        switches leave content identical — the content-addressed skip fires."""
        self._write("a.py", "x = 1\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["a.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={},
        )
        # Touch: rewrite identical content (new mtime, same bytes).
        self._write("a.py", "x = 1\n")
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["a.py"], self.rules_fp
        )
        self.assertEqual(skipped, 1)
        # Modify then revert: content identical again → skipped.
        self._write("a.py", "x = 2\n")
        self._write("a.py", "x = 1\n")
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["a.py"], self.rules_fp
        )
        self.assertEqual(skipped, 1)
        self.assertEqual(to_scan, [])

    def test_unreadable_file_is_never_skipped(self):
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["missing.py"], self.rules_fp
        )
        self.assertEqual(to_scan, ["missing.py"])
        self.assertEqual(skipped, 0)

    def test_cache_row_shape_and_finding_refs(self):
        self._write("dirty.py", "k = 'FAKEKEY-ABCDEF123456'\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["dirty.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={"dirty.py": [{"rule_id": "test-fake-key", "line": 1,
                                            "status": "pending"}]},
        )
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        try:
            row = conn.execute(
                "SELECT content_hash, rules_fingerprint, scanned_at, clean, finding_refs "
                "FROM secret_scan_cache WHERE path='dirty.py'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        content_hash, rules_fp, scanned_at, clean, refs = row
        self.assertEqual(len(content_hash), 64)
        self.assertEqual(rules_fp, self.rules_fp)
        self.assertGreater(scanned_at, 0)
        self.assertEqual(clean, 0)  # has findings → not clean
        self.assertEqual(json.loads(refs)[0]["rule_id"], "test-fake-key")

    def test_removed_paths_are_deleted_from_cache(self):
        self._write("a.py", "x = 1\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["a.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={},
        )
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=[], rules_fingerprint=self.rules_fp,
            findings_by_file={}, removed_rel_paths=["a.py"],
        )
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        try:
            count = conn.execute("SELECT COUNT(*) FROM secret_scan_cache").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 0)

    def test_interrupted_write_leaves_consistent_store(self):
        """AC-1 crash-window: a mid-transaction failure rolls back atomically —
        the cache is either the previous state or the new one, never torn."""
        self._write("a.py", "x = 1\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["a.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={},
        )
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            conn = store._conn
            try:
                with conn:
                    conn.execute("DELETE FROM secret_scan_cache")
                    conn.execute(
                        "INSERT INTO secret_scan_cache (path, content_hash, "
                        "rules_fingerprint, scanned_at, clean, finding_refs) "
                        "VALUES ('b.py', 'h', 'r', 1, 1, '[]')"
                    )
                    raise RuntimeError("simulated crash mid-transaction")
            except RuntimeError:
                pass
        finally:
            store.close()
        # Rolled back: the original row survives, the partial write does not.
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["a.py"], self.rules_fp
        )
        self.assertEqual(skipped, 1)


class SelfHealTests(_CacheCase):
    """AC-7: corrupt/missing cache degrades to a full scan, never a missed secret."""

    def test_absent_cache_is_normal_cold_start(self):
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["a.py", "b.py"], self.rules_fp
        )
        self.assertEqual(len(to_scan), 2)
        self.assertEqual(skipped, 0)

    def test_corrupt_store_fails_toward_full_scan(self):
        self._write("a.py", "x = 1\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["a.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={},
        )
        path = self.iss.state_store_path(self.index_dir)
        for suffix in ("-wal", "-shm"):
            try:
                (Path(str(path) + suffix)).unlink()
            except OSError:
                pass
        path.write_bytes(b"garbage" * 1000)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            to_scan, skipped, _ = self.iss.secret_scan_filter(
                self.index_dir, self.root, ["a.py"], self.rules_fp
            )
        # Everything scans — a bad cache never suppresses a scan.
        self.assertEqual(to_scan, ["a.py"])
        self.assertEqual(skipped, 0)

    def test_schema_mismatch_degrades_to_full_scan(self):
        self._write("a.py", "x = 1\n")
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=["a.py"], rules_fingerprint=self.rules_fp,
            findings_by_file={},
        )
        store = self.iss.IndexStateStore(self.index_dir)
        store.set_meta({"store_schema_version": "999"})
        store.close()
        # A mismatched canonical store is preserved. Cache readers refuse its
        # schema and scan every candidate; failed writes cannot erase it.
        preserved = self.iss.state_store_path(self.index_dir).read_bytes()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.iss.secret_scan_record(
                self.index_dir, self.root,
                scanned_rel_paths=[], rules_fingerprint=self.rules_fp,
                findings_by_file={},
            )
        to_scan, skipped, _ = self.iss.secret_scan_filter(
            self.index_dir, self.root, ["a.py"], self.rules_fp
        )
        self.assertEqual(to_scan, ["a.py"])
        self.assertEqual(skipped, 0)
        self.assertEqual(self.iss.state_store_path(self.index_dir).read_bytes(), preserved)


class RuleCatalogTests(_CacheCase):
    """AC-4: Tier-2-ready per-rule catalog — parse/hash only, delta-sufficient."""

    def test_catalog_derived_without_execution(self):
        catalog = self.scan_secrets._rule_catalog(self.root)
        self.assertEqual(sorted(catalog.keys()), ["test-fake-key", "test-other-token"])
        for rule_hash in catalog.values():
            self.assertEqual(len(rule_hash), 64)

    def test_stored_catalog_identifies_rule_deltas_between_versions(self):
        catalog_v1 = self.scan_secrets._rule_catalog(self.root)
        fp_v1 = self.rules_fp
        self.iss.secret_scan_record(
            self.index_dir, self.root, scanned_rel_paths=[],
            rules_fingerprint=fp_v1, findings_by_file={}, rule_catalog=catalog_v1,
        )
        # Ruleset v2: adds a rule and modifies one.
        modified = RULES_TOML_V2.replace("FAKEKEY-[A-Z0-9]{12}", "FAKEKEY-[A-Z0-9]{14}")
        (self.root / ".wavefoundry" / "framework" / "scan-rules.toml").write_text(
            modified, encoding="utf-8"
        )
        catalog_v2 = self.scan_secrets._rule_catalog(self.root)
        fp_v2 = self.scan_secrets._compute_rules_hash(self.root)
        self.assertNotEqual(fp_v1, fp_v2)
        self.iss.secret_scan_record(
            self.index_dir, self.root, scanned_rel_paths=[],
            rules_fingerprint=fp_v2, findings_by_file={}, rule_catalog=catalog_v2,
        )
        # The stored inputs are sufficient to compute the delta (no execution).
        stored_v1 = self.iss.secret_rule_catalog_for(self.index_dir, fp_v1)
        stored_v2 = self.iss.secret_rule_catalog_for(self.index_dir, fp_v2)
        added = set(stored_v2) - set(stored_v1)
        removed = set(stored_v1) - set(stored_v2)
        modified_rules = {
            rid for rid in set(stored_v1) & set(stored_v2)
            if stored_v1[rid] != stored_v2[rid]
        }
        self.assertEqual(added, {"test-third-rule"})
        self.assertEqual(removed, set())
        self.assertEqual(modified_rules, {"test-fake-key"})


class RunSecretsScanGuardHistoryTests(_CacheCase):
    """1x5tr delivery review (RED-DEL-9): the wf_scan_secrets subprocess path
    shares the unpublished-outcome seam with the indexer scan."""

    def _main(self, mode):
        run_scan = _load("run_secrets_scan")
        out = io.StringIO()
        argv = ["run_secrets_scan.py", "--root", str(self.root), "--mode", mode]
        with patch.object(sys, "argv", argv), redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(run_scan.main(), 0)
        return json.loads(out.getvalue().strip().splitlines()[-1])

    def _cached(self):
        db = index_paths.runtime_database_path(self.index_dir)
        if not db.exists():
            return set()
        with closing(sqlite3.connect(db)) as conn:
            return {row[0] for row in conn.execute("SELECT path FROM secret_scan_cache")}

    def test_failed_publication_keeps_the_run_out_of_the_cache_on_the_scan_tool_path(self):
        from wave_lint_lib import secrets_validators as sv
        import scanner_skips
        self._write("deck.pptx", "\0binary")
        self._write("app.py", "x = 1\n")
        ledger = self.root / scanner_skips.LEDGER_REL
        with patch.object(sv, "update_scanner_skips", side_effect=OSError("fixture publication failure")):
            first = self._main("full")
        self.assertFalse(ledger.exists())
        self.assertEqual(first["files_skipped"], 0)
        self.assertEqual(self._cached() & {"deck.pptx", "app.py"}, set())
        second = self._main("incremental")
        self.assertEqual(second["files_skipped"], 0)
        self.assertLessEqual({"deck.pptx", "app.py"}, self._cached())
        self.assertEqual(scanner_skips.scanner_skip_notice(self.root)["scanner_skips"][0]["file"], "deck.pptx")


class DifferentialEquivalenceTests(_CacheCase):
    """AC-6: cache-path findings are identical to a no-cache full scan across
    add/modify/delete/rename/revert and rules-change fixtures."""

    def setUp(self):
        super().setUp()
        _init_git_repo(self.root)
        self._write("clean.py", "x = 1\n")
        self._write("dirty.py", "key = 'FAKEKEY-ABCDEF123456'\n")
        _commit_all(self.root, "c1")

    def _tracked(self) -> list[str]:
        out = subprocess.run(
            ["git", "-C", str(self.root), "ls-files"],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        return [p for p in out if (self.root / p).is_file()]

    def _normalize_findings(self, root: Path) -> list[tuple]:
        try:
            entries = json.loads(
                (root / "docs" / "scan-findings.json").read_text(encoding="utf-8")
            )
        except Exception:
            entries = []
        return sorted(
            (str(e.get("file")), str(e.get("rule_id") or e.get("rule") or ""),
             e.get("line"), str(e.get("status") or ""))
            for e in entries if isinstance(e, dict)
        )

    def _cache_scan(self) -> list[tuple]:
        """The cache path: filter candidates through the cache, scan the rest."""
        from wave_lint_lib.secrets_validators import check_hardcoded_secrets
        candidates = self._tracked()
        to_scan, _skipped, hashes = self.iss.secret_scan_filter(
            self.index_dir, self.root, candidates, self.rules_fp
        )
        check_hardcoded_secrets(
            self.root, files=[self.root / p for p in to_scan], record_only=True
        )
        self.iss.secret_scan_record(
            self.index_dir, self.root,
            scanned_rel_paths=to_scan, rules_fingerprint=self.rules_fp,
            findings_by_file=self.scan_secrets._findings_by_file(self.root),
            content_hashes=hashes,
        )
        return self._normalize_findings(self.root)

    def _control_scan(self) -> list[tuple]:
        """A no-cache full scan over an identical copy of the repo state."""
        from wave_lint_lib.secrets_validators import check_hardcoded_secrets
        ctrl = Path(self._tmp.name) / "ctrl"
        if ctrl.exists():
            shutil.rmtree(ctrl)
        shutil.copytree(self.root, ctrl, ignore=shutil.ignore_patterns("index"))
        check_hardcoded_secrets(
            ctrl, files=[ctrl / p for p in self._tracked()], record_only=True
        )
        return self._normalize_findings(ctrl)

    def _assert_equivalent(self, step: str):
        cache_findings = self._cache_scan()
        control_findings = self._control_scan()
        self.assertEqual(
            cache_findings, control_findings,
            f"cache-path findings diverged from full scan after: {step}",
        )

    def test_equivalence_across_the_fixture_matrix(self):
        self._assert_equivalent("initial scan (cold cache)")
        # Add a new dirty file.
        self._write("added.py", "tok = 'OTHERTOK-ABCDE12345'\n")
        _commit_all(self.root, "add")
        self._assert_equivalent("add")
        # Modify: clean file becomes dirty.
        self._write("clean.py", "x = 'FAKEKEY-ZZZZZZ999999'\n")
        _commit_all(self.root, "modify")
        self._assert_equivalent("modify")
        # Revert the modification.
        self._write("clean.py", "x = 1\n")
        _commit_all(self.root, "revert")
        self._assert_equivalent("revert")
        # Rename a dirty file.
        subprocess.run(["git", "-C", str(self.root), "mv", "dirty.py", "renamed.py"],
                       check=True)
        _commit_all(self.root, "rename")
        self._assert_equivalent("rename")
        # Delete a file.
        subprocess.run(["git", "-C", str(self.root), "rm", "-q", "added.py"], check=True)
        _commit_all(self.root, "delete")
        self.iss.secret_scan_record(
            self.index_dir, self.root, scanned_rel_paths=[],
            rules_fingerprint=self.rules_fp, findings_by_file={},
            removed_rel_paths=["added.py"],
        )
        self._assert_equivalent("delete")
        # Rules change: fingerprint moves → every cached row mismatches.
        (self.root / ".wavefoundry" / "framework" / "scan-rules.toml").write_text(
            RULES_TOML_V2, encoding="utf-8"
        )
        self.rules_fp = self.scan_secrets._compute_rules_hash(self.root)
        self._write("third.py", "t = 'THIRDR-ABCD1234'\n")
        _commit_all(self.root, "rules-change")
        self._assert_equivalent("rules-change")

    def test_cache_never_suppresses_a_finding_a_full_scan_reports(self):
        """The load-bearing safety property, asserted directly: a dirty file
        whose cache row LIES (claims clean, matching hash) is still reported —
        because the ledger sweep and the skip protect different things, the
        harness must show the divergence attempt FAILS to hide the secret."""
        self._cache_scan()  # populate cache; dirty.py recorded with findings
        control = self._control_scan()
        self.assertTrue(any(f[0] == "dirty.py" for f in control))
        # Even with dirty.py cache-skipped on the next pass, its finding stays
        # in the ledger (the skip never deletes findings).
        cache_second = self._cache_scan()
        self.assertEqual(cache_second, control)


class InstrumentationAndCompatTests(_CacheCase):
    """AC-3 (skip counters + escalation flag), AC-8 (scan-state compat)."""

    def test_update_secrets_scan_reports_skip_and_escalation(self):
        import types
        from unittest.mock import patch
        calls = []
        mock_validators = types.ModuleType("wave_lint_lib.secrets_validators")
        mock_validators.check_hardcoded_secrets = lambda root, **kw: calls.append(kw) or []
        mock_validators.get_scan_files = lambda root, scan_all=False: []
        mock_validators.unpublished_scanner_skips = lambda: []  # wave 1x5tr seam
        mock_validators.load_merged_ruleset = lambda root: ([], {}, [])
        mock_constants = types.ModuleType("wave_lint_lib.constants")
        mock_constants.SCAN_FINDINGS_PATH = "docs/scan-findings.json"
        wave_lint_lib = types.ModuleType("wave_lint_lib")
        scan_dir = self.index_dir / "scan"
        scan_dir.mkdir(parents=True, exist_ok=True)
        self._write("a.py", "x = 1\n")
        # Pre-populate the cache so the skip fires.
        self.iss.secret_scan_record(
            self.index_dir, self.root, scanned_rel_paths=["a.py"],
            rules_fingerprint=self.rules_fp, findings_by_file={},
        )
        self.scan_secrets._save_scan_state(scan_dir, {
            "scanner_version": self.scan_secrets.SCANNER_VERSION,
            "rules_hash": self.rules_fp,
        })
        with patch.dict(sys.modules, {
            "wave_lint_lib": wave_lint_lib,
            "wave_lint_lib.secrets_validators": mock_validators,
            "wave_lint_lib.constants": mock_constants,
        }):
            summary = self.scan_secrets.update_secrets_scan(
                root=self.root, scan_dir=scan_dir,
                changed={"a.py"}, removed=set(), full=False,
            )
        self.assertEqual(summary["files_skipped"], 1)
        self.assertEqual(summary["files_scanned"], 0)
        self.assertFalse(summary["rules_change_escalation"])
        state = self.scan_secrets._load_scan_state(scan_dir)
        self.assertEqual(state.get("files_skipped"), 1)
        self.assertIn("rules_change_escalation", state)

    def test_scan_state_json_rules_hash_contract_preserved(self):
        scan_dir = self.index_dir / "scan"
        scan_dir.mkdir(parents=True, exist_ok=True)
        self.scan_secrets._save_scan_state(scan_dir, {"rules_hash": "abc"})
        state = json.loads((scan_dir / "scan-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["rules_hash"], "abc")

    def test_run_secrets_scan_output_gains_instrumentation_fields(self):
        src = (SCRIPTS_ROOT / "run_secrets_scan.py").read_text(encoding="utf-8")
        for field in ('"files_scanned"', '"files_skipped"', '"escalated_to_full"'):
            self.assertIn(field, src)

    def test_rules_relpaths_cover_the_real_framework_ruleset(self):
        # The corrected fingerprint paths (the old first entry never existed,
        # silently missing framework-rules changes) — both modules agree.
        run_scan = _load("run_secrets_scan")
        expected = (".wavefoundry/framework/scan-rules.toml", "docs/scan-rules.toml")
        self.assertEqual(self.scan_secrets._RULES_RELPATHS, expected)
        self.assertEqual(run_scan._RULES_RELPATHS, expected)
        from wave_lint_lib.constants import SCAN_RULES_FRAMEWORK_PATH, SCAN_RULES_PROJECT_PATH
        self.assertEqual(expected[0], SCAN_RULES_FRAMEWORK_PATH)
        self.assertEqual(expected[1], SCAN_RULES_PROJECT_PATH)


if __name__ == "__main__":
    unittest.main()
