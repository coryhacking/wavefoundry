"""Wave 1zv87 (1zv85): lifecycle tools never build a path from an unchecked change id.

``wf_close_change`` stat'ed and read ``<wave dir>/<change_id>.md`` for any id
(an existence and readability oracle), and ``wf_mark_ac`` / ``wf_mark_task``
rewrote a checkbox there. A malformed id is now refused before any path work,
the mark path requires admission, and close skips its document gates for an
unadmitted id.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from test_close_change import A, WAVE_ID, _CloseChangeCase, srv
from record_layout_support import RecordTreeBuilder

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
        for good in (A, "1200b-enh alpha.v2", "x..y"):
            with self.subTest(good=good):
                self.assertIsNone(srv._change_id_shape_error(good))


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
