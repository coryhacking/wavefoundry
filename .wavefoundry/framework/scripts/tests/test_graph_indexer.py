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

    def test_ts_type_members_and_aliases_are_not_function(self):
        # Wave 1p61v Issue 1: a pure-type TS file must produce ZERO kind="function"
        # nodes — data members are `property`, type aliases are `type`, and only a
        # method signature stays callable.
        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("typescript") is None:
            self.skipTest("tree-sitter typescript grammar unavailable")
        payload = self._build_file(
            "report.types.ts",
            "export interface Report {\n"
            "  run_key: string;\n"
            "  updated_at: string;\n"
            "  describe(): string;\n"
            "}\n"
            "export type AppSource = {\n"
            "  appKey: string;\n"
            "};\n"
            "export type Status = 'a' | 'b';\n",
        )
        kinds = {n["id"]: n["kind"] for n in payload["nodes"] if "::" in n["id"]}
        # Data members → property (NOT function).
        self.assertEqual(kinds.get("report.types.ts::Report.run_key"), "property")
        self.assertEqual(kinds.get("report.types.ts::Report.updated_at"), "property")
        self.assertEqual(kinds.get("report.types.ts::appKey"), "property")
        # Type aliases → type (NOT function).
        self.assertEqual(kinds.get("report.types.ts::AppSource"), "type")
        self.assertEqual(kinds.get("report.types.ts::Status"), "type")
        # The interface itself stays class; its method signature stays callable.
        self.assertEqual(kinds.get("report.types.ts::Report"), "class")
        self.assertEqual(kinds.get("report.types.ts::Report.describe"), "function")
        # The core invariant: no data field / type alias leaked as `function`.
        self.assertNotIn(
            "function",
            {kinds[k] for k in kinds if k.rsplit(".", 1)[-1] not in ("describe",)},
        )

    def test_ts_real_callables_still_emitted(self):
        # Wave 1p61v faithfulness (AC-2): the fix must not drop real callables.
        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("typescript") is None:
            self.skipTest("tree-sitter typescript grammar unavailable")
        payload = self._build_file(
            "app.ts",
            "export const makeLogger = (name: string) => name;\n"
            "export function helper(x: number): number {\n"
            "  return x + 1;\n"
            "}\n"
            "const computeTotal = () => 1;\n",
        )
        kinds = {n["id"]: n["kind"] for n in payload["nodes"] if "::" in n["id"]}
        self.assertEqual(kinds.get("app.ts::makeLogger"), "function")
        self.assertEqual(kinds.get("app.ts::helper"), "function")
        # Arrow-const callable still emitted (the v21/v22 arrow-const path).
        self.assertEqual(kinds.get("app.ts::computeTotal"), "function")

    def test_ts_anonymous_function_keyword_not_registered(self):
        # Wave 1p61v Issue 2: a parser-artifact name (`function`, `/`) is never
        # registered as a symbol. The guard is construct-agnostic.
        self.assertFalse(self.mod._ts_is_emittable_symbol_name("function", "code"))
        self.assertFalse(self.mod._ts_is_emittable_symbol_name("/", "code"))
        self.assertFalse(self.mod._ts_is_emittable_symbol_name("/users", "code"))
        self.assertFalse(self.mod._ts_is_emittable_symbol_name("", "code"))
        # Real identifiers (incl. contextual keywords) are kept — no callable dropped.
        for ok in ("myFn", "fn", "func", "type", "async", "await", "Type.Method"):
            self.assertTrue(self.mod._ts_is_emittable_symbol_name(ok, "code"), ok)
        # Markup names legitimately contain non-identifier characters.
        self.assertTrue(self.mod._ts_is_emittable_symbol_name("my-element", "markup"))
        # Integration: no graph node is literally named `function`.
        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("javascript") is not None:
            payload = self._build_file(
                "anon.js",
                "export default function () { return 1; }\n"
                "[1, 2].map(function (x) { return x + 1; });\n",
            )
            labels = {n.get("label") for n in payload["nodes"]}
            self.assertNotIn("function", labels)

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

    # ------------------------------------------------------------------
    # Wave 1p9qi (1p9qc): SQL keyword/column-token noise suppression.
    # These exact-edge-set expectations are the CLEAN baseline the rest of
    # the SQL wave (1p9qd structured extraction, 1p9qe recovery, 1p9qf/1p9qg
    # binds) builds on — they deliberately encode NO keyword or column noise.
    # ------------------------------------------------------------------

    def _build_files(self, files: dict[str, str]):
        paths = []
        meta = {}
        for rel_path, source in files.items():
            file_path = self.root / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(source, encoding="utf-8")
            paths.append(file_path)
            meta[rel_path.replace("\\", "/")] = {"hash": f"hash-{rel_path}"}
        return self.mod.update_graph_index(
            root=self.root,
            index_dir=self.root / ".wavefoundry" / "index",
            layer="project",
            files=paths,
            current_file_meta=meta,
            changed=set(meta),
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )

    def _require_sql_parser(self):
        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("sql") is None:
            self.skipTest("tree-sitter sql grammar unavailable")

    def test_sql_keyword_and_column_noise_suppressed_exact_edge_set(self):
        """1p9qc AC-1 + AC-2 baseline, restated on 1p9qd's clause-aware model.

        Both flip directions: every genuine table reference is PRESENT — now
        as direction-aware `reads`/`writes` edges (cross-file `users`/`orders`
        binds still land at RECEIVER_RESOLVED) — and every keyword/column
        token is ABSENT. 1p9qd upgrades over the 1p9qc baseline pinned here:
        the schema-qualified reference is a single consolidated
        `external::analytics.events` read (no `analytics`+`events` field-name
        split), SQL emits no `imports`/`calls` edges at all, and write
        statements (INSERT/UPDATE/DELETE) carry the `writes` relation.
        """
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/schema.sql": (
                    "CREATE TABLE users (\n"
                    "    id INT PRIMARY KEY,\n"
                    "    active INT\n"
                    ");\n"
                    "\n"
                    "CREATE TABLE orders (\n"
                    "    id INT PRIMARY KEY,\n"
                    "    user_id INT\n"
                    ");\n"
                ),
                "db/queries.sql": (
                    "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
                    " WHERE users.active = 1;\n"
                    "\n"
                    "INSERT INTO audit_log (event) VALUES ('login');\n"
                    "\n"
                    "UPDATE users SET active = 0 WHERE users.id = 5;\n"
                    "\n"
                    "DELETE FROM orders WHERE orders.user_id = 5;\n"
                    "\n"
                    "SELECT * FROM analytics.events;\n"
                ),
            }
        )
        edges = {
            (edge["relation"], edge["source"], edge["target"], edge.get("confidence"))
            for edge in payload["edges"]
        }
        expected = {
            ("defines", "db/schema.sql", "db/schema.sql::users", "EXTRACTED"),
            ("defines", "db/schema.sql", "db/schema.sql::orders", "EXTRACTED"),
            ("reads", "db/queries.sql", "db/schema.sql::users", "RECEIVER_RESOLVED"),
            ("reads", "db/queries.sql", "db/schema.sql::orders", "RECEIVER_RESOLVED"),
            ("reads", "db/queries.sql", "external::analytics.events", "EXTRACTED"),
            ("writes", "db/queries.sql", "external::audit_log", "EXTRACTED"),
            ("writes", "db/queries.sql", "db/schema.sql::users", "RECEIVER_RESOLVED"),
            ("writes", "db/queries.sql", "db/schema.sql::orders", "RECEIVER_RESOLVED"),
        }
        self.assertEqual(edges, expected)
        # Explicit absence sweeps (readable failures + fixture-drift guards).
        target_labels = {edge["target"].split("::")[-1] for edge in payload["edges"]}
        stoplisted = {
            label for label in target_labels
            if label.casefold() in self.mod._SQL_RELATION_KEYWORD_STOPLIST
        }
        self.assertEqual(stoplisted, set(), "SQL keyword tokens leaked into edge targets")
        column_tokens = {"users.id", "orders.user_id", "users.active", "active", "event", "user_id", "id"}
        self.assertEqual(target_labels & column_tokens, set(), "column tokens leaked into edge targets")
        # 1p9qc finding (a) flip: string-literal contents (`'login'`) never
        # become reference candidates in the clause-aware model.
        self.assertNotIn("login", target_labels)

    def test_sql_create_table_does_not_import_its_own_name(self):
        """1p9qc origin: CREATE TABLE's own name node re-emitted as a
        self-referential import. Under 1p9qd's clause-aware extraction SQL
        emits no `imports` edges at all, and a definition's own name (incl.
        a self-FK) never becomes a reads/writes self-loop."""
        self._require_sql_parser()
        payload = self._build_file(
            "db/schema.sql",
            "CREATE TABLE users (\n"
            "    id INT PRIMARY KEY,\n"
            "    manager_id INT REFERENCES users(id)\n"
            ");\n",
        )
        import_edges = [edge for edge in payload["edges"] if edge["relation"] == "imports"]
        self.assertEqual(import_edges, [])
        self_loops = [e for e in payload["edges"] if e["source"] == e["target"]]
        self.assertEqual(self_loops, [], "self-FK must not emit a self-loop edge")
        # The definition itself is untouched.
        self.assertIn(
            ("defines", "db/schema.sql", "db/schema.sql::users"),
            {(e["relation"], e["source"], e["target"]) for e in payload["edges"]},
        )

    def test_sql_stoplist_never_touches_non_sql_candidates(self):
        """AC-3 flip direction: identifiers named like SQL keywords remain
        first-class call candidates in host languages (the filter is SQL-gated).
        The Kotlin/C#/Go/TS import-candidate baselines pinned in
        SharedImportCandidateBaselineTests cover the import relation."""
        if getattr(self.mod, "_ts_get_parser", lambda *_: None)("javascript") is None:
            self.skipTest("tree-sitter javascript grammar unavailable")
        payload = self._build_file(
            "src/app.js",
            "function select() { return 1; }\n"
            "function update() { return 2; }\n"
            "select();\n"
            "update();\n"
            "from();\n",
        )
        call_targets = {
            (edge["target"], edge.get("confidence"))
            for edge in payload["edges"]
            if edge["relation"] == "calls"
        }
        self.assertIn(("src/app.js::select", "RECEIVER_RESOLVED"), call_targets)
        self.assertIn(("src/app.js::update", "RECEIVER_RESOLVED"), call_targets)
        self.assertIn(("external::from", "EXTRACTED"), call_targets)

    # ------------------------------------------------------------------
    # Wave 1p9qi (1p9qd): clause-aware SQL statement extraction.
    # Exact-edge-set tests over the real grammar for every statement family;
    # the statement-analysis unit contract (AC-5) is what 1p9qe/1p9qf consume.
    # ------------------------------------------------------------------

    def _load_graph_query(self):
        path = SCRIPTS_ROOT / "graph_query.py"
        spec = importlib.util.spec_from_file_location("graph_query_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["graph_query_under_test"] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_sql_merge_statement_directions_exact_edge_set(self):
        """AC-1 (MERGE family): INTO target is a write, USING source is a read;
        aliases (`u`, `e`) and WHEN-clause field qualifiers never mint nodes."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/schema.sql": "CREATE TABLE users (id INT PRIMARY KEY, active INT);\n",
                "db/merge.sql": (
                    "MERGE INTO users u USING analytics.events e ON u.id = e.user_id"
                    " WHEN MATCHED THEN UPDATE SET u.active = 1;\n"
                ),
            }
        )
        edges = {
            (edge["relation"], edge["source"], edge["target"], edge.get("confidence"))
            for edge in payload["edges"]
        }
        expected = {
            ("defines", "db/schema.sql", "db/schema.sql::users", "EXTRACTED"),
            ("writes", "db/merge.sql", "db/schema.sql::users", "RECEIVER_RESOLVED"),
            ("reads", "db/merge.sql", "external::analytics.events", "EXTRACTED"),
        }
        self.assertEqual(edges, expected)
        node_ids = {n["id"] for n in payload["nodes"]}
        self.assertNotIn("db/merge.sql::u", node_ids, "MERGE alias must not register a symbol")

    def test_sql_qualified_name_resolution_three_tiers(self):
        """AC-2: schema-qualified references resolve to the schema-qualified
        object when defined; unqualified references fall back to a UNIQUE
        bare-name match; ambiguity (two `users` tables in different schemas)
        refuses and stays external."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/analytics.sql": "CREATE TABLE analytics.users (id INT);\n",
                "db/sales.sql": (
                    "CREATE TABLE sales.users (id INT);\n"
                    "CREATE TABLE sales.orders (id INT);\n"
                ),
                "db/queries.sql": (
                    "SELECT * FROM analytics.users;\n"   # qualified -> exact object
                    "SELECT * FROM users;\n"             # unqualified + ambiguous -> refuse
                    "SELECT * FROM orders;\n"            # unqualified + unique -> bind
                ),
            }
        )
        edges = {
            (edge["relation"], edge["target"], edge.get("confidence"))
            for edge in payload["edges"]
            if edge["source"] == "db/queries.sql"
        }
        self.assertEqual(edges, {
            ("reads", "db/analytics.sql::analytics.users", "RECEIVER_RESOLVED"),
            ("reads", "external::users", "EXTRACTED"),
            ("reads", "db/sales.sql::sales.orders", "RECEIVER_RESOLVED"),
        })

    def test_sql_view_lineage_chain_traversable_and_impact(self):
        """AC-3: CREATE VIEW chains emit traversable `reads` lineage edges and
        `code_impact` on a base table includes the dependent views (the
        data-layer default-traversal exception in graph_query)."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/schema.sql": "CREATE TABLE users (id INT PRIMARY KEY, active INT);\n",
                "db/views.sql": (
                    "CREATE VIEW active_users AS SELECT id FROM users WHERE active = 1;\n"
                    "CREATE VIEW recent_active AS SELECT id FROM active_users;\n"
                ),
            }
        )
        edges = {
            (edge["relation"], edge["source"], edge["target"], edge.get("confidence"))
            for edge in payload["edges"]
            if edge["relation"] in ("reads", "writes")
        }
        self.assertEqual(edges, {
            ("reads", "db/views.sql::active_users", "db/schema.sql::users", "RECEIVER_RESOLVED"),
            ("reads", "db/views.sql::recent_active", "db/views.sql::active_users", "RECEIVER_RESOLVED"),
        })
        gq = self._load_graph_query()
        idx = gq.GraphQueryIndex(payload)
        impact = idx.graph_impact("users")
        self.assertTrue(impact["resolved"])
        affected = {row["node_id"] for row in impact["affected"]} if impact["affected"] and isinstance(impact["affected"][0], dict) else set(impact["affected"])
        affected_ids = {str(a.get("node_id") if isinstance(a, dict) else a) for a in impact["affected"]}
        self.assertIn("db/views.sql::active_users", affected_ids)
        self.assertIn("db/views.sql::recent_active", affected_ids, "lineage must be transitive")
        # Explicit relations opt OUT of the data-layer exception.
        impact_calls_only = idx.graph_impact("users", relations=("calls",))
        calls_ids = {str(a.get("node_id") if isinstance(a, dict) else a) for a in impact_calls_only["affected"]}
        self.assertEqual(calls_ids & {"db/views.sql::active_users", "db/views.sql::recent_active"}, set())

    def test_sql_kind_property_and_report_labels(self):
        """AC-4: tables and views are distinguishable (`sql_kind` node
        property; both keep kind "class" so existing consumers ingest without
        error) and `wave_graph_report`'s ranked rows surface `sql_kind`."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/schema.sql": "CREATE TABLE users (id INT PRIMARY KEY);\n",
                "db/views.sql": "CREATE VIEW v_users AS SELECT id FROM users;\n",
                "db/q1.sql": "SELECT * FROM users;\n",
                "db/q2.sql": "SELECT * FROM users JOIN v_users ON 1 = 1;\n",
            }
        )
        by_id = {n["id"]: n for n in payload["nodes"]}
        self.assertEqual(by_id["db/schema.sql::users"]["kind"], "class")
        self.assertEqual(by_id["db/schema.sql::users"]["sql_kind"], "table")
        self.assertEqual(by_id["db/views.sql::v_users"]["kind"], "class")
        self.assertEqual(by_id["db/views.sql::v_users"]["sql_kind"], "view")
        gq = self._load_graph_query()
        idx = gq.GraphQueryIndex(payload)
        report = idx.report()
        fan_in = {row["node_id"]: row for row in report["fan_in"]}
        self.assertIn("db/schema.sql::users", fan_in, "table references count toward fan_in")
        self.assertEqual(fan_in["db/schema.sql::users"]["sql_kind"], "table")
        self.assertEqual(fan_in["db/schema.sql::users"]["kind"], "class")
        # Neighbor traversal ingests the new edges without error; `writes` is
        # not opt-in, `reads` inherits the 1p4ls opt-in policy.
        neighbors = idx.one_hop_neighbors(["db/schema.sql::users"], relations=["reads", "writes"])
        self.assertTrue(any(n["id"] == "db/q1.sql" for n in neighbors["nodes"]))

    def test_sql_statement_unit_parity_with_file_path(self):
        """AC-5: the standalone statement-analysis unit returns the same
        reference list the file extraction path derives its edges from — the
        frozen 1p9qe/1p9qf contract (name, direction; exclusions applied)."""
        self._require_sql_parser()
        sql_text = (
            "CREATE TABLE users (id INT PRIMARY KEY, org_id INT REFERENCES orgs(id));\n"
            "CREATE VIEW v1 AS SELECT id FROM users;\n"
            "WITH recent AS (SELECT * FROM orders) SELECT * FROM recent JOIN users u ON u.id = recent.uid;\n"
            "INSERT INTO audit_log (event) SELECT id FROM users;\n"
            "UPDATE users SET active = 0;\n"
            "DELETE FROM orders;\n"
            "CREATE TEMPORARY TABLE staging_x (id INT);\n"
            "SELECT * FROM staging_x;\n"
        )
        unit = self.mod.sql_statement_references(sql_text)
        self.assertIsNotNone(unit)
        self.assertEqual(
            [(d["name"], d["sql_kind"], d["temporary"]) for d in unit["definitions"]],
            [("users", "table", False), ("v1", "view", False)],
        )
        unit_refs = {(r["owner"], r["name"], r["direction"]) for r in unit["references"]}
        self.assertEqual(unit_refs, {
            ("users", "orgs", "read"),        # FK REFERENCES
            ("v1", "users", "read"),          # view lineage
            (None, "orders", "read"),         # CTE body
            (None, "users", "read"),          # outer JOIN (CTE name `recent` excluded)
            (None, "audit_log", "write"),     # INSERT INTO
            (None, "orders", "write"),        # DELETE FROM
            (None, "users", "write"),         # UPDATE
        })
        # Parity: the file path emits exactly one edge per (source, name,
        # direction) — same reference list, mapped through registration.
        payload = self._build_file("db/all.sql", sql_text)
        file_edges = {
            (edge["source"], edge["target"].split("::")[-1], edge["relation"])
            for edge in payload["edges"]
            if edge["relation"] in ("reads", "writes")
        }
        expected_edges = set()
        owner_to_source = {"users": "db/all.sql::users", "v1": "db/all.sql::v1", None: "db/all.sql"}
        for owner, name, direction in unit_refs:
            relation = "writes" if direction == "write" else "reads"
            expected_edges.add((owner_to_source[owner], name, relation))
        self.assertEqual(file_edges, expected_edges)

    def test_sql_scalar_invocation_names_never_become_references(self):
        """Wave 1p9qi integration: a scalar function invocation's name
        (`invocation > object_reference` — `NOW()`, `UPPER(x)`, `IFNULL(a,b)`)
        is a routine name, never a table reference; the generic walk minted
        `reads external::NOW`-style noise (1p9qe Progress Log finding,
        pre-existing from the 1p9qd walk; 4.4% of unit references on the
        Fineract census corpus). Argument subtrees are still walked, so a
        genuine table read inside a function-argument subquery is preserved.
        Flip-verified: pre-fix the unit returned `NOW`/`UPPER` read refs."""
        self._require_sql_parser()
        cases = {
            # (sql, expected {(name, direction)})
            "SELECT * FROM users WHERE created < NOW();": {("users", "read")},
            "SELECT COALESCE(name, 'x'), UPPER(email) FROM users;": {("users", "read")},
            "UPDATE users SET updated_at = NOW() WHERE id = 1;": {("users", "write")},
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM bans WHERE ends > NOW());": {
                ("users", "read"), ("bans", "read"),
            },
            # Genuine table read inside a scalar invocation's argument
            # subquery is PRESERVED (only the function NAME is skipped).
            "SELECT COALESCE((SELECT name FROM orgs WHERE id = 1), 'x') FROM users;": {
                ("orgs", "read"), ("users", "read"),
            },
            # Nested invocations: neither name leaks, argument subquery reads survive.
            "SELECT IFNULL(UPPER((SELECT code FROM refs_tbl LIMIT 1)), 'x') FROM users;": {
                ("refs_tbl", "read"), ("users", "read"),
            },
            # Relation-position invocation (table-valued function): unchanged
            # behavior — a routine call emits no table reference (recorded
            # routine-invocation stance; a `call` clause is future work).
            "SELECT * FROM generate_series(1, 10) g;": set(),
            "SELECT * FROM users u JOIN generate_series(1, 5) s ON u.id = s.n;": {
                ("users", "read"),
            },
        }
        for sql, expected in cases.items():
            unit = self.mod.sql_statement_references(sql)
            self.assertIsNotNone(unit, sql)
            got = {(r["name"], r["direction"]) for r in unit["references"]}
            self.assertEqual(got, expected, sql)

    def test_sql_routine_return_type_never_becomes_a_reference(self):
        """1p9qi review fix (adversarial finding 3): `CREATE FUNCTION f()
        RETURNS <type> AS ...` parses the return type as a SECOND top-level
        `object_reference` sibling of the routine name (`handle_create_
        routine` previously treated the routine name as the only exclusion,
        so the return type fell to the generic walk and minted a
        `reads external::void`-style reference — same class as the landed
        NOW()/invocation-name fix above, but for a routine's declared return
        type rather than a call expression). A named dollar-tag body
        (`$tag$...$tag$`, distinct from the bare-`$$` case already covered
        by the dialect-forms test) is the reproducing shape: the return type
        must never appear as a reference regardless of body form."""
        self._require_sql_parser()
        unit = self.mod.sql_statement_references(
            "CREATE FUNCTION f() RETURNS void AS $tag$\n"
            "  SELECT 1;\n"
            "$tag$ LANGUAGE plpgsql;\n"
        )
        ref_names = {r["name"] for r in unit["references"]}
        self.assertNotIn("void", ref_names)
        self.assertEqual(
            [(d["name"], d["sql_kind"]) for d in unit["definitions"]],
            [("f", "function")],
        )
        # A non-void return type on the trusted bare-`$$` path (already
        # covered indirectly by the dialect-forms test) must also stay clean.
        unit2 = self.mod.sql_statement_references(
            "CREATE FUNCTION count_users() RETURNS integer AS $$\n"
            "BEGIN\n  RETURN (SELECT count(*) FROM users);\nEND;\n$$ LANGUAGE plpgsql;\n"
        )
        ref_names2 = {r["name"] for r in unit2["references"]}
        self.assertNotIn("integer", ref_names2)
        self.assertEqual(ref_names2, {"users"})

    def test_sql_in_body_routine_statements_get_correct_direction(self):
        """1p9qi faithfulness fix: a natively-parsed PL/pgSQL routine body (the
        TRUSTED `$$` path — ``error_regions: 0``, NOT the recovery tier) routes
        each nested `statement` node through analyze_statement instead of
        flattening the whole body through the generic read walk, which
        hard-codes ``direction="read"`` at every object_reference. Before the
        fix this was a systematic in-body write-direction loss: in-body
        INSERT/UPDATE/DELETE were writes emitted as READS (direction inverted →
        wrong writes/writers bucket), a nested CREATE TABLE minted a phantom
        read, and a bare CREATE TEMP TABLE minted a phantom read that bypassed
        the AC-6 temp exclusion. This test pins the flipped, exact reference
        set over the real grammar; a genuine subquery read inside an
        unparseable `IF (...)` (which lands in a nested ERROR region, no
        enclosing `statement`) must still be preserved, and in-body creates
        must never mint module-scope definitions (the recovery tier's stance
        for recovered bodies, now matched on the native path)."""
        self._require_sql_parser()
        unit = self.mod.sql_statement_references(
            "CREATE FUNCTION refresh_stats() RETURNS void AS $$\n"
            "BEGIN\n"
            "  CREATE TABLE ghost_in_body (id int);\n"           # nested create: no read, no def
            "  CREATE TEMP TABLE staging (id int);\n"            # in-body temp: AC-6 exclusion, no read
            "  INSERT INTO real_audit (id) VALUES (1);\n"        # write (was read)
            "  INSERT INTO staging SELECT id FROM real_src;\n"   # staging write EXCLUDED (temp); real_src read
            "  SELECT * FROM users WHERE created < NOW();\n"     # read (NOW() invocation-name skipped)
            "  UPDATE accounts SET x = 1;\n"                     # write (was read)
            "  DELETE FROM sessions;\n"                          # write (was read)
            "  IF (SELECT count(*) FROM cond_tbl) > 0 THEN\n"    # genuine subquery read in ERROR region
            "    UPDATE more SET y = 2;\n"                       # write
            "  END IF;\n"
            "END;\n"
            "$$ LANGUAGE plpgsql;\n"
        )
        self.assertIsNotNone(unit)
        # Trusted native parse: no ERROR-region recovery for the routine itself.
        self.assertEqual(unit["error_regions"], 0)
        # Only the routine is a definition — in-body CREATE TABLE / CREATE TEMP
        # TABLE never mint module-scope definitions.
        self.assertEqual(
            [(d["name"], d["sql_kind"]) for d in unit["definitions"]],
            [("refresh_stats", "function")],
        )
        # Exact reference set: each in-body statement's clause-derived direction
        # owned by the routine. `staging` (temp) and `ghost_in_body`
        # (nested-create name) never appear; NOW/count invocation names never
        # appear.
        got = {(r["owner"], r["name"], r["direction"]) for r in unit["references"]}
        self.assertEqual(got, {
            ("refresh_stats", "real_audit", "write"),   # INSERT INTO -> write (direction corrected)
            ("refresh_stats", "real_src", "read"),      # INSERT ... SELECT source -> read
            ("refresh_stats", "users", "read"),         # SELECT ... FROM -> read
            ("refresh_stats", "accounts", "write"),     # UPDATE -> write (direction corrected)
            ("refresh_stats", "sessions", "write"),     # DELETE FROM -> write (direction corrected)
            ("refresh_stats", "cond_tbl", "read"),      # subquery read inside unparseable IF (ERROR region)
            ("refresh_stats", "more", "write"),         # UPDATE inside IF -> write
        })
        # Belt-and-braces: the in-body temp object and the nested-create name
        # are NOWHERE in the reference list (no phantom read of either).
        ref_names = {r["name"] for r in unit["references"]}
        self.assertNotIn("staging", ref_names)
        self.assertNotIn("ghost_in_body", ref_names)
        # Every in-body reference retains the trusted (unmarked) extraction —
        # the native path is not the recovery tier.
        self.assertTrue(all(r.get("extraction") is None for r in unit["references"]))

    def test_sql_query_local_names_never_mint_nodes(self):
        """AC-6: CTE names, table aliases, derived-table (subquery) aliases,
        and temp-table/table-variable forms (`#t`, `##t`, `@t`, TEMPORARY/TEMP
        TABLE) mint neither external nodes nor definitions. Adversarial
        fixture; exact edge set."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/schema.sql": (
                    "CREATE TABLE users (id INT PRIMARY KEY);\n"
                    "CREATE TABLE orders (id INT, user_id INT);\n"
                ),
                "db/adversarial.sql": (
                    "WITH recent AS (SELECT * FROM orders WHERE user_id > 5)\n"
                    "SELECT * FROM recent JOIN users ON users.id = recent.user_id;\n"
                    "SELECT x.id FROM (SELECT id FROM users) x;\n"
                    "SELECT u.id FROM users u;\n"
                    "CREATE TABLE #tmpstage (id INT);\n"
                    "SELECT * FROM #tmpstage;\n"
                    "INSERT INTO ##globalstage (id) VALUES (1);\n"
                    "SELECT * FROM @tablevar;\n"
                    "CREATE TEMPORARY TABLE staging_x (id INT);\n"
                    "SELECT * FROM staging_x;\n"
                    "DROP TABLE staging_x;\n"
                ),
            }
        )
        edges = {
            (edge["relation"], edge["source"], edge["target"], edge.get("confidence"))
            for edge in payload["edges"]
        }
        expected = {
            ("defines", "db/schema.sql", "db/schema.sql::users", "EXTRACTED"),
            ("defines", "db/schema.sql", "db/schema.sql::orders", "EXTRACTED"),
            ("reads", "db/adversarial.sql", "db/schema.sql::orders", "RECEIVER_RESOLVED"),
            ("reads", "db/adversarial.sql", "db/schema.sql::users", "RECEIVER_RESOLVED"),
        }
        self.assertEqual(edges, expected)
        node_ids = {n["id"] for n in payload["nodes"]}
        for phantom in (
            "db/adversarial.sql::recent", "db/adversarial.sql::x",
            "db/adversarial.sql::u", "db/adversarial.sql::tmpstage",
            "db/adversarial.sql::globalstage", "db/adversarial.sql::staging_x",
        ):
            self.assertNotIn(phantom, node_ids, phantom)
        self.assertFalse(
            any(nid.startswith("external::") for nid in node_ids),
            f"no external nodes expected: {sorted(nid for nid in node_ids if nid.startswith('external::'))}",
        )

    def test_sql_migration_directory_coherent_table_nodes(self):
        """AC-7: a Flyway-style numbered migration directory yields ONE node
        per table with create/alter/index/view/data references all bound."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "migrations/V1__create_users.sql": (
                    "CREATE TABLE users (id INT PRIMARY KEY, email VARCHAR(100));\n"
                ),
                "migrations/V2__create_orders.sql": (
                    "CREATE TABLE orders (id INT PRIMARY KEY, user_id INT REFERENCES users(id));\n"
                ),
                "migrations/V3__alter_users.sql": (
                    "ALTER TABLE users ADD COLUMN active INT;\n"
                    "CREATE INDEX idx_users_active ON users (active);\n"
                ),
                "migrations/V4__views_and_backfill.sql": (
                    "CREATE VIEW active_users AS SELECT id FROM users WHERE active = 1;\n"
                    "UPDATE users SET active = 1;\n"
                    "INSERT INTO orders (id, user_id) SELECT id, id FROM users;\n"
                ),
            }
        )
        users_nodes = [n["id"] for n in payload["nodes"] if n["id"].endswith("::users")]
        self.assertEqual(users_nodes, ["migrations/V1__create_users.sql::users"],
                         "exactly one node per table across the migration set")
        users_id = users_nodes[0]
        incoming = {
            (edge["relation"], edge["source"], edge.get("confidence"))
            for edge in payload["edges"]
            if edge["target"] == users_id
        }
        self.assertEqual(incoming, {
            ("defines", "migrations/V1__create_users.sql", "EXTRACTED"),
            ("reads", "migrations/V2__create_orders.sql::orders", "RECEIVER_RESOLVED"),  # FK
            ("writes", "migrations/V3__alter_users.sql", "RECEIVER_RESOLVED"),           # ALTER
            ("reads", "migrations/V3__alter_users.sql", "RECEIVER_RESOLVED"),            # CREATE INDEX ON
            ("reads", "migrations/V4__views_and_backfill.sql::active_users", "RECEIVER_RESOLVED"),
            ("writes", "migrations/V4__views_and_backfill.sql", "RECEIVER_RESOLVED"),    # UPDATE
            ("reads", "migrations/V4__views_and_backfill.sql", "RECEIVER_RESOLVED"),     # INSERT..SELECT source
        })
        externals = {n["id"] for n in payload["nodes"] if n["id"].startswith("external::")}
        self.assertEqual(externals, set(), "every migration reference binds — no externals")

    def test_sql_reads_writes_fragment_resolution_routing(self):
        """SQL table references route through the CALL machinery in cross-file
        resolution: unresolved SQL reads STAY EXTERNAL (constant reads still
        tombstone), binds require a `sql_kind` node (a same-name host-language
        twin is refused), and exact-unique binds promote to RECEIVER_RESOLVED."""
        node_map = {
            "db/schema.sql::users": {"id": "db/schema.sql::users", "kind": "class", "sql_kind": "table", "label": "users"},
            "app/users.py::users": {"id": "app/users.py::users", "kind": "class", "label": "users"},
        }
        simple_idx = {"users": ["db/schema.sql::users"], "phantom": ["app/users.py::users"]}
        ctx = {
            "node_map": node_map,
            "simple_name_index": simple_idx,
            "qualified_index": {},
            "imports_by_file": {},
            "wildcard_imports_by_file": {},
            "cs_file_ns": {},
            "java_pkg_by_file": {},
        }
        # (1) SQL read binds the unique sql_kind candidate + promotes.
        edge = {"source": "db/q.sql", "target": "external::users", "relation": "reads", "confidence": "EXTRACTED"}
        resolved = self.mod._resolve_fragment_edge(edge, ctx)
        self.assertEqual(resolved["target"], "db/schema.sql::users")
        self.assertEqual(resolved["confidence"], "RECEIVER_RESOLVED")
        # (2) Unresolved SQL read stays external — never a tombstone.
        edge = {"source": "db/q.sql", "target": "external::audit_log", "relation": "reads", "confidence": "EXTRACTED"}
        resolved = self.mod._resolve_fragment_edge(edge, ctx)
        self.assertEqual(resolved["target"], "external::audit_log")
        self.assertNotIn(self.mod._PROV_DROP, resolved)
        # (3) A non-SQL unique twin is refused (sql_kind gate).
        edge = {"source": "db/q.sql", "target": "external::phantom", "relation": "reads", "confidence": "EXTRACTED"}
        resolved = self.mod._resolve_fragment_edge(edge, ctx)
        self.assertEqual(resolved["target"], "external::phantom")
        # (4) Constant reads from non-SQL sources keep the 1p4ls contract:
        # unresolved -> tombstone.
        edge = {"source": "app/main.py::fn", "target": "external::MISSING_CONST", "relation": "reads", "confidence": "EXTRACTED"}
        resolved = self.mod._resolve_fragment_edge(edge, ctx)
        self.assertIn(self.mod._PROV_DROP, resolved)
        # (5) `writes` routes like SQL reads regardless of source suffix.
        edge = {"source": "db/q.sql", "target": "external::users", "relation": "writes", "confidence": "EXTRACTED"}
        resolved = self.mod._resolve_fragment_edge(edge, ctx)
        self.assertEqual(resolved["target"], "db/schema.sql::users")
        # (6) Lookup keys mirror the routing (scope-(b) incremental re-resolution).
        keys = self.mod._edge_lookup_keys(
            {"source": "db/q.sql", "target": "external::analytics.events", "relation": "reads"}
        )
        self.assertEqual(keys, {"analytics.events", "events"})
        keys = self.mod._edge_lookup_keys(
            {"source": "app/main.py::fn", "target": "external::SOME_CONST", "relation": "reads"}
        )
        self.assertEqual(keys, {"SOME_CONST"})

    def test_sql_error_regions_counted_on_module_node(self):
        """Unparsable DDL (e.g. a CREATE PROCEDURE header the grammar cannot
        parse) is counted loudly on the module node — 1p9qe's recovery hook —
        while parsable statements in the same file still extract."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/schema.sql": "CREATE TABLE users (id INT PRIMARY KEY);\n",
                "db/procs.sql": (
                    "CREATE PROCEDURE do_thing AS BEGIN UPDATE users SET active = 0; END;\n"
                    "SELECT * FROM users;\n"
                ),
            }
        )
        module_node = next(n for n in payload["nodes"] if n["id"] == "db/procs.sql")
        self.assertGreaterEqual(int(module_node.get("sql_error_regions") or 0), 1)
        edges = {
            (edge["relation"], edge["target"])
            for edge in payload["edges"]
            if edge["source"] == "db/procs.sql"
        }
        self.assertIn(("reads", "db/schema.sql::users"), edges)

    # ------------------------------------------------------------------
    # 1p9qe: SQL ERROR-region DDL recovery tier. Pre-fix behavior was
    # live-verified (raw tree dump, venv run 2026-07-04): the CREATE
    # PROCEDURE header parses to a top-level ERROR node (no definition, no
    # `defines` edge — the procedure vanished), and the body SELECT parsed
    # as a dangling `block` whose reference emitted at MODULE scope.
    # ------------------------------------------------------------------

    def test_sql_recovery_procedure_definition_and_body_reattachment(self):
        """AC-1 (the live-repro fixture): the unparsable procedure header
        recovers as a definition node (kind function / sql_kind procedure /
        `extraction: "sql_recovery"`) with a `defines` edge, and the body's
        `users` reference attaches to the PROCEDURE node — not the module.
        Exact edge set: no dangling module-level read remains."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/schema.sql": "CREATE TABLE users (id INT PRIMARY KEY);\n",
                "db/procs.sql": (
                    "CREATE PROCEDURE get_active_users()\n"
                    "BEGIN\n"
                    "  SELECT * FROM users;\n"
                    "END;\n"
                ),
            }
        )
        by_id = {n["id"]: n for n in payload["nodes"]}
        proc = by_id["db/procs.sql::get_active_users"]
        self.assertEqual(proc["kind"], "function")
        self.assertEqual(proc["sql_kind"], "procedure")
        self.assertEqual(proc["extraction"], "sql_recovery")
        module = by_id["db/procs.sql"]
        self.assertEqual(int(module.get("sql_error_regions") or 0), 1)
        self.assertEqual(int(module.get("sql_recovered_definitions") or 0), 1)
        self.assertNotIn("sql_unrecovered_regions", module)
        edges = {
            (edge["relation"], edge["source"], edge["target"], edge.get("confidence"))
            for edge in payload["edges"]
        }
        self.assertEqual(edges, {
            ("defines", "db/schema.sql", "db/schema.sql::users", "EXTRACTED"),
            ("defines", "db/procs.sql", "db/procs.sql::get_active_users", "EXTRACTED"),
            ("reads", "db/procs.sql::get_active_users", "db/schema.sql::users", "RECEIVER_RESOLVED"),
        })
        # 1p9qi review fix: this fixture is the DANGLING-BLOCK re-attribution
        # path specifically (the header is a lone ERROR node; BEGIN...END
        # parses as a separate top-level `block` — unlike the trigger form
        # in test_sql_recovery_dialect_forms_with_loud_degradation, where the
        # body is swallowed INSIDE the same ERROR region and re-attaches via
        # the region-tail re-parse). Confirm at the unit level that the
        # dangling-block path stamps `extraction: "sql_recovery"` on both the
        # recovered definition and the re-attributed reference, matching the
        # region-tail re-parse path's marker (scan_top's owner-gated stamp,
        # graph_indexer.py ~7915-7924).
        unit = self.mod.sql_statement_references(
            "CREATE PROCEDURE get_active_users()\nBEGIN\n  SELECT * FROM users;\nEND;\n"
        )
        self.assertEqual(
            [(d["name"], d["sql_kind"], d["extraction"]) for d in unit["definitions"]],
            [("get_active_users", "procedure", "sql_recovery")],
        )
        self.assertEqual(
            {(r["owner"], r["name"], r["direction"], r["extraction"]) for r in unit["references"]},
            {("get_active_users", "users", "read", "sql_recovery")},
        )

    def test_sql_recovery_dialect_forms_with_loud_degradation(self):
        """AC-2: T-SQL, MySQL-delimiter, and trigger forms each recover their
        definition through the ERROR-region scan; PL/pgSQL dollar-quoted
        functions parse natively (recovery never touches them); forms outside
        the vocabulary (GO / DELIMITER fragments) degrade to a counted
        unrecovered region — never silence."""
        self._require_sql_parser()
        # T-SQL: schema-qualified name; trailing GO is outside the vocabulary.
        unit = self.mod.sql_statement_references(
            "CREATE PROCEDURE dbo.get_users\nAS\nBEGIN\n  SELECT * FROM users;\nEND;\nGO\n"
        )
        self.assertEqual(
            [(d["name"], d["sql_kind"], d["extraction"]) for d in unit["definitions"]],
            [("dbo.get_users", "procedure", "sql_recovery")],
        )
        self.assertEqual(
            {(r["owner"], r["name"], r["direction"]) for r in unit["references"]},
            {("dbo.get_users", "users", "read")},
        )
        self.assertEqual(unit["error_regions"], 2)
        self.assertEqual(unit["recovery"], {"recovered_definitions": 1, "unrecovered_regions": 1, "partial_bodies": 0})
        # MySQL delimiter style: CREATE sits mid-region after DELIMITER //.
        unit = self.mod.sql_statement_references(
            "DELIMITER //\nCREATE PROCEDURE audit_cleanup()\nBEGIN\n"
            "  DELETE FROM audit_log WHERE age > 90;\nEND //\nDELIMITER ;\n"
        )
        self.assertEqual(
            [(d["name"], d["sql_kind"], d["extraction"]) for d in unit["definitions"]],
            [("audit_cleanup", "procedure", "sql_recovery")],
        )
        self.assertEqual(
            {(r["owner"], r["name"], r["direction"]) for r in unit["references"]},
            {("audit_cleanup", "audit_log", "write")},
        )
        self.assertEqual(unit["recovery"], {"recovered_definitions": 1, "unrecovered_regions": 1, "partial_bodies": 0})
        # PL/pgSQL dollar-quoted body: parses natively — trusted path, no marker.
        unit = self.mod.sql_statement_references(
            "CREATE FUNCTION count_users() RETURNS integer AS $$\nBEGIN\n"
            "  RETURN (SELECT count(*) FROM users);\nEND;\n$$ LANGUAGE plpgsql;\n"
        )
        self.assertEqual(
            [(d["name"], d["sql_kind"], d["extraction"]) for d in unit["definitions"]],
            [("count_users", "function", None)],
        )
        self.assertEqual(unit["error_regions"], 0)
        self.assertEqual(unit["recovery"], {"recovered_definitions": 0, "unrecovered_regions": 0, "partial_bodies": 0})
        # Trigger: the WHOLE statement (body included) is one ERROR region —
        # the ON-table reference and the re-parsed body INSERT both attach to
        # the recovered trigger, marked with their recovery provenance.
        unit = self.mod.sql_statement_references(
            "CREATE TRIGGER trg_users_audit AFTER INSERT ON users\nFOR EACH ROW\nBEGIN\n"
            "  INSERT INTO audit_log (event) VALUES ('insert');\nEND;\n"
        )
        self.assertEqual(
            [(d["name"], d["sql_kind"], d["extraction"]) for d in unit["definitions"]],
            [("trg_users_audit", "trigger", "sql_recovery")],
        )
        self.assertEqual(
            {(r["owner"], r["name"], r["direction"], r["extraction"]) for r in unit["references"]},
            {
                ("trg_users_audit", "users", "read", "sql_recovery"),
                ("trg_users_audit", "audit_log", "write", "sql_recovery"),
            },
        )
        self.assertEqual(unit["recovery"], {"recovered_definitions": 1, "unrecovered_regions": 0, "partial_bodies": 0})

    def test_sql_recovery_commented_and_string_ddl_never_mints(self):
        """AC-3 (adversarial): commented-out DDL (line + block comments,
        inside AND outside ERROR regions) and DDL text inside string literals
        (parsed statements and ERROR regions alike) emit nothing — recovering
        a ghost schema object would be worse than the hole."""
        self._require_sql_parser()
        unit = self.mod.sql_statement_references(
            "-- CREATE TABLE ghost1 (id INT);\n"
            "/* CREATE PROCEDURE ghost2() BEGIN SELECT 1; END; */\n"
            "CREATE PROCEDURE broken_proc(\n"
            "  -- CREATE TABLE ghost_a (id INT);\n"
            "  /* CREATE VIEW ghost_b AS SELECT 1; */\n"
            ") LANGUAGE whatever;\n"
            "CREATE PROCEDURE dyn_proc()\n"
            "BEGIN\n"
            "  EXECUTE 'CREATE TABLE ghost_c (id INT)';\n"
            "END;\n"
            "INSERT INTO t1 (sql_text) VALUES ('CREATE TABLE ghost_d (id INT)');\n"
        )
        self.assertEqual(
            [(d["name"], d["sql_kind"]) for d in unit["definitions"]],
            [("broken_proc", "procedure"), ("dyn_proc", "procedure")],
        )
        ref_names = {r["name"] for r in unit["references"]}
        self.assertEqual(ref_names, {"t1"}, "only the parsed INSERT target may reference")
        all_names = ref_names | {d["name"] for d in unit["definitions"]}
        for ghost in ("ghost1", "ghost2", "ghost_a", "ghost_b", "ghost_c", "ghost_d"):
            self.assertNotIn(ghost, all_names, ghost)
        # File path: ghosts mint neither nodes nor externals.
        payload = self._build_file(
            "db/ghosts.sql",
            "-- CREATE TABLE ghost1 (id INT);\n"
            "CREATE PROCEDURE real_proc()\n"
            "BEGIN\n"
            "  SELECT * FROM users; -- CREATE TABLE ghost5 (id INT);\n"
            "END;\n",
        )
        node_ids = {n["id"] for n in payload["nodes"]}
        self.assertIn("db/ghosts.sql::real_proc", node_ids)
        symbol_names = {nid.split("::", 1)[1] for nid in node_ids if "::" in nid}
        self.assertEqual(symbol_names & {"ghost1", "ghost5"}, set())

    def test_sql_recovery_masking_and_name_validation_units(self):
        """AC-3 unit level: the mask preserves length/newlines and handles the
        risk-table case both ways (real DDL after a same-line block comment
        recovers; DDL inside the comment does not); name validation strips
        identifier quoting, refuses garbage, and flags temp sigils."""
        text = (
            "CREATE TABLE real1 (id INT); -- CREATE TABLE ghost1\n"
            "/* CREATE TABLE ghost2 */ CREATE TABLE real2 (id INT);\n"
            "SELECT 'CREATE TABLE ghost3', \"CREATE TABLE ghost4\";\n"
            "$$ CREATE TABLE ghost5 $$\n"
            "SELECT 'it''s escaped' FROM t;\n"
        )
        masked = self.mod._sql_recovery_mask_noncode(text)
        self.assertEqual(len(masked), len(text), "masking must preserve offsets")
        self.assertEqual(
            [len(a) for a in masked.splitlines()],
            [len(a) for a in text.splitlines()],
            "masking must preserve line structure",
        )
        self.assertIn("CREATE TABLE real1", masked)
        self.assertIn("CREATE TABLE real2", masked)
        self.assertIn("FROM t", masked, "the '' escape must not swallow trailing code")
        for ghost in ("ghost1", "ghost2", "ghost3", "ghost4", "ghost5"):
            self.assertNotIn(ghost, masked, ghost)
        clean = self.mod._sql_recovery_clean_name
        self.assertEqual(clean("[dbo].[Users]"), ("dbo.Users", False))
        self.assertEqual(clean("`db`.`tbl`"), ("db.tbl", False))
        self.assertEqual(clean("analytics.events;"), ("analytics.events", False))
        self.assertEqual(clean("#tmp"), ("tmp", True))
        self.assertEqual(clean("@tablevar"), ("tablevar", True))
        self.assertEqual(clean("no//good"), (None, False))
        self.assertEqual(clean(""), (None, False))
        # Temp forms in ERROR regions stay excluded (recovery must not
        # reintroduce the 1p9qc/1p9qd-eliminated temp-object noise class).
        unit = self.mod.sql_statement_references(
            "CREATE PROCEDURE p1()\nBEGIN\n  SELECT 1;\nEND;\n"
        )
        self.assertEqual([d["name"] for d in unit["definitions"]], ["p1"])
        region = self.mod._sql_recover_error_region(
            "CREATE TEMPORARY TABLE staging_x (id INT)\nCREATE TABLE #tmpstage (id INT)", 0
        )
        self.assertEqual(region["definitions"], [])
        self.assertEqual(region["temp_names"], {"staging_x", "tmpstage"})

    def test_sql_recovery_named_dollar_tag_masking(self):
        """1p9qi review fix (adversarial finding 1): named dollar tags
        ``$tag$ ... $tag$`` mask exactly like bare ``$$`` — DDL text inside a
        ``$q$``-quoted dynamic-SQL string in an ERROR region can never mint a
        phantom schema object."""
        self._require_sql_parser()
        mask = self.mod._sql_recovery_mask_noncode
        text = "$q$ CREATE TABLE ghost_tag $q$ CREATE TABLE real_t (id INT);\n"
        masked = mask(text)
        self.assertEqual(len(masked), len(text), "masking must preserve offsets")
        self.assertNotIn("ghost_tag", masked)
        self.assertIn("CREATE TABLE real_t", masked)
        # The close tag must MATCH the open tag: $a$ ... $b$ ... $a$ spans
        # through the $b$ (PostgreSQL nested dollar-quoting semantics).
        masked2 = mask("$a$ ghost_x $b$ still_ghost $a$ live_code")
        self.assertNotIn("ghost_x", masked2)
        self.assertNotIn("still_ghost", masked2)
        self.assertIn("live_code", masked2)
        # Unterminated named tag masks to end of text (parity with bare $$).
        masked3 = mask(
            "$q$ CREATE TABLE ghost_unterm (id INT);\nCREATE TABLE ghost2 (id INT);"
        )
        self.assertNotIn("ghost_unterm", masked3)
        self.assertNotIn("ghost2", masked3)
        self.assertEqual(masked3.count("\n"), 1, "newlines preserved through the mask")
        # A lone $ that opens neither $$ nor a $tag$ is plain code text.
        self.assertEqual(mask("SELECT a $ b FROM t"), "SELECT a $ b FROM t")
        # End-to-end (the adversarial report's EXEC($q$ ... $q$) shape): the
        # recovery tier recovers ONLY the routine header — no phantom table.
        unit = self.mod.sql_statement_references(
            "CREATE PROCEDURE dbo.rebuild AS\n"
            "BEGIN\n"
            "  EXEC($q$\n"
            "CREATE TABLE ghost_tbl (id INT);\n"
            "$q$);\n"
            "END\n"
            "GO\n"
        )
        self.assertEqual(
            [(d["name"], d["sql_kind"], d["extraction"]) for d in unit["definitions"]],
            [("dbo.rebuild", "procedure", "sql_recovery")],
        )

    def test_sql_recovery_parsed_extraction_untouched(self):
        """AC-4: files with zero ERROR regions produce identical extraction —
        the exact pre-1p9qe edge/node set (pinned), no recovery markers, no
        recovery module properties; recovery never runs on parsed regions."""
        self._require_sql_parser()
        sql_text = (
            "CREATE TABLE users (id INT PRIMARY KEY);\n"
            "CREATE VIEW v1 AS SELECT id FROM users;\n"
            "INSERT INTO audit_log (event) SELECT id FROM users;\n"
        )
        unit = self.mod.sql_statement_references(sql_text)
        self.assertEqual(unit["error_regions"], 0)
        self.assertEqual(unit["recovery"], {"recovered_definitions": 0, "unrecovered_regions": 0, "partial_bodies": 0})
        self.assertTrue(all(d["extraction"] is None for d in unit["definitions"]))
        self.assertTrue(all(r["extraction"] is None for r in unit["references"]))
        payload = self._build_file("db/clean.sql", sql_text)
        edges = {
            (edge["relation"], edge["source"], edge["target"], edge.get("confidence"))
            for edge in payload["edges"]
        }
        self.assertEqual(edges, {
            ("defines", "db/clean.sql", "db/clean.sql::users", "EXTRACTED"),
            ("defines", "db/clean.sql", "db/clean.sql::v1", "EXTRACTED"),
            ("reads", "db/clean.sql::v1", "db/clean.sql::users", "RECEIVER_RESOLVED"),
            ("writes", "db/clean.sql", "external::audit_log", "EXTRACTED"),
            ("reads", "db/clean.sql", "db/clean.sql::users", "RECEIVER_RESOLVED"),
        })
        for node in payload["nodes"]:
            self.assertNotIn("extraction", node, node["id"])
            for prop in ("sql_error_regions", "sql_recovered_definitions", "sql_unrecovered_regions", "sql_partial_bodies"):
                self.assertNotIn(prop, node, node["id"])

    def test_sql_recovery_bounds_and_log_shape(self):
        """AC-5: per-file recovered/unrecovered counts land on the module
        node; the build-log line has a stable shape; byte/line ceilings
        degrade pathological regions to counted unrecovered — loudly."""
        self._require_sql_parser()
        payload = self._build_files(
            {
                "db/mixed.sql": (
                    "CREATE PROCEDURE dbo.get_users\nAS\nBEGIN\n"
                    "  SELECT * FROM users;\nEND;\nGO\n"
                ),
            }
        )
        module = next(n for n in payload["nodes"] if n["id"] == "db/mixed.sql")
        self.assertEqual(int(module.get("sql_error_regions") or 0), 2)
        self.assertEqual(int(module.get("sql_recovered_definitions") or 0), 1)
        self.assertEqual(int(module.get("sql_unrecovered_regions") or 0), 1)
        self.assertEqual(
            self.mod._sql_recovery_log_line("db/mixed.sql", 2, 1, 1),
            "build_index: sql recovery db/mixed.sql — 2 parse-error "
            "region(s): 1 definition(s) recovered, 1 region(s) unrecovered, "
            "0 routine body(ies) partially parsed",
        )
        # Byte ceiling: an over-limit region degrades to truncated/unrecovered.
        original = self.mod._SQL_RECOVERY_MAX_REGION_BYTES
        self.mod._SQL_RECOVERY_MAX_REGION_BYTES = 16
        try:
            unit = self.mod.sql_statement_references(
                "CREATE PROCEDURE get_active_users()\nBEGIN\n  SELECT * FROM users;\nEND;\n"
            )
            self.assertEqual(unit["definitions"], [])
            self.assertEqual(
                unit["recovery"], {"recovered_definitions": 0, "unrecovered_regions": 1, "partial_bodies": 0}
            )
        finally:
            self.mod._SQL_RECOVERY_MAX_REGION_BYTES = original
        region = self.mod._sql_recover_error_region(
            "CREATE PROCEDURE " + ("x" * (self.mod._SQL_RECOVERY_MAX_LINE_CHARS + 10)) + "()", 0
        )
        self.assertEqual(region["definitions"], [], "over-length lines are skipped")

    def test_sql_partial_body_loudness_for_loop_control_flow(self):
        """1p9qi delivery council: a natively-parsed PL/pgSQL routine whose
        BODY contains a loop / control-flow construct tree-sitter-sql cannot
        parse mangles the loop into a NESTED ERROR under the function body.
        The CREATE header parses at top level, so `error_regions` stays 0 and
        scan_top never sees the nested ERROR — the in-loop DML is dropped
        SILENTLY. This asserts the new `sql_partial_bodies` loudness signal
        fires (module node + unit recovery dict + build-log line) so the
        partial extraction is observable; a clean fully-parsed body does not
        trip it. Actually recovering the dropped in-loop write needs plpgsql
        control-flow parsing the grammar lacks (recorded follow-up)."""
        self._require_sql_parser()
        loop_fn = (
            "CREATE FUNCTION process_all() RETURNS void AS $$\n"
            "DECLARE r RECORD;\n"
            "BEGIN\n"
            "  FOR r IN SELECT id FROM source_tbl LOOP\n"
            "    INSERT INTO loop_audit (id) VALUES (r.id);\n"
            "  END LOOP;\n"
            "END;\n"
            "$$ LANGUAGE plpgsql;\n"
        )
        # Unit level: no top-level ERROR region (the silent-drop hazard), but
        # partial_bodies flags the nested-in-body ERROR loudly. Distinct from
        # unrecovered_regions (which stays 0 — this is NOT a top-level region).
        unit = self.mod.sql_statement_references(loop_fn)
        self.assertEqual(unit["error_regions"], 0)
        self.assertEqual(
            unit["recovery"],
            {"recovered_definitions": 0, "unrecovered_regions": 0, "partial_bodies": 1},
        )
        # The routine header still extracts as a trusted (non-recovery) def.
        self.assertEqual(
            [(d["name"], d["sql_kind"], d["extraction"]) for d in unit["definitions"]],
            [("process_all", "function", None)],
        )
        # The in-loop INSERT write is dropped (the recall gap the signal flags):
        # only the pre-loop FOR-source read survives at the routine owner.
        self.assertNotIn(
            ("loop_audit", "write"),
            {(r["name"], r["direction"]) for r in unit["references"]},
            "in-loop DML is dropped; the signal exists precisely because we cannot recover it",
        )
        # File level: the module node carries the count so it survives worker
        # extraction and reaches the verbose build log.
        payload = self._build_file("db/loop.sql", loop_fn)
        module = next(n for n in payload["nodes"] if n["id"] == "db/loop.sql")
        self.assertEqual(int(module.get("sql_partial_bodies") or 0), 1)
        self.assertNotIn("sql_error_regions", module, "no TOP-LEVEL error region")
        # Build-log line renders the partial-body count.
        self.assertEqual(
            self.mod._sql_recovery_log_line("db/loop.sql", 0, 0, 0, 1),
            "build_index: sql recovery db/loop.sql — 0 parse-error "
            "region(s): 0 definition(s) recovered, 0 region(s) unrecovered, "
            "1 routine body(ies) partially parsed",
        )
        # Negative: a clean fully-parsed body never trips the signal.
        clean_fn = (
            "CREATE FUNCTION count_users() RETURNS integer AS $$\n"
            "BEGIN\n"
            "  RETURN (SELECT count(*) FROM users);\n"
            "END;\n"
            "$$ LANGUAGE plpgsql;\n"
        )
        clean_unit = self.mod.sql_statement_references(clean_fn)
        self.assertEqual(clean_unit["recovery"]["partial_bodies"], 0)
        clean_payload = self._build_file("db/clean_fn.sql", clean_fn)
        clean_module = next(n for n in clean_payload["nodes"] if n["id"] == "db/clean_fn.sql")
        self.assertNotIn("sql_partial_bodies", clean_module)

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
        # Wave 1p9q2: per-file records live in the SQLite state store.
        store = self.mod.GraphStateStore(
            self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.sqlite",
            layer="project",
            walker_version="1",
            chunker_version="1",
        )
        try:
            record = store.get_record("docs/workflow-config.json")
        finally:
            store.close()
        self.assertEqual(record["artifact"]["kind"], "code")

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

    def test_framework_graph_layer_rejected(self):
        # Wave 1p4ww: single project graph — the framework graph layer was removed.
        with self.assertRaises(ValueError):
            self._run(
                {"src/tools.py": "def process():\n    return 1\n"},
                changed={"src/tools.py"},
                removed=set(),
                layer="framework",
            )

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

    # ---- 1p470: Python sibling-loader return-type inference ----
    # The wavefoundry lazy-loader idiom `gq = _load_graph_query()` (→
    # `_load_script("graph_query")`) previously emitted NO edge for
    # `gq.GraphQueryIndex.from_root()` because `gq` had no known type. v24
    # infers the loaded module so the cross-file edge is produced.

    def test_python_lazy_loader_module_var_three_level(self):
        """`gq = _load_graph_query(); gq.GraphQueryIndex.from_root()` resolves
        to the graph_query module's class method (3-level attribute chain)."""
        payload = self._build({
            "graph_query.py": (
                "class GraphQueryIndex:\n"
                "    @classmethod\n"
                "    def from_root(cls, root, layer='project'):\n"
                "        return cls()\n"
            ),
            "server_impl.py": (
                "def _load_script(name):\n    return None\n\n\n"
                "def _load_graph_query():\n    return _load_script('graph_query')\n\n\n"
                "def handler():\n"
                "    gq = _load_graph_query()\n"
                "    return gq.GraphQueryIndex.from_root(None, layer='project')\n"
            ),
        })
        calls = self._calls_edges(payload)
        targets = [e["target"] for e in calls if e.get("source", "").endswith("::handler")]
        self.assertIn("graph_query.py::GraphQueryIndex.from_root", targets,
                      f"lazy-loader 3-level chain must resolve; got {targets}")

    def test_python_lazy_loader_module_var_two_level(self):
        """`gq = _load_graph_query(); gq.module_func()` resolves to the module
        function (2-level), and the inline `_load_graph_query().module_func()`
        form resolves identically."""
        payload = self._build({
            "graph_query.py": "def graph_not_ready_diagnostic():\n    return {}\n",
            "server_impl.py": (
                "def _load_script(name):\n    return None\n\n\n"
                "def _load_graph_query():\n    return _load_script('graph_query')\n\n\n"
                "def via_var():\n"
                "    gq = _load_graph_query()\n"
                "    return gq.graph_not_ready_diagnostic()\n\n\n"
                "def via_inline():\n"
                "    return _load_graph_query().graph_not_ready_diagnostic()\n"
            ),
        })
        calls = self._calls_edges(payload)
        for who in ("::via_var", "::via_inline"):
            targets = [e["target"] for e in calls if e.get("source", "").endswith(who)]
            self.assertIn("graph_query.py::graph_not_ready_diagnostic", targets,
                          f"{who} must resolve module func; got {targets}")

    def test_python_lazy_loader_direct_load_script(self):
        """Direct `gc = _load_script('graph_cluster'); gc.func()` resolves
        without a wrapper function."""
        payload = self._build({
            "graph_cluster.py": "def build_clusters():\n    return []\n",
            "server_impl.py": (
                "def _load_script(name):\n    return None\n\n\n"
                "def handler():\n"
                "    gc = _load_script('graph_cluster')\n"
                "    return gc.build_clusters()\n"
            ),
        })
        calls = self._calls_edges(payload)
        targets = [e["target"] for e in calls if e.get("source", "").endswith("::handler")]
        self.assertIn("graph_cluster.py::build_clusters", targets,
                      f"direct _load_script var must resolve; got {targets}")

    # ---- 1p470: ambiguous cross-file import disambiguation ----
    # When a receiver's simple name maps to MULTIPLE same-named project
    # candidates, the source file's `imports` edge picks the right one.

    def test_python_ambiguous_import_disambiguates(self):
        """Two `User` classes in different packages; `app` importing
        `pkg_a.models.User` must resolve `u.save()` to pkg_a's, not pkg_b's."""
        payload = self._build({
            "pkg_a/models.py": "class User:\n    def save(self):\n        return 1\n",
            "pkg_b/models.py": "class User:\n    def save(self):\n        return 2\n",
            "app.py": "from pkg_a.models import User\n\n\ndef handler():\n    u: User = User()\n    return u.save()\n",
        })
        calls = self._calls_edges(payload)
        save_targets = [
            e["target"] for e in calls
            if e.get("source", "").endswith("::handler") and "save" in str(e.get("target", ""))
        ]
        self.assertIn("pkg_a/models.py::User.save", save_targets,
                      f"must disambiguate to imported pkg_a; got {save_targets}")
        self.assertNotIn("pkg_b/models.py::User.save", save_targets,
                         "must NOT resolve to the non-imported pkg_b twin")

    def test_java_ambiguous_import_disambiguates(self):
        """Two `Helper` classes in different packages; `App` importing
        `com.foo.Helper` must resolve `h.process()` to com.foo's, not com.bar's."""
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        payload = self._build({
            "com/foo/Helper.java": "package com.foo;\npublic class Helper {\n    public void process() {}\n}\n",
            "com/bar/Helper.java": "package com.bar;\npublic class Helper {\n    public void process() {}\n}\n",
            "com/app/App.java": "package com.app;\nimport com.foo.Helper;\npublic class App {\n    void run() {\n        Helper h = new Helper();\n        h.process();\n    }\n}\n",
        })
        calls = self._calls_edges(payload)
        proc_targets = [
            e["target"] for e in calls
            if "App.run" in str(e.get("source", "")) and "process" in str(e.get("target", ""))
        ]
        self.assertIn("com/foo/Helper.java::Helper.process", proc_targets,
                      f"must disambiguate to imported com.foo; got {proc_targets}")
        self.assertNotIn("com/bar/Helper.java::Helper.process", proc_targets,
                         "must NOT resolve to the non-imported com.bar twin")

    def test_ambiguous_without_import_stays_external(self):
        """Safety: an ambiguous receiver with NO disambiguating import must
        stay external — the disambiguation never guesses."""
        payload = self._build({
            "pkg_a/models.py": "class User:\n    def save(self):\n        return 1\n",
            "pkg_b/models.py": "class User:\n    def save(self):\n        return 2\n",
            # No import of User — references it bare (ambiguous, unresolvable).
            "app.py": "def handler():\n    u: User = make()\n    return u.save()\n",
        })
        calls = self._calls_edges(payload)
        save_targets = [
            e["target"] for e in calls
            if e.get("source", "").endswith("::handler") and "save" in str(e.get("target", ""))
        ]
        # Must not have bound to either project node (ambiguous, no import).
        self.assertNotIn("pkg_a/models.py::User.save", save_targets)
        self.assertNotIn("pkg_b/models.py::User.save", save_targets)

    def test_collapsed_class_node_does_not_suppress_resolution(self):
        """1p4ef: two namespace-less C# classes both basename-merge (collapse to the
        file-id node, no `::`). Before the fix, the collapsed nodes leaked the prior
        iteration's `qualified` into the dotted-form `qualified_index` build, injecting
        a phantom candidate that inflated `Service.Process` to ambiguous (`len>1`) and
        the unique cross-file call was suppressed to `external::`. The fix binds
        `qualified = simple` for collapsed nodes so the phantom never appears.
        Verified bug-sensitive: without the fix this resolves to `external::Service.Process`."""
        try:
            import tree_sitter_c_sharp  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_c_sharp not available in test env")
        payload = self._build({
            "Service.cs": "public class Service { public void Process() {} }\n",
            "Worker.cs": "public class Worker { void Run() { Service s = new Service(); s.Process(); } }\n",
        })
        calls = self._calls_edges(payload)
        targets = [
            e["target"] for e in calls
            if "Worker.Run" in str(e.get("source", "")) and "Process" in str(e.get("target", ""))
        ]
        self.assertIn("Service.cs::Service.Process", targets,
                      f"collapsed-class phantom must not suppress the unique cross-file call; got {targets}")
        self.assertNotIn("external::Service.Process", targets)

    def test_java_same_package_ambiguous_receiver_disambiguates(self):
        """1p4er: two `JreCompat` classes in different packages both define
        `canAccess`; a SAME-PACKAGE caller (no import — Java makes same-package
        types visible without one) resolves `jc.canAccess()` to its own-package
        twin, NOT the cross-package twin (the field miss). The 1p470 import
        disambiguation can't fire (no import edge); the same-directory fallback does."""
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        payload = self._build({
            "el/javax/JreCompat.java": "package el.javax;\npublic class JreCompat { public boolean canAccess() { return true; } }\n",
            "el/apache/util/JreCompat.java": "package el.apache.util;\npublic class JreCompat { public boolean canAccess() { return false; } }\n",
            "el/javax/Caller.java": "package el.javax;\npublic class Caller { JreCompat jc; void run() { jc.canAccess(); } }\n",
        })
        calls = self._calls_edges(payload)
        targets = [e["target"] for e in calls
                   if "Caller.run" in str(e.get("source", "")) and "canAccess" in str(e.get("target", ""))]
        self.assertIn("el/javax/JreCompat.java::JreCompat.canAccess", targets,
                      f"same-package twin must resolve; got {targets}")
        self.assertNotIn("el/apache/util/JreCompat.java::JreCompat.canAccess", targets)

    def test_same_package_fallback_no_colocated_candidate_stays_external(self):
        """1p4er safety: an ambiguous receiver with NO import AND no twin in the
        caller's own directory stays external — the fallback never guesses across
        directories (resolution order: explicit import > same package > nothing)."""
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        payload = self._build({
            "el/javax/JreCompat.java": "package el.javax;\npublic class JreCompat { public boolean canAccess() { return true; } }\n",
            "el/apache/util/JreCompat.java": "package el.apache.util;\npublic class JreCompat { public boolean canAccess() { return false; } }\n",
            "el/other/Caller.java": "package el.other;\npublic class Caller { JreCompat jc; void run() { jc.canAccess(); } }\n",
        })
        calls = self._calls_edges(payload)
        targets = [e["target"] for e in calls
                   if "Caller.run" in str(e.get("source", "")) and "canAccess" in str(e.get("target", ""))]
        self.assertNotIn("el/javax/JreCompat.java::JreCompat.canAccess", targets)
        self.assertNotIn("el/apache/util/JreCompat.java::JreCompat.canAccess", targets)

    def test_go_cross_package_method_resolves(self):
        """1p4et: Go methods now key as `Type.method` (was bare `method`) and
        `var h foo.Helper` qualified-type receivers infer their type, so a
        cross-package method call resolves at RECEIVER_RESOLVED."""
        try:
            import tree_sitter_go  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_go not available in test env")
        payload = self._build({
            "foo/helper.go": "package foo\ntype Helper struct{}\nfunc (h Helper) Process() int { return 1 }\n",
            "app/app.go": "package app\nimport \"x/foo\"\nfunc Run() { var h foo.Helper; h.Process() }\n",
        })
        calls = self._calls_edges(payload)
        run = [e for e in calls if "::Run" in str(e.get("source", "")) and "Process" in str(e.get("target", ""))]
        self.assertTrue(
            any(e["target"] == "foo/helper.go::Helper.Process" for e in run),
            f"cross-package Go method must resolve to Helper.Process; got {[(e['target'], e.get('confidence')) for e in run]}")

    def test_go_same_method_name_types_do_not_collide(self):
        """1p4et: two Go types with a same-named method register as distinct
        `Type.method` nodes instead of colliding to one bare-`method` id."""
        try:
            import tree_sitter_go  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_go not available in test env")
        payload = self._build({
            "m/codec.go": "package m\ntype Reader struct{}\nfunc (r Reader) Encode() int { return 1 }\ntype Writer struct{}\nfunc (w Writer) Encode() int { return 2 }\n",
        })
        ids = {n["id"] for n in payload["nodes"] if "Encode" in n["id"]}
        self.assertIn("m/codec.go::Reader.Encode", ids)
        self.assertIn("m/codec.go::Writer.Encode", ids)

    def test_rust_associated_fn_and_let_binding_resolve(self):
        """1p4eu: `Bar::build()` (associated fn, scoped_identifier callee) and
        `let x = Bar{}; x.process()` (struct-literal binding inference) both
        resolve cross-file to the project method nodes (RECEIVER_RESOLVED)."""
        try:
            import tree_sitter_rust  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_rust not available in test env")
        payload = self._build({
            "crate/a.rs": "pub struct Bar {}\nimpl Bar {\n  pub fn build() -> i32 { 1 }\n  pub fn process(&self) -> i32 { 2 }\n}\n",
            "crate/b.rs": "use crate::a::Bar;\npub fn caller() {\n  let _ = Bar::build();\n  let x = Bar{};\n  let _ = x.process();\n}\n",
        })
        targets = {e["target"] for e in self._calls_edges(payload) if "caller" in str(e.get("source", ""))}
        self.assertIn("crate/a.rs::Bar.build", targets, f"associated fn must resolve; got {targets}")
        self.assertIn("crate/a.rs::Bar.process", targets, f"let-bound receiver must resolve; got {targets}")

    def test_rust_module_function_call_stays_external(self):
        """1p4eu faithfulness: a lowercase-module scoped call `io::stdin()` must
        NOT be mis-keyed as a type method — the PascalCase guard leaves it
        external (never a wrong project edge)."""
        try:
            import tree_sitter_rust  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_rust not available in test env")
        payload = self._build({
            "crate/b.rs": "pub fn caller() { let _ = io::stdin(); }\n",
        })
        targets = [e["target"] for e in self._calls_edges(payload)
                   if "caller" in str(e.get("source", "")) and "stdin" in str(e.get("target", ""))]
        self.assertFalse(any(not str(t).startswith("external::") for t in targets),
                         f"lowercase module fn must stay external; got {targets}")

    def test_rust_generic_receiver_stays_external(self):
        """1p4eu AC-6 fail-safe: a method call on a generic receiver whose type
        cannot be statically resolved to a single named type (`fn caller<T: Runner>(t: T)
        { t.run() }`) must stay external — never bind a same-named project method
        (`Thing.run`) by simple-name guesswork."""
        try:
            import tree_sitter_rust  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_rust not available in test env")
        payload = self._build({
            "crate/a.rs": "pub struct Thing {}\nimpl Thing { pub fn run(&self) -> i32 { 1 } }\n",
            "crate/b.rs": "pub trait Runner { fn run(&self) -> i32; }\npub fn caller<T: Runner>(t: T) -> i32 { t.run() }\n",
        })
        targets = [e["target"] for e in self._calls_edges(payload)
                   if "caller" in str(e.get("source", "")) and "run" in str(e.get("target", ""))]
        self.assertTrue(all(str(t).startswith("external::") for t in targets),
                        f"generic/unresolvable receiver must stay external; got {targets}")

    def test_rust_use_import_extractor_clean_no_keyword_noise(self):
        """1p4eu AC-5: Rust `use` declarations produce clean dotted import edges
        (final segment = the imported type name, `imports_by_file`-consumable),
        with the `::` path normalized to dots and an `as` alias's target keeping
        the REAL type name — and NO `use`/`pub`/`fn`/`as` keyword-noise or lossy
        `::`-path edge."""
        try:
            import tree_sitter_rust  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_rust not available in test env")
        payload = self._build({
            "crate/b.rs": "use crate::services::Helper;\nuse super::util::{Reader, Writer as W};\npub fn caller() {}\n",
        })
        imports = {e["target"] for e in payload["edges"]
                   if e.get("relation") == "imports" and "b.rs" in str(e.get("source", ""))}
        self.assertIn("external::crate.services.Helper", imports, f"got {imports}")
        self.assertIn("external::super.util.Reader", imports, f"got {imports}")
        self.assertIn("external::super.util.Writer", imports, f"got {imports}")  # alias's REAL type
        for junk in ("external::use", "external::pub", "external::fn", "external::as",
                     "external::crate::services::Helper", "external::caller"):
            self.assertNotIn(junk, imports, f"keyword/lossy noise leaked: {junk} in {imports}")

    def test_kotlin_aliased_import_no_bare_alias_node(self):
        """1p4eu: a Kotlin aliased import `import X as W` emits the real type's
        edge and registers the alias in import_aliases, but NOT a redundant
        cosmetic `external::W` node — and no `import`/`as`/`package` keyword noise."""
        try:
            import tree_sitter_kotlin  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_kotlin not available in test env")
        payload = self._build({
            "app/Caller.kt": "package app\nimport com.foo.Helper\nimport com.bar.util.Writer as W\nfun run() {}\n",
        })
        imports = {e["target"] for e in payload["edges"]
                   if e.get("relation") == "imports" and "Caller.kt" in str(e.get("source", ""))}
        self.assertIn("external::com.foo.Helper", imports, f"got {imports}")
        self.assertIn("external::com.bar.util.Writer", imports, f"alias's real type must be emitted; got {imports}")
        self.assertNotIn("external::W", imports, f"redundant bare-alias node leaked: {imports}")
        for junk in ("external::import", "external::as", "external::package", "external::fun"):
            self.assertNotIn(junk, imports, f"keyword noise leaked: {junk} in {imports}")

    def test_csharp_namespace_membership_disambiguates(self):
        """1p4ev: two `Service` classes in different namespaces; the call resolves
        to the twin in the `using`-imported namespace — and FLIPS when the `using`
        changes, proving it is import-driven and never binds the wrong twin
        (the security-reviewer faithfulness property). The namespace is derived
        from the node qname (`Namespace.Class.method`)."""
        try:
            import tree_sitter_c_sharp  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_c_sharp not available in test env")
        twins = {
            "svc/Service.cs": "namespace Acme.Services {\n  public class Service { public void Process() {} }\n}\n",
            "oth/Service.cs": "namespace Acme.Other {\n  public class Service { public void Process() {} }\n}\n",
        }

        def resolve(using_ns):
            files = dict(twins)
            files["app/App.cs"] = (
                f"using {using_ns};\nnamespace Acme.App {{\n"
                "  public class App { Service svc; void Run() { svc.Process(); } }\n}\n"
            )
            payload = self._build(files)
            return [e["target"] for e in self._calls_edges(payload)
                    if "App.Run" in str(e.get("source", "")) and "Process" in str(e.get("target", ""))]

        self.assertIn("svc/Service.cs::Acme.Services.Service.Process", resolve("Acme.Services"))
        self.assertIn("oth/Service.cs::Acme.Other.Service.Process", resolve("Acme.Other"))
        # The flip is the faithfulness proof — it never blindly binds one twin.
        self.assertNotIn("oth/Service.cs::Acme.Other.Service.Process", resolve("Acme.Services"))
        self.assertNotIn("svc/Service.cs::Acme.Services.Service.Process", resolve("Acme.Other"))

    def test_csharp_nested_class_caller_binds_own_namespace_not_sibling(self):
        """1p4eq faithfulness: a caller inside a NESTED class must resolve to the
        twin in its FILE's declared namespace, never to a sibling twin whose
        namespace coincides with the nested class path. The caller's namespace is
        derived from its file's declared namespace nodes (nesting-proof), not by
        string-stripping a fixed two qname segments (which mis-derived
        `Acme.Web.Outer` for a caller whose real namespace is `Acme.Web`)."""
        try:
            import tree_sitter_c_sharp  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_c_sharp not available in test env")
        payload = self._build({
            "a/Service.cs": "namespace Acme.Web {\n  public class Service { public void Process(){} }\n}\n",
            "b/Service.cs": "namespace Acme.Web.Outer {\n  public class Service { public void Process(){} }\n}\n",
            "app/App.cs": (
                "namespace Acme.Web {\n  public class Outer {\n"
                "    public class App { Service svc; void Run(){ svc.Process(); } }\n  }\n}\n"
            ),
        })
        targets = {e["target"] for e in self._calls_edges(payload)
                   if "App.Run" in str(e.get("source", "")) and "Process" in str(e.get("target", ""))}
        # Same namespace (Acme.Web) — the correct twin.
        self.assertIn("a/Service.cs::Acme.Web.Service.Process", targets, f"got {targets}")
        # The sibling twin (Acme.Web.Outer) coincides with the nested-class path
        # and MUST NOT be bound — the old fixed-strip derivation bound it.
        self.assertNotIn("b/Service.cs::Acme.Web.Outer.Service.Process", targets, f"got {targets}")

    def test_go_qualified_receiver_binds_named_package_not_colocated_twin(self):
        """1p4eq faithfulness: `var h foo.Helper; h.Process()` must bind the twin
        in package `foo` even when the CALLER is co-located with a different
        same-named twin (package `bar`). The package qualifier is authoritative;
        the 1p4er same-directory fallback must not override an explicit
        cross-package type (the wrong RECEIVER_RESOLVED edge the verification
        caught — dropping the package collapsed both twins to `Helper.Process`)."""
        try:
            import tree_sitter_go  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_go not available in test env")
        payload = self._build({
            "foo/helper.go": "package foo\ntype Helper struct{}\nfunc (h Helper) Process() int { return 1 }\n",
            "bar/helper.go": "package bar\ntype Helper struct{}\nfunc (h Helper) Process() int { return 2 }\n",
            "bar/app.go": "package bar\nimport \"x/foo\"\nfunc Run() { var h foo.Helper; h.Process() }\n",
        })
        targets = {e["target"] for e in self._calls_edges(payload)
                   if "::Run" in str(e.get("source", "")) and "Process" in str(e.get("target", ""))}
        self.assertIn("foo/helper.go::Helper.Process", targets, f"must bind named package foo; got {targets}")
        self.assertNotIn("bar/helper.go::Helper.Process", targets, f"must NOT bind co-located bar twin; got {targets}")

    def test_go_qualified_receiver_unknown_package_stays_external(self):
        """1p4eq faithfulness: `var h foo.Helper` where the project has NO package
        `foo` (foo is a third-party import) must stay external — never bind a
        project `Helper` that lives in a differently-named package."""
        try:
            import tree_sitter_go  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_go not available in test env")
        payload = self._build({
            "x/helper.go": "package x\ntype Helper struct{}\nfunc (h Helper) Process() int { return 1 }\n",
            "y/app.go": "package y\nimport \"ext/foo\"\nfunc Run() { var h foo.Helper; h.Process() }\n",
        })
        targets = [e["target"] for e in self._calls_edges(payload)
                   if "::Run" in str(e.get("source", "")) and "Process" in str(e.get("target", ""))]
        self.assertTrue(all(str(t).startswith("external::") for t in targets),
                        f"unknown package qualifier must stay external; got {targets}")

    def test_python_same_dir_unimported_receiver_stays_external(self):
        """1p4eq regression fix: the 1p4er same-directory fallback is gated to
        Java/Kotlin/Go (same-dir ⇒ same-package visibility). Python requires an
        EXPLICIT import for a sibling symbol, so a co-located same-name twin used
        without an import must stay external — same-directory confers nothing."""
        payload = self._build({
            "pkg_a/models.py": "class User:\n    def save(self): return 1\n",
            "pkg_b/models.py": "class User:\n    def save(self): return 2\n",
            "pkg_a/app.py": "def handler():\n    u: User = make()\n    return u.save()\n",
        })
        targets = [e["target"] for e in self._calls_edges(payload)
                   if "handler" in str(e.get("source", "")) and "save" in str(e.get("target", ""))]
        self.assertTrue(all(str(t).startswith("external::") for t in targets),
                        f"Python same-dir unimported receiver must stay external; got {targets}")


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

    # AC-5 (field reproducer): constructor call resolves to the merged node.
    def test_field_reproducer_constructor_call_resolves(self):
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


class PythonConfidencePromotionTests(unittest.TestCase):
    """1p7dg: v23-style confidence promotion for Python. A call that binds a
    UNIQUE project node BY CONSTRUCTION — enclosing-class method (`self`/`cls`),
    same-file bare def, qualified `Owner.method`, or unique (`len==1`) cross-file
    simple name — lands RECEIVER_RESOLVED, not EXTRACTED, even though no receiver
    TYPE was needed. These binds were already correct; only the confidence label
    was conservatively under-tagged (the documented TS/JS v23 situation; spike:
    6,392 same-file + 552 cross-file Python edges on the self-host graph).

    Faithfulness: a guessed receiver (unannotated local `foo.bar()`) emits no
    edge and is never promoted; an ambiguous (`len>1`) simple name is not
    uniquely bound, so it stays external/EXTRACTED — the existing
    `symbol_lookup`/`simple_name_index` uniqueness gates are unchanged, only the
    label on an already-unique bind moves."""

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

    def _confs(self, payload, src_sub, tgt_sub):
        return [
            e.get("confidence")
            for e in payload.get("edges", [])
            if e.get("relation") == "calls"
            and src_sub in str(e.get("source", ""))
            and tgt_sub in str(e.get("target", ""))
        ]

    def test_self_method_call_promoted(self):
        payload = self._build({
            "src/foo.py": "class Foo:\n    def helper(self): pass\n    def run(self):\n        self.helper()\n",
        })
        confs = self._confs(payload, "Foo.run", "Foo.helper")
        self.assertEqual(confs, ["RECEIVER_RESOLVED"], f"self.helper() not promoted: {confs}")

    def test_same_file_bare_call_promoted(self):
        payload = self._build({
            "src/foo.py": "def helper(): pass\ndef run():\n    helper()\n",
        })
        confs = self._confs(payload, "foo.py::run", "foo.py::helper")
        self.assertEqual(confs, ["RECEIVER_RESOLVED"], f"same-file helper() not promoted: {confs}")

    def test_qualified_owner_method_promoted(self):
        payload = self._build({
            "src/foo.py": "class Foo:\n    def bar(self): pass\ndef run():\n    Foo.bar(None)\n",
        })
        confs = self._confs(payload, "foo.py::run", "Foo.bar")
        self.assertEqual(confs, ["RECEIVER_RESOLVED"], f"Owner.method() not promoted: {confs}")

    def test_cross_file_explicit_import_promoted(self):
        # Wave 1p7dg cross-file pass: a cross-file call via an explicit
        # `from x import y` resolves to the project node through an exact-unique
        # rewrite branch (qualified_index / import-edge disambiguation, len==1) —
        # now promoted EXTRACTED->RECEIVER_RESOLVED (language-agnostic). The bind
        # is exact-by-name; the target is unchanged, only the confidence label.
        payload = self._build({
            "src/a.py": "def uniquefn(): pass\n",
            "src/b.py": "from src.a import uniquefn\ndef run():\n    uniquefn()\n",
        })
        confs = self._confs(payload, "b.py::run", "uniquefn")
        self.assertTrue(confs, f"cross-file call edge missing entirely: {confs}")
        self.assertIn("RECEIVER_RESOLVED", confs, f"exact cross-file bind not promoted: {confs}")

    def test_unannotated_receiver_guess_not_promoted(self):
        # FAITHFULNESS: an unannotated local's `foo.bar()` is a receiver-type
        # guess — it must NOT bind/promote (no type is known).
        payload = self._build({
            "src/foo.py": "class Foo:\n    def bar(self): pass\n",
            "src/bar.py": "from src.foo import Foo\ndef make():\n    foo = Foo()\n    foo.bar()\n",
        })
        confs = self._confs(payload, "bar.py::make", "Foo.bar")
        self.assertNotIn("RECEIVER_RESOLVED", confs, f"guessed receiver wrongly promoted: {confs}")
        self.assertEqual(confs, [], f"guessed receiver should emit no Foo.bar edge: {confs}")

    def test_ambiguous_cross_file_simple_name_not_promoted(self):
        # FAITHFULNESS: two project defs of `dup` → `simple_name_index['dup']`
        # has len 2 → no unique bind → not promoted (stays external/EXTRACTED).
        payload = self._build({
            "src/a.py": "def dup(): pass\n",
            "src/b.py": "def dup(): pass\n",
            "src/c.py": "import src.a\nimport src.b\ndef run():\n    src.a.dup()\n",
        })
        # The ambiguous bare leaf must never be RECEIVER_RESOLVED via simple-name.
        rr = [
            e for e in payload.get("edges", [])
            if e.get("relation") == "calls"
            and "c.py::run" in str(e.get("source", ""))
            and e.get("confidence") == "RECEIVER_RESOLVED"
            and "dup" in str(e.get("target", "")).lower()
            and not str(e.get("target", "")).startswith("src/a.py")
        ]
        self.assertEqual(rr, [], f"ambiguous simple-name wrongly promoted: {rr}")


class CrossLanguageSameFilePromotionTests(unittest.TestCase):
    """1p7dg: the TS/JS symbol-table promotion (v23) widened to ALL tree-sitter
    languages. A same-file call that the per-language receiver resolver does not
    resolve (e.g. a bare same-class call) but `_ts_resolve_target` binds to a
    unique same-file node lands RECEIVER_RESOLVED, not EXTRACTED. Confidence
    relabel only — the target is the same unique bind the resolver already made."""

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

    def _confs(self, payload, src_sub, tgt_sub):
        return [
            e.get("confidence")
            for e in payload.get("edges", [])
            if e.get("relation") == "calls"
            and src_sub in str(e.get("source", ""))
            and tgt_sub in str(e.get("target", ""))
        ]

    def test_java_same_file_bare_call_promoted(self):
        payload = self._build({
            "src/A.java": "class A {\n  void helper() {}\n  void run() { helper(); }\n}\n",
        })
        confs = self._confs(payload, "A.java::A.run", "A.helper")
        self.assertTrue(confs, f"Java same-file call edge missing: {confs}")
        self.assertNotIn("EXTRACTED", confs, f"Java same-file bind not promoted: {confs}")

    def test_swift_same_file_bare_call_promoted(self):
        payload = self._build({
            "src/A.swift": "class A {\n  func helper() {}\n  func run() { helper() }\n}\n",
        })
        confs = self._confs(payload, "A.swift::A.run", "A.helper")
        self.assertTrue(confs, f"Swift same-file call edge missing: {confs}")
        self.assertNotIn("EXTRACTED", confs, f"Swift same-file bind not promoted: {confs}")


class ConfigKeyReaderEdgeTests(unittest.TestCase):
    """1p7dh: config-key -> reader edges. A `.get("KEY")` / `cfg["KEY"]` literal
    that matches a config-key node (`file.json::key`) emits a `reads_config`
    edge at LITERAL_DERIVED confidence. Self-bounding + faithful: an unmatched
    literal emits nothing; an ambiguous one (same key in >1 config file) is
    dropped rather than bound to the wrong twin."""

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

    def _reads_config(self, payload):
        return [
            e for e in payload.get("edges", [])
            if e.get("relation") == "reads_config"
        ]

    def test_get_literal_emits_reads_config_edge(self):
        payload = self._build({
            "settings/app-config.json": '{"factor_review_policy": "strict"}\n',
            "src/loader.py": "def load(cfg):\n    return cfg.get(\"factor_review_policy\")\n",
        })
        edges = self._reads_config(payload)
        self.assertTrue(edges, f"no reads_config edge emitted: {[e for e in payload.get('edges', []) if e.get('relation') != 'defines']}")
        e = edges[0]
        self.assertEqual(e.get("confidence"), "LITERAL_DERIVED", e)
        self.assertIn("loader.py::load", str(e.get("source", "")))
        self.assertIn("app-config.json::factor_review_policy", str(e.get("target", "")))

    def test_subscript_literal_emits_reads_config_edge(self):
        payload = self._build({
            "settings/app-config.json": '{"timeout_seconds": 30}\n',
            "src/loader.py": "def load(cfg):\n    return cfg[\"timeout_seconds\"]\n",
        })
        edges = self._reads_config(payload)
        self.assertTrue(edges, "no reads_config edge for subscript read")
        self.assertIn("app-config.json::timeout_seconds", str(edges[0].get("target", "")))

    def test_unmatched_literal_emits_no_edge(self):
        payload = self._build({
            "settings/app-config.json": '{"factor_review_policy": "strict"}\n',
            "src/loader.py": "def load(cfg):\n    return cfg.get(\"unmatched_config_key\")\n",
        })
        self.assertEqual(self._reads_config(payload), [], "unmatched literal should emit no edge")

    def test_non_config_json_not_bound(self):
        # FAITHFULNESS: a data/fixture .json (no config/profile in name) is not a
        # config surface — a coincidental key match must NOT bind.
        payload = self._build({
            "data/retrieval_eval.json": '{"distinctive_key": 1}\n',
            "src/loader.py": "def load(cfg):\n    return cfg.get(\"distinctive_key\")\n",
        })
        self.assertEqual(self._reads_config(payload), [], "non-config JSON should not bind")

    def test_generic_key_not_bound(self):
        # FAITHFULNESS: a non-distinctive bare key (<10 chars, no underscore) is
        # too generic to bind even on a config file.
        payload = self._build({
            "settings/app-config.json": '{"kind": "x"}\n',
            "src/loader.py": "def load(cfg):\n    return cfg.get(\"kind\")\n",
        })
        self.assertEqual(self._reads_config(payload), [], "generic key should not bind")

    def test_ambiguous_config_key_not_bound(self):
        # FAITHFULNESS: the same key in two config files → ambiguous → no edge.
        payload = self._build({
            "settings/a-config.json": '{"shared_setting_key": 1}\n',
            "settings/b-config.json": '{"shared_setting_key": 2}\n',
            "src/loader.py": "def load(cfg):\n    return cfg.get(\"shared_setting_key\")\n",
        })
        self.assertEqual(self._reads_config(payload), [], "ambiguous config key should not bind")


class JavaConfigReaderEdgeTests(unittest.TestCase):
    """1p7dh: `reads_config` extended to Java/Spring FILE config. A
    `.properties`/`.yml`/`.yaml` config key becomes a config-key node
    (`file::dotted.key`); a Java `@Value("${key}")` annotation or an
    `Environment.getProperty("key")` call captures the key as a config-read
    candidate; the language-agnostic finalize pass binds them on a unique
    config-file + distinctive-key match (LITERAL_DERIVED confidence). Faithful:
    an unmatched key emits nothing; a non-config `.yml` is not a config surface."""

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

    def _reads_config(self, payload):
        return [
            e for e in payload.get("edges", [])
            if e.get("relation") == "reads_config"
        ]

    def test_yaml_value_annotation_emits_reads_config_edge(self):
        payload = self._build({
            "src/main/resources/application.yml": (
                "spring:\n"
                "  datasource:\n"
                "    url: jdbc:postgresql://localhost/db\n"
            ),
            "src/main/java/Db.java": (
                "class Db {\n"
                "  @Value(\"${spring.datasource.url}\")\n"
                "  private String url;\n"
                "}\n"
            ),
        })
        edges = self._reads_config(payload)
        self.assertTrue(edges, f"no reads_config edge: {[e for e in payload.get('edges', []) if e.get('relation') != 'defines']}")
        e = edges[0]
        self.assertEqual(e.get("confidence"), "LITERAL_DERIVED", e)
        # Reader = the enclosing class node; a single basename-matching dominant
        # class (`Db` in `Db.java`) collapses into the file/module node, so the
        # surviving carrier is the file id rather than `Db.java::Db`.
        self.assertIn("Db.java", str(e.get("source", "")))
        self.assertIn("application.yml::spring.datasource.url", str(e.get("target", "")))

    def test_properties_getproperty_emits_reads_config_edge(self):
        payload = self._build({
            "src/main/resources/application.properties": (
                "aceiss.api.endpoint=https://api.example.com\n"
            ),
            "src/main/java/Client.java": (
                "class Client {\n"
                "  String resolve(org.springframework.core.env.Environment env) {\n"
                "    return env.getProperty(\"aceiss.api.endpoint\");\n"
                "  }\n"
                "}\n"
            ),
        })
        edges = self._reads_config(payload)
        self.assertTrue(edges, "no reads_config edge for getProperty read")
        self.assertIn("application.properties::aceiss.api.endpoint", str(edges[0].get("target", "")))

    def test_value_default_separator_key_extraction(self):
        # `${key:default}` → the key is the part before the ':' default separator.
        payload = self._build({
            "src/main/resources/application.yml": (
                "app:\n"
                "  retry:\n"
                "    count: 3\n"
            ),
            "src/main/java/Retry.java": (
                "class Retry {\n"
                "  @Value(\"${app.retry.count:5}\")\n"
                "  private int count;\n"
                "}\n"
            ),
        })
        edges = self._reads_config(payload)
        self.assertTrue(edges, "no reads_config edge for ${key:default}")
        self.assertIn("application.yml::app.retry.count", str(edges[0].get("target", "")))

    def test_unmatched_value_key_emits_no_edge(self):
        # FAITHFULNESS: a @Value placeholder with no matching config node → no edge.
        payload = self._build({
            "src/main/resources/application.yml": (
                "spring:\n"
                "  datasource:\n"
                "    url: x\n"
            ),
            "src/main/java/Db.java": (
                "class Db {\n"
                "  @Value(\"${unmatched.key.absent}\")\n"
                "  private String v;\n"
                "}\n"
            ),
        })
        self.assertEqual(self._reads_config(payload), [], "unmatched @Value key should emit no edge")

    def test_non_config_yaml_not_bound(self):
        # FAITHFULNESS: a `.yml` whose basename is not application/bootstrap/config/
        # profile is not a config surface — a coincidental key match must NOT bind.
        payload = self._build({
            "src/main/resources/fixtures.yml": (
                "spring:\n"
                "  datasource:\n"
                "    url: x\n"
            ),
            "src/main/java/Db.java": (
                "class Db {\n"
                "  @Value(\"${spring.datasource.url}\")\n"
                "  private String url;\n"
                "}\n"
            ),
        })
        self.assertEqual(self._reads_config(payload), [], "non-config .yml should not bind")


class OtelInstrumentsPropertyTests(unittest.TestCase):
    """1p7dh: OTel `TypeInstrumentation.typeMatcher()` ByteBuddy matcher target
    strings are captured as an `instruments` node PROPERTY on the instrumentation
    class (descriptive metadata, not an edge — the targets are third-party types
    by design). Method/parameter matchers in `transform()` are excluded."""

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

    def _instruments(self, payload):
        # Collect the `instruments` property wherever it landed (the carrier may
        # be the `::Class` node or, when the dominant class collapsed into it,
        # the file/module node).
        return {n["id"]: n["instruments"] for n in payload.get("nodes", []) if n.get("instruments")}

    def test_type_matcher_string_captured_as_instruments(self):
        payload = self._build({
            "src/FooInstrumentation.java": (
                "class FooInstrumentation {\n"
                "  public ElementMatcher typeMatcher() {\n"
                "    return named(\"org.hibernate.boot.Metadata\");\n"
                "  }\n"
                "}\n"
            ),
        })
        got = self._instruments(payload)
        self.assertEqual(list(got.values()), [["org.hibernate.boot.Metadata"]], got)

    def test_multiple_matchers_captured(self):
        payload = self._build({
            "src/Bar.java": (
                "class Bar {\n"
                "  public ElementMatcher typeMatcher() {\n"
                "    return named(\"a.b.Foo\").or(nameStartsWith(\"a.c\"));\n"
                "  }\n"
                "}\n"
            ),
        })
        got = self._instruments(payload)
        self.assertEqual(list(got.values()), [["a.b.Foo", "a.c"]], got)

    def test_transform_method_matcher_not_captured(self):
        # FAITHFULNESS scope: a matcher in transform() is a method-name matcher,
        # not a type target — it must NOT land in `instruments`.
        payload = self._build({
            "src/Baz.java": (
                "class Baz {\n"
                "  public ElementMatcher typeMatcher() {\n"
                "    return named(\"a.b.Target\");\n"
                "  }\n"
                "  public void transform(TypeTransformer t) {\n"
                "    t.applyAdviceToMethod(named(\"doStuff\"), \"AdviceClass\");\n"
                "  }\n"
                "}\n"
            ),
        })
        got = self._instruments(payload)
        self.assertEqual(list(got.values()), [["a.b.Target"]], f"transform() matcher leaked: {got}")

    def test_named_one_of_multi_arg_captured(self):
        # `namedOneOf("A","B")` carries multiple type targets — capture all.
        payload = self._build({
            "src/Multi.java": (
                "class Multi {\n"
                "  public ElementMatcher typeMatcher() {\n"
                "    return namedOneOf(\"a.b.Foo\", \"a.b.Bar\");\n"
                "  }\n"
                "}\n"
            ),
        })
        got = self._instruments(payload)
        self.assertEqual(list(got.values()), [["a.b.Bar", "a.b.Foo"]], got)

    def test_implements_interface_namedoneof_captured(self):
        # Neo4j shape: implementsInterface(namedOneOf(...)) — the inner namedOneOf
        # is a buffered call inside typeMatcher, so its strings are captured.
        payload = self._build({
            "src/Neo4jSecurityInstrumentation.java": (
                "class Neo4jSecurityInstrumentation {\n"
                "  public ElementMatcher typeMatcher() {\n"
                "    return implementsInterface(namedOneOf(\n"
                "        \"org.neo4j.server.security.auth.AuthenticationStrategy\",\n"
                "        \"org.neo4j.kernel.impl.query.QueryExecutionEngine\"));\n"
                "  }\n"
                "}\n"
            ),
        })
        got = self._instruments(payload)
        self.assertEqual(list(got.values()), [[
            "org.neo4j.kernel.impl.query.QueryExecutionEngine",
            "org.neo4j.server.security.auth.AuthenticationStrategy",
        ]], got)

    def test_has_super_type_namedoneof_captured(self):
        # Shopizer shape: hasSuperType(namedOneOf("...UserFacade")).
        payload = self._build({
            "src/ShopizerSecurityInstrumentation.java": (
                "class ShopizerSecurityInstrumentation {\n"
                "  public ElementMatcher typeMatcher() {\n"
                "    return hasSuperType(namedOneOf(\n"
                "        \"com.salesmanager.shop.store.controller.user.facade.UserFacade\"));\n"
                "  }\n"
                "}\n"
            ),
        })
        got = self._instruments(payload)
        self.assertEqual(list(got.values()), [[
            "com.salesmanager.shop.store.controller.user.facade.UserFacade",
        ]], got)


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
        from field validation), the class_declaration node remains intact
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

    The field reproducer: `oos.writeObject(...)` in `JdbcConnectionRegistry`
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

    # AC-2: field reproducer — oos.writeObject must NOT attribute to project JSON.writeObject.
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
    # 1p2q3 (1p2q9 C / 1p2tf / 1p2td) bumped 17→18 to invalidate consumer caches for the
    # .gen.ts classifier, cross-file receiver-type via imports, and self_edge_kind shape change.
    # 1p2q3 (1p2tz) bumped 18→19 to invalidate caches for the barrel re-export resolution
    # (method calls) + leading-@ specifier preservation.
    # 1p2q3 (1p2tz post-ship) bumped 19→20 to invalidate caches for the direct-function-call
    # import_targets promotion + bundler-mode .js→.ts extension swap.
    # 1p2q3 (1p2tz post-ship-2) bumped 20→21 to invalidate caches for arrow-const node registration
    # (`export const foo = () => {}` dominates modern TS; was never being emitted as a graph node).
    # 1p2q3 (1p2tz post-ship-5) bumped 22→23 to invalidate caches for TS/JS symbol-table
    # promotion — intra-file (and cross-file unique-simple-name) calls where
    # `_ts_resolve_target` bound directly to a project node now land as
    # RECEIVER_RESOLVED instead of EXTRACTED. Closes the v22 gap where
    # `getRootToken`-style intra-file arrow-const callers were invisible to
    # the `receiver_resolved` attribution bucket.
    def test_graph_builder_version_is_at_or_above_latest_bump(self):
        runtime = int(self.mod.GRAPH_BUILDER_VERSION)
        self.assertGreaterEqual(runtime, 23,
                                "GRAPH_BUILDER_VERSION must be ≥ 23 (wave 1p2q3 extractor-shape changes — "
                                "TS/JS symbol-table promotion of intra-file calls to RECEIVER_RESOLVED). "
                                "Bump in the same change as any future extractor-output shape modification.")


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

    # Wave 1p2q3 (1p2q9 C): JS/TS generated-file conventions.
    def test_tanstack_router_gen_ts_marks_generated(self):
        self.assertTrue(self._classify("apps/web/src/routeTree.gen.ts",
                                       "// Generated by TanStack Router\nexport const routeTree = {};"))

    def test_gen_tsx_suffix_marks_generated(self):
        self.assertTrue(self._classify("src/components/icons.gen.tsx",
                                       "export const Icon = () => null;"))

    def test_generated_ts_suffix_marks_generated(self):
        self.assertTrue(self._classify("src/api/schema.generated.ts",
                                       "export type Foo = { id: string };"))

    def test_generated_jsx_suffix_marks_generated(self):
        self.assertTrue(self._classify("src/forms/widgets.generated.jsx",
                                       "export const Widget = () => null;"))

    def test_underscore_generated_dir_marks_generated(self):
        self.assertTrue(self._classify("src/__generated__/types.ts", "export type T = number;"))

    def test_dot_generated_dir_marks_generated(self):
        self.assertTrue(self._classify("src/.generated/api.ts", "export const api = {};"))

    def test_handwritten_ts_not_marked(self):
        self.assertFalse(self._classify("src/components/Button.tsx",
                                        "export const Button = () => null;"))


class TsConfigPathAliasResolutionTests(unittest.TestCase):
    """Wave 1p2q3 (1p2q9 A): tsconfig.json `paths` alias resolution for TS imports."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.mod._TSCONFIG_PATHS_CACHE.clear()
        self.mod._TSCONFIG_DISCOVERY_CACHE.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_tsconfig(self, content, name="tsconfig.base.json"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            import json as _json
            path.write_text(_json.dumps(content), encoding="utf-8")
        return path

    def _touch(self, rel, content="// stub\n"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_strip_jsonc_comments_handles_line_and_block_comments(self):
        raw = """{
            // line comment
            "compilerOptions": {
                /* block comment */
                "paths": {"@a/*": ["libs/a/*"]},
                "url": "https://example.com",
            }
        }"""
        import json as _json
        data = _json.loads(self.mod._strip_jsonc_comments(raw))
        self.assertEqual(data["compilerOptions"]["paths"]["@a/*"], ["libs/a/*"])
        self.assertEqual(data["compilerOptions"]["url"], "https://example.com")

    def test_discover_tsconfig_base_preferred_over_tsconfig(self):
        self._write_tsconfig({"compilerOptions": {"paths": {"@a/*": ["libs/a/*"]}}}, "tsconfig.base.json")
        self._write_tsconfig({"compilerOptions": {}}, "tsconfig.json")
        src = self._touch("apps/web/src/main.ts")
        found = self.mod._discover_tsconfig_for_file(src, self.root)
        self.assertIsNotNone(found)
        self.assertTrue(found.endswith("tsconfig.base.json"))

    def test_wildcard_alias_resolves_to_real_file(self):
        self._write_tsconfig({"compilerOptions": {"baseUrl": ".", "paths": {"@scope/*": ["libs/*/src/index.ts"]}}})
        self._touch("libs/marketplace/src/index.ts", "export const f = 1;\n")
        src = self._touch("apps/web/src/main.ts")
        resolved = self.mod._resolve_ts_import_via_tsconfig("@scope/marketplace", str(src.relative_to(self.root)), self.root)
        self.assertEqual(resolved, "libs/marketplace/src/index.ts")

    def test_wildcard_alias_with_extension_probe(self):
        self._write_tsconfig({"compilerOptions": {"baseUrl": ".", "paths": {"@scope/*": ["libs/*"]}}})
        self._touch("libs/foo.ts", "export const x = 1;\n")
        src = self._touch("apps/web/src/main.ts")
        resolved = self.mod._resolve_ts_import_via_tsconfig("@scope/foo", str(src.relative_to(self.root)), self.root)
        self.assertEqual(resolved, "libs/foo.ts")

    def test_directory_alias_probes_index_file(self):
        self._write_tsconfig({"compilerOptions": {"baseUrl": ".", "paths": {"@scope/*": ["libs/*"]}}})
        self._touch("libs/marketplace/index.tsx", "export const x = 1;\n")
        src = self._touch("apps/web/src/main.ts")
        resolved = self.mod._resolve_ts_import_via_tsconfig("@scope/marketplace", str(src.relative_to(self.root)), self.root)
        self.assertEqual(resolved, "libs/marketplace/index.tsx")

    def test_exact_alias_resolves(self):
        self._write_tsconfig({"compilerOptions": {"baseUrl": ".", "paths": {"@scope/marketplace": ["libs/marketplace/src/index.ts"]}}})
        self._touch("libs/marketplace/src/index.ts", "export const f = 1;\n")
        src = self._touch("apps/web/src/main.ts")
        resolved = self.mod._resolve_ts_import_via_tsconfig("@scope/marketplace", str(src.relative_to(self.root)), self.root)
        self.assertEqual(resolved, "libs/marketplace/src/index.ts")

    def test_no_match_returns_none(self):
        self._write_tsconfig({"compilerOptions": {"baseUrl": ".", "paths": {"@scope/*": ["libs/*/src/index.ts"]}}})
        src = self._touch("apps/web/src/main.ts")
        self.assertIsNone(self.mod._resolve_ts_import_via_tsconfig("react", str(src.relative_to(self.root)), self.root))
        self.assertIsNone(self.mod._resolve_ts_import_via_tsconfig("@scope/missing", str(src.relative_to(self.root)), self.root))

    def test_relative_imports_skip_alias_resolution(self):
        self._write_tsconfig({"compilerOptions": {"baseUrl": ".", "paths": {"./local/*": ["libs/local/*"]}}})
        src = self._touch("apps/web/src/main.ts")
        self.assertIsNone(self.mod._resolve_ts_import_via_tsconfig("./helper", str(src.relative_to(self.root)), self.root))
        self.assertIsNone(self.mod._resolve_ts_import_via_tsconfig("../sibling", str(src.relative_to(self.root)), self.root))

    def test_baseurl_resolves_paths_relative_to_tsconfig(self):
        self._write_tsconfig({"compilerOptions": {"baseUrl": "./packages", "paths": {"@x/*": ["x/*"]}}})
        self._touch("packages/x/foo.ts", "export const y = 1;\n")
        src = self._touch("apps/web/main.ts")
        resolved = self.mod._resolve_ts_import_via_tsconfig("@x/foo", str(src.relative_to(self.root)), self.root)
        self.assertEqual(resolved, "packages/x/foo.ts")

    def test_no_paths_configured_returns_none(self):
        self._write_tsconfig({"compilerOptions": {}})
        src = self._touch("apps/web/src/main.ts")
        self.assertIsNone(self.mod._resolve_ts_import_via_tsconfig("@x/y", str(src.relative_to(self.root)), self.root))

    def test_malformed_tsconfig_returns_none(self):
        self._write_tsconfig("{ not json at all }}}")
        src = self._touch("apps/web/src/main.ts")
        self.assertIsNone(self.mod._resolve_ts_import_via_tsconfig("@x/y", str(src.relative_to(self.root)), self.root))

    def test_results_cached_per_tsconfig(self):
        self._write_tsconfig({"compilerOptions": {"baseUrl": ".", "paths": {"@a/*": ["libs/*"]}}})
        self._touch("libs/foo.ts", "export const x = 1;\n")
        src = self._touch("apps/web/src/main.ts")
        self.mod._resolve_ts_import_via_tsconfig("@a/foo", str(src.relative_to(self.root)), self.root)
        self.assertEqual(len(self.mod._TSCONFIG_PATHS_CACHE), 1)
        self.assertEqual(len(self.mod._TSCONFIG_DISCOVERY_CACHE), 1)
        src2 = self._touch("apps/api/src/main.ts")
        self.mod._resolve_ts_import_via_tsconfig("@a/foo", str(src2.relative_to(self.root)), self.root)
        self.assertEqual(len(self.mod._TSCONFIG_PATHS_CACHE), 1)
        self.assertEqual(len(self.mod._TSCONFIG_DISCOVERY_CACHE), 2)


class OverloadSelfEdgeClassificationTests(unittest.TestCase):
    """Wave 1p2q3 (1p2td): self-edge classification for overloaded methods.

    A self-edge on a per-file qname-merged overload node is tagged as either
    `recursion` (call signature matches enclosing overload), `overload_forwarding`
    (call signature matches a different overload registered on the same node),
    or `unknown` (signatures missing or ambiguous).
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

    def _self_edges(self, payload):
        return [
            e for e in payload.get("edges", [])
            if e.get("relation") == "calls" and e.get("source") == e.get("target")
        ]

    # AC-2/3: Swift label-fingerprint case (field reproducer).
    def test_swift_overload_forwarding_classified_as_overload_forwarding(self):
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available")
        # 3-param convenience overload forwards to 4-param implementation.
        files = {
            "Controller.swift": (
                "class Controller {\n"
                "  func calc(base: Int, offset: Int, custom: Int) -> Int {\n"
                "    return calc(base: base, offset: offset, custom: custom, roll: true)\n"
                "  }\n"
                "  func calc(base: Int, offset: Int, custom: Int, roll: Bool) -> Int {\n"
                "    return base + offset + custom\n"
                "  }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        self_edges = self._self_edges(payload)
        # The 3-param overload's forwarding call is a self-edge after merge.
        forwarding = [e for e in self_edges if e.get("self_edge_kind") == "overload_forwarding"]
        self.assertTrue(
            forwarding,
            f"expected an overload_forwarding self-edge; got self-edges: {self_edges}",
        )

    def test_swift_recursion_classified_as_recursion(self):
        try:
            import tree_sitter_swift  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_swift not available")
        # Same-signature recursive call.
        files = {
            "Rec.swift": (
                "class Rec {\n"
                "  func loop(n: Int) -> Int {\n"
                "    if n <= 0 { return 0 }\n"
                "    return loop(n: n - 1) + 1\n"
                "  }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        self_edges = self._self_edges(payload)
        recursion = [e for e in self_edges if e.get("self_edge_kind") == "recursion"]
        self.assertTrue(
            recursion,
            f"expected a recursion self-edge; got self-edges: {self_edges}",
        )

    # AC-4/5: Java arity-fingerprint cases.
    def test_java_overload_forwarding_classified_as_overload_forwarding(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available")
        files = {
            "src/Calc.java": (
                "class Calc {\n"
                "    int calc(int a, int b) { return calc(a, b, 0); }\n"
                "    int calc(int a, int b, int c) { return a + b + c; }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        self_edges = self._self_edges(payload)
        forwarding = [e for e in self_edges if e.get("self_edge_kind") == "overload_forwarding"]
        self.assertTrue(
            forwarding,
            f"expected an overload_forwarding self-edge; got self-edges: {self_edges}",
        )

    def test_java_recursion_classified_as_recursion(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available")
        files = {
            "src/Rec.java": (
                "class Rec {\n"
                "    int loop(int n) {\n"
                "        if (n <= 0) return 0;\n"
                "        return loop(n - 1) + 1;\n"
                "    }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        self_edges = self._self_edges(payload)
        recursion = [e for e in self_edges if e.get("self_edge_kind") == "recursion"]
        self.assertTrue(
            recursion,
            f"expected a recursion self-edge; got self-edges: {self_edges}",
        )

    # AC-7: non-overloading language → no field added.
    def test_python_self_edge_carries_no_self_edge_kind(self):
        # Python isn't in _OVERLOAD_LANGUAGES — self-edge stays bare.
        files = {
            "src/rec.py": (
                "def loop(n):\n"
                "    if n <= 0:\n"
                "        return 0\n"
                "    return loop(n - 1) + 1\n"
            ),
        }
        payload = self._build(files)
        self_edges = self._self_edges(payload)
        for e in self_edges:
            self.assertNotIn(
                "self_edge_kind", e,
                f"non-overloading languages must not gain self_edge_kind; got: {e}",
            )

    # AC-8: param_signatures on the merged node.
    def test_param_signatures_attached_to_merged_overload_node(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available")
        files = {
            "src/Calc.java": (
                "class Calc {\n"
                "    int calc(int a) { return 1; }\n"
                "    int calc(int a, int b) { return 2; }\n"
                "    int calc(int a, int b, int c) { return 3; }\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calc_nodes = [n for n in payload.get("nodes", []) if n.get("id", "").endswith("::Calc.calc")]
        self.assertTrue(calc_nodes, "expected Calc.calc node in payload")
        sigs = calc_nodes[0].get("param_signatures") or []
        # Three overloads with arity 1/2/3.
        self.assertEqual(sorted(sigs), ["arity:1", "arity:2", "arity:3"])


class TsImportedNameExtractionTests(unittest.TestCase):
    """Wave 1p2q3 (1p2tf): _ts_extract_imported_names handles named, default,
    namespace, type-only, and aliased import shapes."""

    def setUp(self):
        try:
            import tree_sitter_typescript  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_typescript not available")
        self.mod = load_graph_indexer()

    def _parse_imports(self, source: str):
        import tree_sitter_typescript
        from tree_sitter import Language, Parser
        lang = Language(tree_sitter_typescript.language_typescript())
        parser = Parser(lang)
        tree = parser.parse(source.encode("utf-8"))
        nodes = []
        def walk(n):
            if n.type == "import_statement":
                nodes.append(n)
            for c in n.children:
                walk(c)
        walk(tree.root_node)
        return nodes, source.encode("utf-8")

    def test_named_import_extracts_each_name(self):
        nodes, src = self._parse_imports("import { Foo, Bar } from '@a/b';")
        self.assertEqual(self.mod._ts_extract_imported_names(nodes[0], src), ["Foo", "Bar"])

    def test_default_import_extracts_default_name(self):
        nodes, src = self._parse_imports("import Default from './x';")
        self.assertEqual(self.mod._ts_extract_imported_names(nodes[0], src), ["Default"])

    def test_namespace_import_extracts_namespace_name(self):
        nodes, src = self._parse_imports("import * as Util from './u';")
        self.assertEqual(self.mod._ts_extract_imported_names(nodes[0], src), ["Util"])

    def test_type_only_named_import_extracts_name(self):
        nodes, src = self._parse_imports("import type { Foo } from '@a/b';")
        self.assertEqual(self.mod._ts_extract_imported_names(nodes[0], src), ["Foo"])

    def test_aliased_named_import_uses_local_alias(self):
        nodes, src = self._parse_imports("import { Foo as F } from '@a/b';")
        self.assertEqual(self.mod._ts_extract_imported_names(nodes[0], src), ["F"])

    def test_combined_default_plus_named_extracts_both(self):
        nodes, src = self._parse_imports("import Def, { Foo, Bar } from '@a/b';")
        names = self.mod._ts_extract_imported_names(nodes[0], src)
        self.assertIn("Def", names)
        self.assertIn("Foo", names)
        self.assertIn("Bar", names)

    def test_side_effect_import_returns_empty(self):
        nodes, src = self._parse_imports("import './polyfill';")
        self.assertEqual(self.mod._ts_extract_imported_names(nodes[0], src), [])


class TsReceiverTypeViaImportsTests(unittest.TestCase):
    """Wave 1p2q3 (1p2tf): receiver-type resolution via tsconfig.paths-resolved
    imports. The Nx monorepo case — imported types on aliased specifiers must
    bind cross-package calls to project nodes with RECEIVER_RESOLVED confidence."""

    def setUp(self):
        try:
            import tree_sitter_typescript  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_typescript not available")
        self.mod = load_graph_indexer()
        self.mod._TSCONFIG_PATHS_CACHE.clear()
        self.mod._TSCONFIG_DISCOVERY_CACHE.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
        # Synthetic Nx-shaped layout with tsconfig.base.json.
        (self.root / "tsconfig.base.json").write_text(
            '{"compilerOptions": {"baseUrl": ".", "paths": {"@scope/*": ["libs/*/src/index.ts"]}}}',
            encoding="utf-8",
        )

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

    def test_aliased_import_call_resolves_to_project_with_receiver_resolved(self):
        files = {
            "libs/lib/src/index.ts": (
                "export class Foo {\n"
                "  bar(): number { return 1; }\n"
                "}\n"
            ),
            "apps/web/src/main.ts": (
                "import { Foo } from '@scope/lib';\n"
                "export function caller(foo: Foo): number {\n"
                "  return foo.bar();\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # Expect a RECEIVER_RESOLVED edge from caller → libs/lib/src/index.ts::Foo.bar
        receiver_edges = [
            e for e in calls
            if e.get("confidence") == "RECEIVER_RESOLVED"
            and e.get("target") == "libs/lib/src/index.ts::Foo.bar"
        ]
        self.assertTrue(
            receiver_edges,
            f"expected RECEIVER_RESOLVED edge to project Foo.bar; got calls: {calls}",
        )

    def test_external_import_does_not_get_promoted(self):
        # `react` doesn't have a paths alias and there's no `react` file on disk;
        # the receiver type must stay external::*.
        files = {
            "apps/web/src/main.ts": (
                "import React from 'react';\n"
                "export function caller(r: React): string {\n"
                "  return r.useState();\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = self._calls(payload)
        # No edge should target a project node for React.useState.
        for e in calls:
            target = str(e.get("target") or "")
            self.assertFalse(
                target.endswith("React.useState") and not target.startswith("external::"),
                f"react should stay external; got: {e}",
            )

    def test_nx_project_detected_when_nx_json_present(self):
        (self.root / "nx.json").write_text('{"version": "1.0.0"}', encoding="utf-8")
        files = {
            "apps/web/src/main.ts": "export const x = 1;\n",
        }
        payload = self._build(files)
        self.assertTrue(payload.get("nx_project_detected"))

    def test_nx_project_not_detected_without_nx_json(self):
        files = {
            "apps/web/src/main.ts": "export const x = 1;\n",
        }
        payload = self._build(files)
        self.assertFalse(payload.get("nx_project_detected", False))

    def test_attribution_counts_receiver_resolved_gt_zero_on_nx_fixture(self):
        files = {
            "libs/lib/src/index.ts": (
                "export class Foo {\n"
                "  bar(): number { return 1; }\n"
                "}\n"
            ),
            "apps/web/src/main.ts": (
                "import { Foo } from '@scope/lib';\n"
                "export function caller(foo: Foo): number { return foo.bar(); }\n"
            ),
        }
        payload = self._build(files)
        # Count receiver-resolved TS edges in the merged payload.
        receiver_resolved = sum(
            1 for e in payload.get("edges", [])
            if e.get("relation") == "calls"
            and e.get("confidence") == "RECEIVER_RESOLVED"
            and str(e.get("source") or "").endswith(".ts::caller")
        )
        self.assertGreater(
            receiver_resolved, 0,
            f"expected at least one RECEIVER_RESOLVED TS edge; got 0",
        )


class TsBarrelReExportResolutionTests(unittest.TestCase):
    """Wave 1p2q3 (1p2tz): barrel re-export following. tsconfig.paths aliases
    on Nx-shaped monorepos point at `src/index.ts` barrels that re-export from
    `./lib/<name>`. The receiver-type resolver must walk through the barrel
    chain so import_targets points at the actual definition file, not the
    barrel index.

    Per a field configuration supplement: every alias in the tsconfig.base.json
    resolves to a single-file barrel; the dominant Nx pattern.
    """

    def setUp(self):
        try:
            import tree_sitter_typescript  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_typescript not available")
        self.mod = load_graph_indexer()
        self.mod._TSCONFIG_PATHS_CACHE.clear()
        self.mod._TSCONFIG_DISCOVERY_CACHE.clear()
        self.mod._TS_BARREL_PARSE_CACHE.clear()
        self.mod._TS_BARREL_WILDCARDS_CACHE.clear()
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

    # Helper unit tests for the resolver itself.

    def test_parse_barrel_named_reexport(self):
        barrel = self.root / "lib" / "index.ts"
        barrel.parent.mkdir(parents=True, exist_ok=True)
        barrel.write_text("export { Foo, Bar } from './impl';\n", encoding="utf-8")
        named, wildcards = self.mod._parse_barrel(barrel)
        self.assertEqual(named, {"Foo": "./impl", "Bar": "./impl"})
        self.assertEqual(wildcards, [])

    def test_parse_barrel_renamed_reexport(self):
        barrel = self.root / "lib" / "index.ts"
        barrel.parent.mkdir(parents=True, exist_ok=True)
        barrel.write_text("export { Foo as Bar } from './impl';\n", encoding="utf-8")
        named, _ = self.mod._parse_barrel(barrel)
        self.assertEqual(named, {"Bar": "./impl"})

    def test_parse_barrel_default_reexport(self):
        barrel = self.root / "lib" / "index.ts"
        barrel.parent.mkdir(parents=True, exist_ok=True)
        barrel.write_text("export { default as Foo } from './impl';\n", encoding="utf-8")
        named, _ = self.mod._parse_barrel(barrel)
        self.assertEqual(named, {"Foo": "./impl"})

    def test_parse_barrel_wildcard_reexport(self):
        barrel = self.root / "lib" / "index.ts"
        barrel.parent.mkdir(parents=True, exist_ok=True)
        barrel.write_text("export * from './types';\nexport * from './utils';\n", encoding="utf-8")
        _, wildcards = self.mod._parse_barrel(barrel)
        self.assertEqual(sorted(wildcards), ["./types", "./utils"])

    def test_parse_barrel_cache_keyed_on_mtime(self):
        barrel = self.root / "lib" / "index.ts"
        barrel.parent.mkdir(parents=True, exist_ok=True)
        barrel.write_text("export { Foo } from './a';\n", encoding="utf-8")
        n1, _ = self.mod._parse_barrel(barrel)
        # Cache populated.
        self.assertGreater(
            len([k for k in self.mod._TS_BARREL_PARSE_CACHE if not (isinstance(k, tuple) and len(k) == 3)]),
            0,
        )
        n2, _ = self.mod._parse_barrel(barrel)
        self.assertEqual(n1, n2)

    def test_resolve_through_barrel_named_chain(self):
        # Two-hop chain: index.ts -> lib/impl.ts (declares Foo)
        (self.root / "libs" / "utils" / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "libs" / "utils" / "src" / "index.ts").write_text(
            "export { Foo } from './lib/impl';\n", encoding="utf-8",
        )
        (self.root / "libs" / "utils" / "src" / "lib").mkdir(parents=True, exist_ok=True)
        (self.root / "libs" / "utils" / "src" / "lib" / "impl.ts").write_text(
            "export class Foo { bar() {} }\n", encoding="utf-8",
        )
        result = self.mod._resolve_through_barrel(
            "Foo", "libs/utils/src/index.ts", self.root,
        )
        self.assertEqual(result, "libs/utils/src/lib/impl.ts")

    def test_resolve_through_barrel_renamed_chain(self):
        # Imported as Bar locally, exported by impl.ts as Foo.
        (self.root / "libs" / "utils" / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "libs" / "utils" / "src" / "index.ts").write_text(
            "export { Foo as Bar } from './lib/impl';\n", encoding="utf-8",
        )
        (self.root / "libs" / "utils" / "src" / "lib").mkdir(parents=True, exist_ok=True)
        (self.root / "libs" / "utils" / "src" / "lib" / "impl.ts").write_text(
            "export class Foo { bar() {} }\n", encoding="utf-8",
        )
        # Caller imports Bar; resolver should land on impl.ts (where Foo lives).
        result = self.mod._resolve_through_barrel(
            "Bar", "libs/utils/src/index.ts", self.root,
        )
        self.assertEqual(result, "libs/utils/src/lib/impl.ts")

    def test_resolve_through_barrel_wildcard_finds_declaration(self):
        (self.root / "libs" / "utils" / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "libs" / "utils" / "src" / "index.ts").write_text(
            "export * from './lib/types';\n", encoding="utf-8",
        )
        (self.root / "libs" / "utils" / "src" / "lib").mkdir(parents=True, exist_ok=True)
        (self.root / "libs" / "utils" / "src" / "lib" / "types.ts").write_text(
            "export interface Foo { bar: string; }\n", encoding="utf-8",
        )
        result = self.mod._resolve_through_barrel(
            "Foo", "libs/utils/src/index.ts", self.root,
        )
        self.assertEqual(result, "libs/utils/src/lib/types.ts")

    def test_resolve_through_barrel_no_declaration_falls_back_to_barrel(self):
        (self.root / "libs" / "utils" / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "libs" / "utils" / "src" / "index.ts").write_text(
            "// no re-exports here\n", encoding="utf-8",
        )
        result = self.mod._resolve_through_barrel(
            "Foo", "libs/utils/src/index.ts", self.root,
        )
        # Falls back to barrel since no chain leads to a declaration.
        self.assertEqual(result, "libs/utils/src/index.ts")

    def test_resolve_through_barrel_cycle_detection(self):
        # Set up a cycle: a/index.ts re-exports from ../b, b/index.ts re-exports from ../a.
        (self.root / "a").mkdir(parents=True, exist_ok=True)
        (self.root / "a" / "index.ts").write_text(
            "export { Foo } from '../b';\n", encoding="utf-8",
        )
        (self.root / "b").mkdir(parents=True, exist_ok=True)
        (self.root / "b" / "index.ts").write_text(
            "export { Foo } from '../a';\n", encoding="utf-8",
        )
        # Should terminate without infinite loop.
        result = self.mod._resolve_through_barrel("Foo", "a/index.ts", self.root)
        # Falls back to one of the barrels — either is acceptable, just must not hang.
        self.assertIn(result, ("a/index.ts", "b/index.ts"))

    # End-to-end Nx-shaped fixture mirroring a field tsconfig.paths layout.

    def test_aliased_import_through_barrel_resolves_to_definition_file(self):
        (self.root / "tsconfig.base.json").write_text(
            '{"compilerOptions": {"baseUrl": ".", "paths": {"@scope/utils": ["libs/utils/src/index.ts"]}}}',
            encoding="utf-8",
        )
        files = {
            "libs/utils/src/index.ts": (
                "export { HttpRequest } from './lib/http-request';\n"
            ),
            "libs/utils/src/lib/http-request.ts": (
                "export class HttpRequest {\n"
                "  send(): number { return 1; }\n"
                "}\n"
            ),
            "apps/web/src/main.ts": (
                "import { HttpRequest } from '@scope/utils';\n"
                "export function caller(h: HttpRequest): number {\n"
                "  return h.send();\n"
                "}\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        # Expect a RECEIVER_RESOLVED edge targeting the DEFINITION file, not the barrel.
        definition_edges = [
            e for e in calls
            if e.get("confidence") == "RECEIVER_RESOLVED"
            and e.get("target") == "libs/utils/src/lib/http-request.ts::HttpRequest.send"
        ]
        self.assertTrue(
            definition_edges,
            f"expected RECEIVER_RESOLVED edge through barrel to definition file; got calls: "
            f"{[(e.get('source'), e.get('target'), e.get('confidence')) for e in calls]}",
        )
        # Negative: NO edge should target the barrel directly for this call.
        for e in definition_edges:
            self.assertNotEqual(e.get("target"), "libs/utils/src/index.ts::HttpRequest.send")

    def test_intra_package_relative_import_arrow_const_resolves(self):
        """Wave 1p2q3 (1p2tz post-ship-3 per field v22 prediction): intra-package
        callers using relative imports (`./events`) to call arrow-const-bound
        functions must land RECEIVER_RESOLVED at the definition file. Before
        this fix, the relative-path prefix was lost in `_ts_clean_name`, the
        resolver couldn't tell `./events` apart from `events`, so import_targets
        ended up as `external::events`. The cross-file rewrite pass then
        promoted the edge to the right project node but kept it at EXTRACTED.

        This is the load-bearing case for the 9,379 EXTRACTED edges
        observed in 1.3.11 — intra-package direct calls to arrow-const targets.
        """
        files = {
            "libs/backend/src/lib/events.ts": (
                "export const getRootApp = async (): Promise<number> => { return 1; };\n"
            ),
            "libs/backend/src/lib/caller.ts": (
                "import { getRootApp } from './events';\n"
                "export const callerFn = async (): Promise<number> => { return await getRootApp(); };\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        receiver_edges = [
            e for e in calls
            if e.get("confidence") == "RECEIVER_RESOLVED"
            and e.get("target") == "libs/backend/src/lib/events.ts::getRootApp"
        ]
        self.assertTrue(
            receiver_edges,
            f"expected RECEIVER_RESOLVED edge for intra-package relative-import call to "
            f"arrow-const target; got: {calls}",
        )

    def test_parent_relative_import_arrow_const_resolves(self):
        """Cover `../parent` relative imports too."""
        files = {
            "libs/backend/src/lib/utils/helper.ts": (
                "export const helper = (): number => 1;\n"
            ),
            "libs/backend/src/lib/handlers/main.ts": (
                "import { helper } from '../utils/helper';\n"
                "export const handler = (): number => helper();\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        receiver_edges = [
            e for e in calls
            if e.get("confidence") == "RECEIVER_RESOLVED"
            and e.get("target") == "libs/backend/src/lib/utils/helper.ts::helper"
        ]
        self.assertTrue(
            receiver_edges,
            f"expected RECEIVER_RESOLVED on parent-relative import; got: {calls}",
        )

    def test_extract_import_module_specifier_preserves_dot_prefix(self):
        """The raw-spec helper must preserve `./` and `../` prefixes that
        `_ts_clean_name` strips."""
        try:
            import tree_sitter_typescript  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_typescript not available")
        from tree_sitter import Language, Parser
        import tree_sitter_typescript
        lang = Language(tree_sitter_typescript.language_typescript())
        parser = Parser(lang)
        cases = [
            ("import { x } from './foo';", "./foo"),
            ("import { x } from '../bar/baz';", "../bar/baz"),
            ("import { x } from '@scope/pkg';", "@scope/pkg"),
            ('import { x } from "double-quote";', "double-quote"),
            ("import './side-effect';", "./side-effect"),
        ]
        for source, expected in cases:
            tree = parser.parse(source.encode("utf-8"))
            import_node = None
            for child in tree.root_node.children:
                if child.type == "import_statement":
                    import_node = child
                    break
            self.assertIsNotNone(import_node, f"no import_statement found in {source!r}")
            spec = self.mod._ts_extract_import_module_specifier(import_node, source.encode("utf-8"))
            self.assertEqual(spec, expected, f"raw spec for {source!r}")

    def test_arrow_const_registers_as_function_node(self):
        """Wave 1p2q3 (1p2tz post-ship-2 per field validation): modern
        TS code uses `export const foo = async (args) => { ... }` as the
        dominant function shape. The field smoke test confirmed all three
        target symbols (getRootApplicationForInstallation, setupCognitoUser,
        findOrCreateUserPool) are arrow-const and zero were registered as
        graph nodes on 1.3.10. This test guards the fix end-to-end.
        """
        files = {
            "libs/backend/events.ts": (
                "export const getRootApplicationForInstallation = async (i: any) => { return null; };\n"
                "export const setupCognitoUser = async (i: any) => { return null; };\n"
                "export const findOrCreateUserPool = async () => { return null; };\n"
            ),
        }
        payload = self._build(files)
        node_ids = {n.get("id") for n in payload.get("nodes", [])}
        for name in (
            "getRootApplicationForInstallation",
            "setupCognitoUser",
            "findOrCreateUserPool",
        ):
            expected = f"libs/backend/events.ts::{name}"
            self.assertIn(
                expected, node_ids,
                f"arrow-const symbol {name!r} must register as a graph node",
            )
            # Verify it's registered as kind=function, not kind=variable.
            for n in payload.get("nodes", []):
                if n.get("id") == expected:
                    self.assertEqual(n.get("kind"), "function")
                    break

    def test_arrow_const_function_expression_also_registers(self):
        """Cover the second canonical form: `const X = function() { ... }`."""
        files = {
            "libs/utils/helpers.ts": (
                "export const computeTotal = function(items: number[]): number {\n"
                "  return items.reduce((a, b) => a + b, 0);\n"
                "};\n"
            ),
        }
        payload = self._build(files)
        node_ids = {n.get("id") for n in payload.get("nodes", [])}
        self.assertIn("libs/utils/helpers.ts::computeTotal", node_ids)

    def test_arrow_const_call_inside_attributes_to_const_name(self):
        """Calls FROM inside an arrow-const-bound function should attribute to
        the const name (not the file), so the caller side of the edge is the
        expected symbol when reviewers run code_callhierarchy."""
        files = {
            "libs/svc/index.ts": (
                "export const helperFunc = (): number => { return 1; };\n"
                "export const callerFunc = (): number => { return helperFunc(); };\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        caller_edges = [
            e for e in calls
            if e.get("source") == "libs/svc/index.ts::callerFunc"
        ]
        self.assertTrue(
            caller_edges,
            f"expected `calls` edge sourced at libs/svc/index.ts::callerFunc; got: {calls}",
        )

    def test_intra_file_arrow_const_call_lands_receiver_resolved(self):
        """Wave 1p2q3 (1p2tz post-ship-5 per field v22 stable-state data):
        an intra-file caller of an arrow-const-bound function must produce a
        RECEIVER_RESOLVED edge. The pre-fix code resolved the target correctly
        (`_ts_resolve_target` returned the local symbol id via symbol_lookup)
        but tagged the edge as EXTRACTED — making it invisible to the
        `receiver_resolved` attribution bucket. A `getRootToken` field case had 5
        incoming intra-file callers all landing as EXTRACTED; this test guards
        the promotion."""
        files = {
            "libs/svc/auth.ts": (
                "export const getRootToken = (): string => { return 'tok'; };\n"
                "export const caller1 = (): string => getRootToken();\n"
                "export const caller2 = async (): Promise<string> => await getRootToken();\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        token_edges = [
            e for e in calls
            if e.get("target") == "libs/svc/auth.ts::getRootToken"
        ]
        self.assertTrue(
            token_edges,
            f"expected call edges targeting libs/svc/auth.ts::getRootToken; got: {calls}",
        )
        for e in token_edges:
            self.assertEqual(
                e.get("confidence"), "RECEIVER_RESOLVED",
                f"intra-file arrow-const call must land RECEIVER_RESOLVED, "
                f"not {e.get('confidence')!r}; edge: {e}",
            )

    def test_cross_file_unique_simple_name_call_lands_receiver_resolved(self):
        """The same promotion applies when `symbol_lookup` resolves a unique
        cross-file simple-name match at extraction time. The walker populates
        symbol_lookup from `simple_names` entries with `len(items) == 1`, so
        unambiguous cross-file bare-identifier calls bind directly during
        extraction (not via the cross-file rewrite pass). Confidence must be
        RECEIVER_RESOLVED in that case too."""
        files = {
            "libs/util/format.ts": (
                "export const uniqueFormatterX = (n: number): string => String(n);\n"
            ),
            "libs/app/main.ts": (
                "export const useFormatter = (n: number): string => uniqueFormatterX(n);\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        target_edges = [
            e for e in calls
            if e.get("target") == "libs/util/format.ts::uniqueFormatterX"
            and e.get("source") == "libs/app/main.ts::useFormatter"
        ]
        self.assertTrue(
            target_edges,
            f"expected cross-file unique-simple-name binding edge; got: {calls}",
        )
        self.assertEqual(
            target_edges[0].get("confidence"), "RECEIVER_RESOLVED",
            f"unique cross-file simple-name match must land RECEIVER_RESOLVED; "
            f"got {target_edges[0]}",
        )

    def test_direct_function_call_through_barrel_resolves_to_definition(self):
        """Wave 1p2q3 (1p2tz post-ship): direct function-call dispatch through
        an aliased barrel must produce a RECEIVER_RESOLVED edge at the
        definition file. Per field validation on 1.3.9: barrel method-
        call resolution worked but free-function calls (the majority of
        aliased imports on real codebases) still dropped to external::*.
        """
        (self.root / "tsconfig.base.json").write_text(
            '{"compilerOptions": {"baseUrl": ".", "paths": {"@scope/utils": ["libs/utils/src/index.ts"]}}}',
            encoding="utf-8",
        )
        files = {
            "libs/utils/src/index.ts": (
                "export { httpRequester } from './lib/http-request';\n"
            ),
            "libs/utils/src/lib/http-request.ts": (
                "export function httpRequester(url: string): number { return 1; }\n"
            ),
            "apps/web/src/main.ts": (
                "import { httpRequester } from '@scope/utils';\n"
                "export function caller(): number { return httpRequester('https://x.com'); }\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        receiver_edges = [
            e for e in calls
            if e.get("confidence") == "RECEIVER_RESOLVED"
            and e.get("target") == "libs/utils/src/lib/http-request.ts::httpRequester"
        ]
        self.assertTrue(
            receiver_edges,
            f"expected RECEIVER_RESOLVED edge for direct-function call through barrel; got calls: "
            f"{[(e.get('source'), e.get('target'), e.get('confidence')) for e in calls]}",
        )

    def test_bundler_mode_dot_js_extension_resolves_to_dot_ts(self):
        """Wave 1p2q3 (1p2tz post-ship): TS bundler-mode (TS 5.x) allows source
        to write `./foo.js` and have it resolve to `./foo.ts` at compile time.
        Barrel re-exports written this way must still walk through to the
        definition file.
        """
        (self.root / "tsconfig.base.json").write_text(
            '{"compilerOptions": {"baseUrl": ".", "paths": {"@scope/lib": ["libs/lib/src/index.ts"]}}}',
            encoding="utf-8",
        )
        files = {
            # Barrel uses .js extension; actual file is .ts (bundler-mode).
            "libs/lib/src/index.ts": (
                "export { Worker } from './lib/worker.js';\n"
            ),
            "libs/lib/src/lib/worker.ts": (
                "export class Worker { run(): number { return 1; } }\n"
            ),
            "apps/web/src/main.ts": (
                "import { Worker } from '@scope/lib';\n"
                "export function caller(w: Worker): number { return w.run(); }\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        receiver_edges = [
            e for e in calls
            if e.get("confidence") == "RECEIVER_RESOLVED"
            and e.get("target") == "libs/lib/src/lib/worker.ts::Worker.run"
        ]
        self.assertTrue(
            receiver_edges,
            f"expected bundler-mode .js→.ts resolution; got calls: {calls}",
        )

    def test_alias_collision_both_resolve_to_same_definition(self):
        # Per field supplement: @scope/hooks and @acme/hooks both map to libs/hooks/src/index.ts.
        (self.root / "tsconfig.base.json").write_text(
            '{"compilerOptions": {"baseUrl": ".", "paths": {'
            '"@scope/hooks": ["libs/hooks/src/index.ts"],'
            '"@acme/hooks":  ["libs/hooks/src/index.ts"]'
            '}}}',
            encoding="utf-8",
        )
        files = {
            "libs/hooks/src/index.ts": (
                "export { UseSession } from './lib/use-session';\n"
            ),
            "libs/hooks/src/lib/use-session.ts": (
                "export class UseSession { compute(): number { return 1; } }\n"
            ),
            "apps/scope/src/main.ts": (
                "import { UseSession } from '@scope/hooks';\n"
                "export function scopeCaller(u: UseSession): number { return u.compute(); }\n"
            ),
            "apps/acme/src/main.ts": (
                "import { UseSession } from '@acme/hooks';\n"
                "export function acmeCaller(u: UseSession): number { return u.compute(); }\n"
            ),
        }
        payload = self._build(files)
        calls = [e for e in payload.get("edges", []) if e.get("relation") == "calls"]
        # Both callers should land receiver-resolved edges at the same definition file.
        targets = [
            e.get("target") for e in calls
            if e.get("confidence") == "RECEIVER_RESOLVED"
            and "UseSession.compute" in str(e.get("target") or "")
        ]
        self.assertTrue(targets, f"expected RECEIVER_RESOLVED edges from both aliases; got calls: {calls}")
        # Every receiver-resolved edge for UseSession.compute must land at the same file.
        for t in targets:
            self.assertEqual(t, "libs/hooks/src/lib/use-session.ts::UseSession.compute")


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


class ParallelExtractionSpawnModeTests(unittest.TestCase):
    """Wave 1p2q3 (1p2wd / Bug 4): parallel extraction uses spawn start
    method + worker initializer that registers `graph_indexer` in each
    worker's sys.modules before task unpickling. These tests verify the
    wiring (start method + initializer args) and the initializer's effect.
    The full end-to-end pool spawn is exercised by AC-1's manual
    `build_pack --version <next>` validation step rather than by unit
    tests, because spawning real worker subprocesses materially slows the
    suite for low marginal value (the wiring tests already pin the
    contract).
    """

    def setUp(self):
        self.mod = load_graph_indexer()

    def test_worker_initializer_registers_graph_indexer_in_sys_modules(self):
        """AC-3: the initializer registers `graph_indexer` under that
        canonical name so spawn-mode workers can unpickle the function
        reference `graph_indexer._extract_artifact_for_worker`."""
        import importlib.util as _iu
        import sys as _sys
        graph_indexer_path = str(
            Path(self.mod.__file__).resolve()
            if hasattr(self.mod, "__file__") and self.mod.__file__
            else Path(__file__).resolve().parents[1] / "graph_indexer.py"
        )
        # Snapshot whatever's currently registered (the test runs after
        # load_graph_indexer, which uses a uniquified module name) and
        # restore afterwards so we don't leak state into sibling tests.
        prior = _sys.modules.pop("graph_indexer", None)
        try:
            self.mod._worker_init_graph_indexer(graph_indexer_path)
            self.assertIn("graph_indexer", _sys.modules,
                          "initializer must register the module under the canonical 'graph_indexer' name")
            registered = _sys.modules["graph_indexer"]
            # The registered module must expose the worker entry point so
            # `pool.map(_extract_artifact_for_worker, ...)` unpickling finds it.
            self.assertTrue(hasattr(registered, "_extract_artifact_for_worker"),
                            "registered module lacks _extract_artifact_for_worker — "
                            "unpickling in workers will fail")
            self.assertTrue(callable(registered._extract_artifact_for_worker))
        finally:
            if prior is None:
                _sys.modules.pop("graph_indexer", None)
            else:
                _sys.modules["graph_indexer"] = prior

    def test_auto_scale_worker_count_tiers(self):
        """Wave 1p2q3 (1p2wd post-ship 1.3.30): worker-count auto-scale tiers
        by file count when `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` is not set.
        Pin the breakpoints + the full-P-cores cap so a future inadvertent
        change shows up."""
        from unittest.mock import patch
        # Force override-None, simulate an 8-P-core machine so the cap
        # equals 8 P-cores and only binds in the ≥500 tier.
        with patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", None), \
             patch.object(self.mod, "_physical_perf_core_count", return_value=8), \
             patch("os.cpu_count", return_value=8):
            # Below 200 files: 2 workers
            self.assertEqual(self.mod._auto_scale_worker_count(0), 2)
            self.assertEqual(self.mod._auto_scale_worker_count(100), 2)
            self.assertEqual(self.mod._auto_scale_worker_count(199), 2)
            # 200-499 files: 3 workers
            self.assertEqual(self.mod._auto_scale_worker_count(200), 3)
            self.assertEqual(self.mod._auto_scale_worker_count(499), 3)
            # ≥500 files: P_cores = 8 with 8 P-cores
            self.assertEqual(self.mod._auto_scale_worker_count(500), 8)
            self.assertEqual(self.mod._auto_scale_worker_count(10_000), 8)

    def test_auto_scale_respects_cpu_count_cap_on_small_machines(self):
        """On a 2-physical-core machine the floor of `max(2, ...)` kicks
        in at every tier."""
        from unittest.mock import patch
        with patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", None), \
             patch.object(self.mod, "_physical_perf_core_count", return_value=2), \
             patch("os.cpu_count", return_value=2):
            self.assertEqual(self.mod._auto_scale_worker_count(50), 2)
            self.assertEqual(self.mod._auto_scale_worker_count(300), 2)
            self.assertEqual(self.mod._auto_scale_worker_count(5000), 2)

    def test_auto_scale_uses_cpu_count_fallback_on_non_macos(self):
        """On Linux/Windows where P-core detection isn't applicable,
        `_system_cpu_cap` falls back to `cpu_count() // 2` (approximates
        physical core count on SMT-enabled CPUs)."""
        from unittest.mock import patch
        with patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", None), \
             patch.object(self.mod, "_physical_perf_core_count", return_value=None), \
             patch("os.cpu_count", return_value=12):
            # 12-logical-core SMT machine → physical ≈ 6 → cap = 6
            self.assertEqual(self.mod._auto_scale_worker_count(10_000), 6)

    def test_auto_scale_override_wins_unconditionally(self):
        """`WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS=N` overrides auto-scale,
        including the special case of `1` (which disables parallel by
        making `use_parallel` False at the gate)."""
        from unittest.mock import patch
        with patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", 1):
            self.assertEqual(self.mod._auto_scale_worker_count(10_000), 1)
        with patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", 7):
            self.assertEqual(self.mod._auto_scale_worker_count(50), 7)
            self.assertEqual(self.mod._auto_scale_worker_count(50_000), 7)

    def test_worker_initializer_swallows_failures_silently(self):
        """The initializer wraps the load in try/except so a malformed
        path doesn't raise out of the worker's startup hook (which would
        leave the worker in a broken state without a clear failure
        signal). The worker will then fail at first-task unpickling with
        a clear ImportError — caught by the parent's graceful-fallback
        branch."""
        # Intentionally bogus path — exec_module would raise.
        try:
            self.mod._worker_init_graph_indexer("/nonexistent/path/to/graph_indexer.py")
        except Exception as exc:  # pragma: no cover — test asserts no exception
            self.fail(f"initializer must swallow load failures; raised {exc!r}")

    def test_parallel_branch_end_to_end_with_real_spawn_workers(self):
        """AC-1 in-suite: spawn-mode workers complete end-to-end on a tiny
        fixture without hanging. Catches regressions where the
        parent's sys.path is not propagated to spawned children — a class
        of bug where the wiring (start method, initializer) looks correct
        but unpickling fails at worker boot. Costs ~3-5s for real
        ProcessPoolExecutor startup; flagged as the load-bearing
        regression for Bug 4 and worth the cost."""
        from unittest.mock import patch

        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            _make_repo(root)
            files: list[Path] = []
            meta: dict = {}
            for i in range(4):
                rel = f"src/m{i}.py"
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(
                    f"def fn_{i}(x):\n    return x + {i}\n\n\nclass C{i}:\n    def m(self):\n        return fn_{i}(1)\n",
                    encoding="utf-8",
                )
                files.append(p)
                meta[rel] = {"hash": f"h{i}"}

            # First: capture the serial-path payload for byte-equivalence
            # comparison. Override resolves to "1 worker → serial path".
            with patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", 1):
                serial_payload = self.mod.update_graph_index(
                    root=root,
                    index_dir=root / ".wavefoundry" / "index",
                    layer="project",
                    files=files,
                    current_file_meta=meta,
                    changed=set(meta.keys()),
                    removed=set(),
                    walker_version="1",
                    chunker_version="1",
                    verbose=False,
                )

            # Now exercise the parallel branch with real spawn workers. The
            # override forces 2 workers regardless of auto-scale's per-file
            # tier choice. Explicitly request the process backend — the 1.3.27
            # default is threads, but this test specifically exercises the
            # spawn-mode plumbing.
            with patch.object(self.mod, "_PARALLEL_EXTRACTION_THRESHOLD", 2), \
                 patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", 2), \
                 patch.object(self.mod, "_PARALLEL_EXTRACTION_BACKEND", "processes"):
                parallel_payload = self.mod.update_graph_index(
                    root=root,
                    index_dir=root / ".wavefoundry" / "index",
                    layer="project",
                    files=files,
                    current_file_meta=meta,
                    changed=set(meta.keys()),
                    removed=set(),
                    walker_version="1",
                    chunker_version="1",
                    verbose=False,
                )
        finally:
            tmp.cleanup()

        # Counts and structure must be identical between serial and parallel
        # paths. The node/edge lists are pre-sorted in `update_graph_index`'s
        # output, so direct equality is meaningful.
        self.assertEqual(
            serial_payload["counts"], parallel_payload["counts"],
            f"serial counts={serial_payload['counts']}, "
            f"parallel counts={parallel_payload['counts']} — "
            "spawn-mode parallel must produce identical output",
        )
        self.assertEqual(
            len(serial_payload["nodes"]), len(parallel_payload["nodes"]),
            "node counts diverged between serial and parallel paths",
        )
        self.assertEqual(
            {n["id"] for n in serial_payload["nodes"]},
            {n["id"] for n in parallel_payload["nodes"]},
            "node id sets diverged between serial and parallel paths",
        )

    def test_thread_backend_end_to_end(self):
        """Wave 1p2q3 (1p2wd post-ship 1.3.27): thread backend (default)
        produces byte-identical output to serial. No spawn, no IPC, no
        pickle — just `ThreadPoolExecutor.map` over the same per-file
        worker function."""
        from unittest.mock import patch

        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            _make_repo(root)
            files: list[Path] = []
            meta: dict = {}
            for i in range(4):
                rel = f"src/m{i}.py"
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(
                    f"def fn_{i}(x):\n    return x + {i}\n\n\nclass C{i}:\n    def m(self):\n        return fn_{i}(1)\n",
                    encoding="utf-8",
                )
                files.append(p)
                meta[rel] = {"hash": f"h{i}"}

            # Serial baseline.
            with patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", 1):
                serial_payload = self.mod.update_graph_index(
                    root=root,
                    index_dir=root / ".wavefoundry" / "index",
                    layer="project",
                    files=files,
                    current_file_meta=meta,
                    changed=set(meta.keys()),
                    removed=set(),
                    walker_version="1",
                    chunker_version="1",
                    verbose=False,
                )

            # Thread backend (default in 1.3.27).
            with patch.object(self.mod, "_PARALLEL_EXTRACTION_THRESHOLD", 2), \
                 patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", 2), \
                 patch.object(self.mod, "_PARALLEL_EXTRACTION_BACKEND", "threads"):
                parallel_payload = self.mod.update_graph_index(
                    root=root,
                    index_dir=root / ".wavefoundry" / "index",
                    layer="project",
                    files=files,
                    current_file_meta=meta,
                    changed=set(meta.keys()),
                    removed=set(),
                    walker_version="1",
                    chunker_version="1",
                    verbose=False,
                )
        finally:
            tmp.cleanup()

        self.assertEqual(
            serial_payload["counts"], parallel_payload["counts"],
            f"thread backend output must match serial; "
            f"serial counts={serial_payload['counts']}, "
            f"parallel counts={parallel_payload['counts']}",
        )
        self.assertEqual(
            {n["id"] for n in serial_payload["nodes"]},
            {n["id"] for n in parallel_payload["nodes"]},
        )

    def test_parallel_branch_wires_spawn_and_initializer(self):
        """AC-2 wiring: when the use_parallel branch fires, the
        ProcessPoolExecutor is constructed with the spawn start method and
        with `_worker_init_graph_indexer` as the initializer. Verifies
        the contract without actually spawning workers (we spy on the
        executor construction)."""
        from unittest.mock import patch, MagicMock

        captured: dict = {}

        class _SpyExecutor:
            def __init__(self, *args, **kwargs):
                captured["args"] = args
                captured["kwargs"] = kwargs

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def map(self, fn, args, chunksize=1):
                # Run the task function in-process so the test exercises
                # the same code path the workers would, without forking.
                for item in args:
                    yield fn(item)

        # The parallel branch only fires when there are ≥THRESHOLD code
        # files AND the auto-scaled worker count is > 1. We patch the
        # threshold to a low value and force the worker count via the
        # `_PARALLEL_EXTRACTION_WORKERS_OVERRIDE` (which trumps auto-scale).
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            _make_repo(root)
            files: list[Path] = []
            meta: dict = {}
            for i in range(3):
                rel = f"src/m{i}.py"
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(f"def fn_{i}():\n    return {i}\n", encoding="utf-8")
                files.append(p)
                meta[rel] = {"hash": f"h{i}"}

            with patch.object(self.mod, "_PARALLEL_EXTRACTION_THRESHOLD", 2), \
                 patch.object(self.mod, "_PARALLEL_EXTRACTION_WORKERS_OVERRIDE", 2), \
                 patch.object(self.mod, "_PARALLEL_EXTRACTION_BACKEND", "processes"), \
                 patch("concurrent.futures.ProcessPoolExecutor", _SpyExecutor):
                self.mod.update_graph_index(
                    root=root,
                    index_dir=root / ".wavefoundry" / "index",
                    layer="project",
                    files=files,
                    current_file_meta=meta,
                    changed=set(meta.keys()),
                    removed=set(),
                    walker_version="1",
                    chunker_version="1",
                    verbose=False,
                )
        finally:
            tmp.cleanup()

        # The pool MUST have been constructed with our initializer wired.
        kwargs = captured.get("kwargs") or {}
        self.assertIs(
            kwargs.get("initializer"),
            self.mod._worker_init_graph_indexer,
            "ProcessPoolExecutor must be constructed with _worker_init_graph_indexer as initializer; "
            f"got initializer={kwargs.get('initializer')!r}",
        )
        initargs = kwargs.get("initargs")
        self.assertIsNotNone(initargs)
        self.assertEqual(len(initargs), 1,
                         "initargs must be a single-element tuple carrying the graph_indexer.py path")
        self.assertTrue(
            Path(initargs[0]).name == "graph_indexer.py",
            f"initargs[0] should be the absolute path to graph_indexer.py; got {initargs[0]!r}",
        )
        # And the start method must be spawn (verified through the mp_context).
        mp_ctx = kwargs.get("mp_context")
        self.assertIsNotNone(mp_ctx, "mp_context must be passed to ProcessPoolExecutor")
        self.assertEqual(mp_ctx.get_start_method(), "spawn",
                         f"start method must be 'spawn' (Bug 4 fix); got {mp_ctx.get_start_method()!r}")


class ConstantGraphTests(unittest.TestCase):
    """Wave 1p4ls: constant nodes (kind="constant") + faithfulness-gated function->constant
    `reads` edges across all core languages. Reuses the 1p4mf chunk-lane detection (one detector,
    two consumers). Reader names are >2 chars so the short-symbol prune keeps them."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files: dict) -> dict:
        paths, meta = [], {}
        for rel, content in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            paths.append(p)
            meta[rel] = {"hash": content}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index", layer="project",
            files=paths, current_file_meta=meta, changed=set(meta), removed=set(),
            walker_version="1", chunker_version="1", verbose=False)

    # (rel_path, source, const_simple_suffix, reader_simple_suffix)
    _CASES = [
        ("python", "ind.py",
         'RERANKER_MODEL = "BAAI/bge-reranker-base"\n\ndef get_model():\n    return RERANKER_MODEL\n',
         "RERANKER_MODEL", "get_model"),
        ("go", "a.go",
         "package main\nconst MaxRetries = 3\nfunc compute() int { return MaxRetries }\n",
         "MaxRetries", "compute"),
        ("java", "B.java",
         "class B {\n  static final int MAX_SIZE = 100;\n  int compute() { return MAX_SIZE; }\n}\n",
         "MAX_SIZE", "compute"),
        ("rust", "c.rs",
         "const LIMIT: u32 = 3;\nfn compute() -> u32 { LIMIT }\n",
         "LIMIT", "compute"),
        ("kotlin", "d.kt",
         'const val API_URL = "x"\nfun fetchUrl(): String { return API_URL }\n',
         "API_URL", "fetchUrl"),
        ("csharp", "E.cs",
         "class E { const int MaxRetries = 3; int compute() { return MaxRetries; } }",
         "MaxRetries", "compute"),
        ("swift", "f.swift",
         'let apiURL = "x"\nfunc fetchUrl() -> String { return apiURL }\n',
         "apiURL", "fetchUrl"),
        ("ruby", "g.rb",
         "class Svc\n  LIMIT = 5\n  def compute\n    LIMIT\n  end\nend\n",
         "LIMIT", "compute"),
        ("php", "h.php",
         "<?php\nconst MAX_SIZE = 100;\nfunction compute() { return MAX_SIZE; }\n",
         "MAX_SIZE", "compute"),
        ("typescript", "i.ts",
         'const API_URL = "x";\nfunction fetchUrl() { return API_URL; }\n',
         "API_URL", "fetchUrl"),
    ]

    def test_constant_node_and_reads_edge_per_language(self):
        """AC-1 + AC-2: each core language emits a kind="constant" node and a reader->constant
        `reads` edge. A grammar that silently failed would drop both, FAILing here (not skipping)."""
        for lang, rel, src, const_suffix, reader_suffix in self._CASES:
            with self.subTest(language=lang):
                payload = self._build({rel: src})
                consts = [n for n in payload["nodes"]
                          if n.get("kind") == "constant" and n["id"].split("::")[-1].split(".")[-1] == const_suffix]
                self.assertTrue(consts, f"[{lang}] no constant node ending in {const_suffix}; "
                                        f"got {[n['id'] for n in payload['nodes'] if n.get('kind')=='constant']}")
                const_id = consts[0]["id"]
                reads = [e for e in payload["edges"]
                         if e.get("relation") == "reads" and e.get("target") == const_id
                         and e.get("source", "").split("::")[-1].split(".")[-1] == reader_suffix]
                self.assertTrue(reads, f"[{lang}] no reads edge {reader_suffix}->{const_id}; "
                                       f"reads={[(e['source'],e['target']) for e in payload['edges'] if e.get('relation')=='reads']}")

    def test_constant_value_captured(self):
        """AC-1: a simple-literal RHS is captured on the node's `value`."""
        payload = self._build({"ind.py": 'RERANKER_MODEL = "BAAI/bge-reranker-base"\n'})
        node = next(n for n in payload["nodes"] if n["id"].endswith("::RERANKER_MODEL"))
        self.assertEqual(node.get("kind"), "constant")
        self.assertIn("bge-reranker-base", str(node.get("value")))

    def test_python_local_shadow_not_bound(self):
        """AC-5: a function-local assignment shadowing a module constant must NOT emit a reads
        edge to the module constant (the local-shadow guard)."""
        payload = self._build({"ind.py":
            "MAX_RETRIES = 3\n\ndef shadower():\n    MAX_RETRIES = 99\n    return MAX_RETRIES\n"})
        reads = [e for e in payload["edges"]
                 if e.get("relation") == "reads" and e.get("source", "").endswith("::shadower")]
        self.assertEqual(reads, [], "local shadow must not bind the module constant")

    def test_ambiguous_twin_constant_stays_unresolved(self):
        """AC-5: a bare read of a constant name defined in TWO modules (no import) must NOT bind a
        coincidental twin — symbol_lookup uniqueness keeps it unresolved."""
        payload = self._build({
            "a.py": "LIMIT = 1\n",
            "b.py": "LIMIT = 2\n",
            "c.py": "def use_limit():\n    return LIMIT\n",
        })
        reads = [e for e in payload["edges"]
                 if e.get("relation") == "reads" and e.get("source", "").endswith("::use_limit")]
        self.assertEqual(reads, [], f"ambiguous twin must stay unresolved; got {reads}")

    def test_constant_excluded_function_local(self):
        """A function-local constant is NOT a constant node (scope gate)."""
        payload = self._build({"ind.py":
            "def f():\n    LOCAL_CONST = 9\n    return LOCAL_CONST\n"})
        self.assertEqual(
            [n["id"] for n in payload["nodes"] if n.get("kind") == "constant"], [],
            "function-local constants must not be graph nodes")

    def test_cross_module_imported_constant_read(self):
        """AC-2 (imported): a function reading a constant imported from ANOTHER module gets a reads
        edge (resolved cross-module in finalize). An imported FUNCTION is NOT bound as a read."""
        payload = self._build({
            "consts.py": 'RERANKER_MODEL = "bge"\n\ndef helper():\n    return 1\n',
            "reader.py": "from consts import RERANKER_MODEL, helper\n\n"
                         "def use_model():\n    x = helper()\n    return RERANKER_MODEL\n",
        })
        reads = [(e["source"].split("::")[-1], e["target"]) for e in payload["edges"]
                 if e.get("relation") == "reads"]
        self.assertIn(("use_model", "consts.py::RERANKER_MODEL"), reads)
        self.assertFalse(any("helper" in tgt for _, tgt in reads),
                         "imported FUNCTION must not be bound as a constant read")
        self.assertFalse(any(tgt.startswith("external::") for _, tgt in reads),
                         "unresolved external:: reads must be dropped, not persisted")

    def test_typescript_enum_members_are_constant_nodes(self):
        """AC-3 (1p4q4): TS `enum` / `const enum` / `export enum` members become `kind="constant"`
        nodes (`Enum.Member`) carrying their literal value; the enum TYPE stays a class node."""
        payload = self._build({"e.ts":
            'enum Status { ACTIVE = 0, FAILED = 1 }\n'
            'const enum Dir { Upward, Downward }\n'
            'export enum Color { Crimson = "r" }\n'})
        consts = {n["id"].split("::")[-1]: n.get("value")
                  for n in payload["nodes"] if n.get("kind") == "constant"}
        for m in ("Status.ACTIVE", "Status.FAILED", "Dir.Upward", "Dir.Downward", "Color.Crimson"):
            self.assertIn(m, consts, f"enum member {m} not a constant node; got {sorted(consts)}")
        self.assertEqual(consts["Status.ACTIVE"], "0")
        self.assertEqual(consts["Color.Crimson"], '"r"')
        classes = {n["id"].split("::")[-1] for n in payload["nodes"] if n.get("kind") == "class"}
        self.assertIn("Status", classes, "the enum type stays a class node alongside its member constants")

    def test_short_enum_members_survive_short_symbol_prune(self):
        """Review D2/F1: short (≤2-char) enum members like `Status.OK` / `Dir.Up` — the wave's own
        canonical AC examples — are value-carrying constant nodes and must NOT be dropped by the
        short-symbol prune (constants are exempt). `code_definition("OK")` depends on this."""
        payload = self._build({"s.ts":
            "enum Status { OK = 0, FAIL = 1 }\nconst enum Dir { Up, Down }\n"})
        consts = {n["id"].split("::")[-1]: n.get("value")
                  for n in payload["nodes"] if n.get("kind") == "constant"}
        for m in ("Status.OK", "Status.FAIL", "Dir.Up", "Dir.Down"):
            self.assertIn(m, consts, f"short enum member {m} pruned from graph; got {sorted(consts)}")
        self.assertEqual(consts["Status.OK"], "0")

    def test_namespace_scoped_enum_members_do_not_collide(self):
        """Review D1: two same-named enums in two different namespaces must produce DISTINCT member
        nodes (NS-qualified) — the graph walker doesn't push a namespace scope, so the member qname
        must recover the enclosing namespace prefix from the AST, else NSB clobbers NSA's value."""
        payload = self._build({"s.ts":
            "namespace NSA { export enum Inner { AAA = 1 } }\n"
            "namespace NSB { export enum Inner { AAA = 2 } }\n"})
        consts = {n["id"].split("::")[-1]: n.get("value")
                  for n in payload["nodes"] if n.get("kind") == "constant"}
        self.assertEqual(consts.get("NSA.Inner.AAA"), "1", f"NSA member missing/clobbered; got {sorted(consts)}")
        self.assertEqual(consts.get("NSB.Inner.AAA"), "2", f"NSB member missing/clobbered; got {sorted(consts)}")

    def test_simple_name_stays_first_dot_split_to_avoid_overbind(self):
        """Guard (adversarial review): `_simple_name` must stay `split('.',1)` (first dot), NOT rsplit.
        Returning the bare leaf for a 2+-level-nested id over-binds the unguarded bare-call/bare-read
        paths (verified: nested-method call over-bind; param-shadow read over-fire; import-read shadow
        dropping 5 correct external:: edges on a real file). Nested member-access CONSTANT reads are a
        separate faithful (exact qualified-path) follow-on — see the guard comment on `_simple_name`."""
        sn = load_graph_indexer()._simple_name
        self.assertEqual(sn("f.swift::Cfg.limit"), "limit")                              # 1-level: leaf
        self.assertEqual(sn("f.swift::Outer.Inner.TOKEN"), "Inner.TOKEN")                # 2-level: NOT bare leaf
        self.assertEqual(sn("f.swift::A.B.C.run"), "B.C.run")                            # deep: first dot only

    def test_member_access_constant_read_resolves(self):
        """Member-access read attribution: a CONSTANT read via a qualified path (`Enum.MEMBER`,
        `Outer.Inner.CONST`) produces a `reads` edge by EXACT qname match — covering TS enum members
        (whose trailing `property_identifier` the leaf-capture never sees) and 2+-level-nested
        constants in every language whose member-access node is recognized. Reader names are >2 chars
        so the short-symbol prune keeps them."""
        # TS enum member (member_expression)
        ts = self._build({"a.ts": "enum Status { ACTIVE = 1 }\nfunction reader() { return Status.ACTIVE; }\n"})
        self._assert_reads_in(ts, ("reader", "Status.ACTIVE"))
        # TS namespace enum member (the JS-TS surface) — qualified NS.E.MEMBER
        nsts = self._build({"b.ts": "namespace NS { export enum E { ALPHA = 1 } }\nfunction reader() { return NS.E.ALPHA; }\n"})
        self._assert_reads_in(nsts, ("reader", "NS.E.ALPHA"))
        # Swift nested static (navigation_expression) — the field exact shape
        sw = self._build({"s.swift":
            "struct AppConstants {\n  struct Network { static let userAgent = \"x\" }\n}\n"
            "class NotificationDispatcher { func dispatch() -> String { return AppConstants.Network.userAgent } }\n"})
        self._assert_reads_in(sw, ("NotificationDispatcher.dispatch", "AppConstants.Network.userAgent"))
        # Java 2-level (field_access)
        jv = self._build({"C.java":
            "class Outer { static class Inner { static final String TOKEN=\"T\"; } String reader(){ return Outer.Inner.TOKEN; } }\n"})
        self._assert_reads_in(jv, ("Outer.reader", "Outer.Inner.TOKEN"))

    def test_member_access_read_is_faithful_no_overbind(self):
        """Faithfulness (adversarial — the cases that sank the `_simple_name` rsplit attempt): the
        member-access path approach is exact-qname + const-gated, so a bare parameter/local that
        shares a leaf with a nested constant, and an explicitly-imported same-leaf symbol, must NOT
        wrong-bind to the nested constant."""
        # (a) a function reading its own PARAMETER `TOKEN` must NOT bind the nested const Outer.Inner.TOKEN
        pj = self._build({"P.java":
            "class Outer { static class Inner { static final String TOKEN=\"T\"; } String handle(String TOKEN){ return TOKEN; } }\n"})
        self.assertEqual([e for e in pj["edges"] if e.get("relation") == "reads"], [],
                         "bare parameter read must not bind a same-leaf nested constant")
        # (b) an explicitly-imported `TOKEN` must NOT be shadowed by a same-leaf nested enum member
        it = self._build({
            "c.ts": "export const TOKEN = 1;\n",
            "i.ts": "import { TOKEN } from './c';\nnamespace App { export enum Cfg { TOKEN } }\nfunction f() { return TOKEN; }\n"})
        wrong = [e for e in it["edges"] if e.get("relation") == "reads"
                 and e.get("target", "").endswith("App.Cfg.TOKEN")]
        self.assertEqual(wrong, [], "imported symbol read must not wrong-bind a same-leaf nested enum member")
        # (c) instance access `config.timeout` must NOT bind the 1-level-nested const Outer.config.timeout
        #     via a `_simple_name` partial key (review F1: member-access reads require FULL-qname match).
        inst = self._build({"A.java":
            "class Outer { static class config { static final int timeout=30; } "
            "static class Other { config config; int reader(){ return config.timeout; } } }\n"})
        self.assertEqual([e for e in inst["edges"] if e.get("relation") == "reads"], [],
                         "instance member access must not bind a 1-level-nested const via a partial key")

    def test_member_access_qualifier_shadow_suppressed(self):
        """Faithfulness F4 (review): when a parameter/local is named like a type with a static const and
        accessed as `Name.MEMBER`, the access is on the LOCAL — no `reads` edge to the type's constant
        (the qualifier-shadow guard + property-leaf skip). A genuine `Type.MEMBER` (Type not shadowed)
        still fires."""
        def _reads(payload):
            return [e for e in payload["edges"] if e.get("relation") == "reads"]
        # param shadows a top-level type
        self.assertEqual(_reads(self._build({"s.swift":
            "struct Config { static let value=\"c\" }\nstruct Holder {}\n"
            "func reader(Config: Holder) -> String { return Config.value }\n"})), [],
            "Swift param shadowing a struct must not bind its static const")
        self.assertEqual(_reads(self._build({"k.kt":
            "object Cfg { const val VALUE=1 }\nclass Holder\n"
            "fun reader(Cfg: Holder): Int { return Cfg.VALUE }\n"})), [],
            "Kotlin param shadowing an object must not bind its const")
        # local var shadows a nested type
        self.assertEqual(_reads(self._build({"N.java":
            "class N { static class Status { static final String ACTIVE=\"a\"; } "
            "static class Other { static final String ACTIVE=\"x\"; } "
            "String reader(){ Other Status = new Other(); return Status.ACTIVE; } }\n"})), [],
            "Java local var shadowing a class must not bind its constant")
        # NOT shadowed → the genuine member read still fires
        legit = [(e["source"].split("::")[-1], e["target"].split("::")[-1]) for e in _reads(self._build({"m.kt":
            "object Cfg { const val VALUE=1 }\nfun reader(): Int { return Cfg.VALUE }\n"}))]
        self.assertIn(("reader", "Cfg.VALUE"), legit, f"genuine Type.MEMBER read must still fire; got {legit}")

    def test_object_array_constant_head_read_fires(self):
        """Regression (final review blocker): the property-leaf skip must NOT drop the HEAD of a member
        access. An OBJECT/ARRAY constant read via `CONST.member` / `CONST.length` (where the full path
        is NOT a registered qname) must still emit a `reads` edge to the constant via the captured head.
        (The bug was an `is` identity check on tree-sitter wrappers that blanket-skipped every leaf.)"""
        for rel, src, reader, const in [
            ("a.ts", "const GRAPH_KIND_COLORS = { external: \"#fff\" };\n"
                     "function graphCommunityColor() { return GRAPH_KIND_COLORS.external; }\n",
             "graphCommunityColor", "GRAPH_KIND_COLORS"),
            ("b.ts", "const FRAMEWORK_FLOW = [1,2,3];\nfunction frameworkFlow() { return FRAMEWORK_FLOW.length; }\n",
             "frameworkFlow", "FRAMEWORK_FLOW"),
            ("C.java", "class K { static final int[] RETRY_SCHEDULE_TABLE={1,2}; "
                       "int computeLen(){ return RETRY_SCHEDULE_TABLE.length; } }\n",
             "K.computeLen", "K.RETRY_SCHEDULE_TABLE"),
        ]:
            with self.subTest(file=rel):
                reads = [(e["source"].split("::")[-1], e["target"].split("::")[-1])
                         for e in self._build({rel: src})["edges"] if e.get("relation") == "reads"]
                self.assertIn((reader, const), reads, f"[{rel}] object/array const head read missing; got {reads}")

    def _assert_reads_in(self, payload, pair):
        reads = [(e["source"].split("::")[-1], e["target"].split("::")[-1])
                 for e in payload["edges"] if e.get("relation") == "reads"]
        self.assertIn(pair, reads, f"expected reads {pair}; got {reads}")

    def test_imported_ambiguous_constant_not_external(self):
        """AC-5 (imported): an unresolved imported read never persists as an external:: edge."""
        payload = self._build({
            "x.py": "LIMIT = 1\n",
            "y.py": "LIMIT = 2\n",
            "z.py": "from x import LIMIT\n\ndef use_limit():\n    return LIMIT\n",
        })
        ext = [e for e in payload["edges"]
               if e.get("relation") == "reads" and e.get("target", "").startswith("external::")]
        self.assertEqual(ext, [], "unresolved external:: reads must be dropped")

    def test_kotlin_object_const_read_edge(self):
        """AC-2 (delivery review B1): a `const val` inside an object/companion/class is read by a
        sibling method → a `reads` edge fires. Regression for the const-intercept double-registering
        the declaration's own name-bearing child, which inflated simple_names[name] to len 2 and made
        the same-scope uniqueness lookup skip it (silently zero reads for ALL nested Kotlin consts)."""
        payload = self._build({
            "d.kt": "object Settings {\n  const val TIMEOUT = 30\n"
                    "  fun retrieve(): Int { return TIMEOUT }\n}\n",
        })
        reads = [(e["source"].split("::")[-1], e["target"].split("::")[-1])
                 for e in payload["edges"] if e.get("relation") == "reads"]
        self.assertIn(("Settings.retrieve", "Settings.TIMEOUT"), reads,
                      f"object-const read edge missing; reads={reads}")

    def test_imported_function_with_const_twin_dropped(self):
        """AC-5 (delivery review B2): when the imported symbol is a project FUNCTION (kind gate empties
        the qualified match) and an UNRELATED module defines a coincidental same-name constant, the
        read is DROPPED — never wrong-bound to the twin via a bare simple-name fallback."""
        payload = self._build({
            "modA.py": "def CONFIG():\n    return 1\n",       # imported symbol is a FUNCTION
            "modB.py": "CONFIG = 'real-const'\n",              # coincidental const twin, unrelated
            "reader.py": "from modA import CONFIG\n\ndef use_it():\n    x = CONFIG\n    return x\n",
        })
        reads = [(e["source"].split("::")[-1], e.get("target", "")) for e in payload["edges"]
                 if e.get("relation") == "reads"]
        self.assertFalse(any(t == "modB.py::CONFIG" for _, t in reads),
                         f"imported function must not bind the coincidental const twin; reads={reads}")
        self.assertFalse(any(t.startswith("external::") for _, t in reads),
                         "unresolved external:: reads must be dropped, not persisted")

    def test_imported_thirdparty_name_with_const_twin_dropped(self):
        """AC-5 (delivery review B2): an import from a NON-project (3rd-party) module that happens to
        share a name with a unique project constant must NOT bind that constant — the reader never
        imported it. unique-or-DROP applies to the QUALIFIED import target, not a bare name."""
        payload = self._build({
            "othermod.py": "SHARED = 42\n",
            "reader2.py": "from nonexistent_3rd_party import SHARED\n\n"
                          "def use_shared():\n    return SHARED\n",
        })
        reads = [(e["source"].split("::")[-1], e.get("target", "")) for e in payload["edges"]
                 if e.get("relation") == "reads"]
        self.assertFalse(any(t == "othermod.py::SHARED" for _, t in reads),
                         f"3rd-party import must not bind a same-name project const; reads={reads}")


class GraphBuilderVersionTests(unittest.TestCase):
    """Wave 1p4ls AC-3: the node/edge shape changed (constant nodes + reads edge) so the builder
    version is bumped, forcing a full re-extract against any older cache."""

    def test_graph_builder_version_is_37(self):
        # 1p4ls bumped 25→26 (constant nodes + reads edge); 1p4q4 bumped 26→27 (TS enum member nodes);
        # 1p4q4 review bumped 27→28 (namespace-prefixed enum members + short-symbol-prune exemption);
        # 1p4up bumped 28→29 (member-access constant reads — new function→constant `reads` edges);
        # 1p5c4 bumped 29→30 (oversized-file guard: files over the tree-sitter cap skip AST extraction);
        # 1p61v bumped 30→31 (TS type-alias→`type`, property_signature→`property`; `function`-keyword /
        # non-identifier name guard — node KIND-set + node-set shape change).
        # 1p66e bumped 31→32 (edge-extraction determinism: order-independent cross-file resolution
        # tie-breaks + input fingerprint — resolved edge-set shape stabilizes across rebuilds).
        # 1p7de bumped 32→33→34 (1p7dg generalizes the v23 confidence promotion to all languages —
        # EXTRACTED→RECEIVER_RESOLVED on an already-unique same-file / exact-cross-file bind, target
        # unchanged; 1p7dh adds the `reads_config` edge + the `instruments` node property). 34 supersedes
        # the in-flight 33 test builds: the `instruments` capture was refined to read `namedOneOf(...)` +
        # structural-wrapper-nested matchers — an extraction-output change that gets its own increment.
        # 1p7dh bumped 34→35 (reads_config extended to Java/Spring FILE config: `.properties`/`.yml`/`.yaml`
        # config-key nodes + Java `@Value`/`getProperty` capture into config_read_candidates — new nodes
        # + populated candidates → new reads_config edges, an extraction-output change).
        # 1p9py (wave 1p9q3) bumped 35→36 (compact+gzip+atomic artifact persistence — on-disk FORMAT
        # change; serialization-only, content unchanged; single bump also covers the wave's sibling
        # artifact-shape changes 1p9q1/1p9q2 per the coordinated-single-bump serialization point).
        # 1p9q9 (wave 1p9qh) bumped 36→37 (structured Java import parsing: wildcard package-prefix
        # import edges participate in disambiguation, no spurious external::static, static-import
        # bare-call resolution — extraction-output change; the SINGLE bump also covers the wave's
        # sibling changes 1p9qa inheritance edges + 1p9qb receiver/annotation/package fixes per the
        # coordinated-single-bump serialization point — later lanes do NOT re-bump).
        # Wave 1p9qi bumped 37→38 (coordinated SINGLE bump for the SQL wave: 1p9qc all-relation SQL
        # keyword stoplist + column-token reduction; 1p9qd clause-aware statement-unit rewrite —
        # SQL emits reads + NEW `writes` relation instead of calls/imports, `sql_kind` property;
        # 1p9qe ERROR-region recovery tier — `sql_recovery` provenance + recovery count properties;
        # 1p9qf embedded-SQL capture fragment keys + LITERAL_DERIVED code→table binds +
        # `external::sql::` externals; 1p9qg NEW `maps_to` entity→table relation + orm_entity
        # fragment keys — new relations + relation migration + new fragment keys → re-extract).
        self.assertEqual(load_graph_indexer().GRAPH_BUILDER_VERSION, "38")


class OversizedTreeSitterGuardTests(unittest.TestCase):
    """Wave 1p5c4: tree-sitter graph extraction is skipped for files over the parse cap so a
    multi-MB/GB blob cannot spin the indexer."""

    def setUp(self):
        self.mod = load_graph_indexer()

    def test_ts_parse_returns_none_over_cap(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"WAVEFOUNDRY_MAX_TS_PARSE_BYTES": "100"}):
            self.assertIsNone(self.mod._ts_parse("python", "x = 1\n" * 100))

    def test_ts_parse_allows_small_when_cap_high(self):
        import os
        from unittest.mock import patch
        # A tiny source under the cap is NOT short-circuited by the guard (returns a tree, or
        # None only if tree-sitter itself is unavailable — never blocked by the size check).
        with patch.dict(os.environ, {"WAVEFOUNDRY_MAX_TS_PARSE_BYTES": "1000000"}):
            # The guard must not be the reason for a None here; assert it does not raise.
            self.mod._ts_parse("python", "x = 1\n")


class EdgeExtractionDeterminismTests(unittest.TestCase):
    """1p66e: identical input → identical resolved edge set + input fingerprint.

    The double/shuffled-input builds lock the end-to-end determinism + fingerprint
    contract; `test_pick_shorter_node_id_is_order_independent` is the non-vacuous
    unit lock on the primary tie-break (order-dependent in the pre-fix inline rule).
    """

    FIXTURE = {
        "src/a.py": "def foo():\n    return 42\n",
        "src/b.py": "from src.a import foo\n\n\ndef caller():\n    return foo()\n",
        "src/c.py": "from src.a import foo\n\n\ndef other():\n    return foo()\n",
        "pkg/d.py": "def helper():\n    return 1\n",
        "pkg/e.py": "from pkg.d import helper\n\n\ndef use():\n    return helper()\n",
    }

    def setUp(self):
        self.mod = load_graph_indexer()

    def _build_in(self, root, files, order):
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
        rels = order if order is not None else list(files.keys())
        paths = []
        meta = {}
        for rel in rels:
            content = files[rel]
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            paths.append(p)
            meta[rel.replace("\\", "/")] = {"hash": content}
        return self.mod.update_graph_index(
            root=root,
            index_dir=root / ".wavefoundry" / "index",
            layer="project",
            files=paths,
            current_file_meta=meta,
            changed=set(meta.keys()),
            removed=set(),
            walker_version="1",
            chunker_version="1",
            verbose=False,
        )

    def _edge_set(self, payload):
        return sorted(
            (e.get("source"), e.get("target"), e.get("relation"), e.get("confidence"))
            for e in payload["edges"]
        )

    def test_double_build_identical_edge_set_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            p1 = self._build_in(Path(a), self.FIXTURE, None)
            p2 = self._build_in(Path(b), self.FIXTURE, None)
            self.assertEqual(self._edge_set(p1), self._edge_set(p2))
            self.assertTrue(p1.get("input_fingerprint"))
            self.assertEqual(p1["input_fingerprint"], p2["input_fingerprint"])

    def test_shuffled_input_order_identical_edge_set_and_fingerprint(self):
        order1 = list(self.FIXTURE.keys())
        order2 = list(reversed(order1))
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            p1 = self._build_in(Path(a), self.FIXTURE, order1)
            p2 = self._build_in(Path(b), self.FIXTURE, order2)
            self.assertEqual(self._edge_set(p1), self._edge_set(p2))
            self.assertEqual(p1["input_fingerprint"], p2["input_fingerprint"])

    def test_pick_shorter_node_id_is_order_independent(self):
        pick = self.mod._pick_shorter_node_id
        self.assertEqual(pick(None, "x"), "x")
        # Shortest wins regardless of argument order.
        self.assertEqual(pick("aa", "b"), "b")
        self.assertEqual(pick("b", "aa"), "b")
        # Length tie → lexicographically smaller, commutatively (the pre-fix inline
        # `len(a) < len(b)` rule kept first-seen here → order-dependent).
        self.assertEqual(pick("ab", "aa"), "aa")
        self.assertEqual(pick("aa", "ab"), "aa")
        for x, y in [("f/a::x", "g/b::x"), ("m::Foo.bar", "n::Foo.baz"), ("z", "a")]:
            self.assertEqual(pick(x, y), pick(y, x))

    def test_cross_file_resolution_still_faithful(self):
        # No-regression: the cross-file call still resolves to the project node.
        with tempfile.TemporaryDirectory() as a:
            p = self._build_in(Path(a), self.FIXTURE, None)
            calls = [e for e in p["edges"] if e.get("relation") == "calls"]
            targets = [
                e["target"] for e in calls if e.get("source", "").endswith("::caller")
            ]
            self.assertIn("src/a.py::foo", targets)


class GraphArtifactPersistenceTests(unittest.TestCase):
    """Wave 1p9q3 (1p9py): compact, gzip-compressed, atomic graph artifact persistence.

    Writers emit gzip-compressed compact JSON via same-directory temp + os.replace;
    readers sniff the gzip magic bytes with a transparent legacy plain-JSON fallback,
    and any corrupted/truncated artifact degrades to the caller-supplied default.
    """

    SAMPLE = {
        "schema_version": "1",
        "builder_version": "36",
        "layer": "project",
        "counts": {"files": 1, "nodes": 2, "edges": 1},
        "nodes": [
            {"id": "src/app.py", "kind": "file"},
            {"id": "src/app.py::run", "kind": "function", "label": "run"},
        ],
        "edges": [
            {"source": "src/app.py", "target": "src/app.py::run", "relation": "defines", "confidence": "EXTRACTED"},
        ],
        "input_fingerprint": "abc123",
    }

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "graph" / "project-graph.json"

    def tearDown(self):
        self.tmp.cleanup()

    # -- write format -------------------------------------------------------

    def test_write_json_emits_gzip_compact_sorted(self):
        import gzip
        self.mod._write_json(self.path, self.SAMPLE)
        raw = self.path.read_bytes()
        self.assertEqual(raw[:2], b"\x1f\x8b", "artifact must start with the gzip magic bytes")
        decoded = gzip.decompress(raw).decode("utf-8")
        # Compact separators: no indentation whitespace, no space after ':'.
        self.assertNotIn("\n", decoded)
        self.assertNotIn(": ", decoded)
        self.assertEqual(json.loads(decoded), self.SAMPLE)
        # sort_keys retained: deterministic byte output for identical payloads.
        self.mod._write_json(self.path, dict(reversed(list(self.SAMPLE.items()))))
        self.assertEqual(self.path.read_bytes(), raw)

    def test_write_json_leaves_no_temp_files(self):
        self.mod._write_json(self.path, self.SAMPLE)
        leftovers = [p for p in self.path.parent.iterdir() if p.name != self.path.name]
        self.assertEqual(leftovers, [])

    # -- dual-format read (AC-2) ---------------------------------------------

    def test_read_json_reads_gzip_artifact(self):
        self.mod._write_json(self.path, self.SAMPLE)
        self.assertEqual(self.mod._read_json(self.path, {}), self.SAMPLE)

    def test_read_json_reads_legacy_plain_artifact(self):
        # Pre-upgrade artifact: pretty-printed plain JSON written in place.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.SAMPLE, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(self.mod._read_json(self.path, {}), self.SAMPLE)

    def test_public_alias_is_the_sniffing_reader(self):
        self.assertIs(self.mod.read_json_artifact, self.mod._read_json)

    # -- logical round-trip equivalence (AC-3) --------------------------------

    def test_legacy_roundtrip_yields_identical_payload(self):
        legacy = self.root / "legacy.json"
        legacy.write_text(json.dumps(self.SAMPLE, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        decoded = self.mod._read_json(legacy, None)
        self.mod._write_json(self.path, decoded)
        rewritten = self.mod._read_json(self.path, None)
        self.assertEqual(rewritten, self.SAMPLE)

    # -- corruption contract (AC-4) -------------------------------------------

    def test_truncated_gzip_returns_default(self):
        self.mod._write_json(self.path, self.SAMPLE)
        raw = self.path.read_bytes()
        self.path.write_bytes(raw[: len(raw) // 2])
        sentinel = {"corrupted": True}
        self.assertIs(self.mod._read_json(self.path, sentinel), sentinel)

    def test_corrupted_gzip_body_returns_default(self):
        self.mod._write_json(self.path, self.SAMPLE)
        raw = bytearray(self.path.read_bytes())
        for i in range(12, min(len(raw), 40)):
            raw[i] ^= 0xFF  # scramble the deflate stream, keep the magic bytes
        self.path.write_bytes(bytes(raw))
        self.assertEqual(self.mod._read_json(self.path, {"d": 1}), {"d": 1})

    def test_corrupted_plain_json_returns_default(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.mod._read_json(self.path, None), None)

    def test_missing_file_returns_default(self):
        self.assertEqual(self.mod._read_json(self.path, 42), 42)

    # -- atomicity (AC-8) ------------------------------------------------------

    def test_failed_write_preserves_existing_artifact_and_cleans_temp(self):
        from unittest.mock import patch
        self.mod._write_json(self.path, self.SAMPLE)
        before = self.path.read_bytes()

        with patch.object(self.mod.gzip, "compress", side_effect=RuntimeError("simulated fault")):
            with self.assertRaises(RuntimeError):
                self.mod._write_json(self.path, {"other": 1})
        self.assertEqual(self.path.read_bytes(), before, "a failed write must not touch the artifact")
        leftovers = [p for p in self.path.parent.iterdir() if p.name != self.path.name]
        self.assertEqual(leftovers, [], "a failed write must clean up its temp file")

    def test_reader_never_observes_partial_file_during_slow_writes(self):
        """A reader polling the artifact while slow writes are in flight must only
        ever see a complete old or complete new payload — never a torn one. The
        write path is slowed by chunking + sleeping inside the temp-file write so
        the window between first byte and os.replace is wide."""
        import threading
        import time as _time
        import os as _os

        payload_a = dict(self.SAMPLE, generation="A")
        payload_b = dict(self.SAMPLE, generation="B" * 2048)  # large enough to chunk
        self.mod._write_json(self.path, payload_a)

        real_fdopen = _os.fdopen

        class _SlowHandle:
            def __init__(self, handle):
                self._handle = handle

            def write(self, data):
                for i in range(0, len(data), 64):
                    self._handle.write(data[i : i + 64])
                    _time.sleep(0.0005)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return self._handle.__exit__(*exc)

        def slow_fdopen(fd, mode="r", *args, **kwargs):
            handle = real_fdopen(fd, mode, *args, **kwargs)
            if "b" in mode and "w" in mode:
                return _SlowHandle(handle)
            return handle

        sentinel = object()
        torn: list[Any] = []
        stop = threading.Event()

        def poll():
            while not stop.is_set():
                got = self.mod._read_json(self.path, sentinel)
                if got is sentinel:
                    torn.append("unreadable")
                    return
                if got.get("generation") not in ("A", "B" * 2048):
                    torn.append(got)
                    return

        reader = threading.Thread(target=poll)
        reader.start()
        try:
            from unittest.mock import patch
            with patch.object(self.mod.os, "fdopen", slow_fdopen):
                for _ in range(5):
                    self.mod._write_json(self.path, payload_b)
                    self.mod._write_json(self.path, payload_a)
        finally:
            stop.set()
            reader.join(timeout=10)
        self.assertEqual(torn, [], "reader observed a torn/partial artifact during writes")

    # -- grep gate (AC-8): no in-place write_text remains on the writer paths --

    def test_no_in_place_write_text_in_artifact_writers(self):
        import inspect
        gi_src = inspect.getsource(self.mod._write_json)
        self.assertNotIn("write_text", gi_src)
        self.assertIn("os.replace", gi_src)
        gc_path = SCRIPTS_ROOT / "graph_cluster.py"
        spec = importlib.util.spec_from_file_location("graph_cluster_for_persistence_gate", gc_path)
        gc_mod = importlib.util.module_from_spec(spec)
        sys.modules["graph_cluster_for_persistence_gate"] = gc_mod
        spec.loader.exec_module(gc_mod)
        gc_src = inspect.getsource(gc_mod._write_json)
        self.assertNotIn("write_text", gc_src)
        self.assertIn("os.replace", gc_src)

    # -- reader-copy parity gate (delivery review): the gzip sniff is mirrored
    # in four modules; a future format change must not drift a reader silently.

    def test_all_sniffing_reader_copies_handle_gzip_magic(self):
        reader_sites = {
            "graph_indexer.py": "def _read_json",
            "graph_cluster.py": "def _read_json",
            "dashboard_lib.py": "def _read_json",
            "gen_codebase_map.py": "def _read_json",
        }
        for filename, marker in reader_sites.items():
            src = (SCRIPTS_ROOT / filename).read_text(encoding="utf-8")
            self.assertIn(marker, src, f"{filename}: sniffing reader missing")
            start = src.index(marker)
            body = src[start : start + 2000]
            self.assertTrue(
                "\\x1f" in body or "0x1f" in body or "_GZIP_MAGIC" in body,
                f"{filename}: _read_json no longer sniffs the gzip magic bytes "
                "(format drift across the mirrored reader copies)",
            )

    # -- cluster artifact parity ----------------------------------------------

    def test_cluster_writer_reader_share_the_format(self):
        import gzip
        gc_path = SCRIPTS_ROOT / "graph_cluster.py"
        spec = importlib.util.spec_from_file_location("graph_cluster_for_persistence", gc_path)
        gc_mod = importlib.util.module_from_spec(spec)
        sys.modules["graph_cluster_for_persistence"] = gc_mod
        spec.loader.exec_module(gc_mod)
        path = self.root / "graph" / "project-graph-clusters.json"
        payload = {"cluster_schema_version": "1", "communities": [], "community_count": 0}
        gc_mod._write_json(path, payload)
        self.assertEqual(path.read_bytes()[:2], b"\x1f\x8b")
        self.assertEqual(json.loads(gzip.decompress(path.read_bytes()).decode("utf-8")), payload)
        self.assertEqual(gc_mod._read_json(path, {}), payload)
        # Legacy plain cluster artifact still reads.
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(gc_mod._read_json(path, {}), payload)


class JavaImportWildcardStaticTests(unittest.TestCase):
    """Wave 1p9qh (1p9q9): structured Java import parsing — wildcard imports
    participate in disambiguation, static imports emit no spurious
    `external::static` edge and resolve bare member calls."""

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

    def _run_call_targets(self, payload: dict, member: str = "") -> list[str]:
        return [
            e["target"] for e in payload["edges"]
            if e.get("relation") == "calls"
            and "App.run" in str(e.get("source", ""))
            and (not member or member in str(e.get("target", "")))
        ]

    _TWIN_FOO = "package com.foo;\npublic class Helper {\n    public void process() {}\n}\n"
    _TWIN_BAR = "package com.bar;\npublic class Helper {\n    public void process() {}\n}\n"

    # -- AC-1: wildcard participation in import-edge disambiguation ---------

    def test_wildcard_import_disambiguates_ambiguous_receiver(self):
        """`import com.foo.*;` prefers the com.foo twin of an ambiguous
        simple-name receiver, exactly like an explicit import would."""
        payload = self._build({
            "com/foo/Helper.java": self._TWIN_FOO,
            "com/bar/Helper.java": self._TWIN_BAR,
            "com/app/App.java": (
                "package com.app;\nimport com.foo.*;\npublic class App {\n"
                "    void run() {\n        Helper h = new Helper();\n        h.process();\n    }\n}\n"
            ),
        })
        targets = self._run_call_targets(payload, "process")
        self.assertIn("com/foo/Helper.java::Helper.process", targets,
                      f"wildcard import must disambiguate to com.foo; got {targets}")
        self.assertNotIn("com/bar/Helper.java::Helper.process", targets,
                         "must NOT resolve to the non-imported com.bar twin")

    def test_two_wildcard_imports_both_matching_stay_external(self):
        """Unique-survivor refusal: two wildcard imports both matching the
        ambiguous receiver's twins → never guess, stay external."""
        payload = self._build({
            "com/foo/Helper.java": self._TWIN_FOO,
            "com/bar/Helper.java": self._TWIN_BAR,
            "com/app/App.java": (
                "package com.app;\nimport com.foo.*;\nimport com.bar.*;\npublic class App {\n"
                "    void run() {\n        Helper h = new Helper();\n        h.process();\n    }\n}\n"
            ),
        })
        targets = self._run_call_targets(payload, "process")
        self.assertNotIn("com/foo/Helper.java::Helper.process", targets)
        self.assertNotIn("com/bar/Helper.java::Helper.process", targets)
        self.assertIn("external::Helper.process", targets,
                      f"two matching wildcards must refuse (stay external); got {targets}")

    def test_explicit_import_keeps_precedence_over_wildcard(self):
        """Risk guard: an explicit import shadows a wildcard import — the
        explicit com.bar twin wins even though com.foo.* also matches."""
        payload = self._build({
            "com/foo/Helper.java": self._TWIN_FOO,
            "com/bar/Helper.java": self._TWIN_BAR,
            "com/app/App.java": (
                "package com.app;\nimport com.bar.Helper;\nimport com.foo.*;\npublic class App {\n"
                "    void run() {\n        Helper h = new Helper();\n        h.process();\n    }\n}\n"
            ),
        })
        targets = self._run_call_targets(payload, "process")
        self.assertIn("com/bar/Helper.java::Helper.process", targets,
                      f"explicit import must keep precedence over wildcard; got {targets}")
        self.assertNotIn("com/foo/Helper.java::Helper.process", targets)

    def test_own_package_twin_shadows_wildcard_import(self):
        """Java shadowing faithfulness: a same-package (same-directory) twin
        shadows an on-demand (wildcard) import — the wildcard pass counts the
        own-package twin as a match (→ ambiguous, refuse) and the same-dir
        fallback then binds the own-package twin, never the wildcard one."""
        payload = self._build({
            "com/foo/Helper.java": self._TWIN_FOO,
            "com/app/Helper.java": "package com.app;\npublic class Helper {\n    public void process() {}\n}\n",
            "com/app/App.java": (
                "package com.app;\nimport com.foo.*;\npublic class App {\n"
                "    void run() {\n        Helper h = new Helper();\n        h.process();\n    }\n}\n"
            ),
        })
        targets = self._run_call_targets(payload, "process")
        self.assertIn("com/app/Helper.java::Helper.process", targets,
                      f"same-package twin must shadow the wildcard import; got {targets}")
        self.assertNotIn("com/foo/Helper.java::Helper.process", targets)

    def test_wildcard_import_edge_is_package_prefix_not_truncated(self):
        """The defect shape: `import com.foo.*;` used to emit the truncated
        `external::com.foo.` (trailing dot) candidate. Now it is the explicit
        package-prefix form `external::com.foo.*`."""
        payload = self._build({
            "com/app/App.java": "package com.app;\nimport com.foo.*;\npublic class App { void run() {} }\n",
        })
        import_targets = sorted(
            e["target"] for e in payload["edges"] if e.get("relation") == "imports"
        )
        self.assertEqual(import_targets, ["external::com.foo.*"])

    # -- AC-2: no spurious external::static, asserted over the whole payload -

    def test_static_import_produces_no_external_static_anywhere(self):
        payload = self._build({
            "com/foo/Bar.java": "package com.foo;\npublic class Bar {\n    public static int baz() { return 1; }\n}\n",
            "com/app/App.java": (
                "package com.app;\nimport static com.foo.Bar.baz;\nimport static com.foo.Bar.*;\n"
                "public class App {\n    int run() {\n        return baz();\n    }\n}\n"
            ),
        })
        offenders = [
            (e.get("source"), e.get("target"), e.get("relation"))
            for e in payload["edges"]
            if e.get("source") == "external::static" or e.get("target") == "external::static"
        ]
        self.assertEqual(offenders, [],
                         f"static imports must never emit external::static edges; got {offenders}")
        self.assertNotIn("external::static", {n.get("id") for n in payload["nodes"]},
                         "static imports must never materialize an external::static node")

    # -- AC-3: static-import member resolution --------------------------------

    def test_static_member_bare_call_binds_project_symbol(self):
        """`import static com.foo.Bar.baz;` + bare `baz()` binds the project
        `Bar.baz` at receiver-resolved confidence."""
        payload = self._build({
            "com/foo/Bar.java": "package com.foo;\npublic class Bar {\n    public static int baz() { return 1; }\n}\n",
            "com/app/App.java": (
                "package com.app;\nimport static com.foo.Bar.baz;\npublic class App {\n"
                "    int run() {\n        return baz();\n    }\n}\n"
            ),
        })
        edges = [
            (e["target"], e.get("confidence")) for e in payload["edges"]
            if e.get("relation") == "calls" and "App.run" in str(e.get("source", ""))
        ]
        self.assertIn(("com/foo/Bar.java::Bar.baz", "RECEIVER_RESOLVED"), edges,
                      f"static-imported bare call must bind project Bar.baz; got {edges}")

    def test_static_member_bare_call_external_stays_qualified(self):
        """When the statically-imported class is not a project symbol the bare
        call lands as QUALIFIED `external::Bar.baz` — never bare, never the
        enclosing-class misattribution `external::App.baz`."""
        payload = self._build({
            "com/app/App.java": (
                "package com.app;\nimport static com.foo.Bar.baz;\npublic class App {\n"
                "    int run() {\n        return baz();\n    }\n}\n"
            ),
        })
        targets = self._run_call_targets(payload)
        self.assertIn("external::Bar.baz", targets,
                      f"external static member must stay qualified; got {targets}")
        self.assertNotIn("external::baz", targets, "never a bare external member")
        self.assertNotIn("external::App.baz", targets,
                         "static import must beat the enclosing-class misattribution")

    def test_static_wildcard_resolves_unresolved_bare_call(self):
        """`import static com.foo.Bar.*;` resolves an otherwise-unresolved bare
        call through the wildcard container class."""
        payload = self._build({
            "com/foo/Bar.java": "package com.foo;\npublic class Bar {\n    public static int frob() { return 1; }\n}\n",
            "com/app/App.java": (
                "package com.app;\nimport static com.foo.Bar.*;\npublic class App {\n"
                "    int run() {\n        return frob();\n    }\n}\n"
            ),
        })
        targets = self._run_call_targets(payload)
        self.assertIn("com/foo/Bar.java::Bar.frob", targets,
                      f"static wildcard must resolve the bare call; got {targets}")

    def test_two_static_wildcards_refuse(self):
        """Unique-survivor: two static wildcard imports never guess — the bare
        call keeps its existing enclosing-class attribution."""
        payload = self._build({
            "com/foo/Bar.java": "package com.foo;\npublic class Bar {\n    public static int frob() { return 1; }\n}\n",
            "com/qux/Zed.java": "package com.qux;\npublic class Zed {\n    public static int frob() { return 2; }\n}\n",
            "com/app/App.java": (
                "package com.app;\nimport static com.foo.Bar.*;\nimport static com.qux.Zed.*;\n"
                "public class App {\n    int run() {\n        return frob();\n    }\n}\n"
            ),
        })
        targets = self._run_call_targets(payload)
        self.assertNotIn("com/foo/Bar.java::Bar.frob", targets)
        self.assertNotIn("com/qux/Zed.java::Zed.frob", targets)
        self.assertIn("external::App.frob", targets,
                      f"two static wildcards must refuse (keep enclosing attribution); got {targets}")

    def test_same_file_definition_takes_precedence_over_static_import(self):
        """Same-file scope-first order is unchanged: a `baz` defined by the
        enclosing class wins over the static import."""
        payload = self._build({
            "com/foo/Bar.java": "package com.foo;\npublic class Bar {\n    public static int baz() { return 1; }\n}\n",
            "com/app/App.java": (
                "package com.app;\nimport static com.foo.Bar.baz;\npublic class App {\n"
                "    int baz() { return 2; }\n    int run() {\n        return baz();\n    }\n}\n"
            ),
        })
        targets = self._run_call_targets(payload)
        self.assertIn("com/app/App.java::App.baz", targets,
                      f"same-file definition must win over the static import; got {targets}")
        self.assertNotIn("com/foo/Bar.java::Bar.baz", targets)

    # -- Adversarial fix F2: own-package shadow guard keys on the DECLARED
    # -- package, never the directory (wave 1p9qh review finding).

    def test_own_package_shadow_keys_on_declared_package_not_directory(self):
        """A9 reproducer: the source declares `com.app` but lives OUTSIDE the
        package-mirroring directory; the own-package twin also lives in a
        non-mirroring directory. Java shadowing: the own-package twin shadows
        the wildcard import — the wildcard twin must never bind, and the
        declared-package tier binds the own-package twin."""
        payload = self._build({
            "src/App.java": (
                "package com.app;\nimport com.foo.*;\npublic class App {\n"
                "    void run(Helper h) {\n        h.process();\n    }\n}\n"
            ),
            "com/foo/Helper.java": self._TWIN_FOO,
            "app2/Helper.java": "package com.app;\npublic class Helper {\n    public void process() {}\n}\n",
        })
        targets = self._run_call_targets(payload, "process")
        self.assertNotIn("com/foo/Helper.java::Helper.process", targets,
                         f"wildcard twin must be shadowed by the declared-package twin; got {targets}")
        self.assertIn("app2/Helper.java::Helper.process", targets,
                      f"declared-package tier must bind the own-package twin; got {targets}")

    def test_wildcard_shadow_guard_on_extends_target_uses_declared_package(self):
        """F2-AMP reproducer: the same keying defect on an `extends` target
        amplified into wrong inherited call binds in untouched files. The
        supertype must resolve to the own-package (declared) twin, and the
        inherited-method bind must follow it — never the wildcard twin."""
        payload = self._build({
            "src/Child.java": (
                "package com.app;\nimport com.lib.*;\n"
                "public class Child extends Base {\n    public void other() {}\n}\n"
            ),
            "com/lib/Base.java": "package com.lib;\npublic class Base {\n    public void persist() {}\n}\n",
            "app2/Base.java": "package com.app;\npublic class Base {\n    public void persist() {}\n}\n",
            "src2/Caller.java": (
                "package com.app;\npublic class Caller {\n"
                "    public void run(Child c) {\n        c.persist();\n    }\n}\n"
            ),
        })
        extends = [
            (e["source"], e["target"]) for e in payload["edges"]
            if e.get("relation") == "extends" and str(e.get("source", "")).startswith("src/Child.java")
        ]
        self.assertEqual([t for _s, t in extends], ["app2/Base.java"],
                         f"extends must bind the declared-package twin, never the wildcard twin; got {extends}")
        calls = [
            (e["target"], e.get("via_supertype")) for e in payload["edges"]
            if e.get("relation") == "calls" and "Caller.run" in str(e.get("source", ""))
        ]
        self.assertIn(("app2/Base.java::Base.persist", ["app2/Base.java"]), calls,
                      f"inherited bind must flow through the Java-true parent; got {calls}")
        self.assertNotIn("com/lib/Base.java::Base.persist", [t for t, _v in calls],
                         "the wildcard twin's member must never be inherited-bound")


class JavaStaticImportInheritedShadowTests(unittest.TestCase):
    """Wave 1p9qh adversarial fix (F1): JLS 6.4.1 — members in class scope
    INCLUDING INHERITED ones shadow single-static and static-on-demand
    imports. A bare call that a static-import fact would bind, in a class
    with a supertype clause, is deferred via the reserved
    ``external::staticorinherited#…`` marker and arbitrated in the finalize
    pass: inherited definer wins; multiple definers refuse; no definer lets
    the static claim stand. The marker is unmintable from source and never
    appears in an output payload."""

    _BASE_HELPER = "package com.app;\npublic class Base {\n    public void helper() {}\n}\n"
    _BASE_PLAIN = "package com.app;\npublic class Base {\n    public void other() {}\n}\n"
    _MATHS_HELPER = "package com.util;\npublic class Maths {\n    public static void helper() {}\n}\n"

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

    def _child_calls(self, payload: dict) -> list[tuple[str, list | None]]:
        return [
            (e["target"], e.get("via_supertype")) for e in payload["edges"]
            if e.get("relation") == "calls" and "Child.run" in str(e.get("source", ""))
        ]

    def _child(self, imports: str) -> str:
        return (
            f"package com.app;\n{imports}\n"
            "public class Child extends Base {\n    public void run() {\n        helper();\n    }\n}\n"
        )

    def test_inherited_definer_wins_over_explicit_static_import(self):
        """A8b reproducer: class member scope (inherited Base.helper) shadows
        the single-static-import of Maths.helper (JLS 6.4.1)."""
        payload = self._build({
            "com/app/Base.java": self._BASE_HELPER,
            "com/util/Maths.java": self._MATHS_HELPER,
            "com/app/Child.java": self._child("import static com.util.Maths.helper;"),
        })
        calls = self._child_calls(payload)
        self.assertIn(("com/app/Base.java::Base.helper", ["com/app/Base.java"]), calls,
                      f"inherited definer must win with via_supertype provenance; got {calls}")
        self.assertNotIn("com/util/Maths.java::Maths.helper", [t for t, _v in calls],
                         "the explicit static import must stay shadowed")

    def test_inherited_definer_wins_over_static_wildcard_import(self):
        """A8 reproducer: static-import-on-demand is likewise shadowed."""
        payload = self._build({
            "com/app/Base.java": self._BASE_HELPER,
            "com/util/Maths.java": self._MATHS_HELPER,
            "com/app/Child.java": self._child("import static com.util.Maths.*;"),
        })
        calls = self._child_calls(payload)
        self.assertIn(("com/app/Base.java::Base.helper", ["com/app/Base.java"]), calls,
                      f"inherited definer must win over the static wildcard; got {calls}")
        self.assertNotIn("com/util/Maths.java::Maths.helper", [t for t, _v in calls])

    def test_junit_idiom_static_wildcard_never_steals_inherited_bind(self):
        """A8-EXT direction 1: a plain `import static org.junit.Assert.*;`
        (no project twin for the container class) must not steal a call that
        an inherited member defines."""
        payload = self._build({
            "com/app/Base.java": self._BASE_HELPER,
            "com/app/Child.java": self._child("import static org.junit.Assert.*;"),
        })
        calls = self._child_calls(payload)
        self.assertIn(("com/app/Base.java::Base.helper", ["com/app/Base.java"]), calls,
                      f"inherited bind must survive the JUnit-idiom wildcard; got {calls}")
        self.assertNotIn("external::Assert.helper", [t for t, _v in calls])

    def test_static_claim_stands_when_walk_finds_no_definer_external(self):
        """A8-EXT direction 2: the supertype walk finds NO definer — the
        static claim stands, qualified external as today."""
        payload = self._build({
            "com/app/Base.java": self._BASE_PLAIN,
            "com/app/Child.java": self._child("import static org.junit.Assert.*;"),
        })
        targets = [t for t, _v in self._child_calls(payload)]
        self.assertIn("external::Assert.helper", targets,
                      f"no-definer walk must let the static claim stand (qualified); got {targets}")
        self.assertNotIn("external::helper", targets, "never a bare external member")
        self.assertNotIn("external::Child.helper", targets,
                         "the claim stands — not the enclosing-class refusal")

    def test_static_claim_stands_when_walk_finds_no_definer_project(self):
        """No-definer walk with a PROJECT container class: the deferred claim
        binds the project `Maths.helper` exactly as the direct static bind
        would have."""
        payload = self._build({
            "com/app/Base.java": self._BASE_PLAIN,
            "com/util/Maths.java": self._MATHS_HELPER,
            "com/app/Child.java": self._child("import static com.util.Maths.helper;"),
        })
        edges = [
            (e["target"], e.get("confidence")) for e in payload["edges"]
            if e.get("relation") == "calls" and "Child.run" in str(e.get("source", ""))
        ]
        self.assertIn(("com/util/Maths.java::Maths.helper", "RECEIVER_RESOLVED"), edges,
                      f"standing claim must bind the project symbol at receiver confidence; got {edges}")

    def test_no_supertype_clause_keeps_direct_static_bind(self):
        """A class with NO supertype clause has no inherited members to
        arbitrate — the extraction-time static bind is unchanged and no
        marker is ever emitted."""
        payload = self._build({
            "com/util/Maths.java": self._MATHS_HELPER,
            "com/app/App.java": (
                "package com.app;\nimport static com.util.Maths.helper;\n"
                "public class App {\n    public void run() {\n        helper();\n    }\n}\n"
            ),
        })
        targets = [
            e["target"] for e in payload["edges"]
            if e.get("relation") == "calls" and "App.run" in str(e.get("source", ""))
        ]
        self.assertIn("com/util/Maths.java::Maths.helper", targets,
                      f"no-supertype class keeps the direct static bind; got {targets}")
        self._assert_no_marker_anywhere(payload)

    def test_multi_definer_with_static_import_refuses(self):
        """Walk refuses on MULTIPLE definers — and because inherited members
        exist, the static import stays shadowed (JLS 6.4.1): the arbitration
        must never 'fall back' to the static claim on ambiguity. Refusal is
        the enclosing-class external form."""
        payload = self._build({
            "com/app/Base.java": self._BASE_HELPER,
            "com/app/IAudit.java": (
                "package com.app;\npublic interface IAudit {\n    default void helper() {}\n}\n"
            ),
            "com/util/Maths.java": self._MATHS_HELPER,
            "com/app/Child.java": (
                "package com.app;\nimport static com.util.Maths.helper;\n"
                "public class Child extends Base implements IAudit {\n"
                "    public void run() {\n        helper();\n    }\n}\n"
            ),
        })
        targets = [t for t, _v in self._child_calls(payload)]
        self.assertIn("external::Child.helper", targets,
                      f"multi-definer + static import must refuse; got {targets}")
        for wrong in (
            "com/util/Maths.java::Maths.helper",
            "com/app/Base.java::Base.helper",
            "com/app/IAudit.java::IAudit.helper",
        ):
            self.assertNotIn(wrong, targets,
                             f"never bind {wrong} on a multi-definer refusal")

    def _assert_no_marker_anywhere(self, payload: dict) -> None:
        prefix = self.mod._STATIC_OR_INHERITED_PREFIX
        offenders = [
            (e.get("source"), e.get("target")) for e in payload["edges"]
            if prefix in str(e.get("target", "")) or prefix in str(e.get("source", ""))
        ]
        self.assertEqual(offenders, [], f"marker leaked into payload edges: {offenders}")
        node_offenders = [n.get("id") for n in payload["nodes"] if prefix in str(n.get("id", ""))]
        self.assertEqual(node_offenders, [], f"marker leaked into payload nodes: {node_offenders}")

    def test_marker_never_appears_in_output_payload(self):
        """Every marker is arbitrated by the finalize pass — bind, refusal,
        or standing claim — so no output payload ever contains it."""
        payload = self._build({
            "com/app/Base.java": self._BASE_HELPER,
            "com/util/Maths.java": self._MATHS_HELPER,
            "com/app/Child.java": self._child("import static com.util.Maths.*;"),
        })
        self._assert_no_marker_anywhere(payload)

    def test_marker_prefix_unmintable_from_source_identifiers(self):
        """Reserved-marker invariant (red-team): no source construct in any
        language can mint the `staticorinherited#` marker — the `#` separator
        cannot appear in an identifier, and every other emitter builds calls
        targets from identifier/AST text. A Java class literally named
        `staticorinherited` yields the DOT form `external::staticorinherited.…`,
        which does not match the `#`-terminated prefix and flows through the
        normal resolution machinery untouched."""
        payload = self._build({
            # Ambiguous twins keep the dot-form target external through
            # phase 1 AND the finalize walk (non-unique receiver class).
            "com/a/staticorinherited.java": (
                "package com.a;\npublic class staticorinherited {\n    public void save() {}\n}\n"
            ),
            "com/b/staticorinherited.java": (
                "package com.b;\npublic class staticorinherited {\n    public void save() {}\n}\n"
            ),
            "com/app/Caller.java": (
                "package com.app;\npublic class Caller {\n"
                "    public void run(staticorinherited x) {\n        x.save();\n    }\n}\n"
            ),
            # C# shares the finalize pass; its emitter is identifier-derived too.
            "App/staticorinherited.cs": (
                "namespace App {\n    public class staticorinherited {\n        public void Save() {}\n    }\n}\n"
            ),
        })
        caller_targets = [
            e["target"] for e in payload["edges"]
            if e.get("relation") == "calls" and "Caller.run" in str(e.get("source", ""))
        ]
        self.assertIn("external::staticorinherited.save", caller_targets,
                      f"the dot-form pseudo-collision must pass through as a normal external; got {caller_targets}")
        self._assert_no_marker_anywhere(payload)


class NonJavaImportCandidateRegressionTests(unittest.TestCase):
    """Wave 1p9qh (1p9q9) AC-4: the Java fix is a Java-scoped structured path —
    non-Java import candidate extraction through the SHARED regex fallback is
    pinned byte-identical to the pre-change behavior (baseline captured on the
    pre-change tree, 2026-07-04). If any pinned list changes, the shared
    `_ts_relation_candidates` path drifted for a non-Java language."""

    # (node_type, candidates) per import-classified node, in walk order.
    _BASELINE = {
        "kotlin": [
            ("import", ["com.foo.Bar"]),
            ("import", []),
            ("import", ["com.foo."]),  # Kotlin wildcard truncation: out of scope here, pinned as-is
            ("import", []),
            ("import", ["com.foo.Bar", "W"]),
            ("import", []),
        ],
        "csharp": [
            ("using_directive", ["System.Text"]),
            ("using", []),
            ("using_directive", ["static", "System.Math"]),  # C# `using static`: out of scope, pinned as-is
            ("using", []),
            ("using_directive", ["W"]),
            ("using", []),
        ],
        "go": [
            ("package_clause", ["app"]),
            ("import_declaration", ["fmt"]),
            ("import", []),
            ("import_spec", ["fmt"]),
            ("import_declaration", ["strings", "alias", "net/http"]),
            ("import", []),
            ("import_spec_list", ["strings", "alias", "net/http"]),
            ("import_spec", ["strings"]),
            ("import_spec", ["net/http", "alias"]),
        ],
        "typescript": [
            ("import_statement", ["y"]),
            ("import", []),
            ("import_clause", ["x"]),
            ("named_imports", ["x"]),
            ("import_specifier", ["x"]),
            ("import_statement", ["pkg"]),
            ("import", []),
            ("import_clause", ["ns"]),
            ("namespace_import", ["ns"]),
        ],
    }
    _FIXTURES = {
        "kotlin": "import com.foo.Bar\nimport com.foo.*\nimport com.foo.Bar as W\nclass App\n",
        "csharp": "using System.Text;\nusing static System.Math;\nusing W = System.Wide;\nclass App {}\n",
        "go": 'package app\nimport "fmt"\nimport (\n  "strings"\n  alias "net/http"\n)\n',
        "typescript": "import { x } from './y';\nimport * as ns from 'pkg';\n",
    }
    _GRAMMAR_MODULES = {
        "kotlin": "tree_sitter_kotlin",
        "csharp": "tree_sitter_c_sharp",
        "go": "tree_sitter_go",
        "typescript": "tree_sitter_typescript",
    }

    def setUp(self):
        self.mod = load_graph_indexer()

    def _import_candidates(self, lang: str) -> list[tuple[str, list[str]]]:
        source_text = self._FIXTURES[lang]
        profile = self.mod._TS_LANGUAGE_PROFILES.get(lang)
        self.assertIsNotNone(profile, f"no language profile for {lang}")
        tree = self.mod._ts_parse(lang, source_text)
        self.assertIsNotNone(tree, f"tree-sitter parse unavailable for {lang}")
        source_bytes = source_text.encode("utf-8")
        mode = profile.mode
        out: list[tuple[str, list[str]]] = []

        def walk(node):
            if self.mod._ts_is_import_node(node.type, mode):
                out.append((node.type, self.mod._ts_relation_candidates(node, source_bytes, "import", mode)))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return out

    def _assert_language_pinned(self, lang: str):
        import importlib
        try:
            importlib.import_module(self._GRAMMAR_MODULES[lang])
        except ImportError:
            self.skipTest(f"{self._GRAMMAR_MODULES[lang]} not available in test env")
        self.assertEqual(
            self._import_candidates(lang), self._BASELINE[lang],
            f"{lang}: shared import-candidate extraction drifted from the pre-1p9q9 baseline",
        )

    def test_kotlin_import_candidates_unchanged(self):
        self._assert_language_pinned("kotlin")

    def test_csharp_import_candidates_unchanged(self):
        self._assert_language_pinned("csharp")

    def test_go_import_candidates_unchanged(self):
        self._assert_language_pinned("go")

    def test_typescript_import_candidates_unchanged(self):
        self._assert_language_pinned("typescript")


class JavaCSharpInheritanceTests(unittest.TestCase):
    """Wave 1p9qh (1p9qa): `extends`/`implements` inheritance edges for Java
    and C#, inherited-method + `super.`/`base.` resolution, and the
    single-definer refusal discipline."""

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

    def _require_csharp(self):
        try:
            import tree_sitter_c_sharp  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_c_sharp not available in test env")

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

    def _rel_edges(self, payload: dict, *relations: str) -> list[tuple[str, str, str, str]]:
        return sorted(
            (e["source"], e["target"], e["relation"], e.get("confidence", ""))
            for e in payload["edges"]
            if e.get("relation") in relations
        )

    def _calls_to(self, payload: dict, needle: str) -> list[dict]:
        return [
            e for e in payload["edges"]
            if e.get("relation") == "calls" and needle in str(e.get("target", ""))
        ]

    # ---- AC-1: Java declaration forms -------------------------------------

    def test_java_class_extends_project_class_and_implements_external(self):
        payload = self._build({
            "com/app/AbstractRepo.java": "package com.app;\npublic abstract class AbstractRepo {\n    public void persist() {}\n}\n",
            "com/app/UserRepo.java": "package com.app;\npublic class UserRepo extends AbstractRepo implements Runnable {\n    public void run() {}\n}\n",
        })
        edges = self._rel_edges(payload, "extends", "implements")
        self.assertIn(
            ("com/app/UserRepo.java", "com/app/AbstractRepo.java", "extends", "RECEIVER_RESOLVED"),
            edges, f"project-resolved superclass must bind; got {edges}")
        self.assertIn(
            ("com/app/UserRepo.java", "external::Runnable", "implements", "EXTRACTED"),
            edges, f"unresolvable interface must stay external, never dropped; got {edges}")

    def test_java_generic_supertype_strips_to_raw_name(self):
        payload = self._build({
            "com/app/Base.java": "package com.app;\npublic class Base<T> {\n    public void persist() {}\n}\n",
            "com/app/Child.java": "package com.app;\npublic class Child extends Base<String> {\n    public void other() {}\n}\n",
        })
        edges = self._rel_edges(payload, "extends")
        self.assertEqual(
            [("com/app/Child.java", "com/app/Base.java", "extends", "RECEIVER_RESOLVED")],
            edges, f"`extends Base<String>` must strip to `Base` and bind; got {edges}")

    def test_java_interface_extends_interfaces(self):
        payload = self._build({
            "com/app/Alpha.java": "package com.app;\npublic interface Alpha {\n    void alpha();\n}\n",
            "com/app/Sub.java": "package com.app;\npublic interface Sub extends Alpha, Comparable {\n    void subMethod();\n}\n",
        })
        edges = self._rel_edges(payload, "extends")
        self.assertIn(("com/app/Sub.java", "com/app/Alpha.java", "extends", "RECEIVER_RESOLVED"), edges)
        self.assertIn(("com/app/Sub.java", "external::Comparable", "extends", "EXTRACTED"), edges)
        self.assertEqual(self._rel_edges(payload, "implements"), [],
                         "interface extends-clause must emit extends, never implements")

    def test_java_enum_and_record_implement_interfaces(self):
        payload = self._build({
            "com/app/Marker.java": "package com.app;\npublic interface Marker {\n    void mark();\n}\n",
            "com/app/Color.java": "package com.app;\npublic enum Color implements Marker {\n    RED;\n    public void mark() {}\n}\n",
            "com/app/Point.java": "package com.app;\npublic record Point(int x) implements Marker {\n    public void mark() {}\n}\n",
        })
        edges = self._rel_edges(payload, "implements")
        self.assertIn(("com/app/Color.java", "com/app/Marker.java", "implements", "RECEIVER_RESOLVED"), edges)
        self.assertIn(("com/app/Point.java", "com/app/Marker.java", "implements", "RECEIVER_RESOLVED"), edges)

    def test_java_ambiguous_supertype_stays_external(self):
        payload = self._build({
            "com/foo/Base.java": "package com.foo;\npublic class Base {\n    public void persist() {}\n}\n",
            "com/bar/Base.java": "package com.bar;\npublic class Base {\n    public void persist() {}\n}\n",
            "com/app/Child.java": "package com.app;\npublic class Child extends Base {\n    public void other() {}\n}\n",
        })
        edges = self._rel_edges(payload, "extends")
        self.assertEqual(
            [("com/app/Child.java", "external::Base", "extends", "EXTRACTED")],
            edges, f"two twin candidates must refuse (stay external); got {edges}")

    def test_java_import_disambiguates_supertype(self):
        payload = self._build({
            "com/foo/Base.java": "package com.foo;\npublic class Base {\n    public void persist() {}\n}\n",
            "com/bar/Base.java": "package com.bar;\npublic class Base {\n    public void persist() {}\n}\n",
            "com/app/Child.java": "package com.app;\nimport com.foo.Base;\npublic class Child extends Base {\n    public void other() {}\n}\n",
        })
        edges = self._rel_edges(payload, "extends")
        self.assertEqual(
            [("com/app/Child.java", "com/foo/Base.java", "extends", "RECEIVER_RESOLVED")],
            edges, f"explicit import must disambiguate the supertype twin; got {edges}")

    def test_java_scoped_supertype_emits_qualified_external(self):
        payload = self._build({
            "com/app/Child.java": "package com.app;\npublic class Child extends com.ext.Base {\n    public void other() {}\n}\n",
        })
        edges = self._rel_edges(payload, "extends")
        self.assertEqual(
            [("com/app/Child.java", "external::com.ext.Base", "extends", "EXTRACTED")],
            edges, f"scoped supertype must stay qualified as declared; got {edges}")

    def test_java_supertype_never_binds_non_class_twin(self):
        """Kind gate: a unique same-named FUNCTION can never become a supertype."""
        payload = self._build({
            "util.py": "def Base():\n    return 1\n",
            "com/app/Child.java": "package com.app;\npublic class Child extends Base {\n    public void other() {}\n}\n",
        })
        edges = self._rel_edges(payload, "extends")
        self.assertEqual(
            [("com/app/Child.java", "external::Base", "extends", "EXTRACTED")],
            edges, f"a function twin must be refused as a supertype; got {edges}")

    # ---- AC-2: C# base_list ------------------------------------------------

    def test_csharp_base_list_kind_based_relations(self):
        self._require_csharp()
        payload = self._build({
            "cs/BaseWorker.cs": "namespace App {\n  public class BaseWorker {\n    public void Persist() {}\n  }\n}\n",
            "cs/IWorker.cs": "namespace App {\n  public interface IWorker { void Work(); }\n}\n",
            "cs/RealWorker.cs": "namespace App {\n  public class RealWorker : BaseWorker, IWorker {\n    public void Work() {}\n  }\n}\n",
        })
        edges = self._rel_edges(payload, "extends", "implements")
        self.assertIn(("cs/RealWorker.cs::App.RealWorker", "cs/BaseWorker.cs::App.BaseWorker", "extends", "RECEIVER_RESOLVED"), edges)
        self.assertIn(("cs/RealWorker.cs::App.RealWorker", "cs/IWorker.cs::App.IWorker", "implements", "RECEIVER_RESOLVED"), edges)

    def test_csharp_first_base_project_interface_flips_to_implements(self):
        """The positional first-base-is-extends convention yields to the TRUE
        kind when the base resolves to a project interface."""
        self._require_csharp()
        payload = self._build({
            "cs/IWorker.cs": "namespace App {\n  public interface IWorker { void Work(); }\n}\n",
            "cs/RealWorker.cs": "namespace App {\n  public class RealWorker : IWorker {\n    public void Work() {}\n  }\n}\n",
        })
        edges = self._rel_edges(payload, "extends", "implements")
        self.assertEqual(
            [("cs/RealWorker.cs::App.RealWorker", "cs/IWorker.cs::App.IWorker", "implements", "RECEIVER_RESOLVED")],
            edges, f"project-resolved interface in first position must be implements; got {edges}")

    def test_csharp_unresolved_bases_first_extends_rest_implements(self):
        """C# convention case: at most one base class, listed first — so for
        UNRESOLVED bases the first is labeled extends and the rest implements."""
        self._require_csharp()
        payload = self._build({
            "cs/Worker.cs": "namespace App {\n  public class Worker : ExternalBase, IExternalThing {\n    public void Work() {}\n  }\n}\n",
        })
        edges = self._rel_edges(payload, "extends", "implements")
        self.assertEqual([
            ("cs/Worker.cs::App.Worker", "external::ExternalBase", "extends", "EXTRACTED"),
            ("cs/Worker.cs::App.Worker", "external::IExternalThing", "implements", "EXTRACTED"),
        ], edges, f"unresolved bases: first=extends, rest=implements; got {edges}")

    def test_csharp_interface_and_struct_declarers(self):
        self._require_csharp()
        payload = self._build({
            "cs/Decls.cs": (
                "namespace App {\n"
                "  public interface ISub : IExternalA, IExternalB { void SubWork(); }\n"
                "  public struct SVec : IExternalMarker {\n    public void VecWork() {}\n  }\n"
                "}\n"
            ),
        })
        edges = self._rel_edges(payload, "extends", "implements")
        self.assertIn(("cs/Decls.cs::App.ISub", "external::IExternalA", "extends", "EXTRACTED"), edges)
        self.assertIn(("cs/Decls.cs::App.ISub", "external::IExternalB", "extends", "EXTRACTED"), edges)
        self.assertIn(("cs/Decls.cs::App.SVec", "external::IExternalMarker", "implements", "EXTRACTED"), edges)

    def test_csharp_qualified_base_and_enum_underlying_type(self):
        self._require_csharp()
        payload = self._build({
            "cs/Decls.cs": (
                "namespace App {\n"
                "  public class Worker : Legacy.Models.BaseThing {\n    public void Work() {}\n  }\n"
                "  public enum Level : byte { Low }\n"
                "}\n"
            ),
        })
        edges = self._rel_edges(payload, "extends", "implements")
        self.assertEqual(
            [("cs/Decls.cs::App.Worker", "external::Legacy.Models.BaseThing", "extends", "EXTRACTED")],
            edges,
            f"qualified base stays dotted; enum underlying type is never inheritance; got {edges}")

    # ---- AC-3: inherited-method + super/base resolution --------------------

    def test_java_inherited_method_binds_single_definer_with_provenance(self):
        payload = self._build({
            "com/app/AbstractRepo.java": "package com.app;\npublic abstract class AbstractRepo {\n    public void persist() {}\n}\n",
            "com/app/UserRepo.java": "package com.app;\npublic class UserRepo extends AbstractRepo {\n    public void other() {}\n}\n",
            "com/app/Service.java": "package com.app;\npublic class Service {\n    void process() {\n        UserRepo repo = new UserRepo();\n        repo.persist();\n    }\n}\n",
        })
        binds = self._calls_to(payload, "AbstractRepo.java::AbstractRepo.persist")
        binds = [e for e in binds if "Service.process" in e["source"]]
        self.assertEqual(len(binds), 1, f"inherited method must bind to the single definer; got {self._calls_to(payload, 'persist')}")
        edge = binds[0]
        self.assertEqual(edge.get("confidence"), "RECEIVER_RESOLVED")
        self.assertEqual(
            edge.get("via_supertype"), ["com/app/AbstractRepo.java"],
            "every inherited bind must carry the supertype-hop provenance (council finding)")

    def test_java_inherited_method_multi_definer_refuses(self):
        payload = self._build({
            "com/app/BaseA.java": "package com.app;\npublic class BaseA {\n    public void persist() {}\n}\n",
            "com/app/FaceB.java": "package com.app;\npublic interface FaceB {\n    default void persist() {}\n}\n",
            "com/app/Child.java": "package com.app;\npublic class Child extends BaseA implements FaceB {\n    public void other() {}\n}\n",
            "com/app/Service.java": "package com.app;\npublic class Service {\n    void process() {\n        Child c = new Child();\n        c.persist();\n    }\n}\n",
        })
        targets = [e["target"] for e in self._calls_to(payload, "persist") if "Service.process" in e["source"]]
        self.assertEqual(
            targets, ["external::Child.persist"],
            f"two definers in the walk must refuse (never guess an override winner); got {targets}")

    def test_java_super_call_binds_via_single_extends_target(self):
        payload = self._build({
            "com/app/AbstractRepo.java": "package com.app;\npublic abstract class AbstractRepo {\n    public void persist() {}\n}\n",
            "com/app/UserRepo.java": "package com.app;\npublic class UserRepo extends AbstractRepo {\n    public void persist() { super.persist(); }\n}\n",
        })
        binds = [
            e for e in self._calls_to(payload, "AbstractRepo.java::AbstractRepo.persist")
            if "UserRepo.persist" in e["source"]
        ]
        self.assertEqual(len(binds), 1, f"super.persist() must bind the extends target's method; got {self._calls_to(payload, 'persist')}")
        self.assertEqual(binds[0].get("via_supertype"), ["com/app/AbstractRepo.java"])
        self.assertEqual(binds[0].get("confidence"), "RECEIVER_RESOLVED")

    def test_java_super_call_without_project_parent_stays_external_marker(self):
        payload = self._build({
            "com/app/UserRepo.java": "package com.app;\npublic class UserRepo extends ExternalBase {\n    public void persist() { super.persist(); }\n}\n",
        })
        targets = [e["target"] for e in self._calls_to(payload, "persist") if "UserRepo.persist" in e["source"]]
        self.assertEqual(
            targets, ["external::super.UserRepo.persist"],
            f"an unbound super call must keep the explicit super marker (refusal, not a guess); got {targets}")

    def test_csharp_base_call_binds_via_extends_target(self):
        self._require_csharp()
        payload = self._build({
            "cs/BaseWorker.cs": "namespace App {\n  public class BaseWorker {\n    public void Persist() {}\n  }\n}\n",
            "cs/RealWorker.cs": "namespace App {\n  public class RealWorker : BaseWorker {\n    public void Work() { base.Persist(); }\n  }\n}\n",
        })
        binds = [
            e for e in self._calls_to(payload, "BaseWorker.cs::App.BaseWorker.Persist")
            if "RealWorker.Work" in e["source"]
        ]
        self.assertEqual(len(binds), 1, f"base.Persist() must bind; got {self._calls_to(payload, 'Persist')}")
        self.assertEqual(binds[0].get("via_supertype"), ["cs/BaseWorker.cs::App.BaseWorker"])

    def test_inherited_walk_depth_cap(self):
        """The bounded walk binds at exactly the cap and refuses beyond it."""
        depth_cap = self.mod._INHERITANCE_WALK_MAX_DEPTH
        deep = depth_cap + 1

        def chain_files(levels: int) -> dict[str, str]:
            files = {
                f"com/app/C{levels + 1}.java": (
                    f"package com.app;\npublic class C{levels + 1} {{\n    public void persist() {{}}\n}}\n"
                ),
                "com/app/Service.java": (
                    "package com.app;\npublic class Service {\n"
                    "    void process() {\n        C1 c = new C1();\n        c.persist();\n    }\n}\n"
                ),
            }
            for i in range(1, levels + 1):
                files[f"com/app/C{i}.java"] = (
                    f"package com.app;\npublic class C{i} extends C{i + 1} {{\n    public void other{i}() {{}}\n}}\n"
                )
            return files

        # chain_files(levels) puts the definer at `levels` supertype hops from
        # the receiver C1 (C1 extends C2 ... C{levels} extends C{levels+1},
        # persist defined on C{levels+1}).
        payload = self._build(chain_files(depth_cap))  # definer at exactly the cap
        bound = [e for e in self._calls_to(payload, "persist") if "Service.process" in e["source"]]
        self.assertEqual(len(bound), 1)
        self.assertTrue(bound[0]["target"].startswith(f"com/app/C{depth_cap + 1}.java"),
                        f"definer at the cap must bind; got {bound[0]['target']}")
        self.assertEqual(len(bound[0].get("via_supertype") or []), depth_cap)

        self.setUp()  # fresh temp repo for the over-cap variant
        payload = self._build(chain_files(deep))  # definer one past the cap
        targets = [e["target"] for e in self._calls_to(payload, "persist") if "Service.process" in e["source"]]
        self.assertEqual(targets, ["external::C1.persist"],
                         f"definer beyond the depth cap must refuse; got {targets}")

    def test_inherited_walk_never_through_external_supertype(self):
        """A project class whose only supertype is external:: gets NO walk —
        even when some unrelated project class defines a same-named method."""
        payload = self._build({
            "com/app/Child.java": "package com.app;\npublic class Child extends ExternalBase {\n    public void other() {}\n}\n",
            "com/app/Unrelated.java": "package com.app;\npublic class Unrelated {\n    public void persist() {}\n}\n",
            "com/app/Service.java": "package com.app;\npublic class Service {\n    void process() {\n        Child c = new Child();\n        c.persist();\n    }\n}\n",
        })
        targets = [e["target"] for e in self._calls_to(payload, "persist") if "Service.process" in e["source"]]
        self.assertEqual(
            targets, ["external::Child.persist"],
            f"the walk must never pass through an external supertype; got {targets}")

    # ---- AC-5: payload consistency + consumer ingestion ---------------------

    def test_payload_counts_consistent_with_inheritance_edges(self):
        payload = self._build({
            "com/app/AbstractRepo.java": "package com.app;\npublic abstract class AbstractRepo {\n    public void persist() {}\n}\n",
            "com/app/UserRepo.java": "package com.app;\npublic class UserRepo extends AbstractRepo implements Runnable {\n    public void run() { super.persist(); }\n}\n",
        })
        self.assertEqual(payload["counts"]["nodes"], len(payload["nodes"]))
        self.assertEqual(payload["counts"]["edges"], len(payload["edges"]))
        relations = {e["relation"] for e in payload["edges"]}
        self.assertIn("extends", relations)
        self.assertIn("implements", relations)


class JavaFieldReceiverResolutionTests(unittest.TestCase):
    """Wave 1p9qh (1p9qb): single-segment `field_access` receivers.

    `this.repo.save()` (and `Enclosing.STATIC_FIELD.m()`) resolve the field
    through a field-declaration-ONLY lookup — identical target + confidence to
    the bare form. Deeper chains and non-`this` objects keep refusing, and a
    local/parameter shadow never diverts `this.<field>` (Java semantics:
    `this.f` always denotes the field).
    """

    _SVC_BODY = (
        "package com.app;\n"
        "public class OrderService {\n"
        "    private OrderRepo repo;\n"
        "    private static OrderRepo SHARED;\n"
        "    public void run() {\n"
        "        %s\n"
        "    }\n"
        "}\n"
    )
    _REPO = "package com.app;\npublic class OrderRepo {\n    public void save() {}\n}\n"

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

    def _build(self, files: dict[str, str]) -> dict:
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

    def _save_edges(self, payload: dict) -> list[dict]:
        return [
            e for e in payload["edges"]
            if e.get("relation") == "calls"
            and "OrderService.run" in str(e.get("source", ""))
            and "save" in str(e.get("target", ""))
        ]

    def _resolve_receiver(self, java_source: str, invocation_text: str):
        """Direct `_resolve_java_receiver_type` probe for the invocation whose
        source text starts with ``invocation_text``."""
        tree = self.mod._ts_parse("java", java_source)
        sb = java_source.encode("utf-8")
        found = []

        def walk(n):
            if getattr(n, "type", "") == "method_invocation":
                text = sb[n.start_byte:n.end_byte].decode("utf-8", errors="replace")
                if text.startswith(invocation_text):
                    found.append(n)
            for c in (getattr(n, "children", []) or []):
                walk(c)

        walk(tree.root_node)
        self.assertTrue(found, f"no method_invocation starting with {invocation_text!r}")
        return self.mod._resolve_java_receiver_type(found[0], sb)

    # -- AC-1: this.<field> binds identically to the bare form ---------------

    def test_this_field_receiver_binds_identically_to_bare_form(self):
        this_form = self._build({
            "com/app/OrderRepo.java": self._REPO,
            "com/app/OrderService.java": self._SVC_BODY % "this.repo.save();",
        })
        this_edges = self._save_edges(this_form)
        self.assertEqual(
            [e["target"] for e in this_edges],
            ["com/app/OrderRepo.java::OrderRepo.save"],
            f"this.repo.save() must bind the field's declared type; got "
            f"{[(e.get('source'), e.get('target')) for e in this_edges]}",
        )
        self.setUp()  # fresh temp repo for the bare-form twin fixture
        bare_form = self._build({
            "com/app/OrderRepo.java": self._REPO,
            "com/app/OrderService.java": self._SVC_BODY % "repo.save();",
        })
        bare_edges = self._save_edges(bare_form)
        self.assertEqual(
            [e["target"] for e in bare_edges],
            ["com/app/OrderRepo.java::OrderRepo.save"],
        )
        # Identical confidence — the field's declared type carries the same
        # explicit-declaration guarantee as the bare scope walk.
        self.assertEqual(
            [e["confidence"] for e in this_edges],
            [e["confidence"] for e in bare_edges],
            "this.<field> must carry the same confidence as the bare form",
        )

    def test_static_field_via_enclosing_class_name_binds(self):
        payload = self._build({
            "com/app/OrderRepo.java": self._REPO,
            "com/app/OrderService.java": self._SVC_BODY % "OrderService.SHARED.save();",
        })
        targets = [e["target"] for e in self._save_edges(payload)]
        self.assertEqual(
            targets, ["com/app/OrderRepo.java::OrderRepo.save"],
            f"Enclosing.STATIC_FIELD.m() must bind the field's declared type; got {targets}",
        )

    def test_deeper_chain_still_refuses(self):
        src = self._SVC_BODY % "this.repo.inner.save();"
        self.assertIsNone(
            self._resolve_receiver(src, "this.repo.inner.save"),
            "a two-segment field path must stay uncertain (documented give-up)",
        )

    def test_non_this_object_field_path_still_refuses(self):
        src = self._SVC_BODY % "other.repo.save();"
        self.assertIsNone(
            self._resolve_receiver(src, "other.repo.save"),
            "a non-this/non-enclosing-class field path must stay uncertain",
        )

    # -- Adversarial: shadowing (the Risks-table case) ------------------------

    def test_local_shadow_never_diverts_this_field(self):
        """A local `String repo` shadows the field for the BARE form only:
        `this.repo` explicitly bypasses the shadow (Java semantics), so the
        two forms resolve to DIFFERENT types here — and should."""
        src = self._SVC_BODY % 'String repo = "shadow";\n        this.repo.save();\n        repo.save();'
        self.assertEqual(
            self._resolve_receiver(src, "this.repo.save"), "OrderRepo",
            "this.repo must consult FIELD declarations only, bypassing the local shadow",
        )
        self.assertEqual(
            self._resolve_receiver(src, "repo.save"), "String",
            "the bare form must still see the local shadow (scope-walk order unchanged)",
        )

    def test_parameter_shadow_never_diverts_this_field(self):
        src = (
            "package com.app;\n"
            "public class OrderService {\n"
            "    private OrderRepo repo;\n"
            "    public void run(String repo) {\n"
            "        this.repo.save();\n"
            "    }\n"
            "}\n"
        )
        self.assertEqual(
            self._resolve_receiver(src, "this.repo.save"), "OrderRepo",
            "a parameter shadow must not divert this.<field>",
        )

    def test_undeclared_this_field_refuses(self):
        """`this.ghost` with no such field declaration (e.g. inherited field)
        stays uncertain — never guessed."""
        src = self._SVC_BODY % "this.ghost.save();"
        self.assertIsNone(self._resolve_receiver(src, "this.ghost.save"))


class JavaAnnotationTypeKindTests(unittest.TestCase):
    """Wave 1p9qh (1p9qb): `@interface` classifies as kind "class" (it is a
    TYPE declaration), reviving the previously-dead basename-merge path; no
    other language's kind classification moves."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, files: dict[str, str]) -> dict:
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

    def test_annotation_type_declaration_classifies_as_class(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        payload = self._build({
            "com/app/Anno.java": "package com.app;\npublic @interface Cacheable { String value(); }\n",
        })
        anno = [n for n in payload["nodes"] if n["id"] == "com/app/Anno.java::Cacheable"]
        self.assertTrue(anno, f"annotation type node missing; got {[n['id'] for n in payload['nodes']]}")
        self.assertEqual(anno[0]["kind"], "class",
                         "@interface must classify as a type (kind 'class'), not 'function'")

    def test_annotation_basename_match_merges_via_revived_path(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")
        payload = self._build({
            "Cacheable.java": "package com.app;\npublic @interface Cacheable { String value(); }\n",
        })
        node_ids = {n["id"] for n in payload["nodes"]}
        self.assertIn("Cacheable.java", node_ids)
        self.assertNotIn("Cacheable.java::Cacheable", node_ids,
                         "basename-matching @interface must merge into the file node")
        merged = next(n for n in payload["nodes"] if n["id"] == "Cacheable.java")
        self.assertEqual(merged["label"], "Cacheable")
        self.assertEqual(merged["kind"], "class")
        self.assertTrue(merged.get("collapsed_pair"))

    def test_kind_classification_regression_pins_other_languages(self):
        """The annotation fix is an EXACT node-type match; every neighboring
        classification is pinned so no other language's kind moves."""
        kind = self.mod._ts_kind_for_definition
        # Java: the annotation fix itself + its method-shaped body members.
        self.assertEqual(kind("annotation_type_declaration", None, "code"), "class")
        self.assertEqual(kind("annotation_type_element_declaration", None, "code"), "function",
                         "@interface members (`String value();`) are method-shaped and stay 'function'")
        # Java/C#/Kotlin type declarations (normalize to 'class', unchanged).
        self.assertEqual(kind("class_declaration", None, "code"), "class")
        self.assertEqual(kind("interface_declaration", None, "code"), "class")
        self.assertEqual(kind("enum_declaration", None, "code"), "class")
        self.assertEqual(kind("record_declaration", None, "code"), "class")
        self.assertEqual(kind("method_declaration", None, "code"), "function")
        self.assertEqual(kind("package_declaration", None, "code"), "module")
        # Rust / Go / TS / JS pins.
        self.assertEqual(kind("struct_item", None, "code"), "class")
        self.assertEqual(kind("trait_item", None, "code"), "class")
        self.assertEqual(kind("function_declaration", None, "code"), "function")
        self.assertEqual(kind("type_alias_declaration", None, "code"), "type")
        self.assertEqual(kind("property_signature", None, "code"), "property")
        self.assertEqual(kind("lexical_declaration", None, "code"), "variable")
        # Non-code modes untouched.
        self.assertEqual(kind("create_table_statement", None, "sql"), "class")
        self.assertEqual(kind("workflow_block", None, "config"), "function")
        self.assertEqual(kind("element_node", None, "markup"), "class")


class JavaPackageDeclarationKeyingTests(unittest.TestCase):
    """Wave 1p9qh (1p9qb): the Java/Kotlin same-package disambiguation tier
    keys on the parsed `package` declaration (directory fallback for
    declaration-less files); Go keeps directory keying. Both flip directions
    are deliberate correctness changes."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _require_java(self):
        try:
            import tree_sitter_java  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_java not available in test env")

    def _build(self, files: dict[str, str]) -> dict:
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

    def _go_targets(self, payload: dict) -> list[str]:
        return [
            e["target"] for e in payload["edges"]
            if e.get("relation") == "calls"
            and "Foo.run" in str(e.get("source", ""))
            and "go" in str(e.get("target", ""))
        ]

    # -- AC-3 flip 1: same declared package across directories now binds -----

    def test_split_directory_same_declared_package_disambiguates(self):
        self._require_java()
        payload = self._build({
            "a/Foo.java": "package com.x;\npublic class Foo { Bar b; void run() { b.go(); } }\n",
            "b/Bar.java": "package com.x;\npublic class Bar { public void go() {} }\n",
            "c/Bar.java": "package com.y;\npublic class Bar { public void go() {} }\n",
        })
        targets = self._go_targets(payload)
        self.assertEqual(
            targets, ["b/Bar.java::Bar.go"],
            f"the same-DECLARED-package twin must bind even across directories; got {targets}",
        )

    # -- AC-3 flip 2: same directory, different declared packages now refuse --

    def test_same_directory_different_declared_packages_refuse(self):
        self._require_java()
        payload = self._build({
            "d/Foo.java": "package com.a;\npublic class Foo { Bar b; void run() { b.go(); } }\n",
            "d/Bar.java": "package com.b;\npublic class Bar { public void go() {} }\n",
            "e/Bar.java": "package com.c;\npublic class Bar { public void go() {} }\n",
        })
        targets = self._go_targets(payload)
        self.assertEqual(
            targets, ["external::Bar.go"],
            f"a co-located but DIFFERENT-package twin must refuse; got {targets}",
        )

    # -- Declaration-less fallback preserves pre-1p9qb behavior ---------------

    def test_declaration_less_files_fall_back_to_directory_keying(self):
        self._require_java()
        payload = self._build({
            "d/Foo.java": "public class Foo { Bar b; void run() { b.go(); } }\n",
            "d/Bar.java": "public class Bar { public void go() {} }\n",
            "e/Bar.java": "public class Bar { public void go() {} }\n",
        })
        targets = self._go_targets(payload)
        self.assertEqual(
            targets, ["d/Bar.java::Bar.go"],
            f"package-less files keep directory locality (default package); got {targets}",
        )

    # -- Kotlin parity: the rekeyed tier is Java/KOTLIN (red-team F3) ----------

    def test_kotlin_split_directory_same_declared_package_disambiguates(self):
        """`_KOTLIN_PKG_DECL_RE` shipped with zero `.kt` unit fixtures; this
        mirrors the Java AC-3 positive flip in Kotlin syntax so the Kotlin half
        of the package-keyed tier is pinned in the suite, not only empirically
        (adversarial C6 probe)."""
        try:
            import tree_sitter_kotlin  # noqa: F401
        except ImportError:
            self.skipTest("tree_sitter_kotlin not available in test env")
        payload = self._build({
            "a/Foo.kt": "package com.x\nclass Foo {\n    val b: Bar = Bar()\n    fun run() { b.go() }\n}\n",
            "b/Bar.kt": "package com.x\nclass Bar {\n    fun go() {}\n}\n",
            "c/Bar.kt": "package com.y\nclass Bar {\n    fun go() {}\n}\n",
        })
        targets = self._go_targets(payload)
        self.assertEqual(
            targets, ["b/Bar.kt::Bar.go"],
            f"the same-DECLARED-package Kotlin twin must bind even across directories; got {targets}",
        )

    # -- Unit-level adversarial pins on the pure resolver ---------------------

    def _resolve(self, src: str, bare: str, *, simple: dict, pkg_map: dict):
        resolved, _ = self.mod._resolve_external_call_target(
            src, bare, "EXTRACTED",
            simple_name_index=simple,
            qualified_index={},
            imports_by_file={},
            cs_file_ns={},
            wildcard_imports_by_file=None,
            java_pkg_by_file=pkg_map,
        )
        return resolved

    def test_unit_go_keying_ignores_declared_package_map(self):
        """Go stays on directory keying even when a (nonsensical) package map
        entry exists for its files — a Go package IS its directory."""
        simple = {"helper": ["p/a.go::helper", "q/a.go::helper"]}
        resolved = self._resolve(
            "p/main.go::main", "helper",
            simple=simple,
            pkg_map={"p/a.go": "junkpkg", "q/a.go": "junkpkg", "p/main.go": "junkpkg"},
        )
        self.assertEqual(resolved, "p/a.go::helper",
                         "Go same-dir keying must be unaffected by the Java package map")

    def test_unit_declared_and_undeclared_keys_never_cross_match(self):
        """A declared package can never equal a directory-fallback key (the
        pkg:/dir: prefixes keep the key spaces disjoint): a caller declaring
        `package d` does NOT match a declaration-less candidate in directory
        `d/`."""
        simple = {"go": ["d/Bar.java::Bar.go", "e/Bar.java::Bar.go"]}
        resolved = self._resolve(
            "d/Foo.java::Foo.run", "go",
            simple=simple,
            pkg_map={"d/Foo.java": "d"},  # candidates have NO declaration
        )
        self.assertIsNone(resolved,
                          "declared-package key must never match a directory-fallback key")


class SuperMarkerCallsInvariantTests(unittest.TestCase):
    """Wave 1p9qh red-team F4: the `external::super.` prefix is NOT globally
    unmintable — Rust `use super::…` imports mint `external::super.*` ids too.
    The actual marker-safety contract: the finalize inheritance pass filters to
    `calls`-relation edges, and every language's CALLS extraction independently
    refuses `super` receivers, so in a mixed-language payload the ONLY
    `external::super.`-prefixed `calls` targets are the Java/C# markers
    (Rust's `super.*` ids ride the `imports` relation, which is allowed)."""

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_java_csharp_markers_appear_on_calls_edges(self):
        import importlib.util
        for grammar in ("tree_sitter_java", "tree_sitter_c_sharp",
                        "tree_sitter_kotlin", "tree_sitter_rust"):
            if importlib.util.find_spec(grammar) is None:
                self.skipTest(f"{grammar} not available in test env")
        files = {
            # Rust: `use super::…` mints external::super.* ids — imports relation, allowed.
            "rustmod/b.rs": "use super::util::Reader;\npub fn caller() {}\n",
            # Java: external supertype keeps the marker unresolved so it persists in the payload.
            "j/Child.java": "public class Child extends LibraryBase {\n    void run() { super.persist(); }\n}\n",
            # C#: same marker via `base.` with an external base.
            "cs/Child2.cs": "public class Child2 : LibBase {\n    public void Run() { base.Validate(); }\n}\n",
            # Kotlin: the call path refuses `super` receivers — no marker, no super.-target.
            "k/KChild.kt": "package k\nclass KChild {\n    fun run() { super.toString() }\n}\n",
        }
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": content}
        payload = self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )
        super_calls = sorted({
            str(e.get("target")) for e in payload["edges"]
            if e.get("relation") == "calls"
            and str(e.get("target", "")).startswith("external::super.")
        })
        self.assertEqual(
            super_calls,
            ["external::super.Child.persist", "external::super.Child2.Validate"],
            f"only the Java/C# reserved markers may ride `calls`; got {super_calls}",
        )
        super_imports = [
            str(e.get("target")) for e in payload["edges"]
            if e.get("relation") == "imports"
            and str(e.get("target", "")).startswith("external::super.")
        ]
        self.assertTrue(
            super_imports,
            "the Rust `use super::…` import must mint an external::super.* id "
            "(the collision the reserved-word argument denied — it rides `imports`)",
        )


class _EmbeddedSqlTestBase(unittest.TestCase):
    """Shared harness for wave 1p9qi / 1p9qf embedded-SQL capture + bind tests."""

    SCHEMA = (
        "CREATE TABLE users (id INT PRIMARY KEY, name TEXT);\n"
        "CREATE TABLE audit_log (id INT, age INT);\n"
        "CREATE TABLE analytics.events (id INT);\n"
    )

    def setUp(self):
        self.mod = load_graph_indexer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _require(self, *langs: str):
        for lang in langs:
            if getattr(self.mod, "_ts_get_parser", lambda *_: None)(lang) is None:
                self.skipTest(f"tree-sitter {lang} grammar unavailable")

    def _build(self, files: dict[str, str]):
        paths, meta = [], {}
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
            meta[rel.replace("\\", "/")] = {"hash": f"h-{rel}"}
        return self.mod.update_graph_index(
            root=self.root, index_dir=self.root / ".wavefoundry" / "index",
            layer="project", files=paths, current_file_meta=meta,
            changed=set(meta.keys()), removed=set(),
            walker_version="1", chunker_version="1", verbose=False,
        )

    def _literal_sql_edges(self, payload) -> list[tuple[str, str, str]]:
        """Exact (source, target, relation) set of reads/writes @ LITERAL_DERIVED."""
        return sorted(
            (str(e["source"]), str(e["target"]), str(e["relation"]))
            for e in payload.get("edges", [])
            if e.get("confidence") == "LITERAL_DERIVED"
            and e.get("relation") in ("reads", "writes")
        )

    def _sql_stats(self, payload) -> dict:
        return (payload.get("merge_stats") or {}).get("sql_capture") or {}


class EmbeddedSqlJavaCaptureTests(_EmbeddedSqlTestBase):
    """AC-1: Java sinks — MyBatis annotations, native @Query, JDBC prepare*,
    JdbcTemplate methods — capture and bind method → table at LITERAL_DERIVED."""

    def test_mybatis_select_annotation_binds_exact_edge_set(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/UserMapper.java": (
                "public interface UserMapper {\n"
                "  @Select(\"SELECT * FROM users WHERE id = #{id}\")\n"
                "  Object findUser(int id);\n"
                "  @Delete(\"DELETE FROM audit_log WHERE age > #{age}\")\n"
                "  int prune(int age);\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/UserMapper.java::UserMapper.findUser", "db/schema.sql::users", "reads"),
            ("src/UserMapper.java::UserMapper.prune", "db/schema.sql::audit_log", "writes"),
        ])

    def test_native_query_binds_and_jpql_captures_nothing(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/EventRepo.java": (
                "public interface EventRepo {\n"
                "  @Query(value = \"SELECT * FROM analytics.events\", nativeQuery = true)\n"
                "  java.util.List<Object> events();\n"
                "  @Query(\"SELECT u FROM User u\")\n"
                "  java.util.List<Object> jpql();\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/EventRepo.java::EventRepo.events", "db/schema.sql::analytics.events", "reads"),
        ])

    def test_prepare_statement_and_jdbc_template_bind(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn, JdbcTemplate jdbc) {\n"
                "    conn.prepareStatement(\"SELECT * FROM users WHERE id = ?\");\n"
                "    jdbc.update(\"DELETE FROM audit_log WHERE age > ?\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/Dao.java::Dao.run", "db/schema.sql::audit_log", "writes"),
            ("src/Dao.java::Dao.run", "db/schema.sql::users", "reads"),
        ])

    def test_adjacent_literal_concatenation_binds(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn) {\n"
                "    conn.prepareStatement(\"SELECT * \" + \"FROM users \" + \"WHERE id = ?\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/Dao.java::Dao.run", "db/schema.sql::users", "reads"),
        ])

    def test_generic_template_method_requires_positive_receiver_origin(self):
        # `update`/`query` are generic names: no capture without a receiver
        # that RESOLVES to JdbcTemplate/NamedParameterJdbcTemplate.
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(Object jdbc) {\n"
                "    jdbc.update(\"DELETE FROM audit_log WHERE age > ?\");\n"
                "    getTemplate().update(\"DELETE FROM audit_log WHERE age > ?\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])


class EmbeddedSqlCSharpCaptureTests(_EmbeddedSqlTestBase):
    """AC-2: C# sinks — SqlCommand/CommandText, Dapper, EF raw — capture and bind."""

    def test_sqlcommand_commandtext_dapper_and_ef_bind_exact_edge_set(self):
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/Repo.cs": (
                "public class Repo {\n"
                "  public void Run(IDbConnection conn, AppDbContext db) {\n"
                "    var cmd = new SqlCommand(\"SELECT * FROM users\");\n"
                "    cmd.CommandText = \"UPDATE users SET name = 'x'\";\n"
                "    var rows = conn.Query<object>(\"SELECT * FROM audit_log\");\n"
                "    db.Db.ExecuteSqlRaw(\"DELETE FROM analytics.events\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [
            ("cs/Repo.cs::Repo.Run", "db/schema.sql::analytics.events", "writes"),
            ("cs/Repo.cs::Repo.Run", "db/schema.sql::audit_log", "reads"),
            ("cs/Repo.cs::Repo.Run", "db/schema.sql::users", "reads"),
            ("cs/Repo.cs::Repo.Run", "db/schema.sql::users", "writes"),
        ])

    def test_interpolated_string_at_sink_is_dynamic_refusal(self):
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/Repo.cs": (
                "public class Repo {\n"
                "  public void Run(AppDbContext db, string t) {\n"
                "    db.Db.ExecuteSqlRaw($\"DELETE FROM {t}\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])
        self.assertEqual(self._sql_stats(payload).get("dynamic_refused"), 1)


class EmbeddedSqlMyBatisXmlTests(_EmbeddedSqlTestBase):
    """AC-3: MyBatis mapper XML statements bind with the mapper
    namespace/interface as source."""

    def test_mapper_statement_binds_with_interface_source(self):
        self._require("java", "xml", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "com/example/OrderMapper.java": (
                "public interface OrderMapper {\n"
                "  java.util.List<Object> findAll();\n"
                "}\n"
            ),
            "mappers/OrderMapper.xml": (
                "<?xml version=\"1.0\"?>\n"
                "<mapper namespace=\"com.example.OrderMapper\">\n"
                "  <select id=\"findAll\">SELECT * FROM users</select>\n"
                "</mapper>\n"
            ),
        })
        edges = self._literal_sql_edges(payload)
        self.assertEqual(len(edges), 1, edges)
        source, target, relation = edges[0]
        # The unique project interface (basename-collapsed to the file node)
        # is the bind source — namespace → interface resolution.
        self.assertEqual(source, "com/example/OrderMapper.java")
        self.assertEqual(target, "db/schema.sql::users")
        self.assertEqual(relation, "reads")

    def test_dynamic_statement_tags_and_substitution_refused_and_counted(self):
        self._require("xml", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "mappers/OrderMapper.xml": (
                "<?xml version=\"1.0\"?>\n"
                "<mapper namespace=\"com.example.OrderMapper\">\n"
                "  <select id=\"dyn1\">SELECT * FROM users <where><if test=\"x\">id = #{x}</if></where></select>\n"
                "  <update id=\"dyn2\">UPDATE users SET n = ${col}</update>\n"
                "</mapper>\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])
        self.assertEqual(self._sql_stats(payload).get("dynamic_refused"), 2)

    def test_non_mapper_xml_captures_nothing(self):
        self._require("xml", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "conf/beans.xml": (
                "<beans>\n"
                "  <select id=\"notMyBatis\">SELECT * FROM users</select>\n"
                "</beans>\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])


class EmbeddedSqlFaithfulnessTests(_EmbeddedSqlTestBase):
    """AC-4: adversarial negatives — impostor sinks, non-SQL strings, strings
    outside sinks, dynamic refusal, ambiguity drop, namespaced externals."""

    def test_java_impostor_prepare_statement_refuses(self):
        # A PROJECT type defining prepareStatement is never a JDBC sink.
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/Impostor.java": (
                "class QueryRunner {\n"
                "  Object prepareStatement(String s) { return null; }\n"
                "}\n"
                "class Caller {\n"
                "  void go() {\n"
                "    QueryRunner qr = new QueryRunner();\n"
                "    qr.prepareStatement(\"SELECT * FROM users\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])

    def test_csharp_impostor_dapper_receiver_refuses(self):
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/Impostor.cs": (
                "public class MyRepo {\n"
                "  public object Query(string s) { return null; }\n"
                "}\n"
                "public class Caller {\n"
                "  public void Go() {\n"
                "    MyRepo r = new MyRepo();\n"
                "    r.Query(\"SELECT * FROM users\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])

    def test_sql_looking_strings_outside_sinks_never_capture(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/NotASink.java": (
                "public class NotASink {\n"
                "  static final String Q = \"SELECT * FROM users\";\n"
                "  void go(Object log) {\n"
                "    log.info(\"SELECT * FROM users\");\n"
                "    helper(\"DELETE FROM audit_log\");\n"
                "  }\n"
                "  void helper(String s) {}\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])

    def test_non_sql_string_at_sink_drops_silently(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn) {\n"
                "    conn.prepareStatement(\"users-all-cache-key\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])
        # Silent drop: not SQL, so not a dynamic refusal either.
        self.assertEqual(self._sql_stats(payload).get("dynamic_refused", 0), 0)

    def test_dynamic_sql_refused_and_counted(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn, String tbl) {\n"
                "    conn.prepareStatement(sqlFor(tbl));\n"
                "    conn.prepareStatement(\"SELECT * FROM \" + tbl);\n"
                "  }\n"
                "  String sqlFor(String t) { return t; }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])
        self.assertEqual(self._sql_stats(payload).get("dynamic_refused"), 2)

    def test_ambiguous_table_name_drops_edge(self):
        # Two same-named tables (dev + prod DDL) → the reference binds NEITHER
        # and does NOT go external — unique-match-or-drop.
        self._require("java", "sql")
        payload = self._build({
            "db/dev.sql": "CREATE TABLE users (id INT);\n",
            "db/prod.sql": "CREATE TABLE users (id INT);\n",
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn) {\n"
                "    conn.prepareStatement(\"SELECT * FROM users\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [])
        self.assertEqual(self._sql_stats(payload).get("ambiguous_dropped"), 1)

    def test_schema_qualified_match_beats_bare_leaf(self):
        # `analytics.events` matches the schema-qualified node exactly even
        # when a bare `events` table also exists.
        self._require("java", "sql")
        payload = self._build({
            "db/a.sql": "CREATE TABLE analytics.events (id INT);\n",
            "db/b.sql": "CREATE TABLE events (id INT);\n",
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn) {\n"
                "    conn.prepareStatement(\"SELECT * FROM analytics.events\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/Dao.java::Dao.run", "db/a.sql::analytics.events", "reads"),
        ])

    def test_backtick_quoted_ddl_binds_bare_reference(self):
        # Census finding (Apache Fineract): MySQL dump DDL declares
        # `` `m_loan` `` (backticks preserved by the names-as-written unit
        # contract) while embedded Java SQL references bare `m_loan` — the
        # bind match normalizes identifier quotes on both sides.
        self._require("java", "sql")
        payload = self._build({
            "db/dump.sql": (
                "CREATE TABLE `m_loan` (\n"
                "  `id` BIGINT NOT NULL AUTO_INCREMENT,\n"
                "  PRIMARY KEY (`id`)\n"
                ") ENGINE=InnoDB;\n"
            ),
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn) {\n"
                "    conn.prepareStatement(\"SELECT * FROM m_loan WHERE id = ?\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/Dao.java::Dao.run", "db/dump.sql::`m_loan`", "reads"),
        ])

    def test_unmatched_table_mints_namespaced_external_only(self):
        self._require("java", "sql")
        payload = self._build({
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn) {\n"
                "    conn.prepareStatement(\"SELECT * FROM missing_tbl\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/Dao.java::Dao.run", "external::sql::missing_tbl", "reads"),
        ])
        bare_external = [
            e for e in payload["edges"]
            if str(e.get("target")) == "external::missing_tbl"
        ]
        self.assertEqual(bare_external, [], "unmatched tables must use the sql:: namespace")


class ExternalSqlNamespaceInvariantTests(_EmbeddedSqlTestBase):
    """Wave 1p9qi (1p9qf) freshness finding: `external::sql::` is not globally
    unmintable, so the safety contract is RELATION-SCOPED (mirrors the
    `super.`/`staticorinherited#` reserved-marker treatment): only the finalize
    bind passes mint `external::sql::` targets, only on reads/writes/maps_to
    (1p9qg extends the contract to the ORM mapping pass) at LITERAL_DERIVED,
    and only into the OUTPUT edge map — never into fragments.
    A Rust `use sql::…` import mints the DOTTED `external::sql.…` form on
    `imports` (disjoint by form AND relation)."""

    def test_rust_use_sql_does_not_collide_with_namespace(self):
        self._require("java", "rust", "sql")
        payload = self._build({
            "rustmod/lib.rs": "use sql::users;\npub fn caller() {}\n",
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn) {\n"
                "    conn.prepareStatement(\"SELECT * FROM users\");\n"
                "  }\n"
                "}\n"
            ),
        })
        rust_imports = [
            str(e.get("target")) for e in payload["edges"]
            if str(e.get("source", "")).startswith("rustmod/") and e.get("relation") == "imports"
        ]
        self.assertIn("external::sql.users", rust_imports,
                      "Rust `use sql::users` must mint the DOTTED import form")
        # The relation-scoped invariant: every `external::sql::`-prefixed
        # target in the payload rides reads/writes/maps_to at LITERAL_DERIVED
        # — nothing else may carry the namespace.
        for e in payload["edges"]:
            if str(e.get("target", "")).startswith("external::sql::"):
                self.assertIn(e.get("relation"), ("reads", "writes", "maps_to"), e)
                self.assertEqual(e.get("confidence"), "LITERAL_DERIVED", e)
        # And the bind pass never binds THROUGH a source-minted lookalike:
        # `users` has no sql_kind node here, so the capture goes external
        # under the namespace instead of touching the Rust import target.
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/Dao.java::Dao.run", "external::sql::users", "reads"),
        ])

    def test_bind_edges_are_finalize_only_never_in_fragments(self):
        self._require("java", "sql")
        self._build({
            "db/schema.sql": self.SCHEMA,
            "src/Dao.java": (
                "public class Dao {\n"
                "  void run(java.sql.Connection conn) {\n"
                "    conn.prepareStatement(\"SELECT * FROM users\");\n"
                "    conn.prepareStatement(\"SELECT * FROM missing_tbl\");\n"
                "  }\n"
                "}\n"
            ),
        })
        store = self.mod.GraphStateStore(
            self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.sqlite",
            layer="project", walker_version="1", chunker_version="1",
        )
        try:
            merge_state = store.get_blob("merge_state") or {}
            files = merge_state.get("files") or {}
            self.assertIn("src/Dao.java", files)
            entry = files["src/Dao.java"]
            # The capture candidates ride the fragment…
            cands = entry.get("sql_capture_candidates") or []
            self.assertEqual(len(cands), 2, cands)
            # …but the minted edges do NOT: no fragment edge (any file) may
            # carry an external::sql:: target or a LITERAL_DERIVED reads/writes.
            for rel, fentry in files.items():
                for edge in fentry.get("edges", []) or []:
                    self.assertFalse(
                        str(edge.get("target", "")).startswith("external::sql::"),
                        f"fragment edge in {rel} carries a bind-pass target: {edge}",
                    )
                    if edge.get("relation") in ("reads", "writes", "maps_to"):
                        self.assertNotEqual(edge.get("confidence"), "LITERAL_DERIVED", edge)
        finally:
            store.close()


class EmbeddedSqlConsumerParityTests(_EmbeddedSqlTestBase):
    """AC-5: bound edges carry LITERAL_DERIVED and are down-weighted in
    impact/path exactly like the existing literal-derived edge family."""

    def _load_graph_query(self):
        path = SCRIPTS_ROOT / "graph_query.py"
        spec = importlib.util.spec_from_file_location("graph_query_parity_test", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["graph_query_parity_test"] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_literal_derived_weight_and_path_cost_parity(self):
        gq = self._load_graph_query()
        sql_edge = {"source": "a.java::A.m", "target": "db/s.sql::users",
                    "relation": "reads", "confidence": "LITERAL_DERIVED"}
        sql_write = {"source": "a.java::A.m", "target": "db/s.sql::users",
                     "relation": "writes", "confidence": "LITERAL_DERIVED"}
        config_edge = {"source": "a.java::A.m", "target": "app.yml::k",
                       "relation": "reads_config", "confidence": "LITERAL_DERIVED"}
        # Blast-radius weight: identical to the existing literal family
        # (down-weighted, never full).
        self.assertEqual(
            gq._edge_confidence_weight(sql_edge),
            gq._edge_confidence_weight(config_edge),
        )
        self.assertEqual(gq._edge_confidence_weight(sql_edge), gq._EXTRACTED_EDGE_WEIGHT)
        self.assertEqual(gq._edge_confidence_weight(sql_write), gq._EXTRACTED_EDGE_WEIGHT)
        # Path cost: structural tier — a literal-derived table hop must never
        # out-compete a call chain.
        self.assertEqual(gq._path_edge_cost(sql_edge), gq._PATH_COST_STRUCTURAL)
        self.assertEqual(gq._path_edge_cost(sql_write), gq._PATH_COST_STRUCTURAL)


class AnnotationArgumentSeamTests(_EmbeddedSqlTestBase):
    """The shared annotation/attribute-argument seam (built by 1p9qf,
    extended by 1p9qg): structured {name, args, pairs} records with AST-node
    values on both languages."""

    def _first_node_of_type(self, root, node_type: str):
        stack = [root]
        while stack:
            node = stack.pop(0)
            if str(getattr(node, "type", "") or "") == node_type:
                return node
            stack.extend(getattr(node, "named_children", []) or [])
        return None

    def test_java_annotation_records_shape(self):
        self._require("java")
        source = (
            "public interface R {\n"
            "  @Query(value = \"SELECT 1\", nativeQuery = true)\n"
            "  @Deprecated\n"
            "  Object q();\n"
            "}\n"
        )
        tree = self.mod._ts_parse("java", source)
        method = self._first_node_of_type(tree.root_node, "method_declaration")
        records = self.mod._ts_java_annotation_records(method, source.encode("utf-8"))
        by_name = {r["name"]: r for r in records}
        self.assertIn("Query", by_name)
        self.assertIn("Deprecated", by_name)
        query = by_name["Query"]
        self.assertEqual(sorted(query["pairs"]), ["nativeQuery", "value"])
        sb = source.encode("utf-8")
        self.assertEqual(
            self.mod._java_literal_string_expr(query["pairs"]["value"], sb), "SELECT 1")
        self.assertEqual(
            self.mod._ts_node_text(query["pairs"]["nativeQuery"], sb).strip(), "true")
        self.assertEqual(by_name["Deprecated"]["args"], [])
        self.assertEqual(by_name["Deprecated"]["pairs"], {})

    def test_csharp_attribute_records_shape(self):
        self._require("csharp")
        source = (
            "[Table(\"users\")]\n"
            "public class E {\n"
            "  [Column(Order = 2, Name = \"col\")]\n"
            "  public void M() {}\n"
            "}\n"
        )
        tree = self.mod._ts_parse("csharp", source)
        sb = source.encode("utf-8")
        cls = self._first_node_of_type(tree.root_node, "class_declaration")
        cls_records = self.mod._ts_csharp_attribute_records(cls, sb)
        self.assertEqual(len(cls_records), 1)
        self.assertEqual(cls_records[0]["name"], "Table")
        self.assertEqual(
            self.mod._csharp_literal_string_expr(cls_records[0]["args"][0], sb), "users")
        method = self._first_node_of_type(tree.root_node, "method_declaration")
        m_records = self.mod._ts_csharp_attribute_records(method, sb)
        self.assertEqual(len(m_records), 1)
        column = m_records[0]
        self.assertEqual(column["name"], "Column")
        self.assertEqual(sorted(column["pairs"]), ["Name", "Order"])
        self.assertEqual(
            self.mod._csharp_literal_string_expr(column["pairs"]["Name"], sb), "col")


class _OrmEntityMappingTestBase(_EmbeddedSqlTestBase):
    """Shared harness for wave 1p9qi / 1p9qg ORM entity→table mapping tests."""

    def _maps_to_edges(self, payload) -> list[tuple[str, str, str]]:
        """Exact (source, target, confidence) set of `maps_to` edges."""
        return sorted(
            (str(e["source"]), str(e["target"]), str(e.get("confidence")))
            for e in payload.get("edges", [])
            if e.get("relation") == "maps_to"
        )

    def _orm_stats(self, payload) -> dict:
        return (payload.get("merge_stats") or {}).get("entity_mapping") or {}


class OrmEntityMappingJavaTests(_OrmEntityMappingTestBase):
    """AC-1: JPA — `@Entity` + `@Table(name = "…")` (and schema-qualified /
    `@Entity(name = "…")` forms) bind class → table on `maps_to` at
    LITERAL_DERIVED; a bare `@Entity` binds NOTHING and increments the
    convention counter (declared names only — standing wave decision)."""

    def test_table_name_binds_collapsed_and_nested_exact_edge_set(self):
        # The file-dominant entity (User.java defining class User) collapses
        # into the module node — the mapping must ride the collapsed id; a
        # nested (non-dominant) entity keeps its class node id.
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/User.java": (
                "@Entity\n"
                "@Table(name = \"users\")\n"
                "public class User { private long id; }\n"
            ),
            "src/Models.java": (
                "public class Models {}\n"
                "@Entity\n"
                "@Table(name = \"events\", schema = \"analytics\")\n"
                "class EventRecord { }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("src/Models.java::EventRecord", "db/schema.sql::analytics.events", "LITERAL_DERIVED"),
            ("src/User.java", "db/schema.sql::users", "LITERAL_DERIVED"),
        ])
        stats = self._orm_stats(payload)
        self.assertEqual(stats.get("bound"), 2, stats)
        self.assertEqual(stats.get("convention_refused"), 0, stats)
        self.assertEqual(stats.get("dynamic_refused"), 0, stats)

    def test_entity_name_element_binds_without_table_annotation(self):
        # @Entity(name = "…") is the JPA-spec EXPLICIT entity name (the table
        # name defaults to it verbatim) — a declared string, not a derived
        # convention, so it binds when @Table declares no name.
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/AuditEntry.java": (
                "@Entity(name = \"audit_log\")\n"
                "public class AuditEntry { }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("src/AuditEntry.java", "db/schema.sql::audit_log", "LITERAL_DERIVED"),
        ])

    def test_bare_entity_refuses_convention_temptation(self):
        # Class `User` + existing table `users`: the snake_case/pluralize
        # guess the standing decision forbids. NO edge; counted refusal.
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/User.java": "@Entity\npublic class User { }\n",
        })
        self.assertEqual(self._maps_to_edges(payload), [])
        stats = self._orm_stats(payload)
        self.assertEqual(stats.get("convention_refused"), 1, stats)
        self.assertEqual(stats.get("bound"), 0, stats)

    def test_constant_reference_table_name_refuses_dynamic(self):
        # Only string literals bind: @Table(name = TABLE_NAME) refuses as a
        # counted dynamic case — never resolved, never guessed (AC-3).
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/User.java": (
                "@Entity\n"
                "@Table(name = User.TABLE_NAME)\n"
                "public class User { static final String TABLE_NAME = \"users\"; }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [])
        stats = self._orm_stats(payload)
        self.assertEqual(stats.get("dynamic_refused"), 1, stats)
        self.assertEqual(stats.get("bound"), 0, stats)

    def test_table_without_entity_never_fires(self):
        # A bare @Table without @Entity is some other framework's annotation
        # — the @Entity presence is the Java origin gate. No edge, no counter.
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/NotAnEntity.java": (
                "@Table(name = \"users\")\n"
                "public class NotAnEntity { }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [])
        self.assertEqual(self._orm_stats(payload), {})

    def test_jpql_query_untouched_alongside_mapping(self):
        # The mapping layer must not disturb the 1p9qf JPQL exclusion: a JPQL
        # @Query on the entity's repository captures nothing while the
        # entity's declared mapping still binds.
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/User.java": (
                "@Entity\n"
                "@Table(name = \"users\")\n"
                "public class User { }\n"
            ),
            "src/UserRepo.java": (
                "public interface UserRepo {\n"
                "  @Query(\"SELECT u FROM User u WHERE u.id = :id\")\n"
                "  Object byId(long id);\n"
                "}\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("src/User.java", "db/schema.sql::users", "LITERAL_DERIVED"),
        ])
        jpql_edges = [
            e for e in payload["edges"]
            if str(e.get("source", "")).startswith("src/UserRepo.java")
            and e.get("relation") in ("reads", "writes", "maps_to")
        ]
        self.assertEqual(jpql_edges, [], "JPQL must stay unbound (1p9qg is table-level only)")


class OrmEntityMappingCSharpTests(_OrmEntityMappingTestBase):
    """AC-2: EF — `[Table("…")]` (with optional Schema) and origin-checked
    fluent `ToTable("…")` bind analogously; an impostor `ToTable` on a
    non-EF receiver refuses."""

    def test_table_attribute_binds_exact_edge_set(self):
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/Person.cs": (
                "[Table(\"users\")]\n"
                "public class Person { public long Id { get; set; } }\n"
            ),
            "cs/Models.cs": (
                "public class Models { }\n"
                "[Table(\"events\", Schema = \"analytics\")]\n"
                "public class EventRecord { }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("cs/Models.cs::EventRecord", "db/schema.sql::analytics.events", "LITERAL_DERIVED"),
            ("cs/Person.cs", "db/schema.sql::users", "LITERAL_DERIVED"),
        ])

    def test_totable_entity_chain_and_builder_param_bind(self):
        # Both EF fluent shapes: the `.Entity<T>()` receiver chain and the
        # `IEntityTypeConfiguration<T>.Configure(EntityTypeBuilder<T>)` param
        # form — the entity type resolves to the unique project class.
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/Widget.cs": "public class Widget { }\n",
            "cs/Gadget.cs": "public class Gadget { }\n",
            "cs/Config.cs": (
                "public class AppDbContext {\n"
                "  protected void OnModelCreating(ModelBuilder modelBuilder) {\n"
                "    modelBuilder.Entity<Widget>().ToTable(\"audit_log\");\n"
                "  }\n"
                "}\n"
                "public class GadgetConfig {\n"
                "  public void Configure(EntityTypeBuilder<Gadget> builder) {\n"
                "    builder.ToTable(\"events\", \"analytics\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("cs/Gadget.cs", "db/schema.sql::analytics.events", "LITERAL_DERIVED"),
            ("cs/Widget.cs", "db/schema.sql::audit_log", "LITERAL_DERIVED"),
        ])

    def test_impostor_totable_on_non_ef_receiver_refuses(self):
        # Neither an `.Entity<T>()` chain nor an EntityTypeBuilder<T>
        # parameter: the origin is not established, so the sink never fires
        # (no edge, no counter — it is not a sink at all).
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/Report.cs": "public class Report { public void ToTable(string n) { } }\n",
            "cs/Impostor.cs": (
                "public class Impostor {\n"
                "  public void Run(Report report) { report.ToTable(\"users\"); }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [])
        self.assertEqual(self._orm_stats(payload), {})

    def test_totable_variable_name_is_dynamic_refusal(self):
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/Gadget.cs": "public class Gadget { }\n",
            "cs/Config.cs": (
                "public class GadgetConfig {\n"
                "  public void Configure(EntityTypeBuilder<Gadget> builder, string name) {\n"
                "    builder.ToTable(name);\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [])
        stats = self._orm_stats(payload)
        self.assertEqual(stats.get("dynamic_refused"), 1, stats)

    def test_nameof_table_attribute_is_dynamic_refusal(self):
        # nameof(User) is compile-time-constant to the compiler but a
        # COMPUTED name to this capture: only string literals bind (AC-3).
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/Person.cs": (
                "[Table(nameof(Person))]\n"
                "public class Person { }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [])
        stats = self._orm_stats(payload)
        self.assertEqual(stats.get("dynamic_refused"), 1, stats)


class OrmEntityMappingRefusalTests(_OrmEntityMappingTestBase):
    """AC-3: unique-match-or-drop — ambiguous table names drop; unmatched
    names mint namespaced `external::sql::` targets only; ambiguous entity
    types (ToTable) drop."""

    def test_ambiguous_table_match_drops(self):
        # Two `users` tables (dev + prod DDL): binding either would be a
        # guess. The edge drops and the drop is counted.
        self._require("java", "sql")
        payload = self._build({
            "db/dev.sql": "CREATE TABLE users (id INT);\n",
            "db/prod.sql": "CREATE TABLE users (id INT, created_at TEXT);\n",
            "src/User.java": (
                "@Entity\n"
                "@Table(name = \"users\")\n"
                "public class User { }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [])
        stats = self._orm_stats(payload)
        self.assertEqual(stats.get("ambiguous_dropped"), 1, stats)
        self.assertEqual(stats.get("bound"), 0, stats)

    def test_schema_qualified_declaration_beats_bare_twin(self):
        # A schema-qualified declaration resolves to the exact qualified
        # object even when a bare same-leaf twin exists.
        self._require("java", "sql")
        payload = self._build({
            "db/a.sql": "CREATE TABLE analytics.events (id INT);\n",
            "db/b.sql": "CREATE TABLE events (id INT);\n",
            "src/EventRecord.java": (
                "@Entity\n"
                "@Table(name = \"events\", schema = \"analytics\")\n"
                "public class EventRecord { }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("src/EventRecord.java", "db/a.sql::analytics.events", "LITERAL_DERIVED"),
        ])

    def test_unmatched_name_mints_namespaced_external_only(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/Ghost.java": (
                "@Entity\n"
                "@Table(name = \"missing_tbl\")\n"
                "public class Ghost { }\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("src/Ghost.java", "external::sql::missing_tbl", "LITERAL_DERIVED"),
        ])
        stats = self._orm_stats(payload)
        self.assertEqual(stats.get("external"), 1, stats)
        bare_external = [
            e for e in payload["edges"]
            if str(e.get("target")) == "external::missing_tbl"
        ]
        self.assertEqual(bare_external, [], "unmatched mappings must use the sql:: namespace")

    def test_ambiguous_entity_type_drops_totable_candidate(self):
        # Two project classes named Widget: resolving `.Entity<Widget>()`
        # to either would be a guess — the candidate drops, counted.
        self._require("csharp", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "cs/a/Widget.cs": "public class Widget { }\n",
            "cs/b/Widget.cs": "public class Widget { }\n",
            "cs/Config.cs": (
                "public class AppDbContext {\n"
                "  protected void OnModelCreating(ModelBuilder modelBuilder) {\n"
                "    modelBuilder.Entity<Widget>().ToTable(\"users\");\n"
                "  }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [])
        stats = self._orm_stats(payload)
        self.assertEqual(stats.get("entity_unresolved"), 1, stats)


class OrmEntityMappingImpactTests(_OrmEntityMappingTestBase):
    """AC-4: `code_impact` on a table reaches its mapped entities (hop 1 via
    `maps_to` — the data-layer default-traversal exception) and their
    existing callers (hop 2 via `calls`); explicit `relations` opts out; the
    edge weights/costs match the literal-derived family exactly."""

    def _load_graph_query(self):
        path = SCRIPTS_ROOT / "graph_query.py"
        spec = importlib.util.spec_from_file_location("graph_query_orm_impact_test", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["graph_query_orm_impact_test"] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_impact_on_table_reaches_entity_and_its_callers(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": "CREATE TABLE users (id INT PRIMARY KEY);\n",
            "src/Entities.java": (
                "public class Entities {}\n"
                "@Entity\n"
                "@Table(name = \"users\")\n"
                "class User { }\n"
            ),
            "src/UserService.java": (
                "public class UserService {\n"
                "  void save() { User u = new User(); }\n"
                "}\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("src/Entities.java::User", "db/schema.sql::users", "LITERAL_DERIVED"),
        ])
        gq = self._load_graph_query()
        idx = gq.GraphQueryIndex(payload)
        impact = idx.graph_impact("users")
        self.assertTrue(impact["resolved"])
        affected_ids = {str(a.get("node_id") if isinstance(a, dict) else a) for a in impact["affected"]}
        self.assertIn("src/Entities.java::User", affected_ids,
                      "the mapped entity must join the table's blast radius")
        self.assertIn("src/UserService.java::UserService.save", affected_ids,
                      "the entity's existing callers must join transitively")
        # Explicit relations opt OUT of the data-layer exception.
        impact_calls = idx.graph_impact("users", relations=("calls",))
        calls_ids = {str(a.get("node_id") if isinstance(a, dict) else a) for a in impact_calls["affected"]}
        self.assertEqual(
            calls_ids & {"src/Entities.java::User", "src/UserService.java::UserService.save"},
            set(),
        )

    def test_maps_to_weight_cost_and_consumer_registration_parity(self):
        gq = self._load_graph_query()
        map_edge = {"source": "a.java::User", "target": "db/s.sql::users",
                    "relation": "maps_to", "confidence": "LITERAL_DERIVED"}
        config_edge = {"source": "a.java::A.m", "target": "app.yml::k",
                       "relation": "reads_config", "confidence": "LITERAL_DERIVED"}
        # Blast-radius weight: down-weighted exactly like the literal family.
        self.assertEqual(
            gq._edge_confidence_weight(map_edge),
            gq._edge_confidence_weight(config_edge),
        )
        self.assertEqual(gq._edge_confidence_weight(map_edge), gq._EXTRACTED_EDGE_WEIGHT)
        # Path cost: structural tier — a mapping hop never out-competes calls.
        self.assertEqual(gq._path_edge_cost(map_edge), gq._PATH_COST_STRUCTURAL)
        # The data-layer relation set carries the mapping relation (the
        # impact exception + report fan counting both key off it).
        self.assertIn("maps_to", gq._SQL_DATA_LAYER_RELATIONS)

    def test_report_fan_in_counts_mapping_edges(self):
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": "CREATE TABLE users (id INT PRIMARY KEY);\n",
            "src/User.java": (
                "@Entity\n"
                "@Table(name = \"users\")\n"
                "public class User { }\n"
            ),
        })
        gq = self._load_graph_query()
        idx = gq.GraphQueryIndex(payload)
        report = idx.report()
        fan_in = {row["node_id"]: row for row in report["fan_in"]}
        self.assertIn("db/schema.sql::users", fan_in,
                      "entity mappings count toward the table's fan_in")
        self.assertEqual(fan_in["db/schema.sql::users"]["sql_kind"], "table")


class OrmEntityMappingSeamAndFragmentTests(_OrmEntityMappingTestBase):
    """AC-5 support: the mapping rides the SHARED annotation/attribute seam
    (both 1p9qf sink captures and 1p9qg mappings green on one build) and its
    edges are finalize-only (never in fragments — the `external::sql::`
    invariant contract extended to `maps_to`)."""

    def test_shared_seam_serves_both_changes_on_one_build(self):
        # One build where the SAME annotation machinery feeds 1p9qf (native
        # @Query SQL capture) and 1p9qg (@Table mapping) — both bind.
        self._require("java", "sql")
        payload = self._build({
            "db/schema.sql": self.SCHEMA,
            "src/User.java": (
                "@Entity\n"
                "@Table(name = \"users\")\n"
                "public class User { }\n"
            ),
            "src/UserRepo.java": (
                "public interface UserRepo {\n"
                "  @Query(value = \"SELECT * FROM audit_log\", nativeQuery = true)\n"
                "  java.util.List<Object> audits();\n"
                "}\n"
            ),
        })
        self.assertEqual(self._maps_to_edges(payload), [
            ("src/User.java", "db/schema.sql::users", "LITERAL_DERIVED"),
        ])
        self.assertEqual(self._literal_sql_edges(payload), [
            ("src/UserRepo.java::UserRepo.audits", "db/schema.sql::audit_log", "reads"),
        ])

    def test_mapping_edges_are_finalize_only_never_in_fragments(self):
        self._require("java", "sql")
        self._build({
            "db/schema.sql": self.SCHEMA,
            "src/User.java": (
                "@Entity\n"
                "@Table(name = \"users\")\n"
                "public class User { }\n"
            ),
            "src/Ghost.java": (
                "@Entity\n"
                "@Table(name = \"missing_tbl\")\n"
                "public class Ghost { }\n"
            ),
        })
        store = self.mod.GraphStateStore(
            self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.sqlite",
            layer="project", walker_version="1", chunker_version="1",
        )
        try:
            merge_state = store.get_blob("merge_state") or {}
            files = merge_state.get("files") or {}
            self.assertIn("src/User.java", files)
            # The mapping candidates ride the fragment…
            cands = files["src/User.java"].get("orm_entity_candidates") or []
            self.assertEqual(len(cands), 1, cands)
            # …but the minted edges do NOT: no fragment edge (any file) may
            # carry a maps_to relation or an external::sql:: target.
            for rel, fentry in files.items():
                for edge in fentry.get("edges", []) or []:
                    self.assertNotEqual(edge.get("relation"), "maps_to",
                                        f"fragment edge in {rel} carries a bind-pass relation: {edge}")
                    self.assertFalse(
                        str(edge.get("target", "")).startswith("external::sql::"),
                        f"fragment edge in {rel} carries a bind-pass target: {edge}",
                    )
        finally:
            store.close()
