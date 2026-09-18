"""Golden snapshot of the public MCP tool surface (wave 1y0do / 1xzsl).

Three guards that later refactor waves are judged against:

* ``ToolSurfaceGoldenTests`` — every tool registered by the real
  ``server.build_server`` (implementation tools AND runner survivors) is
  serialized to a deterministic JSON document (name, roster tier, input
  schema, annotations) and compared byte-for-byte to the committed fixture
  ``fixtures/tool-surface-golden.json``. Regeneration is explicit and only
  happens under ``WF_UPDATE_TOOL_SURFACE_GOLDEN=1``.
* ``RosterRuntimeParityTests`` — the registered set equals the roster in
  both directions at runtime (a complement to the AST census in
  ``test_render_platform_surfaces``).
* ``WrapperOrderTests`` — the three post-registration wrapper passes compose
  as cost innermost, lifecycle lock middle, upgrade-publication guard
  outermost, proven by behaviour through the registered callable, with the
  five wrong permutations as negative controls.

No production module is imported for anything but reading; the server is
booted with ``server_impl.build_handler`` stubbed, so no model loads, no
index builds, no monitor starts, and nothing is written under the temp
repository beyond the minimal fixture ``_make_repo`` creates.
"""
from __future__ import annotations

import contextlib
import copy
import itertools
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from server_tools_support import _make_repo, load_server, load_thin_runner

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
GOLDEN_PATH = TESTS_DIR / "fixtures" / "tool-surface-golden.json"
UPDATE_ENV = "WF_UPDATE_TOOL_SURFACE_GOLDEN"
FIXTURE_SCHEMA = "1"

# JSON-Schema keywords whose VALUE is a map of names to schemas. A key named
# ``description`` directly under one of these is a property/definition name,
# not prose, and must survive; anywhere else ``description`` is prose.
_SCHEMA_MAP_KEYS = frozenset({"properties", "$defs", "definitions", "patternProperties"})

_WRAPPER_NAMES = (
    "_wrap_first_party_tool_costs",
    "_wrap_lifecycle_mutation_lock",
    "_wrap_upgrade_publication_guard",
)
# A tool covered by ALL three wrapper passes: in _LIFECYCLE_MUTATION_LOCK_TOOLS,
# in publication_control's writer registry, first-party prefixed, and NOT in
# _COST_EXEMPT_TOOLS (which excludes wf_prepare_wave and four siblings).
_TRIPLE_WRAPPED_TOOL = "wf_add_change"
_TRIPLE_WRAPPED_RESPONSE = "wf_add_change_response"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def strip_prose_descriptions(node, *, in_name_map: bool = False):
    """Drop schema-node ``description`` prose; keep names that happen to be
    ``description`` inside ``properties`` / ``$defs`` maps."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "description" and not in_name_map:
                continue
            child_is_map = (key in _SCHEMA_MAP_KEYS) and not in_name_map
            out[key] = strip_prose_descriptions(value, in_name_map=child_is_map)
        return out
    if isinstance(node, list):
        return [strip_prose_descriptions(item) for item in node]
    return node


def _canonical_schema(schema):
    """Deep copy with prose stripped and set-like ``required`` arrays sorted
    so declaration order never shows up as a public-surface diff."""
    out = strip_prose_descriptions(copy.deepcopy(schema))

    def _sort_required(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "required" and isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    node[key] = sorted(value)
                else:
                    _sort_required(value)
        elif isinstance(node, list):
            for item in node:
                _sort_required(item)

    _sort_required(out)
    return out


def serialize_surface(mcp, tiers) -> dict:
    """Deterministic document for every registered tool."""
    registry = mcp._tool_manager._tools
    tools = {}
    for name in sorted(registry):
        tool = registry[name]
        annotations = getattr(tool, "annotations", None)
        tools[name] = {
            "tier": tiers.get(name),
            "inputSchema": _canonical_schema(tool.parameters),
            "annotations": (
                annotations.model_dump(exclude_none=True)
                if annotations is not None
                else None
            ),
        }
    return {"fixture_schema": FIXTURE_SCHEMA, "tools": tools}


def render_surface(surface) -> bytes:
    """Byte-stable rendering: sorted keys, UTF-8, LF newlines on every platform."""
    text = json.dumps(surface, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    return text.replace("\r\n", "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def _diff_node(tool: str, expected, actual, path: str, lines: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            child = f"{path}/{key}" if path else key
            if key not in actual:
                lines.append(f"{tool}: removed key {child}")
            elif key not in expected:
                lines.append(f"{tool}: added key {child}")
            else:
                _diff_node(tool, expected[key], actual[key], child, lines)
    elif expected != actual:
        lines.append(f"{tool}: changed key {path}: {expected!r} -> {actual!r}")


def diff_surfaces(expected_tools: dict, actual_tools: dict) -> list[str]:
    lines: list[str] = []
    for name in sorted(set(expected_tools) - set(actual_tools)):
        lines.append(f"removed tool: {name}")
    for name in sorted(set(actual_tools) - set(expected_tools)):
        lines.append(f"added tool: {name}")
    for name in sorted(set(expected_tools) & set(actual_tools)):
        _diff_node(name, expected_tools[name], actual_tools[name], "", lines)
    return lines


def check_golden(surface: dict, fixture_path: Path, environ=None) -> list[str]:
    """Compare ``surface`` to the fixture. Returns diff lines (empty means
    match). Writes the fixture ONLY when ``WF_UPDATE_TOOL_SURFACE_GOLDEN=1``."""
    env = os.environ if environ is None else environ
    rendered = render_surface(surface)
    if env.get(UPDATE_ENV) == "1":
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_bytes(rendered)
        return []
    if not fixture_path.exists():
        return [
            f"golden fixture missing: {fixture_path} "
            f"(run the suite with {UPDATE_ENV}=1 to generate it)"
        ]
    on_disk = fixture_path.read_bytes()
    if on_disk == rendered:
        return []
    try:
        expected = json.loads(on_disk.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"golden fixture unreadable: {fixture_path}: {exc}"]
    lines = diff_surfaces(expected.get("tools", {}), surface["tools"])
    if expected.get("fixture_schema") != surface.get("fixture_schema"):
        lines.insert(0, "fixture_schema differs")
    return lines or [
        f"golden fixture bytes differ from the live rendering without a "
        f"semantic diff (formatting or newline drift): {fixture_path}"
    ]


def parity_errors(registered: set[str], tiers, runner_tools) -> list[str]:
    """Bidirectional roster parity over the COMPLETE registered set."""
    roster = set(tiers)
    errors = []
    for name in sorted(registered - roster):
        errors.append(f"registered but not in roster: {name}")
    for name in sorted(roster - registered):
        errors.append(f"in roster but not registered: {name}")
    for name in sorted(set(runner_tools) - registered):
        errors.append(f"runner survivor not registered: {name}")
    return errors


# ---------------------------------------------------------------------------
# Booting the real server with a stub handler
# ---------------------------------------------------------------------------

def _stub_handler(root: Path):
    return types.SimpleNamespace(root=root.resolve(), close=lambda: None)


class _BootedSurface(unittest.TestCase):
    """Per-method boot (reload-sensitive: server.py is re-executed by
    load_server, so class-level sharing is deliberately avoided)."""

    def setUp(self):
        self.impl = load_server()
        self.runner = load_thin_runner()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        fw = self.root / ".wavefoundry" / "framework"
        fw.mkdir(parents=True, exist_ok=True)
        (fw / "VERSION").write_text("test-pack-version", encoding="utf-8")
        scripts_dir = str(SCRIPTS_DIR)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import mcp_tool_roster as roster

        self.roster = roster
        with patch.object(self.impl, "build_handler", return_value=_stub_handler(self.root)):
            try:
                self.mcp = self.runner.build_server(self.root)
            except ImportError:
                self.skipTest("mcp package not installed")

    def tearDown(self):
        self.tmp.cleanup()

    def surface(self) -> dict:
        return serialize_surface(self.mcp, self.roster.TOOL_TIERS)


# ---------------------------------------------------------------------------
# Golden snapshot
# ---------------------------------------------------------------------------

class ToolSurfaceGoldenTests(_BootedSurface):

    def test_boot_wrote_nothing_beyond_the_fixture_repo(self):
        # Requirement 1: no index build, no monitor, no repository writes.
        created = sorted(
            str(p.relative_to(self.root))
            for p in self.root.rglob("*")
            if p.is_file()
        )
        self.assertEqual(
            created,
            [".wavefoundry/framework/VERSION", "docs/workflow-config.json"],
        )

    def test_live_surface_matches_committed_golden(self):
        # AC-1 / Requirement 3: the committed fixture equals the live surface.
        # This is the ONE test that honours WF_UPDATE_TOOL_SURFACE_GOLDEN=1 and
        # rewrites the committed fixture (Requirement 4); every other test pins
        # the flag with patch.dict against temporary fixtures.
        lines = check_golden(self.surface(), GOLDEN_PATH)
        self.assertEqual(
            lines,
            [],
            "public tool surface drifted from fixtures/tool-surface-golden.json; "
            "if the change is intentional, name it in the change doc and rerun with "
            f"{UPDATE_ENV}=1:\n" + "\n".join(lines),
        )

    def test_serialization_is_byte_stable_in_process(self):
        # AC-1: two consecutive generations are identical bytes, LF only.
        first = render_surface(self.surface())
        second = render_surface(self.surface())
        self.assertEqual(first, second)
        self.assertNotIn(b"\r", first)
        self.assertTrue(first.endswith(b"\n"))
        first.decode("utf-8")  # must be valid UTF-8

    def test_committed_fixture_uses_lf_and_utf8(self):
        raw = GOLDEN_PATH.read_bytes()
        self.assertNotIn(b"\r", raw)
        raw.decode("utf-8")
        self.assertEqual(json.loads(raw)["fixture_schema"], FIXTURE_SCHEMA)

    def test_surface_covers_implementation_tools_and_runner_survivors(self):
        # Requirement 1/5: survivors captured from actual registration.
        tools = self.surface()["tools"]
        for name in self.roster.RUNNER_TOOLS:
            self.assertIn(name, tools)
            self.assertEqual(tools[name]["tier"], self.roster.TOOL_TIERS[name])
            self.assertIsInstance(tools[name]["inputSchema"], dict)
        # Every entry carries a tier from the roster; none is unknown.
        self.assertNotIn(None, {entry["tier"] for entry in tools.values()})

    def _golden_in_temp(self, surface: dict) -> Path:
        path = Path(self.tmp.name) / "golden-copy.json"
        path.write_bytes(render_surface(surface))
        return path

    def test_mutations_are_named_per_tool_and_key(self):
        # AC-2: five drift classes, each named with tool and key.
        base = self.surface()
        golden = self._golden_in_temp(base)
        default_tool = next(
            name for name, entry in sorted(base["tools"].items())
            if any("default" in p for p in entry["inputSchema"].get("properties", {}).values())
        )
        default_prop = next(
            prop for prop, spec in base["tools"][default_tool]["inputSchema"]["properties"].items()
            if "default" in spec
        )
        survivor = sorted(self.roster.RUNNER_TOOLS)[0]
        cases = {
            "added parameter": (
                lambda s: s["tools"]["wf_help"]["inputSchema"]["properties"].__setitem__(
                    "extra_param", {"type": "string"}
                ),
                ["wf_help", "inputSchema/properties/extra_param"],
            ),
            "removed tool": (
                lambda s: s["tools"].__delitem__("code_ask"),
                ["removed tool: code_ask"],
            ),
            "flipped annotation": (
                lambda s: s["tools"]["wf_help"]["annotations"].__setitem__(
                    "readOnlyHint", not s["tools"]["wf_help"]["annotations"]["readOnlyHint"]
                ),
                ["wf_help", "annotations/readOnlyHint"],
            ),
            "nested default change": (
                lambda s: s["tools"][default_tool]["inputSchema"]["properties"][default_prop]
                .__setitem__("default", "__mutated__"),
                [default_tool, f"inputSchema/properties/{default_prop}/default"],
            ),
            "survivor schema change": (
                lambda s: s["tools"][survivor]["inputSchema"]["properties"].__setitem__(
                    "surprise", {"type": "integer"}
                ),
                [survivor, "inputSchema/properties/surprise"],
            ),
        }
        for label, (mutate, expected_fragments) in cases.items():
            with self.subTest(case=label):
                mutated = copy.deepcopy(base)
                mutate(mutated)
                lines = check_golden(mutated, golden, environ={})
                self.assertTrue(lines, f"{label}: mutation was not detected")
                joined = "\n".join(lines)
                for fragment in expected_fragments:
                    self.assertIn(fragment, joined, f"{label}: diff does not name {fragment!r}")

    def test_prose_description_is_excluded_but_a_property_named_description_survives(self):
        # AC-2 second clause. Live schemas carry no prose description today,
        # so the clause is exercised by injecting one into the live registry.
        base = self.surface()
        tool = self.mcp._tool_manager._tools["wf_help"]
        original_params = copy.deepcopy(tool.parameters)
        try:
            tool.parameters["description"] = "prose at the schema root"
            for spec in tool.parameters["properties"].values():
                spec["description"] = "prose at a property node"
            self.assertEqual(
                render_surface(self.surface()), render_surface(base),
                "a prose-only description edit must not change the snapshot",
            )
            tool.parameters["properties"]["description"] = {"type": "string"}
            with_prop = self.surface()
            self.assertIn(
                "description", with_prop["tools"]["wf_help"]["inputSchema"]["properties"],
                "an input property literally named description must be covered",
            )
            self.assertNotIn("description", with_prop["tools"]["wf_help"]["inputSchema"])
            self.assertTrue(
                check_golden(with_prop, self._golden_in_temp(base), environ={}),
                "adding a property named description must be detected as drift",
            )
        finally:
            tool.parameters.clear()
            tool.parameters.update(original_params)

    def test_regeneration_is_explicit_and_isolated(self):
        # AC-3: with the flag the temp fixture is rewritten and passes; without
        # it a stale fixture fails and is left untouched; the committed fixture
        # is never touched either way.
        committed_before = GOLDEN_PATH.read_bytes()
        # The outer process may legitimately carry the flag (that is exactly
        # how the contributing doc says to regenerate), so "no leak" means the
        # flag's presence is unchanged by this test, not that it is absent.
        flag_before = os.environ.get(UPDATE_ENV)
        base = self.surface()
        temp_fixture = Path(self.tmp.name) / "regen" / "golden.json"

        with patch.dict(os.environ, {UPDATE_ENV: "1"}, clear=False):
            self.assertEqual(check_golden(base, temp_fixture), [])
        self.assertEqual(temp_fixture.read_bytes(), render_surface(base))

        stale = copy.deepcopy(base)
        del stale["tools"]["wf_help"]
        temp_fixture.write_bytes(render_surface(stale))
        stale_bytes = temp_fixture.read_bytes()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(UPDATE_ENV, None)
            lines = check_golden(base, temp_fixture)
        self.assertTrue(any("added tool: wf_help" in line for line in lines), lines)
        self.assertEqual(temp_fixture.read_bytes(), stale_bytes, "no write without the flag")

        missing = Path(self.tmp.name) / "never" / "golden.json"
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(UPDATE_ENV, None)
            lines = check_golden(base, missing)
        self.assertTrue(lines and "missing" in lines[0])
        self.assertFalse(missing.exists(), "a missing fixture is reported, never created")

        self.assertEqual(GOLDEN_PATH.read_bytes(), committed_before)
        self.assertEqual(
            os.environ.get(UPDATE_ENV), flag_before, "update flag must not leak"
        )


# ---------------------------------------------------------------------------
# Runtime roster parity
# ---------------------------------------------------------------------------

class RosterRuntimeParityTests(_BootedSurface):

    def test_registered_set_equals_roster_both_ways(self):
        # AC-4 / Requirement 5: complete set, survivors included, no literal count.
        registered = set(self.mcp._tool_manager._tools)
        self.assertEqual(parity_errors(registered, self.roster.TOOL_TIERS, self.roster.RUNNER_TOOLS), [])
        self.assertTrue(set(self.roster.RUNNER_TOOLS) <= registered)
        # Implementation-side complement: registered minus survivors equals
        # roster minus survivors (what register_mcp_surface's warning compares).
        runner = set(self.roster.RUNNER_TOOLS)
        self.assertEqual(registered - runner, set(self.roster.TOOL_TIERS) - runner)

    def test_parity_fails_in_both_directions(self):
        registered = set(self.mcp._tool_manager._tools)
        with patch.dict(self.roster.TOOL_TIERS, {"wf_ghost_tool": self.roster.TIER_READ}):
            errors = parity_errors(registered, self.roster.TOOL_TIERS, self.roster.RUNNER_TOOLS)
        self.assertEqual(errors, ["in roster but not registered: wf_ghost_tool"])
        errors = parity_errors(
            registered | {"wf_unlisted_tool"}, self.roster.TOOL_TIERS, self.roster.RUNNER_TOOLS
        )
        self.assertEqual(errors, ["registered but not in roster: wf_unlisted_tool"])
        errors = parity_errors(
            registered - set(self.roster.RUNNER_TOOLS),
            self.roster.TOOL_TIERS,
            self.roster.RUNNER_TOOLS,
        )
        self.assertTrue(any(line.startswith("runner survivor not registered") for line in errors))


# ---------------------------------------------------------------------------
# Wrapper composition order
# ---------------------------------------------------------------------------

class WrapperOrderTests(unittest.TestCase):
    """Requirement 6 / AC-5. The three wrapper passes are invoked by
    module-global name at the tail of ``register_mcp_surface``; rebinding
    those names before a fresh registration permutes the REAL application
    order without editing production code. Inner effects are instrumented
    through the registered callable of a triple-wrapped tool."""

    EXPECTED_PASS = ["guard", "lock_enter", "fn", "cost", "lock_exit"]
    EXPECTED_BLOCK = ["guard"]

    def setUp(self):
        self.impl = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name)).resolve()
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            self.skipTest("mcp package not installed")
        self.FastMCP = FastMCP
        self.originals = {name: getattr(self.impl, name) for name in _WRAPPER_NAMES}

    def tearDown(self):
        self.tmp.cleanup()

    def _observe(self, order: tuple[str, ...], *, block: bool) -> list[str]:
        events: list[str] = []

        @contextlib.contextmanager
        def fake_lock(root):
            events.append("lock_enter")
            try:
                yield
            finally:
                events.append("lock_exit")

        def fake_block_reason(root, tool_name):
            events.append("guard")
            return "upgrade_in_progress: test checkpoint" if block else None

        def fake_response(*args, **kwargs):
            events.append("fn")
            return {"status": "ok", "data": {}, "diagnostics": []}

        class Telemetry:
            focus = types.SimpleNamespace(wave_id="", stage="general")

            def record_tool_cost(self, *args, **kwargs):
                events.append("cost")

        # The registered closure reads handler.root and passes handler.cache
        # through to the (patched) response function; nothing else is touched.
        handler = types.SimpleNamespace(root=self.root, telemetry=Telemetry(), cache=None)
        rebinding = {slot: self.originals[actual] for slot, actual in zip(_WRAPPER_NAMES, order)}
        with contextlib.ExitStack() as stack:
            for slot, fn in rebinding.items():
                stack.enter_context(patch.object(self.impl, slot, fn))
            stack.enter_context(patch.object(self.impl, "_lifecycle_mutation_lock", fake_lock))
            stack.enter_context(
                patch.object(self.impl.publication_control, "publication_block_reason", fake_block_reason)
            )
            stack.enter_context(
                patch.object(self.impl.publication_control, "publication_checkpoint_reason", lambda *a, **k: None)
            )
            stack.enter_context(patch.object(self.impl, _TRIPLE_WRAPPED_RESPONSE, fake_response))
            mcp = self.FastMCP("wrapper-order-probe")
            self.impl.register_mcp_surface(mcp, lambda: handler)
            tool = mcp._tool_manager._tools[_TRIPLE_WRAPPED_TOOL]
            tool.fn(wave_id="1abc", change_id="1abd", mode="dry_run")
        return events

    def test_subject_is_wrapped_by_all_three_passes(self):
        import publication_control

        self.assertIn(_TRIPLE_WRAPPED_TOOL, self.impl._LIFECYCLE_MUTATION_LOCK_TOOLS)
        self.assertIn(_TRIPLE_WRAPPED_TOOL, publication_control.registered_publication_tool_names())
        self.assertNotIn(_TRIPLE_WRAPPED_TOOL, self.impl._COST_EXEMPT_TOOLS)

    def test_production_order_is_cost_inner_lock_middle_guard_outer(self):
        identity = _WRAPPER_NAMES
        self.assertEqual(self._observe(identity, block=False), self.EXPECTED_PASS)
        self.assertEqual(self._observe(identity, block=True), self.EXPECTED_BLOCK)

    def test_every_other_permutation_is_distinguishable(self):
        # Negative controls: each of the five wrong application orders yields
        # an event sequence the assertions above would reject.
        wrong = [p for p in itertools.permutations(_WRAPPER_NAMES) if p != _WRAPPER_NAMES]
        self.assertEqual(len(wrong), 5)
        for order in wrong:
            with self.subTest(order=order):
                observed = (self._observe(order, block=False), self._observe(order, block=True))
                self.assertNotEqual(observed, (self.EXPECTED_PASS, self.EXPECTED_BLOCK))


if __name__ == "__main__":
    unittest.main()
