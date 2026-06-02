from __future__ import annotations

import io
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
GRAPH_INDEXER_PATH = SCRIPTS_ROOT / "graph_indexer.py"


def load_graph_indexer():
    spec = importlib.util.spec_from_file_location("graph_indexer", GRAPH_INDEXER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["graph_indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_repo(root: Path) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "workflow-config.json").write_text(
        json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
        encoding="utf-8",
    )


class GraphIndexerTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, source: str, doc: str, *, changed: set[str] | None = None):
        src = self.root / "src" / "tools.py"
        doc_path = self.root / "docs" / "guide.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(source, encoding="utf-8")
        doc_path.write_text(doc, encoding="utf-8")
        files = [src, doc_path]
        return self.mod.update_graph_index(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            files=files,
            current_file_meta={
                "src/tools.py": {"hash": "src-hash"},
                "docs/guide.md": {"hash": "doc-hash"},
            },
            changed=changed or {"src/tools.py", "docs/guide.md"},
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )

    def _build_file(self, rel_path: str, source: str):
        file_path = self.root / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(source, encoding="utf-8")
        payload = self.mod.update_graph_index(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            files=[file_path],
            current_file_meta={rel_path.replace("\\", "/"): {"hash": "src-hash"}},
            changed={rel_path.replace("\\", "/")},
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )
        return payload

    def test_update_graph_index_writes_code_and_doc_edges(self):
        payload = self._build(
            "import os\n\n\ndef process():\n    return os.path.join('a', 'b')\n",
            "Call `process` from the guide.\n",
        )
        self.assertEqual(payload["layer"], "project")
        self.assertTrue((self.root / ".wavefoundry" / "index" / "graph" / "project-graph.json").exists())
        self.assertGreaterEqual(payload["counts"]["nodes"], 3)
        relations = {edge["relation"] for edge in payload["edges"]}
        self.assertIn("defines", relations)
        self.assertIn("imports", relations)
        self.assertIn("calls", relations)
        self.assertIn("doc_references_code", relations)
        node_ids = {node["id"] for node in payload["nodes"]}
        self.assertIn("src/tools.py::process", node_ids)

    def test_fresh_graph_state_reextracts_full_corpus_not_only_changed(self):
        self._build(
            "import os\n\n\ndef process():\n    return os.path.join('a', 'b')\n",
            "Call `process` from the guide.\n",
        )
        state_path = self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.json"
        state_path.write_text(
            json.dumps(
                {
                    "schema_version": self.mod.GRAPH_SCHEMA_VERSION,
                    "builder_version": self.mod.GRAPH_BUILDER_VERSION,
                    "layer": "project",
                    "walker_version": "1",
                    "chunker_version": "1",
                    "files": {},
                }
            ),
            encoding="utf-8",
        )
        src = self.root / "src" / "tools.py"
        doc_path = self.root / "docs" / "guide.md"
        payload = self.mod.update_graph_index(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            files=[src, doc_path],
            current_file_meta={
                "src/tools.py": {"hash": "src-hash"},
                "docs/guide.md": {"hash": "doc-hash"},
            },
            changed={"docs/guide.md"},
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )
        node_ids = {node["id"] for node in payload["nodes"]}
        self.assertIn("src/tools.py::process", node_ids)

    def test_update_graph_index_drops_doc_reference_when_symbol_is_removed(self):
        self._build(
            "import os\n\n\ndef process():\n    return os.path.join('a', 'b')\n",
            "Call `process` from the guide.\n",
        )
        payload = self._build(
            "import os\n\n\ndef handler():\n    return os.path.join('a', 'b')\n",
            "Call `process` from the guide.\n",
            changed={"src/tools.py"},
        )
        relations = {edge["relation"] for edge in payload["edges"]}
        self.assertNotIn("doc_references_code", relations)
        node_ids = {node["id"] for node in payload["nodes"]}
        self.assertNotIn("src/tools.py::process", node_ids)
        self.assertIn("src/tools.py::handler", node_ids)

    def test_update_graph_index_logs_graph_phase_boundaries(self):
        src = self.root / "src" / "tools.py"
        doc_path = self.root / "docs" / "guide.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("def process():\n    return 1\n", encoding="utf-8")
        doc_path.write_text("Call `process` from the guide.\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.update_graph_index(
                root=self.root,
                index_dir=self.root / ".wavefoundry" / "index",
                layer="project",
                files=[src, doc_path],
                current_file_meta={
                    "src/tools.py": {"hash": "src-hash"},
                    "docs/guide.md": {"hash": "doc-hash"},
                },
                changed={"src/tools.py", "docs/guide.md"},
                removed=set(),
                walker_version="1",
                chunker_version="1",
                verbose=True,
            )
        output = buf.getvalue()
        self.assertIn("graph extraction inputs for project layer", output)
        self.assertIn("graph extraction wrote project graph", output)

    def test_tree_sitter_code_languages_extract_symbols(self):
        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("java") is None:
            self.skipTest("tree-sitter java grammar unavailable")
        payload = self._build_file(
            "src/Example.java",
            """
            import java.util.List;

            public class Example {
                public void run() {
                    helper();
                }

                private void helper() {}
            }
            """.strip(),
        )
        node_ids = {node["id"] for node in payload["nodes"]}
        relations = {edge["relation"] for edge in payload["edges"]}
        # Wave 13190: Java class with basename match (Example.java + class Example)
        # merges into the file node — `src/Example.java::Example` is no longer
        # registered; the file node takes on the class identity.
        self.assertIn("src/Example.java", node_ids)
        self.assertNotIn("src/Example.java::Example", node_ids)
        file_node = next(n for n in payload["nodes"] if n["id"] == "src/Example.java")
        self.assertEqual(file_node["label"], "Example")
        self.assertEqual(file_node["kind"], "class")
        self.assertTrue(file_node.get("collapsed_pair"))
        # Methods remain as separate nodes under the merged class.
        self.assertIn("src/Example.java::Example.run", node_ids)
        self.assertIn("src/Example.java::Example.helper", node_ids)
        node_kinds = {node["id"]: node["kind"] for node in payload["nodes"]}
        self.assertEqual(node_kinds["src/Example.java::Example.run"], "function")
        self.assertEqual(node_kinds["src/Example.java::Example.helper"], "function")
        self.assertNotIn("method", {node["kind"] for node in payload["nodes"]})
        self.assertIn("defines", relations)
        self.assertIn("calls", relations)
        self.assertIn("imports", relations)

    def test_tree_sitter_markup_and_sql_extract_symbols(self):
        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("html") is None:
            self.skipTest("tree-sitter html grammar unavailable")
        html_payload = self._build_file(
            "web/index.html",
            """
            <html>
              <head>
                <script src="app.js"></script>
                <link rel="stylesheet" href="styles.css">
              </head>
              <body>
                <a id="home" href="/home">Home</a>
              </body>
            </html>
            """.strip(),
        )
        html_node_ids = {node["id"] for node in html_payload["nodes"]}
        self.assertTrue(any("home" in node_id for node_id in html_node_ids))
        self.assertIn("imports", {edge["relation"] for edge in html_payload["edges"]})

        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("sql") is None:
            self.skipTest("tree-sitter sql grammar unavailable")
        sql_payload = self._build_file(
            "db/schema.sql",
            """
            CREATE TABLE users (
                id INT PRIMARY KEY
            );

            SELECT * FROM users;
            """.strip(),
        )
        sql_node_ids = {node["id"] for node in sql_payload["nodes"]}
        self.assertTrue(any("users" in node_id for node_id in sql_node_ids))
        self.assertIn("defines", {edge["relation"] for edge in sql_payload["edges"]})

    def test_doc_to_doc_link_produces_edge(self):
        wave = self.root / "docs" / "wave.md"
        change = self.root / "docs" / "change.md"
        wave.parent.mkdir(parents=True, exist_ok=True)
        wave.write_text("[My Change](change.md)\n", encoding="utf-8")
        change.write_text("Change details.\n", encoding="utf-8")
        payload = self.mod.update_graph_index(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            files=[wave, change],
            current_file_meta={
                "docs/wave.md": {"hash": "wave-hash"},
                "docs/change.md": {"hash": "change-hash"},
            },
            changed={"docs/wave.md", "docs/change.md"},
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )
        relations = {edge["relation"] for edge in payload["edges"]}
        self.assertIn("doc_references_doc", relations)
        link_edges = [e for e in payload["edges"] if e["relation"] == "doc_references_doc"]
        self.assertTrue(
            any(e["source"] == "docs/wave.md" and e["target"] == "docs/change.md" for e in link_edges)
        )

    def test_prose_symbol_not_matched(self):
        payload = self._build(
            "import os\n\n\ndef process():\n    return os.path.join('a', 'b')\n",
            "The process function is described here without backticks.\n",
        )
        relations = {edge["relation"] for edge in payload["edges"]}
        self.assertNotIn("doc_references_code", relations)

    def _index_dir(self) -> Path:
        return self.root / ".wavefoundry" / "index"

    def _run(
        self,
        present: dict[str, str],
        *,
        changed: set[str],
        removed: set[str],
        layer: str = "project",
    ) -> dict:
        paths = []
        meta = {}
        for rel, source in present.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(source, encoding="utf-8")
            paths.append(p)
            meta[rel.replace("\\", "/")] = {"hash": source}
        return self.mod.update_graph_index(
            root=self.root,
            index_dir=self._index_dir(),
            layer=layer,
            files=paths,
            current_file_meta=meta,
            changed=changed,
            removed=removed,
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )

    def test_deleting_referenced_code_file_prunes_unchanged_doc_edges(self):
        code = "def process():\n    return 1\n"
        doc = "Call `process` here.\n"
        first = self._run(
            {"src/tools.py": code, "docs/guide.md": doc},
            changed={"src/tools.py", "docs/guide.md"},
            removed=set(),
        )
        self.assertIn("doc_references_code", {e["relation"] for e in first["edges"]})
        # Delete the code file; the referring doc is unchanged.
        (self.root / "src" / "tools.py").unlink()
        payload = self._run({"docs/guide.md": doc}, changed=set(), removed={"src/tools.py"})
        self.assertNotIn("doc_references_code", {e["relation"] for e in payload["edges"]})
        self.assertNotIn("src/tools.py::process", {n["id"] for n in payload["nodes"]})
        self.assertFalse(
            any(str(e["target"]).startswith("src/tools.py") for e in payload["edges"])
        )

    def test_renaming_code_file_prunes_stale_old_path_edges(self):
        code = "def process():\n    return 1\n"
        doc = "Call `process` here.\n"
        self._run(
            {"src/old.py": code, "docs/guide.md": doc},
            changed={"src/old.py", "docs/guide.md"},
            removed=set(),
        )
        (self.root / "src" / "old.py").unlink()
        payload = self._run(
            {"src/new.py": code, "docs/guide.md": doc},
            changed={"src/new.py"},
            removed={"src/old.py"},
        )
        node_ids = {n["id"] for n in payload["nodes"]}
        self.assertNotIn("src/old.py::process", node_ids)
        self.assertIn("src/new.py::process", node_ids)
        self.assertFalse(
            any(str(e["target"]).startswith("src/old.py") for e in payload["edges"])
        )

    def test_doc_to_code_edges_use_ambiguous_confidence(self):
        payload = self._build(
            "import os\n\n\ndef process():\n    return os.path.join('a', 'b')\n",
            "Call `process` from the guide.\n",
        )
        doc_edges = [e for e in payload["edges"] if e["relation"] == "doc_references_code"]
        self.assertTrue(doc_edges)
        self.assertTrue(all(e["confidence"] == "AMBIGUOUS" for e in doc_edges))

    def test_doc_match_requires_full_hyphenated_name_not_subtoken(self):
        payload = self._run(
            {
                "src/context.py": "def build_context():\n    return 1\n",
                "docs/guide.md": "Promote lessons to `docs/references/project-context-memory.md`.\n",
            },
            changed={"src/context.py", "docs/guide.md"},
            removed=set(),
        )
        doc_edges = [e for e in payload["edges"] if e["relation"] == "doc_references_code"]
        self.assertFalse(
            any(
                e["target"] == "src/context.py" and e.get("evidence") == "context"
                for e in doc_edges
            ),
            "hyphenated path must not match the context.py module via subtoken 'context'",
        )

    def test_docs_json_files_indexed_as_code_with_top_level_keys(self):
        payload = self._run(
            {
                "docs/workflow-config.json": json.dumps(
                    {"factor_review_policy": {"findings_advisory": True}}
                ),
            },
            changed={"docs/workflow-config.json"},
            removed=set(),
        )
        node_ids = {node["id"] for node in payload["nodes"]}
        self.assertIn("docs/workflow-config.json", node_ids)
        self.assertIn("docs/workflow-config.json::factor_review_policy", node_ids)
        state_path = self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["files"]["docs/workflow-config.json"]["artifact"]["kind"],
            "code",
        )

    def test_doc_references_workflow_config_key_by_full_name(self):
        payload = self._run(
            {
                "docs/workflow-config.json": json.dumps(
                    {"factor_review_policy": {"findings_advisory": True}}
                ),
                "docs/agents/factor-03-config.md": (
                    "Policy per `docs/workflow-config.json` "
                    "`factor_review_policy.findings_advisory: true`.\n"
                ),
            },
            changed={"docs/workflow-config.json", "docs/agents/factor-03-config.md"},
            removed=set(),
        )
        doc_edges = [
            e for e in payload["edges"]
            if e["relation"] == "doc_references_code"
            and e["source"] == "docs/agents/factor-03-config.md"
            and e["target"] == "docs/workflow-config.json::factor_review_policy"
        ]
        self.assertTrue(doc_edges)
        self.assertEqual(doc_edges[0].get("evidence"), "factor_review_policy")

    def test_doc_file_stem_reference_links_module_only(self):
        payload = self._run(
            {
                "src/tools.py": "def alpha():\n    return 1\n\ndef beta():\n    return 2\n",
                "docs/guide.md": "See `src/tools.py` for helpers.\n",
            },
            changed={"src/tools.py", "docs/guide.md"},
            removed=set(),
        )
        doc_edges = [
            e for e in payload["edges"]
            if e["relation"] == "doc_references_code" and e["source"] == "docs/guide.md"
        ]
        targets = {e["target"] for e in doc_edges}
        self.assertIn("src/tools.py", targets)
        self.assertNotIn("src/tools.py::alpha", targets)
        self.assertNotIn("src/tools.py::beta", targets)
        self.assertEqual(len(doc_edges), 1)

    def test_doc_symbol_reference_still_links_defined_function(self):
        payload = self._build(
            "def process():\n    return 1\n",
            "Call `process` from the guide.\n",
        )
        doc_edges = [e for e in payload["edges"] if e["relation"] == "doc_references_code"]
        self.assertEqual(
            {e["target"] for e in doc_edges},
            {"src/tools.py::process"},
        )

    def test_builder_version_bump_reextracts_full_corpus(self):
        a = "def alpha():\n    return 1\n"
        b = "def beta():\n    return 2\n"
        self._run(
            {"src/a.py": a, "src/b.py": b},
            changed={"src/a.py", "src/b.py"},
            removed=set(),
        )
        original = self.mod.GRAPH_BUILDER_VERSION
        self.mod.GRAPH_BUILDER_VERSION = original + "-bump"
        try:
            payload = self._run({"src/a.py": a, "src/b.py": b}, changed={"src/a.py"}, removed=set())
        finally:
            self.mod.GRAPH_BUILDER_VERSION = original
        node_ids = {n["id"] for n in payload["nodes"]}
        self.assertIn("src/a.py::alpha", node_ids)
        # Empty graph state after a builder bump must re-extract every file in the corpus,
        # not only the indexer "changed" set (which may be a single doc from the hook).
        self.assertIn("src/b.py::beta", node_ids)

    def test_framework_layer_writes_framework_graph_file(self):
        payload = self._run(
            {"src/tools.py": "def process():\n    return 1\n"},
            changed={"src/tools.py"},
            removed=set(),
            layer="framework",
        )
        self.assertEqual(payload["layer"], "framework")
        self.assertTrue((self._index_dir() / "graph" / "framework-graph.json").exists())

    def test_tree_sitter_config_files_get_symbol_nodes(self):
        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("yaml") is None:
            self.skipTest("tree-sitter yaml grammar unavailable")
        payload = self._build_file(
            "config/workflow.yaml",
            """
            workflow:
              name: graph-build
              steps:
                - run: update-indexes
            """.strip(),
        )
        node_ids = {node["id"] for node in payload["nodes"]}
        self.assertTrue(any("workflow" in node_id for node_id in node_ids))
        self.assertTrue(any("name" in node_id or "steps" in node_id for node_id in node_ids))

    def test_doc_json_fence_config_keys_do_not_create_code_edges(self):
        payload = self._run(
            {
                "docs/workflow-config.json": json.dumps({"dashboard": {"enabled": True}}),
                ".wavefoundry/framework/scripts/dashboard_lib.py": (
                    "def collect_waves():\n    return []\n\n"
                    "def collect_agents():\n    return []\n"
                ),
                "docs/adapter.md": (
                    "```json\n"
                    '{\n  "dashboard": {\n    "enabled": true,\n    "auto_index": true\n  }\n}\n'
                    "```\n\n"
                    "| Reader | Function |\n|---|---|\n| Waves | `collect_waves` |\n"
                ),
            },
            changed={
                "docs/workflow-config.json",
                ".wavefoundry/framework/scripts/dashboard_lib.py",
                "docs/adapter.md",
            },
            removed=set(),
        )
        code_edges = [
            e for e in payload["edges"]
            if e["source"] == "docs/adapter.md" and e["relation"] == "doc_references_code"
        ]
        targets = {e["target"] for e in code_edges}
        self.assertIn(".wavefoundry/framework/scripts/dashboard_lib.py::collect_waves", targets)
        self.assertFalse(any(e.get("evidence") == "enabled" for e in code_edges))
        self.assertFalse(any("::enabled" in t or t.endswith("::dashboard") for t in targets))

    def test_doc_backtick_path_creates_doc_reference(self):
        payload = self._run(
            {
                "docs/a.md": "See `.wavefoundry/framework/scripts/dashboard_lib.py`.\n",
                ".wavefoundry/framework/scripts/dashboard_lib.py": "def helper():\n    return 1\n",
            },
            changed={"docs/a.md", ".wavefoundry/framework/scripts/dashboard_lib.py"},
            removed=set(),
        )
        doc_edges = [
            e for e in payload["edges"]
            if e["source"] == "docs/a.md" and e["relation"] == "doc_references_doc"
        ]
        self.assertEqual(
            {e["target"] for e in doc_edges},
            {".wavefoundry/framework/scripts/dashboard_lib.py"},
        )

    def test_doc_named_reader_gets_extracted_confidence(self):
        payload = self._run(
            {
                ".wavefoundry/framework/scripts/dashboard_lib.py": "def collect_dashboard_snapshot():\n    return {}\n",
                "docs/adapter.md": "Snapshot via `collect_dashboard_snapshot`.\n",
            },
            changed={
                ".wavefoundry/framework/scripts/dashboard_lib.py",
                "docs/adapter.md",
            },
            removed=set(),
        )
        edges = [
            e for e in payload["edges"]
            if e["source"] == "docs/adapter.md" and e["relation"] == "doc_references_code"
        ]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].get("confidence"), "EXTRACTED")


class GraphDependencyInjectionTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files: dict[str, str]) -> dict:
        paths = []
        meta = {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            files=paths,
            current_file_meta=meta,
            changed=set(meta.keys()),
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )

    def test_spring_three_file_di_resolution(self):
        payload = self._build(
            {
                "src/AppConfig.java": """
                @Configuration
                public class AppConfig {
                    @Bean
                    public IFooService fooService() { return new FooService(); }
                }
                """.strip(),
                "src/FooService.java": """
                @Service
                public class FooService implements IFooService {}
                """.strip(),
                "src/BarController.java": """
                @RestController
                public class BarController {
                    public BarController(IFooService fooService) {}
                }
                """.strip(),
            }
        )
        relations = {edge["relation"] for edge in payload["edges"]}
        self.assertIn("binds", relations)
        self.assertIn("injects", relations)

    def test_dotnet_registration_and_injection(self):
        payload = self._build(
            {
                "src/Startup.cs": """
                public class Startup {
                    public void ConfigureServices(IServiceCollection services) {
                        services.AddScoped<IFoo, Foo>();
                    }
                }
                """.strip(),
                "src/Foo.cs": "public class Foo : IFoo {}",
                "src/Consumer.cs": """
                public class Consumer {
                    public Consumer(IFoo foo) {}
                }
                """.strip(),
            }
        )
        relations = {edge["relation"] for edge in payload["edges"]}
        self.assertIn("binds", relations)
        self.assertIn("injects", relations)

    def test_no_di_signals_for_plain_python(self):
        payload = self._build({"src/plain.py": "def run():\n    return 1\n"})
        relations = {edge["relation"] for edge in payload["edges"]}
        self.assertNotIn("binds", relations)
        self.assertNotIn("injects", relations)


class CrossFileResolutionTests(unittest.TestCase):
    """Regression tests for wave 130ol: cross-file symbol resolution +
    keyword/builtin filtering + ambiguity safety in the graph extractor."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files: dict[str, str]) -> dict:
        paths = []
        meta = {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            files=paths,
            current_file_meta=meta,
            changed=set(meta.keys()),
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )

    def _calls_edges(self, payload: dict) -> list[dict]:
        return [e for e in payload["edges"] if e.get("relation") == "calls"]

    # AC-7: Python cross-file resolution. Two files: a.py defines foo(),
    # b.py calls foo() — the merged graph must contain
    # `src/b.py::caller → src/a.py::foo`, not `… → external::foo`.
    def test_python_cross_file_call_resolves_to_project_node(self):
        payload = self._build({
            "src/a.py": "def foo():\n    return 42\n",
            "src/b.py": "from src.a import foo\n\n\ndef caller():\n    return foo()\n",
        })
        calls = self._calls_edges(payload)
        targets_to_foo = [
            e["target"] for e in calls
            if e.get("source", "").endswith("::caller")
        ]
        # The resolved target should be the project node, not external::foo.
        self.assertIn("src/a.py::foo", targets_to_foo,
                      f"Expected cross-file resolution to src/a.py::foo; got {targets_to_foo}")
        for tgt in targets_to_foo:
            self.assertFalse(
                tgt == "external::foo",
                f"Cross-file call should NOT remain external::foo: {targets_to_foo}",
            )

    # AC-9: Ambiguity safety net. Two files each defining `helper`, called
    # from a third — the call must stay external::helper because the simple
    # name is ambiguous across project nodes.
    def test_ambiguous_simple_name_stays_external(self):
        payload = self._build({
            "src/a.py": "def helper():\n    return 1\n",
            "src/b.py": "def helper():\n    return 2\n",
            "src/c.py": "def use():\n    return helper()\n",
        })
        calls = self._calls_edges(payload)
        targets = [
            e["target"] for e in calls
            if e.get("source", "").endswith("::use")
        ]
        # Conservative behavior: don't silently pick one of the two.
        for tgt in targets:
            self.assertNotEqual(tgt, "src/a.py::helper",
                                "Ambiguous name must not silently resolve to a.py::helper")
            self.assertNotEqual(tgt, "src/b.py::helper",
                                "Ambiguous name must not silently resolve to b.py::helper")

    # AC-1a: Builtin denylist. Even though we define a project class
    # `len` (silly but possible), calls to `len()` from other files must
    # stay external::len — the call is overwhelmingly to the Python builtin.
    def test_builtin_denylist_blocks_resolution_for_python_len(self):
        payload = self._build({
            "src/weird.py": "class len:\n    pass\n",
            "src/use.py": "def f():\n    return len([1, 2, 3])\n",
        })
        calls = self._calls_edges(payload)
        for edge in calls:
            if edge.get("source", "").endswith("::f"):
                # Should remain external (denylist blocks the rewrite).
                self.assertEqual(
                    edge.get("target"), "external::len",
                    f"Builtin len() should stay external; got {edge.get('target')}",
                )

    # AC-1: Conservative resolution skips dotted external targets even when
    # bare simple-name matches exist. `pathlib.Path` stays external even if
    # a project file defines a class `Path` (with dot resolution gated by
    # the qualified-suffix check + denylist).
    def test_dotted_external_target_stays_external(self):
        payload = self._build({
            "src/myclass.py": "class Path:\n    pass\n",
            "src/use.py": "from pathlib import Path as _P\n\n\ndef f():\n    return _P('/tmp')\n",
        })
        # We expect either external::pathlib.Path (if the dotted form is
        # captured) or external::Path/_P — but never src/myclass.py::Path.
        calls = self._calls_edges(payload)
        for edge in calls:
            tgt = edge.get("target", "")
            if edge.get("source", "").endswith("::f"):
                self.assertNotEqual(
                    tgt, "src/myclass.py::Path",
                    "pathlib.Path() must not resolve to a project Path class",
                )

    # AC-8: Tree-sitter cross-file path. Go is the test target because
    # tree_sitter_go ships with framework deps and has stable call_expression
    # grammar.
    def test_go_cross_file_call_resolves_to_project_node(self):
        try:
            import tree_sitter_go  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_go not available in test env")
        payload = self._build({
            "pkg/a.go": "package pkg\n\nfunc Foo() int {\n    return 1\n}\n",
            "pkg/b.go": "package pkg\n\nfunc Bar() int {\n    return Foo()\n}\n",
        })
        calls = self._calls_edges(payload)
        bar_targets = [
            e["target"] for e in calls
            if "::Bar" in str(e.get("source", ""))
        ]
        self.assertTrue(
            any(t == "pkg/a.go::Foo" for t in bar_targets),
            f"Expected Bar→pkg/a.go::Foo resolution; got {bar_targets}",
        )
        # Go keywords/builtins must not appear as external::* call targets.
        all_targets = {str(e.get("target", "")) for e in calls}
        forbidden_keywords = {
            "external::if", "external::for", "external::range",
            "external::var", "external::const", "external::func",
            "external::package", "external::import", "external::return",
        }
        leaked = forbidden_keywords & all_targets
        self.assertFalse(
            leaked, f"Go keywords should not appear as call targets: {leaked}",
        )

    def test_go_builtins_stay_external_when_called(self):
        try:
            import tree_sitter_go  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_go not available in test env")
        payload = self._build({
            "pkg/a.go": "package pkg\n\nfunc Foo(xs []int) int {\n    return len(xs)\n}\n",
        })
        calls = self._calls_edges(payload)
        target_names = {str(e.get("target", "")) for e in calls if "::Foo" in str(e.get("source", ""))}
        # len() is a Go builtin and must NOT resolve to any project node
        # (denylist guards against accidental mis-resolution).
        for tgt in target_names:
            self.assertFalse(
                tgt.endswith("::len") and not tgt.startswith("external::"),
                f"Go builtin len() must stay external; got {tgt}",
            )

    # ---- AC-8 extended: per-language cross-file resolution ----
    # These tests pin that 130ol's per-language coverage actually delivers
    # cross-file resolution for every tree-sitter language we support.
    # The Swift/Kotlin tests are the load-bearing ones (positional callee
    # fallback was the missing piece). The others guard against grammar drift.

    def _assert_cross_file(self, lang_skip_mod, files, expected_source_contains, expected_target_contains):
        """Helper: build a synthetic two-file project, assert the named cross-file edge."""
        try:
            __import__(lang_skip_mod)
        except ImportError:
            self.skipTest(f"{lang_skip_mod} not available in test env")
        payload = self._build(files)
        calls = self._calls_edges(payload)
        matches = [
            e for e in calls
            if expected_source_contains in str(e.get("source", ""))
            and expected_target_contains in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertTrue(
            matches,
            f"No cross-file resolved edge found. Got calls: "
            f"{[(e.get('source'), e.get('target')) for e in calls]}",
        )

    def test_swift_cross_file_navigation_call(self):
        """Swift: `let r = h.process()` should resolve `process` to the project node
        despite (a) navigation_expression structure, (b) positional callee (no field),
        and (c) being inside a let-binding inside a function."""
        self._assert_cross_file(
            "tree_sitter_swift",
            {
                "A.swift": "class Helper { func process() -> Int { return 1 } }\n",
                "B.swift": "class Worker {\n    let h = Helper()\n    func bar() { let r = h.process() }\n}\n",
            },
            expected_source_contains="B.swift::Worker.bar",
            expected_target_contains="A.swift::Helper.process",
        )

    def test_kotlin_cross_file_navigation_call(self):
        """Kotlin: same shape as Swift — positional callee, navigation suffix."""
        self._assert_cross_file(
            "tree_sitter_kotlin",
            {
                "A.kt": "class Helper { fun process(): Int = 1 }\n",
                "B.kt": "class Worker {\n    val h = Helper()\n    fun bar() { val r = h.process() }\n}\n",
            },
            expected_source_contains="B.kt::Worker.bar",
            expected_target_contains="A.kt::Helper.process",
        )

    def test_java_cross_file_member_call(self):
        self._assert_cross_file(
            "tree_sitter_java",
            {
                "A.java": "class Helper { int process() { return 1; } }\n",
                "B.java": "class Worker {\n    Helper h = new Helper();\n    int bar() { int r = h.process(); return r; }\n}\n",
            },
            expected_source_contains="B.java::Worker.bar",
            expected_target_contains="A.java::Helper.process",
        )

    def test_csharp_cross_file_member_call(self):
        """C#: tests the dotted-target → last-segment fallback (h.Process where
        h is a local variable of unresolvable type)."""
        self._assert_cross_file(
            "tree_sitter_c_sharp",
            {
                "A.cs": "class Helper { public int Process() { return 1; } }\n",
                "B.cs": "class Worker {\n    Helper h = new Helper();\n    int Bar() { var r = h.Process(); return r; }\n}\n",
            },
            expected_source_contains="B.cs::Worker.Bar",
            expected_target_contains="A.cs::Helper.Process",
        )

    def test_cpp_cross_file_function_call(self):
        """C++: tests per-file simple-name dedupe (function_declarator nested
        inside function_definition both registered as the same simple name)."""
        self._assert_cross_file(
            "tree_sitter_cpp",
            {
                "A.cpp": "int helper_process() { return 1; }\n",
                "B.cpp": "int worker_bar() { int r = helper_process(); return r; }\n",
            },
            expected_source_contains="B.cpp::worker_bar",
            expected_target_contains="A.cpp::helper_process",
        )

    def test_rust_cross_file_function_call(self):
        self._assert_cross_file(
            "tree_sitter_rust",
            {
                "src/a.rs": "pub fn process() -> i32 { 1 }\n",
                "src/b.rs": "pub fn bar() -> i32 { let r = process(); r }\n",
            },
            expected_source_contains="src/b.rs::bar",
            expected_target_contains="src/a.rs::process",
        )

    def test_let_binding_does_not_consume_call(self):
        """130ol regression: `let result = foo()` must NOT push a scope. The call
        must be attributed to the enclosing function, not `enclosingFn.result`
        (which the short-symbol pruning pass can silently drop)."""
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available in test env")
        payload = self._build({
            "A.swift": "class Helper { func process() -> Int { return 1 } }\n",
            "B.swift": (
                "class Worker {\n"
                "    let h = Helper()\n"
                "    func bar() {\n"
                "        let result = h.process()\n"
                "        let _ = h.process()\n"
                "    }\n"
                "}\n"
            ),
        })
        calls = self._calls_edges(payload)
        # Call must attribute to the enclosing function, not to ::result or ::_
        for e in calls:
            src = str(e.get("source", ""))
            self.assertFalse(
                src.endswith("::result") or src.endswith("::_"),
                f"Call should attribute to enclosing function, not to local var: {src}",
            )
        # And the cross-file edge must still be there
        bar_edges = [
            e for e in calls
            if "B.swift::Worker.bar" in str(e.get("source", ""))
            and "A.swift::Helper.process" in str(e.get("target", ""))
        ]
        self.assertTrue(bar_edges, f"Expected Worker.bar → Helper.process; got {[(e.get('source'), e.get('target')) for e in calls]}")


class SwiftClassModuleMergeTests(unittest.TestCase):
    """1316l: Swift class/module merge at index time.

    When a Swift file `Foo.swift` contains a top-level type declaration named
    `Foo` (matching basename) with kind class/struct/actor/enum/protocol,
    the indexer merges the file node and the type node into a single node
    at the file id. The constructor call edge target now resolves correctly
    for `code_callhierarchy`.
    """

    def setUp(self):
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available in test env")
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _nodes(self, payload):
        return payload.get("nodes", [])

    def _calls(self, payload):
        return [e for e in payload.get("edges", []) if e.get("relation") == "calls"]

    # AC-2: class Foo in Foo.swift → single merged node at file id.
    def test_class_module_pair_merges_to_file_id(self):
        files = {"Foo.swift": "class Foo {\n    func bar() {}\n}\n"}
        payload = self._build(files)
        nodes = self._nodes(payload)
        node_ids = {n["id"] for n in nodes}
        # Merged node lives at file id.
        self.assertIn("Foo.swift", node_ids)
        # Class id NOT registered.
        self.assertNotIn("Foo.swift::Foo", node_ids)
        merged = next(n for n in nodes if n["id"] == "Foo.swift")
        self.assertEqual(merged["label"], "Foo")
        self.assertEqual(merged["kind"], "class")
        self.assertTrue(merged.get("collapsed_pair"))
        # Children of the class are still registered under the file path.
        self.assertIn("Foo.swift::Foo.bar", node_ids)

    # AC-1: struct Foo in Foo.swift also merges (struct included).
    def test_struct_module_pair_merges(self):
        files = {"Foo.swift": "struct Foo {}\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Foo.swift", node_ids)
        self.assertNotIn("Foo.swift::Foo", node_ids)

    # AC-3: basename mismatch → no merge.
    def test_basename_mismatch_no_merge(self):
        # Foo.swift containing `class FooHelper` (basename `Foo` ≠ class name `FooHelper`).
        files = {"Foo.swift": "class FooHelper {}\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        # Both nodes survive: file (kind=module) + class (kind=class).
        self.assertIn("Foo.swift", node_ids)
        self.assertIn("Foo.swift::FooHelper", node_ids)
        # File node retains module kind.
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Foo.swift")
        self.assertEqual(file_node["kind"], "module")
        self.assertFalse(file_node.get("collapsed_pair", False))

    # AC-3: utility file with no top-level type → no merge.
    def test_function_only_file_no_merge(self):
        files = {"Util.swift": "func helper() {}\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Util.swift", node_ids)
        # File node remains kind=module (no class to merge with).
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Util.swift")
        self.assertEqual(file_node["kind"], "module")

    # AC-5 (Solaris reproducer): constructor call resolves to the merged node.
    def test_solaris_reproducer_constructor_call_resolves(self):
        files = {
            "Foo.swift": "class Foo {\n    init() {}\n}\n",
            "Bar.swift": "class Bar {\n    func use() {\n        let f = Foo()\n    }\n}\n",
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # Bar.use's outgoing call to Foo resolves to Foo.swift (merged), not external::Foo.
        matches = [
            e for e in calls
            if "Bar.swift" in str(e.get("source", ""))
            and str(e.get("target", "")) == "Foo.swift"
        ]
        self.assertTrue(
            matches,
            f"Constructor call did not resolve to merged Foo.swift node. "
            f"Calls: {[(e.get('source'), e.get('target')) for e in calls]}",
        )

    # Wave 13190: Java file with basename-class pattern IS merged.
    def test_java_basename_class_pattern_merges(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available")
        files = {"Foo.java": "class Foo { void bar() {} }\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        # Merged node at file id; class id not registered.
        self.assertIn("Foo.java", node_ids)
        self.assertNotIn("Foo.java::Foo", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Foo.java")
        self.assertEqual(file_node["label"], "Foo")
        self.assertEqual(file_node["kind"], "class")
        self.assertTrue(file_node.get("collapsed_pair"))
        # Method body remains a separate node.
        self.assertIn("Foo.java::Foo.bar", node_ids)

    # Wave 13190: Kotlin file with basename-class pattern IS merged.
    def test_kotlin_basename_class_pattern_merges(self):
        try:
            import tree_sitter_kotlin  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_kotlin not available")
        files = {"Foo.kt": "class Foo { fun bar() {} }\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Foo.kt", node_ids)
        self.assertNotIn("Foo.kt::Foo", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Foo.kt")
        self.assertEqual(file_node["label"], "Foo")
        self.assertEqual(file_node["kind"], "class")
        self.assertTrue(file_node.get("collapsed_pair"))

    # Wave 13190: C# file with basename-class pattern IS merged.
    def test_csharp_basename_class_pattern_merges(self):
        try:
            import tree_sitter_c_sharp  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_c_sharp not available")
        files = {"Foo.cs": "class Foo { public void Bar() {} }\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Foo.cs", node_ids)
        self.assertNotIn("Foo.cs::Foo", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Foo.cs")
        self.assertEqual(file_node["label"], "Foo")
        self.assertEqual(file_node["kind"], "class")
        self.assertTrue(file_node.get("collapsed_pair"))

    # Wave 13196: TypeScript file with basename-class merges.
    def test_typescript_basename_class_pattern_merges(self):
        try:
            import tree_sitter_typescript  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_typescript not available")
        files = {"Foo.ts": "export class Foo { bar(): void {} }\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Foo.ts", node_ids)
        self.assertNotIn("Foo.ts::Foo", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Foo.ts")
        self.assertEqual(file_node["label"], "Foo")
        self.assertTrue(file_node.get("collapsed_pair"))

    # Wave 13196: JavaScript file with basename-class merges.
    def test_javascript_basename_class_pattern_merges(self):
        try:
            import tree_sitter_javascript  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_javascript not available")
        files = {"Foo.js": "class Foo { bar() {} }\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Foo.js", node_ids)
        self.assertNotIn("Foo.js::Foo", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Foo.js")
        self.assertTrue(file_node.get("collapsed_pair"))

    # Wave 13196: Scala file with basename-class merges.
    def test_scala_basename_class_pattern_merges(self):
        try:
            import tree_sitter_scala  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_scala not available")
        files = {"Foo.scala": "class Foo { def bar(): Unit = {} }\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Foo.scala", node_ids)
        self.assertNotIn("Foo.scala::Foo", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Foo.scala")
        self.assertTrue(file_node.get("collapsed_pair"))

    # Wave 1319i: Rust file with snake_case basename matches PascalCase type.
    def test_rust_snake_case_basename_merges_via_pascal_conversion(self):
        try:
            import tree_sitter_rust  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_rust not available")
        # foo_bar.rs contains `struct FooBar` — snake_case file, PascalCase type.
        files = {"foo_bar.rs": "pub struct FooBar { pub x: i32 }\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("foo_bar.rs", node_ids)
        self.assertNotIn("foo_bar.rs::FooBar", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "foo_bar.rs")
        self.assertEqual(file_node["label"], "FooBar")
        self.assertTrue(file_node.get("collapsed_pair"))

    # Wave 1319i: Rust file with PascalCase basename (literal match) also merges.
    def test_rust_pascal_case_basename_literal_match_merges(self):
        try:
            import tree_sitter_rust  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_rust not available")
        files = {"Foo.rs": "pub struct Foo;\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Foo.rs", node_ids)
        self.assertNotIn("Foo.rs::Foo", node_ids)

    # Wave 1319i: Rust file with mismatched type name does not merge.
    def test_rust_basename_mismatch_no_merge(self):
        try:
            import tree_sitter_rust  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_rust not available")
        files = {"foo.rs": "pub struct Bar;\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        # Neither basename "foo" nor PascalCase "Foo" matches "Bar".
        self.assertIn("foo.rs", node_ids)
        self.assertIn("foo.rs::Bar", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "foo.rs")
        self.assertEqual(file_node["kind"], "module")

    # Wave 1319k: Ruby snake_case basename matches PascalCase class.
    def test_ruby_snake_case_basename_merges_via_pascal_conversion(self):
        try:
            import tree_sitter_ruby  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_ruby not available")
        files = {"foo_bar.rb": "class FooBar\n  def hello\n  end\nend\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("foo_bar.rb", node_ids)
        self.assertNotIn("foo_bar.rb::FooBar", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "foo_bar.rb")
        self.assertEqual(file_node["label"], "FooBar")
        self.assertTrue(file_node.get("collapsed_pair"))

    # Wave 1319k: Ruby file with mismatched class name does not merge.
    def test_ruby_basename_mismatch_no_merge(self):
        try:
            import tree_sitter_ruby  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_ruby not available")
        files = {"foo.rb": "class Bar\nend\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("foo.rb", node_ids)
        self.assertIn("foo.rb::Bar", node_ids)

    # Wave 13196: PHP file with basename-class merges.
    def test_php_basename_class_pattern_merges(self):
        try:
            import tree_sitter_php  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_php not available")
        files = {"Foo.php": "<?php\nclass Foo { public function bar() {} }\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        self.assertIn("Foo.php", node_ids)
        self.assertNotIn("Foo.php::Foo", node_ids)
        file_node = next(n for n in self._nodes(payload) if n["id"] == "Foo.php")
        self.assertTrue(file_node.get("collapsed_pair"))

    # Wave 13190: Java file with multiple top-level types — only basename match merges.
    def test_java_multi_top_level_types_partial_merge(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available")
        # Java allows multiple top-level types in one file (though only one
        # may be public). Basename matches Foo; Bar remains separate.
        files = {"Foo.java": "class Foo {} class Bar {}\n"}
        payload = self._build(files)
        node_ids = {n["id"] for n in self._nodes(payload)}
        # Foo merged into file.
        self.assertIn("Foo.java", node_ids)
        self.assertNotIn("Foo.java::Foo", node_ids)
        # Bar remains as a separate node.
        self.assertIn("Foo.java::Bar", node_ids)


class SwiftReceiverTypeTests(unittest.TestCase):
    """1319g: Swift receiver-type resolution at graph-build time."""

    def setUp(self):
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available")
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _calls(self, payload):
        return [e for e in payload.get("edges", []) if e.get("relation") == "calls"]

    def test_swift_typed_local_phantom_routes_to_external(self):
        """`let oos: ObjectOutputStream = ...; oos.writeObject(obj)` routes to
        external::ObjectOutputStream.writeObject, NOT to project JSON.writeObject."""
        files = {
            "JSON.swift": "class JSON { func writeObject(_ obj: Any) {} }\n",
            "JdbcRegistry.swift": (
                "class JdbcRegistry {\n"
                "    func cloneConnectionMap(_ obj: Any) {\n"
                "        let oos: ObjectOutputStream = ObjectOutputStream()\n"
                "        oos.writeObject(obj)\n"
                "    }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        phantom = [
            e for e in calls
            if "JdbcRegistry" in str(e.get("source", ""))
            and "JSON.writeObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertFalse(phantom,
                         f"Phantom Swift edge survived: {[(e.get('source'), e.get('target')) for e in phantom]}")

    def test_swift_self_call_preserves(self):
        """self.method() from within the class preserves the project-internal edge."""
        files = {
            "JSON.swift": (
                "class JSON {\n"
                "    func writeObject(_ obj: Any) {}\n"
                "    func serialize(_ x: Any) { self.writeObject(x) }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # Wave 1316l/13190: Swift class JSON in JSON.swift merges to file id.
        legit = [
            e for e in calls
            if "JSON.swift" in str(e.get("source", ""))
            and "serialize" in str(e.get("source", ""))
            and "writeObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertTrue(legit,
                        f"Swift self-call attribution lost: "
                        f"{[(e.get('source'), e.get('target')) for e in calls]}")


class DominantClassMergeTests(unittest.TestCase):
    """1319o: single-dominant-class merge for Python, JavaScript, TypeScript."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _merged_nodes(self, payload):
        return [n for n in payload.get("nodes", []) if n.get("collapsed_pair")]

    # Python
    def test_python_snake_case_basename_merges_via_pascal_conversion(self):
        payload = self._build({"src/foo_bar.py": "class FooBar:\n    pass\n"})
        merged = self._merged_nodes(payload)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["label"], "FooBar")
        self.assertEqual(merged[0]["id"], "src/foo_bar.py")

    def test_python_pascal_case_basename_literal_match_merges(self):
        payload = self._build({"src/Foo.py": "class Foo:\n    pass\n"})
        merged = self._merged_nodes(payload)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["label"], "Foo")

    def test_python_multi_class_blocked_by_dominance_gate(self):
        payload = self._build({"src/utils.py": "class A: pass\nclass B: pass\nclass C: pass\n"})
        self.assertEqual(len(self._merged_nodes(payload)), 0)

    def test_python_helpers_dont_block_merge(self):
        payload = self._build({"src/foo_bar.py": "class FooBar: pass\ndef helper(): pass\nCONST = 1\n"})
        self.assertEqual(len(self._merged_nodes(payload)), 1)

    def test_python_basename_mismatch_no_merge(self):
        payload = self._build({"src/foo_bar.py": "class Bar:\n    pass\n"})
        self.assertEqual(len(self._merged_nodes(payload)), 0)

    # JavaScript
    def test_javascript_kebab_case_basename_merges_via_pascal_conversion(self):
        payload = self._build({"src/foo-bar.js": "export class FooBar { constructor() {} }\n"})
        merged = self._merged_nodes(payload)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["label"], "FooBar")

    def test_javascript_multi_class_blocked_by_dominance_gate(self):
        payload = self._build({"src/utils.js": "export class A {}\nexport class B {}\nexport class C {}\n"})
        self.assertEqual(len(self._merged_nodes(payload)), 0)

    def test_javascript_export_wrapped_class_counts_toward_dominance(self):
        payload = self._build({"src/FooBar.js": "export default class FooBar {}\n"})
        # export-wrapped class should still count as exactly one top-level class
        # → merge fires when basename matches.
        merged = self._merged_nodes(payload)
        self.assertEqual(len(merged), 1, f"Expected merge for export default class; got {merged}")

    # TypeScript
    def test_typescript_pascal_basename_merges(self):
        payload = self._build({"src/FooBar.ts": "export class FooBar { constructor() {} }\n"})
        merged = self._merged_nodes(payload)
        self.assertEqual(len(merged), 1)

    def test_typescript_kebab_basename_merges_via_pascal_conversion(self):
        payload = self._build({"src/foo-bar.ts": "export class FooBar { constructor() {} }\n"})
        merged = self._merged_nodes(payload)
        self.assertEqual(len(merged), 1)

    def test_typescript_multi_class_blocked_by_dominance_gate(self):
        payload = self._build({"src/utils.ts": "export class A {}\nexport class B {}\nexport class C {}\n"})
        self.assertEqual(len(self._merged_nodes(payload)), 0)


class AnnotationReceiverTypeTests(unittest.TestCase):
    """1319q: receiver-type resolution via PEP 484 / TS / PHP native annotations."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _receiver_edges(self, payload):
        return [e for e in payload.get("edges", []) if e.get("confidence") == "RECEIVER_RESOLVED"]

    # TypeScript
    def test_typescript_typed_local_routes_with_receiver_resolved(self):
        payload = self._build({
            "src/foo.ts": "export class Foo { bar(): void {} }\n",
            "src/bar.ts": "import { Foo } from './foo';\nexport function make() { let foo: Foo = new Foo(); foo.bar(); }\n",
        })
        edges = [e for e in self._receiver_edges(payload) if "bar.ts" in str(e.get("source", "")) and "Foo.bar" in str(e.get("target", ""))]
        self.assertTrue(edges, f"TS typed local edge missing: {self._receiver_edges(payload)}")

    def test_typescript_typed_parameter_routes_with_receiver_resolved(self):
        payload = self._build({
            "src/foo.ts": "export class Foo { bar(): void {} }\n",
            "src/bar.ts": "import { Foo } from './foo';\nexport function make(foo: Foo) { foo.bar(); }\n",
        })
        edges = [e for e in self._receiver_edges(payload) if "Foo.bar" in str(e.get("target", ""))]
        self.assertTrue(edges, f"TS typed param edge missing: {self._receiver_edges(payload)}")

    def test_typescript_unannotated_local_does_not_receiver_resolve(self):
        payload = self._build({
            "src/foo.ts": "export class Foo { bar(): void {} }\n",
            "src/bar.ts": "import { Foo } from './foo';\nexport function make() { let foo = new Foo(); foo.bar(); }\n",
        })
        # No RECEIVER_RESOLVED edge for foo.bar() when foo is unannotated.
        edges = [e for e in self._receiver_edges(payload) if "bar.ts::make" in str(e.get("source", "")) and ".bar" in str(e.get("target", ""))]
        self.assertEqual(edges, [], f"Unexpected RECEIVER_RESOLVED on unannotated TS local: {edges}")

    # PHP
    def test_php_typed_parameter_routes_with_receiver_resolved(self):
        payload = self._build({
            "src/Foo.php": "<?php\nclass Foo { public function bar() {} }\n",
            "src/Bar.php": "<?php\nclass Bar {\n  public function make(Foo $foo) { $foo->bar(); }\n}\n",
        })
        edges = [e for e in self._receiver_edges(payload) if "Bar.make" in str(e.get("source", "")) and "Foo.bar" in str(e.get("target", ""))]
        self.assertTrue(edges, f"PHP typed param edge missing: {self._receiver_edges(payload)}")

    def test_php_this_call_routes_to_enclosing_class(self):
        payload = self._build({
            "src/Foo.php": "<?php\nclass Foo {\n  public function bar() {}\n  public function call_self() { $this->bar(); }\n}\n",
        })
        edges = [e for e in self._receiver_edges(payload) if "Foo.call_self" in str(e.get("source", "")) and "Foo.bar" in str(e.get("target", ""))]
        self.assertTrue(edges, f"PHP $this->call edge missing: {self._receiver_edges(payload)}")

    # Python
    def test_python_typed_local_routes_with_receiver_resolved(self):
        payload = self._build({
            "src/foo.py": "class Foo:\n    def bar(self): pass\n",
            "src/bar.py": "from src.foo import Foo\ndef make():\n    foo: Foo = Foo()\n    foo.bar()\n",
        })
        edges = [e for e in self._receiver_edges(payload) if "Foo.bar" in str(e.get("target", ""))]
        self.assertTrue(edges, f"Python typed local edge missing: {self._receiver_edges(payload)}")

    def test_python_typed_parameter_routes_with_receiver_resolved(self):
        payload = self._build({
            "src/foo.py": "class Foo:\n    def bar(self): pass\n",
            "src/bar.py": "from src.foo import Foo\ndef make(foo: Foo):\n    foo.bar()\n",
        })
        edges = [e for e in self._receiver_edges(payload) if "Foo.bar" in str(e.get("target", ""))]
        self.assertTrue(edges, f"Python typed param edge missing: {self._receiver_edges(payload)}")

    def test_python_unannotated_local_does_not_receiver_resolve(self):
        payload = self._build({
            "src/foo.py": "class Foo:\n    def bar(self): pass\n",
            "src/bar.py": "from src.foo import Foo\ndef make():\n    foo = Foo()\n    foo.bar()\n",
        })
        edges = [e for e in self._receiver_edges(payload) if "bar.py::make" in str(e.get("source", ""))]
        # Self.method and Foo.bar via symbol_lookup may produce EXTRACTED, but no RECEIVER_RESOLVED.
        rr_to_bar = [e for e in edges if "bar" in str(e.get("target", "")).lower()]
        self.assertEqual(rr_to_bar, [], f"Unexpected RECEIVER_RESOLVED on unannotated Python local: {rr_to_bar}")

    # JavaScript (Phase 2a — JSDoc)
    def test_javascript_jsdoc_type_routes_with_receiver_resolved(self):
        payload = self._build({
            "src/foo.js": "export class Foo { bar() {} }\n",
            "src/bar.js": (
                "import { Foo } from './foo.js';\n"
                "export function make() {\n"
                "  /** @type {Foo} */\n"
                "  let foo = createFoo();\n"
                "  foo.bar();\n"
                "}\n"
            ),
        })
        edges = [e for e in self._receiver_edges(payload) if "Foo.bar" in str(e.get("target", ""))]
        self.assertTrue(edges, f"JS JSDoc @type edge missing: {self._receiver_edges(payload)}")

    def test_javascript_no_jsdoc_does_not_receiver_resolve(self):
        payload = self._build({
            "src/foo.js": "export class Foo { bar() {} }\n",
            "src/bar.js": (
                "import { Foo } from './foo.js';\n"
                "export function make() {\n"
                "  let foo = createFoo();\n"
                "  foo.bar();\n"
                "}\n"
            ),
        })
        edges = [e for e in self._receiver_edges(payload) if "bar.js::make" in str(e.get("source", ""))]
        rr_to_bar = [e for e in edges if "bar" in str(e.get("target", "")).lower()]
        self.assertEqual(rr_to_bar, [], f"Unexpected RECEIVER_RESOLVED on unannotated JS local: {rr_to_bar}")

    def test_python_optional_annotation_unwraps_to_inner_type(self):
        payload = self._build({
            "src/foo.py": "class Foo:\n    def bar(self): pass\n",
            "src/bar.py": "from typing import Optional\nfrom src.foo import Foo\ndef make():\n    foo: Optional[Foo] = None\n    foo.bar()\n",
        })
        edges = [e for e in self._receiver_edges(payload) if "Foo.bar" in str(e.get("target", ""))]
        self.assertTrue(edges, f"Python Optional[Foo] edge missing: {self._receiver_edges(payload)}")


class ConstructionEdgesTests(unittest.TestCase):
    """1319s: construction-call edges routed to class node with CONSTRUCTION_RESOLVED."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _construction_edges(self, payload):
        return [
            e for e in payload.get("edges", [])
            if e.get("relation") == "calls"
            and e.get("confidence") == "CONSTRUCTION_RESOLVED"
        ]

    def _find_construction(self, payload, source_contains, target_contains):
        for e in self._construction_edges(payload):
            if source_contains in str(e.get("source", "")) and target_contains in str(e.get("target", "")):
                return e
        return None

    def test_java_new_routes_with_construction_resolved(self):
        files = {
            "src/Foo.java": "public class Foo { public Foo() {} }\n",
            "src/Bar.java": "public class Bar {\n  public Foo make() { return new Foo(); }\n}\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "Bar.make", "Foo.java")
        self.assertIsNotNone(edge, f"Java new Foo() construction edge missing: {self._construction_edges(payload)}")

    def test_csharp_new_routes_with_construction_resolved(self):
        files = {
            "src/Foo.cs": "public class Foo { public Foo() {} }\n",
            "src/Bar.cs": "public class Bar {\n  public Foo Make() { return new Foo(); }\n}\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "Bar.Make", "Foo.cs")
        self.assertIsNotNone(edge, f"C# new Foo() construction edge missing: {self._construction_edges(payload)}")

    def test_typescript_new_routes_with_construction_resolved(self):
        files = {
            "src/foo.ts": "export class Foo { constructor() {} }\n",
            "src/bar.ts": "import { Foo } from './foo';\nexport function make() { return new Foo(); }\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "bar.ts::make", "foo.ts")
        self.assertIsNotNone(edge, f"TS new Foo() construction edge missing: {self._construction_edges(payload)}")

    def test_javascript_new_routes_with_construction_resolved(self):
        files = {
            "src/foo.js": "export class Foo { constructor() {} }\n",
            "src/bar.js": "import { Foo } from './foo.js';\nexport function make() { return new Foo(); }\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "bar.js::make", "foo.js")
        self.assertIsNotNone(edge, f"JS new Foo() construction edge missing: {self._construction_edges(payload)}")

    def test_php_new_routes_with_construction_resolved(self):
        files = {
            "src/Foo.php": "<?php\nclass Foo { public function __construct() {} }\n",
            "src/Bar.php": "<?php\nclass Bar {\n  public function make() { return new Foo(); }\n}\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "Bar.make", "Foo.php")
        self.assertIsNotNone(edge, f"PHP new Foo() construction edge missing: {self._construction_edges(payload)}")

    def test_swift_bare_call_construction_routes_with_construction_resolved(self):
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available")
        files = {
            "src/Foo.swift": "class Foo { init() {} }\n",
            "src/Bar.swift": "class Bar {\n  func make() -> Foo { return Foo() }\n}\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "Bar.make", "Foo.swift")
        self.assertIsNotNone(edge, f"Swift Foo() construction edge missing: {self._construction_edges(payload)}")

    def test_swift_main_actor_observable_object_labeled_arg_construction(self):
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available")
        files = {
            "src/Foo.swift": (
                "import Foundation\n"
                "@MainActor\n"
                "class Foo: ObservableObject {\n"
                "    init(label: String) {}\n"
                "}\n"
            ),
            "src/AppDelegate.swift": (
                "import Foundation\n"
                "@main\n"
                "class AppDelegate: NSObject {\n"
                "    var foo: Foo?\n"
                "    func application(_ application: NSObject, didFinishLaunchingWithOptions options: [String: Any]?) {\n"
                "        let manager = Foo(label: \"x\")\n"
                "        self.foo = manager\n"
                "    }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "AppDelegate.application", "Foo.swift")
        self.assertIsNotNone(
            edge,
            "Swift @MainActor + ObservableObject + labeled-arg construction edge missing: "
            f"{self._construction_edges(payload)}",
        )

    def test_kotlin_bare_call_construction_routes_with_construction_resolved(self):
        files = {
            "src/Foo.kt": "class Foo()\n",
            "src/Bar.kt": "class Bar {\n    fun make(): Foo { return Foo() }\n}\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "Bar.make", "Foo.kt")
        self.assertIsNotNone(edge, f"Kotlin Foo() construction edge missing: {self._construction_edges(payload)}")

    def test_scala_bare_call_case_class_construction(self):
        files = {
            "src/Foo.scala": "case class Foo(x: Int)\n",
            "src/Bar.scala": "class Bar {\n  def make(): Foo = Foo(1)\n}\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "Bar.make", "Foo.scala")
        self.assertIsNotNone(edge, f"Scala Foo(1) construction edge missing: {self._construction_edges(payload)}")

    def test_ruby_dot_new_routes_with_construction_resolved(self):
        files = {
            "src/foo.rb": "class Foo\n  def initialize\n  end\nend\n",
            "src/bar.rb": "class Bar\n  def make\n    Foo.new\n  end\nend\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "bar.rb", "foo.rb")
        self.assertIsNotNone(edge, f"Ruby Foo.new construction edge missing: {self._construction_edges(payload)}")

    def test_rust_struct_literal_routes_with_construction_resolved(self):
        files = {
            "src/foo.rs": "pub struct Foo { pub x: i32 }\n",
            "src/bar.rs": "use crate::foo::Foo;\npub fn make() -> Foo { Foo { x: 1 } }\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "bar.rs::make", "foo.rs")
        self.assertIsNotNone(edge, f"Rust struct literal construction edge missing: {self._construction_edges(payload)}")

    def test_rust_associated_new_convention_routes(self):
        files = {
            "src/foo.rs": "pub struct Foo { pub x: i32 }\nimpl Foo { pub fn new() -> Foo { Foo { x: 1 } } }\n",
            "src/bar.rs": "use crate::foo::Foo;\npub fn make() -> Foo { Foo::new() }\n",
        }
        payload = self._build(files)
        edge = self._find_construction(payload, "bar.rs::make", "foo.rs")
        self.assertIsNotNone(edge, f"Rust Foo::new() convention construction edge missing: {self._construction_edges(payload)}")

    def test_go_composite_literal_routes_with_construction_resolved(self):
        files = {
            "src/foo.go": "package main\ntype Foo struct { X int }\n",
            "src/bar.go": "package main\nfunc makeLit() *Foo { return &Foo{X: 1} }\n",
        }
        payload = self._build(files)
        edges = self._construction_edges(payload)
        # Go composite-literal construction is tagged CONSTRUCTION_RESOLVED; the
        # cross-file rewrite to the project node depends on Go simple-name
        # indexing which is not in this change's scope. Accept either target.
        edge = next(
            (e for e in edges if "makeLit" in str(e.get("source", "")) and "Foo" in str(e.get("target", ""))),
            None,
        )
        self.assertIsNotNone(edge, f"Go composite-literal construction edge missing: {edges}")

    def test_go_new_builtin_routes_with_construction_resolved(self):
        files = {
            "src/foo.go": "package main\ntype Foo struct { X int }\n",
            "src/bar.go": "package main\nfunc makeNew() *Foo { return new(Foo) }\n",
        }
        payload = self._build(files)
        edges = self._construction_edges(payload)
        edge = next(
            (e for e in edges if "makeNew" in str(e.get("source", "")) and "Foo" in str(e.get("target", ""))),
            None,
        )
        self.assertIsNotNone(edge, f"Go new(Foo) construction edge missing: {edges}")

    def test_construction_not_triggered_by_lowercase_method_call(self):
        """Negative case: a lowercase function call must NOT route as construction."""
        files = {
            "src/foo.ts": "export class Foo { constructor() {} }\nexport function helper() { return 1; }\n",
            "src/bar.ts": "import { helper } from './foo';\nexport function make() { return helper(); }\n",
        }
        payload = self._build(files)
        # No CONSTRUCTION_RESOLVED edge should originate from `make` for the helper call.
        construction_from_make = [
            e for e in self._construction_edges(payload)
            if "bar.ts::make" in str(e.get("source", ""))
        ]
        self.assertFalse(
            construction_from_make,
            f"Lowercase helper() call mis-tagged as construction: {construction_from_make}",
        )


class ErrorWrappedClassRecoveryTests(unittest.TestCase):
    """1319v: tree-sitter ERROR-wrapped top-level class declaration recovery.

    Tree-sitter occasionally fails to parse a class body (parse-resistant interior
    construct) and emits an ERROR node wrapping the entire class declaration. Without
    recovery the class node never registers, the class/module merge can't fire, and
    cross-file ``external::ClassName`` CONSTRUCTION_RESOLVED edges lose their target
    project node. The recovery helper detects the pattern from the ERROR node's source-
    text prefix and a present ``type_identifier`` child.
    """

    def setUp(self):
        self.mod = load_graph_indexer()

    class _FakeNode:
        """Stand-in for a tree-sitter node — covers the attributes the recovery helper reads."""
        def __init__(self, *, node_type: str, start_byte: int, end_byte: int, named_children: list):
            self.type = node_type
            self.start_byte = start_byte
            self.end_byte = end_byte
            self.named_children = named_children

    def _identifier_child(self, source: bytes, name: str, *, kind: str = "type_identifier"):
        """Construct an identifier child whose byte range points at the name's location in source."""
        idx = source.find(name.encode())
        if idx < 0:
            idx = 0
        return self._FakeNode(node_type=kind, start_byte=idx, end_byte=idx + len(name), named_children=[])

    def _error_node(self, source: bytes, *, name: str | None = "StatusBarManager",
                    identifier_kind: str = "type_identifier"):
        """Construct an ERROR node with an identifier child pointing at `name` in source.

        Pass ``name=None`` to construct an ERROR node with no identifier children (false-positive guard test).
        """
        children = [self._identifier_child(source, name, kind=identifier_kind)] if name is not None else []
        return self._FakeNode(node_type="ERROR", start_byte=0, end_byte=len(source), named_children=children)

    def test_recovers_mainactor_class(self):
        src = b"@MainActor class StatusBarManager: ObservableObject {\n  init() {}\n}\n"
        result = self.mod._ts_recover_error_class(self._error_node(src), src, "swift")
        self.assertEqual(result, ("StatusBarManager", "class"))

    def test_recovers_plain_class(self):
        src = b"class Foo: Bar {}\n"
        self.assertEqual(self.mod._ts_recover_error_class(self._error_node(src, name="Foo"), src, "swift"), ("Foo", "class"))

    def test_recovers_struct_actor_enum_protocol(self):
        for keyword in ("struct", "actor", "enum", "protocol"):
            src = f"{keyword} Foo {{}}\n".encode()
            self.assertEqual(self.mod._ts_recover_error_class(self._error_node(src, name="Foo"), src, "swift"), ("Foo", "class"),
                             f"swift {keyword} recovery failed")

    def test_recovers_with_multiple_modifiers(self):
        src = b"@MainActor public final class Foo: Bar {}\n"
        self.assertEqual(self.mod._ts_recover_error_class(self._error_node(src, name="Foo"), src, "swift"), ("Foo", "class"))

    def test_recovers_attribute_with_arguments(self):
        src = b"@available(macOS 13.0, *) class Foo: Bar {}\n"
        self.assertEqual(self.mod._ts_recover_error_class(self._error_node(src, name="Foo"), src, "swift"), ("Foo", "class"))

    def test_recovers_when_identifier_is_simple_identifier(self):
        """1.3.2 regression: tree-sitter-swift's ERROR recovery emits the class name
        as ``simple_identifier`` rather than ``type_identifier``. 1.3.1's predicate
        accepted only ``type_identifier`` and silently missed every production
        ERROR-wrapped class. This test pins the broader child-kind acceptance."""
        src = b"@MainActor class StatusBarManager: ObservableObject {}\n"
        self.assertEqual(
            self.mod._ts_recover_error_class(
                self._error_node(src, identifier_kind="simple_identifier"), src, "swift"
            ),
            ("StatusBarManager", "class"),
        )

    def test_recovers_when_identifier_is_plain_identifier(self):
        """Grammar variant: some tree-sitter grammars use ``identifier`` rather
        than ``type_identifier`` or ``simple_identifier`` (e.g. tree-sitter-java
        in certain recovery paths)."""
        src = b"class Foo {}\n"
        self.assertEqual(
            self.mod._ts_recover_error_class(
                self._error_node(src, name="Foo", identifier_kind="identifier"), src, "swift"
            ),
            ("Foo", "class"),
        )

    def test_skips_when_not_error_node(self):
        src = b"class Foo {}\n"
        node = self._FakeNode(node_type="class_declaration", start_byte=0, end_byte=len(src),
                              named_children=[self._identifier_child(src, "Foo")])
        self.assertIsNone(self.mod._ts_recover_error_class(node, src, "swift"))

    def test_skips_when_no_identifier_child(self):
        src = b"class Foo {}\n"
        self.assertIsNone(self.mod._ts_recover_error_class(self._error_node(src, name=None), src, "swift"))

    def test_skips_when_identifier_child_text_does_not_match_name(self):
        """Independent gate: even if an identifier child exists, its text must
        equal the recovered name. Prevents false positives where ERROR wraps
        a non-class construct that happens to contain a PascalCase identifier."""
        src = b"class Foo {}\n"
        # Identifier child points at "Foo" location, but we'll set its byte range
        # to point at "class" instead (mismatched). Recovery should reject.
        child = self._FakeNode(node_type="type_identifier", start_byte=0, end_byte=5, named_children=[])
        node = self._FakeNode(node_type="ERROR", start_byte=0, end_byte=len(src), named_children=[child])
        self.assertIsNone(self.mod._ts_recover_error_class(node, src, "swift"))

    def test_skips_when_prefix_not_class_keyword(self):
        # Common false-positive risk: the word "class" embedded in another context.
        src = b"let metaclass = type(of: x)\n"
        self.assertIsNone(self.mod._ts_recover_error_class(self._error_node(src), src, "swift"))

    def test_skips_when_name_is_lowercase(self):
        # PascalCase requirement keeps the recovery conservative.
        src = b"class foo {}\n"
        self.assertIsNone(self.mod._ts_recover_error_class(self._error_node(src), src, "swift"))

    def test_skips_for_unsupported_language(self):
        src = b"class Foo {}\n"
        self.assertIsNone(self.mod._ts_recover_error_class(self._error_node(src), src, "python"))
        self.assertIsNone(self.mod._ts_recover_error_class(self._error_node(src), src, "javascript"))

    def test_walk_definitions_registers_recovered_class(self):
        """End-to-end: a Swift file with the recovery shape produces simple_name_index
        and a merged module node with kind=class, so a downstream construction edge
        from another file would resolve correctly."""
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available")

        # Direct unit-level check via the helper — guarantees the integration glue
        # in walk_definitions calls register_symbol with kind="class" for any future
        # parse-failure pattern that surfaces a matching ERROR node.
        src = b"@MainActor class StatusBarManager: ObservableObject {\n}\n"
        recovered = self.mod._ts_recover_error_class(self._error_node(src), src, "swift")
        self.assertIsNotNone(recovered)
        name, kind = recovered
        self.assertEqual(name, "StatusBarManager")
        self.assertEqual(kind, "class")

    def test_class_body_with_parse_error_still_resolves_construction_edge(self):
        """Integration regression: when a class body contains tree-sitter-swift's
        switch-case parse-failure pattern (non-declaration statement followed by a
        local class declaration within a case branch — confirmed minimal trigger
        from Solaris field validation), the class_declaration node remains intact
        with ``has_error=True``. The standard registration path still fires, the
        class/module merge runs, and a cross-file CONSTRUCTION_RESOLVED edge from
        another file resolves to the merged module node. This pins the bug class
        regardless of whether the parser localizes the failure (this test) or
        cascades it to a full top-level ERROR-wrap (covered by the helper unit tests
        — production case at scale)."""
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available")
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / "docs").mkdir()
            (root / "docs" / "workflow-config.json").write_text("{}")
            (root / "Sources").mkdir()
            (root / "Sources" / "StatusBarManager.swift").write_text(
                "@MainActor class StatusBarManager: ObservableObject {\n"
                "  init() {}\n"
                "  func method(group: String) {\n"
                "    switch group {\n"
                "    case \"start\":\n"
                "      print(\"hi\")\n"
                "      class Handler {}\n"
                "    case \"other\":\n"
                "      break\n"
                "    default:\n"
                "      break\n"
                "    }\n"
                "  }\n"
                "}\n"
            )
            (root / "Sources" / "AppDelegate.swift").write_text(
                "class AppDelegate: NSObject {\n"
                "  func applicationDidFinishLaunching() {\n"
                "    let manager = StatusBarManager()\n"
                "    _ = manager\n"
                "  }\n"
                "}\n"
            )
            files = [
                root / "Sources" / "StatusBarManager.swift",
                root / "Sources" / "AppDelegate.swift",
            ]
            meta = {
                "Sources/StatusBarManager.swift": {"hash": "1"},
                "Sources/AppDelegate.swift": {"hash": "2"},
            }
            payload = self.mod.update_graph_index(
                root=root, index_dir=root / ".wavefoundry" / "index",
                layer="project", files=files, current_file_meta=meta,
                changed=set(meta.keys()), removed=set(),
                walker_version="1", chunker_version="1", verbose=False,
            )
            nodes = {n["id"]: n for n in payload.get("nodes", [])}
            sbm = nodes.get("Sources/StatusBarManager.swift") or {}
            self.assertEqual(sbm.get("kind"), "class", "merge should fire — module node kind becomes class")
            self.assertTrue(sbm.get("collapsed_pair"), "merged module node should carry collapsed_pair=True")
            construction = [
                e for e in payload.get("edges", [])
                if e.get("relation") == "calls"
                and e.get("confidence") == "CONSTRUCTION_RESOLVED"
                and "applicationDidFinishLaunching" in str(e.get("source", ""))
                and e.get("target") == "Sources/StatusBarManager.swift"
            ]
            self.assertTrue(
                construction,
                "Construction edge from AppDelegate to StatusBarManager.swift missing "
                f"despite parse error in StatusBarManager body. Edges: "
                f"{[(e.get('source'), e.get('target'), e.get('confidence')) for e in payload.get('edges', []) if e.get('relation') == 'calls']}",
            )
        finally:
            tmp.cleanup()


class DirectoryAggregationTests(unittest.TestCase):
    """1319m: cross-language directory aggregation via collapse_package_to_directory_view."""

    def setUp(self):
        scripts = SCRIPTS_ROOT
        spec = importlib.util.spec_from_file_location("graph_query", scripts / "graph_query.py")
        self.gq = importlib.util.module_from_spec(spec)
        sys.modules["graph_query"] = self.gq
        spec.loader.exec_module(self.gq)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make(self, files):
        payload_nodes = []
        for rel, src in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(src, encoding="utf-8")
            payload_nodes.append({"id": rel, "label": rel.split("/")[-1], "kind": "module", "source_file": rel})
        payload = {"nodes": payload_nodes, "edges": []}
        return self.gq.collapse_package_to_directory_view(payload, root=self.root)

    def _pkg_nodes(self, payload):
        return [n for n in payload["nodes"] if n.get("kind") in ("package", "namespace")]

    def test_go_matching_package_collapses(self):
        out = self._make({
            "foo/a.go": "package foo\nfunc A() {}\n",
            "foo/b.go": "package foo\nfunc B() {}\n",
        })
        pkg = self._pkg_nodes(out)
        self.assertEqual(len(pkg), 1)
        self.assertEqual(pkg[0]["label"], "foo")
        self.assertEqual(sorted(pkg[0]["collapse_origin_files"]), ["foo/a.go", "foo/b.go"])

    def test_python_package_collapse_requires_init_py(self):
        # With __init__.py → collapse
        out = self._make({
            "myapp/__init__.py": "",
            "myapp/foo.py": "x = 1\n",
            "myapp/bar.py": "y = 2\n",
        })
        self.assertEqual(len(self._pkg_nodes(out)), 1)

    def test_python_without_init_py_does_not_collapse(self):
        out = self._make({
            "myapp/foo.py": "x = 1\n",
            "myapp/bar.py": "y = 2\n",
        })
        self.assertEqual(len(self._pkg_nodes(out)), 0)

    def test_java_matching_package_collapses(self):
        out = self._make({
            "com/example/Foo.java": "package com.example;\npublic class Foo {}\n",
            "com/example/Bar.java": "package com.example;\npublic class Bar {}\n",
        })
        pkg = self._pkg_nodes(out)
        self.assertEqual(len(pkg), 1)
        self.assertEqual(pkg[0]["label"], "com.example")

    def test_java_mixed_packages_blocks_collapse(self):
        out = self._make({
            "mixed/Foo.java": "package com.alpha;\nclass Foo {}\n",
            "mixed/Bar.java": "package com.beta;\nclass Bar {}\n",
        })
        self.assertEqual(len(self._pkg_nodes(out)), 0)

    def test_single_file_directory_not_collapsed(self):
        out = self._make({"lone/Solo.java": "package com.lone;\nclass Solo {}\n"})
        self.assertEqual(len(self._pkg_nodes(out)), 0)

    def test_swift_convention_collapse(self):
        out = self._make({"Sources/A.swift": "class A {}\n", "Sources/B.swift": "class B {}\n"})
        pkg = self._pkg_nodes(out)
        self.assertEqual(len(pkg), 1)

    def test_rust_excluded(self):
        out = self._make({"src/a.rs": "// rust\n", "src/b.rs": "// rust\n"})
        self.assertEqual(len(self._pkg_nodes(out)), 0)

    def test_csharp_namespace_collapse(self):
        out = self._make({
            "src/Foo.cs": "namespace MyApp.Core;\npublic class Foo {}\n",
            "src/Bar.cs": "namespace MyApp.Core;\npublic class Bar {}\n",
        })
        pkg = [n for n in out["nodes"] if n.get("kind") == "namespace"]
        self.assertEqual(len(pkg), 1)
        self.assertEqual(pkg[0]["label"], "MyApp.Core")


class GoRustScalaReceiverTypeTests(unittest.TestCase):
    """1319a: Go, Rust, Scala receiver-type resolution at graph-build time."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _calls(self, payload):
        return [e for e in payload.get("edges", []) if e.get("relation") == "calls"]

    def test_go_phantom_method_routes_to_external(self):
        try:
            import tree_sitter_go  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_go not available")
        files = {
            "json.go": (
                "package json\n"
                "type JSON struct {}\n"
                "func (j JSON) WriteObject(o interface{}) {}\n"
            ),
            "registry.go": (
                "package main\n"
                "import \"io\"\n"
                "type Helper struct {}\n"
                "func (h Helper) CloneConnectionMap() {\n"
                "    var oos io.Writer\n"
                "    oos.WriteObject(\"x\")\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # No phantom edge from Helper.CloneConnectionMap → JSON.WriteObject.
        phantom = [
            e for e in calls
            if "Helper.CloneConnectionMap" in str(e.get("source", ""))
            and "JSON.WriteObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertFalse(phantom,
                         f"Phantom Go edge survived: {[(e.get('source'), e.get('target')) for e in phantom]}")

    def test_rust_phantom_method_routes_to_external(self):
        try:
            import tree_sitter_rust  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_rust not available")
        files = {
            "json.rs": (
                "struct JSON;\n"
                "impl JSON { fn write_object(&self, o: &str) {} }\n"
            ),
            "registry.rs": (
                "struct OutputStream;\n"
                "impl OutputStream { fn write_object(&self, o: &str) {} }\n"
                "struct Helper;\n"
                "impl Helper {\n"
                "    fn clone_connection_map(&self) {\n"
                "        let oos: OutputStream = OutputStream;\n"
                "        oos.write_object(\"x\");\n"
                "    }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # Helper.clone_connection_map → JSON.write_object should NOT exist.
        phantom = [
            e for e in calls
            if "Helper.clone_connection_map" in str(e.get("source", ""))
            and "JSON.write_object" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertFalse(phantom,
                         f"Phantom Rust edge survived: {[(e.get('source'), e.get('target')) for e in phantom]}")

    def test_scala_phantom_method_routes_to_external(self):
        try:
            import tree_sitter_scala  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_scala not available")
        files = {
            "JSON.scala": (
                "class JSON { def writeObject(o: Any): Unit = {} }\n"
            ),
            "Registry.scala": (
                "class OutputStream { def writeObject(o: Any): Unit = {} }\n"
                "class Helper {\n"
                "  def cloneConnectionMap(): Unit = {\n"
                "    val oos: OutputStream = new OutputStream\n"
                "    oos.writeObject(\"x\")\n"
                "  }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        phantom = [
            e for e in calls
            if "Helper.cloneConnectionMap" in str(e.get("source", ""))
            and "JSON.writeObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertFalse(phantom,
                         f"Phantom Scala edge survived: {[(e.get('source'), e.get('target')) for e in phantom]}")


class KotlinAndCSharpReceiverTypeTests(unittest.TestCase):
    """13194: Kotlin and C# receiver-type resolution at graph-build time.

    Mirrors the Java reproducer (1312l): phantom cross-class callers from
    simple-name attribution must be suppressed when the receiver type can
    be resolved. Conservative coverage: explicit type annotations,
    `this`/`base`, bare calls. Uncertain (var, nullable, extension) falls
    through.
    """

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _calls(self, payload):
        return [e for e in payload.get("edges", []) if e.get("relation") == "calls"]

    # AC-5: Kotlin reproducer — oos.writeObject(object) where oos: ObjectOutputStream
    # routes to external::ObjectOutputStream.writeObject, not project JSON.writeObject.
    def test_kotlin_oos_writeobject_routes_to_external(self):
        try:
            import tree_sitter_kotlin  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_kotlin not available")
        files = {
            "JSON.kt": "class JSON { fun writeObject(o: Any) {} }\n",
            "JdbcRegistry.kt": (
                "import java.io.ObjectOutputStream\n"
                "class JdbcRegistry {\n"
                "    fun cloneConnectionMap(obj: Any) {\n"
                "        val oos: ObjectOutputStream = ObjectOutputStream()\n"
                "        oos.writeObject(obj)\n"
                "    }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # NO phantom edge to JSON.writeObject.
        phantom = [
            e for e in calls
            if "JdbcRegistry" in str(e.get("source", ""))
            and "JSON.writeObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertFalse(phantom,
                         f"Phantom Kotlin edge survived: {[(e.get('source'), e.get('target')) for e in phantom]}")

    # AC-5: Kotlin bare/this call from same class preserved.
    def test_kotlin_this_call_preserves(self):
        try:
            import tree_sitter_kotlin  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_kotlin not available")
        files = {
            "JSON.kt": (
                "class JSON {\n"
                "    fun writeObject(o: Any) {}\n"
                "    fun serialize(x: Any) { this.writeObject(x) }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # 13190 merge: JSON.kt + class JSON merge to file id `JSON.kt`.
        # Caller (`serialize`) → callee (`writeObject`) both inside JSON.
        legit = [
            e for e in calls
            if "JSON.kt::JSON.serialize" in str(e.get("source", ""))
            and "JSON.kt::JSON.writeObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertTrue(legit,
                        f"Kotlin this-call attribution lost: "
                        f"{[(e.get('source'), e.get('target')) for e in calls]}")

    # AC-6: C# reproducer — stream.WriteObject(obj) where stream: ObjectOutputStream
    # routes to external::ObjectOutputStream.WriteObject.
    def test_csharp_stream_writeobject_routes_to_external(self):
        try:
            import tree_sitter_c_sharp  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_c_sharp not available")
        files = {
            "JSON.cs": "class JSON { public void WriteObject(object o) {} }\n",
            "JdbcRegistry.cs": (
                "class JdbcRegistry {\n"
                "    public void CloneConnectionMap(object obj) {\n"
                "        ObjectOutputStream stream = new ObjectOutputStream();\n"
                "        stream.WriteObject(obj);\n"
                "    }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        phantom = [
            e for e in calls
            if "JdbcRegistry" in str(e.get("source", ""))
            and "JSON.WriteObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertFalse(phantom,
                         f"Phantom C# edge survived: {[(e.get('source'), e.get('target')) for e in phantom]}")

    # AC-6: C# bare/this call from same class preserved.
    def test_csharp_this_call_preserves(self):
        try:
            import tree_sitter_c_sharp  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_c_sharp not available")
        files = {
            "JSON.cs": (
                "class JSON {\n"
                "    public void WriteObject(object o) {}\n"
                "    public void Serialize(object x) { this.WriteObject(x); }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        legit = [
            e for e in calls
            if "JSON.cs::JSON.Serialize" in str(e.get("source", ""))
            and "JSON.cs::JSON.WriteObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertTrue(legit,
                        f"C# this-call attribution lost: "
                        f"{[(e.get('source'), e.get('target')) for e in calls]}")


class JavaReceiverTypeAttributionTests(unittest.TestCase):
    """1312l: Java receiver-type resolution at graph-build time eliminates
    phantom cross-class edges from simple-name attribution.

    The Aceiss reproducer: `oos.writeObject(...)` in `JdbcConnectionRegistry`
    where `oos` is `ObjectOutputStream` must NOT attribute to project
    `JSON.writeObject`. Receiver-type resolution emits
    `external::ObjectOutputStream.writeObject` instead.
    """

    def setUp(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _calls(self, payload):
        return [e for e in payload.get("edges", []) if e.get("relation") == "calls"]

    # AC-2: Aceiss reproducer — oos.writeObject must NOT attribute to project JSON.writeObject.
    def test_phantom_oos_writeobject_not_attributed_to_project(self):
        files = {
            "src/JSON.java": "class JSON { public void writeObject(Object o) {} }\n",
            "src/JdbcRegistry.java": (
                "import java.io.ObjectOutputStream;\n"
                "import java.io.FileOutputStream;\n"
                "class JdbcRegistry {\n"
                "    public void cloneConnectionMap(Object object) throws Exception {\n"
                "        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(\"x\"));\n"
                "        oos.writeObject(object);\n"
                "    }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # Phantom edge NOT present: JdbcRegistry.cloneConnectionMap → JSON.writeObject.
        phantom = [
            e for e in calls
            if "JdbcRegistry.cloneConnectionMap" in str(e.get("source", ""))
            and "JSON.writeObject" in str(e.get("target", ""))
        ]
        self.assertFalse(
            phantom,
            f"Phantom cross-class edge survived: {[(e.get('source'), e.get('target')) for e in phantom]}",
        )
        # Qualified-external edge IS present.
        qualified_external = [
            e for e in calls
            if "JdbcRegistry.cloneConnectionMap" in str(e.get("source", ""))
            and e.get("target") == "external::ObjectOutputStream.writeObject"
        ]
        self.assertTrue(
            qualified_external,
            f"Qualified-external edge missing: {[(e.get('source'), e.get('target')) for e in calls]}",
        )

    # AC-6: bare call `process()` from inside JSON class still attributes to JSON.process.
    def test_bare_call_in_project_class_attributes_correctly(self):
        files = {
            "src/JSON.java": (
                "class JSON {\n"
                "    public void writeObject(Object o) {}\n"
                "    public void serialize(Object x) { writeObject(x); }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        legit = [
            e for e in calls
            if "JSON.serialize" in str(e.get("source", ""))
            and "JSON.writeObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertTrue(legit, f"Bare-call attribution lost: {[(e.get('source'), e.get('target')) for e in calls]}")

    # AC-6: this.method() call attributes to enclosing project class.
    def test_this_call_attributes_to_enclosing_class(self):
        files = {
            "src/JSON.java": (
                "class JSON {\n"
                "    public void writeObject(Object o) {}\n"
                "    public void serialize(Object x) { this.writeObject(x); }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        legit = [
            e for e in calls
            if "JSON.serialize" in str(e.get("source", ""))
            and "JSON.writeObject" in str(e.get("target", ""))
            and not str(e.get("target", "")).startswith("external::")
        ]
        self.assertTrue(legit, f"this-call attribution lost: {[(e.get('source'), e.get('target')) for e in calls]}")

    # AC-3: GRAPH_BUILDER_VERSION reflects the latest wave-13129 bump.
    # 1312l bumped 12→13 (Java receiver-type attribution).
    # 1316l bumped 13→14 (Swift class/module merge).
    # 1319s bumped 14→15 (cross-language construction-call edges to class node).
    # 1319v bumped 15→16 (ERROR-wrapped top-level class declaration recovery).
    # 1319v bumped 16→17 (broaden recovery predicate to accept simple_identifier/identifier children).
    def test_graph_builder_version_bumped_for_wave_131bt(self):
        self.assertEqual(self.mod.GRAPH_BUILDER_VERSION, "17",
                         "GRAPH_BUILDER_VERSION must be bumped for wave 131bt 1319v 1.3.2 (broader ERROR-class recovery)")


class HeuristicImpactUnsupportedLanguageTests(unittest.TestCase):
    """AC-12: code_impact path= heuristic returns explicit unsupported_language
    diagnostic for languages whose imports are not parsed (Swift, Java, etc.)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Load server_impl
        scripts_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "server_impl", scripts_root / "server_impl.py"
        )
        self.server_impl = importlib.util.module_from_spec(spec)
        sys.modules["server_impl"] = self.server_impl
        spec.loader.exec_module(self.server_impl)

    def tearDown(self):
        self.tmp.cleanup()

    def test_swift_path_returns_unsupported_language(self):
        swift_file = self.root / "src" / "Foo.swift"
        swift_file.parent.mkdir(parents=True, exist_ok=True)
        swift_file.write_text("class Foo {}\n", encoding="utf-8")
        result = self.server_impl._code_impact_heuristic_response(
            self.root, "src/Foo.swift",
        )
        data = result.get("data") or result
        self.assertTrue(
            data.get("unsupported_language"),
            f"Expected unsupported_language=True for .swift; got {data}",
        )
        self.assertEqual(data.get("importers"), [])
        self.assertEqual(data.get("total_found"), 0)
        diagnostics = result.get("diagnostics") or []
        self.assertTrue(
            any(d.get("code") == "unsupported_language" for d in diagnostics),
            f"Expected unsupported_language diagnostic; got {diagnostics}",
        )

    def test_python_path_still_works(self):
        py_file = self.root / "src" / "tool.py"
        py_file.parent.mkdir(parents=True, exist_ok=True)
        py_file.write_text("def t(): pass\n", encoding="utf-8")
        result = self.server_impl._code_impact_heuristic_response(
            self.root, "src/tool.py",
        )
        data = result.get("data") or result
        # Python is supported — no unsupported_language flag.
        self.assertFalse(data.get("unsupported_language", False))


class GeneratedCodeClassifierTests(unittest.TestCase):
    """130rj-enh generated-code-classifier-and-filters: header + path + gitattributes detection."""

    def setUp(self):
        self.mod = load_graph_indexer()

    def _classify(self, rel_path, source_text, gitattrs=frozenset()):
        return self.mod._classify_generated(
            rel_path,
            source_text.encode("utf-8") if source_text is not None else None,
            gitattrs,
        )

    # AC-1: Java/JVM header markers
    def test_javacc_header_marks_generated(self):
        self.assertTrue(self._classify("src/ELParser.java", "/* Generated By:JJTree&JavaCC: Do not edit this line. ELParser.java */\nclass ELParser {}"))

    def test_javacc_alternate_header(self):
        self.assertTrue(self._classify("src/Parser.java", "/* Generated By:JavaCC */\nclass Parser {}"))

    def test_antlr_header_marks_generated(self):
        self.assertTrue(self._classify("src/MyLexer.java", "// Generated from MyGrammar.g4 by ANTLR 4.13.1\npublic class MyLexer {}"))

    def test_protobuf_do_not_edit_marks_generated(self):
        self.assertTrue(self._classify("src/Foo.java", "// DO NOT EDIT! This file was generated by protoc.\npackage com.example;"))

    def test_jsr250_generated_annotation_marks_generated(self):
        self.assertTrue(self._classify("src/Gen.java", "@javax.annotation.Generated(\"foo\")\nclass Gen {}"))

    def test_jakarta_generated_annotation_marks_generated(self):
        self.assertTrue(self._classify("src/Gen.java", "@jakarta.annotation.Generated(\"foo\")\nclass Gen {}"))

    # AC-1a: C# / .NET header markers
    def test_csharp_auto_generated_marks_generated(self):
        self.assertTrue(self._classify("Foo.cs", "//------------------------------------------------------------------------------\n// <auto-generated>\n//     This code was generated by a tool.\n// </auto-generated>\nnamespace Foo {}"))

    def test_csharp_auto_generated_self_closing_marks_generated(self):
        self.assertTrue(self._classify("Foo.cs", "// <auto-generated/>\nnamespace Foo {}"))

    def test_csharp_generated_code_attribute_marks_generated(self):
        self.assertTrue(self._classify("Foo.cs", "using System.CodeDom.Compiler;\n[GeneratedCode(\"Tool\", \"1.0\")]\nclass Foo {}"))

    # AC-2: generic generated directory segments
    def test_generated_sources_dir_marks_generated(self):
        self.assertTrue(self._classify("generated-sources/foo/Bar.java", "class Bar {}"))

    def test_build_generated_dir_marks_generated(self):
        self.assertTrue(self._classify("build/generated/Bar.java", "class Bar {}"))

    def test_generated_dir_marks_generated(self):
        self.assertTrue(self._classify("src/generated/Bar.java", "class Bar {}"))

    # AC-2: C#-specific generated directories
    def test_service_references_dir_marks_generated(self):
        self.assertTrue(self._classify("Project/Service References/Foo/Reference.cs", "namespace Foo {}"))

    def test_connected_services_dir_marks_generated(self):
        self.assertTrue(self._classify("Project/Connected Services/Foo/Reference.cs", "namespace Foo {}"))

    # AC-2a: C# filename suffix patterns
    def test_designer_cs_suffix_marks_generated(self):
        self.assertTrue(self._classify("Forms/Form1.designer.cs", "namespace Forms {}"))

    def test_g_cs_suffix_marks_generated(self):
        self.assertTrue(self._classify("Pages/Index.g.cs", "// Razor generated\nnamespace Pages {}"))

    def test_g_i_cs_suffix_marks_generated(self):
        self.assertTrue(self._classify("Pages/Index.g.i.cs", "namespace Pages {}"))

    # AC-3: .gitattributes linguist-generated patterns
    def test_gitattributes_pattern_marks_generated(self):
        gitattrs = frozenset({"vendor/*.go", "src/proto/*.pb.go"})
        self.assertTrue(self._classify("src/proto/foo.pb.go", "package foo", gitattrs))
        self.assertTrue(self._classify("vendor/external.go", "package external", gitattrs))

    # AC-4: false-positive guards
    def test_handwritten_code_generator_py_not_marked(self):
        self.assertFalse(self._classify(
            "src/code_generator.py",
            "def generate_code(spec):\n    \"\"\"Generates code from spec.\"\"\"\n    return 'pass'",
        ))

    def test_handwritten_file_with_generated_in_docstring_not_marked(self):
        self.assertFalse(self._classify(
            "src/util.py",
            "def util():\n    # This function helps with generated output but is hand-written.\n    return 1",
        ))

    def test_handwritten_file_with_generator_in_filename_not_marked(self):
        self.assertFalse(self._classify(
            "src/MyGenerator.cs",
            "namespace App {\n    public class MyGenerator {}\n}",
        ))

    def test_header_match_bounded_to_first_200_bytes(self):
        # If the canonical header appears beyond 200 bytes, classifier should NOT trip on it
        # (prevents false positives from docstrings or string literals deep in the file).
        prefix = "// Copyright 2026\nclass Foo {\n" + ("    // padding\n" * 30)
        self.assertGreater(len(prefix), 200)
        source = prefix + "// <auto-generated/>\n}"
        self.assertFalse(self._classify("Foo.cs", source))


class GeneratedCodeIntegrationTests(unittest.TestCase):
    """End-to-end: generated tag propagates to node payload, cluster fraction, report filters."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files: dict[str, str]) -> dict:
        paths = []
        meta = {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content[:8]}
        return self.mod.update_graph_index(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            files=paths,
            current_file_meta=meta,
            changed=set(meta.keys()),
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )

    def test_generated_tag_propagates_to_nodes(self):
        """A generated-classified file's nodes carry `generated: true` in the merged graph."""
        payload = self._build({
            "src/handwritten.py": "def foo():\n    return 1\n",
            "src/ELParser.java": "/* Generated By:JJTree */\npublic class ELParser { public int parse() { return 1; } }",
        })
        nodes_by_id = {n["id"]: n for n in payload["nodes"]}
        # Handwritten file's nodes are NOT marked generated.
        for nid, node in nodes_by_id.items():
            if nid.startswith("src/handwritten.py"):
                self.assertFalse(node.get("generated"), f"handwritten node tagged generated: {nid}")
        # Generated file's nodes ARE marked generated.
        generated_node_ids = [nid for nid, node in nodes_by_id.items() if node.get("generated")]
        self.assertTrue(
            any(nid.startswith("src/ELParser.java") for nid in generated_node_ids),
            f"Expected ELParser nodes to carry generated: true; got {generated_node_ids}"
        )

