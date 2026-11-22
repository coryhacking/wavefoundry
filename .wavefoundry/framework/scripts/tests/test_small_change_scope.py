"""Small change evidence in real, isolated Git checkouts."""
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
import small_change_lane as lane
import record_paths
import vocabulary_profile as vocab


class SmallChangeScopeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.change = "12345-fix internal"
        roots = record_paths.load_record_roots(self.root)
        self.wave = roots.waves / "12346 demo" / vocab.RECORD_FILENAME
        self.wave.parent.mkdir(parents=True)
        # component-fixture: scope assessment reads the typed declaration while inspecting the Git checkout.
        self.wave.write_text("# Wave Record\nreview-evidence-source: events.jsonl\n\n## Changes\n")
        self.spec = self.wave.with_name(self.change + ".md")
        self.staged = roots.plans / self.spec.name
        self.staged.parent.mkdir(parents=True, exist_ok=True)
        self.staged.write_text("# Internal change\n\n## Scope\n\nSort internal samples.\n")
        self.src = self.root / "src"
        self.src.mkdir()
        self.first = self.src / "a.py"
        self.first.write_text("value = 1\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.commit()
        self.paths = ["src/a.py"]

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, check=True).stdout.strip().decode()

    def commit(self):
        self.git("-c", "user.email=fixture@localhost", "-c", "user.name=Fixture", "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")

    def capture(self):
        return lane.capture(self.root, self.wave, self.change, {
            "operator_direction": "Select small review for this admission.",
            "intended_diff": "Sort internal samples.",
            "paths": self.paths,
        }, [self.change])

    def admit(self):
        self.selection, evidence = self.capture()
        self.assertTrue(evidence["eligible"], evidence)
        self.staged.rename(self.spec)
        self.wave.write_text(lane.add_header(self.wave.read_text(), lane.selection_line(self.selection)))
        return self.observe()

    def observe(self):
        return lane.assess(self.root, self.wave, self.selection, [self.change])

    def test_three_declared_add_rename_delete_and_commit(self):
        self.paths += ["src/b.py", "src/c.py"]
        initial = self.admit()
        self.first.rename(self.src / "b.py")
        (self.src / "c.py").write_text("other\n")
        changed = self.observe()
        self.assertTrue(changed["eligible"], changed)
        self.assertEqual(changed["changed_paths"], self.paths)
        self.git("add", "src")
        self.commit()
        committed = self.observe()
        self.assertEqual(committed, changed)
        self.assertNotEqual(initial["content_digest"], changed["content_digest"])
        (self.src / "extra.py").write_text("extra\n")
        self.git("add", "src")
        self.commit()
        self.assertIn("src/extra.py", str(self.observe()["reasons"]))

    def test_admission_detects_dirt_staged_unstaged_and_untracked(self):
        self.first.write_text("changed")
        self.assertIn("clean product", str(self.capture()[1]["reasons"]))
        self.git("add", "src")
        self.assertIn("clean product", str(self.capture()[1]["reasons"]))
        self.git("restore", "--staged", "--worktree", "src")
        (self.root / "new.txt").write_text("untracked")
        self.assertIn("new.txt", str(self.capture()[1]["reasons"]))

    def test_ordinary_for_unverifiable_and_over_budget(self):
        self.paths += ["src/b.py", "src/c.py", "src/d.py"]
        self.assertIn("three", str(self.capture()[1]["reasons"]))
        self.paths = ["src/a.py"]
        self.admit()
        self.selection["baseline"] = "f" * 40
        self.assertFalse(self.observe()["eligible"])

    def test_untracked_file_cannot_hide_partial_staged_deletion(self):
        self.admit()
        self.git("rm", "--cached", "src/a.py")
        self.assertFalse(self.observe()["eligible"])

    def test_staged_bytes_and_file_identity_are_observed(self):
        self.admit()
        self.first.write_text("new\n")
        self.git("add", "src")
        self.first.write_text("different\n")
        self.assertFalse(self.observe()["eligible"])
        self.git("restore", "--staged", "--worktree", "src")
        approved = self.observe()
        self.assertTrue(approved["eligible"], approved)
        self.assertEqual(approved["content_digest"], self.observe()["content_digest"])
        replacement = self.src / "tmp"
        replacement.write_bytes(self.first.read_bytes())
        replacement.chmod(self.first.stat().st_mode)
        replacement.replace(self.first)
        replaced = self.observe()
        self.assertTrue(replaced["eligible"], replaced)
        self.assertNotEqual(approved["content_digest"], replaced["content_digest"])
        self.assertEqual(replaced["content_digest"], self.observe()["content_digest"])
        self.first.write_text("different contents")
        self.assertNotEqual(replaced["content_digest"], self.observe()["content_digest"])
        self.first.chmod(0o755)
        executable = self.observe()
        self.assertTrue(executable["eligible"], executable)
        self.first.chmod(0o644)
        self.assertNotEqual(executable["content_digest"], self.observe()["content_digest"])

    def test_file_identity_survives_device_renumbering_and_requires_evidence(self):
        fields = {"st_ino": 19, "st_birthtime_ns": 20, "st_ctime_ns": 42}
        first = lane._reviewed_file_id(SimpleNamespace(st_dev=1, **fields), "src/a.py")
        self.assertEqual(first, lane._reviewed_file_id(SimpleNamespace(st_dev=2, **fields), "src/a.py"))
        self.assertNotEqual(first, lane._reviewed_file_id(SimpleNamespace(**{**fields, "st_ino": 23}), "src/a.py"))
        for unavailable in ({"st_ino": 0, "st_ctime_ns": 42}, {"st_ino": 19}):
            with self.assertRaisesRegex(lane.Unverified, "No verifiable filesystem"):
                lane._reviewed_file_id(SimpleNamespace(**unavailable), "src/a.py")

    def test_hidden_index_and_ignored_addition(self):
        self.git("update-index", "--assume-unchanged", "src/a.py")
        self.first.write_text("masked")
        self.assertIn("index flags", str(self.capture()[1]["reasons"]))
        self.git("update-index", "--no-assume-unchanged", "src/a.py")
        self.git("restore", "src")
        (self.root / ".gitignore").write_text("src/b.py\n")
        self.git("add", ".gitignore")
        self.commit()
        self.paths = ["src/b.py"]
        self.assertIn("ignores", str(self.capture()[1]["reasons"]))

    def test_requested_and_mandatory_specialists_at_admission(self):
        self.wave.write_text(self.wave.read_text() + "\n## Participants\n\n- Requested review lanes: security-reviewer\n")
        self.assertIn("security-reviewer", str(self.capture()[1]["reasons"]))
        self.git("restore", ".")
        cfg = self.root / "docs/workflow-config.json"
        cfg.write_text('{"required_review_lanes": ["qa-reviewer"]}')
        self.assertIn("qa-reviewer", str(self.capture()[1]["reasons"]))

    def test_protected_scope_and_semantic_effect(self):
        for path in ["src/hooks/worker.py", "security/policy.py", "src/PublicContract.swift",
                     "src/new_release.py", "fixtures/openapi.json", "../out.py", "src/*"]:
            with self.subTest(path=path):
                self.paths = [path]
                self.assertFalse(self.capture()[1]["eligible"])
        self.paths = ["src/a.py"]
        self.staged.write_text("## Requirements\nReturn a new field in the public response.\n")
        self.assertIn("described effect", str(self.capture()[1]["reasons"]))

    @unittest.skipIf(os.name == "nt", "POSIX symlink, FIFO and hardlink checks")
    def test_unsupported_file_types_and_aliases(self):
        self.admit()
        fifo = self.src / "unexpected.pipe"
        os.mkfifo(fifo)
        self.assertIn("Unsupported checkout file type", str(self.observe()["reasons"]))
        fifo.unlink()
        self.first.unlink()
        self.first.symlink_to(self.spec)
        self.assertFalse(self.observe()["eligible"])
        self.first.unlink()
        os.mkfifo(self.first)
        self.assertFalse(self.observe()["eligible"])
        self.first.unlink()
        os.link(self.spec, self.first)
        self.assertFalse(self.observe()["eligible"])

    def test_incomplete_reads_and_unrelated_lifecycle_files(self):
        self.admit()
        with patch.object(lane, "_scope", side_effect=[([], "one"), ([], "two")]):
            self.assertIn("during verification", str(self.observe()["reasons"]))
        (self.wave.parent / "notes.md").write_text("new")
        self.assertIn("notes.md", str(self.observe()["reasons"]))

    def test_pause_handoff_requires_the_exact_owned_update(self):
        from wf_server.edit_gate_handlers import _update_handoff_wave_ref
        self.admit()
        handoff = self.root / "docs/agents/session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(_update_handoff_wave_ref("", self.wave.parent.name))
        self.assertTrue(self.observe()["eligible"], self.observe())
        handoff.write_text(handoff.read_text() + "Unrelated change\n")
        self.assertFalse(self.observe()["eligible"])

    def test_declined_admission_preserves_legacy_and_disabled_policy(self):
        from server_tools_support import load_server
        from lifecycle_gate_support import selected_small_change
        server = load_server()
        original_text = self.wave.read_text().replace("## Changes", vocab.MEMBER_HEADING)
        self.staged.write_text(f"{vocab.MEMBER_ID_LABEL}: `{self.change}`\n")
        request = {"operator_direction": "Use small review here.", "intended_diff": "Sort samples.", "paths": self.paths}
        config = self.root / "docs/workflow-config.json"
        config.write_text('{"wave_review":{"enabled":false,"delivery_mode":"disabled"}}')
        for legacy in (False, True):
            # negative-fixture: removing the declaration exercises admission of a legacy prose wave.
            self.wave.write_text(original_text.replace("review-evidence-source: events.jsonl", "") if legacy else original_text)
            if legacy:
                self.spec.rename(self.staged)
            result = server.wf_add_change_response(self.root, self.wave.parent.name, self.change,
                                                   mode="create", small_change=request)
            self.assertEqual(result["status"], "ok", result)
            self.assertFalse(result["data"]["small_change"]["eligible"])
            self.assertFalse(selected_small_change(self.wave.read_text()))
            self.assertIn(lane.DECLINED, self.wave.read_text())
            retry = server.wf_add_change_response(self.root, self.wave.parent.name, self.change,
                                                  mode="create", small_change=request)
            self.assertEqual(retry["data"]["small_change"], result["data"]["small_change"])

    def test_selection_marker_only_in_wave_header_and_preserved_for_retries(self):
        selection, _ = self.capture()
        line = lane.selection_line(selection)
        header = lane.add_header("# Wave\n\n## Objective\n", line)
        self.assertEqual(lane.read_selection(header), selection)
        self.assertIsNone(lane.read_selection("# Wave\n\n## Objective\n" + line))
        self.assertIn("ambiguous", str(lane.read_selection(lane.add_header(header, line))))
        self.assertIn("malformed", str(lane.read_selection("# Wave\nsmall-change-selection: {}\n")))
