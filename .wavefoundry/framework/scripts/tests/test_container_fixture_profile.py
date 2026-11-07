"""Container fixture calls go through the fork-editable profile (wave 22r99, change 22r98).

A distribution whose served ``wf_create_wave`` or ``wf_close_wave`` needs more
arguments edits ``container_fixture_profile`` only. These tests prove the
helpers in ``server_tools_support`` pass the profile's arguments, refuse a
collision, and that the converted fixture files make no direct container call.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS = Path(__file__).resolve().parent
if str(TESTS.parent) not in sys.path:
    sys.path.insert(0, str(TESTS.parent))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import container_fixture_profile
import server_tools_support
from server_tools_support import close_container, create_container

CONTAINER_TOOLS = frozenset({"wf_create_wave", "wf_close_wave"})
HELPERS = frozenset({"create_container", "close_container"})
WAVE_WORK = TESTS / "test_wave_work_lifecycle.py"
LIFECYCLE = TESTS / "test_server_tools_lifecycle.py"
SNAPSHOT_CLASS = "ReceiptSnapshotPublicIntegrationTests"


def _string(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _scope(source: str, class_name: str | None) -> ast.AST:
    tree = ast.parse(source)
    if class_name is None:
        return tree
    matches = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == class_name]
    if len(matches) != 1:
        raise AssertionError(f"expected one class {class_name}, found {len(matches)}")
    return matches[0]


def direct_container_calls(source: str, class_name: str | None = None) -> list[int]:
    """Line numbers of direct served container-tool calls in the scope.

    A direct call is any call whose first positional argument or ``name=``
    keyword is the string "wf_create_wave" or "wf_close_wave", and any
    ``_tool_manager._tools["wf_create_wave"|"wf_close_wave"]`` lookup.
    """
    lines = []
    for node in ast.walk(_scope(source, class_name)):
        if isinstance(node, ast.Call):
            named = [_string(k.value) for k in node.keywords if k.arg == "name"]
            first = _string(node.args[0]) if node.args else None
            if first in CONTAINER_TOOLS or any(value in CONTAINER_TOOLS for value in named):
                lines.append(node.lineno)
        elif (isinstance(node, ast.Subscript) and _string(node.slice) in CONTAINER_TOOLS
              and isinstance(node.value, ast.Attribute) and node.value.attr == "_tools"
              and isinstance(node.value.value, ast.Attribute) and node.value.value.attr == "_tool_manager"):
            lines.append(node.lineno)
    return sorted(lines)


def helper_calls(source: str, class_name: str | None = None) -> int:
    count = 0
    for node in ast.walk(_scope(source, class_name)):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            count += name in HELPERS
    return count


class ContainerFixtureHelperTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def fake_call(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return {"status": "ok"}

    def test_default_profile_adds_nothing(self):
        root = Path("/fixture/root")
        self.assertEqual(container_fixture_profile.container_fixture_args("wf_create_wave", root), {})
        self.assertEqual(container_fixture_profile.container_fixture_args("wf_close_wave", root), {})
        create_container(self.fake_call, root, "first", mode="create")
        close_container(self.fake_call, root, "abcde first", mode="dry_run")
        self.assertEqual(self.calls, [("wf_create_wave", {"slug": "first", "mode": "create"}),
                                      ("wf_close_wave", {"wave_id": "abcde first", "mode": "dry_run"})])

    def test_profile_arguments_reach_the_served_tool(self):
        seen = []

        def profile(tool_name, root):
            seen.append((tool_name, root))
            return {"wf_create_wave": {"feature": "parent-1", "kind": "delivery"},
                    "wf_close_wave": {"scope": "set"}}[tool_name]

        root = Path("/fixture/root")
        with patch.object(container_fixture_profile, "container_fixture_args", profile):
            create_container(self.fake_call, root, "first", mode="create")
            close_container(self.fake_call, root, "abcde first", mode="create")
        self.assertEqual(seen, [("wf_create_wave", root), ("wf_close_wave", root)])
        self.assertEqual(self.calls, [
            ("wf_create_wave", {"slug": "first", "mode": "create", "feature": "parent-1", "kind": "delivery"}),
            ("wf_close_wave", {"wave_id": "abcde first", "mode": "create", "scope": "set"}),
        ])

    def test_a_profile_key_that_collides_with_a_test_argument_raises(self):
        root = Path("/fixture/root")
        for helper, collision in ((create_container, {"slug": "other"}), (create_container, {"mode": "x"}),
                                  (close_container, {"wave_id": "other"}), (close_container, {"mode": "x"})):
            with self.subTest(helper=helper.__name__, key=next(iter(collision))), \
                    patch.object(container_fixture_profile, "container_fixture_args", lambda *_a, c=collision: c):
                with self.assertRaisesRegex(ValueError, "collide"):
                    helper(self.fake_call, root, "first", mode="create")
        self.assertEqual(self.calls, [])

    def test_the_helpers_resolve_the_profile_at_call_time(self):
        # A patch applied after server_tools_support was imported still applies.
        self.assertIs(server_tools_support.create_container, create_container)
        with patch.object(container_fixture_profile, "container_fixture_args", lambda *_a: {"extra": 1}):
            create_container(self.fake_call, Path("/r"), "s")
        self.assertEqual(self.calls, [("wf_create_wave", {"slug": "s", "extra": 1})])


class ConvertedFixtureCallGuardTests(unittest.TestCase):
    SCOPES = ((WAVE_WORK, None, 17), (LIFECYCLE, SNAPSHOT_CLASS, 1))

    def test_converted_scopes_make_no_direct_container_call(self):
        for path, class_name, _expected in self.SCOPES:
            with self.subTest(path=path.name, scope=class_name or "whole file"):
                self.assertEqual(direct_container_calls(path.read_text(encoding="utf-8"), class_name), [])

    def test_every_converted_site_calls_a_helper(self):
        for path, class_name, expected in self.SCOPES:
            with self.subTest(path=path.name, scope=class_name or "whole file"):
                self.assertEqual(helper_calls(path.read_text(encoding="utf-8"), class_name), expected)

    def test_the_guard_finds_each_direct_form(self):
        source = (
            "class Sample:\n"
            "    def test(self):\n"
            "        self.call('wf_create_wave', slug='a')\n"
            "        call(name='wf_close_wave', wave_id='b')\n"
            "        self.mcp._tool_manager._tools['wf_close_wave'].fn(wave_id='c')\n"
            "        self.call(tool, slug='not-direct')\n"
            "        srv.wf_create_wave_response(root, 'not-direct')\n"
            "        create_container(self.call, self.root, 'converted')\n"
        )
        self.assertEqual(direct_container_calls(source), [3, 4, 5])
        self.assertEqual(direct_container_calls(source, "Sample"), [3, 4, 5])
        self.assertEqual(helper_calls(source), 1)


if __name__ == "__main__":
    unittest.main()
