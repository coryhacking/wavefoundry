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
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from server_tools_support import _make_repo, load_server, load_thin_runner
from declaration_support import apply_base_declaration, base_declaration
from record_layout_support import PROFILES_DIR, SHIPPED_DECLARATION
# Wave 1zyb3 (change 1zxnu): the serializer lives in one stdlib-only support
# module, which the subprocess boot imports from a scratch copy.
from tool_surface_support import (  # noqa: F401 - re-exported for sibling tests
    FIXTURE_SCHEMA,
    _canonical_schema,
    _stub_handler,
    serialize_surface,
    strip_prose_descriptions,
)

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
GOLDEN_PATH = TESTS_DIR / "fixtures" / "tool-surface-golden.json"
# Wave 1zyc3 (1zyc2): one golden per declaring profile asset.
PROFILE_GOLDEN_DIR = TESTS_DIR / "fixtures" / "tool-surface-golden"
UPDATE_ENV = "WF_UPDATE_TOOL_SURFACE_GOLDEN"

_WRAPPER_NAMES = (
    "_wrap_first_party_tool_costs",
    "_wrap_lifecycle_mutation_lock",
    "_wrap_upgrade_publication_guard",
)
# A tool covered by ALL three wrapper passes: in _LIFECYCLE_MUTATION_LOCK_TOOLS,
# in publication_control's writer registry, first-party prefixed, and NOT in
# _COST_EXEMPT_TOOLS (which excludes wf_prepare_wave and four siblings).
# Each wrapper's main-pass keywords come from a provider read by global name
# at call time (wave 1zimf); a permuted slot must pass the keywords of the
# wrapper bound there, not of the slot (Waveforge R1, wave 1zv88).
_KWARGS_PROVIDERS = {
    "_wrap_first_party_tool_costs": "_cost_pass_kwargs",
    "_wrap_lifecycle_mutation_lock": "_lock_pass_kwargs",
    "_wrap_upgrade_publication_guard": "_guard_pass_kwargs",
}
_TRIPLE_WRAPPED_TOOL = "wf_add_change"
_TRIPLE_WRAPPED_RESPONSE = "wf_add_change_response"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

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
        # Write only on a real change, so a no-op regeneration leaves the
        # tree untouched for the runner's repository-state guard.
        if not fixture_path.exists() or fixture_path.read_bytes() != rendered:
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

class _BootedSurface(unittest.TestCase):
    """Per-method boot (reload-sensitive: server.py is re-executed by
    load_server, so class-level sharing is deliberately avoided)."""

    def setUp(self):
        self.impl = load_server()
        self.runner = load_thin_runner()
        # The subject is the shipped surface: boot it on the shipped empty
        # declaration, whatever a distribution declares (change 1zim4).
        apply_base_declaration(self)
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
        # An unchanged regeneration leaves the file untouched (no rewrite),
        # so the runner's repository-state guard sees no change.
        os.utime(temp_fixture, ns=(1_000_000_000, 1_000_000_000))
        with patch.dict(os.environ, {UPDATE_ENV: "1"}, clear=False):
            self.assertEqual(check_golden(base, temp_fixture), [])
        self.assertEqual(temp_fixture.stat().st_mtime_ns, 1_000_000_000)

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
# Per-profile goldens (wave 1zyc3, change 1zyc2)
# ---------------------------------------------------------------------------

def profile_declaration(asset: dict) -> dict:
    """The asset's ``mcp_tool_extensions`` entry alone, with JSON lists
    coerced to the tuples the declaration module requires (as
    ``record_layout_support.apply_profile`` does). Record-layout and
    vocabulary parts of the asset are ignored."""
    entry = (asset.get("modules") or {}).get("mcp_tool_extensions") or {}
    declaration = {}
    for name, value in entry.items():
        if isinstance(SHIPPED_DECLARATION.get(name), tuple) and isinstance(value, list):
            value = tuple(value)
        declaration[name] = value
    return declaration


def declaring_profile_assets(profiles_dir: Path = PROFILES_DIR) -> dict[str, dict]:
    """Every profile asset whose ``mcp_tool_extensions`` entry declares
    anything, by name; active or not."""
    assets = {}
    for path in sorted(Path(profiles_dir).glob("*.json")):
        asset = json.loads(path.read_text(encoding="utf-8"))
        if any(profile_declaration(asset).values()):
            assets[path.stem] = asset
    return assets


def profile_golden_path(name: str, golden_dir: Path = PROFILE_GOLDEN_DIR) -> Path:
    return Path(golden_dir) / f"{name}.json"


def declares_modules(asset: dict) -> bool:
    """Whether the asset declares an extension or helper module, which only a
    scratch copy of the scripts tree can serve (wave 1zyb3, change 1zxnu)."""
    declaration = profile_declaration(asset)
    return bool(declaration.get("EXTENSION_MODULES") or declaration.get("EXTENSION_HELPER_MODULES"))


# Boots the server in a scratch copy made by ``copy_scripts_tree`` and
# ``apply_profile`` (wave 1zyb3, change 1zxnu). ``_load_extension_module`` loads
# a declared module only from the real scripts directory, so a module-declaring
# asset is served from the copy, in its own interpreter. Prints one JSON line.
_SCRATCH_BOOT_DRIVER = r"""
import importlib.util, json, sys
from pathlib import Path
from unittest.mock import patch
scripts = Path(sys.argv[1])
spec = json.loads(sys.argv[2])
sys.path.insert(0, str(scripts))
sys.path.insert(0, str(scripts / "tests"))
from declaration_support import base_declaration
from record_layout_support import SHIPPED_DECLARATION
from tool_surface_support import _stub_handler, serialize_surface

def emit(**out):
    print(json.dumps(out))
    sys.exit(0)

declaration = {name: tuple(value) if isinstance(SHIPPED_DECLARATION.get(name), tuple) else value
               for name, value in spec["declaration"].items()}
root = Path(spec["root"])
(root / "docs").mkdir(parents=True, exist_ok=True)
(root / "docs" / "workflow-config.json").write_text(json.dumps(
    {"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}), encoding="utf-8")
fw = root / ".wavefoundry" / "framework"
fw.mkdir(parents=True, exist_ok=True)
(fw / "VERSION").write_text("test-pack-version", encoding="utf-8")
try:
    server_spec = importlib.util.spec_from_file_location("server", scripts / "server.py")
    runner = importlib.util.module_from_spec(server_spec)
    sys.modules["server"] = runner
    server_spec.loader.exec_module(runner)
except ImportError as exc:
    emit(skip=f"mcp package not installed: {exc}")
impl = sys.modules["server_impl"]
import mcp_tool_extensions
import mcp_tool_roster as roster
with base_declaration(**declaration):
    try:
        tiers = roster.all_tool_tiers()
    except mcp_tool_extensions.ExtensionDeclarationError as exc:
        emit(problems=[f"invalid declaration: {exc}"])
    with patch.object(impl, "build_handler", return_value=_stub_handler(root)):
        try:
            mcp = runner.build_server(root)
        except ImportError as exc:
            emit(skip=f"mcp package not installed: {exc}")
        except Exception as exc:  # noqa: BLE001 - a boot refusal is the failure
            emit(problems=[f"server refused the declaration: {exc}"])
    for tool, properties in spec["schema_patch"].items():
        mcp._tool_manager._tools[tool].parameters["properties"].update(properties)
    emit(surface=serialize_surface(mcp, tiers))
"""

# The subprocess boot copies the scripts tree and starts the server; a loaded
# machine must not fail it, so the timeout is generous.
SCRATCH_BOOT_TIMEOUT_SECONDS = 300


class ProfileToolSurfaceGoldenTests(unittest.TestCase):
    """Requirement 2: each declaring profile asset boots the server exactly
    as the shipped golden test does, on the shipped-empty declaration plus
    that asset's tool declaration alone, and compares the served surface
    (tiers from ``all_tool_tiers()``) with its own golden.

    An asset that declares extension or helper modules boots in a scratch
    copy of the scripts tree, in a subprocess (wave 1zyb3, change 1zxnu);
    every other asset boots in process. Skills are not part of the golden:
    the server never serves them, so the declared asset's skill is pinned by
    ``DeclaredProfileSkillTests`` instead."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        scripts_dir = str(SCRIPTS_DIR)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

    def _boot(self, declaration: dict, schema_patch=None) -> "tuple[dict | None, list[str]]":
        """Serialize the surface served under ``declaration``. Returns
        ``(surface, [])`` or ``(None, problems)`` when the declaration is
        invalid or the server refuses to boot with it."""
        impl = load_server()
        runner = load_thin_runner()
        root = _make_repo(Path(tempfile.mkdtemp(dir=self.tmp.name)))
        fw = root / ".wavefoundry" / "framework"
        fw.mkdir(parents=True, exist_ok=True)
        (fw / "VERSION").write_text("test-pack-version", encoding="utf-8")
        import mcp_tool_extensions
        import mcp_tool_roster as roster

        with base_declaration(**declaration):
            try:
                tiers = roster.all_tool_tiers()
            except mcp_tool_extensions.ExtensionDeclarationError as exc:
                return None, [f"invalid declaration: {exc}"]
            with patch.object(impl, "build_handler", return_value=_stub_handler(root)):
                try:
                    mcp = runner.build_server(root)
                except ImportError:
                    self.skipTest("mcp package not installed")
                except Exception as exc:  # noqa: BLE001 - a boot refusal is the failure
                    return None, [f"server refused the declaration: {exc}"]
            for tool, properties in (schema_patch or {}).items():
                mcp._tool_manager._tools[tool].parameters["properties"].update(properties)
            return serialize_surface(mcp, tiers), []

    def _boot_in_scratch(self, asset: dict, schema_patch=None,
                         module_sources=None) -> "tuple[dict | None, list[str]]":
        """The surface a module-declaring asset serves, booted from a scratch
        copy with the asset applied; ``module_sources`` replaces a copied
        module's source after the asset is applied."""
        from record_layout_support import ProfileInvalid, apply_profile, copy_scripts_tree

        scratch = Path(tempfile.mkdtemp(dir=self.tmp.name))
        scripts = copy_scripts_tree(scratch / "framework")
        try:
            apply_profile(scripts, asset)
        except ProfileInvalid as exc:
            return None, [f"invalid declaration: {exc}"]
        for module, source in (module_sources or {}).items():
            (scripts / f"{module}.py").write_text(source, encoding="utf-8")
        spec = {"declaration": profile_declaration(asset), "root": str(scratch / "repo"),
                "schema_patch": schema_patch or {}}
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, "-B", "-c", _SCRATCH_BOOT_DRIVER, str(scripts), json.dumps(spec)],
            cwd=str(scripts), env=env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False, timeout=SCRATCH_BOOT_TIMEOUT_SECONDS,
        )
        lines = result.stdout.strip().splitlines()
        if result.returncode != 0 or not lines:
            self.fail(f"scratch boot failed (exit {result.returncode}): {result.stderr[-4000:]}")
        out = json.loads(lines[-1])
        if out.get("skip"):
            self.skipTest(out["skip"])
        if out.get("problems"):
            return None, out["problems"]
        return out["surface"], []

    def _check(self, asset: dict, fixture: Path, environ=None, schema_patch=None,
               module_sources=None) -> list[str]:
        if declares_modules(asset):
            surface, problems = self._boot_in_scratch(asset, schema_patch, module_sources)
        else:
            surface, problems = self._boot(profile_declaration(asset), schema_patch)
        if problems:
            return problems
        return check_golden(surface, fixture, environ)

    def test_each_declaring_profile_matches_its_golden(self):
        # AC-1: honours WF_UPDATE_TOOL_SURFACE_GOLDEN=1 like the shipped test.
        assets = declaring_profile_assets()
        self.assertIn("declared", assets)
        for name, asset in assets.items():
            with self.subTest(profile=name):
                fixture = profile_golden_path(name)
                lines = self._check(asset, fixture)
                self.assertEqual(
                    lines, [],
                    f"tool surface served under profile {name!r} drifted from {fixture.name}; "
                    "if the change is intentional, name it in the change doc and rerun with "
                    f"{UPDATE_ENV}=1:\n" + "\n".join(lines),
                )

    def test_declared_golden_carries_aliases_tiers_and_mapped_parameters(self):
        # AC-1: the committed fixture, read independently of the live boot.
        golden = json.loads(profile_golden_path("declared").read_bytes().decode("utf-8"))
        tools = golden["tools"]
        self.assertEqual(tools["wf_alias_help"]["tier"], tools["wf_help"]["tier"])
        self.assertEqual(tools["wf_alias_read_raw"]["tier"], tools["code_read"]["tier"])
        props = tools["wf_alias_read_raw"]["inputSchema"]["properties"]
        self.assertIn("file", props)
        self.assertNotIn("path", props)
        self.assertNotIn("with_line_numbers", props)
        self.assertIn("with_line_numbers", tools["code_read"]["inputSchema"]["properties"])
        shipped = json.loads(GOLDEN_PATH.read_bytes().decode("utf-8"))["tools"]
        self.assertNotIn("wf_alias_help", shipped)
        # Wave 1zyb3 (change 1zxnu): the added names are the aliases, the
        # module tool and the alias_for_core name; the hidden name is gone.
        self.assertEqual(set(tools) - set(shipped), {
            "wf_alias_help", "wf_alias_read_raw", "wf_alias_gpu_doctor",
            "dist_inventory", "dist_open_dashboard_core"})
        self.assertEqual(set(shipped) - set(tools), {"wf_gpu_doctor"})

    def test_declared_golden_pins_module_hidden_and_replaced_tools(self):
        # Wave 1zyb3 (change 1zxnu) AC-9: the committed fixture alone.
        tools = json.loads(profile_golden_path("declared").read_bytes().decode("utf-8"))["tools"]
        shipped = json.loads(GOLDEN_PATH.read_bytes().decode("utf-8"))["tools"]
        asset = declaring_profile_assets()["declared"]
        declaration = asset["modules"]["mcp_tool_extensions"]
        # The module tool: its declared tier and its own schema.
        inventory = tools["dist_inventory"]
        self.assertEqual(inventory["tier"], declaration["EXTENSION_TOOL_TIERS"]["dist_inventory"])
        self.assertEqual(set(inventory["inputSchema"]["properties"]),
                         {"area", "limit", "kinds", "include_archived"})
        self.assertEqual(inventory["inputSchema"].get("required"), ["area"])
        # The hidden canonical name is absent; its alias serves the core schema and tier.
        self.assertNotIn("wf_gpu_doctor", tools)
        self.assertEqual(tools["wf_alias_gpu_doctor"]["inputSchema"], shipped["wf_gpu_doctor"]["inputSchema"])
        self.assertEqual(tools["wf_alias_gpu_doctor"]["tier"], shipped["wf_gpu_doctor"]["tier"])
        # The replaced core name serves the module's schema; alias_for_core the core one.
        self.assertEqual(set(tools["wf_open_dashboard"]["inputSchema"]["properties"]), {"view"})
        self.assertNotEqual(tools["wf_open_dashboard"]["inputSchema"], shipped["wf_open_dashboard"]["inputSchema"])
        self.assertEqual(tools["dist_open_dashboard_core"]["inputSchema"],
                         shipped["wf_open_dashboard"]["inputSchema"])
        self.assertEqual(tools["dist_open_dashboard_core"]["tier"], shipped["wf_open_dashboard"]["tier"])
        self.assertEqual(tools["wf_open_dashboard"]["tier"], shipped["wf_open_dashboard"]["tier"])

    def test_module_declaring_asset_boots_in_scratch(self):
        asset = declaring_profile_assets()["declared"]
        self.assertTrue(declares_modules(asset))
        self.assertFalse(declares_modules({"modules": {"mcp_tool_extensions": {
            "EXTENSION_TOOL_ALIASES": {"wf_alias_help": "wf_help"}}}}))
        self.assertGreaterEqual(SCRATCH_BOOT_TIMEOUT_SECONDS, 300)
        with patch.object(self, "_boot", side_effect=AssertionError("in-process boot used")):
            surface, problems = self._boot_in_scratch(asset)
        self.assertEqual(problems, [])
        self.assertIn("dist_inventory", surface["tools"])

    def test_profile_goldens_use_lf_and_utf8(self):
        for name in declaring_profile_assets():
            with self.subTest(profile=name):
                raw = profile_golden_path(name).read_bytes()
                self.assertNotIn(b"\r", raw)
                raw.decode("utf-8")
                self.assertEqual(json.loads(raw)["fixture_schema"], FIXTURE_SCHEMA)

    def test_declaration_drift_fails_with_a_per_tool_diff(self):
        # AC-2: each mutation goes through the declaration or the served
        # registry, never through shipped code, against the committed golden.
        asset = declaring_profile_assets()["declared"]
        fixture = profile_golden_path("declared")
        base = profile_declaration(asset)

        def with_entry(**changes):
            entry = copy.deepcopy(asset)
            entry["modules"]["mcp_tool_extensions"].update(changes)
            return entry

        fixture_module = (PROFILES_DIR / asset["module_files"]["dist_tools"]).read_text(encoding="utf-8")
        replacements = {k: v for k, v in base["EXTENSION_REPLACEMENTS"].items() if k != "dist_tools"}
        without_replacement = fixture_module[:fixture_module.index("    @mcp.tool()\n    def wf_open_dashboard")]

        cases = {
            "mapping": (
                with_entry(EXTENSION_TOOL_PARAMETERS={"wf_alias_read_raw": {
                    "rename": {"filename": "path"}, "fixed": {"with_line_numbers": False}}}),
                {}, None,
                ["wf_alias_read_raw", "inputSchema/properties/filename"],
            ),
            "pinned parameter": (
                with_entry(EXTENSION_TOOL_PARAMETERS={"wf_alias_read_raw": {
                    "rename": {"file": "path"}}}),
                {}, None,
                ["wf_alias_read_raw", "inputSchema/properties/with_line_numbers"],
            ),
            "tier and target": (
                with_entry(EXTENSION_TOOL_ALIASES={**base["EXTENSION_TOOL_ALIASES"],
                                                   "wf_alias_help": "wf_review_event"}),
                {}, None,
                ["wf_alias_help: changed key tier", "wf_alias_help", "inputSchema/properties/wave_id"],
            ),
            "core schema under the profile": (
                asset, {}, {"wf_help": {"surprise": {"type": "integer"}}},
                ["wf_help", "inputSchema/properties/surprise"],
            ),
            # Wave 1zyb3 (change 1zxnu) AC-10.
            "module tool schema": (
                asset, {"dist_tools": fixture_module.replace("limit: int = 10", "limit: str = '10'")}, None,
                ["dist_inventory: changed key inputSchema/properties/limit"],
            ),
            "hidden tool un-hidden": (
                with_entry(EXTENSION_HIDDEN_TOOLS=[]), {}, None,
                ["added tool: wf_gpu_doctor"],
            ),
            "replacement dropped": (
                with_entry(EXTENSION_REPLACEMENTS=replacements), {"dist_tools": without_replacement}, None,
                ["removed tool: dist_open_dashboard_core", "wf_open_dashboard: ", "inputSchema/properties"],
            ),
        }
        for label, (mutated, module_sources, schema_patch, fragments) in cases.items():
            with self.subTest(case=label):
                lines = self._check(mutated, fixture, environ={}, schema_patch=schema_patch,
                                    module_sources=module_sources)
                self.assertTrue(lines, f"{label}: drift was not detected")
                joined = "\n".join(lines)
                for fragment in fragments:
                    self.assertIn(fragment, joined, f"{label}: diff does not name {fragment!r}")

    def test_regeneration_writes_only_goldens_and_is_byte_stable(self):
        # AC-2: two regenerations into a temporary golden directory.
        golden_dir = Path(self.tmp.name) / "regen"
        assets = declaring_profile_assets()
        committed = {name: profile_golden_path(name).read_bytes() for name in assets}
        generations = []
        for _ in range(2):
            for name, asset in assets.items():
                self.assertEqual(
                    self._check(asset, profile_golden_path(name, golden_dir), environ={UPDATE_ENV: "1"}), []
                )
            generations.append({p.name: p.read_bytes() for p in sorted(golden_dir.iterdir())})
        self.assertEqual(generations[0], generations[1])
        self.assertEqual(sorted(generations[0]), sorted(f"{name}.json" for name in assets))
        for name in assets:
            self.assertEqual(generations[0][f"{name}.json"], committed[name])
            self.assertNotIn(b"\r", generations[0][f"{name}.json"])

    def test_missing_golden_names_the_file_and_the_flag(self):
        # AC-3.
        asset = declaring_profile_assets()["declared"]
        missing = profile_golden_path("declared", Path(self.tmp.name) / "empty")
        lines = self._check(asset, missing, environ={})
        self.assertEqual(len(lines), 1)
        self.assertIn(str(missing), lines[0])
        self.assertIn(UPDATE_ENV, lines[0])
        self.assertFalse(missing.exists())

    def test_invalid_declaration_fails_with_its_problems(self):
        # AC-3: an asset in a temporary profiles directory, never a golden.
        profiles = Path(self.tmp.name) / "profiles"
        profiles.mkdir()
        (profiles / "broken.json").write_text(json.dumps({"modules": {"mcp_tool_extensions": {
            "EXTENSION_TOOL_ALIASES": {"wf_alias_ghost": "wf_no_such_tool"}}}}), encoding="utf-8")
        (profiles / "plain.json").write_text(json.dumps({"modules": {"record_paths": {
            "NESTED": True}}}), encoding="utf-8")
        assets = declaring_profile_assets(profiles)
        self.assertEqual(list(assets), ["broken"])
        fixture = profile_golden_path("broken", Path(self.tmp.name) / "goldens")
        lines = self._check(assets["broken"], fixture, environ={UPDATE_ENV: "1"})
        self.assertEqual(len(lines), 1)
        self.assertIn("invalid declaration", lines[0])
        self.assertIn("wf_alias_ghost", lines[0])
        self.assertFalse(fixture.exists(), "an invalid declaration produces no golden")

    def test_list_values_become_tuples(self):
        declaration = profile_declaration({"modules": {"mcp_tool_extensions": {
            "EXTENSION_HIDDEN_TOOLS": ["wf_help"], "EXTENSION_TOOL_ALIASES": {"a": "b"}}}})
        self.assertEqual(declaration["EXTENSION_HIDDEN_TOOLS"], ("wf_help",))
        self.assertEqual(declaration["EXTENSION_TOOL_ALIASES"], {"a": "b"})


class DeclaredProfileSkillTests(unittest.TestCase):
    """Wave 1zyb3 (change 1zxnu) AC-12: skills sit outside the golden format
    (the server never serves them), so the ``declared`` asset's skill is
    pinned here by rendering a temporary repository under its declaration."""

    def test_declared_asset_renders_its_marked_skill_and_template_prompt_doc(self):
        import time

        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        import render_agent_surfaces as ras

        declaration = profile_declaration(declaring_profile_assets()["declared"])
        (name, spec), = declaration["EXTENSION_SKILLS"].items()
        template = SCRIPTS_DIR.parent / "install" / spec["prompt_doc_template"]
        with tempfile.TemporaryDirectory() as temp_dir, base_declaration(**declaration):
            root = Path(temp_dir)
            hosts = (".codex", ".claude", ".agents")
            for host in hosts:
                (root / host).mkdir()
            written = ras.render_agent_surfaces(root)
            self.assertIn(spec["prompt_doc"], written)
            self.assertEqual(
                (root / spec["prompt_doc"]).read_text(encoding="utf-8"),
                template.read_text(encoding="utf-8").replace("{{generated_at}}", time.strftime("%Y-%m-%d")),
            )
            for host in hosts:
                skill = (root / host / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertTrue(ras.has_declared_skill_marker(skill), host)
                self.assertIn(f"name: {name}\n", skill)
                self.assertIn(f"`{spec['prompt_doc']}`", skill)


# ---------------------------------------------------------------------------
# Runtime roster parity
# ---------------------------------------------------------------------------

class RosterRuntimeParityTests(_BootedSurface):

    def test_registered_set_equals_roster_both_ways(self):
        # AC-4 / Requirement 5: complete set, survivors included, no literal count.
        # Wave 1z8oz: compare with all_tool_tiers(), the served roster; the
        # stock declaration makes it equal TOOL_TIERS.
        registered = set(self.mcp._tool_manager._tools)
        tiers = self.roster.all_tool_tiers()
        self.assertEqual(parity_errors(registered, tiers, self.roster.RUNNER_TOOLS), [])
        self.assertTrue(set(self.roster.RUNNER_TOOLS) <= registered)
        # Implementation-side complement: registered minus survivors equals
        # roster minus survivors (what register_mcp_surface's warning compares).
        runner = set(self.roster.RUNNER_TOOLS)
        self.assertEqual(registered - runner, set(tiers) - runner)

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
        apply_base_declaration(self)
        self.originals = {name: getattr(self.impl, name) for name in _WRAPPER_NAMES}
        self.providers = {name: getattr(self.impl, provider) for name, provider in _KWARGS_PROVIDERS.items()}

    def tearDown(self):
        self.tmp.cleanup()

    def _declared_kwargs(self) -> dict[str, dict]:
        # One extension lifecycle tool and one artifact path field, fed
        # through the providers: the names need not be registered tools.
        return {
            "_wrap_lifecycle_mutation_lock": {"extension_tools": frozenset({"acme_record"})},
            "_wrap_first_party_tool_costs": {
                "artifact_extractors": {"acme_record": self.impl._artifact_from_written_paths("written_paths")},
            },
        }

    def _observe(self, order: tuple[str, ...], *, block: bool, declared: dict | None = None) -> list[str]:
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
        self.received: dict[str, dict] = {}

        def recording(actual: str):
            def wrapper(mcp, get_handler, **kwargs):
                self.received[actual] = kwargs
                return self.originals[actual](mcp, get_handler, **kwargs)
            return wrapper

        rebinding = {slot: recording(actual) for slot, actual in zip(_WRAPPER_NAMES, order)}

        def kwargs_of(actual: str):
            if declared is not None and actual in declared:
                return lambda: dict(declared[actual])
            return self.providers[actual]

        with contextlib.ExitStack() as stack:
            for slot, fn in rebinding.items():
                stack.enter_context(patch.object(self.impl, slot, fn))
            for slot, actual in zip(_WRAPPER_NAMES, order):
                stack.enter_context(patch.object(self.impl, _KWARGS_PROVIDERS[slot], kwargs_of(actual)))
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

    def test_permutations_with_declared_extension_kwargs(self):
        # A distribution that declares a lifecycle tool and an artifact field
        # gives the lock and cost passes keywords the other wrappers do not
        # accept; each slot still passes its bound wrapper's own.
        declared = self._declared_kwargs()
        received = {
            "_wrap_first_party_tool_costs": declared["_wrap_first_party_tool_costs"],
            "_wrap_lifecycle_mutation_lock": declared["_wrap_lifecycle_mutation_lock"],
            "_wrap_upgrade_publication_guard": {},
        }
        self.assertEqual(self._observe(_WRAPPER_NAMES, block=False, declared=declared), self.EXPECTED_PASS)
        self.assertEqual(self.received, received)
        self.assertEqual(self._observe(_WRAPPER_NAMES, block=True, declared=declared), self.EXPECTED_BLOCK)
        for order in itertools.permutations(_WRAPPER_NAMES):
            if order == _WRAPPER_NAMES:
                continue
            with self.subTest(order=order):
                observed = (
                    self._observe(order, block=False, declared=declared),
                    self._observe(order, block=True, declared=declared),
                )
                self.assertNotEqual(observed, (self.EXPECTED_PASS, self.EXPECTED_BLOCK))
                # Each wrapper received its own declared keywords, wherever it sat.
                self.assertEqual(self.received, received)


if __name__ == "__main__":
    unittest.main()
