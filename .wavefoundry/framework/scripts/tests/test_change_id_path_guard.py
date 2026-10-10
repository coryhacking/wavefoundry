"""Wave 1zv87 (1zv85): lifecycle tools never build a path from an unchecked change id.

``wf_close_change`` stat'ed and read ``<wave dir>/<change_id>.md`` for any id
(an existence and readability oracle), and ``wf_mark_ac`` / ``wf_mark_task``
rewrote a checkbox there. A malformed id is now refused before any path work,
the mark path requires admission, and close skips its document gates for an
unadmitted id.
"""
from __future__ import annotations

import builtins
import contextlib
import io
import json
import os
import re
import stat
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from test_close_change import A, WAVE_ID, _CloseChangeCase, srv
from record_layout_support import RecordTreeBuilder, default_profile_only

_OUTSIDE_DOC = (
    "# Outside\n\n## Acceptance Criteria\n\n- [ ] AC-1: Outside criterion.\n\n"
    "## Tasks\n\n- [ ] Outside task.\n"
)


class _GuardCase(_CloseChangeCase):
    def setUp(self) -> None:
        super().setUp()
        # The repository is a subdirectory, so a planted file sits OUTSIDE it.
        self.outer = self.root
        self.root = self.outer / "repo"
        (self.root / "docs").mkdir(parents=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
            encoding="utf-8",
        )
        self.builder = RecordTreeBuilder(self.root)
        self.wave([(A, "implemented")])
        self.outside = self.outer / "outside" / "secret.md"
        self.outside.parent.mkdir(parents=True)
        self.outside.write_bytes(_OUTSIDE_DOC.encode("utf-8"))
        rel = os.path.relpath(self.outside.with_suffix(""), self.wave_md.parent)
        self.traversal_ids = [rel.replace(os.sep, "/"), rel.replace(os.sep, "\\"), str(self.outside.with_suffix(""))]

    def mark(self, change_id: str, *, task: bool = False) -> dict:
        if task:
            return srv._mark_change_item_response(
                self.root, WAVE_ID[:5], change_id, "Outside task", "x", target_section="Tasks", mode="apply",
            )
        return srv._mark_change_item_response(
            self.root, WAVE_ID[:5], change_id, "AC-1", "x", target_section="Acceptance Criteria", mode="apply",
        )


class ChangeIdShapeTests(_GuardCase):
    def test_shape_check_refuses_without_filesystem_access(self) -> None:
        for bad in ("", "  ", "a/b", "a\\b", "..", "/abs/x", "\\\\server\\share", "C:x", "c:\\x", "a\x00b"):
            with self.subTest(bad=bad):
                with patch.object(Path, "is_file", side_effect=AssertionError("filesystem touched")):
                    diagnostic = srv._change_id_shape_error(bad)
                self.assertIsNotNone(diagnostic)
                self.assertEqual(diagnostic["code"], "invalid_arguments")
        for good in (A, "1200b-enh alpha-v2", "00000-task x"):
            with self.subTest(good=good):
                self.assertIsNone(srv._change_id_shape_error(good))
        # Wave 1zxo0 (1zxns): the allow-list closes the deny-list's gaps.
        for bad in ("1200b-enh alpha.v2", "x..y", "1200b-enh a\r\nb", "x:y", "CON", "abc. ", "."):
            with self.subTest(allow_list_bad=bad):
                diagnostic = srv._change_id_shape_error(bad)
                self.assertIsNotNone(diagnostic)
                self.assertEqual(diagnostic["code"], "invalid_arguments")
                if len(bad) > 3:
                    self.assertNotIn(bad, diagnostic["message"])


class CloseChangeOracleTests(_GuardCase):
    def test_traversal_and_absolute_ids_answer_the_same_whether_the_target_exists(self) -> None:
        for change_id in self.traversal_ids:
            with self.subTest(change_id=change_id):
                present = self.close(change_id, mode="dry_run")
                self.outside.rename(self.outside.with_suffix(".bak"))
                try:
                    absent = self.close(change_id, mode="dry_run")
                finally:
                    self.outside.with_suffix(".bak").rename(self.outside)
                self.assertEqual(self.codes(present), ["invalid_arguments"])
                self.assertEqual(present, absent)

    def test_unadmitted_well_formed_id_skips_the_document_gates(self) -> None:
        stray = "1200z-enh stray"
        (self.wave_md.parent / f"{stray}.md").write_bytes(b"\xff not utf-8")
        response = self.close(stray, mode="dry_run")
        codes = self.codes(response)
        self.assertIn("change_not_admitted", codes)
        self.assertNotIn("change_doc_missing", codes)
        self.assertNotIn("change_doc_unreadable", codes)
        missing = self.close("1200y-enh absent", mode="dry_run")
        self.assertIn("change_not_admitted", self.codes(missing))
        self.assertNotIn("change_doc_missing", self.codes(missing))

    def test_admitted_change_still_closes(self) -> None:
        response = self.close(A)
        self.assertEqual(response["status"], "ok", response)


class MarkItemPathTests(_GuardCase):
    def test_traversal_ids_are_refused_and_the_outside_file_is_untouched(self) -> None:
        before = self.outside.read_bytes()
        for change_id in self.traversal_ids:
            for task in (False, True):
                with self.subTest(change_id=change_id, task=task):
                    response = self.mark(change_id, task=task)
                    self.assertEqual(self.codes(response), ["invalid_arguments"], response)
                    self.assertEqual(self.outside.read_bytes(), before)

    def test_unadmitted_id_is_refused_before_a_path_is_built(self) -> None:
        stray = "1200z-enh stray"
        stray_doc = self.wave_md.parent / f"{stray}.md"
        stray_doc.write_bytes(_OUTSIDE_DOC.encode("utf-8"))
        built: list[str] = []
        real = srv._wave_change_doc_path

        def spy(root, wave_md, change_id):
            built.append(change_id)
            return real(root, wave_md, change_id)

        with patch.object(srv, "_wave_change_doc_path", side_effect=spy):
            response = self.mark(stray)
        self.assertEqual(self.codes(response), ["change_not_found"], response)
        self.assertNotIn(stray, built)
        self.assertEqual(stray_doc.read_bytes(), _OUTSIDE_DOC.encode("utf-8"))

    def test_admitted_change_is_still_marked(self) -> None:
        doc = self.doc(A)
        doc.write_text(doc.read_text(encoding="utf-8").replace("- [x] AC-1", "- [ ] AC-1"), encoding="utf-8")
        response = self.mark(A)
        self.assertEqual(response["status"], "ok", response)
        self.assertTrue(response["data"]["changed"])
        self.assertIn("- [x] AC-1", doc.read_text(encoding="utf-8"))



# --- Wave 1zxo0 (1zxns): change-id allow-list and member-doc containment ---

import lifecycle_gate_support as lgs  # noqa: E402
import record_paths  # noqa: E402
import vocabulary_profile as vp  # noqa: E402
from test_close_change import B, C, _doc_text, _member  # noqa: E402
from wave_lint_lib import constants as lint_constants  # noqa: E402

_MARKER = "zzsecretzz"
_BAD_PATH = f"../../outside/{_MARKER}"
_BAD_CTRL = f"1200x-enh {_MARKER}\nnext"
_BAD_SHAPE = f"1200x-Enh {_MARKER}"
_REJECTED_CLASSES = [
    "", "   ", "1200b-enh a\x00b", "1200b-enh a\nb", "1200b-enh a\rb", "1200b-enh a\tb",
    "1200b-enh a\x7fb", "1200b-enh a/b", "1200b-enh a\\b", "../1200b-enh alpha", ".", "..",
    "1200b-enh a:b", "C:x", "1200B-enh alpha", "1200b-Enh alpha", "1200b-enh Alpha",
    " 1200b-enh alpha", "1200b-enh alpha ", "1200b-enh alpha.", ".1200b-enh alpha",
    "CON", "NUL", "COM1", "LPT1", "enh alpha", "1200b alpha", "1200b-enh", "-enh alpha",
    "1200b- alpha", "1200b-enh  alpha",
]


@contextlib.contextmanager
def _filesystem_spy(marker: str):
    """Record every stat, lstat or open whose path argument contains ``marker``."""
    touched: list[str] = []

    def wrap(fn):
        def inner(*args, **kwargs):
            if args:
                try:
                    text = os.fspath(args[0])
                except TypeError:
                    text = ""
                if isinstance(text, bytes):
                    text = text.decode("utf-8", "replace")
                if isinstance(text, str) and marker in text:
                    touched.append(f"{getattr(fn, '__name__', fn)}:{text}")
            return fn(*args, **kwargs)
        return inner

    targets = [(os, "stat"), (os, "lstat"), (os, "open"), (io, "open"), (builtins, "open"),
               (os, "scandir"), (os, "listdir")]
    with contextlib.ExitStack() as stack:
        for module, name in targets:
            stack.enter_context(patch.object(module, name, wrap(getattr(module, name))))
        yield touched


class IsChangeIdTests(unittest.TestCase):
    """AC-1: the allow-list predicate."""

    def test_accepts_every_lint_id_for_every_kind(self) -> None:
        for kind in vp.CHANGE_KINDS:
            for prefix in ("1200b", "00000", "1zxns0"):
                value = f"{prefix}-{kind} some-slug-2"
                with self.subTest(value=value):
                    self.assertTrue(lgs.is_change_id(value))
                    line = f"{vp.MEMBER_ID_LABEL}: `{value}`"
                    self.assertIsNotNone(lint_constants.CHANGE_ID_PATTERN.match(line))

    def test_rejects_each_class(self) -> None:
        for value in [*_REJECTED_CLASSES, None, 12, b"1200b-enh alpha", ["1200b-enh alpha"]]:
            with self.subTest(value=value):
                self.assertFalse(lgs.is_change_id(value))

    def test_fragments_equal_the_lint_constants(self) -> None:
        self.assertEqual(lgs._CHANGE_ID_PREFIX_FRAGMENT, lint_constants.LIFECYCLE_PREFIX_PATTERN)
        self.assertEqual(lgs._CHANGE_ID_SLUG_FRAGMENT, lint_constants.SLUG_PATTERN)
        self.assertEqual(lgs._CHANGE_ID_KIND_SHAPE_FRAGMENT, vp._EXTRA_CHANGE_KIND_RE.pattern)

    @default_profile_only("this repository's admitted-ID corpus uses the shipped vocabulary and layout")
    def test_accepts_every_admitted_id_in_this_repository(self) -> None:
        repo = Path(__file__).resolve().parents[4]
        roots = record_paths.load_record_roots(repo)
        pattern = re.compile(rf"^{vp.MEMBER_ID_LABEL_RE}:\s+`([^`]+)`", re.MULTILINE)
        archive = vp.archive_profile()
        archive_pattern = re.compile(rf"^{archive.MEMBER_ID_LABEL_RE}:\s+`([^`]+)`", re.MULTILINE)
        ids: list[str] = []
        for directory in record_paths.discover_wave_dirs(repo, roots):
            record = directory / vp.RECORD_FILENAME
            if record.is_file():
                ids.extend(pattern.findall(record.read_text(encoding="utf-8")))
        for directory in record_paths.discover_archive_dirs(repo, roots):
            record = directory / archive.RECORD_FILENAME
            if record.is_file():
                ids.extend(archive_pattern.findall(record.read_text(encoding="utf-8")))
        self.assertGreater(len(ids), 100)
        rejected = [value for value in ids if not lgs.is_change_id(value)]
        self.assertEqual(rejected, [])


def _record_with(members: str) -> str:
    return f"# Wave Record\n\nStatus: active\n\n{vp.MEMBER_HEADING}\n\n{members}\n\n## Notes\n"


class PartitionAndExtractionTests(unittest.TestCase):
    """AC-2: extraction filters; rejections carry a line number and class only."""

    def setUp(self) -> None:
        self.text = _record_with("\n\n".join([
            _member(A, "implemented"),
            f"{vp.MEMBER_ID_LABEL}: `{_BAD_PATH}`\n{vp.MEMBER_STATUS_LABEL}: `planned`",
            f"{vp.MEMBER_ID_LABEL}: `{_BAD_CTRL}`",
            f"{vp.MEMBER_ID_LABEL}: `{_BAD_SHAPE}`",
            _member(B, "ready"),
        ]))

    def test_partition_reports_line_and_class_without_the_value(self) -> None:
        valid, rejected = lgs._partition_member_ids(self.text)
        self.assertEqual(valid, [A, B])
        lines = self.text.splitlines()
        self.assertEqual([entry["reason"] for entry in rejected], ["path character", "control character", "shape"])
        for entry in rejected:
            self.assertTrue(lines[entry["line"] - 1].startswith(f"{vp.MEMBER_ID_LABEL}:"))
            self.assertEqual(set(entry), {"line", "reason"})
            self.assertNotIn(_MARKER, json.dumps(entry))
        for diagnostic in lgs._change_id_invalid_diagnostics("docs/w/record.md", rejected):
            self.assertEqual(diagnostic["code"], "change_id_invalid")
            self.assertNotIn(_MARKER, diagnostic["message"])
            self.assertIsNone(re.search(r"[\x00-\x1f\x7f]", diagnostic["message"]))
            self.assertIn("by hand", diagnostic["message"])

    def test_extraction_and_close_gate_ids_are_allow_listed(self) -> None:
        self.assertEqual(lgs._extract_change_ids_from_wave_text(self.text), [A, B])
        self.assertEqual(lgs._close_gate_change_ids(self.text), [A, B])
        archive = vp.archive_profile()
        archived = self.text.replace(f"{vp.MEMBER_ID_LABEL}:", f"{archive.MEMBER_ID_LABEL}:")
        self.assertEqual(lgs._extract_change_ids_from_wave_text(archived, archive), [A, B])


class PathHelperAssertionTests(unittest.TestCase):
    """AC-3: the path helpers refuse before any filesystem call."""

    def test_helpers_raise_without_touching_the_filesystem(self) -> None:
        root = Path("/nonexistent-root")
        wave_md = root / "w" / vp.RECORD_FILENAME
        boom = AssertionError("filesystem touched")
        for value in _REJECTED_CLASSES:
            with self.subTest(value=value):
                with patch.object(os, "stat", side_effect=boom), patch.object(os, "lstat", side_effect=boom), \
                        patch.object(record_paths, "load_record_roots", side_effect=boom):
                    with self.assertRaises(lgs.ChangeIdRejected):
                        lgs._wave_change_doc_path(root, wave_md, value)
                    with self.assertRaises(lgs.ChangeIdRejected) as caught:
                        lgs._plan_change_doc_path(root, value)
                self.assertTrue(issubclass(lgs.ChangeIdRejected, ValueError))
                if value.strip():
                    self.assertNotIn(value, str(caught.exception))


class _BadLineCase(_GuardCase):
    """A wave with valid members and rejected member lines (one carries a status)."""

    def setUp(self) -> None:
        super().setUp()
        validate = patch.object(srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""})
        validate.start()
        self.addCleanup(validate.stop)
        garden = patch.object(srv, "run_garden", return_value={"passed": True})
        garden.start()
        self.addCleanup(garden.stop)
        self.wave([(A, "implemented"), (B, "ready"), (C, "ready")])
        text = self.wave_md.read_text(encoding="utf-8")
        a_block = _member(A, "implemented")
        b_block = _member(B, "ready")
        bad = "\n\n".join([
            f"{vp.MEMBER_ID_LABEL}: `{_BAD_PATH}`\n{vp.MEMBER_STATUS_LABEL}: `planned`",
            f"{vp.MEMBER_ID_LABEL}: `{_BAD_CTRL}`",
            f"{vp.MEMBER_ID_LABEL}: `{_BAD_SHAPE}`",
        ])
        self.assertIn(a_block, text)
        # Bad lines first, then A; B loses its status line (no positional shift).
        text = text.replace(a_block, bad + "\n\n" + a_block, 1)
        text = text.replace(b_block, f"{vp.MEMBER_ID_LABEL}: `{B}`", 1)
        self.wave_md.write_text(text, encoding="utf-8")
        self.text = text
        self.record_rel = self.wave_md.relative_to(self.root).as_posix()
        # A planted target for the traversal value, outside the repository.
        target = self.outer / "outside" / f"{_MARKER}.md"
        target.write_bytes(_OUTSIDE_DOC.encode("utf-8"))
        self.bad_line_numbers = [entry["line"] for entry in lgs._partition_member_ids(text)[1]]
        self.assertEqual(len(self.bad_line_numbers), 3)

    def invalid_diagnostics(self, response: dict) -> list[dict]:
        return [d for d in response.get("diagnostics") or [] if d["code"] == "change_id_invalid"]


class BadLineReaderTests(_BadLineCase):
    """AC-4: every reader returns structured output, never reads the bad line."""

    def test_readers_skip_the_rejected_lines(self) -> None:
        import dashboard_lib

        wid = WAVE_ID[:5]
        calls = {
            "wf_get_change": lambda: srv.wf_get_change_response(self.root, wave_id=wid),
            "wf_current_wave": lambda: srv.wf_current_wave_response(self.root),
            "wf_list_waves": lambda: srv.wf_list_waves_response(self.root),
            "_wave_code_footprint": lambda: srv._wave_code_footprint(self.root, self.wave_md),
            "_prepare_council_verdict_locations": lambda: srv._prepare_council_verdict_locations(
                self.root, self.wave_md, self.text, include_review_checkpoints=True),
            "_review_policy_receipt_diagnostics": lambda: srv._review_policy_receipt_diagnostics(
                self.root, self.wave_md, self.text),
            "_generate_wf_close_wave_summary": lambda: srv._generate_wf_close_wave_summary(
                WAVE_ID, self.text, self.wave_md, self.root),
            "wf_prepare_wave": lambda: srv.wf_prepare_wave_response(self.root, wid, "dry_run"),
            "wf_implement_wave": lambda: srv.wf_implement_wave_response(self.root, wid, "dry_run"),
            "wf_review_wave": lambda: srv.wf_review_wave_response(self.root, wid),
            "wf_close_wave": lambda: srv.wf_close_wave_response(self.root, wid, "dry_run"),
            "wf_audit": lambda: srv.wf_audit_response(self.root, wid),
            "list_waves": lambda: srv.list_waves(self.root),
            "_read_wave_record": lambda: srv._read_wave_record(self.root, self.wave_md),
            "collect_changes": lambda: dashboard_lib.collect_changes(self.root),
            "dashboard_snapshot": lambda: dashboard_lib.collect_dashboard_snapshot(self.root, skip_git=True),
        }
        for name, call in calls.items():
            with self.subTest(reader=name):
                with _filesystem_spy(_MARKER) as touched:
                    result = call()
                self.assertEqual(touched, [])
                blob = json.dumps(result, default=str)
                self.assertNotIn("Outside criterion", blob)
                # No surface echoes a rejected value.
                self.assertNotIn(_MARKER, blob)
                if name not in ("_wave_code_footprint", "_review_policy_receipt_diagnostics",
                                "_prepare_council_verdict_locations", "wf_implement_wave",
                                "wf_review_wave", "wf_close_wave"):
                    self.assertIn(A, blob)

    def test_each_member_keeps_its_own_status(self) -> None:
        record = srv._read_wave_record(self.root, self.wave_md)
        self.assertEqual(record["changes"], [
            {"id": A, "status": "implemented"},
            {"id": B, "status": "unknown"},
            {"id": C, "status": "ready"},
        ])


class BadLinePolicyTests(_BadLineCase):
    """AC-5: gates fail closed with ``change_id_invalid``; single-change tools are not blocked."""

    def assert_blocking(self, response: dict) -> None:
        self.assertEqual(response["status"], "error", response)
        invalid = self.invalid_diagnostics(response)
        self.assertEqual(len(invalid), 3, response)
        for diagnostic, line in zip(invalid, self.bad_line_numbers):
            self.assertIn(self.record_rel, diagnostic["message"])
            self.assertIn(f"line {line}", diagnostic["message"])
            self.assertIn("by hand", diagnostic["message"])
            self.assertNotIn(_MARKER, diagnostic["message"])
            self.assertFalse(diagnostic.get("advisory"))

    def test_close_gate_finding_shape(self) -> None:
        import lifecycle_gates

        findings = [f for f in lgs._collect_silent_unchecked_items_for_close(self.wave_md, self.text, self.root)
                    if f["item_type"] == "change id"]
        self.assertEqual([f["change_id"] for f in findings], ["", "", ""])
        self.assertEqual([f["item_text"] for f in findings], [str(n) for n in self.bad_line_numbers])
        ctx = lifecycle_gates.GateContext(self.root, self.wave_md, self.text, "dry_run", {}, "close")
        codes = [d["code"] for d in lifecycle_gates.close_checkbox_gate(ctx).diagnostics]
        self.assertEqual(codes.count("change_id_invalid"), 3)
        self.assertNotIn("silent_unchecked_items_at_close", codes)

    def test_phase_tools_block(self) -> None:
        wid = WAVE_ID[:5]
        self.assert_blocking(srv.wf_prepare_wave_response(self.root, wid, "dry_run"))
        self.assert_blocking(srv.wf_review_wave_response(self.root, wid))
        self.assert_blocking(srv.wf_review_wave_response(self.root, wid, phase="prepare"))
        self.assert_blocking(srv.wf_close_wave_response(self.root, wid, "dry_run"))
        status = self.wave_md.read_text(encoding="utf-8")
        self.wave_md.write_text(status.replace("Status: active", "Status: planned", 1), encoding="utf-8")
        implement = srv.wf_implement_wave_response(self.root, wid, "dry_run")
        self.assertEqual(implement["status"], "error", implement)
        self.assertEqual(len(self.invalid_diagnostics(implement)), 3, implement)

    def test_bulk_get_change_is_advisory(self) -> None:
        response = srv.wf_get_change_response(self.root, wave_id=WAVE_ID[:5])
        self.assertEqual(response["status"], "ok")
        invalid = self.invalid_diagnostics(response)
        self.assertEqual(len(invalid), 3)
        self.assertTrue(all(d.get("advisory") for d in invalid))
        self.assertEqual([c["id"] for c in response["data"]["changes"]], [A, B, C])

    def test_single_change_tools_are_not_blocked(self) -> None:
        doc = self.doc(A)
        doc.write_text(doc.read_text(encoding="utf-8").replace("- [x] AC-1", "- [ ] AC-1"), encoding="utf-8")
        marked = self.mark(A)
        self.assertEqual(marked["status"], "ok", marked)
        closed = self.close(A, mode="dry_run")
        self.assertNotIn("change_id_invalid", self.codes(closed))
        self.assertNotIn("silent_unchecked_items", self.codes(closed))


class ArgumentAndHeaderTests(_GuardCase):
    """AC-6: tool arguments and plan headers."""

    def test_arguments_in_every_class_are_refused(self) -> None:
        wid = WAVE_ID[:5]
        for value in _REJECTED_CLASSES:
            with self.subTest(value=value):
                self.assertEqual(self.codes(self.mark(value)), ["invalid_arguments"])
                self.assertEqual(self.codes(self.close(value, mode="dry_run")), ["invalid_arguments"])
                removed = srv.wf_remove_change_response(self.root, wid, value, mode="create")
                self.assertEqual(self.codes(removed), ["invalid_arguments"])
                if "1200" in value:
                    self.assertNotIn(json.dumps(value)[1:-1], json.dumps(removed))

    def test_add_change_refuses_a_plan_whose_header_is_not_a_change_id(self) -> None:
        plans = record_paths.load_record_roots(self.root).plans
        plans.mkdir(parents=True, exist_ok=True)
        stem = "1200q-enh bad-header"
        plan = plans / f"{stem}.md"
        body = _doc_text("1200q-enh Bad Header", "planned")
        plan.write_text(body, encoding="utf-8")
        before = self.wave_md.read_bytes()
        response = srv.wf_add_change_response(self.root, WAVE_ID[:5], stem, mode="create")
        self.assertEqual(self.codes(response), ["change_id_invalid"], response)
        self.assertNotIn("Bad Header", json.dumps(response))
        self.assertEqual(plan.read_text(encoding="utf-8"), body)
        self.assertEqual(self.wave_md.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.wave_md.parent.glob("1200q*")), [])


def _can_symlink(base: Path) -> bool:
    probe = base / ".symlink-probe"
    try:
        probe.symlink_to(base)
    except (OSError, NotImplementedError):
        return False
    probe.unlink()
    return True


# The known-good ``wave_review`` shape (the ``test_lifecycle_golden``
# ``_WAVE_REVIEW_CONFIG`` block): enabled with a delivery mode, so
# ``normalize_wave_review_policy`` accepts it and every reader reaches its
# member-doc read.
_MEMBER_DOC_WAVE_REVIEW = {"enabled": True, "delivery_mode": "targeted"}


class MemberDocContainmentTests(_GuardCase):
    """AC-7: a member doc that is a link or not a regular file is never read."""

    _INSIDE_TEXT = _doc_text(A, "implemented").replace("Fixture criterion", "Inside link target")

    def setUp(self) -> None:
        super().setUp()
        if not _can_symlink(self.outer):
            self.skipTest("symbolic links are unavailable")
        validate = patch.object(srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""})
        validate.start()
        self.addCleanup(validate.stop)
        config_path = self.root / "docs" / "workflow-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        # Change 200ex: a known-good literal, never the running checkout's
        # config, whose review policy a repository owns (and may not yet pass
        # validation before its upgrade writes one).
        config["wave_review"] = json.loads(json.dumps(_MEMBER_DOC_WAVE_REVIEW))
        config_path.write_text(json.dumps(config), encoding="utf-8")
        self.inside_target = self.root / "docs" / "inside-target.md"
        self.inside_target.write_text(self._INSIDE_TEXT, encoding="utf-8")
        self.outside.write_text(_doc_text(A, "implemented").replace("Fixture criterion", "Outside criterion"),
                                encoding="utf-8")

    def readers(self) -> dict:
        import dashboard_lib
        from wave_lint_lib.wave_validators import member_status_drift

        wid = WAVE_ID[:5]
        text = lambda: self.wave_md.read_text(encoding="utf-8")  # noqa: E731
        brief = lambda: lgs._build_prepare_council_brief(self.wave_md.parent.name, text(), [A], typed=True)  # noqa: E731
        return {
            "wf_get_change": lambda: srv.wf_get_change_response(self.root, wave_id=wid),
            "_mark_change_item_response": lambda: self.mark(A),
            "_prepare_policy_state": lambda: srv._prepare_policy_state(self.root, self.wave_md, text(), [A], brief()),
            "_prepare_council_verdict_locations": lambda: srv._prepare_council_verdict_locations(
                self.root, self.wave_md, text(), include_review_checkpoints=True),
            "_wave_code_footprint": lambda: srv._wave_code_footprint(self.root, self.wave_md),
            "wf_implement_wave": lambda: srv.wf_implement_wave_response(self.root, wid, "dry_run"),
            "_generate_wf_close_wave_summary": lambda: self._summary(text()),
            "_collect_silent_unchecked_items_for_close": lambda: lgs._collect_silent_unchecked_items_for_close(
                self.wave_md, text(), self.root),
            "wf_close_change": lambda: self.close(A, mode="dry_run"),
            "wf_prepare_wave": lambda: srv.wf_prepare_wave_response(self.root, wid, "dry_run"),
            "collect_changes": lambda: dashboard_lib.collect_changes(self.root),
            "member_status_drift": lambda: member_status_drift(text(), self.wave_md.parent, root=self.root),
        }

    def _summary(self, text: str):
        try:
            return srv._generate_wf_close_wave_summary(WAVE_ID, text, self.wave_md, self.root)
        except ValueError as exc:
            return str(exc)

    def clear_doc(self) -> None:
        doc = self.doc(A)
        if doc.is_dir() and not doc.is_symlink():
            doc.rmdir()
        elif os.path.lexists(doc):
            doc.unlink()

    def replace_doc(self, kind: str) -> None:
        doc = self.doc(A)
        doc.unlink()
        if kind == "link-outside":
            doc.symlink_to(self.outside)
        elif kind == "link-inside":
            doc.symlink_to(self.inside_target)
        elif kind == "directory":
            doc.mkdir()

    def test_links_and_directories_are_never_read(self) -> None:
        for kind in ("link-outside", "link-inside", "directory"):
            with self.subTest(kind=kind):
                self.clear_doc()
                self.wave([(A, "implemented")])
                self.replace_doc(kind)
                for name, call in self.readers().items():
                    with self.subTest(reader=name):
                        try:
                            result = call()
                        except (OSError, ValueError) as exc:
                            result = repr(exc)
                        blob = json.dumps(result, default=str)
                        self.assertNotIn("Outside criterion", blob)
                        self.assertNotIn("Inside link target", blob)
                self.assertEqual(self.inside_target.read_text(encoding="utf-8"), self._INSIDE_TEXT)

    def test_every_member_doc_read_goes_through_the_helper(self) -> None:
        self.wave([(A, "implemented")])
        doc = self.doc(A)
        helper_calls: list[str] = []
        real_helper = lgs._read_member_doc_bytes

        def helper_spy(folder, path, *, root):
            helper_calls.append(Path(path).name)
            return real_helper(folder, path, root=root)

        def forbid(fn):
            def inner(self_path, *args, **kwargs):
                # Docs-lint's general reads of the docs tree are out of scope
                # (they run only after the member doc passed the helper).
                caller = sys._getframe(1).f_code.co_filename.replace("\\", "/")
                if Path(self_path).name == doc.name and "/wave_lint_lib/" not in caller:
                    raise AssertionError(f"unconfined read of {doc.name}")
                return fn(self_path, *args, **kwargs)
            return inner

        readers = self.readers()
        with patch.object(lgs, "_read_member_doc_bytes", side_effect=helper_spy) as support_spy, \
                patch.object(srv, "_read_member_doc_bytes", side_effect=helper_spy) as server_spy, \
                patch.object(Path, "read_text", forbid(Path.read_text)), \
                patch.object(Path, "read_bytes", forbid(Path.read_bytes)):
            for name, call in readers.items():
                with self.subTest(reader=name):
                    helper_calls.clear()
                    call()
                    self.assertIn(doc.name, helper_calls)
        self.assertTrue(support_spy.called)
        self.assertTrue(server_spy.called)

    def test_wave_folder_links(self) -> None:
        # Inside the repository: still reads.
        real = self.root / "docs" / "real-wave"
        real.mkdir()
        (real / f"{A}.md").write_text(_doc_text(A, "implemented"), encoding="utf-8")
        inside_link = self.root / "docs" / "linked-wave"
        inside_link.symlink_to(real, target_is_directory=True)
        data = lgs._read_member_doc_bytes(inside_link, inside_link / f"{A}.md", root=self.root)
        self.assertIn(b"Fixture criterion", data)
        # Outside the repository: refused, nothing read.
        away = self.outer / "away-wave"
        away.mkdir()
        (away / f"{A}.md").write_text(_doc_text(A, "implemented"), encoding="utf-8")
        outside_link = self.root / "docs" / "away-link"
        outside_link.symlink_to(away, target_is_directory=True)
        with patch.object(os, "read", side_effect=AssertionError("read")):
            with self.assertRaises(lgs.MemberDocRefused):
                lgs._read_member_doc_bytes(outside_link, outside_link / f"{A}.md", root=self.root)

    def test_add_change_refuses_a_linked_staged_plan_before_any_move(self) -> None:
        plans = record_paths.load_record_roots(self.root).plans
        plans.mkdir(parents=True, exist_ok=True)
        stem = "1200r-enh staged"
        plan = plans / f"{stem}.md"
        target = self.outer / "outside" / "staged-target.md"
        target_body = _doc_text(stem, "planned").replace("Fixture criterion", "Outside criterion")
        target.write_text(target_body, encoding="utf-8")
        plan.symlink_to(target)
        before = self.wave_md.read_bytes()
        response = srv.wf_add_change_response(self.root, WAVE_ID[:5], stem, mode="create")
        self.assertIn("change_doc_unreadable", self.codes(response), response)
        self.assertTrue(plan.is_symlink())
        self.assertFalse(os.path.lexists(self.wave_md.parent / f"{stem}.md"))
        self.assertEqual(target.read_text(encoding="utf-8"), target_body)
        self.assertEqual(self.wave_md.read_bytes(), before)
        self.assertNotIn("Outside criterion", json.dumps(response))

    def test_prepare_refuses_a_linked_staged_doc_before_any_move(self) -> None:
        patcher = patch.object(srv, "run_garden", return_value={"passed": True})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.wave([(A, "ready")])
        doc = self.doc(A)
        doc.unlink()
        plans = record_paths.load_record_roots(self.root).plans
        plans.mkdir(parents=True, exist_ok=True)
        staged = plans / f"{A}.md"
        staged.symlink_to(self.outside)
        outside_before = self.outside.read_bytes()
        response = srv.wf_prepare_wave_response(self.root, WAVE_ID[:5], "ready")
        self.assertIn("change_doc_unreadable", self.codes(response), response)
        self.assertTrue(staged.is_symlink())
        self.assertFalse(os.path.lexists(doc))
        self.assertEqual(self.outside.read_bytes(), outside_before)
        self.assertNotIn("Outside criterion", json.dumps(response))


class BulkExactLookupTests(_GuardCase):
    """AC-8: bulk ``wf_get_change`` resolves each member by exact name."""

    def test_substring_sibling_staged_member_and_subfolders(self) -> None:
        shorter, longer, staged, nested = "1200c-enh bravo", "1200c-enh bravo-two", "1200s-enh staged", "1200t-enh nested"
        self.wave([(shorter, "ready"), (longer, "ready"), (staged, "ready"), (nested, "ready")])
        self.doc(shorter).write_text(_doc_text(shorter, "ready").replace("Fixture change.", "Shorter doc."), encoding="utf-8")
        self.doc(longer).write_text(_doc_text(longer, "ready").replace("Fixture change.", "Longer doc."), encoding="utf-8")
        plans = record_paths.load_record_roots(self.root).plans
        plans.mkdir(parents=True, exist_ok=True)
        self.doc(staged).rename(plans / f"{staged}.md")
        sub = self.wave_md.parent / "sub"
        sub.mkdir()
        self.doc(nested).rename(sub / f"{nested}.md")
        response = srv.wf_get_change_response(self.root, wave_id=WAVE_ID[:5])
        by_id = {c["id"]: c for c in response["data"]["changes"]}
        self.assertIn("Shorter doc.", by_id[shorter]["content"])
        self.assertIn("Longer doc.", by_id[longer]["content"])
        self.assertEqual(by_id[staged]["path"], (plans / f"{staged}.md").relative_to(self.root).as_posix())
        self.assertIsNone(by_id[nested]["path"])
        self.assertIsNone(by_id[nested]["content"])


class MemberDocReaderUnitTests(unittest.TestCase):
    """AC-16: non-blocking refusal of non-regular files, a counted cap, one read."""

    def setUp(self) -> None:
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.folder = self.root / "wave"
        self.folder.mkdir()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX only")
    def test_fifo_is_refused_without_blocking(self) -> None:
        fifo = self.folder / f"{A}.md"
        os.mkfifo(fifo)
        with patch.object(os, "open", side_effect=AssertionError("opened")):
            with self.assertRaises(lgs.MemberDocRefused):
                lgs._read_member_doc_bytes(self.folder, fifo, root=self.root)

    def test_cap_is_enforced_by_read_count(self) -> None:
        doc = self.folder / f"{A}.md"
        doc.write_bytes(b"x" * 64)
        # inert-by-design: patches a size constant, not a callable; nothing is called.
        with patch.object(lgs, "MEMBER_DOC_MAX_BYTES", 16):
            with self.assertRaises(lgs.MemberDocRefused):
                lgs._read_member_doc_bytes(self.folder, doc, root=self.root)
            doc.write_bytes(b"x" * 16)
            self.assertEqual(lgs._read_member_doc_bytes(self.folder, doc, root=self.root), b"x" * 16)

    def test_growth_after_lstat_is_still_refused(self) -> None:
        doc = self.folder / f"{A}.md"
        doc.write_bytes(b"x" * 8)
        real_lstat = os.lstat

        def lstat_then_grow(path, *args, **kwargs):
            result = real_lstat(path, *args, **kwargs)
            if Path(path) == doc:
                doc.write_bytes(b"x" * 64)
            return result

        requested: list[int] = []
        real_read = os.read

        def counting_read(fd, size):
            requested.append(size)
            return real_read(fd, size)

        # inert-by-design: patches a size constant, not a callable; nothing is called.
        with patch.object(lgs, "MEMBER_DOC_MAX_BYTES", 16), patch.object(os, "lstat", side_effect=lstat_then_grow), \
                patch.object(os, "read", side_effect=counting_read):
            with self.assertRaises(lgs.MemberDocRefused):
                lgs._read_member_doc_bytes(self.folder, doc, root=self.root)
        if hasattr(os, "O_NOFOLLOW"):
            self.assertLessEqual(sum(requested), 17)

    def test_wrong_folder_and_outside_root_are_refused(self) -> None:
        doc = self.folder / f"{A}.md"
        doc.write_text("x", encoding="utf-8")
        with self.assertRaises(lgs.MemberDocRefused):
            lgs._read_member_doc_bytes(self.root, doc, root=self.root)
        other = self.root / "other"
        other.mkdir()
        with self.assertRaises(lgs.MemberDocRefused):
            lgs._read_member_doc_bytes(self.folder, doc, root=other)
        self.assertIsInstance(lgs.MemberDocRefused("x"), OSError)

    def test_parse_change_doc_with_text_reads_nothing(self) -> None:
        import dashboard_lib

        doc = self.folder / f"{A}.md"
        with patch.object(Path, "read_text", side_effect=AssertionError("read")):
            record = dashboard_lib.parse_change_doc(self.root, doc, text=_doc_text(A, "ready"))
        self.assertEqual(record.change_id, A)


class UnstableIdLintMessageTests(_GuardCase):
    """AC-16 (lint): the unstable-id messages carry a line number and class, never the value."""

    def test_messages_omit_the_value(self) -> None:
        text = self.wave_md.read_text(encoding="utf-8")
        a_block = _member(A, "implemented")
        bell = f"1200x-enh {_MARKER}\x07y"
        text = text.replace(a_block, a_block + f"\n\n{vp.MEMBER_ID_LABEL}: `{bell}`\n"
                            f"{vp.MEMBER_STATUS_LABEL}: `planned`\n\nItem ID: `{_MARKER}\x07x`\n", 1)
        self.wave_md.write_text(text, encoding="utf-8")
        lines = text.splitlines()
        member_line = next(i for i, line in enumerate(lines, 1) if bell in line)
        item_line = next(i for i, line in enumerate(lines, 1) if line.startswith("Item ID:"))
        all_failures = self.lint()
        failures = [f for f in all_failures if "unstable" in f]
        self.assertTrue(any(f"on line {member_line} (control character)" in f for f in failures), failures)
        self.assertTrue(any(f"Item ID on line {item_line} (control character)" in f for f in failures), failures)
        for failure in failures:
            self.assertNotIn(_MARKER, failure)
            self.assertNotIn("\x07", failure)


# --- Wave 1zxo0 (1zxns) delivery repairs: staged-plan enumeration, the
# post-open identity check, the runtime-lock hard-link rule and the lint loop ---

import threading  # noqa: E402

_FIFO_TIMEOUT = 10.0


def _call_with_fifo_guard(test: unittest.TestCase, fifo: Path, fn):
    """Run ``fn`` in a thread; if it is still blocked after ``_FIFO_TIMEOUT``
    seconds, open the FIFO's write end (unblocking a reader stuck in ``open``)
    and fail, so a regression fails the test instead of hanging the suite."""
    outcome: dict = {}

    def run() -> None:
        try:
            outcome["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised on the test thread
            outcome["error"] = exc

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(_FIFO_TIMEOUT)
    if worker.is_alive():
        try:
            fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            fd = None
        if fd is not None:
            os.close(fd)
        worker.join(_FIFO_TIMEOUT)
        test.fail(f"blocked on a FIFO for more than {_FIFO_TIMEOUT} seconds")
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


class StagedPlanEnumerationTests(_GuardCase):
    """DEL-1: ``list_plans`` and the dashboard plan rows read staged plans
    under the member-doc rule, so a link or a FIFO is reported, never read."""

    _HEADING = f"# {_MARKER} heading"

    def setUp(self) -> None:
        super().setUp()
        self.plans = record_paths.load_record_roots(self.root).plans
        self.plans.mkdir(parents=True, exist_ok=True)
        self.good_stem = "1200p-enh good-plan"
        (self.plans / f"{self.good_stem}.md").write_text(_doc_text(self.good_stem, "planned"), encoding="utf-8")
        self.outside.write_text(f"{self._HEADING}\n\n{vp.MEMBER_ID_LABEL}: `1200q-enh {_MARKER}`\n",
                                encoding="utf-8")

    def readers(self) -> dict:
        import dashboard_lib

        return {
            "list_plans": lambda: srv.list_plans(self.root),
            "wf_list_plans": lambda: srv.wf_list_plans_response(self.root),
            "collect_changes": lambda: dashboard_lib.collect_changes(self.root),
        }

    def assert_reported_not_read(self, entry: Path, result, name: str) -> None:
        blob = json.dumps(result, default=str)
        self.assertNotIn(_MARKER, blob, name)
        self.assertNotIn(str(self.outer), blob, name)
        self.assertIn(self.good_stem, blob, name)
        if name == "list_plans":
            row = next(r for r in result if r["path"].endswith(entry.name))
            self.assertEqual(row["title"], entry.stem)
            self.assertIn("read_error", row)

    def test_a_linked_staged_plan_is_reported_without_its_target(self) -> None:
        if not _can_symlink(self.outer):
            self.skipTest("symbolic links are unavailable")
        entry = self.plans / "1200z-enh linked-plan.md"
        entry.symlink_to(self.outside)
        for name, call in self.readers().items():
            with self.subTest(reader=name):
                self.assert_reported_not_read(entry, call(), name)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX only")
    def test_a_fifo_staged_plan_does_not_block(self) -> None:
        entry = self.plans / "1200z-enh fifo-plan.md"
        os.mkfifo(entry)
        for name, call in self.readers().items():
            with self.subTest(reader=name):
                result = _call_with_fifo_guard(self, entry, call)
                self.assert_reported_not_read(entry, result, name)


class MemberDocPostOpenIdentityTests(unittest.TestCase):
    """DEL-2: an entry swapped between the ``lstat`` and the open is refused by
    the post-open ``fstat`` check (regular file with the ``lstat`` identity)."""

    def setUp(self) -> None:
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.folder = self.root / "wave"
        self.folder.mkdir()
        self.doc = self.folder / f"{A}.md"
        self.doc.write_text("original\n", encoding="utf-8")
        # A second name keeps the original inode alive, so the swapped-in
        # file can never reuse its identity.
        self.keep = self.root / "keep.md"
        os.link(self.doc, self.keep)

    def _swap_after_first_lstat(self, swap):
        real_lstat = os.lstat
        state = {"swapped": False}

        def lstat_then_swap(path, *args, **kwargs):
            result = real_lstat(path, *args, **kwargs)
            if not state["swapped"] and Path(path) == self.doc:
                state["swapped"] = True
                swap()
            return result

        return patch.object(os, "lstat", side_effect=lstat_then_swap)

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "the post-open identity check is POSIX only")
    def test_a_regular_file_swapped_in_is_refused(self) -> None:
        def swap() -> None:
            replacement = self.folder / "replacement.tmp"
            replacement.write_text(f"{_MARKER}\n", encoding="utf-8")
            os.replace(replacement, self.doc)

        with self._swap_after_first_lstat(swap):
            with self.assertRaises(lgs.MemberDocRefused) as caught:
                lgs._read_member_doc_bytes(self.folder, self.doc, root=self.root)
        self.assertIn("changed", str(caught.exception))
        self.assertNotIn(_MARKER, str(caught.exception))

    @unittest.skipUnless(hasattr(os, "mkfifo") and hasattr(os, "O_NOFOLLOW"), "FIFOs are POSIX only")
    def test_a_fifo_swapped_in_is_refused_without_blocking(self) -> None:
        def swap() -> None:
            self.doc.unlink()
            os.mkfifo(self.doc)

        def call():
            with self._swap_after_first_lstat(swap):
                with self.assertRaises(lgs.MemberDocRefused):
                    lgs._read_member_doc_bytes(self.folder, self.doc, root=self.root)

        _call_with_fifo_guard(self, self.doc, call)


class MemberDocRuntimeLockLinkTests(unittest.TestCase):
    """DEL-3: a member doc hard-linked to a runtime lock is refused, and the
    member-doc rule and the server's runtime-lock rule agree."""

    _LOCK_BODY = f"{_MARKER} lock body\n".encode("utf-8")

    def setUp(self) -> None:
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.folder = self.root / "docs" / "wave"
        self.folder.mkdir(parents=True)
        lock_dir = self.root / ".wavefoundry" / "index"
        lock_dir.mkdir(parents=True)
        self.lock = lock_dir / "index-build.lock"
        self.lock.write_bytes(self._LOCK_BODY)
        self.doc = self.folder / f"{A}.md"
        try:
            os.link(self.lock, self.doc)
        except (OSError, NotImplementedError):
            self.skipTest("hard links are unavailable")
        self.plain = self.folder / f"{B}.md"
        self.plain.write_text(_doc_text(B, "ready"), encoding="utf-8")

    def test_a_hard_link_to_a_lock_is_refused_unread(self) -> None:
        with self.assertRaises(lgs.MemberDocRefused) as caught:
            lgs._read_member_doc_bytes(self.folder, self.doc, root=self.root)
        self.assertIn("runtime lock", str(caught.exception))
        self.assertNotIn(_MARKER, str(caught.exception))
        self.assertEqual(self.lock.read_bytes(), self._LOCK_BODY)
        # An ordinary member doc beside it still reads.
        self.assertIn(B.encode("utf-8"), lgs._read_member_doc_bytes(self.folder, self.plain, root=self.root))

    def test_member_doc_rule_and_server_rule_agree(self) -> None:
        self.assertEqual(srv._runtime_lock_identities(self.root), lgs.runtime_lock_identities(self.root))
        for path, expected in ((self.doc, True), (self.plain, False)):
            with self.subTest(path=path.name):
                self.assertEqual(lgs._runtime_lock_identity_match(self.root, os.lstat(path)), expected)
                self.assertEqual(srv._is_runtime_lock_path(self.root, path), expected)



class SingleIdChangeLookupTests(_GuardCase):
    """Wave 200xy (200v1) AC-5 and AC-6: the single-id change lookup reads each
    candidate through the member-doc rule, after the runtime-lock check."""

    _STEM = "1200s-enh looked-up"

    def setUp(self) -> None:
        super().setUp()
        self.plans = record_paths.load_record_roots(self.root).plans
        self.plans.mkdir(parents=True, exist_ok=True)
        self.entry = self.plans / f"{self._STEM}.md"

    def resource_change(self):
        import types as _types

        from declaration_support import RecordingFastMCP

        recorder = RecordingFastMCP()
        handler = _types.SimpleNamespace(root=self.root, cache=None)
        srv.register_mcp_surface(recorder, lambda: handler)
        return recorder.resource_functions["resource_change"]

    def _single(self) -> dict:
        return srv.wf_get_change_response(self.root, change_id=self._STEM)

    def _assert_unreadable(self, response: dict, *forbidden: str) -> None:
        blob = json.dumps(response, default=str)
        self.assertEqual(response["status"], "error", response)
        self.assertIn("change_doc_unreadable", self.codes(response), response)
        [match] = srv._resolve_change_doc_matches(self.root, self._STEM)
        self.assertEqual(match["content"], "")
        self.assertNotIn("refused", match)
        self.assertNotIn("/", match["read_error"])
        self.assertNotIn(str(self.outer), match["read_error"])
        for text in forbidden:
            self.assertNotIn(text, blob)

    def test_a_linked_change_doc_is_an_unreadable_match(self) -> None:
        if not _can_symlink(self.outer):
            self.skipTest("symbolic links are unavailable")
        inside = self.root / "docs" / "inside-target.md"
        inside.write_text(_doc_text(self._STEM, "planned").replace("Fixture criterion", "Inside criterion"),
                          encoding="utf-8")
        self.outside.write_text(_doc_text(self._STEM, "planned").replace("Fixture criterion", "Outside criterion"),
                                encoding="utf-8")
        resource = self.resource_change()
        for label, target, marker in (("inside", inside, "Inside criterion"),
                                      ("outside", self.outside, "Outside criterion")):
            with self.subTest(target=label):
                if os.path.lexists(self.entry):
                    self.entry.unlink()
                self.entry.symlink_to(target)
                with self.subTest(caller="wf_get_change"):
                    self._assert_unreadable(self._single(), marker, str(target))
                with self.subTest(caller="get_change"):
                    self.assertIsNone(srv.get_change(self.root, self._STEM))
                with self.subTest(caller="resource_change"):
                    text = resource(self._STEM)
                    self.assertTrue(text.startswith("# Unreadable Change"), text)
                    self.assertNotIn(marker, text)
                    self.assertNotIn(str(target), text)
                    self.assertNotIn(str(self.outer), text)

    def test_a_refused_linked_doc_matches_only_its_own_token(self) -> None:
        # The member-doc refusal branch still filters by token: a linked doc is an
        # unreadable match for its own id and no match at all for an unrelated one.
        if not _can_symlink(self.outer):
            self.skipTest("symbolic links are unavailable")
        self.outside.write_text(_doc_text(self._STEM, "planned"), encoding="utf-8")
        self.entry.symlink_to(self.outside)
        [match] = srv._resolve_change_doc_matches(self.root, self._STEM)
        self.assertEqual(match["content"], "")
        self.assertEqual(srv._resolve_change_doc_matches(self.root, "1zzzz-bug unrelated"), [])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX only")
    def test_a_fifo_candidate_does_not_block(self) -> None:
        os.mkfifo(self.entry)
        response = _call_with_fifo_guard(self, self.entry, self._single)
        self._assert_unreadable(response)

    def test_an_ordinary_document_is_returned_as_before(self) -> None:
        body = _doc_text(self._STEM, "planned").replace("\n", "\r\n")
        self.entry.write_bytes(body.encode("utf-8"))
        response = self._single()
        expected = self.entry.read_text(encoding="utf-8")
        self.assertEqual(response["status"], "ok", response)
        self.assertEqual(response["data"]["change"]["content"], expected)
        [match] = srv._resolve_change_doc_matches(self.root, self._STEM)
        self.assertEqual(match, {
            "path": self.entry.relative_to(self.root).as_posix(),
            "change_id": self._STEM,
            "content": expected,
        })
        self.assertEqual(self.resource_change()(self._STEM), expected)

    def test_symlinked_and_hard_linked_locks_are_refused_unopened(self) -> None:
        lock_dir = self.root / ".wavefoundry" / "index"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock = lock_dir / "index-build.lock"
        lock.write_bytes(f"{_MARKER} lock body\n".encode("utf-8"))
        kinds = []
        if _can_symlink(self.outer):
            kinds.append("symlink")
        kinds.append("hard link")
        resource = self.resource_change()
        for kind in kinds:
            with self.subTest(kind=kind):
                if os.path.lexists(self.entry):
                    self.entry.unlink()
                try:
                    if kind == "symlink":
                        self.entry.symlink_to(lock)
                    else:
                        os.link(lock, self.entry)
                except (OSError, NotImplementedError):
                    self.skipTest("hard links are unavailable")
                opened: list[str] = []
                real_open, real_os_open = builtins.open, os.open

                def spy_open(path, *args, **kwargs):
                    opened.append(os.path.realpath(os.fspath(path)) if not isinstance(path, int) else "")
                    return real_open(path, *args, **kwargs)

                def spy_os_open(path, *args, **kwargs):
                    opened.append(os.path.realpath(os.fspath(path)))
                    return real_os_open(path, *args, **kwargs)

                with patch.object(builtins, "open", spy_open), patch.object(os, "open", spy_os_open):
                    [match] = srv._resolve_change_doc_matches(self.root, self._STEM)
                    text = resource(self._STEM)
                self.assertTrue(match.get("refused"), match)
                self.assertEqual(match["content"], "")
                self.assertTrue(text.startswith("# Refused"), text)
                self.assertNotIn(os.path.realpath(lock), opened)
                self.assertNotIn(_MARKER, json.dumps(match) + text)
        # The member-doc rule's own lock-identity refusal (reached when the
        # path check does not see the lock, as in a swap between the two) is
        # also ``refused``.
        if os.path.lexists(self.entry):
            self.entry.unlink()
        try:
            os.link(lock, self.entry)
        except (OSError, NotImplementedError):
            return
        with patch.object(srv, "_refuse_runtime_lock_target", lambda root, path: None):
            [match] = srv._resolve_change_doc_matches(self.root, self._STEM)
        self.assertTrue(match.get("refused"), match)
        self.assertIn("runtime lock", match["read_error"])

    def test_add_change_on_a_linked_change_doc_changes_nothing(self) -> None:
        if not _can_symlink(self.outer):
            self.skipTest("symbolic links are unavailable")
        self.outside.write_text(_doc_text(self._STEM, "planned").replace("Fixture criterion", "Outside criterion"),
                                encoding="utf-8")
        self.entry.symlink_to(self.outside)

        def snapshot() -> dict:
            return {
                path.relative_to(self.root).as_posix(): (
                    os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None)
                for path in sorted(self.root.rglob("*"))
            }

        before = snapshot()
        response = srv.wf_add_change_response(self.root, WAVE_ID[:5], self._STEM, mode="create")
        self.assertEqual(response["status"], "error", response)
        self.assertEqual(snapshot(), before)
        self.assertNotIn("Outside criterion", json.dumps(response))
        self.assertNotIn(str(self.outside), json.dumps(response))

    def test_the_uncalled_unique_resolver_is_gone(self) -> None:
        self.assertFalse(hasattr(srv, "_resolve_unique_change_doc"))

class WaveOwnedDocLintGuardTests(_GuardCase):
    """DEL-5: docs-lint never reads a member doc that is not a regular file.
    Wave 200xy (200v1): the refusal goes through the per-run registry, so the
    docs-lint entry point reports it once, by the entry's own path and a cause
    class, never by a target or anything read from one."""

    def _lint(self) -> list[str]:
        """Run the docs-lint entry point in process; return its stderr lines."""
        from wave_lint_lib import cli

        err = io.StringIO()
        with patch.dict(os.environ, {"PROJECT_ROOT": str(self.root)}), \
                patch.object(sys, "argv", ["docs_lint.py"]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            cli.main()
        return err.getvalue().splitlines()

    def _failures_for(self, lines: list[str], doc: Path) -> list[str]:
        rel = doc.relative_to(self.root).as_posix()
        return [line for line in lines if line.startswith("ERROR: ") and rel in line]

    def _expected(self, doc: Path) -> str:
        return (f"ERROR: {doc.relative_to(self.root).as_posix()}: record document refused "
                "(a link or special file); it was not read. Replace it with the document itself.")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX only")
    def test_a_fifo_member_doc_is_reported_without_blocking(self) -> None:
        doc = self.doc(A)
        doc.unlink()
        os.mkfifo(doc)
        lines = _call_with_fifo_guard(self, doc, self._lint)
        hits = self._failures_for(lines, doc)
        self.assertEqual(hits, [self._expected(doc)], lines)

    def test_a_linked_member_doc_is_reported_without_its_target(self) -> None:
        if not _can_symlink(self.outer):
            self.skipTest("symbolic links are unavailable")
        self.outside.write_text(_doc_text(A, "implemented").replace("# Fixture", f"# {_MARKER}"),
                                encoding="utf-8")
        doc = self.doc(A)
        doc.unlink()
        doc.symlink_to(self.outside)
        lines = self._lint()
        hits = self._failures_for(lines, doc)
        self.assertEqual(hits, [self._expected(doc)], lines)
        for line in lines:
            self.assertNotIn(_MARKER, line)
            self.assertNotIn(str(self.outside), line)
