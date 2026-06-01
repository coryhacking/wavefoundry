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
        self.assertIn("src/Example.java::Example", node_ids)
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

