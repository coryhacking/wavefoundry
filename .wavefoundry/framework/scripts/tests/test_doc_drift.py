"""Tests for doc-code drift + wave→files attribution (wave 1ro44 / 1ro43).

Covers landing-commit derivation over the censused subject variants, the
living-doc drift model (content/verification anchors, gardener-stamp
immunity, threshold flagging), the historical class for ``docs/waves/``
(landing anchor, waves-behind, worklist exclusion), the build-pass
fingerprint skip (including stamp participation), the batched retrieval
read, and the drift worklist consumer contract. All git history is
synthetic with pinned commit timestamps (council guidance: no live-repo
assumptions).
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
STORE_PATH = SCRIPTS_ROOT / "index_state_store.py"


def _rmtree_git(path: Path) -> None:
    """Windows-safe ``rmtree`` for a ``.git`` tree: git marks loose objects and
    pack files read-only, so a plain ``shutil.rmtree`` raises ``PermissionError``
    on Windows. Clear the read-only bit and retry (mirrors
    ``setup_index._rmtree_clearing_readonly``); a harmless no-op on POSIX."""
    def _clear(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    kw = {"onexc": _clear} if sys.version_info >= (3, 12) else {"onerror": _clear}
    shutil.rmtree(path, **kw)


def load_store_module():
    spec = importlib.util.spec_from_file_location("index_state_store", STORE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["index_state_store"] = mod
    spec.loader.exec_module(mod)
    return mod


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)


# Fixed epoch base far in the past so churn windows behave deterministically.
_T0 = 1700000000


def _commit_all_at(root: Path, message: str, ts: int) -> None:
    """Commit with a pinned author+committer timestamp (deterministic anchors)."""
    stamp = f"{ts} +0000"
    env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-qm", message], check=True, env=env
    )


class _DriftCase(unittest.TestCase):
    def setUp(self):
        self.iss = load_store_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self.index_dir = self.root / ".wavefoundry" / "index"

    def _write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _update(self, docs, all_paths):
        return self.iss.update_drift_from_build(
            self.root, self.index_dir, docs, all_paths
        )


class WaveAttributionDerivationTests(unittest.TestCase):
    """Req 12: tolerant landing-subject parsing over the censused variants."""

    def setUp(self):
        self.iss = load_store_module()

    def _derive(self, subjects_and_files):
        commits = [
            {"sha": f"{i:040x}", "ts": _T0 + (len(subjects_and_files) - i) * 100,
             "subject": subject, "files": files}
            for i, (subject, files) in enumerate(subjects_and_files)
        ]
        return self.iss.derive_wave_attribution(commits)

    def test_single_wave_landing_with_colon(self):
        landings, files = self._derive(
            [("Land wave 1sed7: retire meta.json", ["a.py", "b.py"])]
        )
        self.assertEqual([w for w, _s, _t in landings], ["1sed7"])
        self.assertEqual(files, [("1sed7", "a.py"), ("1sed7", "b.py")])

    def test_no_colon_and_parenthesized_version_variants(self):
        landings, _ = self._derive([
            ("Land wave 1p9hn windows-portability-round-2", ["x.py"]),
            ("Land wave 1p8xm (1.9.8): downstream-upgrade fixes", ["y.py"]),
        ])
        self.assertEqual(sorted(w for w, _s, _t in landings), ["1p8xm", "1p9hn"])

    def test_bundle_commits_attribute_wave_set_coarsely(self):
        landings, files = self._derive([
            ("Land waves 1rycd + 1rycg: cleanup and optimize", ["m.py", "n.py"]),
        ])
        self.assertEqual(sorted(w for w, _s, _t in landings), ["1rycd", "1rycg"])
        # Every bundled wave shares the full change set (wave-set attribution).
        self.assertIn(("1rycd", "m.py"), files)
        self.assertIn(("1rycg", "m.py"), files)
        self.assertIn(("1rycd", "n.py"), files)
        self.assertIn(("1rycg", "n.py"), files)

    def test_comma_list_bundle_and_land_without_the_word_wave(self):
        landings, _ = self._derive([
            ("Land waves 1p93a, 1p99f, 1p99p (1.10.0): the bundle", ["z.py"]),
            ("Land 1p7ir: docs-first flow", ["w.py"]),
            ("Land design-system foundation wave (1p75h) and scrub refs", ["v.py"]),
        ])
        self.assertEqual(
            sorted(w for w, _s, _t in landings),
            ["1p75h", "1p7ir", "1p93a", "1p99f", "1p99p"],
        )

    def test_version_only_landing_never_parses_as_a_wave(self):
        landings, files = self._derive([
            ("Land 1.8.0: retrieval hardening", ["a.py"]),
            ("Land 1.10.1 release hardening", ["b.py"]),
        ])
        self.assertEqual(landings, [])
        self.assertEqual(files, [])

    def test_close_wave_counts_only_without_a_land_commit(self):
        landings, files = self._derive([
            # 1p9hi closed with the implementation code, no Land commit.
            ("Close wave 1p9hi python3-prereq-stop: fail setup", ["setup.py"]),
            # 1p9gr landed separately; its close is docs-only bookkeeping.
            ("Close wave 1p9gr setup proxy defaults", ["docs/waves/1p9gr x/wave.md"]),
            ("Land 1p9gr setup proxy and index defaults", ["proxy.py"]),
        ])
        by_wave = {w: sha for w, sha, _t in landings}
        self.assertIn("1p9hi", by_wave)
        self.assertIn("1p9gr", by_wave)
        self.assertIn(("1p9hi", "setup.py"), files)
        self.assertIn(("1p9gr", "proxy.py"), files)
        # The close commit's docs-only diff must NOT be attributed to 1p9gr.
        self.assertNotIn(("1p9gr", "docs/waves/1p9gr x/wave.md"), files)

    def test_lifecycle_noise_is_excluded(self):
        landings, _ = self._derive([
            ("Bump VERSION to 1.11.2+pahu after release", ["VERSION"]),
            ("Advance wave 1seav: mid-wave checkpoint (implementing)", ["s.py"]),
            ("Plan wave 1zzzz for later", ["docs/plans/p.md"]),
            ("Ready wave 1zzzz", ["docs/waves/w/wave.md"]),
            ("Update session handoff: wave 1seav closed", ["docs/agents/session-handoff.md"]),
        ])
        self.assertEqual(landings, [])

    def test_bare_numbers_never_match_the_id_token(self):
        self.assertEqual(self.iss.WAVE_ID_TOKEN.findall("Land 2026 and 10000 things"), [])
        self.assertEqual(self.iss.WAVE_ID_TOKEN.findall("Land wave 1p45l now"), ["1p45l"])


class VerificationStampParsingTests(unittest.TestCase):
    def setUp(self):
        self.iss = load_store_module()

    def test_wellformed_full_and_abbreviated(self):
        sha, malformed = self.iss.parse_verification_stamp(
            "# Doc\n\nVerified against: " + "a1" * 20 + "\n"
        )
        self.assertEqual(sha, "a1" * 20)
        self.assertFalse(malformed)
        sha, malformed = self.iss.parse_verification_stamp(
            "Owner: X\nVerified against: ABC1234\n"
        )
        self.assertEqual(sha, "abc1234")
        self.assertFalse(malformed)

    def test_malformed_is_flagged_and_ignored(self):
        for value in ("not-a-sha", "12345", "<commit-sha>", ""):
            sha, malformed = self.iss.parse_verification_stamp(
                f"Verified against: {value}\n"
            )
            self.assertIsNone(sha, value)
            self.assertTrue(malformed, value)

    def test_absent_line_is_neither(self):
        sha, malformed = self.iss.parse_verification_stamp("# Doc\nLast verified: 2026-07-13\n")
        self.assertIsNone(sha)
        self.assertFalse(malformed)


class LivingDocDriftTests(_DriftCase):
    """Reqs 3 + 10: anchors, gardener immunity, threshold, stamp reset."""

    def _seed_history(self):
        """doc.md references src/a.py; then a.py churns 3 commits later."""
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write(
            "docs/guide.md",
            "Owner: X\nLast verified: 2020-01-01\n\nSee `src/a.py` for details.\n",
        )
        _commit_all_at(self.root, "c1: initial", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"c{i + 2}: churn a.py", _T0 + 1000 * (i + 1))

    def test_drift_flags_after_threshold_commits_on_referenced_path(self):
        self._seed_history()
        summary = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        self.assertNotIn("error", summary)
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertTrue(drift["drifted"])
        self.assertEqual(drift["drift_refs"], ["src/a.py"])
        self.assertEqual(drift["commits_since"], 3)
        self.assertEqual(drift["anchor_kind"], "content")
        self.assertFalse(drift["historical"])

    def test_below_threshold_is_annotated_not_flagged(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md", "See `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        self._write("src/a.py", "x = 2\n")
        _commit_all_at(self.root, "c2", _T0 + 1000)
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertFalse(drift["drifted"])
        self.assertEqual(drift["commits_since"], 1)

    def test_gardener_last_verified_date_never_moves_the_anchor(self):
        """AC-2: a fresh-looking gardener stamp value is not a verification."""
        self._seed_history()
        # Claim today's date in the (uncommitted) Last verified line — the
        # mechanical stamp text must carry zero anchor meaning.
        today = time.strftime("%Y-%m-%d")
        self._write(
            "docs/guide.md",
            f"Owner: X\nLast verified: {today}\n\nSee `src/a.py` for details.\n",
        )
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertTrue(drift["drifted"])
        self.assertEqual(drift["anchor_kind"], "content")
        self.assertEqual(drift["commits_since"], 3)

    def test_verification_stamp_resets_the_drift_clock(self):
        self._seed_history()
        head = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        # Deliberate review against HEAD (uncommitted stamp — working form).
        self._write(
            "docs/guide.md",
            f"Owner: X\nVerified against: {head}\n\nSee `src/a.py` for details.\n",
        )
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertFalse(drift["drifted"])
        self.assertEqual(drift["commits_since"], 0)
        self.assertEqual(drift["anchor_kind"], "verification")
        # Commit the stamp (the normal flow), then churn only the referenced
        # file: drift resumes accumulating, and the doc stays labeled
        # "verification" even though the stamping commit is now the doc's
        # newest content change.
        _commit_all_at(self.root, "record verification stamp", _T0 + 9000)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 10}\n")
            _commit_all_at(self.root, f"post-stamp churn {i}", _T0 + 10000 + i * 100)
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertTrue(drift["drifted"])
        self.assertEqual(drift["commits_since"], 3)
        self.assertEqual(drift["anchor_kind"], "verification")

    def test_abbreviated_stamp_resolves_and_unresolvable_degrades_to_content(self):
        self._seed_history()
        head = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self._write(
            "docs/guide.md",
            f"Verified against: {head[:10]}\n\nSee `src/a.py`.\n",
        )
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["anchor_kind"], "verification")
        self.assertFalse(drift["drifted"])
        # Unknown SHA: fail toward the content anchor, never toward trust.
        self._write(
            "docs/guide.md",
            "Verified against: ffffffffffff\n\nSee `src/a.py`.\n",
        )
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["anchor_kind"], "content")
        self.assertTrue(drift["drifted"])

    def test_doc_without_valid_refs_never_flags(self):
        _init_git_repo(self.root)
        self._write("docs/plain.md", "No code references here, just prose a/b.\n")
        self._write("src/a.py", "x = 1\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(4):
            self._write("src/a.py", f"x = {i}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 100)
        self._update(["docs/plain.md"], ["docs/plain.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/plain.md")
        self.assertFalse(drift["drifted"])
        self.assertEqual(drift["drift_refs"], [])
        self.assertEqual(drift["commits_since"], 0)

    def test_dot_prefixed_reference_paths_resolve(self):
        _init_git_repo(self.root)
        self._write(".wavefoundry/framework/scripts/tool.py", "y = 1\n")
        self._write("docs/ref.md", "See `.wavefoundry/framework/scripts/tool.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        self._update(
            ["docs/ref.md"],
            ["docs/ref.md", ".wavefoundry/framework/scripts/tool.py"],
        )
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/ref.md")
        self.assertEqual(drift["drift_refs"], [".wavefoundry/framework/scripts/tool.py"])


class HistoricalClassTests(_DriftCase):
    """Req 13 / AC-14: landing anchor, waves-behind, never flagged/worklisted."""

    def _seed_waves(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/waves/1aaaa first-wave/wave.md", "# Wave 1aaaa\n")
        _commit_all_at(self.root, "Land wave 1aaaa: ship the feature", _T0)
        # Later wave touches the same change set (src/a.py) → 1aaaa is behind.
        self._write("src/a.py", "x = 2\n")
        self._write("docs/waves/1bbbb second-wave/wave.md", "# Wave 1bbbb\n")
        _commit_all_at(self.root, "Land wave 1bbbb: rework the feature", _T0 + 5000)

    def test_landing_anchor_waves_behind_and_no_drift_flag(self):
        self._seed_waves()
        docs = [
            "docs/waves/1aaaa first-wave/wave.md",
            "docs/waves/1bbbb second-wave/wave.md",
        ]
        self._update(docs, docs + ["src/a.py"])
        old = self.iss.doc_drift_for_path(
            self.index_dir, "docs/waves/1aaaa first-wave/wave.md"
        )
        self.assertTrue(old["historical"])
        self.assertFalse(old["drifted"])
        self.assertEqual(old["waves_behind"], 1)
        self.assertGreaterEqual(old["commits_since"], 1)
        new = self.iss.doc_drift_for_path(
            self.index_dir, "docs/waves/1bbbb second-wave/wave.md"
        )
        self.assertTrue(new["historical"])
        self.assertEqual(new["waves_behind"], 0)
        self.assertEqual(new["commits_since"], 0)

    def test_wave_without_derivable_landing_keeps_historical_marker(self):
        _init_git_repo(self.root)
        self._write("docs/waves/1cccc quiet-wave/wave.md", "# Wave 1cccc\n")
        _commit_all_at(self.root, "checkpoint without landing convention", _T0)
        self._update(
            ["docs/waves/1cccc quiet-wave/wave.md"],
            ["docs/waves/1cccc quiet-wave/wave.md"],
        )
        drift = self.iss.doc_drift_for_path(
            self.index_dir, "docs/waves/1cccc quiet-wave/wave.md"
        )
        self.assertTrue(drift["historical"])
        self.assertFalse(drift["drifted"])
        self.assertEqual(drift["waves_behind"], 0)
        self.assertEqual(drift["commits_since"], 0)

    def test_historical_docs_are_excluded_from_the_worklist(self):
        self._seed_waves()
        # Add a genuinely drifted living doc for contrast.
        self._write("docs/guide.md", "See `src/a.py`.\n")
        _commit_all_at(self.root, "add guide", _T0 + 6000)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 10}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + 7000 + i * 100)
        docs = [
            "docs/waves/1aaaa first-wave/wave.md",
            "docs/waves/1bbbb second-wave/wave.md",
            "docs/guide.md",
        ]
        self._update(docs, docs + ["src/a.py"])
        worklist = self.iss.drift_worklist(self.index_dir)
        self.assertTrue(worklist["available"])
        self.assertEqual(worklist["flagged_count"], 1)
        self.assertEqual(worklist["entries"][0]["path"], "docs/guide.md")
        self.assertEqual(worklist["entries"][0]["commits_since"], 3)


class BuildPassContractTests(_DriftCase):
    """Fingerprint skip, stamp participation, non-git degrade, full replace."""

    def test_zero_change_build_skips(self):
        _init_git_repo(self.root)
        self._write("docs/a.md", "hello\n")
        _commit_all_at(self.root, "c1", _T0)
        first = self._update(["docs/a.md"], ["docs/a.md"])
        self.assertFalse(first["skipped"])
        second = self._update(["docs/a.md"], ["docs/a.md"])
        self.assertTrue(second["skipped"])

    def test_uncommitted_stamp_invalidates_the_skip(self):
        _init_git_repo(self.root)
        self._write("docs/a.md", "hello\n")
        self._write("src/a.py", "x = 1\n")
        _commit_all_at(self.root, "c1", _T0)
        self._update(["docs/a.md"], ["docs/a.md", "src/a.py"])
        head = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self._write("docs/a.md", f"Verified against: {head}\n\nhello\n")
        summary = self._update(["docs/a.md"], ["docs/a.md", "src/a.py"])
        self.assertFalse(summary["skipped"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/a.md")
        self.assertEqual(drift["anchor_kind"], "verification")

    def test_non_git_root_degrades_silently(self):
        self._write("docs/a.md", "hello\n")
        summary = self._update(["docs/a.md"], ["docs/a.md"])
        self.assertTrue(summary["skipped"])
        self.assertNotIn("error", summary)
        self.assertIsNone(self.iss.doc_drift_for_path(self.index_dir, "docs/a.md"))

    def test_removed_docs_leave_no_stale_rows(self):
        _init_git_repo(self.root)
        self._write("docs/a.md", "a\n")
        self._write("docs/b.md", "b\n")
        _commit_all_at(self.root, "c1", _T0)
        self._update(["docs/a.md", "docs/b.md"], ["docs/a.md", "docs/b.md"])
        self.assertIsNotNone(self.iss.doc_drift_for_path(self.index_dir, "docs/b.md"))
        (self.root / "docs/b.md").unlink()
        _commit_all_at(self.root, "remove b", _T0 + 100)
        self._update(["docs/a.md"], ["docs/a.md"])
        self.assertIsNone(self.iss.doc_drift_for_path(self.index_dir, "docs/b.md"))
        self.assertIsNotNone(self.iss.doc_drift_for_path(self.index_dir, "docs/a.md"))


class BatchedRetrievalReadTests(_DriftCase):
    """The retrieval-annotation read: one connection, whole citation set."""

    def test_batched_read_merges_freshness_and_drift(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md", "See `src/a.py`.\n")
        self._write("docs/waves/1aaaa w/wave.md", "# W\n")
        _commit_all_at(self.root, "Land wave 1aaaa: ship", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 100)
        self.iss.update_freshness_from_build(
            self.root, self.index_dir,
            ["src/a.py", "docs/guide.md", "docs/waves/1aaaa w/wave.md"],
        )
        self._update(
            ["docs/guide.md", "docs/waves/1aaaa w/wave.md"],
            ["src/a.py", "docs/guide.md", "docs/waves/1aaaa w/wave.md"],
        )
        out = self.iss.freshness_for_paths(
            self.index_dir,
            ["src/a.py", "docs/guide.md", "docs/waves/1aaaa w/wave.md", "missing.py"],
        )
        self.assertIn("src/a.py", out)
        self.assertIn("churn_score", out["src/a.py"])
        self.assertIn("age_days", out["src/a.py"])
        self.assertNotIn("drifted", out["src/a.py"])  # code: freshness only
        self.assertTrue(out["docs/guide.md"]["drifted"])
        self.assertEqual(out["docs/guide.md"]["commits_since_verified"], 3)
        self.assertTrue(out["docs/waves/1aaaa w/wave.md"]["historical"])
        self.assertIn("waves_behind", out["docs/waves/1aaaa w/wave.md"])
        self.assertNotIn("drifted", out["docs/waves/1aaaa w/wave.md"])
        self.assertNotIn("missing.py", out)

    def test_absent_store_returns_empty(self):
        self.assertEqual(self.iss.freshness_for_paths(self.index_dir, ["a.py"]), {})
        self.assertEqual(self.iss.freshness_for_paths(self.index_dir, []), {})


class DriftExemptPrefixTests(_DriftCase):
    """Census finding (AC-8): generated point-in-time artifacts are exempt
    from the drift flag (annotation still rides) and thus the worklist."""

    def test_reports_are_never_drift_flagged(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/reports/reindex-2020-01-01.md", "Touched `src/a.py`.\n")
        self._write("docs/guide.md", "See `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 100)
        docs = ["docs/reports/reindex-2020-01-01.md", "docs/guide.md"]
        self._update(docs, docs + ["src/a.py"])
        report = self.iss.doc_drift_for_path(
            self.index_dir, "docs/reports/reindex-2020-01-01.md")
        self.assertFalse(report["drifted"])
        self.assertEqual(report["commits_since"], 3)  # annotation still honest
        guide = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertTrue(guide["drifted"])
        worklist = self.iss.drift_worklist(self.index_dir)
        self.assertEqual([e["path"] for e in worklist["entries"]], ["docs/guide.md"])


class GardenerAnchorTests(_DriftCase):
    """Delivery-review P0: a committed gardener-only (`Last verified:`) change
    must NOT reset the drift clock — the anchor is the last MATERIAL content
    change."""

    def test_committed_gardener_bump_does_not_reset_drift(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write(
            "docs/guide.md",
            "Owner: X\nStatus: active\nLast verified: 2020-01-01\n\nSee `src/a.py`.\n",
        )
        _commit_all_at(self.root, "c1: create guide + a.py", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"code churn {i}", _T0 + (i + 1) * 1000)
        # Gardener commits ONLY the Last verified date on the doc (newest
        # commit that names the doc) — must not become the anchor.
        self._write(
            "docs/guide.md",
            "Owner: X\nStatus: active\nLast verified: 2026-07-14\n\nSee `src/a.py`.\n",
        )
        _commit_all_at(self.root, "gardener: refresh Last verified", _T0 + 5000)
        summary = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        self.assertNotIn("error", summary)
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["commits_since"], 3,
                         "the 3 code commits are after the material anchor")
        self.assertTrue(drift["drifted"])
        self.assertEqual(drift["anchor_kind"], "content")

    def test_material_edit_alongside_gardener_field_still_anchors(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md",
                    "Status: active\nLast verified: 2020-01-01\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        # This commit changes Last verified AND real prose → material, anchors here.
        self._write("docs/guide.md",
                    "Status: active\nLast verified: 2026-07-14\n\nSee `src/a.py` now.\n")
        _commit_all_at(self.root, "real doc edit + stamp", _T0 + 6000)
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["commits_since"], 0, "material edit is newer than all churn")
        self.assertFalse(drift["drifted"])


class TopologyNotTimestampTests(_DriftCase):
    """Delivery-review P1: churn/landing counting uses git order, not %ct.
    Clock-skewed commits (topologically later, timestamp earlier) must count."""

    def test_living_doc_skewed_timestamps(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1: anchor", _T0)
        # Three code commits that are topologically LATER but timestamped
        # BEFORE the anchor (rebase / clock-skew shape).
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"skewed churn {i}", _T0 - (i + 1) * 1000)
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["commits_since"], 3,
                         "topologically-later churn counts despite earlier timestamps")
        self.assertTrue(drift["drifted"])

    def test_historical_waves_behind_skewed_timestamps(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/waves/1aaaa first/wave.md", "# 1aaaa\n")
        _commit_all_at(self.root, "Land wave 1aaaa: ship", _T0)
        # A later wave landing touching the same change set, timestamped BEFORE.
        self._write("src/a.py", "x = 2\n")
        self._write("docs/waves/1bbbb second/wave.md", "# 1bbbb\n")
        _commit_all_at(self.root, "Land wave 1bbbb: rework", _T0 - 9000)
        docs = ["docs/waves/1aaaa first/wave.md", "docs/waves/1bbbb second/wave.md"]
        self._update(docs, docs + ["src/a.py"])
        old = self.iss.doc_drift_for_path(self.index_dir, "docs/waves/1aaaa first/wave.md")
        self.assertEqual(old["waves_behind"], 1,
                         "1bbbb landed later by topology even though timestamped earlier")
        self.assertGreaterEqual(old["commits_since"], 1)


class DriftFingerprintContentTests(_DriftCase):
    """Delivery-review P1: the skip fingerprint includes material doc content,
    so uncommitted reference edits at stable HEAD cannot be skipped."""

    def _seed(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("src/b.py", "y = 1\n")
        self._write("docs/guide.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        first = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py", "src/b.py"])
        self.assertFalse(first["skipped"])

    def test_changed_reference_invalidates_skip(self):
        self._seed()
        self._write("docs/guide.md", "Status: active\n\nSee `src/b.py`.\n")  # uncommitted
        summary = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py", "src/b.py"])
        self.assertFalse(summary["skipped"], "uncommitted ref change must not be skipped")
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["drift_refs"], ["src/b.py"])

    def test_added_and_removed_references_invalidate_skip(self):
        self._seed()
        # Add a reference.
        self._write("docs/guide.md", "Status: active\n\nSee `src/a.py` and `src/b.py`.\n")
        s2 = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py", "src/b.py"])
        self.assertFalse(s2["skipped"])
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")["drift_refs"],
            ["src/a.py", "src/b.py"])
        # Remove all references.
        self._write("docs/guide.md", "Status: active\n\nNo refs now.\n")
        s3 = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py", "src/b.py"])
        self.assertFalse(s3["skipped"])
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")["drift_refs"], [])

    def test_gardener_only_working_tree_edit_still_skips(self):
        # A mechanical Last verified working-tree bump must NOT thrash the skip
        # (it is normalized out of the content digest).
        _init_git_repo(self.root)
        self._write("docs/guide.md", "Status: active\nLast verified: 2020-01-01\n\nBody.\n")
        _commit_all_at(self.root, "c1", _T0)
        self._update(["docs/guide.md"], ["docs/guide.md"])
        self._write("docs/guide.md", "Status: active\nLast verified: 2026-07-14\n\nBody.\n")
        summary = self._update(["docs/guide.md"], ["docs/guide.md"])
        self.assertTrue(summary["skipped"], "gardener-only working-tree edit is normalized out")


def _git(root, *args, ts=None):
    env = dict(os.environ)
    if ts is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{ts} +0000"
    return subprocess.run(["git", "-C", str(root), *args], check=True, env=env,
                          capture_output=True, text=True)


class GardenerDetectorFailClosedTests(_DriftCase):
    """Delivery re-review P1: on classifier failure, prior drift is preserved
    — a detector error must NOT republish the gardener-reset defect."""

    def test_detector_failure_preserves_prior_drift(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md", "Status: active\nLast verified: 2020-01-01\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        # Healthy build → commits_since 3, drifted.
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")["commits_since"], 3)
        fp_before = None
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            fp_before = store.get_meta(self.iss.META_DRIFT_FINGERPRINT)
        finally:
            store.close()
        # Commit a gardener-only bump, then FORCE the detector to fail.
        self._write("docs/guide.md", "Status: active\nLast verified: 2026-07-14\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "gardener bump", _T0 + 5000)
        real = self.iss._gardener_only_pairs
        self.iss._gardener_only_pairs = lambda *a, **k: (False, set())
        try:
            summary = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        finally:
            self.iss._gardener_only_pairs = real
        self.assertTrue(summary.get("drift_detect_failed"))
        self.assertTrue(summary.get("skipped"))
        # Prior drift rows + fingerprint untouched — NOT reset to 0.
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["commits_since"], 3, "prior drift must be preserved")
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertEqual(store.get_meta(self.iss.META_DRIFT_FINGERPRINT), fp_before)
        finally:
            store.close()


class HeaderScopedNormalizationTests(_DriftCase):
    """Delivery re-review P1: only the canonical header `Last verified: <date>`
    is mechanical — body/fenced lookalikes are real content."""

    def test_strip_only_touches_header_date_line(self):
        text = ("# Doc\n\nStatus: active\nLast verified: 2020-01-01\n\n"
                "## Body\n\nExample: `Last verified: see src/a.py` in a code span.\n"
                "Last verified: not-a-date line in body\n")
        stripped = self.iss._strip_gardener_field(text)
        self.assertNotIn("Last verified: 2020-01-01", stripped)  # header date removed
        self.assertIn("Last verified: see src/a.py", stripped)   # body span kept
        self.assertIn("Last verified: not-a-date line in body", stripped)  # body kept

    def test_body_reference_edit_invalidates_skip(self):
        # A body line `Last verified: see src/a.py` → `src/b.py` must change the
        # normalized digest (it is NOT a header date line).
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("src/b.py", "y = 1\n")
        self._write("docs/guide.md",
                    "Status: active\nLast verified: 2020-01-01\n\n"
                    "## Notes\n\nOnce `Last verified: see src/a.py` was noted.\n")
        _commit_all_at(self.root, "c1", _T0)
        first = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py", "src/b.py"])
        self.assertFalse(first["skipped"])
        # Change the BODY lookalike's referenced path (uncommitted).
        self._write("docs/guide.md",
                    "Status: active\nLast verified: 2020-01-01\n\n"
                    "## Notes\n\nOnce `Last verified: see src/b.py` was noted.\n")
        summary = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py", "src/b.py"])
        self.assertFalse(summary["skipped"],
                         "a body reference change must not be normalized away")


class MergeDagAncestryTests(_DriftCase):
    """Delivery re-review P1: churn is counted over the anchor..HEAD ancestry
    range, matching `git rev-list`, not relative log position."""

    def test_sibling_branch_churn_is_counted(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "A: anchor", _T0)
        anchor = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        branch = _git(self.root, "branch", "--show-current").stdout.strip() or "master"
        # Sibling branch off the anchor changes src/a.py.
        _git(self.root, "checkout", "-q", "-b", "sib")
        self._write("src/a.py", "x = 2\n")
        _commit_all_at(self.root, "S: sibling churn", _T0 + 100)
        # Merge the sibling back into the main branch (no-ff → merge commit).
        _git(self.root, "checkout", "-q", branch)
        _git(self.root, "merge", "--no-ff", "-m", "merge sib", "sib", ts=_T0 + 200)
        head = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        # Ground truth from git itself.
        rev = _git(self.root, "rev-list", "--count", f"{anchor}..{head}", "--", "src/a.py")
        self.assertEqual(int(rev.stdout.strip()), 1, "git ground truth: 1 sibling commit")
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["commits_since"], 1,
                         "ancestry range must count the merged sibling commit")


class GardenerContentClassificationTests(_DriftCase):
    """Round-4 P1: gardener classification is by metadata-scoped content, not
    line shape — a fenced/body exact-date edit is MATERIAL."""

    def test_body_date_edit_is_material_not_gardener(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md",
                    "Status: active\nLast verified: 2020-01-01\n\n"
                    "## Notes\n\nExample fence:\n\n    Last verified: 2020-01-01\n\n"
                    "See `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        # Change ONLY the body/fenced date line (date-form, but in the body).
        self._write("docs/guide.md",
                    "Status: active\nLast verified: 2020-01-01\n\n"
                    "## Notes\n\nExample fence:\n\n    Last verified: 2026-07-14\n\n"
                    "See `src/a.py`.\n")
        _commit_all_at(self.root, "body date edit", _T0 + 5000)
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        # The body edit is the newest MATERIAL commit → anchor moves to it →
        # zero churn after it. (If it were misclassified gardener-only, the
        # anchor would stay at c1 and commits_since would be 3.)
        self.assertEqual(drift["commits_since"], 0,
                         "a body/fenced date edit must be material, not gardener-only")
        self.assertFalse(drift["drifted"])

    def test_header_date_edit_still_gardener(self):
        # Control: the canonical HEADER date bump stays gardener-only.
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md", "Status: active\nLast verified: 2020-01-01\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._write("docs/guide.md", "Status: active\nLast verified: 2026-07-14\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "header gardener bump", _T0 + 5000)
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")
        self.assertEqual(drift["commits_since"], 3)
        self.assertTrue(drift["drifted"])


class GitWalkFailClosedTests(_DriftCase):
    """Round-4 P1: both git walks are typed and fail closed; a failure of
    either preserves prior attribution + drift + fingerprint."""

    def _seed_healthy(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")["commits_since"], 3)

    def test_collect_history_typed_result(self):
        _init_git_repo(self.root)
        self._write("a.py", "x=1\n")
        _commit_all_at(self.root, "c1", _T0)
        ok, commits = self.iss._collect_git_history(self.root)
        self.assertTrue(ok)
        self.assertTrue(commits and self.iss._HEX40_RE.match(commits[0]["sha"]))

    def test_malformed_history_output_is_not_ok(self):
        _init_git_repo(self.root)
        self._write("a.py", "x=1\n")
        _commit_all_at(self.root, "c1", _T0)
        import subprocess as _sp
        real = self.iss.subprocess_util.isolated_run

        def fake(cmd, **k):
            if "--name-only" in cmd:
                return _sp.CompletedProcess(cmd, 0, stdout="\x01NOT_A_SHA\x02123\x02\x02subj\n", stderr="")
            return real(cmd, **k)

        self.iss.subprocess_util.isolated_run = fake
        try:
            ok, commits = self.iss._collect_git_history(self.root)
        finally:
            self.iss.subprocess_util.isolated_run = real
        self.assertFalse(ok)

    def test_history_walk_failure_preserves_prior_drift(self):
        self._seed_healthy()
        self._write("src/a.py", "x = 99\n")
        _commit_all_at(self.root, "new HEAD", _T0 + 9000)
        real = self.iss._collect_git_history
        self.iss._collect_git_history = lambda *a, **k: (False, [])
        try:
            summary = self._update(["docs/guide.md"], ["docs/guide.md", "src/a.py"])
        finally:
            self.iss._collect_git_history = real
        self.assertTrue(summary.get("drift_detect_failed"))
        self.assertTrue(summary.get("skipped"))
        self.assertEqual(summary.get("written", 0), 0)
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/guide.md")["commits_since"], 3,
            "healthy drift must survive a history-walk failure")

    def test_malformed_gardener_patch_is_not_ok(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/guide.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        ok, commits = self.iss._collect_git_history(self.root)
        self.assertTrue(ok)
        import subprocess as _sp
        real = self.iss.subprocess_util.isolated_run

        def fake(cmd, **k):
            if "-U0" in cmd:  # the gardener -p pass
                return _sp.CompletedProcess(cmd, 0, stdout="+orphan content, no commit sentinel\n", stderr="")
            return real(cmd, **k)

        self.iss.subprocess_util.isolated_run = fake
        try:
            gok, pairs = self.iss._gardener_only_pairs(self.root, commits, ["docs/guide.md"])
        finally:
            self.iss.subprocess_util.isolated_run = real
        self.assertFalse(gok, "content before any commit sentinel is malformed → ok=False")


class EvilMergeAttributionTests(_DriftCase):
    """Adversarial-pass P2: a file changed only inside a merge commit's own
    tree must be attributed to the merge (`-c`), matching `git rev-list`."""

    def test_ref_changed_in_merge_is_counted(self):
        _init_git_repo(self.root)
        self._write("src/code.py", "v0\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/code.py`.\n")
        _commit_all_at(self.root, "A anchor", _T0)
        anchor = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        branch = _git(self.root, "branch", "--show-current").stdout.strip() or "master"
        _git(self.root, "checkout", "-q", "-b", "sib")
        self._write("o.py", "side\n")
        _commit_all_at(self.root, "sib touches o.py", _T0 + 100)
        _git(self.root, "checkout", "-q", branch)
        env = dict(os.environ, GIT_AUTHOR_DATE=f"{_T0+200} +0000", GIT_COMMITTER_DATE=f"{_T0+200} +0000")
        subprocess.run(["git", "-C", str(self.root), "merge", "--no-commit", "--no-ff", "sib"],
                       env=env, capture_output=True)
        self._write("src/code.py", "vEVIL\n")  # change code.py IN the merge
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "M evil merge"],
                       check=True, env=env)
        head = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        rev = int(_git(self.root, "rev-list", "--count", f"{anchor}..{head}", "--", "src/code.py").stdout.strip())
        self.assertEqual(rev, 1, "git ground truth: the merge changed code.py")
        self._update(["docs/g.md"], ["docs/g.md", "src/code.py", "o.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")
        self.assertEqual(drift["commits_since"], 1,
                         "a ref changed inside a merge must be counted (-c attribution)")

    def test_clean_merge_does_not_overcount(self):
        # A clean merge (no evil change) must not attribute branch files to
        # itself — `-c` lists nothing for it.
        _init_git_repo(self.root)
        self._write("src/code.py", "v0\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/code.py`.\n")
        _commit_all_at(self.root, "A anchor", _T0)
        anchor = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        branch = _git(self.root, "branch", "--show-current").stdout.strip() or "master"
        _git(self.root, "checkout", "-q", "-b", "sib")
        self._write("src/code.py", "v1\n")  # the branch changes code.py once
        _commit_all_at(self.root, "sib changes code.py", _T0 + 100)
        _git(self.root, "checkout", "-q", branch)
        _git(self.root, "merge", "--no-ff", "-m", "clean merge", "sib", ts=_T0 + 200)
        head = _git(self.root, "rev-parse", "HEAD").stdout.strip()
        rev = int(_git(self.root, "rev-list", "--count", f"{anchor}..{head}", "--", "src/code.py").stdout.strip())
        self.assertEqual(rev, 1, "only the sib commit changed code.py")
        self._update(["docs/g.md"], ["docs/g.md", "src/code.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")
        self.assertEqual(drift["commits_since"], 1, "clean merge must not double-count")


class GardenerBatchAndFailClosedTests(_DriftCase):
    """Adversarial-pass: the batched confirmation fails closed on a real git
    error (not just absence), and a heading-less body date stays material."""

    def test_real_git_error_on_confirm_fails_closed(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\nLast verified: 2020-01-01\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._write("docs/g.md", "Status: active\nLast verified: 2026-07-14\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "gardener bump", _T0 + 5000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])  # healthy: commits_since 3
        self.assertEqual(self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3)
        # Force the blob batch to FAIL (real error, not missing) on the next build.
        real = self.iss._batch_git_blobs
        self.iss._batch_git_blobs = lambda *a, **k: None
        try:
            self._write("docs/g.md", "Status: active\nLast verified: 2026-08-01\n\nSee `src/a.py`.\n")
            _commit_all_at(self.root, "another gardener bump", _T0 + 6000)
            summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        finally:
            self.iss._batch_git_blobs = real
        self.assertTrue(summary.get("drift_detect_failed"))
        self.assertEqual(self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3,
                         "a real confirm error must preserve prior drift, not reset it")

    def test_heading_less_body_date_edit_is_material(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        # A doc with NO `## ` heading; a date-form line lives in the body.
        self._write("docs/g.md",
                    "Status: active\nLast verified: 2020-01-01\n\n"
                    "Prose about `src/a.py`.\nLast verified: 2020-01-01\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        # Change ONLY the BODY date line (the header one is untouched).
        self._write("docs/g.md",
                    "Status: active\nLast verified: 2020-01-01\n\n"
                    "Prose about `src/a.py`.\nLast verified: 2026-07-14\n")
        _commit_all_at(self.root, "body date edit", _T0 + 5000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")
        self.assertEqual(drift["commits_since"], 0,
                         "body date edit is material → anchor moves to it (frontmatter scoping)")


class DriftTornWriteTests(_DriftCase):
    """Adversarial-pass P3: attribution + drift + fingerprint replace in ONE
    transaction — a fault mid-write rolls back, no torn state."""

    def test_fault_mid_write_rolls_back_all(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            before_landings = store._conn.execute("SELECT COUNT(*) FROM wave_landing").fetchone()[0]
            fp_before = store.get_meta(self.iss.META_DRIFT_FINGERPRINT)
            # An un-serializable drift_refs makes the param build raise INSIDE
            # the single transaction, after the DELETEs — must roll back.
            class Bad:
                pass
            with self.assertRaises(TypeError):
                store.replace_attribution_and_drift(
                    landings=[("1abcd", "d" * 40, 1)],
                    change_files=[("1abcd", "src/a.py")],
                    entries={"docs/g.md": {"drift_refs": [Bad()], "drifted": False,
                                           "commits_since": 0, "anchor_kind": "content"}},
                    fingerprint="NEWFP",
                )
            after_landings = store._conn.execute("SELECT COUNT(*) FROM wave_landing").fetchone()[0]
            self.assertEqual(after_landings, before_landings, "attribution DELETE rolled back")
            self.assertEqual(store.get_meta(self.iss.META_DRIFT_FINGERPRINT), fp_before,
                             "fingerprint unchanged after a rolled-back write")
        finally:
            store.close()


class GardenerFrameCompletenessTests(_DriftCase):
    """Round-4 P1: pass-1 rejects truncated patch frames (sentinel-only,
    diff-only, header-only) as ok=False; a complete frame passes."""

    def _run_with_patch(self, fake_stdout):
        _init_git_repo(self.root)
        self._write("docs/g.md", "Status: active\n\nBody.\n")
        _commit_all_at(self.root, "c1", _T0)
        ok, commits = self.iss._collect_git_history(self.root)
        self.assertTrue(ok)
        import subprocess as _sp
        real = self.iss.subprocess_util.isolated_run

        def fake(cmd, **k):
            if "-U0" in cmd:
                return _sp.CompletedProcess(cmd, 0, stdout=fake_stdout, stderr="")
            return real(cmd, **k)

        self.iss.subprocess_util.isolated_run = fake
        try:
            return self.iss._gardener_only_pairs(self.root, commits, ["docs/g.md"])
        finally:
            self.iss.subprocess_util.isolated_run = real

    def test_sentinel_only_is_not_ok(self):
        ok, _ = self._run_with_patch("\x01" + "a" * 40 + "\n")
        self.assertFalse(ok)

    def test_diff_only_is_not_ok(self):
        ok, _ = self._run_with_patch("\x01" + "a" * 40 + "\ndiff --git a/docs/g.md b/docs/g.md\n")
        self.assertFalse(ok)

    def test_header_only_no_content_is_not_ok(self):
        s = ("\x01" + "a" * 40 + "\ndiff --git a/docs/g.md b/docs/g.md\n"
             "--- a/docs/g.md\n+++ b/docs/g.md\n@@ -1 +1 @@\n")
        ok, _ = self._run_with_patch(s)
        self.assertFalse(ok)

    def test_complete_frame_is_ok(self):
        s = ("\x01" + "a" * 40 + "\ndiff --git a/docs/g.md b/docs/g.md\n"
             "--- a/docs/g.md\n+++ b/docs/g.md\n@@ -1 +1 @@\n-old\n+new\n")
        ok, _ = self._run_with_patch(s)
        self.assertTrue(ok)


class HistoryStrictFramingTests(_DriftCase):
    """Round-4 P1: `_collect_git_history` rejects orphan pre-sentinel content,
    invalid timestamps, and duplicate SHAs; each malformed exit-0 shape
    preserves last-good drift."""

    def _history_with(self, fake_stdout):
        import subprocess as _sp
        real = self.iss.subprocess_util.isolated_run

        def fake(cmd, **k):
            if "--name-only" in cmd:
                return _sp.CompletedProcess(cmd, 0, stdout=fake_stdout, stderr="")
            return real(cmd, **k)

        self.iss.subprocess_util.isolated_run = fake
        try:
            return self.iss._collect_git_history(self.root)
        finally:
            self.iss.subprocess_util.isolated_run = real

    def test_orphan_pre_sentinel_content(self):
        ok, _ = self._history_with("some/orphan/path.py\n\x01" + "a" * 40 + "\x02100\x02\x02subj\n")
        self.assertFalse(ok)

    def test_invalid_timestamp(self):
        ok, _ = self._history_with("\x01" + "a" * 40 + "\x02notanumber\x02\x02subj\n")
        self.assertFalse(ok)

    def test_duplicate_sha(self):
        sha = "a" * 40
        ok, _ = self._history_with(f"\x01{sha}\x02100\x02\x02s1\n\x01{sha}\x02200\x02\x02s2\n")
        self.assertFalse(ok)

    def test_error_text_before_sentinel(self):
        ok, _ = self._history_with("fatal: your current branch does not have any commits yet\n")
        self.assertFalse(ok)

    def test_every_malformed_shape_preserves_last_good(self):
        # Seed healthy drift, then each malformed history shape must preserve it.
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertEqual(self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3)
        sha = "b" * 40
        shapes = (
            "orphan\n\x01" + sha + "\x02100\x02\x02s\n",
            "\x01" + sha + "\x02bad\x02\x02s\n",
            f"\x01{sha}\x02100\x02\x02a\n\x01{sha}\x02200\x02\x02b\n",
        )
        for j, shape in enumerate(shapes):
            self._write("src/a.py", f"x = {900 + j}\n")  # unique so each commit lands
            _commit_all_at(self.root, f"new head {j}", _T0 + 20000 + j * 10)
            import subprocess as _sp
            real = self.iss.subprocess_util.isolated_run

            def fake(cmd, _real=real, _shape=shape, **k):
                if "--name-only" in cmd:
                    return _sp.CompletedProcess(cmd, 0, stdout=_shape, stderr="")
                return _real(cmd, **k)

            self.iss.subprocess_util.isolated_run = fake
            try:
                summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
            finally:
                self.iss.subprocess_util.isolated_run = real
            self.assertTrue(summary.get("drift_detect_failed"), shape[:20])
            self.assertEqual(
                self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3,
                f"malformed shape must preserve last-good: {shape[:20]!r}")


class NonGitProjectTests(_DriftCase):
    """A project not (yet) under source control must degrade cleanly — drift
    skips (no error, no fail-closed), and the memory seqlock works without
    git. Guards against the git-fail-closed hardening breaking non-git repos."""

    def test_non_git_drift_skips_without_error(self):
        # No _init_git_repo — the repo has no .git at all.
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        self._write("src/a.py", "x = 1\n")
        summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertTrue(summary.get("skipped"))
        self.assertIsNone(summary.get("error"))
        self.assertFalse(summary.get("drift_detect_failed"),
                         "a non-git repo must SKIP, not fail-closed")
        # No drift row is written (nothing to anchor against).
        self.assertIsNone(self.iss.doc_drift_for_path(self.index_dir, "docs/g.md"))

    def test_memory_seqlock_works_without_git(self):
        self.assertTrue(self.iss.memory_fence(self.index_dir))
        gen = self.iss.memory_advance(self.index_dir)
        self.assertIsNotNone(gen)
        state = self.iss.read_memory_state(self.index_dir)
        self.assertTrue(state["epoch"])  # epoch minted without git
        self.assertGreaterEqual(state["generation"], 1)

    def test_typed_history_walk_on_non_git_is_not_ok(self):
        # Direct contract: no git → (False, []); callers gate on _git_head so
        # this is never reached in a build, but the typed result is honest.
        ok, commits = self.iss._collect_git_history(self.root)
        self.assertFalse(ok)
        self.assertEqual(commits, [])

    def test_git_to_non_git_transition_clears_stale_drift(self):
        # Round-4 re-review P1: a git-built index whose repo later loses git
        # authority (git metadata removed, or the built index copied into a
        # non-git root) must NOT keep serving stale git-derived drift.
        import shutil
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        row = self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")
        self.assertTrue(row["drifted"])
        self.assertEqual(row["commits_since"], 3)
        # Git authority disappears.
        _rmtree_git(self.root / ".git")
        self.assertEqual(self.iss._git_head(self.root), "")
        summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertTrue(summary.get("skipped"))
        self.assertIsNone(summary.get("error"))
        self.assertTrue(summary.get("cleared_git_derived"),
                        "the non-git path must clear the stale git-derived rows")
        # The stale row is gone — no reader can serve the old drift claim.
        self.assertIsNone(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md"),
            "stale git-derived drift must not survive the git→non-git transition")

    def test_non_git_clear_is_idempotent_no_repeat_work(self):
        # After the first clear the non-git path finds nothing to remove — it
        # must not report cleared_git_derived on every subsequent build.
        import shutil
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        _rmtree_git(self.root / ".git")
        first = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertTrue(first.get("cleared_git_derived"))
        second = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertIsNone(second.get("cleared_git_derived"),
                          "an already-clean non-git store must not re-clear")


class GitAuthorityTypedStateTests(_DriftCase):
    """Round-4 re-review P1: `_git_head` conflated timeout / git-missing /
    nonzero into one empty value, so a transient probe failure destructively
    cleared valid drift. `_git_authority` returns typed states; drift clears
    ONLY on a confirmed non-git transition and PRESERVES on a probe failure."""

    def _seed_drift(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3)

    def test_authority_states(self):
        # git with a HEAD
        _init_git_repo(self.root)
        self._write("a.py", "x=1\n")
        _commit_all_at(self.root, "c1", _T0)
        state, head = self.iss._git_authority(self.root)
        self.assertEqual(state, "git")
        self.assertTrue(self.iss._HEX40_RE.match(head))

    def test_authority_unborn_head_is_git_not_cleared(self):
        _init_git_repo(self.root)  # repo exists, NO commits → unborn HEAD
        state, head = self.iss._git_authority(self.root)
        self.assertEqual(state, "git")
        self.assertEqual(head, "")

    def test_authority_confirmed_non_git(self):
        state, head = self.iss._git_authority(self.root)  # no .git at all
        self.assertEqual(state, "confirmed_non_git")

    def test_empty_corrupt_git_dir_is_probe_failed(self):
        # A repo whose `.git/` is emptied/corrupt: git says "not a git
        # repository", but the marker is PRESENT → must NOT clear (probe_failed).
        import shutil
        _init_git_repo(self.root)
        self._write("a.py", "x=1\n")
        _commit_all_at(self.root, "c1", _T0)
        _rmtree_git(self.root / ".git")
        (self.root / ".git").mkdir()  # present but empty/corrupt
        self.assertEqual(self.iss._git_authority(self.root)[0], "probe_failed")

    def test_broken_worktree_pointer_is_probe_failed(self):
        # A `.git` FILE pointing at a missing gitdir: present-but-invalid marker.
        import shutil
        _init_git_repo(self.root)
        self._write("a.py", "x=1\n")
        _commit_all_at(self.root, "c1", _T0)
        _rmtree_git(self.root / ".git")
        (self.root / ".git").write_text("gitdir: /nonexistent/git/dir\n", encoding="utf-8")
        self.assertEqual(self.iss._git_authority(self.root)[0], "probe_failed")

    def test_inherited_bad_git_dir_env_is_stripped(self):
        # A valid repo probed with an inherited GIT_DIR=/missing must resolve to
        # the REAL repo (env override stripped), not be mis-read as non-git.
        _init_git_repo(self.root)
        self._write("a.py", "x=1\n")
        _commit_all_at(self.root, "c1", _T0)
        old = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = "/nonexistent/git/dir"
        try:
            state, head = self.iss._git_authority(self.root)
        finally:
            if old is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = old
        self.assertEqual(state, "git")
        self.assertTrue(self.iss._HEX40_RE.match(head))

    def test_corrupt_git_preserves_drift_on_both_paths(self):
        # Real-git integration: a present-but-corrupt `.git/` must PRESERVE drift
        # on BOTH the build-tail and the zero-change reconcile paths.
        import shutil
        self._seed_drift()
        _rmtree_git(self.root / ".git")
        (self.root / ".git").mkdir()  # corrupt marker present
        # build-tail
        summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertTrue(summary.get("git_probe_failed"))
        self.assertNotIn("cleared_git_derived", summary)
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3)
        # no-op reconcile
        out = self.iss.reconcile_non_git_drift(self.root, self.index_dir)
        self.assertEqual(out.get("git_state"), "probe_failed")
        self.assertIsNone(out.get("cleared_git_derived"))
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3)

    def test_probe_failure_preserves_last_good_drift(self):
        # A forced timeout/exception during the authority probe must NOT clear
        # valid drift (the destructive-clear-on-timeout defect).
        self._seed_drift()
        real = self.iss.subprocess_util.isolated_run

        def boom(cmd, **k):
            if cmd[:2] == ["git", "-C"]:
                raise TimeoutError("forced probe timeout")
            return real(cmd, **k)

        self.iss.subprocess_util.isolated_run = boom
        try:
            state, _ = self.iss._git_authority(self.root)
            self.assertEqual(state, "probe_failed")
            summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        finally:
            self.iss.subprocess_util.isolated_run = real
        self.assertTrue(summary.get("git_probe_failed"))
        self.assertNotIn("cleared_git_derived", summary)
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3,
            "a probe failure must preserve last-good drift, never clear it")

    def _fake_git_result(self, returncode, stderr):
        """Patch isolated_run so BOTH git probes return the given failure."""
        real = self.iss.subprocess_util.isolated_run

        def fake(cmd, **k):
            if cmd[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr=stderr)
            return real(cmd, **k)

        return real, fake

    def test_dubious_ownership_is_probe_failed_not_non_git(self):
        # The reproduction: `fatal: detected dubious ownership` (exit 128) must
        # NOT be read as confirmed_non_git (which would authorize clearing).
        real, fake = self._fake_git_result(
            128, "fatal: detected dubious ownership in repository at '/x'\n")
        self.iss.subprocess_util.isolated_run = fake
        try:
            state, _ = self.iss._git_authority(self.root)
        finally:
            self.iss.subprocess_util.isolated_run = real
        self.assertEqual(state, "probe_failed")

    def test_permission_failure_is_probe_failed(self):
        real, fake = self._fake_git_result(
            128, "fatal: unable to access '.git/': Permission denied\n")
        self.iss.subprocess_util.isolated_run = fake
        try:
            self.assertEqual(self.iss._git_authority(self.root)[0], "probe_failed")
        finally:
            self.iss.subprocess_util.isolated_run = real

    def test_corrupt_repo_is_probe_failed(self):
        real, fake = self._fake_git_result(128, "fatal: bad object HEAD\n")
        self.iss.subprocess_util.isolated_run = fake
        try:
            self.assertEqual(self.iss._git_authority(self.root)[0], "probe_failed")
        finally:
            self.iss.subprocess_util.isolated_run = real

    def test_unexpected_nonzero_output_is_probe_failed(self):
        real, fake = self._fake_git_result(1, "some unexpected non-fatal noise\n")
        self.iss.subprocess_util.isolated_run = fake
        try:
            self.assertEqual(self.iss._git_authority(self.root)[0], "probe_failed")
        finally:
            self.iss.subprocess_util.isolated_run = real

    def test_positive_not_a_repository_is_confirmed_non_git(self):
        real, fake = self._fake_git_result(
            128, "fatal: not a git repository (or any of the parent directories): .git\n")
        self.iss.subprocess_util.isolated_run = fake
        try:
            self.assertEqual(self.iss._git_authority(self.root)[0], "confirmed_non_git")
        finally:
            self.iss.subprocess_util.isolated_run = real

    def test_dubious_ownership_preserves_drift_on_build_tail(self):
        # End-to-end: the build-tail drift pass must PRESERVE last-good drift
        # under a dubious-ownership error, never clear it.
        self._seed_drift()
        real, fake = self._fake_git_result(
            128, "fatal: detected dubious ownership in repository at '/x'\n")
        self.iss.subprocess_util.isolated_run = fake
        try:
            summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        finally:
            self.iss.subprocess_util.isolated_run = real
        self.assertTrue(summary.get("git_probe_failed"))
        self.assertNotIn("cleared_git_derived", summary)
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3,
            "an ambiguous git error must never clear valid drift")

    def test_dubious_ownership_preserves_drift_on_reconcile_path(self):
        # And the zero-change reconciliation path must preserve too.
        self._seed_drift()
        real, fake = self._fake_git_result(
            128, "fatal: detected dubious ownership in repository at '/x'\n")
        self.iss.subprocess_util.isolated_run = fake
        try:
            out = self.iss.reconcile_non_git_drift(self.root, self.index_dir)
        finally:
            self.iss.subprocess_util.isolated_run = real
        self.assertEqual(out.get("git_state"), "probe_failed")
        self.assertIsNone(out.get("cleared_git_derived"))
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3)

    def test_confirmed_non_git_clear_failure_fails_closed(self):
        # If the clear itself fails on a confirmed transition, surface
        # drift_clear_failed (not a silent clean skip) and retry next build.
        self._seed_drift()
        import shutil
        _rmtree_git(self.root / ".git")

        real_ctor = self.iss.IndexStateStore

        class _BoomStore(real_ctor):
            def clear_attribution_and_drift(self):
                raise RuntimeError("forced clear failure")

        self.iss.IndexStateStore = _BoomStore
        try:
            summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        finally:
            self.iss.IndexStateStore = real_ctor
        self.assertTrue(summary.get("drift_clear_failed"))
        self.assertIn("error", summary)
        self.assertNotIn("cleared_git_derived", summary)


class NoOpBuildDriftReconcileTests(_DriftCase):
    """Round-4 re-review P1: a true no-op build skipped the tail drift pass, so
    an unchanged copied index / a repo that lost .git kept serving stale drift.
    `reconcile_non_git_drift` (gated on `has_drift_state`) closes that path."""

    def test_has_drift_state_reflects_store(self):
        self.assertFalse(self.iss.has_drift_state(self.index_dir))
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertTrue(self.iss.has_drift_state(self.index_dir))

    def test_reconcile_clears_on_confirmed_non_git(self):
        import shutil
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        _rmtree_git(self.root / ".git")
        out = self.iss.reconcile_non_git_drift(self.root, self.index_dir)
        self.assertTrue(out.get("cleared_git_derived"))
        self.assertIsNone(self.iss.doc_drift_for_path(self.index_dir, "docs/g.md"))

    def test_reconcile_preserves_on_real_git(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)
        self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        out = self.iss.reconcile_non_git_drift(self.root, self.index_dir)
        self.assertEqual(out.get("git_state"), "git")
        self.assertIsNone(out.get("cleared_git_derived"))
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3)


class AmbientGitDirIsolationTests(_DriftCase):
    """Round-4 re-review (5) P1: `_git_authority` sanitized its own env, but the
    downstream freshness / history / gardener / blob-read subprocesses did not,
    so an ambient GIT_DIR pointing at an unrelated DECOY repo redirected them.
    Every git subprocess must derive from the TARGET root only."""

    def _make_decoy(self) -> Path:
        decoy = Path(self._tmp.name) / "decoy"
        decoy.mkdir()
        _init_git_repo(decoy)
        (decoy / "decoy_only.py").write_text("y = 1\n", encoding="utf-8")
        _commit_all_at(decoy, "decoy commit", _T0)
        return decoy

    def _seed_target(self):
        _init_git_repo(self.root)
        self._write("src/a.py", "x = 1\n")
        self._write("docs/g.md", "Status: active\n\nSee `src/a.py`.\n")
        _commit_all_at(self.root, "c1", _T0)
        for i in range(3):
            self._write("src/a.py", f"x = {i + 2}\n")
            _commit_all_at(self.root, f"churn {i}", _T0 + (i + 1) * 1000)

    def _with_ambient_git_dir(self, decoy: Path):
        saved = {k: os.environ.get(k) for k in ("GIT_DIR", "GIT_WORK_TREE")}
        os.environ["GIT_DIR"] = str(decoy / ".git")
        os.environ["GIT_WORK_TREE"] = str(decoy)

        def restore():
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.addCleanup(restore)

    def test_history_and_freshness_derive_from_target_not_decoy(self):
        self._seed_target()
        decoy = self._make_decoy()
        self._with_ambient_git_dir(decoy)
        # Authority still resolves the target (sanitized).
        self.assertEqual(self.iss._git_authority(self.root)[0], "git")
        # Drift history walk reads the TARGET tree, never the decoy.
        ok, commits = self.iss._collect_git_history(self.root)
        self.assertTrue(ok)
        files = {f for c in commits for f in c["files"]}
        self.assertIn("src/a.py", files)
        self.assertNotIn("decoy_only.py", files)
        # Freshness extraction reads the TARGET tree.
        rows, _ = self.iss._collect_git_freshness(self.root, {"src/a.py", "docs/g.md"})
        self.assertIn("src/a.py", rows)
        self.assertNotIn("decoy_only.py", rows)

    def test_end_to_end_drift_derives_from_target_under_ambient_git_dir(self):
        self._seed_target()
        decoy = self._make_decoy()
        self._with_ambient_git_dir(decoy)
        # First (fresh) drift computation happens entirely under the decoy env.
        summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertFalse(summary.get("skipped"), "a fresh computation must not skip")
        row = self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")
        self.assertEqual(row["commits_since"], 3,
                         "drift must derive from the TARGET history, not the decoy's")
        self.assertTrue(row["drifted"])

    def _raw_git_log_count(self) -> int:
        # A DELIBERATELY unsanitized git log (inherits the ambient env) — used
        # to prove an ambient interpretation var actually perturbs raw git, so
        # the sanitized-preserves assertions are not vacuous.
        r = subprocess.run(
            ["git", "-C", str(self.root), "log", "--oneline"],
            capture_output=True, text=True, env=dict(os.environ),
        )
        return len([ln for ln in r.stdout.splitlines() if ln.strip()])

    def _set_ambient(self, **vars_):
        saved = {k: os.environ.get(k) for k in vars_}
        os.environ.update({k: str(v) for k, v in vars_.items()})

        def restore():
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.addCleanup(restore)

    def test_ambient_git_shallow_file_does_not_truncate_history(self):
        self._seed_target()
        ok, full = self.iss._collect_git_history(self.root)
        self.assertTrue(ok)
        full_n = len(full)
        self.assertGreaterEqual(full_n, 4)
        # A shallow-boundary file grafting a mid-history commit to parentless.
        shas = [c["sha"] for c in full]  # newest first
        boundary = shas[len(shas) // 2]
        shallow = Path(self._tmp.name) / "shallow-boundary"
        shallow.write_text(boundary + "\n", encoding="utf-8")
        self._set_ambient(GIT_SHALLOW_FILE=str(shallow))
        # Guard: the ambient var MUST perturb raw git, else the test is vacuous.
        self.assertLess(self._raw_git_log_count(), full_n,
                        "GIT_SHALLOW_FILE should truncate an unsanitized git log")
        # The sanitized derivation reads the FULL target history regardless.
        ok2, sanitized = self.iss._collect_git_history(self.root)
        self.assertTrue(ok2)
        self.assertEqual(len(sanitized), full_n,
                         "GIT_SHALLOW_FILE must not truncate the sanitized history")
        # And end-to-end drift stays derived from the full history.
        summary = self._update(["docs/g.md"], ["docs/g.md", "src/a.py"])
        self.assertFalse(summary.get("skipped"))
        self.assertEqual(
            self.iss.doc_drift_for_path(self.index_dir, "docs/g.md")["commits_since"], 3,
            "drift must derive from the full target history, not the shallow boundary")

    def test_ambient_git_graft_file_does_not_reshape_history(self):
        self._seed_target()
        ok, full = self.iss._collect_git_history(self.root)
        self.assertTrue(ok)
        full_n = len(full)
        shas = [c["sha"] for c in full]
        boundary = shas[len(shas) // 2]
        graft = Path(self._tmp.name) / "grafts"
        graft.write_text(boundary + "\n", encoding="utf-8")  # graft: no parents
        self._set_ambient(GIT_GRAFT_FILE=str(graft))
        # Guard the graft actually perturbs raw git before asserting isolation.
        if self._raw_git_log_count() >= full_n:
            self.skipTest("this git honors grafts differently; boundary not effective")
        ok2, sanitized = self.iss._collect_git_history(self.root)
        self.assertTrue(ok2)
        self.assertEqual(len(sanitized), full_n,
                         "GIT_GRAFT_FILE must not reshape the sanitized history")

    def test_local_env_vars_census_all_stripped(self):
        # Fixture (reviewer-required): every var in git's authoritative
        # `--local-env-vars` census must be in the strip-set.
        res = subprocess.run(
            ["git", "rev-parse", "--local-env-vars"], capture_output=True, text=True)
        if res.returncode != 0:
            self.skipTest("git rev-parse --local-env-vars unavailable")
        census = {t.strip() for t in res.stdout.split() if t.strip().startswith("GIT_")}
        self.assertTrue(census, "census must be non-empty")
        strip = self.iss._git_strip_vars()
        missing = census - strip
        self.assertEqual(
            missing, set(),
            f"every repository-local git var must be stripped or justified; missing: {missing}")

    # --- rename determinism via a pinned command flag (NOT config neutralization) ---

    def _seed_rename(self):
        # A repo whose newest commit is a pure content-identical rename. Rename
        # DETECTION (diff.renames) is what would otherwise vary the --name-only
        # attribution; the derivation pins `--no-renames` so it is deterministic.
        _init_git_repo(self.root)
        self._write("a.txt", "l1\nl2\nl3\nl4\nl5\n")
        _commit_all_at(self.root, "add a", _T0)
        subprocess.run(["git", "-C", str(self.root), "mv", "a.txt", "b.txt"], check=True)
        _commit_all_at(self.root, "rename a->b", _T0 + 1000)

    def _rename_files_sanitized(self) -> set:
        ok, commits = self.iss._collect_git_history(self.root)
        self.assertTrue(ok)
        return set(commits[0]["files"])  # newest = the rename commit

    def _raw_rename_files(self) -> set:
        r = subprocess.run(
            ["git", "-C", str(self.root), "log", "-1", "--name-only", "--format="],
            capture_output=True, text=True, env=dict(os.environ),
        )
        return {f.strip() for f in r.stdout.split() if f.strip()}

    def test_sanitized_env_preserves_protected_global_config(self):
        # Scope decision: protected GLOBAL/SYSTEM config is NOT neutralized (so
        # operator-configured safe.directory keeps working). The sanitized env
        # must NOT force GIT_CONFIG_* selectors, and must pass an ambient
        # GIT_CONFIG_GLOBAL through unchanged.
        self._set_ambient(GIT_CONFIG_GLOBAL="/operator/gitconfig")
        env = self.iss._sanitized_git_env()
        self.assertEqual(env.get("GIT_CONFIG_GLOBAL"), "/operator/gitconfig",
                         "protected global config must pass through (safe.directory)")
        self.assertNotIn("GIT_CONFIG_NOSYSTEM", env,
                         "must not force-disable system config (would break safe.directory)")

    def test_rename_attribution_is_deterministic_via_pinned_flag(self):
        # The derivation pins `--no-renames`, so rename attribution is invariant
        # to the ambient diff.renames config (a command flag outranks all config
        # levels) — WITHOUT neutralizing that config.
        self._seed_rename()
        base = self._rename_files_sanitized()  # deterministic, rename-detection off
        self.assertEqual(base, {"a.txt", "b.txt"})
        for value in ("true", "false"):
            gc = Path(self._tmp.name) / f"gc-{value}"
            gc.write_text(f"[diff]\n\trenames = {value}\n", encoding="utf-8")
            saved = os.environ.get("GIT_CONFIG_GLOBAL")
            os.environ["GIT_CONFIG_GLOBAL"] = str(gc)
            try:
                self.assertEqual(
                    self._rename_files_sanitized(), base,
                    f"pinned --no-renames must be invariant to diff.renames={value}")
            finally:
                if saved is None:
                    os.environ.pop("GIT_CONFIG_GLOBAL", None)
                else:
                    os.environ["GIT_CONFIG_GLOBAL"] = saved
        # Guard (non-vacuous, robust to the CI's own gitconfig): with rename
        # detection FORCED on (`-M`), git attributes the rename to the new name
        # only — which DIFFERS from the pinned `--no-renames` result, proving the
        # flag is active, not a coincidence.
        detected = subprocess.run(
            ["git", "-C", str(self.root), "log", "-1", "--name-only", "-M", "--format="],
            capture_output=True, text=True,
        )
        detected_files = {f.strip() for f in detected.stdout.split() if f.strip()}
        self.assertEqual(detected_files, {"b.txt"})
        self.assertNotEqual(base, detected_files)


class GitSubprocessCensusTests(unittest.TestCase):
    """Round-4 re-review (5/6) P1: a STRUCTURAL guard that EVERY process-spawn in
    the store module routes through the sanitized `_run_git` (or the census
    helper). Strengthened (re-review (6) evidence note) to catch variable-built
    commands, tuples, aliased modules, and `Popen` — not just literal git lists."""

    # Only these functions may call a raw process runner directly.
    _ALLOWED = {"_run_git", "_git_strip_vars"}
    # Distinctive process-runner attribute/callable names.
    _RUNNER_ATTRS = {
        "run", "Popen", "call", "check_call", "check_output",
        "getoutput", "getstatusoutput", "isolated_run",
    }
    _RUNNER_BARE = {
        "Popen", "check_call", "check_output", "getoutput", "getstatusoutput",
    }

    def _enclosing_funcs(self, tree):
        # Map each Call node's lineno-range to the nearest enclosing FunctionDef.
        import ast
        parents = {}

        def walk(node, fn):
            for child in ast.iter_child_nodes(node):
                nxt = child.name if isinstance(child, ast.FunctionDef) else fn
                if isinstance(child, ast.Call):
                    parents[id(child)] = fn
                walk(child, nxt)
        walk(tree, None)
        return parents

    def test_every_process_spawn_routes_through_run_git(self):
        import ast
        src = STORE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        enclosing = self._enclosing_funcs(tree)

        def is_runner(func):
            # `<anything>.run/Popen/isolated_run/...` (catches subprocess.run,
            # subprocess_util.isolated_run, aliased `sp.run`, `_subprocess.run`).
            if isinstance(func, ast.Attribute) and func.attr in self._RUNNER_ATTRS:
                return True
            # bare `Popen(...)` / `check_output(...)` from `from subprocess import …`.
            if isinstance(func, ast.Name) and func.id in self._RUNNER_BARE:
                return True
            return False

        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and is_runner(node.func):
                fn = enclosing.get(id(node))
                if fn not in self._ALLOWED:
                    offenders.append((fn, node.lineno))
        self.assertEqual(
            offenders, [],
            f"process spawn(s) not routed through the sanitized wrapper "
            f"(allowed only in {sorted(self._ALLOWED)}): {offenders}")


if __name__ == "__main__":
    unittest.main()
