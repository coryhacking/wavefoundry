"""Tests for commit->wave reverse provenance (wave 1sufq / change 1sufp).

Hermetic: each test builds its own throwaway git repo + wave records, so nothing
depends on this repo's real history. Verifies both resolution paths, Decision Log
surfacing, honest absence/conflict, the bounded blame + path-traversal guard, the
uncommitted-line filter, and that the resolver never mutates git or wave state.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commit_provenance as cp  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
    )
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, env=env, check=True,
    ).stdout.strip()


class _RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")
        _git(self.root, "config", "commit.gpgsign", "false")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def _commit(self, message: str) -> str:
        _git(self.root, "add", "-A")
        _git(self.root, "-c", "user.name=t", "-c", "user.email=t@example.com",
             "commit", "-q", "-m", message)
        return _git(self.root, "rev-parse", "HEAD")

    def _wave(self, wave_id: str, slug: str, decisions: list[str]) -> None:
        rows = "\n".join(f"| 2026-01-0{i+1} | {d} | reason | alt |"
                         for i, d in enumerate(decisions))
        change = (
            f"# {slug}\n\nChange ID: `{wave_id}a-feat {slug}`\n\n"
            "## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| ---- | -------- | ------ | ------------ |\n"
            f"{rows}\n"
        )
        self._write(f"docs/waves/{wave_id} {slug}/{wave_id}a-feat {slug}.md", change)
        self._write(f"docs/waves/{wave_id} {slug}/wave.md",
                    f"# Wave Record\n\nwave-id: `{wave_id} {slug}`\n")


class ResolutionTests(_RepoCase):
    def test_message_path_resolves_landed_wave(self):
        self._write("f.txt", "x\n")
        sha = self._commit("Land wave 1abcd: a feature")
        v = cp.resolve_commit_to_waves(self.root, sha)
        self.assertEqual(v["waves"], ["1abcd"])
        self.assertEqual(v["method"], "message")
        self.assertTrue(v["resolved"])

    def test_multi_wave_message(self):
        self._write("f.txt", "x\n")
        sha = self._commit("Land waves 1abcd, 1abce and 1abcf for 1.2.0")
        self.assertEqual(
            cp.resolve_via_message(self.root, sha), ["1abcd", "1abce", "1abcf"])

    def test_version_token_is_not_a_wave_id(self):
        self._write("f.txt", "x\n")
        sha = self._commit("Land wave 1abcd for 1.13.0")
        self.assertEqual(cp.resolve_via_message(self.root, sha), ["1abcd"])

    def test_evidence_path_resolves_non_conventional_commit(self):
        self._write("f.txt", "x\n")
        sha = self._commit("fix: something unconventional")
        # an explicit typed landing association (generic SHA prose is not authority)
        self._write("docs/waves/1zzzz slug/wave.md",
                    f"# Wave\n\nlanding-commit: {sha[:7]}\n")
        self._commit("Land wave 1zzzz: record the sha")
        v = cp.resolve_commit_to_waves(self.root, sha)
        self.assertIn("1zzzz", v["via_evidence"])
        self.assertEqual(v["method"], "evidence")

    def test_conflict_reports_both_never_reconciles(self):
        self._write("f.txt", "x\n")
        sha = self._commit("Land wave 1aaaa: msg says aaaa")
        self._write("docs/waves/1bbbb slug/wave.md",
                    f"# Wave\n\nlanding-commit: {sha[:7]}\n")
        self._commit("Land wave 1bbbb: evidence says bbbb")
        v = cp.resolve_commit_to_waves(self.root, sha)
        self.assertTrue(v["conflict"])
        self.assertEqual(set(v["waves"]), {"1aaaa", "1bbbb"})

    def test_honest_absence_never_fabricates(self):
        self._write("f.txt", "x\n")
        sha = self._commit("chore: no wave here")
        v = cp.resolve_commit_to_waves(self.root, sha)
        self.assertFalse(v["resolved"])
        self.assertEqual(v["method"], "none")
        self.assertEqual(v["waves"], [])

    def test_generic_sha_mention_is_not_authority(self):
        self._write("f.txt", "x\n")
        sha = self._commit("chore: no wave here")
        self._write("docs/waves/1zzzz slug/wave.md",
                    f"# Wave\n\nUnrelated fixture commit `{sha[:7]}`\n")
        self.assertEqual(cp.resolve_via_evidence(self.root, sha), [])

    def test_landing_marker_inside_code_fence_is_not_authority(self):
        self._write("f.txt", "x\n")
        sha = self._commit("chore: no wave here")
        self._write(
            "docs/waves/1zzzz slug/wave.md",
            f"# Wave\n\n```text\nlanding-commit: {sha}\n```\n",
        )
        self.assertEqual(cp.resolve_via_evidence(self.root, sha), [])

    def test_nonexistent_sha_cannot_resolve_from_prose(self):
        sha = "deadbee"
        self._write("docs/waves/1zzzz slug/wave.md",
                    f"# Wave\n\nlanding-commit: {sha}\n")
        self.assertFalse(cp.resolve_commit_to_waves(self.root, sha)["resolved"])

    def test_subject_grammar_rejects_revert_and_stops_before_description(self):
        self._write("f.txt", "x\n")
        reverted = self._commit('Revert "Land wave 1aaaa: broken"')
        self.assertEqual(cp.resolve_via_message(self.root, reverted), [])
        self._write("g.txt", "y\n")
        descriptive = self._commit("Land wave 1aaaa for change 1bbbbb")
        self.assertEqual(cp.resolve_via_message(self.root, descriptive), ["1aaaa"])

    def test_invalid_sha_fails_closed(self):
        v = cp.resolve_commit_to_waves(self.root, "not-a-sha!!")
        self.assertFalse(v["resolved"])
        self.assertEqual(v["method"], "invalid_sha")
        self.assertFalse(cp.is_valid_sha("zzz"))
        self.assertTrue(cp.is_valid_sha("abc1234"))


class ReasoningSurfacingTests(_RepoCase):
    def test_provenance_surfaces_decision_log(self):
        self._wave("1abcd", "myslug", ["chose X over Y", "deferred Z"])
        sha = self._commit("Land wave 1abcd: surfaced")
        v = cp.provenance_for_sha(self.root, sha)
        with_content = [r for r in v["provenance"] if r.get("decisions")]
        self.assertTrue(with_content, "a change doc's Decision Log must be surfaced")
        row = with_content[0]
        self.assertIn("chose X over Y", "\n".join(row["decisions"]))
        self.assertIn("excerpt", row)  # content-bearing → credited by the metric census


class BlameTests(_RepoCase):
    def test_blame_line_to_commit(self):
        self._write("src.txt", "line1\nline2\n")
        sha = self._commit("Land wave 1abcd: seed")
        shas, err = cp.blame_line_commits(self.root, "src.txt", 1, 1)
        self.assertIsNone(err)
        self.assertIn(sha, shas)

    def test_uncommitted_line_sentinel_filtered(self):
        self._write("src.txt", "committed\n")
        self._commit("Land wave 1abcd: seed")
        (self.root / "src.txt").write_text("committed\nuncommitted\n", encoding="utf-8")
        shas, err = cp.blame_line_commits(self.root, "src.txt", 2, 2)
        self.assertIsNone(err)
        self.assertNotIn("0" * 40, shas)  # the not-yet-committed sentinel is dropped

    def test_mixed_range_reports_partial_coverage(self):
        self._wave("1abcd", "myslug", ["keep coverage"])
        self._write("src.txt", "committed\nsecond\n")
        self._commit("Land wave 1abcd: seed")
        self._write("src.txt", "committed\nmodified\n")
        v = cp.provenance_for_line(self.root, "src.txt", 1, 2)
        self.assertTrue(v["partial"])
        self.assertGreater(v["coverage"]["uncommitted_lines"], 0)

    def test_path_traversal_guard(self):
        shas, err = cp.blame_line_commits(self.root, "../../../etc/passwd", 1, 1)
        self.assertEqual(shas, [])
        self.assertEqual(err, "path outside repository")

    def test_invalid_range(self):
        self._write("src.txt", "a\n")
        self._commit("Land wave 1abcd: seed")
        _, err = cp.blame_line_commits(self.root, "src.txt", 5, 1)
        self.assertEqual(err, "invalid line range")


class ReadOnlyTests(_RepoCase):
    def test_resolver_never_mutates_repo(self):
        self._write("f.txt", "x\n")
        sha = self._commit("Land wave 1abcd: x")
        head_before = _git(self.root, "rev-parse", "HEAD")
        status_before = _git(self.root, "status", "--porcelain")
        cp.provenance_for_sha(self.root, sha)
        cp.blame_line_commits(self.root, "f.txt", 1, 1)
        self.assertEqual(_git(self.root, "rev-parse", "HEAD"), head_before)
        self.assertEqual(_git(self.root, "status", "--porcelain"), status_before)


class ResolutionSignalTests(_RepoCase):
    """AC-7: the tool response stamps a per-call resolution activity signal."""

    def _resolution(self, **kwargs):
        import server_impl  # heavy import; only this class needs it
        resp = server_impl.code_commit_provenance_response(self.root, **kwargs)
        return resp["data"].get("resolution")

    def test_resolved_signal(self):
        self._write("f.txt", "x\n")
        sha = self._commit("Land wave 1abcd: x")
        self.assertEqual(self._resolution(commit=sha), "resolved")

    def test_honest_absence_signal(self):
        self._write("f.txt", "x\n")
        self._commit("chore: no wave")
        # a valid hex sha that resolves to no wave
        self.assertEqual(self._resolution(commit="0" * 40), "honest_absence")

    def test_conflict_signal(self):
        self._write("f.txt", "x\n")
        sha = self._commit("Land wave 1aaaa: msg")
        self._write("docs/waves/1bbbb slug/wave.md",
                    f"# Wave\n\nlanding-commit: {sha[:7]}\n")
        self._commit("Land wave 1bbbb: evidence")
        self.assertEqual(self._resolution(commit=sha), "conflict")

    def test_invalid_and_dual_inputs_are_errors(self):
        import server_impl
        invalid = server_impl.code_commit_provenance_response(
            self.root, commit="not-a-sha")
        self.assertEqual(invalid["status"], "error")
        dual = server_impl.code_commit_provenance_response(
            self.root, commit="deadbee", path="f.txt")
        self.assertEqual(dual["status"], "error")
        missing_range = server_impl.code_commit_provenance_response(
            self.root, path="f.txt")
        self.assertEqual(missing_range["status"], "error")
        malformed_range = server_impl.code_commit_provenance_response(
            self.root, path="f.txt", line_start="not-a-line")
        self.assertEqual(malformed_range["status"], "error")

    def test_conflict_takes_precedence_while_partial_remains_diagnostic(self):
        import server_impl
        fake = SimpleNamespace(
            provenance_for_line=lambda *_args: {
                "resolved": True,
                "waves": ["1aaaa", "1bbbb"],
                "provenance": [],
                "partial": True,
                "conflict": True,
            }
        )
        with patch.object(server_impl, "_load_script", return_value=fake):
            response = server_impl.code_commit_provenance_response(
                self.root, path="f.txt", line_start=1, line_end=2
            )
        self.assertEqual(response["data"]["resolution"], "conflict")
        self.assertEqual(
            {item["code"] for item in response["diagnostics"]},
            {"partial_provenance", "provenance_conflict"},
        )


if __name__ == "__main__":
    unittest.main()
