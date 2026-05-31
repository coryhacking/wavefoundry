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

