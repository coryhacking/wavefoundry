from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
GEN_PATH = SCRIPTS_ROOT / "gen_codebase_map.py"


def load_gen():
    spec = importlib.util.spec_from_file_location("gen_codebase_map", GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gen_codebase_map"] = mod
    spec.loader.exec_module(mod)
    return mod


def _graph_dir(root: Path) -> Path:
    d = root / ".wavefoundry" / "index" / "graph"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_graph(root: Path, nodes, edges, builder_version="1") -> None:
    payload = {
        "schema_version": "1",
        "builder_version": builder_version,
        "layer": "project",
        "nodes": nodes,
        "edges": edges,
    }
    (_graph_dir(root) / "project-graph.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_cluster(root: Path, communities, builder_version="9") -> None:
    payload = {
        "cluster_schema_version": "1",
        "cluster_builder_version": builder_version,
        "layer": "project",
        "communities": communities,
        "community_count": len(communities),
    }
    (_graph_dir(root) / "project-graph-clusters.json").write_text(json.dumps(payload), encoding="utf-8")


def _node(nid, kind, label, source_file):
    return {"id": nid, "kind": kind, "label": label, "layer": "project", "source_file": source_file}


# --------------------------------------------------------------------------- #
# Small fixture: 2 communities -> near-flat map.
# --------------------------------------------------------------------------- #
def _build_small(root: Path) -> None:
    nodes = [
        _node("src/auth.py", "module", "auth", "src/auth.py"),
        _node("src/auth.py::login", "function", "login", "src/auth.py"),
        _node("src/auth.py::logout", "function", "logout", "src/auth.py"),
        _node("src/auth.py::Session", "class", "Session", "src/auth.py"),
        _node("api/server.py", "module", "server", "api/server.py"),
        _node("api/server.py::serve", "function", "serve", "api/server.py"),
        _node("api/server.py::Handler", "class", "Handler", "api/server.py"),
    ]
    # Give login the highest degree so it ranks as the hub of the auth area.
    edges = [
        {"source": "src/auth.py", "target": "src/auth.py::login", "relation": "defines"},
        {"source": "api/server.py::serve", "target": "src/auth.py::login", "relation": "calls"},
        {"source": "src/auth.py::Session", "target": "src/auth.py::login", "relation": "calls"},
        {"source": "api/server.py", "target": "api/server.py::serve", "relation": "defines"},
    ]
    _write_graph(root, nodes, edges)
    _write_cluster(root, [
        {
            "community_id": "project:c0",
            "label": "auth",
            "seed_node_id": "src/auth.py::login",
            "node_ids": ["src/auth.py", "src/auth.py::login", "src/auth.py::logout", "src/auth.py::Session"],
            "node_count": 4,
            "boundary_node_count": 1,
        },
        {
            "community_id": "project:c1",
            "label": "server",
            "seed_node_id": "api/server.py::serve",
            "node_ids": ["api/server.py", "api/server.py::serve", "api/server.py::Handler"],
            "node_count": 3,
            "boundary_node_count": 1,
        },
        # A fixed category that must NOT appear as a product area.
        {
            "community_id": "project:c2",
            "label": "Tests",
            "kind": "fixed",
            "seed_node_id": "tests/test_auth.py",
            "node_ids": ["tests/test_auth.py"],
            "node_count": 1,
            "boundary_node_count": 0,
        },
    ])


# --------------------------------------------------------------------------- #
# Large fixture: many communities across many directories -> bounded top tier.
# --------------------------------------------------------------------------- #
def _build_large(root: Path, n_dirs: int = 60) -> None:
    nodes = []
    edges = []
    communities = []
    for i in range(n_dirs):
        d = f"pkg{i:03d}"
        mod = f"src/{d}/mod.py"
        fn = f"{mod}::run{i}"
        cls = f"{mod}::Widget{i}"
        nodes.append(_node(mod, "module", "mod", mod))
        nodes.append(_node(fn, "function", f"run{i}", mod))
        nodes.append(_node(cls, "class", f"Widget{i}", mod))
        edges.append({"source": mod, "target": fn, "relation": "defines"})
        edges.append({"source": mod, "target": cls, "relation": "defines"})
        # Cross edge so fn accumulates degree.
        if i > 0:
            edges.append({"source": f"src/pkg{i-1:03d}/mod.py::run{i-1}", "target": fn, "relation": "calls"})
        communities.append({
            "community_id": f"project:c{i}",
            "label": f"area{i}",
            "seed_node_id": fn,
            "node_ids": [mod, fn, cls],
            "node_count": 3,
            "boundary_node_count": 1,
        })
    _write_graph(root, nodes, edges)
    _write_cluster(root, communities)


class ComputeAreasSmallTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _build_small(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_near_flat_small_map(self):
        model = self.gen.compute_areas(self.root)
        self.assertTrue(model.present)
        # Two product areas; the fixed Tests community is excluded. Tier-1 labels:
        # `src/auth.py` → `src` is a generic root, so the cluster label `auth`
        # wins; `api/server.py` → `api` is a meaningful directory segment, so the
        # directory segment wins over the symbol-derived cluster label `server`.
        names = {a.name for a in model.areas}
        self.assertIn("auth", names)
        self.assertIn("api", names)
        self.assertNotIn("Tests", names)
        self.assertEqual(model.total_area_count, len(model.areas))
        self.assertFalse(model.truncated)
        self.assertEqual(model.grouping, "package-directory")
        self.assertEqual(model.cluster_builder_version, "9")

    def test_hub_is_stable_node_id_not_community_id(self):
        model = self.gen.compute_areas(self.root)
        auth = next(a for a in model.areas if a.name == "auth")
        # Hub is the highest-degree member — login has the most edges.
        self.assertEqual(auth.hub_node_id, "src/auth.py::login")
        # Never a community_id like "project:cN".
        for a in model.areas:
            self.assertFalse(a.hub_node_id.startswith("project:c"))

    def test_entry_point_symbols_ranked_and_filtered(self):
        model = self.gen.compute_areas(self.root)
        auth = next(a for a in model.areas if a.name == "auth")
        labels = [s["label"] for s in auth.key_symbols]
        self.assertEqual(labels[0], "login")  # highest degree first
        # Only entry-point kinds (no module/file container nodes).
        for s in auth.key_symbols:
            self.assertIn(s["kind"], {"function", "method", "class", "interface", "struct", "trait", "enum"})

    def test_key_files_present_and_in_scope(self):
        model = self.gen.compute_areas(self.root)
        auth = next(a for a in model.areas if a.name == "auth")
        self.assertIn("src/auth.py", auth.key_files)

    def test_render_is_docs_lint_clean(self):
        # Write into a repo with a docs/ tree and run docs-lint scoped to the file
        # via the standalone metadata + link validators.
        model = self.gen.compute_areas(self.root)
        md = self.gen.render_markdown(model, last_verified="2026-06-16")
        # Header fields required by docs-lint metadata validator.
        self.assertIn("Owner: Engineering", md)
        self.assertIn("Status:", md)
        self.assertRegex(md, r"Last verified: \d{4}-\d{2}-\d{2}")
        # No bare (non-code) markdown links that would trip the link checker.
        self._assert_lint_clean(md)

    def _assert_lint_clean(self, md: str):
        # Reuse the actual lint validators (metadata + links) on a temp repo.
        import importlib as _il
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        mv = _il.import_module("wave_lint_lib.metadata_validators")
        lv = _il.import_module("wave_lint_lib.link_validators")
        repo = Path(self.tmp.name)
        out = repo / "docs" / "references" / "codebase-map.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        self.assertEqual(mv.check_metadata(repo, out), [])
        self.assertEqual(lv.check_markdown_links(repo, out), [])


class ComputeAreasLargeTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _build_large(self.root, n_dirs=60)

    def tearDown(self):
        self.tmp.cleanup()

    def test_top_tier_is_bounded(self):
        model = self.gen.compute_areas(self.root)
        self.assertTrue(model.present)
        # 60 communities/directories, but the top tier is capped.
        self.assertLessEqual(len(model.areas), self.gen.MAX_TOP_AREAS)
        self.assertEqual(model.total_area_count, 60)
        self.assertTrue(model.truncated)

    def test_drilldown_handles_present_per_area(self):
        model = self.gen.compute_areas(self.root)
        for a in model.areas:
            self.assertTrue(a.hub_node_id)
            self.assertFalse(a.hub_node_id.startswith("project:c"))

    def test_render_shows_overflow_handoff(self):
        model = self.gen.compute_areas(self.root)
        md = self.gen.render_markdown(model)
        self.assertIn("More areas", md)
        self.assertIn("code_graph_report", md)
        self.assertIn("code_graph_community", md)


# --------------------------------------------------------------------------- #
# 1p5zr: ranking quality, config demotion, oversized subdivision, link fix.
# --------------------------------------------------------------------------- #
class EntryPointRankingTests(unittest.TestCase):
    """Entry points rank by cross-file fan-in / public symbols over private utils."""

    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # One area, three real symbols:
        #   register_surface — called from 3 OTHER files (high cross-file fan-in)
        #   _response        — private helper, called 20x but all WITHIN its file
        #   helper           — public, low fan-in
        nodes = [
            _node("svc/api.py", "module", "api", "svc/api.py"),
            _node("svc/api.py::register_surface", "function", "register_surface", "svc/api.py"),
            _node("svc/api.py::_response", "function", "_response", "svc/api.py"),
            _node("svc/api.py::helper", "function", "helper", "svc/api.py"),
            _node("svc/a.py::a", "function", "a", "svc/a.py"),
            _node("svc/b.py::b", "function", "b", "svc/b.py"),
            _node("svc/c.py::c", "function", "c", "svc/c.py"),
        ]
        edges = []
        # _response gets huge raw degree but only from within svc/api.py.
        for i in range(20):
            edges.append({"source": "svc/api.py::helper", "target": "svc/api.py::_response", "relation": "calls"})
        # register_surface called from three DIFFERENT files -> cross-file fan-in 3.
        for caller in ("svc/a.py::a", "svc/b.py::b", "svc/c.py::c"):
            edges.append({"source": caller, "target": "svc/api.py::register_surface", "relation": "calls"})
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {
                "community_id": "project:c0",
                "label": "api",
                "seed_node_id": "svc/api.py::register_surface",
                "node_ids": [n["id"] for n in nodes if n["id"].startswith("svc/api.py")],
                "node_count": 4,
                "boundary_node_count": 1,
            },
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_cross_file_fanin_beats_raw_degree(self):
        model = self.gen.compute_areas(self.root)
        api = next(a for a in model.areas if a.representative_path == "svc")
        labels = [s["label"] for s in api.key_symbols]
        # register_surface (fan-in 3) ranks first; _response (degree 20, fan-in 0)
        # is filtered as a trivial private helper.
        self.assertEqual(labels[0], "register_surface")
        self.assertNotIn("_response", labels)

    def test_private_helper_with_cross_file_fanin_is_kept(self):
        # Give _response cross-file fan-in -> it should no longer be filtered.
        nodes = [
            _node("svc/api.py", "module", "api", "svc/api.py"),
            _node("svc/api.py::_response", "function", "_response", "svc/api.py"),
            _node("svc/x.py::x", "function", "x", "svc/x.py"),
            _node("svc/y.py::y", "function", "y", "svc/y.py"),
        ]
        edges = [
            {"source": "svc/x.py::x", "target": "svc/api.py::_response", "relation": "calls"},
            {"source": "svc/y.py::y", "target": "svc/api.py::_response", "relation": "calls"},
        ]
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "api", "seed_node_id": "svc/api.py::_response",
             "node_ids": ["svc/api.py", "svc/api.py::_response"], "node_count": 2, "boundary_node_count": 1},
        ])
        model = self.gen.compute_areas(self.root)
        api = next(a for a in model.areas if a.representative_path == "svc")
        self.assertIn("_response", [s["label"] for s in api.key_symbols])


class NameResponsibilityConsistencyTests(unittest.TestCase):
    """Area name and Responsibility never present two contradicting derivations.

    Regression (wave 1p60q): the tiered-label work made ``name`` directory-first
    but left ``responsibility`` falling back to the graph ``cluster_label`` — an
    unrelated high-fan-in symbol. teton p60n field re-test saw name (`packages`)
    and Responsibility (`logger`) disagree in 14/24 areas.
    """

    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Representative directory is the meaningful segment ``packages``; the
        # community label is an UNRELATED symbol (``logger``). Pre-fix the area
        # was named ``packages`` with Responsibility ``logger`` (a contradiction).
        nodes = [
            _node("packages/log.py", "module", "log", "packages/log.py"),
            _node("packages/log.py::logger", "function", "logger", "packages/log.py"),
            _node("packages/log.py::emit", "function", "emit", "packages/log.py"),
            _node("packages/sink.py::write", "function", "write", "packages/sink.py"),
        ]
        edges = [
            {"source": "packages/log.py", "target": "packages/log.py::logger", "relation": "defines"},
            {"source": "packages/sink.py::write", "target": "packages/log.py::logger", "relation": "calls"},
        ]
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {
                "community_id": "project:c0",
                "label": "logger",
                "seed_node_id": "packages/log.py::logger",
                "node_ids": [n["id"] for n in nodes],
                "node_count": len(nodes),
                "boundary_node_count": 1,
            },
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_directory_name_does_not_pair_with_unrelated_cluster_label(self):
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "packages")
        # Name is the directory segment, not the cluster symbol.
        self.assertEqual(area.name, "packages")
        # Responsibility mirrors the name — it must NOT be the unrelated cluster
        # label, and must not contradict the name.
        self.assertEqual(area.responsibility, area.name)
        self.assertNotEqual(area.responsibility, "logger")

    def test_agents_md_first_line_remains_authoritative_responsibility(self):
        # Tier-2 path is preserved: an area AGENTS.md still supplies the
        # responsibility, overriding the name-mirror default.
        area_dir = self.root / "packages"
        area_dir.mkdir(parents=True, exist_ok=True)
        (area_dir / "AGENTS.md").write_text(
            "# Logging package\n\nStructured logging and sinks for all services.\n",
            encoding="utf-8",
        )
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "packages")
        self.assertEqual(area.name, "Logging package")
        self.assertEqual(area.responsibility, "Structured logging and sinks for all services.")


class ConfigAreaTests(unittest.TestCase):
    """Config-only areas render files-only, no entry points, demoted/tagged."""

    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        nodes = [
            # A config "area": JSON keys parse as `class` nodes — NOT real code.
            _node("conf/workflow-config.json", "module", "workflow-config", "conf/workflow-config.json"),
            _node("conf/workflow-config.json::wave_review", "class", "wave_review", "conf/workflow-config.json"),
            _node("conf/workflow-config.json::enabled", "class", "enabled", "conf/workflow-config.json"),
            # A real code area.
            _node("svc/api.py", "module", "api", "svc/api.py"),
            _node("svc/api.py::serve", "function", "serve", "svc/api.py"),
        ]
        edges = [{"source": "svc/api.py", "target": "svc/api.py::serve", "relation": "defines"}]
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "workflow-config",
             "seed_node_id": "conf/workflow-config.json",
             "node_ids": [n["id"] for n in nodes if "json" in n["id"]],
             "node_count": 3, "boundary_node_count": 0},
            {"community_id": "project:c1", "label": "api", "seed_node_id": "svc/api.py::serve",
             "node_ids": ["svc/api.py", "svc/api.py::serve"], "node_count": 2, "boundary_node_count": 0},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_area_flagged_no_entry_points(self):
        model = self.gen.compute_areas(self.root)
        cfg = next(a for a in model.areas if a.representative_path == "conf")
        self.assertTrue(cfg.is_config)
        self.assertEqual(cfg.key_symbols, ())  # NO JSON keys as entry points
        self.assertIn("conf/workflow-config.json", cfg.key_files)

    def test_config_area_demoted_below_code(self):
        model = self.gen.compute_areas(self.root)
        kinds = [a.is_config for a in model.areas]
        # All code (False) areas come before all config (True) areas.
        self.assertEqual(kinds, sorted(kinds))

    def test_render_omits_config_entry_points_and_json_keys(self):
        model = self.gen.compute_areas(self.root)
        md = self.gen.render_markdown(model, last_verified="2026-06-16")
        self.assertIn("(config)", md)
        self.assertIn("configuration/data", md)
        # JSON keys never appear as entry points.
        self.assertNotIn("`wave_review` (class)", md)
        self.assertNotIn("`enabled` (class)", md)


class OversizedSubdivisionTests(unittest.TestCase):
    """An oversized directory bucket subdivides into its communities, within cap."""

    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _build_oversized(self, n_comms=10, per_comm=80):
        # Many communities ALL collapsing to one directory `scripts/`, each large
        # enough that the combined bucket clears the absolute cap.
        nodes = []
        edges = []
        communities = []
        for ci in range(n_comms):
            ids = []
            for j in range(per_comm):
                nid = f"scripts/mod{ci}.py::sym{ci}_{j}"
                nodes.append(_node(nid, "function", f"sym{ci}_{j}", f"scripts/mod{ci}.py"))
                ids.append(nid)
            communities.append({
                "community_id": f"project:c{ci}", "label": f"feature{ci}",
                "seed_node_id": ids[0], "node_ids": ids,
                "node_count": len(ids), "boundary_node_count": 0,
            })
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, communities)

    def test_oversized_bucket_subdivides(self):
        self.assertGreater(800, self.gen.OVERSIZED_AREA_NODE_CAP)  # sanity: 10*80=800 > 400
        self._build_oversized(n_comms=10, per_comm=80)
        model = self.gen.compute_areas(self.root)
        # Without subdivision, this would be ONE 800-node `scripts` area. With it,
        # the bucket splits into its per-community sub-areas.
        scripts_areas = [a for a in model.areas if a.representative_path == "scripts"]
        self.assertGreater(len(scripts_areas), 1)
        names = {a.name for a in scripts_areas}
        self.assertIn("feature0", names)

    def test_subdivision_stays_within_cap(self):
        self._build_oversized(n_comms=40, per_comm=80)  # 40 sub-areas pre-cap
        model = self.gen.compute_areas(self.root)
        self.assertLessEqual(len(model.areas), self.gen.MAX_TOP_AREAS)
        self.assertTrue(model.truncated)

    def test_small_bucket_not_subdivided(self):
        # A directory below the cap with several communities stays fused as one.
        self._build_oversized(n_comms=3, per_comm=20)  # 60 nodes < 400 cap
        model = self.gen.compute_areas(self.root)
        scripts_areas = [a for a in model.areas if a.representative_path == "scripts"]
        self.assertEqual(len(scripts_areas), 1)


class MapLinkHrefTests(unittest.TestCase):
    """Area->AGENTS.md link present iff the file exists, with a map-relative href."""

    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _build_small(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_link_when_agents_md_absent(self):
        model = self.gen.compute_areas(self.root)
        md = self.gen.render_markdown(model, root=self.root)
        self.assertNotIn("Area context:", md)

    def test_link_present_with_map_relative_href_when_file_exists(self):
        model = self.gen.compute_areas(self.root)
        area = model.areas[0]
        rel = self.gen._area_context_rel_path(area)
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text("# stub\n", encoding="utf-8")
        href = self.gen._area_context_link_href(rel)
        md = self.gen.render_markdown(model, root=self.root)
        self.assertIn(f"]({href})", md)
        # The href is map-relative (starts with ../), never a bare repo-root path
        # that docs-lint would resolve under docs/references/ and flag as broken.
        self.assertTrue(href.startswith("../"), href)


class AreaContextWalkUpResolverTests(unittest.TestCase):
    """1p66d — per-area AGENTS.md resolution walks UP to the nearest ancestor."""

    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _area(self, rep_path):
        return self.gen.CodebaseArea(
            area_id="buttons",
            name="buttons",
            representative_path=rep_path,
            responsibility="buttons",
            key_files=(),
            key_symbols=(),
            hub_node_id="hub",
            community_ids=("c1",),
            node_count=1,
            boundary_node_count=0,
        )

    def _write(self, rel):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# ctx\n", encoding="utf-8")

    def test_resolves_to_ancestor_when_not_at_rep_path(self):
        # Conventional project-root placement; rep path is a deep subdir.
        self._write("libs/ui/AGENTS.md")
        area = self._area("libs/ui/src/components/buttons")
        self.assertEqual(
            self.gen._resolve_area_context_rel_path(self.root, area),
            "libs/ui/AGENTS.md",
        )

    def test_nearest_ancestor_wins(self):
        self._write("libs/ui/AGENTS.md")
        self._write("libs/ui/src/components/AGENTS.md")
        area = self._area("libs/ui/src/components/buttons")
        self.assertEqual(
            self.gen._resolve_area_context_rel_path(self.root, area),
            "libs/ui/src/components/AGENTS.md",
        )

    def test_exact_rep_path_still_resolves(self):
        self._write("libs/ui/src/components/buttons/AGENTS.md")
        area = self._area("libs/ui/src/components/buttons")
        self.assertEqual(
            self.gen._resolve_area_context_rel_path(self.root, area),
            "libs/ui/src/components/buttons/AGENTS.md",
        )

    def test_root_area_resolves_repo_root_agents(self):
        self._write("AGENTS.md")
        area = self._area("(root)")
        self.assertEqual(
            self.gen._resolve_area_context_rel_path(self.root, area), "AGENTS.md"
        )

    def test_repo_root_excluded_for_non_root_area(self):
        # Only the repo-root AGENTS.md exists — a non-root area must NOT link it.
        self._write("AGENTS.md")
        area = self._area("libs/ui/src/components/buttons")
        self.assertIsNone(self.gen._resolve_area_context_rel_path(self.root, area))

    def test_none_when_no_ancestor_has_one(self):
        area = self._area("libs/ui/src/components/buttons")
        self.assertIsNone(self.gen._resolve_area_context_rel_path(self.root, area))

    def test_deterministic_repeat(self):
        self._write("libs/ui/AGENTS.md")
        area = self._area("libs/ui/src/components/buttons")
        first = self.gen._resolve_area_context_rel_path(self.root, area)
        for _ in range(5):
            self.assertEqual(
                self.gen._resolve_area_context_rel_path(self.root, area), first
            )

    def test_render_links_ancestor_file(self):
        # End-to-end: a deep area links its project-root AGENTS.md in the map.
        self._write("libs/ui/AGENTS.md")
        area = self._area("libs/ui/src/components/buttons")
        model = self.gen.CodebaseMapModel(
            present=True,
            reason="",
            layer="project",
            areas=(area,),
            total_area_count=1,
            truncated=False,
            grouping="package-directory",
            cluster_builder_version="10",
            cluster_schema_version="1",
            graph_builder_version="31",
            file_count=1,
            symbol_count=1,
        )
        md = self.gen.render_markdown(model, root=self.root)
        self.assertIn("Area context:", md)
        self.assertIn("libs/ui/AGENTS.md", md)


class DeterminismTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()

    def test_deterministic_for_fixed_artifact(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra, rb = Path(a), Path(b)
            _build_large(ra, n_dirs=40)
            _build_large(rb, n_dirs=40)
            ma = self.gen.render_markdown(self.gen.compute_areas(ra), last_verified="2026-06-16")
            mb = self.gen.render_markdown(self.gen.compute_areas(rb), last_verified="2026-06-16")
            self.assertEqual(ma, mb)


class FailSafeTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_graph(self):
        model = self.gen.compute_areas(self.root)
        self.assertFalse(model.present)
        self.assertIn("no persisted graph", model.reason)
        md = self.gen.render_markdown(model)
        self.assertIn("No map could be generated", md)

    def test_empty_graph(self):
        _write_graph(self.root, [], [])
        model = self.gen.compute_areas(self.root)
        self.assertFalse(model.present)

    def test_partial_missing_cluster_falls_back_to_directories(self):
        # Graph present, cluster missing -> directory-fallback grouping.
        _build_small(self.root)
        (_graph_dir(self.root) / "project-graph-clusters.json").unlink()
        model = self.gen.compute_areas(self.root)
        self.assertTrue(model.present)
        self.assertEqual(model.grouping, "directory-fallback")
        names = {a.name for a in model.areas}
        # Directory basenames become area names.
        self.assertTrue({"src", "api"} & names)

    def test_generate_safe_never_raises_and_writes_degraded_map(self):
        # No artifacts at all — generate_safe must not raise; it writes a degraded
        # (not-present) map and reports success (the index build is never broken).
        ok = self.gen.generate_safe(self.root, verbose=False)
        self.assertTrue(ok)
        out = self.gen.output_path(self.root)
        self.assertTrue(out.exists())
        self.assertIn("No map could be generated", out.read_text(encoding="utf-8"))

    def test_generate_safe_swallows_corrupt_graph(self):
        # Corrupt graph json -> compute degrades to not-present; never raises.
        (_graph_dir(self.root) / "project-graph.json").write_text("{not json", encoding="utf-8")
        ok = self.gen.generate_safe(self.root, verbose=False)
        self.assertTrue(ok)
        self.assertTrue(self.gen.output_path(self.root).exists())


class CliTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _build_small(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_cli_writes_map(self):
        rc = self.gen.main(["--root", str(self.root)])
        self.assertEqual(rc, 0)
        out = self.gen.output_path(self.root)
        self.assertTrue(out.exists())
        self.assertIn("# Codebase Map", out.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1p5zr req 4: tiered labels + carry-forward (AGENTS.md re-read each generation).
# --------------------------------------------------------------------------- #
class TieredLabelTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _build_small(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_agents_md_title_overrides_label(self):
        # api/server.py → rep_path "api". Author an AGENTS.md there.
        agents = self.root / "api" / "AGENTS.md"
        agents.parent.mkdir(parents=True, exist_ok=True)
        agents.write_text(
            "# Public HTTP Surface\n\nOwner: Eng\n\nHandles inbound request routing.\n",
            encoding="utf-8",
        )
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "api")
        self.assertEqual(area.name, "Public HTTP Surface")
        self.assertEqual(area.responsibility, "Handles inbound request routing.")

    def test_carry_forward_survives_regeneration(self):
        # Human knowledge in AGENTS.md must survive a full regen (it is re-read,
        # never stored in the map). Generate once, then again — title persists.
        agents = self.root / "api" / "AGENTS.md"
        agents.parent.mkdir(parents=True, exist_ok=True)
        agents.write_text("# Edge Gateway\n\nFront door for the service.\n", encoding="utf-8")
        self.gen.generate_codebase_map(self.root, force=True)
        md1 = self.gen.output_path(self.root).read_text(encoding="utf-8")
        self.assertIn("Edge Gateway", md1)
        # Regenerate from scratch — knowledge is re-read from AGENTS.md.
        model = self.gen.compute_areas(self.root)
        self.assertIn("Edge Gateway", {a.name for a in model.areas})

    def test_no_doc_spec_config_label(self):
        # A cluster whose label looks like a doc/spec (e.g. "repo-index") must not
        # be used as the Tier-1 label; the directory segment is used instead.
        nodes = [
            _node("orchestrator/run.py", "module", "run", "orchestrator/run.py"),
            _node("orchestrator/run.py::main", "function", "main", "orchestrator/run.py"),
        ]
        edges = [{"source": "orchestrator/run.py", "target": "orchestrator/run.py::main", "relation": "defines"}]
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "current-state",
             "seed_node_id": "orchestrator/run.py::main",
             "node_ids": [n["id"] for n in nodes], "node_count": 2, "boundary_node_count": 0},
        ])
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "orchestrator")
        self.assertNotEqual(area.name, "current-state")
        self.assertEqual(area.name, "orchestrator")


# --------------------------------------------------------------------------- #
# 1p5zr req 7: kind tags, same-package collapse, hub membership, non-code.
# --------------------------------------------------------------------------- #
class TetonDefectTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_kind_tags_accurate_or_omitted(self):
        # A type/interface/const carries its real tag; an unknown kind is omitted
        # (never blanket `function`).
        nodes = [
            _node("lib/types.ts", "module", "types", "lib/types.ts"),
            _node("lib/types.ts::User", "interface", "User", "lib/types.ts"),
            _node("lib/types.ts::Id", "type", "Id", "lib/types.ts"),
            _node("lib/types.ts::serialize", "function", "serialize", "lib/types.ts"),
            # A node whose kind the graph does not recognize → omit tag.
            _node("lib/types.ts::theme", "themetoken", "theme", "lib/types.ts"),
        ]
        edges = []
        # Give cross-file fan-in so they survive ranking.
        for sym in ("User", "Id", "serialize", "theme"):
            nodes.append(_node(f"lib/caller_{sym}.ts::c", "function", f"c_{sym}", f"lib/caller_{sym}.ts"))
            edges.append({"source": f"lib/caller_{sym}.ts::c", "target": f"lib/types.ts::{sym}", "relation": "calls"})
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "types",
             "seed_node_id": "lib/types.ts::User",
             "node_ids": [n["id"] for n in nodes if n["source_file"] == "lib/types.ts"],
             "node_count": 5, "boundary_node_count": 0},
        ])
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "lib")
        by_label = {s["label"]: s["kind"] for s in area.key_symbols}
        # interface/type tags are accurate; theme (unknown kind) is excluded since
        # only _ENTRY_SYMBOL_KINDS are eligible — so no blanket function tag leaks.
        if "User" in by_label:
            self.assertEqual(by_label["User"], "interface")
        if "Id" in by_label:
            self.assertEqual(by_label["Id"], "type")
        # No symbol is ever tagged with the wrong category.
        for label, kind in by_label.items():
            self.assertNotEqual((label, kind), ("theme", "function"))

    def test_kind_tag_helper_omits_unknown(self):
        self.assertEqual(self.gen._kind_tag({"kind": "interface"}), "interface")
        self.assertEqual(self.gen._kind_tag({"kind": "type"}), "type")
        self.assertEqual(self.gen._kind_tag({"kind": "const"}), "const")
        self.assertEqual(self.gen._kind_tag({"kind": "themetoken"}), "")
        self.assertEqual(self.gen._kind_tag({"kind": ""}), "")

    def test_same_package_communities_collapse(self):
        # Multiple communities resolving to the SAME representative directory
        # collapse into one area (not N areas eating N slots).
        nodes = []
        edges = []
        communities = []
        for i in range(7):
            nid = f"libs/typings/src/lib/m{i}.ts::T{i}"
            nodes.append(_node(nid, "type", f"T{i}", f"libs/typings/src/lib/m{i}.ts"))
            communities.append({
                "community_id": f"project:c{i}", "label": f"thing{i}.types",
                "seed_node_id": nid, "node_ids": [nid], "node_count": 1, "boundary_node_count": 0,
            })
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, communities)
        model = self.gen.compute_areas(self.root)
        typings = [a for a in model.areas if a.representative_path == "libs/typings/src/lib"]
        self.assertEqual(len(typings), 1)

    def test_hub_is_member_of_area_and_in_key_files(self):
        nodes = [
            _node("svc/core.py", "module", "core", "svc/core.py"),
            _node("svc/core.py::run", "function", "run", "svc/core.py"),
            _node("svc/core.py::helper", "function", "helper", "svc/core.py"),
        ]
        edges = [
            {"source": "svc/core.py", "target": "svc/core.py::run", "relation": "defines"},
            {"source": "svc/core.py::helper", "target": "svc/core.py::run", "relation": "calls"},
        ]
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "core", "seed_node_id": "svc/core.py::run",
             "node_ids": [n["id"] for n in nodes], "node_count": 3, "boundary_node_count": 0},
        ])
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "svc")
        hub_sf = next(n["source_file"] for n in nodes if n["id"] == area.hub_node_id)
        self.assertIn(hub_sf, area.key_files)
        self.assertEqual(self.gen._representative_dir(hub_sf), area.representative_path)

    def test_non_code_excluded_from_areas(self):
        # .html / styleguide / asset nodes never form or pollute an area.
        nodes = [
            _node("ui/page.html", "module", "page", "ui/page.html"),
            _node("ui/page.html::widget", "class", "widget", "ui/page.html"),
            _node("svc/api.py", "module", "api", "svc/api.py"),
            _node("svc/api.py::serve", "function", "serve", "svc/api.py"),
        ]
        edges = [{"source": "svc/api.py", "target": "svc/api.py::serve", "relation": "defines"}]
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "page", "seed_node_id": "ui/page.html",
             "node_ids": ["ui/page.html", "ui/page.html::widget"], "node_count": 2, "boundary_node_count": 0},
            {"community_id": "project:c1", "label": "api", "seed_node_id": "svc/api.py::serve",
             "node_ids": ["svc/api.py", "svc/api.py::serve"], "node_count": 2, "boundary_node_count": 0},
        ])
        model = self.gen.compute_areas(self.root)
        paths = {a.representative_path for a in model.areas}
        self.assertIn("svc", paths)
        self.assertNotIn("ui", paths)
        for a in model.areas:
            for f in a.key_files:
                self.assertFalse(f.endswith(".html"))


# --------------------------------------------------------------------------- #
# 1p601 req 6: change-only idempotence (no write when inputs unchanged).
# --------------------------------------------------------------------------- #
class IdempotenceTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _build_small(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_back_to_back_generate_is_byte_identical_and_no_write(self):
        self.gen.generate_codebase_map(self.root, last_verified="2026-06-16")
        out = self.gen.output_path(self.root)
        first = out.read_bytes()
        mtime1 = out.stat().st_mtime_ns
        import time as _t
        _t.sleep(0.01)
        # Second back-to-back generate with no input change: byte-identical, no write.
        self.gen.generate_codebase_map(self.root)
        second = out.read_bytes()
        mtime2 = out.stat().st_mtime_ns
        self.assertEqual(first, second)
        self.assertEqual(mtime1, mtime2)  # file was NOT rewritten

    def test_date_preserved_when_content_unchanged(self):
        self.gen.generate_codebase_map(self.root, last_verified="2025-01-01")
        out = self.gen.output_path(self.root)
        self.assertIn("Last verified: 2025-01-01", out.read_text(encoding="utf-8"))
        # A later generate with no input change preserves the original date.
        self.gen.generate_codebase_map(self.root)
        self.assertIn("Last verified: 2025-01-01", out.read_text(encoding="utf-8"))

    def test_input_change_triggers_rewrite(self):
        self.gen.generate_codebase_map(self.root, last_verified="2026-06-16")
        out = self.gen.output_path(self.root)
        before = out.read_bytes()
        # Author an AGENTS.md (a Tier-2 input) → fingerprint changes → rewrite.
        agents = self.root / "api" / "AGENTS.md"
        agents.parent.mkdir(parents=True, exist_ok=True)
        agents.write_text("# Renamed Area\n\nNew responsibility line.\n", encoding="utf-8")
        self.gen.generate_codebase_map(self.root, last_verified="2026-06-16")
        after = out.read_bytes()
        self.assertNotEqual(before, after)
        self.assertIn("Renamed Area", out.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1p5zr req 6: repo-index marker block feed (idempotent, narrative preserved).
# --------------------------------------------------------------------------- #
class RepoIndexFeedTests(unittest.TestCase):
    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _build_small(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_repo_index(self):
        path = self.root / "docs" / "repo-index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Repo Index\n\nOwner: Eng\n\n## Summary\n\nHUMAN NARRATIVE ABOVE.\n\n"
            "## Top-Level Modules\n\n"
            f"{self.gen.REPO_INDEX_MARKER_BEGIN}\n{self.gen.REPO_INDEX_MARKER_END}\n\n"
            "## Architecture\n\nHUMAN NARRATIVE BELOW.\n",
            encoding="utf-8",
        )
        return path

    def test_feed_fills_marker_block_and_preserves_narrative(self):
        path = self._write_repo_index()
        self.gen.generate_codebase_map(self.root, force=True)
        text = path.read_text(encoding="utf-8")
        self.assertIn("HUMAN NARRATIVE ABOVE.", text)
        self.assertIn("HUMAN NARRATIVE BELOW.", text)
        # Structural block now contains area rows between the markers.
        begin = text.index(self.gen.REPO_INDEX_MARKER_BEGIN)
        end = text.index(self.gen.REPO_INDEX_MARKER_END)
        block = text[begin:end]
        self.assertIn("auth", block)
        self.assertIn("| Area |", block)

    def test_feed_is_idempotent(self):
        path = self._write_repo_index()
        self.gen.generate_codebase_map(self.root, force=True)
        first = path.read_text(encoding="utf-8")
        self.gen.generate_codebase_map(self.root, force=True)
        second = path.read_text(encoding="utf-8")
        self.assertEqual(first, second)

    def test_feed_no_markers_is_safe_noop(self):
        path = self.root / "docs" / "repo-index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        original = "# Repo Index\n\nOwner: Eng\n\nNo markers here.\n"
        path.write_text(original, encoding="utf-8")
        self.gen.generate_codebase_map(self.root, force=True)
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_feed_missing_file_is_safe_noop(self):
        # No repo-index.md at all — never created, never raises.
        self.gen.generate_codebase_map(self.root, force=True)
        self.assertFalse((self.root / "docs" / "repo-index.md").exists())


class GeneratorAreaSelectionTests(unittest.TestCase):
    """Wave 1p61w (javaagent field test): area selection consumes the generated
    signal, floors per-module, keeps hubs on real code, and disambiguates labels."""

    def setUp(self):
        self.gen = load_gen()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _mk_area(self, name, rep, n=10):
        return self.gen.CodebaseArea(
            area_id=name, name=name, representative_path=rep, responsibility=name,
            key_files=(), key_symbols=(), hub_node_id=f"{rep}/x", community_ids=(),
            node_count=n, boundary_node_count=0,
        )

    def test_generated_dominated_community_excluded(self):
        # A 99%-generated community (e.g. a JavaCC parser) must NOT become an area;
        # a normal community at the same size still does. The omission is surfaced.
        nodes = [
            _node("src/auth.py", "module", "auth", "src/auth.py"),
            _node("src/auth.py::login", "function", "login", "src/auth.py"),
            _node("gen/parser.py", "module", "parser", "gen/parser.py"),
            _node("gen/parser.py::parse", "function", "parse", "gen/parser.py"),
        ]
        _write_graph(self.root, nodes, [
            {"source": "src/auth.py", "target": "src/auth.py::login", "relation": "defines"},
            {"source": "gen/parser.py", "target": "gen/parser.py::parse", "relation": "defines"},
        ])
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "auth", "seed_node_id": "src/auth.py::login",
             "node_ids": ["src/auth.py", "src/auth.py::login"], "node_count": 2,
             "boundary_node_count": 0, "generated_node_fraction": 0.0},
            {"community_id": "project:c1", "label": "ELParser", "seed_node_id": "gen/parser.py::parse",
             "node_ids": ["gen/parser.py", "gen/parser.py::parse"], "node_count": 2,
             "boundary_node_count": 0, "generated_node_fraction": 0.99},
        ])
        model = self.gen.compute_areas(self.root)
        names = {a.name for a in model.areas}
        self.assertNotIn("ELParser", names)
        self.assertTrue(any(a.representative_path == "src" for a in model.areas))
        self.assertEqual(model.extra.get("generated_areas_omitted"), 1)
        md = self.gen.render_markdown(model, last_verified="2026-06-17")
        self.assertIn("omitted from areas", md)

    def test_hub_is_never_a_non_code_data_node(self):
        # A high-degree `.json` data node must not be chosen as the drill-in hub.
        nodes = [
            _node("src/svc.py", "module", "svc", "src/svc.py"),
            _node("src/svc.py::run", "function", "run", "src/svc.py"),
            _node("src/data.json::map", "class", "map", "src/data.json"),
        ]
        # Give the json node the highest degree so it would win without the guard.
        edges = [
            {"source": "src/svc.py", "target": "src/svc.py::run", "relation": "defines"},
            {"source": "src/svc.py::run", "target": "src/data.json::map", "relation": "reads"},
            {"source": "src/svc.py", "target": "src/data.json::map", "relation": "reads"},
        ]
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "svc", "seed_node_id": "src/svc.py::run",
             "node_ids": [n["id"] for n in nodes], "node_count": 3, "boundary_node_count": 0},
        ])
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "src")
        self.assertNotEqual(area.hub_node_id, "src/data.json::map")
        self.assertNotIn(".json", area.hub_node_id)

    def test_per_module_floor_guarantees_each_module(self):
        # 3 vendor areas (largest) + 2 small product modules; cap=3. Pure size
        # ranking would keep only vendor; the floor guarantees each module a slot.
        areas = [
            self._mk_area("a", "vendor/a", 100),
            self._mk_area("b", "vendor/b", 90),
            self._mk_area("c", "vendor/c", 80),
            self._mk_area("p1", "product1", 10),
            self._mk_area("p2", "product2", 5),
        ]
        kept = self.gen._select_with_module_floor(areas, 3)
        kept_modules = {self.gen._area_module_key(a) for a in kept}
        self.assertEqual(len(kept), 3)
        self.assertIn("product1", kept_modules)
        self.assertIn("product2", kept_modules)

    def test_area_name_disambiguation_and_ordinal_strip(self):
        areas = [
            self._mk_area("parser", "el/apache/parser"),
            self._mk_area("parser", "el/javax"),
            self._mk_area("Foo 1", "x/foo"),
        ]
        out = self.gen._disambiguate_area_names(areas)
        names = [a.name for a in out]
        # Ordinal noise stripped.
        self.assertIn("Foo", names)
        self.assertNotIn("Foo 1", names)
        # Colliding `parser` titles disambiguated to distinct path-based names.
        self.assertNotIn("parser", names)
        self.assertEqual(len(set(names)), len(names))

    def _write_vendored_fixture(self):
        # A product community (src/) + a vendored community (vendor/el/).
        nodes = [
            _node("src/app.py", "module", "app", "src/app.py"),
            _node("src/app.py::run", "function", "run", "src/app.py"),
            _node("vendor/el/parser.py", "module", "parser", "vendor/el/parser.py"),
            _node("vendor/el/parser.py::parse", "function", "parse", "vendor/el/parser.py"),
        ]
        _write_graph(self.root, nodes, [
            {"source": "src/app.py", "target": "src/app.py::run", "relation": "defines"},
            {"source": "vendor/el/parser.py", "target": "vendor/el/parser.py::parse", "relation": "defines"},
        ])
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "app", "seed_node_id": "src/app.py::run",
             "node_ids": ["src/app.py", "src/app.py::run"], "node_count": 2, "boundary_node_count": 0},
            {"community_id": "project:c1", "label": "elparser", "seed_node_id": "vendor/el/parser.py::parse",
             "node_ids": ["vendor/el/parser.py", "vendor/el/parser.py::parse"], "node_count": 2,
             "boundary_node_count": 0},
        ])

    def test_vendored_paths_glob_excludes_community(self):
        self._write_vendored_fixture()
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "repo-profile.json").write_text(
            json.dumps({"vendored_paths": ["**/vendor/el/**"]}), encoding="utf-8")
        model = self.gen.compute_areas(self.root)
        reps = {a.representative_path for a in model.areas}
        self.assertIn("src", reps)
        self.assertNotIn("vendor/el", reps)  # vendored community dropped
        self.assertEqual(model.extra.get("vendored_areas_omitted"), 1)
        md = self.gen.render_markdown(model, last_verified="2026-06-17")
        self.assertIn("vendored / third-party", md.lower())

    def test_gitattributes_linguist_vendored_excludes_community(self):
        self._write_vendored_fixture()
        (self.root / ".gitattributes").write_text(
            "vendor/el/* linguist-vendored=true\n", encoding="utf-8")
        model = self.gen.compute_areas(self.root)
        reps = {a.representative_path for a in model.areas}
        self.assertNotIn("vendor/el", reps)
        self.assertEqual(model.extra.get("vendored_areas_omitted"), 1)

    def test_vendored_generated_excluded_from_key_files_symbols_hub(self):
        # Wave 1p65l #1: a vendored (glob) or generated (tag) file absorbed as a
        # MINORITY of a product community is never a key file, key symbol, or hub —
        # even when it has the highest degree (would otherwise win the hub).
        nodes = [
            _node("svc/app.ts", "module", "app", "svc/app.ts"),
            _node("svc/app.ts::run", "function", "run", "svc/app.ts"),
            _node("vendor/opt/dependencies/otel.cjs::OTel", "function", "OTel", "vendor/opt/dependencies/otel.cjs"),
            _node("svc/gen.ts::g", "function", "g", "svc/gen.ts"),
        ]
        nodes[3]["generated"] = True
        edges = [{"source": "svc/app.ts", "target": "svc/app.ts::run", "relation": "defines"}]
        for _ in range(10):  # otel.cjs = highest degree
            edges.append({"source": "svc/app.ts::run", "target": "vendor/opt/dependencies/otel.cjs::OTel", "relation": "calls"})
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "app", "seed_node_id": "svc/app.ts::run",
             "node_ids": [n["id"] for n in nodes], "node_count": 4, "boundary_node_count": 0}])
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "repo-profile.json").write_text(
            json.dumps({"vendored_paths": ["**/opt/dependencies/**"]}), encoding="utf-8")
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "svc")
        self.assertNotIn("vendor/opt/dependencies/otel.cjs", area.key_files)
        self.assertNotIn("svc/gen.ts", area.key_files)
        self.assertNotIn("otel.cjs", area.hub_node_id)
        labels = {s["label"] for s in area.key_symbols}
        self.assertNotIn("OTel", labels)  # vendored
        self.assertNotIn("g", labels)     # generated
        self.assertIn("run", labels)      # product survives

    def test_area_keyfiles_hub_restricted_to_own_module(self):
        # Wave 1p65m #2 (generator-side cohesion): a cross-package stray a grab-bag
        # community absorbed (backend file in a libs/utils area) is not a key file or
        # the hub, even at high degree.
        nodes = [
            _node("libs/utils/src/u.ts::run", "function", "run", "libs/utils/src/u.ts"),
            _node("libs/utils/src/v.ts::helper", "function", "helper", "libs/utils/src/v.ts"),
            _node("backend/apis/ldap.ts::ldap", "function", "ldap", "backend/apis/ldap.ts"),
        ]
        edges = [{"source": "libs/utils/src/u.ts::run", "target": "libs/utils/src/v.ts::helper", "relation": "calls"}]
        for _ in range(8):  # stray = highest degree
            edges.append({"source": "libs/utils/src/u.ts::run", "target": "backend/apis/ldap.ts::ldap", "relation": "calls"})
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "u", "seed_node_id": "libs/utils/src/u.ts::run",
             "node_ids": [n["id"] for n in nodes], "node_count": 3, "boundary_node_count": 0}])
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "libs/utils/src")
        self.assertNotIn("backend/apis/ldap.ts", area.key_files)
        self.assertNotIn("backend", area.hub_node_id)
        self.assertIn("libs/utils/src/u.ts", area.key_files)

    def test_qualify_structural_name(self):
        q = self.gen._qualify_structural_name
        self.assertEqual(q("v1", "libs/x/reports/github/cards/v1"), "github-cards (v1)")
        self.assertEqual(q("shared", "a/sailpoint/idn/shared"), "idn shared")
        self.assertEqual(q("data-grid", "libs/ui/data-grid"), "data-grid")  # descriptive, unchanged
        self.assertEqual(q("BackendApi", "libs/api"), "BackendApi")          # symbol, unchanged
        self.assertEqual(q("core", "core"), "core")                          # no ancestor → safe

    def test_type_only_communities_collapse_to_one_types_area(self):
        # Wave 1p65l #4: an oversized package of several type-only communities (by
        # KIND) collapses into ONE area instead of one area per type file.
        rep = "libs/typings/src/lib"
        nodes = []
        comms = []
        for ci in range(5):  # 5 type-only communities, ~90 property nodes each → oversized
            ids = []
            for i in range(90):
                nid = f"{rep}/t{ci}.ts::P{ci}_{i}"
                nodes.append(_node(nid, "property", f"P{ci}_{i}", f"{rep}/t{ci}.ts"))
                ids.append(nid)
            comms.append({"community_id": f"project:c{ci}", "label": f"t{ci}",
                          "seed_node_id": ids[0], "node_ids": ids,
                          "node_count": len(ids), "boundary_node_count": 0})
        _write_graph(self.root, nodes, [])
        _write_cluster(self.root, comms)
        model = self.gen.compute_areas(self.root)
        typing_areas = [a for a in model.areas if a.representative_path == rep]
        self.assertEqual(len(typing_areas), 1, "5 type-only communities should collapse to one area")

    def test_config_area_name_not_doc_prose(self):
        # Wave 1p65l #3-name: a config area must not borrow a doc-prose cluster label.
        nodes = [
            _node("tsconfig.base.json::a", "class", "a", "tsconfig.base.json"),
            _node("cdk.json::b", "class", "b", "cdk.json"),
            _node("nx.json::c", "class", "c", "nx.json"),
        ]
        _write_graph(self.root, nodes, [])
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "Agent Entry Guide", "seed_node_id": "tsconfig.base.json::a",
             "node_ids": [n["id"] for n in nodes], "node_count": 3, "boundary_node_count": 0}])
        (self.root / "AGENTS.md").write_text(
            "# Agent Entry Guide\n\nIf the user's request matches a phrase below, execute it immediately.\n",
            encoding="utf-8")
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.is_config)
        self.assertEqual(area.name, "configuration")
        self.assertNotIn("Agent Entry Guide", area.name)
        self.assertEqual(area.responsibility, "configuration / manifest files")

    def test_vendored_axis_no_config_is_safe_noop(self):
        # No repo-profile.json / .gitattributes → nothing vendored, no exclusion.
        self._write_vendored_fixture()
        model = self.gen.compute_areas(self.root)
        reps = {a.representative_path for a in model.areas}
        self.assertIn("vendor/el", reps)  # not excluded without an explicit signal
        self.assertEqual(model.extra.get("vendored_areas_omitted"), 0)

    def _write_absorbed_module_fixture(self, hibernate_files=3):
        # ONE community spanning serialization (dominant, 4 files) + inst/hibernate
        # (hibernate_files files), joined only by calls into a shared serializer.
        nodes = [_node(f"serialization/s{i}.py::f{i}", "function", f"f{i}", f"serialization/s{i}.py")
                 for i in range(4)]
        nodes += [_node(f"inst/hibernate/h{i}.py::g{i}", "function", f"g{i}", f"inst/hibernate/h{i}.py")
                  for i in range(hibernate_files)]
        edges = [{"source": n["id"], "target": "serialization/s0.py::f0", "relation": "calls"}
                 for n in nodes if n["id"] != "serialization/s0.py::f0"]
        _write_graph(self.root, nodes, edges)
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "serialization",
             "seed_node_id": "serialization/s0.py::f0",
             "node_ids": [n["id"] for n in nodes], "node_count": len(nodes),
             "boundary_node_count": 0},
        ])

    def test_buried_module_surfaced_as_area(self):
        # inst/hibernate is absorbed into the serialization community but clears the
        # file floor → it must surface as its own area (javaagent #2).
        self._write_absorbed_module_fixture(hibernate_files=3)
        model = self.gen.compute_areas(self.root)
        reps = {a.representative_path for a in model.areas}
        self.assertIn("serialization", reps)
        self.assertIn("inst/hibernate", reps)

    def test_buried_dir_below_floor_not_fragmented(self):
        # Only 2 hibernate files (< MODULE_FLOOR_MIN_FILES) → NOT surfaced
        # (anti-fragmentation: a stray-file scatter doesn't each become an area).
        self._write_absorbed_module_fixture(hibernate_files=2)
        model = self.gen.compute_areas(self.root)
        reps = {a.representative_path for a in model.areas}
        self.assertNotIn("inst/hibernate", reps)

    def test_config_area_responsibility_is_not_scraped_instruction(self):
        nodes = [
            _node("conf/a.json::k1", "class", "k1", "conf/a.json"),
            _node("conf/b.json::k2", "class", "k2", "conf/b.json"),
            _node("conf/c.json::k3", "class", "k3", "conf/c.json"),
        ]
        _write_graph(self.root, nodes, [])
        _write_cluster(self.root, [
            {"community_id": "project:c0", "label": "conf", "seed_node_id": "conf/a.json::k1",
             "node_ids": [n["id"] for n in nodes], "node_count": 3, "boundary_node_count": 0},
        ])
        (self.root / "conf").mkdir(parents=True, exist_ok=True)
        (self.root / "conf" / "AGENTS.md").write_text(
            "# Agent Entry Guide\n\nIf the user's request matches a phrase below, do X.\n",
            encoding="utf-8")
        model = self.gen.compute_areas(self.root)
        area = next(a for a in model.areas if a.representative_path == "conf")
        self.assertTrue(area.is_config)
        self.assertEqual(area.responsibility, "configuration / manifest files")
        self.assertNotIn("If the user", area.responsibility)

    def test_same_path_collision_gets_third_distinguisher(self):
        areas = [
            self._mk_area("javax", "el/javax", n=267),
            self._mk_area("javax", "el/javax", n=32),
        ]
        out = self.gen._disambiguate_area_names(areas)
        names = [a.name for a in out]
        self.assertEqual(len(set(names)), 2)  # no longer identical
        self.assertTrue(any("267" in n for n in names))
        self.assertTrue(any("32" in n for n in names))


if __name__ == "__main__":
    unittest.main()
