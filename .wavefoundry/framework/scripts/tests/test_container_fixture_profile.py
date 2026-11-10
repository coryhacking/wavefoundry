"""Container fixture calls go through the fork-editable profile (wave 22r99, change 22r98).

A distribution whose served ``wf_create_wave`` or ``wf_close_wave`` needs more
arguments edits ``container_fixture_profile`` only. These tests prove the
helpers in ``server_tools_support`` pass the profile's arguments, refuse a
collision, and that the converted fixture files make no direct container call.

Change 230k7: the arguments belong to the handler a distribution serves, so a
fixture that pinned the base declaration (``declaration_support``) calls the core
tool without them, and a declaration that overrides or replaces the tool still
receives them.
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
import declaration_support
import server_tools_support
from declaration_support import base_declaration
from server_tools_support import close_container, create_container
from record_layout_support import default_profile_only

CONTAINER_TOOLS = frozenset({"wf_create_wave", "wf_close_wave"})
HELPERS = frozenset({"create_container", "close_container"})
WAVE_WORK = TESTS / "test_wave_work_lifecycle.py"
LIFECYCLE = TESTS / "test_server_tools_lifecycle.py"
SNAPSHOT_CLASS = "ReceiptSnapshotPublicIntegrationTests"
PREVIEW_CLASS = "RetainedUpgradePreviewTests"


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

    @default_profile_only("checks upstream's shipped profile, which a distribution fills in with its own arguments")
    def test_shipped_profile_adds_nothing(self):
        root = Path("/fixture/root")
        self.assertEqual(container_fixture_profile.container_fixture_args("wf_create_wave", root), {})
        self.assertEqual(container_fixture_profile.container_fixture_args("wf_close_wave", root), {})

    def test_an_empty_profile_passes_the_test_arguments_through_unchanged(self):
        # Patch the shipped default in, so this holds on any tree, including a
        # distribution whose profile supplies its own arguments (change 22rmf).
        root = Path("/fixture/root")
        with patch.object(container_fixture_profile, "container_fixture_args", lambda tool_name, root: {}):
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


class ActiveDeclarationRoutingTests(unittest.TestCase):
    """Change 230k7 AC-3: fixture arguments follow the active declaration."""

    OVERRIDES = dict(EXTENSION_MODULES=("fork_tools",),
                     EXTENSION_OVERRIDES={"fork_tools": ("wf_close_wave",)})
    REPLACES = dict(EXTENSION_MODULES=("fork_tools",),
                    EXTENSION_REPLACEMENTS={"fork_tools": {"wf_create_wave": {"alias_for_core": "fork_create"}}})

    def setUp(self):
        self.calls = []
        self.consulted = []
        patcher = patch.object(container_fixture_profile, "container_fixture_args", self.profile)
        patcher.start()
        self.addCleanup(patcher.stop)

    def profile(self, tool_name, root):
        self.consulted.append(tool_name)
        return {"scope": "set"}

    def fake_call(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return {"status": "ok"}

    def both(self):
        self.calls.clear()
        create_container(self.fake_call, Path("/r"), "first")
        close_container(self.fake_call, Path("/r"), "abcde first")
        return [("scope" in kwargs) for _name, kwargs in self.calls]

    def test_the_base_declaration_calls_core_tools_without_fixture_arguments(self):
        with base_declaration():
            self.assertEqual(self.both(), [False, False])
        self.assertEqual(self.consulted, [])
        self.assertEqual(self.calls, [("wf_create_wave", {"slug": "first"}),
                                      ("wf_close_wave", {"wave_id": "abcde first"})])

    def test_a_declared_distribution_handler_receives_its_fixture_arguments(self):
        with base_declaration(**self.OVERRIDES):
            self.assertEqual(self.both(), [False, True])
        with base_declaration(**self.REPLACES):
            self.assertEqual(self.both(), [True, False])
        self.assertEqual(self.consulted, ["wf_close_wave", "wf_create_wave"])

    def test_the_ambient_declaration_receives_fixture_arguments(self):
        # No pinned declaration: the checkout's own declaration and profile apply together.
        self.assertEqual(self.both(), [True, True])

    def test_both_declaration_states_in_one_process_restore_between_fixtures(self):
        self.assertTrue(declaration_support.distribution_handler_served("wf_close_wave"))
        with base_declaration(**self.OVERRIDES):
            self.assertEqual(self.both(), [False, True])
            with base_declaration():
                self.assertEqual(self.both(), [False, False])
            self.assertEqual(self.both(), [False, True])
        self.assertEqual(declaration_support._PINNED_DECLARATIONS, [])
        self.assertEqual(self.both(), [True, True])

    def test_apply_base_declaration_is_released_at_cleanup(self):
        class Fixture(unittest.TestCase):
            def runTest(inner):
                declaration_support.apply_base_declaration(inner)
                inner.assertEqual(self.both(), [False, False])

        result = unittest.TestResult()
        Fixture().run(result)
        self.assertEqual((result.failures, result.errors), ([], []))
        self.assertEqual(self.both(), [True, True])

    def test_a_collision_is_still_refused_for_a_declared_distribution_handler(self):
        collide = patch.object(container_fixture_profile, "container_fixture_args",
                               lambda *_a: {"wave_id": "other"})
        with base_declaration(**self.OVERRIDES), collide:
            with self.assertRaisesRegex(ValueError, "collide"):
                close_container(self.fake_call, Path("/r"), "abcde first")
        self.assertEqual(self.calls, [])


class ConvertedFixtureCallGuardTests(unittest.TestCase):
    SCOPES = ((WAVE_WORK, None, 17), (LIFECYCLE, SNAPSHOT_CLASS, 1), (LIFECYCLE, PREVIEW_CLASS, 3))

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


class RetainedUpgradePreviewProfileTests(unittest.TestCase):
    """The upgrade-preview close sites go through the fixture helper (wave 22u26, change 22sfu).

    Those fixtures pin the base declaration, so the registered tools are the core ones and the
    profile's arguments, which only a distribution's handler accepts, are not passed (change
    230k7). The served core tool would refuse an unknown argument, so an injected one fails
    the suite as well as the recorded calls.
    """

    SITES = (
        "test_registered_actual_lint_previews_are_read_only_for_default_and_positional_modes",
        "test_mutations_unknown_corrupt_and_stale_code_remain_refused",
        "test_close_reports_new_unpublished_secrets_in_same_lint_pass",
    )

    def test_each_close_site_calls_the_core_tool_without_profile_arguments_and_keeps_positional_modes(self):
        import test_server_tools_lifecycle as lifecycle

        preview = lifecycle.RetainedUpgradePreviewTests
        original = preview.positional_call
        calls = []

        def spy(test, name, **kwargs):
            # Record whether the profile's `extra` arrived; it is passed on, so the served
            # core tool refuses it if it did.
            extra = kwargs.get("extra")
            tool = test.mcp._tool_manager._tools[name]
            served = tool.fn

            def recorder(*args, **keywords):
                calls.append((name, args, keywords, extra))
                return served(*args, **keywords)

            tool.fn = recorder
            try:
                return original(test, name, **kwargs)
            finally:
                tool.fn = served

        def profile(tool_name, root):
            return {"extra": 1} if tool_name == "wf_close_wave" else {}

        suite = unittest.TestSuite(preview(name) for name in self.SITES)
        with patch.object(container_fixture_profile, "container_fixture_args", profile), \
                patch.object(preview, "positional_call", spy):
            outcome = unittest.TestResult()
            suite.run(outcome)
        self.assertEqual((outcome.failures, outcome.errors), ([], []))
        wave_id = "00057 preview"
        self.assertEqual(calls, [
            ("wf_close_wave", (wave_id, "dry_run"), {}, None),
            ("wf_close_wave", (wave_id, "apply"), {}, None),
            ("wf_close_wave", (wave_id, "evaluate"), {}, None),
            ("wf_close_wave", (wave_id,), {}, None),
        ])


if __name__ == "__main__":
    unittest.main()
