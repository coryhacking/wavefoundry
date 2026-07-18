"""Wave 1p5xc (1p5x8 large-codebase-map) — per-area AGENTS.md context.

Covers: idempotent stub scaffolding (no overwrite, stub-only), map linking an
area to its AGENTS.md when present, the root @AGENTS.md bridge in CLAUDE.md (no
prose-only pointer), no @import outside root, no subdirectory CLAUDE.md, and the
seed-first convention + operating-instruction weave.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parents[0]
PROJECT_ROOT = TESTS_ROOT.parents[2]  # .wavefoundry
REPO_ROOT = PROJECT_ROOT.parent
GEN_PATH = SCRIPTS_ROOT / "gen_codebase_map.py"
RENDER_SCRIPT = SCRIPTS_ROOT / "render_agent_surfaces.py"
GURU_STUB = "# Guru\n\nRole: guru\n"


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


def _node(nid, kind, label, source_file):
    return {"id": nid, "kind": kind, "label": label, "layer": "project", "source_file": source_file}


def _build_two_area_fixture(root: Path) -> None:
    nodes = [
        _node("src/auth.py", "module", "auth", "src/auth.py"),
        _node("src/auth.py::login", "function", "login", "src/auth.py"),
        _node("src/auth.py::Session", "class", "Session", "src/auth.py"),
        _node("api/server.py", "module", "server", "api/server.py"),
        _node("api/server.py::serve", "function", "serve", "api/server.py"),
    ]
    edges = [
        {"source": "src/auth.py", "target": "src/auth.py::login", "relation": "defines"},
        {"source": "api/server.py::serve", "target": "src/auth.py::login", "relation": "calls"},
        {"source": "api/server.py", "target": "api/server.py::serve", "relation": "defines"},
    ]
    (_graph_dir(root) / "project-graph.json").write_text(
        json.dumps({"schema_version": "1", "builder_version": "1", "layer": "project",
                    "nodes": nodes, "edges": edges}),
        encoding="utf-8",
    )
    communities = [
        {"community_id": "project:c0", "label": "auth", "seed_node_id": "src/auth.py::login",
         "node_ids": ["src/auth.py", "src/auth.py::login", "src/auth.py::Session"],
         "node_count": 3, "boundary_node_count": 1},
        {"community_id": "project:c1", "label": "server", "seed_node_id": "api/server.py::serve",
         "node_ids": ["api/server.py", "api/server.py::serve"],
         "node_count": 2, "boundary_node_count": 1},
    ]
    (_graph_dir(root) / "project-graph-clusters.json").write_text(
        json.dumps({"cluster_schema_version": "1", "cluster_builder_version": "9",
                    "layer": "project", "communities": communities,
                    "community_count": len(communities)}),
        encoding="utf-8",
    )


class ScaffoldTests(unittest.TestCase):
    def test_scaffolds_stubs_for_areas(self) -> None:
        gen = load_gen()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_two_area_fixture(root)
            created = gen.scaffold_area_contexts(root)
            self.assertTrue(created, "expected at least one area stub")
            model = gen.compute_areas(root)
            for area in model.areas:
                rel = gen._area_context_rel_path(area)
                dest = root / rel
                self.assertTrue(dest.is_file(), f"missing {rel}")
                body = dest.read_text(encoding="utf-8")
                # Stub-only: placeholder + map pointer, never authored conventions.
                self.assertIn("Status: stub", body)
                self.assertIn("Fill in conventions", body)
                self.assertIn("codebase-map.md", body)

    def test_idempotent_and_never_overwrites(self) -> None:
        gen = load_gen()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_two_area_fixture(root)
            model = gen.compute_areas(root)
            first_area = model.areas[0]
            rel = gen._area_context_rel_path(first_area)
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            human = "# My area\n\nHuman-authored conventions: never clobber me.\n"
            dest.write_text(human, encoding="utf-8")

            created1 = gen.scaffold_area_contexts(root)
            # The pre-existing human file must NOT be in the created list.
            self.assertNotIn(rel, created1)
            self.assertEqual(dest.read_text(encoding="utf-8"), human)

            # Second run is a no-op (all present now).
            created2 = gen.scaffold_area_contexts(root)
            self.assertEqual(created2, [])
            self.assertEqual(dest.read_text(encoding="utf-8"), human)

    def test_scaffold_noop_when_no_areas(self) -> None:
        gen = load_gen()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(gen.scaffold_area_contexts(root), [])


class MapLinkTests(unittest.TestCase):
    def test_links_area_to_agents_md_when_present(self) -> None:
        gen = load_gen()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_two_area_fixture(root)
            model = gen.compute_areas(root)
            area = model.areas[0]
            rel = gen._area_context_rel_path(area)
            href = gen._area_context_link_href(rel)  # map-relative (resolves under docs-lint)

            # Without the file: no link.
            md_no = gen.render_markdown(model, root=root)
            self.assertNotIn(f"]({href})", md_no)

            # With the file present: link rendered. The href is relative to the
            # rendered map's directory (docs/references), NOT a repo-root path —
            # otherwise docs-lint reports a broken link (the 1p5xc bug).
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("# stub\n", encoding="utf-8")
            md_yes = gen.render_markdown(model, root=root)
            self.assertIn(f"]({href})", md_yes)
            self.assertIn(f"[{rel}]", md_yes)  # display text is the repo-root path
            self.assertIn("Area context:", md_yes)


class RootBridgeTests(unittest.TestCase):
    def _render(self, repo_root: Path):
        return subprocess.run(
            ["python3", str(RENDER_SCRIPT), "--repo-root", str(repo_root)],
            cwd=SCRIPTS_ROOT, capture_output=True, text=True, check=False,
        )

    def test_replaces_prose_pointer_with_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            (repo_root / "CLAUDE.md").write_text(
                "# Claude\n\nThin pointer. Read `AGENTS.md` first for the full surface.\n\n"
                "## Startup Order\n\n1. AGENTS.md\n",
                encoding="utf-8",
            )
            result = self._render(repo_root)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            claude = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("@AGENTS.md", claude)
            self.assertNotIn("Thin pointer. Read", claude)
            self.assertIn("wave:root-bridge begin", claude)

    def test_bridge_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            (repo_root / "CLAUDE.md").write_text(
                "# Claude\n\nThin pointer. Read `AGENTS.md` first.\n\n## Startup Order\n\n1. x\n",
                encoding="utf-8",
            )
            self._render(repo_root)
            first = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
            self._render(repo_root)
            second = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
            # The root-bridge block itself is stable across re-renders: exactly
            # one import line and one marker pair, identical between runs.
            self.assertEqual(second.count("@AGENTS.md"), 1)
            self.assertEqual(second.count("wave:root-bridge begin"), 1)
            for text in (first, second):
                begin = text.index("wave:root-bridge begin")
                end = text.index("wave:root-bridge end")
                self.assertLess(begin, end)
            # The bridge region is byte-identical between runs.
            def bridge(t: str) -> str:
                b = t.index("wave:root-bridge begin")
                e = t.index("wave:root-bridge end")
                return t[b:e]
            self.assertEqual(bridge(first), bridge(second))


class RepoInvariantTests(unittest.TestCase):
    """Assert the no-@import-outside-root + no-subdir-CLAUDE.md constraints on
    the live repo, plus the root bridge and seed weave."""

    def test_root_claude_md_is_import_not_prose(self) -> None:
        claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("@AGENTS.md", claude)
        self.assertNotIn("Thin pointer. Read", claude)

    def test_no_import_outside_root_and_no_subdir_claude_md(self) -> None:
        # Search tracked files only (git) to avoid index blobs / venvs.
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
        for rel in tracked:
            name = rel.rsplit("/", 1)[-1]
            # No subdirectory CLAUDE.md bridge files.
            if name == "CLAUDE.md":
                self.assertEqual(rel, "CLAUDE.md", f"subdirectory CLAUDE.md not allowed: {rel}")
            # @AGENTS.md import line allowed only in the root CLAUDE.md.
            if not rel.endswith(".md"):
                continue
            try:
                text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for line in text.splitlines():
                if line.strip() == "@AGENTS.md":
                    self.assertEqual(
                        rel, "CLAUDE.md",
                        f"@AGENTS.md import found outside root CLAUDE.md: {rel}",
                    )

    def test_convention_in_root_agents_seed_surface(self) -> None:
        # Seed-first: the operating instruction is woven into the run-contract
        # seed (020) so it renders into every host surface, and seed-050 carries
        # the per-area context + root-bridge guidance.
        seed_020 = (PROJECT_ROOT / "framework" / "seeds" / "020-run-contract.prompt.md").read_text(encoding="utf-8")
        self.assertIn("consult that area's `AGENTS.md`", seed_020)
        self.assertIn("codebase-map.md", seed_020)

        seed_050 = (PROJECT_ROOT / "framework" / "seeds" / "050-agent-entry-surface-bootstrap.prompt.md").read_text(encoding="utf-8")
        self.assertIn("@AGENTS.md", seed_050)
        self.assertIn("consult that area's `AGENTS.md`", seed_050)

        # Rendered root AGENTS.md carries the standing convention line.
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("consult that area's `AGENTS.md`", agents)


if __name__ == "__main__":
    unittest.main()
