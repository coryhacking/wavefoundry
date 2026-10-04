"""Wave 1zlu1 (change 1zlu2): ``wf_close_change`` closes one admitted change
inside an OPEN wave and moves the dependents its close unblocks to ``ready``.

Fixtures are written in the loaded vocabulary profile (labels, record file
name, member heading and waves root come from ``vocabulary_profile`` and
``record_paths``), so a ``run_tests.py --profile second`` run exercises the
same assertions under renamed labels (AC-7).
"""
from __future__ import annotations

import hashlib
import json
import threading
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from server_tools_support import load_server
from record_layout_support import RecordTreeBuilder
import vocabulary_profile as vp

srv = load_server()

WAVE_ID = "1200a close-change"
A = "1200b-enh alpha"
B = "1200c-enh bravo"
C = "1200d-enh charlie"
D = "1200e-enh delta"
E = "1200f-enh echo"
F = "1200g-enh foxtrot"
G = "1200h-enh golf"
H = "1200i-enh hotel"


def _member(change_id: str, status: str, *, previous: "str | None" = None, depends_on: "tuple[str, ...]" = ()) -> str:
    lines = [f"{vp.MEMBER_ID_LABEL}: `{change_id}`"]
    if previous:
        lines.append(f"{vp.PREVIOUS_STATUS_LABEL}: `{previous}`")
    lines.append(f"{vp.MEMBER_STATUS_LABEL}: `{status}`")
    if depends_on:
        lines.append("Depends On: " + ", ".join(f"`{d}`" for d in depends_on))
    return "\n".join(lines)


def _doc_text(change_id: str, status: str, *, ac: str = "x", task: str = "x", extra_header: str = "",
              last_verified: bool = True) -> str:
    verified = "Last verified: 2026-03-21\n" if last_verified else ""
    return (
        f"# Fixture\n\n{vp.MEMBER_ID_LABEL}: `{change_id}`\n{vp.MEMBER_STATUS_LABEL}: `{status}`\n"
        f"{extra_header}Owner: Engineering\nStatus: {status}\n{verified}Wave: {WAVE_ID}\n\n"
        "## Rationale\n\nFixture change.\n\n"
        f"## Acceptance Criteria\n\n- [{ac}] AC-1: Fixture criterion.\n\n"
        f"## Tasks\n\n- [{task}] Do the fixture task.\n\n"
        "## AC Priority\n\n| AC | Priority |\n|----|----------|\n| AC-1 | required |\n"
    )


class _CloseChangeCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
            encoding="utf-8",
        )
        self.builder = RecordTreeBuilder(self.root)
        # The post-write lint attachment spawns docs-lint; it is not under test.
        patcher = patch.object(srv, "_attach_lint_to_response", side_effect=lambda envelope, *a, **k: envelope)
        patcher.start()
        self.addCleanup(patcher.stop)
        refresh = patch.object(srv, "_trigger_background_index_refresh_for_paths", return_value={})
        refresh.start()
        self.addCleanup(refresh.stop)

    def wave(self, members: "list[tuple]", *, status: str = "active", docs: "dict[str, str] | None" = None) -> Path:
        """``members`` are ``(change_id, status, previous, depends_on)``;
        ``docs`` overrides a change document's text."""
        text = self.builder.container_text(WAVE_ID, [], title="Fixture", status=status, vocab=self.builder.live)
        blocks = "\n\n".join(
            _member(m[0], m[1], previous=m[2] if len(m) > 2 else None, depends_on=m[3] if len(m) > 3 else ())
            for m in members
        )
        heading = f"{vp.MEMBER_HEADING}\n\n"
        text = text.replace(heading, heading + blocks + "\n", 1)
        self.builder.waves_readme()
        directory = self.builder.waves_dir / WAVE_ID
        directory.mkdir(parents=True, exist_ok=True)
        self.wave_md = vp.record_file(directory)
        self.wave_md.write_text(text, encoding="utf-8")
        (directory / "events.jsonl").write_text("", encoding="utf-8")
        for member in members:
            body = (docs or {}).get(member[0], _doc_text(member[0], member[1]))
            (directory / f"{member[0]}.md").write_text(body, encoding="utf-8")
        return self.wave_md

    def doc(self, change_id: str) -> Path:
        return self.wave_md.parent / f"{change_id}.md"

    def close(self, change_id: str = A, mode: str = "create") -> dict:
        return srv.wf_close_change_response(self.root, WAVE_ID[:5], change_id, mode=mode)

    def snapshot(self) -> dict[str, bytes]:
        return {p.name: p.read_bytes() for p in sorted(self.wave_md.parent.iterdir()) if p.is_file()}

    def block_status(self, change_id: str) -> "tuple[str | None, str | None]":
        from wave_lint_lib.wave_validators import _parse_change_records

        record = {r.record_id: r for r in _parse_change_records(self.wave_md.read_text(encoding="utf-8"), "")}[change_id]
        return record.previous_status, record.status

    def doc_statuses(self, change_id: str) -> "tuple[str | None, str | None]":
        import re

        text = self.doc(change_id).read_text(encoding="utf-8")
        member = re.search(rf"(?m)^{vp.MEMBER_STATUS_LABEL_RE}:\s+`([^`]+)`", text)
        plain = re.search(r"(?m)^Status:\s+(\S+)", text)
        return (member.group(1) if member else None), (plain.group(1) if plain else None)

    def lint(self) -> list[str]:
        from wave_lint_lib import helpers, wave_validators
        from wave_lint_lib.metadata_validators import check_metadata

        helpers.read_text_cache_clear()
        failures = list(wave_validators.check_wave_docs(self.root))
        for path in sorted(self.wave_md.parent.glob("*.md")):
            failures.extend(check_metadata(self.root, path))
        return failures

    @staticmethod
    def codes(response: dict) -> list[str]:
        return [d["code"] for d in response.get("diagnostics") or []]


class CloseChangeWriteTests(_CloseChangeCase):
    """AC-1: the core write, in both files, with lint passing."""

    def test_closes_ready_active_and_review_changes(self) -> None:
        for status in ("ready", "active", "review"):
            with self.subTest(status=status):
                self.setUp()
                self.wave([(A, status, "active" if status == "review" else "planned"), (B, "complete", "planned")])
                self.assertEqual(self.lint(), [])
                dry = self.close(mode="dry_run")
                self.assertEqual(dry["status"], "dry_run", dry)
                before = self.snapshot()
                self.assertEqual(self.snapshot(), before)
                result = self.close()
                self.assertEqual(result["status"], "ok", result)
                self.assertEqual(self.block_status(A), (status, "complete"))
                self.assertEqual(self.doc_statuses(A), ("complete", "complete"))
                self.assertNotIn(vp.PREVIOUS_STATUS_LABEL, self.doc(A).read_text(encoding="utf-8"))
                self.assertEqual(result["data"]["previous_status"], status)
                self.assertEqual(result["data"]["status"], "complete")
                self.assertEqual(sorted(result["data"]["written"]), sorted(dry["data"]["planned_writes"]))
                self.assertEqual(dry["data"]["written"], [])
                self.assertEqual(self.lint(), [])

    def test_dry_run_writes_nothing(self) -> None:
        self.wave([(A, "active", "planned"), (B, "planned", None, (A,))])
        before = self.snapshot()
        result = self.close(mode="dry_run")
        self.assertEqual(result["status"], "dry_run", result)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual([a["change_id"] for a in result["data"]["activated"]], [B])

    def test_implemented_change_closes_with_previous_implemented(self) -> None:
        self.wave([(A, "implemented")])
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(self.block_status(A), ("implemented", "complete"))
        self.assertEqual(self.lint(), [])

    def test_existing_previous_line_is_replaced(self) -> None:
        self.wave([(A, "review", "active")])
        self.assertEqual(self.close()["status"], "ok")
        text = self.wave_md.read_text(encoding="utf-8")
        self.assertEqual(text.count(f"{vp.PREVIOUS_STATUS_LABEL}:"), 1)
        self.assertEqual(self.block_status(A), ("review", "complete"))

    def test_apply_is_an_alias_and_unknown_mode_is_refused(self) -> None:
        self.wave([(A, "active")])
        bad = self.close(mode="write")
        self.assertEqual(self.codes(bad), ["invalid_arguments"])
        self.assertEqual(bad["data"]["valid_modes"], ["dry_run", "create"])
        self.assertEqual(self.close(mode="apply")["status"], "ok")

    def test_crlf_documents_keep_their_line_endings(self) -> None:
        self.wave([(A, "active", "planned")])
        for path in (self.wave_md, self.doc(A)):
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(self.close()["status"], "ok")
        for path in (self.wave_md, self.doc(A)):
            raw = path.read_bytes()
            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""), path.name)


class CloseChangeGateTests(_CloseChangeCase):
    """AC-2: each gate refuses with its own diagnostic and writes nothing."""

    def assert_refused(self, code: str, change_id: str = A) -> dict:
        before = self.snapshot()
        for mode in ("dry_run", "create"):
            result = self.close(change_id, mode=mode)
            self.assertEqual(result["status"], "error", result)
            self.assertIn(code, self.codes(result), result)
            self.assertEqual(self.snapshot(), before, f"{mode} wrote")
        return result

    def test_wave_not_open(self) -> None:
        for status in ("planned", "closed"):
            with self.subTest(status=status):
                self.setUp()
                self.wave([(A, "active")], status=status)
                self.assert_refused("wave_not_open")

    def test_change_not_admitted(self) -> None:
        self.wave([(A, "active")])
        self.assert_refused("change_not_admitted", change_id="1200z-enh stranger")

    def test_change_doc_missing(self) -> None:
        self.wave([(A, "active")])
        self.doc(A).unlink()
        self.assert_refused("change_doc_missing")

    def test_status_not_closable(self) -> None:
        for status in ("planned", "blocked", "complete", "landed"):
            with self.subTest(status=status):
                self.setUp()
                self.wave([(A, status)])
                self.assert_refused("change_status_not_closable")

    def test_status_drift(self) -> None:
        self.wave([(A, "active")], docs={A: _doc_text(A, "review")})
        self.assert_refused("change_status_drift")

    def test_silent_unchecked_ac_and_task(self) -> None:
        for ac, task in ((" ", "x"), ("x", " ")):
            with self.subTest(ac=ac, task=task):
                self.setUp()
                self.wave([(A, "active")], docs={A: _doc_text(A, "active", ac=ac, task=task)})
                result = self.assert_refused("silent_unchecked_items")
                diagnostic = next(d for d in result["diagnostics"] if d["code"] == "silent_unchecked_items")
                self.assertIn("wf_mark_ac", diagnostic["recovery_tools"])
                self.assertIn("wf_mark_task", diagnostic["recovery_tools"])

    def test_open_item_in_another_change_does_not_block(self) -> None:
        self.wave([(A, "active"), (B, "active")], docs={B: _doc_text(B, "active", ac=" ", task=" ")})
        self.assertEqual(self.close()["status"], "ok")

    def test_non_done_and_out_of_wave_dependency(self) -> None:
        self.wave([(A, "active", None, (B,)), (B, "active")])
        self.assert_refused("dependencies_not_done")
        self.setUp()
        self.wave([(A, "ready", None, ("1200z-enh elsewhere",))])
        self.assert_refused("dependencies_not_done")

    def test_implemented_dependency_is_done(self) -> None:
        self.wave([(A, "active", None, (B,)), (B, "implemented")])
        self.assertEqual(self.close()["status"], "ok")

    def test_dry_run_lists_every_failing_gate(self) -> None:
        self.wave([(A, "planned", None, (B,)), (B, "active")], status="planned",
                  docs={A: _doc_text(A, "active", ac=" ")})
        result = self.close(mode="dry_run")
        self.assertEqual(
            set(self.codes(result)),
            {"wave_not_open", "change_status_not_closable", "change_status_drift",
             "silent_unchecked_items", "dependencies_not_done"},
        )

    def test_closable_set_comes_from_the_lint_constants(self) -> None:
        from wave_lint_lib import constants as lint_constants

        self.assertEqual(srv._close_change_closable_statuses(), frozenset({"ready", "active", "review", "implemented"}))
        narrowed = {k: (v - {"complete"} if k == "implemented" else v)
                    for k, v in lint_constants.ALLOWED_CHANGE_STATUS_TRANSITIONS.items()}
        with patch.object(lint_constants, "ALLOWED_CHANGE_STATUS_TRANSITIONS", narrowed):
            self.assertNotIn("implemented", srv._close_change_closable_statuses())


class CloseChangeActivationTests(_CloseChangeCase):
    """AC-3: only dependents whose Depends On names the closed change."""

    def members(self, e_status: str) -> "list[tuple]":
        return [
            (A, "active", "planned"),
            (B, "planned", None, (A,)),
            (C, "blocked", "planned", (A,)),
            (D, "planned", None, (A, E)),
            (E, e_status),
            (F, "planned"),
            (H, "complete", "planned"),
            (G, "planned", None, (H,)),
        ]

    def test_activation_scope(self) -> None:
        self.wave(self.members("planned"))
        untouched = {name: self.doc(name).read_bytes() for name in (D, F, G)}
        wave_before = self.wave_md.read_text(encoding="utf-8")
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        activated = {a["change_id"]: a["previous_status"] for a in result["data"]["activated"]}
        self.assertEqual(activated, {B: "planned", C: "blocked"})
        self.assertEqual(self.block_status(B), ("planned", "ready"))
        self.assertEqual(self.block_status(C), ("blocked", "ready"))
        self.assertEqual(self.doc_statuses(B), ("ready", "ready"))
        self.assertEqual(self.doc_statuses(C), ("ready", "ready"))
        not_activated = {n["change_id"]: n["reason"] for n in result["data"]["not_activated"]}
        self.assertEqual(not_activated, {D: "dependencies_not_done"})
        for name in (D, F, G):
            self.assertEqual(self.doc(name).read_bytes(), untouched[name], name)
            self.assertNotIn(name, activated)
        wave_after = self.wave_md.read_text(encoding="utf-8")
        shapes = {D: {"depends_on": (A, E)}, F: {}, G: {"depends_on": (H,)}}
        for name in (D, F, G):
            block = _member(name, "planned", **shapes[name])
            self.assertIn(block, wave_before)
            self.assertIn(block, wave_after, name)
        self.assertNotIn("`active`", "\n".join(
            line for line in wave_after.splitlines() if line.startswith(f"{vp.MEMBER_STATUS_LABEL}:")))
        self.assertEqual(self.lint(), [])

    def test_implemented_co_dependency_activates(self) -> None:
        self.wave(self.members("implemented"))
        result = self.close()
        activated = {a["change_id"] for a in result["data"]["activated"]}
        self.assertEqual(activated, {B, C, D})
        self.assertEqual(self.lint(), [])

    def test_ready_dependent_is_not_rewritten(self) -> None:
        self.wave([(A, "active"), (B, "ready", None, (A,))])
        before = self.doc(B).read_bytes()
        result = self.close()
        self.assertEqual(result["data"]["not_activated"][0]["reason"], "status_not_activatable")
        self.assertEqual(self.doc(B).read_bytes(), before)

    def test_change_doc_only_dependency_is_reported_not_activated(self) -> None:
        legacy = _doc_text(B, "planned", extra_header=f"Depends On: `{A}`\n")
        self.wave([(A, "active"), (B, "planned")], docs={B: legacy})
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["data"]["activated"], [])
        self.assertIn("dependencies_not_in_wave_record", self.codes(result))
        self.assertEqual(self.doc_statuses(B)[0], "planned")


class CloseChangeLintRollbackTests(_CloseChangeCase):
    """AC-4: an introduced lint failure restores every written file."""

    def test_introduced_failure_rolls_back(self) -> None:
        from wave_lint_lib import wave_validators

        self.wave([(A, "active", "planned"), (B, "planned", None, (A,))])
        before = self.snapshot()
        original = wave_validators.check_wave_docs

        def strict(root, only=None, skip=None, warnings=None):
            failures = original(root, only=only, skip=skip, warnings=warnings)
            if f"{vp.MEMBER_STATUS_LABEL}: `complete`" in self.doc(A).read_text(encoding="utf-8"):
                failures.append(f"{srv._repo_rel(self.root, self.doc(A))}: fixture rule refuses `complete`")
            return failures

        with patch.object(wave_validators, "check_wave_docs", strict):
            result = self.close()
        self.assertEqual(result["status"], "error", result)
        self.assertEqual(self.codes(result), ["close_change_lint_failed"])
        self.assertEqual(self.snapshot(), before)

    def test_preexisting_failure_does_not_roll_back(self) -> None:
        self.wave([(A, "active", "planned")], docs={A: _doc_text(A, "active", last_verified=False)})
        self.assertTrue(any("Last verified" in f for f in self.lint()))
        dry = self.close(mode="dry_run")
        self.assertEqual(dry["status"], "dry_run", dry)
        self.assertIn("close_change_lint_preexisting", self.codes(dry))
        self.assertTrue(all(d.get("advisory") for d in dry["diagnostics"]))
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(self.doc_statuses(A)[0], "complete")


class CloseChangeReviewNeutralityTests(_CloseChangeCase):
    """AC-5: the review-policy digest does not move; no ledger event."""

    def digest(self) -> str:
        from review_policy import policy_input_snapshot

        changes = []
        for path in sorted(self.wave_md.parent.glob("*.md")):
            if path.name == vp.RECORD_FILENAME:
                continue
            changes.append((path.stem, path.stem.split(" ", 1)[0].split("-", 1)[1], path.read_bytes()))
        return policy_input_snapshot(wave_review={}, project_lanes=(), review_policies={},
                                     changes=changes, requested_lanes=())[0]

    def test_digest_is_unchanged_and_no_event_is_written(self) -> None:
        self.wave([(A, "active", "planned"), (B, "planned", None, (A,))])
        events = self.wave_md.parent / "events.jsonl"
        before, events_before = self.digest(), events.read_bytes()
        self.assertEqual(self.close()["status"], "ok")
        self.assertEqual(self.digest(), before)
        self.assertEqual(events.read_bytes(), events_before)

    def test_previous_line_in_the_change_doc_would_move_the_digest(self) -> None:
        self.wave([(A, "active", "planned")])
        before = self.digest()
        path = self.doc(A)
        text = path.read_text(encoding="utf-8")
        status_line = f"{vp.MEMBER_STATUS_LABEL}: `active`\n"
        path.write_text(text.replace(status_line, f"{vp.PREVIOUS_STATUS_LABEL}: `active`\n" + status_line, 1),
                        encoding="utf-8")
        self.assertNotEqual(self.digest(), before)


class CloseChangeRegistrationTests(unittest.TestCase):
    """AC-6: serialized, decorated and registered like the other lifecycle writers."""

    def test_registries(self) -> None:
        import mcp_tool_roster
        import publication_control

        self.assertIn("wf_close_change", srv._LIFECYCLE_MUTATION_LOCK_TOOLS)
        self.assertEqual(mcp_tool_roster.TOOL_TIERS["wf_close_change"], mcp_tool_roster.TIER_WRITE)
        writer = {w.tool_name: w for w in publication_control.PUBLICATION_WRITER_REGISTRY}["wf_close_change"]
        self.assertEqual((writer.producer, writer.contention_policy), ("lifecycle", "fail_fast"))

    def test_record_layout_refusal_is_structured(self) -> None:
        import record_paths

        with patch.object(srv, "_find_wave_md_detailed",
                          side_effect=record_paths.RecordLayoutInvalid(["record_layout_invalid: fixture"])):
            result = srv.wf_close_change_response(Path("."), "x", A)
        self.assertEqual(result["status"], "error")
        self.assertIn("record_layout_invalid", json.dumps(result))

    def test_busy_lifecycle_lock_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wavefoundry").mkdir()
            called: list = []
            tool = SimpleNamespace(fn=lambda **kw: called.append(kw))
            mcp = SimpleNamespace(_tool_manager=SimpleNamespace(_tools={"wf_close_change": tool}))
            srv._wrap_lifecycle_mutation_lock(mcp, lambda: SimpleNamespace(root=root))
            held, release = threading.Event(), threading.Event()

            def holder() -> None:
                with srv._lifecycle_mutation_lock(root):
                    held.set()
                    release.wait(timeout=10)

            thread = threading.Thread(target=holder)
            thread.start()
            try:
                self.assertTrue(held.wait(timeout=10))
                result = tool.fn(wave_id="x", change_id=A, mode="create")
            finally:
                release.set()
                thread.join(timeout=10)
            self.assertEqual(called, [])
            self.assertEqual(result["status"], "error")
            self.assertTrue(result["data"]["busy"])


class FencedDependsOnTests(_CloseChangeCase):
    """Wave 1zoju (1zogm): a `Depends On:` line inside a closed fenced block is
    an example, not a declaration; a fenced status line is still read."""

    def fence_after(self, change_id: str, body: str, *, closer: str = "```") -> None:
        """Insert a fenced block holding ``body`` after ``change_id``'s status line."""
        text = self.wave_md.read_text(encoding="utf-8")
        lines = text.split("\n")
        start = lines.index(f"{vp.MEMBER_ID_LABEL}: `{change_id}`")
        status = next(i for i in range(start, len(lines)) if lines[i].startswith(f"{vp.MEMBER_STATUS_LABEL}:"))
        block = ["", "```text", *body.split("\n")] + ([closer] if closer else []) + [""]
        lines[status + 1:status + 1] = block
        self.wave_md.write_text("\n".join(lines), encoding="utf-8")

    def lint_with_warnings(self) -> "tuple[list[str], list[str]]":
        from wave_lint_lib import helpers, wave_validators

        helpers.read_text_cache_clear()
        warnings: list[str] = []
        failures = list(wave_validators.check_wave_docs(self.root, warnings=warnings))
        return failures, warnings

    def test_fenced_dependency_does_not_activate(self) -> None:
        """AC-1: closing A leaves B (fenced dependency only) `planned`."""
        self.wave([(A, "active", "planned"), (B, "planned")])
        self.fence_after(B, f"Depends On: `{A}`")
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["data"]["activated"], [])
        self.assertEqual(self.block_status(B), (None, "planned"))
        self.assertEqual(self.doc_statuses(B), ("planned", "planned"))

    def test_fenced_dependency_lints_clean_with_a_warning(self) -> None:
        """AC-2: no dependency or syntax failure; the warning names B's line."""
        self.wave([(A, "active", "planned"), (B, "ready", "planned")])
        self.fence_after(B, f"Depends On: `{A}`\nDepends On: {A}")
        failures, warnings = self.lint_with_warnings()
        self.assertEqual([f for f in failures if "Depends On" in f or "depend" in f], [], failures)
        fenced = [w for w in warnings if "inside a fenced block" in w]
        self.assertEqual(len(fenced), 2, warnings)
        for warning in fenced:
            self.assertIn(f"under `{B}`", warning)
            self.assertIn("is not read as a dependency", warning)

    def test_unfenced_dependency_still_gates_and_unterminated_fence_is_read(self) -> None:
        """AC-3: an unterminated fence leaves the line read as a dependency."""
        self.wave([(A, "active", "planned"), (B, "planned")])
        self.fence_after(B, f"Depends On: `{A}`", closer="")
        from wave_lint_lib.wave_validators import _parse_change_records

        records = {r.record_id: r for r in _parse_change_records(self.wave_md.read_text(encoding="utf-8"), "")}
        self.assertEqual(records[B].depends_on, [A])
        _failures, warnings = self.lint_with_warnings()
        self.assertEqual([w for w in warnings if "inside a fenced block" in w], [])
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual([a["change_id"] for a in result["data"]["activated"]], [B])

    def test_fenced_status_line_still_keeps_a_record_open(self) -> None:
        """AC-4: the 1zlu0 fail-closed status reading survives."""
        self.wave([(A, "complete", "active")])
        self.fence_after(A, f"{vp.MEMBER_STATUS_LABEL}: `active`")
        text = self.wave_md.read_text(encoding="utf-8")
        self.assertEqual(srv._close_open_work_records(text), [(A, "active")])
        with patch.object(srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}), \
             patch.object(srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            response = srv.wf_close_wave_response(self.root, WAVE_ID[:5], mode="dry_run")
        self.assertEqual(response["status"], "error", response)
        self.assertIn("open_changes_remaining", self.codes(response))

    def test_every_reader_sees_the_same_dependency_set(self) -> None:
        """AC-6: the record parser, the implement-wave parser and the close
        path agree. A fenced ``## `` line sits before C's unfenced dependency,
        so a fence-unaware section split would drop it."""
        from wave_lint_lib.wave_validators import _parse_change_records

        self.wave([(A, "active", "planned"), (B, "planned"), (C, "planned", None, (A,)),
                   (D, "planned", None, (A, E)), (E, "complete", "planned")])
        self.fence_after(B, f"## Example heading\nDepends On: `{A}`")
        self.fence_after(D, f"Depends On: `{E}`, `{A}`")
        text = self.wave_md.read_text(encoding="utf-8")
        self.assertIn("## Example heading", text.split(f"{vp.MEMBER_ID_LABEL}: `{C}`")[0])
        expected = {C: [A], D: [A, E]}
        records = {r.record_id: r.depends_on for r in _parse_change_records(text, "") if r.depends_on}
        self.assertEqual(records, expected)
        self.assertEqual(srv._wave_member_dependencies(text), expected)
        result = self.close(mode="dry_run")
        # Repair F1: the close path activates exactly the unfenced dependents,
        # including C after the fenced `## ` line.
        self.assertEqual([a["change_id"] for a in result["data"]["activated"]], [C, D])
        self.assertEqual(result["data"]["not_activated"], [])

    def test_the_close_path_reads_each_unfenced_dependency_once(self) -> None:
        """AC-6 (reverification R1): with E still open, the close path names
        E as D's only unmet dependency, once, so a dropped or fenced-duplicated
        dependency is visible."""
        self.wave([(A, "active", "planned"), (B, "planned"), (C, "planned", None, (A,)),
                   (D, "planned", None, (A, E)), (E, "planned")])
        self.fence_after(B, f"## Example heading\nDepends On: `{A}`")
        self.fence_after(D, f"Depends On: `{E}`, `{A}`")
        result = self.close(mode="dry_run")
        self.assertEqual([a["change_id"] for a in result["data"]["activated"]], [C])
        not_activated = result["data"]["not_activated"]
        self.assertEqual([entry["change_id"] for entry in not_activated], [D])
        self.assertEqual(not_activated[0]["reason"], "dependencies_not_done")
        self.assertEqual(not_activated[0]["dependencies"], [E])

    def test_fenced_heading_after_a_member_does_not_end_the_member_list(self) -> None:
        """Repair F1: a fenced ``## `` line after B leaves C's block readable,
        so closing A activates C."""
        self.wave([(A, "active", "planned"), (B, "planned"), (C, "planned", None, (A,))])
        self.fence_after(B, "## Example heading")
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual([a["change_id"] for a in result["data"]["activated"]], [C])
        self.assertEqual(self.block_status(C), ("planned", "ready"))

    def test_fenced_member_heading_example_does_not_start_the_member_list(self) -> None:
        """Repair F1: a fenced member-heading example above the real heading
        is not the member list, so A is still admitted."""
        self.wave([(A, "active", "planned"), (B, "planned", None, (A,))])
        text = self.wave_md.read_text(encoding="utf-8")
        example = f"```text\n{vp.MEMBER_HEADING}\n\nAn example only.\n```\n\n"
        self.wave_md.write_text(text.replace(f"{vp.MEMBER_HEADING}\n", example + f"{vp.MEMBER_HEADING}\n", 1),
                                encoding="utf-8")
        self.assertEqual(self.wave_md.read_text(encoding="utf-8").count(vp.MEMBER_HEADING), 2)
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        self.assertNotIn("change_not_admitted", self.codes(result))
        self.assertEqual([a["change_id"] for a in result["data"]["activated"]], [B])

    def test_admission_never_inserts_inside_a_fence(self) -> None:
        """Repair F1: `wf_add_change`'s insertion ignores fenced headings, both
        a fenced ``## `` line inside the member list and a fenced member-heading
        example above it."""
        import change_doc_checklist

        member = f"{vp.MEMBER_ID_LABEL}: `{A}`\n{vp.MEMBER_STATUS_LABEL}: `planned`\n"
        cases = {
            "fenced_end": (f"# Wave\n\n{vp.MEMBER_HEADING}\n\n{member}\n```text\n## Example\n```\n\n"
                           "## Watchpoints\n\n- w\n"),
            "fenced_start": (f"# Wave\n\n```text\n{vp.MEMBER_HEADING}\n```\n\n{vp.MEMBER_HEADING}\n\n{member}\n"
                             "## Watchpoints\n\n- w\n"),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                out = srv._insert_change_block_into_changes_section(text, B)
                lines = out.split("\n")
                flags = change_doc_checklist.fenced_line_flags(lines)
                index = lines.index(f"{vp.MEMBER_ID_LABEL}: `{B}`")
                self.assertFalse(flags[index], out)
                self.assertLess(index, lines.index("## Watchpoints"), out)
                self.assertGreater(index, lines.index(f"{vp.MEMBER_ID_LABEL}: `{A}`"), out)

    def test_fenced_change_doc_dependency_is_not_a_legacy_declaration(self) -> None:
        """Requirement 2: the close-change legacy reader skips fenced lines."""
        legacy = _doc_text(B, "planned", extra_header=f"\n```text\nDepends On: `{A}`\n```\n\n")
        self.wave([(A, "active"), (B, "planned")], docs={B: legacy})
        result = self.close()
        self.assertEqual(result["status"], "ok", result)
        self.assertNotIn("dependencies_not_in_wave_record", self.codes(result))

    def test_crlf_record_reads_the_same(self) -> None:
        """Requirement 5: LF and CRLF records read the same."""
        self.wave([(A, "active", "planned"), (B, "planned"), (C, "planned", None, (A,))])
        self.fence_after(B, f"## Example heading\nDepends On: `{A}`")
        text = self.wave_md.read_text(encoding="utf-8")
        self.assertEqual(srv._wave_member_dependencies(text.replace("\n", "\r\n")),
                         srv._wave_member_dependencies(text))
        self.assertEqual(srv._wave_member_dependencies(text), {C: [A]})


class CloseWaveCompletedChangeTests(unittest.TestCase):
    """Requirement 8: wave close treats a closed change as finished."""

    def test_complete_change_is_not_open_at_wave_close(self) -> None:
        text = f"{vp.MEMBER_HEADING}\n\n" + _member(A, "complete", previous="active") + "\n"
        self.assertEqual(srv._close_open_work_records(text), [])


if __name__ == "__main__":
    unittest.main()
