"""Tests for the agent memory layer (wave 1ro44 / 1p8gy): record parsing,
writing, reconciliation, kind-aware decay, and the memory_* MCP tools.

Fixtures cover all eight memory kinds, supersession history preservation,
the fragile_file needs-reverification amendment, decay via the 1ro43
freshness primitive (synthetic git history), and graceful absence of the
index/graph layers at every surfacing point.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_server():
    if "server_impl" in sys.modules:
        return sys.modules["server_impl"]
    return _load("server_impl")


def load_independent_server():
    """Load a SEPARATE ``server_impl`` module instance with its OWN module
    globals — crucially its own ``_MEMORY_RECORDS_CACHE`` and ``_script_cache``
    (hence its own ``index_state_store`` instance). This models a SECOND MCP
    process that shares only the on-disk ``memory-state.sqlite`` with the first,
    so a genuine cross-process cache-coherence claim can be made (not the same
    module's cache cleared to fake a second process)."""
    spec = importlib.util.spec_from_file_location(
        "server_impl_proc2", SCRIPTS_ROOT / "server_impl.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _MemoryCase(unittest.TestCase):
    def setUp(self):
        self.mem = _load("memory_records")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        (self.root / "docs" / "agents").mkdir(parents=True)
        self.index_dir = self.root / ".wavefoundry" / "index"

    def _add(self, memory_id: str, kind: str, *, status="active", confidence=0.8,
             targets=("src/a.py",), created="2026-07-13", supersedes="") -> Path:
        content = self.mem.render_memory_record(
            memory_id=memory_id, kind=kind, summary=f"Lesson from {memory_id}.",
            evidence=["`1abcd-bug some-change` — observed"], targets=list(targets),
            title=f"Lesson {memory_id}", confidence=confidence, status=status,
            supersedes=supersedes, date=created,
        )
        return self.mem.write_memory_record(self.root, content, memory_id)


class RecordRoundTripTests(_MemoryCase):
    def test_render_parse_round_trip_all_kinds(self):
        for kind in self.mem.MEMORY_KINDS:
            mid = f"mem-{kind.replace('_', '-')}"
            path = self._add(mid, kind)
            record = self.mem.parse_memory_record(path)
            self.assertIsNotNone(record, kind)
            self.assertEqual(record["memory_id"], mid)
            self.assertEqual(record["kind"], kind)
            self.assertEqual(record["status"], "active")
            self.assertEqual(record["confidence"], 0.8)
            self.assertEqual(record["target_refs"], ["src/a.py"])
            self.assertTrue(record["evidence_refs"])
            self.assertTrue(record["summary"])

    def test_load_filters_by_status_and_skips_readme_and_garbage(self):
        self._add("mem-a", "decision", status="active")
        self._add("mem-b", "decision", status="stale")
        mem_dir = self.root / self.mem.MEMORY_DIR
        (mem_dir / "README.md").write_text("# Schema doc\n", encoding="utf-8")
        (mem_dir / "not-a-record.md").write_text("random prose\n", encoding="utf-8")
        surfaced = self.mem.load_memory_records(
            self.root, statuses=self.mem.DEFAULT_SURFACED_STATUSES)
        self.assertEqual([r["memory_id"] for r in surfaced], ["mem-a"])
        everything = self.mem.load_memory_records(self.root)
        self.assertEqual({r["memory_id"] for r in everything}, {"mem-a", "mem-b"})

    def test_duplicate_write_refuses(self):
        self._add("mem-a", "decision")
        with self.assertRaises(FileExistsError):
            self._add("mem-a", "decision")


class ReconcileTests(_MemoryCase):
    def test_supersession_preserves_history(self):
        self._add("mem-old", "decision")
        self.mem.reconcile_memory_record(
            self.root, "mem-old", "superseded", superseded_by="mem-new")
        record = self.mem.parse_memory_record(self.root / self.mem.MEMORY_DIR / "mem-old.md")
        self.assertEqual(record["status"], "superseded")
        self.assertEqual(record["superseded_by"], "mem-new")
        self.assertTrue(record["summary"], "content must survive reconciliation")

    def test_superseded_requires_link_and_unknown_status_rejected(self):
        self._add("mem-a", "decision")
        with self.assertRaises(ValueError):
            self.mem.reconcile_memory_record(self.root, "mem-a", "superseded")
        with self.assertRaises(ValueError):
            self.mem.reconcile_memory_record(self.root, "mem-a", "obliterated")
        with self.assertRaises(FileNotFoundError):
            self.mem.reconcile_memory_record(self.root, "mem-missing", "stale")


class DecayTests(_MemoryCase):
    """1p8gy Req 13 / AC-13 via the landed 1ro43 freshness primitive."""

    def _seed_churn(self, commits: int):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "t"], check=True)
        iss = _load("index_state_store")
        (self.root / "src").mkdir(exist_ok=True)
        for i in range(commits):
            (self.root / "src" / "a.py").write_text(f"x = {i}\n")
            subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(self.root), "commit", "-qm", f"c{i}"], check=True)
        iss.update_freshness_from_build(self.root, self.index_dir, ["src/a.py"])

    def test_failed_attempt_decays_with_target_churn(self):
        self._seed_churn(10)
        path = self._add("mem-fail", "failed_attempt", created="2020-01-01")
        record = self.mem.parse_memory_record(path)
        decay = self.mem.apply_decay(record, index_dir=self.index_dir)
        self.assertLess(decay["effective_confidence"], 0.8)
        self.assertIn("target_churn", decay["decay_basis"])
        # Enough churn pushes it below the briefing floor.
        self.assertAlmostEqual(decay["effective_confidence"], 0.8 / 2.0, places=2)

    def test_operator_preference_never_decays_on_churn(self):
        self._seed_churn(10)
        record = self.mem.parse_memory_record(
            self._add("mem-pref", "operator_preference", created="2020-01-01"))
        decay = self.mem.apply_decay(record, index_dir=self.index_dir)
        self.assertEqual(decay["effective_confidence"], 0.8)
        self.assertEqual(decay["decay_basis"], "none")
        self.assertTrue(decay["briefing_included"])

    def test_fragile_file_flags_instead_of_attenuating(self):
        self._seed_churn(10)
        record = self.mem.parse_memory_record(
            self._add("mem-fragile", "fragile_file", created="2020-01-01"))
        decay = self.mem.apply_decay(record, index_dir=self.index_dir)
        self.assertEqual(decay["effective_confidence"], 0.8)  # never attenuated
        self.assertTrue(decay["needs_reverification"])
        self.assertTrue(decay["briefing_included"])  # never drops from churn

    def test_environment_gotcha_decays_on_elapsed_time(self):
        record = self.mem.parse_memory_record(
            self._add("mem-env", "environment_gotcha", created="2020-01-01"))
        decay = self.mem.apply_decay(record, index_dir=None)
        self.assertLess(decay["effective_confidence"], 0.8)
        self.assertIn("age_days", decay["decay_basis"])

    def test_absent_store_means_no_churn_decay(self):
        record = self.mem.parse_memory_record(
            self._add("mem-fail", "failed_attempt", created="2020-01-01"))
        decay = self.mem.apply_decay(record, index_dir=self.index_dir)  # no store built
        self.assertEqual(decay["effective_confidence"], 0.8)


class MemoryToolTests(_MemoryCase):
    def setUp(self):
        super().setUp()
        self.srv = load_server()
        # The tool layer needs docs/ to exist (record dir is created on write).

    def test_add_search_brief_reconcile_flow(self):
        resp = self.srv.memory_add_response(
            self.root, "fragile_file",
            "Edits to the chunker regress silently; run the multi-lang pack.",
            ["`1abcd-bug chunker-regression` — the regression wave"],
            ["src/chunker.py"], title="Chunker is fragile", confidence=0.9,
        )
        self.assertEqual(resp["status"], "ok", resp)
        self.assertTrue(resp["data"]["written"])
        mid = resp["data"]["record"]["memory_id"]
        self.assertTrue(mid.startswith("mem-"))

        search = self.srv.memory_search_response(self.root, target="src/chunker.py")
        self.assertEqual(search["data"]["count"], 1)
        self.assertEqual(search["data"]["records"][0]["memory_id"], mid)

        brief = self.srv.memory_brief_response(
            self.root, context="pre_implementation", targets=["src/chunker.py"])
        self.assertEqual(brief["data"]["count"], 1)
        self.assertEqual(brief["data"]["advisories"][0]["kind"], "fragile_file")

        rec = self.srv.memory_reconcile_response(self.root, mid, "rejected")
        self.assertTrue(rec["data"]["updated"])
        gone = self.srv.memory_search_response(self.root, target="src/chunker.py")
        self.assertEqual(gone["data"]["count"], 0)
        history = self.srv.memory_search_response(
            self.root, target="src/chunker.py", include_history=True)
        self.assertEqual(history["data"]["count"], 1)

    def test_add_refuses_forbidden_and_invalid_content(self):
        resp = self.srv.memory_add_response(
            self.root, "environment_gotcha", "Set api_key: sk-live-123 in the env.",
            ["`x`"], ["src/a.py"])
        self.assertEqual(resp["status"], "error")
        self.assertFalse((self.root / self.mem.MEMORY_DIR).exists(),
                         "forbidden content must be refused BEFORE write")
        resp = self.srv.memory_add_response(self.root, "vibes", "s", ["`e`"], ["t"])
        self.assertEqual(resp["status"], "error")
        resp = self.srv.memory_add_response(self.root, "decision", "s", [], ["t"])
        self.assertEqual(resp["status"], "error")

    def test_add_with_supersedes_marks_old_record(self):
        self.srv.memory_add_response(
            self.root, "decision", "Old direction.", ["`1old`"], ["src/a.py"],
            memory_id="mem-old-direction")
        resp = self.srv.memory_add_response(
            self.root, "decision", "New direction.", ["`1new`"], ["src/a.py"],
            memory_id="mem-new-direction", supersedes="mem-old-direction")
        self.assertEqual(resp["status"], "ok")
        old = self.mem.parse_memory_record(
            self.root / self.mem.MEMORY_DIR / "mem-old-direction.md")
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(old["superseded_by"], "mem-new-direction")

    def test_search_semantic_assist_degrades_silently(self):
        self.srv.memory_add_response(
            self.root, "decision", "Retrieval uses annotation-first decay.",
            ["`1ro43`"], ["src/a.py"], memory_id="mem-decay-direction")
        broken_index = MagicMock()
        broken_index.search_docs.side_effect = RuntimeError("no index")
        resp = self.srv.memory_search_response(
            self.root, query="annotation decay", index=broken_index)
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["count"], 1)  # text containment served
        self.assertFalse(resp["data"]["semantic_assist"])

    def test_brief_cap_and_invalid_context(self):
        for i in range(8):
            self.srv.memory_add_response(
                self.root, "decision", f"Decision {i}.", [f"`1d{i}`"], ["src/a.py"],
                memory_id=f"mem-decision-{i}")
        brief = self.srv.memory_brief_response(self.root, limit=99)
        self.assertLessEqual(brief["data"]["count"], self.srv.MEMORY_BRIEF_CAP)
        self.assertEqual(brief["data"]["total_surfaceable"], 8)
        bad = self.srv.memory_brief_response(self.root, context="vibes")
        self.assertEqual(bad["status"], "error")

    def test_community_scoped_records_group_separately(self):
        self.srv.memory_add_response(
            self.root, "fragile_file", "This whole area is fragile.",
            ["`1abcd`"], ["community:hub:src/core.py::main"],
            memory_id="mem-fragile-area")
        brief = self.srv.memory_brief_response(self.root)
        self.assertEqual(brief["data"]["advisories"], [])
        self.assertEqual(
            brief["data"]["community_scoped"][0]["memory_id"], "mem-fragile-area")

class ActionTimeAdvisoryTests(_MemoryCase):
    """1p8gy AC-5/AC-6: capped memory advisories on hot read tools and
    lifecycle surfaces, with graceful absence everywhere."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "src" / "core.py").write_text("def main():\n    return 1\n")

    def test_code_read_carries_capped_matching_advisories(self):
        for i in range(5):
            self.srv.memory_add_response(
                self.root, "fragile_file", f"Lesson {i} about core.",
                [f"`1c{i}`"], ["src/core.py"], memory_id=f"mem-core-{i}",
                confidence=0.5 + i * 0.1)
        resp = self.srv.code_read_response(self.root, "src/core.py")
        advisories = resp["data"].get("memory_advisories")
        self.assertIsNotNone(advisories)
        self.assertEqual(len(advisories), self.srv.MEMORY_ADVISORY_CAP)
        # Highest confidence first (no churn data → flat decay).
        self.assertEqual(advisories[0]["memory_id"], "mem-core-4")

    def test_code_read_without_matches_is_unchanged(self):
        self.srv.memory_add_response(
            self.root, "decision", "Unrelated lesson.", ["`1x`"], ["src/other.py"],
            memory_id="mem-unrelated")
        resp = self.srv.code_read_response(self.root, "src/core.py")
        self.assertNotIn("memory_advisories", resp["data"])

    def test_code_read_graceful_when_memory_dir_absent(self):
        resp = self.srv.code_read_response(self.root, "src/core.py")
        self.assertEqual(resp["status"], "ok")
        self.assertNotIn("memory_advisories", resp["data"])

    def test_wave_advisories_match_change_ids_and_fragile_flags(self):
        self.srv.memory_add_response(
            self.root, "review_finding", "AC evidence was overstated in 1abcd.",
            ["`1abcd-enh some-change` — delivery review round 2"], ["src/core.py"],
            memory_id="mem-review-lesson")
        self.srv.memory_add_response(
            self.root, "operator_preference", "Never batch AC updates.",
            ["`1zzzz-enh other`"], ["src/other.py"], memory_id="mem-unrelated-pref")
        views = self.srv._memory_advisories_for_wave(
            self.root, {"wave_id": "1abce some-wave",
                        "changes": [{"id": "1abcd-enh some-change"}]})
        ids = [v["memory_id"] for v in views]
        self.assertIn("mem-review-lesson", ids)
        self.assertNotIn("mem-unrelated-pref", ids)

    def test_wave_advisories_graceful_on_empty_and_bad_input(self):
        self.assertEqual(self.srv._memory_advisories_for_wave(self.root, {}), [])
        self.assertEqual(self.srv._memory_advisories_for_wave(self.root, {"wave_id": None}), [])


class LifecyclePromptTextTests(unittest.TestCase):
    """1p8gy AC-7/AC-9: the pause/review/close/implement prompt surfaces and
    the canonical seed carry the memory capture/distillation steps."""

    REPO = Path(__file__).resolve().parents[4]

    def _text(self, rel: str) -> str:
        path = self.REPO / rel
        if not path.exists():
            self.skipTest(f"surface not present: {rel}")
        return path.read_text(encoding="utf-8")

    def test_close_prompt_requires_the_agent_validation_checkpoint(self):
        text = self._text("docs/prompts/close-wave.prompt.md")
        self.assertIn("Agent Memory Validation Checkpoint", text)
        for word in ("promote", "reject", "retain", "rewrite", "memory_validate"):
            self.assertIn(word, text)

    def test_review_and_pause_prompts_propose_candidates(self):
        review = self._text("docs/prompts/review-wave.prompt.md")
        self.assertIn("memory_add(status='candidate'", review)
        pause = self._text("docs/prompts/pause-wave.prompt.md")
        self.assertIn("memory_add(status='candidate'", pause)

    def test_implement_prompt_requires_the_briefing(self):
        text = self._text("docs/prompts/implement-wave.prompt.md")
        self.assertIn("memory_brief(context='pre_implementation'", text)
        self.assertIn("needs_reverification", text)

    def test_seed_100_carries_the_canonical_directives(self):
        text = self._text(".wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md")
        self.assertIn("Memory validation checkpoint", text)
        self.assertIn("memory_validate", text)
        self.assertIn("memory_brief(context='pre_implementation'", text)
        self.assertIn("- **pause-wave**:", text)


class MemoryIdTraversalTests(_MemoryCase):
    """Delivery-review security finding (2026-07-13): caller-supplied memory
    ids are path components — traversal and grammar violations must be
    refused at every filesystem access, for add AND reconcile, with the
    escape target provably untouched."""

    EVIL_IDS = (
        "../escape", "../../docs/ARCHITECTURE", "..", "a/../b", "sub/dir",
        "..\\escape", "MEM-UPPER", "mem_underscore", "mem id", ".hidden",
        "-leading-dash", "", "x" * 65,
    )

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        # A tempting escape target with a Status line reconcile could flip.
        self.target = self.root / "docs" / "target.md"
        self.target.write_text(
            "# Target\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-07-13\n",
            encoding="utf-8",
        )
        self.target_bytes = self.target.read_bytes()

    def _tree_snapshot(self):
        return {p for p in self.root.rglob("*") if p.is_file()}

    def test_validate_memory_id_grammar(self):
        for evil in self.EVIL_IDS:
            with self.assertRaises(ValueError, msg=repr(evil)):
                self.mem.validate_memory_id(evil)
        self.assertEqual(self.mem.validate_memory_id("mem-good-1"), "mem-good-1")
        self.assertEqual(self.mem.validate_memory_id("  mem-trimmed  "), "mem-trimmed")

    def test_write_and_reconcile_refuse_traversal_ids(self):
        for evil in self.EVIL_IDS:
            with self.assertRaises(ValueError, msg=repr(evil)):
                self.mem.write_memory_record(self.root, "content", evil)
            with self.assertRaises(ValueError, msg=repr(evil)):
                self.mem.reconcile_memory_record(self.root, evil, "stale")

    def test_memory_add_refuses_traversal_without_touching_disk(self):
        before = self._tree_snapshot()
        for evil in ("../target", "../../etc/evil", "a/../b"):
            resp = self.srv.memory_add_response(
                self.root, "decision", "Escape attempt.", ["`1x`"], ["src/a.py"],
                memory_id=evil)
            self.assertEqual(resp["status"], "error", evil)
            self.assertIn("invalid memory id", str(resp), evil)
        self.assertEqual(self._tree_snapshot(), before,
                         "a refused add must create no file anywhere")

    def test_memory_add_refuses_traversal_supersedes(self):
        before = self._tree_snapshot()
        resp = self.srv.memory_add_response(
            self.root, "decision", "Escape via supersedes.", ["`1x`"], ["src/a.py"],
            memory_id="mem-legit", supersedes="../target")
        self.assertEqual(resp["status"], "error")
        self.assertEqual(self._tree_snapshot(), before)
        self.assertEqual(self.target.read_bytes(), self.target_bytes)

    def test_memory_reconcile_refuses_traversal_and_leaves_target_intact(self):
        # "../target" resolves to an EXISTING file with a Status line — the
        # exact escalation the finding described (flipping a doc's status).
        resp = self.srv.memory_reconcile_response(self.root, "../target", "stale")
        self.assertEqual(resp["status"], "error")
        self.assertFalse(resp["data"]["updated"])
        self.assertEqual(self.target.read_bytes(), self.target_bytes,
                         "the escape target must be byte-identical")
        # superseded_by is also grammar-validated (it is written into content
        # and becomes a future path component).
        self._add("mem-real", "decision")
        resp = self.srv.memory_reconcile_response(
            self.root, "mem-real", "superseded", superseded_by="../target")
        self.assertEqual(resp["status"], "error")
        record = self.mem.parse_memory_record(
            self.root / self.mem.MEMORY_DIR / "mem-real.md")
        self.assertEqual(record["status"], "active", "refusal must not half-apply")

    def test_valid_ids_still_work_end_to_end(self):
        resp = self.srv.memory_add_response(
            self.root, "decision", "Sanity.", ["`1x`"], ["src/a.py"],
            memory_id="mem-sanity-check")
        self.assertEqual(resp["status"], "ok")
        resp = self.srv.memory_reconcile_response(
            self.root, "mem-sanity-check", "rejected")
        self.assertTrue(resp["data"]["updated"])


class SymlinkContainmentTests(_MemoryCase):
    """Delivery-review P0: a symlinked memory root (or ancestor) that
    redirects outside the repo must be rejected — containment proves the
    root's canonical location, not just the record's parent."""

    def test_symlinked_memory_root_is_rejected(self):
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        mem_parent = self.root / "docs" / "agents"
        mem_parent.mkdir(parents=True, exist_ok=True)
        # docs/agents/memory -> ../../outside (escapes the repo).
        (mem_parent / "memory").symlink_to(outside)
        before = {p for p in outside.rglob("*")}
        with self.assertRaises(ValueError):
            self.mem.write_memory_record(self.root, "content", "mem-escape")
        with self.assertRaises(ValueError):
            self.mem.reconcile_memory_record(self.root, "mem-escape", "stale")
        self.assertEqual({p for p in outside.rglob("*")}, before,
                         "no file may be written through the symlinked root")

    def test_normal_in_repo_root_control_still_works(self):
        path = self.mem.write_memory_record(
            self.root, "# ok\nStatus: active\n", "mem-control")
        self.assertTrue(path.is_file())
        self.assertTrue(str(path).startswith(str(self.root)))


class FailClosedParseTests(_MemoryCase):
    """Delivery-review P1: readers fail closed — every required field/section
    must be valid or the record parses to None and never surfaces."""

    BASE = {
        "memory_id": "mem-x", "kind": "decision", "status": "active",
        "confidence": "0.8", "created": "2026-07-13", "updated": "2026-07-13",
        "summary": "A lesson.", "evidence": "- `1x`", "targets": "- `src/a.py`",
    }

    def _compose(self, **overrides):
        f = {**self.BASE, **overrides}
        lines = ["# Title", "", "Owner: Engineering", f"Status: {f['status']}",
                 "Last verified: 2026-07-13", "", f"Memory ID: `{f['memory_id']}`",
                 f"Kind: `{f['kind']}`", f"Confidence: {f['confidence']}",
                 f"Created: {f['created']}", f"Updated: {f['updated']}", "",
                 "## Summary", "", f["summary"], "", "## Evidence", "", f["evidence"],
                 "", "## Targets", "", f["targets"], ""]
        return "\n".join(lines)

    def _write(self, stem, text):
        mem_dir = self.root / self.mem.MEMORY_DIR
        mem_dir.mkdir(parents=True, exist_ok=True)
        p = mem_dir / f"{stem}.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_each_malformed_shape_parses_to_none(self):
        # (stem, text-producing kwargs, why)
        cases = {
            "mem-nostatus": self._compose(status="").replace("Status: \n", ""),
            "mem-badstatus": self._compose(status="maybe"),
            "mem-noconf": self._compose(confidence="").replace("Confidence: \n", ""),
            "mem-badconf": self._compose(confidence="9"),
            "mem-baddate": self._compose(created="not-a-date"),
            "mem-nosummary": self._compose(summary=""),
            "mem-noevidence": self._compose(evidence=""),
            "mem-notargets": self._compose(targets=""),
        }
        for stem, text in cases.items():
            path = self._write(stem, text)
            self.assertIsNone(self.mem.parse_memory_record(path), stem)
        # id != filename stem also fails closed.
        path = self._write("mem-mismatch", self._compose(memory_id="mem-other"))
        self.assertIsNone(self.mem.parse_memory_record(path))

    def test_malformed_record_never_surfaces_via_load_or_search(self):
        # A status-less record on disk must not appear as an advisory.
        self._write("mem-broken", self._compose(status="").replace("Status: \n", ""))
        self._write("mem-good", self._compose(memory_id="mem-good"))
        surfaced = self.mem.load_memory_records(
            self.root, statuses=self.mem.DEFAULT_SURFACED_STATUSES)
        self.assertEqual([r["memory_id"] for r in surfaced], ["mem-good"])


class CreationAtomicityTests(_MemoryCase):
    """Delivery-review P1: exclusive creation closes the TOCTOU window."""

    def test_explicit_id_collision_raises(self):
        self.mem.write_memory_record(self.root, "a", "mem-dup")
        with self.assertRaises(FileExistsError):
            self.mem.write_memory_record(self.root, "b", "mem-dup")
        # content of the first writer is intact.
        self.assertEqual(
            (self.root / self.mem.MEMORY_DIR / "mem-dup.md").read_text(encoding="utf-8"), "a")

    def test_create_memory_record_retries_generated_ids(self):
        p1, id1 = self.mem.create_memory_record(
            self.root, lambda mid: f"content-{mid}", "mem-gen", explicit=False)
        p2, id2 = self.mem.create_memory_record(
            self.root, lambda mid: f"content-{mid}", "mem-gen", explicit=False)
        self.assertNotEqual(id1, id2)
        self.assertEqual(id1, "mem-gen")
        self.assertEqual(id2, "mem-gen-2")

    def test_concurrent_generated_create_never_overwrites(self):
        import threading
        n = 8
        barrier = threading.Barrier(n)
        results: list[str] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker():
            try:
                barrier.wait()
                _p, mid = self.mem.create_memory_record(
                    self.root, lambda m: f"body-{m}\n", "mem-race", explicit=False)
                with lock:
                    results.append(mid)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(set(results)), n, "every concurrent create got a distinct id")
        files = list((self.root / self.mem.MEMORY_DIR).glob("*.md"))
        self.assertEqual(len(files), n, "no write overwrote another")
        # Every file's body matches its own id — no lost update.
        for f in files:
            self.assertEqual(f.read_text(encoding="utf-8"), f"body-{f.stem}\n")


class SecretScanCoverageTests(_MemoryCase):
    """Delivery-review P1: every persisted caller field is scanned, and the
    rejected content is never echoed back."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()

    def _tree(self):
        return {p for p in self.root.rglob("*") if p.is_file()}

    def test_secret_in_title_or_targets_is_refused_without_side_effect(self):
        before = self._tree()
        for field in ("title", "targets"):
            kwargs = dict(title="Clean title", summary="Clean summary.",
                         evidence=["`1x`"], targets=["src/a.py"])
            if field == "title":
                kwargs["title"] = "set api_key: sk-live-abc in env"
            else:
                kwargs["targets"] = ["config.py password: hunter2"]
            resp = self.srv.memory_add_response(
                self.root, "environment_gotcha", kwargs["summary"], kwargs["evidence"],
                kwargs["targets"], title=kwargs["title"])
            self.assertEqual(resp["status"], "error", field)
            # The field name is reported; the secret text is NOT echoed.
            blob = json.dumps(resp)
            self.assertIn(field, blob)
            self.assertNotIn("sk-live-abc", blob)
            self.assertNotIn("hunter2", blob)
        self.assertEqual(self._tree(), before, "refused add wrote no file")

    def test_clean_record_still_writes(self):
        resp = self.srv.memory_add_response(
            self.root, "decision", "A clean lesson.", ["`1x`"], ["src/a.py"],
            title="Clean")
        self.assertEqual(resp["status"], "ok")


class ExactLifecycleMatchingTests(_MemoryCase):
    """Delivery-review P2: wave/change matching is exact-token, not substring."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()

    def test_token_extraction_ignores_substrings(self):
        self.assertEqual(self.srv._lifecycle_id_tokens("1abcd-enh some-change"), {"1abcd"})
        # 1abcd must NOT be found inside 1abcde.
        self.assertEqual(self.srv._lifecycle_id_tokens("1abcde longer"), set())
        self.assertEqual(self.srv._lifecycle_id_tokens("no ids here"), set())

    def test_prefix_collision_does_not_attach(self):
        # Record references the LONGER id; the wave is the SHORTER prefix id.
        self.srv.memory_add_response(
            self.root, "review_finding", "About the longer wave.",
            ["`1abce-enh longer-change`"], ["src/a.py"], memory_id="mem-longer")
        views = self.srv._memory_advisories_for_wave(
            self.root, {"wave_id": "1abcd short-wave",
                        "changes": [{"id": "1abcd-enh short-change"}]})
        self.assertEqual(views, [], "a prefix id must not attach the longer-id memory")

    def test_exact_token_match_attaches(self):
        self.srv.memory_add_response(
            self.root, "review_finding", "About this exact wave.",
            ["`1abcd-enh the-change` — round 2"], ["src/a.py"], memory_id="mem-exact")
        views = self.srv._memory_advisories_for_wave(
            self.root, {"wave_id": "1abce some-wave",
                        "changes": [{"id": "1abcd-enh the-change"}]})
        self.assertEqual([v["memory_id"] for v in views], ["mem-exact"])


class HotPathBoundedIOTests(_MemoryCase):
    """Delivery-review P1: warm-path advisories ride caches — records parse
    once across calls, the cluster artifact decompresses once, and freshness
    is one batched store read per call (never per-target)."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.srv._MEMORY_RECORDS_CACHE.clear()
        self.srv._MEMORY_BETWEENNESS_CACHE.clear()
        self.addCleanup(self.srv._MEMORY_RECORDS_CACHE.clear)
        self.addCleanup(self.srv._MEMORY_BETWEENNESS_CACHE.clear)
        (self.root / "src").mkdir(exist_ok=True)
        # Five churn-decayed records all targeting the same file (worst case
        # for per-target freshness reads under the old code).
        for i in range(5):
            self.srv.memory_add_response(
                self.root, "failed_attempt", f"Attempt {i}.", [f"`1c{i}`"],
                ["src/core.py"], memory_id=f"mem-core-{i}")
        # A gzip cluster artifact so betweenness has something to decompress.
        art = self.index_dir / "graph" / "project-graph-clusters.json"
        art.parent.mkdir(parents=True, exist_ok=True)
        import gzip as _gz
        with _gz.open(art, "wt", encoding="utf-8") as fh:
            json.dump({"betweenness": {"ranking": [
                {"node_id": "src/core.py::main", "score": 9.0}]}}, fh)
        self.srv._MEMORY_RECORDS_CACHE.clear()  # writes warmed it; start cold

    def test_warm_path_call_counts_and_latency_are_bounded(self):
        import gzip
        import time as _time
        counters = {"load": 0, "commits": 0, "gzip": 0}
        modmem = self.srv._memory_mod()
        modiss = self.srv._load_script("index_state_store")
        real_load = modmem.load_memory_records
        real_commits = modiss.file_commit_times
        real_gzip = gzip.open

        def load_spy(*a, **k):
            counters["load"] += 1
            return real_load(*a, **k)

        def commits_spy(*a, **k):
            counters["commits"] += 1
            return real_commits(*a, **k)

        def gzip_spy(*a, **k):
            counters["gzip"] += 1
            return real_gzip(*a, **k)

        modmem.load_memory_records = load_spy
        modiss.file_commit_times = commits_spy
        self.addCleanup(setattr, modmem, "load_memory_records", real_load)
        self.addCleanup(setattr, modiss, "file_commit_times", real_commits)
        with unittest.mock.patch("gzip.open", gzip_spy):
            t0 = _time.perf_counter()
            first = self.srv._memory_advisories_for_path(self.root, "src/core.py")
            t1 = _time.perf_counter()
            second = self.srv._memory_advisories_for_path(self.root, "src/core.py")
            t2 = _time.perf_counter()

        self.assertEqual(len(first), self.srv.MEMORY_ADVISORY_CAP)
        self.assertEqual(len(second), self.srv.MEMORY_ADVISORY_CAP)
        # Records parsed once total (second call is a cache hit).
        self.assertEqual(counters["load"], 1, "records must not re-parse on the warm call")
        # One batched freshness read per call — NOT one per matched record.
        self.assertEqual(counters["commits"], 2, "freshness must be one batched read per call")
        # Cluster artifact decompressed once across both calls (cached).
        self.assertEqual(counters["gzip"], 1, "betweenness must decompress once, then cache")
        # Bounded latency (local file ops; generous ceiling).
        self.assertLess(t1 - t0, 0.5)
        self.assertLess(t2 - t1, 0.5)

    def test_cache_invalidates_when_a_record_changes(self):
        self.srv._memory_advisories_for_path(self.root, "src/core.py")  # warm
        # A new matching record must be visible on the next call (signature
        # changes → cache miss).
        self.srv.memory_add_response(
            self.root, "fragile_file", "Newly fragile.", ["`1cx`"],
            ["src/core.py"], memory_id="mem-core-new")
        ids = {v["memory_id"]
               for v in self.srv._memory_advisories_for_path(self.root, "src/core.py")}
        # cap is 3, so assert the new one can appear by ranking it top (fragile
        # high confidence) — at minimum the cache reloaded (count grew on disk).
        records = self.srv._memory_records_cached(self.root, None)
        self.assertIn("mem-core-new", {r["memory_id"] for r in records})


class SymlinkReadAndMkdirTests(_MemoryCase):
    """Delivery re-review P0: containment covers READS (no external records
    surface) and validates BEFORE mkdir (no external dir is created)."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.srv._MEMORY_RECORDS_CACHE.clear()
        self.addCleanup(self.srv._MEMORY_RECORDS_CACHE.clear)

    def test_symlinked_memory_dir_surfaces_no_external_records(self):
        external = Path(self._tmp.name) / "external"
        external.mkdir()
        good = (
            "# Ext\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-07-13\n\n"
            "Memory ID: `mem-ext`\nKind: `decision`\nConfidence: 0.9\n"
            "Created: 2026-07-13\nUpdated: 2026-07-13\n\n"
            "## Summary\n\nExternal secret lesson.\n\n## Evidence\n\n- `1x`\n\n"
            "## Targets\n\n- `src/core.py`\n"
        )
        (external / "mem-ext.md").write_text(good, encoding="utf-8")
        # docs/agents exists from setUp; point memory at the external dir.
        (self.root / "docs" / "agents" / "memory").symlink_to(external)
        self.assertEqual(self.mem.load_memory_records(self.root), [],
                         "a symlinked memory dir must surface no records")
        self.assertEqual(
            self.srv._memory_advisories_for_path(self.root, "src/core.py"), [])
        self.assertIsNone(self.mem.canonical_memory_root(self.root))

    def test_refused_write_creates_no_external_directory(self):
        # A fresh repo whose docs/agents ANCESTOR is a symlink outside, with no
        # `memory` child yet — the refused write must not materialize it.
        repo2 = Path(self._tmp.name) / "repo2"
        (repo2 / "docs").mkdir(parents=True)
        external = Path(self._tmp.name) / "ext-agents"
        external.mkdir()
        (repo2 / "docs" / "agents").symlink_to(external)
        with self.assertRaises(ValueError):
            self.mem.write_memory_record(repo2, "content", "mem-x")
        self.assertFalse((external / "memory").exists(),
                         "mkdir must not run before containment is proven")
        with self.assertRaises(ValueError):
            self.mem.reconcile_memory_record(repo2, "mem-x", "stale")


class ParserLintParityTests(_MemoryCase):
    """Delivery re-review P1: every lint-invalid record is reader-invalid."""

    def _write(self, stem, text):
        d = self.root / self.mem.MEMORY_DIR
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{stem}.md"
        p.write_text(text, encoding="utf-8")
        return p

    def _rec(self, **o):
        f = {"mid": "mem-x", "status": "active", "extra": "",
             "evidence": "- `1x` note", "targets": "- `src/a.py`", **o}
        return (
            f"# T\n\nOwner: Engineering\nStatus: {f['status']}\nLast verified: 2026-07-13\n\n"
            f"Memory ID: `{f['mid']}`\nKind: `decision`\nConfidence: 0.8\n"
            f"Created: 2026-07-13\nUpdated: 2026-07-13\n{f['extra']}\n"
            f"## Summary\n\nBody.\n\n## Evidence\n\n{f['evidence']}\n\n## Targets\n\n{f['targets']}\n"
        )

    def test_superseded_without_link_is_reader_invalid(self):
        p = self._write("mem-x", self._rec(status="superseded"))
        self.assertIsNone(self.mem.parse_memory_record(p))

    def test_backticks_without_bullets_is_reader_invalid(self):
        # Evidence/Targets carry backticked refs but as prose, not bullets.
        p = self._write("mem-x", self._rec(
            evidence="see `1x` inline", targets="ref `src/a.py` inline"))
        self.assertIsNone(self.mem.parse_memory_record(p))

    def test_superseded_with_link_and_bulleted_refs_parses(self):
        p = self._write("mem-x", self._rec(
            status="superseded", extra="Superseded by: `mem-y`\n"))
        rec = self.mem.parse_memory_record(p)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["superseded_by"], "mem-y")


class GenerationCacheTests(_MemoryCase):
    """Delivery re-review P1: the advisory cache keys on a bounded, monotonic
    generation — no per-call tree walk, and no aliasing of distinct states."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.srv._MEMORY_RECORDS_CACHE.clear()
        self.addCleanup(self.srv._MEMORY_RECORDS_CACHE.clear)
        (self.root / "src").mkdir(exist_ok=True)

    def test_warm_calls_do_not_reparse_and_key_is_o1(self):
        for i in range(6):
            self.srv.memory_add_response(
                self.root, "decision", f"D{i}.", [f"`1c{i}`"], ["src/core.py"],
                memory_id=f"mem-{i}")
        self.srv._MEMORY_RECORDS_CACHE.clear()
        modmem = self.srv._memory_mod()
        real_load = modmem.load_memory_records
        calls = {"n": 0}

        def spy(*a, **k):
            calls["n"] += 1
            return real_load(*a, **k)

        modmem.load_memory_records = spy
        self.addCleanup(setattr, modmem, "load_memory_records", real_load)
        for _ in range(5):
            self.srv._memory_advisories_for_path(self.root, "src/core.py")
        self.assertEqual(calls["n"], 1, "warm calls must not re-parse the record set")
        # The key is O(1): (epoch, generation, dir mtime), never a per-file walk.
        key = self.srv._memory_cache_key(self.root)
        self.assertEqual(len(key), 3)

    def test_generation_bump_prevents_aliasing_on_same_size_edit(self):
        iss = self.srv._load_script("index_state_store")
        idx = self.root / ".wavefoundry" / "index"
        self.srv.memory_add_response(
            self.root, "fragile_file", "AAAA fragile.", ["`1x`"], ["src/core.py"],
            memory_id="mem-alias")
        first = self.srv._memory_advisories_for_path(self.root, "src/core.py")
        self.assertEqual(first[0]["summary"].split(".")[0], "AAAA fragile")
        key1 = self.srv._memory_cache_key(self.root)
        gen1 = iss.read_memory_state(idx)["generation"]
        # Reconcile (sanctioned mutation) advances the seqlock generation even
        # though the record file's size barely changes.
        self.srv.memory_reconcile_response(self.root, "mem-alias", "stale")
        gen2 = iss.read_memory_state(idx)["generation"]
        key2 = self.srv._memory_cache_key(self.root)
        self.assertGreater(gen2, gen1, "every sanctioned mutation advances the generation")
        self.assertNotEqual(key1, key2, "the key cannot alias distinct states")
        # The now-stale record is gone from active advisories (cache reloaded).
        after = self.srv._memory_advisories_for_path(self.root, "src/core.py")
        self.assertEqual(after, [])

    def test_indexer_style_bump_invalidates_after_raw_edit(self):
        iss = self.srv._load_script("index_state_store")
        idx = self.root / ".wavefoundry" / "index"
        self.srv.memory_add_response(
            self.root, "decision", "AAAA body.", ["`1x`"], ["src/core.py"],
            memory_id="mem-raw")
        self.srv._memory_records_cached(self.root, None)  # warm
        # Simulate a hook-driven raw edit: rewrite the file AND restore mtime,
        # then the indexer bumps the generation (as the build path does).
        p = self.root / self.mem.MEMORY_DIR / "mem-raw.md"
        st = p.stat()
        p.write_text(p.read_text(encoding="utf-8").replace("AAAA body", "BBBB body"),
                     encoding="utf-8")
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))  # restore mtime
        iss.memory_advance(idx)  # indexer invalidation signal
        records = {r["memory_id"]: r for r in self.srv._memory_records_cached(self.root, None)}
        self.assertIn("BBBB body", records["mem-raw"]["summary"],
                      "generation bump invalidates despite restored mtime")


class PerRecordSymlinkTests(_MemoryCase):
    """Round-4 P2 (defense in depth): an individual symlinked record pointing
    outside the canonical memory root must not be read or surfaced."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.srv._MEMORY_RECORDS_CACHE.clear()
        self.addCleanup(self.srv._MEMORY_RECORDS_CACHE.clear)

    def test_symlinked_record_is_skipped(self):
        external = Path(self._tmp.name) / "ext"
        external.mkdir()
        good = (
            "# Ext\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-07-13\n\n"
            "Memory ID: `mem-ext`\nKind: `decision`\nConfidence: 0.9\n"
            "Created: 2026-07-13\nUpdated: 2026-07-13\n\n"
            "## Summary\n\nExternal lesson.\n\n## Evidence\n\n- `1x`\n\n## Targets\n\n- `src/core.py`\n"
        )
        (external / "mem-ext.md").write_text(good, encoding="utf-8")
        mem_dir = self.root / self.mem.MEMORY_DIR
        mem_dir.mkdir(parents=True, exist_ok=True)
        # A single record file that is a symlink to the external record.
        (mem_dir / "mem-ext.md").symlink_to(external / "mem-ext.md")
        # A legitimate in-repo record for contrast.
        (mem_dir / "mem-real.md").write_text(good.replace("mem-ext", "mem-real"), encoding="utf-8")
        ids = {r["memory_id"] for r in self.mem.load_memory_records(self.root)}
        self.assertEqual(ids, {"mem-real"}, "symlinked record must be skipped")
        adv = {v["memory_id"]
               for v in self.srv._memory_advisories_for_path(self.root, "src/core.py")}
        self.assertEqual(adv, {"mem-real"})


class CacheFailureCorrectnessTests(_MemoryCase):
    """Round-4 P1: a failed/absent durable generation cannot serve stale
    memory — unconditional local eviction after mutation + cache bypass."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.srv._MEMORY_RECORDS_CACHE.clear()
        self.addCleanup(self.srv._MEMORY_RECORDS_CACHE.clear)
        (self.root / "src").mkdir(exist_ok=True)
        self.iss = self.srv._load_script("index_state_store")
        self.idx = self.root / ".wavefoundry" / "index"

    def test_failed_bump_does_not_serve_stale_after_reconcile(self):
        self.srv.memory_add_response(
            self.root, "fragile_file", "Active fragile lesson.", ["`1x`"],
            ["src/core.py"], memory_id="mem-a")
        first = self.srv._memory_advisories_for_path(self.root, "src/core.py")
        self.assertEqual([v["memory_id"] for v in first], ["mem-a"])  # warm + cached
        # Force the durable FINALIZE to fail — the fence set dirty=1 before
        # the write, so a failed finalize leaves dirty=1 and EVERY process
        # (fresh cache included) bypasses → reloads → sees 'stale'.
        real_fin = self.iss.memory_finalize
        self.iss.memory_finalize = lambda *a, **k: None
        try:
            self.srv.memory_reconcile_response(self.root, "mem-a", "stale")
        finally:
            self.iss.memory_finalize = real_fin
        # A SECOND independent process (cleared cache) must also see fresh.
        self.srv._MEMORY_RECORDS_CACHE.clear()
        after = self.srv._memory_advisories_for_path(self.root, "src/core.py")
        self.assertEqual(after, [], "a failed finalize must not serve the pre-write candidate")

    def test_unreadable_generation_bypasses_cache(self):
        self.srv.memory_add_response(
            self.root, "decision", "AAAA.", ["`1x`"], ["src/core.py"], memory_id="mem-b")
        real_read = self.iss.read_memory_state
        self.iss.read_memory_state = lambda *a, **k: None  # unreadable
        try:
            self.assertEqual(self.srv._memory_cache_key(self.root), self.srv._MEMORY_KEY_BYPASS)
            self.srv._memory_records_cached(self.root, None)  # populate nothing (bypass)
            # A raw edit is reflected immediately because caching is bypassed.
            p = self.root / self.mem.MEMORY_DIR / "mem-b.md"
            p.write_text(p.read_text(encoding="utf-8").replace("AAAA", "BBBB"), encoding="utf-8")
            recs = {r["memory_id"]: r for r in self.srv._memory_records_cached(self.root, None)}
            self.assertIn("BBBB", recs["mem-b"]["summary"])
            self.assertNotIn(str(self.root), self.srv._MEMORY_RECORDS_CACHE,
                             "bypass must not populate the cache")
        finally:
            self.iss.read_memory_state = real_read

    def test_atomic_concurrent_bumps(self):
        import threading
        n = 12
        barrier = threading.Barrier(n)

        def worker():
            barrier.wait()
            self.iss.memory_advance(self.idx)

        threads = [threading.Thread(target=worker) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.iss.read_memory_state(self.idx)["generation"], n,
                         "concurrent increments must be atomic (no lost updates)")

    def test_bump_does_not_touch_canonical_index_state_store(self):
        # A memory bump must never create/mutate index-state.sqlite (no
        # ensure_current/reset of canonical state).
        canonical = self.idx / "index-state.sqlite"
        self.assertFalse(canonical.exists())
        self.iss.memory_advance(self.idx)
        self.assertTrue((self.idx / "memory-state.sqlite").exists())
        self.assertFalse(canonical.exists(),
                         "the memory generation lives in its own store")


class ParserLintValueParityTests(_MemoryCase):
    """Adversarial-pass: the reader's value grammars match the lint's — no
    lint-invalid record parses (unsafe direction) and no lint-valid record is
    silently dropped (safe direction)."""

    def _write(self, stem, text):
        d = self.root / self.mem.MEMORY_DIR
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{stem}.md"
        p.write_text(text, encoding="utf-8")
        return p

    def _rec(self, **o):
        f = {"status": "active", "confidence": "0.8", "created": "2026-07-13",
             "evidence": "- `1x` note", "targets": "- `src/a.py`", **o}
        return (
            f"# T\n\nOwner: Engineering\nStatus: {f['status']}\nLast verified: 2026-07-13\n\n"
            f"Memory ID: `mem-x`\nKind: `decision`\nConfidence: {f['confidence']}\n"
            f"Created: {f['created']}\nUpdated: 2026-07-13\n\n"
            f"## Summary\n\nBody.\n\n## Evidence\n\n{f['evidence']}\n\n## Targets\n\n{f['targets']}\n"
        )

    def test_star_bullet_is_reader_invalid(self):
        # UNSAFE direction: lint rejects `*` bullets; the reader must too.
        p = self._write("mem-x", self._rec(evidence="* `1x` note", targets="* `src/a.py`"))
        self.assertIsNone(self.mem.parse_memory_record(p))

    def test_tab_after_dash_is_reader_invalid(self):
        p = self._write("mem-x", self._rec(evidence="-\t`1x` tabbed"))
        self.assertIsNone(self.mem.parse_memory_record(p))

    def test_scientific_and_signed_confidence_parse(self):
        # lint-valid float forms must not be silently dropped by the reader.
        for c in ("1e-1", "+0.5", "0.80"):
            p = self._write("mem-x", self._rec(confidence=c))
            rec = self.mem.parse_memory_record(p)
            self.assertIsNotNone(rec, c)
            self.assertTrue(0.0 <= rec["confidence"] <= 1.0)

    def test_dash_space_bullet_parses(self):
        p = self._write("mem-x", self._rec())
        self.assertIsNotNone(self.mem.parse_memory_record(p))


class NestedRecordTests(_MemoryCase):
    """Adversarial-pass: a lint-valid record in a real nested subdir surfaces
    (reader/lint parity), while symlink escapes stay blocked."""

    def test_nested_record_surfaces(self):
        good = (
            "# N\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-07-13\n\n"
            "Memory ID: `mem-nested`\nKind: `decision`\nConfidence: 0.7\n"
            "Created: 2026-07-13\nUpdated: 2026-07-13\n\n"
            "## Summary\n\nNested lesson.\n\n## Evidence\n\n- `1x`\n\n## Targets\n\n- `src/a.py`\n"
        )
        nested = self.root / self.mem.MEMORY_DIR / "archive"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "mem-nested.md").write_text(good, encoding="utf-8")
        ids = {r["memory_id"] for r in self.mem.load_memory_records(self.root)}
        self.assertIn("mem-nested", ids, "a real nested record must surface (parity with lint)")


class SeqlockCoherenceTests(_MemoryCase):
    """Round-4 P1: the durable memory seqlock gives cross-process coherence
    even when the finalize (generation advance) fails, and its random epoch
    defeats the delete/recreate ABA."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.srv._MEMORY_RECORDS_CACHE.clear()
        self.addCleanup(self.srv._MEMORY_RECORDS_CACHE.clear)
        (self.root / "src").mkdir(exist_ok=True)
        self.iss = self.srv._load_script("index_state_store")
        self.idx = self.root / ".wavefoundry" / "index"

    def test_failed_finalize_leaves_dirty_and_every_process_bypasses(self):
        self.srv.memory_add_response(
            self.root, "fragile_file", "Active lesson.", ["`1x`"], ["src/core.py"],
            memory_id="mem-a")
        self.srv._memory_advisories_for_path(self.root, "src/core.py")  # warm cache A
        real_fin = self.iss.memory_finalize
        self.iss.memory_finalize = lambda *a, **k: None  # finalize fails
        try:
            self.srv.memory_reconcile_response(self.root, "mem-a", "stale")
        finally:
            self.iss.memory_finalize = real_fin
        # The fence left dirty=1; a failed finalize did not clear it.
        state = self.iss.read_memory_state(self.idx)
        self.assertEqual(state["dirty"], 1, "a failed finalize leaves the fence set")
        # ANY process (its own key) BYPASSES while dirty → reloads fresh.
        self.assertEqual(self.srv._memory_cache_key(self.root), self.srv._MEMORY_KEY_BYPASS)
        # A second process (fresh cache) sees the stale record excluded.
        self.srv._MEMORY_RECORDS_CACHE.clear()
        after = self.srv._memory_advisories_for_path(self.root, "src/core.py")
        self.assertEqual(after, [], "cross-process: no stale advisory despite failed finalize")

    def test_random_epoch_defeats_delete_recreate_aba(self):
        self.srv.memory_add_response(
            self.root, "decision", "d.", ["`1x`"], ["src/core.py"], memory_id="mem-b")
        key1 = self.srv._memory_cache_key(self.root)
        epoch1 = self.iss.read_memory_state(self.idx)["epoch"]
        self.assertTrue(epoch1)
        # Delete + recreate the store (ABA): a naive counter would return to the
        # same generation; the random epoch must change the key.
        (self.idx / self.iss.MEMORY_STATE_FILENAME).unlink()
        self.iss.memory_advance(self.idx)  # recreates with a NEW epoch
        epoch2 = self.iss.read_memory_state(self.idx)["epoch"]
        key2 = self.srv._memory_cache_key(self.root)
        self.assertNotEqual(epoch1, epoch2, "a recreated store must mint a new epoch")
        self.assertNotEqual(key1, key2, "the epoch defeats the delete/recreate ABA")

    def test_fence_refusal_blocks_the_write(self):
        real_fence = self.iss.memory_fence
        self.iss.memory_fence = lambda *a, **k: False  # cannot establish the fence
        try:
            before = {p for p in self.root.rglob("*.md")}
            resp = self.srv.memory_add_response(
                self.root, "decision", "refused.", ["`1x`"], ["src/core.py"],
                memory_id="mem-refused")
            self.assertEqual(resp["status"], "error")
            self.assertIn("memory_state_unwritable", str(resp))
            self.assertEqual({p for p in self.root.rglob("*.md")}, before,
                             "a fence refusal must write no record file")
            rec = self.srv.memory_add_response(
                self.root, "decision", "x.", ["`1y`"], ["src/core.py"], memory_id="mem-r2")
            self.assertEqual(rec["status"], "error")
        finally:
            self.iss.memory_fence = real_fence


class TwoProcessCacheCoherenceTests(_MemoryCase):
    """Round-4 re-review evidence: two independently LOADED server module
    instances (distinct ``_MEMORY_RECORDS_CACHE`` + distinct
    ``index_state_store``) in ONE interpreter, sharing only the on-disk seqlock
    — stronger than clearing one module's cache to fake a second process, but
    still same-interpreter. ``RealChildProcessCoherenceTests`` adds the true
    separate-OS-process probe for the core reader-bypass property."""

    def setUp(self):
        super().setUp()
        self.p1 = load_server()
        self.p2 = load_independent_server()
        self.p1._MEMORY_RECORDS_CACHE.clear()
        self.p2._MEMORY_RECORDS_CACHE.clear()
        self.addCleanup(self.p1._MEMORY_RECORDS_CACHE.clear)
        self.addCleanup(self.p2._MEMORY_RECORDS_CACHE.clear)
        (self.root / "src").mkdir(exist_ok=True)
        # Distinct module instances → distinct index_state_store objects.
        self.iss1 = self.p1._load_script("index_state_store")
        self.iss2 = self.p2._load_script("index_state_store")
        self.assertIsNot(self.iss1, self.iss2, "processes must not share iss")
        self.idx = self.root / ".wavefoundry" / "index"

    def _warm_both(self):
        a = [v["memory_id"] for v in self.p1._memory_advisories_for_path(self.root, "src/core.py")]
        b = [v["memory_id"] for v in self.p2._memory_advisories_for_path(self.root, "src/core.py")]
        return a, b

    def test_second_process_never_serves_stale_after_failed_finalize(self):
        # p1 writes; both processes warm their OWN caches on the active record.
        self.p1.memory_add_response(
            self.root, "fragile_file", "Active lesson.", ["`1x`"], ["src/core.py"],
            memory_id="mem-a")
        a, b = self._warm_both()
        self.assertEqual((a, b), (["mem-a"], ["mem-a"]), "both warm on the active record")
        self.assertIn(str(self.root), self.p2._MEMORY_RECORDS_CACHE, "p2 cache is genuinely warm")
        # p1 reconciles to 'stale' but its FINALIZE fails → fence's dirty=1
        # persists on disk. Only p1's iss is patched (its own code); p2 is not.
        real_fin = self.iss1.memory_finalize
        self.iss1.memory_finalize = lambda *a, **k: None
        try:
            self.p1.memory_reconcile_response(self.root, "mem-a", "stale")
        finally:
            self.iss1.memory_finalize = real_fin
        self.assertEqual(self.iss2.read_memory_state(self.idx)["dirty"], 1)
        # p2 NEVER cleared its cache; it must still bypass (dirty) and reload,
        # excluding the now-stale record. This is the genuine cross-process proof.
        after = self.p2._memory_advisories_for_path(self.root, "src/core.py")
        self.assertEqual(after, [], "warm second process must not serve the pre-write advisory")

    def test_second_process_sees_generation_advance_after_normal_edit(self):
        self.p1.memory_add_response(
            self.root, "fragile_file", "Active lesson.", ["`1x`"], ["src/core.py"],
            memory_id="mem-a")
        a, b = self._warm_both()
        self.assertEqual((a, b), (["mem-a"], ["mem-a"]))
        gen_before = self.iss2.read_memory_state(self.idx)["generation"]
        # Normal reconcile: finalize succeeds → generation advances, dirty clears.
        self.p1.memory_reconcile_response(self.root, "mem-a", "stale")
        self.assertGreater(self.iss2.read_memory_state(self.idx)["generation"], gen_before)
        # p2's cached key carries the OLD generation → key mismatch → reload.
        after = self.p2._memory_advisories_for_path(self.root, "src/core.py")
        self.assertEqual(after, [], "the advanced generation invalidates the second process' warm cache")

    def test_indexer_invalidate_fallback_reaches_second_process(self):
        # A raw edit (no tool call): memory_invalidate returns False when the
        # generation cannot advance (the indexer then FAILS the build), but it
        # sets a best-effort fence token so the second warm process bypasses in
        # the meantime. Uses the real indexer-side entry point.
        self.p1.memory_add_response(
            self.root, "fragile_file", "AAAA.", ["`1x`"], ["src/core.py"], memory_id="mem-a")
        self._warm_both()
        # Raw-edit the record on disk (bypasses the tool fence path entirely).
        rec = self.root / self.mem.MEMORY_DIR / "mem-a.md"
        rec.write_text(rec.read_text(encoding="utf-8").replace("AAAA", "BBBB"), encoding="utf-8")
        # Force advance to fail so the fail-closed fence-token path is exercised.
        real_adv = self.iss1.memory_advance
        self.iss1.memory_advance = lambda *a, **k: None
        try:
            self.assertFalse(self.iss1.memory_invalidate(self.idx),
                             "a failed advance is NOT durable invalidation — returns False "
                             "so the indexer fails the build")
        finally:
            self.iss1.memory_advance = real_adv
        # But a best-effort fence token was set → readers bypass in the window.
        self.assertEqual(self.iss2.read_memory_state(self.idx)["dirty"], 1)
        # p2 (warm, never cleared) bypasses and reloads the edited record.
        recs = {r["memory_id"]: r for r in self.p2._memory_records_cached(self.root, None)}
        self.assertIn("BBBB", recs["mem-a"]["summary"])


class WriterTokenInterleaveTests(_MemoryCase):
    """Round-4 re-review P1: writer-owned fence tokens — one writer's finalize
    CANNOT clear a concurrent writer's fence (the shared-`dirty` bug), and a
    crashed writer's token self-heals after the TTL."""

    def setUp(self):
        super().setUp()
        self.iss = _load("index_state_store")
        self.idx = self.root / ".wavefoundry" / "index"

    def _dirty(self) -> int:
        return self.iss.read_memory_state(self.idx)["dirty"]

    def test_finalize_a_does_not_clear_fence_b(self):
        # A fence → B fence → A finalize: B's fence must survive (readers still
        # bypass) because A removes only its OWN token.
        tok_a = self.iss.memory_fence(self.idx)
        tok_b = self.iss.memory_fence(self.idx)
        self.assertTrue(tok_a and tok_b and tok_a != tok_b, "distinct writer tokens")
        self.assertEqual(self._dirty(), 1)
        self.iss.memory_finalize(self.idx, tok_a)
        self.assertEqual(self._dirty(), 1,
                         "A's finalize must NOT clear B's in-flight fence")
        self.iss.memory_finalize(self.idx, tok_b)
        self.assertEqual(self._dirty(), 0, "once B also finalizes, no writer remains")

    def test_generation_advances_once_per_finalize(self):
        g0 = self.iss.read_memory_state(self.idx)["generation"]
        tok_a = self.iss.memory_fence(self.idx)
        tok_b = self.iss.memory_fence(self.idx)
        self.assertEqual(self.iss.read_memory_state(self.idx)["generation"], g0,
                         "fencing does not advance the generation")
        self.iss.memory_finalize(self.idx, tok_a)
        self.iss.memory_finalize(self.idx, tok_b)
        self.assertEqual(self.iss.read_memory_state(self.idx)["generation"], g0 + 2)

    def test_stale_writer_token_self_heals_after_ttl(self):
        # A token older than the TTL must not keep readers bypassing forever.
        self.iss.memory_fence(self.idx)
        self.assertEqual(self._dirty(), 1)
        # Backdate the token's started_at beyond the TTL (simulate a crashed
        # writer) — no wall-clock sleep.
        conn = self.iss._memory_state_rw(self.idx)
        try:
            old = 1  # epoch seconds, far in the past
            conn.execute("UPDATE memory_writers SET started_at = ?", (old,))
        finally:
            conn.close()
        self.assertEqual(self._dirty(), 0,
                         "a token older than the TTL is not a live fence (self-heal)")

    def test_failed_finalize_keeps_only_its_own_token_live(self):
        # A's finalize fails (token not removed) while B finalizes cleanly:
        # readers keep bypassing on A's live token, not B's.
        tok_a = self.iss.memory_fence(self.idx)
        tok_b = self.iss.memory_fence(self.idx)
        self.iss.memory_finalize(self.idx, tok_b)  # B clean
        self.assertEqual(self._dirty(), 1, "A's token still live → bypass")
        self.iss.memory_finalize(self.idx, tok_a)  # A recovers
        self.assertEqual(self._dirty(), 0)


class RealChildProcessCoherenceTests(_MemoryCase):
    """Round-4 re-review P2 evidence: prove cross-process reader coherence with
    a REAL OS child process (not two module instances in one interpreter). A
    child interpreter reads the shared on-disk seqlock and reports dirty."""

    def setUp(self):
        super().setUp()
        self.iss = _load("index_state_store")
        self.idx = self.root / ".wavefoundry" / "index"
        self.idx.mkdir(parents=True, exist_ok=True)

    def _child_dirty(self) -> int:
        # Spawn a fresh Python that imports index_state_store and reads state.
        code = (
            "import importlib.util, sys, json\n"
            f"spec = importlib.util.spec_from_file_location('iss', {str(SCRIPTS_ROOT / 'index_state_store.py')!r})\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "from pathlib import Path\n"
            f"st = m.read_memory_state(Path({str(self.idx)!r}))\n"
            "print(json.dumps(st))\n"
        )
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout.strip())["dirty"]

    def test_child_process_sees_live_fence_and_clear(self):
        self.assertEqual(self._child_dirty(), 0, "no writer → child sees clean")
        tok = self.iss.memory_fence(self.idx)  # this process fences
        self.assertEqual(self._child_dirty(), 1,
                         "a REAL child process observes the in-flight fence")
        self.iss.memory_finalize(self.idx, tok)
        self.assertEqual(self._child_dirty(), 0,
                         "the child observes the fence cleared after finalize")


class FindDuplicatesTests(_MemoryCase):
    """Wave 1stwl: detection-only exact/normalized duplicate detection."""

    def _rec(self, memory_id, *, kind="review_finding", summary="A lesson.",
             evidence=("`ev-1`",), targets=("src/a.py",), status="active"):
        return {"memory_id": memory_id, "kind": kind, "summary": summary,
                "evidence_refs": list(evidence), "target_refs": list(targets),
                "status": status}

    def test_evidence_id_overlap_flags_duplicate(self):
        existing = [self._rec("mem-a", evidence=["`ev-42`", "`1abcd`"])]
        cand = self._rec("mem-b", summary="totally different words",
                         evidence=["`ev-42`"])
        dups = self.mem.find_duplicates(cand, existing)
        self.assertEqual(len(dups), 1)
        self.assertIn("evidence_ref", dups[0]["signals"])
        self.assertEqual(dups[0]["memory_id"], "mem-a")
        self.assertEqual(dups[0]["shared_evidence"], ["ev-42"])

    def test_normalized_summary_match_flags_duplicate(self):
        existing = [self._rec("mem-a", summary="The Chunker regresses, silently!")]
        # different punctuation/case/whitespace, no shared evidence → normalized only
        cand = self._rec("mem-b", summary="the   chunker regresses silently",
                         evidence=["`ev-99`"])
        dups = self.mem.find_duplicates(cand, existing)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]["signals"], ["normalized_content"])
        self.assertEqual(dups[0]["shared_evidence"], [])

    def test_distinct_records_do_not_match(self):
        existing = [self._rec("mem-a", summary="one thing", targets=["src/a.py"])]
        cand = self._rec("mem-b", summary="another thing", targets=["src/b.py"],
                         evidence=["`ev-2`"])
        self.assertEqual(self.mem.find_duplicates(cand, existing), [])

    def test_different_targets_break_normalized_match(self):
        existing = [self._rec("mem-a", summary="same words", targets=["src/a.py"])]
        cand = self._rec("mem-b", summary="same words", targets=["src/b.py"],
                         evidence=["`ev-2`"])
        self.assertEqual(self.mem.find_duplicates(cand, existing), [])

    def test_unicode_letters_are_not_erased_into_a_false_duplicate(self):
        existing = [self._rec("mem-a", summary="修复解析器", targets=["src/a.py"])]
        cand = self._rec(
            "mem-b", summary="修复缓存", targets=["src/a.py"], evidence=["`ev-2`"]
        )
        self.assertEqual(self.mem.find_duplicates(cand, existing), [])
        self.assertNotEqual(
            self.mem.normalize_summary(existing[0]["summary"]),
            self.mem.normalize_summary(cand["summary"]),
        )

    def test_generic_wave_reference_is_not_duplicate_evidence(self):
        existing = [self._rec("mem-a", summary="first", evidence=["`1abcd`"])]
        cand = self._rec(
            "mem-b", summary="second", evidence=["1abcd"], targets=["src/a.py"]
        )
        self.assertEqual(self.mem.find_duplicates(cand, existing), [])

    def test_history_records_are_never_duplicates(self):
        for st in ("superseded", "stale", "rejected"):
            existing = [self._rec("mem-old", evidence=["`ev-1`"], status=st)]
            cand = self._rec("mem-new", evidence=["`ev-1`"])
            self.assertEqual(self.mem.find_duplicates(cand, existing), [],
                             f"{st} record must not count as a duplicate")

    def test_own_id_is_skipped(self):
        existing = [self._rec("mem-a", evidence=["`ev-1`"])]
        cand = self._rec("mem-a", evidence=["`ev-1`"])  # same id = same record
        self.assertEqual(self.mem.find_duplicates(cand, existing), [])

    def test_determinism(self):
        existing = [self._rec("mem-a", summary="X  Y, z.", evidence=["`ev-1`"])]
        cand = self._rec("mem-b", summary="x y z", evidence=["`ev-1`"])
        first = self.mem.find_duplicates(cand, existing)
        second = self.mem.find_duplicates(cand, existing)
        self.assertEqual(first, second)
        self.assertEqual(set(first[0]["signals"]),
                         {"evidence_ref", "normalized_content"})

    def test_normalize_summary_is_fixed(self):
        self.assertEqual(self.mem.normalize_summary("Foo—Bar!!  baz"), "foo bar baz")
        self.assertEqual(self.mem.normalize_summary("  A_B  "), "a b")
        self.assertEqual(self.mem.normalize_summary(""), "")


class MemoryAddDuplicateDiagnosticTests(_MemoryCase):
    """Wave 1stwl: memory_add surfaces possible_duplicate (non-blocking)."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()

    def _add(self, summary, evidence, targets, memory_id, **kw):
        return self.srv.memory_add_response(
            self.root, "review_finding", summary, evidence, targets,
            memory_id=memory_id, **kw)

    def test_duplicate_add_written_with_advisory(self):
        first = self._add("The chunker regresses silently.", ["`ev-7`"],
                          ["src/chunker.py"], "mem-first")
        self.assertEqual(first["status"], "ok")
        self.assertFalse(any(d["code"] == "possible_duplicate"
                             for d in first["diagnostics"]))
        # same evidence id + same normalized content → possible duplicate
        second = self._add("the chunker regresses silently", ["`ev-7`"],
                           ["src/chunker.py"], "mem-second")
        self.assertEqual(second["status"], "ok")
        self.assertTrue(second["data"]["written"], "non-blocking: still written")
        codes = [d["code"] for d in second["diagnostics"]]
        self.assertIn("possible_duplicate", codes)
        self.assertTrue((self.root / self.mem.MEMORY_DIR / "mem-second.md").is_file())

    def test_abort_if_duplicate_refuses_without_mutation(self):
        self._add("A durable lesson.", ["`ev-9`"], ["src/a.py"], "mem-orig")
        before = sorted(p.name for p in (self.root / self.mem.MEMORY_DIR).glob("*.md"))
        resp = self._add("a durable lesson", ["`ev-9`"], ["src/a.py"],
                         "mem-dupe", abort_if_duplicate=True)
        self.assertEqual(resp["status"], "error")
        self.assertFalse(resp["data"]["written"])
        self.assertIn("possible_duplicate", [d["code"] for d in resp["diagnostics"]])
        after = sorted(p.name for p in (self.root / self.mem.MEMORY_DIR).glob("*.md"))
        self.assertEqual(before, after, "abort must not write anything")

    def test_non_duplicate_add_has_no_advisory(self):
        self._add("First lesson.", ["`ev-1`"], ["src/a.py"], "mem-a")
        resp = self._add("A wholly different lesson.", ["`ev-2`"], ["src/b.py"],
                         "mem-b")
        self.assertEqual(resp["status"], "ok")
        self.assertFalse(any(d["code"] == "possible_duplicate"
                             for d in resp["diagnostics"]))

    def test_concurrent_abort_if_duplicate_serializes_scan_and_write(self):
        barrier = threading.Barrier(2)
        results = []

        def run(index):
            barrier.wait()
            results.append(
                self._add(
                    "Same concurrent lesson.", ["`ev-concurrent`"],
                    ["src/a.py"], f"mem-concurrent-{index}",
                    abort_if_duplicate=True,
                )
            )

        threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sorted(result["status"] for result in results), ["error", "ok"])
        self.assertEqual(
            len(list((self.root / self.mem.MEMORY_DIR).glob("*.md"))), 1
        )


class MemoryProposeTests(_MemoryCase):
    """Wave 1stwk: draft candidate records from a wave's typed review evidence."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.supply = _load("memory_supply")

    def _wave(self, wave_id, slug, *, decision_rows=(), ce_totals=None):
        d = self.root / "docs" / "waves" / f"{wave_id} {slug}"
        d.mkdir(parents=True)
        change_id = f"{wave_id}k-feat {slug}"
        rows = "\n".join(f"| 2026-01-0{i + 1} | {dec} | {reason} | alt |"
                         for i, (dec, reason) in enumerate(decision_rows))
        change = (
            f"# {slug}\n\nChange ID: `{change_id}`\n\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| ---- | -------- | ------ | ------------ |\n" + rows + "\n"
        )
        (d / f"{change_id}.md").write_text(change, encoding="utf-8")
        ce = ""
        if ce_totals is not None:
            ce = ("\n## Context Efficiency\n\n<!-- wave:context-efficiency-state "
                  + json.dumps({"totals": ce_totals}) + " -->\n")
        (d / "wave.md").write_text(
            f"# Wave\n\nwave-id: `{wave_id} {slug}`\n\n"
            f"Change ID: `{change_id}`\n\n"
            f"review-evidence-source: events.jsonl\n{ce}", encoding="utf-8")
        (d / "events.jsonl").write_bytes(b"")
        return change_id

    def test_drafts_only_code_anchored_decisions(self):
        self._wave("1aaaa", "demo",
                   decision_rows=[("Use `src/foo.py` for X", "because Y"),
                                  ("A prose-only decision", "no anchor")],
                   ce_totals={"request_debit": 100, "response_debit": 900})
        r = self.srv.memory_propose_response(self.root, "1aaaa", "dry_run")
        d = r["data"]
        self.assertEqual(d["records_proposed"], 1, "prose-only decision must be skipped")
        draft = d["proposed"][0]
        self.assertEqual(draft["kind"], "decision")
        self.assertEqual(draft["targets"], ["src/foo.py"])
        self.assertEqual(draft["source_exploration_cost"], 1000)

    def test_only_admitted_change_docs_supply_decisions(self):
        self._wave(
            "1aaaa", "demo",
            decision_rows=[("Use `src/kept.py`", "admitted")],
        )
        wave_dir = self.root / "docs" / "waves" / "1aaaa demo"
        (wave_dir / "1zzzz-feat stray.md").write_text(
            "# Stray\n\nChange ID: `1zzzz-feat stray`\n\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| --- | --- | --- | --- |\n"
            "| 2026-01-01 | Use `src/stray.py` | unadmitted | none |\n",
            encoding="utf-8",
        )
        drafts = self.supply.draft_candidates(self.root, "1aaaa")
        self.assertEqual([draft["targets"] for draft in drafts], [["src/kept.py"]])

    def test_decision_parser_preserves_escaped_and_inline_code_pipes(self):
        rows = self.supply._decision_log_rows(
            "## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| --- | --- | --- | --- |\n"
            "| 2026-01-01 | Use `src/a.py` with `x|y` | left \\| right | none |\n"
        )
        self.assertEqual(len(rows), 1)
        self.assertIn("`x|y`", rows[0]["decision"])
        self.assertEqual(rows[0]["reason"], "left \\| right")

    def test_create_writes_candidate_and_stamps_cost(self):
        cid = self._wave("1aaaa", "demo",
                         decision_rows=[("Fix `src/foo.py`", "reason")],
                         ce_totals={"request_debit": 10, "response_debit": 40})
        r = self.srv.memory_propose_response(self.root, "1aaaa", "create")
        self.assertEqual(r["data"]["records_written"], 1)
        self.assertEqual(r["data"]["records_promoted"], 0)
        rec = self.mem.parse_memory_record(self.root / r["data"]["written"][0]["path"])
        self.assertEqual(rec["status"], "candidate", "never auto-promotes to active")
        self.assertEqual(rec["source_exploration_cost"], 50)
        self.assertIn("1aaaa", rec["evidence_refs"])
        self.assertIn(cid, rec["evidence_refs"])
        self.assertIn("src/foo.py", rec["target_refs"])

    def test_live_sqlite_cost_supersedes_stale_markdown_projection(self):
        self._wave(
            "1aaaa", "demo",
            decision_rows=[("Fix `src/foo.py`", "reason")],
            ce_totals={"request_debit": 1, "response_debit": 2},
        )
        ce = _load("context_efficiency")
        conn = ce._open_write_store(self.root)
        conn.execute(
            "INSERT INTO phase_state(wave_id,phase_id,stage,ordinal,created_at)"
            " VALUES('1aaaa demo','implement-1','implement',1,1)"
        )
        conn.execute(
            "INSERT INTO telemetry_event("
            "event_id,producer_id,wave_id,phase_id,stage,tool_name,event_kind,"
            "request_tokens,response_tokens,workflow_prompt_tokens,"
            "source_credits_dropped,created_at"
            ") VALUES('event-1','producer','1aaaa demo','implement-1',"
            "'implement','code_read','retrieval',40,60,0,0,1)"
        )
        conn.commit()
        conn.close()
        wave_dir = self.root / "docs" / "waves" / "1aaaa demo"
        self.assertEqual(self.supply.source_exploration_cost(wave_dir), 100)

    def test_authoritative_zero_sqlite_cost_does_not_revive_stale_projection(self):
        self._wave(
            "1aaaa", "demo",
            decision_rows=[("Fix `src/foo.py`", "reason")],
            ce_totals={"request_debit": 400, "response_debit": 600},
        )
        ce = _load("context_efficiency")
        conn = ce._open_write_store(self.root)
        conn.execute(
            "INSERT INTO wave_state(wave_id,generation,pending,measurement_status)"
            " VALUES('1aaaa demo',1,0,'healthy')"
        )
        conn.commit()
        conn.close()
        wave_dir = self.root / "docs" / "waves" / "1aaaa demo"
        self.assertEqual(self.supply.source_exploration_cost(wave_dir), 0)

    def test_create_is_idempotent(self):
        self._wave("1aaaa", "demo", decision_rows=[("Fix `src/foo.py`", "reason")])
        first = self.srv.memory_propose_response(self.root, "1aaaa", "create")
        self.assertEqual(first["data"]["records_written"], 1)
        self.assertEqual(first["data"]["records_promoted"], 0)
        second = self.srv.memory_propose_response(self.root, "1aaaa", "create")
        self.assertEqual(second["data"]["records_promoted"], 0)
        self.assertEqual(second["data"]["skipped_dispositions"], 1)
        files = list((self.root / self.mem.MEMORY_DIR).glob("*.md"))
        self.assertEqual(len(files), 1, "re-running must not flood duplicates")

    def test_disposition_pagination_reaches_sources_beyond_public_cap(self):
        self._wave(
            "1many",
            "many",
            decision_rows=[
                (f"Use `src/file_{index}.py` for boundary {index}", "durable reason")
                for index in range(25)
            ],
        )
        first = self.srv.memory_propose_response(
            self.root, "1many", "create", limit=20
        )
        self.assertEqual(first["data"]["records_written"], 20)
        second = self.srv.memory_propose_response(
            self.root, "1many", "dry_run", limit=20
        )
        self.assertEqual(second["data"]["records_proposed"], 5)
        self.assertEqual(second["data"]["skipped_dispositions"], 20)
        codes = [
            item["code"]
            for item in self.srv._memory_validation_diagnostics(self.root, "1many")
        ]
        self.assertIn("memory_validation_candidates_missing", codes)
        self.assertIn("memory_validation_required", codes)

    def test_concurrent_public_create_serializes_dedup_and_write(self):
        self._wave("1aaaa", "demo", decision_rows=[("Fix `src/foo.py`", "reason")])
        barrier = threading.Barrier(2)
        results = []

        def run():
            barrier.wait()
            results.append(
                self.srv.memory_propose_response(
                    self.root, "1aaaa", "create"
                )
            )

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(
            sorted(result["data"]["records_written"] for result in results),
            [0, 1],
        )
        self.assertEqual(
            len(list((self.root / self.mem.MEMORY_DIR).glob("*.md"))), 1
        )

    def test_no_material_evidence_diagnostic(self):
        self._wave("1aaaa", "demo", decision_rows=[("prose only", "no anchor")])
        r = self.srv.memory_propose_response(self.root, "1aaaa", "dry_run")
        self.assertEqual(r["data"]["records_proposed"], 0)
        self.assertIn("no_material_evidence", [x["code"] for x in r["diagnostics"]])

    def test_docs_and_config_paths_are_not_code_anchors(self):
        self._wave(
            "1aaaa", "demo",
            decision_rows=[
                ("Update `docs/guide.md`", "docs"),
                ("Update `config/settings.json`", "config"),
            ],
        )
        r = self.srv.memory_propose_response(self.root, "1aaaa", "dry_run")
        self.assertEqual(r["data"]["records_proposed"], 0)

    def test_dry_run_writes_nothing(self):
        self._wave("1aaaa", "demo", decision_rows=[("Fix `src/foo.py`", "reason")])
        r = self.srv.memory_propose_response(self.root, "1aaaa", "dry_run")
        self.assertEqual(r["data"]["records_promoted"], 0)
        self.assertFalse((self.root / self.mem.MEMORY_DIR).exists(),
                         "dry_run must not write records")

    def test_invalid_mode_and_missing_wave(self):
        bad = self.srv.memory_propose_response(self.root, "1aaaa", "wat")
        self.assertEqual(bad["status"], "error")
        self.assertIn("invalid_arguments", [x["code"] for x in bad["diagnostics"]])
        none = self.srv.memory_propose_response(self.root, "", "dry_run")
        self.assertEqual(none["status"], "error")

    def test_unique_prefix_resolves_and_ambiguous_prefix_fails(self):
        self._wave("1aaaa", "one", decision_rows=[("Fix `src/a.py`", "reason")])
        resolved = self.srv.memory_propose_response(
            self.root, "1aaa", "dry_run"
        )
        self.assertEqual(resolved["status"], "ok")
        self._wave("1aaab", "two", decision_rows=[("Fix `src/b.py`", "reason")])
        ambiguous = self.srv.memory_propose_response(
            self.root, "1aaa", "dry_run"
        )
        self.assertEqual(ambiguous["status"], "error")
        self.assertIn(
            "ambiguous_wave_id",
            [diagnostic["code"] for diagnostic in ambiguous["diagnostics"]],
        )

    def test_finding_path_fragile_and_failed_attempt(self):
        self._wave("1aaaa", "demo", decision_rows=[])
        heads = (
            {"record_type": "executable_evidence", "evidence_record_id": "ev-1",
             "artifact_or_test_id": "src/bug.py"},
            {"record_type": "executable_evidence", "evidence_record_id": "ev-2",
             "artifact_or_test_id": "src/frag.py"},
            {"record_type": "executable_evidence", "evidence_record_id": "ev-3",
             "artifact_or_test_id": "src/frag.py"},
            {"record_type": "executable_evidence", "evidence_record_id": "ev-4",
             "artifact_or_test_id": "src/x.py"},
            {"record_type": "finding_synthesis", "finding_id": "finding-1",
             "disposition": "do_now", "repair_execution_state": "completed",
             "disposition_rationale": "Fixed a real bug in `src/bug.py`.",
             "evidence_record_id": "ev-1"},
            {"record_type": "finding_synthesis", "finding_id": "finding-2",
             "disposition": "do_now", "repair_execution_state": "completed",
             "disposition_rationale": "First fix in `src/frag.py`.",
             "evidence_record_id": "ev-2"},
            {"record_type": "finding_synthesis", "finding_id": "finding-3",
             "disposition": "do_now", "repair_execution_state": "completed",
             "disposition_rationale": "Second fix in `src/frag.py`.",
             "evidence_record_id": "ev-3"},
            {"record_type": "finding_synthesis", "finding_id": "finding-4",
             "disposition": "maybe_later", "repair_execution_state": "completed",
             "disposition_rationale": "Not a real defect `src/x.py`.",
             "evidence_record_id": "ev-4"},
        )
        orig = self.supply.read_review_event_ledger
        self.supply.read_review_event_ledger = lambda wave_dir: (heads, ())
        try:
            drafts = self.supply.draft_candidates(self.root, "1aaaa")
        finally:
            self.supply.read_review_event_ledger = orig
        by_kind = {d["kind"]: d for d in drafts}
        self.assertIn("fragile_file", by_kind, "frag.py repaired twice → fragile_file")
        self.assertIn("failed_attempt", by_kind, "bug.py repaired once → failed_attempt")
        self.assertEqual(by_kind["fragile_file"]["targets"], ["src/frag.py"])
        self.assertEqual(
            by_kind["failed_attempt"]["source_event"],
            "finding:1aaaa:finding-1",
        )
        self.assertNotIn("src/x.py", [t for d in drafts for t in d["targets"]],
                         "maybe_later finding is ephemeral and skipped")

    def test_real_event_ledger_repair_chain_supplies_executable_anchor(self):
        self._wave("1aaaa", "demo", decision_rows=[])
        review = _load("review_evidence")
        base = {
            "event": "finding",
            "actor": "qa-reviewer",
            "context_id": "memory-supply-finding",
            "finding_id": "real-ledger-defect",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": {
                "validation_status": "real",
                "scope_relation": "admitted",
                "introduced_or_worsened_by_wave": True,
                "contract_relevance": "required_ac",
                "supported_reachability": True,
                "attacker_reachability": False,
                "authority_domain": "integrity",
                "authority_delta": "low",
                "observable_impact": "material",
                "containment": "none",
            },
            "proposition": "the repaired implementation preserves the code path",
            "failure_condition": "the code path loses the repaired behavior",
            "public_path": "memory candidate supply",
            "command_or_fixture": "test_real_event_ledger_repair_chain",
            "expected": "a durable candidate targets the executable artifact",
            "observed": "the defect reproduced before repair",
            "artifact_or_test_id": "src/real_bug.py",
            "known_bad_detection_method": "pre-repair behavior probe",
            "limitations": "local disposable fixture",
            "safety_and_authorization": "local fixture only",
            "disposition_rationale": "a reproduced required-contract defect",
            "integrity_confirmed": True,
            "review_boundaries_changed": [],
            "source_lanes": ["qa-reviewer"],
            "blocking_required_lanes": ["qa-reviewer"],
            "approval_recheck_lanes": ["qa-reviewer"],
        }
        records = ()
        for run_kind, cycle in (
            ("initial_delivery", 0),
            ("repair_start", 1),
            ("reverification", 1),
        ):
            event = dict(base, run_kind=run_kind, cycle=cycle,
                         context_id=f"memory-supply-{run_kind}")
            if run_kind == "reverification":
                event["blocking_required_lanes"] = []
                event["fresh_context"] = True
                event["independent"] = True
            rows, errors = review.build_compact_review_event(records, event)
            self.assertEqual(errors, ())
            records = (*records, *rows)
        events = self.root / "docs" / "waves" / "1aaaa demo" / "events.jsonl"
        events.write_text(
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in records
            ),
            encoding="utf-8",
        )
        drafts = self.supply.draft_candidates(self.root, "1aaaa")
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["kind"], "failed_attempt")
        self.assertEqual(drafts[0]["targets"], ["src/real_bug.py"])
        self.assertEqual(
            drafts[0]["source_event"],
            "finding:1aaaa:real-ledger-defect",
        )

    def test_verification_command_never_becomes_a_target(self):
        """Wave 1t72b (1t728) AC-1: command_or_fixture describes HOW a claim was
        verified; its file tokens (the verification harness) must never become
        draft targets. Mirrors the real 1t3ek misattribution shape through the
        canonical ledger producer."""
        self._wave("1aaaa", "demo", decision_rows=[])
        review = _load("review_evidence")
        base = {
            "event": "finding", "actor": "qa-reviewer",
            "context_id": "target-misattribution",
            "finding_id": "wrapper-defect", "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": {
                "validation_status": "real", "scope_relation": "admitted",
                "introduced_or_worsened_by_wave": True,
                "contract_relevance": "required_ac",
                "supported_reachability": True, "attacker_reachability": False,
                "authority_domain": "integrity", "authority_delta": "low",
                "observable_impact": "material", "containment": "none",
            },
            "proposition": "the wrapper credit computation matches the contract",
            "failure_condition": "aggregate flooring returns",
            "public_path": "src/server_impl.py credit wrapper",
            "command_or_fixture": "python3 run_tests.py (6024 OK, uncontended)",
            "expected": "per-artifact flooring", "observed": "repaired",
            "artifact_or_test_id": "canonical suite green; boundary regression",
            "known_bad_detection_method": "pre-repair behavior probe",
            "limitations": "local fixture", "safety_and_authorization": "local",
            "disposition_rationale": "a reproduced required-contract defect",
            "integrity_confirmed": True, "review_boundaries_changed": [],
            "source_lanes": ["qa-reviewer"],
            "blocking_required_lanes": ["qa-reviewer"],
            "approval_recheck_lanes": ["qa-reviewer"],
        }
        records = ()
        for run_kind, cycle in (
            ("initial_delivery", 0), ("repair_start", 1), ("reverification", 1),
        ):
            event = dict(base, run_kind=run_kind, cycle=cycle,
                         context_id=f"misattribution-{run_kind}")
            if run_kind == "reverification":
                event["blocking_required_lanes"] = []
                event["fresh_context"] = True
                event["independent"] = True
            rows, errors = review.build_compact_review_event(records, event)
            self.assertEqual(errors, ())
            records = (*records, *rows)
        events = self.root / "docs" / "waves" / "1aaaa demo" / "events.jsonl"
        events.write_text(
            "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n"
                    for r in records),
            encoding="utf-8",
        )
        drafts = self.supply.draft_candidates(self.root, "1aaaa")
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["targets"], ["src/server_impl.py"],
                         "the repaired surface, never the verification command")
        all_targets = [t for d in drafts for t in d["targets"]]
        self.assertNotIn("run_tests.py", all_targets)

    def test_command_only_file_token_drafts_nothing(self):
        """Wave 1t72b (1t728) AC-2: when the only file token lives in
        command_or_fixture, the finding has no concrete repaired-surface anchor
        and drafts nothing — an honest gap beats a wrong advisory."""
        self._wave("1aaaa", "demo", decision_rows=[])
        heads = (
            {"record_type": "executable_evidence", "evidence_record_id": "ev-1",
             "artifact_or_test_id": "canonical suite green",
             "public_path": "the credit wrapper path",
             "command_or_fixture": "python3 run_tests.py"},
            {"record_type": "finding_synthesis", "finding_id": "finding-1",
             "disposition": "do_now", "repair_execution_state": "completed",
             "disposition_rationale": "Fixed.", "evidence_record_id": "ev-1"},
        )
        orig = self.supply.read_review_event_ledger
        self.supply.read_review_event_ledger = lambda wave_dir: (heads, ())
        try:
            drafts = self.supply.draft_candidates(self.root, "1aaaa")
        finally:
            self.supply.read_review_event_ledger = orig
        self.assertEqual(drafts, [],
                         "no repaired-surface anchor: draft nothing, not run_tests.py")

    def test_conservative_skips_unrepaired_findings(self):
        self._wave("1aaaa", "demo", decision_rows=[])
        heads = (
            {"record_type": "finding_synthesis", "finding_id": "finding-1",
             "disposition": "do_now", "repair_execution_state": "pending",
             "disposition_rationale": "Open issue in `src/open.py`.",
             "evidence_record_id": "ev-1"},
        )
        orig = self.supply.read_review_event_ledger
        self.supply.read_review_event_ledger = lambda wave_dir: (heads, ())
        try:
            drafts = self.supply.draft_candidates(self.root, "1aaaa")
        finally:
            self.supply.read_review_event_ledger = orig
        self.assertEqual(drafts, [], "an unrepaired finding is not a durable lesson")


class ExplorationAvoidedTests(_MemoryCase):
    """Wave 1svuk: the separate, grounded, labeled estimated-exploration-avoided metric."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.ea = _load("exploration_avoided")

    def _open_wave(self, wave_id="1zaaa demo", status="implementing"):
        d = self.root / "docs" / "waves" / wave_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "wave.md").write_text(
            f"# Wave\n\nStatus: {status}\nwave-id: `{wave_id}`\n", encoding="utf-8")
        return wave_id

    def _record(self, memory_id, *, cost, targets=("src/hot.py",)):
        content = self.mem.render_memory_record(
            memory_id=memory_id, kind="failed_attempt", summary=f"Lesson {memory_id}.",
            evidence=["`1abcd`"], targets=list(targets), title=f"T {memory_id}",
            status="active", source_exploration_cost=cost)
        return self.mem.write_memory_record(self.root, content, memory_id)

    # --- module unit tests ---

    def test_attribution_factor_bounded_below_one(self):
        self.assertLess(self.ea.attribution_factor(1.0, cited=False), 1.0)
        self.assertLess(self.ea.attribution_factor(1.0, cited=True), 1.0)
        self.assertGreater(self.ea.attribution_factor(1.0, cited=True),
                           self.ea.attribution_factor(1.0, cited=False))
        self.assertEqual(self.ea.attribution_factor(0.0), 0.0)

    def test_estimate_credit_grounded_and_skips_costless(self):
        r = self.ea.estimate_credit([
            {"source_exploration_cost": 1000, "match_confidence": 1.0},
            {"source_exploration_cost": None, "match_confidence": 1.0},
            {"source_exploration_cost": 0, "match_confidence": 1.0},
        ])
        self.assertEqual(r["credit"], 500)  # 1000 * 0.5 * 1.0; costless skipped
        self.assertEqual(r["credited_records"], 1)
        self.assertEqual(r["surfaced_events"], 1)
        self.assertEqual(r["cited_events"], 0)

    def test_credit_accumulates_and_reads(self):
        self.ea.credit_surface(self.root, "1zaaa demo",
                               [{"memory_id": "mem-a", "source_origin": "1srca",
                                 "source_exploration_cost": 1000,
                                 "match_confidence": 1.0}],
                               context_key="src/a.py")
        self.ea.credit_surface(self.root, "1zaaa demo",
                               [{"memory_id": "mem-b", "source_origin": "1srcb",
                                 "source_exploration_cost": 400,
                                 "match_confidence": 1.0}],
                               context_key="src/b.py")
        est = self.ea.read_wave(self.root, "1zaaa demo")
        self.assertEqual(est["estimated_exploration_avoided"], 500 + 200)
        self.assertEqual(est["surfaced_events"], 2)

    def test_same_phase_context_deduplicates_and_origin_budget_caps(self):
        item_a = {"memory_id": "mem-a", "source_origin": "1same",
                  "source_exploration_cost": 1000, "match_confidence": 1.0}
        item_b = {"memory_id": "mem-b", "source_origin": "1same",
                  "source_exploration_cost": 1000, "match_confidence": 1.0}
        self.ea.credit_surface(
            self.root, "1zaaa demo", [item_a], stage="review", phase_id="review-1",
            context_key="src/hot.py")
        self.ea.credit_surface(
            self.root, "1zaaa demo", [item_a], stage="review", phase_id="review-1",
            context_key="src/hot.py")
        self.ea.credit_surface(
            self.root, "1zaaa demo", [item_b], stage="review", phase_id="review-1",
            context_key="src/other.py")
        est = self.ea.read_wave(self.root, "1zaaa demo")
        self.assertEqual(est["estimated_exploration_avoided"], 500,
                         "one source wave gets one bounded phase budget")
        self.assertEqual(est["surfaced_events"], 2,
                         "the repeated identical event is deduplicated")

    def test_new_phase_can_credit_same_memory_again(self):
        item = {"memory_id": "mem-a", "source_origin": "1same",
                "source_exploration_cost": 1000, "match_confidence": 1.0}
        for phase in ("review-1", "repair-1"):
            self.ea.credit_surface(
                self.root, "1zaaa demo", [item], stage="review", phase_id=phase,
                context_key="src/hot.py")
        self.assertEqual(
            self.ea.read_wave(self.root, "1zaaa demo")[
                "estimated_exploration_avoided"
            ],
            1000,
        )

    def test_concurrent_distinct_origins_are_lossless(self):
        barrier = threading.Barrier(8)
        results = []

        def run(index):
            barrier.wait()
            results.append(
                self.ea.credit_surface(
                    self.root, "1zaaa demo",
                    [{"memory_id": f"mem-{index}", "source_origin": f"1src{index}",
                      "source_exploration_cost": 100, "match_confidence": 1.0}],
                    stage="review", phase_id="review-1",
                    context_key=f"src/{index}.py",
                )
            )

        threads = [threading.Thread(target=run, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertTrue(all(result is not None for result in results))
        totals = self.ea.read_wave(self.root, "1zaaa demo")
        self.assertEqual(totals["estimated_exploration_avoided"], 400)
        self.assertEqual(totals["surfaced_events"], 8)

    def test_cited_state_is_distinct_and_can_use_cited_budget(self):
        item = {"memory_id": "mem-a", "source_origin": "1same",
                "source_exploration_cost": 1000, "match_confidence": 1.0}
        self.ea.credit_surface(
            self.root, "1zaaa demo", [item], cited=False,
            stage="review", phase_id="review-1", context_key="src/a.py")
        self.ea.credit_surface(
            self.root, "1zaaa demo", [item], cited=True,
            stage="review", phase_id="review-1", context_key="src/a.py")
        totals = self.ea.read_wave(self.root, "1zaaa demo")
        self.assertEqual(totals["estimated_exploration_avoided"], 750)
        self.assertEqual(totals["surfaced_events"], 1)
        self.assertEqual(totals["cited_events"], 1)

    def test_non_exact_match_gets_no_credit(self):
        result = self.ea.credit_surface(
            self.root, "1zaaa demo",
            [{"memory_id": "mem-a", "source_origin": "1same",
              "source_exploration_cost": 1000, "match_confidence": 0.25}],
            context_key="unmatched")
        self.assertIsNone(result)
        self.assertEqual(
            self.ea.read_wave(self.root, "1zaaa demo")[
                "estimated_exploration_avoided"
            ],
            0,
        )

    def test_read_absent_wave_is_zero(self):
        self.assertEqual(
            self.ea.read_wave(self.root, "9none")["estimated_exploration_avoided"], 0)

    def test_first_credit_lazily_extends_existing_sqlite_authority(self):
        self.ea.credit_surface(
            self.root, "1zaaa demo",
            [{"memory_id": "mem-a", "source_origin": "1srca",
              "source_exploration_cost": 1000, "match_confidence": 1.0}],
            context_key="src/a.py")
        store = self.root / ".wavefoundry" / "logs" / "context-efficiency.sqlite"
        self.assertTrue(store.is_file())
        conn = sqlite3.connect(store)
        try:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        finally:
            conn.close()
        self.assertIn("telemetry_event", tables)
        self.assertIn("exploration_credit_event", tables)
        self.assertFalse(
            (self.root / ".wavefoundry" / "index" / "exploration-avoided.json").exists()
        )

    def test_lazy_schema_upgrade_preserves_existing_store_state(self):
        ce = _load("context_efficiency")
        conn = ce._open_write_store(self.root)
        conn.execute("DROP TABLE exploration_credit_event")
        conn.execute("INSERT INTO meta(key,value) VALUES('fixture_sentinel','kept')")
        conn.commit()
        conn.close()
        self.ea.credit_surface(
            self.root, "1zaaa demo",
            [{"memory_id": "mem-a", "source_origin": "1srca",
              "source_exploration_cost": 1000, "match_confidence": 1.0}],
            context_key="src/a.py")
        conn = sqlite3.connect(ce.store_path(self.root))
        try:
            self.assertEqual(
                conn.execute(
                    "SELECT value FROM meta WHERE key='fixture_sentinel'"
                ).fetchone()[0],
                "kept",
            )
            self.assertIsNotNone(
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='exploration_credit_event'"
                ).fetchone()
            )
        finally:
            conn.close()

    def test_projection_is_separate_from_context_efficiency(self):
        self.ea.credit_surface(
            self.root, "1zaaa demo",
            [{"memory_id": "mem-a", "source_origin": "1srca",
              "source_exploration_cost": 1000, "match_confidence": 1.0}],
            context_key="src/a.py")
        projected = self.ea.replace_checkpoint_block(
            "# Wave\n\n## Context Efficiency\n\nMeasured.\n",
            self.root,
            "1zaaa demo",
        )
        self.assertIn("## Estimated Exploration Avoided", projected)
        self.assertIn("Estimated tokens avoided", projected)
        self.assertIn("## Context Efficiency", projected)
        self.assertNotIn("estimated_tokens_saved", projected)

    # --- integration with the advisory surface ---

    def test_brief_surface_credits_open_wave(self):
        wid = self._open_wave()
        self._record("mem-hot", cost=2000, targets=("src/hot.py",))
        self.srv.memory_brief_response(self.root, targets=["src/hot.py"])
        est = self.ea.read_wave(self.root, wid)
        self.assertEqual(est["estimated_exploration_avoided"], 1000)  # 2000*0.5*1.0
        self.assertEqual(est["surfaced_events"], 1)

    def test_passive_path_advisory_uses_same_credit_api(self):
        wid = self._open_wave()
        self._record("mem-hot", cost=2000, targets=("src/hot.py",))
        advisories = self.srv._memory_advisories_for_path(
            self.root, "src/hot.py"
        )
        self.assertEqual([item["memory_id"] for item in advisories], ["mem-hot"])
        est = self.ea.read_wave(self.root, wid)
        self.assertEqual(est["estimated_exploration_avoided"], 1000)
        self.assertEqual(est["surfaced_events"], 1)

    def test_passive_advisory_records_current_stage_and_phase(self):
        wid = self._open_wave()
        ce = _load("context_efficiency")
        conn = ce._open_write_store(self.root)
        conn.execute(
            "INSERT INTO phase_state(wave_id,phase_id,stage,ordinal,created_at)"
            " VALUES(?,?,?,?,?)",
            (wid, "review-7", "review", 1, 1),
        )
        conn.commit()
        conn.close()
        self._record("mem-hot", cost=2000, targets=("src/hot.py",))
        self.srv._memory_advisories_for_path(self.root, "src/hot.py")
        conn = sqlite3.connect(ce.store_path(self.root))
        try:
            row = conn.execute(
                "SELECT stage,phase_id FROM exploration_credit_event"
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row, ("review", "review-7"))

    def test_lifecycle_flush_projects_sqlite_estimate_into_wave(self):
        wid = self._open_wave()
        self.ea.credit_surface(
            self.root, wid,
            [{"memory_id": "mem-a", "source_origin": "1srca",
              "source_exploration_cost": 1000, "match_confidence": 1.0}],
            context_key="src/a.py")

        class Telemetry:
            def flush(self, *_args, **_kwargs):
                ce = _load("context_efficiency")
                return ce.FlushResult(success=True, persistence="durable")

        handler = type("Handler", (), {"root": self.root, "telemetry": Telemetry()})()
        result, _ = self.srv._flush_context_efficiency(handler, wid)
        self.assertEqual(result["projection"], "published")
        wave_md = self.root / "docs" / "waves" / wid / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("<!-- wave:exploration-avoided begin -->", text)
        self.assertIn("| 1 | 0 | 1 | 500 |", text)

    def test_pending_projection_covers_reload_and_upgrade_barrier(self):
        wid = self._open_wave()
        self.ea.credit_surface(
            self.root, wid,
            [{"memory_id": "mem-a", "source_origin": "1srca",
              "source_exploration_cost": 1000, "match_confidence": 1.0}],
            context_key="src/a.py")

        class Telemetry:
            def flush(self, *_args, **_kwargs):
                ce = _load("context_efficiency")
                return ce.FlushResult(success=True, persistence="durable")

        handler = type("Handler", (), {"root": self.root, "telemetry": Telemetry()})()
        result = self.srv.project_pending_context_efficiency(handler)
        self.assertTrue(result["ok"])
        self.assertEqual(result["projected"], [wid])
        text = (
            self.root / "docs" / "waves" / wid / "wave.md"
        ).read_text(encoding="utf-8")
        self.assertIn("<!-- wave:exploration-avoided begin -->", text)

    def test_existence_alone_does_not_accrue(self):
        wid = self._open_wave()
        self._record("mem-hot", cost=2000)
        # never surface an advisory
        self.assertEqual(
            self.ea.read_wave(self.root, wid)["estimated_exploration_avoided"], 0)

    def test_credits_implementing_wave_not_a_readied_wave(self):
        # A readied (planned) wave that sorts BEFORE the implementing one must
        # not steal attribution — they coexist under the single-OPEN rule.
        self._open_wave("1aaaa readied", status="planned")   # sorts first
        self._open_wave("1zzzz open", status="implementing")
        self._record("mem-hot", cost=2000, targets=("src/hot.py",))
        self.srv.memory_brief_response(self.root, targets=["src/hot.py"])
        self.assertEqual(
            self.ea.read_wave(self.root, "1zzzz open")["estimated_exploration_avoided"],
            1000, "credit attributes to the implementing wave")
        self.assertEqual(
            self.ea.read_wave(self.root, "1aaaa readied")["estimated_exploration_avoided"],
            0, "a readied wave must not be credited")

    def test_no_open_wave_no_accrual(self):
        self._record("mem-hot", cost=2000, targets=("src/hot.py",))
        self.srv.memory_brief_response(self.root, targets=["src/hot.py"])
        sidecar = self.root / ".wavefoundry" / "index" / "exploration-avoided.json"
        self.assertFalse(sidecar.exists(), "no open wave → nothing to attribute")

    def test_wf_current_wave_surfaces_separate_labeled_estimate(self):
        self._open_wave()
        self._record("mem-hot", cost=2000, targets=("src/hot.py",))
        self.srv.memory_brief_response(self.root, targets=["src/hot.py"])
        cur = self.srv.wf_current_wave_response(self.root)
        blk = cur["data"].get("estimated_exploration_avoided")
        self.assertIsNotNone(blk, "the estimate must surface as its own labeled block")
        self.assertGreater(blk["tokens"], 0)
        self.assertFalse(blk["measured"], "labeled as an estimate, not measured")
        self.assertIn("caveat", blk)
        self.assertNotIn("context_efficiency", blk, "never inside the measured block")

    @unittest.skipIf(getattr(os, "geteuid", lambda: 1)() == 0, "root bypasses chmod")
    def test_advisory_output_invariant_to_credit_failure(self):
        self._open_wave()
        self._record("mem-hot", cost=2000, targets=("src/hot.py",))
        good = self.srv.memory_brief_response(self.root, targets=["src/hot.py"])
        idx = self.root / ".wavefoundry" / "index"
        idx.mkdir(parents=True, exist_ok=True)
        os.chmod(idx, 0o500)  # credit write now fails
        try:
            degraded = self.srv.memory_brief_response(self.root, targets=["src/hot.py"])
        finally:
            os.chmod(idx, 0o700)
        self.assertEqual(good["status"], "ok")
        self.assertEqual(good["data"]["advisories"], degraded["data"]["advisories"],
                         "credit success/failure must not change the advisory output")


class MemorySearchOrderingTests(_MemoryCase):
    """Wave 1svuj: semantic rank tie-breaks within the trust policy, never overrides it."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()

    def _semantic_index(self, *memory_ids):
        """A mock index whose search_docs ranks the given memory ids, in order."""
        idx = MagicMock()
        idx.search_docs.return_value = (
            [{"path": f"{self.mem.MEMORY_DIR}/{mid}.md"} for mid in memory_ids], False)
        return idx

    def test_semantic_does_not_demote_high_trust_record(self):
        # A: high confidence; B: low confidence but the top semantic hit.
        self._add("mem-a", "operator_preference", confidence=0.9, targets=("src/a.py",))
        self._add("mem-b", "review_finding", confidence=0.3, targets=("src/b.py",))
        idx = self._semantic_index("mem-b", "mem-a")  # semantic wants B first
        resp = self.srv.memory_search_response(self.root, query="regress", index=idx)
        ids = [r["memory_id"] for r in resp["data"]["records"]]
        self.assertLess(ids.index("mem-a"), ids.index("mem-b"),
                        "the higher-confidence record must not be demoted by text relevance")

    def test_semantic_tiebreaks_within_a_confidence_tier(self):
        # Same confidence tier → semantic rank decides the order within it.
        self._add("mem-a", "review_finding", confidence=0.5, targets=("src/a.py",))
        self._add("mem-b", "review_finding", confidence=0.5, targets=("src/b.py",))
        idx = self._semantic_index("mem-b", "mem-a")
        resp = self.srv.memory_search_response(self.root, query="q", index=idx)
        ids = [r["memory_id"] for r in resp["data"]["records"]]
        self.assertEqual(ids, ["mem-b", "mem-a"],
                         "within one confidence tier, semantic rank orders the records")

    def test_no_index_path_is_policy_order(self):
        self._add("mem-a", "operator_preference", confidence=0.9)
        self._add("mem-b", "review_finding", confidence=0.3)
        # No index → semantic_hit_order stays empty → the re-sort never runs.
        resp = self.srv.memory_search_response(self.root, query="lesson")
        ids = [r["memory_id"] for r in resp["data"]["records"]]
        self.assertEqual(ids, ["mem-a", "mem-b"],
                         "no-index path stays in policy order (confidence desc)")


class MemoryAutoPopulateTests(_MemoryCase):
    """Wave 1svr6/1syle: close fallback creates candidates, never verdicts."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        self.supply = _load("memory_supply")

    def _wave(self, wave_id, slug, decision_rows):
        d = self.root / "docs" / "waves" / f"{wave_id} {slug}"
        d.mkdir(parents=True)
        change_id = f"{wave_id}k-feat {slug}"
        rows = "\n".join(f"| 2026-01-0{i + 1} | {dec} | {reason} | alt |"
                         for i, (dec, reason) in enumerate(decision_rows))
        change = (
            f"# {slug}\n\nChange ID: `{change_id}`\n\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| ---- | -------- | ------ | ------------ |\n" + rows + "\n"
        )
        (d / f"{change_id}.md").write_text(change, encoding="utf-8")
        (d / "wave.md").write_text(
            f"# Wave\n\nwave-id: `{wave_id} {slug}`\n\n"
            f"Change ID: `{change_id}`\n",
            encoding="utf-8",
        )

    def test_close_drafts_candidates_without_promotion(self):
        self._wave("1aaaa", "demo", [
            ("Use `src/foo.py` for X", "because Y"),   # rationale -> active
            ("Bare choice on `src/bar.py`", ""),        # no rationale -> candidate
        ])
        summary = self.srv._auto_populate_memory_for_wave(self.root, "1aaaa")
        self.assertEqual(summary["drafted"], 2)
        self.assertEqual(summary["promoted"], 0)
        self.assertEqual(summary["candidate"], 2)
        self.assertEqual(summary["validation_required"], 2)
        recs = self.mem.load_memory_records(self.root, statuses=("active", "candidate"))
        self.assertEqual([r["status"] for r in recs], ["candidate", "candidate"])
        self.assertTrue(all(r["validation"] == "pending" for r in recs))
        self.assertEqual(len({r["source_event"] for r in recs}), 2)

    def test_close_is_idempotent(self):
        self._wave("1aaaa", "demo", [("Use `src/foo.py`", "because")])
        first = self.srv._auto_populate_memory_for_wave(self.root, "1aaaa")
        self.assertEqual(first["drafted"], 1)
        second = self.srv._auto_populate_memory_for_wave(self.root, "1aaaa")
        self.assertEqual(second, {}, "re-close must not re-draft")
        self.assertEqual(len(list((self.root / self.mem.MEMORY_DIR).glob("*.md"))), 1)

    def test_never_auto_supersedes_existing(self):
        self._add("mem-existing", "decision", status="active", targets=("src/existing.py",))
        before = (self.root / self.mem.MEMORY_DIR / "mem-existing.md").read_text(encoding="utf-8")
        self._wave("1aaaa", "demo", [("Use `src/foo.py`", "because")])
        self.srv._auto_populate_memory_for_wave(self.root, "1aaaa")
        after = (self.root / self.mem.MEMORY_DIR / "mem-existing.md").read_text(encoding="utf-8")
        self.assertEqual(before, after, "auto-populate must never rewrite an existing record")

    def test_empty_wave_returns_empty_summary(self):
        self._wave("1aaaa", "demo", [("prose only, no code anchor", "reason")])
        self.assertEqual(self.srv._auto_populate_memory_for_wave(self.root, "1aaaa"), {})


class MemoryAgentValidationTests(_MemoryCase):
    """1syle: compact agent judgment + durable source disposition."""

    def setUp(self):
        super().setUp()
        self.srv = load_server()
        (self.root / "src").mkdir(parents=True)

    def _candidate(self, memory_id: str, source_event: str, target: str = "src/a.py"):
        (self.root / target).parent.mkdir(parents=True, exist_ok=True)
        (self.root / target).write_text("value = 1\n", encoding="utf-8")
        content = self.mem.render_memory_record(
            memory_id=memory_id, kind="failed_attempt",
            title=f"Candidate {memory_id}",
            summary="Generated prose that requires semantic validation.",
            evidence=["ev-proof", "1aaaa"], targets=[target],
            source_event=source_event, validation="pending",
        )
        self.mem.write_memory_record(self.root, content, memory_id)

    def _validate(self, memory_id: str, verdict: str, **kwargs):
        return self.srv.memory_validate_response(
            self.root, memory_id, verdict,
            kwargs.pop("action_delta", "Run the targeted regression before editing."),
            kwargs.pop("rationale", "Evidence and current target support the lesson."),
            kwargs.pop("evidence_verified", True),
            kwargs.pop("current_target_verified", True),
            kwargs.pop("canonical_overlap", "none"),
            **kwargs,
        )

    def test_promote_retain_and_reject_persist_compact_judgment(self):
        expected = {
            "promote": ("active", "promote"),
            "retain": ("candidate", "retain"),
            "reject": ("rejected", "reject"),
        }
        for verdict, (status, validation) in expected.items():
            with self.subTest(verdict=verdict):
                mid = f"mem-{verdict}"
                self._candidate(mid, f"finding:{verdict}")
                result = self._validate(
                    mid, verdict,
                    evidence_verified=verdict != "reject",
                    current_target_verified=verdict != "reject",
                    canonical_overlap="duplicates" if verdict == "reject" else "none",
                    action_delta=(
                        "No memory action; the canonical contract already owns this."
                        if verdict == "reject"
                        else "Run the targeted regression before editing."
                    ),
                )
                self.assertEqual(result["status"], "ok", result)
                record = self.mem.parse_memory_record(
                    self.root / self.mem.MEMORY_DIR / f"{mid}.md"
                )
                self.assertEqual(record["status"], status)
                self.assertEqual(record["validation"], validation)
                self.assertEqual(record["validated_by"], "agent")
                self.assertTrue(record["action_delta"])

    def test_rewrite_creates_corrected_record_and_supersedes_candidate(self):
        self._candidate("mem-generated", "finding:rewrite")
        result = self._validate(
            "mem-generated", "rewrite",
            rewrite_kind="successful_pattern",
            rewrite_title="Verify parser parity",
            rewrite_summary=(
                "When editing the parser fallback, compare the exact public result "
                "with the independent reference and expected specification."
            ),
            rewrite_evidence=["ev-proof", "1aaaa", "test_parser_parity"],
            rewrite_targets=["src/a.py"],
            rewrite_confidence=0.9,
        )
        self.assertEqual(result["status"], "ok", result)
        replacement = result["data"]["rewrite_record"]["memory_id"]
        old = self.mem.parse_memory_record(
            self.root / self.mem.MEMORY_DIR / "mem-generated.md"
        )
        new = self.mem.parse_memory_record(
            self.root / self.mem.MEMORY_DIR / f"{replacement}.md"
        )
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(old["validation"], "rewrite")
        self.assertEqual(old["superseded_by"], replacement)
        self.assertEqual(new["status"], "active")
        self.assertEqual(new["validation"], "promote")
        self.assertEqual(new["source_event"], "finding:rewrite")

    def test_rewrite_retry_reuses_replacement_after_partial_failure(self):
        self._candidate("mem-partial", "finding:partial")
        kwargs = {
            "rewrite_kind": "successful_pattern",
            "rewrite_title": "Corrected durable lesson",
            "rewrite_summary": "Run the exact parity regression before editing this parser.",
            "rewrite_evidence": ["ev-proof", "1aaaa", "test_parser_parity"],
            "rewrite_targets": ["src/a.py"],
            "rewrite_confidence": 0.9,
        }
        server_mem = self.srv._memory_mod()
        with patch.object(
            server_mem,
            "record_memory_validation",
            side_effect=OSError("forced source-update failure"),
        ):
            first = self._validate("mem-partial", "rewrite", **kwargs)
        self.assertEqual(first["status"], "error")
        self.assertEqual(
            len(list((self.root / self.mem.MEMORY_DIR).glob("*.md"))),
            2,
        )
        second = self._validate("mem-partial", "rewrite", **kwargs)
        self.assertEqual(second["status"], "ok", second)
        self.assertEqual(
            len(list((self.root / self.mem.MEMORY_DIR).glob("*.md"))),
            2,
            "retry must reuse the already-created replacement",
        )

    def test_validation_fails_closed_on_missing_judgment_or_target(self):
        self._candidate("mem-invalid", "finding:invalid")
        missing = self._validate(
            "mem-invalid", "promote", evidence_verified=False
        )
        self.assertEqual(missing["status"], "error")
        (self.root / "src" / "a.py").unlink()
        stale = self._validate("mem-invalid", "promote")
        self.assertEqual(stale["status"], "error")
        record = self.mem.parse_memory_record(
            self.root / self.mem.MEMORY_DIR / "mem-invalid.md"
        )
        self.assertEqual(record["validation"], "pending")

    def test_validation_rejects_forbidden_metadata_without_echo_or_write(self):
        self._candidate("mem-secret-validation", "finding:secret-validation")
        before = (
            self.root / self.mem.MEMORY_DIR / "mem-secret-validation.md"
        ).read_bytes()
        result = self._validate(
            "mem-secret-validation",
            "promote",
            action_delta="set api_key: sk-live-validation-secret in env",
        )
        self.assertEqual(result["status"], "error")
        blob = json.dumps(result)
        self.assertIn("action_delta", blob)
        self.assertNotIn("sk-live-validation-secret", blob)
        self.assertEqual(
            (self.root / self.mem.MEMORY_DIR / "mem-secret-validation.md").read_bytes(),
            before,
        )

    def test_rejected_source_is_not_regenerated(self):
        wave = self.root / "docs" / "waves" / "1aaaa demo"
        wave.mkdir(parents=True)
        change_id = "1aaaak-feat demo"
        (wave / f"{change_id}.md").write_text(
            "# Demo\n\n"
            f"Change ID: `{change_id}`\n\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| --- | --- | --- | --- |\n"
            "| 2026-01-01 | Use `src/a.py` | grounded | none |\n",
            encoding="utf-8",
        )
        (wave / "wave.md").write_text(
            f"# Wave\n\nwave-id: `1aaaa demo`\n\nChange ID: `{change_id}`\n",
            encoding="utf-8",
        )
        created = self.srv.memory_propose_response(
            self.root, "1aaaa", "create"
        )
        mid = created["data"]["written"][0]["memory_id"]
        rejected = self._validate(
            mid, "reject", evidence_verified=False,
            current_target_verified=False, canonical_overlap="duplicates",
            action_delta="No memory action; the canonical contract owns the rule.",
        )
        self.assertEqual(rejected["status"], "ok", rejected)
        rerun = self.srv.memory_propose_response(
            self.root, "1aaaa", "dry_run"
        )
        self.assertEqual(rerun["data"]["records_proposed"], 0)
        self.assertEqual(rerun["data"]["skipped_dispositions"], 1)

    def test_close_diagnostics_require_candidate_and_verdict_but_allow_zero_memory(self):
        wave = self.root / "docs" / "waves" / "1valid validation"
        wave.mkdir(parents=True)
        change_id = "1validk-feat validation"
        (wave / f"{change_id}.md").write_text(
            "# Validation\n\n"
            f"Change ID: `{change_id}`\n\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| --- | --- | --- | --- |\n"
            "| 2026-01-01 | Use `src/a.py` | owns the durable boundary | none |\n",
            encoding="utf-8",
        )
        (wave / "wave.md").write_text(
            f"# Wave\n\nwave-id: `1valid validation`\n\nChange ID: `{change_id}`\n",
            encoding="utf-8",
        )
        (self.root / "src" / "a.py").write_text("value = 1\n", encoding="utf-8")

        missing = self.srv._memory_validation_diagnostics(self.root, "1valid")
        self.assertEqual(
            [item["code"] for item in missing],
            ["memory_validation_candidates_missing"],
        )
        created = self.srv.memory_propose_response(
            self.root, wave_id="1valid", mode="create"
        )
        memory_id = created["data"]["written"][0]["memory_id"]
        pending = self.srv._memory_validation_diagnostics(self.root, "1valid")
        self.assertEqual([item["code"] for item in pending], ["memory_validation_required"])
        with patch.object(
            self.srv, "run_validate",
            return_value={"passed": True, "errors": [], "warnings": []},
        ):
            close_pending = self.srv.wf_close_wave_response(
                self.root, "1valid", mode="dry_run"
            )
        self.assertIn(
            "memory_validation_required",
            [item["code"] for item in close_pending["diagnostics"]],
        )

        rejected = self._validate(
            memory_id,
            "reject",
            action_delta="Do not inject this already-owned rule into future work.",
            rationale="The canonical module contract already states the same boundary.",
            evidence_verified=False,
            current_target_verified=False,
            canonical_overlap="duplicates",
        )
        self.assertEqual(rejected["status"], "ok")
        self.assertEqual(self.srv._memory_validation_diagnostics(self.root, "1valid"), [])
        with patch.object(
            self.srv, "run_validate",
            return_value={"passed": True, "errors": [], "warnings": []},
        ):
            close_validated = self.srv.wf_close_wave_response(
                self.root, "1valid", mode="dry_run"
            )
        self.assertNotIn(
            "memory_validation_required",
            [item["code"] for item in close_validated["diagnostics"]],
        )

        empty = self.root / "docs" / "waves" / "1empty empty"
        empty.mkdir(parents=True)
        (empty / "wave.md").write_text(
            "# Wave\n\nwave-id: `1empty empty`\n",
            encoding="utf-8",
        )
        self.assertEqual(self.srv._memory_validation_diagnostics(self.root, "1empty"), [])


if __name__ == "__main__":
    unittest.main()
