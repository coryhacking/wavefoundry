"""Wave 244in (change 244fj) AC-1, AC-3 and AC-4: lifecycle writers keep a
wave record's and a spec's own line endings.

One public lifecycle (create, admit, Prepare, review events, implement, pause
with its handoff, reopen, close change, close wave, reopen) runs on LF, CRLF
and mixed records, natively and under the shared Windows-write simulation.
After every mutating step each document must be exactly its LF content in the
input's shape: LF stays LF, CRLF stays CRLF, and a mixed file (first line LF,
the rest CRLF) keeps its LF first line while every other line, inserted ones
included, is CRLF.  No step may write ``\\r\\r\\n``.

The oracle is ``shape(to_lf(output)) == output``: it pins every byte of every
line ending, while the content of each step is pinned by the lifecycle suites.
"""

from __future__ import annotations

import contextlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from declaration_support import RecordingFastMCP
from line_ending_support import CRLF, LF, mixed, windows_text_writes, with_endings
from server_tools_support import (
    _make_repo, close_container, create_container, declared_wave_doc_gates, integrity_checks,
    load_server, review_policy_config,
)
import vocabulary_profile as vp

SHAPES = {
    "lf": lambda text: text,
    "crlf": lambda text: with_endings(text, CRLF),
    "mixed": mixed,
}


def _to_lf(data: bytes) -> str:
    return data.decode("utf-8").replace(CRLF, LF)


class LifecycleLineEndingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = _make_repo(Path(tmp.name)).resolve()
        config_path = root / "docs/workflow-config.json"
        config = json.loads(config_path.read_text())
        config["wave_review"] = review_policy_config()
        config_path.write_text(json.dumps(config))
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stubs = {
            "run_validate": lambda *a, **k: {"passed": True, "errors": [], "warnings": [], "output": ""},
            "run_garden": lambda *a, **k: {"passed": True, "files_updated": 0, "updated": [], "output": ""},
            "_run_post_write_lint": lambda *a, **k: {"mode": "stubbed"},
            "_trigger_background_index_refresh_for_paths": lambda *a, **k: None,
        }
        stack.enter_context(declared_wave_doc_gates(self.srv, stubs))
        for name in ("_regenerate_codebase_map_safe", "_auto_populate_memory_for_wave",
                     "_maybe_optimize_index_on_close"):
            stack.enter_context(patch.object(self.srv, name, return_value={}))
        telemetry = MagicMock()
        telemetry.focus = SimpleNamespace(wave_id="", stage="general")
        telemetry.record_workflow.return_value = {}
        handler = SimpleNamespace(root=root, cache=None, telemetry=telemetry)
        mcp = RecordingFastMCP()
        self.srv.register_mcp_surface(mcp, lambda: handler)
        return root, (lambda name, **kwargs: mcp._tool_manager._tools[name].fn(**kwargs))

    def ok(self, result):
        self.assertEqual(result["status"], "ok", result)
        return result["data"]

    def assert_shape(self, shape, path: Path, step: str):
        data = path.read_bytes()
        with self.subTest(step=step, path=path.name):
            self.assertNotIn(b"\r\r\n", data)
            self.assertEqual(data, SHAPES[shape](_to_lf(data)).encode("utf-8"))

    def reshape(self, shape, path: Path):
        path.write_bytes(SHAPES[shape](_to_lf(path.read_bytes())).encode("utf-8"))

    @staticmethod
    def replace_bytes(path: Path, old: str, new: str):
        data = path.read_bytes()
        assert old.encode() in data, old
        path.write_bytes(data.replace(old.encode(), new.encode()))

    def spec_text(self, cid):
        # ``Wave: TBD`` exercises the admission back-reference repair (AC-3);
        # the missing blank line before ``## Tasks`` exercises Prepare's
        # heading-spacing fix, which inserts a line.
        return (
            f"# Line ending fixture\n\n{vp.MEMBER_ID_LABEL}: `{cid}`\n"
            f"{vp.MEMBER_STATUS_LABEL}: `planned`\nOwner: Engineering\nStatus: planned\n"
            f"Last verified: 2026-11-22\n{vp.BACKREF_LABEL}: TBD\n\n## Rationale\n\nLifecycle fixture.\n\n"
            "## Requirements\n\n1. Keep line endings.\n\n## Scope\n\nTemporary repository.\n\n"
            "## Acceptance Criteria\n\n- [x] AC-1: Fixture is complete.\n"
            "## Tasks\n\n- [x] Complete fixture.\n\n## AC Priority\n\n"
            "| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Fixture. |\n"
        )

    def run_lifecycle(self, shape):
        srv = self.srv
        root, call = self._fresh()
        made = self.ok(srv._change_create_response(root, "enh", "endings-child", mode="create"))
        cid = made["change_id"]
        spec = root / made["path"]
        spec.write_text(SHAPES[shape](self.spec_text(cid)), encoding="utf-8", newline="")
        wave = self.ok(srv.wf_create_wave_response(root, "endings", mode="create"))
        wid, wave_md = wave["wave_id"], root / wave["path"]
        self.reshape(shape, wave_md)
        handoff = root / "docs/agents/session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(SHAPES[shape]("# Session Handoff\n\n## Notes\n\nkeep-me\n"),
                           encoding="utf-8", newline="")

        self.ok(srv.wf_add_change_response(root, wid, cid, mode="create"))
        spec = wave_md.parent / spec.name
        self.assert_shape(shape, wave_md, "add_change")
        self.assert_shape(shape, spec, "add_change")
        self.assertIn(f"{vp.BACKREF_LABEL}: {wid}\n", _to_lf(spec.read_bytes()), "AC-3: the back-reference is repaired")

        prepared = srv.wf_prepare_wave_response(root, wid, mode="ready")
        self.assertIn(prepared["status"], {"ok", "error"}, prepared)
        self.assert_shape(shape, wave_md, "prepare")
        self.assert_shape(shape, spec, "prepare heading fix")
        self.assertIn("\n\n## Tasks", _to_lf(spec.read_bytes()))
        self.ok(srv.wf_review_event_response(
            root, wid, event="run", actor="council-chair", context_id="endings-readiness",
            mode="create", run_kind="readiness", cycle=0))
        self.assert_shape(shape, wave_md, "review run")
        for key in ("council-readiness", "code-reviewer"):
            actor = "council-chair" if key.startswith("council-") else key
            self.ok(srv.wf_review_event_response(
                root, wid, event="approval", actor=actor, context_id="endings-approval-" + key,
                mode="create", signoff_key=key, approval_phase="readiness",
                fresh_context=True, independent=True,
                evidence={"observed": "fixture approval", "artifact_or_test_id": self.id(),
                          **({"intent_fit": "establishes"} if "council" in key else {})},
                integrity_checks=integrity_checks()))
            self.assert_shape(shape, wave_md, "review approval " + key)
        self.ok(call("wf_prepare_wave", wave_id=wid, mode="ready"))
        self.assert_shape(shape, wave_md, "prepare ready")

        self.ok(call("wf_implement_wave", wave_id=wid, mode="create"))
        self.assert_shape(shape, wave_md, "implement")
        self.ok(call("wf_pause_wave", wave_id=wid, mode="create"))
        self.assert_shape(shape, wave_md, "pause")
        self.assert_shape(shape, handoff, "pause handoff")
        self.assertIn("keep-me", _to_lf(handoff.read_bytes()))
        self.ok(call("wf_reopen_wave", wave_id=wid, purpose="implement"))
        self.assert_shape(shape, wave_md, "reopen paused")
        self.ok(call("wf_implement_wave", wave_id=wid, mode="create"))
        self.assert_shape(shape, wave_md, "implement again")

        for path in (wave_md, spec):
            self.replace_bytes(path, f"{vp.MEMBER_STATUS_LABEL}: `planned`",
                               f"{vp.MEMBER_STATUS_LABEL}: `implemented`")
        self.replace_bytes(spec, "Status: planned", "Status: implemented")
        review = call("wf_review_wave", wave_id=wid, phase="implementation")
        self.ok(call("wf_review_event", wave_id=wid, event="run", actor="council-chair",
                     context_id="endings-delivery", run_kind="initial_delivery", cycle=0, mode="create"))
        keys = [*review["data"].get("required_lanes", ()),
                *review["data"].get("required_council_signoffs", ()), "operator-signoff"]
        for key in dict.fromkeys(keys):
            actor = ("operator" if key == "operator-signoff" else
                     "council-chair" if key.startswith(("wave-council", "council-")) else key)
            self.ok(call(
                "wf_review_event", wave_id=wid, event="approval", actor=actor,
                context_id="endings-delivery-" + key, signoff_key=key,
                approval_phase="delivery", fresh_context=True, independent=True, mode="create",
                evidence={"observed": "line ending fixture", "artifact_or_test_id": self.id(),
                          **({"intent_fit": "establishes"} if "council" in key else {})},
                integrity_checks=integrity_checks()))
        self.assert_shape(shape, wave_md, "delivery review")
        self.ok(call("wf_close_change", wave_id=wid, change_id=cid, mode="create"))
        self.assert_shape(shape, wave_md, "close change")
        self.assert_shape(shape, spec, "close change")
        self.ok(close_container(call, root, wid, mode="create"))
        self.assert_shape(shape, wave_md, "close wave")
        self.assertIn("Status: closed", _to_lf(wave_md.read_bytes()))
        self.ok(call("wf_reopen_wave", wave_id=wid, purpose="implement"))
        self.assert_shape(shape, wave_md, "reopen closed")

    def test_lifecycle_writers_keep_line_endings(self):
        for shape in SHAPES:
            for simulated in (False, True):
                with self.subTest(shape=shape, windows_simulation=simulated):
                    with windows_text_writes() if simulated else contextlib.nullcontext():
                        self.run_lifecycle(shape)

    def test_remove_change_keeps_line_endings(self):
        srv = self.srv
        for shape in SHAPES:
            for simulated in (False, True):
                with self.subTest(shape=shape, windows_simulation=simulated), \
                        (windows_text_writes() if simulated else contextlib.nullcontext()):
                    root, _call = self._fresh()
                    made = self.ok(srv._change_create_response(root, "enh", "remove-child", mode="create"))
                    wave = self.ok(srv.wf_create_wave_response(root, "remove", mode="create"))
                    wave_md = root / wave["path"]
                    self.reshape(shape, wave_md)
                    self.ok(srv.wf_add_change_response(root, wave["wave_id"], made["change_id"], mode="create"))
                    self.assert_shape(shape, wave_md, "add")
                    self.ok(srv.wf_remove_change_response(root, wave["wave_id"], made["change_id"], mode="create"))
                    self.assert_shape(shape, wave_md, "remove")
                    self.assertNotIn(made["change_id"], _to_lf(wave_md.read_bytes()))


class AdmissionBackReferenceTests(unittest.TestCase):
    """AC-3: a pure CRLF spec's ``Wave: TBD`` line is repaired and stays CRLF;
    a mixed spec admitted under the Windows simulation gains no ``\\r\\r\\n``."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def _admit(self, spec_bytes, *, simulated):
        srv = self.srv
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = _make_repo(Path(tmp.name)).resolve()
        made = srv._change_create_response(root, "bug", "backref", mode="create")["data"]
        spec = root / made["path"]
        lf = spec.read_text(encoding="utf-8")
        self.assertIn(f"\n{vp.BACKREF_LABEL}: TBD\n", lf)
        spec.write_bytes(spec_bytes(lf))
        wave = srv.wf_create_wave_response(root, "backref", mode="create")["data"]
        with patch.object(srv, "_trigger_background_index_refresh_for_paths", lambda *a, **k: None), \
                (windows_text_writes() if simulated else contextlib.nullcontext()):
            result = srv.wf_add_change_response(root, wave["wave_id"], made["change_id"], mode="create")
        self.assertEqual(result["status"], "ok", result)
        return wave["wave_id"], (root / wave["path"]).parent / spec.name, lf

    def test_pure_crlf_spec_is_repaired_and_stays_crlf(self):
        for simulated in (False, True):
            with self.subTest(windows_simulation=simulated):
                wid, spec, lf = self._admit(lambda t: t.replace(LF, CRLF).encode(), simulated=simulated)
                expected = lf.replace(f"\n{vp.BACKREF_LABEL}: TBD\n", f"\n{vp.BACKREF_LABEL}: {wid}\n").replace(LF, CRLF).encode()
                self.assertEqual(spec.read_bytes(), expected)

    def test_mixed_spec_gains_no_double_carriage_return(self):
        for simulated in (False, True):
            with self.subTest(windows_simulation=simulated):
                wid, spec, lf = self._admit(lambda t: mixed(t).encode(), simulated=simulated)
                data = spec.read_bytes()
                self.assertNotIn(b"\r\r\n", data)
                self.assertEqual(
                    data, mixed(lf.replace(f"\n{vp.BACKREF_LABEL}: TBD\n", f"\n{vp.BACKREF_LABEL}: {wid}\n")).encode())


class HandoffAndEscalationWriterTests(unittest.TestCase):
    """AC-1 and AC-4 for ``_write_handoff_text`` and ``_retain_review_escalation``."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = _make_repo(Path(tmp.name)).resolve()

    def test_handoff_keeps_lf_and_crlf_and_creates_lf(self):
        path = self.root / "docs/agents/session-handoff.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        before = "# Session Handoff\n\n## Notes\n\nkeep-me\n"
        after = before + "\n## Current Session\n\nnew\n"
        for simulated in (False, True):
            ctx = windows_text_writes if simulated else contextlib.nullcontext
            for shape, build in SHAPES.items():
                with self.subTest(shape=shape, windows_simulation=simulated):
                    path.write_bytes(build(before).encode())
                    with ctx():
                        self.srv._write_handoff_text(self.root, path, after)
                    self.assertEqual(path.read_bytes(), build(after).encode())
            with self.subTest(shape="missing", windows_simulation=simulated):
                path.unlink()
                with ctx():
                    self.srv._write_handoff_text(self.root, path, after)
                self.assertEqual(path.read_bytes(), after.encode())

    def test_retained_escalation_keeps_line_endings(self):
        srv = self.srv
        wave = srv.wf_create_wave_response(self.root, "escalation", mode="create")["data"]
        wave_md = self.root / wave["path"]
        lf = wave_md.read_text(encoding="utf-8")
        authority = SimpleNamespace(wave_closed=False, ledger_errors=(), records=())
        lane = {"effective_lane": "ordinary", "reasons": ["scope grew"]}
        for simulated in (False, True):
            for shape, build in SHAPES.items():
                with self.subTest(shape=shape, windows_simulation=simulated):
                    wave_md.write_bytes(build(lf).encode())
                    with patch.object(srv, "current_policy_receipt",
                                      return_value={"small_change": {"effective_lane": "small"}}), \
                            patch.object(srv, "resolve_review_authority", return_value=authority), \
                            (windows_text_writes() if simulated else contextlib.nullcontext()):
                        result = srv._retain_review_escalation(self.root, wave_md, authority, lane)
                    self.assertEqual(result["code"], "review_policy_reprepare_required", result)
                    data = wave_md.read_bytes()
                    self.assertNotIn(b"\r\r\n", data)
                    self.assertNotEqual(_to_lf(data), lf)
                    self.assertEqual(data, build(_to_lf(data)).encode())


class NormalizingGateRegressionTests(unittest.TestCase):
    """AC-12: the gates that already normalize treat LF and CRLF content as
    equal. This pins existing behavior at the operator's request."""

    BODY = "# Spec\n\n## Requirements\n\nKeep this.\nLast verified: 2026-11-22\n"

    def test_review_policy_receipt_and_canonical_body(self):
        import gardener_metadata
        import review_policy

        lf, crlf = self.BODY.encode(), self.BODY.replace(LF, CRLF).encode()
        self.assertEqual(gardener_metadata.canonical_review_policy_body(lf),
                         gardener_metadata.canonical_review_policy_body(crlf))

        def receipt(body):
            return review_policy.policy_input_snapshot(
                wave_review={"enabled": True, "delivery_mode": "universal"},
                project_lanes=(), review_policies={},
                changes=(("1abc-bug example", "bug", body),), requested_lanes=(),
            )[0]

        self.assertEqual(receipt(lf), receipt(crlf))

    def test_gardener_changed_from_head_comparison(self):
        import docs_gardener

        lf, crlf = self.BODY.encode(), self.BODY.replace(LF, CRLF).encode()
        self.assertEqual(docs_gardener._without_date_line(lf), docs_gardener._without_date_line(crlf))

    def test_secrets_allowlist_file_digest(self):
        import build_scan_allowlist
        from wave_lint_lib import secrets_validators

        with tempfile.TemporaryDirectory() as tmp:
            lf_path, crlf_path = Path(tmp) / "lf.txt", Path(tmp) / "crlf.txt"
            lf_path.write_bytes(self.BODY.encode())
            crlf_path.write_bytes(self.BODY.replace(LF, CRLF).encode())
            for digest in (build_scan_allowlist._sha256_file, secrets_validators._sha256_file):
                with self.subTest(digest=digest.__module__):
                    self.assertEqual(digest(lf_path), digest(crlf_path))


class GeneratedWriterSimulationTests(unittest.TestCase):
    """AC-6, executed: generated writers write LF bytes under the shared
    Windows-write simulation (the census checks every generated writer's
    ``newline`` statically)."""

    def test_guard_override_writers_are_lf(self):
        import wave_gate
        import wf_server.edit_gate_handlers as edit_gate_handlers

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with windows_text_writes():
                wave_gate._write(root, {"a": {"b": 1}})
                data = (root / ".wavefoundry/guard-overrides.json").read_bytes()
                self.assertIn(b"\n", data)
                self.assertNotIn(b"\r", data)
                edit_gate_handlers._write_guard_overrides(root, {"c": [1, 2]})
                data = (root / ".wavefoundry/guard-overrides.json").read_bytes()
                self.assertIn(b"\n", data)
                self.assertNotIn(b"\r", data)

    def test_new_spec_is_lf(self):
        srv = load_server()
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            with windows_text_writes():
                made = srv._change_create_response(root, "bug", "lf-spec", mode="create")["data"]
            data = (root / made["path"]).read_bytes()
            self.assertIn(b"\n", data)
            self.assertNotIn(b"\r", data)


if __name__ == "__main__":
    unittest.main()
