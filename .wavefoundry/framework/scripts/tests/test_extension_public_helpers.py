"""Public helpers for extension handlers (wave 1zimf, change 1zimn).

``server_impl`` exposes a small stable surface for distribution extension
handlers: ``ensure_no_extra_args``, ``make_response``, ``make_diagnostic`` and
(change 1zimp) ``change_doc_response``. Each is a thin wrapper that looks up
its private counterpart at call time. Wave 1zls8 (change 1zltx) adds five
wrappers (``find_wave_record``, ``refuse_if_archived``,
``fail_closed_on_record_layout``, ``attach_lint``, ``refresh_index_for_paths``)
and lists the module-level ``list_waves`` and ``wf_review_wave_response``. The
end-to-end path (a fixture module that registers and serves through
``call_tool``, and reload) runs in the extension driver in
``test_extension_tool_modules``.
"""
from __future__ import annotations

import copy
import inspect
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from record_layout_support import apply_layout
from server_tools_support import _make_repo, load_server
from test_archive_root import ARCHIVED_CHANGE, ARCHIVED_WAVE, _ArchiveCase


# The documented signatures (docs/specs/mcp-tool-surface.md, Registration).
# server_impl uses postponed annotations, so annotations are their source text.
EXPECTED_SIGNATURES = {
    "ensure_no_extra_args": "(tool_name: 'str', kwargs: 'dict') -> 'dict | None'",
    "make_response": (
        "(status, data=None, *, diagnostics=None, next_tools=None, usage='') -> 'dict'"
    ),
    "make_diagnostic": (
        "(code, message, *, recovery_tools=None, recovery_usage='', advisory=False) -> 'dict'"
    ),
    "change_doc_response": "(root, kind, slug, *, cache=None) -> 'dict'",
    # Wave 1zls8 (change 1zltx).
    "find_wave_record": "(root, wave_id_or_prefix, wave_dirs=None)",
    "refuse_if_archived": "(root, token, kind)",
    "fail_closed_on_record_layout": "(tool)",
    "attach_lint": "(envelope, root, mode)",
    "refresh_index_for_paths": "(root, paths)",
    "list_waves": "(root: 'Path', wave_dirs: 'Optional[list[Path]]' = None) -> 'list[dict]'",
    "wf_review_wave_response": "(root: 'Path', wave_id: 'str', phase: 'str' = 'implementation') -> 'dict[str, Any]'",
    # Wave 200ey (change 200ew): the member-doc reader, the change-id shape
    # test and the reader's refusal type (a class: its signature is the
    # constructor's).
    "read_member_doc_bytes": "(folder, path, *, root) -> 'bytes'",
    "is_change_id": "(value) -> 'bool'",
    "MemberDocRefused": "(cause: 'str') -> 'None'",
}

# Change 1zltx: each new wrapper and the private function it calls at call time.
WRAPPED = (
    ("find_wave_record", "_find_wave_md_detailed"),
    ("refuse_if_archived", "_refuse_if_archived"),
    ("fail_closed_on_record_layout", "_fail_closed_on_record_layout"),
    ("attach_lint", "_attach_lint_to_response"),
    ("refresh_index_for_paths", "_trigger_background_index_refresh_for_paths"),
)


class PublicHelperContractTests(unittest.TestCase):
    """AC-1 and AC-3 (change 1zimn); the fourth name is change 1zimp's."""

    @classmethod
    def setUpClass(cls):
        cls.impl = load_server()

    def test_the_named_contract_lists_exactly_the_public_helpers(self):
        self.assertEqual(
            self.impl.EXTENSION_PUBLIC_HELPERS,
            ("ensure_no_extra_args", "make_response", "make_diagnostic", "change_doc_response",
             "find_wave_record", "refuse_if_archived", "fail_closed_on_record_layout", "attach_lint",
             "refresh_index_for_paths", "list_waves", "wf_review_wave_response",
             "read_member_doc_bytes", "is_change_id", "MemberDocRefused"),
        )
        self.assertIsInstance(self.impl.EXTENSION_PUBLIC_HELPERS, tuple)

    def test_each_named_helper_is_callable_with_its_documented_signature(self):
        for name in self.impl.EXTENSION_PUBLIC_HELPERS:
            with self.subTest(helper=name):
                helper = getattr(self.impl, name, None)
                self.assertTrue(callable(helper), f"{name} is missing or not callable")
                self.assertEqual(str(inspect.signature(helper)), EXPECTED_SIGNATURES[name])

    def test_ensure_no_extra_args_equals_the_private_helper(self):
        impl = self.impl
        for kwargs in ({}, {"kwargs": {}}, {"bogus": 1}, {"kwargs": {"mode": "x"}}, {"kwargs": 5},
                       {"b": 1, "a": 2}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(impl.ensure_no_extra_args("t", dict(kwargs)),
                                 impl._ensure_no_extra_args("t", dict(kwargs)))
        self.assertIsNone(impl.ensure_no_extra_args("t", {}))
        self.assertIsNone(impl.ensure_no_extra_args("t", {"kwargs": {}}))
        refused = impl.ensure_no_extra_args("t", {"bogus": 1})
        self.assertTrue(refused["isError"])
        self.assertEqual(refused["status"], "error")
        self.assertEqual([d["code"] for d in refused["diagnostics"]], ["unknown_arguments"])
        self.assertEqual(refused["data"]["rejected_arguments"], ["bogus"])

    def test_make_response_equals_the_private_helper(self):
        impl = self.impl
        diag = [{"code": "c", "message": "m"}]
        for args, kwargs in (
            (("ok",), {}),
            (("error",), {}),
            (("dry_run", {"a": 1}), {"diagnostics": diag, "next_tools": ["wf_help"], "usage": "u"}),
            (("error", {"b": 2}), {"usage": "x"}),
        ):
            with self.subTest(args=args, kwargs=kwargs):
                self.assertEqual(impl.make_response(*args, **kwargs), impl._response(*args, **kwargs))
        self.assertIs(impl.make_response("error")["isError"], True)
        self.assertNotIn("isError", impl.make_response("ok"))

    def test_make_diagnostic_equals_the_private_helper(self):
        impl = self.impl
        for args, kwargs in (
            (("c", "m"), {}),
            (("c", "m"), {"recovery_tools": ["wf_help"], "recovery_usage": "wf_help()"}),
            (("c", "m"), {"advisory": True}),
            (("c", "m"), {"advisory": "yes"}),
        ):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(impl.make_diagnostic(*args, **kwargs), impl._diagnostic(*args, **kwargs))


class PublicHelperLateBindingTests(unittest.TestCase):
    """AC-2: each public helper reaches the private function current at call time."""

    @classmethod
    def setUpClass(cls):
        cls.impl = load_server()

    def test_patching_the_private_helper_changes_the_public_result(self):
        impl = self.impl
        sentinel = {"patched": True}
        for public, private, call in (
            ("ensure_no_extra_args", "_ensure_no_extra_args", lambda: impl.ensure_no_extra_args("t", {"x": 1})),
            ("make_response", "_response", lambda: impl.make_response("ok")),
            ("make_diagnostic", "_diagnostic", lambda: impl.make_diagnostic("c", "m")),
            ("change_doc_response", "_change_create_response",
             lambda: impl.change_doc_response("/nonexistent", "feat", "s")),
            # Change 1zltx.
            ("find_wave_record", "_find_wave_md_detailed", lambda: impl.find_wave_record("/r", "1abcd")),
            ("refuse_if_archived", "_refuse_if_archived", lambda: impl.refuse_if_archived("/r", "1abcd", "wave")),
            ("fail_closed_on_record_layout", "_fail_closed_on_record_layout",
             lambda: impl.fail_closed_on_record_layout("t")),
            ("attach_lint", "_attach_lint_to_response", lambda: impl.attach_lint({}, "/r", "create")),
            ("refresh_index_for_paths", "_trigger_background_index_refresh_for_paths",
             lambda: impl.refresh_index_for_paths("/r", ["docs/x.md"])),
        ):
            with self.subTest(helper=public):
                with mock.patch.object(impl, private, lambda *a, **k: sentinel):
                    self.assertIs(call(), sentinel)

    def test_the_wrappers_are_distinct_functions_not_aliases(self):
        # An alias (``make_response = _response``) would bind the function
        # object at import and miss a patch or an in-place reload.
        impl = self.impl
        for public, private in (("ensure_no_extra_args", "_ensure_no_extra_args"),
                                ("make_response", "_response"), ("make_diagnostic", "_diagnostic"),
                                ("change_doc_response", "_change_create_response"), *WRAPPED):
            with self.subTest(helper=public):
                self.assertIsNot(getattr(impl, public), getattr(impl, private))



class LifecycleHelperEqualityTests(unittest.TestCase):
    """Change 1zltx AC-1: the lifecycle wrappers return and raise what their private counterparts do."""

    NESTED_LAYOUT = {
        "waves_root": "project/records/waves", "plans_root": "project/records/plans",
        "nested": True, "max_depth": 4,
    }

    def setUp(self):
        self.impl = load_server()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = _make_repo(Path(tmp.name))

    def _layout(self, **kwargs):
        apply_layout(self, modules=(self.impl.record_paths,), **kwargs)

    def _created_wave(self):
        created = self.impl.wf_create_wave_response(self.root, "helper", mode="create")
        self.assertEqual(created["status"], "ok", created)
        return created["data"]["wave_id"]

    def _duplicate(self, wave_id):
        waves = self.root / "project" / "records" / "waves"
        twin = waves / "team" / wave_id
        twin.parent.mkdir(parents=True)
        shutil.copytree(waves / wave_id, twin)

    def test_find_wave_record_equals_the_private_function(self):
        impl = self.impl
        wave_id = self._created_wave()
        for token in (wave_id, wave_id[:5], "1zzzz", ""):
            with self.subTest(token=token):
                self.assertEqual(impl.find_wave_record(self.root, token),
                                 impl._find_wave_md_detailed(self.root, token))
        found, read_error, unreadable = impl.find_wave_record(self.root, wave_id)
        self.assertEqual(found.name, impl._vocab.RECORD_FILENAME)
        self.assertIsNone(read_error)
        self.assertEqual(unreadable, [])
        dirs = [found.parent.parent]
        self.assertEqual(impl.find_wave_record(self.root, wave_id, dirs),
                         impl._find_wave_md_detailed(self.root, wave_id, dirs))

    def test_find_wave_record_raises_what_the_private_function_raises(self):
        impl = self.impl
        self._layout(**self.NESTED_LAYOUT)
        wave_id = self._created_wave()
        self._duplicate(wave_id)
        for fn in (impl.find_wave_record, impl._find_wave_md_detailed):
            with self.subTest(fn=fn.__name__):
                with self.assertRaises(impl.record_paths.AmbiguousWaveId):
                    fn(self.root, wave_id)
        self._layout(waves_root="../x")
        for fn in (impl.find_wave_record, impl._find_wave_md_detailed):
            with self.subTest(fn=fn.__name__, layout="invalid"):
                with self.assertRaises(impl.record_paths.RecordLayoutInvalid):
                    fn(self.root, wave_id)

    def test_fail_closed_on_record_layout_behaves_as_the_private_decorator(self):
        # A new decorated function per call, so it is pinned by behaviour.
        impl = self.impl

        def body(token):
            wave_md, _error, _unreadable = impl.find_wave_record(self.root, token)
            return {"status": "ok", "data": {"found": wave_md is not None}}

        public = impl.fail_closed_on_record_layout("acme_tool")(body)
        private = impl._fail_closed_on_record_layout("acme_tool")(body)
        self.assertEqual(public.__wrapped__, body)
        wave_id = self._created_wave()
        self.assertEqual(public(wave_id), private(wave_id))
        self.assertEqual(public(wave_id), {"status": "ok", "data": {"found": True}})
        self._layout(**self.NESTED_LAYOUT)
        nested_id = self._created_wave()
        self._duplicate(nested_id)
        duplicated = public(nested_id)
        self.assertEqual(duplicated, private(nested_id))
        self.assertEqual(duplicated["diagnostics"][0]["code"], "ambiguous_wave_id")
        self._layout(waves_root="../x")
        invalid = public(nested_id)
        self.assertEqual(invalid, private(nested_id))
        self.assertEqual(invalid["diagnostics"][0]["code"], impl.record_paths.DIAGNOSTIC_CODE)

    def test_attach_lint_equals_the_private_function(self):
        impl = self.impl
        lint = {"passed": True, "errors": [], "warnings": []}
        with mock.patch.object(impl, "_run_post_write_lint", lambda root: copy.deepcopy(lint)):
            for envelope, mode in (
                ({"status": "ok", "data": {"a": 1}}, "create"),
                ({"status": "ok", "data": {"a": 1}}, "dry_run"),
                ({"status": "error", "data": {"a": 1}}, "create"),
                ({"status": "ok"}, "apply"),
            ):
                with self.subTest(mode=mode, status=envelope["status"]):
                    public = impl.attach_lint(copy.deepcopy(envelope), self.root, mode)
                    self.assertEqual(public, impl._attach_lint_to_response(copy.deepcopy(envelope), self.root, mode))
                    self.assertEqual(public["status"], envelope["status"])
                    self.assertEqual("lint" in (public.get("data") or {}),
                                     mode != "dry_run" and envelope["status"] != "error")

    def test_refresh_index_for_paths_equals_the_private_function(self):
        impl = self.impl
        import wf_server.index_handlers as index_handlers
        started = []
        with mock.patch.object(index_handlers, "_start_background_index_refresh",
                               lambda root, layer: started.append(layer) or True):
            for paths in (["src/app.py"], [self.root / "notes.txt"], ["docs/a.md"], ["./docs/b.md", "x"], []):
                with self.subTest(paths=paths):
                    self.assertEqual(impl.refresh_index_for_paths(self.root, paths),
                                     impl._trigger_background_index_refresh_for_paths(self.root, paths))
        self.assertEqual(impl.refresh_index_for_paths(self.root, ["src/app.py"]), {"project": False})
        self.assertIn("project", started)


class RefuseIfArchivedEqualityTests(_ArchiveCase):
    """Change 1zltx AC-1: ``refuse_if_archived`` returns the private diagnostic or ``None``."""

    def test_refuse_if_archived_equals_the_private_function(self):
        srv = self.srv
        for token, kind in ((ARCHIVED_WAVE.split()[0], "wave"), (ARCHIVED_CHANGE.split("-")[0], "change"),
                            ("1zzzz", "wave"), ("1zzzz", "change")):
            with self.subTest(token=token, kind=kind):
                self.assertEqual(srv.refuse_if_archived(self.root, token, kind),
                                 srv._refuse_if_archived(self.root, token, kind))
        refused = srv.refuse_if_archived(self.root, ARCHIVED_WAVE.split()[0], "wave")
        self.assertEqual(refused["code"], "archived_record_read_only")
        self.assertIsNone(srv.refuse_if_archived(self.root, "1zzzz", "wave"))


if __name__ == "__main__":
    unittest.main()
