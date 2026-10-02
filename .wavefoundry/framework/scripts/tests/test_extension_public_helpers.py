"""Public helpers for extension handlers (wave 1zimf, change 1zimn).

``server_impl`` exposes a small stable surface for distribution extension
handlers: ``ensure_no_extra_args``, ``make_response``, ``make_diagnostic`` and
(change 1zimp) ``change_doc_response``. Each is a thin wrapper that looks up
its private counterpart at call time. The end-to-end path (a fixture module
that registers and serves through ``call_tool``, and reload) runs in the
extension driver in ``test_extension_tool_modules``.
"""
from __future__ import annotations

import inspect
import unittest
from unittest import mock

from server_tools_support import load_server


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
}


class PublicHelperContractTests(unittest.TestCase):
    """AC-1 and AC-3 (change 1zimn); the fourth name is change 1zimp's."""

    @classmethod
    def setUpClass(cls):
        cls.impl = load_server()

    def test_the_named_contract_lists_exactly_the_public_helpers(self):
        self.assertEqual(
            self.impl.EXTENSION_PUBLIC_HELPERS,
            ("ensure_no_extra_args", "make_response", "make_diagnostic", "change_doc_response"),
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
                                ("change_doc_response", "_change_create_response")):
            with self.subTest(helper=public):
                self.assertIsNot(getattr(impl, public), getattr(impl, private))


if __name__ == "__main__":
    unittest.main()
